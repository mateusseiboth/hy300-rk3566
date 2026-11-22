"""Testes das funções do modo Wi-Fi do /init de teste (kernel/initramfs-test/hy300-wifi.sh).

Com hy300.wifi=1 na cmdline o /init carrega o driver do AIC8800, conecta na rede com o
wpa_supplicant, põe o IP fixo e abre o telnetd, e fica no ar até um prazo (padrão 15 min).
Os comandos que mexem no sistema (insmod, ip, wpa_cli) são trocados por falsos que gravam os
argumentos, como em tests/test_initramfs_misc.py.

Rodar: python3 -I -m unittest discover -s tests
Roda no /bin/sh do host e, se houver o busybox aarch64 e o binfmt do qemu, no busybox também.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

from test_initramfs_misc import BINFMT, BUSYBOX, build_applet_dir

HERE = os.path.dirname(os.path.abspath(__file__))
LIBS = [os.path.join(HERE, "..", "kernel", "initramfs-test", name) for name in ("hy300-test.sh", "hy300-wifi.sh")]

FAKE = """#!/bin/sh
echo "$(basename "$0") $*" >>"$FAKE_LOG"
case "$(basename "$0") $*" in
{cases}
esac
exit 0
"""


def read_text(path):
    with open(path) as f:
        return f.read()


class Runner:
    def __init__(self, argv, path=None):
        self.argv = argv
        self.path = path

    def run(self, script, tmp, fake_bin):
        sources = "; ".join(f'. "{lib}"' for lib in LIBS)
        path = fake_bin + ":" + (self.path or os.environ["PATH"])
        env = {"PATH": path, "FAKE_LOG": os.path.join(tmp, "fake.log"), "LANG": "C"}
        return subprocess.run(self.argv + ["-c", f"{sources}; {script}"], cwd=tmp, env=env,
                              capture_output=True, text=True, timeout=30)


def build_runners():
    runners = {"host": Runner(["/bin/sh"])}
    if os.path.isfile(BUSYBOX) and os.path.isfile(BINFMT):
        runners["busybox"] = Runner([BUSYBOX, "sh"], build_applet_dir(BUSYBOX))
    return runners


class WifiMixin:
    runner = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-wifi-sh-")
        self.bin = os.path.join(self.tmp, "fake-bin")
        os.makedirs(self.bin)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def fake(self, name, cases=""):
        path = os.path.join(self.bin, name)
        with open(path, "w") as f:
            f.write(FAKE.format(cases=cases))
        os.chmod(path, 0o755)

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        return path

    def sh(self, script):
        return self.runner.run(script, self.tmp, self.bin)

    def calls(self):
        path = os.path.join(self.tmp, "fake.log")
        return read_text(path).splitlines() if os.path.exists(path) else []

    # --- cmdline ---

    def test_wifi_mode_needs_exact_flag(self):
        cases = {"console=tty0 hy300.wifi=1 panic=10": 0, "hy300.wifi=1": 0, "hy300.wifi=0": 1,
                 "hy300.wifi=10": 1, "xhy300.wifi=1": 1, "console=tty0": 1}
        for cmdline, expected in cases.items():
            with self.subTest(cmdline=cmdline):
                self.write("cmdline", cmdline + "\n")
                self.assertEqual(self.sh('is_wifi_mode "$PWD/cmdline"').returncode, expected)

    def test_read_cmdline_number(self):
        self.write("cmdline", "a=1 hy300.wifi_limit=300 hy300.wifi=1\n")
        out = self.sh('read_cmdline_number hy300.wifi_limit 900 "$PWD/cmdline"')
        self.assertEqual(out.stdout, "300\n")

    def test_read_cmdline_number_falls_back_to_default(self):
        for cmdline in ("hy300.wifi=1", "hy300.wifi_limit=", "hy300.wifi_limit=9x", "hy300.wifi_limitx=5"):
            with self.subTest(cmdline=cmdline):
                self.write("cmdline", cmdline + "\n")
                out = self.sh('read_cmdline_number hy300.wifi_limit 900 "$PWD/cmdline"')
                self.assertEqual(out.stdout, "900\n")

    # --- módulos ---

    def test_loads_bsp_with_firmware_path_then_fdrv(self):
        self.fake("insmod")
        out = self.sh("load_wifi_modules /lib/modules/aic8800 /lib/firmware/aic8800")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.calls(), [
            "insmod /lib/modules/aic8800/aic8800_bsp.ko aic_fw_path=/lib/firmware/aic8800 sdio_clock=50000000",
            "insmod /lib/modules/aic8800/aic8800_fdrv.ko"])

    def test_stops_and_names_the_module_that_failed(self):
        self.fake("insmod", '"insmod /m/aic8800_bsp.ko"*) exit 1 ;;')
        out = self.sh("load_wifi_modules /m /f")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("aic8800_bsp", out.stdout)
        self.assertEqual(len(self.calls()), 1)

    # --- interface ---

    def test_finds_wireless_interface(self):
        os.makedirs(os.path.join(self.tmp, "net", "lo"))
        os.makedirs(os.path.join(self.tmp, "net", "wlan0", "wireless"))
        out = self.sh('find_wireless_iface "$PWD/net"')
        self.assertEqual(out.stdout, "wlan0\n")

    def test_no_wireless_interface(self):
        os.makedirs(os.path.join(self.tmp, "net", "lo"))
        out = self.sh('wait_for_wireless_iface 0 "$PWD/net"')
        self.assertNotEqual(out.returncode, 0)
        self.assertEqual(out.stdout, "")

    # --- wpa_supplicant ---

    def test_wpa_completed(self):
        self.fake("wpa_cli", '*status*) echo "bssid=x"; echo "wpa_state=COMPLETED" ;;')
        out = self.sh("wait_for_wpa_completed wlan0 0")
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_wpa_timeout_reports_last_state(self):
        self.fake("wpa_cli", '*status*) echo "wpa_state=4WAY_HANDSHAKE" ;;')
        out = self.sh("wait_for_wpa_completed wlan0 0")
        self.assertNotEqual(out.returncode, 0)
        self.assertEqual(out.stdout, "4WAY_HANDSHAKE\n")

    def test_starts_wpa_supplicant_in_background_with_nl80211(self):
        self.fake("wpa_supplicant")
        out = self.sh("start_wpa_supplicant wlan0 /etc/wpa_supplicant.conf /tmp/wpa.log")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.calls(), [
            "wpa_supplicant -B -D nl80211 -i wlan0 -c /etc/wpa_supplicant.conf -f /tmp/wpa.log"])

    # --- IP fixo ---

    def test_configures_static_ip_route_and_dns(self):
        self.fake("ip")
        conf = self.write("hy300-wifi.conf", "WIFI_ADDRESS=192.0.2.10/24\nWIFI_GATEWAY=192.0.2.1\nWIFI_DNS=192.0.2.53\n")
        out = self.sh(f'configure_static_ip wlan0 "{conf}" "$PWD/resolv.conf"')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.calls(), [
            "ip link set lo up",
            "ip addr add 192.0.2.10/24 dev wlan0",
            "ip link set wlan0 up",
            "ip route add default via 192.0.2.1 dev wlan0"])
        self.assertEqual(read_text(os.path.join(self.tmp, "resolv.conf")), "nameserver 192.0.2.53\n")

    def test_static_ip_failure_stops(self):
        self.fake("ip", '"ip addr add"*) exit 2 ;;')
        conf = self.write("hy300-wifi.conf", "WIFI_ADDRESS=192.0.2.10/24\nWIFI_GATEWAY=192.0.2.1\nWIFI_DNS=192.0.2.1\n")
        out = self.sh(f'configure_static_ip wlan0 "{conf}" "$PWD/resolv.conf"')
        self.assertNotEqual(out.returncode, 0)
        self.assertNotIn("ip route add default via 192.0.2.1 dev wlan0", self.calls())

    def test_reads_ipv4_of_interface(self):
        self.fake("ip", '"ip -4 -o addr show dev wlan0") echo "3: wlan0    inet 192.0.2.10/24 scope global wlan0" ;;')
        out = self.sh("read_iface_ip wlan0")
        self.assertEqual(out.stdout, "192.0.2.10\n")

    def test_announces_ip_with_unsolicited_arp(self):
        # O IP fixo é o mesmo que o Android usa com outro MAC: o ARP não solicitado atualiza
        # o cache dos vizinhos na hora.
        self.fake("arping")
        out = self.sh("announce_ip wlan0 192.0.2.10")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.calls(), ["arping -U -c 2 -I wlan0 192.0.2.10"])

    # --- prazo ---

    def test_deadline_reached_only_after_time_and_without_stay_file(self):
        stay = os.path.join(self.tmp, "ficar")
        self.assertNotEqual(self.sh(f'is_deadline_reached 899 900 "{stay}"').returncode, 0)
        self.assertEqual(self.sh(f'is_deadline_reached 900 900 "{stay}"').returncode, 0)
        open(stay, "w").close()
        self.assertNotEqual(self.sh(f'is_deadline_reached 5000 900 "{stay}"').returncode, 0)

    def test_deadline_file_is_read_with_safe_default(self):
        self.write("prazo", "900\n")
        self.assertEqual(self.sh('read_deadline "$PWD/prazo"').stdout, "900\n")
        self.write("prazo", "lixo\n")
        self.assertEqual(self.sh('read_deadline "$PWD/prazo"').stdout, "0\n")
        self.assertEqual(self.sh('read_deadline "$PWD/nao-existe"').stdout, "0\n")

    def test_shorten_deadline_never_extends(self):
        path = self.write("prazo", "900\n")
        self.sh('shorten_deadline "$PWD/prazo" 200')
        self.assertEqual(read_text(path), "200\n")
        self.sh('shorten_deadline "$PWD/prazo" 500')
        self.assertEqual(read_text(path), "200\n")

    def test_countdown_respects_stay_file(self):
        stay = os.path.join(self.tmp, "ficar")
        self.assertEqual(self.sh(f'build_countdown 100 940 "{stay}"').stdout, "reinicia em 840 s\n")
        open(stay, "w").close()
        self.assertEqual(self.sh(f'build_countdown 100 940 "{stay}"').stdout, "sem reinício automático\n")

    def test_status_line_shows_ip_telnet_and_countdown(self):
        stay = os.path.join(self.tmp, "ficar")
        out = self.sh(f'build_wifi_status 192.0.2.10 100 940 "{stay}"')
        self.assertEqual(out.stdout, "IP 192.0.2.10, telnet 192.0.2.10 23; reinicia em 840 s\n")
        open(stay, "w").close()
        out = self.sh(f'build_wifi_status 192.0.2.10 100 940 "{stay}"')
        self.assertEqual(out.stdout, "IP 192.0.2.10, telnet 192.0.2.10 23; sem reinício automático\n")


def make_cases():
    cases = {}
    for label, runner in build_runners().items():
        name = f"Wifi_{label}"
        cases[name] = type(name, (WifiMixin, unittest.TestCase), {"runner": runner})
    return cases


globals().update(make_cases())

if __name__ == "__main__":
    unittest.main()
