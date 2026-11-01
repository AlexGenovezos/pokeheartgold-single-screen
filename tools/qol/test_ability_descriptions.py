"""Modern descriptions stay in the summary's real ability bank, 722."""
from pathlib import Path
import importlib.util
import struct
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from game_text import game_text
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc

ROOT = Path(__file__).resolve().parents[2]


def original_descriptions(bank=722):
    rows=ET.parse(ROOT/f'files/msgdata/msg/msg_{bank:04}.gmm').findall('row')
    return [game_text(row.find('language').text.replace('\\n','\n'),ROOT/'charmap.txt') for row in rows]


class AbilityDescriptionTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('ability_descriptions'), 'Modern ability descriptions are missing')
        import ability_descriptions
        return ability_descriptions

    def test_original_entries_survive_and_all_three_banks_extend_atomically(self):
        module=self.module()
        banks=[b'original bank']*830;original=original_descriptions()
        for bank in (720,721,722):banks[bank]=pack_messages(original_descriptions(bank),26692)
        result,names=unpack_narc(module.modern_ability_description_resources(pack_narc(banks),ROOT/'charmap.txt'))
        self.assertEqual(names,unpack_narc(pack_narc(banks))[1]);self.assertEqual(len(result),830)
        words,key=unpack_messages(result[722]);self.assertEqual(key,26692)
        expected={81:'Raises evasion when\nit is snowing.',
                  115:'Restores HP when\nit is snowing.',
                  117:'Summons snow for\nfive turns in battle.',
                  12:'Blocks infatuation,\nTaunt and Intimidate.',
                  20:"Prevents confusion and\nIntimidate’s stat loss.",
                  39:"Prevents flinching and\nIntimidate’s stat loss.",
                  113:"Hits Ghosts. Blocks\nIntimidate’s stat loss.",
                  5:'At full HP, survives a hit.\nBlocks 1-hit KO moves.',
                  31:'Draws in Electric moves.\nAbsorbs them for Sp. Atk.',
                  35:'Prevents accuracy loss.\nIgnores evasion changes.',
                  51:'Prevents accuracy loss.\nIgnores evasion changes.',
                  114:'Draws in Water moves.\nAbsorbs them for Sp. Atk.',
                  130:'May disable a move that\nhits this Pokémon.',
                  172:'Stat loss from a foe\nsharply raises Sp. Atk.'}
        self.assertEqual(len(words),173)
        for index,word in enumerate(words[:124]):
            self.assertEqual(word,game_text(expected[index],ROOT/'charmap.txt') if index in expected else original[index])
        self.assertEqual(result[:720],banks[:720]);self.assertEqual(result[723:],banks[723:])
        for bank,label in ((720,'Cursed Body'),(721,'CURSED BODY'),(722,'May disable a move that\nhits this Pokémon.')):
            extended,key=unpack_messages(result[bank]);self.assertEqual(key,26692)
            self.assertEqual(len(extended),173)
            self.assertEqual(extended[130],game_text(label,ROOT/'charmap.txt'))
            self.assertEqual(extended[124:130],[game_text(' -',ROOT/'charmap.txt')]*6)
            competitive={720:'Competitive',721:'COMPETITIVE',722:expected[172]}
            self.assertEqual(extended[172],game_text(competitive[bank],ROOT/'charmap.txt'))
            self.assertEqual(extended[131:172],[game_text(' -',ROOT/'charmap.txt')]*41)
            if bank!=722:self.assertEqual(extended[:124],original_descriptions(bank))
        summary=(ROOT/'src/pokemon_summary_text.c').read_text()
        self.assertIn('NARC_msg_msg_0722_bin',summary)
        # All three labels fit the existing two-line description box, with no
        # summary-window growth or message/name capacity changes.
        font_path=ROOT/'files/graphic/font/font_00000000.bin'
        font=font_path.read_bytes() if font_path.is_file() else None
        widths=struct.unpack_from('<I',font,4)[0] if font else None
        for text in expected.values():
            self.assertEqual(len(text.splitlines()),2)
            if font:
                for line in text.splitlines():
                    self.assertLessEqual(sum(font[widths+glyph-1] for glyph in game_text(line,ROOT/'charmap.txt')[:-1]),19*8-3)

    def test_description_transform_rejects_missing_bank_binary_and_source_drift(self):
        module=self.module();words=original_descriptions()
        with self.assertRaisesRegex(ValueError,'absent'):
            module.modern_ability_description_resources(pack_narc([b'']*722),ROOT/'charmap.txt')
        banks=[b'']*829
        for bank in (720,721):banks[bank]=pack_messages(original_descriptions(bank),26692)
        words[5]=game_text('wrong',ROOT/'charmap.txt');banks[722]=pack_messages(words,26692)
        with self.assertRaisesRegex(ValueError,'match'):
            module.modern_ability_description_resources(pack_narc(banks),ROOT/'charmap.txt')
        source=(ROOT/'files/msgdata/msg/msg_0722.gmm').read_text()
        with self.assertRaisesRegex(ValueError,'expected source'):
            module.modern_ability_description_source(source+'\n',ROOT/'charmap.txt')

    def test_every_ability_bank_rejects_source_or_binary_drift_before_returning_archive(self):
        module=self.module();banks=[b'keep']*830
        for bank in (720,721,722):banks[bank]=pack_messages(original_descriptions(bank),26692)
        for bank in (720,721,722):
            corrupt=list(banks);words=original_descriptions(bank);words[26]=game_text('wrong',ROOT/'charmap.txt')
            corrupt[bank]=pack_messages(words,26692)
            with self.assertRaisesRegex(ValueError,f'bank{bank}.*match'):
                module.modern_ability_description_resources(pack_narc(corrupt),ROOT/'charmap.txt')
            read_text=Path.read_text
            def read(path,*args,**kwargs):
                text=read_text(path,*args,**kwargs)
                return text+'\n' if path.name==f'msg_{bank:04}.gmm' else text
            with patch.object(Path,'read_text',read),self.assertRaisesRegex(ValueError,f'bank{bank}.*expected source'):
                module.modern_ability_description_resources(pack_narc(banks),ROOT/'charmap.txt')

    def test_real_fairy_and_extended_move_transforms_compose_with_ability_descriptions(self):
        module=self.module()
        import modern_rom
        from move_resources import extended_move_resources,read_entries
        paths=[ROOT/p for p in ('files/msgdata/msg.narc','files/poketool/waza/waza_tbl.narc',
                               'files/battledata/script/move_script.narc')]
        if not all(p.is_file() for p in paths):self.skipTest('Original generated archives unavailable')
        messages=paths[0].read_bytes()
        header=bytes.fromhex('5247434efffe010130010000100001005241484320010000ffffffff0300000010000000000000000001000018000000')
        from nitro_data import lz10_literals
        icons=[b'keep']*346;icons[236]=lz10_literals(header+b'\xAA'*256)
        _,fairy=modern_rom.modern_type_resources(pack_narc(icons),messages,ROOT/'charmap.txt')
        ability=module.modern_ability_description_resources(fairy,ROOT/'charmap.txt')
        entries=read_entries(ROOT/'include/data/qol_move_entries.inc')
        _,_,final=extended_move_resources(paths[1].read_bytes(),paths[2].read_bytes(),ability,ROOT/'charmap.txt',entries)
        before,_=unpack_narc(messages);after,_=unpack_narc(final)
        self.assertEqual(len(after),830)
        self.assertEqual(after[722],unpack_narc(ability)[0][722])
        self.assertEqual(after[735],unpack_narc(fairy)[0][735])
        self.assertNotEqual(after[722],before[722]);self.assertNotEqual(after[735],before[735])
        for i,bank in enumerate(before):
            if i not in (720,721,722,735,749,750,751):self.assertEqual(after[i],bank)
        self.assertTrue(unpack_messages(after[829])[0][577])

    def test_battle_flag_routes_descriptions_and_scripts_before_move_resources(self):
        self.module()
        import modern_rom
        self.assertTrue(callable(getattr(modern_rom,'modern_sturdy_resources',None)), 'Sturdy ROM integration is missing')
        paths={path:(i,i,i+1) for i,path in enumerate(('a/0/0/8','a/0/2/7','a/0/6/8','a/0/0/1','a/0/1/1','a/0/0/0','a/0/3/0'))}
        with patch('modern_rom.rom_files',return_value=paths), \
             patch('modern_rom.modern_type_resources',return_value=(b'icons',b'fairy')), \
             patch('modern_rom.modern_pokedex_resources',return_value=b'dex'), \
             patch('modern_rom.modern_battle_resources',return_value=b'numeric'), \
             patch('modern_rom.modern_paralysis_resources',return_value=b'electric'), \
             patch('modern_rom.modern_weather_resources',return_value=b'finite'), \
             patch('modern_rom.modern_absorption_resources',return_value=b'absorption'), \
             patch('modern_rom.modern_sturdy_resources',return_value=b'sturdy') as sturdy, \
             patch('modern_rom.modern_cursed_body_resources',return_value=b'cursed') as cursed, \
             patch('modern_rom.modern_competitive_resources',return_value=b'competitive') as competitive, \
             patch('modern_rom.modern_oblivious_intimidate_resources',return_value=b'oblivious') as oblivious, \
             patch.multiple('modern_rom', modern_simple_resources=lambda data:data,
                            modern_simple_message_resources=lambda data,charmap:data,
                            modern_snow_message_resources=lambda data,charmap:data,
                            modern_snow_effect_resources=lambda data:b'snow'), \
             patch('modern_rom.modern_ability_description_resources',return_value=b'abilities') as abilities, \
             patch('modern_rom.modern_drain_resources',return_value=b'drain') as drain, \
             patch('modern_rom.modern_move_stat_resources',return_value=b'stat-moves') as stat_moves, \
             patch('modern_rom.modern_move_effect_resources',return_value=b'move-effects') as move_effects, \
             patch('modern_rom.extended_move_resources',return_value=(b'data',b'moves',b'all')) as extended, \
             patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:replacements):
            result=modern_rom.make_modern_rom(b'123456',ROOT/'charmap.txt',types=True,battle_rules=True,moves=True)
        sturdy.assert_called_once_with(b'absorption');abilities.assert_called_once_with(b'fairy',ROOT/'charmap.txt')
        cursed.assert_called_once_with(b'sturdy');competitive.assert_called_once_with(b'cursed');oblivious.assert_called_once_with(b'competitive');drain.assert_called_once_with(b'oblivious');self.assertEqual(extended.call_args.args[2],b'abilities')
        stat_moves.assert_called_once_with(b'drain',True)
        move_effects.assert_called_once_with(b'snow')
        self.assertEqual(result['a/0/0/1'],b'stat-moves')
        self.assertEqual(result['a/0/3/0'],b'move-effects')
        self.assertEqual(result['a/0/2/7'],b'all')


if __name__=='__main__':unittest.main()
