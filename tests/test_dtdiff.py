"""Testes do tools/dtdiff.py (diferenças nó a nó entre duas saídas do dtnorm.py).

Rodar: python3 -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import dtdiff  # noqa: E402

FACTORY = """\
/ {
  model = "fabrica"
}
/leds {
  compatible = "gpio-leds"
}
/leds/fan {
  gpios = <&/gpio0 0xd 0x0>
}
/hdmi {
  status = "disabled"
}
/pinctrl/x {
  rockchip,pins = <0x0 0x1 0x0 &/pinctrl/pcfg>
}
"""

PORT = """\
/ {
  model = "porte"
}
/leds {
  compatible = "gpio-leds"
}
/hdmi {
  status = "disabled"
  extra = <0x1>
}
/novo {
  status = "okay"
}
/velho {
  status = "disabled"
}
"""


class ParseTest(unittest.TestCase):
    def test_parse_reads_nodes_and_properties(self):
        nodes = dtdiff.parse(FACTORY)
        self.assertEqual(nodes["/leds/fan"], {"gpios": "<&/gpio0 0xd 0x0>"})
        self.assertEqual(nodes["/"], {"model": '"fabrica"'})


class DiffTest(unittest.TestCase):
    def setUp(self):
        self.lines = dtdiff.diff(dtdiff.parse(FACTORY), dtdiff.parse(PORT))

    def test_lists_nodes_only_in_each_side(self):
        self.assertIn("- /leds/fan", self.lines)
        self.assertIn("+ /novo", self.lines)

    def test_marks_disabled_nodes(self):
        self.assertIn("+ /velho (disabled)", self.lines)

    def test_lists_changed_properties(self):
        self.assertIn('~ / model: "fabrica" -> "porte"', self.lines)
        self.assertIn("~ /hdmi extra: (ausente) -> <0x1>", self.lines)

    def test_ignores_equal_properties(self):
        self.assertFalse(any(line.startswith("~ /leds ") for line in self.lines))

    def test_skips_prefixes(self):
        lines = dtdiff.diff(dtdiff.parse(FACTORY), dtdiff.parse(PORT), skip=("/pinctrl",))
        self.assertFalse(any("/pinctrl" in line for line in lines))
        self.assertIn("- /pinctrl/x", self.lines)


if __name__ == "__main__":
    unittest.main()
