"""Testes do scripts/block-telemetry.sh com um `adb` falso no PATH.

O adb falso registra cada chamada e guarda uma cópia de cada arquivo enviado por `adb push`.
Os testes conferem que o hosts e o .rc vão por push (o `adb exec-in` deste aparelho passa
por um terminal e deixou o .rc com modo 666, que o init ignora), que os dois ficam com modo
644 e que o .rc roda o iptables com um domínio SELinux. Nenhum aparelho é usado.

Rodar: python3 -m unittest discover -s tests
"""
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "block-telemetry.sh")

FAKE_ADB = r"""#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
[[ "$1" == push ]] && cp "$2" "$FAKE_PUSHED/$(basename "$3")"
exit 0
"""


class BlockTelemetryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-tele-")
        bindir = os.path.join(self.tmp, "bin")
        self.pushed = os.path.join(self.tmp, "pushed")
        os.mkdir(bindir)
        os.mkdir(self.pushed)
        adb = os.path.join(bindir, "adb")
        with open(adb, "w") as f:
            f.write(FAKE_ADB)
        os.chmod(adb, 0o755)
        self.log = os.path.join(self.tmp, "adb.log")
        env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", FAKE_LOG=self.log,
                   FAKE_PUSHED=self.pushed)
        self.result = subprocess.run(["bash", SCRIPT], env=env, capture_output=True, text=True,
                                     timeout=60)
        with open(self.log) as f:
            self.calls = f.read().splitlines()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def read_pushed(self, name):
        with open(os.path.join(self.pushed, name)) as f:
            return f.read()

    def test_runs_ok(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)

    def test_never_uses_exec_in(self):
        self.assertFalse([c for c in self.calls if c.startswith("exec-in")])

    def test_pushes_hosts_and_rc(self):
        pushes = [c.split()[-1] for c in self.calls if c.startswith("push ")]
        self.assertIn("/system/etc/hosts", pushes)
        self.assertIn("/system/etc/init/hy300-telemetria.rc", pushes)

    def test_sets_mode_644(self):
        chmods = " ".join(c for c in self.calls if "chmod 644" in c)
        self.assertIn("/system/etc/hosts", chmods)
        self.assertIn("/system/etc/init/hy300-telemetria.rc", chmods)

    def test_hosts_blocks_domains(self):
        hosts = self.read_pushed("hosts")
        self.assertIn("0.0.0.0 shzhtxcz.com", hosts)
        self.assertIn("127.0.0.1       localhost", hosts)

    def test_rc_runs_iptables_with_selinux_domain(self):
        rc = self.read_pushed("hy300-telemetria.rc")
        self.assertIn("seclabel u:r:su:s0", rc)
        self.assertIn("iptables -w -I OUTPUT -d 47.113.90.237 -j REJECT", rc)
        self.assertIn("on property:sys.boot_completed=1", rc)


if __name__ == "__main__":
    unittest.main()
