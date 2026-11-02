"""Soul Dew presentation owns only row225, after Snow validates bank221."""
from contextlib import ExitStack
from pathlib import Path
import hashlib
import importlib.util
import itertools
import struct
import unittest
from unittest.mock import patch
from game_text import game_text
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc
from simple_scripts import modern_simple_message_resources
from snow_resources import modern_snow_message_resources

ROOT=Path(__file__).resolve().parents[2]
CHARMAP=ROOT/'charmap.txt'
TEXT='LATIOS or LATIAS: boosts\nPsychic- and Dragon-type\nmoves by 20%.'


class SoulDewResourceTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('soul_dew_resources'),'Soul Dew resource owner is missing')
        import soul_dew_resources
        return soul_dew_resources

    def original(self):
        return (ROOT/'files/msgdata/msg.narc').read_bytes()

    def incoming(self):
        return modern_snow_message_resources(modern_simple_message_resources(self.original(),CHARMAP),CHARMAP)

    def test_exact_row_only_key_names_members_and_fit(self):
        module=self.module();incoming=self.incoming();old,names=unpack_narc(incoming)
        result,resultnames=unpack_narc(module.modern_soul_dew_message_resources(incoming,CHARMAP))
        self.assertEqual(resultnames,names);self.assertEqual(len(result),len(old))
        self.assertEqual(result[:221],old[:221]);self.assertEqual(result[222:],old[222:])
        before,key=unpack_messages(old[221]);after,newkey=unpack_messages(result[221])
        self.assertEqual((len(after),newkey),(537,24316));self.assertEqual(key,newkey)
        self.assertEqual({i for i in range(537) if before[i]!=after[i]},{225})
        self.assertEqual(after[225],game_text(TEXT,CHARMAP));self.assertEqual(len(TEXT),63)
        font=(ROOT/'files/graphic/font/font_00000000.bin').read_bytes();offset=struct.unpack_from('<I',font,4)[0]
        widths=[sum(font[offset+glyph-1] for glyph in game_text(line,CHARMAP)[:-1]) for line in TEXT.splitlines()]
        self.assertEqual(widths,[137,137,73]);self.assertLessEqual(max(widths),149);self.assertLess(len(after[225]),130)
        self.assertIn('NARC_msg_msg_0221_bin', (ROOT/'src/item.c').read_text())

    def test_rejects_pre_snow_duplicate_missing_and_every_bank_drift(self):
        module=self.module();incoming=self.incoming();banks,names=unpack_narc(incoming)
        for archive in (self.original(),pack_narc(banks[:221]),module.modern_soul_dew_message_resources(incoming,CHARMAP)):
            with self.subTest(size=len(archive)),self.assertRaises(ValueError):module.modern_soul_dew_message_resources(archive,CHARMAP)
        original,key=unpack_messages(banks[221])
        for row in (0,225,282,334,536):
            words=[list(w) for w in original];words[row]=game_text('drift',CHARMAP)
            corrupt=list(banks);corrupt[221]=pack_messages(words,key)
            with self.subTest(row=row),self.assertRaisesRegex(ValueError,'post-Snow'):
                module.modern_soul_dew_message_resources(pack_narc(corrupt,names),CHARMAP)
        for words,otherkey in ((original,key+1),(original[:-1],key),(original+[original[0]],key)):
            corrupt=list(banks);corrupt[221]=pack_messages(words,otherkey)
            with self.assertRaises(ValueError):module.modern_soul_dew_message_resources(pack_narc(corrupt,names),CHARMAP)
        original_read=Path.read_bytes
        def drift(path,*args,**kwargs):
            data=original_read(path,*args,**kwargs)
            return data+b'\n' if path.name=='msg_0221.gmm' else data
        with patch.object(Path,'read_bytes',drift),self.assertRaisesRegex(ValueError,'source'):
            module.modern_soul_dew_message_resources(incoming,CHARMAP)
        self.assertEqual(hashlib.sha256((ROOT/'files/msgdata/msg/msg_0221.gmm').read_bytes()).hexdigest(),'72a2c890304ebcab65f70d487423e402572301ec208936888061db5ff137748d')

    def test_real_message_pipeline_all_eight_flags_after_snow_before_moves(self):
        module=self.module()
        import modern_rom
        from move_resources import read_entries
        originals={'a/0/2/7':self.original(),'a/0/1/1':(ROOT/'files/poketool/waza/waza_tbl.narc').read_bytes(),
                   'a/0/0/0':(ROOT/'files/battledata/script/move_script.narc').read_bytes()}
        for path in ('a/0/0/8','a/0/6/8','a/0/0/1','a/0/3/0'):originals[path]=b'untouched'
        rom=b'';paths={}
        for i,(path,data) in enumerate(originals.items()):paths[path]=(i,len(rom),len(rom)+len(data));rom+=data
        scripts=('modern_battle_resources','modern_paralysis_resources','modern_weather_resources','modern_absorption_resources',
                 'modern_sturdy_resources','modern_cursed_body_resources','modern_competitive_resources','modern_oblivious_intimidate_resources',
                 'modern_simple_resources','modern_snow_effect_resources','modern_drain_resources','modern_move_stat_resources','modern_move_effect_resources')
        for types,battle,moves in itertools.product((False,True),repeat=3):
            with self.subTest(types=types,battle=battle,moves=moves),ExitStack() as stack:
                stack.enter_context(patch('modern_rom.rom_files',return_value=paths))
                stack.enter_context(patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:replacements))
                stack.enter_context(patch('modern_rom.modern_type_resources',side_effect=lambda icons,messages,charmap:(icons,messages)))
                stack.enter_context(patch('modern_rom.modern_pokedex_resources',side_effect=lambda data:data))
                for name in scripts:stack.enter_context(patch('modern_rom.'+name,side_effect=lambda data,*args:data))
                owner=stack.enter_context(patch('modern_rom.modern_soul_dew_message_resources',wraps=module.modern_soul_dew_message_resources))
                output=modern_rom.make_modern_rom(rom,CHARMAP,types=types,battle_rules=battle,moves=moves)
                self.assertEqual(owner.call_count,int(battle))
                after=unpack_narc(output.get('a/0/2/7',originals['a/0/2/7']))[0]
                old=unpack_narc(originals['a/0/2/7'])[0]
                words=unpack_messages(after[221])[0]
                self.assertEqual(words[225],game_text(TEXT,CHARMAP) if battle else unpack_messages(old[221])[0][225])
                self.assertEqual(len(unpack_messages(after[720])[0]),243 if battle else 124)
                if battle:
                    before=unpack_messages(unpack_narc(self.incoming())[0][221])[0]
                    self.assertEqual(words[282],before[282]);self.assertEqual(words[334],before[334])


if __name__=='__main__':unittest.main()
