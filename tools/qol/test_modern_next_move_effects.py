"""Execute audited native effects and controller functions against original scripts."""
from pathlib import Path
import struct
import re
import unittest

import test_game_logic as game
import test_modern_moves as moves
import test_modern_rules as rules
from test_modern_next_moves import ROWS, native, ROOT, PLAYER
from nitro_data import unpack_narc

EFFECT_ARCHIVE=ROOT/'files/battledata/script/effect_script.narc'
SUB_ARCHIVE=ROOT/'files/battledata/script/subscript.narc'
EFFECTS=unpack_narc(EFFECT_ARCHIVE.read_bytes())[0] if EFFECT_ARCHIVE.exists() else []
SUBS=unpack_narc(SUB_ARCHIVE.read_bytes())[0] if SUB_ARCHIVE.exists() else []


def c_array(name,binary):
    words=struct.unpack('<'+'I'*(len(binary)//4),binary)
    return 'static const u32 '+name+'[]={'+','.join(str(w)+'u' for w in words)+'};\n'


def vm_source():
    source=moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/battle_script.h"
#include "constants/battle_subscript.h"
#include "constants/abilities.h"
#include "constants/items.h"
#include "constants/opcode.h"
#include "constants/move_effects.h"
#include "constants/message_tags.h"
#define GF_ASSERT assert
typedef int BattleSystem;
typedef struct {int hp,maxHp,ability,status,status2,moveEffectFlags,item;
 struct {int moveNoChoice;} moveEffectData;} Mon;
typedef struct {
 Mon battleMons[4];struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
 struct {int physicalDamage,specialDamage,statusFlags;} selfTurnData[4];
 unsigned sideEffectFlagsDirect,sideEffectFlagsIndirect,sideEffectFlagsAbility,moveStatusFlag,battleStatus,battleStatus2;
 unsigned fieldSideConditionFlags[2];struct {int reflectTurns,lightScreenTurns;} fieldSideConditionData[2];
 int statChangeType,statChangeParam,statChangeFlag,battlerIdStatChange,battlerIdAttacker,battlerIdTarget,
 battlerIdTemp,battlerIdAbility,tempData,multiHitCount,multiHitCountTemp,checkMultiHit,moveNoCur,calcTemp;
 const u32 *words;int pos,length,vars[70],updates,applied,message,damageCalls,criticalCalls;
} BattleContext;
static int roll,randomCalls;
static int BattleSystem_Random(BattleSystem *s){randomCalls++;return roll;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 2;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int GetBattlerAbility(BattleContext *c,int b){return c->battleMons[b].ability;}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){
 switch(side){case BATTLER_CATEGORY_ATTACKER:return c->battlerIdAttacker;
 case BATTLER_CATEGORY_DEFENDER:return c->battlerIdTarget;
 case BATTLER_CATEGORY_SIDE_EFFECT_MON:return c->battlerIdStatChange;default:assert(0);return 0;}}
static void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;assert(c->pos>=0&&c->pos<=c->length);}
static int BattleScriptReadWord(BattleContext *c){assert(c->pos<c->length);return c->words[c->pos++];}
static int *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int v){
 switch(v){case BSCRIPT_VAR_SIDE_EFFECT_FLAGS_DIRECT:return (int *)&c->sideEffectFlagsDirect;
 case BSCRIPT_VAR_SIDE_EFFECT_FLAGS_INDIRECT:return (int *)&c->sideEffectFlagsIndirect;
 case BSCRIPT_VAR_BATTLE_STATUS:return (int *)&c->battleStatus;
 case BSCRIPT_VAR_MOVE_STATUS_FLAGS:return (int *)&c->moveStatusFlag;
 case BSCRIPT_VAR_CALC_TEMP:return &c->calcTemp;
 case BSCRIPT_VAR_MOVE_NO_CUR:return &c->moveNoCur;
 default:assert(v>=0&&v<70);return &c->vars[v];}}
static int GetBattlerVar(BattleContext *c,int b,int v,void *unused){
 if(v==BMON_DATA_STATUS2)return c->battleMons[b].status2;
 if(v==BMON_DATA_HP)return c->battleMons[b].hp;
 assert(0);return 0;}
static void SetBattlerVar(BattleContext *c,int b,int v,int *value){
 assert(v==BMON_DATA_STATUS2);c->battleMons[b].status2=*value;}
static void BattlerSetAbility(BattleContext *c,int b,int v){c->battleMons[b].ability=v;}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int b){}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''+re.search(r'static const int sMoveStatusChangeScripts\[.*?\n\};', (ROOT/'src/battle/battle_util.c').read_text(), re.S)[0]+'\n'+native('Qol_GetActualStatStageDelta','GetMoveStatusChangeScript','BattlerCheckSubstitute','BattleSystem_TryIndirectSideEffect','DamageDivide')
    source+=native('BtlCmd_UpdateVar','BtlCmd_UpdateVar2','BtlCmd_CompareVarToValue','BtlCmd_CompareMonDataToValue',
                  'BtlCmd_CheckAbility','BtlCmd_Random','BtlCmd_UpdateMonDataFromVar','BtlCmd_Goto',
                  'BtlCmd_DivideVarByValue','BtlCmd_SetMultiHit','BtlCmd_TryBreakScreens',path='src/battle/battle_command.c')
    return source+r'''
// Execute the real script-control and arithmetic commands. Damage calculation,
// presentation, and HP application are explicit harness boundaries; separate
// tests execute native HpCalc, on-hit abilities, and multi-hit continuation.
static void run(BattleContext *c,const u32 *words,int length){
 c->words=words;c->length=length;c->pos=0;
 for(int steps=0;steps<100;steps++){
  switch(c->words[c->pos]){
  case 14:case 17:c->pos++;break;
  case 15:c->damageCalls++;c->pos++;break;
  case 38:c->criticalCalls++;c->pos++;break;
  case 18:{c->pos++;c->message=BattleScriptReadWord(c);int tag=BattleScriptReadWord(c);
   c->pos+=(tag>0)+(tag>TAG_TRNAME)+(tag>TAG_TRCLASS_TRNAME)+(tag>TAG_TRCLASS_TRNAME_ITEM);break;}
  case 30:c->pos+=2;break;
  case 32:BtlCmd_CompareVarToValue(NULL,c);break;
  case 33:BtlCmd_CompareMonDataToValue(NULL,c);break;
  case 49:BtlCmd_SetMultiHit(NULL,c);break;
  case 50:BtlCmd_UpdateVar(NULL,c);break;
  case 55:BtlCmd_CheckAbility(NULL,c);break;
  case 56:BtlCmd_Random(NULL,c);break;
  case 57:BtlCmd_UpdateVar2(NULL,c);break;
  case 58:BtlCmd_UpdateMonDataFromVar(NULL,c);break;
  case 59:BtlCmd_Goto(NULL,c);break;
  case 60:c->pos++;{int sub=BattleScriptReadWord(c);if(sub==BATTLE_SUBSCRIPT_UPDATE_HP){
   c->updates++;c->applied=c->vars[BSCRIPT_VAR_HP_CALC];}else assert(sub==BATTLE_SUBSCRIPT_ATTACK_MESSAGE_AND_ANIMATION);}break;
  case 85:BtlCmd_DivideVarByValue(NULL,c);break;
  case 133:BtlCmd_TryBreakScreens(NULL,c);break;
  case 224:return;
  default:assert(0);
  }
 }
 assert(0);
}
static BattleContext fixture(int move){
 BattleContext c={0};c.moveNoCur=move;c.battlerIdTarget=c.battlerIdStatChange=1;
 c.battleMons[0].hp=c.battleMons[1].hp=c.battleMons[0].maxHp=c.battleMons[1].maxHp=100;
 roll=randomCalls=0;return c;
}
#define RUN(c,a) run(c,a,sizeof(a)/sizeof(*(a)))
'''


@unittest.skipUnless(EFFECTS and SUBS, 'Needs locally supplied original battle archives')
class NextMoveEffectTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    def check(self,source):
        self.compile_run(source,'-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1',
                         '-Wno-unused-function','-Wno-sign-compare')

    def test_quarter_and_third_recoil_rounding_rock_head_reckless_substitute_ko_and_immunity(self):
        arrays=''.join(c_array('effect'+str(i),EFFECTS[i]) for i in (48,198))
        arrays+=''.join(c_array('sub'+str(i),SUBS[i]) for i in (63,147))
        self.check(vm_source()+arrays+r'''
int main(void) {
 const int damages[]={1,2,3,4,5,7,11,20,99,100};
 const int abilities[]={0,ABILITY_ROCK_HEAD,ABILITY_RECKLESS,ABILITY_MAGIC_GUARD};
 for(int move=0;move<2;move++)for(int a=0;a<4;a++)for(int d=0;d<10;d++)for(int failure=0;failure<4;failure++) {
  BattleContext c=fixture(move?837:531);c.battleMons[0].ability=abilities[a];
  // Native hitDamage is capped to actual target/Substitute HP by HpCalc.
  int damage=damages[d];if(failure==1&&damage>10)damage=10; // Substitute
  if(failure==2)c.battleMons[1].hp=0; // recoil still follows a KO
  if(failure==3)c.moveStatusFlag=MOVE_STATUS_NO_EFFECT;
  if(move)RUN(&c,effect198);else RUN(&c,effect48);
  assert(c.vars[BSCRIPT_VAR_POWER_MULTI]==(a==2?12:0));
  int script=-1;
  assert(BattleSystem_TryIndirectSideEffect(NULL,&c,&script)==(failure!=3));
  if(failure==3)continue;
  assert(script==(move?BATTLE_SUBSCRIPT_RECOIL_1_3:BATTLE_SUBSCRIPT_RECOIL_1_4));
  c.vars[BSCRIPT_VAR_HIT_DAMAGE]=-damage;
  if(move)RUN(&c,sub147);else RUN(&c,sub63);
  if(a==1||a==3)assert(!c.updates);
  else {int expected=damage/(move?3:4);if(!expected)expected=1;
   assert(c.updates==1&&c.applied==-expected&&c.message==279);}
 }
 return 0;
}
''')

    def test_fixed_two_hits_never_roll_skill_link_or_variable_hit_distribution(self):
        self.check(vm_source()+c_array('two',EFFECTS[44])+r'''
int main(void) {
 const int ids[]={533,817,891};
 for(int m=0;m<3;m++)for(int skill=0;skill<2;skill++) {
  BattleContext c=fixture(ids[m]);c.battleMons[0].ability=skill?ABILITY_SKILL_LINK:0;
  RUN(&c,two);assert(c.multiHitCount==2&&c.multiHitCountTemp==2);
  assert(!randomCalls&&c.criticalCalls==1&&c.damageCalls==1);
  c.multiHitCount=1;RUN(&c,two);assert(c.multiHitCount==1&&c.multiHitCountTemp==2);
 }
 return 0;
}
''')

    def test_native_self_stat_effects_require_a_hit_and_survive_target_ko(self):
        arrays=''.join(c_array('e'+str(i),EFFECTS[i]) for i in (138,139,229))
        self.check(vm_source()+arrays+r'''
int main(void) {
 const int ids[]={831,615,623,841};
 for(int m=0;m<4;m++)for(int fail=0;fail<4;fail++)for(int ko=0;ko<2;ko++) {
  BattleContext c=fixture(ids[m]);c.battleMons[1].hp=ko?0:100;
  c.moveStatusFlag=fail==1?MOVE_STATUS_MISSED:fail==2?MOVE_STATUS_PROTECTED:fail==3?MOVE_STATUS_NO_EFFECT:0;
  if(m==0)RUN(&c,e138);else if(m==1)RUN(&c,e139);else RUN(&c,e229);
  int script=-1;assert(BattleSystem_TryIndirectSideEffect(NULL,&c,&script)==!fail);
  if(!fail){assert(c.battlerIdStatChange==0);
   assert(script==(m<2?BATTLE_SUBSCRIPT_UPDATE_STAT_STAGE:BATTLE_SUBSCRIPT_USER_DEF_AND_SPDEF_DOWN_1_STAGE));}
 }
 return 0;
}
''')

    def test_nuzzle_dispatches_the_existing_modern_paralysis_subscript(self):
        self.check(vm_source()+c_array('nuzzle',EFFECTS[6])+r'''
int main(void) {
 BattleContext c=fixture(612);RUN(&c,nuzzle);int script=-1;
 assert(BattleSystem_TryIndirectSideEffect(NULL,&c,&script));
 assert(script==BATTLE_SUBSCRIPT_PARALYZE&&c.battlerIdStatChange==1);
 assert(c.statChangeType==SIDE_EFFECT_TYPE_INDIRECT);
 return 0;
}
''')

    def test_actual_stat_command_applies_self_boosts_and_both_defensive_drops(self):
        import test_modern_competitive as competitive
        self.check(competitive.stat_source()+r'''
int main(void) {
 const int ids[]={831,615,623,841};
 for(int move=0;move<4;move++)for(int stage=0;stage<=12;stage++) {
  BattleContext c=fixture();c.moveNoCur=ids[move];c.battlerIdStatChange=0;
  c.statChangeType=SIDE_EFFECT_TYPE_INDIRECT;c.battleMons[0].ability=0;
  c.battleMons[0].statChanges[STAT_ATK]=c.battleMons[0].statChanges[STAT_DEF]=c.battleMons[0].statChanges[STAT_SPDEF]=stage;
  if(move<2) {
   mutate(&c,move?MOVE_SUBSCRIPT_PTR_ATTACK_UP_1_STAGE:MOVE_SUBSCRIPT_PTR_DEFENSE_UP_1_STAGE);
   assert(c.battleMons[0].statChanges[move?STAT_ATK:STAT_DEF]==(stage<12?stage+1:12));
  } else {
   mutate(&c,MOVE_SUBSCRIPT_PTR_DEFENSE_DOWN_1_STAGE);
   mutate(&c,MOVE_SUBSCRIPT_PTR_SP_DEFENSE_DOWN_1_STAGE);
   assert(c.battleMons[0].statChanges[STAT_DEF]==(stage?stage-1:0));
   assert(c.battleMons[0].statChanges[STAT_SPDEF]==(stage?stage-1:0));
  }
 }
 return 0;
}
''')

    def test_raging_fury_two_or_three_turn_lock_and_native_confusion_residual(self):
        self.check(vm_source()+c_array('rampage',SUBS[44])+r'''
int main(void) {
 for(int r=0;r<8;r++) {
  BattleContext c=fixture(836);roll=r;RUN(&c,rampage);
  assert((c.battleMons[0].status2&STATUS2_RAMPAGE)==((2+(r&1))<<STATUS2_RAMPAGE_SHIFT));
  assert(c.vars[BSCRIPT_VAR_ATTACKER_LOCKED_MOVE]==836&&randomCalls==1);
 }
 return 0;
}
''')
        controller=(ROOT/PLAYER).read_text()
        residual=controller.split('        case UMC_STATE_RAMPAGE:\n',1)[1].split('        case UMC_STATE_DISABLE:',1)[0]
        source=moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/battle_subscript.h"
enum {NARC_a_0_0_1};
typedef int BattleSystem;
typedef struct {struct {int status2;} battleMons[4];
 struct {int paralysis,noEffect,imprison,infatuation,disabled,taunt,flinch,gravity,confusion;} moveFail[4];
 int battlerIdStatChange,command,commandNext,stateUpdateMonCondition,script;} BattleContext;
static void ReadBattleScriptFromNarc(BattleContext *c,int n,int script){c->script=script;}
'''+native('BattleContext_HasMoveFailed')
        source+='static void residual(BattleSystem *battleSystem,BattleContext *ctx){int battlerId=0,flag=0;switch(0){case 0:\n'+residual+'}\n(void)flag;}\n'
        source+=r'''
int main(void) {
 for(int turns=2;turns<=3;turns++)for(int failure=0;failure<2;failure++) {
  BattleContext c={0};c.battleMons[0].status2=turns<<STATUS2_RAMPAGE_SHIFT;
  c.moveFail[0].noEffect=failure;
  for(int t=1;t<=turns;t++) {
   residual(NULL,&c);
   if(failure){assert(!(c.battleMons[0].status2&STATUS2_RAMPAGE)&&!c.script);break;}
   assert((c.battleMons[0].status2&STATUS2_RAMPAGE)==((turns-t)<<STATUS2_RAMPAGE_SHIFT));
   assert(c.script==(t==turns?BATTLE_SUBSCRIPT_THRASH_END:0));
  }
 }
 return 0;
}
'''
        self.check(source)

    def test_screen_subscript_clears_both_timers_before_hp_damage(self):
        self.check(vm_source()+c_array('screens',SUBS[140])+r'''
int main(void) {
 for(int flags=0;flags<4;flags++) {
  BattleContext c=fixture(709);c.fieldSideConditionFlags[1]=(flags&1?SIDE_CONDITION_REFLECT:0)|(flags&2?SIDE_CONDITION_LIGHT_SCREEN:0);
  c.fieldSideConditionData[1].reflectTurns=5;c.fieldSideConditionData[1].lightScreenTurns=4;
  RUN(&c,screens);
  assert(!c.fieldSideConditionFlags[1]&&!c.updates);
  if(flags)assert(!c.fieldSideConditionData[1].reflectTurns&&!c.fieldSideConditionData[1].lightScreenTurns&&c.message==606);
 }
 return 0;
}
''')
        # The controller invokes direct scripts before failure/UseMove/HpCalc;
        # CalcMoveDamage explicitly excludes REMOVE_SCREENS from screen reduction.
        calc=game.function_source('src/battle/battle_util.c','CalcMoveDamage')
        self.assertEqual(calc.count('BATTLE_MOVE_DATA(ctx, moveNo).effect != MOVE_EFFECT_REMOVE_SCREENS'),2)
        direct=game.function_source(PLAYER,'BattleControllerPlayer_DirectSideEffect')
        self.assertIn('ctx->commandNext = CONTROLLER_COMMAND_26;',direct)
        self.assertIn('CONTROLLER_COMMAND_27',game.function_source(PLAYER,'BattleControllerPlayer_CheckMoveFailure'))
        self.assertIn('CONTROLLER_COMMAND_HP_CALC',game.function_source(PLAYER,'BattleControllerPlayer_UseMove'))

    def test_sdk_compilation_retains_original_effect_and_subscript_parity(self):
        import battle_scripts as scripts
        try:
            scripts.battle_script_tools()
        except FileNotFoundError as error:
            self.skipTest(str(error))
        # Every reused effect is checked, including the effects with new hooks.
        for effect in sorted({r[1] for r in ROWS}):
            with self.subTest(effect=effect):
                source=ROOT/f'files/battledata/script/effect_script/effect_script_{effect:04}.s'
                self.assertEqual(scripts.compile_battle_script(source.read_text()),EFFECTS[effect])
        for sub in (44,63,140,147,161,175):
            with self.subTest(subscript=sub):
                source=next((ROOT/'files/battledata/script/subscript').glob(f'subscript_{sub:04}_*.s'))
                self.assertEqual(scripts.compile_battle_script(source.read_text()),SUBS[sub])
