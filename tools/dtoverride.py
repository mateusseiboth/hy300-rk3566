#!/usr/bin/env python3
"""Gera um .dtsi de sobrescritas que transforma o DT de BASE no DT ALVO.

Entrada: dois arquivos normalizados por dtnorm.py (base.norm e alvo.norm).
Saída (stdout): blocos `&{/caminho} { ... };`, `/delete-node/` e `/delete-property/`
prontos para incluir depois do .dts da placa de referência.

Valores que parecem phandle mas não foram resolvidos pelo dtnorm saem com o comentário
`REVISAR` para conferência manual.

Uso: dtoverride.py base.norm alvo.norm > overrides.dtsi
"""
import re
import sys


def load(f):
    nodes, cur = {}, None
    for line in open(f):
        line = line.rstrip("\n")
        if line.endswith(" {") and line.startswith("/"):
            cur = line[:-2]
            nodes[cur] = {}
        elif line == "}":
            cur = None
        elif cur is not None and line.startswith("  "):
            k, _, v = line[2:].partition(" = ")
            nodes[cur][k] = v
    return nodes


REF = re.compile(r"&(/[^ >]*)")


def dts_value(v):
    if v == "<true>":
        return None
    # &/a/b -> &{/a/b} (vale também dentro de listas mistas)
    return REF.sub(lambda m: "&{" + m.group(1) + "}", v)


def parent(p):
    return p.rsplit("/", 1)[0] or "/"


def main(basef, tgtf):
    base, tgt = load(basef), load(tgtf)
    out = ["/* Gerado por tools/dtoverride.py — sobrescritas sobre a placa de referência */", ""]

    # 1) nós a remover (só o mais alto de cada subárvore)
    gone = sorted(set(base) - set(tgt))
    top = [p for p in gone if parent(p) not in gone and p != "/"]
    for p in top:
        pa, name = parent(p), p.rsplit("/", 1)[1]
        out.append(f"&{{{pa}}} {{ /delete-node/ {name}; }};")
    out.append("")

    # 2) nós novos ou alterados (em ordem de caminho: pais antes dos filhos)
    for p in sorted(tgt):
        tp = tgt[p]
        bp = base.get(p)
        lines = []
        if bp is not None:
            for k in sorted(set(bp) - set(tp)):
                lines.append(f"\t/delete-property/ {k};")
        for k in sorted(tp):
            if bp is not None and bp.get(k) == tp[k]:
                continue
            v = dts_value(tp[k])
            note = ""
            if v and re.fullmatch(r"<0x[0-9a-f]{1,3}>", v) and not re.search(
                    r"(cells|reg|freq|size|width|height|id|num|max|min|level|count|index|"
                    r"mode|rate|delay|ms|us|ns|latency|threshold|channel|bits|offset|"
                    r"temperature|hysteresis|polling|voltage|microvolt|current)", k):
                note = "  /* REVISAR: pode ser phandle */"
            lines.append(f"\t{k};" if v is None else f"\t{k} = {v};{note}")
        if bp is None:
            # nó novo: cria a partir do pai (os filhos novos vêm depois, no seu próprio bloco)
            pa, name = parent(p), p.rsplit("/", 1)[1]
            if p == "/":
                continue
            out.append(f"&{{{pa}}} {{\n\t{name} {{\n" +
                       "\n".join("\t" + l for l in lines) + "\n\t};\n};")
        elif lines:
            out.append(f"&{{{p}}} {{\n" + "\n".join(lines) + "\n};")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
