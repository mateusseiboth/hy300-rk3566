#!/usr/bin/env python3
"""Monta os arquivos do modo Wi-Fi (hy300.wifi=1) do initramfs de teste do 6.1.

Nada disto vai para o repositório: o firmware da AICSemi sai do vendor.img de fábrica e a rede
(SSID, senha, IP fixo) de um arquivo local, fora dos repositórios, com modo 600:

    WIFI_SSID=NomeDaRede
    WIFI_PSK=senha
    WIFI_ADDRESS=192.0.2.10/24
    WIFI_GATEWAY=192.0.2.1
    WIFI_DNS=192.0.2.1

Saída em <out>:
    etc/wpa_supplicant.conf      SSID em hexadecimal e a PSK já derivada (sem a senha em claro)
    etc/hy300-wifi.conf          IP, gateway e DNS, lido pelo /init com `.`
    lib/firmware/aic8800/        firmware do AIC8800D80, conferido por MD5

Uso: wifi_payload.py build --credentials ARQ --vendor-img vendor.img --out DIR
"""
import argparse
import hashlib
import ipaddress
import os
import subprocess
import sys

REQUIRED_KEYS = ("WIFI_SSID", "WIFI_PSK", "WIFI_ADDRESS", "WIFI_GATEWAY", "WIFI_DNS")
VENDOR_FIRMWARE_DIR = "/etc/firmware"
FIRMWARE_DEST = os.path.join("lib", "firmware", "aic8800")

# O que o aic8800_bsp/aic8800_fdrv carregam para o AIC8800D80 revisão U02 (SDIO 0xc8a1:0x0082).
# MD5 dos binários: os que o driver de fábrica imprime no dmesg (kernel/dmesg-boot.txt); o
# userconfig não aparece lá e vem do vendor.img de fábrica.
FIRMWARE_D80 = {
    "fw_patch_table_8800d80_u02.bin": "03837cc7d45b566ced87b308339d2898",
    "fw_adid_8800d80_u02.bin": "f546881a81b960d89a672578eb45a809",
    "fw_patch_8800d80_u02.bin": "8202766f27e88f4866f272b45fa5ab66",
    "fmacfw_8800d80_u02.bin": "2aa840eaea976e7fb87e33fd9e82a653",
    "aic_userconfig_8800d80.txt": "2c9d3ab6e42c03bd2adb9f9e2b6180f2",
}


class PayloadError(Exception):
    pass


def require_private_file(path):
    if not os.path.isfile(path):
        raise PayloadError(f"{path} não existe. Crie com as chaves {', '.join(REQUIRED_KEYS)} "
                           f"(uma por linha, CHAVE=valor) e rode chmod 600 {path}")
    if os.stat(path).st_mode & 0o077:
        raise PayloadError(f"{path} pode ser lido por outros usuários: rode chmod 600 {path}")


def parse_assignments(path):
    values = {}
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            line = line.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if not sep or key not in REQUIRED_KEYS:
                raise PayloadError(f"{path}:{number}: linha inválida (chaves aceitas: {', '.join(REQUIRED_KEYS)})")
            values[key] = value
    return values


def require_keys(path, values):
    missing = [key for key in REQUIRED_KEYS if not values.get(key)]
    if missing:
        raise PayloadError(f"{path}: falta {', '.join(missing)}")


def require_wpa_fields(ssid, passphrase):
    if not 1 <= len(ssid.encode()) <= 32:
        raise PayloadError("WIFI_SSID precisa ter de 1 a 32 bytes")
    if not 8 <= len(passphrase) <= 63 or not passphrase.isascii() or not passphrase.isprintable():
        raise PayloadError("WIFI_PSK precisa ter de 8 a 63 caracteres ASCII imprimíveis")


def parse_interface(value):
    if "/" not in value:
        raise PayloadError(f"WIFI_ADDRESS precisa do prefixo (ex.: 192.0.2.10/24): {value!r}")
    try:
        return ipaddress.IPv4Interface(value)
    except ValueError as error:
        raise PayloadError(f"WIFI_ADDRESS inválido: {value!r}") from error


def parse_address(key, value):
    try:
        return ipaddress.IPv4Address(value)
    except ValueError as error:
        raise PayloadError(f"{key} inválido: {value!r}") from error


def require_network(values):
    interface = parse_interface(values["WIFI_ADDRESS"])
    gateway = parse_address("WIFI_GATEWAY", values["WIFI_GATEWAY"])
    parse_address("WIFI_DNS", values["WIFI_DNS"])
    if gateway not in interface.network:
        raise PayloadError(f"WIFI_GATEWAY {gateway} fora da rede {interface.network}")


def read_credentials(path):
    require_private_file(path)
    values = parse_assignments(path)
    require_keys(path, values)
    require_wpa_fields(values["WIFI_SSID"], values["WIFI_PSK"])
    require_network(values)
    return values


def compute_psk(ssid, passphrase):
    """PSK de 256 bits do WPA-PSK (PBKDF2-HMAC-SHA1, 4096 iterações, SSID como sal)."""
    return hashlib.pbkdf2_hmac("sha1", passphrase.encode(), ssid.encode(), 4096, 32).hex()


def build_wpa_conf(creds):
    ssid = creds["WIFI_SSID"]
    return (
        "ctrl_interface=/var/run/wpa_supplicant\n"
        "network={\n"
        f"\tssid={ssid.encode().hex()}\n"
        "\tscan_ssid=1\n"
        "\tkey_mgmt=WPA-PSK\n"
        f"\tpsk={compute_psk(ssid, creds['WIFI_PSK'])}\n"
        "}\n"
    )


def build_net_conf(creds):
    return "".join(f"{key}={creds[key]}\n" for key in ("WIFI_ADDRESS", "WIFI_GATEWAY", "WIFI_DNS"))


def dump_with_debugfs(image, inner, out):
    subprocess.run(["debugfs", "-R", f"dump {inner} {out}", image], capture_output=True, check=False)


def read_md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def extract_one(image, dest, name, md5, dump):
    out = os.path.join(dest, name)
    dump(image, f"{VENDOR_FIRMWARE_DIR}/{name}", out)
    if not os.path.isfile(out) or os.path.getsize(out) == 0:
        raise PayloadError(f"{name} não está em {VENDOR_FIRMWARE_DIR} de {image}")
    got = read_md5(out)
    if got != md5:
        raise PayloadError(f"{name}: MD5 {got}, esperado {md5}")


def extract_firmware(image, dest, firmware=FIRMWARE_D80, dump=dump_with_debugfs):
    if dump is dump_with_debugfs and not os.path.isfile(image):
        raise PayloadError(f"{image} não existe (vendor.img de fábrica, ext4)")
    os.makedirs(dest, exist_ok=True)
    for name, md5 in firmware.items():
        extract_one(image, dest, name, md5, dump)


def write_private(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.chmod(path, 0o600)


def build_payload(credentials, image, out, firmware=FIRMWARE_D80, dump=dump_with_debugfs):
    creds = read_credentials(credentials)
    write_private(os.path.join(out, "etc", "wpa_supplicant.conf"), build_wpa_conf(creds))
    write_private(os.path.join(out, "etc", "hy300-wifi.conf"), build_net_conf(creds))
    extract_firmware(image, os.path.join(out, FIRMWARE_DEST), firmware, dump)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--credentials", required=True)
    build.add_argument("--vendor-img", required=True)
    build.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        build_payload(args.credentials, args.vendor_img, args.out)
    except PayloadError as error:
        print(f"wifi_payload: {error}", file=sys.stderr)
        return 1
    print(f"ok {args.out}: wpa_supplicant.conf, hy300-wifi.conf e {len(FIRMWARE_D80)} arquivos de firmware")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
