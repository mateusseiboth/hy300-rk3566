#!/usr/bin/env python3
"""Prebuilts do kernel para a árvore do LineageOS (device/hy300/rk3566) e conferência do
boot.img que o build do Lineage gera.

  install:     Image (com o DT do HY300 embutido) -> prebuilt/Image.gz (gzip -9 sem data,
               reproduzível), DTB -> prebuilt/dtb/, resource.img DE FÁBRICA (seção second do
               boot.img do aparelho) -> prebuilt/resource.img, e prebuilt/VERSION com a origem
               do kernel e os sha256.
  verify-boot: confere o boot.img do Lineage contra o de fábrica: header v2, endereços e
               página iguais, ID que o U-Boot confere, resource de fábrica, kernel igual ao
               prebuilt, ramdisk presente, boot_devices na cmdline e tamanho da partição.

Uso:
  lineage_prebuilt.py install --image Image --dtb rk3566-hy300.dtb --factory-boot boot.img \\
                      --out <árvore>/prebuilt --kernel-ref "hy300-ack-6.1 <commit>" \\
                      [--modules-dir <dir com .ko>]
  lineage_prebuilt.py verify-boot boot.img --factory-boot boot.img --kernel-gz Image.gz \\
                      [--partition-size 41943040]
  lineage_prebuilt.py variant boot.img -o boot-panfrost.img --set androidboot.hy300.gpu=panfrost
                      (troca o valor de uma chave da cmdline e refaz o ID; mesmo tamanho)
"""
import argparse
import gzip
import hashlib
import io
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkboot  # noqa: E402

BUILTIN_DT_MARK = b"HY300 Projector"
UBOOT_EMMC_COMPATIBLE = b"snps,dwcmshc-sdhci"
RESOURCE_MAGIC = b"RSCE"
DTB_NAME = "rk3566-hy300.dtb"
BOOT_PARTITION_SIZE = 41943040
SAME_AS_FACTORY = ("kernel_addr", "ramdisk_addr", "second_addr", "tags_addr", "page_size")
REQUIRED_CMDLINE = (b"androidboot.boot_devices=", b"androidboot.hardware=rk3566")


def compress_kernel(image):
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=9, mtime=0, filename="") as handle:
        handle.write(image)
    return out.getvalue()


def require_builtin_dtb(image):
    if BUILTIN_DT_MARK not in image:
        raise ValueError("Image sem o DT embutido do HY300 (CONFIG_HY300_BUILTIN_DTB)")


def read_factory_resource(boot):
    resource = mkboot.unpack(boot).second
    if not resource.startswith(RESOURCE_MAGIC):
        raise ValueError("a seção second do boot.img não é um resource.img (RSCE)")
    if UBOOT_EMMC_COMPATIBLE not in resource:
        raise ValueError("o rk-kernel.dtb do resource não tem o eMMC snps,dwcmshc-sdhci do U-Boot")
    return resource


def read_file(path):
    with open(path, "rb") as handle:
        return handle.read()


def write_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def build_version(kernel_ref, files):
    lines = [f"kernel: {kernel_ref}"]
    lines += [f"{hashlib.sha256(data).hexdigest()}  {name}" for name, data in sorted(files.items())]
    return ("\n".join(lines) + "\n").encode()


def collect_modules(modules_dir):
    if not modules_dir:
        return {}
    return {f"modules/{name}": read_file(os.path.join(modules_dir, name))
            for name in sorted(os.listdir(modules_dir)) if name.endswith(".ko")}


def install_prebuilts(image, dtb, factory_boot, outdir, kernel_ref, modules_dir=None):
    kernel = read_file(image)
    require_builtin_dtb(kernel)
    files = {
        "Image.gz": compress_kernel(kernel),
        f"dtb/{DTB_NAME}": read_file(dtb),
        "resource.img": read_factory_resource(read_file(factory_boot)),
        **collect_modules(modules_dir),
    }
    shutil.rmtree(os.path.join(outdir, "modules"), ignore_errors=True)
    for name, data in files.items():
        write_file(os.path.join(outdir, name), data)
    write_file(os.path.join(outdir, "VERSION"), build_version(kernel_ref, files))
    return files


def find_header_problems(img, factory):
    problems = [f"{field}: {getattr(img, field):#x}, fábrica {getattr(factory, field):#x}"
                for field in SAME_AS_FACTORY if getattr(img, field) != getattr(factory, field)]
    problems += [f"cmdline sem {flag.decode()}" for flag in REQUIRED_CMDLINE if flag not in img.cmdline]
    return problems


def find_section_problems(img, factory, kernel_gz):
    checks = (
        (img.kernel != kernel_gz, "kernel diferente do prebuilt Image.gz"),
        (img.second != factory.second, "second diferente do resource de fábrica"),
        (not img.ramdisk, "ramdisk vazio"),
        (not img.dtb, "seção dtb vazia (header v2 exige)"),
    )
    return [message for failed, message in checks if failed]


def find_boot_problems(boot, factory_boot, kernel_gz, partition_size=BOOT_PARTITION_SIZE):
    if boot[:8] != mkboot.MAGIC or int.from_bytes(boot[40:44], "little") != mkboot.HEADER_VERSION:
        return ["não é boot.img header v2"]
    img, factory = mkboot.unpack(boot), mkboot.unpack(factory_boot)
    problems = find_header_problems(img, factory) + find_section_problems(img, factory, kernel_gz)
    if boot[576:596] != mkboot.compute_id(img):
        problems.append("id do header não é o SHA-1 que o U-Boot confere")
    if len(boot) > partition_size:
        problems.append(f"{len(boot)} bytes não cabem na partição de {partition_size}")
    return problems


def replace_cmdline_value(boot, key, value):
    img = mkboot.unpack(boot)
    prefix = key.encode() + b"="
    tokens = img.cmdline.split(b" ")
    if not any(t.startswith(prefix) for t in tokens):
        raise ValueError(f"{key} não está na cmdline")
    cmdline = b" ".join(prefix + value.encode() if t.startswith(prefix) else t for t in tokens)
    return mkboot.build(mkboot.replace(img, cmdline=cmdline), pad_to=len(boot))


def run_variant(args):
    key, _, value = args.set.partition("=")
    data = replace_cmdline_value(read_file(args.boot), key, value)
    write_file(args.output, data)
    print(f"ok {args.output}: {args.set}")
    return 0


def run_install(args):
    files = install_prebuilts(args.image, args.dtb, args.factory_boot, args.out, args.kernel_ref,
                              args.modules_dir)
    for name, data in sorted(files.items()):
        print(f"ok {name}: {len(data)} bytes")
    return 0


def run_verify_boot(args):
    problems = find_boot_problems(read_file(args.boot), read_file(args.factory_boot),
                                  read_file(args.kernel_gz), args.partition_size)
    for problem in problems:
        print(f"FALHOU: {problem}")
    if problems:
        return 1
    print(f"ok {args.boot}: header v2, id, endereços, resource de fábrica e kernel conferem")
    return 0


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    install = sub.add_parser("install")
    install.add_argument("--image", required=True)
    install.add_argument("--dtb", required=True)
    install.add_argument("--factory-boot", required=True)
    install.add_argument("--out", required=True)
    install.add_argument("--kernel-ref", required=True)
    install.add_argument("--modules-dir")
    install.set_defaults(run=run_install)
    verify = sub.add_parser("verify-boot")
    verify.add_argument("boot")
    verify.add_argument("--factory-boot", required=True)
    verify.add_argument("--kernel-gz", required=True)
    verify.add_argument("--partition-size", type=int, default=BOOT_PARTITION_SIZE)
    verify.set_defaults(run=run_verify_boot)
    variant = sub.add_parser("variant")
    variant.add_argument("boot")
    variant.add_argument("-o", "--output", required=True)
    variant.add_argument("--set", required=True, help="chave=valor da cmdline")
    variant.set_defaults(run=run_variant)
    return parser.parse_args(argv)


if __name__ == "__main__":
    parsed = parse_args(sys.argv[1:])
    sys.exit(parsed.run(parsed))
