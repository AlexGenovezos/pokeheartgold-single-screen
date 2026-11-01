"""BPS conformance and safe CLI behavior; no game data is needed."""
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from rom_patch import apply_patch, create_patch


def finish_patch(payload, source, target):
    data = payload + struct.pack("<II", zlib.crc32(source), zlib.crc32(target))
    return data + struct.pack("<I", zlib.crc32(data))


class BpsTests(unittest.TestCase):
    def test_known_source_read_and_literal_fixture(self):
        # BPS integers: sizes 3, metadata 0, source-read 2, literal 1.
        patch = finish_patch(b"BPS1\x83\x83\x80\x84\x81d", b"abc", b"abd")
        self.assertEqual(apply_patch(b"abc", patch), b"abd")
        self.assertEqual(create_patch(b"abc", b"abd"), patch)

    def test_external_source_copy_and_overlapping_target_copy(self):
        # SourceCopy: 3 bytes from offset +3 ("def"), then overlapping
        # TargetCopy: 6 bytes from offset 0, yielding "defdefdef".
        patch = finish_patch(b"BPS1\x86\x89\x80\x8a\x86\x97\x80",
                             b"abcdef", b"defdefdef")
        self.assertEqual(apply_patch(b"abcdef", patch), b"defdefdef")

    def test_round_trip_sizes_and_patterns(self):
        pairs = [(b"", b""), (b"", b"new"), (b"gone", b""),
                 (b"same", b"same"), (b"abcdef", b"abXdeY"),
                 (b"a" * 300, b"a" * 129 + b"xyz" + b"a" * 168),
                 (bytes(range(256)), bytes(reversed(range(256))))]
        for source, target in pairs:
            with self.subTest(source_length=len(source), target_length=len(target)):
                self.assertEqual(apply_patch(source, create_patch(source, target)), target)

    def test_wrong_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "source"):
            apply_patch(b"wrong", create_patch(b"right", b"changed"))

    def test_patch_corruption_is_rejected(self):
        patch = bytearray(create_patch(b"abc", b"abd"))
        patch[4] ^= 1
        with self.assertRaisesRegex(ValueError, "patch.*CRC"):
            apply_patch(b"abc", bytes(patch))

    def test_target_crc_is_verified_independently(self):
        patch = bytearray(create_patch(b"abc", b"abd"))
        patch[-8] ^= 1
        patch[-4:] = struct.pack("<I", zlib.crc32(patch[:-4]))
        with self.assertRaisesRegex(ValueError, "target.*CRC"):
            apply_patch(b"abc", bytes(patch))

    def test_truncated_and_invalid_instructions_are_rejected(self):
        valid = create_patch(b"abc", b"abd")
        for length in range(len(valid)):
            with self.subTest(length=length), self.assertRaises(ValueError):
                apply_patch(b"abc", valid[:length])
        # Source read beyond input; target copy before any output; missing literal.
        for payload in (b"BPS1\x83\x84\x80\x8c",
                        b"BPS1\x83\x81\x80\x83\x80",
                        b"BPS1\x83\x81\x80\x81"):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                apply_patch(b"abc", finish_patch(payload, b"abc", b"x"))

    def test_extra_commands_after_target_are_rejected(self):
        patch = finish_patch(b"BPS1\x83\x83\x80\x88\x80", b"abc", b"abc")
        with self.assertRaisesRegex(ValueError, "trailing"):
            apply_patch(b"abc", patch)


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(Path(__file__).with_name("rom_patch.py")),
                               *map(str, args)], capture_output=True, text=True)

    def test_hash_guard_round_trip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, target, patch, output = [root / n for n in ("clean.nds", "mod.nds", "mod.bps", "out.nds")]
            source.write_bytes(b"clean")
            target.write_bytes(b"modified")
            args = ("create", source, target, patch, "--source-sha1")
            self.assertNotEqual(self.run_cli(*args, "0" * 40).returncode, 0)
            self.assertFalse(patch.exists())
            result = self.run_cli(*args, hashlib.sha1(b"clean").hexdigest())
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(self.run_cli(*args, hashlib.sha1(b"clean").hexdigest()).returncode, 0)
            result = self.run_cli("apply", source, patch, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), target.read_bytes())
            self.assertNotEqual(self.run_cli("apply", source, patch, source).returncode, 0)
            self.assertEqual(source.read_bytes(), b"clean")


if __name__ == "__main__":
    unittest.main()

