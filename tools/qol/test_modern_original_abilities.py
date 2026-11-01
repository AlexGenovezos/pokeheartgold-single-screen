"""Execute native C for the first targeted original-ability Gen IX batch."""
from pathlib import Path
import struct
import unittest
import test_game_logic as game
import test_modern_moves
import test_modern_rules as rules
import test_modern_competitive as competitive

ROOT = Path(__file__).resolve().parents[2]
UTIL = 'src/battle/battle_util.c'
PLAYER = 'src/battle/battle_controller_player.c'


def native(*names, path=UTIL):
    return '\n'.join(game.function_source(path, name) for name in names) + '\n'


def accuracy_source():
    return test_modern_moves.ModernMoveTests().source() + r'''
#include "constants/battle.h"
#include "constants/abilities.h"
#include "constants/items.h"
#include "constants/move_effects.h"
#include "constants/battle_subscript.h"
typedef int BattleSystem;
enum {NARC_a_0_0_1};
typedef struct {
 struct {int hp,maxHp,ability,status,type1,type2,statChanges[8];unsigned status2,moveEffectFlags;
  struct {int micleBerryFlag,battlerIdLockOn,magnetRiseTurns;} moveEffectData;} battleMons[4];
 struct {int moldBreakerFlag;} selfTurnData[4];
 struct {int protectFlag,roostFlag;} turnData[4];
 struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
 unsigned fieldCondition,battleStatus,moveStatusFlag;
 int moveType,moveNoCur,battlerIdAttacker,battlerIdTarget,checkMoveImmunityState,
  command,commandNext,script,hpCalc;
} BattleContext;
static int randomCalls,randomValue;
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static int CheckAbilityActive(BattleSystem *s,BattleContext *c,int mode,int mon,int ability){return 0;}
static int GetBattlerHeldItemEffect(BattleContext *c,int id){return 0;}
static int GetHeldItemModifier(BattleContext *c,int id,int unused){return 0;}
static int BattleContext_IsActionDone(BattleContext *c,int id){return 0;}
static int BattleSystem_Random(BattleSystem *s){randomCalls++;return randomValue;}
static void ReadBattleScriptFromNarc(BattleContext *c,int narc,int script){c->script=script;}
static int CurseUserIsGhost(BattleContext *c,int move,int a){return 0;}
static void UnlockBattlerOutOfCurrentMove(BattleSystem *s,BattleContext *c,int a){}
''' + rules.array('sHitChanceTable', PLAYER) + rules.array('sSoundMoves') + native(
        'Qol_MoveIgnoresTargetStatStages', 'GetBattlerAbility', 'CheckBattlerAbilityIfNotIgnored', 'DamageDivide',
        'BattleCtx_IsIdenticalToCurrentMove', 'BattleContext_CheckMoveImmunityFromAbility') + native(
        'BattleSystem_CheckMoveHit', 'BattleSystem_CheckMoveEffect',
        'BattleControllerPlayer_CheckMoveImmunity', path=PLAYER) + r'''
static BattleContext fixture(int move) {
 BattleContext c={0};c.moveNoCur=move;c.battlerIdTarget=1;
 c.battleMons[0].hp=c.battleMons[1].hp=c.battleMons[1].maxHp=100;
 for(int b=0;b<4;b++)for(int s=0;s<8;s++)c.battleMons[b].statChanges[s]=6;
 c.trainerAIData.moveData[move].type=TYPE_NORMAL;
 c.trainerAIData.moveData[move].accuracy=60;
 c.trainerAIData.moveData[move].power=40;
 c.trainerAIData.moveData[move].flags=2;randomCalls=0;
 return c;
}
'''


class OriginalAbilityTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def variants(self, source, *flags):
        for variant in ((), ('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source, *variant, '-Wno-sign-compare', *flags)

    def test_keen_eye_and_illuminate_ignore_all_evasion_but_keep_accuracy_and_other_factors(self):
        self.variants(accuracy_source() + r'''
int main(void) {
 const int abilities[]={ABILITY_KEEN_EYE,ABILITY_ILLUMINATE};
 const int factors[]={100,75,60,50,43,36,33};
 for(int a=0;a<2;a++)for(int ev=0;ev<=12;ev+=6)for(int acc=0;acc<=6;acc+=3)
 for(int suppress=0;suppress<2;suppress++)for(int fog=0;fog<2;fog++)for(int roll=0;roll<100;roll++) {
  BattleContext c=fixture(MOVE_TACKLE);c.battleMons[0].ability=abilities[a];
  c.battleMons[1].ability=ABILITY_MOLD_BREAKER; // does not ignore the user's own ability
  c.battleMons[0].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].statChanges[STAT_ACC]=acc;c.battleMons[1].statChanges[STAT_EVASION]=ev;
  c.fieldCondition=fog?FIELD_CONDITION_FOG:0;randomValue=roll;
  int stage=acc-6+((QOL_MODERN_BATTLE&&!suppress)?0:6-ev);
  if(stage < -6)stage=-6;if(stage>6)stage=6;
  // Independent rational accuracy table, including truncation before fog.
  int rate=stage<=0?60*factors[-stage]/100:60*(stage+3)/3;
  if(stage==0)rate=60;
  if(fog)rate=rate*6/10;
  BattleSystem_CheckMoveHit(NULL,&c,0,1,MOVE_TACKLE);
  assert(!!(c.moveStatusFlag&MOVE_STATUS_MISSED)==(roll+1>rate));
  assert(randomCalls==1);
 }
 return 0;
}
''', '-Wno-unused-function', '-Wno-unused-variable', '-Wno-unused-but-set-variable', '-Wno-misleading-indentation')

    def test_illuminate_accuracy_drop_protection_suppression_mold_breaker_and_other_stats(self):
        self.variants(competitive.stat_source() + r'''
int main(void) {
 const int abilities[]={ABILITY_KEEN_EYE,ABILITY_ILLUMINATE};
 for(int a=0;a<2;a++)for(int suppress=0;suppress<2;suppress++)for(int mold=0;mold<2;mold++)
 for(int stat=1;stat<=7;stat++)for(int self=0;self<2;self++) {
  BattleContext c=fixture();c.battleMons[1].ability=abilities[a];
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  if(self)c.battlerIdAttacker=1;
  mutate(&c,22+stat-1);
  int blocked=stat==STAT_ACC&&!self&&!suppress&&!mold&&(a==0||QOL_MODERN_BATTLE);
  assert(c.battleMons[1].statChanges[stat]==(blocked?6:5));
  assert(!(c.statChangeFlag&1)); // no accidental Competitive dispatch
  if(QOL_MODERN_BATTLE&&stat!=STAT_ACC) {
   assert(!c.selfTurnData[c.battlerIdAttacker].moldBreakerFlag);
   assert(!(c.battleStatus&BATTLE_STATUS_MOLD_BREAKER));
  }
 }
 return 0;
}
''', '-Wno-unused-function')

    def test_flash_fire_intercepts_frozen_wisp_before_rng_but_respects_protect_and_semi_states(self):
        self.variants(accuracy_source() + r'''
int main(void) {
 for(int moveKind=0;moveKind<3;moveKind++)for(int frozen=0;frozen<2;frozen++)
 for(int mold=0;mold<2;mold++)for(int suppress=0;suppress<2;suppress++)for(int fail=0;fail<6;fail++) {
  int move=moveKind==1?MOVE_WILL_O_WISP:MOVE_EMBER;
  BattleContext c=fixture(move);c.battleMons[1].ability=ABILITY_FLASH_FIRE;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  c.battleMons[1].status=frozen?STATUS_FREEZE:0;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.trainerAIData.moveData[move].type=TYPE_FIRE;
  c.trainerAIData.moveData[move].power=moveKind?0:40;
  c.trainerAIData.moveData[move].accuracy=1;randomValue=99;
  c.battleMons[0].moveEffectData.micleBerryFlag=1;
  if(fail==1)c.turnData[1].protectFlag=1;
  if(fail==2)c.battleMons[1].moveEffectFlags|=MOVE_EFFECT_FLAG_FLY;
  if(fail==3)c.battleMons[1].moveEffectFlags|=MOVE_EFFECT_FLAG_DIG;
  if(fail==4)c.battleMons[1].moveEffectFlags|=MOVE_EFFECT_FLAG_DIVE;
  if(fail==5)c.battleMons[1].moveEffectFlags|=MOVE_EFFECT_FLAG_PHANTOM_FORCE;
  int eligible=moveKind!=2&&!mold&&!suppress;
  int intercept=QOL_MODERN_BATTLE&&eligible;
  BattleSystem_CheckMoveHit(NULL,&c,0,1,move);
  assert(randomCalls==!intercept);
  assert(c.battleMons[0].moveEffectData.micleBerryFlag==intercept);
  BattleSystem_CheckMoveEffect(NULL,&c,0,1,move);
  int expected=intercept&&!fail;
  assert(BattleControllerPlayer_CheckMoveImmunity(NULL,&c)==expected);
  if(expected)assert(c.script==BATTLE_SUBSCRIPT_ABSORB_AND_BOOST_FIRE_TYPE_MOVES);
  assert(c.battleMons[1].status==(frozen?STATUS_FREEZE:0));
  assert(c.battleMons[1].hp==100&&c.hpCalc==0);
  // Runtime predicate on a successful accuracy path, including repeated activation.
  c.battleStatus=0;
  for(int repeat=0;repeat<2;repeat++) {
   int active=eligible&&(QOL_MODERN_BATTLE||!frozen);
   assert(BattleContext_CheckMoveImmunityFromAbility(&c,0,1)==
    (active?BATTLE_SUBSCRIPT_ABSORB_AND_BOOST_FIRE_TYPE_MOVES:0));
  }
  c.battleStatus=BATTLE_STATUS_CHARGE_TURN;
  assert(BattleContext_CheckMoveImmunityFromAbility(&c,0,1)==0);
 }
 return 0;
}
''', '-Wno-unused-variable', '-Wno-unused-but-set-variable')

    def test_flash_fire_preview_runtime_agree_when_frozen_without_mutating_flags(self):
        source = accuracy_source() + r'''
static int GetBattlerVar(BattleContext *c,int id,int field,void *out){return field==BMON_DATA_TYPE_1?c->battleMons[id].type1:c->battleMons[id].type2;}
''' + rules.array('sTypeEffectiveness') + rules.array('sFixedDamageMoveEffects') + native(
            'CheckChargeMoveHitTurn', 'BattleSystem_IsTypeMatchupActive', 'IsFixedDamageMove',
            'Qol_PreviewTypeEffectiveness')
        self.variants(source + r'''
int main(void) {
 for(int frozen=0;frozen<2;frozen++)for(int suppress=0;suppress<2;suppress++)for(int mold=0;mold<2;mold++) {
  BattleContext c=fixture(MOVE_EMBER);c.battleMons[1].ability=ABILITY_FLASH_FIRE;
  c.battleMons[1].status=frozen?STATUS_FREEZE:0;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  c.trainerAIData.moveData[MOVE_EMBER].type=TYPE_FIRE;
  c.trainerAIData.moveData[MOVE_EMBER].category=CATEGORY_SPECIAL;
  c.selfTurnData[0].moldBreakerFlag=7;c.battleStatus=0x123456;
  BattleContext before=c;
  int expected=!mold&&!suppress&&(QOL_MODERN_BATTLE||!frozen);
  assert(Qol_PreviewTypeEffectiveness(&c,MOVE_EMBER,0,1)==(expected?0:40));
  assert(!memcmp(&c,&before,sizeof(c)));
  c.battleStatus=0;
  assert(!!BattleContext_CheckMoveImmunityFromAbility(&c,0,1)==expected);
 }
 return 0;
}
''', '-Wno-unused-function', '-Wno-unused-variable', '-Wno-unused-but-set-variable')

    def test_flash_fire_dynamic_fire_override_and_normalize_match_accuracy_and_immunity(self):
        self.variants(accuracy_source() + r'''
int main(void) {
 for(int normalize=0;normalize<2;normalize++)for(int override=0;override<2;override++) {
  BattleContext c=fixture(MOVE_WEATHER_BALL);c.battleMons[1].ability=ABILITY_FLASH_FIRE;
  c.battleMons[1].status=STATUS_FREEZE;c.battleMons[0].ability=normalize?ABILITY_NORMALIZE:ABILITY_NONE;
  c.moveType=override?TYPE_FIRE:0;c.trainerAIData.moveData[MOVE_WEATHER_BALL].accuracy=1;randomValue=99;
  int expected=QOL_MODERN_BATTLE&&override&&!normalize;
  BattleSystem_CheckMoveHit(NULL,&c,0,1,MOVE_WEATHER_BALL);
  assert(randomCalls==!expected);
  assert(!!BattleContext_CheckMoveImmunityFromAbility(&c,0,1)==expected);
 }
 return 0;
}
''', '-Wno-unused-function', '-Wno-unused-variable', '-Wno-unused-but-set-variable')

    def test_plus_minus_requires_distinct_living_active_ally_for_special_damage(self):
        source = rules.COMMON + r'''
typedef struct {int power,type,category,effect,range;} Move;
typedef struct {
 struct {int hp,ability;unsigned moveEffectFlags;} battleMons[4];
 struct {int helpingHandFlag;} turnData[4];
 struct {Move moveData[NUM_MOVES+1];int calcTemp;} trainerAIData;
 int powerMultiplier,fieldCondition;
} BattleContext;
static int vars[4][256],maxBattlers;
static int GetBattlerVar(BattleContext *c,int id,int field,void *unused){return vars[id][field];}
static int GetBattlerHeldItem(BattleContext *c,int id){return 0;}
static int GetItemVar(BattleContext *c,int item,int field){return 0;}
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return maxBattlers;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int id){return id&1;}
static int BattleContext_Get(BattleSystem *s,BattleContext *c,int field,int id){return 10;}
static int CheckBattlerAbilityIfNotIgnored(BattleContext *c,int a,int d,int ability){return GetBattlerAbility(c,d)==ability;}
static int CheckMoveEffectOnField(BattleSystem *s,BattleContext *c,int effect){return 0;}
static int GetMonsHitCount(BattleSystem *s,BattleContext *c,int side,int id){return 1;}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''
        # Declaration before dependent environmental stubs; actual ability accessor below.
        source = source.replace('static int vars[4][256],maxBattlers;',
                                'static int vars[4][256],maxBattlers;\nu8 GetBattlerAbility(BattleContext *c,int id);')
        util = (ROOT / UTIL).read_text()
        structure = util[util.index('typedef struct MoveDamageCalc {'):util.index('} MoveDamageCalc;')+len('} MoveDamageCalc;')]
        source += native('GetBattlerAbility', 'CheckAbilityActive') + '#if QOL_MODERN_BATTLE\n' + rules.helper('Qol_HasPlusMinusAlly', UTIL) + '#endif\n'
        source += structure + ''.join(rules.array(n) for n in ('sStatChangeTable','sTypeEnhancingItems','sPunchingMoves')) + native('Qol_MoveUsesPhysicalDefense') + native('CalcMoveDamage')
        self.variants(source + r'''
int main(void) {
 (void)BattleSystem_Random(NULL);
 for(int a=0;a<2;a++)for(int partner=0;partner<3;partner++)for(int hp=0;hp<2;hp++)
 for(int suppress=0;suppress<2;suppress++)for(int ownSuppress=0;ownSuppress<2;ownSuppress++)
 for(int doubles=0;doubles<2;doubles++)for(int side=0;side<2;side++)for(int category=0;category<2;category++) {
  BattleContext c={0};c.powerMultiplier=10;maxBattlers=doubles?4:2;
  for(int b=0;b<4;b++) {
   vars[b][BMON_DATA_ATK]=vars[b][BMON_DATA_SPATK]=vars[b][BMON_DATA_DEF]=vars[b][BMON_DATA_SPDEF]=100;
   vars[b][BMON_DATA_LEVEL]=50;vars[b][BMON_DATA_GENDER]=MON_GENDERLESS;
   vars[b][BMON_DATA_STAT_CHANGE_ATK]=vars[b][BMON_DATA_STAT_CHANGE_DEF]=6;
   vars[b][BMON_DATA_STAT_CHANGE_SPATK]=vars[b][BMON_DATA_STAT_CHANGE_SPDEF]=6;
  }
  int ability=a?ABILITY_MINUS:ABILITY_PLUS;
  c.battleMons[0].hp=100;c.battleMons[0].ability=ability;
  c.battleMons[0].moveEffectFlags=ownSuppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int ally=side?3:2;c.battleMons[ally].hp=hp?100:0;
  c.battleMons[ally].ability=partner==0?ABILITY_NONE:partner==1?ABILITY_PLUS:ABILITY_MINUS;
  c.battleMons[ally].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.trainerAIData.moveData[MOVE_TACKLE]=(Move){100,TYPE_NORMAL,category,0,0};
  int paired=partner&&(QOL_MODERN_BATTLE||c.battleMons[ally].ability!=ability);
  int boosted=category==CATEGORY_SPECIAL&&paired&&hp&&!suppress&&!ownSuppress&&doubles&&!side;
  assert(CalcMoveDamage(NULL,&c,MOVE_TACKLE,0,0,0,0,0,1,1)==(boosted?68:46));
  // Hypothetical party candidates use the same slot: never invent a second ally
  // from the evaluated user's own Plus/Minus, even with a populated inactive slot.
  maxBattlers=2;c.battleMons[0].hp=0;
  assert(CalcMoveDamage(NULL,&c,MOVE_TACKLE,0,0,0,0,0,1,1)==46);
 }
 return 0;
}
''', '-Wno-sign-compare')


class OriginalAbilitySdkTests(unittest.TestCase):
    def test_original_flash_fire_script_boosts_once_and_keeps_frozen_status_and_hp(self):
        from battle_scripts import battle_script_tools, compile_battle_script
        from nitro_data import unpack_narc
        try:
            battle_script_tools()
        except FileNotFoundError as error:
            self.skipTest(str(error))
        archive = ROOT / 'files/battledata/script/subscript.narc'
        if not archive.is_file():
            self.skipTest('Original battle subscript archive is absent')
        script = compile_battle_script((ROOT / 'files/battledata/script/subscript/subscript_0179_FlashFire.s').read_text())
        self.assertEqual(script, unpack_narc(archive.read_bytes())[0][179])
        words = ','.join(str(w)+'u' for w in struct.unpack('<'+'I'*(len(script)//4),script))
        source = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include "constants/battle.h"
#include "constants/message_tags.h"
typedef int BOOL;typedef uint32_t u32;typedef int BattleSystem;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
typedef struct {int pos,flashFire,status,hp,message,updates;} BattleContext;
static const u32 script[]={WORDS};
static void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;assert(c->pos>=0&&c->pos<sizeof(script)/4);}
static int BattleScriptReadWord(BattleContext *c){assert(c->pos<sizeof(script)/4);return script[c->pos++];}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){assert(side==BATTLER_CATEGORY_DEFENDER);return 1;}
static int GetBattlerVar(BattleContext *c,int id,int field,void *out){assert(id==1&&field==BMON_DATA_FLASH_FIRE);return c->flashFire;}
static void SetBattlerVar(BattleContext *c,int id,int field,int *v){assert(id==1&&field==BMON_DATA_FLASH_FIRE);c->flashFire=*v;c->updates++;}
static void BattlerSetAbility(BattleContext *c,int id,int value){assert(0);}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int id){}
static int MaskOfFlagNo(int n){return 1u<<n;}
'''.replace('WORDS', words) + native('BtlCmd_CompareMonDataToValue', 'BtlCmd_UpdateMonData', path='src/battle/battle_command.c') + r'''
static void run(BattleContext *c) {
 c->pos=0;
 for(int steps=0;steps<100;steps++) {
  switch(script[c->pos]) {
  case 14:case 17:c->pos++;break;
  case 18:{c->pos++;c->message=BattleScriptReadWord(c);int tag=BattleScriptReadWord(c);
   c->pos+=(tag>0)+(tag>TAG_TRNAME)+(tag>TAG_TRCLASS_TRNAME)+(tag>TAG_TRCLASS_TRNAME_ITEM);break;}
  case 30:c->pos+=2;break;
  case 33:BtlCmd_CompareMonDataToValue(NULL,c);break;
  case 52:BtlCmd_UpdateMonData(NULL,c);break;
  case 224:return;
  default:assert(0);
  }
 }
 assert(0);
}
int main(void) {
 for(int frozen=0;frozen<2;frozen++) {
  BattleContext c={0};c.status=frozen?STATUS_FREEZE:0;c.hp=100;
  for(int repeat=0;repeat<3;repeat++) {
   run(&c);assert(c.flashFire==1&&c.updates==1);
   assert(c.message==(repeat?714:656));
   assert(c.hp==100&&c.status==(frozen?STATUS_FREEZE:0));
  }
 }
 return 0;
}
'''
        game.GameLogicTests.compile_run(self, source, '-Wno-sign-compare')


if __name__ == '__main__':
    unittest.main()
