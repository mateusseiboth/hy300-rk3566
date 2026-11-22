#!/usr/bin/env python3
"""Confere um .config do kernel contra os requisitos do Android (kernel/configs).

Lê de um diretório de requisitos (ex.: kernel/configs/u/android-6.1 do LineageOS/AOSP):
  - android-base.config: fragmento com os valores obrigatórios;
  - android-base-conditional.xml (opcional): grupos que só valem quando as condições
    batem com o próprio .config (ex.: só para CONFIG_ARM64=y), e o minlts do kernel.

Regras, as mesmas do libvintf: `# CONFIG_X is not set` e a ausência valem "n";
tristate é comparado ao pé da letra ("m" não satisfaz "y").

Saída: uma linha por diferença ("CONFIG_X: exige y, tem m") e o total.
Código de saída 1 se houver diferença ou se o kernel estiver abaixo do minlts.

Uso: kconfig_check.py <dir-de-requisitos> <.config> [--kernel-version 6.1.172]
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import namedtuple

Mismatch = namedtuple("Mismatch", "key required actual")

NOT_SET = re.compile(r"^# (CONFIG_\w+) is not set$")
ASSIGNMENT = re.compile(r"^(CONFIG_\w+)=(.*)$")
MINLTS = re.compile(r'<kernel\s+minlts="([^"]+)"')
KERNEL_TAG = re.compile(r"<kernel\b[^>]*/>")
BASE_FRAGMENT = "android-base.config"
CONDITIONAL_XML = "android-base-conditional.xml"


def parse_fragment(text):
    values = {}
    for line in text.splitlines():
        line = line.strip()
        not_set = NOT_SET.match(line)
        if not_set:
            values[not_set.group(1)] = "n"
            continue
        assignment = ASSIGNMENT.match(line)
        if assignment:
            values[assignment.group(1)] = assignment.group(2)
    return values


def read_config_element(element):
    return element.findtext("key").strip(), element.findtext("value").strip()


def parse_group(group):
    conditions = dict(read_config_element(c) for c in group.findall("conditions/config"))
    required = dict(read_config_element(c) for c in group.findall("config"))
    return conditions, required


def parse_conditional_xml(text):
    root = ET.fromstring("<root>" + KERNEL_TAG.sub("", text) + "</root>")
    return [parse_group(group) for group in root.findall("group")]


def parse_minlts(text):
    found = MINLTS.search(text)
    return found.group(1) if found else None


def normalize_value(value):
    return value if value else "n"


def is_condition_met(conditions, config):
    return all(normalize_value(config.get(key, "n")) == value for key, value in conditions.items())


def collect_requirements(base, groups, config):
    required = dict(base)
    for conditions, values in groups:
        if is_condition_met(conditions, config):
            required.update(values)
    return required


def find_mismatches(required, config):
    return [
        Mismatch(key, value, config.get(key, "n"))
        for key, value in sorted(required.items())
        if config.get(key, "n") != value
    ]


def parse_version(text):
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def is_version_at_least(version, minimum):
    return parse_version(version) >= parse_version(minimum)


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def read_optional(path):
    return read_text(path) if os.path.exists(path) else ""


def format_mismatch(mismatch):
    return f"{mismatch.key}: exige {mismatch.required}, tem {mismatch.actual}"


def check_version(minlts, version):
    if not (minlts and version):
        return True, None
    ok = is_version_at_least(version, minlts)
    relation = ">=" if ok else "<"
    return ok, f"kernel {version} {relation} {minlts} (minlts)"


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("requirements_dir")
    parser.add_argument("dotconfig")
    parser.add_argument("--kernel-version")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    config = parse_fragment(read_text(args.dotconfig))
    base = parse_fragment(read_text(os.path.join(args.requirements_dir, BASE_FRAGMENT)))
    conditional = read_optional(os.path.join(args.requirements_dir, CONDITIONAL_XML))
    groups = parse_conditional_xml(conditional) if conditional else []
    mismatches = find_mismatches(collect_requirements(base, groups, config), config)
    version_ok, version_line = check_version(parse_minlts(conditional), args.kernel_version)
    for mismatch in mismatches:
        print(format_mismatch(mismatch))
    if version_line:
        print(version_line)
    print(f"{len(mismatches)} diferenças")
    return 0 if version_ok and not mismatches else 1


if __name__ == "__main__":
    sys.exit(main())
