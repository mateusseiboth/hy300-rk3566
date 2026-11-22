#!/usr/bin/env python3
"""Gera logo.bmp (1280x720, 24 bits, top-down) para o U-Boot Rockchip e injeta no boot.img.

Uso:
  make_splash.py imagem.png logo.bmp [--scale 0.85] [--bg 000000]
  make_splash.py inject boot.img logo.bmp out_boot.img
"""
import sys, struct, hashlib
from PIL import Image

W, H = 1280, 720

def make_bmp(src, out, scale=0.85, bg="000000"):
    im = Image.open(src).convert("RGBA")
    h = int(H * scale); w = int(im.width * h / im.height)
    im = im.resize((w, h), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), "#" + bg)
    canvas.alpha_composite(im, ((W - w) // 2, (H - h) // 2))
    rgb = canvas.convert("RGB")
    px = rgb.tobytes("raw", "BGR")              # 1280*3 = 3840, já múltiplo de 4
    hdr = b"BM" + struct.pack("<IHHI", 54 + len(px), 0, 0, 54)
    dib = struct.pack("<IiiHHIIiiII", 40, W, -H, 1, 24, 0, len(px), 2834, 2834, 0, 0)
    open(out, "wb").write(hdr + dib + px)
    print(f"ok {out} ({54 + len(px)} bytes)")

def align(n, p): return (n + p - 1) // p * p

def boot_parts(b):
    ks, ka, rs, ra, ss, sa, ta, ps, hv = struct.unpack_from("<9I", b, 8)
    off = ps; parts = []
    for size in (ks, rs, ss):
        parts.append((off, size)); off += align(size, ps)
    if hv >= 1:
        rdsz, = struct.unpack_from("<I", b, 1632)
        parts.append((off, rdsz)); off += align(rdsz, ps)
    if hv >= 2:
        dtbsz, = struct.unpack_from("<I", b, 1648)
        parts.append((off, dtbsz))
    return ps, hv, parts

def calc_id(b):
    ps, hv, parts = boot_parts(b)
    h = hashlib.sha1()
    for off, size in parts:
        h.update(b[off:off + size]); h.update(struct.pack("<I", size))
    return h.digest()

def inject(bootf, bmpf, outf):
    import os; sys.path.insert(0, os.path.dirname(__file__))
    from rk_resource import parse
    b = bytearray(open(bootf, "rb").read()); bmp = open(bmpf, "rb").read()
    ps, hv, parts = boot_parts(b)
    sec_off, sec_size = parts[2]
    ents = {n: (o, s) for n, o, s, _ in parse(bytes(b[sec_off:sec_off + sec_size]))}
    lo, ls = ents["logo.bmp"]
    if len(bmp) < ls: bmp += b"\0" * (ls - len(bmp))   # original tem padding no fim
    assert len(bmp) == ls, f"tamanho diferente: {len(bmp)} != {ls} (substituição in-place exige igual)"
    orig_id = bytes(b[576:576 + 20])
    assert calc_id(b) == orig_id, "SHA1 do header original não confere — formato inesperado, abortando"
    b[sec_off + lo: sec_off + lo + ls] = bmp
    b[576:576 + 32] = calc_id(b).ljust(32, b"\0")
    open(outf, "wb").write(b)
    print(f"ok {outf}: logo @ {sec_off + lo:#x}, header v{hv}, id recalculado")

if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "inject": inject(*a[1:4])
    elif len(a) >= 2:
        kw = dict(zip(a[2::2], a[3::2]))
        make_bmp(a[0], a[1], float(kw.get("--scale", 0.85)), kw.get("--bg", "000000"))
    else: print(__doc__)
