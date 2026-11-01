"""Asset transforms preserve unrelated archives, strings and executable bytes."""
import struct
import unittest

import nitro_data as nitro


class NitroDataTests(unittest.TestCase):
    def test_archive_replacement_keeps_other_members_and_name_table(self):
        names = b'BTNF' + struct.pack('<I', 16) + bytes.fromhex('0400000000000100')
        original = nitro.pack_narc([b'old', b'untouched', b''], names)
        members, actual_names = nitro.unpack_narc(original)
        self.assertEqual(actual_names, names)
        self.assertEqual(members, [b'old', b'untouched', b''])
        members[0] = b'a much longer new asset'
        modified = nitro.pack_narc(members, actual_names)
        self.assertEqual(nitro.unpack_narc(modified), (members, names))
        damaged = bytearray(original)
        struct.pack_into('<I', damaged, 32, 0xFFFFFFFF)  # First member end.
        with self.assertRaises(ValueError):
            nitro.unpack_narc(damaged)
        with self.assertRaises(ValueError):
            nitro.unpack_narc(original[:-1])

    def test_message_encryption_matches_known_single_entry_and_preserves_packed_words(self):
        # Header key1: entry key765, message key0x1BD3. Off12,len2.
        expected = struct.pack('<HHIIHH', 1, 1, 12 ^ 0x02FD02FD,
                               2 ^ 0x02FD02FD, 0x012B ^ 0x1BD3,
                               0xFFFF ^ ((0x1BD3 + 18749) & 0xFFFF))
        self.assertEqual(nitro.pack_messages([[0x012B, 0xFFFF]], 1), expected)
        words = [[0x012B, 0xFFFF], [0xF100, 0x8132, 0xFFFF], [0xFFFF]]
        bank = nitro.pack_messages(words, 0x3B89)
        decoded, key = nitro.unpack_messages(bank)
        self.assertEqual(decoded, words)
        decoded[0] = [0x0130, 0x0133, 0xFFFF]
        result, result_key = nitro.unpack_messages(nitro.pack_messages(decoded, key))
        self.assertEqual(result[1:], words[1:])
        self.assertEqual(result_key, 0x3B89)
        with self.assertRaises(ValueError):
            nitro.unpack_messages(bank[:-1])

    def test_lz10_literals_and_overlapping_copy(self):
        data = bytes(range(256)) + b'FAIRY' * 20
        self.assertEqual(nitro.lz10_decompress(nitro.lz10_literals(data)), data)
        # Literal A, then an overlapping 5-byte match at distance1.
        self.assertEqual(nitro.lz10_decompress(bytes.fromhex('1006000040412000')), b'AAAAAA')
        with self.assertRaises(ValueError):
            nitro.lz10_decompress(bytes.fromhex('10040000800000'))

    def test_rom_file_growth_keeps_code_and_other_file_and_fixes_header(self):
        rom = bytearray(b'\xFF' * 0x40000)
        # One root directory, two files, no overlays. ARM9 marker stays untouched.
        names = struct.pack('<IHH', 8, 0, 1) + b'\x05first\x06second\0'
        struct.pack_into('<4I', rom, 0x40, 0x200, len(names), 0x240, 16)
        rom[0x200:0x200+len(names)] = names
        struct.pack_into('<4I', rom, 0x240, 0x400, 0x403, 0x404, 0x408)
        struct.pack_into('<I', rom, 0x80, 0x408)
        rom[0x400:0x403] = b'old'
        rom[0x404:0x408] = b'keep'
        rom[0x300:0x30C] = b'ARM9-CONTENT'
        original = bytes(rom)
        output = nitro.replace_rom_files(original, {'first': b'new asset data'})
        self.assertEqual(original, bytes(rom))
        self.assertEqual(output[0x300:0x30C], b'ARM9-CONTENT')
        files = nitro.rom_files(output)
        self.assertEqual(output[slice(*files['first'][1:])], b'new asset data')
        self.assertEqual(output[slice(*files['second'][1:])], b'keep')
        self.assertEqual(len(output), len(original))
        self.assertEqual(struct.unpack_from('<H', output, 0x15E)[0], nitro.crc16(output[:0x15E]))
        with self.assertRaises(ValueError):
            nitro.replace_rom_files(original, {'missing': b'bad'})
        broken = bytearray(original)
        struct.pack_into('<I', broken, 0x244, len(rom) + 1)
        with self.assertRaises(ValueError):
            nitro.rom_files(broken)
