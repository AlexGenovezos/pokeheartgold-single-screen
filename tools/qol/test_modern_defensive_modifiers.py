"""D1c actual shared damage/AI; rational expectations independent of Q12 helpers."""
import unittest

import test_modern_damage_layers as layers
import test_modern_selected_stats as selected
import test_modern_snow as snow


ORACLE = r'''
// Stage rational, then direct weather floor, then one completed modifier group.
// All included factors have exact power-of-two denominators; ties round down.
static int stageDefense(int raw,int stage){return stage>=6?raw*(stage-4)/2:raw*2/(8-stage);}
static int roundedRatio(int raw,int n,int d){return (raw*n+(d-1)/2)/d;}
static void defenseFixture(BattleContext *c,int move,int special,int stage){
 *c=fixture();vars[0][BMON_DATA_ATK]=vars[0][BMON_DATA_SPATK]=1000;
 vars[1][BMON_DATA_DEF]=vars[1][BMON_DATA_SPDEF]=101;
 vars[1][BMON_DATA_STAT_CHANGE_DEF]=vars[1][BMON_DATA_STAT_CHANGE_SPDEF]=stage;
 c->trainerAIData.moveData[move]=(Move){100,TYPE_NORMAL,special?CATEGORY_SPECIAL:CATEGORY_PHYSICAL,0,0};
}
static void expectDefense(BattleContext *c,int move,int field,int crit,int defense){
 int before=rngCalls,raw[4][256];memcpy(raw,vars,sizeof(raw));
 Mon mons[4];memcpy(mons,c->battleMons,sizeof(mons));
 int result=CalcMoveDamage(NULL,c,move,0,field,100,0,0,1,crit);
 int expected=1000*100*22/defense/50+2;
 if(result!=expected)fprintf(stderr,"move%d field%d crit%d defense%d: expected%d got%d\n",move,field,crit,defense,expected,result);
 assert(result==expected);assert(before==rngCalls);
 assert(!memcmp(raw,vars,sizeof(raw))&&!memcmp(mons,c->battleMons,sizeof(mons)));
}
'''


class DefensiveModifierTests(unittest.TestCase):
    compile_run = selected.SelectedStatTests.compile_run
    variants = selected.SelectedStatTests.variants

    def test_literal_stage_sand_scale_native_discriminator_and_grouped_defense(self):
        self.variants(layers.damage_source()+ORACLE+r'''
int main(void){
 BattleContext c;defenseFixture(&c,MOVE_OVERHEAT,1,7);
 vars[0][BMON_DATA_SPATK]=103;vars[1][BMON_DATA_SPECIES]=SPECIES_CLAMPERL;
 vars[1][BMON_DATA_TYPE_1]=TYPE_ROCK;items[1]=HOLD_EFFECT_CLAMPERL_SPDEF;
 // Deliberate raw-stat/native fixture, not natural stats or modern Overheat BP.
 int value=CalcMoveDamage(NULL,&c,MOVE_OVERHEAT,0,FIELD_CONDITION_SANDSTORM_PERMANENT,140,0,0,1,1);
 if(value!=(QOL_MODERN_BATTLE?16:15))fprintf(stderr,"stage151 -> Sand226 -> Scale452: expected%d got%d\n",QOL_MODERN_BATTLE?16:15,value);
 assert(value==(QOL_MODERN_BATTLE?16:15)); // Neutral pre-type value: resisted native8 vs7.
 // Two 1.5 factors with no intermediate stat floor: 101*9/4 ->227, not226.
 defenseFixture(&c,MOVE_SWIFT,1,6);c.battleMons[1].ability=ABILITY_FLOWER_GIFT;
 c.battleMons[3].ability=ABILITY_FLOWER_GIFT;
 vars[1][BMON_DATA_SPECIES]=vars[3][BMON_DATA_SPECIES]=SPECIES_CHERRIM;
 expectDefense(&c,MOVE_SWIFT,FIELD_CONDITION_SUN,1,QOL_MODERN_BATTLE?227:151);
 // Marvel Scale and Metal Powder group: 101*3 ->303, not151*2=302.
 defenseFixture(&c,MOVE_TACKLE,0,6);vars[1][BMON_DATA_SPECIES]=SPECIES_DITTO;
 items[1]=HOLD_EFFECT_DITTO_DEF_UP;c.battleMons[1].ability=ABILITY_MARVEL_SCALE;
 vars[1][BMON_DATA_STATUS]=STATUS_POISON;
 expectDefense(&c,MOVE_TACKLE,0,1,QOL_MODERN_BATTLE?303:302);
 return 0;}
''')

    def test_literal_snow_marvel_powder_native_discriminator(self):
        self.variants(layers.damage_source()+ORACLE+r'''
int main(void){
 BattleContext c;defenseFixture(&c,MOVE_EARTHQUAKE,0,6);
 vars[0][BMON_DATA_ATK]=113;vars[1][BMON_DATA_SPECIES]=SPECIES_DITTO;
 vars[1][BMON_DATA_TYPE_1]=TYPE_ICE;items[1]=HOLD_EFFECT_DITTO_DEF_UP;
 c.battleMons[1].ability=ABILITY_MARVEL_SCALE;vars[1][BMON_DATA_STATUS]=STATUS_PARALYSIS;
 // Direct Snow151 -> group3 gives453. Legacy Snow151 -> Marvel226 -> Powder452.
 int actual=CalcMoveDamage(NULL,&c,MOVE_EARTHQUAKE,0,FIELD_CONDITION_HAIL_PERMANENT,100,0,0,1,1);
 assert(actual==(QOL_MODERN_BATTLE?12:18)); // Battle-off has no Snow: defense302.
 return 0;}
''')

    def test_flower_scale_group_caller_weather_suppression_and_transformed_provider(self):
        self.variants(layers.damage_source()+ORACLE+r'''
int main(void){
 for(int weather=0;weather<3;weather++)for(int blocker=0;blocker<5;blocker++)for(int transformed=0;transformed<2;transformed++)
 for(int current=0;current<2;current++)for(int original=0;original<2;original++)for(int selfAlive=0;selfAlive<2;selfAlive++){
  BattleContext c;defenseFixture(&c,MOVE_SWIFT,1,7);c.fieldCondition=FIELD_CONDITION_SUN;
  // Base Clamperl has Scale but is never a base Cherrim self-provider.
  vars[1][BMON_DATA_SPECIES]=SPECIES_CLAMPERL;items[1]=HOLD_EFFECT_CLAMPERL_SPDEF;
  c.battleMons[1].ability=ABILITY_FLOWER_GIFT;c.battleMons[1].hp=selfAlive?100:0;
  c.battleMons[3].ability=ABILITY_FLOWER_GIFT;vars[3][BMON_DATA_SPECIES]=current?SPECIES_CHERRIM:SPECIES_DITTO;
  vars[3][BMON_DATA_STATUS2]=transformed?STATUS2_TRANSFORM:0;partySpecies[3]=original?SPECIES_CHERRIM:SPECIES_DITTO;
  c.battleMons[2].ability=blocker==1||blocker==3?ABILITY_CLOUD_NINE:blocker?ABILITY_AIR_LOCK:ABILITY_NONE;
  c.battleMons[2].moveEffectFlags=blocker>=3?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int sun=weather&&!(blocker==1||blocker==2),provider=transformed?original:current;
  int field=weather==1?FIELD_CONDITION_SUN:weather==2?FIELD_CONDITION_SUN_PERMANENT:0,d;
#if QOL_MODERN_BATTLE
  d=sun&&provider?453:302; // stage151 * Scale2 * Flower1.5, one group.
#else
  d=202;if(sun)d=d*3/2;d=stageDefense(d,7); // Native self ability ignores base species and HP.
#endif
  expectDefense(&c,MOVE_SWIFT,field,1,d);
 }
 return 0;}
''')

    def test_every_selected_stage_crit_unaware_ignore_moves_weather_and_modifier(self):
        self.variants(layers.damage_source()+ORACLE+r'''
int main(void){
 const int ids[]={MOVE_TACKLE,MOVE_SWIFT,MOVE_PSYSHOCK,MOVE_PSYSTRIKE,MOVE_SACRED_SWORD,MOVE_DARKEST_LARIAT};
 for(int m=0;m<6;m++)for(int stage=0;stage<=12;stage++)for(int crit=1;crit<=3;crit++)
 for(int user=0;user<3;user++)for(int hidden=0;hidden<2;hidden++)for(int weather=0;weather<3;weather++)for(int mod=0;mod<3;mod++){
  BattleContext c;defenseFixture(&c,ids[m],m>=1&&m<=3,stage);
  c.battleMons[0].ability=user==1?ABILITY_UNAWARE:user==2?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  c.battleMons[0].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int physical=!(m>=1&&m<=3)||(QOL_MODERN_MOVES&&m>=2&&m<=3);
  vars[1][physical?BMON_DATA_SPDEF:BMON_DATA_DEF]=907;
  vars[1][physical?BMON_DATA_STAT_CHANGE_SPDEF:BMON_DATA_STAT_CHANGE_DEF]=12;
  vars[1][BMON_DATA_TYPE_2]=physical?TYPE_ICE:TYPE_ROCK;
  if(mod==1){c.battleMons[1].ability=ABILITY_MARVEL_SCALE;vars[1][BMON_DATA_STATUS]=STATUS_POISON;}
  if(mod==2){items[1]=physical?HOLD_EFFECT_DITTO_DEF_UP:HOLD_EFFECT_CLAMPERL_SPDEF;vars[1][BMON_DATA_SPECIES]=physical?SPECIES_DITTO:SPECIES_CLAMPERL;}
  int ignored=(user==1&&!hidden)||(QOL_MODERN_MOVES&&m>=4),chosen=ignored||(crit>1&&stage>6)?6:stage;
  int field=weather==1?(physical?FIELD_CONDITION_HAIL:FIELD_CONDITION_SANDSTORM):weather==2?(physical?FIELD_CONDITION_HAIL_PERMANENT:FIELD_CONDITION_SANDSTORM_PERMANENT):0;
  int d=101,marvel=physical&&mod==1&&!(user==2&&!hidden);
#if QOL_MODERN_BATTLE
  d=stageDefense(d,chosen);if(weather)d=d*3/2;
  d=roundedRatio(d,marvel?3:mod==2?2:1,marvel?2:1);
#else
  if(marvel)d=d*3/2;if(mod==2)d*=2;
  if(weather&&!physical)d=d*3/2;d=stageDefense(d,chosen);
#endif
  expectDefense(&c,ids[m],field,crit,d);
 }
 return 0;}
''')

    def test_selected_only_causal_queries_status_suppression_and_simple_ability_loss(self):
        self.variants(layers.damage_source()+ORACLE+r'''
int main(void){
 const int ids[]={MOVE_TACKLE,MOVE_SWIFT,MOVE_PSYSHOCK};
 for(int m=0;m<3;m++)for(int status=0;status<2;status++)for(int hidden=0;hidden<4;hidden++){
  BattleContext c;defenseFixture(&c,ids[m],m>0,8);
  c.battleMons[0].ability=ABILITY_MOLD_BREAKER;c.battleMons[1].ability=ABILITY_MARVEL_SCALE;
  c.battleMons[0].moveEffectFlags=hidden&1?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].moveEffectFlags=hidden&2?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  vars[1][BMON_DATA_STATUS]=status?STATUS_POISON:0;
  int physical=m==0||(QOL_MODERN_MOVES&&m==2),mold=!(hidden&1),active=!(hidden&2);
  int d=202;if(physical&&status&&active&&!mold)d=d*3/2;
  expectDefense(&c,ids[m],0,1,d);
  int causal=mold&&active;
#if QOL_MODERN_BATTLE
  causal=causal&&physical&&status;
#endif
  assert(!!c.selfTurnData[0].moldBreakerFlag==causal);
  assert(!!(c.battleStatus&BATTLE_STATUS_MOLD_BREAKER)==causal);
 }
 for(int special=0;special<2;special++)for(int stage=0;stage<=12;stage++)for(int state=0;state<3;state++)for(int crit=1;crit<=3;crit++){
  BattleContext c;defenseFixture(&c,MOVE_TACKLE,special,stage);
  c.battleMons[1].ability=state==2?ABILITY_NONE:ABILITY_SIMPLE;
  c.battleMons[1].moveEffectFlags=state==1?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int chosen=stage;
#if !QOL_MODERN_BATTLE
  if(state==0){chosen=6+(chosen-6)*2;if(chosen<0)chosen=0;if(chosen>12)chosen=12;}
#endif
  if(crit>1&&chosen>6)chosen=6;
  expectDefense(&c,MOVE_TACKLE,0,crit,stageDefense(101,chosen));
 }
 return 0;}
''')

    def test_weather_current_types_caller_flags_active_hp_and_suppression(self):
        self.variants(layers.damage_source()+ORACLE+r'''
int main(void){
 for(int special=0;special<2;special++)for(int slot=0;slot<3;slot++)for(int field=0;field<4;field++)
 for(int blocker=0;blocker<3;blocker++)for(int alive=0;alive<2;alive++)for(int hidden=0;hidden<2;hidden++){
  BattleContext c;defenseFixture(&c,MOVE_TACKLE,special,7);
  c.fieldCondition=FIELD_CONDITION_HAIL_ALL|FIELD_CONDITION_SANDSTORM_ALL;
  vars[1][BMON_DATA_TYPE_1]=slot==1?(special?TYPE_ROCK:TYPE_ICE):TYPE_NORMAL;
  vars[1][BMON_DATA_TYPE_2]=slot==2?(special?TYPE_ROCK:TYPE_ICE):TYPE_NORMAL;
  c.battleMons[2].hp=alive;c.battleMons[2].ability=blocker==1?ABILITY_CLOUD_NINE:blocker==2?ABILITY_AIR_LOCK:ABILITY_NONE;
  c.battleMons[2].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int weather=field==1?(special?FIELD_CONDITION_SANDSTORM:FIELD_CONDITION_HAIL):field==2?(special?FIELD_CONDITION_SANDSTORM_PERMANENT:FIELD_CONDITION_HAIL_PERMANENT):field==3?(special?FIELD_CONDITION_HAIL:FIELD_CONDITION_SANDSTORM):0;
  int boost=slot&&(field==1||field==2)&&!(blocker&&alive&&!hidden),d;
#if QOL_MODERN_BATTLE
  d=boost?226:151;
#else
  d=boost&&special?226:151; // Legacy raw weather151 -> stage226.
#endif
  expectDefense(&c,MOVE_TACKLE,weather,1,d);
 }
 return 0;}
''')

    def test_actual_item_accessor_base_current_species_transform_klutz_embargo(self):
        source=layers.damage_source().replace('static int GetBattlerHeldItem(BattleContext *c,int b){return items[b];}',
                                             'static u16 GetBattlerHeldItem(BattleContext *c,int b);')
        source+=snow.native('GetBattlerHeldItem')
        self.variants(source+ORACLE+r'''
int main(void){
 const int species[]={SPECIES_CLAMPERL,SPECIES_DITTO,SPECIES_PIKACHU};
 for(int special=0;special<2;special++)for(int current=0;current<3;current++)for(int original=0;original<3;original++)
 for(int transformed=0;transformed<2;transformed++)for(int suppress=0;suppress<4;suppress++){
  BattleContext c;defenseFixture(&c,MOVE_TACKLE,special,7);
  c.battleMons[1].item=special?HOLD_EFFECT_CLAMPERL_SPDEF:HOLD_EFFECT_DITTO_DEF_UP;
  vars[1][BMON_DATA_SPECIES]=species[current];partySpecies[1]=species[original];
  vars[1][BMON_DATA_STATUS2]=transformed?STATUS2_TRANSFORM:0;
  c.battleMons[1].ability=suppress==1||suppress==3?ABILITY_KLUTZ:ABILITY_NONE;
  c.battleMons[1].moveEffectData.embargoFlag=suppress==2;
  c.battleMons[1].moveEffectFlags=suppress==3?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int eligible=suppress==0||suppress==3,d;
#if QOL_MODERN_BATTLE
  eligible=eligible&&(special?(transformed?original:current)==0:current==1&&!transformed);
  d=eligible?302:151;
#else
  eligible=eligible&&(special?current==0:current==1);d=eligible?303:151;
#endif
  expectDefense(&c,MOVE_TACKLE,0,1,d);
 }
 return 0;}
''')

    def test_flower_gift_each_live_base_provider_and_mold_breaker_causality(self):
        source=layers.damage_source().replace('static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}',
                                             'static int maxBattlers;static int BattleSystem_GetMaxBattlers(BattleSystem *s){return maxBattlers;}')
        self.variants(source+ORACLE+r'''
int main(void){
 for(int special=0;special<2;special++)for(int slots=2;slots<=4;slots+=2)for(int self=0;self<2;self++)
 for(int ally=0;ally<7;ally++)for(int hidden=0;hidden<2;hidden++)for(int user=0;user<3;user++)for(int sun=0;sun<2;sun++){
  BattleContext c;defenseFixture(&c,MOVE_TACKLE,special,6);maxBattlers=slots;
  c.battleMons[0].ability=user?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  c.battleMons[0].moveEffectFlags=user==2?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].ability=self?ABILITY_FLOWER_GIFT:ABILITY_NONE;vars[1][BMON_DATA_SPECIES]=SPECIES_CHERRIM;
  c.battleMons[1].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[3].ability=ally?ABILITY_FLOWER_GIFT:ABILITY_NONE;c.battleMons[3].hp=ally==2?0:100;
  c.battleMons[3].moveEffectFlags=ally==3?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  vars[3][BMON_DATA_SPECIES]=ally==4?SPECIES_PIKACHU:SPECIES_CHERRIM;
  vars[3][BMON_DATA_STATUS2]=ally>=5?STATUS2_TRANSFORM:0;partySpecies[3]=ally==6?SPECIES_CHERRIM:SPECIES_DITTO;
  // Enemy provider never protects defender (offensive Attack is irrelevant here).
  c.battleMons[2].ability=special?ABILITY_FLOWER_GIFT:ABILITY_NONE;vars[2][BMON_DATA_SPECIES]=SPECIES_CHERRIM;
  int providers=self&&!hidden;providers+=slots==4&&(ally==1||ally==6);
  int mold=user==1,d=101,causal=0;
#if QOL_MODERN_BATTLE
  if(special&&sun){causal=mold&&providers;int n=1,den=1;if(!mold)for(int i=0;i<providers;i++){n*=3;den*=2;}d=roundedRatio(d,n,den);}
#else
  if(special&&sun&&!mold&&((self&&!hidden)||(slots==4&&ally&&ally!=2&&ally!=3)))d=d*3/2;
#endif
  expectDefense(&c,MOVE_TACKLE,sun?FIELD_CONDITION_SUN:0,1,d);
  assert(!!c.selfTurnData[0].moldBreakerFlag==!!causal);
 }
 return 0;}
''')

    def test_explosion_minimum_and_atomic_soul_dew_defense_removal(self):
        source=layers.damage_source().replace('static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}',
                                             'static int battleType;static int BattleSystem_GetBattleType(BattleSystem *s){return battleType;}')
        self.variants(source+ORACLE+r'''
int main(void){
 const int ids[]={MOVE_EXPLOSION,MOVE_SELFDESTRUCT};
 for(int m=0;m<2;m++){
  BattleContext c;defenseFixture(&c,ids[m],0,6);c.trainerAIData.moveData[ids[m]].effect=MOVE_EFFECT_HALVE_DEFENSE;
  expectDefense(&c,ids[m],0,1,QOL_MODERN_BATTLE?101:50);
 }
 for(int stage=0;stage<=12;stage++)for(int frontier=0;frontier<2;frontier++)for(int current=0;current<3;current++)for(int crit=1;crit<=3;crit++){
  BattleContext c;defenseFixture(&c,MOVE_SWIFT,1,stage);battleType=frontier?BATTLE_TYPE_FRONTIER:0;
  vars[1][BMON_DATA_SPECIES]=current==0?SPECIES_LATIAS:current==1?SPECIES_LATIOS:SPECIES_CLAMPERL;
  vars[1][BMON_DATA_STATUS2]=STATUS2_TRANSFORM;partySpecies[1]=SPECIES_PIKACHU; // legacy uses current species; modern has no defensive Soul Dew
  items[1]=HOLD_EFFECT_LATI_SPECIAL;vars[1][BMON_DATA_TYPE_1]=TYPE_ROCK;
  int raw=!frontier&&current<2?151:101,chosen=crit>1&&stage>6?6:stage,d;
#if QOL_MODERN_BATTLE
  d=stageDefense(101,chosen)*3/2; // Soul Dew defense removed atomically with BP owner.
#else
  d=stageDefense(raw*3/2,chosen);
#endif
  expectDefense(&c,MOVE_SWIFT,FIELD_CONDITION_SANDSTORM,crit,d);
 }
#if QOL_MODERN_BATTLE
 BattleContext c;defenseFixture(&c,MOVE_TACKLE,0,0);vars[1][BMON_DATA_DEF]=1;
 expectDefense(&c,MOVE_TACKLE,0,1,1); // stage floor zero is clamped at effective-stat boundary.
 defenseFixture(&c,MOVE_TACKLE,0,6);vars[1][BMON_DATA_DEF]=1000;vars[0][BMON_DATA_ATK]=1;
 assert(CalcMoveDamage(NULL,&c,MOVE_TACKLE,0,0,1,0,0,1,1)==2); // Later formula/min damage remains unchanged.
#endif
 return 0;}
''')

    def test_real_trainer_ai_selected_defense_modifiers_all_stages_and_variances(self):
        # Neutral type wrapper deliberately isolates shared defensive arithmetic;
        # final AI variance/type reordering and candidate projection remain later work.
        self.variants(layers.ai_source()+r'''
static int stageDefense(int raw,int stage){return stage>=6?raw*(stage-4)/2:raw*2/(8-stage);}
int main(void){
 const int ids[]={MOVE_TACKLE,MOVE_SWIFT,MOVE_PSYSHOCK,MOVE_PSYSTRIKE,MOVE_SACRED_SWORD,MOVE_DARKEST_LARIAT};
 for(int m=0;m<6;m++)for(int stage=0;stage<=12;stage++)for(int mod=0;mod<4;mod++)for(int variance=85;variance<=100;variance++){
#if !QOL_MODERN_MOVES
  if(m>=2)continue;
#endif
  BattleContext c=fixture();c.trainerAIData.battlerIdTarget=1;
  int special=m>=1&&m<=3,physical=!special||(QOL_MODERN_MOVES&&m>=2),power=m==2?80:m==3?100:m==4?90:m==5?85:100;
  c.trainerAIData.moveData[ids[m]]=(Move){.power=100,.type=TYPE_NORMAL,.category=special?CATEGORY_SPECIAL:CATEGORY_PHYSICAL};
  vars[1][BMON_DATA_STAT_CHANGE_DEF]=vars[1][BMON_DATA_STAT_CHANGE_SPDEF]=stage;
  vars[1][BMON_DATA_TYPE_1]=physical?TYPE_ICE:TYPE_ROCK;
  c.fieldCondition=physical?FIELD_CONDITION_HAIL:FIELD_CONDITION_SANDSTORM;
  if(mod==1){c.battleMons[1].ability=ABILITY_MARVEL_SCALE;vars[1][BMON_DATA_STATUS]=STATUS_POISON;}
  if(mod==2){items[1]=physical?HOLD_EFFECT_DITTO_DEF_UP:HOLD_EFFECT_CLAMPERL_SPDEF;vars[1][BMON_DATA_SPECIES]=physical?SPECIES_DITTO:SPECIES_CLAMPERL;}
  if(mod==3)c.battleMons[0].ability=ABILITY_UNAWARE;
  int chosen=mod==3||(QOL_MODERN_MOVES&&m>=4)?6:stage,d=101;
#if QOL_MODERN_BATTLE
  d=stageDefense(d,chosen)*3/2;if(mod==1&&physical)d=d*3/2;if(mod==2)d*=2;
#else
  if(mod==1&&physical)d=d*3/2;if(mod==2)d*=2;if(!physical)d=d*3/2;d=stageDefense(d,chosen);
#endif
  int base=1000*power*22/d/50+2,expected=base*variance/100;if(!expected)expected=1;
  int before=rngCalls;u8 ivs[6]={0};BattleContext snapshot=c;int raw[4][256];memcpy(raw,vars,sizeof(raw));
  int actual=TrainerAI_CalcDamage(NULL,&c,ids[m],0,ivs,0,c.battleMons[0].ability,0,variance);
  if(actual!=expected)fprintf(stderr,"AI m%d stage%d mod%d var%d defense%d expected%d got%d\n",m,stage,mod,variance,d,expected,actual);
  assert(actual==expected);assert(before==rngCalls&&!memcmp(&snapshot,&c,sizeof(c))&&!memcmp(raw,vars,sizeof(raw)));
 }
 return 0;}
''')


if __name__ == '__main__':
    unittest.main()
