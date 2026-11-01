"""Finite ability weather: source parity, real bytecode and normal C commands."""
import importlib
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
WEATHER = {
    183: ('Drizzle', 'RAIN', 'RAIN'),
    184: ('SandStream', 'SANDSTORM', 'SANDSTORM'),
    185: ('Drought', 'SUN', 'SUN'),
    252: ('SnowWarning', 'HAIL', 'HAIL'),
}


def source_path(member):
    return ROOT / f'files/battledata/script/subscript/subscript_{member:04}_{WEATHER[member][0]}.s'


def transform(test, source, member):
    scripts = importlib.import_module('battle_scripts')
    test.assertTrue(callable(getattr(scripts, 'modern_weather_source', None)),
                    'finite ability-weather source transform is missing')
    return scripts.modern_weather_source(source, member)


class ModernWeatherSourceTests(unittest.TestCase):
    def test_weather_is_temporary_with_matching_source_rock_and_preserved_presentation(self):
        for member, (_, flag, rock) in WEATHER.items():
            with self.subTest(member=member):
                source = source_path(member).read_text()
                modern = transform(self, source, member)
                prefix = source[:source.index('    UpdateVar OPCODE_FLAG_OFF')]
                self.assertTrue(modern.startswith(prefix))
                self.assertIn(f'OPCODE_FLAG_ON, BSCRIPT_VAR_FIELD_CONDITION, FIELD_CONDITION_{flag}\n', modern)
                self.assertNotIn(f'FIELD_CONDITION_{flag}_PERMANENT', modern)
                self.assertIn('UpdateVar OPCODE_SET, BSCRIPT_VAR_WEATHER_TURNS, 5', modern)
                self.assertIn('UpdateVar OPCODE_SET, BSCRIPT_VAR_WEATHER_TURNS, 8', modern)
                self.assertIn(f'CheckItemHoldEffect CHECK_OPCODE_NOT_HAVE, BATTLER_CATEGORY_MSG_BATTLER_TEMP, HOLD_EFFECT_EXTEND_{rock}, _QolWeatherEnd', modern)

    def test_full_source_drift_wrong_member_and_double_transform_are_rejected(self):
        for member in WEATHER:
            source = source_path(member).read_text()
            for changed in (source + '\n', source.replace('WaitButtonABTime 30', 'WaitButtonABTime 31'),
                            source.replace('FIELD_CONDITION_WEATHER', 'FIELD_CONDITION_FOG'),
                            source.replace('TAG_NICKNAME_ABILITY', 'TAG_NICKNAME'),
                            transform(self, source, member)):
                with self.subTest(member=member), self.assertRaisesRegex(ValueError, 'expected source'):
                    transform(self, changed, member)
            other = next(i for i in WEATHER if i != member)
            with self.assertRaisesRegex(ValueError, 'expected source'):
                transform(self, source, other)
        with self.assertRaises(ValueError):
            transform(self, source, 31)

    def test_original_narc_parity_precedes_transformed_compilation(self):
        import battle_scripts as scripts
        self.assertTrue(callable(getattr(scripts, 'modern_weather_script', None)), 'weather compiler is missing')
        for member in WEATHER:
            with self.subTest(member=member), patch.object(scripts, 'compile_battle_script', return_value=b'wrong') as compiler:
                with self.assertRaisesRegex(ValueError, f'unchanged.*match.*{member}'):
                    scripts.modern_weather_script(b'original', member)
                compiler.assert_called_once_with(source_path(member).read_text(), scripts.ROOT)
            with patch.object(scripts, 'compile_battle_script', side_effect=[b'original', b'modern']) as compiler:
                self.assertEqual(scripts.modern_weather_script(b'original', member), b'modern')
                self.assertEqual([c.args[0] for c in compiler.call_args_list],
                                 [source_path(member).read_text(), transform(self, source_path(member).read_text(), member)])

    def test_archive_changes_only_four_ability_members_and_preserves_names(self):
        import modern_rom
        from nitro_data import pack_narc, unpack_narc
        self.assertTrue(callable(getattr(modern_rom, 'modern_weather_resources', None)), 'weather archive transform is missing')
        members = [struct.pack('<I', n) for n in range(300)]
        archive = pack_narc(members)
        with patch('modern_rom.modern_weather_script', side_effect=lambda data, member: b'new' + data) as compiler:
            actual, names = unpack_narc(modern_rom.modern_weather_resources(archive))
        self.assertEqual(names, unpack_narc(archive)[1])
        self.assertEqual(compiler.call_count, 4)
        for i, before in enumerate(members):
            self.assertEqual(actual[i], b'new' + before if i in WEATHER else before)
        with self.assertRaisesRegex(ValueError, 'absent'):
            modern_rom.modern_weather_resources(pack_narc(members[:252]))

    def test_battle_rules_always_applies_weather_after_numeric_and_paralysis(self):
        import modern_rom
        self.assertTrue(callable(getattr(modern_rom, 'modern_weather_resources', None)), 'weather ROM integration is missing')
        with patch('modern_rom.rom_files', return_value={'a/0/0/1': (0, 0, 3), 'a/0/2/7': (1, 0, 3), 'a/0/3/0': (2, 0, 3)}), \
             patch('modern_rom.modern_battle_resources', return_value=b'numeric') as numeric, \
             patch('modern_rom.modern_paralysis_resources', return_value=b'electric') as electric, \
             patch('modern_rom.modern_weather_resources', return_value=b'finite') as weather, \
             patch('modern_rom.modern_absorption_resources', side_effect=lambda data:data), \
             patch('modern_rom.modern_sturdy_resources',side_effect=lambda data:data), patch('modern_rom.modern_cursed_body_resources',side_effect=lambda data:data), patch('modern_rom.modern_competitive_resources',side_effect=lambda data:data), patch('modern_rom.modern_oblivious_intimidate_resources',side_effect=lambda data:data), patch('modern_rom.modern_simple_resources',side_effect=lambda data:data), patch('modern_rom.modern_simple_message_resources',side_effect=lambda data,charmap:data), patch('modern_rom.modern_snow_message_resources',side_effect=lambda data,charmap:data), patch('modern_rom.modern_snow_effect_resources',return_value=b'snow'), \
             patch('modern_rom.modern_ability_description_resources',return_value=b'abilities'), \
             patch('modern_rom.replace_rom_files', side_effect=lambda rom, replacements: replacements):
            result = modern_rom.make_modern_rom(b'rom', None, types=False, battle_rules=True)
        numeric.assert_called_once_with(b'rom')
        electric.assert_called_once_with(b'numeric')
        weather.assert_called_once_with(b'electric')
        self.assertEqual(result, {'a/0/0/1': b'finite', 'a/0/2/7': b'abilities', 'a/0/3/0': b'snow'})

    def test_default_and_type_only_rom_paths_do_not_transform_weather(self):
        import modern_rom
        self.assertTrue(callable(getattr(modern_rom, 'modern_weather_resources', None)), 'weather ROM integration is missing')
        paths = {path: (0, 0, 3) for path in ('a/0/0/8', 'a/0/2/7', 'a/0/6/8')}
        for types in (False, True):
            with self.subTest(types=types), \
                 patch('modern_rom.rom_files', return_value=paths), \
                 patch('modern_rom.modern_type_resources', return_value=(b'icons', b'messages')), \
                 patch('modern_rom.modern_pokedex_resources', return_value=b'dex'), \
                 patch('modern_rom.modern_weather_resources') as weather, \
                 patch('modern_rom.replace_rom_files', side_effect=lambda rom, replacements: rom):
                self.assertEqual(modern_rom.make_modern_rom(b'rom', None, types=types), b'rom')
            weather.assert_not_called()

    def test_real_sendout_branch_uses_all_weather_only_when_enabled(self):
        import test_game_logic as game
        source = (ROOT / 'src/battle/battle_util.c').read_text()
        branch = source[source.index('        case 2: // Weather from abilities'):source.index('        case 3: // Intimidate')]
        declarations = r'''
#include <assert.h>
#include "constants/abilities.h"
#include "constants/battle.h"
#include "constants/battle_subscript.h"
#define TRUE 1
#define FALSE 0
typedef struct {int hp,sendOutFlag,ability;} BattleMon;
typedef struct {BattleMon battleMons[4];int turnOrder[4],fieldCondition,battlerIdTemp,sendOutState;} BattleContext;
int GetBattlerAbility(BattleContext *ctx,int id){return ctx->battleMons[id].ability;}
int weather(BattleContext *ctx){int i,battlerId,script=0,flag=FALSE,maxBattlers=4;switch(2){
'''
        checks = r'''
}return script;}
int main(void){
 int abilities[]={ABILITY_DRIZZLE,ABILITY_SAND_STREAM,ABILITY_DROUGHT,ABILITY_SNOW_WARNING};
 int flags[]={FIELD_CONDITION_RAIN,FIELD_CONDITION_SANDSTORM,FIELD_CONDITION_SUN,FIELD_CONDITION_HAIL};
 int scripts[]={183,184,185,252};
 for(int w=0;w<4;w++)for(int holder=0;holder<4;holder++)for(int condition=0;condition<256;condition++){
  BattleContext c={0};for(int i=0;i<4;i++){c.turnOrder[i]=3-i;c.battleMons[i].hp=1;}
  c.battleMons[holder].ability=abilities[w];c.fieldCondition=condition;c.battlerIdTemp=-1;
  int mask=flags[w]*2;
#if QOL_MODERN_BATTLE
  mask|=flags[w];
#endif
  int expected=(condition&mask)?0:scripts[w];
  assert(weather(&c)==expected);assert(c.battleMons[holder].sendOutFlag==TRUE);
  if(expected)assert(c.battlerIdTemp==holder);else assert(c.battlerIdTemp==-1);
  assert(c.fieldCondition==condition);assert(weather(&c)==0);
 }
 // Fainted sources do not start weather.
 BattleContext c={0};c.battleMons[0].ability=ABILITY_DRIZZLE;
 assert(weather(&c)==0);assert(c.battleMons[0].sendOutFlag==0);
 return 0;
}
'''
        for flag in (0, 1):
            with self.subTest(flag=flag):
                game.GameLogicTests.compile_run(self, declarations + branch + checks, f'-DQOL_MODERN_BATTLE={flag}')


class ModernWeatherSdkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import battle_scripts as scripts
        from nitro_data import unpack_narc
        if not callable(getattr(scripts, 'modern_weather_script', None)):
            raise unittest.SkipTest('weather compiler not implemented yet')
        try:
            scripts.battle_script_tools()
        except FileNotFoundError as error:
            raise unittest.SkipTest(str(error))
        archive = ROOT / 'files/battledata/script/subscript.narc'
        if not archive.exists():
            raise unittest.SkipTest('original subscript archive is absent')
        cls.members = unpack_narc(archive.read_bytes())[0]
        cls.unchanged = {i: scripts.compile_battle_script(source_path(i).read_text()) for i in WEATHER}
        cls.modern = {i: scripts.modern_weather_script(cls.members[i], i) for i in WEATHER}

    def test_all_four_original_sources_compile_to_exact_narc_bytes(self):
        for member in WEATHER:
            with self.subTest(member=member):
                self.assertEqual(self.unchanged[member], self.members[member])
                self.assertGreater(len(self.modern[member]), len(self.members[member]))

    def test_real_commands_use_source_rock_suppression_and_existing_expiration(self):
        import test_game_logic as game
        def array(data):
            return ','.join(f'{word}u' for word in struct.unpack('<' + 'I' * (len(data)//4), data))
        declarations = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include "constants/abilities.h"
#include "constants/battle.h"
#include "constants/battle_script.h"
#include "constants/battle_subscript.h"
#include "constants/items.h"
#include "constants/opcode.h"
#include "constants/message_tags.h"
#include "msg_0197.h"
typedef int BOOL;typedef uint32_t u32;typedef uint16_t u16;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT(x) assert(x)
enum {UFC_STATE_RAIN,UFC_STATE_SANDSTORM,UFC_STATE_SUN,UFC_STATE_HAIL};
enum {NARC_a_0_0_1=1};
typedef struct {int unused;} BattleSystem;
typedef struct {int item,ability;struct {int embargoFlag;} moveEffectData;} BattleMon;
typedef struct {const u32 *words;int pos,length,fieldCondition,battlerIdTemp,readScript;
 struct {int weatherTurns;} fieldConditionData;BattleMon battleMons[4];
 struct {int id,tag;} buffMsg;int commandNext,command,tempData,stateFieldConditionUpdate;
} BattleContext;
void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;assert(c->pos>=0&&c->pos<=c->length);}
int BattleScriptReadWord(BattleContext *c){assert(c->pos<c->length);return c->words[c->pos++];}
int *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int v){
 if(v==BSCRIPT_VAR_FIELD_CONDITION)return &c->fieldCondition;
 assert(v==BSCRIPT_VAR_WEATHER_TURNS);return &c->fieldConditionData.weatherTurns;}
int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){
 assert(side==BATTLER_CATEGORY_MSG_BATTLER_TEMP);return c->battlerIdTemp;}
int GetBattlerAbility(BattleContext *c,int id){return c->battleMons[id].ability;}
int GetItemVar(BattleContext *c,u16 item,int field){assert(field==ITEM_VAR_HOLD_EFFECT);
 switch(item){case ITEM_DAMP_ROCK:return HOLD_EFFECT_EXTEND_RAIN;
 case ITEM_SMOOTH_ROCK:return HOLD_EFFECT_EXTEND_SANDSTORM;
 case ITEM_HEAT_ROCK:return HOLD_EFFECT_EXTEND_SUN;
 case ITEM_ICY_ROCK:return HOLD_EFFECT_EXTEND_HAIL;default:return HOLD_EFFECT_NONE;}}
int MaskOfFlagNo(int n){return 1u<<n;}
void ReadBattleScriptFromNarc(BattleContext *c,int narc,int script){assert(narc==1);c->readScript=script;}
'''
        functions = '\n'.join(game.function_source('src/battle/battle_util.c', n) for n in ('GetBattlerHeldItem', 'GetBattlerHeldItemEffect'))
        functions += '\n' + '\n'.join(game.function_source('src/battle/battle_command.c', n) for n in ('BtlCmd_UpdateVar', 'BtlCmd_CheckItemHoldEffect'))
        controller = (ROOT / 'src/battle/battle_controller_player.c').read_text()
        fragment = controller[controller.index('        case UFC_STATE_RAIN:'):controller.index('        case UFC_STATE_FOG:')]
        functions += '\nstatic void end_turn(BattleSystem *battleSystem,BattleContext *ctx,int state){int flag=0;switch(state){\n' + fragment + '\n}assert(flag==1);}\n'
        arrays = []
        for w, member in enumerate(WEATHER):
            for name, data in (('old', self.members[member]), ('modern', self.modern[member]), ('end', self.members[234+w])):
                arrays.append(f'static const u32 {name}{w}[]={{ {array(data)} }};')
        checks = r'''
static void execute(BattleContext *c,const u32 *script,int length){
 BattleSystem s={0};c->words=script;c->length=length;c->pos=0;
 for(int steps=0;steps<100;steps++){
  assert(c->pos<c->length);
  switch(c->words[c->pos]){
  case 14:c->pos++;break;
  case 18:{c->pos++;BattleScriptReadWord(c);int tag=BattleScriptReadWord(c);
   c->pos+=(tag>0)+(tag>TAG_TRNAME)+(tag>TAG_TRCLASS_TRNAME)+(tag>TAG_TRCLASS_TRNAME_ITEM);break;}
  case 30:c->pos+=2;break;
  case 50:BtlCmd_UpdateVar(&s,c);break;
  case 69:c->pos+=3;break;
  case 166:BtlCmd_CheckItemHoldEffect(&s,c);break;
  case 224:return;
  default:assert(0);
  }
 }assert(0);
}
#define SCRIPT_SET(prefix) {prefix##0,prefix##1,prefix##2,prefix##3}
#define LENGTH_SET(prefix) {sizeof(prefix##0)/4,sizeof(prefix##1)/4,sizeof(prefix##2)/4,sizeof(prefix##3)/4}
int main(void){
 const u32 *old[]=SCRIPT_SET(old),*modern[]=SCRIPT_SET(modern),*ends[]=SCRIPT_SET(end);
 int oldLen[]=LENGTH_SET(old),modernLen[]=LENGTH_SET(modern),endLen[]=LENGTH_SET(end);
 int flags[]={FIELD_CONDITION_RAIN,FIELD_CONDITION_SANDSTORM,FIELD_CONDITION_SUN,FIELD_CONDITION_HAIL};
 int rocks[]={ITEM_DAMP_ROCK,ITEM_SMOOTH_ROCK,ITEM_HEAT_ROCK,ITEM_ICY_ROCK,ITEM_NONE,ITEM_LEFTOVERS};
 for(int w=0;w<4;w++)for(int holder=0;holder<4;holder++)for(int rock=0;rock<6;rock++)for(int suppression=0;suppression<4;suppression++){
  BattleContext c={0};BattleSystem s={0};c.battlerIdTemp=holder;
  // Other battlers hold the correct rock: only the source's item may extend.
  for(int i=0;i<4;i++)c.battleMons[i].item=rocks[w];
  c.battleMons[holder].item=rocks[rock];c.battleMons[holder].moveEffectData.embargoFlag=suppression&1;
  c.battleMons[holder].ability=(suppression&2)?ABILITY_KLUTZ:ABILITY_NONE;
  c.fieldCondition=FIELD_CONDITION_WEATHER|FIELD_CONDITION_TRICK_ROOM;
  c.fieldConditionData.weatherTurns=99;
  BattleContext legacy=c;execute(&legacy,old[w],oldLen[w]);
  assert(legacy.fieldCondition==(FIELD_CONDITION_TRICK_ROOM|flags[w]*2));
  assert(legacy.fieldConditionData.weatherTurns==99);
  execute(&c,modern[w],modernLen[w]);
  int expected=(rock==w&&suppression==0)?8:5;
  assert(c.fieldCondition==(FIELD_CONDITION_TRICK_ROOM|flags[w]));
  assert(c.fieldConditionData.weatherTurns==expected);
  // Item removal or the source leaving cannot change an established duration.
  c.battleMons[holder].item=ITEM_NONE;
  for(int turn=1;turn<=expected;turn++){
   end_turn(&s,&c,w);assert(c.fieldConditionData.weatherTurns==expected-turn);
   if(turn<expected)assert(c.readScript==BATTLE_SUBSCRIPT_WEATHER_CONTINUES);
   else {assert(c.readScript==234+w);execute(&c,ends[w],endLen[w]);}
  }
  assert(c.fieldCondition==FIELD_CONDITION_TRICK_ROOM);
  end_turn(&s,&legacy,w);assert(legacy.fieldConditionData.weatherTurns==99);
  assert(legacy.readScript==BATTLE_SUBSCRIPT_WEATHER_CONTINUES);
 }
 return 0;
}
'''
        game.GameLogicTests.compile_run(self, declarations + functions + '\n'.join(arrays) + checks,
                                        '-iquote', str(ROOT / 'files/msgdata/msg'))
