#!/usr/bin/env python3
"""Desmonta e monta boot.img Android header v2 (formato usado pela Rockchip no HY300).

Layout v2: header de 1660 bytes numa página, depois kernel, ramdisk, second (resource.img
da Rockchip), recovery_dtbo e dtb, cada um alinhado à página. O campo `id` é o SHA-1 das
seções seguidas do tamanho de cada uma (o U-Boot da Rockchip confere).

Uso:
  mkboot.py unpack boot.img outdir/
  mkboot.py build  --like boot.img -o out.img [--kernel Image] [--ramdisk r] [--second s]
                   [--dtb d] [--append-cmdline "x=1"] [--pad-to-like]
"""
import argparse
import dataclasses
import hashlib
import json
import os
import struct
import sys

MAGIC = b"ANDROID!"
HEADER_VERSION = 2
HEADER_SIZE = 1660
SECTIONS = ("kernel", "ramdisk", "second", "recovery_dtbo", "dtb")
FIELD_LIMITS = {"name": 16, "cmdline": 512, "extra_cmdline": 1024}


@dataclasses.dataclass
class BootImage:
    kernel: bytes
    ramdisk: bytes
    second: bytes
    recovery_dtbo: bytes
    dtb: bytes
    kernel_addr: int
    ramdisk_addr: int
    second_addr: int
    tags_addr: int
    dtb_addr: int
    page_size: int
    os_version: int
    name: bytes
    cmdline: bytes
    extra_cmdline: bytes


def align(n, page):
    return (n + page - 1) // page * page


def compute_id(img):
    h = hashlib.sha1()
    for section in SECTIONS:
        part = getattr(img, section)
        h.update(part)
        h.update(struct.pack("<I", len(part)))
    return h.digest()


def build_section_offsets(img):
    offsets, off = {}, img.page_size
    for section in SECTIONS:
        offsets[section] = off
        off += align(len(getattr(img, section)), img.page_size)
    return offsets, off


def require_fields_fit(img):
    for field, limit in FIELD_LIMITS.items():
        if len(getattr(img, field)) >= limit:
            raise ValueError(f"{field} tem {len(getattr(img, field))} bytes; o limite é {limit - 1}")


def build_header(img, offsets):
    rdtbo_offset = offsets["recovery_dtbo"] if img.recovery_dtbo else 0
    return b"".join((
        MAGIC,
        struct.pack("<9I", len(img.kernel), img.kernel_addr, len(img.ramdisk), img.ramdisk_addr,
                    len(img.second), img.second_addr, img.tags_addr, img.page_size, HEADER_VERSION),
        struct.pack("<I", img.os_version),
        img.name.ljust(16, b"\0"),
        img.cmdline.ljust(512, b"\0"),
        compute_id(img).ljust(32, b"\0"),
        img.extra_cmdline.ljust(1024, b"\0"),
        struct.pack("<IQI", len(img.recovery_dtbo), rdtbo_offset, HEADER_SIZE),
        struct.pack("<IQ", len(img.dtb), img.dtb_addr),
    ))


def build(img, pad_to=None):
    require_fields_fit(img)
    offsets, end = build_section_offsets(img)
    out = bytearray(end)
    out[:HEADER_SIZE] = build_header(img, offsets)
    for section in SECTIONS:
        part = getattr(img, section)
        out[offsets[section]:offsets[section] + len(part)] = part
    if pad_to is None:
        return bytes(out)
    if pad_to < len(out):
        raise ValueError(f"imagem tem {len(out)} bytes, não cabe em {pad_to}")
    return bytes(out.ljust(pad_to, b"\0"))


def read_cstr(data, off, size):
    return data[off:off + size].split(b"\0", 1)[0]


def unpack(data):
    if data[:8] != MAGIC:
        raise ValueError("não é boot.img Android")
    ks, ka, rs, ra, ss, sa, ta, ps, hv = struct.unpack_from("<9I", data, 8)
    if hv != HEADER_VERSION:
        raise ValueError(f"header v{hv}; só o v2 é suportado")
    rdtbo_size, _, _ = struct.unpack_from("<IQI", data, 1632)
    dtb_size, dtb_addr = struct.unpack_from("<IQ", data, 1648)
    sizes = dict(zip(SECTIONS, (ks, rs, ss, rdtbo_size, dtb_size)))
    parts, off = {}, ps
    for section in SECTIONS:
        parts[section] = data[off:off + sizes[section]]
        off += align(sizes[section], ps)
    return BootImage(
        **parts, kernel_addr=ka, ramdisk_addr=ra, second_addr=sa, tags_addr=ta, dtb_addr=dtb_addr,
        page_size=ps, os_version=struct.unpack_from("<I", data, 44)[0],
        name=read_cstr(data, 48, 16), cmdline=read_cstr(data, 64, 512),
        extra_cmdline=read_cstr(data, 608, 1024),
    )


def replace(img, **sections):
    return dataclasses.replace(img, **sections)


def append_cmdline(img, extra):
    return dataclasses.replace(img, cmdline=b" ".join(filter(None, (img.cmdline, extra))))


def read_file(path):
    with open(path, "rb") as f:
        return f.read()


def write_file(path, data):
    with open(path, "wb") as f:
        f.write(data)


def run_unpack(args):
    img = unpack(read_file(args.image))
    os.makedirs(args.outdir, exist_ok=True)
    for section in SECTIONS:
        write_file(os.path.join(args.outdir, section), getattr(img, section))
    meta = {k: v.decode() if isinstance(v, bytes) else v
            for k, v in dataclasses.asdict(img).items() if k not in SECTIONS}
    write_file(os.path.join(args.outdir, "header.json"), json.dumps(meta, indent=2).encode())
    print(f"ok {args.outdir}: " + " ".join(f"{s}={len(getattr(img, s))}" for s in SECTIONS))


def run_build(args):
    like = read_file(args.like)
    img = unpack(like)
    new_sections = {s: read_file(getattr(args, s)) for s in SECTIONS if getattr(args, s, None)}
    img = replace(img, **new_sections)
    if args.append_cmdline:
        img = append_cmdline(img, args.append_cmdline.encode())
    data = build(img, pad_to=len(like) if args.pad_to_like else None)
    write_file(args.output, data)
    print(f"ok {args.output}: {len(data)} bytes, id {compute_id(img).hex()}")


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("unpack")
    u.add_argument("image")
    u.add_argument("outdir")
    u.set_defaults(run=run_unpack)
    b = sub.add_parser("build")
    b.add_argument("--like", required=True, help="imagem de referência (endereços, cmdline, seções)")
    b.add_argument("-o", "--output", required=True)
    for section in SECTIONS:
        b.add_argument(f"--{section.replace('_', '-')}", dest=section)
    b.add_argument("--append-cmdline")
    b.add_argument("--pad-to-like", action="store_true", help="completa com zeros até o tamanho da referência")
    b.set_defaults(run=run_build)
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    args.run(args)
