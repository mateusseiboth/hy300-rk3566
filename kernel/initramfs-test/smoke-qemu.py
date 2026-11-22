#!/usr/bin/env python3
"""Teste de fumaça do initramfs do marco 1 num kernel 6.1 de verdade, no QEMU (virt).

Monta um disco GPT falso com uma partição "misc" de 4 MiB que tem "boot-recovery" no
bootloader_message (como o Android 12 deixa depois do `adb reboot recovery`), boota o
kernel com o initramfs e confere:
  - o /init achou a misc pelo nome, apagou só os 2048 bytes do BCB e não tocou no resto;
  - o relatório saiu no log do kernel;
  - o /init tentou armar o watchdog (o virt não tem um, então registra a ausência);
  - o reset de emergência (sysrq b) aconteceu perto dos 20 s (o QEMU sai com -no-reboot);
  - com hy300.shutdown_debug=1, o /init usa reboot -f com initcall_debug ligado e o kernel
    registra o shutdown de cada dispositivo antes de reiniciar.

O kernel precisa do config do marco 1 mais o fragmento qemu.config deste diretório
(PL011 e virtio). O build-marco1.sh faz esse build à parte quando o QEMU está instalado.

Uso: smoke-qemu.py Image initramfs.cpio.gz dir_de_trabalho [misc_de_fabrica.img]
"""
import os
import re
import subprocess
import sys

SECTOR = 512
MISC_START = 10240
MISC_SECTORS = 8192
BCB_SIZE = 2048
TIMEOUT = 180
# rockchip_drm_init faz SMC para o TF-A, que não existe no virt.
CMDLINE = "console=ttyAMA0 hy300.test=marco1 panic=10 initcall_blacklist=rockchip_drm_init"
EXPECTED = (
    "hy300: [misc] misc: comando 'boot-recovery' apagado",
    "hy300: [init] relatório: fim",
    "hy300: [init] watchdog: /dev/watchdog ausente",
    "hy300: [init] marco1: fim, sysrq b",
    "sysrq: Resetting",
)


def build_misc(factory):
    misc = bytearray(open(factory, "rb").read() if factory else bytes(MISC_SECTORS * SECTOR))
    bcb = b"boot-recovery".ljust(32, b"\0") + b"recovery\n--hy300-smoke\0"
    misc[:len(bcb)] = bcb
    return bytes(misc)


def create_disk(path, misc):
    with open(path, "wb") as f:
        f.truncate(32 * 1024 * 1024)
    layout = "label: gpt\nstart=2048, size=8192, name=uboot\nsize=8192, name=misc\nsize=16384, name=recovery\n"
    subprocess.run(["sfdisk", "-q", path], input=layout, text=True, check=True)
    with open(path, "r+b") as f:
        f.seek(MISC_START * SECTOR)
        f.write(misc)


def read_misc(path):
    with open(path, "rb") as f:
        f.seek(MISC_START * SECTOR)
        return f.read(MISC_SECTORS * SECTOR)


SHUTDOWN_DEBUG_EXPECTED = (
    "hy300: [init] marco1: fim, reboot -f com initcall_debug",
    "reboot: Restarting system",
)


def run_qemu(image, initramfs, disk, extra=""):
    argv = ["qemu-system-aarch64", "-M", "virt,gic-version=3", "-cpu", "cortex-a55", "-smp", "4",
            "-m", "1024", "-kernel", image, "-initrd", initramfs, "-append", f"{CMDLINE} {extra}".strip(),
            "-drive", f"if=none,file={disk},format=raw,id=d", "-device", "virtio-blk-device,drive=d",
            "-nographic", "-no-reboot"]
    return subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT).stdout


def find_reboot_time(log):
    match = re.search(r"\[\s*([0-9.]+)\] sysrq: Resetting", log)
    return float(match.group(1)) if match else None


def check(log, before, after):
    failures = [f"falta no log: {line}" for line in EXPECTED if line not in log]
    failures += [] if after[:BCB_SIZE] == bytes(BCB_SIZE) else ["BCB não foi apagado"]
    failures += [] if after[BCB_SIZE:] == before[BCB_SIZE:] else ["misc mudou além do BCB"]
    reboot_at = find_reboot_time(log)
    failures += [] if reboot_at and 18 <= reboot_at <= 40 else [f"reboot fora da janela: {reboot_at}"]
    return failures


def check_shutdown_debug(log):
    failures = [f"falta no log: {line}" for line in SHUTDOWN_DEBUG_EXPECTED if line not in log]
    failures += [] if re.search(r": shutdown$", log, re.M) else ["nenhum dispositivo registrou o shutdown"]
    return failures


def run_shutdown_debug(image, initramfs, workdir, factory):
    disk = os.path.join(workdir, "smoke-disk-shutdown.img")
    create_disk(disk, build_misc(factory))
    log = run_qemu(image, initramfs, disk, "hy300.shutdown_debug=1")
    with open(os.path.join(workdir, "smoke-qemu-shutdown.log"), "w") as f:
        f.write(log)
    return check_shutdown_debug(log)


def main(image, initramfs, workdir, factory=None):
    os.makedirs(workdir, exist_ok=True)
    disk = os.path.join(workdir, "smoke-disk.img")
    before = build_misc(factory)
    create_disk(disk, before)
    log = run_qemu(image, initramfs, disk)
    with open(os.path.join(workdir, "smoke-qemu.log"), "w") as f:
        f.write(log)
    failures = check(log, before, read_misc(disk))
    failures += run_shutdown_debug(image, initramfs, workdir, factory)
    for failure in failures:
        print("FALHOU:", failure)
    print("ok: smoke-qemu" if not failures else f"smoke-qemu: {len(failures)} falha(s), log em {workdir}")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
