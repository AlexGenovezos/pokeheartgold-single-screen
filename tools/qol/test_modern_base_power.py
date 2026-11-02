"""D2a1: actual shared damage/AI, with literal/rational BP oracles."""
import unittest
import test_game_logic as game
import test_modern_snow as snow
import test_modern_damage_layers as layers
import test_modern_selected_stats as selected


def source(ai=False):
    s = layers.ai_source() if ai else snow.damage_source()
    s = s.replace('static int GetItemVar(BattleContext *c,int item,int f){return f==ITEM_VAR_HOLD_EFFECT?item:0;}',
                  'static int itemMod=20;static int GetItemVar(BattleContext *c,int item,int f){return f==ITEM_VAR_HOLD_EFFECT?item:itemMod;}')
    s = s.replace('static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}',
                  'static int battleType;static int BattleSystem_GetBattleType(BattleSystem *s){return battleType;}')
    s = s.replace('static int CheckMoveEffectOnField(BattleSystem *s,BattleContext *c,int effect){return 0;}',
                  'static int sports;static int CheckMoveEffectOnField(BattleSystem *s,BattleContext *c,int effect){return !!(sports&effect);}')
    return s + r'''
static void bpFixture(BattleContext *c,int move,int bp,int type,int category,int effect){
 *c=fixture();sports=battleType=0;itemMod=20;
 vars[0][BMON_DATA_ATK]=vars[0][BMON_DATA_SPATK]=5000;
 vars[1][BMON_DATA_DEF]=vars[1][BMON_DATA_SPDEF]=100;
 c->trainerAIData.moveData[move]=(Move){.power=bp,.type=type,.category=category,.effect=effect};
}
static int hit(BattleContext *c,int move,int bp,int type,int weather){
 int before=rngCalls,multi=c->powerMultiplier;BattleContext copy=*c;
 int result=CalcMoveDamage(NULL,c,move,0,weather,bp,type,0,1,1);
 assert(rngCalls==before&&multi==c->powerMultiplier&&!memcmp(&copy,c,sizeof(copy)));
 return result;
}
static int bpDamage(int bp){return bp*22+2;}
'''


class ConfirmedBasePowerTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run
    variants = selected.SelectedStatTests.variants

    def test_technician_helping_hand_items_and_native_discriminator(self):
        self.variants(source()+r'''
int main(void){
 BattleContext c;
 bpFixture(&c,MOVE_TACKLE,55,TYPE_NORMAL,CATEGORY_PHYSICAL,0);
 c.battleMons[0].ability=ABILITY_TECHNICIAN;items[0]=HOLD_EFFECT_STRENGTHEN_NORMAL;
 assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage(QOL_MODERN_BATTLE?99:98));
 c.turnData[0].helpingHandFlag=1;
 assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage(QOL_MODERN_BATTLE?149:QOL_MODERN_MOVES?147:98));
 bpFixture(&c,MOVE_TACKLE,75,TYPE_NORMAL,CATEGORY_PHYSICAL,0);c.turnData[0].helpingHandFlag=1;
 assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage(112));
 // Native discriminator: explicit intrinsic55 models item-held Acrobatics515.
 vars[0][BMON_DATA_ATK]=102;c.battleMons[0].ability=ABILITY_TECHNICIAN;
 c.turnData[0].helpingHandFlag=0;items[0]=HOLD_EFFECT_STRENGTHEN_NORMAL;
 assert(hit(&c,MOVE_TACKLE,55,0,0)==(QOL_MODERN_BATTLE?46:45));
 return 0;}
''')

    def test_atomic_soul_dew_both_stat_owners_and_frontier(self):
        self.variants(source()+r'''
int main(void){
 for(int frontier=0;frontier<2;frontier++)for(int who=0;who<4;who++)for(int type=0;type<3;type++){
  BattleContext c;bpFixture(&c,MOVE_PSYCHIC,90,type==0?TYPE_PSYCHIC:type==1?TYPE_DRAGON:TYPE_NORMAL,CATEGORY_SPECIAL,0);
  vars[0][BMON_DATA_SPATK]=99;vars[1][BMON_DATA_SPDEF]=100;
  vars[0][BMON_DATA_SPECIES]=SPECIES_LATIOS;vars[1][BMON_DATA_SPECIES]=SPECIES_LATIAS;
  items[0]=who&1?HOLD_EFFECT_LATI_SPECIAL:0;items[1]=who&2?HOLD_EFFECT_LATI_SPECIAL:0;
  battleType=frontier?BATTLE_TYPE_FRONTIER:0;
  int bp=90,a=99,d=100;
#if QOL_MODERN_BATTLE
  if((who&1)&&type<2)bp=108;
#else
  if(!frontier){if(who&1)a=148;if(who&2)d=150;}
#endif
  assert(hit(&c,MOVE_PSYCHIC,0,0,0)==22*bp*a/d/50+2);
  if(!frontier&&who==3&&type==0)assert(hit(&c,MOVE_PSYCHIC,0,0,0)==(QOL_MODERN_BATTLE?49:41));
 }
 return 0;}
''')

    def test_real_ai_consumes_confirmed_group_all_flags_and_variances(self):
        self.variants(source(ai=True)+r'''
int main(void){
 for(int roll=85;roll<=100;roll++){
  BattleContext c;bpFixture(&c,MOVE_TACKLE,55,TYPE_NORMAL,CATEGORY_PHYSICAL,0);
  c.trainerAIData.battlerIdTarget=1;c.battleMons[0].ability=ABILITY_TECHNICIAN;
  c.turnData[0].helpingHandFlag=1;items[0]=HOLD_EFFECT_STRENGTHEN_NORMAL;
  u8 ivs[6]={0};int before=rngCalls;BattleContext copy=c;
  int expected=bpDamage(QOL_MODERN_BATTLE?149:QOL_MODERN_MOVES?147:98)*roll/100;
  assert(TrainerAI_CalcDamage(NULL,&c,MOVE_TACKLE,0,ivs,0,ABILITY_TECHNICIAN,0,roll)==expected);
  assert(rngCalls==before&&!memcmp(&copy,&c,sizeof(c)));
 }
 return 0;}
''')

    def test_priority_constants_half_boundaries_zero_and_wide_products(self):
        # Literal values independently calculated from pinned integer callbacks.
        self.variants(source()+r'''
int main(void){
#if QOL_MODERN_BATTLE
 assert(Qol_ChainStatModifier(6144,4915)==7373);
 assert(Qol_ChainStatModifier(7373,6144)==11060);
 assert(Qol_ApplyStatModifier(55,11060)==149);
 assert(Qol_ApplyStatModifier(75,6144)==112);
 // Pure injected factor proves the later Sharpness prerequisite; no ability242.
 assert(Qol_ApplyStatModifier(75,Qol_ChainStatModifier(6144,6144))==169);
 assert(Qol_ApplyStatModifier(Qol_ApplyStatModifier(75,6144),6144)==168);
 assert(Qol_ChainStatModifier(8191,2048)==4096); // chain halfUP
 assert(Qol_ApplyStatModifier(8191,2048)==4095); // apply halfDOWN
 assert(Qol_ChainStatModifier(1048576,8192)==2097152);
 assert(Qol_ApplyStatModifier(1048576,8192)==2097152); // >32bit product
 BattleContext c;bpFixture(&c,MOVE_TACKLE,1,TYPE_ELECTRIC,CATEGORY_PHYSICAL,0);
 sports=MOVE_EFFECT_FLAG_MUD_SPORT;
 assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage(1)); // valid BP floor only
 c.trainerAIData.moveData[MOVE_TACKLE].power=0;
 assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage(0));
 MoveDamageCalc u={0},v={0};u.ability=ABILITY_TECHNICIAN;
 assert(Qol_ModernBasePower(0,MOVE_TACKLE,CATEGORY_PHYSICAL,TYPE_NORMAL,&u,&v,0,4096,0,FALSE,1,0,0,0)==0);
 assert(Qol_ModernBasePower(1,MOVE_TACKLE,CATEGORY_STATUS,TYPE_NORMAL,&u,&v,0,4096,0,FALSE,1,0,0,0)==1);
#endif
 return 0;}
''')

    def test_attainable_groups_independent_pinned_integer_oracle(self):
        # Python creates expected literals from Q12 callbacks, independent of C.
        def grouped(bp, factors):
            total = 4096
            for factor in factors:
                total = (total * factor + 2048) // 4096
            return max(1, (bp * total + 2047) // 4096)
        rows=[]
        for bp in (1,15,40,41,55,60,61,75,80,90,65535):
            for ability in range(5):
                for item in range(3):
                    for hh in range(2):
                        for charged_sport in range(4):
                            factors=[]
                            if ability==1 and bp<=60:factors.append(6144)
                            if ability==2:factors.append(5120)
                            if ability in (3,4):factors.append(4915)
                            if item:factors.append(4915 if item==1 else 4505)
                            if hh:factors.append(6144)
                            if charged_sport&1:factors.append(8192)
                            if charged_sport&2:factors.append(1352)
                            rows.append((bp,ability,item,hh,charged_sport,grouped(bp,factors)))
        table='static const int rows[][6]={'+','.join('{'+','.join(map(str,r))+'}' for r in rows)+'};\n'
        self.variants(source()+table+r'''
int main(void){
#if QOL_MODERN_BATTLE
 const int abilities[]={ABILITY_NONE,ABILITY_TECHNICIAN,ABILITY_RIVALRY,ABILITY_IRON_FIST,ABILITY_RECKLESS};
 for(unsigned r=0;r<NELEMS(rows);r++){
  const int *v=rows[r];int move=v[1]==3?MOVE_THUNDER_PUNCH:MOVE_TACKLE;
  BattleContext c;bpFixture(&c,move,v[0],TYPE_ELECTRIC,CATEGORY_PHYSICAL,v[1]==4?MOVE_EFFECT_RECOIL_QUARTER_DAMAGE_DELT:0);
  c.battleMons[0].ability=abilities[v[1]];
  items[0]=v[2]==1?HOLD_EFFECT_STRENGTHEN_ELECTRIC:v[2]==2?HOLD_EFFECT_POWER_UP_PHYS:0;
  c.turnData[0].helpingHandFlag=v[3];if(v[4]&1)c.battleMons[0].moveEffectFlags|=MOVE_EFFECT_FLAG_CHARGE;
  if(v[4]&2)sports=MOVE_EFFECT_FLAG_MUD_SPORT;
  // Large BP exercises widened intrinsic/group locals; keep final formula safe.
  vars[0][BMON_DATA_ATK]=100;
  assert(hit(&c,move,0,0,0)==v[5]*22/50+2);
 }
#endif
 return 0;}
''')

    def test_native_external_vs_intrinsic_and_unknown_multiplier_ownership(self):
        self.variants(source()+r'''
int main(void){
 BattleContext c;
 const int effects[]={MOVE_EFFECT_DOUBLE_POWER_WHEN_STATUSED,MOVE_EFFECT_DOUBLE_POWER_WHEN_BELOW_HALF};
 for(int event=0;event<2;event++)for(int multi=10;multi<=20;multi+=10){
  bpFixture(&c,MOVE_TACKLE,41,TYPE_NORMAL,CATEGORY_PHYSICAL,effects[event]);
  vars[0][BMON_DATA_STATUS]=STATUS_PARALYSIS;vars[1][BMON_DATA_HP]=50;
  c.powerMultiplier=multi;c.battleMons[0].ability=ABILITY_TECHNICIAN;
  int bp=QOL_MODERN_BATTLE?123:multi==20?82:61;
  assert(hit(&c,MOVE_TACKLE,41,0,0)==bpDamage(bp));
 }
 // All six real Reckless effects, including added moves reusing native effects.
 const int recoil[]={45,48,198,253,262,269};
 for(unsigned e=0;e<NELEMS(recoil);e++)for(int multi=10;multi<=12;multi+=2){
  bpFixture(&c,MOVE_TACKLE,80,TYPE_NORMAL,CATEGORY_PHYSICAL,recoil[e]);
  c.battleMons[0].ability=ABILITY_RECKLESS;c.powerMultiplier=multi;
  c.turnData[0].helpingHandFlag=1;items[0]=HOLD_EFFECT_STRENGTHEN_NORMAL;
  assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage(QOL_MODERN_BATTLE?173:multi==12?172:144));
 }
 // Intrinsic, deferred semi-invulnerable and unknown20 all retain early doubles.
 const int compat[]={185,171,217,126,146,147,149,150,257,261,0,230};
 for(unsigned e=0;e<NELEMS(compat);e++){
  bpFixture(&c,MOVE_TACKLE,40,TYPE_NORMAL,CATEGORY_PHYSICAL,compat[e]);
  c.powerMultiplier=20;c.battleMons[0].ability=ABILITY_TECHNICIAN;
  assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage(80));
 }
 for(int multi=11;multi<=31;multi++){
  bpFixture(&c,MOVE_TACKLE,41,TYPE_NORMAL,CATEGORY_PHYSICAL,0);c.powerMultiplier=multi;
  assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage(41*multi/10));
 }
 return 0;}
''')

    def test_items_base_species_transform_effective_type_and_suppression(self):
        s=source().replace('static int GetBattlerHeldItem(BattleContext *c,int b){return items[b];}',
                           'static u16 GetBattlerHeldItem(BattleContext *c,int b);')
        s+=snow.native('GetBattlerHeldItem')
        self.variants(s+r'''
int main(void){
 const int species[]={SPECIES_LATIAS,SPECIES_LATIOS,SPECIES_DIALGA,SPECIES_PALKIA,SPECIES_GIRATINA};
 const int held[]={HOLD_EFFECT_LATI_SPECIAL,HOLD_EFFECT_LATI_SPECIAL,HOLD_EFFECT_DIALGA_BOOST,HOLD_EFFECT_PALKIA_BOOST,HOLD_EFFECT_GIRATINA_BOOST};
 for(int item=0;item<5;item++)for(int transform=0;transform<2;transform++)for(int original=0;original<2;original++)
 for(int blocked=0;blocked<4;blocked++)for(int type=0;type<2;type++){
  BattleContext c;bpFixture(&c,MOVE_SWIFT,41,TYPE_NORMAL,CATEGORY_SPECIAL,0);
  c.battleMons[0].item=held[item];vars[0][BMON_DATA_SPECIES]=original?species[item]:SPECIES_DITTO;
  if(transform){vars[0][BMON_DATA_STATUS2]=STATUS2_TRANSFORM;partySpecies[0]=original?SPECIES_DITTO:species[item];}
  if(blocked==1)c.battleMons[0].ability=ABILITY_KLUTZ;
  if(blocked==2)c.battleMons[0].moveEffectData.embargoFlag=1;
  if(blocked==3){c.battleMons[0].ability=ABILITY_KLUTZ;c.battleMons[0].moveEffectFlags=MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED;}
  int active=blocked!=1&&blocked!=2,base=transform?!original:original,bp=41;
#if QOL_MODERN_BATTLE
  if(active&&base&&type)bp=49;
  assert(hit(&c,MOVE_SWIFT,0,type?TYPE_DRAGON:TYPE_NORMAL,0)==bpDamage(bp));
#endif
 }
 return 0;}
''')

    def test_dry_skin_rivalry_sports_weather_and_mold_breaker_roles(self):
        self.variants(source()+r'''
int main(void){
#if QOL_MODERN_BATTLE
 for(int gender=0;gender<3;gender++)for(int item=0;item<3;item++){
  BattleContext c;bpFixture(&c,MOVE_TACKLE,41,TYPE_NORMAL,CATEGORY_PHYSICAL,0);
  c.battleMons[0].ability=ABILITY_RIVALRY;vars[1][BMON_DATA_GENDER]=gender;
  items[0]=item==1?HOLD_EFFECT_STRENGTHEN_NORMAL:item==2?HOLD_EFFECT_POWER_UP_PHYS:0;
  // Exact rational factors, followed by pinned Q12 item rounding.
  int factor=gender==0?5120:gender==1?3072:4096;
  if(item)factor=(factor*(item==1?4915:4505)+2048)/4096;
  assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage((41*factor+2047)/4096));
 }
 for(int mold=0;mold<2;mold++)for(int hidden=0;hidden<2;hidden++){
  BattleContext c;bpFixture(&c,MOVE_EMBER,41,TYPE_FIRE,CATEGORY_SPECIAL,0);
  c.battleMons[1].ability=ABILITY_DRY_SKIN;c.battleMons[1].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  if(mold&&!hidden){ // Native causal bypass bookkeeping is allowed at caller boundary.
   assert(CalcMoveDamage(NULL,&c,MOVE_EMBER,0,0,0,0,0,1,1)==bpDamage(41));
   assert(c.selfTurnData[0].moldBreakerFlag);
  }else assert(hit(&c,MOVE_EMBER,0,0,0)==bpDamage(hidden?41:51));
 }
 // Attainable user Technician + target Dry Skin + category item + HH + Sport.
 for(int item=0;item<3;item++)for(int hh=0;hh<2;hh++)for(int sport=0;sport<2;sport++){
  BattleContext c;bpFixture(&c,MOVE_EMBER,41,TYPE_FIRE,CATEGORY_SPECIAL,0);
  c.battleMons[0].ability=ABILITY_TECHNICIAN;c.battleMons[1].ability=ABILITY_DRY_SKIN;
  items[0]=item==1?HOLD_EFFECT_STRENGTHEN_FIRE:item==2?HOLD_EFFECT_POWER_UP_SPEC:0;
  c.turnData[0].helpingHandFlag=hh;if(sport)sports=MOVE_EFFECT_FLAG_WATER_SPORT;
  int factor=7680; // exact1.5*1.25 before item, then HH, then Sport
  if(item)factor=(factor*(item==1?4915:4505)+2048)/4096;
  if(hh)factor=(factor*6144+2048)/4096;
  if(sport)factor=(factor*1352+2048)/4096;
  assert(hit(&c,MOVE_EMBER,0,0,0)==bpDamage((41*factor+2047)/4096));
 }
 for(int blocker=0;blocker<3;blocker++)for(int hidden=0;hidden<2;hidden++)for(int weather=0;weather<4;weather++){
  BattleContext c;bpFixture(&c,MOVE_SOLAR_BEAM,41,TYPE_GRASS,CATEGORY_SPECIAL,0);
  c.battleMons[2].ability=blocker==1?ABILITY_CLOUD_NINE:blocker==2?ABILITY_AIR_LOCK:ABILITY_NONE;
  c.battleMons[2].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int fields[]={0,FIELD_CONDITION_RAIN,FIELD_CONDITION_SANDSTORM,FIELD_CONDITION_HAIL};
  c.fieldCondition=FIELD_CONDITION_SUN; // supplied field is authoritative
  assert(hit(&c,MOVE_SOLAR_BEAM,0,0,fields[weather])==bpDamage(weather&&(!blocker||hidden)?20:41));
 }
 BattleContext c;bpFixture(&c,MOVE_EMBER,75,TYPE_FIRE,CATEGORY_SPECIAL,0);
 sports=MOVE_EFFECT_FLAG_WATER_SPORT;c.turnData[0].helpingHandFlag=1;items[0]=HOLD_EFFECT_POWER_UP_SPEC;
 // chain4505*6144*1352=2231; apply75=>41.
 assert(hit(&c,MOVE_EMBER,0,0,0)==bpDamage(41));
#endif
 return 0;}
''')


    def test_actual_payback_revenge_and_pursuit_commands_feed_intrinsic_power(self):
        s=source().replace('int hp,ability,status,item,statChanges[8];',
                           'int hp,ability,status,item,statChanges[8],moves[4],movePPCur[4];')
        s=s.replace('int embargoFlag;', 'int embargoFlag,encoredMove,encoredMoveIndex,moveNoChoice;')
        s=s.replace('int helpingHandFlag;', 'int helpingHandFlag,physicalDamage[4],specialDamage[4],battlerBitPhysicalDamage,battlerBitSpecialDamage;')
        s=s.replace('int selectedMonIndex[4];', 'int selectedMonIndex[4];int movePower,moveNoCur,battlerIdAttacker,battlerIdTarget,battlerIdSwitch,moveNoBattlerPrev[4];struct {int command;}playerActions[4];')
        s+=r'''
static int scriptSteps,resets,copies;
static void BattleScriptIncrementPointer(BattleContext *c,int n){scriptSteps+=n;}
static int BattleScriptReadWord(BattleContext *c){return 7;}
static int CheckTruant(BattleContext *c,int b){return 0;}
static int GetBattlerSelectedMove(BattleContext *c,int b){return c->battleMons[b].moves[0];}
static int BattleMon_GetMoveIndex(Mon *m,int move){for(int i=0;i<4;i++)if(m->moves[i]==move)return i;assert(0);return 0;}
static void BattleContext_ResetMoveStatus(BattleSystem *s,BattleContext *c){resets++;}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int b){copies++;}
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return items[b];}
static int GetHeldItemModifier(BattleContext *c,int b,int mode){return 0;}
'''+''.join(snow.native(n,'src/battle/battle_command.c') for n in
            ('BtlCmd_CalcPaybackPower','BtlCmd_CalcRevengeDamageMul','BtlCmd_TryPursuit'))
        self.variants(s+r'''
int main(void){
 for(int acted=0;acted<2;acted++){
  BattleContext c;bpFixture(&c,MOVE_PAYBACK,50,TYPE_NORMAL,CATEGORY_PHYSICAL,MOVE_EFFECT_DOUBLE_POWER_IF_HIT);
  c.moveNoCur=MOVE_PAYBACK;c.battlerIdTarget=1;c.playerActions[1].command=acted?CONTROLLER_COMMAND_40:0;
  c.battleMons[0].ability=ABILITY_TECHNICIAN;scriptSteps=0;
  assert(!BtlCmd_CalcPaybackPower(NULL,&c));assert(scriptSteps==1);
  assert(c.movePower==(acted?100:50)&&c.powerMultiplier==10);
  assert(hit(&c,MOVE_PAYBACK,c.movePower,0,0)==bpDamage(acted?100:75));
 }
 for(int category=0;category<2;category++)for(int damage=0;damage<2;damage++)for(int target=1;target<4;target++)for(int mask=0;mask<4;mask++){
  BattleContext c;bpFixture(&c,MOVE_REVENGE,60,TYPE_NORMAL,CATEGORY_PHYSICAL,185);
  c.battlerIdTarget=target;c.battleMons[0].ability=ABILITY_TECHNICIAN;
  if(category){c.turnData[0].specialDamage[target]=damage;c.turnData[0].battlerBitSpecialDamage=mask?1<<mask:0;}
  else{c.turnData[0].physicalDamage[target]=damage;c.turnData[0].battlerBitPhysicalDamage=mask?1<<mask:0;}
  BtlCmd_CalcRevengeDamageMul(NULL,&c);int boosted=damage&&target==mask;
  assert(c.powerMultiplier==(boosted?20:10)&&!c.movePower);
  assert(hit(&c,MOVE_REVENGE,0,0,0)==bpDamage(boosted?120:90));
 }
 for(int pressure=0;pressure<2;pressure++)for(int encore=0;encore<2;encore++)for(int pp=0;pp<4;pp++){
  BattleContext c;bpFixture(&c,MOVE_PURSUIT,40,TYPE_NORMAL,CATEGORY_PHYSICAL,MOVE_EFFECT_HIT_BEFORE_SWITCH);
  c.battlerIdSwitch=1;c.battleMons[0].ability=ABILITY_TECHNICIAN;
  c.battleMons[1].ability=pressure?ABILITY_PRESSURE:ABILITY_NONE;
  c.battleMons[0].moves[0]=MOVE_PURSUIT;c.battleMons[0].movePPCur[0]=pp;
  if(encore)c.battleMons[0].moveEffectData.encoredMove=MOVE_PURSUIT;
  for(int b=1;b<4;b++)c.playerActions[b].command=CONTROLLER_COMMAND_40;
  items[0]=HOLD_EFFECT_CHOICE_ATK;resets=copies=scriptSteps=0;
  assert(!BtlCmd_TryPursuit(NULL,&c));assert(resets==!!pp&&copies==!!pp);
  assert(c.battleMons[0].movePPCur[0]==(pp?(pressure&&pp>1?pp-2:pp-1):0));
  if(pp){
   assert(c.battlerIdAttacker==0&&c.battlerIdTarget==1&&c.moveNoCur==MOVE_PURSUIT);
   assert(c.powerMultiplier==20&&c.moveNoBattlerPrev[0]==MOVE_PURSUIT);
   assert(c.playerActions[0].command==CONTROLLER_COMMAND_40&&c.battleMons[0].moveEffectData.moveNoChoice==MOVE_PURSUIT);
   items[0]=0; // Isolate intrinsic BP; Choice offensive layer has separate D1 tests.
   assert(hit(&c,MOVE_PURSUIT,0,0,0)==bpDamage(80));
  }else assert(c.powerMultiplier==10);
 }
 return 0;}
''')

    def test_original_effect_bytecode_runs_real_external_producers(self):
        import test_modern_next_move_effects as effects
        s=effects.vm_source().replace('if(v==BMON_DATA_HP)return c->battleMons[b].hp;',
             'if(v==BMON_DATA_HP)return c->battleMons[b].hp;\n if(v==BMON_DATA_MAXHP)return c->battleMons[b].maxHp;\n if(v==BMON_DATA_STATUS)return c->battleMons[b].status;')
        s=s.replace('case 33:BtlCmd_CompareMonDataToValue(NULL,c);break;',
                    'case 33:BtlCmd_CompareMonDataToValue(NULL,c);break;\n case 79:BtlCmd_CompareMonDataToVar(NULL,c);break;')
        s=s.replace('static void run(BattleContext *c,const u32 *words,int length){', 'static BOOL BtlCmd_CompareMonDataToVar(BattleSystem *s,BattleContext *c);\nstatic void run(BattleContext *c,const u32 *words,int length){')
        s=s.replace('static int *BattleScriptGetVarPointer(', 'static void *BattleScriptGetVarPointer(')
        s+=snow.native('BtlCmd_CompareMonDataToVar','src/battle/battle_command.c')
        s+= ''.join(effects.c_array('effect'+str(e),effects.EFFECTS[e]) for e in (45,48,198,253,262,269,169,221))
        self.variants(s+r'''
int main(void){
 const u32 *scripts[]={effect45,effect48,effect198,effect253,effect262,effect269};
 const int lengths[]={NELEMS(effect45),NELEMS(effect48),NELEMS(effect198),NELEMS(effect253),NELEMS(effect262),NELEMS(effect269)};
 for(int e=0;e<6;e++)for(int reckless=0;reckless<2;reckless++){
  BattleContext c=fixture(MOVE_TACKLE);c.vars[BSCRIPT_VAR_POWER_MULTI]=10;
  c.battleMons[0].ability=reckless?ABILITY_RECKLESS:ABILITY_NONE;
  run(&c,scripts[e],lengths[e]);assert(c.vars[BSCRIPT_VAR_POWER_MULTI]==(reckless?12:10));
  assert(c.criticalCalls==1&&c.damageCalls==1&&!randomCalls);
 }
 const int statuses[]={0,STATUS_SLEEP,STATUS_FREEZE,STATUS_PARALYSIS,STATUS_BURN,STATUS_POISON,STATUS_BAD_POISON};
 for(unsigned status=0;status<NELEMS(statuses);status++){
  BattleContext c=fixture(MOVE_FACADE);c.vars[BSCRIPT_VAR_POWER_MULTI]=10;c.battleMons[0].status=statuses[status];
  RUN(&c,effect169);assert(c.vars[BSCRIPT_VAR_POWER_MULTI]==(statuses[status]&STATUS_FACADE_BOOST?20:10));
  assert(c.criticalCalls==1&&c.damageCalls==1&&!randomCalls);
 }
 for(int hp=49;hp<=52;hp++){
  BattleContext c=fixture(MOVE_BRINE);c.vars[BSCRIPT_VAR_POWER_MULTI]=10;c.battleMons[1].maxHp=101;c.battleMons[1].hp=hp;
  RUN(&c,effect221);assert(c.vars[BSCRIPT_VAR_POWER_MULTI]==(hp<=50?20:10));
  assert(c.criticalCalls==1&&c.damageCalls==1&&!randomCalls);
 }
 return 0;}
''')


    def test_every_target_no_state_write_and_explicit_projection_limits(self):
        self.variants(source(ai=True)+r'''
int main(void){
 for(int target=0;target<4;target++)for(int ambient=0;ambient<3;ambient++){
  int multipliers[]={10,12,20};BattleContext c;bpFixture(&c,MOVE_TACKLE,41,TYPE_NORMAL,CATEGORY_PHYSICAL,0);
  int attacker=target^1;c.trainerAIData.battlerIdTarget=target;c.powerMultiplier=multipliers[ambient];
  vars[attacker][BMON_DATA_ATK]=5000;vars[target][BMON_DATA_DEF]=100;
  // Candidate projection still consumes ambient native state: it has no real
  // effect-script provenance. Preserve/characterize that limit, never invent it.
  int expected=bpDamage(41*multipliers[ambient]/10),before=rngCalls;BattleContext snapshot=c;u8 ivs[6]={0};
  assert(CalcMoveDamage(NULL,&c,MOVE_TACKLE,0,0,0,0,attacker,target,1)==expected);
  assert(TrainerAI_CalcDamage(NULL,&c,MOVE_TACKLE,0,ivs,attacker,ABILITY_NONE,0,100)==expected);
  assert(rngCalls==before&&!memcmp(&snapshot,&c,sizeof(c)));
 }
 BattleContext c;bpFixture(&c,MOVE_STRUGGLE,40,TYPE_NORMAL,CATEGORY_PHYSICAL,0);
 c.battleMons[0].ability=ABILITY_TECHNICIAN;assert(hit(&c,MOVE_STRUGGLE,0,0,0)==bpDamage(40));
 // Exact value/effect/state prerequisites: unsupported combinations fall back.
 const int effects[]={48,169,221};
 for(int e=0;e<3;e++){
  bpFixture(&c,MOVE_TACKLE,41,TYPE_NORMAL,CATEGORY_PHYSICAL,effects[e]);
  c.powerMultiplier=e==0?12:20;vars[1][BMON_DATA_HP]=100;
  assert(hit(&c,MOVE_TACKLE,0,0,0)==bpDamage(e==0?49:82));
 }
#if QOL_MODERN_MOVES
 // A14 callback owns only intrinsic powers; explicit values bypass it once.
 const int ids[]={MOVE_VENOSHOCK,MOVE_HEX,MOVE_STORED_POWER,MOVE_POWER_TRIP,MOVE_ACROBATICS};
 const int table[]={65,65,20,20,55},resolved[]={130,130,860,860,110};
 for(int m=0;m<5;m++){
  bpFixture(&c,ids[m],table[m],TYPE_NORMAL,CATEGORY_PHYSICAL,0);
  c.battleMons[1].status=STATUS_POISON;c.battleMons[0].item=ITEM_NONE;
  for(int stage=STAT_ATK;stage<=STAT_EVASION;stage++)c.battleMons[0].statChanges[stage]=12;
  assert(hit(&c,ids[m],0,0,0)==bpDamage(resolved[m]));
  c.battleMons[0].ability=ABILITY_TECHNICIAN;
  assert(hit(&c,ids[m],41,0,0)==bpDamage(61));
 }
#endif
 return 0;}
''')


if __name__ == '__main__':
    unittest.main()
