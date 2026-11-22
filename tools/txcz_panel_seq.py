#!/usr/bin/env python3
"""Sequência SPI de inicialização do painel LCD do HY300, tirada do kernel de fábrica.

O panel_simple_probe do kernel 4.19 da TXCZ manda ao controlador do painel, por SPI de 3 fios
em bit-bang (GPIO1_D5 dados, GPIO1_D6 clock, GPIO1_D7 CS, GPIO2_A0 strobe), 26 quadros de
uma tabela fixa em .rodata: o quadro i tem `contagem[i]` bytes, a partir de
`tabela + i * 0x5e`, e depois do quadro 24 (0x29, display on) há 200 ms de pausa.

Endereços (kallsyms do kernel de fábrica): `panel_simple_funcs` = 0xffffff80093c2660; a tabela
fica em +0x38 e as contagens (u16) em +0x968. `_text` = 0xffffff8008080000 é o offset 0 da
Image. O DT do 6.1 leva a tabela em `hy300,spi-init-sequence` como
[atraso_ms, tamanho, bytes...] por quadro.

Uso: txcz_panel_seq.py Image_de_fabrica   (imprime a propriedade para o DTS)
"""
import re
import struct
import sys

TEXT = 0xffffff8008080000
FUNCS = 0xffffff80093c2660
TABLE = FUNCS + 0x38
COUNTS = FUNCS + 0x968
ROWS = 26
ROW_STRIDE = 0x5e
DELAYS_MS = {24: 200}
PROPERTY = "hy300,spi-init-sequence"


def read_factory_rows(image):
    counts = struct.unpack_from(f"<{ROWS}H", image, COUNTS - TEXT)
    return [list(struct.unpack_from(f"<{n}H", image, TABLE - TEXT + i * ROW_STRIDE))
            for i, n in enumerate(counts)]


def to_dt_bytes(rows, delays):
    out = []
    for i, row in enumerate(rows):
        out += [delays.get(i, 0), len(row)] + row
    return out


def parse_dts_property(dts):
    match = re.search(re.escape(PROPERTY) + r"\s*=\s*/bits/\s*8\s*<([^>]*)>", dts)
    return [int(x, 16) for x in match.group(1).split()] if match else None


def format_dts_property(rows, delays):
    lines = []
    for i, row in enumerate(rows):
        frame = [delays.get(i, 0), len(row)] + row
        lines.append("\t\t\t" + " ".join(f"0x{b:02x}" for b in frame))
    return f"\t\t{PROPERTY} = /bits/ 8 <\n" + "\n".join(lines) + "\n\t\t>;"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1], "rb") as f:
        print(format_dts_property(read_factory_rows(f.read()), DELAYS_MS))
