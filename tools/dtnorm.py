#!/usr/bin/env python3
"""Normaliza um DTB em texto comparável: phandles viram o caminho do nó de destino.

Dois DTBs compilados separadamente têm numeração de phandle diferente; depois de
normalizados, `diff` mostra só diferenças reais (nós, propriedades, valores).

Uso: dtnorm.py arquivo.dtb > saida.txt
Requer a biblioteca `fdt` (pip install fdt).
"""
import re
import sys

import fdt

# propriedades "lista de (phandle + N args)" e o nome do #cells no nó de destino
LIST_PROPS = {
    "clocks": "#clock-cells", "assigned-clocks": "#clock-cells",
    "assigned-clock-parents": "#clock-cells", "resets": "#reset-cells",
    "power-domains": "#power-domain-cells", "phys": "#phy-cells", "dmas": "#dma-cells",
    "iommus": "#iommu-cells", "pwms": "#pwm-cells", "io-channels": "#io-channel-cells",
    "thermal-sensors": "#thermal-sensor-cells", "mboxes": "#mbox-cells",
    "interrupts-extended": "#interrupt-cells", "cooling-device": "#cooling-cells",
    "sound-dai": "#sound-dai-cells", "nvmem-cells": None, "hwlocks": "#hwlock-cells",
    "mux-controls": "#mux-control-cells", "interconnects": "#interconnect-cells",
}
# propriedades que são phandle(s) puros, sem argumentos
SINGLE_RE = re.compile(
    r"^(interrupt-parent|remote-endpoint|phy-handle|memory-region|operating-points-v2|"
    r"cpu-idle-states|next-level-cache|trip|cpu|cpus|pinctrl-\d+|.*-supply|"
    r"rockchip,(grf|pmugrf|cru|pmu|phy-grf|pipe-grf|usbgrf|sram|vo-grf|vop|lvds|dmc)|"
    r"shmem|pm_qos|mmc-pwrseq|snps,(axi|mtl-tx|mtl-rx)-config|"
    r"simple-audio-card,(frame|bitclock)-master|rockchip,(pipe-phy-grf|cif|hw)|"
    r"ports|port|connect|clock-sources|ddr_timing|devfreq|dmc|nvmem|.*-phandle|"
    r"sram|syscon|display-subsystem|backlight|panel|ddc-i2c-bus|hdmi|i2s-controller|"
    r"audio-codec|simple-audio-card,codec|rockchip,cpu|rockchip,codec|dsp|"
    r"rockchip,(resetgroup-node|srv|taskqueue-node|rcb-.*)|iommu|power-supply)$")
GPIO_RE = re.compile(r"^(.*-gpios?|gpios?)$")


def walk(node, path="/"):
    yield path, node
    for n in node.nodes:
        yield from walk(n, (path.rstrip("/") + "/" + n.name))


def main(f):
    d = fdt.parse_dtb(open(f, "rb").read())
    ph = {}                                   # phandle -> path
    nodes = {}
    for path, n in walk(d.root):
        nodes[path] = n
        for p in n.props:
            if p.name in ("phandle", "linux,phandle") and hasattr(p, "data") and p.data:
                ph[p.data[0]] = path

    def cells(path, cname, default=0):
        n = nodes.get(path)
        if n is None or cname is None:
            return default
        p = n.get_property(cname)
        return p.data[0] if p is not None else default

    out = []
    for path, n in sorted(walk(d.root), key=lambda x: x[0]):
        if path.startswith("/__symbols__") or path.startswith("/__fixups__") or \
           path.startswith("/__local_fixups__"):
            continue
        out.append(f"{path} {{")
        for p in sorted(n.props, key=lambda x: x.name):
            if p.name in ("phandle", "linux,phandle"):
                continue
            val = render(p, ph, cells)
            out.append(f"  {p.name} = {val}")
        out.append("}")
    print("\n".join(out))


def render(p, ph, cells):
    t = type(p).__name__
    if t == "Property":
        return "<true>"
    if t == "PropStrings":
        return ", ".join(f'"{s}"' for s in p.data)
    if t == "PropBytes":
        return "[" + " ".join(f"{b:02x}" for b in p.data) + "]"
    if t != "PropWords":
        return str(p.data)
    w = list(p.data)
    name = p.name
    try:
        if name == "msi-map" and len(w) % 4 == 0 and all(w[i] in ph for i in range(1, len(w), 4)):
            return ", ".join(f"<{w[i]:#x} &{ph[w[i+1]]} {w[i+2]:#x} {w[i+3]:#x}>" for i in range(0, len(w), 4))
        if name == "interrupt-map":   # PCIe: 3 cells addr + 1 cell int + phandle + #interrupt-cells(pai)
            r, i = [], 0
            while i + 4 < len(w) and w[i + 4] in ph:
                tgt = ph[w[i + 4]]
                nc = cells(tgt, "#interrupt-cells", 1)
                r.append("<" + " ".join(f"{x:#x}" for x in w[i:i + 4]) + f" &{tgt} " +
                         " ".join(f"{x:#x}" for x in w[i + 5:i + 5 + nc]) + ">")
                i += 5 + nc
            if i == len(w):
                return ", ".join(r)
        if name in LIST_PROPS or GPIO_RE.match(name):
            cname = LIST_PROPS.get(name, "#gpio-cells")
            r, i = [], 0
            while i < len(w):
                tgt = ph.get(w[i])
                if tgt is None:
                    return words(w)
                nc = cells(tgt, cname, 0 if cname is None else 1)
                r.append("<&" + tgt + "".join(f" {x:#x}" for x in w[i + 1:i + 1 + nc]) + ">")
                i += 1 + nc
            return ", ".join(r)
        if SINGLE_RE.match(name) and all(x in ph for x in w):
            return ", ".join(f"<&{ph[x]}>" for x in w)
    except Exception:
        pass
    return words(w)


def words(w):
    return "<" + " ".join(f"{x:#x}" for x in w) + ">"


if __name__ == "__main__":
    main(sys.argv[1])
