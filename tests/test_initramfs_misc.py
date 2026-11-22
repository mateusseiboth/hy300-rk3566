"""Testes da lógica do /init de teste que mexe na `misc` (kernel/initramfs-test/hy300-test.sh).

O /init do marco 1 só pode apagar o bootloader_message (2048 bytes no início da `misc`)
quando o comando (primeiros 32 bytes) começa com "boot-recovery". Fora isso a `misc`
fica intacta. Os testes rodam as funções de shell contra arquivos falsos.

Rodar: python3 -m unittest discover -s tests
Por padrão usa o /bin/sh do host. Com o busybox aarch64 já compilado e o binfmt do
qemu-aarch64 registrado, roda também com o shell e os applets do próprio busybox (o mesmo
binário que vai no initramfs), com um PATH que só tem os applets dele.
HY300_BUSYBOX aponta para outro binário.
"""
import atexit
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "kernel", "initramfs-test", "hy300-test.sh")
BUSYBOX = os.environ.get(
    "HY300_BUSYBOX", os.path.expanduser("~/hy300-work/marco1/initramfs/rootfs/bin/busybox"))
BINFMT = "/proc/sys/fs/binfmt_misc/qemu-aarch64"

MISC_SIZE = 4 * 1024 * 1024
BCB_SIZE = 2048
AB_DATA_OFFSET = 0x800
LEGACY_BCB_OFFSET = 0x4000


def build_misc(command, extra=b""):
    """misc falsa: BCB no início, dados A/B em 0x800 e o BCB legado da Rockchip em 16 KiB."""
    data = bytearray(MISC_SIZE)
    bcb = command.ljust(32, b"\0") + b"recovery\n--wipe_data\0" + extra
    data[:len(bcb)] = bcb
    data[AB_DATA_OFFSET:AB_DATA_OFFSET + 8] = b"\0AB0\x01\0\0\0"
    legacy = b"boot-recovery".ljust(64, b"\0") + b"recovery\n--wipe_all\0"
    data[LEGACY_BCB_OFFSET:LEGACY_BCB_OFFSET + len(legacy)] = legacy
    return bytes(data)


class ShellRunner:
    """Roda `. hy300-test.sh; <script>` num shell (host ou busybox sob qemu-user)."""

    def __init__(self, argv, env=None):
        self.argv = argv
        self.env = env

    def run(self, script, cwd):
        return subprocess.run(self.argv + ["-c", f'. "{LIB}"; {script}'], cwd=cwd, env=self.env,
                              capture_output=True, text=True, timeout=30)


def build_applet_dir(busybox):
    """Diretório com um link por applet: o PATH dos testes não enxerga o host."""
    applets = subprocess.run([busybox, "--list"], capture_output=True, text=True, check=True)
    bindir = tempfile.mkdtemp(prefix="hy300-busybox-")
    atexit.register(shutil.rmtree, bindir, True)
    for name in applets.stdout.split():
        os.symlink(busybox, os.path.join(bindir, name))
    return bindir


def build_runners():
    runners = {"host": ShellRunner(["/bin/sh"])}
    if os.path.isfile(BUSYBOX) and os.path.isfile(BINFMT):
        env = {"PATH": build_applet_dir(BUSYBOX), "LANG": "C"}
        runners["busybox"] = ShellRunner([BUSYBOX, "sh"], env)
    return runners


class MiscLogicMixin:
    runner = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-misc-")
        self.misc = os.path.join(self.tmp, "misc")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_misc(self, data):
        with open(self.misc, "wb") as f:
            f.write(data)

    def read_misc(self):
        with open(self.misc, "rb") as f:
            return f.read()

    def sh(self, script):
        return self.runner.run(script, self.tmp)

    def test_read_bcb_command_stops_at_nul(self):
        self.write_misc(build_misc(b"boot-recovery"))
        out = self.sh('read_bcb_command "$PWD/misc"')
        self.assertEqual(out.stdout, "boot-recovery\n")

    def test_read_bcb_command_reads_only_32_bytes(self):
        self.write_misc(b"x" * 40 + bytes(MISC_SIZE - 40))
        out = self.sh('read_bcb_command "$PWD/misc"')
        self.assertEqual(out.stdout, "x" * 32 + "\n")

    def test_clears_bcb_when_command_is_boot_recovery(self):
        original = build_misc(b"boot-recovery")
        self.write_misc(original)
        out = self.sh('clear_bcb_if_recovery "$PWD/misc"')
        after = self.read_misc()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(after[:BCB_SIZE], bytes(BCB_SIZE))
        self.assertEqual(after[BCB_SIZE:], original[BCB_SIZE:])
        self.assertEqual(len(after), MISC_SIZE)

    def test_clears_when_command_only_starts_with_boot_recovery(self):
        self.write_misc(build_misc(b"boot-recovery-hy300"))
        out = self.sh('clear_bcb_if_recovery "$PWD/misc"')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.read_misc()[:BCB_SIZE], bytes(BCB_SIZE))

    def test_keeps_misc_when_command_is_other(self):
        for command in (b"bootonce-bootloader", b"boot-fastboot", b" boot-recovery", b"Boot-recovery"):
            with self.subTest(command=command):
                original = build_misc(command)
                self.write_misc(original)
                out = self.sh('clear_bcb_if_recovery "$PWD/misc"')
                self.assertNotEqual(out.returncode, 0)
                self.assertEqual(self.read_misc(), original)

    def test_keeps_misc_when_command_is_empty(self):
        original = build_misc(b"")
        self.write_misc(original)
        out = self.sh('clear_bcb_if_recovery "$PWD/misc"')
        self.assertNotEqual(out.returncode, 0)
        self.assertEqual(self.read_misc(), original)

    def test_keeps_legacy_bcb_at_16k(self):
        # A misc de fábrica tem "boot-recovery --wipe_all" em 16 KiB (BCB legado da
        # Rockchip, que o U-Boot ignora). O init não pode encostar nele.
        original = build_misc(b"")
        self.write_misc(original)
        self.sh('clear_bcb_if_recovery "$PWD/misc"')
        self.assertEqual(self.read_misc()[LEGACY_BCB_OFFSET:], original[LEGACY_BCB_OFFSET:])

    def test_clear_reports_what_happened(self):
        self.write_misc(build_misc(b"boot-recovery"))
        cleared = self.sh('clear_bcb_if_recovery "$PWD/misc"').stdout
        self.write_misc(build_misc(b"bootonce-bootloader"))
        kept = self.sh('clear_bcb_if_recovery "$PWD/misc"').stdout
        self.assertIn("boot-recovery", cleared)
        self.assertIn("bootonce-bootloader", kept)

    def test_missing_device_is_not_cleared(self):
        out = self.sh('clear_bcb_if_recovery "$PWD/nao-existe"')
        self.assertNotEqual(out.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "nao-existe")))


class PartitionLookupMixin:
    runner = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-sysfs-")
        self.block = os.path.join(self.tmp, "block")
        self.add_block("mmcblk2", "DEVTYPE=disk", 30535680)
        self.add_block("mmcblk2p1", "PARTNAME=uboot", 8192)
        self.add_block("mmcblk2p3", "PARTNAME=misc", 8192)
        self.add_block("mmcblk2p4", "PARTNAME=miscx", 8192)
        self.add_block("mmcblk2p9", "PARTNAME=recovery", 221184)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def add_block(self, name, line, sectors):
        d = os.path.join(self.block, name)
        os.makedirs(d)
        with open(os.path.join(d, "uevent"), "w") as f:
            f.write(f"MAJOR=179\nMINOR=0\nDEVNAME={name}\n{line}\n")
        with open(os.path.join(d, "size"), "w") as f:
            f.write(f"{sectors}\n")

    def sh(self, script):
        return self.runner.run(script, self.tmp)

    def test_find_partition_by_exact_name(self):
        out = self.sh('find_partition_by_name misc "$PWD/block"')
        self.assertEqual(out.stdout, "mmcblk2p3\n")
        self.assertEqual(out.returncode, 0)

    def test_find_partition_fails_when_absent(self):
        out = self.sh('find_partition_by_name userdata "$PWD/block"')
        self.assertEqual(out.stdout, "")
        self.assertNotEqual(out.returncode, 0)

    def test_misc_size_must_be_4_mib(self):
        ok = self.sh('is_misc_size_expected mmcblk2p3 "$PWD/block"')
        wrong = self.sh('is_misc_size_expected mmcblk2p9 "$PWD/block"')
        self.assertEqual(ok.returncode, 0)
        self.assertNotEqual(wrong.returncode, 0)

    def test_wait_for_partition_gives_up_after_timeout(self):
        out = self.sh('wait_for_partition userdata 0 "$PWD/block"')
        self.assertNotEqual(out.returncode, 0)

    def test_wait_for_partition_returns_name(self):
        out = self.sh('wait_for_partition misc 1 "$PWD/block"')
        self.assertEqual(out.stdout, "mmcblk2p3\n")


class KmsgMixin:
    runner = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-kmsg-")
        self.kmsg = os.path.join(self.tmp, "kmsg")
        open(self.kmsg, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_each_line_becomes_one_prefixed_record(self):
        out = self.runner.run(
            'printf "linha 1\\n\\n  linha 3  \\n" | send_lines_to_kmsg secao "$PWD/kmsg"', self.tmp)
        self.assertEqual(out.returncode, 0, out.stderr)
        with open(self.kmsg) as f:
            self.assertEqual(f.read(), "hy300: [secao] linha 1\nhy300: [secao]   linha 3  \n")

    def test_section_runs_command_and_reports_failure(self):
        out = self.runner.run('report_section falha "$PWD/kmsg" cat "$PWD/nao-existe"', self.tmp)
        self.assertEqual(out.returncode, 0, out.stderr)
        with open(self.kmsg) as f:
            text = f.read()
        self.assertIn("hy300: [falha] ", text)
        self.assertIn("nao-existe", text)


def make_cases():
    cases = {}
    for label, runner in build_runners().items():
        for mixin in (MiscLogicMixin, PartitionLookupMixin, KmsgMixin):
            name = f"{mixin.__name__.replace('Mixin', '')}_{label}"
            cases[name] = type(name, (mixin, unittest.TestCase), {"runner": runner})
    return cases


globals().update(make_cases())

if __name__ == "__main__":
    unittest.main()
