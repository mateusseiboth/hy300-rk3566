#!/usr/bin/env python3
"""Lista as diferenças nó a nó entre dois DTs normalizados por dtnorm.py.

Saída, uma por linha:
  - /caminho            nó só em A (fábrica)
  + /caminho            nó só em B (porte); "(disabled)" quando status != okay
  ~ /caminho prop: a -> b   propriedade diferente ou ausente de um lado

Uso: dtdiff.py fabrica.norm porte.norm [--skip /pinctrl,/__symbols__]
"""
import argparse
import sys

ABSENT = "(ausente)"
ENABLED = ('"okay"', '"ok"')


def parse(text):
    nodes, current = {}, None
    for line in text.splitlines():
        if line.startswith("/") and line.endswith(" {"):
            current = nodes.setdefault(line[:-2], {})
            continue
        if line == "}":
            current = None
            continue
        if current is not None and " = " in line:
            name, value = line.strip().split(" = ", 1)
            current[name] = value
    return nodes


def is_skipped(path, skip):
    return any(path == s or path.startswith(s.rstrip("/") + "/") for s in skip)


def describe_node(sign, path, props):
    disabled = props.get("status", '"okay"') not in ENABLED
    return f"{sign} {path}" + (" (disabled)" if disabled else "")


def diff_props(path, a, b):
    for name in sorted(set(a) | set(b)):
        va, vb = a.get(name, ABSENT), b.get(name, ABSENT)
        if va != vb:
            yield f"~ {path} {name}: {va} -> {vb}"


def diff(a, b, skip=()):
    lines = []
    for path in sorted(set(a) - set(b)):
        lines += [] if is_skipped(path, skip) else [describe_node("-", path, a[path])]
    for path in sorted(set(b) - set(a)):
        lines += [] if is_skipped(path, skip) else [describe_node("+", path, b[path])]
    for path in sorted(set(a) & set(b)):
        lines += [] if is_skipped(path, skip) else list(diff_props(path, a[path], b[path]))
    return lines


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--skip", default="", help="prefixos de caminho ignorados, separados por vírgula")
    args = p.parse_args(argv)
    with open(args.a) as fa, open(args.b) as fb:
        lines = diff(parse(fa.read()), parse(fb.read()), tuple(filter(None, args.skip.split(","))))
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
