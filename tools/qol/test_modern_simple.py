"""Execute native semantic stage mutations and guarded Simple/X-item resources."""
from pathlib import Path
import hashlib
import importlib.util
import re
import struct
import unittest
from unittest.mock import patch
import test_game_logic as game
import test_modern_competitive as competitive
import test_modern_original_abilities as original
import test_modern_rules as rules

ROOT = Path(__file__).resolve().parents[2]
UTIL = 'src/battle/battle_util.c'
COMMAND = 'src/battle/battle_command.c'
PLAYER = 'src/battle/battle_controller_player.c'


def native(name, path=UTIL):
    return game.function_source(path, name) + '\n'


def stage_source():
    source = competitive.stat_source()
    if 'Qol_GetActualStatStageDelta' in (ROOT/UTIL).read_text() and 'int Qol_GetActualStatStageDelta(' not in source:
        source = source.replace('BOOL BtlCmd_ChangeStatStage(', native('Qol_GetActualStatStageDelta')+'\nBOOL BtlCmd_ChangeStatStage(', 1)
    return source


def opcode_source():
    source = stage_source()+r'''
#include "constants/opcode.h"
static int raw[4][256],operand,lastSetVar,copies;
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side) {
 if(side==BATTLER_CATEGORY_ATTACKER)return c->battlerIdAttacker;
 if(side==BATTLER_CATEGORY_MSG_TEMP)return c->battlerIdTemp;
 if(side==BATTLER_CATEGORY_SIDE_EFFECT_MON)return c->battlerIdStatChange;
 assert(0);return -1;
}
static int GetBattlerVar(BattleContext *c,int b,int var,void *unused) {
 if(var==BMON_DATA_TEMP)var=c->tempData;
 if(var>=BMON_DATA_STAT_CHANGE_ATK&&var<=BMON_DATA_STAT_CHANGE_EVASION)
  return c->battleMons[b].statChanges[1+var-BMON_DATA_STAT_CHANGE_ATK];
 return raw[b][var];
}
static void SetBattlerVar(BattleContext *c,int b,int var,void *p) {
 lastSetVar=var;if(var==BMON_DATA_TEMP)var=c->tempData;
 if(var>=BMON_DATA_STAT_CHANGE_ATK&&var<=BMON_DATA_STAT_CHANGE_EVASION)
  c->battleMons[b].statChanges[1+var-BMON_DATA_STAT_CHANGE_ATK]=(signed char)*(int *)p;
 else raw[b][var]=*(int *)p;
}
static void *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int var){return &operand;}
static void BattlerSetAbility(BattleContext *c,int b,int value){c->battleMons[b].ability=value;}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int b){copies++;}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''
    return source+native('BtlCmd_UpdateMonData',COMMAND)+native('BtlCmd_UpdateMonDataFromVar',COMMAND)


def xitem_source():
    source=opcode_source().replace('typedef int BattleSystem;', 'typedef struct BattleSystem BattleSystem;')
    source=source.replace('static int BattleSystem_GetFieldSide(', 'struct BattleSystem {BattleContext *ctx;};\nstatic int BattleSystem_GetFieldSide(',1)
    source=source.replace('statChangeType,statChangeFlag,tempData,', 'selectedMonIndex[4],statChangeType,statChangeFlag,tempData,')
    source+=r'''
#include "constants/items.h"
#include "constants/pokemon.h"
enum {HEAP_ID_BATTLE};
typedef int Pokemon;
static int moods,activeSlot=2;
static int BattleContext_Get(BattleSystem *s,BattleContext *c,int f,int b){return f==2?activeSlot:0;}
static void BattleContext_Set(BattleSystem *s,BattleContext *c,int f,int b,int val){}
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static int BattleSystem_GetBattlerType(BattleSystem *s,int b){return b;}
static int BattleSystem_GetBattlerIdPartner(BattleSystem *s,int b){return b^2;}
static Pokemon *BattleSystem_GetPartyMon(BattleSystem *s,int b,int slot){return NULL;}
static int GetMonData(Pokemon *m,int field,void *v){return 0;}
static void SetMonData(Pokemon *m,int field,void *v){}
static void AddMonData(Pokemon *m,int field,int val){}
static void AddBattlerVar(BattleContext *c,int b,int var,int delta){int v=GetBattlerVar(c,b,var,NULL)+delta;SetBattlerVar(c,b,var,&v);}
static int BallToItemId(int ball){return ball;}
static int BattleSystem_GetMonBall(BattleSystem *s,Pokemon *m){return 0;}
static int BattleSystem_GetLocation(BattleSystem *s){return 0;}
static void ApplyItemEffectOnMonMood(Pokemon *m,int item){moods++;}
static const int xitems[]={ITEM_X_ATTACK,ITEM_X_DEFENSE,ITEM_X_SPEED,ITEM_X_SPECIAL,ITEM_X_SP__DEF,ITEM_X_ACCURACY};
static const int xstats[]={STAT_ATK,STAT_DEF,STAT_SPEED,STAT_SPATK,STAT_SPDEF,STAT_ACC};
static const int xattrs[]={ITEMATTR_ATK_STAGES,ITEMATTR_DEF_STAGES,ITEMATTR_SPEED_STAGES,ITEMATTR_SPATK_STAGES,ITEMATTR_SPDEF_STAGES,ITEMATTR_ACCURACY_STAGES};
static int GetItemAttr(int item,int attr,int heap) {
 for(int i=0;i<6;i++)if(item==xitems[i])return attr==xattrs[i];
 return item==ITEM_DIRE_HIT&&attr==ITEMATTR_CRITRATE_STAGES;
}
'''
    return source+native('BattleSystem_RecoverStatus','src/battle/battle_system.c')+native('BtlCmd_UseBagItem',COMMAND)


class SimpleNativeTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def variants(self, source, *flags):
        for variant in ((), ('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source, *variant, '-Wno-unused-function', *flags)

    def test_pure_delta_all_stages_signed_changes_suppression_and_ignore(self):
        self.assertTrue('int Qol_GetActualStatStageDelta(' in (ROOT/UTIL).read_text(), 'pure stage delta helper missing')
        self.variants(stage_source()+r'''
int main(void) {
 for(int stat=1;stat<=7;stat++)for(int before=0;before<=12;before++)
 for(int base=-2;base<=2;base++)for(int ability=0;ability<2;ability++)
 for(int suppress=0;suppress<2;suppress++)for(int ignore=0;ignore<2;ignore++) {
  BattleContext c=fixture();c.battleMons[1].ability=ability?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].statChanges[stat]=before;c.battleStatus=123;c.battleStatus2=456;
  c.statChangeFlag=0x12345678;BattleContext saved=c;
  int expected=before+base*((QOL_MODERN_BATTLE&&ability&&!suppress&&!ignore)?2:1);
  if(expected<0)expected=0;if(expected>12)expected=12;
  assert(Qol_GetActualStatStageDelta(&c,1,before,base,ignore)==expected-before);
  assert(!memcmp(&c,&saved,sizeof(c)));
 }
 return 0;
}
''', '-Wno-misleading-indentation')

    def test_central_all_stats_actual_delta_messages_and_causal_mold(self):
        self.variants(stage_source()+r'''
int main(void) {
 const int bases[]={1,2,-1,-2};const int params[]={15,39,22,46};
 for(int stat=1;stat<=7;stat++)for(int before=0;before<=12;before++)
 for(int k=0;k<4;k++)for(int simple=0;simple<2;simple++)for(int suppress=0;suppress<2;suppress++)
 for(int mold=0;mold<3;mold++)for(int type=0;type<4;type++)for(int self=0;self<2;self++) {
  BattleContext c=fixture();c.battleMons[1].ability=simple?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  c.battleMons[0].moveEffectFlags=mold==2?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  if(self)c.battlerIdAttacker=1;
  c.statChangeType=type==0?SIDE_EFFECT_TYPE_DIRECT:type==1?SIDE_EFFECT_TYPE_INDIRECT:type==2?SIDE_EFFECT_TYPE_ABILITY:SIDE_EFFECT_TYPE_HELD_ITEM;
  c.battleMons[1].statChanges[stat]=before;
  int ignored=!self&&mold==1&&type<2;
  int after=before+bases[k]*((QOL_MODERN_BATTLE&&simple&&!suppress&&!ignored)?2:1);
  if(after<0)after=0;if(after>12)after=12;
  mutate(&c,params[k]+stat-1);
  assert(c.battleMons[1].statChanges[stat]==after);
  int delta=after-before;
  if(delta&&type!=2) {
   int msg;
   if(delta>0)msg=type==3?(delta>=3?1282:delta==2?759:756):(delta>=3?1276:delta==2?753:750);
   else msg=delta<=-3?1279:delta==-2?765:762;
   // Legacy wording follows the requested magnitude, including clipping and items.
   if(!QOL_MODERN_BATTLE)msg=delta>0?(type==3?756:bases[k]==1?750:753):(bases[k]==-1?762:765);
   assert(c.buffMsg.id==msg);
   assert(c.buffMsg.param[0]==101);
   assert(c.buffMsg.param[delta>0&&type==3?2:1]==stat);
  }
  if(QOL_MODERN_BATTLE&&simple&&!suppress&&ignored&&delta)assert(c.selfTurnData[0].moldBreakerFlag);
  if(!mold||mold==2||self)assert(!c.selfTurnData[0].moldBreakerFlag);
 }
 return 0;
}
''', '-Wno-misleading-indentation')

    def test_blocked_simple_drop_preserves_stages_and_does_not_announce_mold(self):
        self.variants(stage_source()+r'''
int main(void) {
 for(int reason=0;reason<3;reason++) {
  BattleContext c=fixture();c.battleMons[0].ability=ABILITY_MOLD_BREAKER;c.battleMons[1].ability=ABILITY_SIMPLE;
  if(reason==0)c.fieldSideConditionData[1].mistTurns=1;
  if(reason==1)c.battleMons[1].status2=STATUS2_SUBSTITUTE;
  if(reason==2)c.battleMons[1].statChanges[STAT_ATK]=0;
  int before=c.battleMons[1].statChanges[STAT_ATK];mutate(&c,46);
  assert(c.battleMons[1].statChanges[STAT_ATK]==before&&!c.selfTurnData[0].moldBreakerFlag);
  assert(!(c.battleStatus&BATTLE_STATUS_MOLD_BREAKER));
 }
 BattleContext c=fixture();c.battleMons[0].ability=ABILITY_MOLD_BREAKER;c.battleMons[1].ability=ABILITY_SIMPLE;
 c.battleMons[1].statChanges[STAT_ATK]=12;mutate(&c,39);assert(!c.selfTurnData[0].moldBreakerFlag);
 return 0;
}
''')

    def test_script_arithmetic_resolves_temp_signed_clips_preserves_operand_and_set(self):
        self.variants(opcode_source()+r'''
int main(void) {
 const int ops[]={OPCODE_ADD,OPCODE_SUB,OPCODE_SUB_TO_ZERO,OPCODE_SET,OPCODE_GET};
 for(int stat=0;stat<8;stat++)for(int before=0;before<=12;before++)for(int n=-2;n<=2;n++)
 for(int type=0;type<5;type++)for(int alias=0;alias<2;alias++)for(int fromvar=0;fromvar<2;fromvar++) {
  if(!fromvar&&type==4)continue;
  BattleContext c=fixture();c.battleMons[1].ability=ABILITY_SIMPLE;c.battleMons[0].ability=ABILITY_MOLD_BREAKER;
  c.battlerIdTemp=1;int var=BMON_DATA_STAT_CHANGE_HP+stat;
  c.tempData=var;if(stat)c.battleMons[1].statChanges[stat]=before;else raw[1][var]=before;
  c.battleScriptBuffer[1]=ops[type];c.battleScriptBuffer[2]=BATTLER_CATEGORY_MSG_TEMP;
  c.battleScriptBuffer[3]=alias?BMON_DATA_TEMP:var;c.battleScriptBuffer[4]=fromvar?999:n;operand=n;
  if(fromvar)BtlCmd_UpdateMonDataFromVar(NULL,&c);else BtlCmd_UpdateMonData(NULL,&c);
  int after=before,delta=type==0?n:-n;
  if(type<3) {
   after+=delta*((QOL_MODERN_BATTLE&&stat)?2:1);
   if(QOL_MODERN_BATTLE&&stat){if(after<0)after=0;if(after>12)after=12;}
   else if(type==2&&after<0)after=0;
  }else if(type==3)after=n;
  assert(GetBattlerVar(&c,1,var,NULL)==after);
  assert(operand==(type==4?before:n));
  if(type!=4)assert(lastSetVar==(alias?BMON_DATA_TEMP:var));
  assert(!c.selfTurnData[0].moldBreakerFlag);
 }
 // Clamp in int before s8 storage, including large Stockpile-style losses.
 for(int sign=-1;sign<=1;sign+=2){BattleContext c=fixture();c.battleMons[1].ability=ABILITY_SIMPLE;c.battlerIdTemp=1;
 c.battleScriptBuffer[1]=OPCODE_ADD;c.battleScriptBuffer[2]=BATTLER_CATEGORY_MSG_TEMP;
 c.battleScriptBuffer[3]=BMON_DATA_STAT_CHANGE_ATK;c.battleScriptBuffer[4]=sign*100;
 BtlCmd_UpdateMonData(NULL,&c);assert(c.battleMons[1].statChanges[1]==(QOL_MODERN_BATTLE?(sign>0?12:0):(sign>0?106:-94)));}
 return 0;
}
''', '-Wno-misleading-indentation')

    def test_xitems_six_stats_player_and_trainer_clips_noop_dire_hit(self):
        self.variants(xitem_source()+r'''
int main(void) {
 for(int i=0;i<6;i++)for(int before=0;before<=12;before++)for(int simple=0;simple<2;simple++)
 for(int suppress=0;suppress<2;suppress++)for(int trainer=0;trainer<2;trainer++)for(int wrongSlot=0;wrongSlot<2;wrongSlot++) {
  BattleContext c=fixture();BattleSystem s={&c};int stat=xstats[i];c.battlerIdAttacker=1;
  c.battleMons[0].ability=ABILITY_MOLD_BREAKER;c.battleMons[1].ability=simple?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].statChanges[stat]=before;c.itemTemp=xitems[i];c.selectedMonIndex[1]=2+wrongSlot;
  c.battleScriptBuffer[1]=BATTLER_CATEGORY_ATTACKER;int oldMoods=moods;
  int delta=QOL_MODERN_BATTLE?(simple&&!suppress?4:2):1;
  if(before+delta>12)delta=12-before;if(wrongSlot)delta=0;
  if(trainer)BtlCmd_UseBagItem(&s,&c);
  else assert(BattleSystem_RecoverStatus(&s,1,c.selectedMonIndex[1],0,xitems[i])==!!delta);
  assert(c.battleMons[1].statChanges[stat]==before+delta);
  assert(moods==oldMoods+!!delta);assert(!c.selfTurnData[0].moldBreakerFlag);
  if(QOL_MODERN_BATTLE&&trainer&&delta) {
   assert(c.buffMsg.id==(delta>=3?1282:delta==2?759:756));assert(c.buffMsg.tag==TAG_NICKNAME_ITEM_STAT);
   assert(c.buffMsg.param[0]==101&&c.buffMsg.param[1]==xitems[i]&&c.buffMsg.param[2]==stat);
  }
 }
 BattleContext c=fixture();BattleSystem s={&c};c.battleMons[1].ability=ABILITY_SIMPLE;
 assert(BattleSystem_RecoverStatus(&s,1,2,0,ITEM_DIRE_HIT));
 assert(raw[1][BMON_DATA_STATUS2]&STATUS2_FOCUS_ENERGY);
 assert(!BattleSystem_RecoverStatus(&s,1,2,0,ITEM_DIRE_HIT));
 for(int stat=1;stat<=7;stat++)assert(c.battleMons[1].statChanges[stat]==6);
 return 0;
}
''', '-Wno-misleading-indentation')

    def test_rage_native_scheduler_uses_self_delta_once_per_successful_hit(self):
        source=stage_source().replace('int moldBreakerFlag;', 'int moldBreakerFlag,statusFlags,physicalDamage,specialDamage;')
        source=source.replace('battleStatus,battleStatus2,','command,commandNext,moveStatusFlag,battleStatus,battleStatus2,')
        self.variants(source+native('TryBuildRage',PLAYER)+r'''
int main(void) {
 for(int before=0;before<=12;before++)for(int reason=0;reason<7;reason++)for(int suppress=0;suppress<2;suppress++) {
  BattleContext c=fixture();c.battleMons[1].ability=ABILITY_SIMPLE;c.battleMons[0].ability=ABILITY_MOLD_BREAKER;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].statChanges[STAT_ATK]=before;c.battleMons[1].status2=STATUS2_RAGE;
  c.selfTurnData[1].physicalDamage=10;c.command=91;
  if(reason==1)c.battlerIdTarget=BATTLER_NONE;if(reason==2)c.battleMons[1].status2=0;
  if(reason==3)c.moveStatusFlag=MOVE_STATUS_MULTI_HIT_DISRUPTED;if(reason==4)c.battlerIdAttacker=1;
  if(reason==5)c.battleMons[1].hp=0;if(reason==6)c.selfTurnData[1].physicalDamage=0; // includes Substitute absorbing the hit
  for(int hit=0;hit<4;hit++) {
   int current=c.battleMons[1].statChanges[STAT_ATK];int success=reason==0&&current<12;
   assert(TryBuildRage(NULL,&c)==success);
   if(success){current+=QOL_MODERN_BATTLE&&!suppress?2:1;if(current>12)current=12;assert(c.scriptFileId==245&&c.commandNext==(hit?CONTROLLER_COMMAND_RUN_SCRIPT:91));}
   assert(c.battleMons[1].statChanges[STAT_ATK]==current);assert(!c.selfTurnData[0].moldBreakerFlag);
  }
 }
 return 0;
}
''', '-Wno-misleading-indentation')

    def test_downstream_speed_uses_stored_stage_after_simple_loss_gain_or_suppression(self):
        source=rules.COMMON+r'''
typedef struct {int priority;} Move;
typedef struct {int hp,maxHp,speed,statChanges[8],item,species,ability,status,moveEffectFlags;
 struct {int slowStartTurns,knockOffFlag,quickClawFlag,custapBerryFlag;} moveEffectData;} Mon;
typedef struct {Mon battleMons[4];unsigned fieldCondition,fieldSideConditionFlags[2],effectiveSpeed[4];
 int totalTurns,quickClawRandom[4],movePos[4];struct {int inputSelection;} playerActions[4];
 struct {int struggleFlag;} turnData[4];struct {Move moveData[NUM_MOVES+1];int calcTemp;} trainerAIData;} BattleContext;
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return 0;}
static int GetHeldItemModifier(BattleContext *c,int b,int f){return 1;}
static int GetItemVar(BattleContext *c,int item,int f){return 0;}
static int GetBattlerVar(BattleContext *c,int b,int f,void *p){return MOVE_TACKLE;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int CheckAbilityActive(BattleSystem *s,BattleContext *c,int scope,int b,int a){return 0;}
'''+native('GetBattlerAbility')+native('Qol_GetActualStatStageDelta')+rules.array('sSpeedHalvingItemEffects')+rules.array('sStatChangeTable')+native('CheckSortSpeed')
        self.variants(source+r'''
int main(void) {
 (void)BattleSystem_Random(NULL);
 for(int stage=0;stage<=12;stage++)for(int simple=0;simple<2;simple++)for(int suppress=0;suppress<2;suppress++) {
  BattleContext c={0};for(int b=0;b<2;b++){c.battleMons[b].hp=100;c.battleMons[b].speed=101;c.battleMons[b].statChanges[3]=stage;c.battleMons[b].ability=simple?ABILITY_SIMPLE:ABILITY_NONE;c.battleMons[b].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;}
  CheckSortSpeed(NULL,&c,0,1,1);
  int effective=stage;if(!QOL_MODERN_BATTLE&&simple&&!suppress){effective=6+(stage-6)*2;if(effective<0)effective=0;if(effective>12)effective=12;}
  int expected=effective>=6?101*(effective-4)/2:101*2/(8-effective);
  assert(c.effectiveSpeed[0]==(unsigned)expected&&c.effectiveSpeed[1]==(unsigned)expected);
  assert(c.battleMons[0].statChanges[3]==stage&&c.battleMons[1].statChanges[3]==stage);
 }
 return 0;
}
''','-Wno-sign-compare','-Wno-misleading-indentation')

    def test_damage_stored_attack_and_defense_simple_never_reinterprets_or_mold_erases(self):
        source=rules.COMMON+r'''
typedef struct {int power,type,category,effect,range;} Move;
typedef struct {struct {int hp,ability;unsigned moveEffectFlags;} battleMons[4];
 struct {int helpingHandFlag;} turnData[4];struct {Move moveData[NUM_MOVES+1];int calcTemp;} trainerAIData;
 int powerMultiplier,fieldCondition;struct {int moldBreakerFlag;} selfTurnData[4];int battleStatus;} BattleContext;
static int vars[4][256];
static int GetBattlerVar(BattleContext *c,int b,int f,void *p){return vars[b][f];}
static int GetBattlerHeldItem(BattleContext *c,int b){return 0;}
static int GetItemVar(BattleContext *c,int item,int f){return 0;}
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 2;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int BattleContext_Get(BattleSystem *s,BattleContext *c,int f,int b){return 10;}
static int CheckMoveEffectOnField(BattleSystem *s,BattleContext *c,int effect){return 0;}
static int GetMonsHitCount(BattleSystem *s,BattleContext *c,int side,int b){return 1;}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''+native('GetBattlerAbility')+native('CheckBattlerAbilityIfNotIgnored')+native('CheckAbilityActive')
        util=(ROOT/UTIL).read_text()
        source+='#if QOL_MODERN_BATTLE\n'+rules.helper('Qol_HasPlusMinusAlly',UTIL)+'#endif\n'
        source+=util[util.index('typedef struct MoveDamageCalc {'):util.index('} MoveDamageCalc;')+len('} MoveDamageCalc;')]
        source+=''.join(rules.array(n) for n in ('sStatChangeTable','sTypeEnhancingItems','sPunchingMoves'))+native('Qol_MoveUsesPhysicalDefense')+native('CalcMoveDamage')
        self.variants(source+r'''
static int changed(int before,int simple) {int stage=before-6;if(!QOL_MODERN_BATTLE&&simple)stage*=2;if(stage< -6)stage=-6;if(stage>6)stage=6;return stage>=0?101*(stage+2)/2:101*2/(2-stage);}
int main(void) {
 (void)BattleSystem_Random(NULL);
 for(int category=0;category<2;category++)for(int at=0;at<=12;at++)for(int df=0;df<=12;df++)
 for(int attackerSimple=0;attackerSimple<2;attackerSimple++)for(int defenderSimple=0;defenderSimple<2;defenderSimple++)for(int suppress=0;suppress<2;suppress++)for(int mold=0;mold<2;mold++) {
  BattleContext c={0};c.powerMultiplier=10;c.battleMons[0].hp=c.battleMons[1].hp=100;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:attackerSimple?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].ability=defenderSimple?ABILITY_SIMPLE:ABILITY_NONE;
  for(int b=0;b<2;b++){c.battleMons[b].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
   vars[b][BMON_DATA_LEVEL]=50;vars[b][BMON_DATA_GENDER]=MON_GENDERLESS;
   vars[b][BMON_DATA_ATK]=vars[b][BMON_DATA_SPATK]=vars[b][BMON_DATA_DEF]=vars[b][BMON_DATA_SPDEF]=101;
   vars[b][BMON_DATA_STAT_CHANGE_ATK]=vars[b][BMON_DATA_STAT_CHANGE_SPATK]=at;
   vars[b][BMON_DATA_STAT_CHANGE_DEF]=vars[b][BMON_DATA_STAT_CHANGE_SPDEF]=df;}
  c.trainerAIData.moveData[MOVE_TACKLE]=(Move){100,TYPE_NORMAL,category,0,0};
  int a=changed(at,attackerSimple&&!mold&&!suppress),d=changed(df,defenderSimple&&(!mold||suppress)&&!suppress);
  assert(CalcMoveDamage(NULL,&c,MOVE_TACKLE,0,0,0,0,0,1,1)==a*100*22/d/50+2);
  // Modern defender Simple never asks a damage-time Mold Breaker bypass.
  if(QOL_MODERN_BATTLE)assert(!c.selfTurnData[0].moldBreakerFlag);
 }
 return 0;
}
''','-Wno-sign-compare','-Wno-misleading-indentation')

    def test_native_copy_and_haze_keep_exact_stored_stage_values(self):
        self.variants(stage_source()+native('BtlCmd_CopyStatStages',COMMAND)+native('BtlCmd_ResetAllStatChanges',COMMAND)+r'''
int main(void) {
 for(int stage=0;stage<=12;stage++)for(int simple=0;simple<2;simple++) {
  BattleContext c=fixture();c.battleMons[0].ability=simple?ABILITY_SIMPLE:ABILITY_NONE;
  for(int s=0;s<8;s++)c.battleMons[1].statChanges[s]=stage;
  BtlCmd_CopyStatStages(NULL,&c);for(int s=0;s<8;s++)assert(c.battleMons[0].statChanges[s]==stage);
  BtlCmd_ResetAllStatChanges(NULL,&c);for(int b=0;b<4;b++)for(int s=0;s<8;s++)assert(c.battleMons[b].statChanges[s]==6);
 }
 return 0;
}
''')

    def test_native_berry_selectors_rng_eligible_stats_and_white_herb_exact_reset(self):
        source=stage_source().replace('int hp,ability,moveEffectFlags,status2,statChanges[8];',
            'int hp,maxHp,item,status,ability,moveEffectFlags,status2,statChanges[8],moves[4],movePPCur[4],movePP[4],personality;')
        source=source.replace('int moldBreakerFlag;', 'int moldBreakerFlag,statusFlags;')
        source=source.replace('battleStatus,battleStatus2,','command,commandNext,hpCalc,moveTemp,movePower,flingScript,flingData,battleStatus,battleStatus2,')
        source+=r'''
#include "constants/items.h"
#include "constants/pokemon.h"
static int heldEffect,stealEffect,rolls[10],rollCount;
static int BattleSystem_Random(BattleSystem *s){assert(rollCount<10);return rolls[rollCount++];}
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return heldEffect;}
static int GetHeldItemModifier(BattleContext *c,int b,int flag){return 4;}
static int GetBattlerHeldItem(BattleContext *c,int b){return c->battleMons[b].item;}
static int GetHeldItemStealBerryEffect(BattleContext *c,int b){return stealEffect;}
static int GetHeldItemFlingEffect(BattleContext *c,int b){return stealEffect;}
static int GetHeldItemFlingPower(BattleContext *c,int b){return 10;}
static int GetFlavorPreferenceFromPID(int p,int f){return 0;}
static void BattleMon_AddVar(BattleMon *m,int f,int n){assert(0);}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int b){}
static int BattlerCheckSubstitute(BattleSystem *s,int b){assert(0);return 0;}
u8 GetMoveMaxPP(u16 move,u8 ups){return 10;}
static int ItemIdIsBerry(int item){return 1;}
'''
        # Actual BattlerCheckSubstitute has (BattleContext *,int), without system.
        source=source.replace('BattlerCheckSubstitute(BattleSystem *s,int b){assert(0);return 0;}',
            'BattlerCheckSubstitute(BattleContext *c,int b){return !!(c->battleMons[b].status2&STATUS2_SUBSTITUTE);}')
        source+=native('DamageDivide')+''.join(native(n) for n in ('TryUseHeldItem','CheckUseHeldItem','TryEatOpponentBerry','TryFling'))
        self.variants(source+r'''
int main(void) {
 for(int eligible=0;eligible<5;eligible++)for(int origin=0;origin<4;origin++)for(int allCapped=0;allCapped<2;allCapped++) {
  BattleContext c=fixture();c.battleMons[0].ability=ABILITY_MOLD_BREAKER;c.battleMons[1].ability=ABILITY_SIMPLE;
  c.battleMons[1].hp=10;c.battleMons[1].maxHp=100;c.battleMons[1].item=ITEM_STARF_BERRY;
  int holder=1;if(origin==2){c.battlerIdAttacker=1;c.battlerIdTarget=0;c.battleMons[0].item=ITEM_STARF_BERRY;}
  for(int stat=1;stat<=5;stat++)c.battleMons[holder].statChanges[stat]=12;
  if(!allCapped)c.battleMons[holder].statChanges[eligible+1]=11;
  rollCount=0;rolls[0]=(eligible+1)%5;rolls[1]=eligible;
  heldEffect=HOLD_EFFECT_PINCH_RANDOM_UP;stealEffect=STEAL_EFFECT_RANDOM_UP;u32 script=0;
  if(origin==0)assert(TryUseHeldItem(NULL,&c,1)==!allCapped);
  if(origin==1)assert(CheckUseHeldItem(NULL,&c,1,&script)==!allCapped);
  if(origin==2)assert(TryEatOpponentBerry(NULL,&c,0));
  if(origin==3)assert(TryFling(NULL,&c,0));
  assert(rollCount==(allCapped?0:2));
  if(!allCapped){assert(c.msgTemp==eligible+1);if(origin==0)assert(c.scriptFileId==210);if(origin==1)assert(script==210);if(origin==2)assert(c.tempData==210);if(origin==3)assert(c.flingScript==210);}
  // Selection does not store the semantic change; script210 applies it later.
  assert(c.battleMons[holder].statChanges[eligible+1]==(allCapped?12:11));
 }
 for(int stat=1;stat<=5;stat++)for(int origin=0;origin<4;origin++) {
  BattleContext c=fixture();c.battleMons[1].ability=ABILITY_SIMPLE;c.battleMons[1].hp=10;c.battleMons[1].maxHp=100;
  if(origin==2){c.battlerIdAttacker=1;c.battlerIdTarget=0;}
  heldEffect=HOLD_EFFECT_PINCH_ATK_UP+stat-1;stealEffect=STEAL_EFFECT_ATK_UP+stat-1;u32 script=0;rollCount=0;
  if(origin==0){assert(TryUseHeldItem(NULL,&c,1));assert(c.scriptFileId==208);}
  if(origin==1){assert(CheckUseHeldItem(NULL,&c,1,&script));assert(script==208);}
  if(origin==2){assert(TryEatOpponentBerry(NULL,&c,0));assert(c.tempData==208);}
  if(origin==3){assert(TryFling(NULL,&c,0));assert(c.flingScript==208);}
  assert(c.msgTemp==stat&&!rollCount);
 }
 // White Herb is an exact reset in all applicable native selection routes.
 for(int origin=0;origin<3;origin++) {
  BattleContext c=fixture();c.battleMons[1].ability=ABILITY_SIMPLE;c.battleMons[1].hp=10;
  int holder=1;for(int stat=0;stat<8;stat++)c.battleMons[holder].statChanges[stat]=stat+2;
  heldEffect=HOLD_EFFECT_STATDOWN_RESTORE;stealEffect=STEAL_EFFECT_RESET_STATS;
  if(origin==0)assert(TryUseHeldItem(NULL,&c,1));
  if(origin==1){u32 script;assert(CheckUseHeldItem(NULL,&c,1,&script));}
  if(origin==2)assert(TryFling(NULL,&c,0));
  for(int stat=0;stat<8;stat++)assert(c.battleMons[holder].statChanges[stat]==(stat+2<6?6:stat+2));
 }
 return 0;
}
''','-Wno-sign-compare','-Wno-misleading-indentation')

    def test_derived_accuracy_reads_stored_stages_once_after_ability_changes(self):
        self.variants(original.accuracy_source()+r'''
int main(void) {
 const int factors[]={100,75,60,50,43,36,33};
 for(int simple=0;simple<2;simple++)for(int loss=0;loss<3;loss++)for(int mold=0;mold<2;mold++)for(int accuracySimple=0;accuracySimple<2;accuracySimple++)
 for(int a=0;a<=12;a++)for(int ev=0;ev<=12;ev++)for(int roll=0;roll<100;roll++) {
  BattleContext c=fixture(MOVE_TACKLE);c.trainerAIData.moveData[MOVE_TACKLE].accuracy=40;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:accuracySimple?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].ability=simple&&loss!=1?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].moveEffectFlags=loss==2?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].statChanges[STAT_ACC]=a;c.battleMons[1].statChanges[STAT_EVASION]=ev;
  randomValue=roll;
  int stage=(a-6)*((!QOL_MODERN_BATTLE&&accuracySimple&&!mold)?2:1)+(6-ev)*((!QOL_MODERN_BATTLE&&simple&&!loss&&!mold)?2:1);
  if(stage< -6)stage=-6;if(stage>6)stage=6;
  const int positive[]={100,133,166,200,233,266,300};
  int rate=40*(stage<=0?factors[-stage]:positive[stage])/100;
  BattleSystem_CheckMoveHit(NULL,&c,0,1,MOVE_TACKLE);
  assert(!!(c.moveStatusFlag&MOVE_STATUS_MISSED)==(roll+1>rate));assert(randomCalls==1);
 }
 return 0;
}
''', '-Wno-unused-variable','-Wno-unused-but-set-variable','-Wno-sign-compare','-Wno-misleading-indentation')


class SimpleResourceTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('simple_scripts'), 'Simple resource generator missing')
        import simple_scripts
        return simple_scripts

    def test_source_guards_parity_and_only_two_existing_members_change(self):
        mod=self.module()
        import modern_rom
        from nitro_data import pack_narc,unpack_narc
        for member,(name,digest) in mod.SIMPLE_SCRIPTS.items():
            source=(ROOT/f'files/battledata/script/subscript/subscript_{member:04}_{name}.s').read_text()
            updated=mod.modern_simple_source(source,member)
            for drift in (source+'\n',updated):
                with self.assertRaisesRegex(ValueError,'expected source'):mod.modern_simple_source(drift,member)
            with patch.object(mod,'compile_battle_script',return_value=b'wrong') as compiler:
                with self.assertRaisesRegex(ValueError,'unchanged.*match'):mod.modern_simple_script(b'original',member)
                compiler.assert_called_once_with(source,mod.ROOT)
            with patch.object(mod,'compile_battle_script',side_effect=[b'original',b'modern']) as compiler:
                self.assertEqual(mod.modern_simple_script(b'original',member),b'modern')
                self.assertEqual([c.args[0] for c in compiler.call_args_list],[source,updated])
        for member in (12,208,297):
            with self.assertRaises(ValueError):mod.modern_simple_source(source,member)
        members=[struct.pack('<I',i) for i in range(299)]
        with patch('modern_rom.modern_simple_script',side_effect=lambda data,member:b'new'+data):
            after,names=unpack_narc(modern_rom.modern_simple_resources(pack_narc(members)))
        self.assertEqual(len(after),299);self.assertEqual(names,unpack_narc(pack_narc(members))[1])
        for i,before in enumerate(members):self.assertEqual(after[i],b'new'+before if i in (210,269) else before)
        for count in (298,300):
            with self.assertRaisesRegex(ValueError,'299'):modern_rom.modern_simple_resources(pack_narc((members+[b'last'])[:count]))

    def test_encoded_triplets_preserve_original_controls_key_rows_and_other_banks(self):
        mod=self.module()
        from game_text import game_text
        from nitro_data import unpack_narc,unpack_messages,pack_narc,pack_messages
        archive=(ROOT/'files/msgdata/msg.narc').read_bytes();before,names=unpack_narc(archive)
        words,key=unpack_messages(before[197]);self.assertEqual((len(words),key),(1276,47860))
        result=mod.modern_simple_message_resources(archive,ROOT/'charmap.txt')
        after,newnames=unpack_narc(result);new,newkey=unpack_messages(after[197])
        self.assertEqual(names,newnames);self.assertEqual(newkey,key);self.assertEqual(len(new),1285)
        self.assertEqual(new[:1276],words)
        for i,bank in enumerate(before):
            if i!=197:self.assertEqual(after[i],bank)
        for offset,old,literal,replacement in ((1276,753,'sharply','drastically'),(1279,765,'harshly','severely'),(1282,759,'sharply','drastically')):
            oldcodes=game_text(literal,ROOT/'charmap.txt')[:-1];newcodes=game_text(replacement,ROOT/'charmap.txt')[:-1]
            for side in range(3):
                row=words[old+side];start=next(i for i in range(len(row)) if row[i:i+len(oldcodes)]==oldcodes)
                self.assertEqual(new[offset+side],row[:start]+newcodes+row[start+len(oldcodes):])
        for mutation in ('source','key','count','control'):
            banks=list(before);bad=list(words)
            if mutation=='control':bad[753]=[1]+bad[753][1:]
            if mutation=='count':bad.append([0xffff])
            banks[197]=pack_messages(bad,key+(mutation=='key'))
            with patch.object(mod,'MESSAGE_SOURCE_SHA256','wrong') if mutation=='source' else patch.object(mod,'MESSAGE_SOURCE_SHA256',mod.MESSAGE_SOURCE_SHA256):
                with self.assertRaises(ValueError):mod.modern_simple_message_resources(pack_narc(banks,names),ROOT/'charmap.txt')
        with self.assertRaises(ValueError):mod.modern_simple_message_resources(result,ROOT/'charmap.txt')

    def test_original_stage_arithmetic_inventory_includes_dynamic_temp_alias(self):
        found=[]
        for path in (ROOT/'files/battledata/script').rglob('*.s'):
            for line in path.read_text().splitlines():
                match=re.match(r'\s*UpdateMonData(?:FromVar)?\s+(OPCODE_(?:ADD|SUB|SUB_TO_ZERO)),\s*(\w+),\s*(\w+),',line)
                if not match:continue
                op,side,dest=match.groups()
                if dest=='BMON_DATA_TEMP' or dest.startswith('BMON_DATA_STAT_CHANGE_') or dest.isdigit() and 19<=int(dest)<=25:
                    found.append((path.name,op,side,dest))
        expected=[('subscript_0121_FutureSightDamage.s','OPCODE_ADD','BATTLER_CATEGORY_MSG_TEMP','BMON_DATA_STAT_CHANGE_ATK'),
            ('subscript_0182_MotorDrive.s','OPCODE_ADD','BATTLER_CATEGORY_DEFENDER','BMON_DATA_STAT_CHANGE_SPEED'),
            ('subscript_0210_HeldItemSharplyRaiseStat.s','OPCODE_ADD','BATTLER_CATEGORY_MSG_TEMP','BMON_DATA_TEMP')]
        expected += [(f'effect_script_0{member}.s','OPCODE_SUB_TO_ZERO','BATTLER_CATEGORY_ATTACKER',f'BMON_DATA_STAT_CHANGE_{stat}') for member in (161,162) for stat in ('DEF','SPDEF')]
        self.assertEqual(sorted(found),sorted(expected),'New stage arithmetic needs a causal-source review before using the self delta hook')
        source=(ROOT/'files/battledata/script/subscript/subscript_0210_HeldItemSharplyRaiseStat.s').read_text()
        self.assertIn('BSCRIPT_VAR_TEMP_DATA, 18',source)
        self.assertIn('OPCODE_ADD, BSCRIPT_VAR_TEMP_DATA, BSCRIPT_VAR_MESSAGE',source)
        for name in ('SetBattlerVar','AddBattlerVar','BattleMon_AddVar'):
            self.assertNotIn('Qol_GetActualStatStageDelta',native(name))
        for name in ('BtlCmd_CopyStatStages','BtlCmd_ResetAllStatChanges','BtlCmd_Transform'):
            self.assertNotIn('Qol_GetActualStatStageDelta',native(name,COMMAND))
        self.assertIn('if (!(ctx->battleStatus & BATTLE_STATUS_BATON_PASS))',native('BattleSystem_GetBattleMon'))

    def test_new_adjectives_fit_battle_font_lines(self):
        from game_text import game_text
        font=(ROOT/'files/graphic/font/font_00000000.bin').read_bytes()
        widths=struct.unpack_from('<I',font,4)[0]
        # New literal runs plus the longest applicable stat/item wording; the
        # nickname line and all placeholders retain their original controls.
        for line in ('The Starf Berry drastically raised', 'Sp. Def drastically rose!', 'Sp. Def severely fell!'):
            codes=game_text(line,ROOT/'charmap.txt')[:-1]
            self.assertLessEqual(sum(font[widths+glyph-1] for glyph in codes),240)

    def test_new_triplets_use_actual_native_side_adjustment(self):
        source=r'''
#include <assert.h>
#include "constants/battle.h"
#include "constants/message_tags.h"
#define GF_ASSERT assert
#define FALSE 0
typedef unsigned int u32;
typedef struct {int type;} BattleSystem;
typedef struct {int id,tag,battlerId,param[6];} BattleMessage;
static int BattleSystem_GetBattleType(BattleSystem *s){return s->type;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
'''+native('BattleSystem_AdjustMessageForSide','src/battle/battle_system.c')+r'''
int main(void) {
 const int bases[]={1276,1279,1282};
 for(int i=0;i<3;i++)for(int side=0;side<2;side++)for(int trainer=0;trainer<2;trainer++) {
  BattleSystem s={trainer?BATTLE_TYPE_TRAINER:0};BattleMessage m={0};m.id=bases[i];
  m.tag=i==2?TAG_NICKNAME_ITEM_STAT:TAG_NICKNAME_STAT;m.param[0]=side|(4<<8);
  BattleSystem_AdjustMessageForSide(&s,&m);assert(m.id==bases[i]+side*(1+trainer));
 }
 return 0;
}
'''
        game.GameLogicTests.compile_run(self,source)

    def test_default_and_type_only_never_invoke_simple_resources(self):
        self.module()
        import modern_rom
        paths={p:(0,0,3) for p in ('a/0/0/8','a/0/2/7','a/0/6/8')}
        for types in (False,True):
            with patch('modern_rom.rom_files',return_value=paths),patch('modern_rom.modern_type_resources',return_value=(b'i',b'm')),patch('modern_rom.modern_pokedex_resources',return_value=b'd'),patch('modern_rom.modern_simple_resources') as scripts,patch('modern_rom.modern_simple_message_resources') as messages,patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:rom):
                self.assertEqual(modern_rom.make_modern_rom(b'rom',None,types=types),b'rom')
            scripts.assert_not_called();messages.assert_not_called()


class SimpleSdkTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    @classmethod
    def setUpClass(cls):
        from battle_scripts import battle_script_tools
        from nitro_data import unpack_narc
        import simple_scripts
        try: battle_script_tools()
        except FileNotFoundError as error: raise unittest.SkipTest(str(error))
        cls.original=unpack_narc((ROOT/'files/battledata/script/subscript.narc').read_bytes())[0]
        ids=(12,16,120,121,124,129,138,161,165,166,168,182,208,210,211,219,220,245,269,290)
        cls.scripts={i:cls.original[i] for i in ids}
        # Each required unchanged parity and transformed compile runs once here.
        for i in (210,269):cls.scripts[i]=simple_scripts.modern_simple_script(cls.original[i],i)
        effects=unpack_narc((ROOT/'files/battledata/script/effect_script.narc').read_bytes())[0]
        cls.scripts.update({1001:effects[161],1002:effects[162]})

    def source(self, modern=True):
        scripts=dict(self.scripts)
        if not modern:
            for i in (210,269):scripts[i]=self.original[i]
        source="#include <stdio.h>\n"+xitem_source()
        source=source.replace('int hp,ability,moveEffectFlags,status2,statChanges[8];',
            'int hp,maxHp,item,ability,moveEffectFlags,status2,statChanges[8];')
        source=source.replace('int moldBreakerFlag;', 'int moldBreakerFlag,statusFlags;')
        source=source.replace('battleStatus,battleStatus2,',
            'command,commandNext,battlerIdAbility,moveStatusFlag,critMultiplier,calcTemp,hpCalc,movePower,flingScript,flingData,sideEffectFlagsDirect,sideEffectFlagsIndirect,moveEffectChance,battlerIdMsgAttacker,battleStatus,battleStatus2,')
        source=source.replace('static int GetNarcMemberSizeByIdPair(int n,int m){return 4;}',
            'static int GetNarcMemberSizeByIdPair(int n,int m);')
        source=source.replace('static void ReadWholeNarcMemberByIdPair(void *out,int n,int m){memset(out,0,4);}',
            'static void ReadWholeNarcMemberByIdPair(void *out,int n,int m);')
        source=source.replace('if(side==BATTLER_CATEGORY_MSG_TEMP)return c->battlerIdTemp;',
            'if(side==BATTLER_CATEGORY_MSG_TEMP||side==BATTLER_CATEGORY_MSG_BATTLER_TEMP)return c->battlerIdTemp;\n if(side==BATTLER_CATEGORY_DEFENDER)return c->battlerIdTarget;')
        source=source.replace('if(var==BMON_DATA_TEMP)var=c->tempData;\n if(var>=',
            'if(var==BMON_DATA_TEMP)var=c->tempData;\n if(var==BMON_DATA_HP)return c->battleMons[b].hp;\n if(var==BMON_DATA_MAXHP)return c->battleMons[b].maxHp;\n if(var==BMON_DATA_STATUS2)return c->battleMons[b].status2;\n if(var>=',1)
        source=source.replace('else raw[b][var]=*(int *)p;',
            'else if(var==BMON_DATA_STATUS2)c->battleMons[b].status2=*(int *)p;else raw[b][var]=*(int *)p;',1)
        source=source.replace('static void *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int var){return &operand;}',r'''
static void *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int var) {
 switch(var) {
#define V(key,field) case key:return &c->field
 V(BSCRIPT_VAR_SIDE_EFFECT_TYPE,statChangeType);V(BSCRIPT_VAR_SIDE_EFFECT_PARAM,statChangeParam);
 V(BSCRIPT_VAR_BATTLE_STATUS,battleStatus);V(BSCRIPT_VAR_BATTLE_STATUS_2,battleStatus2);
 V(BSCRIPT_VAR_MOVE_STATUS_FLAGS,moveStatusFlag);V(BSCRIPT_VAR_BATTLER_STAT_CHANGE,battlerIdStatChange);
 V(BSCRIPT_VAR_BATTLER_ATTACKER,battlerIdAttacker);V(BSCRIPT_VAR_BATTLER_TARGET,battlerIdTarget);
 V(BSCRIPT_VAR_MSG_BATTLER_TEMP,battlerIdTemp);V(BSCRIPT_VAR_TEMP_DATA,tempData);V(BSCRIPT_VAR_MESSAGE,msgTemp);
 V(BSCRIPT_VAR_CALC_TEMP,calcTemp);V(BSCRIPT_VAR_HP_CALC,hpCalc);V(BSCRIPT_VAR_MOVE_POWER,movePower);
 V(BSCRIPT_VAR_FLING_SCRIPT,flingScript);V(BSCRIPT_VAR_FLING_DATA,flingData);
 V(BSCRIPT_VAR_SIDE_EFFECT_FLAGS_DIRECT,sideEffectFlagsDirect);V(BSCRIPT_VAR_SIDE_EFFECT_FLAGS_INDIRECT,sideEffectFlagsIndirect);
 V(BSCRIPT_VAR_MOVE_EFFECT_CHANCE,moveEffectChance);
#undef V
 case BSCRIPT_VAR_CRIT_MULTIPLIER:return &c->critMultiplier;
 case BSCRIPT_VAR_ATTACKER_SELF_TURN_STATUS_FLAGS:return &c->selfTurnData[c->battlerIdAttacker].statusFlags;
 default:assert(0);return NULL;
 }
}
''')
        # xitem_source's raw operand fixture is unused by the real script VM.
        source=source.replace('static int raw[4][256],operand,lastSetVar,copies;', 'static int raw[4][256],lastSetVar,copies;')
        for i,data in scripts.items():
            words=','.join(str(w)+'u' for w in struct.unpack('<'+'I'*(len(data)//4),data))
            source+=f'static const u32 script{i}[]={{ {words} }};\n'
        source+='''
static const u32 *archive(int member,int *size) {
 switch(member) {
#define M(n) case n:*size=sizeof(script##n);return script##n
'''+''.join(f'M({i});' for i in scripts)+'''
#undef M
 default:assert(0);return NULL;
 }
}
static int GetNarcMemberSizeByIdPair(int n,int m){int size;archive(m,&size);return size;}
static void ReadWholeNarcMemberByIdPair(void *out,int n,int m){int size;const u32 *p=archive(m,&size);memcpy(out,p,size);}
'''
        for name,path in [('BattleScript_Call',UTIL),('DamageDivide',UTIL)]+[(n,COMMAND) for n in
            ('BtlCmd_CheckAbility','BtlCmd_DivideVarByValue','BattleScriptGotoSubscript','BtlCmd_Call','BtlCmd_CallFromVar','BtlCmd_CompareVarToValue',
             'BtlCmd_CompareMonDataToValue','BtlCmd_CompareMonDataToVar','BtlCmd_UpdateVar',
             'BtlCmd_UpdateVar2','BtlCmd_Goto','BtlCmd_DivideVarByVar','BtlCmd_CheckSubstitute')]:
            source+=native(name,path)
        return source+r'''
static int count,events[40],tags[40],parameters[40][3],peakDepth,removals[4],stopDepth;
static int moveMissed;
static void run(BattleContext *c,int member) {
 BattleSystem system={c};int entryDepth=c->scriptStackDepth;
 stopDepth=entryDepth-1;count=0;peakDepth=entryDepth;
 ReadBattleScriptFromNarc(c,NARC_a_0_0_1,member);
 for(int step=0;step<1000;step++) {
  assert(c->scriptStackDepth<=4);if(c->scriptStackDepth>peakDepth)peakDepth=c->scriptStackDepth;
  switch(c->battleScriptBuffer[c->scriptSeqNo]) {
  case 14:case 16:case 17:case 38:c->scriptSeqNo++;break;
  case 18:{c->scriptSeqNo++;int id=BattleScriptReadWord(c),tag=BattleScriptReadWord(c);
   c->scriptSeqNo+=(tag>0)+(tag>TAG_TRNAME)+(tag>TAG_TRCLASS_TRNAME)+(tag>TAG_TRCLASS_TRNAME_ITEM);
   events[count]=id;tags[count++]=tag;break;}
  case 20:events[count]=c->buffMsg.id;tags[count]=c->buffMsg.tag;
   for(int i=0;i<3;i++)parameters[count][i]=c->buffMsg.param[i];count++;c->scriptSeqNo++;break;
  case 23:case 208:c->scriptSeqNo+=2;break;
  case 24:c->scriptSeqNo+=4;break;
  case 122:{int jump=c->battleScriptBuffer[c->scriptSeqNo+4];c->scriptSeqNo+=5;if(moveMissed)c->scriptSeqNo+=jump;break;}
  case 30:c->scriptSeqNo+=2;break;
  case 31:case 69:case 71:c->scriptSeqNo+=3;break;
  case 32:BtlCmd_CompareVarToValue(&system,c);break;
  case 33:BtlCmd_CompareMonDataToValue(&system,c);break;
  case 79:BtlCmd_CompareMonDataToVar(&system,c);break;
  case 50:BtlCmd_UpdateVar(&system,c);break;
  case 51:BtlCmd_ChangeStatStage(&system,c);break;
  case 52:BtlCmd_UpdateMonData(&system,c);break;
  case 55:BtlCmd_CheckAbility(&system,c);break;
  case 85:BtlCmd_DivideVarByValue(&system,c);break;
  case 57:BtlCmd_UpdateVar2(&system,c);break;
  case 58:BtlCmd_UpdateMonDataFromVar(&system,c);break;
  case 59:BtlCmd_Goto(&system,c);break;
  case 60:if(c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLE_SUBSCRIPT_UPDATE_HP){c->scriptSeqNo+=2;c->battleMons[c->battlerIdTemp].hp+=c->hpCalc;if(c->battleMons[c->battlerIdTemp].hp<0)c->battleMons[c->battlerIdTemp].hp=0;}
   else if(c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLE_SUBSCRIPT_HIT_SUBSTITUTE||c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLE_SUBSCRIPT_ATTACK_MESSAGE_AND_ANIMATION)c->scriptSeqNo+=2;
   else BtlCmd_Call(&system,c);break;
  case 61:BtlCmd_CallFromVar(&system,c);break;
  case 86:BtlCmd_DivideVarByVar(&system,c);break;
  case 21:{c->scriptSeqNo++;int id=BattleScriptReadWord(c),tag=BattleScriptReadWord(c);c->scriptSeqNo+=(tag>0);(void)id;break;}
  case 173:{c->scriptSeqNo+=3;c->tempData=210;c->itemTemp=c->battleMons[c->battlerIdTarget].item;c->selfTurnData[c->battlerIdAttacker].statusFlags|=SELF_TURN_FLAG_PLUCK_BERRY;break;}
  case 187:BtlCmd_UseBagItem(&system,c);break;
  case 202:{c->scriptSeqNo++;int b=BattleSystem_GetBattlerIDBySide(&system,c,BattleScriptReadWord(c));removals[b]++;c->battleMons[b].item=0;break;}
  case 210:BtlCmd_CheckSubstitute(&system,c);break;
  case 224:{int depth=c->scriptStackDepth;if(BtlCmd_EndScript(&system,c))return;
   if(c->scriptStackDepth<depth&&c->scriptStackDepth==stopDepth)return;break;}
  default:fprintf(stderr,"unhandled opcode %u in %d at %d\n",c->battleScriptBuffer[c->scriptSeqNo],c->scriptFileId,c->scriptSeqNo);assert(0);
  }
 }
 assert(0);
}
static void frames(BattleContext *c,int depth) {
 c->scriptStackDepth=depth;
 for(int d=0;d<4;d++){c->scriptStackNarcId[d]=NARC_a_0_0_1;c->scriptStackFileId[d]=129;c->scriptStackSeqNo[d]=70+d;}
}
'''

    def test_sdk_starf_held_pluck_fling_and_pinch_berry_clips_messages_consumption_and_stack(self):
        checks=r'''
int main(void) {
 for(int stat=1;stat<=5;stat++)for(int before=6;before<=11;before++)for(int simple=0;simple<2;simple++)
 for(int origin=0;origin<4;origin++)for(int depth=0;depth<3+(origin<2);depth++) {
  BattleContext c=fixture();frames(&c,depth);memset(removals,0,sizeof(removals));
  c.battleMons[0].ability=ABILITY_MOLD_BREAKER;c.battleMons[1].ability=simple?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].statChanges[stat]=before;c.msgTemp=stat;c.battlerIdTemp=1;c.itemTemp=ITEM_STARF_BERRY;c.battleMons[1].item=ITEM_STARF_BERRY;
  c.battleStatus2=0;c.statChangeType=SIDE_EFFECT_TYPE_HELD_ITEM;
  int member=origin==0?210:origin==1?208:origin==2?219:220;
  if(origin==2){c.battlerIdAttacker=1;c.battlerIdTarget=0;c.battleMons[0].item=ITEM_STARF_BERRY;c.battleMons[1].item=ITEM_LIECHI_BERRY;}
  if(origin==3){c.battlerIdAttacker=0;c.battlerIdTarget=1;c.flingScript=210;c.flingData=77;c.battleMons[1].item=ITEM_LIECHI_BERRY;c.selfTurnData[0].statusFlags=SELF_TURN_FLAG_PLUCK_BERRY;}
  run(&c,member);
  int base=origin==1?1:2,delta=base*(QOL_MODERN_BATTLE&&simple?2:1);if(before+delta>12)delta=12-before;
  assert(c.battleMons[1].statChanges[stat]==before+delta);
  int msg=QOL_MODERN_BATTLE?(delta>=3?1282:delta==2?759:756):(origin==1?756:759);
  int found=0;for(int i=0;i<count;i++)if(events[i]==msg){found++;if(QOL_MODERN_BATTLE){assert(tags[i]==TAG_NICKNAME_ITEM_STAT);assert(parameters[i][0]==101&&parameters[i][1]==ITEM_STARF_BERRY&&parameters[i][2]==stat);}}
  assert(found==1);assert(c.scriptStackDepth==(depth?depth-1:0));assert(peakDepth<=4);
  assert(peakDepth==depth+(origin<2?1:2));
  if(depth)assert(c.scriptFileId==129&&c.scriptSeqNo==70+depth-1);
  if(origin<2)assert(removals[1]==1&&c.battleMons[1].item==0);
  if(origin==2)assert(removals[0]==1&&removals[1]==0&&c.battleMons[1].item==ITEM_LIECHI_BERRY);
  if(origin==3)assert(!removals[1]&&c.battleMons[1].item==ITEM_LIECHI_BERRY);
  assert(!c.selfTurnData[0].moldBreakerFlag);
 }
 return 0;
}
'''
        for modern in (False,True):
            self.compile_run(self.source(modern)+checks,*(['-DQOL_MODERN_BATTLE=1'] if modern else []),'-Wno-unused-function','-Wno-unused-variable','-Wno-misleading-indentation','-Wno-sign-compare')

    def test_sdk_delayed_rage_uses_recipient_not_current_or_delayed_source(self):
        checks=r'''
int main(void) {
 for(int before=6;before<=12;before++)for(int suppress=0;suppress<2;suppress++)for(int sub=0;sub<2;sub++)for(int ko=0;ko<2;ko++)for(int missed=0;missed<2;missed++) {
  BattleContext c=fixture();c.battleMons[0].ability=c.battleMons[2].ability=ABILITY_MOLD_BREAKER;
  c.battlerIdMsgAttacker=2;c.battlerIdAttacker=0;c.battlerIdTemp=1;c.battleMons[1].ability=ABILITY_SIMPLE;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].hp=ko?10:100;c.battleMons[1].status2=STATUS2_RAGE|(sub?STATUS2_SUBSTITUTE:0);
  c.battleMons[1].statChanges[STAT_ATK]=before;c.hpCalc=-10;raw[1][BMON_DATA_SUBSTITUTE_HP]=20;moveMissed=missed;
  run(&c,121);int delta=missed||sub||ko?0:QOL_MODERN_BATTLE&&!suppress?2:1;if(before+delta>12)delta=12-before;
  assert(c.battleMons[1].statChanges[STAT_ATK]==before+delta);
  assert(!c.selfTurnData[0].moldBreakerFlag&&!c.selfTurnData[2].moldBreakerFlag);
  int rageMessages=0;for(int i=0;i<count;i++)if(events[i]==363)rageMessages++;
  assert(rageMessages==!!delta);
 }
 return 0;
}
'''
        for modern in (False,True):
            self.compile_run(self.source(modern)+checks,*(['-DQOL_MODERN_BATTLE=1'] if modern else []),'-Wno-unused-function','-Wno-unused-variable','-Wno-misleading-indentation','-Wno-sign-compare')

    def test_sdk_exact_swaps_belly_drum_and_two_multistat_self_drops(self):
        self.compile_run(self.source()+r'''
int main(void) {
 for(int member=165;member<=168;member++) {
  if(member==167)continue;BattleContext c=fixture();c.battleMons[0].ability=c.battleMons[1].ability=ABILITY_SIMPLE;
  int a[8],b[8];for(int stat=0;stat<8;stat++){a[stat]=stat;b[stat]=12-stat;c.battleMons[0].statChanges[stat]=a[stat];c.battleMons[1].statChanges[stat]=b[stat];}
  run(&c,member);for(int stat=1;stat<8;stat++) {
   int swap=member==168||(member==165&&(stat==STAT_ATK||stat==STAT_SPATK))||(member==166&&(stat==STAT_DEF||stat==STAT_SPDEF));
   assert(c.battleMons[0].statChanges[stat]==(swap?b[stat]:a[stat]));assert(c.battleMons[1].statChanges[stat]==(swap?a[stat]:b[stat]));
  }
 }
 for(int stage=0;stage<=11;stage++) {
  BattleContext c=fixture();c.battlerIdAttacker=1;c.battleMons[1].ability=ABILITY_SIMPLE;c.battleMons[1].maxHp=100;c.battleMons[1].statChanges[STAT_ATK]=stage;
  run(&c,120);assert(c.battleMons[1].statChanges[STAT_ATK]==12&&c.battleMons[1].hp==50);
 }
 for(int member=138;member<=161;member+=23) {
  BattleContext c=fixture();c.battlerIdAttacker=c.battlerIdStatChange=1;c.battleMons[1].ability=ABILITY_SIMPLE;
  run(&c,member);assert(c.battleMons[1].statChanges[STAT_DEF]==4);
  assert(c.battleMons[1].statChanges[member==138?STAT_ATK:STAT_SPDEF]==4);
 }
 return 0;
}
''','-DQOL_MODERN_BATTLE=1','-Wno-unused-function','-Wno-unused-variable','-Wno-misleading-indentation','-Wno-sign-compare')

    def test_sdk_trainer_xitem_message_is_actual_native_application_once(self):
        checks=r'''
int main(void) {
 for(int item=0;item<6;item++)for(int simple=0;simple<2;simple++)for(int before=6;before<=12;before++) {
  BattleContext c=fixture();c.battlerIdAttacker=1;c.battleMons[1].ability=simple?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].statChanges[xstats[item]]=before;c.selectedMonIndex[1]=2;c.itemTemp=xitems[item];
  int oldMoods=moods;run(&c,269);int delta=QOL_MODERN_BATTLE?(simple?4:2):1;if(before+delta>12)delta=12-before;
  assert(c.battleMons[1].statChanges[xstats[item]]==before+delta&&moods==oldMoods+!!delta);
  assert(count==2&&events[0]==858&&events[1]==(QOL_MODERN_BATTLE?(!delta?607:delta>=3?1282:delta==2?759:756):756));
  if(QOL_MODERN_BATTLE&&delta)assert(parameters[1][0]==101&&parameters[1][1]==xitems[item]&&parameters[1][2]==xstats[item]);
 }
 return 0;
}
'''
        for modern in (False,True):
            self.compile_run(self.source(modern)+checks,*(['-DQOL_MODERN_BATTLE=1'] if modern else []),'-Wno-unused-function','-Wno-unused-variable','-Wno-misleading-indentation','-Wno-sign-compare')

    def test_sdk_stockpile_counts_successful_events_and_current_ability_losses(self):
        self.compile_run(self.source()+r'''
int main(void) {
 for(int gained=0;gained<2;gained++)for(int consumed=0;consumed<2;consumed++)for(int move=1001;move<=1002;move++)
 for(int def=0;def<=12;def++)for(int spdef=0;spdef<=12;spdef++) {
  BattleContext c=fixture();memset(raw,0,sizeof(raw));c.battlerIdAttacker=c.battlerIdStatChange=1;c.battlerIdTemp=1;
  c.battleMons[1].ability=gained?ABILITY_SIMPLE:ABILITY_NONE;c.battleMons[1].statChanges[STAT_DEF]=def;c.battleMons[1].statChanges[STAT_SPDEF]=spdef;
  c.battleMons[1].maxHp=100;run(&c,124);
  int d=def+(gained?2:1),sd=spdef+(gained?2:1);if(d>12)d=12;if(sd>12)sd=12;
  assert(c.battleMons[1].statChanges[STAT_DEF]==d&&c.battleMons[1].statChanges[STAT_SPDEF]==sd);
  assert(raw[1][BMON_DATA_STOCKPILE_COUNT]==1&&raw[1][BMON_DATA_STOCKPILE_DEF_BOOSTS]==(def<12)&&raw[1][BMON_DATA_STOCKPILE_SPDEF_BOOSTS]==(spdef<12));
  c.battleMons[1].ability=consumed?ABILITY_SIMPLE:ABILITY_NONE;run(&c,move);
  int expected=d-(def<12)*(consumed?2:1);if(expected<0)expected=0;assert(c.battleMons[1].statChanges[STAT_DEF]==expected);
  expected=sd-(spdef<12)*(consumed?2:1);if(expected<0)expected=0;assert(c.battleMons[1].statChanges[STAT_SPDEF]==expected);
  assert(!raw[1][BMON_DATA_STOCKPILE_COUNT]&&!raw[1][BMON_DATA_STOCKPILE_DEF_BOOSTS]&&!raw[1][BMON_DATA_STOCKPILE_SPDEF_BOOSTS]);
 }
 return 0;
}
''','-DQOL_MODERN_BATTLE=1','-Wno-unused-function','-Wno-unused-variable','-Wno-misleading-indentation','-Wno-sign-compare')


if __name__ == '__main__':
    unittest.main()
