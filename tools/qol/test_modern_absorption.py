"""Modern absorbing abilities use the real battle predicate and script commands."""
from pathlib import Path
import re
import struct
import importlib
import importlib.util
import unittest
import test_game_logic as game
import test_modern_moves

ROOT=Path(__file__).resolve().parents[2]


class AbsorptionTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    def test_lightning_rod_and_storm_drain_block_damage_and_status_except_mold_breaker(self):
        util=(ROOT/'src/battle/battle_util.c').read_text()
        sounds=re.search(r'static u16 sSoundMoves\[\].*?\n\};',util,re.S)[0]
        source=test_modern_moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/abilities.h"
#include "constants/battle_subscript.h"
typedef int BattleSystem;
enum {NARC_a_0_0_1};
typedef struct {
    struct {int ability,maxHp,status;unsigned moveEffectFlags;} battleMons[4];
    struct {int moldBreakerFlag;} selfTurnData[4];
    struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
    unsigned fieldCondition,battleStatus;
    int moveType,moveNoCur,hpCalc,checkMoveImmunityState,battlerIdAttacker,battlerIdTarget,
        moveStatusFlag,command,commandNext,script;
} BattleContext;
static void ReadBattleScriptFromNarc(BattleContext *c,int narc,int script){c->script=script;}
'''+sounds+'\n'+'\n'.join(game.function_source('src/battle/battle_util.c',f) for f in (
            'GetBattlerAbility','CheckBattlerAbilityIfNotIgnored','DamageDivide',
            'BattleContext_CheckMoveImmunityFromAbility'))+'\n'+game.function_source(
            'src/battle/battle_controller_player.c','BattleControllerPlayer_CheckMoveImmunity')+r'''
int main(void) {
    const int abilities[]={ABILITY_LIGHTNINGROD,ABILITY_STORM_DRAIN};
    const int types[]={TYPE_ELECTRIC,TYPE_WATER};
    for(int a=0;a<2;a++)for(int type=0;type<18;type++)for(int status=0;status<2;status++)
    for(int mold=0;mold<2;mold++)for(int suppressed=0;suppressed<2;suppressed++)
    for(int charge=0;charge<2;charge++)for(int self=0;self<2;self++) {
        BattleContext c={0};c.moveNoCur=MOVE_WATER_GUN;
        c.trainerAIData.moveData[MOVE_WATER_GUN].type=type;
        c.trainerAIData.moveData[MOVE_WATER_GUN].power=status?0:40;
        c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
        c.battleMons[1].ability=abilities[a];
        c.battleMons[1].moveEffectFlags=suppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
        c.battleStatus=charge?BATTLE_STATUS_CHARGE_TURN:0;
        int expected=QOL_MODERN_BATTLE && type==types[a] && !mold && !suppressed && !charge && !self;
        assert(BattleContext_CheckMoveImmunityFromAbility(&c,self?1:0,1)==
            (expected?BATTLE_SUBSCRIPT_ABSORB_AND_SPEED_UP_1_STAGE:BATTLE_SUBSCRIPT_NONE));
    }
    // The actual caller sees Ground-type immunity before it checks abilities.
    for(int status=0;status<2;status++)for(int protect=0;protect<2;protect++) {
        BattleContext c={0};c.moveNoCur=status?MOVE_THUNDER_WAVE:MOVE_THUNDERBOLT;
        c.battlerIdTarget=1;c.battleMons[1].ability=ABILITY_LIGHTNINGROD;
        c.trainerAIData.moveData[c.moveNoCur].type=TYPE_ELECTRIC;
        c.trainerAIData.moveData[c.moveNoCur].power=status?0:90;
        c.moveStatusFlag=MOVE_STATUS_NO_EFFECT|(protect?MOVE_STATUS_PROTECTED:0);
        int expected=QOL_MODERN_BATTLE&&!protect;
        assert(BattleControllerPlayer_CheckMoveImmunity(NULL,&c)==expected);
        if(expected) {
            assert(c.script==182 && c.command==CONTROLLER_COMMAND_RUN_SCRIPT);
            assert(c.moveStatusFlag&MOVE_STATUS_NO_MORE_WORK);
            assert(!(c.moveStatusFlag&MOVE_STATUS_NO_EFFECT));
        } else assert(c.script==0);
    }
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source,*flags,'-Wno-sign-compare','-Wno-unused-variable')

    def test_absorption_script_keeps_motor_drive_and_adds_sp_attack_paths(self):
        self.assertIsNotNone(importlib.util.find_spec('absorption_scripts'),'modern absorption script module is missing')
        scripts=importlib.import_module('absorption_scripts')
        source=(ROOT/'files/battledata/script/subscript/subscript_0182_MotorDrive.s').read_text()
        updated=scripts.modern_absorption_source(source)
        for ability in ('LIGHTNINGROD','STORM_DRAIN'):
            self.assertIn(f'CheckAbility CHECK_OPCODE_HAVE, BATTLER_CATEGORY_DEFENDER, ABILITY_{ability}, _QolSpAttack',updated)
        prefix=updated.split('\n_QolSpAttack:\n')[0]
        checks=''.join(f'    CheckAbility CHECK_OPCODE_HAVE, BATTLER_CATEGORY_DEFENDER, ABILITY_{ability}, _QolSpAttack\n'
                       for ability in ('LIGHTNINGROD','STORM_DRAIN'))
        self.assertEqual(prefix.replace(checks,''),source)
        self.assertIn('BMON_DATA_STAT_CHANGE_SPATK, 1',updated)
        self.assertIn('BSCRIPT_VAR_MESSAGE, 4',updated)
        for changed in (source+'\n',source.replace('BMON_DATA_STAT_CHANGE_SPEED','BMON_DATA_STAT_CHANGE_ATK'),updated):
            with self.assertRaises(ValueError):scripts.modern_absorption_source(changed)

    def test_absorption_script_refuses_compiler_profile_mismatch(self):
        from unittest.mock import patch
        self.assertIsNotNone(importlib.util.find_spec('absorption_scripts'),'modern absorption script module is missing')
        scripts=importlib.import_module('absorption_scripts')
        with patch.object(scripts,'compile_battle_script',return_value=b'wrong') as compiler:
            with self.assertRaisesRegex(ValueError,'unchanged.*match.*182'):
                scripts.modern_absorption_script(b'original')
        self.assertEqual(compiler.call_count,1)

    def test_absorption_archive_changes_only_member_182(self):
        from unittest.mock import patch
        import modern_rom
        from nitro_data import pack_narc,unpack_narc
        self.assertTrue(callable(getattr(modern_rom,'modern_absorption_resources',None)), 'absorption archive integration missing')
        members=[bytes([i%256])*4 for i in range(300)]
        with patch('modern_rom.modern_absorption_script',return_value=b'absorption') as compiler:
            result,_=unpack_narc(modern_rom.modern_absorption_resources(pack_narc(members)))
        compiler.assert_called_once_with(members[182])
        self.assertEqual(result[:182],members[:182]);self.assertEqual(result[182],b'absorption')
        self.assertEqual(result[183:],members[183:])

    def test_battle_rules_requires_absorption_transform_after_weather(self):
        from unittest.mock import patch
        import modern_rom
        with patch('modern_rom.rom_files',return_value={'a/0/0/1':(0,0,3),'a/0/2/7':(1,0,3),'a/0/3/0':(2,0,3)}), \
             patch('modern_rom.modern_battle_resources',return_value=b'numeric'), \
             patch('modern_rom.modern_paralysis_resources',return_value=b'electric'), \
             patch('modern_rom.modern_weather_resources',return_value=b'finite'), \
             patch('modern_rom.modern_absorption_resources',return_value=b'absorption') as absorb, \
             patch('modern_rom.modern_sturdy_resources',side_effect=lambda data:data), patch('modern_rom.modern_cursed_body_resources',side_effect=lambda data:data), patch('modern_rom.modern_competitive_resources',side_effect=lambda data:data), patch('modern_rom.modern_oblivious_intimidate_resources',side_effect=lambda data:data), patch('modern_rom.modern_simple_resources',side_effect=lambda data:data), patch('modern_rom.modern_simple_message_resources',side_effect=lambda data,charmap:data), patch('modern_rom.modern_snow_message_resources',side_effect=lambda data,charmap:data), patch('modern_rom.modern_soul_dew_message_resources',side_effect=lambda data,charmap:data), patch('modern_rom.modern_snow_effect_resources',return_value=b'snow'), \
             patch('modern_rom.modern_ability_description_resources',return_value=b'abilities'), \
             patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:replacements):
            result=modern_rom.make_modern_rom(b'rom',None,types=False,battle_rules=True)
        absorb.assert_called_once_with(b'finite')
        self.assertEqual(result,{'a/0/0/1':b'absorption','a/0/2/7':b'abilities','a/0/3/0':b'snow'})

    def test_preview_and_ai_recognize_the_same_new_absorption_immunities(self):
        util=(ROOT/'src/battle/battle_util.c').read_text()
        arrays='\n'.join(re.search(r'static (?:const )?u(?:8|16) '+name+r'\[.*?\n\};',util,re.S)[0]
                         for name in ('sTypeEffectiveness','sSoundMoves','sFixedDamageMoveEffects'))
        source=test_modern_moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/abilities.h"
#include "constants/items.h"
#include "constants/move_effects.h"
typedef struct {
    int hp,type1,type2,ability,itemEffect;
    unsigned status,status2,moveEffectFlags;
    struct {int magnetRiseTurns;} moveEffectData;
} Mon;
typedef struct {
    Mon battleMons[4];struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
    unsigned fieldCondition,battleStatus;struct {int roostFlag;} turnData[4];
} BattleContext;
static int GetBattlerHeldItemEffect(BattleContext *c,int id){return c->battleMons[id].itemEffect;}
static int GetBattlerVar(BattleContext *c,int id,int field,void *out){return field==BMON_DATA_TYPE_1?c->battleMons[id].type1:c->battleMons[id].type2;}
'''+arrays+'\n'+'\n'.join(game.function_source('src/battle/battle_util.c',f) for f in (
            'GetBattlerAbility','CheckChargeMoveHitTurn','CheckFlyingImmunity','ApplyEffectivenessFlags',
            'BattleSystem_IsTypeMatchupActive','IsFixedDamageMove','Qol_PreviewTypeEffectiveness','CalcTypeEffectivenessFlags'))+r'''
int main(void) {
    const int abilities[]={ABILITY_LIGHTNINGROD,ABILITY_STORM_DRAIN};
    const int types[]={TYPE_ELECTRIC,TYPE_WATER};
    for(int a=0;a<2;a++)for(int move=0;move<2;move++)for(int mold=0;mold<2;mold++)for(int suppress=0;suppress<2;suppress++) {
        BattleContext c={0};c.battleMons[0].hp=c.battleMons[1].hp=100;
        c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
        c.battleMons[1].ability=abilities[a];c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
        c.trainerAIData.moveData[MOVE_WATER_GUN].type=types[move];
        c.trainerAIData.moveData[MOVE_WATER_GUN].power=40;
        c.trainerAIData.moveData[MOVE_WATER_GUN].category=CATEGORY_SPECIAL;
        int immune=QOL_MODERN_BATTLE && a==move && !mold && !suppress;
        BattleContext before=c;
        assert(Qol_PreviewTypeEffectiveness(&c,MOVE_WATER_GUN,0,1)==(immune?0:40));
        u32 flags=0;CalcTypeEffectivenessFlags(&c,MOVE_WATER_GUN,0,GetBattlerAbility(&c,0),GetBattlerAbility(&c,1),0,TYPE_NORMAL,TYPE_NORMAL,&flags);
        assert(flags==(immune?MOVE_STATUS_NO_EFFECT:0));
        assert(!memcmp(&c,&before,sizeof(c)));
    }
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source,*flags,'-Wno-sign-compare')

    def test_redirect_absorption_skips_accuracy_rng_and_micle_consumption(self):
        controller=(ROOT/'src/battle/battle_controller_player.c').read_text()
        table=re.search(r'static const u\d+ sHitChanceTable\[.*?\n\};',controller,re.S)[0]
        source=test_modern_moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/abilities.h"
#include "constants/items.h"
#include "constants/move_effects.h"
typedef int BattleSystem;
typedef struct {
    struct {int ability,statChanges[8];unsigned status2,moveEffectFlags;struct {int micleBerryFlag;} moveEffectData;} battleMons[4];
    struct {int moldBreakerFlag;} selfTurnData[4];
    struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
    unsigned fieldCondition,battleStatus,moveStatusFlag;int moveType;
} BattleContext;
static int randomCalls;
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static int CheckAbilityActive(BattleSystem *s,BattleContext *c,int mode,int mon,int ability){return 0;}
static int GetBattlerHeldItemEffect(BattleContext *c,int id){return 0;}
static int GetHeldItemModifier(BattleContext *c,int id,int unused){return 0;}
static int BattleContext_IsActionDone(BattleContext *c,int id){return 0;}
static int BattleSystem_Random(BattleSystem *s){randomCalls++;return 99;}
'''+table+'\n'+'\n'.join(game.function_source('src/battle/battle_util.c',f) for f in (
            'GetBattlerAbility','CheckBattlerAbilityIfNotIgnored'))+'\n'+game.function_source(
            'src/battle/battle_controller_player.c','BattleSystem_CheckMoveHit')+r'''
int main(void) {
    const int abilities[]={ABILITY_LIGHTNINGROD,ABILITY_STORM_DRAIN};
    const int types[]={TYPE_ELECTRIC,TYPE_WATER};
    for(int a=0;a<2;a++)for(int type=0;type<2;type++)for(int mold=0;mold<2;mold++)for(int suppress=0;suppress<2;suppress++) {
        BattleContext c={0};c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
        c.battleMons[1].ability=abilities[a];c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
        for(int i=0;i<8;i++)c.battleMons[0].statChanges[i]=c.battleMons[1].statChanges[i]=6;
        c.trainerAIData.moveData[MOVE_THUNDER_WAVE].type=types[type];
        c.trainerAIData.moveData[MOVE_THUNDER_WAVE].accuracy=50;
        c.trainerAIData.moveData[MOVE_THUNDER_WAVE].category=CATEGORY_STATUS;
        c.battleMons[0].moveEffectData.micleBerryFlag=1;randomCalls=0;
        int absorbed=QOL_MODERN_BATTLE && a==type && !mold && !suppress;
        assert(!BattleSystem_CheckMoveHit(NULL,&c,0,1,MOVE_THUNDER_WAVE));
        assert(randomCalls==!absorbed);
        assert(c.battleMons[0].moveEffectData.micleBerryFlag==absorbed);
        assert((!!(c.moveStatusFlag&MOVE_STATUS_MISSED))==!absorbed);
    }
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source,*flags,'-Wno-unused-but-set-variable')


class AbsorptionSdkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import absorption_scripts as scripts
        from battle_scripts import battle_script_tools
        from nitro_data import unpack_narc
        try:
            battle_script_tools()
        except FileNotFoundError as error:
            raise unittest.SkipTest(str(error))
        archive=ROOT/'files/battledata/script/subscript.narc'
        if not archive.is_file():
            raise unittest.SkipTest('Original battle subscript archive is absent')
        cls.original=unpack_narc(archive.read_bytes())[0][182]
        cls.modern=scripts.modern_absorption_script(cls.original)

    def test_compiled_branch_executes_real_stat_commands_and_preserves_motor_drive(self):
        def words(data):
            return ','.join(str(v)+'u' for v in struct.unpack('<'+'I'*(len(data)//4),data))
        declarations=r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "constants/battle.h"
#include "constants/battle_script.h"
#include "constants/abilities.h"
#include "constants/opcode.h"
#include "constants/message_tags.h"
typedef int BOOL;typedef uint32_t u32;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
typedef int BattleSystem;
typedef struct {
    const u32 *words;int pos,length,vars[70],ability,battlerIdAbility,stages[32],message,tempData;
} BattleContext;
static void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;assert(c->pos>=0&&c->pos<=c->length);}
static int BattleScriptReadWord(BattleContext *c){assert(c->pos<c->length);return c->words[c->pos++];}
static int *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int v){assert(v>=0&&v<70);return &c->vars[v];}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){assert(side==BATTLER_CATEGORY_DEFENDER);return 1;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 2;}
static int GetBattlerAbility(BattleContext *c,int id){return id==1?c->ability:ABILITY_NONE;}
static int GetBattlerVar(BattleContext *c,int id,int field,void *out){assert(id==1&&field>=0&&field<32);return c->stages[field];}
static void SetBattlerVar(BattleContext *c,int id,int field,int *value){assert(id==1&&field>=0&&field<32);c->stages[field]=*value;}
static void BattlerSetAbility(BattleContext *c,int id,int value){assert(0);}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int id){}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''
        functions=game.function_source('src/battle/battle_util.c','Qol_GetActualStatStageDelta')+'\n'+'\n'.join(game.function_source('src/battle/battle_command.c',f) for f in (
            'BtlCmd_CompareMonDataToValue','BtlCmd_CheckAbility','BtlCmd_UpdateMonData','BtlCmd_UpdateVar'))
        checks=r'''
static const u32 original[]={ORIGINAL};
static const u32 modern[]={MODERN};
static BattleContext run(int updated,int ability,int speed,int spa) {
    BattleContext c={0};c.words=updated?modern:original;
    c.length=updated?sizeof(modern)/4:sizeof(original)/4;
    c.ability=ability;c.stages[BMON_DATA_STAT_CHANGE_SPEED]=speed;c.stages[BMON_DATA_STAT_CHANGE_SPATK]=spa;
    for(int steps=0;steps<100;steps++) {
        assert(c.pos<c.length);
        switch(c.words[c.pos]) {
        case 14:case 17:c.pos++;break;
        case 18:{c.pos++;c.message=BattleScriptReadWord(&c);int tag=BattleScriptReadWord(&c);
            c.pos+=(tag>0)+(tag>TAG_TRNAME)+(tag>TAG_TRCLASS_TRNAME)+(tag>TAG_TRCLASS_TRNAME_ITEM);break;}
        case 30:c.pos+=2;break;
        case 33:BtlCmd_CompareMonDataToValue(NULL,&c);break;
        case 50:BtlCmd_UpdateVar(NULL,&c);break;
        case 52:BtlCmd_UpdateMonData(NULL,&c);break;
        case 55:BtlCmd_CheckAbility(NULL,&c);break;
        case 69:c.pos+=3;break;
        case 224:return c;
        default:assert(0);
        }
    }
    assert(0);return c;
}
int main(void) {
    const int abilities[]={ABILITY_MOTOR_DRIVE,ABILITY_LIGHTNINGROD,ABILITY_STORM_DRAIN};
    for(int a=0;a<3;a++)for(int speed=0;speed<=12;speed++)for(int spa=0;spa<=12;spa++) {
        BattleContext c=run(1,abilities[a],speed,spa);
        int stage=a?spa:speed;
        assert(c.stages[BMON_DATA_STAT_CHANGE_SPEED]==speed+(!a&&speed<12));
        assert(c.stages[BMON_DATA_STAT_CHANGE_SPATK]==spa+(a&&spa<12));
        assert(c.message==(stage==12?638:622));
        if(stage<12)assert(c.vars[BSCRIPT_VAR_MESSAGE]==(a?4:3));
        if(!a) {
            BattleContext old=run(0,abilities[a],speed,spa);
            assert(!memcmp(old.vars,c.vars,sizeof(c.vars)));
            assert(!memcmp(old.stages,c.stages,sizeof(c.stages)));
            assert(old.message==c.message);
        }
    }
    return 0;
}
'''.replace('ORIGINAL',words(self.original)).replace('MODERN',words(self.modern))
        game.GameLogicTests.compile_run(self,declarations+functions+checks)


if __name__=='__main__':
    unittest.main()
