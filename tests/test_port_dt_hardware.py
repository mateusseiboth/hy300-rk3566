"""DT do porte (rk3566-hy300.dtb do hy300-ack-6.1): motor de foco, acelerômetro, Bluetooth e HDMI-in.

O que cada nó precisa ter, levantado do DT, do dmesg e do kernel de fábrica:
  - motor de foco: 4 fases no GPIO4_C2..C5 e o fim de curso no GPIO4_D1 (gpio 146..149 e 153 do
    usb-cam-gpio de fábrica, que usava números fixos no código);
  - acelerômetro SC7A20 no I2C0 0x19 (o dmesg de fábrica lê o id 0x11);
  - Bluetooth do AIC8800 no UART1 (ttyS1) com o bluetooth-platdata;
  - amplificador do alto-falante ligado pelo GPIO1_B2 (gpio 42 fixo no mute do dummy-codec de
    fábrica: nível alto = som);
  - RK628 (HDMI -> MIPI CSI) ligado ao csi2-dphy0 e ao rkisp-vir0, e a placa "rockchip,hdmiin"
    no I2S3.

Rodar: HY300_PORT_DTB=<dtb> python3 -I -m unittest discover -s tests
Pulado sem HY300_PORT_DTB.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import dt_gpio_irq as dt  # noqa: E402

PORT_DTB = os.environ.get("HY300_PORT_DTB", "")
GPIO1 = "/pinctrl/gpio@fe740000"
GPIO4 = "/pinctrl/gpio@fe770000"
RK_PB2 = 10
GPIO_ACTIVE_HIGH = 0


def nodes_with(tree, compatible):
    return [p for p, props in tree.items() if compatible.encode() in props.get("compatible", b"").split(b"\0")]


def is_okay(props):
    return props.get("status", b"okay\0").rstrip(b"\0") in (b"okay", b"ok")


def gpio_list(tree, value):
    """[(controlador, pino, flags)] de uma propriedade com vários GPIOs de 2 células."""
    words, ph = dt.cells(value), dt.phandles(tree)
    return [(ph[words[i]], words[i + 1], words[i + 2]) for i in range(0, len(words), 3)]


def remote_endpoint(tree, path):
    return dt.phandles(tree)[dt.cells(tree[path]["remote-endpoint"])[0]]


@unittest.skipUnless(PORT_DTB, "sem HY300_PORT_DTB")
class PortHardwareDtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = dt.load(PORT_DTB)

    def only(self, compatible):
        found = [p for p in nodes_with(self.tree, compatible) if is_okay(self.tree[p])]
        self.assertEqual(len(found), 1, f"{compatible}: {found}")
        return found[0], self.tree[found[0]]

    def test_focus_motor_has_four_phases_on_gpio4_c2_to_c5(self):
        _, props = self.only("txcz,hy300-focus-motor")
        self.assertEqual(gpio_list(self.tree, props["phase-gpios"]),
                         [(GPIO4, pin, GPIO_ACTIVE_HIGH) for pin in (18, 19, 20, 21)])

    def test_focus_motor_limit_switch_is_gpio4_d1(self):
        _, props = self.only("txcz,hy300-focus-motor")
        self.assertEqual(gpio_list(self.tree, props["limit-gpios"]), [(GPIO4, 25, GPIO_ACTIVE_HIGH)])

    def test_accelerometer_sc7a20_on_i2c0_0x19(self):
        path, props = self.only("gs_sc7a20")
        self.assertTrue(path.startswith("/i2c@fdd40000/"))
        self.assertEqual(dt.cells(props["reg"]), [0x19])

    def test_bluetooth_platdata_and_uart1_enabled(self):
        self.only("bluetooth-platdata")
        self.assertTrue(is_okay(self.tree["/serial@fe650000"]))

    def test_rk628_enabled_and_linked_to_csi2_dphy0(self):
        path, _ = self.only("rockchip,rk628-csi-v4l2")
        self.assertTrue(remote_endpoint(self.tree, path + "/port/endpoint").startswith("/csi2-dphy0/"))

    def test_csi2_dphy0_feeds_rkisp_vir0(self):
        self.assertTrue(is_okay(self.tree["/csi2-dphy0"]))
        self.assertTrue(is_okay(self.tree["/rkisp-vir0"]))
        self.assertEqual(remote_endpoint(self.tree, "/rkisp-vir0/port/endpoint@0"),
                         "/csi2-dphy0/ports/port@1/endpoint@0")

    def test_hdmiin_sound_card_on_i2s3(self):
        path = next(p for p in nodes_with(self.tree, "simple-audio-card")
                    if self.tree[p].get("simple-audio-card,name") == b"rockchip,hdmiin\0")
        self.assertTrue(is_okay(self.tree[path]))
        cpu = dt.phandles(self.tree)[dt.cells(self.tree[path + "/simple-audio-card,cpu"]["sound-dai"])[0]]
        self.assertEqual(cpu, "/i2s@fe430000")
        self.assertTrue(is_okay(self.tree[cpu]))

    def card_index(self, name):
        path = next(p for p in nodes_with(self.tree, "simple-audio-card")
                    if self.tree[p].get("simple-audio-card,name") == name.encode() + b"\0")
        return dt.cells(self.tree[path]["hy300,card-index"])

    def test_speaker_card_is_card0_like_factory(self):
        # O áudio do LineageOS usa card 0 = alto-falante (I2S1) e card 1 = HDMI In (I2S3).
        self.assertEqual(self.card_index("rockchip,rockchip-i2s-sound"), [0])

    def test_hdmiin_card_is_card1_like_factory(self):
        self.assertEqual(self.card_index("rockchip,hdmiin"), [1])

    def test_no_placeholder_rk_motor_node(self):
        # o nó "rk_motor" de fábrica não tem driver no 6.1; o motor é o txcz,hy300-focus-motor
        self.assertEqual(nodes_with(self.tree, "usb-cam-gpio"), [])

    def test_speaker_amplifier_enabled_by_gpio1_b2_high(self):
        hogs = [props for path, props in self.tree.items()
                if path.startswith(GPIO1 + "/") and "gpio-hog" in props]
        self.assertEqual(len(hogs), 1, hogs)
        self.assertEqual(dt.cells(hogs[0]["gpios"]), [RK_PB2, GPIO_ACTIVE_HIGH])
        self.assertIn("output-high", hogs[0])


if __name__ == "__main__":
    unittest.main()
