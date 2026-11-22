"""Testes do tools/mkboot.py (boot.img Android header v2 da Rockchip).

Rodar: python3 -m unittest discover -s tests
Os testes de ida e volta com as imagens de fábrica usam ~/hy300-backup (fora do repo)
e são pulados se o backup não existir.
"""
import hashlib
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import mkboot  # noqa: E402

BACKUP = os.path.expanduser("~/hy300-backup")
PAGE = 2048


def make_sample(**overrides):
    fields = dict(
        kernel=b"K" * 5000,
        ramdisk=b"R" * 3000,
        second=b"S" * 100,
        recovery_dtbo=b"",
        dtb=b"D" * 700,
        kernel_addr=0x10008000,
        ramdisk_addr=0x11000000,
        second_addr=0x10F00000,
        tags_addr=0x10000100,
        dtb_addr=0x11F00000,
        page_size=PAGE,
        os_version=0x18000167,
        name=b"",
        cmdline=b"console=ttyFIQ0 init=/init",
        extra_cmdline=b"",
    )
    fields.update(overrides)
    return mkboot.BootImage(**fields)


class BuildTest(unittest.TestCase):
    def test_build_then_unpack_returns_same_sections(self):
        img = make_sample()
        back = mkboot.unpack(mkboot.build(img))
        self.assertEqual(back, img)

    def test_sections_start_on_page_boundaries(self):
        data = mkboot.build(make_sample())
        self.assertEqual(data[:8], b"ANDROID!")
        self.assertEqual(data[PAGE:PAGE + 5000], b"K" * 5000)
        ramdisk_off = PAGE + 3 * PAGE  # kernel de 5000 bytes ocupa 3 páginas
        self.assertEqual(data[ramdisk_off:ramdisk_off + 3000], b"R" * 3000)
        self.assertEqual(len(data) % PAGE, 0)

    def test_header_v2_fields(self):
        data = mkboot.build(make_sample())
        self.assertEqual(struct.unpack_from("<I", data, 40)[0], 2)  # header_version
        self.assertEqual(struct.unpack_from("<I", data, 1644)[0], 1660)  # header_size
        self.assertEqual(struct.unpack_from("<I", data, 1648)[0], 700)  # dtb_size

    def test_recovery_dtbo_offset_is_absolute(self):
        data = mkboot.build(make_sample(recovery_dtbo=b"O" * 10))
        size, offset = struct.unpack_from("<IQ", data, 1632)
        self.assertEqual(size, 10)
        self.assertEqual(data[offset:offset + 10], b"O" * 10)

    def test_id_is_sha1_of_sections_and_sizes(self):
        img = make_sample()
        h = hashlib.sha1()
        for part in (img.kernel, img.ramdisk, img.second, img.recovery_dtbo, img.dtb):
            h.update(part)
            h.update(struct.pack("<I", len(part)))
        data = mkboot.build(img)
        self.assertEqual(data[576:596], h.digest())
        self.assertEqual(data[596:608], b"\0" * 12)

    def test_pad_to_fills_with_zeros(self):
        data = mkboot.build(make_sample(), pad_to=64 * PAGE)
        self.assertEqual(len(data), 64 * PAGE)

    def test_pad_to_smaller_than_image_fails(self):
        with self.assertRaises(ValueError):
            mkboot.build(make_sample(), pad_to=PAGE)

    def test_cmdline_longer_than_field_fails(self):
        with self.assertRaises(ValueError):
            mkboot.build(make_sample(cmdline=b"x" * 600))


class ReplaceTest(unittest.TestCase):
    def test_append_cmdline_keeps_original_and_adds_marker(self):
        img = mkboot.append_cmdline(make_sample(), b"hy300.test=1")
        self.assertEqual(img.cmdline, b"console=ttyFIQ0 init=/init hy300.test=1")

    def test_replace_kernel_changes_only_kernel(self):
        img = make_sample()
        new = mkboot.replace(img, kernel=b"N" * 10)
        self.assertEqual(new.kernel, b"N" * 10)
        self.assertEqual(new.ramdisk, img.ramdisk)
        self.assertEqual(new.dtb, img.dtb)


@unittest.skipUnless(os.path.isdir(BACKUP), "backup de fábrica ausente")
class FactoryRoundTripTest(unittest.TestCase):
    def assert_roundtrip(self, name):
        with open(os.path.join(BACKUP, name), "rb") as f:
            original = f.read()
        rebuilt = mkboot.build(mkboot.unpack(original), pad_to=len(original))
        self.assertEqual(hashlib.sha256(rebuilt).hexdigest(), hashlib.sha256(original).hexdigest())

    def test_boot_img_roundtrip_is_identical(self):
        self.assert_roundtrip("boot.img")

    def test_recovery_img_roundtrip_is_identical(self):
        self.assert_roundtrip("recovery.img")


if __name__ == "__main__":
    unittest.main()
