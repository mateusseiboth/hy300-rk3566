"""Testes do kernel/reboot-recovery (entrar na recovery só pelo registrador de reboot-mode).

1. Compila os testes de unidade em C com o gcc do host e roda.
2. Se o binário aarch64 já foi compilado (kernel/reboot-recovery/build.sh) e o
   qemu-aarch64-static existe, roda o binário sob `qemu-aarch64-static -strace` com um
   sysrq e um /proc/mounts falsos e confere as syscalls; com o strace do host, confere
   também a string "recovery" já decodificada. Como usuário comum o host devolve EPERM
   no reboot: nada reinicia. O teste se recusa a rodar como root.

Rodar: python3 -m unittest discover -s tests
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "kernel", "reboot-recovery")
BINARY = os.environ.get(
    "HY300_REBOOT_RECOVERY", os.path.expanduser("~/hy300-work/marco1/reboot-recovery/reboot-recovery"))
QEMU = shutil.which("qemu-aarch64-static")
STRACE = shutil.which("strace")

ALL_RO = "/dev/block/dm-0 / ext4 ro,seclabel 0 0\ntmpfs /dev tmpfs rw 0 0\n"
STILL_RW = ALL_RO + "/dev/block/dm-5 /data f2fs rw,lazytime 0 0\n"


@unittest.skipUnless(shutil.which("gcc"), "gcc do host ausente")
class UnitTest(unittest.TestCase):
    def test_c_unit_tests_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = os.path.join(tmp, "test_reboot_recovery")
            subprocess.run(["gcc", "-std=c11", "-D_GNU_SOURCE", "-Wall", "-Wextra", "-Werror",
                            "-o", exe, os.path.join(SRC, "test_reboot_recovery.c"),
                            os.path.join(SRC, "reboot_recovery.c")], check=True)
            out = subprocess.run([exe], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)


@unittest.skipUnless(QEMU and os.path.isfile(BINARY), "binário aarch64 ou qemu-aarch64-static ausente")
@unittest.skipIf(os.geteuid() == 0, "não rodar como root: o reboot seria de verdade")
class QemuStraceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-reboot-")
        self.sysrq = os.path.join(self.tmp, "sysrq-trigger")
        self.mounts = os.path.join(self.tmp, "mounts")
        open(self.sysrq, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_binary(self, mounts, *extra):
        with open(self.mounts, "w") as f:
            f.write(mounts)
        argv = [QEMU, "-strace", BINARY, "--sysrq", self.sysrq, "--mounts", self.mounts,
                "--timeout-ms", "300", *extra]
        return subprocess.run(argv, capture_output=True, text=True, timeout=30)

    def read_sysrq(self):
        with open(self.sysrq) as f:
            return f.read()

    def test_calls_sync_sysrq_u_then_restart2_recovery(self):
        out = self.run_binary(ALL_RO)
        trace = out.stderr
        self.assertEqual(self.read_sysrq(), "u")
        reboot = re.search(r"reboot\(([^)]*)\)", trace)
        self.assertIsNotNone(reboot, trace)
        args = reboot.group(1)
        # o -strace do qemu mostra os números em decimal e não decodifica a string
        magic1, magic2, cmd, arg = args.split(",")[:4]
        self.assertEqual(int(magic1), 0xfee1dead)
        self.assertEqual(int(magic2), 0x28121969)
        self.assertEqual(int(cmd), 0xa1b2c3d4)
        self.assertNotEqual(int(arg), 0)
        self.assertLess(trace.index("sync("), trace.index("reboot("))
        self.assertLess(trace.rindex("sync("), trace.index("reboot("))
        # como usuário comum o kernel do host recusa: o binário reporta e sai com erro
        self.assertNotEqual(out.returncode, 0)

    @unittest.skipUnless(STRACE, "strace do host ausente")
    def test_host_strace_decodes_recovery_argument(self):
        with open(self.mounts, "w") as f:
            f.write(ALL_RO)
        argv = [STRACE, "-f", "-e", "trace=reboot", QEMU, BINARY, "--sysrq", self.sysrq,
                "--mounts", self.mounts, "--timeout-ms", "300"]
        out = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        self.assertIn('reboot(LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2, LINUX_REBOOT_CMD_RESTART2, '
                      '"recovery") = -1 EPERM', out.stderr)

    def test_dry_run_does_not_touch_anything(self):
        out = self.run_binary(ALL_RO, "--dry-run")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("reboot(", out.stderr)
        self.assertEqual(self.read_sysrq(), "")
        self.assertIn('reboot(0xfee1dead, 0x28121969, 0xa1b2c3d4, "recovery")', out.stdout)

    def test_reboots_anyway_after_timeout_with_rw_mounts(self):
        out = self.run_binary(STILL_RW)
        self.assertIn("reboot(", out.stderr)
        self.assertIn("ainda rw", out.stdout + out.stderr)

    def test_aborts_when_sysrq_cannot_be_written(self):
        os.remove(self.sysrq)
        os.mkdir(self.sysrq)
        out = self.run_binary(ALL_RO)
        self.assertNotEqual(out.returncode, 0)
        self.assertNotIn("reboot(", out.stderr)

    def test_rejects_extra_arguments(self):
        out = self.run_binary(ALL_RO, "bootloader")
        self.assertEqual(out.returncode, 2)
        self.assertNotIn("reboot(", out.stderr)


if __name__ == "__main__":
    unittest.main()
