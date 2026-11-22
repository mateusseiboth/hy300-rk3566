#!/usr/bin/env python3
"""Extrai/lista/reempacota o resource.img (RSCE) da Rockchip e o 'second' de um boot.img v2.

Uso:
  rk_resource.py boot-extract boot.img out_resource.img
  rk_resource.py list resource.img
  rk_resource.py unpack resource.img outdir/
  rk_resource.py replace resource.img nome_no_resource arquivo_novo out_resource.img
  rk_resource.py boot-replace boot.img novo_resource.img out_boot.img
"""
import struct, sys, os

def boot_hdr(b):
    assert b[:8] == b"ANDROID!", "não é boot.img Android"
    (ks, ka, rs, ra, ss, sa, ta, ps, hv) = struct.unpack_from("<9I", b, 8)
    return dict(ks=ks, rs=rs, ss=ss, ps=ps, hv=hv)

def align(n, p): return (n + p - 1) // p * p

def second_off(h):
    p = h["ps"]
    return p + align(h["ks"], p) + align(h["rs"], p)

def boot_extract(bootf, outf):
    b = open(bootf, "rb").read(); h = boot_hdr(b)
    o = second_off(h)
    open(outf, "wb").write(b[o:o + h["ss"]])
    print(f"header v{h['hv']} page={h['ps']} kernel={h['ks']} ramdisk={h['rs']} second={h['ss']} @ {o:#x}")

BLK = 512
def parse(r):
    assert r[:4] == b"RSCE", "não é RSCE"
    # magic[4] ptn_ver u16 tbl_ver u16 hdr_blks u8 tbl_off u8 ent_blks u8 pad u8 n u32
    hdr_blks, tbl_off, ent_blks = r[8], r[9], r[10]
    n = struct.unpack_from("<I", r, 12)[0]
    ents = []
    for i in range(n):
        e = (tbl_off + i * ent_blks) * BLK
        assert r[e:e+4] == b"ENTR"
        name = r[e+4:e+4+256].split(b"\0")[0].decode()
        off_blk, size = struct.unpack_from("<II", r, e + 4 + 256)
        ents.append((name, off_blk * BLK, size, e))
    return ents

def cmd_list(f):
    r = open(f, "rb").read()
    for name, off, size, _ in parse(r): print(f"{off:#10x} {size:>9}  {name}")

def cmd_unpack(f, d):
    r = open(f, "rb").read(); os.makedirs(d, exist_ok=True)
    for name, off, size, _ in parse(r):
        p = os.path.join(d, name); os.makedirs(os.path.dirname(p) or d, exist_ok=True)
        open(p, "wb").write(r[off:off+size]); print("->", p)

def cmd_replace(f, target, newf, outf):
    r = bytearray(open(f, "rb").read()); new = open(newf, "rb").read()
    ents = parse(r)
    # reconstrói: cabeçalho+tabela intactos, dados realocados em sequência
    data_start = min(off for _, off, _, _ in ents)
    out = bytearray(r[:data_start]); found = False
    for name, off, size, eoff in ents:
        blob = new if name == target else bytes(r[off:off+size])
        found |= name == target
        cur = len(out)
        struct.pack_into("<II", out, eoff + 4 + 256, cur // BLK, len(blob))
        out += blob + b"\0" * (align(len(blob), BLK) - len(blob))
    assert found, f"{target} não encontrado"
    open(outf, "wb").write(out); print(f"ok {outf} ({len(out)} bytes)")

def boot_replace(bootf, resf, outf):
    b = bytearray(open(bootf, "rb").read()); h = boot_hdr(b); res = open(resf, "rb").read()
    o = second_off(h); p = h["ps"]
    tail = b[o + align(h["ss"], p):]          # recovery_dtbo / dtb (header v2)
    struct.pack_into("<I", b, 8 + 16, len(res))  # second_size
    out = b[:o] + res + b"\0" * (align(len(res), p) - len(res)) + tail
    # boot header v2: recovery_dtbo_offset aponta para o fim — recalcula se existir
    open(outf, "wb").write(out); print(f"ok {outf} ({len(out)} bytes, second={len(res)})")

if __name__ == "__main__":
    c, *a = sys.argv[1:] or ["-h"]
    {"boot-extract": boot_extract, "list": cmd_list, "unpack": cmd_unpack,
     "replace": cmd_replace, "boot-replace": boot_replace}.get(c, lambda *_: print(__doc__))(*a)
