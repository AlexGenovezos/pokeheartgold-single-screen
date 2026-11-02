"""D1a/D1b execute production damage/AI with separate modern/legacy oracles."""
import unittest

import test_modern_selected_stats as selected
import test_modern_snow as snow
import test_modern_moves as moves


def damage_source():
    source = selected.damage_source()
    # Count the real query without replacing its suppression/Mold Breaker logic.
    source = source.replace('BOOL CheckBattlerAbilityIfNotIgnored(',
                            'BOOL realAbilityQuery(', 1)
    boundary = source.index(snow.native('CheckAbilityActive').strip())
    source = source[:boundary] + r'''
static int unawareQueries;
static BOOL CheckBattlerAbilityIfNotIgnored(BattleContext *c,int a,int d,int ability){
 if(ability==ABILITY_UNAWARE)unawareQueries++;
 return realAbilityQuery(c,a,d,ability);
}
''' + source[boundary:]
    return source + r'''
static int staged(int raw,int stage){return stage>=6?raw*(stage-4)/2:raw*2/(8-stage);}
static int filtered(int stage,int crit,int unaware){return unaware||(crit>1&&stage<6)?6:stage;}
static void offenseFixture(BattleContext *c,int move,int stage){
 *c=fixture();vars[0][BMON_DATA_ATK]=vars[0][BMON_DATA_SPATK]=101;
 vars[0][BMON_DATA_DEF]=101;vars[1][BMON_DATA_ATK]=101;
 vars[1][BMON_DATA_DEF]=vars[1][BMON_DATA_SPDEF]=100;
 vars[0][BMON_DATA_STAT_CHANGE_ATK]=vars[0][BMON_DATA_STAT_CHANGE_SPATK]=stage;
 vars[0][BMON_DATA_STAT_CHANGE_DEF]=vars[1][BMON_DATA_STAT_CHANGE_ATK]=stage;
 c->trainerAIData.moveData[move]=(Move){100,TYPE_NORMAL,move==MOVE_SWIFT?CATEGORY_SPECIAL:CATEGORY_PHYSICAL,0,0};
}
static int run(BattleContext *c,int move,int field,int crit){
 int before=rngCalls,queries=unawareQueries,raw[4][256];memcpy(raw,vars,sizeof(raw));
 Mon mons[4];memcpy(mons,c->battleMons,sizeof(mons));
 int result=CalcMoveDamage(NULL,c,move,0,field,100,0,0,1,crit);
 assert(rngCalls==before&&unawareQueries==queries+1);
 assert(!memcmp(raw,vars,sizeof(raw))&&!memcmp(mons,c->battleMons,sizeof(mons)));
 return result;
}
'''


def ai_source():
    # Fixture writes include extended IDs; the real accessor still selects the
    # production extended table, but fixture setup must remain in bounds.
    source = snow.damage_source().replace('moveData[NUM_MOVES+1]', 'moveData[900]')
    source = source.replace(snow.native('Qol_IsSlicingMove','src/qol_moves.c'), '')
    definitions = '\n#undef BATTLE_MOVE_DATA\n#undef Qol_IsSupportedMove\n' + ''.join(
        moves.no_includes((selected.ROOT / p).read_text()) for p in
        ('include/move.h', 'include/qol_moves.h', 'src/qol_moves.c')) + '\ntypedef MoveTbl Move;'
    source = source.replace('typedef struct {int power,type,category,effect,range;} Move;', definitions)
    source = source.replace('(Move){500,TYPE_NORMAL,CATEGORY_PHYSICAL,0,0}',
                            '(Move){.power=100,.type=TYPE_NORMAL,.category=CATEGORY_PHYSICAL}')
    source = source.replace('int hp,ability,status,item,statChanges[8];',
                            'int hp,ability,status,item,statChanges[8],level,friendship,weight;')
    source = source.replace('int calcTemp;} trainerAIData;', 'int calcTemp,battlerIdTarget;} trainerAIData;')
    source = source.replace('int powerMultiplier,fieldCondition;',
                            'int powerMultiplier,fieldCondition,effectiveSpeed[4];unsigned fieldSideConditionFlags[2];')
    return source + r'''
#define MOVE_STATUS_IMMUNE (MOVE_STATUS_NO_EFFECT|MOVE_STATUS_LEVITATE_IMMUNE|MOVE_STATUS_WONDER_GUARD_IMMUNE|MOVE_STATUS_MAGNET_RISE_IMMUNE)
static const u16 sWeightToPower[][2]={{0xFFFF,0xFFFF}};
enum {WEIGHT_TO_POWER_WEIGHT,WEIGHT_TO_POWER_POWER};
static int TrainerAI_MoveType(BattleSystem *s,BattleContext *c,int b,int move){return TYPE_NORMAL;}
// Neutral chart/no STAB isolates D1a; broader AI/type/variance ordering is deferred.
static int BattleSystem_ApplyTypeEffectiveness(BattleSystem *s,BattleContext *c,int m,int type,int a,int d,int damage,u32 *flags){return damage;}
''' + snow.native('DamageDivide') + snow.native('TrainerAI_CalcDamage', 'src/battle/trainer_ai.c')


class OffensiveStageOrderTests(unittest.TestCase):
    compile_run = selected.SelectedStatTests.compile_run
    variants = selected.SelectedStatTests.variants

    def test_literal_full_formula_134_modern_135_legacy_and_user_source_ownership(self):
        self.variants(damage_source() + r'''
int main(void){
 const int ids[]={MOVE_TACKLE,MOVE_FOUL_PLAY,MOVE_BODY_PRESS,MOVE_SWIFT};
 for(int m=0;m<4;m++)for(int power=0;power<2;power++){
  BattleContext c;offenseFixture(&c,ids[m],7);
  c.battleMons[0].ability=power?ABILITY_PURE_POWER:ABILITY_HUGE_POWER;
  if(m==3){c.battleMons[0].ability=ABILITY_NONE;vars[0][BMON_DATA_SPECIES]=SPECIES_CLAMPERL;items[0]=HOLD_EFFECT_CLAMPERL_SPATK;}
  assert(run(&c,ids[m],0,1)==(QOL_MODERN_BATTLE?134:135));
 }
 return 0;}
''')

    def test_every_stage_crit_and_physical_ability_item_group_or_legacy_sequence(self):
        self.variants(damage_source() + r'''
int main(void){
 const int ids[]={MOVE_TACKLE,MOVE_FOUL_PLAY,MOVE_BODY_PRESS};
 const int abilities[]={ABILITY_NONE,ABILITY_HUGE_POWER,ABILITY_PURE_POWER,ABILITY_HUSTLE,ABILITY_GUTS,ABILITY_SLOW_START};
 for(int m=0;m<3;m++)for(int stage=0;stage<=12;stage++)for(int crit=1;crit<=3;crit++)
 for(int a=0;a<6;a++)for(int item=0;item<3;item++)for(int suppressed=0;suppressed<2;suppressed++){
  BattleContext c;offenseFixture(&c,ids[m],stage);
  c.battleMons[0].ability=abilities[a];c.battleMons[0].moveEffectFlags=suppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  vars[0][BMON_DATA_STATUS]=a==4?STATUS_POISON:0;vars[0][BMON_DATA_SLOW_START_TURN_NUMBER]=8;
  items[0]=item==1?HOLD_EFFECT_CHOICE_ATK:item==2?HOLD_EFFECT_CUBONE_ATK_UP:0;
  vars[0][BMON_DATA_SPECIES]=SPECIES_CUBONE;
  // Supplier ability/item/status are not offensive modifiers on Foul Play.
  c.battleMons[1].ability=ABILITY_HUGE_POWER;items[1]=HOLD_EFFECT_CHOICE_ATK;vars[1][BMON_DATA_STATUS]=STATUS_BURN;
  int chosen=filtered(stage,crit,0),offense=101;
#if QOL_MODERN_BATTLE
  offense=staged(offense,chosen);
  if(!suppressed&&a==3)offense=offense*3/2; // Hustle direct, outside group.
  int numerator=1,denominator=1;
  if(!suppressed&&(a==1||a==2))numerator*=2;
  if(!suppressed&&a==5)denominator*=2;
  if(!suppressed&&a==4){numerator*=3;denominator*=2;}
  if(item==1){numerator*=3;denominator*=2;}if(item==2)numerator*=2;
  offense=(offense*numerator+(denominator-1)/2)/denominator;
  if(!offense)offense=1;
#else
  if(!suppressed&&(a==1||a==2))offense*=2;
  if(!suppressed&&a==5)offense/=2;
  if(item==1)offense=offense*3/2;if(item==2)offense*=2;
  if(!suppressed&&(a==3||a==4))offense=offense*3/2;
  offense=staged(offense,chosen);
#endif
  assert(run(&c,ids[m],0,crit)==oracle(offense,100));
 }
 return 0;}
''')

    def test_special_stage_precedes_choice_solar_plus_minus_and_species_items(self):
        self.variants(damage_source() + r'''
int main(void){
 const int abilities[]={ABILITY_NONE,ABILITY_SOLAR_POWER,ABILITY_PLUS,ABILITY_MINUS};
 for(int stage=0;stage<=12;stage++)for(int crit=1;crit<=3;crit++)for(int a=0;a<4;a++)
 for(int item=0;item<4;item++)for(int suppressed=0;suppressed<2;suppressed++){
  BattleContext c;offenseFixture(&c,MOVE_SWIFT,stage);c.battleMons[0].ability=abilities[a];
  c.battleMons[0].moveEffectFlags=suppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[2].ability=a==2?ABILITY_MINUS:ABILITY_PLUS;
  items[0]=item==1?HOLD_EFFECT_CHOICE_SPATK:item==2?HOLD_EFFECT_CLAMPERL_SPATK:item==3?HOLD_EFFECT_LATI_SPECIAL:0;
  vars[0][BMON_DATA_SPECIES]=item==2?SPECIES_CLAMPERL:SPECIES_LATIAS;
  int chosen=filtered(stage,crit,0),offense=101;
#if QOL_MODERN_BATTLE
  offense=staged(offense,chosen);
  // D2a1 Soul Dew has no stat bonus; Normal Swift has no matching BP boost.
  int numerator=1,denominator=1;
  if(item==1){numerator*=3;denominator*=2;}if(item==2)numerator*=2;
  if(a&&!suppressed){numerator*=3;denominator*=2;}
  offense=(offense*numerator+(denominator-1)/2)/denominator;
#else
  if(item==1||item==3)offense=offense*3/2;if(item==2)offense*=2;
  if(a&&!suppressed)offense=offense*3/2;
  offense=staged(offense,chosen);
#endif
  assert(run(&c,MOVE_SWIFT,FIELD_CONDITION_SUN,crit)==oracle(offense,100));
 }
 return 0;}
''')

    def test_selected_stage_unaware_owners_mold_breaker_suppression_and_causal_query(self):
        self.variants(damage_source() + r'''
int main(void){
 const int ids[]={MOVE_TACKLE,MOVE_FOUL_PLAY,MOVE_BODY_PRESS,MOVE_SWIFT};
 const int users[]={ABILITY_NONE,ABILITY_UNAWARE,ABILITY_MOLD_BREAKER};
 for(int m=0;m<4;m++)for(int stage=0;stage<=12;stage++)for(int crit=1;crit<=3;crit++)
 for(int user=0;user<3;user++)for(int defender=0;defender<2;defender++)for(int hidden=0;hidden<4;hidden++){
  BattleContext c;offenseFixture(&c,ids[m],stage);
  // Different irrelevant user stage detects selection after Unaware filtering.
  if(QOL_MODERN_MOVES&&(m==1||m==2))vars[0][BMON_DATA_STAT_CHANGE_ATK]=0;
  c.battleMons[0].ability=users[user];c.battleMons[1].ability=defender?ABILITY_UNAWARE:ABILITY_NONE;
  c.battleMons[0].moveEffectFlags=hidden&1?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].moveEffectFlags=hidden&2?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  items[0]=m==3?HOLD_EFFECT_CHOICE_SPATK:HOLD_EFFECT_CHOICE_ATK;
  int mold=user==2&&!(hidden&1),unaware=defender&&!(hidden&2)&&!mold;
  int chosen=filtered(stage,crit,unaware),offense=101;
#if QOL_MODERN_BATTLE
  offense=staged(offense,chosen);
#endif
  offense=offense*3/2;
#if !QOL_MODERN_BATTLE
  offense=staged(offense,chosen);
#endif
  assert(run(&c,ids[m],0,crit)==oracle(offense,100));
  int causal=mold&&defender&&!(hidden&2);
  assert(c.selfTurnData[0].moldBreakerFlag==causal);
  assert(!!(c.battleStatus&BATTLE_STATUS_MOLD_BREAKER)==causal);
 }
 return 0;}
''')

    def test_simple_stored_stages_survive_suppression_and_ability_loss(self):
        self.variants(damage_source() + r'''
int main(void){
 const int ids[]={MOVE_TACKLE,MOVE_FOUL_PLAY,MOVE_BODY_PRESS,MOVE_SWIFT};
 for(int m=0;m<4;m++)for(int stage=0;stage<=12;stage++)for(int crit=1;crit<=3;crit++)for(int state=0;state<3;state++){
  BattleContext c;offenseFixture(&c,ids[m],stage);c.battleMons[0].ability=state==2?ABILITY_NONE:ABILITY_SIMPLE;
  c.battleMons[0].moveEffectFlags=state==1?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  items[0]=m==3?HOLD_EFFECT_CHOICE_SPATK:HOLD_EFFECT_CHOICE_ATK;
  int chosen=stage;
#if !QOL_MODERN_BATTLE
  if(state==0){chosen=6+(stage-6)*2;if(chosen<0)chosen=0;if(chosen>12)chosen=12;}
#endif
  chosen=filtered(chosen,crit,0);int offense=101;
#if QOL_MODERN_BATTLE
  offense=staged(offense,chosen);
#endif
  offense=offense*3/2;
#if !QOL_MODERN_BATTLE
  offense=staged(offense,chosen);
#endif
  assert(run(&c,ids[m],0,crit)==oracle(offense,100));
 }
 // Intrinsic BP counts all seven stored positive stages, even with Unaware.
#if QOL_MODERN_MOVES
 BattleContext c;offenseFixture(&c,MOVE_STORED_POWER,8);
 for(int stat=STAT_ATK;stat<=STAT_EVASION;stat++)c.battleMons[0].statChanges[stat]=8;
 c.battleMons[1].ability=ABILITY_UNAWARE;
 c.trainerAIData.moveData[MOVE_STORED_POWER]=(Move){20,TYPE_NORMAL,CATEGORY_SPECIAL,0,0};
 assert(CalcMoveDamage(NULL,&c,MOVE_STORED_POWER,0,0,0,0,0,1,1)==101*300*22/100/50+2);
 for(int stat=STAT_ATK;stat<=STAT_EVASION;stat++)assert(c.battleMons[0].statChanges[stat]==8);
#endif
 return 0;}
''')

    def test_real_trainer_ai_matches_stage_first_shared_calc_without_rng(self):
        self.variants(ai_source() + r'''
static int staged(int raw,int stage){return stage>=6?raw*(stage-4)/2:raw*2/(8-stage);}
int main(void){
 const int ids[]={MOVE_TACKLE,MOVE_SWIFT,MOVE_FOUL_PLAY,MOVE_BODY_PRESS};
 for(int m=0;m<4;m++)for(int stage=0;stage<=12;stage++)for(int unaware=0;unaware<2;unaware++){
  BattleContext c=fixture();c.trainerAIData.battlerIdTarget=1;
  vars[0][BMON_DATA_ATK]=vars[0][BMON_DATA_SPATK]=vars[0][BMON_DATA_DEF]=vars[1][BMON_DATA_ATK]=101;
  vars[1][BMON_DATA_DEF]=vars[1][BMON_DATA_SPDEF]=100;
  vars[0][BMON_DATA_STAT_CHANGE_ATK]=vars[0][BMON_DATA_STAT_CHANGE_DEF]=vars[0][BMON_DATA_STAT_CHANGE_SPATK]=vars[1][BMON_DATA_STAT_CHANGE_ATK]=stage;
  c.battleMons[0].ability=ABILITY_HUGE_POWER;c.battleMons[1].ability=unaware?ABILITY_UNAWARE:ABILITY_NONE;
  if(m==1){c.battleMons[0].ability=ABILITY_NONE;items[0]=HOLD_EFFECT_CLAMPERL_SPATK;vars[0][BMON_DATA_SPECIES]=SPECIES_CLAMPERL;}
  c.trainerAIData.moveData[ids[m]]=(Move){.power=100,.type=TYPE_NORMAL,.category=m==1?CATEGORY_SPECIAL:CATEGORY_PHYSICAL};
#if !QOL_MODERN_MOVES
  if(m>1)continue; // Extended accessors intentionally reject disabled moves.
#endif
  int power=m==2?95:m==3?80:100,offense=101,chosen=unaware?6:stage;
#if QOL_MODERN_BATTLE
  offense=staged(offense,chosen);
#endif
  offense*=2;
#if !QOL_MODERN_BATTLE
  offense=staged(offense,chosen);
#endif
  int expected=offense*power*22/100/50+2,before=rngCalls;u8 ivs[6]={0};BattleContext snapshot=c;
  assert(CalcMoveDamage(NULL,&c,ids[m],0,0,0,0,0,1,1)==expected);
  assert(TrainerAI_CalcDamage(NULL,&c,ids[m],0,ivs,0,c.battleMons[0].ability,0,100)==expected);
  assert(!memcmp(&snapshot,&c,sizeof(c))&&before==rngCalls);
  if(stage==7&&!unaware&&m<2)assert(expected==(QOL_MODERN_BATTLE?134:135));
 }
 return 0;}
''')


if __name__ == '__main__':
    unittest.main()
