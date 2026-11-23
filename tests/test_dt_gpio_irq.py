"""Testes do tools/dt_gpio_irq.py: teclas do gpio-keys contra os LEDs e o DT de fábrica.

O DT do 6.1 pôs a tecla de energia no GPIO1_B0 (o pino do LED "green", saída em nível baixo)
com IRQ_TYPE_NONE: a interrupção fica em nível baixo para sempre e a CPU0 passa o boot inteiro
atendendo a tecla (2,7 milhões de interrupções aos 17 s). O de fábrica usa o GPIO1_A0.

Rodar: python3 -I -m unittest discover -s tests
Os DTs sintéticos são compilados com o dtc (pulados sem ele). O teste do DT do porte usa o DTB
de HY300_PORT_DTB e é pulado sem ele.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import dt_gpio_irq  # noqa: E402

REPO = os.path.join(os.path.dirname(__file__), "..")
FACTORY_DTB = os.path.join(REPO, "device-tree", "rk3566-hy300-txcz.dtb")
PORT_DTB = os.environ.get("HY300_PORT_DTB", "")

BASE = """\
/dts-v1/;
/ {
\t#address-cells = <1>;
\t#size-cells = <0>;
\tgpio1: gpio@fe740000 {
\t\treg = <0xfe740000>;
\t\tgpio-controller;
\t\t#gpio-cells = <2>;
\t\tinterrupt-controller;
\t\t#interrupt-cells = <2>;
\t};
\tleds {
\t\tcompatible = "gpio-leds";
\t\tgreen {
\t\t\tgpios = <&gpio1 8 1>;
\t\t};
\t};
\tgpio-keys {
\t\tcompatible = "gpio-keys";
%s
\t};
};
"""

KEY_ON_LED_PIN = """\
\t\tpower-key {
\t\t\tlabel = "GPIO Key Home";
\t\t\tinterrupt-parent = <&gpio1>;
\t\t\tinterrupts = <8 0>;
\t\t\tlinux,code = <116>;
\t\t};"""

KEY_FACTORY_IRQ = """\
\t\tPOWER {
\t\t\tlabel = "GPIO Key Home";
\t\t\tinterrupt-parent = <&gpio1>;
\t\t\tinterrupts = <0 8>;
\t\t\tlinux,code = <116>;
\t\t};"""

KEY_GPIO = """\
\t\tpower-key {
\t\t\tlabel = "GPIO Key Home";
\t\t\tgpios = <&gpio1 0 1>;
\t\t\tlinux,code = <116>;
\t\t};"""

KEY_GPIO_OTHER_PIN = """\
\t\tpower-key {
\t\t\tlabel = "GPIO Key Home";
\t\t\tgpios = <&gpio1 3 1>;
\t\t\tlinux,code = <116>;
\t\t};"""


@unittest.skipUnless(shutil.which("dtc"), "sem dtc")
class DtGpioIrqTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def build(self, name, key):
        dts = os.path.join(self.tmp.name, name + ".dts")
        dtb = os.path.join(self.tmp.name, name + ".dtb")
        with open(dts, "w", encoding="utf-8") as f:
            f.write(BASE % key)
        subprocess.run(["dtc", "-q", "-I", "dts", "-O", "dtb", "-o", dtb, dts], check=True)
        return dt_gpio_irq.load(dtb)

    def test_keys_reads_interrupt_key_with_controller_pin_and_type(self):
        keys = dt_gpio_irq.keys(self.build("a", KEY_ON_LED_PIN))
        self.assertEqual(keys, [dt_gpio_irq.Key("/gpio-keys/power-key", 116, "/gpio@fe740000", 8, "irq", 0)])

    def test_keys_reads_gpio_key(self):
        keys = dt_gpio_irq.keys(self.build("a", KEY_GPIO))
        self.assertEqual(keys, [dt_gpio_irq.Key("/gpio-keys/power-key", 116, "/gpio@fe740000", 0, "gpio", 1)])

    def test_led_outputs_lists_controller_and_pin(self):
        self.assertEqual(dt_gpio_irq.led_outputs(self.build("a", KEY_GPIO)), {("/gpio@fe740000", 8)})

    def test_problems_flags_key_on_led_output_and_irq_without_type(self):
        problems = dt_gpio_irq.problems(self.build("a", KEY_ON_LED_PIN))
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("saída de LED" in p for p in problems))
        self.assertTrue(any("sem tipo" in p for p in problems))

    def test_problems_accepts_gpio_key_on_free_pin(self):
        self.assertEqual(dt_gpio_irq.problems(self.build("a", KEY_GPIO)), [])

    def test_problems_against_factory_accepts_same_pin_as_gpio(self):
        factory = self.build("f", KEY_FACTORY_IRQ)
        self.assertEqual(dt_gpio_irq.problems(self.build("p", KEY_GPIO), factory), [])

    def test_problems_against_factory_flags_other_pin(self):
        factory = self.build("f", KEY_FACTORY_IRQ)
        problems = dt_gpio_irq.problems(self.build("p", KEY_GPIO_OTHER_PIN), factory)
        self.assertEqual(len(problems), 1)
        self.assertIn("fábrica", problems[0])

    def test_main_returns_1_and_reports_problems(self):
        dtb = os.path.join(self.tmp.name, "bad.dtb")
        self.build("bad", KEY_ON_LED_PIN)
        with redirect_stdout(StringIO()) as out:
            self.assertEqual(dt_gpio_irq.main(["check", dtb]), 1)
        self.assertIn("FALHOU", out.getvalue())

    def test_main_returns_0_for_clean_dt(self):
        dtb = os.path.join(self.tmp.name, "ok.dtb")
        self.build("ok", KEY_GPIO)
        with redirect_stdout(StringIO()):
            self.assertEqual(dt_gpio_irq.main(["check", dtb]), 0)


class FactoryDtTest(unittest.TestCase):
    def test_factory_power_key_is_gpio1_a0_level_low(self):
        keys = dt_gpio_irq.keys(dt_gpio_irq.load(FACTORY_DTB))
        self.assertEqual([(k.code, k.pin, k.kind, k.flags) for k in keys], [(116, 0, "irq", 8)])


@unittest.skipUnless(PORT_DTB, "sem HY300_PORT_DTB")
class PortDtTest(unittest.TestCase):
    def test_port_dt_has_no_key_problems_against_factory(self):
        port = dt_gpio_irq.load(PORT_DTB)
        self.assertEqual(dt_gpio_irq.problems(port, dt_gpio_irq.load(FACTORY_DTB)), [])


if __name__ == "__main__":
    unittest.main()
