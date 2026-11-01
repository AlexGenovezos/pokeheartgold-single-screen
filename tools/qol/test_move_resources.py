from pathlib import Path
import struct
import unittest

import move_resources
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc

ROOT = Path(__file__).resolve().parents[2]


class MoveResourceTests(unittest.TestCase):
    def test_numeric_rows_share_the_game_source_and_reject_unexpected_syntax(self):
        entries = move_resources.read_entries(ROOT / 'include/data/qol_move_entries.inc')
        self.assertEqual([e['id'] for e in entries], [577, 580, 586, 588, 608])
        self.assertEqual(entries[3]['chance'], 30)
        self.assertEqual(entries[1]['effect'], 3)
        self.assertEqual(entries[0]['flags'], 0x32)
        with self.assertRaises(ValueError):
            move_resources.parse_entries('QOL_EXTRA_MOVE(577, FUNCTION(), 1)')
        with self.assertRaises(ValueError):
            move_resources.parse_entries('QOL_EXTRA_MOVE(577,17,1,40,9,0,15,0,4,0,50,304)\n' * 2)

    def test_new_resources_preserve_legacy_data_and_derive_metadata_from_shared_rows(self):
        entries = move_resources.read_entries(ROOT / 'include/data/qol_move_entries.inc')
        data = [bytes([i % 256]) * 16 for i in range(471)]
        # Original archive includes 33 unused script members after move467.
        scripts = [struct.pack('<2I', i, i + 1) for i in range(501)]
        messages = [b'keep'] * 803
        words = [[0x012B, 0xFFFF] for _ in range(468)]
        for bank in (749, 750, 751):
            messages[bank] = pack_messages(words, bank)
        output = move_resources.extended_move_resources(pack_narc(data), pack_narc(scripts),
                                                        pack_narc(messages), ROOT / 'charmap.txt', entries)
        actual_data, _ = unpack_narc(output[0])
        actual_scripts, _ = unpack_narc(output[1])
        actual_messages, _ = unpack_narc(output[2])
        self.assertEqual(actual_data[:471], data)
        self.assertEqual(actual_scripts[:501], scripts)
        for row in entries:
            actual = struct.unpack('<H6BHbB2BH', actual_data[row['id']])
            self.assertEqual(actual, tuple(row[k] for k in ('effect','category','power','type','accuracy',
                            'pp','chance','range','priority','flags')) + (0,0,0))
            self.assertEqual(actual_scripts[row['id']], scripts[row['animation']])
        for bank in (749,750,751):
            updated, key = unpack_messages(actual_messages[bank])
            self.assertEqual(updated[:468], words)
            self.assertEqual(key, bank)
            self.assertEqual(len(updated), 609)
            self.assertNotEqual(updated[588], [0xFFFF])
        for i, member in enumerate(messages):
            if i not in (749,750,751):
                self.assertEqual(actual_messages[i], member)

    def test_new_card_labels_and_full_names_fit_the_existing_font_and_string_capacity(self):
        from modern_rom import game_text
        font_path=ROOT/'files/graphic/font/font_00000000.bin'
        if not font_path.exists():
            self.skipTest('Needs the locally supplied game font')
        font=font_path.read_bytes();widths=font[struct.unpack_from('<I',font,4)[0]:]
        for presentation in move_resources.PRESENTATION.values():
            self.assertLessEqual(len(presentation['name']),15)
            codes=game_text(presentation['card'],ROOT/'charmap.txt')[:-1]
            self.assertLessEqual(sum(widths[c-1] for c in codes)+24+12,108)

    def test_combined_rom_passes_updated_messages_and_scripts_to_next_transform(self):
        from unittest.mock import patch
        import modern_rom
        paths={path:(i,i,i+1) for i,path in enumerate(('a/0/0/8','a/0/2/7','a/0/6/8','a/0/0/1','a/0/1/1','a/0/0/0'))}
        with patch('modern_rom.rom_files',return_value=paths), \
             patch('modern_rom.modern_type_resources',return_value=(b'icons',b'fairy messages')), \
             patch('modern_rom.modern_pokedex_resources',return_value=b'dex'), \
             patch('modern_rom.modern_battle_resources',return_value=b'numeric'), \
             patch('modern_rom.modern_paralysis_resources',return_value=b'electric'), \
             patch('modern_rom.modern_drain_resources',return_value=b'drain') as drain, \
             patch('modern_rom.extended_move_resources',return_value=(b'data',b'moves',b'all messages')) as extended, \
             patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:replacements):
            result=modern_rom.make_modern_rom(b'123456',ROOT/'charmap.txt',types=True,battle_rules=True,moves=True)
        drain.assert_called_once_with(b'electric')
        self.assertEqual(extended.call_args.args[2],b'fairy messages')
        self.assertEqual(result['a/0/2/7'],b'all messages')
        self.assertEqual(result['a/0/0/1'],b'drain')

    def test_drain_archive_preserves_every_other_member(self):
        from unittest.mock import patch
        import modern_rom
        members=[bytes([i])*4 for i in range(40)]
        with patch('modern_rom.modern_drain_script',return_value=b'drain') as compile_script:
            actual,_=unpack_narc(modern_rom.modern_drain_resources(pack_narc(members)))
        compile_script.assert_called_once_with(members[24])
        self.assertEqual(actual[:24],members[:24])
        self.assertEqual(actual[24],b'drain')
        self.assertEqual(actual[25:],members[25:])
