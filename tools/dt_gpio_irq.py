#!/usr/bin/env python3
"""Confere as teclas do gpio-keys de um DTB: pino, tipo da interrupção e LEDs no mesmo pino.

Problemas apontados:
  - tecla por interrupção sem tipo (IRQ_TYPE_NONE): o GPIO da Rockchip fica no padrão do
    hardware, nível baixo, e dispara sem parar se o pino estiver em 0;
  - tecla no mesmo pino de uma saída do gpio-leds;
  - com --factory, tecla (por linux,code) em pino diferente do DT de fábrica.

Uso: dt_gpio_irq.py check porte.dtb [--factory fabrica.dtb]
Sai com 1 se houver problema. Lê o DTB direto (formato FDT), sem dependências.
"""
import argparse
import struct
import sys
from collections import namedtuple

FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE, FDT_END_NODE, FDT_PROP, FDT_NOP, FDT_END = 1, 2, 3, 4, 9

Key = namedtuple("Key", "path code controller pin kind flags")


def parse(blob):
    """Devolve {caminho: {propriedade: bytes}} de um DTB."""
    magic, _, off_struct, off_strings = struct.unpack_from(">4I", blob, 0)
    if magic != FDT_MAGIC:
        raise ValueError("não é um DTB")
    tree, stack, pos = {}, [], off_struct
    while True:
        (token,) = struct.unpack_from(">I", blob, pos)
        pos += 4
        if token == FDT_BEGIN_NODE:
            end = blob.index(b"\0", pos)
            name = blob[pos:end].decode()
            pos = (end + 4) & ~3
            stack.append(name)
            tree["/" + "/".join(n for n in stack if n)] = {}
        elif token == FDT_END_NODE:
            stack.pop()
        elif token == FDT_PROP:
            size, name_off = struct.unpack_from(">2I", blob, pos)
            name = blob[off_strings + name_off:blob.index(b"\0", off_strings + name_off)].decode()
            tree["/" + "/".join(n for n in stack if n)][name] = blob[pos + 8:pos + 8 + size]
            pos = (pos + 8 + size + 3) & ~3
        elif token == FDT_END:
            return tree
        elif token != FDT_NOP:
            raise ValueError(f"token FDT inválido {token:#x}")


def load(path):
    with open(path, "rb") as f:
        return parse(f.read())


def cells(value):
    return list(struct.unpack(f">{len(value) // 4}I", value))


def phandles(tree):
    return {cells(props["phandle"])[0]: path for path, props in tree.items() if "phandle" in props}


def children_of(tree, compatible):
    parents = [p for p, props in tree.items() if compatible.encode() in props.get("compatible", b"").split(b"\0")]
    return [(path, tree[path]) for parent in parents for path in tree
            if path.rsplit("/", 1)[0] == parent and path != parent]


def gpio_ref(tree, value):
    phandle, pin, flags = cells(value)[:3]
    return phandles(tree)[phandle], pin, flags


def ancestors(path):
    parts = path.strip("/").split("/")
    return ["/" + "/".join(parts[:i]) for i in range(len(parts), -1, -1)]


def interrupt_parent(tree, path):
    """interrupt-parent do nó ou do ancestral mais próximo que o declara."""
    owner = next((p for p in ancestors(path) if "interrupt-parent" in tree.get(p, {})), None)
    return phandles(tree)[cells(tree[owner]["interrupt-parent"])[0]] if owner else None


def read_key(tree, path, props):
    code = cells(props["linux,code"])[0] if "linux,code" in props else None
    if "gpios" in props:
        controller, pin, flags = gpio_ref(tree, props["gpios"])
        return Key(path, code, controller, pin, "gpio", flags)
    pin, flags = cells(props["interrupts"])[:2]
    return Key(path, code, interrupt_parent(tree, path), pin, "irq", flags)


def keys(tree):
    return [read_key(tree, path, props) for path, props in children_of(tree, "gpio-keys")
            if "gpios" in props or "interrupts" in props]


def led_outputs(tree):
    return {gpio_ref(tree, props["gpios"])[:2] for _, props in children_of(tree, "gpio-leds") if "gpios" in props}


def controller_id(tree, path):
    """Identidade do controlador entre DTs diferentes: o endereço do reg, ou o caminho."""
    reg = tree.get(path, {}).get("reg")
    return f"reg {cells(reg)[:2]}" if reg else path


def key_problems(tree, key, leds):
    if key.kind == "irq" and key.flags == 0:
        yield f"{key.path}: interrupção sem tipo (IRQ_TYPE_NONE) no pino {key.pin} de {key.controller}"
    if (key.controller, key.pin) in leds:
        yield f"{key.path}: pino {key.pin} de {key.controller} também é saída de LED (gpio-leds)"


def factory_problems(tree, factory, port_keys):
    by_code = {k.code: k for k in keys(factory)}
    for key in port_keys:
        ref = by_code.get(key.code)
        if ref is None:
            continue
        here = (controller_id(tree, key.controller), key.pin)
        there = (controller_id(factory, ref.controller), ref.pin)
        if here != there:
            yield f"{key.path}: pino {key.pin} de {key.controller}, na fábrica é {ref.pin} de {ref.controller}"


def problems(tree, factory=None):
    port_keys, leds = keys(tree), led_outputs(tree)
    found = [p for key in port_keys for p in key_problems(tree, key, leds)]
    return found + (list(factory_problems(tree, factory, port_keys)) if factory else [])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["check"])
    parser.add_argument("dtb")
    parser.add_argument("--factory")
    args = parser.parse_args(argv)
    found = problems(load(args.dtb), load(args.factory) if args.factory else None)
    for line in found:
        print(f"FALHOU: {line}")
    print(f"gpio-keys: {len(found)} problema(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
