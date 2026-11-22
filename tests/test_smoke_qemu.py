"""Testes das funções de leitura de log do kernel/initramfs-test/smoke-qemu.py.

O kernel Android liga o CONFIG_PRINTK_CALLER, que acrescenta "[T1]" ou "[C2]" depois do
tempo de cada linha; o BSP Linux não. O smoke tem de achar o reboot nos dois formatos.

Rodar: python3 -I -m unittest discover -s tests
"""
import importlib.util
import os
import unittest

SMOKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kernel", "initramfs-test", "smoke-qemu.py")


def load_smoke():
    spec = importlib.util.spec_from_file_location("smoke_qemu", SMOKE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FindRebootTimeTest(unittest.TestCase):
    smoke = load_smoke()

    def test_linux_bsp_format(self):
        log = "[   21.221367] sysrq: Resetting\n"
        self.assertEqual(self.smoke.find_reboot_time(log), 21.221367)

    def test_android_format_with_caller(self):
        log = "[   21.217143][    T1] hy300: [init] marco1: fim\n[   21.221367][    T1] sysrq: Resetting\n"
        self.assertEqual(self.smoke.find_reboot_time(log), 21.221367)

    def test_android_format_with_cpu_caller(self):
        log = "[   51.650824][   C3] sysrq: Resetting\n"
        self.assertEqual(self.smoke.find_reboot_time(log), 51.650824)

    def test_no_reboot(self):
        self.assertIsNone(self.smoke.find_reboot_time("[    1.0][    T1] nada\n"))


class ShutdownDebugTest(unittest.TestCase):
    smoke = load_smoke()

    def test_device_shutdown_line_with_caller(self):
        log = ("[   21.0][    T1] hy300: [init] marco1: fim, reboot -f com initcall_debug\n"
               "[   21.1][    T1] platform fe310000.sdhci: shutdown\n"
               "[   21.2][    T1] reboot: Restarting system\n")
        self.assertEqual(self.smoke.check_shutdown_debug(log), [])


if __name__ == "__main__":
    unittest.main()
