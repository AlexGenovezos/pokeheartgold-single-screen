"""A14 literal contracts and actual native C/SDK control execution."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import re
import struct
import unittest
from unittest.mock import patch

import test_game_logic as game
import test_modern_moves as moves
import test_modern_rules as rules
import test_modern_simple as simple
import test_modern_snow as snow
import move_resources
from nitro_data import unpack_narc, pack_narc, unpack_messages

ROOT=Path(__file__).resolve().parents[2]
ROWS=[
(471,277,2,0,17,0,15,0,16,0,72,14),
(486,278,2,0,6,0,20,0,16,0,8,349),
(492,279,2,0,3,0,20,0,16,0,72,151),
(529,280,2,0,0,0,30,0,16,0,72,74),
(507,281,2,0,0,0,15,0,16,0,8,334),
(541,282,2,0,12,0,10,0,16,0,8,133),
(494,271,1,40,3,100,20,100,0,0,50,188),
(491,283,0,50,10,100,20,100,0,0,51,172),
(888,283,0,50,12,100,20,100,0,0,51,345),
(477,0,1,65,3,100,10,0,0,0,50,188),
(509,0,1,65,7,100,10,0,0,0,50,247),
(503,0,1,20,14,100,10,0,0,0,50,60),
(684,0,0,20,17,100,10,0,0,0,51,242),
(515,0,0,55,2,100,15,0,0,0,51,332),
]
IDS={r[0] for r in ROWS}
NAMES=['Hone Claws','Quiver Dance','Coil','Work Up','Shell Smash','Cotton Guard',
       'Acid Spray','Flame Charge','Trailblaze','Venoshock','Hex','Stored Power','Power Trip','Acrobatics']


def native(name,path='src/battle/battle_util.c'):
    return game.function_source(path,name)+'\n'


class Next14NativeTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    def test_literal_metadata_flags_gaps_metronome_and_abi(self):
        entries=move_resources.read_entries(ROOT/'include/data/qol_move_entries.inc')
        self.assertEqual(len(entries),72,'A14 metadata missing')
        source=moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
typedef int BattleSystem;typedef int BattleContext;
static int BattleContext_CheckMoveUnuseableInGravity(BattleSystem *s,BattleContext *c,int b,int m){return 0;}
static int BattleContext_CheckMoveHealBlocked(BattleSystem *s,BattleContext *c,int b,int m){return 0;}
'''+rules.array('sMetronomeUnuseableMoves')+native('CheckLegalMimicMove')+native('CheckLegalMetronomeMove')
        source+='static const int rows[][12]={'+','.join('{'+','.join(map(str,r))+'}' for r in ROWS)+'};\n'
        source+=r'''
int main(void){
 assert(NUM_MOVES==467&&sizeof(MoveTbl)==16&&QOL_EXTENDED_MOVE_COUNT==72);
 for(unsigned i=0;i<NELEMS(rows);i++){
  int id=rows[i][0];const MoveTbl *e=Qol_GetExtendedMoveData(id);
  assert(Qol_IsSupportedMove(id)==QOL_MODERN_MOVES);
#if QOL_MODERN_MOVES
  const int actual[]={e->effect,e->category,e->power,e->type,e->accuracy,e->pp,e->effectChance,e->range,e->priority,e->flags,Qol_GetMoveAnimation(id)};
  for(int k=0;k<11;k++)assert(actual[k]==rows[i][k+1]);
#else
  assert(!e);
#endif
  assert(!Qol_IsSoundMove(id)&&!Qol_MoveBypassesSubstitute(id));
  assert(CheckLegalMimicMove(id));
  assert(CheckLegalMetronomeMove(NULL,NULL,0,id)==!(QOL_MODERN_MOVES&&id==888));
 }
 const int gaps[]={468,469,470,487,500,538,65535};
 for(unsigned i=0;i<NELEMS(gaps);i++)assert(!Qol_IsSupportedMove(gaps[i]));
 return 0;}
'''
        for battle in (0,1):
            for enabled in (0,1):
                self.compile_run(source,f'-DQOL_MODERN_BATTLE={battle}',f'-DQOL_MODERN_MOVES={enabled}')
        by_id={e['id']:e for e in entries}
        profile=json.loads((ROOT/'.local-tools/validation/gen9-import-profile.json').read_text())
        pinned={m['engine_id']:m for m in profile['moves']}
        for row,name in zip(ROWS,NAMES):
            self.assertEqual(tuple(by_id[row[0]][k] for k in move_resources.FIELDS),row)
            self.assertEqual(move_resources.PRESENTATION[row[0]]['name'],name)
            self.assertEqual(pinned[row[0]]['name'],name)
            self.assertLess(len(name),32)
            alias=next((ROOT/'files/battledata/script/move_script').glob(f'move_script_{row[-1]:04}*.s'))
            commands=[l.strip() for l in alias.read_text().splitlines() if l.strip() and not l.strip().startswith(('.','_','//'))]
            self.assertEqual(commands,['GoToEffectScript'])

    def test_cotton_single_actual_event_all_caps_simple_suppression_and_ability_loss(self):
        self.assertTrue('statChangeParam == 150' in (ROOT/'src/battle/battle_command.c').read_text(),'Cotton descriptor must precede >=46 decode')
        source=simple.stage_source()+r'''
int main(void){
 for(int before=0;before<=12;before++)for(int simple=0;simple<2;simple++)for(int suppressed=0;suppressed<2;suppressed++){
  BattleContext c=fixture();c.moveNoCur=541;c.battlerIdAttacker=c.battlerIdStatChange=1;
  c.battleMons[1].ability=simple?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].moveEffectFlags=suppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].statChanges[STAT_DEF]=before;mutate(&c,150);
  int delta=3*(QOL_MODERN_BATTLE&&simple&&!suppressed?2:1);if(before+delta>12)delta=12-before;
  assert(c.battleMons[1].statChanges[STAT_DEF]==before+delta);
  if(delta)assert(c.buffMsg.id==(delta>=3?1276:delta==2?753:750));
  else assert(c.buffMsg.id==142);
  assert(!(c.statChangeFlag&QOL_STAT_CHANGE_COMPETITIVE_PENDING));
  // Losing Simple never retroactively changes stored stages.
  int saved=c.battleMons[1].statChanges[STAT_DEF];c.battleMons[1].ability=ABILITY_NONE;
  assert(c.battleMons[1].statChanges[STAT_DEF]==saved);
 }
 return 0;}
'''
        for battle in (0,1):
            self.compile_run(source,'-DQOL_MODERN_MOVES=1',f'-DQOL_MODERN_BATTLE={battle}','-Wno-unused-function')

    def test_pure_power_major_status_all_seven_stages_items_and_maximum(self):
        self.assertTrue('Qol_GetMoveBasePower(' in (ROOT/'src/battle/battle_util.c').read_text(),'conditional power helper missing')
        source=rules.COMMON+'#include "constants/qol_moves.h"\n'+r'''
typedef struct {struct {unsigned status;int status2,item,ability,moveEffectFlags,statChanges[8];} battleMons[4];} BattleContext;
'''+native('Qol_GetMoveBasePower')+r'''
int main(void){(void)BattleSystem_Random;
 const int statuses[]={0,STATUS_POISON,STATUS_BAD_POISON,STATUS_BURN,STATUS_SLEEP,STATUS_PARALYSIS,STATUS_FREEZE};
 for(int b=1;b<4;b+=2)for(int s=0;s<7;s++){
  BattleContext c={0};c.battleMons[b].status=statuses[s];c.battleMons[b].status2=~0u;BattleContext saved=c;
  assert(Qol_GetMoveBasePower(&c,477,0,b,65)==(QOL_MODERN_MOVES&&(s==1||s==2)?130:65));
  assert(Qol_GetMoveBasePower(&c,509,0,b,65)==(QOL_MODERN_MOVES&&s?130:65));
  assert(!memcmp(&c,&saved,sizeof(c)));
 }
 for(int stat=1;stat<=7;stat++)for(int level=0;level<=12;level++){
  BattleContext c={0};for(int s=1;s<=7;s++)c.battleMons[0].statChanges[s]=6;
  c.battleMons[0].statChanges[stat]=level;c.battleMons[0].ability=ABILITY_SIMPLE;
  int expected=QOL_MODERN_MOVES?20+20*(level>6?level-6:0):20;
  assert(Qol_GetMoveBasePower(&c,503,0,1,20)==expected);
  assert(Qol_GetMoveBasePower(&c,684,0,1,20)==expected);
 }
 BattleContext c={0};for(int s=1;s<=7;s++)c.battleMons[0].statChanges[s]=12;
 assert(Qol_GetMoveBasePower(&c,503,0,1,20)==(QOL_MODERN_MOVES?860:20));
 for(int item=0;item<3;item++){
  c.battleMons[0].item=item;c.battleMons[0].ability=ABILITY_KLUTZ;c.battleMons[0].moveEffectFlags=~0u;
  assert(Qol_GetMoveBasePower(&c,515,0,1,55)==(QOL_MODERN_MOVES&&!item?110:55));
 }
 assert(Qol_GetMoveBasePower(&c,MOVE_TACKLE,0,1,99)==99);
 return 0;}
'''
        for enabled in (0,1):
            self.compile_run(source,f'-DQOL_MODERN_MOVES={enabled}')

    def test_shared_damage_and_actual_ai_resolve_before_technician_and_honor_override(self):
        self.assertTrue('Qol_GetMoveBasePower(' in (ROOT/'src/battle/battle_util.c').read_text())
        source=snow.damage_source()
        source=source.replace(snow.native('Qol_IsSlicingMove','src/qol_moves.c'),'')
        definitions='\n#undef BATTLE_MOVE_DATA\n#undef Qol_IsSupportedMove\n'+''.join(moves.no_includes((ROOT/p).read_text()) for p in ('include/move.h','include/qol_moves.h','src/qol_moves.c'))+'\ntypedef MoveTbl Move;'
        source=source.replace('typedef struct {int power,type,category,effect,range;} Move;',definitions)
        source=source.replace('(Move){500,TYPE_NORMAL,CATEGORY_PHYSICAL,0,0}', '(Move){.power=100,.type=TYPE_NORMAL,.category=CATEGORY_PHYSICAL}')
        source=source.replace('int hp,ability,status,item,statChanges[8];','int hp,ability,status,item,statChanges[8],level,friendship,weight;')
        source=source.replace('int calcTemp;} trainerAIData;', 'int calcTemp,battlerIdTarget;} trainerAIData;')
        source=source.replace('int powerMultiplier,fieldCondition;', 'int powerMultiplier,fieldCondition,effectiveSpeed[4];unsigned fieldSideConditionFlags[2];')
        source+=r'''
#define MOVE_STATUS_IMMUNE (MOVE_STATUS_NO_EFFECT|MOVE_STATUS_LEVITATE_IMMUNE|MOVE_STATUS_WONDER_GUARD_IMMUNE|MOVE_STATUS_MAGNET_RISE_IMMUNE)
static const u16 sWeightToPower[][2]={{0xFFFF,0xFFFF}};
enum {WEIGHT_TO_POWER_WEIGHT,WEIGHT_TO_POWER_POWER};
static int TrainerAI_MoveType(BattleSystem *s,BattleContext *c,int b,int move){return TYPE_NORMAL;}
static int BattleSystem_ApplyTypeEffectiveness(BattleSystem *s,BattleContext *c,int m,int type,int a,int d,int damage,u32 *flags){return damage;}
'''+native('DamageDivide')+native('TrainerAI_CalcDamage','src/battle/trainer_ai.c')+r'''
static void check(BattleContext *c,int move,int power){
 int saved=rngCalls;int expected=CalcMoveDamage(NULL,c,move,0,0,power,0,0,1,1);
 assert(CalcMoveDamage(NULL,c,move,0,0,0,0,0,1,1)==expected);
 c->trainerAIData.battlerIdTarget=1;u8 ivs[6]={0};
 assert(TrainerAI_CalcDamage(NULL,c,move,c->battleMons[0].item,ivs,0,c->battleMons[0].ability,0,100)==expected);
 assert(rngCalls==saved);
}
int main(void){
 for(int poison=0;poison<3;poison++)for(int tech=0;tech<2;tech++){
  BattleContext c=fixture();c.battleMons[0].ability=tech?ABILITY_TECHNICIAN:ABILITY_NONE;
  c.battleMons[1].status=poison==1?STATUS_POISON:poison==2?STATUS_BAD_POISON:0;
  check(&c,477,poison?130:65);check(&c,509,poison?130:65);
  c.battleMons[1].status=STATUS_BURN;check(&c,509,130);check(&c,477,65);
 }
 for(int item=0;item<2;item++)for(int tech=0;tech<2;tech++){
  BattleContext c=fixture();c.battleMons[0].item=item?ITEM_POTION:ITEM_NONE;
  c.battleMons[0].ability=tech?ABILITY_TECHNICIAN:ABILITY_KLUTZ;
  check(&c,515,item?55:110);
  int resolved=item?(tech?82:55):110;
  // Exact odd-power integer truncation: Technician 55 -> 82.
  c.battleMons[0].ability=ABILITY_NONE;
  int expected=CalcMoveDamage(NULL,&c,515,0,0,resolved,0,0,1,1);
  c.battleMons[0].ability=tech?ABILITY_TECHNICIAN:ABILITY_KLUTZ;
  assert(CalcMoveDamage(NULL,&c,515,0,0,0,0,0,1,1)==expected);
 }
 for(int sum=0;sum<=4;sum++)for(int simple=0;simple<2;simple++){
  BattleContext c=fixture();for(int stat=1;stat<=7;stat++)c.battleMons[0].statChanges[stat]=6;
  c.battleMons[0].statChanges[STAT_ACC]=6+sum;
  c.battleMons[0].statChanges[STAT_EVASION]=4; // negatives never cancel boosts
  c.battleMons[0].ability=simple?ABILITY_SIMPLE:ABILITY_TECHNICIAN;
  c.battleMons[1].ability=ABILITY_UNAWARE;
  check(&c,503,20+20*sum);check(&c,684,20+20*sum);
  int power=20+20*sum,resolved=!simple&&power<=60?power*15/10:power;
  c.battleMons[0].ability=ABILITY_NONE;
  int expected=CalcMoveDamage(NULL,&c,503,0,0,resolved,0,0,1,1);
  c.battleMons[0].ability=simple?ABILITY_SIMPLE:ABILITY_TECHNICIAN;
  assert(CalcMoveDamage(NULL,&c,503,0,0,0,0,0,1,1)==expected);
 }
 BattleContext c=fixture();for(int s=1;s<=7;s++)c.battleMons[0].statChanges[s]=12;
 check(&c,503,860);check(&c,684,860);
 // Resolved-power eligibility survives modifiers crossing the threshold.
 // Moves-only keeps sequential floors. Modern battle applies one BP group;
 // intrinsic55 with Technician+HH becomes124 instead of123.
 const int cases[][7]={
  // move, raw item, Stored Power boosts, HH, Charge, supplied power, final power
  {515,ITEM_POTION,0,1,0,0,123}, // intrinsic55 -> HH82 -> Technician123
  {515,ITEM_NONE,0,1,0,0,165},   // intrinsic110 -> HH165, ineligible
  {503,ITEM_NONE,2,1,0,0,135},   // intrinsic60 -> HH90 -> Technician135
  {503,ITEM_NONE,3,1,0,0,120},   // intrinsic80 -> HH120, ineligible
  {MOVE_TACKLE,ITEM_NONE,0,0,1,0,120}, // intrinsic40 -> Charge80 -> Technician120
  {515,ITEM_NONE,0,1,0,60,135},  // supplied60 is already resolved and qualifies
  {515,ITEM_NONE,0,1,0,80,120},  // supplied80 is already resolved and ineligible
 };
 for(unsigned k=0;k<NELEMS(cases);k++){
  c=fixture();for(int stat=1;stat<=7;stat++)c.battleMons[0].statChanges[stat]=6;
  int move=cases[k][0];c.battleMons[0].ability=ABILITY_TECHNICIAN;c.battleMons[0].item=cases[k][1];
  c.battleMons[0].statChanges[STAT_ACC]=6+cases[k][2];c.turnData[0].helpingHandFlag=cases[k][3];
  if(cases[k][4]){c.battleMons[0].moveEffectFlags=MOVE_EFFECT_FLAG_CHARGE;
   c.trainerAIData.moveData[MOVE_TACKLE].power=40;c.trainerAIData.moveData[MOVE_TACKLE].type=TYPE_ELECTRIC;}
  int rngBefore=rngCalls;int actual=CalcMoveDamage(NULL,&c,move,0,0,cases[k][5],0,0,1,1);
  // Unmodified explicit final power supplies an independent numeric oracle.
  BattleContext plain=c;plain.battleMons[0].ability=ABILITY_NONE;plain.turnData[0].helpingHandFlag=0;
  plain.battleMons[0].moveEffectFlags&=~MOVE_EFFECT_FLAG_CHARGE;
  int finalPower=QOL_MODERN_BATTLE&&k==0?124:cases[k][6];
  int expected=CalcMoveDamage(NULL,&plain,move,0,0,finalPower,0,0,1,1);
  assert(actual==expected);
  if(!cases[k][5]){
   c.trainerAIData.battlerIdTarget=1;u8 ivs[6]={0};
   assert(TrainerAI_CalcDamage(NULL,&c,move,c.battleMons[0].item,ivs,0,ABILITY_TECHNICIAN,0,100)==expected);
  }
  assert(rngCalls==rngBefore);
 }
 // Native conditional effects use ctx->powerMultiplier for intrinsic power.
 // Pursuit153 and Revenge use20; this synthetic Payback20 is fallback
 // arithmetic only. Real Payback writes explicit power (D2a1 producer test).
 const int conditional[][3]={{MOVE_PURSUIT,40,80},{MOVE_PAYBACK,50,100},{MOVE_REVENGE,60,120}};
 for(unsigned k=0;k<NELEMS(conditional);k++){
  c=fixture();c.powerMultiplier=20;c.battleMons[0].ability=ABILITY_TECHNICIAN;
  int move=conditional[k][0];c.trainerAIData.moveData[move].power=conditional[k][1];
  int multiplied=CalcMoveDamage(NULL,&c,move,0,0,0,0,0,1,1);
  c.powerMultiplier=10;c.battleMons[0].ability=ABILITY_NONE;
  assert(multiplied==CalcMoveDamage(NULL,&c,move,0,0,conditional[k][2],0,0,1,1));
 }
 // A caller-supplied power is already resolved; no poisoning or no-item doubling.
 c.battleMons[1].status=STATUS_POISON;
 assert(CalcMoveDamage(NULL,&c,477,0,0,65,0,0,1,1)!=CalcMoveDamage(NULL,&c,477,0,0,0,0,0,1,1));
 return 0;}
'''
        for battle in (0,1):
            self.compile_run(source,'-DQOL_MODERN_MOVES=1',f'-DQOL_MODERN_BATTLE={battle}','-Wno-unused-function','-Wno-sign-compare')

    def test_overlay_reproducible_counts_and_no_capacity_increase(self):
        import learnset_import
        profile=json.loads((ROOT/'.local-tools/validation/gen9-import-profile.json').read_text())
        text=learnset_import.generate(profile)
        rows=[tuple(map(int,r)) for r in re.findall(r'QOL_LEVEL_UP_MOVE\((\d+), (\d+), (\d+)\)',text)]
        self.assertEqual(len(rows),336)
        self.assertEqual(len({s for s,l,m in rows}),237)
        self.assertEqual(max(Counter(s for s,l,m in rows).values()),5)
        self.assertEqual(Counter(m for s,l,m in rows if m in IDS),Counter(dict(zip([r[0] for r in ROWS],[9,10,8,5,13,5,5,8,0,12,17,6,3,8]))))
        self.assertEqual((ROOT/'include/data/qol_learnsets.inc').read_text(),text)
        self.assertIn('QOL_LEVEL_UP_ADDITIONS_MAX 5',(ROOT/'include/qol_learnsets.h').read_text())
        legacy=unpack_narc((ROOT/'files/poketool/personal/wotbl.narc').read_bytes())[0]
        largest=0
        for s in range(1,494):
            packed=struct.unpack('<'+'H'*(len(legacy[s])//2),legacy[s])
            packed=packed[:packed.index(65535)]
            merged={(v>>9,v&511) for v in packed}|{(l,m) for mon,l,m in rows if mon==s}
            largest=max(largest,len(merged));self.assertLessEqual(len(merged)+1,28)
        self.assertEqual(largest,22)


class Next14SourceTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('next14_scripts'),'guarded A14 effect/subscript generator missing')
        import next14_scripts
        return next14_scripts

    def test_append_contract_reservations_guards_and_unchanged_prefixes(self):
        module=self.module()
        effects=unpack_narc((ROOT/'files/battledata/script/effect_script.narc').read_bytes())[0]
        subs=unpack_narc((ROOT/'files/battledata/script/subscript.narc').read_bytes())[0]
        def compile_source(source,root=ROOT):
            # This resource test isolates archive composition. The SDK/VM class
            # below independently compiles all generated command sources.
            if source==(ROOT/module.STATUS_EFFECT_SOURCE).read_text():return effects[10]
            if source==(ROOT/module.SELF_EFFECT_SOURCE).read_text():return effects[138]
            if source==(ROOT/module.MULTI_SOURCE).read_text():return subs[150]
            return hashlib.sha256(source.encode()).digest()
        with patch.object(module,'compile_battle_script',side_effect=compile_source):
            for battle in (False,True):
                initial=subs+([b'cursed',b'competitive'] if battle else [])
                archive=pack_narc(initial);result,names=unpack_narc(module.modern_move_stat_resources(archive,battle))
                self.assertEqual(len(result),304)
                self.assertEqual(result[:len(initial)],initial)
                self.assertEqual(names,unpack_narc(archive)[1])
                if not battle:self.assertEqual(result[297:299],[struct.pack('<I',224)]*2)
                with self.assertRaises(ValueError):module.modern_move_stat_resources(pack_narc(result),battle)
                with self.assertRaises(ValueError):module.modern_move_stat_resources(pack_narc(initial[:-1]),battle)
            result,names=unpack_narc(module.modern_move_effect_resources(pack_narc(effects)))
            self.assertEqual(len(result),284);self.assertEqual(result[:277],effects)
            self.assertEqual(names,unpack_narc(pack_narc(effects))[1])
            with self.assertRaises(ValueError):module.modern_move_effect_resources(pack_narc(result))
        for member,path in ((277,module.STATUS_EFFECT_SOURCE),(283,module.SELF_EFFECT_SOURCE)):
            raw=(ROOT/path).read_text()
            for drift in (raw+'\n',raw.replace('ATTACKER','DEFENDER')):
                with self.assertRaisesRegex(ValueError,'expected source'):module.modern_move_effect_source(drift,member)
        raw=(ROOT/module.MULTI_SOURCE).read_text()
        with self.assertRaisesRegex(ValueError,'expected source'):module.modern_move_stat_source(raw+'\n',299)
        with patch.object(module,'compile_battle_script',return_value=b'wrong profile') as compiler:
            with self.assertRaisesRegex(ValueError,'unchanged.*match'):module.modern_move_effect_resources(pack_narc(effects))
        self.assertEqual(compiler.call_count,1)
        with patch.object(module,'compile_battle_script',return_value=b'wrong profile') as compiler:
            with self.assertRaisesRegex(ValueError,'unchanged.*match'):module.modern_move_stat_resources(pack_narc(subs),False)
        self.assertEqual(compiler.call_count,1)

    def test_flag_matrix_pipeline_runs_old_exact_299_transforms_before_appending(self):
        import modern_rom
        self.assertTrue(hasattr(modern_rom,'modern_move_stat_resources'),'ROM pipeline lacks A14 scripts')
        from contextlib import ExitStack
        paths={p:(0,0,3) for p in ('a/0/0/1','a/0/3/0','a/0/1/1','a/0/0/0','a/0/2/7')}
        transforms=('modern_battle_resources','modern_paralysis_resources','modern_weather_resources',
          'modern_absorption_resources','modern_sturdy_resources','modern_cursed_body_resources',
          'modern_competitive_resources','modern_oblivious_intimidate_resources','modern_simple_resources','modern_tailwind_resources',
          'modern_snow_effect_resources','modern_ability_description_resources','modern_simple_message_resources',
          'modern_snow_message_resources','modern_soul_dew_message_resources','modern_tailwind_message_resources','modern_drain_resources','modern_move_stat_resources','modern_move_effect_resources','modern_wind_rider_resources')
        for battle in (False,True):
            for enabled in (False,True):
                calls=[]
                with ExitStack() as stack:
                    stack.enter_context(patch('modern_rom.rom_files',return_value=paths))
                    stack.enter_context(patch('modern_rom.replace_rom_files',side_effect=lambda r,v:v))
                    stack.enter_context(patch('modern_rom.extended_move_resources',side_effect=lambda a,b,c,*rest:(a,b,c)))
                    for name in transforms:
                        def record(*args,name=name):calls.append((name,args));return args[0]
                        stack.enter_context(patch('modern_rom.'+name,side_effect=record))
                    modern_rom.make_modern_rom(b'rom',None,types=False,battle_rules=battle,moves=enabled)
                names=[n for n,args in calls]
                self.assertEqual(names.count('modern_simple_message_resources'),int(battle or enabled))
                self.assertEqual(names.count('modern_move_stat_resources'),int(enabled))
                self.assertEqual(names.count('modern_move_effect_resources'),int(enabled))
                self.assertEqual(names.count('modern_ability_description_resources'),int(battle))
                self.assertEqual(names.count('modern_snow_message_resources'),int(battle))
                self.assertEqual(names.count('modern_soul_dew_message_resources'),int(battle))
                if battle:self.assertLess(names.index('modern_snow_message_resources'),names.index('modern_soul_dew_message_resources'))
                if enabled:
                    self.assertEqual(next(args[1] for n,args in calls if n=='modern_move_stat_resources'),battle)
                if battle and enabled:
                    self.assertLess(names.index('modern_simple_resources'),names.index('modern_move_stat_resources'))
                    self.assertLess(names.index('modern_simple_message_resources'),names.index('modern_snow_message_resources'))

    def test_real_message_bank_matrix_and_full_names_preserve_encoded_templates(self):
        import modern_rom
        from contextlib import ExitStack
        original_messages=(ROOT/'files/msgdata/msg.narc').read_bytes()
        original_banks=unpack_narc(original_messages)[0]
        originals={
          'a/0/2/7':original_messages,
          'a/0/0/1':(ROOT/'files/battledata/script/subscript.narc').read_bytes(),
          'a/0/3/0':(ROOT/'files/battledata/script/effect_script.narc').read_bytes(),
          'a/0/1/1':(ROOT/'files/poketool/waza/waza_tbl.narc').read_bytes(),
          'a/0/0/0':(ROOT/'files/a/0/0/0').read_bytes()}
        rom=b'';paths={}
        for path,data in originals.items():paths[path]=(0,len(rom),len(rom)+len(data));rom+=data
        old_words,key=unpack_messages(original_banks[197]);triplets=None
        for battle in (False,True):
            for enabled in (False,True):
                with ExitStack() as stack:
                    stack.enter_context(patch('modern_rom.rom_files',return_value=paths))
                    stack.enter_context(patch('modern_rom.replace_rom_files',side_effect=lambda r,v:v))
                    # Message composition is real; SDK script composition is
                    # covered separately, so its toolchain is not needed here.
                    for name in ('modern_battle_resources','modern_paralysis_resources','modern_weather_resources',
                      'modern_absorption_resources','modern_sturdy_resources','modern_cursed_body_resources',
                      'modern_competitive_resources','modern_oblivious_intimidate_resources','modern_simple_resources','modern_tailwind_resources',
                      'modern_snow_effect_resources','modern_drain_resources','modern_move_effect_resources','modern_wind_rider_resources'):
                        stack.enter_context(patch('modern_rom.'+name,side_effect=lambda data,*args:data))
                    stack.enter_context(patch('modern_rom.modern_move_stat_resources',side_effect=lambda data,battle:data))
                    result=modern_rom.make_modern_rom(rom,ROOT/'charmap.txt',types=False,battle_rules=battle,moves=enabled)
                banks=unpack_narc(result.get('a/0/2/7',original_messages))[0]
                words,new_key=unpack_messages(banks[197]);self.assertEqual(new_key,key)
                self.assertEqual(len(words),1285 if battle or enabled else 1276)
                changed=[i for i,(a,b) in enumerate(zip(old_words,words)) if a!=b]
                self.assertEqual(changed,[701,702,703,810,811,812] if battle else [])
                if battle or enabled:
                    if triplets is None:triplets=words[1276:]
                    self.assertEqual(words[1276:],triplets)
                self.assertEqual(banks[722]==original_banks[722],not battle)
                self.assertEqual(len(banks),830 if enabled else 829)
                if enabled:
                    for bank in (750,751):
                        names=unpack_messages(banks[bank])[0];self.assertEqual(len(names),899)
                        self.assertEqual(names[:468],unpack_messages(original_banks[bank])[0])
                    self.assertEqual(len(unpack_narc(result['a/0/0/0'])[0]),899)
                    self.assertEqual(len(unpack_narc(result['a/0/1/1'])[0]),899)

    def test_script_owner_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('next14_scripts'),'guarded A14 effect/subscript generator missing')


class Next14SdkTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    @classmethod
    def setUpClass(cls):
        import next14_scripts as module
        from battle_scripts import battle_script_tools,compile_battle_script
        try:tool_paths=battle_script_tools()
        except FileNotFoundError as error:raise unittest.SkipTest(str(error))
        # Cache only test SDK assembly, with complete macro/constants/tool
        # fingerprints and output hashes. Native C/VM assertions run every time.
        fingerprint=hashlib.sha256()
        dependencies=[ROOT/'tools/qol/battle_scripts.py',ROOT/'asm/macros/btlcmd.inc',ROOT/'files/msgdata/msg/msg_0197.h']
        dependencies+=sorted((ROOT/'include/constants').rglob('*.h'))
        dependencies += [Path(p) for p in tool_paths if Path(p).is_file()]
        for dependency in dependencies:
            fingerprint.update(str(dependency).encode());fingerprint.update(dependency.read_bytes())
        profile=fingerprint.digest()
        cache=ROOT/'.local-tools/validation/next14-sdk-cache';cache.mkdir(parents=True,exist_ok=True)
        def compile_source(source,root=ROOT):
            key=hashlib.sha256(profile+source.encode()).hexdigest();path=cache/(key+'.json')
            if path.exists():
                record=json.loads(path.read_text());binary=bytes.fromhex(record['binary'])
                if record['sha256']==hashlib.sha256(binary).hexdigest():return binary
            binary=compile_battle_script(source,root)
            path.write_text(json.dumps({'binary':binary.hex(),'sha256':hashlib.sha256(binary).hexdigest()}))
            return binary
        cls.original=unpack_narc((ROOT/'files/battledata/script/subscript.narc').read_bytes())[0]
        cls.effects=unpack_narc((ROOT/'files/battledata/script/effect_script.narc').read_bytes())[0]
        with patch.object(module,'compile_battle_script',side_effect=compile_source):
            cls.stat_members=unpack_narc(module.modern_move_stat_resources(pack_narc(cls.original),False))[0]
            cls.effect_members=unpack_narc(module.modern_move_effect_resources(pack_narc(cls.effects)))[0]
        # A14 Acid Spray uses unchanged native271. Verify its source too.
        cls.acid=compile_source((ROOT/'files/battledata/script/effect_script/effect_script_0271.s').read_text())
        cls.central=compile_source((ROOT/'files/battledata/script/subscript/subscript_0012_UpdateStatStage.s').read_text())
        from competitive_scripts import COMPETITIVE_SOURCE
        cls.competitive=compile_source(COMPETITIVE_SOURCE)

    def source(self):
        harness=simple.SimpleSdkTests()
        harness.original=self.original
        harness.scripts={i:self.stat_members[i] for i in (12,76,129,146,299,300,301,302,303)}
        harness.scripts.update({1000+i:self.effect_members[i] for i in range(277,284)})
        harness.scripts[1271]=self.acid
        harness.scripts[298]=self.competitive
        source=harness.source()
        source=source.replace('BattleMon battleMons[4];','BattleMon battleMons[4];\n struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;')
        source=source.replace('sideEffectFlagsDirect,sideEffectFlagsIndirect,', 'sideEffectFlagsDirect,sideEffectFlagsIndirect,sideEffectFlagsAbility,')
        source=source.replace('movePower,flingScript,','movePower,moveTemp,flingScript,')
        source=source.replace('V(BSCRIPT_VAR_SIDE_EFFECT_TYPE,statChangeType);', 'V(BSCRIPT_VAR_MSG_ATTACKER,battlerIdMsgAttacker);V(BSCRIPT_VAR_MSG_MOVE_TEMP,moveTemp);V(BSCRIPT_VAR_MOVE_NO_CUR,moveNoCur);V(BSCRIPT_VAR_SIDE_EFFECT_TYPE,statChangeType);')
        source=source.replace('static int moveMissed;', 'static int moveMissed,statCalls,statParams[20],snapshots[20][8],announcements,moveAnimations,statAnimations;')
        source=source.replace('stopDepth=entryDepth-1;count=0;', 'stopDepth=entryDepth-1;count=0;statCalls=announcements=moveAnimations=statAnimations=0;')
        source=source.replace('case 14:case 16:case 17:case 38:c->scriptSeqNo++;break;',
          'case 17:if(!(c->battleStatus&BATTLE_STATUS_NO_ATTACK_MESSAGE))announcements++;c->scriptSeqNo++;break;\n  case 14:case 15:case 16:case 38:c->scriptSeqNo++;break;')
        source=source.replace('case 23:case 208:c->scriptSeqNo+=2;break;',
          'case 23:if(!(c->battleStatus&BATTLE_STATUS_MOVE_ANIMATIONS_OFF))moveAnimations++;c->scriptSeqNo+=2;break;\n  case 208:c->scriptSeqNo+=2;break;')
        source=source.replace('case 31:case 69:case 71:c->scriptSeqNo+=3;break;',
          'case 31:c->scriptSeqNo+=3;break;\n  case 69:case 71:statAnimations++;c->scriptSeqNo+=3;break;')
        source=source.replace('case 51:BtlCmd_ChangeStatStage(&system,c);break;',
          'case 51:assert(statCalls<20);statParams[statCalls]=c->statChangeParam;BtlCmd_ChangeStatStage(&system,c);memcpy(snapshots[statCalls++],c->battleMons[c->battlerIdStatChange].statChanges,sizeof(snapshots[0]));break;')
        old='else if(c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLE_SUBSCRIPT_HIT_SUBSTITUTE||c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLE_SUBSCRIPT_ATTACK_MESSAGE_AND_ANIMATION)c->scriptSeqNo+=2;'
        new='else if(c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLE_SUBSCRIPT_HIT_SUBSTITUTE)c->scriptSeqNo+=2;\n   else if(c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLE_SUBSCRIPT_ATTACK_MESSAGE_AND_ANIMATION)BtlCmd_Call(&system,c);'
        self.assertIn(old,source);source=source.replace(old,new)
        descriptor=re.search(r'static const int sMoveStatusChangeScripts\[.*?\n\};',(ROOT/'src/battle/battle_util.c').read_text(),re.S)[0]
        source+='\n'+descriptor+'\n'+native('GetMoveStatusChangeScript')+native('BattlerCheckSubstitute')
        # The fixture RNG is explicit; native indirect command owns the timing.
        source+='static int randomCalls,roll;\nstatic int BattleSystem_Random(BattleSystem *s){randomCalls++;return roll;}\n'
        source+=native('BattleSystem_TryDirectSideEffect')+native('BattleSystem_TryIndirectSideEffect')
        return source

    def variants(self,checks):
        for battle in (0,1):
            self.compile_run(self.source()+checks,'-DQOL_MODERN_MOVES=1',f'-DQOL_MODERN_BATTLE={battle}',
              '-Wno-unused-function','-Wno-unused-variable','-Wno-misleading-indentation','-Wno-sign-compare')

    def test_all_compiled_appends_native_prefixes_and_reserved_end_members(self):
        self.assertEqual(len(self.stat_members),304);self.assertEqual(len(self.effect_members),284)
        self.assertEqual(self.stat_members[:297],self.original)
        self.assertEqual(self.effect_members[:277],self.effects)
        self.assertEqual(self.stat_members[297:299],[struct.pack('<I',224)]*2)
        self.assertEqual(self.acid,self.effects[271]);self.assertEqual(self.central,self.original[12])
        # Seven native effects each dispatch exactly the admitted descriptor.
        for effect in range(277,283):
            words=struct.unpack('<5I',self.effect_members[effect])
            self.assertEqual(words,(50,7,2,(1<<30)|(145+effect-277),224))
        old=struct.unpack('<7I',self.effects[138]);new=struct.unpack('<7I',self.effect_members[283])
        self.assertEqual(new,(*old[:3],(1<<30)|17,*old[4:]))

    def test_multi_actual_central_events_caps_partials_simple_suppression_snatch_and_stack(self):
        self.variants(r'''
static const int stats[5][5]={{1,6},{4,5,3},{1,2,6},{1,4},{2,5,1,4,3}};
static const int deltas[5][5]={{1,1},{1,1,1},{1,1,1},{1,1},{-1,-1,2,2,2}};
static const int sizes[]={2,3,3,2,5};
static const int moves[]={471,486,492,529,507};
int main(void){
 for(int move=0;move<5;move++)for(int capmask=0;capmask<(1<<sizes[move]);capmask++)
 for(int simple=0;simple<2;simple++)for(int suppressed=0;suppressed<2;suppressed++)for(int snatch=0;snatch<2;snatch++)for(int depth=0;depth<=3;depth++){
  BattleContext c=fixture();int b=snatch?2:0;c.battlerIdAttacker=c.battlerIdStatChange=b;c.moveNoCur=moves[move];
  c.battleMons[b].ability=simple?ABILITY_SIMPLE:ABILITY_NONE;c.battleMons[b].hp=100;
  c.battleMons[b].moveEffectFlags=suppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int expected[8];for(int s=0;s<8;s++)expected[s]=6;
  for(int k=0;k<sizes[move];k++){
   int stat=stats[move][k],delta=deltas[move][k];
   int before=(capmask&(1<<k))?(delta>0?12:0):(delta>0?11:6);
   expected[stat]=before;c.battleMons[b].statChanges[stat]=before;
  }
  frames(&c,depth);c.battleStatus=c.battleStatus2=0;run(&c,299+move);
  int calls=0;
  for(int k=0;k<sizes[move];k++){
   int stat=stats[move][k],delta=deltas[move][k]*(QOL_MODERN_BATTLE&&simple&&!suppressed?2:1);
   if(capmask&(1<<k))continue;
   int after=expected[stat]+delta;if(after>12)after=12;if(after<0)after=0;
   int actual=after-expected[stat];expected[stat]=after;
   assert(snapshots[calls][stat]==after);
   assert(events[calls]==(actual>0?(actual>=3?1276:actual==2?753:750):(actual<=-3?1279:actual==-2?765:762)));
   assert(parameters[calls][0]==100+b&&parameters[calls][1]==stat);calls++;
  }
  for(int stat=1;stat<=7;stat++)assert(c.battleMons[b].statChanges[stat]==expected[stat]);
  assert(announcements==1&&moveAnimations==!!calls&&statCalls==calls);
  assert(statAnimations==!!calls&&peakDepth<=4);
  assert(!(c.battleStatus2&(BATTLE_STATUS2_UPDATE_STAT_STAGES|BATTLE_STATUS2_STAT_STAGE_CHANGE_SHOWN)));
  assert(!(c.statChangeFlag&QOL_STAT_CHANGE_COMPETITIVE_PENDING));
  if(!calls){assert(c.moveStatusFlag&MOVE_STATUS_NO_MORE_WORK);assert(count==1&&events[0]==(move==4?796:768));}
  else assert(!c.moveStatusFlag);
 }
 return 0;}
''')

    def test_shell_drop_first_self_immunity_competitive_and_white_herb_after_sequence(self):
        # Execute the actual White Herb selection branch, without stubbing its
        # stage reset. The surrounding item cases are irrelevant to this item.
        item=native('TryUseHeldItem')
        branch=item[item.index('        case HOLD_EFFECT_STATDOWN_RESTORE:'):item.index('        case HOLD_EFFECT_HEAL_INFATUATION:')]
        checks='static int herb(BattleContext *ctx,int battlerId){int ret=0,script=0;switch(HOLD_EFFECT_STATDOWN_RESTORE){\n'+branch+'\n}return script;}\n'
        checks+=r'''
int main(void){
 const int abilities[]={ABILITY_COMPETITIVE,ABILITY_CLEAR_BODY,ABILITY_WHITE_SMOKE,ABILITY_SHIELD_DUST,ABILITY_SIMPLE};
 for(int k=0;k<5;k++){
  BattleContext c=fixture();c.battlerIdAttacker=c.battlerIdStatChange=0;c.moveNoCur=507;c.battleMons[0].ability=abilities[k];
  c.battleMons[0].item=ITEM_WHITE_HERB;c.battleStatus=c.battleStatus2=0;run(&c,303);
  assert(statCalls==5&&statParams[0]==23&&statParams[1]==26&&statParams[2]==39&&statParams[3]==42&&statParams[4]==41);
  int factor=QOL_MODERN_BATTLE&&k==4?2:1;
  assert(snapshots[0][STAT_DEF]==6-factor&&snapshots[0][STAT_SPDEF]==6);
  assert(snapshots[1][STAT_DEF]==6-factor&&snapshots[1][STAT_SPDEF]==6-factor);
  assert(snapshots[1][STAT_ATK]==6&&snapshots[1][STAT_SPATK]==6&&snapshots[1][STAT_SPEED]==6);
  assert(c.battleMons[0].statChanges[STAT_ATK]==6+2*factor&&c.battleMons[0].statChanges[STAT_SPATK]==6+2*factor&&c.battleMons[0].statChanges[STAT_SPEED]==6+2*factor);
  assert(c.battleMons[0].item==ITEM_WHITE_HERB&&!(c.statChangeFlag&QOL_STAT_CHANGE_COMPETITIVE_PENDING));
  assert(herb(&c,0)==BATTLE_SUBSCRIPT_HELD_ITEM_STATDOWN_RESTORE);
  assert(c.battleMons[0].statChanges[STAT_DEF]==6&&c.battleMons[0].statChanges[STAT_SPDEF]==6);
  assert(c.battleMons[0].statChanges[STAT_ATK]==6+2*factor);
 }
 return 0;}
'''
        self.variants(checks)

    def test_effect_dispatch_acid_immunities_competitive_selfboost_sub_ko_and_failures(self):
        self.variants(r'''
int main(void){
 // Native Snatch146 changes the attacker before the effect selects its recipient.
 for(int effect=277;effect<=282;effect++){
  BattleContext c=fixture();c.moveNoCur=471;c.battlerIdAttacker=0;c.battlerIdTarget=0;c.battlerIdTemp=2;
  run(&c,146);assert(c.battlerIdAttacker==2&&c.battlerIdTarget==0);
  c.battleMons[2].hp=100;run(&c,1000+effect);int script=0;
  assert(BattleSystem_TryDirectSideEffect(NULL,&c,&script));assert(c.battlerIdStatChange==2);
 }
 for(int effect=277;effect<=282;effect++){
  BattleContext c=fixture();c.battleMons[0].hp=100;c.moveNoCur=471;run(&c,1000+effect);
  int script=0;assert(BattleSystem_TryDirectSideEffect(NULL,&c,&script));
  assert(script==(effect==282?12:299+effect-277));assert(c.battlerIdStatChange==0);
  assert(c.statChangeParam==145+effect-277);
 }
 const int failures[]={0,MOVE_STATUS_MISSED,MOVE_STATUS_PROTECTED,MOVE_STATUS_NO_EFFECT,MOVE_STATUS_FAILED};
 for(int move=0;move<2;move++)for(int ko=0;ko<2;ko++)for(int sub=0;sub<2;sub++)
 for(int failed=0;failed<5;failed++)for(int simple=0;simple<3;simple++)for(int grace=0;grace<2;grace++){
  BattleContext c=fixture();c.battlerIdAttacker=0;c.battlerIdTarget=1;c.moveNoCur=move?888:491;c.battleMons[1].hp=ko?0:100;
  c.selfTurnData[1].statusFlags=sub?8:0;c.battleMons[1].status2=sub?STATUS2_SUBSTITUTE:0;
  c.battleMons[1].ability=ABILITY_SHIELD_DUST;c.battleMons[0].ability=grace?ABILITY_SERENE_GRACE:simple?ABILITY_SIMPLE:ABILITY_SHIELD_DUST;
  c.battleMons[0].moveEffectFlags=simple==2?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.moveStatusFlag=failures[failed];run(&c,1283);int script=0;randomCalls=0;roll=99;
  int applied=BattleSystem_TryIndirectSideEffect(NULL,&c,&script);assert(applied==!failed&&randomCalls==1);
  if(applied){assert(script==12&&c.battlerIdStatChange==0);c.battleStatus=c.battleStatus2=0;run(&c,script);
   assert(c.battleMons[0].statChanges[STAT_SPEED]==6+(QOL_MODERN_BATTLE&&!grace&&simple==1?2:1));}
 }
 const int abilities[]={ABILITY_NONE,ABILITY_SHIELD_DUST,ABILITY_CLEAR_BODY,ABILITY_WHITE_SMOKE,ABILITY_COMPETITIVE};
 for(int a=0;a<5;a++)for(int sub=0;sub<2;sub++)for(int mold=0;mold<2;mold++){
  BattleContext c=fixture();c.moveNoCur=494;c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
  c.battleMons[1].ability=abilities[a];c.battleMons[1].status2=sub?STATUS2_SUBSTITUTE:0;c.selfTurnData[1].statusFlags=sub?8:0;
  run(&c,1271);int script=0;roll=0;int dispatched=BattleSystem_TryIndirectSideEffect(NULL,&c,&script);
  assert(dispatched==!sub);
  if(dispatched){assert(script==12);c.battleStatus=c.battleStatus2=0;run(&c,script);}
  int applied=!sub&&(a==0||a==4||mold);
  assert(c.battleMons[1].statChanges[STAT_SPDEF]==6-2*applied);
  // End12 consumes Competitive pending only after an actual opponent drop.
  assert(c.battleMons[1].statChanges[STAT_SPATK]==6+(QOL_MODERN_BATTLE&&a==4&&applied?2:0));
  assert(!(c.statChangeFlag&QOL_STAT_CHANGE_COMPETITIVE_PENDING));
 }
 return 0;}
''')

if __name__=='__main__':unittest.main()
