from pathlib import Path
import struct
import unittest

import modern_rom
import nitro_data as nitro


ROOT = Path(__file__).resolve().parents[2]


class ModernRomTests(unittest.TestCase):
    def test_fairy_resources_preserve_shared_palette_and_unrelated_messages(self):
        # Matching sprite resource header; 32x16, four-bit, eight tiles.
        header = bytes.fromhex('5247434efffe010130010000100001005241484320010000ffffffff0300000010000000000000000001000018000000')
        chars = [b'keep'] * 346
        chars[74] = b'shared palette must not change'
        chars[236] = nitro.lz10_literals(header + b'\xAA' * 256)
        icons = nitro.pack_narc(chars)
        original_words = [[0x012B, 0xFFFF] for _ in range(18)]
        messages = [b'other-bank'] * 803
        messages[735] = nitro.pack_messages(original_words, 0x3B89)
        bank = nitro.pack_narc(messages)
        new_icons, new_bank = modern_rom.modern_type_resources(icons, bank, ROOT / 'charmap.txt')
        new_chars, _ = nitro.unpack_narc(new_icons)
        new_messages, _ = nitro.unpack_narc(new_bank)
        for i, data in enumerate(chars):
            if i != 236:
                self.assertEqual(new_chars[i], data)
        self.assertEqual(nitro.lz10_decompress(new_chars[236])[:48], header)
        self.assertNotEqual(nitro.lz10_decompress(new_chars[236])[48:], b'\xAA' * 256)
        for i, data in enumerate(messages):
            if i != 735:
                self.assertEqual(new_messages[i], data)
        words, key = nitro.unpack_messages(new_messages[735])
        self.assertEqual(key, 0x3B89)
        self.assertEqual(words[:9], original_words[:9])
        self.assertEqual(words[10:], original_words[10:])
        self.assertEqual(words[9], [0x0130, 0x012B, 0x0133, 0x013C, 0x0143, 0xFFFF])

    def test_icon_stays_inside_existing_cell_and_uses_the_existing_palette(self):
        pixels = modern_rom.fairy_icon_pixels()
        self.assertEqual((len(pixels), len(pixels[0])), (16, 32))
        self.assertEqual({p for row in pixels for p in row}, {0, 5, 6, 13, 15})
        self.assertEqual(pixels[0], [0] * 32)
        self.assertEqual(pixels[15], [0] * 32)
        self.assertEqual(pixels[5][4:8], [15] * 4)  # F's top bar.
        self.assertEqual(pixels[10][4], 15)  # F's vertical stem.

    def test_invalid_sprite_geometry_and_unrepresentable_text_are_rejected(self):
        with self.assertRaises(ValueError):
            modern_rom.fairy_icon(b'invalid')
        with self.assertRaises(ValueError):
            modern_rom.game_text('not in the DS font: \U0001F9DA', ROOT / 'charmap.txt')

    def test_pokedex_gets_a_separate_48_pixel_fairy_icon(self):
        header = bytes.fromhex('5247434efffe0101b00100001000010052414843a0010000ffffffff0300000010001000000000008001000018000000')
        members = [b'unchanged'] * 123
        members[36] = nitro.lz10_literals(header + b'\x11' * 384)
        before = nitro.pack_narc(members)
        output = modern_rom.modern_pokedex_resources(before)
        actual, _ = nitro.unpack_narc(output)
        self.assertEqual(actual[:123], members)
        self.assertEqual(len(actual), 124)
        graphic = nitro.lz10_decompress(actual[123])
        self.assertEqual(graphic[:48], header)
        self.assertEqual(len(graphic), 432)
        self.assertNotEqual(graphic[48:], b'\x11' * 384)
