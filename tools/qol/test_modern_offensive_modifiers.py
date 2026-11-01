"""D1b real CalcMoveDamage/TrainerAI fixtures, independent rational oracles."""
import unittest

import test_modern_damage_layers as layers
import test_modern_selected_stats as selected
import test_modern_snow as snow


class OffensiveModifierTests(unittest.TestCase):
    compile_run = selected.SelectedStatTests.compile_run
    variants = selected.SelectedStatTests.variants

    def test_literal_q12_half_up_chain_half_down_apply_and_wide_product(self):
        self.variants(layers.damage_source()+r'''
int main(void){
#if QOL_MODERN_BATTLE
 assert(Qol_ChainOffenseModifier(4097,2048)==2049); // 2048.5 ->2049
 assert(Qol_ApplyOffenseModifier(4097,2048)==2048); // 2048.5 ->2048
 assert(Qol_ApplyOffenseModifier(3,6144)==4);       // 4.5 ->4
 assert(Qol_ApplyOffenseModifier(1,6143)==1);
 assert(Qol_ApplyOffenseModifier(1,6145)==2);
 assert(Qol_ChainOffenseModifier(6144,6144)==9216);
 // Pure-helper arithmetic probe only; synthetic native wrap parity is excluded.
 assert(Qol_ApplyOffenseModifier(100000,49152)==1200000);
#endif
 return 0;}
''')

    def test_literal_grouped_one_point_and_relocated_flash_fire(self):
        self.variants(layers.damage_source() + r'''
int main(void){
 BattleContext c;offenseFixture(&c,MOVE_TACKLE,7);
 c.battleMons[0].ability=ABILITY_GUTS;vars[0][BMON_DATA_STATUS]=STATUS_POISON;
 items[0]=HOLD_EFFECT_CHOICE_ATK;vars[1][BMON_DATA_DEF]=99;
 int result=run(&c,MOVE_TACKLE,0,1);
 if(result!=(QOL_MODERN_BATTLE?153:152))fprintf(stderr,"Guts/Band: expected%d got%d\n",QOL_MODERN_BATTLE?153:152,result);
 assert(result==(QOL_MODERN_BATTLE?153:152));
 c=fixture();vars[0][BMON_DATA_ATK]=101;vars[1][BMON_DATA_DEF]=100;
 c.battleMons[0].ability=ABILITY_FLASH_FIRE;vars[0][BMON_DATA_FLASH_FIRE]=1;
 c.trainerAIData.moveData[MOVE_EMBER]=(Move){80,TYPE_FIRE,CATEGORY_PHYSICAL,0,0};
 assert(CalcMoveDamage(NULL,&c,MOVE_EMBER,0,0,80,0,0,1,1)==(QOL_MODERN_BATTLE?55:54));
 return 0;}
''')

    def test_relocated_type_abilities_items_reductions_sources_and_suppression(self):
        self.variants(layers.damage_source() + r'''
int main(void){
 const int abilities[]={ABILITY_NONE,ABILITY_OVERGROW,ABILITY_BLAZE,ABILITY_TORRENT,ABILITY_SWARM,ABILITY_FLASH_FIRE};
 const int types[]={TYPE_NORMAL,TYPE_GRASS,TYPE_FIRE,TYPE_WATER,TYPE_BUG,TYPE_ICE};
 const int reductions[]={ABILITY_NONE,ABILITY_THICK_FAT,ABILITY_HEATPROOF};
 const int ids[]={MOVE_TACKLE,MOVE_FOUL_PLAY,MOVE_BODY_PRESS,MOVE_PSYSHOCK};
 for(int m=0;m<4;m++)for(int a=0;a<6;a++)for(int t=0;t<6;t++)for(int r=0;r<3;r++)
 for(int item=0;item<3;item++)for(int hidden=0;hidden<4;hidden++)for(int hp=0;hp<2;hp++){
  BattleContext c;offenseFixture(&c,ids[m],6);
  c.trainerAIData.moveData[ids[m]].type=types[t];
  c.trainerAIData.moveData[ids[m]].category=m==3?CATEGORY_SPECIAL:CATEGORY_PHYSICAL;
  c.battleMons[0].ability=abilities[a];c.battleMons[1].ability=reductions[r];
  c.battleMons[0].moveEffectFlags=hidden&1?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].moveEffectFlags=hidden&2?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  vars[0][BMON_DATA_HP]=hp?34:33;vars[0][BMON_DATA_FLASH_FIRE]=1;
  vars[0][BMON_DATA_SPECIES]=SPECIES_PIKACHU;
  vars[0][BMON_DATA_ATK]=vars[0][BMON_DATA_SPATK]=103;
  vars[1][BMON_DATA_ATK]=107;vars[0][BMON_DATA_DEF]=109;
  // Target's ability/item/status never becomes the user's offensive boost.
  items[1]=HOLD_EFFECT_CHOICE_ATK;vars[1][BMON_DATA_STATUS]=STATUS_POISON;
  items[0]=item==1?(m==3?HOLD_EFFECT_CHOICE_SPATK:HOLD_EFFECT_CHOICE_ATK):item==2?HOLD_EFFECT_PIKA_SPATK_UP:0;
  int raw=QOL_MODERN_MOVES&&m==1?107:QOL_MODERN_MOVES&&m==2?109:103;
  int boost=!(hidden&1)&&((a>=1&&a<=4&&!hp&&types[t]==types[a])||(a==5&&types[t]==TYPE_FIRE));
  int reduced=!(hidden&2)&&((r==1&&(types[t]==TYPE_FIRE||types[t]==TYPE_ICE))||(r==2&&types[t]==TYPE_FIRE));
  int offense=raw,power=100;
#if QOL_MODERN_BATTLE
  int numerator=(boost?3:2)*(reduced?1:2)*(item==1?3:item==2?4:2);
  // All factors are exact halves: round the single rational product, ties down.
  offense=(raw*numerator+3)/8;
#else
  if(item==1)offense=offense*3/2;if(item==2)power*=2;
  if(r==1&&reduced)power/=2;
  if(boost&&a!=5)power=power*3/2;
  if(r==2&&reduced)power/=2;
#endif
  int expected=offense*power*22/100/50;
#if !QOL_MODERN_BATTLE
  if(types[t]==TYPE_FIRE)expected=expected*3/2; // Legacy flag-only boost, any ability, even suppressed.
#endif
  int actual=run(&c,ids[m],0,1);
  if(actual!=expected+2)fprintf(stderr,"source%d ability%d type%d reduction%d item%d hidden%d hp%d: expected%d got%d\n",m,a,t,r,item,hidden,hp,expected+2,actual);
  assert(actual==expected+2);
 }
 return 0;}
''')

    def test_target_reductions_mold_breaker_preserves_user_owned_boosts(self):
        self.variants(layers.damage_source() + r'''
int main(void){
 const int abilities[]={ABILITY_MOLD_BREAKER,ABILITY_GUTS,ABILITY_HUGE_POWER};
 for(int a=0;a<3;a++)for(int r=0;r<2;r++)for(int hidden=0;hidden<4;hidden++)for(int special=0;special<2;special++){
  BattleContext c;offenseFixture(&c,MOVE_TACKLE,6);
  c.trainerAIData.moveData[MOVE_TACKLE].type=TYPE_FIRE;
  c.trainerAIData.moveData[MOVE_TACKLE].category=special?CATEGORY_SPECIAL:CATEGORY_PHYSICAL;
  c.battleMons[0].ability=abilities[a];c.battleMons[1].ability=r?ABILITY_HEATPROOF:ABILITY_THICK_FAT;
  vars[0][BMON_DATA_STATUS]=STATUS_POISON;items[0]=special?HOLD_EFFECT_CHOICE_SPATK:HOLD_EFFECT_CHOICE_ATK;
  c.battleMons[0].moveEffectFlags=hidden&1?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].moveEffectFlags=hidden&2?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int mold=a==0&&!(hidden&1),reduced=!(hidden&2)&&!mold;
  int offense=101,power=100;
#if QOL_MODERN_BATTLE
  int n=3,d=2;if(reduced)d*=2;
  if(!special&&!(hidden&1)){if(a==1){n*=3;d*=2;}if(a==2)n*=2;}
  offense=(offense*n+(d-1)/2)/d;
#else
  if(!special&&a==2&&!(hidden&1))offense*=2;
  offense=offense*3/2;
  if(!special&&a==1&&!(hidden&1))offense=offense*3/2;
  if(reduced)power/=2;
#endif
  assert(run(&c,MOVE_TACKLE,0,1)==offense*power*22/100/50+2);
  assert(c.selfTurnData[0].moldBreakerFlag==(mold&&!(hidden&2)));
 }
 return 0;}
''')

    def test_weather_flower_gift_species_live_providers_and_priority(self):
        self.variants(layers.damage_source() + r'''
int main(void){
 for(int special=0;special<2;special++)for(int a=0;a<3;a++)for(int ally=0;ally<7;ally++)
 for(int weather=0;weather<3;weather++)for(int blocker=0;blocker<5;blocker++)for(int item=0;item<2;item++){
  BattleContext c;offenseFixture(&c,MOVE_TACKLE,7);
  c.trainerAIData.moveData[MOVE_TACKLE].category=special?CATEGORY_SPECIAL:CATEGORY_PHYSICAL;
  c.battleMons[0].ability=a==1?ABILITY_FLOWER_GIFT:a==2?ABILITY_SOLAR_POWER:ABILITY_NONE;
  vars[0][BMON_DATA_SPECIES]=a==1?SPECIES_CHERRIM:SPECIES_NONE;
  c.battleMons[2].ability=ally?ABILITY_FLOWER_GIFT:ABILITY_NONE;
  vars[2][BMON_DATA_SPECIES]=ally==2?SPECIES_PIKACHU:SPECIES_CHERRIM;
  c.battleMons[2].hp=ally==3?0:100;
  c.battleMons[2].moveEffectFlags=ally==4?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  vars[2][BMON_DATA_STATUS2]=ally>=5?STATUS2_TRANSFORM:0;
  partySpecies[2]=ally==6?SPECIES_CHERRIM:SPECIES_DITTO;
  c.battleMons[3].ability=blocker==1||blocker==3?ABILITY_CLOUD_NINE:blocker?ABILITY_AIR_LOCK:ABILITY_NONE;
  c.battleMons[3].moveEffectFlags=blocker>=3?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  items[0]=item?(special?HOLD_EFFECT_CHOICE_SPATK:HOLD_EFFECT_CHOICE_ATK):0;
  c.fieldCondition=FIELD_CONDITION_SUN; // supplied weather controls, not ctx.
  int field=weather==1?FIELD_CONDITION_SUN:weather==2?FIELD_CONDITION_SUN_PERMANENT:0;
  int sun=weather&&!(blocker==1||blocker==2),offense=101;
#if QOL_MODERN_BATTLE
  offense=151;int n=1,d=1;
  if(sun&&special&&a==2){n*=3;d*=2;}
  // Flower Gift's priority3 follows ability5 and precedes item1. Each actual
  // eligible Cherrim supplies one factor, including self. Enemy never supplies.
  int providers=(a==1)+(ally==1||ally==6);
  if(sun&&!special)for(int i=0;i<providers;i++){n*=3;d*=2;}
  if(item){n*=3;d*=2;}
  offense=(offense*n+(d-1)/2)/d;
#else
  if(item)offense=offense*3/2;
  if(sun&&special&&a==2)offense=offense*3/2;
  if(sun&&!special&&(a==1||(ally&&ally!=3&&ally!=4)))offense=offense*3/2;
  offense=offense*3/2;
#endif
  assert(run(&c,MOVE_TACKLE,field,1)==oracle(offense,100));
 }
 return 0;}
''')

    def test_actual_item_accessor_species_category_transform_klutz_and_embargo(self):
        source=layers.damage_source()
        source=source.replace('static int GetBattlerHeldItem(BattleContext *c,int b){return items[b];}',
                              'static u16 GetBattlerHeldItem(BattleContext *c,int b);')
        source += snow.native('GetBattlerHeldItem')
        self.variants(source+r'''
int main(void){
 const int held[]={HOLD_EFFECT_CHOICE_ATK,HOLD_EFFECT_CHOICE_SPATK,HOLD_EFFECT_CUBONE_ATK_UP,HOLD_EFFECT_CLAMPERL_SPATK,HOLD_EFFECT_PIKA_SPATK_UP};
 const int species[]={SPECIES_CUBONE,SPECIES_MAROWAK,SPECIES_CLAMPERL,SPECIES_PIKACHU,SPECIES_DITTO};
 for(int special=0;special<2;special++)for(int item=0;item<5;item++)for(int sp=0;sp<5;sp++)
 for(int transform=0;transform<2;transform++)for(int suppress=0;suppress<4;suppress++){
  BattleContext c;offenseFixture(&c,MOVE_TACKLE,7);
  c.trainerAIData.moveData[MOVE_TACKLE].category=special?CATEGORY_SPECIAL:CATEGORY_PHYSICAL;
  c.battleMons[0].item=held[item];vars[0][BMON_DATA_SPECIES]=species[sp];
  vars[0][BMON_DATA_STATUS2]=transform?STATUS2_TRANSFORM:0;partySpecies[0]=SPECIES_PIKACHU;
  c.battleMons[0].ability=suppress==1||suppress==3?ABILITY_KLUTZ:ABILITY_NONE;
  c.battleMons[0].moveEffectData.embargoFlag=suppress==2;
  c.battleMons[0].moveEffectFlags=suppress==3?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int available=suppress==0||suppress==3,offense=101,power=100;
#if QOL_MODERN_BATTLE
  offense=151;int base=transform?SPECIES_PIKACHU:species[sp];
  if(available){
   if((item==0&&!special)||(item==1&&special))offense=offense*3/2;
   if((item==2&&!special&&(base==SPECIES_CUBONE||base==SPECIES_MAROWAK))||
      (item==3&&special&&base==SPECIES_CLAMPERL)||(item==4&&base==SPECIES_PIKACHU))offense*=2;
  }
#else
  if(available){
   if((item==0&&!special)||(item==1&&special))offense=offense*3/2;
   if(item==2&&!special&&(sp==0||sp==1))offense*=2;
   if(item==3&&special&&sp==2)offense*=2;
   if(item==4&&sp==3)power*=2;
  }
  offense=offense*3/2;
#endif
  assert(run(&c,MOVE_TACKLE,0,1)==offense*power*22/100/50+2);
 }
 return 0;}
''')

    def test_flower_gift_self_ally_active_slots_hp_suppression_and_mold_breaker(self):
        source=layers.damage_source().replace('static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}',
                                             'static int maxBattlers;static int BattleSystem_GetMaxBattlers(BattleSystem *s){return maxBattlers;}')
        self.variants(source+r'''
int main(void){
 for(int doubles=0;doubles<2;doubles++)for(int alive=0;alive<2;alive++)for(int supplier=0;supplier<3;supplier++)
 for(int suppressed=0;suppressed<2;suppressed++)for(int mold=0;mold<2;mold++){
  BattleContext c;offenseFixture(&c,MOVE_TACKLE,7);maxBattlers=doubles?4:2;
  c.battleMons[0].hp=alive?100:0;c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_FLOWER_GIFT;
  vars[0][BMON_DATA_SPECIES]=SPECIES_CHERRIM;items[0]=HOLD_EFFECT_CHOICE_ATK;
  c.battleMons[0].moveEffectFlags=suppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int provider=supplier==1?2:3;
  c.battleMons[provider].ability=supplier?ABILITY_FLOWER_GIFT:ABILITY_NONE;
  vars[provider][BMON_DATA_SPECIES]=SPECIES_CHERRIM;
  int self=alive&&!suppressed&&!mold,ally=doubles&&supplier==1;
  int offense;
#if QOL_MODERN_BATTLE
  int n=3,d=2;for(int i=0;i<self+ally;i++){n*=3;d*=2;}
  offense=(151*n+(d-1)/2)/d;
#else
  offense=151;if(self||ally)offense=offense*3/2;offense=offense*3/2;
#endif
  assert(run(&c,MOVE_TACKLE,FIELD_CONDITION_SUN,1)==oracle(offense,100));
 }
 return 0;}
''')

    def test_hp_slow_start_flash_fire_boundaries_and_minimum_stat(self):
        self.variants(layers.damage_source()+r'''
int main(void){
 for(int elapsed=4;elapsed<=6;elapsed++)for(int raw=1;raw<=103;raw+=102)for(int hidden=0;hidden<2;hidden++){
  BattleContext c;offenseFixture(&c,MOVE_TACKLE,6);vars[0][BMON_DATA_ATK]=raw;
  c.battleMons[0].ability=ABILITY_SLOW_START;
  c.battleMons[0].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  vars[0][BMON_DATA_SLOW_START_TURN_NUMBER]=10-elapsed;items[0]=HOLD_EFFECT_CHOICE_ATK;
  int offense;
#if QOL_MODERN_BATTLE
  offense=elapsed<5&&!hidden?(raw*3+1)/4:raw*3/2;if(!offense)offense=1;
#else
  offense=elapsed<5&&!hidden?raw/2:raw;offense=offense*3/2;
#endif
  if(raw==1)vars[1][BMON_DATA_DEF]=1; // Minimum1 must affect actual damage.
  assert(run(&c,MOVE_TACKLE,0,1)==oracle(offense,raw==1?1:100));
 }
 BattleContext tiny;offenseFixture(&tiny,MOVE_TACKLE,0);
 vars[0][BMON_DATA_ATK]=1;vars[1][BMON_DATA_DEF]=1;tiny.battleMons[0].ability=ABILITY_HUGE_POWER;
 assert(run(&tiny,MOVE_TACKLE,0,1)==(QOL_MODERN_BATTLE?46:2));
 for(int ability=0;ability<3;ability++)for(int flag=0;flag<2;flag++)for(int hidden=0;hidden<2;hidden++){
  BattleContext c;offenseFixture(&c,MOVE_TACKLE,6);
  c.trainerAIData.moveData[MOVE_TACKLE].type=TYPE_FIRE;
  c.battleMons[0].ability=ability==1?ABILITY_FLASH_FIRE:ability==2?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  c.battleMons[0].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  vars[0][BMON_DATA_FLASH_FIRE]=flag;
  int offense=101,expected;
#if QOL_MODERN_BATTLE
  if(flag&&ability==1&&!hidden)offense=151;
  expected=oracle(offense,100);
#else
  expected=oracle(offense,100)-2;if(flag)expected=expected*3/2;expected+=2;
#endif
  assert(run(&c,MOVE_TACKLE,0,1)==expected);
 }
 return 0;}
''')

    def test_soul_dew_retains_both_legacy_stat_effects_and_frontier_rule(self):
        source=layers.damage_source().replace('static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}',
                                             'static int battleType;static int BattleSystem_GetBattleType(BattleSystem *s){return battleType;}')
        self.variants(source+r'''
int main(void){
 for(int frontier=0;frontier<2;frontier++)for(int side=0;side<2;side++)for(int stage=0;stage<=12;stage++){
  BattleContext c;offenseFixture(&c,MOVE_SWIFT,stage);battleType=frontier?BATTLE_TYPE_FRONTIER:0;
  vars[side][BMON_DATA_SPECIES]=SPECIES_LATIAS;items[side]=HOLD_EFFECT_LATI_SPECIAL;
  int offense=101,defense=100;
#if QOL_MODERN_BATTLE
  offense=staged(offense,stage);
#endif
  if(!frontier&&!side)offense=offense*3/2;
  if(!frontier&&side)defense=defense*3/2;
#if !QOL_MODERN_BATTLE
  offense=staged(offense,stage);
#endif
  assert(run(&c,MOVE_SWIFT,0,1)==oracle(offense,defense));
 }
 return 0;}
''')

    def test_real_trainer_ai_grouped_abilities_items_and_live_flower_gift(self):
        self.variants(layers.ai_source()+r'''
int main(void){
 const int abilities[]={ABILITY_GUTS,ABILITY_HUSTLE,ABILITY_SLOW_START,ABILITY_HUGE_POWER,ABILITY_PURE_POWER,ABILITY_SOLAR_POWER,ABILITY_PLUS,ABILITY_MINUS,ABILITY_BLAZE,ABILITY_FLASH_FIRE};
 const int held[]={0,HOLD_EFFECT_CHOICE_ATK,HOLD_EFFECT_CHOICE_SPATK,HOLD_EFFECT_CUBONE_ATK_UP,HOLD_EFFECT_CLAMPERL_SPATK,HOLD_EFFECT_PIKA_SPATK_UP};
 const int ids[]={MOVE_TACKLE,MOVE_SWIFT,MOVE_FOUL_PLAY,MOVE_BODY_PRESS,MOVE_PSYSHOCK};
 for(int m=0;m<5;m++)for(int a=0;a<10;a++)for(int item=0;item<6;item++)for(int hidden=0;hidden<2;hidden++){
#if !QOL_MODERN_MOVES
  if(m>=2)continue;
#endif
  BattleContext c=fixture();c.trainerAIData.battlerIdTarget=1;c.fieldCondition=FIELD_CONDITION_SUN;
  vars[0][BMON_DATA_ATK]=vars[0][BMON_DATA_SPATK]=vars[0][BMON_DATA_DEF]=vars[1][BMON_DATA_ATK]=101;
  vars[0][BMON_DATA_STAT_CHANGE_ATK]=vars[0][BMON_DATA_STAT_CHANGE_SPATK]=vars[0][BMON_DATA_STAT_CHANGE_DEF]=vars[1][BMON_DATA_STAT_CHANGE_ATK]=7;
  vars[1][BMON_DATA_DEF]=vars[1][BMON_DATA_SPDEF]=99;
  c.battleMons[0].ability=abilities[a];c.battleMons[2].ability=ABILITY_MINUS;
  c.battleMons[0].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  vars[0][BMON_DATA_STATUS]=STATUS_POISON;vars[0][BMON_DATA_HP]=33;
  vars[0][BMON_DATA_FLASH_FIRE]=1;vars[0][BMON_DATA_SLOW_START_TURN_NUMBER]=6;
  vars[0][BMON_DATA_SPECIES]=item==3?SPECIES_CUBONE:item==4?SPECIES_CLAMPERL:SPECIES_PIKACHU;
  items[0]=held[item];
  int special=m==1||m==4,type=a>=8?TYPE_FIRE:TYPE_NORMAL;
  c.trainerAIData.moveData[ids[m]]=(Move){.power=100,.type=type,.category=special?CATEGORY_SPECIAL:CATEGORY_PHYSICAL};
  int before=rngCalls;u8 ivs[6]={0};BattleContext snapshot=c;
  int direct=CalcMoveDamage(NULL,&c,ids[m],0,c.fieldCondition,0,0,0,1,1);
  int ai=TrainerAI_CalcDamage(NULL,&c,ids[m],0,ivs,0,abilities[a],0,100);
  int power=m==2?95:m==3||m==4?80:100;
  if(m>=2)type=m==2?TYPE_DARK:m==3?TYPE_FIGHTING:TYPE_PSYCHIC;
  int offense=101,boost=!hidden;
#if QOL_MODERN_BATTLE
  offense=151;if(!special&&a==1&&boost)offense=offense*3/2;
  int n=1,d=1;
  if(boost){
   if(!special&&(a==3||a==4))n*=2;
   if(!special&&a==2)d*=2;
   if((!special&&a==0)||(special&&(a==5||a==6||a==7))||
      ((a==8||a==9)&&type==TYPE_FIRE)){n*=3;d*=2;}
  }
  if((item==1&&!special)||(item==2&&special)){n*=3;d*=2;}
  if((item==3&&!special)||(item==4&&special)||item==5)n*=2;
  offense=(offense*n+(d-1)/2)/d;
#else
  if(!special&&boost&&(a==3||a==4))offense*=2;
  if(!special&&boost&&a==2)offense/=2;
  if((item==1&&!special)||(item==2&&special))offense=offense*3/2;
  if((item==3&&!special)||(item==4&&special))offense*=2;
  if(item==5)power*=2;
  if(!special&&boost&&(a==0||a==1))offense=offense*3/2;
  if(special&&boost&&(a==5||a==6))offense=offense*3/2;
  if(boost&&a==8&&type==TYPE_FIRE)power=power*3/2;
  offense=offense*3/2;
#endif
  int expected=offense*power*22/99/50;
  if(type==TYPE_FIRE)expected=expected*3/2; // Existing sun damage placement.
#if !QOL_MODERN_BATTLE
  if(type==TYPE_FIRE)expected=expected*3/2; // Legacy flag-only Flash Fire.
#endif
  if(direct!=expected+2)fprintf(stderr,"AI source%d ability%d item%d hidden%d power%d type%d stat%d: expected%d got%d\n",m,a,item,hidden,power,type,offense,expected+2,direct);
  assert(direct==expected+2);
  assert(ai==direct&&before==rngCalls&&!memcmp(&snapshot,&c,sizeof(c)));
 }
 // A hypothetical ability argument is not a live field provider. Existing AI
 // prediction uses live context for ordinary moves; projection is separate.
 BattleContext c=fixture();c.trainerAIData.battlerIdTarget=1;c.fieldCondition=FIELD_CONDITION_SUN;
 vars[0][BMON_DATA_SPECIES]=SPECIES_CHERRIM;c.battleMons[0].ability=ABILITY_NONE;
 u8 ivs[6]={0};int base=CalcMoveDamage(NULL,&c,MOVE_TACKLE,0,c.fieldCondition,0,0,0,1,1);
 assert(TrainerAI_CalcDamage(NULL,&c,MOVE_TACKLE,0,ivs,0,ABILITY_FLOWER_GIFT,0,100)==base);
 c.battleMons[0].ability=ABILITY_FLOWER_GIFT;
 vars[0][BMON_DATA_ATK]=101;vars[0][BMON_DATA_STAT_CHANGE_ATK]=7;
 vars[1][BMON_DATA_DEF]=99;items[0]=HOLD_EFFECT_CHOICE_ATK;
 int expected=QOL_MODERN_BATTLE?153:152;
 assert(CalcMoveDamage(NULL,&c,MOVE_TACKLE,0,c.fieldCondition,100,0,0,1,1)==expected);
 assert(TrainerAI_CalcDamage(NULL,&c,MOVE_TACKLE,0,ivs,0,ABILITY_NONE,0,100)==expected);
 return 0;}
''')


if __name__ == '__main__':
    unittest.main()
