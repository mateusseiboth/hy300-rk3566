"""Testes do tools/dtnorm.py (DTB -> texto comparável, phandles viram caminhos).

Rodar: python3 -m unittest discover -s tests
Precisa da biblioteca `fdt` (pip install fdt, num venv fora do repo); sem ela, os testes são pulados.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

try:
    import fdt
    import dtnorm
except ImportError:  # pragma: no cover - depende do ambiente
    fdt = None


def build_dtb():
    tree = fdt.FDT()
    pinctrl = fdt.Node("pinctrl")
    pull_none = fdt.Node("pcfg-pull-none")
    pull_none.append(fdt.Property("bias-disable"))
    pull_none.append(fdt.PropWords("phandle", 5))
    pull_up = fdt.Node("pcfg-pull-up")
    pull_up.append(fdt.PropWords("phandle", 6))
    group = fdt.Node("i2c0")
    xfer = fdt.Node("i2c0-xfer")
    xfer.append(fdt.PropWords("rockchip,pins", 0, 9, 1, 5, 0, 10, 1, 6))
    xfer.append(fdt.PropWords("phandle", 7))
    group.append(xfer)
    for node in (pull_none, pull_up, group):
        pinctrl.append(node)
    tree.add_item(pinctrl, "/")
    i2c = fdt.Node("i2c@fdd40000")
    i2c.append(fdt.PropWords("pinctrl-0", 7))
    tree.add_item(i2c, "/")
    timings = fdt.Node("display-timings")
    timings.append(fdt.PropWords("native-mode", 9))
    timing0 = fdt.Node("timing0")
    timing0.append(fdt.PropWords("phandle", 9))
    timings.append(timing0)
    panel = fdt.Node("panel")
    panel.append(timings)
    tree.add_item(panel, "/")
    return tree.to_dtb(version=17)


@unittest.skipIf(fdt is None, "biblioteca fdt ausente")
class NormalizeTest(unittest.TestCase):
    def setUp(self):
        self.text = dtnorm.normalize(build_dtb())

    def test_rockchip_pins_resolve_pcfg_phandle(self):
        self.assertIn(
            "rockchip,pins = <0x0 0x9 0x1 &/pinctrl/pcfg-pull-none>, <0x0 0xa 0x1 &/pinctrl/pcfg-pull-up>",
            self.text,
        )

    def test_pinctrl_reference_becomes_path(self):
        self.assertIn("pinctrl-0 = <&/pinctrl/i2c0/i2c0-xfer>", self.text)

    def test_native_mode_becomes_path(self):
        self.assertIn("native-mode = <&/panel/display-timings/timing0>", self.text)

    def test_phandle_property_is_dropped(self):
        self.assertNotIn("phandle =", self.text)


if __name__ == "__main__":
    unittest.main()
