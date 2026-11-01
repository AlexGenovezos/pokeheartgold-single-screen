"""Gen IX Snow uses actual damage/weather commands and guarded native resources."""
from pathlib import Path
import hashlib
import re
import struct
import unittest
from unittest.mock import patch
import test_game_logic as game
import test_modern_rules as rules

ROOT = Path(__file__).resolve().parents[2]
CHARMAP = ROOT/'charmap.txt'


def native(name, path='src/battle/battle_util.c'):
    return game.function_source(path,name)+'\n'


def damage_source():
    source=rules.COMMON+'#include "constants/qol_moves.h"\n'+r'''
typedef struct {int power,type,category,effect,range;} Move;
typedef struct {int hp,ability,status,item,statChanges[8];struct {int embargoFlag;} moveEffectData;unsigned moveEffectFlags;} Mon;
typedef struct {Mon battleMons[4];struct {int helpingHandFlag;} turnData[4];
 struct {Move moveData[NUM_MOVES+1];int calcTemp;} trainerAIData;
 int powerMultiplier,fieldCondition;struct {int moldBreakerFlag;} selfTurnData[4];int battleStatus;int selectedMonIndex[4];} BattleContext;
typedef unsigned long long u64;
typedef int Pokemon;
static Pokemon partySpecies[4];
static Pokemon *BattleSystem_GetPartyMon(BattleSystem *s,int b,int slot){return &partySpecies[b];}
static int GetMonData(Pokemon *mon,int field,void *out){assert(field==MON_DATA_SPECIES);return *mon;}
static int vars[4][256],items[4];
static int GetBattlerVar(BattleContext *c,int b,int f,void *p){return vars[b][f];}
static int GetBattlerHeldItem(BattleContext *c,int b){return items[b];}
static int GetItemVar(BattleContext *c,int item,int f){return f==ITEM_VAR_HOLD_EFFECT?item:0;}
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int BattleContext_Get(BattleSystem *s,BattleContext *c,int f,int b){return 10;}
static int CheckMoveEffectOnField(BattleSystem *s,BattleContext *c,int effect){return 0;}
static int GetMonsHitCount(BattleSystem *s,BattleContext *c,int side,int b){return 1;}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''+native('GetBattlerAbility')+native('CheckBattlerAbilityIfNotIgnored')+native('CheckAbilityActive')
    util=(ROOT/'src/battle/battle_util.c').read_text()
    source+='#if QOL_MODERN_BATTLE\n'+rules.helper('Qol_HasPlusMinusAlly','src/battle/battle_util.c')+'#endif\n'
    source+=util[util.index('typedef struct MoveDamageCalc {'):util.index('} MoveDamageCalc;')+len('} MoveDamageCalc;')]
    source+='\n#if QOL_MODERN_BATTLE\n'+''.join(rules.helper(n,'src/battle/battle_util.c') for n in ('Qol_ChainStatModifier','Qol_ApplyStatModifier','Qol_GetBaseSpecies','Qol_CountFlowerGiftProviders','Qol_ModernOffenseStat','Qol_ModernDefenseStat'))+'#endif\n'
    source+=''.join(rules.array(n) for n in ('sStatChangeTable','sTypeEnhancingItems','sPunchingMoves'))+''.join(native(n) for n in ('Qol_GetMoveOffenseSource','Qol_MoveUsesPhysicalDefense','Qol_MoveIgnoresTargetStatStages','Qol_GetMoveBasePower','CalcMoveDamage'))
    return source+r'''
static BattleContext fixture(void){
 BattleContext c={0};memset(vars,0,sizeof(vars));memset(items,0,sizeof(items));c.powerMultiplier=10;
 for(int b=0;b<4;b++){c.battleMons[b].hp=100;vars[b][BMON_DATA_HP]=100;vars[b][BMON_DATA_MAXHP]=100;
 vars[b][BMON_DATA_ATK]=vars[b][BMON_DATA_SPATK]=1000;
 vars[b][BMON_DATA_DEF]=vars[b][BMON_DATA_SPDEF]=101;vars[b][BMON_DATA_LEVEL]=50;
 vars[b][BMON_DATA_STAT_CHANGE_ATK]=vars[b][BMON_DATA_STAT_CHANGE_SPATK]=6;
 vars[b][BMON_DATA_STAT_CHANGE_DEF]=vars[b][BMON_DATA_STAT_CHANGE_SPDEF]=6;}
 c.trainerAIData.moveData[MOVE_TACKLE]=(Move){500,TYPE_NORMAL,CATEGORY_PHYSICAL,0,0};return c;
}
static int damage(BattleContext *c,int field,int crit){return CalcMoveDamage(NULL,c,MOVE_TACKLE,0,field,0,0,0,1,crit);}
static int expected(int defense){return 1000*500*22/defense/50+2;}
'''


class SnowNativeTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    def variants(self, source):
        for flags in ((),('-DQOL_MODERN_TYPES=1',),('-DQOL_MODERN_MOVES=1',),
                      ('-DQOL_MODERN_BATTLE=1',),('-DQOL_MODERN_TYPES=1','-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1')):
            with self.subTest(flags=flags):
                self.compile_run(source,*flags,'-Wno-unused-function','-Wno-sign-compare')

    def test_current_ice_stage_then_snow_then_marvel_and_metal_powder(self):
        self.variants(damage_source()+r'''
int main(void){(void)BattleSystem_Random(NULL);
 for(int slot=0;slot<3;slot++)for(int stage=0;stage<=12;stage++)for(int crit=1;crit<=2;crit++)
 for(int unaware=0;unaware<2;unaware++)for(int modifier=0;modifier<3;modifier++){
  BattleContext c=fixture();vars[1][BMON_DATA_TYPE_1]=slot==1?TYPE_ICE:TYPE_NORMAL;
  vars[1][BMON_DATA_TYPE_2]=slot==2?TYPE_ICE:TYPE_NORMAL;
  vars[1][BMON_DATA_STAT_CHANGE_DEF]=stage;c.battleMons[0].ability=unaware?ABILITY_UNAWARE:ABILITY_NONE;
  if(modifier==1){c.battleMons[1].ability=ABILITY_MARVEL_SCALE;vars[1][BMON_DATA_STATUS]=STATUS_POISON;}
  if(modifier==2){vars[1][BMON_DATA_SPECIES]=SPECIES_DITTO;items[1]=HOLD_EFFECT_DITTO_DEF_UP;}
  int selected=unaware||(crit>1&&stage>6)?6:stage;
  int d=101;
#if !QOL_MODERN_BATTLE
  if(modifier==1)d=d*3/2;if(modifier==2)d*=2;
#endif
  d=d*sStatChangeTable[selected][0]/sStatChangeTable[selected][1];
#if QOL_MODERN_BATTLE
  if(slot)d=d*3/2;
  if(modifier==1)d=d*3/2;if(modifier==2)d*=2;
#endif
  assert(damage(&c,FIELD_CONDITION_HAIL,crit)==expected(d));
  // Special attacks use Sp. Def, regardless of current Ice typing.
  c.trainerAIData.moveData[MOVE_TACKLE].category=CATEGORY_SPECIAL;
  assert(damage(&c,FIELD_CONDITION_HAIL,crit)==expected(101));
 }
 return 0;}
''')

    def test_supplied_weather_suppression_current_types_and_mold_breaker(self):
        self.variants(damage_source()+r'''
int main(void){(void)BattleSystem_Random(NULL);
 for(int field=0;field<3;field++)for(int actual=0;actual<2;actual++)for(int blocker=0;blocker<3;blocker++)
 for(int hp=0;hp<2;hp++)for(int suppressed=0;suppressed<2;suppressed++)for(int mold=0;mold<2;mold++){
  BattleContext c=fixture();vars[1][BMON_DATA_TYPE_2]=TYPE_ICE;
  c.fieldCondition=actual?FIELD_CONDITION_HAIL_ALL:0;
  c.battleMons[2].ability=blocker==1?ABILITY_CLOUD_NINE:blocker==2?ABILITY_AIR_LOCK:ABILITY_NONE;
  c.battleMons[2].hp=hp;c.battleMons[2].moveEffectFlags=suppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  int snow=QOL_MODERN_BATTLE&&field&&!(blocker&&hp&&!suppressed);
  int weather=field==1?FIELD_CONDITION_HAIL:field==2?FIELD_CONDITION_HAIL_PERMANENT:0;
  assert(damage(&c,weather,1)==expected(snow?151:101));
  vars[1][BMON_DATA_TYPE_2]=TYPE_NORMAL;assert(damage(&c,weather,1)==expected(101));
 }
 return 0;}
''')

    def test_weather_command_removes_only_chip_preserves_ice_body_and_guards(self):
        source=rules.COMMON+r'''
typedef struct {int hp,maxHp,status,ability;unsigned moveEffectFlags;} Mon;
typedef struct {Mon battleMons[4];int fieldCondition,tempData,hpCalc,moveTemp,msgTemp;} BattleContext;
static int types[4][2],target;
static void BattleScriptIncrementPointer(BattleContext *c,int n){}
static int BattleScriptReadWord(BattleContext *c){return 0;}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){return target;}
static int GetBattlerVar(BattleContext *c,int b,int f,void *p){return types[b][f==BMON_DATA_TYPE_2];}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''+native('GetBattlerAbility')+native('CheckAbilityActive')+native('DamageDivide')+native('BtlCmd_EndOfTurnWeatherEffect','src/battle/battle_command.c')+r'''
int main(void){(void)BattleSystem_Random(NULL);
 for(int weather=0;weather<2;weather++)for(int ability=0;ability<3;ability++)for(int ice=0;ice<2;ice++)
 for(int hp=0;hp<3;hp++)for(int blocked=0;blocked<3;blocked++)for(int hidden=0;hidden<3;hidden++){
  BattleContext c={0};c.fieldCondition=weather?FIELD_CONDITION_HAIL:FIELD_CONDITION_HAIL_PERMANENT;
  c.battleMons[0]=(Mon){hp==0?0:hp==1?80:160,160,0,ability==1?ABILITY_ICE_BODY:ability==2?ABILITY_SNOW_CLOAK:ABILITY_NONE,hidden==1?0x80:hidden==2?0x40000:0};
  c.battleMons[1].hp=1;c.battleMons[1].ability=blocked==1?ABILITY_CLOUD_NINE:blocked==2?ABILITY_AIR_LOCK:ABILITY_NONE;
  types[0][0]=TYPE_NORMAL;types[0][1]=ice?TYPE_ICE:TYPE_NORMAL;
  c.moveTemp=999;BtlCmd_EndOfTurnWeatherEffect(NULL,&c);
  int heal=!blocked&&!hidden&&hp==1&&ability==1;
  int chip=!QOL_MODERN_BATTLE&&!blocked&&!hidden&&hp&&!ice&&!ability;
  assert(c.hpCalc==(heal?10:chip?-10:0));assert(c.tempData==0);
  assert(c.moveTemp==(chip?MOVE_HAIL:999));
 }
 return 0;}
'''
        self.variants(source)


class SnowResourceTests(unittest.TestCase):
    def module(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('snow_resources'),'Snow resource owner is missing')
        import snow_resources
        return snow_resources

    def test_effect_source_guards_and_all_weather_duplicate(self):
        module=self.module();source=(ROOT/'files/battledata/script/effect_script/effect_script_0164.s').read_text()
        modern=module.modern_snow_effect_source(source)
        self.assertEqual(modern,source.replace('FIELD_CONDITION_HAIL, _036','FIELD_CONDITION_HAIL_ALL, _036',1))
        for drift in (source+'\n',modern,source.replace('ATTACKER','TARGET')):
            with self.assertRaisesRegex(ValueError,'expected source'):module.modern_snow_effect_source(drift)

    def test_messages_follow_simple_preserve_every_other_word_and_bank(self):
        module=self.module()
        from simple_scripts import modern_simple_message_resources
        from nitro_data import unpack_narc,unpack_messages
        original=(ROOT/'files/msgdata/msg.narc').read_bytes()
        simple=modern_simple_message_resources(original,CHARMAP)
        before,names=unpack_narc(simple)
        result=module.modern_snow_message_resources(simple,CHARMAP)
        after,resultnames=unpack_narc(result);self.assertEqual(names,resultnames)
        targets={197:{701,702,703,810,811,812},221:{282,334},622:{4},426:{43},157:{47},749:{258}}
        self.assertEqual(len(before),len(after))
        for bank,old in enumerate(before):
            if bank not in targets:self.assertEqual(after[bank],old);continue
            oldwords,key=unpack_messages(old);newwords,newkey=unpack_messages(after[bank]);self.assertEqual(key,newkey)
            self.assertEqual(len(oldwords),len(newwords))
            self.assertEqual({i for i,(a,b) in enumerate(zip(oldwords,newwords)) if a!=b},targets[bank])
        oldwords,_=unpack_messages(before[197]);newwords,_=unpack_messages(after[197]);self.assertEqual(newwords[1276:],oldwords[1276:])
        for row in (701,702,703):
            self.assertEqual([v for v in newwords[row] if v>=0xF000],[v for v in oldwords[row] if v>=0xF000])
        with self.assertRaises(ValueError):module.modern_snow_message_resources(original,CHARMAP)
        with self.assertRaises(ValueError):module.modern_snow_message_resources(result,CHARMAP)

    def test_numeric_ai_same_width_full_guard_and_impossible_chip_branch(self):
        module=self.module();source=(ROOT/'asm/trainer_ai_data.s').read_text()
        updated=module.modern_snow_ai_source(source)
        def words(text):
            data=bytes(int(n,16) for n in re.findall(r'0x([0-9A-Fa-f]{2})',text.split('gTrainerAITable:\n',1)[1].split('\n\t.public',1)[0]))
            return struct.unpack('<'+'I'*(len(data)//4),data)
        old,new=words(source),words(updated);self.assertEqual(len(old),len(new))
        self.assertEqual([i for i,(a,b) in enumerate(zip(old,new)) if a!=b],[5747]);self.assertEqual(new[5747],0xffffffff)
        self.assertEqual(old[5746:5749],(19,4,14));self.assertEqual(new[5746:5749],(19,0xffffffff,14))
        for drift in (source+'\n',updated,source.replace('AICmd_LoadCurrentWeather','AICmd_Dummy')):
            with self.assertRaisesRegex(ValueError,'expected source'):module.modern_snow_ai_source(drift)

    def test_effect_parity_precedes_transformed_compile_and_archive_preserves_members(self):
        module=self.module()
        from nitro_data import pack_narc,unpack_narc
        source=(ROOT/module.EFFECT_SOURCE).read_text()
        with patch.object(module,'compile_battle_script',return_value=b'wrong') as compiler:
            with self.assertRaisesRegex(ValueError,'unchanged.*match'):module.modern_snow_effect_script(b'original')
            compiler.assert_called_once_with(source,module.ROOT)
        with patch.object(module,'compile_battle_script',side_effect=[b'original',b'modern']) as compiler:
            self.assertEqual(module.modern_snow_effect_script(b'original'),b'modern')
            self.assertEqual(compiler.call_args_list[1].args[0],module.modern_snow_effect_source(source))
        members=[struct.pack('<I',i) for i in range(276)]
        archive=pack_narc(members)
        with patch.object(module,'modern_snow_effect_script',return_value=b'snow'):
            result,names=unpack_narc(module.modern_snow_effect_resources(archive))
        self.assertEqual(names,unpack_narc(archive)[1]);self.assertEqual(result[:164],members[:164]);self.assertEqual(result[165:],members[165:]);self.assertEqual(result[164],b'snow')
        with self.assertRaisesRegex(ValueError,'absent'):module.modern_snow_effect_resources(pack_narc(members[:164]))

    def test_messages_reject_every_target_source_and_encoded_bank_drift(self):
        module=self.module()
        from simple_scripts import modern_simple_message_resources
        from nitro_data import unpack_narc,unpack_messages,pack_messages,pack_narc
        simple=modern_simple_message_resources((ROOT/'files/msgdata/msg.narc').read_bytes(),CHARMAP)
        banks,names=unpack_narc(simple)
        for bank in module.MESSAGE_BANKS:
            corrupt=list(banks);words,key=unpack_messages(corrupt[bank]);words[-1][0]^=1;corrupt[bank]=pack_messages(words,key)
            with self.subTest(bank=bank),self.assertRaises(ValueError):module.modern_snow_message_resources(pack_narc(corrupt,names),CHARMAP)
            original_read=Path.read_bytes
            def read(path):
                data=original_read(path)
                return data+b'\n' if path.name.startswith(f'msg_{bank:04}') else data
            with self.subTest(source=bank),patch.object(Path,'read_bytes',read),self.assertRaisesRegex(ValueError,'expected source'):
                module.modern_snow_message_resources(simple,CHARMAP)
        # Extended move messages may add bank829; do not assume exactly829 banks.
        banks.append(b'unrelated extension')
        self.assertEqual(unpack_narc(module.modern_snow_message_resources(pack_narc(banks,names),CHARMAP))[0][-1],banks[-1])
        for malformed in (b'',b'NARC'+b'\x00'*20):
            with self.assertRaises(ValueError):module.modern_snow_message_resources(malformed,CHARMAP)

    def test_rom_flag_routes_effects_and_messages_after_simple(self):
        self.module()
        import modern_rom
        self.assertTrue(hasattr(modern_rom,'modern_snow_effect_resources'),'Snow ROM integration missing')
        from contextlib import ExitStack
        transforms=['modern_battle_resources','modern_paralysis_resources','modern_weather_resources',
            'modern_absorption_resources','modern_sturdy_resources','modern_cursed_body_resources',
            'modern_competitive_resources','modern_oblivious_intimidate_resources','modern_simple_resources',
            'modern_simple_message_resources','modern_ability_description_resources','modern_drain_resources',
            'modern_move_stat_resources','modern_move_effect_resources']
        paths={p:(0,0,3) for p in ('a/0/0/8','a/0/2/7','a/0/6/8','a/0/0/1','a/0/3/0','a/0/1/1','a/0/0/0')}
        for types,battle,moves in ((False,False,False),(True,False,False),(False,False,True),(True,True,True),(False,True,False)):
            with self.subTest(types=types,battle=battle,moves=moves),ExitStack() as stack:
                mocks={name:stack.enter_context(patch('modern_rom.'+name,side_effect=lambda data,*args:data))
                       for name in transforms}
                stack.enter_context(patch('modern_rom.rom_files',return_value=paths))
                stack.enter_context(patch('modern_rom.modern_type_resources',return_value=(b'icons',b'fairy')))
                stack.enter_context(patch('modern_rom.modern_pokedex_resources',return_value=b'dex'))
                effect=stack.enter_context(patch('modern_rom.modern_snow_effect_resources',return_value=b'snoweffect'))
                message=stack.enter_context(patch('modern_rom.modern_snow_message_resources',return_value=b'snowmessages'))
                extended=stack.enter_context(patch('modern_rom.extended_move_resources',side_effect=lambda a,b,c,*args:(a,b,c)))
                stack.enter_context(patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:replacements))
                result=modern_rom.make_modern_rom(b'rom',CHARMAP,types=types,battle_rules=battle,moves=moves)
                self.assertEqual(effect.call_count,int(battle));self.assertEqual(message.call_count,int(battle))
                self.assertEqual(mocks['modern_move_stat_resources'].call_count,int(moves))
                self.assertEqual(mocks['modern_move_effect_resources'].call_count,int(moves))
                if moves:
                    self.assertEqual(mocks['modern_move_stat_resources'].call_args.args[1],battle)
                    self.assertEqual(mocks['modern_move_effect_resources'].call_args.args[0],
                                     b'snoweffect' if battle else b'rom')
                if battle:
                    self.assertEqual(result['a/0/3/0'],b'snoweffect');self.assertEqual(result['a/0/2/7'],b'snowmessages')
                    if moves:self.assertEqual(extended.call_args.args[2],b'snowmessages')

    def test_make_ai_producer_tracks_same_defines_and_default_identity(self):
        self.module()
        source=(ROOT/'Makefile').read_text()
        self.assertIn('# BEGIN SNOW AI PRODUCER\n',source)
        import shutil,subprocess,tempfile
        rules_text=source.split('# BEGIN SNOW AI PRODUCER\n',1)[1].split('# END SNOW AI PRODUCER\n',1)[0]
        make=shutil.which('gmake') or shutil.which('make')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'build/asm').mkdir(parents=True)
            makefile=root/'Makefile'
            makefile.write_text('BUILD_DIR := '+str(root/'build')+'\nWORK_DIR := '+str(ROOT)+'\nDEFINES := $(CLI_DEFINES)\n'+rules_text)
            target=root/'build/asm/trainer_ai_data.qol.s'
            for flags in ('','-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1','-DQOL_MODERN_BATTLE=0'):
                (root/'build/game-defines.txt').write_text(flags)
                result= subprocess.run([make,'-f',str(makefile),str(target),'CLI_DEFINES='+flags],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(target.read_text()==(ROOT/'asm/trainer_ai_data.s').read_text(),flags!='-DQOL_MODERN_BATTLE=1')
            # Exercise the actual object rule with a recording assembler edge.
            # Its first input must be the generated copy, not game-defines.txt.
            recorder=root/'assembler.py'
            recorder.write_text('import pathlib,sys\nargs=sys.argv[1:]\npathlib.Path(args[args.index("-o")+1]).write_bytes(pathlib.Path(args[-1]).read_bytes())\n')
            with makefile.open('a') as stream:
                stream.write('\nNODEP := 1\nMWAS := python3 '+str(recorder)+'\n')
            output=root/'build/asm/trainer_ai_data.o'
            result=subprocess.run([make,'-f',str(makefile),str(output),'CLI_DEFINES=-DQOL_MODERN_BATTLE=1'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(output.read_bytes(),target.read_bytes())


class SnowConsumerTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    def test_weather_ball_type_power_ai_and_healing_suppression(self):
        source=rules.COMMON+r'''
typedef int Pokemon;
typedef struct {int power,type;} Move;
typedef struct {int hp,maxHp,ability,hpIV,atkIV,defIV,speedIV,spAtkIV,spDefIV;unsigned moveEffectFlags;} Mon;
typedef struct {Mon battleMons[4];int fieldCondition,moveNoCur,movePower,moveType,hpCalc,battlerIdAttacker;
 struct {Move moveData[NUM_MOVES+1];} trainerAIData;} BattleContext;
static int MaskOfFlagNo(int n){return 1u<<n;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int GetNaturalGiftType(BattleContext *c,int b){return TYPE_NORMAL;}
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return 0;}
static int GetItemVar(BattleContext *c,int item,int f){return 0;}
static int GetMonData(Pokemon *m,int f,void *p){return 0;}
static void BattleScriptIncrementPointer(BattleContext *c,int n){}
'''+native('GetBattlerAbility')+native('CheckAbilityActive')+native('DamageDivide')
        source+=native('GetDynamicMoveType')+native('TrainerAI_MoveType','src/battle/trainer_ai.c')+native('TrainerAI_GetMoveType','src/battle/battle_controller_opponent.c')
        source+=native('BtlCmd_CalcWeatherBallParams','src/battle/battle_command.c')+native('BtlCmd_WeatherHPRecovery','src/battle/battle_command.c')
        calc=native('TrainerAI_CalcDamage','src/battle/trainer_ai.c')
        self.assertIn('case MOVE_WEATHER_BALL:',calc,'AI damage does not account for Weather Ball weather')
        branch=calc[calc.index('    case MOVE_WEATHER_BALL:'):]
        branch=branch[:branch.index('        break;')+len('        break;')]
        source+='static int ai_weather(BattleSystem *battleSystem,BattleContext *ctx){int move=MOVE_WEATHER_BALL,attacker=0,power=0,type=0;switch(move){\n'+branch+'\n}return power*100+type;}\n'
        source+=r'''
int main(void){(void)BattleSystem_Random(NULL);
 for(int weather=0;weather<3;weather++)for(int blocker=0;blocker<3;blocker++)for(int hp=0;hp<2;hp++)for(int suppressed=0;suppressed<2;suppressed++){
  BattleContext c={0};c.fieldCondition=weather==1?FIELD_CONDITION_HAIL:weather==2?FIELD_CONDITION_HAIL_PERMANENT:0;
  c.moveNoCur=MOVE_WEATHER_BALL;c.movePower=50;c.moveType=TYPE_NORMAL;c.trainerAIData.moveData[MOVE_WEATHER_BALL]=(Move){50,TYPE_NORMAL};
  c.battleMons[0].hp=80;c.battleMons[0].maxHp=160;
  c.battleMons[2].hp=hp;c.battleMons[2].ability=blocker==1?ABILITY_CLOUD_NINE:blocker==2?ABILITY_AIR_LOCK:ABILITY_NONE;
  c.battleMons[2].moveEffectFlags=suppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int effective=weather&&!(blocker&&hp&&!suppressed),type=effective?TYPE_ICE:TYPE_NORMAL;
  assert(GetDynamicMoveType(NULL,&c,0,MOVE_WEATHER_BALL)==type);
  assert(TrainerAI_MoveType(NULL,&c,0,MOVE_WEATHER_BALL)==type);
  assert(TrainerAI_GetMoveType(NULL,&c,NULL,MOVE_WEATHER_BALL)==type);
  BtlCmd_CalcWeatherBallParams(NULL,&c);assert(c.moveType==type);assert(c.movePower==(effective?100:50));
  assert(ai_weather(NULL,&c)==(effective?100:50)*100+type);
  BtlCmd_WeatherHPRecovery(NULL,&c);assert(c.hpCalc==(effective?40:80));
 }
 return 0;}
'''
        self.compile_run(source,'-DQOL_MODERN_BATTLE=1','-Wno-unused-function','-Wno-sign-compare')

    def test_solar_beam_snow_penalty_and_special_rock_selected_stage_order(self):
        source=damage_source()+r'''
int main(void){(void)BattleSystem_Random(NULL);
 BattleContext c=fixture();c.trainerAIData.moveData[MOVE_SOLAR_BEAM]=(Move){100,TYPE_GRASS,CATEGORY_SPECIAL,0,0};
 int normal=CalcMoveDamage(NULL,&c,MOVE_SOLAR_BEAM,0,0,0,0,0,1,1);
 int snow=CalcMoveDamage(NULL,&c,MOVE_SOLAR_BEAM,0,FIELD_CONDITION_HAIL,0,0,0,1,1);
 assert(snow==(normal-2)/2+2);
 c.battleMons[2].ability=ABILITY_CLOUD_NINE;assert(CalcMoveDamage(NULL,&c,MOVE_SOLAR_BEAM,0,FIELD_CONDITION_HAIL,0,0,0,1,1)==normal);
 // D1c modern Sand follows the selected SpDef stage; battle-off stays native.
 c=fixture();vars[1][BMON_DATA_TYPE_2]=TYPE_ROCK;vars[1][BMON_DATA_STAT_CHANGE_SPDEF]=8;
 c.trainerAIData.moveData[MOVE_TACKLE].category=CATEGORY_SPECIAL;
 assert(damage(&c,FIELD_CONDITION_SANDSTORM,1)==expected(QOL_MODERN_BATTLE?(101*2)*3/2:(101*3/2)*2));
 return 0;}
'''
        for flag in (0,1):self.compile_run(source,f'-DQOL_MODERN_BATTLE={flag}','-Wno-unused-function','-Wno-sign-compare')

    def test_blizzard_and_snow_cloak_preserve_protection_semi_states_and_mold(self):
        import test_modern_original_abilities as original
        source=original.accuracy_source()
        source=source.replace('static int CheckAbilityActive(BattleSystem *s,BattleContext *c,int mode,int mon,int ability){return 0;}',
            'static int MaskOfFlagNo(int n){return 1u<<n;}\nstatic int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}\nstatic int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}\n'+native('CheckAbilityActive'))
        # CheckAbilityActive needs the actual accessor's declaration first.
        source=source.replace('static int MaskOfFlagNo(', 'u8 GetBattlerAbility(BattleContext *c,int b);\nstatic int MaskOfFlagNo(',1)
        source+=r'''
int main(void){
 for(int permanent=0;permanent<2;permanent++)for(int blocker=0;blocker<3;blocker++)for(int mold=0;mold<2;mold++)
 for(int abilitySuppressed=0;abilitySuppressed<2;abilitySuppressed++)for(int roll=0;roll<100;roll++){
  BattleContext c=fixture(MOVE_TACKLE);c.fieldCondition=permanent?FIELD_CONDITION_HAIL_PERMANENT:FIELD_CONDITION_HAIL;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;c.battleMons[1].ability=ABILITY_SNOW_CLOAK;
  c.battleMons[1].moveEffectFlags=abilitySuppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[2].hp=100;c.battleMons[2].ability=blocker==1?ABILITY_CLOUD_NINE:blocker==2?ABILITY_AIR_LOCK:ABILITY_NONE;
  randomValue=roll;BattleSystem_CheckMoveHit(NULL,&c,0,1,MOVE_TACKLE);
  int chance=(!blocker&&!mold&&!abilitySuppressed)?48:60;
  assert(!!(c.moveStatusFlag&MOVE_STATUS_MISSED)==(roll+1>chance));
 }
 for(int blocker=0;blocker<3;blocker++)for(int fail=0;fail<5;fail++){
  BattleContext c=fixture(MOVE_BLIZZARD);c.fieldCondition=FIELD_CONDITION_HAIL_ALL;
  c.trainerAIData.moveData[MOVE_BLIZZARD].effect=MOVE_EFFECT_BLIZZARD;
  c.battleMons[2].hp=100;c.battleMons[2].ability=blocker==1?ABILITY_CLOUD_NINE:blocker==2?ABILITY_AIR_LOCK:ABILITY_NONE;
  c.moveStatusFlag=MOVE_STATUS_MISSED;
  if(fail==1)c.turnData[1].protectFlag=1;
  if(fail==2)c.battleMons[1].moveEffectFlags=MOVE_EFFECT_FLAG_FLY;
  if(fail==3)c.battleMons[1].moveEffectFlags=MOVE_EFFECT_FLAG_DIG;
  if(fail==4)c.battleMons[1].moveEffectFlags=MOVE_EFFECT_FLAG_DIVE;
  BattleSystem_CheckMoveEffect(NULL,&c,0,1,MOVE_BLIZZARD);
  assert(!!(c.moveStatusFlag&MOVE_STATUS_MISSED)==(blocker||fail==1));
  assert(!!(c.moveStatusFlag&MOVE_STATUS_PROTECTED)==(fail==1));
  assert(!!(c.moveStatusFlag&MOVE_STATUS_SEMI_INVULNERABLE)==(fail>1));
 }
 return 0;}
'''
        for flag in (0,1):self.compile_run(source,f'-DQOL_MODERN_BATTLE={flag}','-Wno-unused-function','-Wno-unused-variable','-Wno-unused-but-set-variable','-Wno-sign-compare')

    def test_forecast_current_ice_and_cherrim_revert(self):
        function=native('Battler_CheckWeatherFormChange')
        # Execute the complete native Castform and Cherrim branches; unrelated
        # legendary-party update code below them needs no fixture here.
        fragment=function[function.index('        if (ctx->battleMons[ctx->battlerIdTemp].species == SPECIES_CASTFORM'):function.index('        if (ctx->battleMons[ctx->battlerIdTemp].species == SPECIES_ARCEUS')]
        source=rules.COMMON+r'''
typedef struct {int hp,ability,species,type1,type2,form;unsigned moveEffectFlags;} Mon;
typedef struct {Mon battleMons[4];int fieldCondition,battlerIdTemp,turnOrder[4];} BattleContext;
static int MaskOfFlagNo(int n){return 1u<<n;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
'''+native('GetBattlerAbility')+native('CheckAbilityActive')
        source+='static int forms(BattleSystem *battleSystem,BattleContext *ctx,int *script){int ret=0;for(int i=0;i<4;i++){ctx->battlerIdTemp=ctx->turnOrder[i];\n'+fragment+'\n}return ret;}\n'
        source+=r'''
int main(void){(void)BattleSystem_Random(NULL);
 for(int permanent=0;permanent<2;permanent++)for(int blocker=0;blocker<3;blocker++){
  BattleContext c={0};for(int i=0;i<4;i++)c.turnOrder[i]=i;
  c.fieldCondition=permanent?FIELD_CONDITION_HAIL_PERMANENT:FIELD_CONDITION_HAIL;
  c.battleMons[0]=(Mon){100,ABILITY_FORECAST,SPECIES_CASTFORM,TYPE_FIRE,TYPE_FIRE,CASTFORM_SUNNY,0};
  c.battleMons[1]=(Mon){100,ABILITY_FLOWER_GIFT,SPECIES_CHERRIM,TYPE_GRASS,TYPE_GRASS,CHERRIM_SUNNY,0};
  c.battleMons[2].hp=100;c.battleMons[2].ability=blocker==1?ABILITY_CLOUD_NINE:blocker==2?ABILITY_AIR_LOCK:ABILITY_NONE;
  int script=0;assert(forms(NULL,&c,&script));assert(script==BATTLE_SUBSCRIPT_FORM_CHANGE);
  assert(c.battleMons[0].type1==(blocker?TYPE_NORMAL:TYPE_ICE));assert(c.battleMons[0].type2==c.battleMons[0].type1);
  assert(c.battleMons[0].form==(blocker?CASTFORM_NORMAL:CASTFORM_SNOWY));
  assert(forms(NULL,&c,&script));assert(c.battleMons[1].form==CHERRIM_CLOUDY);
  assert(!forms(NULL,&c,&script));
 }
 return 0;}
'''
        for flag in (0,1):self.compile_run(source,f'-DQOL_MODERN_BATTLE={flag}','-Wno-unused-function','-Wno-sign-compare')


    def test_numeric_ai_executes_no_snow_chip_branch_and_retains_raw_weather(self):
        import snow_resources
        raw=(ROOT/'asm/trainer_ai_data.s').read_text()
        def operand(source):
            table=source.split('gTrainerAITable:\n',1)[1].split('\n\t.public',1)[0]
            data=bytes(int(n,16) for n in re.findall(r'0x([0-9A-Fa-f]{2})',table))
            return struct.unpack_from('<3i',data,5746*4)
        old,new=operand(raw),operand(snow_resources.modern_snow_ai_source(raw))
        source=rules.COMMON+r'''
#include "constants/battle/trainer_ai.h"
typedef struct {int calcTemp;} AI;
typedef struct {AI trainerAIData;int fieldCondition,pos;const int *words;} BattleContext;
static void AIScript_IncrementCursor(BattleContext *c,int n){c->pos+=n;}
static int AIScript_Read(BattleContext *c){return c->words[c->pos++];}
'''+native('AICmd_IfLoadedEqualTo','src/battle/trainer_ai.c')+native('AICmd_LoadCurrentWeather','src/battle/trainer_ai.c')
        source+='static const int old[]={'+','.join(map(str,old))+'};\nstatic const int modern[]={'+','.join(map(str,new))+'};\n'
        source+=r'''
int main(void){(void)BattleSystem_Random(NULL);
 for(int weather=0;weather<2;weather++){
  BattleContext c={0};c.fieldCondition=weather?FIELD_CONDITION_HAIL_PERMANENT:FIELD_CONDITION_HAIL;
  AICmd_LoadCurrentWeather(NULL,&c);assert(c.trainerAIData.calcTemp==AI_WEATHER_HAILING);
  c.pos=0;c.words=old;AICmd_IfLoadedEqualTo(NULL,&c);assert(c.pos==17);
  c.pos=0;c.words=modern;AICmd_IfLoadedEqualTo(NULL,&c);assert(c.pos==3);
 }
 return 0;}
'''
        self.compile_run(source)

    def test_counter_and_mirror_coat_keep_fixed_returned_damage_in_snow(self):
        source=rules.COMMON+r'''
enum {NARC_a_0_0_1};
typedef struct {int hp,type1,type2;} Mon;
typedef struct {Mon battleMons[4];int fieldCondition,battlerIdAttacker,battlerIdTarget,damage,moveStatusFlag,commandNext;
 struct {int physicalDamage[4],specialDamage[4],battlerIdPhysicalDamage,battlerIdSpecialDamage;} turnData[4];
 struct {int followMeFlag,battlerIdFollowMe;} fieldSideConditionData[2];struct {int ignorePressure;} selfTurnData[4];} BattleContext;
static void BattleScriptIncrementPointer(BattleContext *c,int n){}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int Battler_GetRandomOpposingBattlerId(BattleSystem *s,BattleContext *c,int b){return b^1;}
static void BattleScriptJump(BattleContext *c,int narc,int script){assert(0);}
static void CheckIgnorePressure(BattleContext *c,int a,int d){}
'''+native('BtlCmd_Counter','src/battle/battle_command.c')+native('BtlCmd_MirrorCoat','src/battle/battle_command.c')+r'''
int main(void){(void)BattleSystem_Random(NULL);
 for(int type=0;type<2;type++)for(int weather=0;weather<3;weather++){
  BattleContext c={0};c.battleMons[1].hp=100;c.battleMons[1].type1=type?TYPE_ICE:TYPE_NORMAL;
  c.fieldCondition=weather==1?FIELD_CONDITION_HAIL:weather==2?FIELD_CONDITION_HAIL_PERMANENT:0;
  c.turnData[0].battlerIdPhysicalDamage=c.turnData[0].battlerIdSpecialDamage=1;
  c.turnData[0].physicalDamage[1]=-37;c.turnData[0].specialDamage[1]=-23;
  BtlCmd_Counter(NULL,&c);assert(c.damage==-74&&c.battlerIdTarget==1);
  BtlCmd_MirrorCoat(NULL,&c);assert(c.damage==-46&&c.battlerIdTarget==1);
 }
 return 0;}
'''
        for flag in (0,1):self.compile_run(source,f'-DQOL_MODERN_BATTLE={flag}')


class SnowSdkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import snow_resources as module
        from battle_scripts import battle_script_tools,compile_battle_script
        from nitro_data import unpack_narc
        try:battle_script_tools()
        except FileNotFoundError as error:raise unittest.SkipTest(str(error))
        cls.original=unpack_narc((ROOT/'files/battledata/script/effect_script.narc').read_bytes())[0][164]
        cls.unchanged=compile_battle_script((ROOT/module.EFFECT_SOURCE).read_text())
        cls.modern=module.modern_snow_effect_script(cls.original)

    def test_original_effect_sdk_parity_and_only_duplicate_operand_changes(self):
        self.assertEqual(self.original,self.unchanged)
        old=struct.unpack('<'+'I'*(len(self.original)//4),self.original)
        new=struct.unpack('<'+'I'*(len(self.modern)//4),self.modern)
        self.assertEqual(len(old),len(new));self.assertEqual([i for i,(a,b) in enumerate(zip(old,new)) if a!=b],[3])
        self.assertEqual(old[3],64);self.assertEqual(new[3],192)

    def test_actual_compiled_hail_commands_duplicate_finite_source_rock_and_suppression(self):
        def array(data):return ','.join(f'{n}u' for n in struct.unpack('<'+'I'*(len(data)//4),data))
        source=rules.COMMON+r'''
#include "constants/battle_script.h"
#include "constants/opcode.h"
#include "constants/message_tags.h"
#include "msg_0197.h"
typedef struct {int item,ability;struct {int embargoFlag;} moveEffectData;} Mon;
typedef struct {const u32 *words;int pos,length,fieldCondition,attacker,moveStatusFlag,calcTemp,indirect,buffer;
 struct {int weatherTurns;} fieldConditionData;Mon battleMons[4];} BattleContext;
static void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;assert(c->pos>=0&&c->pos<=c->length);}
static int BattleScriptReadWord(BattleContext *c){assert(c->pos<c->length);return c->words[c->pos++];}
static int *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int v){
 switch(v){case BSCRIPT_VAR_FIELD_CONDITION:return &c->fieldCondition;
 case BSCRIPT_VAR_WEATHER_TURNS:return &c->fieldConditionData.weatherTurns;
 case BSCRIPT_VAR_MOVE_STATUS_FLAGS:return &c->moveStatusFlag;
 case BSCRIPT_VAR_CALC_TEMP:return &c->calcTemp;
 case BSCRIPT_VAR_SIDE_EFFECT_FLAGS_INDIRECT:return &c->indirect;}assert(0);return NULL;}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){assert(side==BATTLER_CATEGORY_ATTACKER);return c->attacker;}
static int GetBattlerAbility(BattleContext *c,int b){return c->battleMons[b].ability;}
static int GetItemVar(BattleContext *c,int item,int f){
 if(f==ITEM_VAR_MODIFIER)return item==ITEM_ICY_ROCK?3:0;
 assert(f==ITEM_VAR_HOLD_EFFECT);return item==ITEM_ICY_ROCK?HOLD_EFFECT_EXTEND_HAIL:HOLD_EFFECT_NONE;}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''
        source+=native('GetBattlerHeldItem')+native('GetBattlerHeldItemEffect')
        for name in ('BtlCmd_CompareVarToValue','BtlCmd_UpdateVar','BtlCmd_CheckItemHoldEffect','BtlCmd_GetItemEffectParam','BtlCmd_UpdateVar2'):
            source+=native(name,'src/battle/battle_command.c')
        source+='static const u32 original[]={'+array(self.original)+'};\nstatic const u32 modern[]={'+array(self.modern)+'};\n'
        source+=r'''
static void execute(BattleContext *c,const u32 *script,int length){
 c->words=script;c->pos=0;c->length=length;
 for(int steps=0;steps<50;steps++){
  switch(c->words[c->pos]){
  case 21:c->pos++;c->buffer=BattleScriptReadWord(c);assert(BattleScriptReadWord(c)==TAG_NONE);break;
  case 32:BtlCmd_CompareVarToValue(NULL,c);break;
  case 50:BtlCmd_UpdateVar(NULL,c);break;
  case 57:BtlCmd_UpdateVar2(NULL,c);break;
  case 166:BtlCmd_CheckItemHoldEffect(NULL,c);break;
  case 168:BtlCmd_GetItemEffectParam(NULL,c);break;
  case 224:return;
  default:fprintf(stderr,"unexpected opcode %u at%d\n",c->words[c->pos],c->pos);assert(0);
  }
 }assert(0);
}
int main(void){(void)BattleSystem_Random(NULL);
 for(int source=0;source<4;source++)for(int weather=0;weather<4;weather++)for(int rock=0;rock<2;rock++)for(int suppressed=0;suppressed<4;suppressed++){
  BattleContext c={0};c.attacker=source;c.fieldCondition=FIELD_CONDITION_TRICK_ROOM|(weather==1?FIELD_CONDITION_HAIL:weather==2?FIELD_CONDITION_HAIL_PERMANENT:weather==3?FIELD_CONDITION_RAIN:0);
  c.fieldConditionData.weatherTurns=99;
  for(int b=0;b<4;b++)c.battleMons[b].item=ITEM_ICY_ROCK;
  c.battleMons[source].item=rock?ITEM_ICY_ROCK:ITEM_NONE;
  c.battleMons[source].moveEffectData.embargoFlag=suppressed&1;c.battleMons[source].ability=suppressed&2?ABILITY_KLUTZ:ABILITY_NONE;
  BattleContext old=c;execute(&old,original,sizeof(original)/4);execute(&c,modern,sizeof(modern)/4);
  int duplicate=weather==1||weather==2;
  assert(!!(c.moveStatusFlag&MOVE_STATUS_FAILED)==duplicate);
  if(duplicate){assert(c.fieldCondition==old.fieldCondition||weather==2);assert(c.fieldConditionData.weatherTurns==99);assert(c.buffer==0);assert(c.indirect==0);}
  else {assert(c.fieldCondition==(FIELD_CONDITION_TRICK_ROOM|FIELD_CONDITION_HAIL));assert(c.fieldConditionData.weatherTurns==(rock&&!suppressed?8:5));
   assert(c.buffer==msg_0197_00810);assert(c.indirect==(MOVE_SIDE_EFFECT_ON_HIT|MOVE_SUBSCRIPT_PTR_WEATHER_START));}
  // Original temporary Hail duplicate remains; original permanent Hail restart
  // is the deliberately corrected modern difference.
  assert(!!(old.moveStatusFlag&MOVE_STATUS_FAILED)==(weather==1));
 }
 return 0;}
'''
        game.GameLogicTests.compile_run(self,source,'-iquote',str(ROOT/'files/msgdata/msg'),'-Wno-unused-function')


class SnowAISdkTests(unittest.TestCase):
    def test_assembled_ai_preserves_all_bytes_except_one_comparison_word(self):
        import snow_resources
        from battle_scripts import battle_script_tools,compile_battle_script
        try:battle_script_tools()
        except FileNotFoundError as error:self.skipTest(str(error))
        source=(ROOT/'asm/trainer_ai_data.s').read_text()
        original=compile_battle_script(source)
        modern=compile_battle_script(snow_resources.modern_snow_ai_source(source))
        expected=bytearray(original);struct.pack_into('<I',expected,5747*4,0xffffffff)
        self.assertEqual(modern,bytes(expected));self.assertEqual(struct.unpack_from('<3i',original,5746*4),(19,4,14))
