"""Testes do tools/wifi_payload.py: credenciais, configuração de rede e firmware do modo Wi-Fi.

O modo hy300.wifi=1 do initramfs de teste precisa de três coisas que não podem ir para o
repositório: o firmware da AICSemi (lido do vendor.img de fábrica), a rede (SSID e senha) e o
IP fixo. O build lê tudo de arquivos locais e falha com mensagem clara se faltar algo.
Os valores aqui são fictícios (192.0.2.0/24 é a rede de documentação TEST-NET-1).

Rodar: python3 -I -m unittest discover -s tests
"""
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")
sys.path.insert(0, TOOLS)

import wifi_payload  # noqa: E402

WPA_SUPPLICANT = os.environ.get("HY300_WPA_SUPPLICANT",
                                os.path.expanduser("~/hy300-work/marco1/wifi-root/usr/sbin/wpa_supplicant"))
BINFMT = "/proc/sys/fs/binfmt_misc/qemu-aarch64"

EXAMPLE = (
    "# exemplo\n"
    "WIFI_SSID=RedeExemplo\n"
    "WIFI_PSK=senha-de-exemplo\n"
    "\n"
    "WIFI_ADDRESS=192.0.2.10/24\n"
    "WIFI_GATEWAY=192.0.2.1\n"
    "WIFI_DNS=192.0.2.1\n"
)


class CredentialsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-wifi-")
        self.path = os.path.join(self.tmp, "credenciais.conf")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, text, mode=0o600):
        with open(self.path, "w") as f:
            f.write(text)
        os.chmod(self.path, mode)

    def test_reads_all_keys(self):
        self.write(EXAMPLE)
        creds = wifi_payload.read_credentials(self.path)
        self.assertEqual(creds["WIFI_SSID"], "RedeExemplo")
        self.assertEqual(creds["WIFI_PSK"], "senha-de-exemplo")
        self.assertEqual(creds["WIFI_ADDRESS"], "192.0.2.10/24")

    def test_keeps_spaces_inside_ssid(self):
        self.write(EXAMPLE.replace("RedeExemplo", "Rede de Casa"))
        self.assertEqual(wifi_payload.read_credentials(self.path)["WIFI_SSID"], "Rede de Casa")

    def test_missing_file_says_where_to_create_it(self):
        with self.assertRaises(wifi_payload.PayloadError) as ctx:
            wifi_payload.read_credentials(self.path)
        self.assertIn(self.path, str(ctx.exception))
        self.assertIn("WIFI_SSID", str(ctx.exception))

    def test_file_readable_by_others_is_refused(self):
        self.write(EXAMPLE, 0o644)
        with self.assertRaises(wifi_payload.PayloadError) as ctx:
            wifi_payload.read_credentials(self.path)
        self.assertIn("chmod 600", str(ctx.exception))

    def test_missing_key_is_named(self):
        self.write(EXAMPLE.replace("WIFI_GATEWAY=192.0.2.1\n", ""))
        with self.assertRaises(wifi_payload.PayloadError) as ctx:
            wifi_payload.read_credentials(self.path)
        self.assertIn("WIFI_GATEWAY", str(ctx.exception))

    def test_unknown_key_is_refused(self):
        self.write(EXAMPLE + "WIFI_SENHA=x\n")
        with self.assertRaises(wifi_payload.PayloadError):
            wifi_payload.read_credentials(self.path)

    def test_invalid_address_is_refused(self):
        for bad in ("192.0.2.10", "192.0.2.300/24", "rede/24", "192.0.2.10/24; reboot"):
            with self.subTest(bad=bad):
                self.write(EXAMPLE.replace("192.0.2.10/24", bad))
                with self.assertRaises(wifi_payload.PayloadError):
                    wifi_payload.read_credentials(self.path)

    def test_gateway_outside_network_is_refused(self):
        self.write(EXAMPLE.replace("WIFI_GATEWAY=192.0.2.1", "WIFI_GATEWAY=198.51.100.1"))
        with self.assertRaises(wifi_payload.PayloadError) as ctx:
            wifi_payload.read_credentials(self.path)
        self.assertIn("WIFI_GATEWAY", str(ctx.exception))

    def test_passphrase_length_follows_wpa(self):
        for bad in ("curta", "x" * 64):
            with self.subTest(bad=bad):
                self.write(EXAMPLE.replace("senha-de-exemplo", bad))
                with self.assertRaises(wifi_payload.PayloadError):
                    wifi_payload.read_credentials(self.path)

    def test_ssid_length_follows_802_11(self):
        self.write(EXAMPLE.replace("RedeExemplo", "r" * 33))
        with self.assertRaises(wifi_payload.PayloadError):
            wifi_payload.read_credentials(self.path)


def build_creds(**changes):
    creds = {"WIFI_SSID": "RedeExemplo", "WIFI_PSK": "senha-de-exemplo",
             "WIFI_ADDRESS": "192.0.2.10/24", "WIFI_GATEWAY": "192.0.2.1", "WIFI_DNS": "192.0.2.1"}
    creds.update(changes)
    return creds


class WpaConfTest(unittest.TestCase):
    def test_psk_matches_ieee_802_11i_vector(self):
        # IEEE 802.11i-2004, anexo H.4: passphrase "password", SSID "IEEE".
        self.assertEqual(wifi_payload.compute_psk("IEEE", "password"),
                         "f42c6fc52df0ebef9ebb4b90b38a5f902e83fe1b135a70e23aed762e9710a12e")

    def test_conf_has_hex_ssid_and_psk_without_passphrase(self):
        conf = wifi_payload.build_wpa_conf(build_creds(WIFI_SSID='Rede "x"'))
        self.assertIn("ssid=" + 'Rede "x"'.encode().hex() + "\n", conf)
        self.assertIn("psk=" + wifi_payload.compute_psk('Rede "x"', "senha-de-exemplo") + "\n", conf)
        self.assertNotIn("senha-de-exemplo", conf)
        self.assertIn("key_mgmt=WPA-PSK", conf)
        self.assertIn("ctrl_interface=/var/run/wpa_supplicant", conf)

    @unittest.skipUnless(os.path.isfile(WPA_SUPPLICANT) and os.path.isfile(BINFMT),
                         "sem o wpa_supplicant aarch64 compilado ou sem binfmt do qemu-aarch64")
    def test_real_wpa_supplicant_parses_conf(self):
        # O wpa_supplicant é compilado com CONFIG_NO_CONFIG_WRITE: campo desconhecido no
        # arquivo (ex.: update_config) faz ele recusar o arquivo inteiro.
        tmp = tempfile.mkdtemp(prefix="hy300-wpa-")
        self.addCleanup(shutil.rmtree, tmp)
        conf = os.path.join(tmp, "wpa.conf")
        with open(conf, "w") as f:
            f.write(wifi_payload.build_wpa_conf(build_creds(WIFI_SSID="Rede de Teste")))
        out = subprocess.run([WPA_SUPPLICANT, "-c", conf, "-i", "naoexiste0", "-D", "nl80211", "-d"],
                             capture_output=True, text=True, timeout=30)
        self.assertNotIn("Failed to read or parse configuration", out.stdout + out.stderr)
        self.assertIn("ssid='Rede de Teste'", out.stdout)

    def test_net_conf_is_plain_assignments(self):
        conf = wifi_payload.build_net_conf(build_creds())
        self.assertEqual(conf, "WIFI_ADDRESS=192.0.2.10/24\nWIFI_GATEWAY=192.0.2.1\nWIFI_DNS=192.0.2.1\n")
        self.assertNotIn("RedeExemplo", conf)

    def test_net_conf_works_when_sourced_by_sh(self):
        conf = wifi_payload.build_net_conf(build_creds())
        out = subprocess.run(["/bin/sh", "-c", conf + 'echo "$WIFI_ADDRESS $WIFI_GATEWAY $WIFI_DNS"'],
                             capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout, "192.0.2.10/24 192.0.2.1 192.0.2.1\n")


class FirmwareTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-fw-")
        self.dest = os.path.join(self.tmp, "fw")
        self.contents = {name: f"conteudo {name}".encode() for name in ("a.bin", "b.txt")}
        self.expected = {name: hashlib.md5(data).hexdigest() for name, data in self.contents.items()}

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def fake_dump(self, image, inner, out):
        name = os.path.basename(inner)
        self.assertEqual(inner, "/etc/firmware/" + name)
        if name in self.contents:
            with open(out, "wb") as f:
                f.write(self.contents[name])

    def test_d80_list_is_what_the_factory_driver_loads(self):
        self.assertEqual(set(wifi_payload.FIRMWARE_D80), {
            "fw_adid_8800d80_u02.bin", "fw_patch_8800d80_u02.bin", "fw_patch_table_8800d80_u02.bin",
            "fmacfw_8800d80_u02.bin", "aic_userconfig_8800d80.txt"})
        # MD5 que o aic8800_bsp de fábrica imprime no dmesg (kernel/dmesg-boot.txt).
        self.assertEqual(wifi_payload.FIRMWARE_D80["fmacfw_8800d80_u02.bin"], "2aa840eaea976e7fb87e33fd9e82a653")

    def test_extracts_and_checks_md5(self):
        wifi_payload.extract_firmware("vendor.img", self.dest, self.expected, dump=self.fake_dump)
        for name, data in self.contents.items():
            with open(os.path.join(self.dest, name), "rb") as f:
                self.assertEqual(f.read(), data)

    def test_wrong_md5_fails_and_names_the_file(self):
        expected = dict(self.expected, **{"a.bin": "0" * 32})
        with self.assertRaises(wifi_payload.PayloadError) as ctx:
            wifi_payload.extract_firmware("vendor.img", self.dest, expected, dump=self.fake_dump)
        self.assertIn("a.bin", str(ctx.exception))

    def test_missing_file_fails(self):
        expected = dict(self.expected, **{"c.bin": "0" * 32})
        with self.assertRaises(wifi_payload.PayloadError) as ctx:
            wifi_payload.extract_firmware("vendor.img", self.dest, expected, dump=self.fake_dump)
        self.assertIn("c.bin", str(ctx.exception))

    def test_missing_vendor_image_fails_before_dumping(self):
        with self.assertRaises(wifi_payload.PayloadError) as ctx:
            wifi_payload.extract_firmware(os.path.join(self.tmp, "nao-existe.img"), self.dest, self.expected)
        self.assertIn("nao-existe.img", str(ctx.exception))


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-payload-")
        self.creds = os.path.join(self.tmp, "credenciais.conf")
        with open(self.creds, "w") as f:
            f.write(EXAMPLE)
        os.chmod(self.creds, 0o600)
        self.out = os.path.join(self.tmp, "payload")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def fake_dump(self, image, inner, out):
        with open(out, "wb") as f:
            f.write(b"x")

    def test_build_writes_configs_and_firmware(self):
        firmware = {"a.bin": hashlib.md5(b"x").hexdigest()}
        wifi_payload.build_payload(self.creds, "vendor.img", self.out, firmware, dump=self.fake_dump)
        wpa = os.path.join(self.out, "etc", "wpa_supplicant.conf")
        self.assertEqual(stat.S_IMODE(os.stat(wpa).st_mode), 0o600)
        self.assertTrue(os.path.isfile(os.path.join(self.out, "etc", "hy300-wifi.conf")))
        self.assertTrue(os.path.isfile(os.path.join(self.out, "lib", "firmware", "aic8800", "a.bin")))

    def test_cli_fails_with_message_when_credentials_are_missing(self):
        os.remove(self.creds)
        out = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "wifi_payload.py"), "build",
                              "--credentials", self.creds, "--vendor-img", "vendor.img", "--out", self.out],
                             capture_output=True, text=True)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn(self.creds, out.stderr)
        self.assertNotIn("Traceback", out.stderr)


if __name__ == "__main__":
    unittest.main()
