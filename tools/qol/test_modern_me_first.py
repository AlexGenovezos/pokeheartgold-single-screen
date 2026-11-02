"""D2a2: real command provenance, Me First BP ownership and compatibility."""
import itertools
import re
import subprocess
import tempfile
import unittest
import struct
from pathlib import Path

import test_game_logic as game
import test_modern_base_power as bp
import test_modern_selected_stats as selected
import test_modern_snow as snow
import test_modern_rules as rules

COMMAND = 'src/battle/battle_command.c'
BASELINE = '25716c38fdd369c03fa17b50fa294c640c363107'


def function(text, name):
    match = re.search(r'^[\w *]+\b' + re.escape(name) + r'\([^;{}]*\)\s*\{', text, re.M)
    if not match:
        raise AssertionError('missing function: ' + name)
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end]


def baseline(path):
    return subprocess.check_output(['git', 'show', BASELINE + ':' + path], text=True)


def old_formula():
    old = baseline('src/battle/battle_util.c')
    return ('#if QOL_MODERN_BATTLE\n' + function(old, 'Qol_ModernBasePower').replace(
        'Qol_ModernBasePower', 'BaselineBasePower') + '\n#endif\n' +
        function(old, 'CalcMoveDamage').replace('CalcMoveDamage', 'BaselineDamage').replace(
            'Qol_ModernBasePower', 'BaselineBasePower') + '\n')


def command_source():
    s = bp.source()
    s = s.replace('int embargoFlag;', 'int embargoFlag,metronomeTurns;')
    s = s.replace('int powerMultiplier,fieldCondition;', '''int powerMultiplier,fieldCondition;
 int damage,criticalMultiplier,battlerIdAttacker,battlerIdTarget,moveType,moveNoCur,movePower;
 int fieldSideConditionFlags[2];''')
    return s + r'''
static int scriptPosition;
static void BattleScriptIncrementPointer(BattleContext *c,int n){scriptPosition+=n;}
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return items[b];}
static int GetHeldItemModifier(BattleContext *c,int b,int n){return itemMod;}
''' + ''.join(snow.native(n) for n in ('ApplyDamageRange',)) + ''.join(
        snow.native(n, COMMAND) for n in ('Qol_ApplyCriticalDamage', 'DamageCalcDefault',
                                         'BtlCmd_CalcDamage', 'BtlCmd_CalcDamageRaw')) + r'''
static void commandFixture(BattleContext *c,int power){
 bpFixture(c,MOVE_EMBER,power,TYPE_FIRE,CATEGORY_SPECIAL,0);
 c->moveNoCur=MOVE_EMBER;c->battlerIdTarget=1;c->criticalMultiplier=1;
 c->battleMons[0].ability=ABILITY_TECHNICIAN;
 c->battleMons[0].moveEffectData.meFirstFlag=1;
 c->battleMons[0].moveEffectData.meFirstCount=1;c->meFirstTotal=1;
}
'''


def route_source():
    s = command_source()
    s = s.replace('assert(field==MON_DATA_SPECIES);return *mon;',
                  'if(field==MON_DATA_LEVEL)return 50;if(field==MON_DATA_FORM)return 0;return *mon;')
    s = s.replace('int hp,ability,status,item,statChanges[8];',
                  'int hp,ability,status,item,statChanges[8],moves[4],movePPCur[4],species,form;')
    s = s.replace('int embargoFlag,metronomeTurns;',
                  'int embargoFlag,metronomeTurns,encoredMove,encoredMoveIndex,moveNoChoice;')
    s = s.replace('int helpingHandFlag;', 'int helpingHandFlag,struggleFlag;')
    s = s.replace('int fieldSideConditionFlags[2];', '''int fieldSideConditionFlags[2];
 struct {int command,battlerIdTarget;} playerActions[4];
 int moveTemp,commandNext,battlerIdSwitch,moveNoBattlerPrev[4];u32 moveStatusFlag;
 struct {int futureSightTurns[4],futureSightMoveNo[4],battlerIdFutureSight[4],futureSightDamage[4];} fieldConditionData;
 int multiHitCountTemp,checkMultiHit,beatUpCount,multiHitCount;
 struct {int id,tag,param[4];} buffMsg;''')
    return s + r'''
#include "constants/battle_script.h"
#include "constants/opcode.h"
enum {NARC_a_0_0_1,NARC_a_0_0_0,msg_0197_00481,TAG_NICKNAME};
static int readWord=7,jumpArchive,jumpMember,copies;
static const u32 *scriptWords;
static int BattleScriptReadWord(BattleContext *c){return scriptWords?scriptWords[scriptPosition++]:readWord;}
static int *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int var){assert(var==BSCRIPT_VAR_POWER_MULTI);return &c->powerMultiplier;}
static int GetBattlerSelectedMove(BattleContext *c,int b){return c->battleMons[b].moves[0];}
static int BattleSystem_GetMoveTarget(BattleSystem *s,BattleContext *c,int b,u16 move,int x,int y){return c->battlerIdTarget;}
static void BattleSystem_TryRedirectMoveTarget(BattleSystem *s,BattleContext *c,int b,int move){}
static void BattleScriptJump(BattleContext *c,int archive,int member){jumpArchive=archive;jumpMember=member;}
static int CheckTruant(BattleContext *c,int b){return 0;}
static int BattleMon_GetMoveIndex(Mon *m,int move){for(int i=0;i<4;i++)if(m->moves[i]==move)return i;assert(0);return 0;}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int b){copies++;}
static int BattleSystem_GetPartySize(BattleSystem *s,int b){return 1;}
static int GetMonBaseStat_HandleAlternateForm(int species,int form,int attr){return 100;}
''' + rules.array('sMeFirstUnuseableMoves') + ''.join(snow.native(n) for n in (
        'CheckLegalMeFirstMove', 'BattleContext_ResetMoveStatus')) + ''.join(
        snow.native(n, COMMAND) for n in ('BtlCmd_TryMeFirst', 'BtlCmd_GoToMoveScript',
                                         'BtlCmd_TryPursuit', 'BtlCmd_TryFutureSight', 'BtlCmd_BeatUp', 'BtlCmd_UpdateVar')) + r'''
static void acquisitionFixture(BattleContext *c){
 commandFixture(c,40);c->battleMons[0].moveEffectData.meFirstFlag=0;
 c->battleMons[0].moveEffectData.meFirstCount=0;
 c->battleMons[1].moves[0]=MOVE_EMBER;
 // Distinct native banned effects, independent of the candidate's effect.
 for(unsigned i=0;i<NELEMS(sMeFirstUnuseableMoves);i++)
  c->trainerAIData.moveData[sMeFirstUnuseableMoves[i]].effect=100+i;
 scriptPosition=copies=0;readWord=7;scriptWords=NULL;
}
'''


class MeFirstRouteTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run
    variants = selected.SelectedStatTests.variants

    def test_actual_command_native_ember_and_grouped_41_discriminators(self):
        self.variants(command_source() + r'''
int main(void){
 BattleContext c;commandFixture(&c,40);
 vars[0][BMON_DATA_SPATK]=100;int before=rngCalls;
 BtlCmd_CalcDamageRaw(NULL,&c);
 assert(c.damage==-(QOL_MODERN_BATTLE?41:42));
 assert(rngCalls==before&&c.meFirstTotal==1);
 assert(c.battleMons[0].moveEffectData.meFirstFlag==1);
 assert(c.battleMons[0].moveEffectData.meFirstCount==0);
 commandFixture(&c,41);BtlCmd_CalcDamageRaw(NULL,&c);
 assert(c.damage==-(QOL_MODERN_BATTLE?2026:2016));
 return 0;}
''')

    def test_pure_predicate_normalization_future_counts_and_wide_math(self):
        self.variants(command_source() + r'''
#include <limits.h>
int main(void){
 const int pairs[][2]={{1,1},{1,0},{2,1},{3,1},{0,1},{-4,-4},{-3,-5},
  {INT_MIN,INT_MIN},{INT_MAX,INT_MIN},{INT_MIN,INT_MAX},{INT_MAX,INT_MAX}};
 for(int flag=0;flag<2;flag++)for(unsigned i=0;i<NELEMS(pairs);i++){
  int total=pairs[i][0],count=pairs[i][1];BattleContext c;commandFixture(&c,41);
  c.meFirstTotal=total;c.battleMons[0].moveEffectData.meFirstCount=count;
  c.battleMons[0].moveEffectData.meFirstFlag=flag;BattleContext copy=c;int before=rngCalls;
  // Independent branching oracle; never run corrupted counters in execution.
  s64 delta=(s64)total-(s64)count;if(total==count)delta++;
  assert(Qol_IsMeFirstEligible(flag,total,count)==(flag&&delta<2));
  assert(!memcmp(&c,&copy,sizeof(c))&&before==rngCalls);
 }
 return 0;}
''')

    def test_explicit_origin_public_abi_and_no_ambient_inference(self):
        self.variants(command_source() + r'''
int main(void){
 int (*publicAbi)(BattleSystem *,BattleContext *,u32,u32,u32,u16,u8,u8,u8,u8)=CalcMoveDamage;
 for(int flag=0;flag<2;flag++)for(int current=0;current<2;current++)
 for(int origin=0;origin<2;origin++)for(int eligible=0;eligible<2;eligible++){
  BattleContext c;commandFixture(&c,41);c.moveNoCur=current?MOVE_ME_FIRST:MOVE_EMBER;
  c.battleMons[0].moveEffectData.meFirstFlag=flag;c.damage=-777;c.movePower=41;
  BattleContext copy=c;int before=rngCalls;
  assert(publicAbi(NULL,&c,MOVE_EMBER,0,0,41,0,0,1,1)==1344);
  assert(Qol_CalcMoveDamageInternal(NULL,&c,MOVE_EMBER,0,0,41,0,0,1,1,
   (QolDamageOrigin)origin,eligible)==(QOL_MODERN_BATTLE&&origin&&eligible?2026:1344));
  assert(!memcmp(&c,&copy,sizeof(c))&&rngCalls==before);
 }
#if QOL_MODERN_BATTLE
 assert(Qol_ChainStatModifier(6144,6144)==9216);
 assert(Qol_ApplyStatModifier(41,9216)==92);
 assert(Qol_ApplyStatModifier(Qol_ApplyStatModifier(41,6144),6144)==91);
#endif
 return 0;}
''')

    def test_real_commands_all_rolls_crits_slots_repeats_expiry_and_reset(self):
        self.variants(route_source() + r'''
int main(void){
 for(int attacker=0;attacker<4;attacker++)for(int raw=0;raw<2;raw++)
 for(int roll=0;roll<16;roll++)for(int crit=1;crit<=3;crit++){
  BattleContext c;commandFixture(&c,40);c.battleMons[0].ability=0;
  int target=(attacker+1)%4;c.battlerIdAttacker=attacker;c.battlerIdTarget=target;
  c.battleMons[attacker].ability=ABILITY_TECHNICIAN;
  c.battleMons[attacker].moveEffectData.meFirstFlag=1;
  c.battleMons[attacker].moveEffectData.meFirstCount=1;
  vars[attacker][BMON_DATA_SPATK]=100;vars[target][BMON_DATA_SPDEF]=100;
  int before=rngCalls;c.criticalMultiplier=crit;rng=roll;
  int expected=QOL_MODERN_BATTLE?41:28;
  expected=QOL_MODERN_BATTLE&&crit>1?expected*3/2:expected*crit;
  if(!QOL_MODERN_BATTLE)expected=expected*15/10;
  for(int hit=0;hit<3;hit++){
   if(raw)BtlCmd_CalcDamageRaw(NULL,&c);else BtlCmd_CalcDamage(NULL,&c);
   assert(c.damage==-(raw?expected:expected*(100-roll)/100));
   assert(c.battleMons[attacker].moveEffectData.meFirstCount==0);
   assert(c.battleMons[attacker].moveEffectData.meFirstFlag==1&&c.meFirstTotal==1);
   assert(rngCalls==before+(raw?0:hit+1));
   BattleContext_ResetMoveStatus(NULL,&c);c.criticalMultiplier=crit;
   assert(c.battleMons[attacker].moveEffectData.meFirstFlag==1);
   assert(c.battleMons[attacker].moveEffectData.meFirstCount==0);
  }
  c.meFirstTotal++;c.criticalMultiplier=1;
  BtlCmd_CalcDamageRaw(NULL,&c);assert(c.damage==-28);
  assert(!c.battleMons[attacker].moveEffectData.meFirstFlag);
  assert(c.battleMons[attacker].moveEffectData.meFirstCount==0);
 }
 return 0;}
''')

    def test_actual_acquisition_encore_order_legality_and_copied_dispatch(self):
        self.variants(route_source() + r'''
int main(void){
 for(int mode=0;mode<7;mode++){
  BattleContext c;acquisitionFixture(&c);int before=rngCalls;
  if(mode==1)c.playerActions[1].command=CONTROLLER_COMMAND_40;
  if(mode==2)c.turnData[1].struggleFlag=1;
  if(mode==3)c.trainerAIData.moveData[MOVE_EMBER].power=0;
  if(mode==4)c.trainerAIData.moveData[MOVE_EMBER].effect=c.trainerAIData.moveData[MOVE_COUNTER].effect;
  if(mode>=5){
   c.battleMons[1].moves[1]=MOVE_EMBER;c.battleMons[1].moves[0]=MOVE_COUNTER;
   c.battleMons[1].moveEffectData.encoredMove=MOVE_EMBER;
   c.battleMons[1].moveEffectData.encoredMoveIndex=mode==5?1:0;
   c.trainerAIData.moveData[MOVE_COUNTER].power=1;
  }
  BtlCmd_TryMeFirst(NULL,&c);int success=mode==0||mode==5;
  assert(c.battleMons[0].moveEffectData.meFirstFlag==success);
  assert(c.battleMons[0].moveEffectData.meFirstCount==success);
  assert(scriptPosition==(success?1:8)&&rngCalls==before);
  if(success){
   assert(c.moveTemp==MOVE_EMBER);c.moveNoCur=MOVE_ME_FIRST;readWord=1;
   BtlCmd_GoToMoveScript(NULL,&c);
   assert(c.moveNoCur==MOVE_EMBER&&jumpArchive==NARC_a_0_0_0&&jumpMember==MOVE_EMBER);
   assert(c.battleMons[0].moveEffectData.meFirstCount==1);
   vars[0][BMON_DATA_SPATK]=100;BtlCmd_CalcDamageRaw(NULL,&c);
   assert(c.damage==-(QOL_MODERN_BATTLE?41:42));
  }
 }
 return 0;}
''')

    def test_actual_pursuit_two_set20_pressure_choice_and_me_first(self):
        import test_modern_next_move_effects as effects
        # Original NARC words: Call(push), TryPursuit, SET20, CalcCrit, CalcDamage.
        words = struct.unpack('<10I', effects.SUBS[153][:40])
        self.assertEqual(words[:3], (60, 279, 142))
        self.assertEqual(words[4:], (50, 7, 8, 20, 38, 15))
        table = 'static const u32 pursuitPrefix[]={' + ','.join(map(str, words)) + '};\n'
        self.variants(route_source() + table + r'''
int main(void){
 for(int pressure=0;pressure<2;pressure++)for(int pp=0;pp<4;pp++)for(int encore=0;encore<2;encore++){
  BattleContext c;acquisitionFixture(&c);c.battlerIdSwitch=1;
  c.trainerAIData.moveData[MOVE_PURSUIT]=(Move){40,TYPE_DARK,CATEGORY_PHYSICAL,MOVE_EFFECT_HIT_BEFORE_SWITCH,0};
  c.battleMons[0].moves[0]=MOVE_PURSUIT;c.battleMons[0].movePPCur[0]=pp;
  c.battleMons[0].moveEffectData.meFirstFlag=1;c.battleMons[0].moveEffectData.meFirstCount=1;
  if(encore)c.battleMons[0].moveEffectData.encoredMove=MOVE_PURSUIT;
  c.battleMons[1].ability=pressure?ABILITY_PRESSURE:0;
  for(int b=1;b<4;b++)c.playerActions[b].command=CONTROLLER_COMMAND_40;
  items[0]=HOLD_EFFECT_CHOICE_ATK;
  // Start after the independent attacker/defender stack command.
  scriptWords=pursuitPrefix;scriptPosition=2;BtlCmd_TryPursuit(NULL,&c);
  assert(c.battleMons[0].movePPCur[0]==(pp?pp-1-(pressure&&pp>1):0));
  assert(copies==!!pp&&rngCalls==0);
  if(pp){
   assert(c.moveNoCur==MOVE_PURSUIT&&c.powerMultiplier==20);
   assert(c.battlerIdAttacker==0&&c.battlerIdTarget==1);
   assert(c.moveNoBattlerPrev[0]==MOVE_PURSUIT&&c.playerActions[0].command==CONTROLLER_COMMAND_40);
   assert(c.battleMons[0].moveEffectData.moveNoChoice==MOVE_PURSUIT);
   // Execute the actual UpdateVar command against original subscript153 words.
   assert(scriptPosition==4&&scriptWords[scriptPosition]==50);
   BtlCmd_UpdateVar(NULL,&c);assert(scriptPosition==8&&c.powerMultiplier==20);
   items[0]=0;
   BtlCmd_CalcDamageRaw(NULL,&c);
   assert(c.damage==-(QOL_MODERN_BATTLE?2642:2643));
   assert(c.battleMons[0].moveEffectData.meFirstCount==0&&c.battleMons[0].moveEffectData.meFirstFlag);
  }
 }
 return 0;}
''')

    def test_actual_ai_ambient_flag_never_leaks_into_candidate_damage(self):
        s = bp.source(ai=True).replace('int selectedMonIndex[4];',
                                      'int selectedMonIndex[4];int moveNoCur;')
        self.variants(s + r'''
int main(void){
 const int moves[]={MOVE_TACKLE,MOVE_EMBER,MOVE_LOW_KICK,MOVE_DRAGON_RAGE};
 for(unsigned m=0;m<NELEMS(moves);m++)for(int count=0;count<4;count++)
 for(int current=0;current<2;current++)for(int multi=12;multi<=20;multi+=8){
  BattleContext c;bpFixture(&c,moves[m],41,TYPE_NORMAL,CATEGORY_PHYSICAL,0);
  c.moveNoCur=current?moves[m]:MOVE_ME_FIRST;c.powerMultiplier=multi;
  c.trainerAIData.battlerIdTarget=1;c.battleMons[1].weight=300;
  c.battleMons[0].ability=ABILITY_TECHNICIAN;c.meFirstTotal=1;
  c.battleMons[0].moveEffectData.meFirstCount=count;
  u8 ivs[6]={0};int before=rngCalls;BattleContext copy=c;
  int expected=TrainerAI_CalcDamage(NULL,&c,moves[m],0,ivs,0,ABILITY_TECHNICIAN,0,100);
  assert(!memcmp(&copy,&c,sizeof(c))&&rngCalls==before);
  c.battleMons[0].moveEffectData.meFirstFlag=1;copy=c;
  assert(TrainerAI_CalcDamage(NULL,&c,moves[m],0,ivs,0,ABILITY_TECHNICIAN,0,100)==expected);
  assert(!memcmp(&copy,&c,sizeof(c))&&rngCalls==before);
  if(moves[m]==MOVE_DRAGON_RAGE)assert(expected==40);
 }
 return 0;}
''')

    def test_actual_future_sight_and_beat_up_keep_exceptional_lifecycle(self):
        self.variants(route_source() + r'''
int main(void){
 for(int route=0;route<2;route++){
  BattleContext c;acquisitionFixture(&c);
  int move=route?MOVE_BEAT_UP:MOVE_FUTURE_SIGHT;
  c.battleMons[1].moves[0]=move;
  c.trainerAIData.moveData[move]=(Move){40,TYPE_NORMAL,CATEGORY_PHYSICAL,0,0};
  BtlCmd_TryMeFirst(NULL,&c);assert(c.battleMons[0].moveEffectData.meFirstFlag);
  readWord=1;BtlCmd_GoToMoveScript(NULL,&c);assert(c.moveNoCur==move);
  int before=rngCalls;vars[0][BMON_DATA_ATK]=100;rng=0;
  if(route){BtlCmd_BeatUp(NULL,&c);assert(c.damage==-19);}
  else {BtlCmd_TryFutureSight(NULL,&c);
   assert(c.fieldConditionData.futureSightDamage[1]==-28);
   assert(c.fieldConditionData.futureSightTurns[1]==3&&c.fieldConditionData.futureSightMoveNo[1]==move);
   assert(c.fieldConditionData.battlerIdFutureSight[1]==0);
  }
  assert(rngCalls==before+1&&c.battleMons[0].moveEffectData.meFirstFlag);
  assert(c.battleMons[0].moveEffectData.meFirstCount==1&&c.meFirstTotal==1);
  // Existing retained flag can still apply to a subsequent ordinary formula.
  c.moveNoCur=MOVE_EMBER;vars[0][BMON_DATA_SPATK]=100;
  BtlCmd_CalcDamageRaw(NULL,&c);assert(c.damage==-(QOL_MODERN_BATTLE?41:42));
 }
 return 0;}
''')

    def test_pinned_priority_group_with_items_hh_charge_and_sports(self):
        def grouped(power, factors):
            modifier = 4096
            for factor in factors:
                modifier = (modifier * factor + 2048) // 4096
            return max(1, (power * modifier + 2047) // 4096)
        rows = []
        for power, tech, item, hh, charge, sport in itertools.product(
                (1, 40, 41, 55, 60, 61, 80), range(2), range(3), range(2), range(2), range(2)):
            factors = ([6144] if tech and power <= 60 else [])
            if item:
                factors.append(4915 if item == 1 else 4505)
            factors.append(6144)  # Me First12, between item15 and HH10.
            if hh:
                factors.append(6144)
            if charge:
                factors.append(8192)
            if sport:
                factors.append(1352)
            rows.append((power, tech, item, hh, charge, sport, grouped(power, factors)))
        table = 'static const int cases[][7]={' + ','.join(
            '{' + ','.join(map(str, row)) + '}' for row in rows) + '};\n'
        self.variants(command_source() + table + r'''
int main(void){
#if QOL_MODERN_BATTLE
 for(unsigned row=0;row<NELEMS(cases);row++){
  const int *v=cases[row];BattleContext c;
  bpFixture(&c,MOVE_THUNDER_SHOCK,v[0],TYPE_ELECTRIC,CATEGORY_SPECIAL,0);
  c.battleMons[0].ability=v[1]?ABILITY_TECHNICIAN:0;
  items[0]=v[2]==1?HOLD_EFFECT_STRENGTHEN_ELECTRIC:v[2]==2?HOLD_EFFECT_POWER_UP_SPEC:0;
  c.turnData[0].helpingHandFlag=v[3];
  c.battleMons[0].moveEffectFlags=v[4]?MOVE_EFFECT_FLAG_CHARGE:0;
  sports=v[5]?MOVE_EFFECT_FLAG_MUD_SPORT:0;BattleContext copy=c;int before=rngCalls;
  int actual=Qol_CalcMoveDamageInternal(NULL,&c,MOVE_THUNDER_SHOCK,0,0,0,0,0,1,1,QOL_DAMAGE_ORDINARY_COMMAND,TRUE);
  assert(actual==v[6]*22+2);
  assert(!memcmp(&copy,&c,sizeof(c))&&rngCalls==before);
 }
#endif
 return 0;}
''')

    def test_actual_accessors_suppression_mold_klutz_embargo_and_supplied_weather(self):
        rows = []
        for ability, suppressed, target_suppressed, embargo, hh, weather, blocker in itertools.product(
                range(4), range(2), range(2), range(2), range(2), range(3), range(3)):
            factors = []
            if ability == 1 and not suppressed:
                factors.append(6144)
            if not target_suppressed and not (ability == 2 and not suppressed):
                factors.append(5120)
            if not embargo and not (ability == 3 and not suppressed):
                factors.append(4915)
            factors.append(6144)
            if hh:
                factors.append(6144)
            modifier = 4096
            for factor in factors:
                modifier = (modifier * factor + 2048) // 4096
            power = (41 * modifier + 2047) // 4096
            damage = power * 22
            if not blocker:
                if weather == 1:
                    damage = damage * 15 // 10
                if weather == 2:
                    damage //= 2
            rows.append((ability, suppressed, target_suppressed, embargo, hh, weather, blocker, damage + 2))
        table = 'static const int cases[][8]={' + ','.join(
            '{' + ','.join(map(str, row)) + '}' for row in rows) + '};\n'
        s = command_source().replace(
            'static int GetBattlerHeldItem(BattleContext *c,int b){return items[b];}',
            'static u16 GetBattlerHeldItem(BattleContext *c,int b);')
        self.variants(s + snow.native('GetBattlerHeldItem') + table + r'''
int main(void){
#if QOL_MODERN_BATTLE
 const int abilities[]={ABILITY_NONE,ABILITY_TECHNICIAN,ABILITY_MOLD_BREAKER,ABILITY_KLUTZ};
 const int weather[]={0,FIELD_CONDITION_SUN,FIELD_CONDITION_RAIN};
 for(unsigned row=0;row<NELEMS(cases);row++){
  const int *v=cases[row];BattleContext c;commandFixture(&c,41);
  c.battleMons[0].ability=abilities[v[0]];
  c.battleMons[0].moveEffectFlags=v[1]?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].ability=ABILITY_DRY_SKIN;
  c.battleMons[1].moveEffectFlags=v[2]?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].item=HOLD_EFFECT_STRENGTHEN_FIRE;c.battleMons[0].moveEffectData.embargoFlag=v[3];
  c.turnData[0].helpingHandFlag=v[4];
  c.battleMons[2].ability=v[6]==1?ABILITY_CLOUD_NINE:v[6]==2?ABILITY_AIR_LOCK:0;
  // The supplied weather argument owns formula weather, independent of ctx.
  c.fieldCondition=FIELD_CONDITION_HAIL;int before=rngCalls;
  assert(Qol_CalcMoveDamageInternal(NULL,&c,MOVE_EMBER,0,weather[v[5]],0,0,0,1,1,QOL_DAMAGE_ORDINARY_COMMAND,TRUE)==v[7]);
  assert(rngCalls==before&&c.meFirstTotal==1);
  assert(c.battleMons[0].moveEffectData.meFirstFlag&&c.battleMons[0].moveEffectData.meFirstCount==1);
  // Causal Mold Breaker queries may retain their existing knowledge writes.
 }
#endif
 return 0;}
''')

    def test_execution_state_matches_original_owner_for_valid_and_future_counts(self):
        old = function(baseline(COMMAND), 'DamageCalcDefault').replace(
            'DamageCalcDefault', 'BaselineCommand')
        self.variants(command_source() + old + r'''
int main(void){
 for(int total=-3;total<=6;total++)for(int count=-4;count<=7;count++)for(int flag=0;flag<2;flag++){
  BattleContext c;commandFixture(&c,41);c.meFirstTotal=total;
  c.battleMons[0].moveEffectData.meFirstFlag=flag;c.battleMons[0].moveEffectData.meFirstCount=count;
  BattleContext legacy=c,modern=c;int before=rngCalls;
  BaselineCommand(NULL,&legacy);DamageCalcDefault(NULL,&modern);
  assert(rngCalls==before);
  int eligible=flag&&((s64)total-count+(total==count))<2;
  assert(modern.damage==(eligible?(QOL_MODERN_BATTLE?2026:2016):1344));
  legacy.damage=modern.damage;
  assert(!memcmp(&legacy,&modern,sizeof(legacy)));
 }
 return 0;}
''')

    def test_baseline_differential_public_compatibility_and_ordinary_false(self):
        self.variants(command_source() + old_formula() + r'''
int main(void){
 const int powers[]={0,1,40,41,60,61,100};
 const int abilities[]={ABILITY_NONE,ABILITY_TECHNICIAN,ABILITY_HUSTLE,ABILITY_GUTS,ABILITY_RIVALRY,ABILITY_IRON_FIST};
 const int held[]={0,HOLD_EFFECT_CHOICE_ATK,HOLD_EFFECT_STRENGTHEN_NORMAL,HOLD_EFFECT_POWER_UP_PHYS,HOLD_EFFECT_LATI_SPECIAL};
 const int weather[]={0,FIELD_CONDITION_RAIN,FIELD_CONDITION_SUN,FIELD_CONDITION_HAIL};
 for(unsigned p=0;p<NELEMS(powers);p++)for(unsigned a=0;a<NELEMS(abilities);a++)
 for(unsigned item=0;item<NELEMS(held);item++)for(unsigned w=0;w<NELEMS(weather);w++)
 for(int special=0;special<2;special++)for(int stage=4;stage<=8;stage+=2)for(int override=0;override<2;override++){
  BattleContext c;bpFixture(&c,MOVE_TACKLE,powers[p],TYPE_NORMAL,special?CATEGORY_SPECIAL:CATEGORY_PHYSICAL,0);
  vars[0][BMON_DATA_ATK]=vars[0][BMON_DATA_SPATK]=101;
  vars[0][BMON_DATA_STAT_CHANGE_ATK]=vars[0][BMON_DATA_STAT_CHANGE_SPATK]=stage;
  vars[1][BMON_DATA_STAT_CHANGE_DEF]=vars[1][BMON_DATA_STAT_CHANGE_SPDEF]=12-stage;
  vars[0][BMON_DATA_SPECIES]=SPECIES_LATIOS;c.battleMons[0].ability=abilities[a];items[0]=held[item];
  c.turnData[0].helpingHandFlag=1;c.battleMons[0].moveEffectData.meFirstFlag=1;
  c.meFirstTotal=1;c.battleMons[0].moveEffectData.meFirstCount=1;
  BattleContext old=c,pub=c,compat=c,ordinary=c;int before=rngCalls;
  int power=override?powers[p]:0;
  int expected=BaselineDamage(NULL,&old,MOVE_TACKLE,0,weather[w],power,0,0,1,1);
  assert(CalcMoveDamage(NULL,&pub,MOVE_TACKLE,0,weather[w],power,0,0,1,1)==expected);
  assert(Qol_CalcMoveDamageInternal(NULL,&compat,MOVE_TACKLE,0,weather[w],power,0,0,1,1,QOL_DAMAGE_COMPATIBILITY,TRUE)==expected);
  assert(Qol_CalcMoveDamageInternal(NULL,&ordinary,MOVE_TACKLE,0,weather[w],power,0,0,1,1,QOL_DAMAGE_ORDINARY_COMMAND,FALSE)==expected);
  assert(!memcmp(&old,&pub,sizeof(old))&&!memcmp(&old,&compat,sizeof(old))&&!memcmp(&old,&ordinary,sizeof(old)));
  assert(rngCalls==before);
 }
 return 0;}
''')

    def test_battle_off_formula_body_and_command_tokens_preserve_baseline(self):
        s = command_source()
        old_util = baseline('src/battle/battle_util.c')
        old_command = function(baseline(COMMAND), 'DamageCalcDefault')
        s += function(old_util, 'CalcMoveDamage').replace('CalcMoveDamage', 'BaselineDamage') + '\n'
        s += old_command.replace('DamageCalcDefault', 'BaselineCommand') + '\n'
        # Prevent C assert's source-line strings from polluting token identity.
        s = s.replace('#define GF_ASSERT assert', '#define GF_ASSERT(x) fixtureAssert(x)')
        for types, moves in itertools.product((0, 1), repeat=2):
            with self.subTest(types=types, moves=moves), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'check.c'
                path.write_text(s)
                output = subprocess.check_output([
                    'cc', '-E', '-P', '-iquote', str(game.ROOT / 'include'),
                    '-DQOL_MODERN_BATTLE=0', f'-DQOL_MODERN_TYPES={types}',
                    f'-DQOL_MODERN_MOVES={moves}', str(path)], text=True)
                def body(name):
                    f = function(output, name)
                    return re.findall(r'[A-Za-z_]\w*|\d+|[^\s]', f[f.index('{'):])
                self.assertEqual(body('BaselineDamage'), body('Qol_CalcMoveDamageInternal'))
                self.assertEqual(body('BaselineCommand'), body('DamageCalcDefault'))

    def test_source_contract_single_formula_public_header_and_exceptional_routes(self):
        self.assertEqual(baseline('include/battle/battle_util.h'),
                         (game.ROOT / 'include/battle/battle_util.h').read_text())
        worker = snow.native('Qol_CalcMoveDamageInternal')
        self.assertNotIn('meFirstFlag', worker)
        self.assertNotIn('meFirstCount', worker)
        self.assertNotIn('meFirstTotal', worker)
        self.assertNotIn('MOVE_ME_FIRST', worker)
        self.assertNotIn('Qol_CalcMoveDamageInternal', baseline('src/battle/battle_util.c'))
        # These unchanged function bodies retain fixed/OHKO/returned and public
        # confusion/switching behavior without a new boost or lifecycle owner.
        for path, names in (
            (COMMAND, ('BtlCmd_TryMeFirst', 'BtlCmd_GoToMoveScript', 'BtlCmd_TryPursuit',
                       'BtlCmd_TryFutureSight', 'BtlCmd_BeatUp', 'BtlCmd_TryMetalBurst')),
        ):
            old = baseline(path)
            for name in names:
                self.assertEqual(function(old, name), game.function_source(path, name))
        for path in ('src/battle/trainer_ai.c', 'src/battle/battle_controller_player.c',
                     'src/battle/battle_controller_opponent.c'):
            self.assertEqual(baseline(path), (game.ROOT / path).read_text())
