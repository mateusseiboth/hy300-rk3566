"""Testes do tools/kconfig_check.py (config do kernel contra os requisitos do Android).

Rodar: python3 -I -m unittest discover -s tests
"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import kconfig_check  # noqa: E402

FRAGMENT = """\
# Requisitos de exemplo
CONFIG_ANDROID_BINDER_IPC=y
CONFIG_ANDROID_BINDERFS=y
CONFIG_ANDROID_BINDER_DEVICES=""
CONFIG_DEFAULT_MMAP_MIN_ADDR=32768
# CONFIG_DEVMEM is not set
CONFIG_PSI=y
"""

CONDITIONAL = """\
<kernel minlts="6.1.0" />

<!-- ARM64 -->
<group>
\t<conditions>
\t\t<config>
\t\t\t<key>CONFIG_ARM64</key>
\t\t\t<value type="bool">y</value>
\t\t</config>
\t</conditions>
\t<config>
\t\t<key>CONFIG_ARM64_PAN</key>
\t\t<value type="bool">y</value>
\t</config>
\t<!--<config>
\t\t<key>CONFIG_CFI_CLANG</key>
\t\t<value type="bool">y</value>
\t</config>-->
</group>

<!-- ARM 32 bits: nao vale para arm64 -->
<group>
\t<conditions>
\t\t<config>
\t\t\t<key>CONFIG_ARM</key>
\t\t\t<value type="bool">y</value>
\t\t</config>
\t</conditions>
\t<config>
\t\t<key>CONFIG_AEABI</key>
\t\t<value type="bool">y</value>
\t</config>
</group>

<group>
\t<conditions>
\t\t<config>
\t\t\t<key>CONFIG_ARM64</key>
\t\t\t<value type="bool">y</value>
\t\t</config>
\t</conditions>
\t<config>
\t\t<key>CONFIG_ARM64_VA_BITS</key>
\t\t<value type="int">39</value>
\t</config>
\t<config>
\t\t<key>CONFIG_DEVKMEM</key>
\t\t<value type="bool">n</value>
\t</config>
</group>
"""

DOTCONFIG = """\
CONFIG_ARM64=y
CONFIG_ANDROID_BINDER_IPC=y
CONFIG_ANDROID_BINDER_DEVICES=""
CONFIG_DEFAULT_MMAP_MIN_ADDR=4096
CONFIG_DEVMEM=y
CONFIG_PSI=m
CONFIG_ARM64_PAN=y
CONFIG_ARM64_VA_BITS=39
"""


def write_temp(test, text, suffix):
    handle = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False)
    handle.write(text)
    handle.close()
    test.addCleanup(os.unlink, handle.name)
    return handle.name


class ParseTest(unittest.TestCase):
    def test_parse_fragment_reads_values_and_not_set(self):
        req = kconfig_check.parse_fragment(FRAGMENT)
        self.assertEqual(req["CONFIG_ANDROID_BINDER_IPC"], "y")
        self.assertEqual(req["CONFIG_ANDROID_BINDER_DEVICES"], '""')
        self.assertEqual(req["CONFIG_DEFAULT_MMAP_MIN_ADDR"], "32768")
        self.assertEqual(req["CONFIG_DEVMEM"], "n")
        self.assertNotIn("# Requisitos de exemplo", req)

    def test_parse_dotconfig_treats_not_set_as_n(self):
        cfg = kconfig_check.parse_fragment("# CONFIG_X is not set\nCONFIG_Y=m\n")
        self.assertEqual(cfg, {"CONFIG_X": "n", "CONFIG_Y": "m"})

    def test_parse_conditional_skips_commented_config(self):
        groups = kconfig_check.parse_conditional_xml(CONDITIONAL)
        self.assertEqual(len(groups), 3)
        conditions, required = groups[0]
        self.assertEqual(conditions, {"CONFIG_ARM64": "y"})
        self.assertEqual(required, {"CONFIG_ARM64_PAN": "y"})

    def test_parse_conditional_reads_minlts(self):
        self.assertEqual(kconfig_check.parse_minlts(CONDITIONAL), "6.1.0")
        self.assertIsNone(kconfig_check.parse_minlts("<group></group>"))


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.cfg = kconfig_check.parse_fragment(DOTCONFIG)

    def test_find_mismatches_lists_missing_wrong_and_forbidden(self):
        req = kconfig_check.parse_fragment(FRAGMENT)
        found = {m.key: m for m in kconfig_check.find_mismatches(req, self.cfg)}
        self.assertEqual(found["CONFIG_ANDROID_BINDERFS"].actual, "n")
        self.assertEqual(found["CONFIG_DEFAULT_MMAP_MIN_ADDR"].actual, "4096")
        self.assertEqual(found["CONFIG_DEVMEM"].required, "n")
        self.assertEqual(found["CONFIG_PSI"].actual, "m")
        self.assertNotIn("CONFIG_ANDROID_BINDER_IPC", found)
        self.assertNotIn("CONFIG_ANDROID_BINDER_DEVICES", found)

    def test_is_condition_met(self):
        self.assertTrue(kconfig_check.is_condition_met({"CONFIG_ARM64": "y"}, self.cfg))
        self.assertFalse(kconfig_check.is_condition_met({"CONFIG_ARM": "y"}, self.cfg))

    def test_collect_requirements_applies_only_met_groups(self):
        groups = kconfig_check.parse_conditional_xml(CONDITIONAL)
        req = kconfig_check.collect_requirements({}, groups, self.cfg)
        self.assertIn("CONFIG_ARM64_PAN", req)
        self.assertIn("CONFIG_DEVKMEM", req)
        self.assertNotIn("CONFIG_AEABI", req)
        self.assertNotIn("CONFIG_CFI_CLANG", req)

    def test_check_version_against_minlts(self):
        self.assertTrue(kconfig_check.is_version_at_least("6.1.172", "6.1.0"))
        self.assertTrue(kconfig_check.is_version_at_least("6.1.25", "6.1.25"))
        self.assertFalse(kconfig_check.is_version_at_least("6.1.24", "6.1.25"))
        self.assertFalse(kconfig_check.is_version_at_least("5.15.200", "6.1.0"))


class MainTest(unittest.TestCase):
    def run_main(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = kconfig_check.main(argv)
        return code, out.getvalue()

    def test_main_reports_and_fails_on_mismatch(self):
        req_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.unlink(os.path.join(req_dir, n)) for n in os.listdir(req_dir)] and None)
        with open(os.path.join(req_dir, "android-base.config"), "w") as f:
            f.write(FRAGMENT)
        with open(os.path.join(req_dir, "android-base-conditional.xml"), "w") as f:
            f.write(CONDITIONAL)
        dotconfig = write_temp(self, DOTCONFIG, ".config")
        code, out = self.run_main([req_dir, dotconfig, "--kernel-version", "6.1.172"])
        self.assertEqual(code, 1)
        self.assertIn("CONFIG_ANDROID_BINDERFS", out)
        # ausente no .config vale "n", que é o exigido pelo grupo condicional
        self.assertNotIn("CONFIG_DEVKMEM", out)
        self.assertNotIn("CONFIG_AEABI", out)
        self.assertIn("6.1.172 >= 6.1.0", out)

    def test_main_passes_when_everything_matches(self):
        req_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.unlink(os.path.join(req_dir, n)) for n in os.listdir(req_dir)] and None)
        with open(os.path.join(req_dir, "android-base.config"), "w") as f:
            f.write("CONFIG_PSI=y\n# CONFIG_DEVMEM is not set\n")
        dotconfig = write_temp(self, "CONFIG_PSI=y\n", ".config")
        code, out = self.run_main([req_dir, dotconfig])
        self.assertEqual(code, 0)
        self.assertIn("0 diferenças", out)


if __name__ == "__main__":
    unittest.main()
