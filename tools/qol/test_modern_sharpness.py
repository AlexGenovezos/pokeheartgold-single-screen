"""D2b: actual slicing classifier, shared formula, AI and command routes."""
from pathlib import Path
import itertools
import re
import unittest
import test_game_logic as game
import test_modern_base_power as bp
import test_modern_me_first as mf
import test_modern_moves as moves
import test_modern_selected_stats as selected
import test_modern_snow as snow

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = (15,75,163,210,314,332,348,400,403,404,427,440)
LATER = (536,537,898)


class SharpnessTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run
    variants = selected.SelectedStatTests.variants

    def test_actual_classifier_exhaustive_u16_all_eight_flags(self):
        from nitro_data import unpack_narc
        original=unpack_narc((ROOT/'files/poketool/waza/waza_tbl.narc').read_bytes())[0]
        for move in ORIGINAL:
            self.assertEqual(original[move][2],1 if move in (314,403) else 0)
        self.assertIn('BOOL Qol_IsSlicingMove(u16 moveId);',(ROOT/'include/qol_moves.h').read_text())
        self.variants(moves.ModernMoveTests().source()+r'''
int main(void){
 for(int id=0;id<=65535;id++){
  int expected=id==15||id==75||id==163||id==210||id==314||id==332||id==348||id==400||id==403||id==404||id==427||id==440;
  expected|=QOL_MODERN_MOVES&&(id==536||id==537||id==898);
  assert(Qol_IsSlicingMove(id)==expected);
 }
 assert(sizeof(MoveTbl)==16&&NUM_MOVES==467);
 return 0;}
''')

    def test_actual_shared_formula_physical_special_and_non_slicing(self):
        self.variants(bp.source()+r'''
int main(void){
 const int slicing[]={15,75,163,210,314,332,348,400,403,404,427,440};
 for(unsigned i=0;i<NELEMS(slicing);i++)for(int category=0;category<2;category++)for(int hidden=0;hidden<2;hidden++){
  BattleContext c;bpFixture(&c,slicing[i],75,TYPE_NORMAL,category,0);
  c.battleMons[0].ability=242;c.battleMons[0].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  assert(hit(&c,slicing[i],0,0,0)==bpDamage(QOL_MODERN_BATTLE&&!hidden?112:75));
  c.battleMons[1].ability=ABILITY_MOLD_BREAKER;
  assert(hit(&c,slicing[i],0,0,0)==bpDamage(QOL_MODERN_BATTLE&&!hidden?112:75));
  c.battleMons[0].ability=ABILITY_MOLD_BREAKER;c.battleMons[1].ability=242;
  assert(hit(&c,slicing[i],0,0,0)==bpDamage(75));
 }
 BattleContext zero;bpFixture(&zero,MOVE_AIR_SLASH,0,TYPE_FLYING,CATEGORY_SPECIAL,0);zero.battleMons[0].ability=242;
 assert(hit(&zero,MOVE_AIR_SLASH,0,0,0)==bpDamage(0));
 const int controls[]={13,33,232,306,337,421,467};
 for(unsigned i=0;i<NELEMS(controls);i++){
  BattleContext c;bpFixture(&c,controls[i],75,TYPE_NORMAL,CATEGORY_PHYSICAL,0);c.battleMons[0].ability=242;
  assert(hit(&c,controls[i],0,0,0)==bpDamage(75));
 }
 return 0;}
''')

    def test_grouped_literals_internal_public_origin_and_all_overrides(self):
        self.variants(mf.command_source()+r'''
int main(void){
 for(int p=0;p<=81;p++)for(int hh=0;hh<2;hh++)for(int item=0;item<2;item++)for(int origin=0;origin<2;origin++)for(int eligible=0;eligible<2;eligible++){
  BattleContext c;bpFixture(&c,MOVE_AIR_SLASH,75,TYPE_FLYING,CATEGORY_SPECIAL,0);
  c.battleMons[0].ability=242;c.turnData[0].helpingHandFlag=hh;
  items[0]=item?HOLD_EFFECT_STRENGTHEN_FLYING:0;
  int power=p?p:75,group=4096;
  if(QOL_MODERN_BATTLE)group=6144;
  if(item)group=(group*4915+2048)/4096;
  if(QOL_MODERN_BATTLE&&origin&&eligible)group=(group*6144+2048)/4096;
  if(hh)group=(group*6144+2048)/4096;
  int expected=QOL_MODERN_BATTLE?(power*group+2047)/4096:power*(hh?15:10)/10*(item?120:100)/100;
  assert(Qol_CalcMoveDamageInternal(NULL,&c,MOVE_AIR_SLASH,0,0,p,0,0,1,1,(QolDamageOrigin)origin,eligible)==bpDamage(expected));
 }
 BattleContext c;bpFixture(&c,MOVE_AIR_SLASH,75,TYPE_FLYING,CATEGORY_SPECIAL,0);
 c.battleMons[0].ability=242;
 assert(hit(&c,MOVE_AIR_SLASH,0,0,0)==bpDamage(QOL_MODERN_BATTLE?112:75));
 c.turnData[0].helpingHandFlag=1;
 assert(hit(&c,MOVE_AIR_SLASH,0,0,0)==bpDamage(QOL_MODERN_BATTLE?169:112));
 vars[0][BMON_DATA_SPATK]=100;
 assert(hit(&c,MOVE_AIR_SLASH,0,0,0)==(QOL_MODERN_BATTLE?76:51));
 vars[0][BMON_DATA_SPATK]=5000;items[0]=HOLD_EFFECT_STRENGTHEN_FLYING;
 assert(hit(&c,MOVE_AIR_SLASH,0,0,0)==bpDamage(QOL_MODERN_BATTLE?203:134));
 items[0]=0;
 assert(Qol_CalcMoveDamageInternal(NULL,&c,MOVE_AIR_SLASH,0,0,41,0,0,1,1,QOL_DAMAGE_ORDINARY_COMMAND,TRUE)==bpDamage(QOL_MODERN_BATTLE?138:61));
 c.battleMons[0].moveEffectData.meFirstFlag=1;c.battleMons[0].moveEffectData.meFirstCount=1;c.meFirstTotal=1;
 assert(hit(&c,MOVE_AIR_SLASH,41,0,0)==bpDamage(QOL_MODERN_BATTLE?92:61));
#if QOL_MODERN_BATTLE
 MoveDamageCalc u={0},v={0};u.ability=242;
 assert(Qol_ModernBasePower(0,MOVE_AIR_SLASH,CATEGORY_SPECIAL,TYPE_FLYING,&u,&v,0,4096,0,0,1,0,0,0)==0);
 assert(Qol_ModernBasePower(41,MOVE_AIR_SLASH,CATEGORY_STATUS,TYPE_FLYING,&u,&v,0,4096,0,0,1,0,0,0)==41);
#endif
 return 0;}
''')

    def test_actual_ai_all_rolls_and_ambient_me_first_never_inferred(self):
        self.variants(bp.source(ai=True)+r'''
int main(void){
 for(int roll=85;roll<=100;roll++)for(int hidden=0;hidden<2;hidden++)for(int stale=0;stale<3;stale++){
  BattleContext c;bpFixture(&c,MOVE_AIR_SLASH,75,TYPE_FLYING,CATEGORY_SPECIAL,0);
  c.trainerAIData.battlerIdTarget=1;c.battleMons[0].ability=242;c.turnData[0].helpingHandFlag=1;
  c.battleMons[0].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].moveEffectData.meFirstFlag=stale!=0;c.battleMons[0].moveEffectData.meFirstCount=stale==2?0:1;c.meFirstTotal=1;
  u8 ivs[6]={0};BattleContext copy=c;int before=rngCalls;
  assert(TrainerAI_CalcDamage(NULL,&c,MOVE_AIR_SLASH,0,ivs,0,242,0,roll)==bpDamage(QOL_MODERN_BATTLE&&!hidden?169:112)*roll/100);
  assert(rngCalls==before&&!memcmp(&copy,&c,sizeof(c)));
 }
 return 0;}
''')

    def test_actual_default_and_raw_commands_group_once_all_rolls_slots_crits(self):
        self.variants(mf.command_source()+r'''
int main(void){
 for(int raw=0;raw<2;raw++)for(int roll=0;roll<16;roll++)for(int attacker=0;attacker<4;attacker++)for(int crit=1;crit<=3;crit++){
  BattleContext c;commandFixture(&c,41);int target=(attacker+1)%4;
  c.trainerAIData.moveData[MOVE_AIR_SLASH]=(Move){41,TYPE_FLYING,CATEGORY_SPECIAL,0,0};
  c.moveNoCur=MOVE_AIR_SLASH;c.movePower=41;c.battlerIdAttacker=attacker;c.battlerIdTarget=target;c.criticalMultiplier=crit;
  for(int b=0;b<4;b++){c.battleMons[b].ability=0;c.battleMons[b].moveEffectData.meFirstFlag=0;}
  c.battleMons[attacker].ability=242;c.turnData[attacker].helpingHandFlag=1;
  c.battleMons[attacker].moveEffectData.meFirstFlag=1;c.battleMons[attacker].moveEffectData.meFirstCount=1;
  vars[attacker][BMON_DATA_SPATK]=5000;vars[target][BMON_DATA_SPDEF]=100;
  rng=roll;int before=rngCalls;
  if(raw)BtlCmd_CalcDamageRaw(NULL,&c);else BtlCmd_CalcDamage(NULL,&c);
  int damage=QOL_MODERN_BATTLE?(crit>1?bpDamage(138)*3/2:bpDamage(138)):bpDamage(61)*crit*15/10;
  assert(c.damage==-(raw?damage:damage*(100-roll)/100));
  assert(rngCalls==before+!raw&&c.battleMons[attacker].moveEffectData.meFirstCount==0);
 }
 return 0;}
''')

    def test_python_q12_literals_attainable_groups_and_intrinsic_fury_cutter(self):
        # Independent host oracle supplies literal expected BP, rather than
        # querying either the collector or a second C implementation.
        rows=[]
        for power,item,hh,me_first,sport in itertools.product((1,15,40,41,55,60,61,75,80,90,65535),range(3),range(2),range(2),range(2)):
            factors=[6144]
            if item:factors.append(4915 if item==1 else 4505)
            if me_first:factors.append(6144)
            if hh:factors.append(6144)
            if sport:factors.append(1352)
            group=4096
            for factor in factors:group=(group*factor+2048)//4096
            rows.append((power,item,hh,me_first,sport,max(1,(power*group+2047)//4096)))
        table='static const int rows[][6]={'+','.join('{'+','.join(map(str,r))+'}' for r in rows)+'};\n'
        self.variants(bp.source()+table+r'''
int main(void){
#if QOL_MODERN_BATTLE
 for(unsigned r=0;r<NELEMS(rows);r++){
  const int *v=rows[r];BattleContext c;bpFixture(&c,MOVE_AIR_SLASH,v[0],TYPE_ELECTRIC,CATEGORY_SPECIAL,0);
  c.battleMons[0].ability=242;c.turnData[0].helpingHandFlag=v[2];
  items[0]=v[1]==1?HOLD_EFFECT_STRENGTHEN_ELECTRIC:v[1]==2?HOLD_EFFECT_POWER_UP_SPEC:0;
  if(v[4])sports=MOVE_EFFECT_FLAG_MUD_SPORT;
  vars[0][BMON_DATA_SPATK]=100;
  assert(Qol_CalcMoveDamageInternal(NULL,&c,MOVE_AIR_SLASH,0,0,v[0],0,0,1,1,QOL_DAMAGE_ORDINARY_COMMAND,v[3])==v[5]*22/50+2);
 }
 assert(Qol_ChainStatModifier(Qol_ChainStatModifier(6144,4915),6144)==11060);
 assert(Qol_ApplyStatModifier(75,11060)==203); // Q12 approximation crosses exact202.5
#endif
 // Fury Cutter's intrinsic multiplier resolves before the slicing event.
 for(int multi=10;multi<=80;multi*=2){
  BattleContext c;bpFixture(&c,MOVE_FURY_CUTTER,41,TYPE_BUG,CATEGORY_PHYSICAL,MOVE_EFFECT_DOUBLE_POWER_EACH_TURN);
  c.powerMultiplier=multi;c.battleMons[0].ability=242;
  int intrinsic=41*multi/10,power=QOL_MODERN_BATTLE?intrinsic*3/2:intrinsic;
  assert(hit(&c,MOVE_FURY_CUTTER,0,0,0)==bpDamage(power));
 }
 return 0;}
''')

    def test_later_moves_use_actual_classifier_and_tables_only_with_move_flag(self):
        self.variants(bp.source(ai=True)+r'''
int main(void){
 const int ids[]={536,537,898},power[]={90,75,70};
 for(int i=0;i<3;i++){
  BattleContext c;bpFixture(&c,ids[i],1,TYPE_NORMAL,CATEGORY_PHYSICAL,0);
  c.battleMons[0].ability=242;c.trainerAIData.battlerIdTarget=1;
#if QOL_MODERN_MOVES
  assert(BATTLE_MOVE_DATA(&c,ids[i]).power==power[i]);
  assert(BATTLE_MOVE_DATA(&c,ids[i]).category==CATEGORY_PHYSICAL);
  assert(hit(&c,ids[i],0,0,0)==bpDamage(QOL_MODERN_BATTLE?power[i]*3/2:power[i]));
  u8 ivs[6]={0};
  for(int roll=85;roll<=100;roll++)
   assert(TrainerAI_CalcDamage(NULL,&c,ids[i],0,ivs,0,242,0,roll)==bpDamage(QOL_MODERN_BATTLE?power[i]*3/2:power[i])*roll/100);
#else
  assert(!Qol_IsSlicingMove(ids[i])&&!Qol_IsSupportedMove(ids[i]));
#endif
 }
 return 0;}
''')

    def test_critical_burn_screens_slots_and_native_item_suppression(self):
        s=bp.source().replace('static int GetBattlerHeldItem(BattleContext *c,int b){return items[b];}',
                             'static u16 GetBattlerHeldItem(BattleContext *c,int b);')
        s+=snow.native('GetBattlerHeldItem')
        self.variants(s+r'''
int main(void){
 for(int category=0;category<2;category++)for(int crit=1;crit<=3;crit++)for(int burn=0;burn<2;burn++)for(int screen=0;screen<2;screen++)for(int attacker=0;attacker<4;attacker++){
  BattleContext c;bpFixture(&c,MOVE_AIR_SLASH,75,TYPE_FLYING,category,0);int target=(attacker+1)%4;
  c.battleMons[attacker].ability=242;vars[attacker][BMON_DATA_ATK]=vars[attacker][BMON_DATA_SPATK]=100;
  vars[target][BMON_DATA_DEF]=vars[target][BMON_DATA_SPDEF]=100;vars[attacker][BMON_DATA_STATUS]=burn?STATUS_BURN:0;
  int side=screen?SIDE_CONDITION_REFLECT|SIDE_CONDITION_LIGHT_SCREEN:0;
  BattleContext before=c;int count=rngCalls;
  int sharp=CalcMoveDamage(NULL,&c,MOVE_AIR_SLASH,side,0,0,0,attacker,target,crit);
  assert(!memcmp(&before,&c,sizeof(c))&&count==rngCalls);
  c.battleMons[attacker].ability=ABILITY_STEADFAST;
  assert(CalcMoveDamage(NULL,&c,MOVE_AIR_SLASH,side,0,QOL_MODERN_BATTLE?112:75,0,attacker,target,crit)==sharp);
 }
 for(int ability=0;ability<3;ability++)for(int hidden=0;hidden<2;hidden++)for(int embargo=0;embargo<2;embargo++)for(int override=0;override<2;override++){
  BattleContext c;bpFixture(&c,MOVE_AIR_SLASH,75,TYPE_FLYING,CATEGORY_SPECIAL,0);
  c.battleMons[0].ability=ability==0?242:ability==1?ABILITY_KLUTZ:ABILITY_NORMALIZE;
  c.battleMons[0].moveEffectFlags=hidden?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].moveEffectData.embargoFlag=embargo;
  c.battleMons[0].item=override?HOLD_EFFECT_STRENGTHEN_FIRE:HOLD_EFFECT_STRENGTHEN_FLYING;
  int activeItem=!embargo&&!(ability==1&&!hidden),normal=ability==2&&!hidden;
  int group=QOL_MODERN_BATTLE&&ability==0&&!hidden?6144:4096;
  if(activeItem&&!normal)group=(group*4915+2048)/4096;
  int power=QOL_MODERN_BATTLE?(75*group+2047)/4096:75*(activeItem&&!normal?120:100)/100;
  assert(hit(&c,MOVE_AIR_SLASH,0,override?TYPE_FIRE:0,0)==bpDamage(power));
 }
 return 0;}
''')

    def test_accepted_me_first_worker_commands_and_public_abi_remain_identical_off(self):
        import subprocess,tempfile
        revision='d37566880c390cf485f4d286a81ba174a5e4dff9'
        old=lambda path:subprocess.check_output(['git','show',revision+':'+path],text=True)
        self.assertEqual(old('include/battle/battle_util.h'),(ROOT/'include/battle/battle_util.h').read_text())
        util=old('src/battle/battle_util.c');command=old(mf.COMMAND)
        s=mf.command_source()+mf.function(util,'Qol_CalcMoveDamageInternal').replace('Qol_CalcMoveDamageInternal','BaselineWorker')+'\n'
        for name in ('DamageCalcDefault','BtlCmd_CalcDamageRaw'):
            s+=mf.function(command,name).replace(name,'Baseline'+name)+'\n'
        s=s.replace('#define GF_ASSERT assert','#define GF_ASSERT(x) fixtureAssert(x)')
        for types,moves_flag in itertools.product((0,1),repeat=2):
            with self.subTest(types=types,moves=moves_flag),tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'check.c';path.write_text(s)
                out=subprocess.check_output(['cc','-E','-P','-iquote',str(ROOT/'include'),'-DQOL_MODERN_BATTLE=0',f'-DQOL_MODERN_TYPES={types}',f'-DQOL_MODERN_MOVES={moves_flag}',str(path)],text=True)
                def tokens(name):
                    f=mf.function(out,name);return re.findall(r'[A-Za-z_]\w*|\d+|[^\s]',f[f.index('{'):])
                self.assertEqual(tokens('BaselineWorker'),tokens('Qol_CalcMoveDamageInternal'))
                for name in ('DamageCalcDefault','BtlCmd_CalcDamageRaw'):
                    self.assertEqual(tokens('Baseline'+name),tokens(name))


if __name__=='__main__':unittest.main()
