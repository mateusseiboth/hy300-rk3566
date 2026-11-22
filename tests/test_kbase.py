"""Testes do kernel/lib-kbase.sh: a escolha da base do kernel no build-marco1.sh.

Duas bases:
  - ack (padrão): kernel Android da Rockchip (branch hy300-ack-6.1), rockchip_defconfig +
    android-14.config + rk3566_hy300.config, clang dos prebuilts do LineageOS (LLVM=1);
  - bsp: o BSP Linux develop-6.1 (branch hy300-6.1), rockchip_linux_defconfig + rk3566.config +
    rk3566_hy300.config, GCC cruzado do Fedora.

Cada teste roda as funções num bash de verdade (`source` da biblioteca) e lê as variáveis que
elas definem. Nada é compilado.

Rodar: python3 -I -m unittest discover -s tests
"""
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "kernel", "lib-kbase.sh")

PRINT_VARS = r"""
printf 'configs=%s\n' "${KCONFIGS[*]}"
printf 'make=%s\n' "${KMAKE_TOOLCHAIN[*]}"
printf 'strip=%s\n' "$KSTRIP"
printf 'kout=%s\n' "$KOUT_DEFAULT"
printf 'work=%s\n' "$KWORK_DEFAULT"
printf 'android=%s\n' "$KANDROID"
"""


def run_bash(script, **env):
    full_env = dict(os.environ, **env)
    return subprocess.run(["bash", "-c", f'set -euo pipefail; source "{LIB}"; {script}'],
                          capture_output=True, text=True, env=full_env)


def parse_vars(stdout):
    return dict(line.split("=", 1) for line in stdout.splitlines() if "=" in line)


class SelectKbaseTest(unittest.TestCase):
    def select(self, base):
        result = run_bash(f"select_kbase {base}; {PRINT_VARS}", HOME="/home/teste")
        self.assertEqual(result.returncode, 0, result.stderr)
        return parse_vars(result.stdout)

    def test_ack_uses_android_configs_in_order(self):
        self.assertEqual(self.select("ack")["configs"],
                         "rockchip_defconfig android-14.config rk3566_hy300.config")

    def test_ack_builds_with_llvm(self):
        values = self.select("ack")
        self.assertEqual(values["make"], "LLVM=1 LLVM_IAS=1")
        self.assertEqual(values["strip"], "llvm-strip")

    def test_ack_has_its_own_output_dirs(self):
        values = self.select("ack")
        self.assertEqual(values["kout"], "/home/teste/hy300-work/kbuild-ack-6.1")
        self.assertEqual(values["work"], "/home/teste/hy300-work/marco1-ack")
        self.assertEqual(values["android"], "1")

    def test_bsp_keeps_the_marco1_build(self):
        values = self.select("bsp")
        self.assertEqual(values["configs"], "rockchip_linux_defconfig rk3566.config rk3566_hy300.config")
        self.assertEqual(values["make"], "CROSS_COMPILE=aarch64-linux-gnu-")
        self.assertEqual(values["strip"], "aarch64-linux-gnu-strip")
        self.assertEqual(values["kout"], "/home/teste/hy300-work/kbuild-6.1")
        self.assertEqual(values["work"], "/home/teste/hy300-work/marco1")
        self.assertEqual(values["android"], "0")

    def test_unknown_base_fails(self):
        result = run_bash("select_kbase gki")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("base do kernel desconhecida: gki", result.stderr)


class TreeTest(unittest.TestCase):
    def setUp(self):
        self.tree = tempfile.mkdtemp(prefix="hy300-kbase-")

    def tearDown(self):
        shutil.rmtree(self.tree)

    def touch(self, relative):
        path = os.path.join(self.tree, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()

    def require(self, base):
        return run_bash(f'select_kbase {base}; require_kbase_tree "{self.tree}"')

    def test_ack_accepts_android_tree(self):
        self.touch("kernel/configs/android-14.config")
        self.touch("arch/arm64/configs/rockchip_defconfig")
        self.assertEqual(self.require("ack").returncode, 0)

    def test_ack_refuses_linux_bsp_tree(self):
        self.touch("arch/arm64/configs/rockchip_linux_defconfig")
        result = self.require("ack")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("não é a base ack", result.stderr)
        self.assertIn("kernel/configs/android-14.config", result.stderr)

    def test_bsp_refuses_android_tree(self):
        self.touch("kernel/configs/android-14.config")
        self.touch("arch/arm64/configs/rockchip_defconfig")
        self.touch("arch/arm64/configs/rockchip_linux_defconfig")
        result = self.require("bsp")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("não é a base bsp", result.stderr)

    def test_bsp_accepts_linux_bsp_tree(self):
        self.touch("arch/arm64/configs/rockchip_linux_defconfig")
        self.assertEqual(self.require("bsp").returncode, 0)


class ToolchainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-clang-")
        self.clang_dir = os.path.join(self.tmp, "clang-r000000")
        os.makedirs(os.path.join(self.clang_dir, "bin"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def add_clang(self):
        clang = os.path.join(self.clang_dir, "bin", "clang")
        with open(clang, "w") as f:
            f.write("#!/bin/sh\necho 'Android (0, based on r000000) clang version 20.0.0'\n")
        os.chmod(clang, 0o755)

    def test_ack_puts_clang_first_in_path(self):
        self.add_clang()
        result = run_bash('select_kbase ack; use_kbase_toolchain; command -v clang', CLANG_DIR=self.clang_dir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), os.path.join(self.clang_dir, "bin", "clang"))

    def test_ack_without_clang_fails_with_hint(self):
        result = run_bash("select_kbase ack; use_kbase_toolchain", CLANG_DIR=self.clang_dir)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"clang ausente em {self.clang_dir}/bin", result.stderr)

    def test_ack_default_clang_is_lineage_r547379(self):
        result = run_bash('select_kbase ack; printf "%s" "$CLANG_DIR"', HOME="/home/teste")
        self.assertEqual(result.stdout,
                         "/home/teste/android/lineage/prebuilts/clang/host/linux-x86/clang-r547379")

    def test_bsp_does_not_need_clang(self):
        result = run_bash("select_kbase bsp; use_kbase_toolchain", CLANG_DIR=self.clang_dir)
        self.assertEqual(result.returncode, 0, result.stderr)


ANDROID_BASE = "CONFIG_ANDROID_BINDER_IPC=y\n# CONFIG_DEVMEM is not set\n"
CONDITIONAL = '<kernel minlts="6.1.0" />\n'


class AndroidKconfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hy300-kconfig-")
        self.reqs = os.path.join(self.tmp, "android-6.1")
        os.mkdir(self.reqs)
        with open(os.path.join(self.reqs, "android-base.config"), "w") as f:
            f.write(ANDROID_BASE)
        with open(os.path.join(self.reqs, "android-base-conditional.xml"), "w") as f:
            f.write(CONDITIONAL)
        self.dotconfig = os.path.join(self.tmp, ".config")
        self.report = os.path.join(self.tmp, "kconfig-check.txt")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_config(self, text):
        with open(self.dotconfig, "w") as f:
            f.write(text)

    def check(self, base="ack", reqs=None):
        return run_bash(f'select_kbase {base}; check_android_kconfig "{self.dotconfig}" "{reqs or self.reqs}" '
                        f'"{self.report}" 6.1.172')

    def test_passes_and_writes_report(self):
        self.write_config("CONFIG_ANDROID_BINDER_IPC=y\n")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 diferenças", result.stdout)
        with open(self.report) as f:
            self.assertIn("0 diferenças", f.read())

    def test_fails_on_difference(self):
        self.write_config("CONFIG_DEVMEM=y\n")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FALHOU: o .config não atende", result.stdout + result.stderr)
        with open(self.report) as f:
            report = f.read()
        self.assertIn("CONFIG_ANDROID_BINDER_IPC: exige y, tem n", report)
        self.assertIn("CONFIG_DEVMEM: exige n, tem y", report)

    def test_skips_without_requirements_dir(self):
        self.write_config("")
        result = self.check(reqs=os.path.join(self.tmp, "nada"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pulado", result.stdout)

    def test_bsp_is_not_checked(self):
        self.write_config("CONFIG_DEVMEM=y\n")
        result = self.check(base="bsp")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pulado", result.stdout)
        self.assertFalse(os.path.exists(self.report))


if __name__ == "__main__":
    unittest.main()
