"""B6 selected-stat contracts execute the shared native damage and hit paths."""
from pathlib import Path
from collections import Counter
import itertools
import json
import re
import struct
import unittest
import test_game_logic as game
import test_modern_snow as snow
import test_modern_moves as moves
import test_modern_rules as rules
import move_resources
import learnset_import
import test_modern_original_abilities as original
import test_modern_sturdy as sturdy
ROOT=Path(__file__).resolve().parents[2]
ROWS=[(476,0,1,80,14,100,10,0,0,0,50,428),(543,0,1,100,14,100,10,0,0,0,50,94),
      (495,0,0,95,17,100,15,0,0,0,51,242),(779,0,0,80,1,100,10,0,0,0,51,34),
      (536,0,0,90,1,100,15,0,0,0,51,427),(666,0,0,85,17,100,15,0,0,0,51,242)]

def damage_source():
    source=snow.damage_source().replace('moveData[NUM_MOVES+1]','moveData[900]')
    return source+r'''
static int calc(BattleContext *c,int move,int field,int crit,int side){
 int category=(move==476||move==543)?CATEGORY_SPECIAL:CATEGORY_PHYSICAL;
 c->trainerAIData.moveData[move]=(Move){100,TYPE_NORMAL,category,0,0};
 int saved=rngCalls;int result=CalcMoveDamage(NULL,c,move,side,field,100,0,0,1,crit);
 assert(saved==rngCalls);return result;
}
static int oracle(int offense,int defense){return offense*100*22/defense/50+2;}
'''

class SelectedStatTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run
    def variants(self,source):
        for bits in itertools.product((0,1),repeat=3):
            flags=tuple(f'-D{name}={bit}' for name,bit in zip(('QOL_MODERN_TYPES','QOL_MODERN_BATTLE','QOL_MODERN_MOVES'),bits))
            with self.subTest(flags=flags):
                self.compile_run(source,*flags,'-Wno-unused-function','-Wno-sign-compare','-Wno-unused-variable','-Wno-unused-but-set-variable')

    def test_psyshock_selected_defense_and_foul_play_body_press_raw_offense(self):
        self.variants(damage_source()+r'''
int main(void){
 BattleContext c=fixture();vars[1][BMON_DATA_DEF]=101;vars[1][BMON_DATA_SPDEF]=503;
 assert(calc(&c,476,0,1,0)==oracle(1000,QOL_MODERN_MOVES?101:503));
 vars[1][BMON_DATA_ATK]=407;vars[0][BMON_DATA_DEF]=211;
 assert(calc(&c,495,0,1,0)==oracle(QOL_MODERN_MOVES?407:1000,101));
 assert(calc(&c,779,0,1,0)==oracle(QOL_MODERN_MOVES?211:1000,101));
 return 0;}
''')

    def test_literal_metadata_and_regenerated_learnsets(self):
        entries={r['id']:r for r in move_resources.read_entries(ROOT/'include/data/qol_move_entries.inc')}
        self.assertEqual(len(entries),72)
        for row in ROWS:self.assertEqual(tuple(entries[row[0]][f] for f in move_resources.FIELDS),row)
        profile=json.loads((ROOT/'.local-tools/validation/gen9-import-profile.json').read_text())
        actual=(ROOT/'include/data/qol_learnsets.inc').read_text()
        self.assertEqual(learnset_import.generate(profile),actual)
        rows=[tuple(map(int,r)) for r in re.findall(r'QOL_LEVEL_UP_MOVE\((\d+), (\d+), (\d+)\)',actual)]
        self.assertEqual(len(rows),336);self.assertEqual(len({s for s,l,m in rows}),237)
        self.assertIn((150,72,543),rows);self.assertIn((475,1,536),rows);self.assertIn((486,42,779),rows)
        self.assertEqual(Counter(m for s,l,m in rows if m in {r[0] for r in ROWS}),Counter({476:9,543:1,495:6,779:1,536:1}))
        self.assertEqual(sum('MOVE_DARKEST_LARIAT' in profile['learnsets'][mon['constant']]['MachineMoves'] for mon in profile['species']),8)
        self.assertEqual(sum(m==666 for s,l,m in rows),0)


    def test_selected_defense_stages_snow_items_abilities_and_category_screens(self):
        self.variants(damage_source()+r"""
static int stageStat(int raw,int stage){return stage>=6?raw*(stage-4)/2:raw*2/(8-stage);}
int main(void){
#if QOL_MODERN_MOVES
 for(int move=476;move<=543;move+=67)for(int stage=0;stage<=12;stage++)
 for(int crit=1;crit<=2;crit++)for(int unaware=0;unaware<2;unaware++)
 for(int modifier=0;modifier<3;modifier++)for(int ice=0;ice<3;ice++){
  BattleContext c=fixture();vars[1][BMON_DATA_SPDEF]=907;vars[1][BMON_DATA_STAT_CHANGE_SPDEF]=12;
  vars[1][BMON_DATA_STAT_CHANGE_DEF]=stage;vars[1][BMON_DATA_TYPE_1]=ice==1?TYPE_ICE:TYPE_NORMAL;
  vars[1][BMON_DATA_TYPE_2]=ice==2?TYPE_ICE:TYPE_NORMAL;
  c.battleMons[0].ability=unaware?ABILITY_UNAWARE:ABILITY_NONE;
  if(modifier==1){c.battleMons[1].ability=ABILITY_MARVEL_SCALE;vars[1][BMON_DATA_STATUS]=STATUS_POISON;}
  if(modifier==2){items[1]=HOLD_EFFECT_DITTO_DEF_UP;vars[1][BMON_DATA_SPECIES]=SPECIES_DITTO;}
  int chosen=unaware||(crit>1&&stage>6)?6:stage,d=101;
#if !QOL_MODERN_BATTLE
  if(modifier==1)d=d*3/2;if(modifier==2)d*=2;
#endif
  d=stageStat(d,chosen);
#if QOL_MODERN_BATTLE
  if(ice)d=d*3/2;if(modifier==1)d=d*3/2;if(modifier==2)d*=2;
#endif
  assert(calc(&c,move,FIELD_CONDITION_HAIL,crit,0)==oracle(1000,d));
 }
 BattleContext c=fixture();vars[1][BMON_DATA_TYPE_1]=TYPE_ICE;
 vars[1][BMON_DATA_STAT_CHANGE_DEF]=8;c.fieldCondition=FIELD_CONDITION_HAIL;
 assert(calc(&c,476,0,1,0)==oracle(1000,202)); // supplied field, not ctx weather
 assert(calc(&c,476,FIELD_CONDITION_HAIL,1,0)==oracle(1000,QOL_MODERN_BATTLE?303:202));
 for(int ability=0;ability<2;ability++)for(int suppress=0;suppress<2;suppress++){
  c=fixture();vars[1][BMON_DATA_TYPE_2]=TYPE_ICE;
  c.battleMons[2].hp=100;c.battleMons[2].ability=ability?ABILITY_CLOUD_NINE:ABILITY_AIR_LOCK;
  c.battleMons[2].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  assert(calc(&c,476,FIELD_CONDITION_HAIL,1,0)==oracle(1000,QOL_MODERN_BATTLE&&suppress?151:101));
 }
 for(int mold=0;mold<2;mold++)for(int suppress=0;suppress<2;suppress++){
  c=fixture();c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  c.battleMons[1].ability=ABILITY_MARVEL_SCALE;vars[1][BMON_DATA_STATUS]=STATUS_POISON;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  assert(calc(&c,476,0,1,0)==oracle(1000,!mold&&!suppress?151:101));
 }
 // Selected Defense excludes every Sp. Def-only modifier, including Sand.
 c=fixture();vars[1][BMON_DATA_TYPE_1]=TYPE_ROCK;vars[1][BMON_DATA_SPECIES]=SPECIES_CLAMPERL;
 items[1]=HOLD_EFFECT_CLAMPERL_SPDEF;
 assert(calc(&c,476,FIELD_CONDITION_SANDSTORM,1,0)==oracle(1000,101));
 vars[1][BMON_DATA_SPECIES]=SPECIES_LATIAS;items[1]=HOLD_EFFECT_LATI_SPECIAL;
 assert(calc(&c,543,0,1,0)==oracle(1000,101));
 c=fixture();vars[0][BMON_DATA_ATK]=11;vars[0][BMON_DATA_SPATK]=1000;
 vars[0][BMON_DATA_STATUS]=STATUS_BURN;
 assert(calc(&c,476,0,1,SIDE_CONDITION_REFLECT)==oracle(1000,101));
 assert(calc(&c,476,0,1,SIDE_CONDITION_LIGHT_SCREEN)==(oracle(1000,101)-2)/2+2);
 assert(calc(&c,476,0,2,SIDE_CONDITION_LIGHT_SCREEN)==oracle(1000,101));
 // The one-point odd-stat fixture distinguishes stage-before-Snow rounding.
 c=fixture();vars[1][BMON_DATA_STAT_CHANGE_DEF]=8;vars[1][BMON_DATA_TYPE_1]=TYPE_ICE;
 c.battleMons[1].ability=ABILITY_MARVEL_SCALE;vars[1][BMON_DATA_STATUS]=STATUS_POISON;
 assert(calc(&c,476,FIELD_CONDITION_HAIL,1,0)==oracle(1000,QOL_MODERN_BATTLE?454:302));
#endif
 return 0;}
""")

    def test_foul_play_body_press_selected_stage_crit_unaware_and_user_modifiers(self):
        self.variants(damage_source()+r"""
static int staged(int raw,int stage){return stage>=6?raw*(stage-4)/2:raw*2/(8-stage);}
int main(void){
#if QOL_MODERN_MOVES
 for(int which=0;which<2;which++)for(int stage=0;stage<=12;stage++)
 for(int crit=1;crit<=2;crit++)for(int defenderUnaware=0;defenderUnaware<2;defenderUnaware++)
 for(int userUnaware=0;userUnaware<2;userUnaware++)for(int mold=0;mold<2;mold++)for(int suppress=0;suppress<2;suppress++){
  BattleContext c=fixture();int move=which?779:495,raw=which?211:407;
  vars[0][BMON_DATA_DEF]=211;vars[1][BMON_DATA_ATK]=407;
  vars[0][BMON_DATA_STAT_CHANGE_ATK]=1;vars[0][BMON_DATA_STAT_CHANGE_DEF]=stage;
  vars[1][BMON_DATA_STAT_CHANGE_ATK]=stage;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:userUnaware?ABILITY_UNAWARE:ABILITY_NONE;
  c.battleMons[1].ability=defenderUnaware?ABILITY_UNAWARE:ABILITY_NONE;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int selected=(defenderUnaware&&!mold&&!suppress)||(crit>1&&stage<6)?6:stage;
  assert(calc(&c,move,0,crit,0)==oracle(staged(raw,selected),101));
 }
 for(int which=0;which<2;which++)for(int mod=0;mod<6;mod++)for(int targetBurn=0;targetBurn<2;targetBurn++){
  BattleContext c=fixture();int move=which?779:495,raw=which?211:407;
  vars[0][BMON_DATA_DEF]=211;vars[1][BMON_DATA_ATK]=407;
  vars[1][BMON_DATA_STATUS]=targetBurn?STATUS_BURN:0;
  c.battleMons[1].ability=ABILITY_HUGE_POWER;items[1]=HOLD_EFFECT_CHOICE_ATK;
  if(mod==1)c.battleMons[0].ability=ABILITY_HUGE_POWER;
  if(mod==2)items[0]=HOLD_EFFECT_CHOICE_ATK;
  if(mod==3)vars[0][BMON_DATA_STATUS]=STATUS_BURN;
  if(mod==4){c.battleMons[0].ability=ABILITY_GUTS;vars[0][BMON_DATA_STATUS]=STATUS_BURN;}
  if(mod==5){c.battleMons[0].ability=ABILITY_SLOW_START;vars[0][BMON_DATA_SLOW_START_TURN_NUMBER]=8;}
  int offense=mod==1?raw*2:mod==2||mod==4?raw*3/2:mod==5?raw/2:raw;
  int expected=oracle(offense,101);if(mod==3)expected=(expected-2)/2+2;
  assert(calc(&c,move,0,1,0)==expected);
 }
 // Defensive boosts on the user never modify Body Press's offensive Defense.
 for(int mod=0;mod<3;mod++){
  BattleContext c=fixture();vars[0][BMON_DATA_DEF]=211;vars[0][BMON_DATA_TYPE_1]=TYPE_ICE;
  if(mod==1){c.battleMons[0].ability=ABILITY_MARVEL_SCALE;vars[0][BMON_DATA_STATUS]=STATUS_POISON;}
  if(mod==2){items[0]=HOLD_EFFECT_DITTO_DEF_UP;vars[0][BMON_DATA_SPECIES]=SPECIES_DITTO;}
  assert(calc(&c,779,FIELD_CONDITION_HAIL,1,0)==oracle(211,101));
 }
#endif
 return 0;}
""")

    def test_sacred_sword_lariat_ignore_both_target_defense_stage_directions(self):
        self.variants(damage_source()+r"""
int main(void){
#if QOL_MODERN_MOVES
 const int ids[]={536,666};for(int m=0;m<2;m++)for(int stage=0;stage<=12;stage++){
  BattleContext c=fixture();vars[1][BMON_DATA_STAT_CHANGE_DEF]=stage;
  assert(calc(&c,ids[m],0,1,0)==oracle(1000,101));
  c.battleMons[1].ability=ABILITY_MARVEL_SCALE;vars[1][BMON_DATA_STATUS]=STATUS_POISON;
  assert(calc(&c,ids[m],0,1,0)==oracle(1000,151));
  c.battleMons[0].ability=ABILITY_MOLD_BREAKER;
  assert(calc(&c,ids[m],0,1,0)==oracle(1000,101));
 }
#endif
 return 0;}
""")

    def test_real_accuracy_preserves_user_stages_hustle_target_abilities_and_items(self):
        source=original.accuracy_source()
        source=source.replace('static int GetBattlerHeldItemEffect(BattleContext *c,int id){return 0;}',
            'static int hitItems[4],hitMods[4];\nstatic int GetBattlerHeldItemEffect(BattleContext *c,int id){return hitItems[id];}')
        source=source.replace('static int GetHeldItemModifier(BattleContext *c,int id,int unused){return 0;}',
            'static int GetHeldItemModifier(BattleContext *c,int id,int unused){return hitMods[id];}')
        self.variants(source+r"""
int main(void){
#if QOL_MODERN_MOVES
 const int ids[]={536,666};
 for(int m=0;m<2;m++)for(int accuracy=0;accuracy<=12;accuracy++)for(int evasion=0;evasion<=12;evasion++)
 for(int modifier=0;modifier<5;modifier++){
  BattleContext c=fixture(MOVE_TACKLE);memset(hitItems,0,sizeof(hitItems));memset(hitMods,0,sizeof(hitMods));
  c.battleMons[0].statChanges[STAT_ACC]=accuracy;c.battleMons[1].statChanges[STAT_EVASION]=evasion;
  int chance=100*sHitChanceTable[accuracy][0]/sHitChanceTable[accuracy][1];
  if(modifier==1){c.battleMons[0].ability=ABILITY_HUSTLE;chance=chance*80/100;}
  if(modifier==2){c.battleMons[1].ability=ABILITY_TANGLED_FEET;c.battleMons[1].status2=STATUS2_CONFUSION;chance=chance*50/100;}
  if(modifier==3){hitItems[1]=HOLD_EFFECT_ACC_REDUCE;hitMods[1]=20;chance=chance*80/100;}
  if(modifier==4){hitItems[0]=HOLD_EFFECT_ACCURACY_UP;hitMods[0]=10;chance=chance*110/100;}
  for(randomValue=0;randomValue<100;randomValue++){
   c.moveStatusFlag=0;int before=randomCalls;
   assert(!BattleSystem_CheckMoveHit(NULL,&c,0,1,ids[m]));
   assert(!!(c.moveStatusFlag&MOVE_STATUS_MISSED)==(randomValue+1>chance));
   assert(randomCalls==before+1);
  }
 }
#endif
 return 0;}
""")


    def test_metadata_accessors_metronome_classifiers_and_abi_all_flags(self):
        source=moves.ModernMoveTests().source()+r"""
#include "constants/battle.h"
typedef int BattleSystem;typedef int BattleContext;
static int BattleContext_CheckMoveUnuseableInGravity(BattleSystem *s,BattleContext *c,int b,int m){return 0;}
static int BattleContext_CheckMoveHealBlocked(BattleSystem *s,BattleContext *c,int b,int m){return 0;}
"""+rules.array('sMetronomeUnuseableMoves')+rules.array('sPunchingMoves')+snow.native('CheckLegalMimicMove')+snow.native('CheckLegalMetronomeMove')
        source+='static const int rows[][12]={'+','.join('{'+','.join(map(str,r))+'}' for r in ROWS)+'};\n'
        self.variants(source+r"""
int main(void){
 assert(NUM_MOVES==467&&sizeof(MoveTbl)==16&&QOL_EXTENDED_MOVE_COUNT==72);
 struct {MoveTbl moveData[NUM_MOVES+1];} ai;assert(NELEMS(ai.moveData)==468);
 for(unsigned r=0;r<NELEMS(rows);r++){
  int move=rows[r][0];const MoveTbl *e=Qol_GetExtendedMoveData(move);
  assert(Qol_IsSupportedMove(move)==QOL_MODERN_MOVES);
#if QOL_MODERN_MOVES
  const int actual[]={e->effect,e->category,e->power,e->type,e->accuracy,e->pp,e->effectChance,e->range,e->priority,e->flags,Qol_GetMoveAnimation(move)};
  for(int f=0;f<11;f++)assert(actual[f]==rows[r][f+1]);
#else
  assert(!e);
#endif
  assert(!Qol_IsSoundMove(move)&&!Qol_MoveBypassesSubstitute(move));
  for(unsigned i=0;i<NELEMS(sPunchingMoves);i++)assert(sPunchingMoves[i]!=move);
  assert(CheckLegalMimicMove(move));
  assert(CheckLegalMetronomeMove(NULL,NULL,0,move)==!(QOL_MODERN_MOVES&&move==779));
 }
 const int gaps[]={468,469,470,487,500,538,65535};
 for(unsigned i=0;i<NELEMS(gaps);i++)assert(!Qol_IsSupportedMove(gaps[i]));
 return 0;}
""")
        profile=json.loads((ROOT/'.local-tools/validation/gen9-import-profile.json').read_text())
        pinned={m['engine_id']:m for m in profile['moves']}
        for row in ROWS:
            data=move_resources.PRESENTATION[row[0]]
            self.assertEqual(data['name'],pinned[row[0]]['name'])
            self.assertLess(len(data['name']),32)
            alias=next((ROOT/'files/battledata/script/move_script').glob(f'move_script_{row[-1]:04}*.s'))
            self.assertEqual([l.strip() for l in alias.read_text().splitlines() if l.strip() and not l.strip().startswith(('.','_','//'))],['GoToEffectScript'])

    def test_real_trainer_ai_shared_selected_stats_numeric_damage_no_rng(self):
        source=snow.damage_source()
        definitions='\n#undef BATTLE_MOVE_DATA\n#undef Qol_IsSupportedMove\n'+''.join(moves.no_includes((ROOT/p).read_text()) for p in ('include/move.h','include/qol_moves.h','src/qol_moves.c'))+'\ntypedef MoveTbl Move;'
        source=source.replace('typedef struct {int power,type,category,effect,range;} Move;',definitions)
        source=source.replace('(Move){500,TYPE_NORMAL,CATEGORY_PHYSICAL,0,0}', '(Move){.power=100,.type=TYPE_NORMAL,.category=CATEGORY_PHYSICAL}')
        source=source.replace('int hp,ability,status,item,statChanges[8];','int hp,ability,status,item,statChanges[8],level,friendship,weight;')
        source=source.replace('int calcTemp;} trainerAIData;', 'int calcTemp,battlerIdTarget;} trainerAIData;')
        source=source.replace('int powerMultiplier,fieldCondition;', 'int powerMultiplier,fieldCondition,effectiveSpeed[4];unsigned fieldSideConditionFlags[2];')
        source+=r"""
#define MOVE_STATUS_IMMUNE (MOVE_STATUS_NO_EFFECT|MOVE_STATUS_LEVITATE_IMMUNE|MOVE_STATUS_WONDER_GUARD_IMMUNE|MOVE_STATUS_MAGNET_RISE_IMMUNE)
static const u16 sWeightToPower[][2]={{0xFFFF,0xFFFF}};
enum {WEIGHT_TO_POWER_WEIGHT,WEIGHT_TO_POWER_POWER};
static int TrainerAI_MoveType(BattleSystem *s,BattleContext *c,int b,int move){return TYPE_NORMAL;}
static int BattleSystem_ApplyTypeEffectiveness(BattleSystem *s,BattleContext *c,int m,int type,int a,int d,int damage,u32 *flags){return damage;}
"""+snow.native('DamageDivide')+snow.native('TrainerAI_CalcDamage','src/battle/trainer_ai.c')+r"""
static int oracle(int offense,int defense,int power){return offense*power*22/defense/50+2;}
int main(void){
#if QOL_MODERN_MOVES
 const int ids[]={476,543,495,779,536,666},powers[]={80,100,95,80,90,85};
 for(int m=0;m<6;m++)for(int stage=0;stage<=12;stage++)for(int field=0;field<2;field++){
  BattleContext c=fixture();c.trainerAIData.battlerIdTarget=1;
  vars[1][BMON_DATA_ATK]=407;vars[0][BMON_DATA_DEF]=211;vars[1][BMON_DATA_SPDEF]=503;
  vars[1][BMON_DATA_STAT_CHANGE_DEF]=stage;vars[1][BMON_DATA_TYPE_2]=TYPE_ICE;
  c.fieldCondition=field?FIELD_CONDITION_HAIL:0;
  int before=rngCalls;u8 ivs[6]={0};
  int actual=CalcMoveDamage(NULL,&c,ids[m],0,c.fieldCondition,0,0,0,1,1);
  int defense=101;
  if(m<4)defense=stage>=6?defense*(stage-4)/2:defense*2/(8-stage);
#if QOL_MODERN_BATTLE
  if(field)defense=defense*3/2;
#endif
  int offense=m==2?407:m==3?211:1000;
  assert(actual==oracle(offense,defense,powers[m]));
  assert(TrainerAI_CalcDamage(NULL,&c,ids[m],0,ivs,0,ABILITY_NONE,0,100)==actual);
  assert(before==rngCalls);
  // Explicit power/type alter power/weather while preserving selected stats.
  int supplied=CalcMoveDamage(NULL,&c,ids[m],0,FIELD_CONDITION_RAIN,40,TYPE_FIRE,0,1,1);
  defense=101;if(m<4)defense=stage>=6?defense*(stage-4)/2:defense*2/(8-stage);
  assert(supplied==(oracle(offense,defense,40)-2)/2+2);
 }
#endif
 return 0;}
"""
        self.variants(source)

    def test_real_hp_controller_records_category_and_respects_substitute(self):
        self.variants(sturdy.damage_source()+r"""
int main(void){
#if QOL_MODERN_MOVES
 const int ids[]={476,543,495,779,536,666};
 for(int i=0;i<6;i++)for(int substitute=0;substitute<2;substitute++){
  BattleContext c=fixture(100,-25);c.moveNoCur=ids[i];c.battleMons[1].ability=ABILITY_NONE;
  if(substitute){c.battleMons[1].status2=STATUS2_SUBSTITUTE;c.battleMons[1].moveEffectData.substituteHp=50;}
  BattleControllerPlayer_HpCalc(NULL,&c);
  if(substitute){assert(c.battleMons[1].moveEffectData.substituteHp==25);assert(!c.selfTurnData[1].specialDamage&&!c.selfTurnData[1].physicalDamage);}
  else if(i<2){assert(c.selfTurnData[1].specialDamage==-25&&!c.selfTurnData[1].physicalDamage);assert(c.turnData[1].specialDamage[0]==-25);}
  else{assert(c.selfTurnData[1].physicalDamage==-25&&!c.selfTurnData[1].specialDamage);}
 }
#endif
 return 0;}
""")


    def test_real_ai_score_admits_effect_zero_nonzero_power_without_exceptions(self):
        source=moves.ModernMoveTests().source()+r"""
#include "constants/battle.h"
#include "constants/battle/trainer_ai.h"
typedef int BattleSystem;typedef int s32;
typedef struct {
 struct {int moves[4],item;struct {int embargoFlag;} moveEffectData;} battleMons[4];
 struct {MoveTbl moveData[NUM_MOVES+1];int move,battlerIdAttacker,moveSlot,calcTemp;} trainerAIData;
} BattleContext;
static int admitted;
static void AIScript_IncrementCursor(BattleContext *c,int n){}
static int AIScript_Read(BattleContext *c){return 0;}
static int GetBattlerVar(BattleContext *c,int b,int f,void *p){return 0;}
static int GetBattlerAbility(BattleContext *c,int b){return 0;}
static void TrainerAI_CalcAllDamage(BattleSystem *s,BattleContext *c,int b,int *moves,int *damages,int item,u8 *ivs,int ability,int embargo,int variance){
 admitted++;damages[0]=10;for(int i=1;i<4;i++)damages[i]=0;
}
"""
        assembly=(ROOT/'asm/trainer_ai_data.s').read_text()
        for name in ('sNoDamageCalcMoveEffects','sAltPowerMoveEffects'):
            block=assembly.split(name+':',1)[1].split('.public',1)[0]
            data=bytes(int(h,16) for line in block.splitlines() if '.byte' in line for h in re.findall(r'0x([0-9A-Fa-f]{2})',line))
            values=struct.unpack('<'+'H'*(len(data)//2),data)
            source+='static const u16 '+name+'[]={'+','.join(map(str,values))+'};\n'
        source+=snow.native('AICmd_FlagMoveDamageScore','src/battle/trainer_ai.c')+r"""
int main(void){
#if QOL_MODERN_MOVES
 const int ids[]={476,543,495,779,536,666};
 for(int i=0;i<6;i++){
  BattleContext c={0};c.trainerAIData.move=ids[i];int before=admitted;
  AICmd_FlagMoveDamageScore(NULL,&c);assert(admitted==before+1);
  assert(c.trainerAIData.calcTemp==AI_MOVE_IS_HIGHEST_DAMAGE);
 }
#endif
 return 0;}
"""
        self.variants(source)

    def test_offensive_stage_rounding_is_modern_only_with_legacy_baseline(self):
        self.variants(damage_source()+r"""
int main(void){
#if QOL_MODERN_MOVES
 // Stage-first101 ->151 ->302; native modifier-first101 ->202 ->303.
 const int ids[]={495,779};
 for(int i=0;i<2;i++){
  BattleContext c=fixture();c.battleMons[0].ability=ABILITY_HUGE_POWER;
  vars[1][BMON_DATA_ATK]=vars[0][BMON_DATA_DEF]=101;
  vars[1][BMON_DATA_STAT_CHANGE_ATK]=vars[0][BMON_DATA_STAT_CHANGE_DEF]=7;
  vars[1][BMON_DATA_DEF]=100;
  assert(calc(&c,ids[i],0,1,0)==(QOL_MODERN_BATTLE?134:135));
 }
 // Psyshock's offense still uses the user's Sp. Atk and Sp. Atk stage.
 BattleContext c=fixture();vars[0][BMON_DATA_SPATK]=211;
 vars[0][BMON_DATA_STAT_CHANGE_SPATK]=8;vars[0][BMON_DATA_STAT_CHANGE_ATK]=0;
 assert(calc(&c,476,0,1,0)==oracle(422,101));
 vars[0][BMON_DATA_LEVEL]=10;vars[1][BMON_DATA_LEVEL]=99;
 vars[1][BMON_DATA_ATK]=407;
 assert(calc(&c,495,0,1,0)==407*100*6/101/50+2);
#endif
 return 0;}
""")


    def test_special_category_items_and_user_offensive_ability_suppression(self):
        source=damage_source().replace('return f==ITEM_VAR_HOLD_EFFECT?item:0;','return f==ITEM_VAR_HOLD_EFFECT?item:20;')
        self.variants(source+r"""
int main(void){
#if QOL_MODERN_MOVES
 BattleContext c=fixture();items[0]=HOLD_EFFECT_POWER_UP_SPEC;
 // Synthetic native modifier20 stays legacy120; modern Wise Glasses is
 // pinned4505/4096, so its category BP is110 regardless of that old parameter.
 assert(calc(&c,476,0,1,0)==1000*(QOL_MODERN_BATTLE?110:120)*22/101/50+2);
 items[0]=HOLD_EFFECT_POWER_UP_PHYS;
 assert(calc(&c,476,0,1,0)==oracle(1000,101));
 items[0]=HOLD_EFFECT_CHOICE_SPATK;
 assert(calc(&c,543,0,1,0)==oracle(1500,101));
 const int ids[]={495,779};for(int i=0;i<2;i++)for(int suppressed=0;suppressed<2;suppressed++){
  c=fixture();vars[1][BMON_DATA_ATK]=407;vars[0][BMON_DATA_DEF]=211;
  c.battleMons[0].ability=ABILITY_HUGE_POWER;
  c.battleMons[0].moveEffectFlags=suppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int raw=i?211:407;
  assert(calc(&c,ids[i],0,1,0)==oracle(raw*(suppressed?1:2),101));
 }
#endif
 return 0;}
""")

if __name__=='__main__':unittest.main()
