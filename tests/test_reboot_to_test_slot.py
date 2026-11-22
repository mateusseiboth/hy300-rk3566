"""Testes do scripts/reboot-to-test-slot.sh com um `adb` falso no PATH.

O adb falso responde ao uname, à leitura do BCB e ao sha256 da recovery conforme variáveis de
ambiente, e registra cada chamada. Os testes conferem quando o script recusa seguir e que o
binário só roda sem --dry-run quando tudo confere. Nenhum aparelho é usado.

Rodar: python3 -m unittest discover -s tests
"""
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "reboot-to-test-slot.sh")
BINARY = os.environ.get(
    "HY300_REBOOT_RECOVERY", os.path.expanduser("~/hy300-work/marco1/reboot-recovery/reboot-recovery"))
DEST = "/data/local/tmp/hy300-reboot-recovery"

FAKE_ADB = r"""#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
case "$*" in
  "shell uname -m") echo aarch64 ;;
  "shell dd if=/dev/block/by-name/misc"*) printf '%s' "$FAKE_BCB" ;;
  "shell sha256sum /dev/block/by-name/recovery") echo "$FAKE_RECOVERY_SHA  /dev/block/by-name/recovery" ;;
  *) : ;;
esac
"""


@unittest.skipUnless(os.path.isfile(BINARY), "binário aarch64 ausente (kernel/reboot-recovery/build.sh)")
class RebootToTestSlotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-slot-")
        bindir = os.path.join(self.tmp, "bin")
        os.mkdir(bindir)
        adb = os.path.join(bindir, "adb")
        with open(adb, "w") as f:
            f.write(FAKE_ADB)
        os.chmod(adb, 0o755)
        self.image = os.path.join(self.tmp, "recovery-marco1.img")
        with open(self.image, "wb") as f:
            f.write(b"imagem de teste")
        self.log = os.path.join(self.tmp, "adb.log")
        self.env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", FAKE_LOG=self.log,
                        FAKE_BCB="", FAKE_RECOVERY_SHA=self.sha(self.image),
                        REBOOT_BIN=BINARY, TEST_IMAGE=self.image)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    @staticmethod
    def sha(path):
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def run_script(self, *args, **env):
        self.env.update(env)
        return subprocess.run(["bash", SCRIPT, *args], env=self.env, capture_output=True,
                              text=True, timeout=60)

    def calls(self):
        with open(self.log) as f:
            return f.read().splitlines()

    def test_runs_binary_when_bcb_empty_and_image_matches(self):
        out = self.run_script()
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        calls = self.calls()
        self.assertIn(f"shell {DEST} --dry-run", calls)
        self.assertEqual(calls[-1], f"shell {DEST}")

    def test_refuses_when_bcb_has_a_command(self):
        out = self.run_script(FAKE_BCB="boot-recovery")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("boot-recovery", out.stdout)
        self.assertFalse(any(c.startswith("push") or DEST in c for c in self.calls()))

    def test_refuses_when_recovery_has_another_image(self):
        out = self.run_script(FAKE_RECOVERY_SHA="0" * 64)
        self.assertNotEqual(out.returncode, 0)
        self.assertFalse(any(DEST in c for c in self.calls()))

    def test_dry_run_never_runs_the_real_reboot(self):
        out = self.run_script("--dry-run", FAKE_RECOVERY_SHA="0" * 64)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        runs = [c for c in self.calls() if c.startswith(f"shell {DEST}")]
        self.assertEqual(runs, [f"shell {DEST} --dry-run"])


if __name__ == "__main__":
    unittest.main()
