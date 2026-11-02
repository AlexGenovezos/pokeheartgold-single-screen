"""Tailwind's fourth turn uses actual C and guarded original resources."""
from contextlib import ExitStack
from pathlib import Path
import hashlib
import importlib.util
import itertools
import os
import re
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import test_game_logic as game
import test_modern_rules as rules

ROOT = Path(__file__).resolve().parents[2]
CHARMAP = ROOT / 'charmap.txt'
PLAYER = 'src/battle/battle_controller_player.c'
COMMAND = 'src/battle/battle_command.c'
UTIL = 'src/battle/battle_util.c'
AI = 'src/battle/trainer_ai.c'
TEXT = 'The user whips up a\nturbulent whirlwind\nthat ups the Speed\nof all party Pokémon\nfor four turns.'


def native(name, path=UTIL):
    return game.function_source(path, name) + '\n'


def timer_helpers():
    return '#if QOL_MODERN_BATTLE\n' + ''.join(rules.helper(name, PLAYER) for name in
        ('Qol_GetTailwindTurns', 'Qol_SetTailwindTurns')) + '#endif\n'


def residual_source():
    # Retain the real case body, including the iterator and yield/resume logic.
    text = (ROOT / PLAYER).read_text()
    start = text.index('static void BattleControllerPlayer_UpdateFieldCondition(BattleSystem *battleSystem, BattleContext *ctx) {')
    actual = text[start:text.index('\nstatic ', start + 1)]
    case = actual[actual.index('        case UFC_STATE_TAILWIND:'):actual.index('        case UFC_STATE_LUCKY_CHANT:')]
    declaration = '#if QOL_MODERN_BATTLE\nu8 tailwindTurns;\n#endif\n' if 'u8 tailwindTurns;' in actual else ''
    return rules.COMMON + r'''
enum { UFC_STATE_TAILWIND, UFC_STATE_LUCKY_CHANT, NARC_a_0_0_1 };
typedef struct {u32 fieldSideConditionFlags[2];int fieldConditionUpdateData,stateFieldConditionUpdate;
 int command,commandNext,battlerIdTemp;} BattleContext;
static int ends[2],scheduledSnatch;
static void ReadBattleScriptFromNarc(BattleContext *ctx,int narc,int script){
 if(script==146){scheduledSnatch++;return;}assert(script==233);ends[ctx->fieldConditionUpdateData]++;
}
static int BattleSystem_GetFirstBattlerOnSide(BattleSystem *s,BattleContext *c,int side){return side;}
''' + timer_helpers() + 'static void residual(BattleSystem *battleSystem,BattleContext *ctx){int side,flag=0;\n' + declaration + 'switch(ctx->stateFieldConditionUpdate){\n' + case + r'''
 default:break;
}}
static void tick(BattleContext *c){
 c->stateFieldConditionUpdate=UFC_STATE_TAILWIND;c->fieldConditionUpdateData=0;
 do{residual(NULL,c);}while(c->stateFieldConditionUpdate==UFC_STATE_TAILWIND);
}
'''


def speed_source():
    damage=native('TrainerAI_CalcDamage',AI)
    gyro=damage[damage.index('    case MOVE_GYRO_BALL:'):]
    gyro=gyro[:gyro.index('        break;')+len('        break;')]
    gyro='static int gyro(BattleContext *ctx,int attacker){int move=MOVE_GYRO_BALL,power=0,type=0;switch(move){'+gyro+'}assert(type==TYPE_NORMAL);return power;}\n'
    return rules.COMMON+r'''
typedef struct {int priority;} Move;
typedef struct {int hp,maxHp,speed,statChanges[8],item,species,ability,status;
 struct {int slowStartTurns,knockOffFlag,quickClawFlag,custapBerryFlag;} moveEffectData;} Mon;
typedef struct {Mon battleMons[4];u32 fieldCondition,fieldSideConditionFlags[2],effectiveSpeed[4];
 int totalTurns,quickClawRandom[4],movePos[4];struct {int inputSelection;} playerActions[4];
 struct {int struggleFlag;} turnData[4];
 struct {Move moveData[NUM_MOVES+1];int calcTemp,battlerIdAttacker,battlerIdTarget;} trainerAIData;
 const int *aiWords;int aiPos;} BattleContext;
static int maxBattlers;
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return maxBattlers;}
static int GetBattlerAbility(BattleContext *c,int b){return c->battleMons[b].ability;}
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return 0;}
static int GetHeldItemModifier(BattleContext *c,int b,int f){return 1;}
static int GetItemVar(BattleContext *c,int i,int f){return 0;}
static int GetBattlerVar(BattleContext *c,int b,int f,void *p){return MOVE_TACKLE;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int CheckAbilityActive(BattleSystem *s,BattleContext *c,int scope,int b,int ability){return 0;}
static void AIScript_IncrementCursor(BattleContext *c,int n){c->aiPos+=n;}
static int AIScript_Read(BattleContext *c){return c->aiWords[c->aiPos++];}
static int AIScript_Battler(BattleContext *c,int b){return b;}
'''+rules.array('sSpeedHalvingItemEffects')+rules.array('sStatChangeTable')+native('CheckSortSpeed')+''.join(native(name,AI) for name in
 ('AICmd_IfSideCondition','AICmd_IfNotSideCondition','AICmd_IfSpeedCompareEqualTo','AICmd_IfSpeedCompareNotEqualTo','AICmd_LoadBattlerSpeedOrderPosition'))+gyro


def context_types():
    header=(ROOT/'include/battle/battle.h').read_text()
    move=(ROOT/'include/move.h').read_text()
    return ('\n'.join(line for line in (ROOT/'include/constants/global.h').read_text().splitlines()
                         if line.startswith(('#define PLAYER_NAME_LENGTH ', '#define POKEMON_NAME_LENGTH ')))+'\n'
            'typedef int NarcId;typedef struct ItemData ItemData;\n'
            +move[move.index('typedef struct MoveTbl {'):move.index('} MoveTbl;')+len('} MoveTbl;')]+'\n'
            +header[header.index('typedef struct BattleMessage {'):header.index('} BattleContext;')+len('} BattleContext;')]+'\n')


def command_source():
    source=rules.COMMON.replace('typedef int BattleSystem;',r'''
typedef struct {int battleType,battleOutcomeFlag,battleSpecial,safariBallCnt,regulationFlag,maxBattlers,linkVersionMismatch;} BattleSystem;
''')+context_types()+r'''
#include <stdlib.h>
#include "constants/opcode.h"
#include "constants/battle_script.h"
#include "constants/message_tags.h"
enum {NARC_a_0_0_1};
static int messages,animations,lastMessage,poisonType;
// Historical duration/alias fixtures have no Wind holder. Wind tests separately
// execute the real registry, allocator, cast->304 dispatcher and complete VM.
static void Qol_QueueTailwindStart(BattleSystem *s,BattleContext *c,int side){
 for(int b=0;b<4;b++)assert(c->battleMons[b].ability!=ABILITY_WIND_RIDER);
}
static void Qol_WindEventsNew(BattleContext *c){}
static void Qol_WindEventsDelete(BattleContext *c){}
static void Qol_WindEventsReset(BattleContext *c){}

static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){
 if(side==BATTLER_CATEGORY_ATTACKER)return c->battlerIdAttacker;
 if(side==BATTLER_CATEGORY_DEFENDER)return c->battlerIdTarget;
 if(side==BATTLER_CATEGORY_SWITCHED_MON)return c->battlerIdSwitch;
 return side&3;
}
static int MaskOfFlagNo(int bit){return 1u<<bit;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static void TrainerAIData_ClearMoves(BattleContext *c,int b){}
static void TrainerAIData_ClearAbility(BattleContext *c,int b){}
static void TrainerAIData_ClearHeldItem(BattleContext *c,int b){}
static void UnlockBattlerOutOfCurrentMove(BattleSystem *s,BattleContext *c,int b){}
static void MIi_CpuClearFast(int val,u32 *p,size_t size){memset(p,val,size);}
static void BattleScriptGotoSubscript(BattleContext *c,int narc,int script){}
static int GetBattlerVar(BattleContext *c,int b,int f,void *p){return poisonType?TYPE_POISON:TYPE_NORMAL;}
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return 0;}
static int GetHeldItemModifier(BattleContext *c,int b,int field){return 0;}
static int GetMonsHitCount(BattleSystem *s,BattleContext *c,int a,int b){return 1;}
'''
    # Message IDs are generated from the original GMM; only their integer values
    # are SDK edges in these host command fixtures.
    ids={int(i) for name in ('BtlCmd_TryLightScreen','BtlCmd_TryReflect','BtlCmd_TrySafeguard')
         for i in re.findall(r'msg_0197_(\d+)',native(name,COMMAND))}
    source+=''.join(f'#define msg_0197_{i:05} {i}\n' for i in sorted(ids))
    source+=''.join(native(name,COMMAND) for name in ('BattleScriptReadWord','BattleScriptIncrementPointer',
        'BattleScriptGetVarPointer','BtlCmd_CompareVarToValue','BtlCmd_UpdateVar','BtlCmd_UpdateVar2',
        'BtlCmd_CheckSideCondition','BtlCmd_TryToxicSpikes','BtlCmd_CheckToxicSpikes','BtlCmd_TrySpikes',
        'BtlCmd_RapidSpin','BtlCmd_TryBreakScreens','BtlCmd_TryReflect','BtlCmd_TryLightScreen','BtlCmd_TryMist',
        'BtlCmd_TrySafeguard','BtlCmd_Transform'))
    source+=''.join(native(name) for name in ('BattleContext_Get','BattleContext_Set','BattleContext_Init',
        'BattleContext_ResetTurnData','InitSwitchWork','InitFaintedWork'))
    return source+r'''
static void load(BattleContext *c,const u32 *words,int count){
 assert(count<=400);memcpy(c->battleScriptBuffer,words,count*sizeof(u32));c->scriptSeqNo=0;
}
static void run(BattleContext *c,const u32 *words,int count){
 load(c,words,count);
 for(int steps=0;steps<1000;steps++){
  assert(c->scriptSeqNo>=0&&c->scriptSeqNo<count);int op=c->battleScriptBuffer[c->scriptSeqNo];
  switch(op){
   case 17:c->scriptSeqNo++;break;
   case 23:c->scriptSeqNo+=2;break;
   case 32:BtlCmd_CompareVarToValue(NULL,c);break;
   case 50:BtlCmd_UpdateVar(NULL,c);break;
   case 57:BtlCmd_UpdateVar2(NULL,c);break;
   case 155:BtlCmd_CheckSideCondition(NULL,c);break;
   case 60:assert(c->battleScriptBuffer[c->scriptSeqNo+1]==76||c->battleScriptBuffer[c->scriptSeqNo+1]==172||c->battleScriptBuffer[c->scriptSeqNo+1]==12);
    if(c->battleScriptBuffer[c->scriptSeqNo+1]==76)animations++;
    c->scriptSeqNo+=2;break;
   case 18:lastMessage=c->battleScriptBuffer[c->scriptSeqNo+1];messages++;
    c->scriptSeqNo+=3+((c->battleScriptBuffer[c->scriptSeqNo+2]==9||c->battleScriptBuffer[c->scriptSeqNo+2]==10)?2:1);break;
   case 14:c->scriptSeqNo++;break;
   case 30:c->scriptSeqNo+=2;break;
   case 59:c->scriptSeqNo+=2+c->battleScriptBuffer[c->scriptSeqNo+1];break;
   case 224:return;
   default:fprintf(stderr,"unexpected opcode %d at %d\n",op,c->scriptSeqNo);abort();
  }
 }assert(0);
}
'''


def script_words(member):
    from nitro_data import unpack_narc
    members=unpack_narc((ROOT/'files/battledata/script/subscript.narc').read_bytes())[0]
    return members[member]


def c_array(name,data):
    words=struct.unpack('<'+'I'*(len(data)//4),data)
    return f'static const u32 {name}[]={{'+','.join(str(word)+'u' for word in words)+'};\n'


class TailwindNativeTests(unittest.TestCase):
    def compile_run(self, source, *flags):
        if os.environ.get('TAILWIND_SANITIZE') == '1':
            flags += ('-fsanitize=address,undefined','-fno-omit-frame-pointer')
        game.GameLogicTests.compile_run(self,source,*flags)

    def variants(self, source, *extra):
        for types,battle,moves in itertools.product((0,1),repeat=3):
            with self.subTest(types=types,battle=battle,moves=moves):
                self.compile_run(source,f'-DQOL_MODERN_TYPES={types}',f'-DQOL_MODERN_BATTLE={battle}',
                                 f'-DQOL_MODERN_MOVES={moves}','-Wno-unused-function',*extra)

    def test_successful_cast_counts_four_ticks_in_modern_mode(self):
        source=(ROOT/'files/battledata/script/subscript/subscript_0160_TailwindStart.s').read_text()
        if importlib.util.find_spec('tailwind_resources'):
            from tailwind_resources import modern_tailwind_source
            source=modern_tailwind_source(source)
        start=0xb00 if 'SIDE_CONDITION_TAILWIND | QOL_TAILWIND_FOURTH_TURN' in source else 0x300
        self.variants(residual_source()+f'\n#define MODERN_START {start}\n'+r'''
int main(void){BattleContext c={0};int count=0;
 c.fieldSideConditionFlags[0]=QOL_MODERN_BATTLE?MODERN_START:0x300;
 do{tick(&c);count++;}while(c.fieldSideConditionFlags[0]&0x300);
 if(count!=(QOL_MODERN_BATTLE?4:3)){fprintf(stderr,"duration: actual %d expected %d\n",count,QOL_MODERN_BATTLE?4:3);return 1;}
 assert(ends[0]==1);return 0;}
''')

    def test_modern_four_residuals_and_legacy_three(self):
        # Before implementation this compiles and fails numerically: the real
        # subtraction changes B00 to A00 instead of canonical three turns 300.
        self.variants(residual_source()+r'''
int main(void){
 BattleContext c={0};const u32 modern[]={0x300,0x200,0x100,0};
 const u32 legacy[]={0x200,0x100,0};int turns=QOL_MODERN_BATTLE?4:3;
 const u32 *expected=QOL_MODERN_BATTLE?modern:legacy;
 c.fieldSideConditionFlags[0]=QOL_MODERN_BATTLE?0xb00:0x300;
 for(int turn=0;turn<turns;turn++){
  tick(&c);if(c.fieldSideConditionFlags[0]!=expected[turn]){
   fprintf(stderr,"turn %d: actual %x expected %x\n",turn+1,c.fieldSideConditionFlags[0],expected[turn]);return 1;}
  assert(ends[0]==(turn==turns-1));assert(ends[1]==0);
 }
 tick(&c);assert(ends[0]==1);assert(ends[1]==0);return 0;
}
''')

    def test_every_storage_pattern_setter_range_and_other_flag_combination(self):
        self.variants(residual_source()+r'''
int main(void){
 const int positions[]={0,1,2,3,4,5,6,7,10,12,13,14};
 const u32 canonical[]={0,0x100,0x200,0x300,0xb00};
 for(unsigned pattern=0;pattern<4096;pattern++){
  u32 outside=0;
  for(int bit=0;bit<12;bit++)if(pattern&(1u<<bit))outside|=1u<<positions[bit];
  for(unsigned storage=0;storage<8;storage++){
   u32 flags=outside|((storage&3)<<8)|((storage&4)<<9);
#if QOL_MODERN_BATTLE
   int turns=(storage&3)?(storage&4?4:storage&3):0;
   assert(Qol_GetTailwindTurns(flags)==turns);
   for(unsigned set=0;set<256;set++){
    u32 updated=Qol_SetTailwindTurns(flags,(u8)set);
    assert(updated==(outside|canonical[set>4?4:set]));
    assert((updated&~0xb00u)==outside);
   }
   BattleContext c={0};c.fieldSideConditionFlags[0]=flags;ends[0]=ends[1]=0;
   tick(&c);assert(c.fieldSideConditionFlags[0]==(outside|canonical[turns?turns-1:0]));
   assert(ends[0]==(turns==1));
#else
   (void)canonical;BattleContext c={0};c.fieldSideConditionFlags[0]=flags;ends[0]=ends[1]=0;
   tick(&c);assert((c.fieldSideConditionFlags[0]&~0x300u)==(flags&~0x300u));
#endif
  }
 }
#if QOL_MODERN_BATTLE
 for(int bit=15;bit<=32;bit++){
  u32 outside=bit==32?0xffff8000u:1u<<bit;
  for(unsigned storage=0;storage<8;storage++)for(unsigned set=0;set<256;set++){
   u32 flags=outside|((storage&3)<<8)|((storage&4)<<9);
   assert(Qol_SetTailwindTurns(flags,(u8)set)==(outside|canonical[set>4?4:set]));
   if(set==0){BattleContext c={0};int turns=(storage&3)?(storage&4?4:storage&3):0;
    c.fieldSideConditionFlags[0]=flags;tick(&c);
    assert(c.fieldSideConditionFlags[0]==(outside|canonical[turns?turns-1:0]));}
  }
 }
#endif
 return 0;}
''')

    def test_staggered_sides_orphan_normalization_and_resume(self):
        self.variants(residual_source()+r'''
int main(void){BattleContext c={0};int duration=QOL_MODERN_BATTLE?4:3;
 c.fieldSideConditionFlags[0]=QOL_MODERN_BATTLE?0xb00:0x300;
 tick(&c);c.fieldSideConditionFlags[1]=QOL_MODERN_BATTLE?0xb00:0x300;
 for(int i=1;i<duration;i++)tick(&c);
 assert(ends[0]==1&&ends[1]==0);assert(c.fieldSideConditionFlags[1]==0x100);
 tick(&c);assert(ends[0]==1&&ends[1]==1);
 // Both sides expire together, with the actual iterator advancing before yield.
 c=(BattleContext){0};c.fieldSideConditionFlags[0]=c.fieldSideConditionFlags[1]=0x100;
 c.stateFieldConditionUpdate=UFC_STATE_TAILWIND;ends[0]=ends[1]=0;
 residual(NULL,&c);assert(c.fieldConditionUpdateData==1);assert(ends[0]==1&&ends[1]==0);
 assert(c.command==CONTROLLER_COMMAND_RUN_SCRIPT&&c.commandNext==0&&c.battlerIdTemp==0);
 residual(NULL,&c);assert(c.fieldConditionUpdateData==2);assert(ends[0]==1&&ends[1]==1);
 residual(NULL,&c);assert(c.stateFieldConditionUpdate==UFC_STATE_LUCKY_CHANT);
 assert(ends[0]==1&&ends[1]==1);
#if QOL_MODERN_BATTLE
 for(int malformed=0x800;malformed<=0xa00;malformed+=0x100){
  c=(BattleContext){0};c.fieldSideConditionFlags[0]=malformed;ends[0]=ends[1]=0;tick(&c);
  assert(c.fieldSideConditionFlags[0]==(malformed==0x800?0:0x300));assert(ends[0]==0);
 }
#endif
 return 0;}
''')

    def test_speed_both_operands_singles_doubles_presence_ai_and_trick_room(self):
        self.variants(speed_source()+r'''
int main(void){
 const u32 states[]={0,0x100,0x200,0x300,0x800,0x900,0xa00,0xb00,0x400};
 for(maxBattlers=2;maxBattlers<=4;maxBattlers+=2)
 for(int b=0;b<maxBattlers;b++)for(int state=0;state<9;state++)for(int side=0;side<2;side++)
 for(int status=0;status<3;status++)for(int trick=0;trick<2;trick++){
  BattleContext c={0};for(int i=0;i<4;i++){
   c.battleMons[i].hp=c.battleMons[i].maxHp=100;c.battleMons[i].statChanges[3]=6;
   c.battleMons[i].speed=(i&1)?150:100;
  }
  c.fieldSideConditionFlags[side]=states[state];c.fieldCondition=trick?FIELD_CONDITION_TRICK_ROOM:0;
  c.battleMons[b].status=status?STATUS_PARALYSIS:0;c.battleMons[b].ability=status==2?ABILITY_QUICK_FEET:ABILITY_NONE;
  int target=b^1;
  int speeds[2]={c.battleMons[b].speed,c.battleMons[target].speed};
  if(status==2)speeds[0]=speeds[0]*3/2;else if(status)speeds[0]/=QOL_MODERN_BATTLE?2:4;
  if((b&1)==side&&(states[state]&0x300))speeds[0]*=2;
  if((target&1)==side&&(states[state]&0x300))speeds[1]*=2;
  // Avoid tied fixtures; the tie path intentionally calls RNG in production.
  if(speeds[0]==speeds[1])continue;
  rngCalls=0;int expected=trick?(speeds[0]>speeds[1]):(speeds[0]<speeds[1]);
  assert(CheckSortSpeed(NULL,&c,b,target,TRUE)==expected);
  assert(c.effectiveSpeed[b]==(unsigned)speeds[0]&&c.effectiveSpeed[target]==(unsigned)speeds[1]);
  assert(CheckSortSpeed(NULL,&c,target,b,TRUE)==!expected);assert(rngCalls==0);
  // AI comparison commands route through the same actual speed calculation.
  c.trainerAIData.battlerIdAttacker=b;c.trainerAIData.battlerIdTarget=target;
  int power=1+25*speeds[1]/speeds[0];assert(gyro(&c,b)==(power>150?150:power));
  int compare[]={0,expected,17};c.aiWords=compare;c.aiPos=0;
  AICmd_IfSpeedCompareEqualTo(NULL,&c);assert(c.aiPos==20);
  c.aiPos=0;AICmd_IfSpeedCompareNotEqualTo(NULL,&c);assert(c.aiPos==3);
  int presence[]={0,b,0x300,17};c.aiWords=presence;c.aiPos=0;
  u32 old[2]={c.fieldSideConditionFlags[0],c.fieldSideConditionFlags[1]};
  int present=(old[b&1]&0x300)!=0;AICmd_IfSideCondition(NULL,&c);assert(c.aiPos==(present?21:4));
  c.aiPos=0;AICmd_IfNotSideCondition(NULL,&c);assert(c.aiPos==(present?4:21));
  assert(c.fieldSideConditionFlags[0]==old[0]&&c.fieldSideConditionFlags[1]==old[1]);assert(rngCalls==0);
 }
 // Speed-order loading covers all battlers with distinct speeds and no RNG.
 for(maxBattlers=2;maxBattlers<=4;maxBattlers+=2)for(int side=0;side<2;side++)for(int state=0;state<9;state++){
  BattleContext c={0};for(int i=0;i<4;i++){
   c.battleMons[i].hp=100;c.battleMons[i].statChanges[3]=6;c.battleMons[i].speed=100+17*i;
  }c.fieldSideConditionFlags[side]=states[state];rngCalls=0;
  for(int b=0;b<maxBattlers;b++){
   int words[]={0,b};c.aiWords=words;c.aiPos=0;AICmd_LoadBattlerSpeedOrderPosition(NULL,&c);
   int own=(100+17*b)*(((b&1)==side&&(states[state]&0x300))?2:1),position=0;
   for(int i=0;i<maxBattlers;i++){
    int speed=(100+17*i)*(((i&1)==side&&(states[state]&0x300))?2:1);position+=speed>own;
   }assert(c.trainerAIData.calcTemp==position);
  }assert(rngCalls==0);
 }
 return 0;}
''','-Wno-sign-compare')


    def test_actual_side_aliases_hazard_screen_and_script_mutations_preserve_timer(self):
        arrays=c_array('lucky',script_words(164))+c_array('defog',script_words(171))
        self.variants(command_source()+arrays+r'''
int main(void){const int chant[]={0,1,5,7};
 for(int b=0;b<4;b++)for(unsigned storage=0;storage<8;storage++)for(int tox=0;tox<3;tox++)for(int l=0;l<4;l++){
  BattleContext c={0};c.battlerIdAttacker=c.battlerIdTarget=c.battlerIdStatChange=c.battlerIdSwitch=b;
  int side=b&1;u32 timer=((storage&3)<<8)|((storage&4)<<9);
  u32 flags=timer|(tox?0x400:0)|(chant[l]<<12)|0xff;
  c.fieldSideConditionFlags[side]=flags;c.fieldSideConditionFlags[side^1]=0xb00;
  c.fieldSideConditionData[side].toxicSpikesLayers=tox;c.fieldSideConditionData[side].spikesLayers=3;
  // Full-word script aliases, immediate and from-variable updates.
  for(int alias=11;alias<=13;alias++){
   assert(*(u32 *)BattleScriptGetVarPointer(NULL,&c,alias)==flags);
   u32 compare[]={32,4,(u32)alias,0x300,17};load(&c,compare,5);BtlCmd_CompareVarToValue(NULL,&c);
   assert(c.scriptSeqNo==((timer&0x300)?22:5));
   u32 update[]={50,10,(u32)alias,1};load(&c,update,4);BtlCmd_UpdateVar(NULL,&c);
   assert((c.fieldSideConditionFlags[side]&0xb00)==timer);
   u32 copy[]={57,10,(u32)alias,9};c.calcTemp=0x5000;load(&c,copy,4);BtlCmd_UpdateVar2(NULL,&c);
   assert((c.fieldSideConditionFlags[side]&0xb00)==timer);c.fieldSideConditionFlags[side]=flags;
  }
  assert((u32)BattleContext_Get(NULL,&c,0,b)==flags);
  BattleContext_Set(NULL,&c,0,b,(int)(flags|0x40));assert(c.fieldSideConditionFlags[side]==(flags|0x40));
  u32 check[]={155,1,2,0,0};for(unsigned flag=0;flag<6;flag++){
   check[3]=flag;load(&c,check,5);BtlCmd_CheckSideCondition(NULL,&c);
   assert((c.fieldSideConditionFlags[side]&0xb00)==timer);
  }
  c.fieldSideConditionFlags[side]=flags;run(&c,lucky,sizeof(lucky)/4);
  assert((c.fieldSideConditionFlags[side]&0xb00)==timer);
  c.fieldSideConditionFlags[side]=flags;run(&c,defog,sizeof(defog)/4);
  assert((c.fieldSideConditionFlags[side]&0xb00)==timer);
  u32 noargs[]={0,0,0};
  c.fieldSideConditionFlags[side]=flags;load(&c,noargs,3);BtlCmd_TryBreakScreens(NULL,&c);
  assert((c.fieldSideConditionFlags[side]&0xb00)==timer);
  c.fieldSideConditionData[side].toxicSpikesLayers=tox;
  c.fieldSideConditionData[side].spikesLayers=3;c.fieldSideConditionFlags[side]=flags;
  for(int spin=0;spin<4;spin++){load(&c,noargs,3);BtlCmd_RapidSpin(NULL,&c);assert((c.fieldSideConditionFlags[side]&0xb00)==timer);}
  c.fieldSideConditionData[side].toxicSpikesLayers=tox;c.fieldSideConditionFlags[side]=flags;
  poisonType=1;u32 poison[]={0,1,0};load(&c,poison,3);BtlCmd_CheckToxicSpikes(NULL,&c);
  assert((c.fieldSideConditionFlags[side]&0xb00)==timer);assert(c.fieldSideConditionData[side].toxicSpikesLayers==0);
  c.fieldSideConditionFlags[side]=timer;load(&c,noargs,3);BtlCmd_TryReflect(NULL,&c);
  load(&c,noargs,3);BtlCmd_TryLightScreen(NULL,&c);load(&c,noargs,3);BtlCmd_TryMist(NULL,&c);
  load(&c,noargs,3);BtlCmd_TrySafeguard(NULL,&c);assert((c.fieldSideConditionFlags[side]&0xb00)==timer);
  // Setting hazards targets the other side and leaves its timer independent.
  c.fieldSideConditionData[side^1].toxicSpikesLayers=tox;load(&c,noargs,3);BtlCmd_TryToxicSpikes(NULL,&c);
  load(&c,noargs,3);BtlCmd_TrySpikes(NULL,&c);assert((c.fieldSideConditionFlags[side^1]&0xb00)==0xb00);
 }
 return 0;}
''','-Wno-sign-compare','-Wno-unused-but-set-variable')

    def test_actual_snatch_selection_and_script_resolve_the_casting_side(self):
        residual=('enum {UFC_STATE_TAILWIND,UFC_STATE_LUCKY_CHANT};\nstatic int ends[2],scheduledSnatch;'
                  +residual_source().split('static int ends[2],scheduledSnatch;',1)[1])
        source=command_source()+residual+'static void CheckIgnorePressure(BattleContext *c,int a,int b){}\n'
        # The original signed 1<<31 macro predates Tailwind. Normalize that
        # constant's type only in this fixture, preserving its ARM flag bits;
        # leave the extracted Snatch/controller code and all sanitizers intact.
        source+='#undef MOVE_STATUS_NO_MORE_WORK\n#define MOVE_STATUS_NO_MORE_WORK (1u << 31)\n'
        source+=native('BattleControllerPlayer_CheckMagicCoat',PLAYER)
        source+=c_array('snatch',script_words(146))+c_array('cast',script_words(160))
        self.variants(source+r'''
int main(void){assert(MOVE_STATUS_NO_MORE_WORK==0x80000000u);for(int b=0;b<4;b++){
 BattleContext c={0};for(int i=0;i<4;i++){c.turnOrder[i]=i;c.battleMons[i].hp=100;}
 c.battlerIdAttacker=b^1;c.battlerIdTarget=b^1;c.moveNoCur=MOVE_TAILWIND;
 c.turnData[b].snatchFlag=1;c.trainerAIData.moveData[MOVE_TAILWIND].flags=8;scheduledSnatch=0;
 assert(BattleControllerPlayer_CheckMagicCoat(NULL,&c));assert(scheduledSnatch==1);
 assert(c.battlerIdTemp==b&&c.turnData[b].snatchFlag==0);
 run(&c,snatch,sizeof(snatch)/4);assert(c.battlerIdAttacker==b&&c.battlerIdTarget==(b^1));
 run(&c,cast,sizeof(cast)/4);assert(c.fieldSideConditionFlags[b&1]==0x300);
 assert(c.fieldSideConditionFlags[(b&1)^1]==0);
 }return 0;}
''','-Wno-sign-compare','-Wno-unused-but-set-variable')

    def test_actual_context_init_reset_switch_faint_transform_copy_and_allocation(self):
        allocator=r'''
enum {HEAP_ID_BATTLE};static int freed;
static void *Heap_Alloc(int heap,size_t size){void *p=malloc(size);memset(p,0xff,size);return p;}
static void Heap_Free(void *p){freed++;free(p);}
static void BattleContext_InitBattleStart(BattleSystem *s,BattleContext *c){}
static void BattleControllerPlayer_InitTrainerAIData(BattleSystem *s,BattleContext *c){}
static void LoadMoveTbl(MoveTbl *m){}
static ItemData *LoadAllItemData(int heap){return malloc(4);}
'''+native('BattleContext_New',PLAYER)+native('BattleContext_Delete',PLAYER)
        # Preserve the actual Guard Spec whole-word read/OR/write statements.
        item=(ROOT/'src/battle/battle_system.c').read_text()
        start=item.index('    if (GetItemAttr(item, ITEMATTR_GUARD_SPEC, HEAP_ID_BATTLE)) {')
        end=item.index('    if (GetItemAttr(item, ITEMATTR_ATK_STAGES, HEAP_ID_BATTLE)) {',start)
        guard='static int GetItemAttr(int item,int attr,int heap){return 1;}\n'
        guard+='static int guard_spec(BattleSystem *battleSystem,BattleContext *ctx,int battlerId){int data,item=0,ret=FALSE;\n'+item[start:end]+'return ret;}\n'
        self.variants(command_source()+allocator+guard+r'''
int main(void){
 BattleContext *c=BattleContext_New(NULL);assert(c->fieldSideConditionFlags[0]==0&&c->fieldSideConditionFlags[1]==0);
 for(int b=0;b<4;b++)for(int baton=0;baton<2;baton++){
  c->fieldSideConditionFlags[0]=0xfbu<<4;c->fieldSideConditionFlags[1]=0x8700;
  u32 first=c->fieldSideConditionFlags[0],second=c->fieldSideConditionFlags[1];
  c->battleStatus=baton?BATTLE_STATUS_BATON_PASS:0;
  BattleContext_Init(c);BattleContext_ResetTurnData(NULL,c);
  assert(c->fieldSideConditionFlags[0]==first&&c->fieldSideConditionFlags[1]==second);
  InitSwitchWork(NULL,c,b);InitFaintedWork(NULL,c,b);
  assert(c->fieldSideConditionFlags[0]==first&&c->fieldSideConditionFlags[1]==second);
  c->battlerIdAttacker=b;c->battlerIdTarget=b^1;c->scriptSeqNo=0;
  BtlCmd_Transform(NULL,c);assert(c->fieldSideConditionFlags[0]==first&&c->fieldSideConditionFlags[1]==second);
  BattleContext copy=*c;memset(c->fieldSideConditionFlags,0,sizeof(c->fieldSideConditionFlags));*c=copy;
  assert(c->fieldSideConditionFlags[0]==first&&c->fieldSideConditionFlags[1]==second);
  guard_spec(NULL,c,b);assert((c->fieldSideConditionFlags[b&1]&0xb00)==((b&1?second:first)&0xb00));
 }
 BattleContext_Delete(c);assert(freed==2);c=BattleContext_New(NULL);
 assert(c->fieldSideConditionFlags[0]==0&&c->fieldSideConditionFlags[1]==0);BattleContext_Delete(c);assert(freed==4);
 return 0;}
''','-Wno-sign-compare','-Wno-unused-but-set-variable')


    def test_battle_off_preprocessed_controller_matches_accepted_baseline(self):
        baseline='b385edc340e6ba7fbeeda29a9216d69c20a107fa'
        def accepted(path):
            return subprocess.run(['git','show',baseline+':'+path],cwd=ROOT,check=True,capture_output=True,text=True).stdout
        def preprocess(source,types,moves):
            source=re.sub(r'^#include[^\n]*','',source,flags=re.M)
            result=subprocess.run([os.environ.get('CC','cc'),'-E','-P','-x','c','-DQOL_MODERN_BATTLE=0',
                f'-DQOL_MODERN_TYPES={types}',f'-DQOL_MODERN_MOVES={moves}','-'],input=source,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            return re.findall(r'\w+|[^\s\w]',result.stdout)
        original=accepted(PLAYER);current=(ROOT/PLAYER).read_text()
        for types,moves in itertools.product((0,1),repeat=2):
            self.assertEqual(preprocess(current,types,moves),preprocess(original,types,moves))
        # Wind owns guarded changes in util/commands. Compare all battle-off
        # tokens under every other flag, retaining exact native ABI/AI guards.
        for path in (UTIL,COMMAND):
            for types,moves in itertools.product((0,1),repeat=2):
                self.assertEqual(preprocess((ROOT/path).read_text(),types,moves),preprocess(accepted(path),types,moves),path)
        for path in (AI,'include/battle/battle.h','asm/trainer_ai_data.s'):
            self.assertEqual((ROOT/path).read_text(),accepted(path),path+' unexpectedly changed')
        old=accepted('include/constants/battle.h');new=(ROOT/'include/constants/battle.h').read_text()
        olddefines=re.findall(r'^#define SIDE_CONDITION_.*$',old,re.M)
        self.assertEqual(re.findall(r'^#define SIDE_CONDITION_.*$',new,re.M),olddefines)

    def test_helpers_c89_and_arm_target_context_layout(self):
        declarations=r'''
#include "constants/battle.h"
#include "constants/moves.h"
#include "constants/pokemon.h"
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;
typedef signed short s16;typedef unsigned int u32;typedef int s32;
'''
        controller=(ROOT/PLAYER).read_text()
        start=controller.index('// Keep the public 0x300 presence mask')
        end=controller.index('\n#endif',start)
        helpers=controller[start:end]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'check.c';path.write_text(declarations+helpers+'\nint main(void){return Qol_GetTailwindTurns(Qol_SetTailwindTurns(0,4))!=4;}\n')
            result=subprocess.run([os.environ.get('CC','cc'),'-std=c89','-Werror','-Wno-comment',
                '-iquote',str(ROOT/'include'),str(path),'-o',str(Path(folder)/'check')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(subprocess.run([str(Path(folder)/'check')]).returncode,0)
            # This compiles the actual complete declarations for an ARM target;
            # host pointer sizes are never used as evidence of the game ABI.
            path.write_text(declarations+context_types()+r'''
typedef char ArmPointerWidth[(sizeof(void *)==4)?1:-1];
typedef char SideWordsWidth[(sizeof(((BattleContext *)0)->fieldSideConditionFlags)==8)?1:-1];
typedef char SideWordsContiguous[(__builtin_offsetof(BattleContext,fieldSideConditionData)
 ==__builtin_offsetof(BattleContext,fieldSideConditionFlags)+8)?1:-1];
typedef char SideDataWidth[(sizeof(SideConditionData)==8)?1:-1];
typedef char MoveEffectWidth[(sizeof(MoveEffectData)==56)?1:-1];
''')
            result=subprocess.run([os.environ.get('CC','cc'),'-target','armv5te-none-eabi','-std=c99','-Werror',
                '-fsyntax-only','-iquote',str(ROOT/'include'),str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_raw_ai_operand_and_snow_word_remain_independent(self):
        source=(ROOT/'asm/trainer_ai_data.s').read_text()
        data=bytes(int(n,16) for n in re.findall(r'0x([0-9A-Fa-f]{2})',source.split('gTrainerAITable:\n',1)[1].split('\n\t.public',1)[0]))
        self.assertEqual(len(data),42428)
        words=struct.unpack('<'+'I'*(len(data)//4),data)
        self.assertEqual([i*4 for i,value in enumerate(words) if value==0x300],[7328])
        self.assertEqual(struct.unpack_from('<4I',data,7320),(15,1,0x300,0x2b0))
        from snow_resources import modern_snow_ai_source
        modern=modern_snow_ai_source(source)
        updated=bytes(int(n,16) for n in re.findall(r'0x([0-9A-Fa-f]{2})',modern.split('gTrainerAITable:\n',1)[1].split('\n\t.public',1)[0]))
        self.assertEqual(updated[7320:7336],data[7320:7336]);self.assertEqual(struct.unpack_from('<I',updated,5747*4)[0],0xffffffff)
        self.assertIn('ctx->effectiveSpeed[ctx->trainerAIData.battlerIdTarget] / ctx->effectiveSpeed[attacker]',native('TrainerAI_CalcDamage',AI))
        effect=(ROOT/'files/battledata/script/effect_script/effect_script_0225.s').read_text()
        self.assertIn('MOVE_SUBSCRIPT_PTR_TAILWIND_START',effect)
        table=re.search(r'static const int sMoveStatusChangeScripts\[[^]]+\] = \{(.*?)\n\};',(ROOT/UTIL).read_text(),re.S)[1]
        rows=re.findall(r'BATTLE_SUBSCRIPT_[A-Z0-9_]+',table)
        self.assertEqual(rows[121],'BATTLE_SUBSCRIPT_TAILWIND_START')



class TailwindResourceTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('tailwind_resources'),'Tailwind resource owner missing')
        import tailwind_resources
        return tailwind_resources

    def incoming(self):
        from simple_scripts import modern_simple_message_resources
        from snow_resources import modern_snow_message_resources
        from soul_dew_resources import modern_soul_dew_message_resources
        return modern_soul_dew_message_resources(modern_snow_message_resources(
            modern_simple_message_resources((ROOT/'files/msgdata/msg.narc').read_bytes(),CHARMAP),CHARMAP),CHARMAP)

    def test_supported_moves_learnsets_and_ability_gaps_stay_bounded(self):
        from move_resources import read_entries
        self.assertEqual(len(read_entries(ROOT/'include/data/qol_move_entries.inc')),72)
        rows=[tuple(map(int,row)) for row in re.findall(r'QOL_LEVEL_UP_MOVE\((\d+), (\d+), (\d+)\)',
            (ROOT/'include/data/qol_learnsets.inc').read_text())]
        self.assertEqual(len(rows),336);self.assertEqual(len({s for s,l,m in rows}),237)
        from ability_descriptions import modern_ability_description_resources
        from nitro_data import unpack_narc,unpack_messages
        from game_text import game_text
        banks=unpack_narc(modern_ability_description_resources((ROOT/'files/msgdata/msg.narc').read_bytes(),CHARMAP))[0]
        for bank in (720,721,722):
            words=unpack_messages(banks[bank])[0];self.assertEqual(len(words),243)
            self.assertEqual(words[240],game_text(' -',CHARMAP))
            self.assertNotEqual(words[241],game_text(' -',CHARMAP))
            self.assertNotEqual(words[242],game_text(' -',CHARMAP))

    def test_script_source_changes_only_success_operand_and_rejects_drift(self):
        module=self.module();source=(ROOT/module.SCRIPT_SOURCE).read_text()
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),'c8457cc7a3ae9e1d6bc291e70c96e6a58fdcec979abfb1ea64c2a95ef98662b7')
        modern=module.modern_tailwind_source(source)
        expected=source.replace('    UpdateVar OPCODE_FLAG_ON, BSCRIPT_VAR_SIDE_CONDITION_ATTACKER, SIDE_CONDITION_TAILWIND\n',
            '    UpdateVar OPCODE_FLAG_ON, BSCRIPT_VAR_SIDE_CONDITION_ATTACKER, SIDE_CONDITION_TAILWIND | QOL_TAILWIND_FOURTH_TURN\n')
        self.assertEqual(modern,expected)
        for drift in (source+'\n',modern,source.replace('_018','_019')):
            with self.assertRaisesRegex(ValueError,'expected source'):module.modern_tailwind_source(drift)

    def test_script_original_parity_precedes_compile_and_299_members(self):
        from nitro_data import pack_narc,unpack_narc
        module=self.module();source=(ROOT/module.SCRIPT_SOURCE).read_text()
        with patch.object(module,'compile_battle_script',return_value=b'bad') as compiler:
            with self.assertRaisesRegex(ValueError,'unchanged.*match'):module.modern_tailwind_script(b'original')
            compiler.assert_called_once_with(source,module.ROOT)
        with patch.object(module,'compile_battle_script',side_effect=[b'original',b'modern']) as compiler:
            self.assertEqual(module.modern_tailwind_script(b'original'),b'modern')
            self.assertEqual(compiler.call_args_list[1].args[0],module.modern_tailwind_source(source))
        members=[struct.pack('<I',i) for i in range(299)]
        before=pack_narc(members)
        with patch.object(module,'modern_tailwind_script',return_value=b'tailwind'):
            after,names=unpack_narc(module.modern_tailwind_resources(before))
        self.assertEqual(names,unpack_narc(before)[1]);self.assertEqual(after[:160],members[:160])
        self.assertEqual(after[161:],members[161:]);self.assertEqual(after[160],b'tailwind')
        for count in (0,160,297,298,300):
            with self.assertRaisesRegex(ValueError,'299'):module.modern_tailwind_resources(pack_narc((members+[b'last'])[:count]))

    def test_description_exact_row_only_names_keys_and_fit(self):
        from game_text import game_text
        from nitro_data import unpack_narc,unpack_messages
        module=self.module();incoming=self.incoming();before,names=unpack_narc(incoming)
        after,newnames=unpack_narc(module.modern_tailwind_message_resources(incoming,CHARMAP))
        self.assertEqual(names,newnames);self.assertEqual(len(before),len(after))
        self.assertEqual(before[:749],after[:749]);self.assertEqual(before[750:],after[750:])
        old,key=unpack_messages(before[749]);new,newkey=unpack_messages(after[749])
        self.assertEqual((len(new),key,newkey),(468,27800,27800))
        self.assertEqual({i for i in range(468) if old[i]!=new[i]},{366})
        self.assertEqual(new[366],game_text(TEXT,CHARMAP));self.assertEqual(new[258],old[258])
        font=(ROOT/'files/graphic/font/font_00000000.bin').read_bytes();offset=struct.unpack_from('<I',font,4)[0]
        widths=[sum(font[offset+glyph-1] for glyph in game_text(line,CHARMAP)[:-1]) for line in TEXT.splitlines()]
        self.assertEqual(widths,[103,102,102,109,83]);self.assertLessEqual(max(widths),149);self.assertLess(len(new[366]),128)
        self.assertIn('summary->buffer = String_New(128, HEAP_ID_19)',(ROOT/'src/pokemon_summary.c').read_text())
        self.assertIn('NARC_msg_msg_0749_bin',native('PokemonSummary_PrintMoveInfo','src/pokemon_summary_text.c'))

    def test_description_rejects_pre_snow_duplicate_extension_and_drift(self):
        from game_text import game_text
        from nitro_data import pack_narc,unpack_narc,pack_messages,unpack_messages
        module=self.module();incoming=self.incoming();banks,names=unpack_narc(incoming)
        for archive in ((ROOT/'files/msgdata/msg.narc').read_bytes(),pack_narc(banks[:749]),
                        module.modern_tailwind_message_resources(incoming,CHARMAP)):
            with self.assertRaises(ValueError):module.modern_tailwind_message_resources(archive,CHARMAP)
        original,key=unpack_messages(banks[749])
        for row in (0,258,366,467):
            words=[list(w) for w in original];words[row]=game_text('drift',CHARMAP)
            corrupt=list(banks);corrupt[749]=pack_messages(words,key)
            with self.subTest(row=row),self.assertRaisesRegex(ValueError,'post-Snow'):
                module.modern_tailwind_message_resources(pack_narc(corrupt,names),CHARMAP)
        for words,otherkey in ((original,key+1),(original[:-1],key),(original+original[:1],key),(original+[original[0]]*431,key)):
            corrupt=list(banks);corrupt[749]=pack_messages(words,otherkey)
            with self.assertRaises(ValueError):module.modern_tailwind_message_resources(pack_narc(corrupt,names),CHARMAP)
        read=Path.read_bytes
        def drift(path,*args,**kwargs):
            data=read(path,*args,**kwargs);return data+b'\n' if path.name=='msg_0749.gmm' else data
        with patch.object(Path,'read_bytes',drift),self.assertRaisesRegex(ValueError,'source'):
            module.modern_tailwind_message_resources(incoming,CHARMAP)
        # Extra unrelated banks are preserved; the owned bank must still be exact.
        banks.append(b'extra');result=unpack_narc(module.modern_tailwind_message_resources(pack_narc(banks,names),CHARMAP))[0]
        self.assertEqual(result[-1],b'extra')

    def test_all_eight_real_message_routes_and_owner_order(self):
        import modern_rom
        from game_text import game_text
        from nitro_data import unpack_narc,unpack_messages
        module=self.module()
        self.assertTrue(hasattr(modern_rom,'modern_tailwind_resources'),'Tailwind script routing missing')
        original=(ROOT/'files/msgdata/msg.narc').read_bytes()
        originals={'a/0/2/7':original,'a/0/1/1':(ROOT/'files/poketool/waza/waza_tbl.narc').read_bytes(),
                   'a/0/0/0':(ROOT/'files/a/0/0/0').read_bytes()}
        for path in ('a/0/0/8','a/0/6/8'):originals[path]=(ROOT/'files'/path).read_bytes()
        for path in ('a/0/0/1','a/0/3/0'):originals[path]=b'untouched'
        rom=b'';paths={}
        for path,data in originals.items():paths[path]=(0,len(rom),len(rom)+len(data));rom+=data
        scripts=('modern_battle_resources','modern_paralysis_resources','modern_weather_resources','modern_absorption_resources',
                 'modern_sturdy_resources','modern_cursed_body_resources','modern_competitive_resources',
                 'modern_oblivious_intimidate_resources','modern_simple_resources','modern_tailwind_resources',
                 'modern_snow_effect_resources','modern_drain_resources','modern_move_stat_resources','modern_move_effect_resources','modern_wind_rider_resources')
        owners=('modern_ability_description_resources','modern_simple_message_resources','modern_snow_message_resources',
                'modern_soul_dew_message_resources','modern_tailwind_message_resources','extended_move_resources')
        before=unpack_narc(original)[0]
        for types,battle,moves in itertools.product((False,True),repeat=3):
            calls=[]
            with self.subTest(types=types,battle=battle,moves=moves),ExitStack() as stack:
                stack.enter_context(patch('modern_rom.rom_files',return_value=paths))
                stack.enter_context(patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:replacements))
                for name in scripts:
                    def script(data,*args,name=name):calls.append(name);return data
                    stack.enter_context(patch('modern_rom.'+name,side_effect=script))
                for name in owners:
                    original_owner=getattr(modern_rom,name)
                    def owner(*args,name=name,original_owner=original_owner):calls.append(name);return original_owner(*args)
                    stack.enter_context(patch('modern_rom.'+name,side_effect=owner))
                result=modern_rom.make_modern_rom(rom,CHARMAP,types=types,battle_rules=battle,moves=moves)
            after,names=unpack_narc(result.get('a/0/2/7',original));self.assertEqual(names,unpack_narc(original)[1])
            self.assertEqual(unpack_messages(after[735])[0][9],game_text('FAIRY',CHARMAP) if types else unpack_messages(before[735])[0][9])
            words,key=unpack_messages(after[749]);self.assertEqual(key,27800)
            self.assertEqual(len(words),899 if moves else 468)
            self.assertEqual(words[366],game_text(TEXT,CHARMAP) if battle else unpack_messages(before[749])[0][366])
            self.assertEqual(len(unpack_messages(after[720])[0]),243 if battle else 124)
            self.assertEqual(calls.count('modern_tailwind_resources'),int(battle))
            self.assertEqual(calls.count('modern_tailwind_message_resources'),int(battle))
            for bank in (750,751):
                self.assertEqual(unpack_messages(after[bank])[0][:468],unpack_messages(before[bank])[0])
            if battle:
                order=[name for name in owners if name!='extended_move_resources' or moves]
                self.assertEqual([name for name in calls if name in owners],order)
                self.assertLess(calls.index('modern_simple_resources'),calls.index('modern_tailwind_resources'))
                from snow_resources import SNOW_TEXT
                from soul_dew_resources import SOUL_DEW_TEXT
                self.assertEqual(words[258],game_text(SNOW_TEXT[749][258],CHARMAP))
                self.assertEqual(unpack_messages(after[221])[0][225],game_text(SOUL_DEW_TEXT,CHARMAP))
            if moves:
                self.assertEqual(len(after),830);self.assertTrue(unpack_messages(after[829])[0][577])


class TailwindSdkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import battle_scripts
        import tailwind_resources
        from nitro_data import unpack_narc
        try:
            battle_scripts.battle_script_tools()
        except FileNotFoundError as error:
            raise unittest.SkipTest(str(error))
        cls.archive=(ROOT/'files/battledata/script/subscript.narc').read_bytes()
        cls.members,cls.names=unpack_narc(cls.archive)
        cls.original=cls.members[160]
        source=(ROOT/tailwind_resources.SCRIPT_SOURCE).read_text()
        cls.unchanged=battle_scripts.compile_battle_script(source)
        cls.modern=tailwind_resources.modern_tailwind_script(cls.original)

    def test_original_sdk_parity_and_exactly_one_or_operand_word_changes(self):
        self.assertEqual(self.unchanged,self.original)
        self.assertEqual(len(self.original),96);self.assertEqual(len(self.modern),len(self.original))
        old=struct.unpack('<24I',self.original);new=struct.unpack('<24I',self.modern)
        self.assertEqual([i for i,(a,b) in enumerate(zip(old,new)) if a!=b],[17])
        self.assertEqual(old[14:18],(50,10,11,0x300));self.assertEqual(new[14:18],(50,10,11,0xb00))
        self.assertEqual(new[:5],(32,4,11,0x300,14))
        from nitro_data import pack_narc,unpack_narc
        from tailwind_resources import modern_tailwind_resources
        members=self.members+[b'cursed-body',b'competitive'];incoming=pack_narc(members,self.names)
        # Compilation is already real above; use the result to isolate archive ownership.
        with patch('tailwind_resources.modern_tailwind_script',return_value=self.modern):
            after,names=unpack_narc(modern_tailwind_resources(incoming))
        self.assertEqual(names,self.names);self.assertEqual(len(after),299)
        self.assertEqual(after[:160],members[:160]);self.assertEqual(after[161:],members[161:])
        self.assertEqual(after[160],self.modern)

    def test_actual_vm_cast_recast_snatch_expiry_and_fresh_recast_all_eight_flags(self):
        # The full real side aliases and compare/update commands consume SDK bytecode.
        # Presentation/Call edges are stubbed; timer mutation and scheduling are real.
        from nitro_data import unpack_narc
        effect=unpack_narc((ROOT/'files/battledata/script/effect_script.narc').read_bytes())[0][225]
        arrays=c_array('original',self.original)+c_array('modern',self.modern)+c_array('end',self.members[233])+c_array('effect',effect)
        arrays+=re.search(r'static const int sMoveStatusChangeScripts\[[^]]+\] = \{.*?\n\};',(ROOT/UTIL).read_text(),re.S)[0]+'\n'
        arrays+=native('GetMoveStatusChangeScript')
        residual=('enum {UFC_STATE_TAILWIND,UFC_STATE_LUCKY_CHANT};\nstatic int ends[2],scheduledSnatch;'
                  +residual_source().split('static int ends[2],scheduledSnatch;',1)[1])
        fixture=command_source()+residual+arrays+r'''
int main(void){
 const u32 *script=QOL_MODERN_BATTLE?modern:original;u32 start=QOL_MODERN_BATTLE?0xb00:0x300;
 for(int b=0;b<4;b++){
  BattleContext c={0};c.battlerIdAttacker=b;c.battlerIdTarget=b^1;
  u32 other=0x7404;c.fieldSideConditionFlags[(b&1)^1]=other;messages=animations=0;
  run(&c,effect,sizeof(effect)/4);
  assert((c.sideEffectFlagsDirect&0xffffff)==121);assert(GetMoveStatusChangeScript(&c,1,c.sideEffectFlagsDirect)==160);
  run(&c,script,24);assert(c.fieldSideConditionFlags[b&1]==start);
  assert(c.fieldSideConditionFlags[(b&1)^1]==other);assert(lastMessage==1230&&messages==1&&animations==1);
  // The resolved attacker owns the side after Snatch; the old attacker/target side is untouched.
  for(int timer=1;timer<=4;timer++){
   c.fieldSideConditionFlags[b&1]=timer==4?0xb00:(u32)timer<<8;c.moveStatusFlag=0;
   messages=animations=0;run(&c,script,24);
   assert(c.moveStatusFlag&MOVE_STATUS_FAILED);assert(messages==0&&animations==0);
   assert(c.fieldSideConditionFlags[b&1]==(timer==4?0xb00:(u32)timer<<8));
  }
  c.fieldSideConditionFlags[b&1]=0;c.moveStatusFlag=0;run(&c,script,24);
  ends[0]=ends[1]=0;int duration=0;
  while(c.fieldSideConditionFlags[b&1]&0x300){tick(&c);duration++;}
  assert(duration==(QOL_MODERN_BATTLE?4:3));assert(ends[b&1]==1&&ends[(b&1)^1]==0);
  messages=0;run(&c,end,8);assert(messages==1&&lastMessage==1232);
  c.battlerIdAttacker=b;c.moveStatusFlag=0;run(&c,script,24);
  assert(c.fieldSideConditionFlags[b&1]==start&&c.moveStatusFlag==0);
 }
 return 0;}
'''
        TailwindNativeTests().variants(fixture,'-Wno-sign-compare','-Wno-unused-but-set-variable')


if __name__=='__main__':unittest.main()
