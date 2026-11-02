"""Parity and control-flow checks for the generated modern paralysis subscript."""
import importlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'files/battledata/script/subscript/subscript_0031_Paralyze.s'


class ModernStatusSourceTests(unittest.TestCase):
    def test_current_target_types_are_checked_after_existing_paralysis(self):
        self.assertIsNotNone(importlib.util.find_spec('battle_scripts'),
                             'modern paralysis source transform is missing')
        scripts = importlib.import_module('battle_scripts')
        original = SOURCE.read_text()
        result = scripts.modern_paralysis_source(original)
        old_check = '    CompareMonDataToValue OPCODE_FLAG_SET, BATTLER_CATEGORY_SIDE_EFFECT_MON, BMON_DATA_STATUS, STATUS_PARALYSIS, _139\n'
        new_checks = ''.join(
            f'    CompareMonDataToValue OPCODE_EQU, BATTLER_CATEGORY_SIDE_EFFECT_MON, BMON_DATA_TYPE_{slot}, TYPE_ELECTRIC, _QolElectricImmune\n'
            for slot in (1, 2))
        self.assertIn(old_check + new_checks + '    CompareMonDataToValue OPCODE_NEQ', result)
        self.assertIn('    GoTo _211\n\n_QolElectricImmune:\n    CompareVarToValue OPCODE_EQU, BSCRIPT_VAR_SIDE_EFFECT_TYPE, SIDE_EFFECT_TYPE_INDIRECT, _218\n', result)
        self.assertEqual(result.replace(new_checks, '').replace('\n_QolElectricImmune:\n', ''), original)

    def test_source_transform_rejects_missing_duplicate_and_already_modern_anchors(self):
        scripts = importlib.import_module('battle_scripts')
        original = SOURCE.read_text()
        anchors = (
            '    CompareMonDataToValue OPCODE_FLAG_SET, BATTLER_CATEGORY_SIDE_EFFECT_MON, BMON_DATA_STATUS, STATUS_PARALYSIS, _139\n',
            '    GoTo _211\n    CompareVarToValue OPCODE_EQU, BSCRIPT_VAR_SIDE_EFFECT_TYPE, SIDE_EFFECT_TYPE_INDIRECT, _218\n',
        )
        for anchor in anchors:
            for changed in (original.replace(anchor, '', 1), original + anchor):
                with self.subTest(anchor=anchor, changed=changed[-40:]):
                    with self.assertRaisesRegex(ValueError, 'expected source'):
                        scripts.modern_paralysis_source(changed)
        with self.assertRaises(ValueError):
            scripts.modern_paralysis_source(scripts.modern_paralysis_source(original))

    def test_source_transform_rejects_drift_in_priority_or_failure_message(self):
        scripts = importlib.import_module('battle_scripts')
        original = SOURCE.read_text()
        for before, after in (
            ('BMON_DATA_STATUS, STATUS_NONE, _123', 'BMON_DATA_STATUS, STATUS_NONE, _139'),
            ('PrintMessage msg_0197_00027,', 'PrintMessage msg_0197_00133,'),
        ):
            with self.subTest(before=before):
                with self.assertRaises(ValueError):
                    scripts.modern_paralysis_source(original.replace(before, after))

    def test_compiler_profile_mismatch_rejects_before_compiling_modern_source(self):
        from unittest.mock import patch
        scripts = importlib.import_module('battle_scripts')
        with patch.object(scripts, 'compile_battle_script', return_value=b'wrong profile') as compile_script:
            with self.assertRaisesRegex(ValueError, 'unchanged.*match'):
                scripts.modern_paralysis_script(b'original')
        self.assertEqual(compile_script.call_count, 1)
        self.assertEqual(compile_script.call_args.args[0], SOURCE.read_text())

    def test_paralysis_archive_replaces_only_member_31_and_preserves_names(self):
        from unittest.mock import patch
        import modern_rom
        import nitro_data as nitro
        members = [bytes([i]) * 4 for i in range(40)]
        archive = nitro.pack_narc(members)
        names = nitro.unpack_narc(archive)[1]
        with patch('modern_rom.modern_paralysis_script', return_value=b'compiled modern') as compile_script:
            result, actual_names = nitro.unpack_narc(modern_rom.modern_paralysis_resources(archive))
        compile_script.assert_called_once_with(members[31])
        self.assertEqual(actual_names, names)
        self.assertEqual(result[:31], members[:31])
        self.assertEqual(result[31], b'compiled modern')
        self.assertEqual(result[32:], members[32:])
        with self.assertRaises(ValueError):
            modern_rom.modern_paralysis_resources(nitro.pack_narc(members[:31]))

    def test_default_and_type_only_rom_paths_do_not_compile_battle_scripts(self):
        from unittest.mock import patch
        import modern_rom
        paths = {path: (0, 0, 3) for path in ('a/0/0/8', 'a/0/2/7', 'a/0/6/8')}
        for types in (False, True):
            with self.subTest(types=types), patch('modern_rom.rom_files', return_value=paths), patch('modern_rom.modern_type_resources', return_value=(b'icons', b'messages')), patch('modern_rom.modern_pokedex_resources', return_value=b'dex'), patch('modern_rom.replace_rom_files', side_effect=lambda rom, replacements: rom), patch('modern_rom.modern_paralysis_script') as compile_script:
                self.assertEqual(modern_rom.make_modern_rom(b'rom', None, types=types), b'rom')
            compile_script.assert_not_called()

    def test_battle_rules_always_applies_paralysis_after_numeric_changes(self):
        from unittest.mock import patch
        import modern_rom
        with patch('modern_rom.rom_files', return_value={'a/0/0/1': (0, 0, 3), 'a/0/2/7': (1, 0, 3), 'a/0/3/0': (2, 0, 3)}), patch('modern_rom.modern_battle_resources', return_value=b'numeric') as numeric, patch('modern_rom.modern_paralysis_resources', return_value=b'electric') as electric, patch('modern_rom.modern_weather_resources', return_value=b'finite') as weather, patch('modern_rom.modern_absorption_resources',side_effect=lambda data:data), patch('modern_rom.modern_sturdy_resources',side_effect=lambda data:data), patch('modern_rom.modern_cursed_body_resources',side_effect=lambda data:data), patch('modern_rom.modern_competitive_resources',side_effect=lambda data:data), patch('modern_rom.modern_oblivious_intimidate_resources',side_effect=lambda data:data), patch('modern_rom.modern_simple_resources',side_effect=lambda data:data), patch('modern_rom.modern_simple_message_resources',side_effect=lambda data,charmap:data), patch('modern_rom.modern_snow_message_resources',side_effect=lambda data,charmap:data), patch('modern_rom.modern_soul_dew_message_resources',side_effect=lambda data,charmap:data), patch('modern_rom.modern_snow_effect_resources',return_value=b'snow'), patch('modern_rom.modern_ability_description_resources',return_value=b'abilities'), patch('modern_rom.replace_rom_files', side_effect=lambda rom, replacements: replacements):
            result = modern_rom.make_modern_rom(b'rom', None, types=False, battle_rules=True)
        numeric.assert_called_once_with(b'rom')
        electric.assert_called_once_with(b'numeric')
        weather.assert_called_once_with(b'electric')
        self.assertEqual(result, {'a/0/0/1': b'finite', 'a/0/2/7': b'abilities', 'a/0/3/0': b'snow'})


class ModernStatusSdkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import battle_scripts as scripts
        import nitro_data as nitro
        try:
            scripts.battle_script_tools()
        except FileNotFoundError as error:
            raise unittest.SkipTest(str(error))
        archive = ROOT / 'files/battledata/script/subscript.narc'
        if not archive.is_file():
            raise unittest.SkipTest('original battle subscript archive is absent')
        cls.original = nitro.unpack_narc(archive.read_bytes())[0][31]
        cls.unchanged = scripts.compile_battle_script(SOURCE.read_text())
        cls.modern = scripts.modern_paralysis_script(cls.original)

    def test_unchanged_sdk_compilation_matches_original_narc_bytes(self):
        self.assertEqual(self.unchanged, self.original)
        self.assertEqual(len(self.modern), len(self.original) + 48)

    def test_every_original_command_and_relative_jump_survives_relocation(self):
        import struct
        def decode(binary):
            words = struct.unpack('<' + 'i' * (len(binary) // 4), binary)
            lengths = {14: 1, 17: 1, 23: 2, 30: 2, 32: 5, 33: 6,
                       50: 4, 52: 5, 59: 2, 60: 2, 66: 3, 69: 3,
                       161: 5, 210: 3, 211: 2, 224: 1}
            commands = []
            offset = 0
            while offset < len(words):
                opcode = words[offset]
                if opcode == 18:
                    tag = words[offset + 2]
                    size = 3 + (tag > 0) + (tag > 8) + (tag > 30) + (tag > 51)
                else:
                    size = lengths[opcode]
                commands.append((offset, words[offset:offset + size]))
                offset += size
            self.assertEqual(offset, len(words))
            return commands
        original, modern = map(decode, (self.original, self.modern))
        inserted = [offset for offset, command in modern
                    if command[:5] in ((33, 0, 7, 27, 13), (33, 0, 7, 28, 13))]
        self.assertEqual(len(inserted), 2)
        def normalize(commands, omitted):
            indices = {offset: i for i, (offset, command) in enumerate(
                (item for item in commands if item[0] not in omitted))}
            result = []
            for offset, command in commands:
                if command[0] in (32, 33, 59, 161, 210, 211):
                    target = offset + len(command) + command[-1]
                    self.assertIn(target, indices, 'branch must reach a command boundary')
                    if offset not in omitted:
                        command = (*command[:-1], ('jump', indices[target]))
                if offset not in omitted:
                    result.append(command)
            return result
        self.assertEqual(normalize(original, ()), normalize(modern, inserted))
        by_offset = dict(modern)
        targets = [offset + len(by_offset[offset]) + by_offset[offset][-1] for offset in inserted]
        self.assertEqual(targets[0], targets[1])
        self.assertEqual(by_offset[targets[0]][:4], (32, 0, 5, 2))

    def test_compiled_control_flow_and_real_commands_preserve_old_paths(self):
        import struct
        import test_game_logic as game
        def array(data):
            return ','.join(str(word) + 'u' for word in struct.unpack('<' + 'I' * (len(data) // 4), data))
        declarations = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "constants/battle.h"
#include "constants/battle_script.h"
#include "constants/abilities.h"
#include "constants/pokemon.h"
#include "constants/opcode.h"
#include "constants/message_tags.h"
typedef int BOOL; typedef uint32_t u32;
#define FALSE 0
#define TRUE 1
#define GF_ASSERT(x) assert(x)
typedef struct {int unused;} BattleSystem;
typedef struct {int status,status2,hp,type1,type2;} BattleMon;
typedef struct {int statusFlags;} SelfTurn;
typedef struct {
 const u32 *words; int pos,length,vars[70],ability,ignored,message,failed,tempData;
 int battlerIdAttacker,battlerIdAbility,turnOrder[4],moveNoCur,statChangeType;
 BattleMon battleMons[4]; SelfTurn selfTurnData[4];
} BattleContext;
void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;assert(c->pos>=0 && c->pos<=c->length);}
int BattleScriptReadWord(BattleContext *c){assert(c->pos<c->length);return c->words[c->pos++];}
int *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int v){assert(v>=0&&v<70);return &c->vars[v];}
int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){assert(side==BATTLER_CATEGORY_SIDE_EFFECT_MON);return 0;}
int BattleSystem_GetMaxBattlers(BattleSystem *s){return 1;}
int GetBattlerVar(BattleContext *c,int id,int field,void *unused){
 assert(id==0);switch(field){case BMON_DATA_STATUS:return c->battleMons[id].status;
 case BMON_DATA_TYPE_1:return c->battleMons[id].type1;case BMON_DATA_TYPE_2:return c->battleMons[id].type2;default:assert(0);return 0;}}
void SetBattlerVar(BattleContext *c,int id,int field,int *value){assert(id==0&&field==BMON_DATA_STATUS);c->battleMons[id].status=*value;}
void BattlerSetAbility(BattleContext *c,int id,int value){assert(0);}
void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int id){}
int GetBattlerAbility(BattleContext *c,int id){return c->ability;}
int CheckBattlerAbilityIfNotIgnored(BattleContext *c,int attacker,int target,int ability){return !c->ignored&&c->ability==ability;}
int CheckAbilityActive(BattleSystem *s,BattleContext *c,int mode,int battler,int ability){return 0;}
int MaskOfFlagNo(int n){return 1u<<n;}
// These paralysis control-flow fixtures use a nonsound move. Sound/Substitute
// behavior runs the real helper and command in test_modern_substitute.py.
int Qol_MoveBypassesSubstitute(int move){return FALSE;}
'''
        functions = game.function_source('src/battle/battle_util.c','Qol_GetActualStatStageDelta')+'\n'+'\n'.join(game.function_source('src/battle/battle_command.c', name) for name in (
            'BtlCmd_CompareVarToValue', 'BtlCmd_CompareMonDataToValue',
            'BtlCmd_CheckIgnorableAbility', 'BtlCmd_CheckSubstitute',
            'BtlCmd_CheckIgnoreWeather', 'BtlCmd_Goto', 'BtlCmd_UpdateVar', 'BtlCmd_UpdateMonData'))
        checks = r'''
static const u32 original[]={ORIGINAL};
static const u32 modern[]={MODERN};
static void run(BattleContext *c,const u32 *script,int length){
 BattleSystem s={0};c->words=script;c->length=length;c->pos=0;c->message=0;c->failed=0;
 for(int steps=0;steps<200;steps++){
  assert(c->pos<length);
  switch(script[c->pos]){
  case 14:case 17:c->pos++;break;
  case 18:{c->pos++;c->message=BattleScriptReadWord(c);int tag=BattleScriptReadWord(c);
   int count=(tag>0)+(tag>TAG_TRNAME)+(tag>TAG_TRCLASS_TRNAME)+(tag>TAG_TRCLASS_TRNAME_ITEM);
   c->pos+=count;break;}
  case 23:case 30:c->pos+=2;break;
  case 32:BtlCmd_CompareVarToValue(&s,c);break;
  case 33:BtlCmd_CompareMonDataToValue(&s,c);break;
  case 50:BtlCmd_UpdateVar(&s,c);break;
  case 52:BtlCmd_UpdateMonData(&s,c);break;
  case 59:BtlCmd_Goto(&s,c);break;
  case 60:c->failed++;c->pos+=2;break;
  case 66:case 69:c->pos+=3;break;
  case 161:BtlCmd_CheckIgnorableAbility(&s,c);break;
  case 210:BtlCmd_CheckSubstitute(&s,c);break;
  case 211:BtlCmd_CheckIgnoreWeather(&s,c);break;
  case 224:return;
  default:assert(0);
  }
 }
 assert(0);
}
static BattleContext fixture(int t1,int t2,int effect,int status,int ability,int flags){
 BattleContext c={0};c.battleMons[0]=(BattleMon){status,(flags&1)?(1<<24):0,100,t1,t2};
 // Nuzzle uses the indirect paralysis script and never bypasses Substitute.
 c.moveNoCur=612;c.statChangeType=effect;
 c.ability=ability;c.ignored=!!(flags&16);
 c.vars[BSCRIPT_VAR_SIDE_EFFECT_TYPE]=effect;
 c.vars[BSCRIPT_VAR_SIDE_CONDITION_STAT_CHANGE]=(flags&2)?SIDE_CONDITION_SAFEGUARD:0;
 c.vars[BSCRIPT_VAR_MOVE_STATUS_FLAGS]=(flags&4)?MOVE_STATUS_MISSED:0;
 c.vars[BSCRIPT_VAR_FIELD_CONDITION]=(flags&8)?FIELD_CONDITION_SUN_ALL:0;
 return c;
}
static BattleContext execute(BattleContext c,int updated){
 run(&c,updated?modern:original,updated?sizeof(modern)/4:sizeof(original)/4);return c;
}
static void same(BattleContext a,BattleContext b){
 assert(a.battleMons[0].status==b.battleMons[0].status);
 assert(a.message==b.message&&a.failed==b.failed&&a.battlerIdAbility==b.battlerIdAbility);
 assert(memcmp(a.vars,b.vars,sizeof(a.vars))==0);
}
int main(void){
 int statuses[]={STATUS_NONE,STATUS_PARALYSIS,STATUS_BURN};
 int abilities[]={ABILITY_NONE,ABILITY_LIMBER,ABILITY_LEAF_GUARD,ABILITY_SHIELD_DUST};
 // Every pair of original type IDs, including the old mystery slot. The C
 // command reads CURRENT battler fields, with no species or party type lookup.
 for(int t1=0;t1<18;t1++)for(int t2=0;t2<18;t2++)for(int effect=1;effect<=3;effect++){
  BattleContext base=fixture(t1,t2,effect,STATUS_NONE,ABILITY_NONE,0);
  BattleContext a=execute(base,0),b=execute(base,1);
  if(t1==TYPE_ELECTRIC||t2==TYPE_ELECTRIC){
   assert(b.battleMons[0].status==STATUS_NONE);
   assert(b.message==(effect==SIDE_EFFECT_TYPE_INDIRECT?0:27));
   assert(b.failed==0);
   assert(!!((u32)b.vars[BSCRIPT_VAR_MOVE_STATUS_FLAGS]&MOVE_STATUS_NO_MORE_WORK)==(effect!=SIDE_EFFECT_TYPE_INDIRECT));
  }else same(a,b);
 }
 for(int status=0;status<3;status++)for(int ability=0;ability<4;ability++)
 for(int flags=0;flags<32;flags++)for(int effect=1;effect<=3;effect++){
  BattleContext base=fixture(TYPE_NORMAL,TYPE_WATER,effect,statuses[status],abilities[ability],flags);
  same(execute(base,0),execute(base,1));
  // Ability and Substitute checks still precede the new type checks.
  base.battleMons[0].type2=TYPE_ELECTRIC;
  BattleContext a=execute(base,0),b=execute(base,1);
  int abilityBlocks=!(flags&16)&&(abilities[ability]==ABILITY_LIMBER||
    (abilities[ability]==ABILITY_LEAF_GUARD&&(flags&8))||
    (abilities[ability]==ABILITY_SHIELD_DUST&&effect==SIDE_EFFECT_TYPE_INDIRECT));
  int substituteBlocks=(flags&1)&&effect!=SIDE_EFFECT_TYPE_ABILITY;
  if(abilityBlocks||substituteBlocks||statuses[status]==STATUS_PARALYSIS) same(a,b);
  else {
   assert(b.battleMons[0].status==statuses[status]);
   assert(b.message==(effect==SIDE_EFFECT_TYPE_INDIRECT?0:27));assert(b.failed==0);
  }
 }
 return 0;
}
'''.replace('ORIGINAL', array(self.original)).replace('MODERN', array(self.modern))
        game.GameLogicTests.compile_run(self, declarations + functions + checks)
