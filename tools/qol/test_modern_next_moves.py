"""Independent data and real native-control regressions for the next35 batch."""
from pathlib import Path
from collections import Counter
import json
import re
import struct
import unittest

import test_game_logic as game
import test_modern_moves as moves
import test_modern_rules as rules
import move_resources

ROOT = Path(__file__).resolve().parents[2]
UTIL = 'src/battle/battle_util.c'
PLAYER = 'src/battle/battle_controller_player.c'
# Independent audit expectations: id, effect, category, power, type, accuracy,
# PP, chance, range, priority, native flags, plain animation alias.
ROWS = [
(485,2,1,95,3,100,10,10,8,0,50,188),
(493,70,0,65,1,100,20,100,0,0,51,280),
(506,125,1,80,11,100,15,30,0,0,114,57),
(520,4,1,100,10,50,5,100,0,0,114,126),
(524,228,1,70,13,100,20,0,0,0,50,369),
(525,71,1,50,6,100,20,100,4,0,50,405),
(530,70,1,55,13,95,15,100,4,0,114,81),
(531,48,0,90,13,100,15,0,0,0,51,209),
(533,44,0,40,16,90,15,0,0,0,115,337),
(537,69,0,75,11,95,10,50,0,0,51,75),
(539,73,1,65,12,90,10,50,0,0,50,345),
(558,71,1,55,17,95,15,100,4,0,114,399),
(559,31,0,85,15,90,10,30,0,0,82,419),
(592,18,2,0,0,0,20,100,0,0,20,204),
(598,71,1,75,10,100,10,100,0,0,114,261),
(611,18,2,0,9,100,30,0,0,1,22,204),
(612,6,0,20,13,100,20,100,0,0,115,209),
(615,139,0,40,1,100,20,100,0,0,115,409),
(623,229,0,120,2,100,5,100,0,0,115,413),
(682,68,0,80,6,100,15,100,0,0,51,404),
(709,186,0,85,14,100,15,0,0,0,51,242),
(713,69,0,85,11,100,10,20,0,0,51,127),
(787,68,0,60,16,100,15,100,4,0,51,337),
(809,71,0,70,6,90,10,100,0,0,51,404),
(815,228,0,60,11,100,20,0,0,0,51,369),
(817,44,0,40,2,90,10,0,0,0,115,332),
(818,125,1,70,4,100,10,30,0,0,50,189),
(831,138,0,70,14,90,10,100,0,0,115,428),
(836,27,0,120,10,100,10,0,2,0,50,394),
(837,198,0,120,11,100,10,0,0,0,51,127),
(841,229,0,120,4,100,5,0,0,0,51,370),
(876,186,0,90,0,100,10,0,0,0,51,36),
(887,70,0,50,6,100,20,100,0,0,51,450),
(889,68,1,50,11,100,20,100,0,0,50,352),
(891,44,1,40,14,100,10,0,0,0,50,60),
]
IDS = {r[0] for r in ROWS}


def native(*names, path=UTIL):
    return '\n'.join(game.function_source(path, n) for n in names) + '\n'


class NextMoveTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_all_audited_metadata_classifiers_and_unsupported_gaps_flag_off_on(self):
        rows = ',\n'.join('{' + ','.join(map(str,r)) + '}' for r in ROWS)
        source = moves.ModernMoveTests().source() + r'''
#include "constants/battle.h"
#include "constants/move_effects.h"
#include "constants/abilities.h"
typedef int BattleSystem;
typedef int BattleContext;
static int BattleContext_CheckMoveUnuseableInGravity(BattleSystem *s,BattleContext *c,int b,int m){return 0;}
static int BattleContext_CheckMoveHealBlocked(BattleSystem *s,BattleContext *c,int b,int m){return 0;}
''' + rules.array('sSoundMoves') + rules.array('sPunchingMoves') + rules.array('sMetronomeUnuseableMoves') + native('CheckLegalMimicMove', 'CheckLegalMetronomeMove') + r'''
static int contains(const u16 *a,int n,int move){for(int i=0;i<n;i++)if(a[i]==move)return 1;return 0;}
static const int rows[][12]={ROWS};
int main(void) {
 assert(NUM_MOVES==467&&sizeof(MoveTbl)==16);
 assert(QOL_EXTENDED_MOVE_COUNT==72);
 for(unsigned i=0;i<NELEMS(rows);i++) {
  int id=rows[i][0];const MoveTbl *e=Qol_GetExtendedMoveData(id);
  assert(Qol_IsSupportedMove(id)==QOL_MODERN_MOVES);
#if QOL_MODERN_MOVES
  assert(e);
  const int actual[]={e->effect,e->category,e->power,e->type,e->accuracy,e->pp,
   e->effectChance,e->range,e->priority,e->flags,Qol_GetMoveAnimation(id)};
  for(int a=0;a<11;a++)assert(actual[a]==rows[i][a+1]);
#else
  assert(!e&&Qol_GetMoveAnimation(id)==id);
#endif
  assert(Qol_IsSoundMove(id)==(QOL_MODERN_MOVES&&id==558));
  assert(Qol_MoveBypassesSubstitute(id)==(QOL_MODERN_MOVES&&(id==558||id==592)));
  assert(contains(sSoundMoves,NELEMS(sSoundMoves),id)==(QOL_MODERN_MOVES&&id==558));
  assert(contains(sPunchingMoves,NELEMS(sPunchingMoves),id)==(QOL_MODERN_MOVES&&(id==615||id==841)));
  int banned=QOL_MODERN_MOVES&&(id==558||id==623||id==787||id==836||id==876||id==887||id==889||id==891);
  assert(CheckLegalMimicMove(id));
  assert(CheckLegalMetronomeMove(NULL,NULL,0,id)==!banned);
 }
 const int gaps[]={468,469,470,526,544,601,614,672,65535};
 for(unsigned i=0;i<NELEMS(gaps);i++)assert(!Qol_IsSupportedMove(gaps[i]));
 return 0;
}
'''.replace('ROWS', rows)
        for flags in ((), ('-DQOL_MODERN_MOVES=1',), ('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1')):
            self.compile_run(source, *flags, '-Wno-unused-const-variable')

    def test_pinned_profile_metadata_overrides_and_plain_native_animation_scripts(self):
        entries={r['id']:r for r in move_resources.read_entries(ROOT/'include/data/qol_move_entries.inc')}
        profile_path=ROOT/'.local-tools/validation/gen9-import-profile.json'
        if not profile_path.exists():
            self.skipTest('Needs the approved pinned import profile')
        profile=json.loads(profile_path.read_text())
        self.assertEqual(profile['engine_revision'],'61b510cfb6cf7d77c3b083150fad3499f82fd326')
        source={m['engine_id']:m for m in profile['moves']}
        overrides={(531,'effect'):48,(818,'effect'):125,(709,'pp'):15}
        for expected in ROWS:
            move_id=expected[0]
            self.assertIn(move_id, entries)
            row=entries[move_id]
            for field in move_resources.FIELDS[1:10]:
                reference=source[move_id]['effectChance' if field=='chance' else field]
                self.assertEqual(row[field], overrides.get((move_id,field),reference), (move_id,field))
            self.assertEqual(tuple(row[k] for k in move_resources.FIELDS),expected)
            alias=next((ROOT/"files/battledata/script/move_script").glob(f"move_script_{row['animation']:04}*.s"))
            commands=[l.strip() for l in alias.read_text().splitlines() if l.strip() and not l.strip().startswith(('.','_'))]
            self.assertEqual(commands,['GoToEffectScript'])
            self.assertEqual(move_resources.PRESENTATION[move_id]['name'],source[move_id]['name'])
        expansion=ROOT/'.local-tools/pokeemerald-expansion/src/data/moves_info.h'
        if expansion.exists():
            fang=expansion.read_text().split('[MOVE_PSYCHIC_FANGS] =',1)[1].split('[MOVE_',1)[0]
            self.assertRegex(fang,r'\.pp\s*=\s*15\b')

    def test_screen_break_only_successful_hits_in_modern_rules(self):
        source=moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/move_effects.h"
#include "constants/battle_subscript.h"
typedef int BattleSystem;
typedef struct {struct {int hp;} battleMons[4];struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
 unsigned sideEffectFlagsDirect,moveStatusFlag;int battlerIdStatChange,moveNoCur;} BattleContext;
static int GetMoveStatusChangeScript(BattleContext *c,int type,unsigned flags){c->battlerIdStatChange=1;return 77;}
'''+native('BattleSystem_TryDirectSideEffect')+r'''
int main(void) {
 const int ids[]={280,709,876};
 const unsigned failures[]={0,MOVE_STATUS_NO_EFFECT,MOVE_STATUS_WONDER_GUARD_IMMUNE,
  MOVE_STATUS_MISSED,MOVE_STATUS_PROTECTED,MOVE_STATUS_FAILED};
 for(int m=0;m<3;m++)for(int f=0;f<6;f++)for(int hp=0;hp<2;hp++) {
  BattleContext c={0};c.moveNoCur=ids[m];c.battleMons[1].hp=100*hp;
  c.sideEffectFlagsDirect=MOVE_SIDE_EFFECT_BREAK_SCREENS|MOVE_SIDE_EFFECT_TO_DEFENDER|MOVE_SUBSCRIPT_PTR_BREAK_SCREENS;
  c.moveStatusFlag=failures[f];int script=0;
  int modern=QOL_MODERN_BATTLE||QOL_MODERN_MOVES;
  int expected=hp&&(modern?f==0:(f<=2));
  assert(BattleSystem_TryDirectSideEffect(NULL,&c,&script)==expected);
  assert(!c.sideEffectFlagsDirect&&script==77);
 }
 return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',),('-DQOL_MODERN_MOVES=1',)):
            self.compile_run(source,*flags)

    def test_choice_history_tracks_failed_pivots_but_skips_completed_pivots(self):
        source=moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/items.h"
#include "constants/move_effects.h"
typedef int BattleSystem;
typedef struct {struct {struct {int moveNoChoice;} moveEffectData;} battleMons[4];
 struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
 unsigned battleStatus,battleStatus2;int battlerIdAttacker,moveNoTemp,moveNoCur,
 moveNoProtect[4],moveNoPrev,moveNoBattlerPrev[4],moveNoSketch[4],command;} BattleContext;
static int held;
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return held;}
static void BattleControllerPlayer_UpdateTargetMoveHistory(BattleSystem *s,BattleContext *c){}
static void BattleContext_UndoMetronomeItemOnFail(BattleSystem *s,BattleContext *c){}
'''+native('BattleControllerPlayer_UpdateMoveHistory',path=PLAYER)+r'''
int main(void) {
 const int ids[]={369,524,815,33,165,226};
 const int items[]={HOLD_EFFECT_CHOICE_ATK,HOLD_EFFECT_CHOICE_SPEED,HOLD_EFFECT_CHOICE_SPATK,0};
 for(int m=0;m<6;m++)for(int i=0;i<4;i++)for(int complete=0;complete<2;complete++) {
  BattleContext c={0};held=items[i];c.moveNoTemp=c.moveNoCur=ids[m];
  c.trainerAIData.moveData[369].effect=MOVE_EFFECT_SWITCH_HIT;
  c.battleMons[0].moveEffectData.moveNoChoice=99;
  c.battleStatus2=BATTLE_STATUS2_DISPLAY_ATTACK_MESSAGE|
    (complete?((m<3?BATTLE_STATUS2_UTURN:0)|BATTLE_STATUS2_MOVE_SUCCEEDED):0);
  BattleControllerPlayer_UpdateMoveHistory(NULL,&c);
  int pivot=m==0||(QOL_MODERN_MOVES&&(m==1||m==2));
  int skip=m==4||(complete&&(pivot||m==5));
  assert(c.battleMons[0].moveEffectData.moveNoChoice==(i==3?0:skip?99:ids[m]));
  assert(c.moveNoPrev==ids[m]&&c.moveNoSketch[0]==ids[m]);
  assert(c.command==CONTROLLER_COMMAND_40);
 }
 // moveNoTemp belongs to the caller. Pursuit can restore moveNoCur to that
 // caller as well, so the completed-pivot flag owns replacement protection.
 const int callers[]={MOVE_METRONOME,MOVE_COPYCAT,MOVE_SLEEP_TALK};
 for(int caller=0;caller<3;caller++)for(int pivot=0;pivot<3;pivot++)
 for(int pursuit=0;pursuit<2;pursuit++)for(int complete=0;complete<2;complete++) {
  BattleContext c={0};held=HOLD_EFFECT_CHOICE_ATK;c.moveNoTemp=callers[caller];
  c.moveNoCur=pursuit?callers[caller]:ids[pivot];
  c.battleStatus2=BATTLE_STATUS2_DISPLAY_ATTACK_MESSAGE|(complete?BATTLE_STATUS2_UTURN:0);
  c.battleMons[0].moveEffectData.moveNoChoice=99;
  BattleControllerPlayer_UpdateMoveHistory(NULL,&c);
  assert(c.battleMons[0].moveEffectData.moveNoChoice==
   (QOL_MODERN_MOVES&&complete?99:callers[caller]));
 }
 return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_MOVES=1',),('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1')):
            self.compile_run(source,*flags)

    def test_target_thaw_requires_successful_actual_hp_damage(self):
        source=moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/abilities.h"
#include "constants/battle_subscript.h"
typedef int BattleSystem;
enum {NARC_a_0_0_1};
typedef struct {struct {int hp,status,ability;unsigned moveEffectFlags,moveEffectFlagsTemp;} battleMons[4];
 struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
 struct {int physicalDamage,specialDamage;} selfTurnData[4];
 unsigned moveStatusFlag,switchInFlag;int afterMoveEffectState,afterMoveEffectIndex,
 battlerIdAttacker,battlerIdTarget,battlerIdTemp,command,commandNext,moveType,moveNoCur,turnOrder[4],script;} BattleContext;
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 0;}
static int TrySyncronizeStatus(BattleSystem *s,BattleContext *c,int cmd){return 0;}
static int TryAbilityOnEntry(BattleSystem *s,BattleContext *c){return 0;}
static int TryUseHeldItem(BattleSystem *s,BattleContext *c,int b){return 0;}
static int CheckItemEffectOnHit(BattleSystem *s,BattleContext *c,int *out){return 0;}
static int CheckUseHeldItem(BattleSystem *s,BattleContext *c,int b,int *out){return 0;}
static int GetBattlerAbility(BattleContext *c,int b){return c->battleMons[b].ability;}
static void ReadBattleScriptFromNarc(BattleContext *c,int n,int script){c->script=script;}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''+native('BattleControllerPlayer_AfterMoveEffects',path=PLAYER)+r'''
int main(void) {
 const int ids[]={52,506,818,57};
 for(int m=0;m<4;m++)for(int reason=0;reason<10;reason++)for(int physical=0;physical<2;physical++) {
  BattleContext c={0};c.moveNoCur=ids[m];c.battlerIdTarget=1;c.afterMoveEffectState=6;
  c.battleMons[1].status=STATUS_FREEZE;c.battleMons[1].hp=100;
  c.trainerAIData.moveData[52].type=TYPE_FIRE;
  if(physical)c.selfTurnData[1].physicalDamage=-20;else c.selfTurnData[1].specialDamage=-20;
  if(reason==1)c.moveStatusFlag=MOVE_STATUS_MISSED;
  if(reason==2)c.moveStatusFlag=MOVE_STATUS_PROTECTED;
  if(reason==3)c.moveStatusFlag=MOVE_STATUS_NO_EFFECT;
  if(reason==4)c.selfTurnData[1].physicalDamage=c.selfTurnData[1].specialDamage=0; // Substitute/no damage
  if(reason==5)c.battleMons[1].hp=0;
  if(reason==6)c.battleMons[1].status=0;
  if(reason==7)c.battlerIdTarget=BATTLER_NONE;
  if(reason==8)c.battlerIdAttacker=1;
  if(reason==9)c.moveStatusFlag=MOVE_STATUS_MULTI_HIT_DISRUPTED;
  BattleControllerPlayer_AfterMoveEffects(NULL,&c);
  int modern=QOL_MODERN_MOVES;
  int expected=(m==0||(modern&&(m==1||m==2)))&&reason==0;
  // New failure gate also protects the old Fire path from stale damage counters.
  if(!(QOL_MODERN_MOVES||QOL_MODERN_BATTLE)&&m==0&&reason>=1&&reason<=3)expected=1;
  assert((c.script==BATTLE_SUBSCRIPT_THAW_OUT)==expected);
  if(expected)assert(c.battlerIdTemp==1&&c.afterMoveEffectState==7);
 }
 return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_MOVES=1',),('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1')):
            self.compile_run(source,*flags)

class NextMoveNativeTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_snarl_soundproof_preview_substitute_damage_and_spatk_drop(self):
        import test_modern_original_abilities as original
        source=original.accuracy_source()+r'''
int main(void) {
 for(int target=1;target<=3;target+=2)for(int suppress=0;suppress<2;suppress++)for(int mold=0;mold<2;mold++) {
  BattleContext c=fixture(MOVE_TACKLE);c.moveNoCur=558;c.battlerIdTarget=target;
  c.battleMons[target].hp=100;c.battleMons[target].ability=ABILITY_SOUNDPROOF;
  c.battleMons[target].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  assert(BattleContext_CheckMoveImmunityFromAbility(&c,0,target)==
   ((!suppress&&!mold)?BATTLE_SUBSCRIPT_BLOCKED_BY_SOUNDPROOF:0));
 }
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1','-Wno-unused-function','-Wno-unused-variable','-Wno-unused-but-set-variable','-Wno-sign-compare')
        import test_modern_sturdy as sturdy
        source=sturdy.damage_source()+r'''
int main(void) {
 for(int target=1;target<=3;target+=2) {
  BattleContext c=fixture(100,-20);c.moveNoCur=558;c.battlerIdTarget=target;
  c.battleMons[target].hp=100;c.battleMons[target].status2=STATUS2_SUBSTITUTE;
  c.battleMons[target].moveEffectData.substituteHp=40;
  BattleControllerPlayer_HpCalc(NULL,&c);
  assert(c.hpCalc==-20&&c.script==BATTLE_SUBSCRIPT_UPDATE_HP);
  assert(c.battleMons[target].moveEffectData.substituteHp==40);
  assert(c.selfTurnData[target].specialDamage==-20);
  assert(!(c.selfTurnData[target].statusFlags&8));
 }
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1','-Wno-unused-function')
        import test_modern_competitive as competitive
        source=competitive.stat_source()+r'''
int main(void) {
 for(int target=1;target<=3;target+=2)for(int stage=0;stage<=12;stage++) {
  BattleContext c=fixture();c.moveNoCur=558;c.battlerIdStatChange=c.battlerIdTarget=target;
  c.battleMons[target].hp=100;c.battleMons[target].ability=0;
  c.battleMons[target].status2=STATUS2_SUBSTITUTE;c.battleMons[target].statChanges[STAT_SPATK]=stage;
  c.statChangeType=SIDE_EFFECT_TYPE_INDIRECT;mutate(&c,22+STAT_SPATK-1);
  assert(c.battleMons[target].statChanges[STAT_SPATK]==(stage?stage-1:0));
 }
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1','-Wno-unused-function')

    def test_play_nice_substitute_floor_protect_magic_coat_and_baby_eyes_priority(self):
        import test_modern_competitive as competitive
        source=competitive.stat_source()+r'''
int main(void) {
 for(int move=0;move<2;move++)for(int stage=0;stage<=12;stage++) {
  BattleContext c=fixture();c.moveNoCur=move?611:592;c.battleMons[1].ability=0;
  c.battleMons[1].status2=STATUS2_SUBSTITUTE;c.battleMons[1].statChanges[STAT_ATK]=stage;
  mutate(&c,22);
  assert(c.battleMons[1].statChanges[STAT_ATK]==(move?stage:stage?stage-1:0));
 }
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1','-Wno-unused-function')
        import test_modern_original_abilities as original
        source=original.accuracy_source().replace('int protectFlag,roostFlag;','int protectFlag,roostFlag,magicCoatFlag,snatchFlag;')
        source=source.replace('static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}',
                              'static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 2;}')
        source=source.replace('command,commandNext,script,hpCalc;', 'command,commandNext,script,hpCalc,moveNoTemp,moveStatus,moveNoMagicCoat,battlerIdMagicCoat,moveNoProtect[4],moveNoBattlerPrev[4],moveNoPrev,turnOrder[4],battlerIdTemp;')
        source+=r'''
static void CheckIgnorePressure(BattleContext *c,int a,int b){}
static int BattleMon_GetMoveIndex(void *m,int move){return 0;}
'''+native('BattleControllerPlayer_CheckMagicCoat',path=PLAYER)+r'''
int main(void) {
 for(int which=0;which<2;which++)for(int protect=0;protect<2;protect++) {
  int move=which?611:592;BattleContext c=fixture(MOVE_TACKLE);c.moveNoCur=move;
  c.turnData[1].protectFlag=protect;c.turnData[1].magicCoatFlag=1;
  BattleSystem_CheckMoveEffect(NULL,&c,0,1,move);
  assert(!!(c.moveStatusFlag&MOVE_STATUS_PROTECTED)==(which&&protect));
  assert(BattleControllerPlayer_CheckMagicCoat(NULL,&c)==!(which&&protect));
  if(!(which&&protect))assert(c.script==BATTLE_SUBSCRIPT_MAGIC_COAT);
 }
 assert(Qol_GetExtendedMoveData(611)->priority==1);
 assert(Qol_GetExtendedMoveData(592)->accuracy==0);
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1','-Wno-unused-function','-Wno-unused-variable','-Wno-unused-but-set-variable','-Wno-sign-compare')

    def test_self_thaw_uses_both_native_frozen_branches(self):
        player=(ROOT/PLAYER).read_text()
        first=player.split('        case 2:\n            if (ctx->battleMons[ctx->battlerIdAttacker].status & STATUS_FREEZE)',1)[1].split('        case 3:',1)[0]
        last=player.split('        case 15:\n            if (ctx->battleMons[ctx->battlerIdAttacker].status & STATUS_FREEZE)',1)[1].split('        case 16:',1)[0]
        source=moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/move_effects.h"
#include "constants/battle_subscript.h"
typedef int BattleSystem;
enum {NARC_a_0_0_1};
typedef struct {struct {int status;} battleMons[4];int battlerIdAttacker,checkAttackerStatusState,battlerIdTemp,command,commandNext,script;} BattleContext;
static int roll;
static int BattleSystem_Random(BattleSystem *s){return roll;}
static void ReadBattleScriptFromNarc(BattleContext *c,int n,int script){c->script=script;}
'''
        prefix='            if (ctx->battleMons[ctx->battlerIdAttacker].status & STATUS_FREEZE)'
        source+='static int frozen(BattleSystem *battleSystem,BattleContext *ctx,int effect) {int ret=0;switch(0){case 0:\n'+prefix+first+'}\nreturn ret;}\n'
        source+='static int defrost(BattleSystem *battleSystem,BattleContext *ctx,int effect) {int ret=0;switch(0){case 0:\n'+prefix+last+'}\nreturn ret;}\n'
        source+=r'''
int main(void) {
 const int ids[]={506,818,520};
 for(int m=0;m<3;m++)for(int r=0;r<5;r++) {
  BattleContext c={0};c.battleMons[0].status=STATUS_FREEZE;roll=r;
  int effect=Qol_GetExtendedMoveData(ids[m])->effect;
  assert(frozen(NULL,&c,effect)==(r==0?2:m<2?0:1));
  c.script=0;assert(defrost(NULL,&c,effect)==(m<2?2:0));
  assert(c.script==(m<2?BATTLE_SUBSCRIPT_DEFROSTED_BY_MOVE:0));
 }
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1')

    def test_actual_merged_learnset_capacity_matches_the_original_archive(self):
        import learnset_import
        from nitro_data import unpack_narc
        data=(ROOT/'include/data/qol_learnsets.inc').read_text()
        rows=[tuple(map(int,r)) for r in re.findall(r'QOL_LEVEL_UP_MOVE\((\d+), (\d+), (\d+)\)',data)]
        self.assertEqual(len(rows),336)
        self.assertEqual(len({r[0] for r in rows}),237)
        self.assertEqual(max(Counter(s for s,l,m in rows).values()),5)
        legacy_path=ROOT/'files/poketool/personal/wotbl.narc'
        if not legacy_path.exists():
            self.skipTest('Needs the locally supplied original learnset archive')
        legacy,_=unpack_narc(legacy_path.read_bytes())
        largest=0
        for species in range(1,494):
            packed=struct.unpack('<'+'H'*(len(legacy[species])//2),legacy[species])
            packed=packed[:packed.index(65535)]
            merged={(v>>9,v&511) for v in packed}
            merged.update((l,m) for s,l,m in rows if s==species)
            largest=max(largest,len(merged)+1)
            self.assertLessEqual(len(merged)+1,28)
        self.assertEqual(largest,23)
        self.assertEqual(set(learnset_import.SUPPORTED)-{m for s,l,m in rows},
                         {506,530,615,696,709,787,809,815,818,831,854,887,888,889,666})

    def test_two_hit_damage_contact_items_and_early_ko_execute_native_functions(self):
        import test_modern_sturdy as sturdy
        source=sturdy.damage_source().replace('NARC_a_0_0_1,GAME_STAT_ALLIES_DAMAGED','NARC_a_0_0_1,NARC_a_0_0_0,GAME_STAT_ALLIES_DAMAGED')
        source=source.replace('int hp,maxHp,hitCount,ability,item,itemMod;', 'int hp,maxHp,hitCount,ability,item,itemMod;u16 moves[4];u8 movePPCur[4];')
        source=source.replace('struct {int substituteHp;} moveEffectData;', 'struct {int substituteHp,disabledMove;unsigned disabledTurns:3;} moveEffectData;')
        source=source.replace('scriptNarcId,scriptFileId,pos,words[2],multiHitCountTemp,multiHitCount,battlerIdFainted,criticalMultiplier;',
         'scriptNarcId,scriptFileId,pos,words[3],multiHitCountTemp,multiHitCount,battlerIdFainted,criticalMultiplier,\n'
         'moveNoTemp,moveTemp,moveType,msgTemp,statChangeType,battlerIdStatChange,battleStatus2,multiHitLoop,moveCheckSkipFlags,checkMultiHit,itemTemp,abilityTemp,tempData,selectedMonIndex[4];\n'
         'struct {int battlerBitKnockedOffItem;} fieldSideConditionData[2];')
        source+=r'''
static int BattleMon_GetMoveIndex(Mon *m,int move){for(int i=0;i<4;i++)if(m->moves[i]==move)return i;return 4;}
static int GetBattlerVar(BattleContext *c,int b,int v,void *unused){return TYPE_NORMAL;}
static int CheckAbilityActive(BattleSystem *s,BattleContext *c,int a,int b,int ability){return 0;}
static void BattleController_EmitBlankMessage(BattleSystem *s){}
'''+native('DamageDivide','BattlerCheckSubstitute','Qol_GetCursedBodyMove','CheckAbilityEffectOnHit','CheckItemEffectOnHit')
        source+=native('BtlCmd_SetMultiHit',path='src/battle/battle_command.c')+native('BattleControllerPlayer_CheckMultiHit',path=PLAYER)+r'''
int main(void) {
 const int ids[]={533,817,891};
 for(int m=0;m<3;m++)for(int early=0;early<3;early++) {
  BattleContext c=fixture(100,-20);c.moveNoCur=c.moveNoTemp=ids[m];
  c.battleMons[0].hp=c.battleMons[0].maxHp=100;c.battleMons[1].ability=ABILITY_ROUGH_SKIN;
  c.words[0]=49;c.words[1]=2;c.words[2]=MULTIHIT_MULTI_HIT_MOVE;
  BtlCmd_SetMultiHit(NULL,&c);assert(c.multiHitCount==2);
  if(early==1)c.battleMons[1].hp=10;
  if(early==2)c.battleMons[0].hp=1;
  int hits=0,contact=0,itemUses=0;
  while(c.battleMons[0].hp&&c.battleMons[1].hp) {
   c.damage=-20;BattleControllerPlayer_HpCalc(NULL,&c);
   int actual=c.hpCalc;if(-actual>c.battleMons[1].hp)actual=-c.battleMons[1].hp;
   c.battleMons[1].hp+=actual;hits++;
   int script=-1;
   if(CheckAbilityEffectOnHit(NULL,&c,&script)) {
    assert(m<2&&script==BATTLE_SUBSCRIPT_ROUGH_SKIN);contact++;
    c.battleMons[0].hp+=c.hpCalc;if(c.battleMons[0].hp<0)c.battleMons[0].hp=0;
   }
   // Execute an actual physical/special reactive item on each surviving hit.
   c.battleMons[1].item=m<2?HOLD_EFFECT_RECOIL_PHYSICAL:HOLD_EFFECT_RECOIL_SPECIAL;
   c.battleMons[1].itemMod=8;
   if(CheckItemEffectOnHit(NULL,&c,&script)) {
    assert(script==BATTLE_SUBSCRIPT_HELD_ITEM_RECOIL_WHEN_HIT);itemUses++;
   }
   c.battleMons[1].item=0; // native consumption subscript boundary
   if(!c.battleMons[0].hp||!c.battleMons[1].hp)c.battlerIdFainted=1;
   BattleControllerPlayer_CheckMultiHit(NULL,&c);
   if(c.commandNext!=CONTROLLER_COMMAND_24)break;
  }
  int expected=(early==1||(early==2&&m<2))?1:2;
  assert(hits==expected&&contact==(m<2?hits:0));
  assert(itemUses==(early==2&&m<2?0:hits));
  assert(c.commandNext==CONTROLLER_COMMAND_34);
 }
 // A first strike breaks Substitute; the second damages the actual holder.
 // Contact abilities and reactive items belong to the second strike.
 for(int m=0;m<3;m++) {
  BattleContext c=fixture(100,-20);c.moveNoCur=c.moveNoTemp=ids[m];
  c.battleMons[0].hp=c.battleMons[0].maxHp=100;c.battleMons[1].ability=ABILITY_ROUGH_SKIN;
  c.battleMons[1].status2=STATUS2_SUBSTITUTE;c.battleMons[1].moveEffectData.substituteHp=10;
  BattleControllerPlayer_HpCalc(NULL,&c);assert(c.script==BATTLE_SUBSCRIPT_HIT_SUBSTITUTE);
  int script=-1;assert(!CheckAbilityEffectOnHit(NULL,&c,&script));
  c.battleMons[1].item=m<2?HOLD_EFFECT_RECOIL_PHYSICAL:HOLD_EFFECT_RECOIL_SPECIAL;
  c.battleMons[1].itemMod=8;assert(!CheckItemEffectOnHit(NULL,&c,&script));
  c.damage=-20;BattleControllerPlayer_HpCalc(NULL,&c);
  assert(c.script==BATTLE_SUBSCRIPT_UPDATE_HP);
  assert(CheckAbilityEffectOnHit(NULL,&c,&script)==(m<2));
  assert(CheckItemEffectOnHit(NULL,&c,&script));
 }
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1','-Wno-unused-function')

    def test_real_hp_strike_clears_only_stale_substitute_marker_in_modern_modes(self):
        import test_modern_sturdy as sturdy
        source=sturdy.damage_source()+native('BattlerCheckSubstitute')+r'''
int main(void) {
 BattleContext c=fixture(100,-20);c.moveNoCur=MOVE_DOUBLE_KICK;
 c.trainerAIData.moveData[MOVE_DOUBLE_KICK].flags=1;
 c.battleMons[1].status2=STATUS2_SUBSTITUTE;c.battleMons[1].moveEffectData.substituteHp=10;
 c.selfTurnData[1].statusFlags=0x24;
 BattleControllerPlayer_HpCalc(NULL,&c);
 assert(c.script==BATTLE_SUBSCRIPT_HIT_SUBSTITUTE&&c.selfTurnData[1].statusFlags==0x2c);
 assert(BattlerCheckSubstitute(&c,1));
 c.damage=-20;BattleControllerPlayer_HpCalc(NULL,&c);
 assert(c.script==BATTLE_SUBSCRIPT_UPDATE_HP);
 int modern=QOL_MODERN_BATTLE||QOL_MODERN_MOVES;
 assert(c.selfTurnData[1].statusFlags==(modern?0x24:0x2c));
 assert(BattlerCheckSubstitute(&c,1)==!modern);
 assert(c.selfTurnData[1].physicalDamage==-20);
 return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_MOVES=1',),('-DQOL_MODERN_BATTLE=1',),('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1')):
            self.compile_run(source,*flags,'-Wno-unused-function')

    def test_random_and_spread_targeting_uses_native_selection_and_live_slots(self):
        source=moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
typedef int BattleSystem;typedef int OpponentData;
typedef struct {struct {int hp;} battleMons[4];struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
 struct {int followMeFlag,battlerIdFollowMe;} fieldSideConditionData[2];
 struct {int battlerIdTarget;} playerActions[4];int turnOrder[4],moveTargetLoopIndex;} BattleContext;
static int roll;
static int BattleSystem_GetBattleType(BattleSystem *s){return BATTLE_TYPE_DOUBLES;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}
static int BattleSystem_Random(BattleSystem *s){return roll;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int BattleSystem_GetOpponentBattler(BattleSystem *s,int b,int slot){return (b^1)^slot;}
static int BattleSystem_GetBattlerIdPartner(BattleSystem *s,int b){return b^2;}
static OpponentData *BattleSystem_GetOpponentData(BattleSystem *s,int b){static int ids[]={0,1,2,3};return &ids[b];}
static int OpponentData_GetBattlerType(OpponentData *o){return *o;}
'''+native('Battler_GetRandomOpposingBattlerId','BattleSystem_GetMoveTarget')+r'''
int main(void) {
 for(int r=0;r<4;r++)for(int faint=0;faint<3;faint++) {
  BattleContext c={0};roll=r;
  for(int b=0;b<4;b++){c.battleMons[b].hp=100;c.turnOrder[b]=b;}
  if(faint)c.battleMons[faint==1?1:3].hp=0;
  int expected=faint==1?3:faint==2?1:1+(r&1)*2;
  assert(BattleSystem_GetMoveTarget(NULL,&c,0,836,0,0)==expected);
  // Snarl targets both live opponents and excludes the ally.
  int first=BattleSystem_GetMoveTarget(NULL,&c,0,558,0,0);
  assert(first==(faint==1?3:1));
 }
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1','-Wno-sign-compare')

    def test_pivot_replacement_ignores_traps_but_requires_live_non_egg_reserve(self):
        source=moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/species.h"
typedef int BattleSystem;
typedef struct {int species,hp,egg;} Pokemon;
typedef struct {Pokemon mons[3];} Party;
typedef struct {struct {int hp,status2;} battleMons[4];int selectedMonIndex[4],showPartyFlags[4],pos,words[4];} BattleContext;
static Party party;
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static Party *BattleSystem_GetParty(BattleSystem *s,int b){return &party;}
static int BattleSystem_GetPartySize(BattleSystem *s,int b){return 3;}
static int BattleSystem_GetBattlerType(BattleSystem *s,int b){return b;}
static int BattleSystem_GetBattlerIdPartner(BattleSystem *s,int b){return b^2;}
static Pokemon *Party_GetMonByIndex(Party *p,int slot){return &p->mons[slot];}
static int GetMonData(Pokemon *m,int f,void *unused){switch(f){case MON_DATA_SPECIES:return m->species;case MON_DATA_IS_EGG:return m->egg;case MON_DATA_HP:return m->hp;default:assert(0);return 0;}}
static void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;}
static int BattleScriptReadWord(BattleContext *c){return c->words[c->pos++];}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){return 0;}
'''+native('CanSwitchMon')+native('BtlCmd_TryReplaceFaintedMon',path='src/battle/battle_command.c')+r'''
int main(void) {
 for(int trap=0;trap<4;trap++)for(int reason=0;reason<4;reason++) {
  BattleContext c={0};c.battleMons[0].status2=trap==1?STATUS2_MEAN_LOOK:trap==2?STATUS2_BIND:0;
  party=(Party){{{1,100,0},{2,100,0},{0,0,0}}};
  if(reason==1)party.mons[1].hp=0;
  if(reason==2)party.mons[1].egg=1;
  if(reason==3)party.mons[1].species=0;
  c.words[0]=62;c.words[1]=BATTLER_CATEGORY_ATTACKER;c.words[2]=1;c.words[3]=20;
  BtlCmd_TryReplaceFaintedMon(NULL,&c);
  assert(c.pos==(reason?24:4)&&c.showPartyFlags[0]==!reason);
 }
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1')
        import test_modern_original_abilities as original
        source=original.accuracy_source()+r'''
int main(void) {
 const int ids[]={524,815};
 for(int m=0;m<2;m++)for(int absorb=0;absorb<3;absorb++) {
  BattleContext c=fixture(MOVE_TACKLE);c.moveNoCur=ids[m];
  c.battleMons[1].ability=absorb==1?(m?ABILITY_WATER_ABSORB:ABILITY_VOLT_ABSORB):absorb==2?(m?ABILITY_STORM_DRAIN:ABILITY_LIGHTNINGROD):0;
  int script=BattleContext_CheckMoveImmunityFromAbility(&c,0,1);
  assert(!!script==!!absorb);
  if(absorb){assert(c.battleMons[0].hp==100);assert(Qol_GetExtendedMoveData(ids[m])->effect==228);}
 }
 return 0;
}
'''
        self.compile_run(source,'-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1','-Wno-unused-function','-Wno-unused-variable','-Wno-unused-but-set-variable','-Wno-sign-compare')


if __name__=='__main__':
    unittest.main()
