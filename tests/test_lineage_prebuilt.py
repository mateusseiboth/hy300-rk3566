"""Testes do tools/lineage_prebuilt.py: prebuilts do kernel para a árvore do LineageOS e a
conferência do boot.img que o build do Lineage gera.

Rodar: python3 -I -m unittest discover -s tests
Os testes com as imagens de fábrica usam ~/hy300-backup (fora do repo) e são pulados sem ele.
"""
import gzip
import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import lineage_prebuilt  # noqa: E402
import mkboot  # noqa: E402

BACKUP = os.path.expanduser("~/hy300-backup")
FACTORY_BOOT = os.path.join(BACKUP, "boot.img")
PAGE = 2048
IMAGE = b"ARM64 Image ... HY300 Projector ..." + b"\0" * 5000
RESOURCE = b"RSCE" + b"\0" * 508 + b"compatible snps,dwcmshc-sdhci" + b"\0" * 100


def make_boot(**overrides):
    fields = dict(
        kernel=lineage_prebuilt.compress_kernel(IMAGE), ramdisk=b"R" * 3000, second=RESOURCE,
        recovery_dtbo=b"", dtb=b"D" * 77, kernel_addr=0x10008000, ramdisk_addr=0x11000000,
        second_addr=0x10F00000, tags_addr=0x10000100, dtb_addr=0x11F00000, page_size=PAGE,
        os_version=0, name=b"",
        cmdline=b"console=ttyFIQ0 androidboot.hardware=rk3566 androidboot.boot_devices=fe310000.sdhci",
        extra_cmdline=b"",
    )
    fields.update(overrides)
    return mkboot.BootImage(**fields)


class CompressKernelTest(unittest.TestCase):
    def test_compress_kernel_round_trips(self):
        self.assertEqual(gzip.decompress(lineage_prebuilt.compress_kernel(IMAGE)), IMAGE)

    def test_compress_kernel_is_reproducible(self):
        self.assertEqual(lineage_prebuilt.compress_kernel(IMAGE), lineage_prebuilt.compress_kernel(IMAGE))

    def test_compress_kernel_has_no_timestamp(self):
        self.assertEqual(lineage_prebuilt.compress_kernel(IMAGE)[4:8], b"\0\0\0\0")


class RequireTest(unittest.TestCase):
    def test_require_builtin_dtb_accepts_hy300_image(self):
        lineage_prebuilt.require_builtin_dtb(IMAGE)

    def test_require_builtin_dtb_rejects_kernel_without_hy300_dt(self):
        with self.assertRaisesRegex(ValueError, "DT embutido"):
            lineage_prebuilt.require_builtin_dtb(b"ARM64 Image generica")

    def test_read_factory_resource_returns_second_section(self):
        boot = mkboot.build(make_boot())
        self.assertEqual(lineage_prebuilt.read_factory_resource(boot), RESOURCE)

    def test_read_factory_resource_rejects_non_rsce(self):
        boot = mkboot.build(make_boot(second=b"XXXX" + b"\0" * 600))
        with self.assertRaisesRegex(ValueError, "RSCE"):
            lineage_prebuilt.read_factory_resource(boot)

    def test_read_factory_resource_requires_emmc_known_by_uboot(self):
        boot = mkboot.build(make_boot(second=b"RSCE" + b"\0" * 600))
        with self.assertRaisesRegex(ValueError, "dwcmshc"):
            lineage_prebuilt.read_factory_resource(boot)

    @unittest.skipUnless(os.path.exists(FACTORY_BOOT), "boot.img de fábrica fora deste host")
    def test_read_factory_resource_accepts_factory_boot(self):
        with open(FACTORY_BOOT, "rb") as handle:
            self.assertTrue(lineage_prebuilt.read_factory_resource(handle.read()).startswith(b"RSCE"))


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, data):
        path = os.path.join(self.tmp.name, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def install(self):
        out = os.path.join(self.tmp.name, "prebuilt")
        lineage_prebuilt.install_prebuilts(
            image=self.write("Image", IMAGE), dtb=self.write("hy300.dtb", b"\xd0\x0d\xfe\xed dtb"),
            factory_boot=self.write("boot.img", mkboot.build(make_boot())), outdir=out,
            kernel_ref="hy300-ack-6.1 c42119ce5a22")
        return out

    def read(self, *path):
        with open(os.path.join(*path), "rb") as handle:
            return handle.read()

    def test_install_prebuilts_writes_the_files_the_tree_expects(self):
        out = self.install()
        self.assertEqual(gzip.decompress(self.read(out, "Image.gz")), IMAGE)
        self.assertEqual(self.read(out, "dtb", "rk3566-hy300.dtb"), b"\xd0\x0d\xfe\xed dtb")
        self.assertEqual(self.read(out, "resource.img"), RESOURCE)

    def test_install_prebuilts_records_kernel_ref_and_checksums(self):
        out = self.install()
        version = self.read(out, "VERSION").decode()
        self.assertIn("kernel: hy300-ack-6.1 c42119ce5a22", version)
        digest = hashlib.sha256(self.read(out, "Image.gz")).hexdigest()
        self.assertIn(f"{digest}  Image.gz", version)


class VerifyBootTest(unittest.TestCase):
    def setUp(self):
        self.factory = mkboot.build(make_boot(kernel=b"K" * 9000, ramdisk=b"F" * 100))
        self.kernel_gz = lineage_prebuilt.compress_kernel(IMAGE)

    def verify(self, img, partition_size=41943040):
        return lineage_prebuilt.find_boot_problems(
            mkboot.build(img), self.factory, kernel_gz=self.kernel_gz, partition_size=partition_size)

    def test_find_boot_problems_accepts_good_image(self):
        self.assertEqual(self.verify(make_boot()), [])

    def test_find_boot_problems_reports_wrong_id(self):
        data = bytearray(mkboot.build(make_boot()))
        data[576:580] = b"\xff\xff\xff\xff"
        problems = lineage_prebuilt.find_boot_problems(
            bytes(data), self.factory, kernel_gz=self.kernel_gz, partition_size=41943040)
        self.assertTrue(any("id" in p for p in problems), problems)

    def test_find_boot_problems_reports_other_resource(self):
        problems = self.verify(make_boot(second=b"RSCE outro"))
        self.assertTrue(any("resource" in p for p in problems), problems)

    def test_find_boot_problems_reports_address_mismatch(self):
        problems = self.verify(make_boot(ramdisk_addr=0x12000000))
        self.assertTrue(any("ramdisk_addr" in p for p in problems), problems)

    def test_find_boot_problems_reports_other_kernel(self):
        problems = self.verify(make_boot(kernel=b"outro kernel"))
        self.assertTrue(any("kernel" in p for p in problems), problems)

    def test_find_boot_problems_reports_image_bigger_than_partition(self):
        problems = self.verify(make_boot(), partition_size=4096)
        self.assertTrue(any("partição" in p for p in problems), problems)

    def test_find_boot_problems_requires_boot_devices_on_cmdline(self):
        problems = self.verify(make_boot(cmdline=b"console=ttyFIQ0 androidboot.hardware=rk3566"))
        self.assertTrue(any("boot_devices" in p for p in problems), problems)

    def test_find_boot_problems_requires_ramdisk(self):
        problems = self.verify(make_boot(ramdisk=b""))
        self.assertTrue(any("ramdisk" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
