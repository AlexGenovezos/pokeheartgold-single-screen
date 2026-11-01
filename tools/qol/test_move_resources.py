from pathlib import Path
import struct
import json
import re
import unittest

import move_resources
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc

ROOT = Path(__file__).resolve().parents[2]


class MoveResourceTests(unittest.TestCase):
    def test_numeric_rows_share_the_game_source_and_reject_unexpected_syntax(self):
        entries = move_resources.read_entries(ROOT / 'include/data/qol_move_entries.inc')
        from test_modern_next_moves import ROWS
        self.assertEqual([e['id'] for e in entries], [577, 580, 586, 588, 608, 587, 673, 670, 696, 532, 687, 898, 622, 621, 575, 589, 854] + [r[0] for r in ROWS])
        self.assertEqual({e['id'] for e in entries}, set(move_resources.PRESENTATION))
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
        scripts = [struct.pack('<I', 36) for i in range(501)]
        messages = [b'keep'] * 829
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
            self.assertEqual(len(updated), 899)
            self.assertNotEqual(updated[588], [0xFFFF])
        self.assertEqual(len(actual_messages), 830)
        cards, _ = unpack_messages(actual_messages[829])
        self.assertEqual(len(cards), 899)
        for move_id, presentation in move_resources.PRESENTATION.items():
            self.assertEqual(cards[move_id], move_resources.game_text(presentation['card'], ROOT / 'charmap.txt'))
        for move_id in (0, 467, 468, 500, 853, 897):
            self.assertEqual(cards[move_id], [0xFFFF])
        names, _ = unpack_messages(actual_messages[750])
        self.assertEqual(names[622], move_resources.game_text('Precipice Blades', ROOT / 'charmap.txt'))
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
            self.assertLessEqual(len(presentation['name']),31)
            codes=game_text(presentation['card'],ROOT/'charmap.txt')[:-1]
            self.assertLessEqual(sum(widths[c-1] for c in codes)+24+12,108)

    def test_move_archive_rejects_unexpected_baselines_and_nonplain_alias_scripts(self):
        entries = move_resources.read_entries(ROOT / 'include/data/qol_move_entries.inc')
        data = pack_narc([bytes(16)] * 471)
        scripts = [struct.pack('<I',36)] * 501
        messages = [b'keep'] * 829
        for bank in (749,750,751):
            messages[bank] = pack_messages([[0xFFFF]] * 468, bank)
        for count in (803,828,830):
            with self.subTest(count=count), self.assertRaises(ValueError):
                move_resources.extended_move_resources(data, pack_narc(scripts),
                    pack_narc((messages + [b'extra'])[:count]), ROOT/'charmap.txt', entries)
        scripts[entries[-1]['animation']] = struct.pack('<I', 0)
        with self.assertRaises(ValueError):
            move_resources.extended_move_resources(data, pack_narc(scripts), pack_narc(messages),
                ROOT/'charmap.txt', entries)

    def test_batch_matches_pinned_gen9_rows_and_plain_source_scripts(self):
        profile_path=ROOT/'.local-tools/validation/gen9-import-profile.json'
        if not profile_path.exists():
            self.skipTest('Needs pinned import profile')
        profile=json.loads(profile_path.read_text())
        self.assertEqual(profile['engine_revision'],'61b510cfb6cf7d77c3b083150fad3499f82fd326')
        self.assertEqual(profile['target_generation'],9)
        self.assertIs(profile['champions_changes'],False)
        source={m['engine_id']:m for m in profile['moves']}
        batch={587,673,670,696,532,687,898,622,621,575,589,854}
        entries=move_resources.read_entries(ROOT/'include/data/qol_move_entries.inc')
        for row in entries:
            if row['id'] not in batch:
                continue
            move=source[row['id']]
            for field in move_resources.FIELDS[1:10]:
                self.assertEqual(row[field],move['effectChance' if field=='chance' else field])
            # These no-secondary-effect attacks are natively eligible for item flinch.
            self.assertEqual(row['flags'],(move['source_flags'] & ~0x20) | 0x20)
            self.assertEqual(move['upstream_unimplemented'],row['id']==854)
            if row['id']!=622:
                self.assertEqual(move_resources.PRESENTATION[row['id']]['name'],move['name'])
            source_folder=ROOT/'.local-tools/hg-engine/data/battle_scripts/moves'
            if source_folder.exists():
                script=next(source_folder.glob(f"move_script_{row['id']:04}_*.s")).read_text()
                commands=[line.strip() for line in script.splitlines()
                          if line.strip() and not line.strip().startswith(('#','.','_'))]
                self.assertEqual(commands,['GoToEffectScript'])
            alias=(ROOT/f"files/battledata/script/move_script/move_script_{row['animation']:04}.s").read_text()
            self.assertEqual([line.strip() for line in alias.splitlines()
                if line.strip() and not line.strip().startswith(('.','_'))],['GoToEffectScript'])
        self.assertIn('BSCRIPT_VAR_CRITICAL_BOOSTS, 1',
            (ROOT/'files/battledata/script/effect_script/effect_script_0043.s').read_text())
        header=(ROOT/'include/constants/qol_moves.h').read_text()
        self.assertEqual(int(re.search(r'#define QOL_MOVE_CARD_MESSAGE_BANK (\d+)',header)[1]),
                         move_resources.CARD_MESSAGE_BANK)
        self.assertIn('Terastallization is unavailable',move_resources.PRESENTATION[854]['description'])

    def test_actual_archives_keep_legacy_members_and_support_all_new_rows(self):
        paths=[ROOT/path for path in ('files/poketool/waza/waza_tbl.narc',
            'files/a/0/0/0','files/msgdata/msg.narc')]
        if not all(p.exists() for p in paths):
            self.skipTest('Needs locally supplied original archives')
        originals=[p.read_bytes() for p in paths]
        entries=move_resources.read_entries(ROOT/'include/data/qol_move_entries.inc')
        result=move_resources.extended_move_resources(*originals,ROOT/'charmap.txt',entries)
        for index,(before,after) in enumerate(zip(originals,result)):
            original,names=unpack_narc(before)
            updated,updated_names=unpack_narc(after)
            self.assertEqual(updated_names,names)
            for member,words in enumerate(original):
                if index==2 and member in (749,750,751):
                    self.assertEqual(unpack_messages(updated[member])[0][:468],unpack_messages(words)[0])
                else:
                    self.assertEqual(updated[member],words)
        self.assertEqual(len(unpack_narc(result[2])[0]),830)

    def test_combined_rom_passes_updated_messages_and_scripts_to_next_transform(self):
        from unittest.mock import patch
        import modern_rom
        paths={path:(i,i,i+1) for i,path in enumerate(('a/0/0/8','a/0/2/7','a/0/6/8','a/0/0/1','a/0/1/1','a/0/0/0'))}
        with patch('modern_rom.rom_files',return_value=paths), \
             patch('modern_rom.modern_type_resources',return_value=(b'icons',b'fairy messages')), \
             patch('modern_rom.modern_pokedex_resources',return_value=b'dex'), \
             patch('modern_rom.modern_battle_resources',return_value=b'numeric'), \
             patch('modern_rom.modern_paralysis_resources',return_value=b'electric'), \
             patch('modern_rom.modern_weather_resources',return_value=b'finite'), \
             patch('modern_rom.modern_absorption_resources',side_effect=lambda data:data), \
             patch('modern_rom.modern_sturdy_resources',side_effect=lambda data:data), patch('modern_rom.modern_cursed_body_resources',side_effect=lambda data:data), patch('modern_rom.modern_competitive_resources',side_effect=lambda data:data), \
             patch('modern_rom.modern_ability_description_resources',return_value=b'abilities'), \
             patch('modern_rom.modern_drain_resources',return_value=b'drain') as drain, \
             patch('modern_rom.extended_move_resources',return_value=(b'data',b'moves',b'all messages')) as extended, \
             patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:replacements):
            result=modern_rom.make_modern_rom(b'123456',ROOT/'charmap.txt',types=True,battle_rules=True,moves=True)
        drain.assert_called_once_with(b'finite')
        self.assertEqual(extended.call_args.args[2],b'abilities')
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
