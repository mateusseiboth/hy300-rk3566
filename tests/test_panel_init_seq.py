"""Testes do tools/txcz_panel_seq.py: a sequência SPI de inicialização do painel LCD.

O kernel de fábrica (4.19, TXCZ) manda ao controlador do painel, no panel_simple_probe, uma
tabela fixa de comandos por SPI de 3 fios em bit-bang. O DT do 6.1 leva a mesma tabela em
`hy300,spi-init-sequence` ([atraso_ms, tamanho, bytes...] por comando). Os testes conferem a
conversão e, se a Image de fábrica estiver em ~/hy300-work/kimg/kernel, que o DTS do kernel
tem exatamente a tabela de fábrica.

Rodar: python3 -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import txcz_panel_seq  # noqa: E402

FACTORY_IMAGE = os.path.expanduser("~/hy300-work/kimg/kernel")
KERNEL_DTS = os.path.expanduser(
    "~/hy300-handoff/kernel-hy300-rk3566/arch/arm64/boot/dts/rockchip/rk3566-hy300.dts")


class ConversionTest(unittest.TestCase):
    def test_rows_to_dt_bytes(self):
        rows = [[0xf1, 0x01, 0x00, 0x11], [0xf1, 0x01, 0x00, 0x29], []]
        self.assertEqual(txcz_panel_seq.to_dt_bytes(rows, {1: 200}),
                         [0, 4, 0xf1, 0x01, 0x00, 0x11, 200, 4, 0xf1, 0x01, 0x00, 0x29, 0, 0])

    def test_parse_dts_property(self):
        dts = 'panel {\n\thy300,spi-init-sequence = /bits/ 8 <\n\t\t0x00 0x02 0xf1 0x01\n\t>;\n};\n'
        self.assertEqual(txcz_panel_seq.parse_dts_property(dts), [0, 2, 0xf1, 0x01])


@unittest.skipUnless(os.path.isfile(FACTORY_IMAGE), "Image de fábrica ausente")
class FactoryTableTest(unittest.TestCase):
    def setUp(self):
        with open(FACTORY_IMAGE, "rb") as f:
            self.rows = txcz_panel_seq.read_factory_rows(f.read())

    def test_table_shape(self):
        self.assertEqual(len(self.rows), 26)
        self.assertEqual(self.rows[0], [0xf1, 0x01, 0x03, 0xdf, 0x91, 0x68, 0xf9])
        self.assertEqual(self.rows[23], [0xf1, 0x01, 0x00, 0x11])
        self.assertEqual(self.rows[24], [0xf1, 0x01, 0x00, 0x29])
        self.assertEqual(self.rows[25], [])

    def test_kernel_dts_has_factory_table(self):
        with open(KERNEL_DTS) as f:
            got = txcz_panel_seq.parse_dts_property(f.read())
        self.assertEqual(got, txcz_panel_seq.to_dt_bytes(self.rows, txcz_panel_seq.DELAYS_MS))


if __name__ == "__main__":
    unittest.main()
