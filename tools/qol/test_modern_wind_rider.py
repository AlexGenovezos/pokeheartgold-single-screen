"""Wind Rider exercises extracted production C and genuine SDK script bytecode."""
from pathlib import Path
import itertools
import os
import re
import struct
import unittest
import test_game_logic as game
import test_modern_moves as moves
import test_modern_rules as rules
import test_modern_tailwind as tailwind

ROOT=Path(__file__).resolve().parents[2]
UTIL='src/battle/battle_util.c'
PLAYER='src/battle/battle_controller_player.c'
COMMAND='src/battle/battle_command.c'

def native(name,path=UTIL):
    return game.function_source(path,name)+'\n'

def base():
    # Full native context declarations; no host substitute layouts for VM state.
    return moves.ModernMoveTests().source()+r'''
#include <stdio.h>
#include <stdlib.h>
#include "constants/battle.h"
#include "constants/abilities.h"
#include "constants/battle_subscript.h"
#include "constants/items.h"
#include "constants/move_effects.h"
#include "constants/opcode.h"
#include "constants/battle_script.h"
#include "constants/message_tags.h"
typedef int s32;typedef short s16;typedef struct {int battleType,battleOutcomeFlag,battleSpecial,safariBallCnt,regulationFlag,maxBattlers,linkVersionMismatch;} BattleSystem;
#define QOL_STAT_CHANGE_COMPETITIVE_PENDING (1 << 0)
''' + tailwind.context_types().split('typedef struct MoveTbl {')[0]+tailwind.context_types().split('} MoveTbl;')[1]+r'''
#ifndef ABILITY_WIND_RIDER
#define ABILITY_WIND_RIDER 241
#endif
#ifndef BATTLE_SUBSCRIPT_WIND_RIDER_STAT_UP
#define BATTLE_SUBSCRIPT_WIND_RIDER_STAT_UP 304
#endif
enum {NARC_a_0_0_1=1,HEAP_ID_BATTLE=5};
static int assertions,allocs,frees,allocationFails;
#define GF_ASSERT(x) do{if(!(x))assertions++;}while(0)
static void *Heap_Alloc(int heap,size_t size){assert(heap==HEAP_ID_BATTLE);if(allocationFails)return NULL;allocs++;return malloc(size);}
static void Heap_Free(void *p){assert(p);frees++;free(p);}
static void MIi_CpuClearFast(int v,u32 *p,size_t n){memset(p,v,n);}
static int BattleSystem_GetMaxBattlers(BattleSystem *bs){return 4;}
static int BattleSystem_GetFieldSide(BattleSystem *bs,int b){return b&1;}
static void ReadBattleScriptFromNarc(BattleContext *c,int n,int f){c->scriptNarcId=n;c->scriptFileId=f;c->scriptSeqNo=0;}
''' + native('GetBattlerAbility')

def immunity():
    return base()+rules.array('sSoundMoves')+native('CheckBattlerAbilityIfNotIgnored')+native('DamageDivide')+native('BattleContext_CheckMoveImmunityFromAbility')+native('BattleControllerPlayer_CheckMoveImmunity',PLAYER)

def event_source():
    text=(ROOT/UTIL).read_text()
    event=(text.split('// QOL_WIND_EVENTS_BEGIN\n')[1].split('// QOL_WIND_EVENTS_END')[0]
           if '// QOL_WIND_EVENTS_BEGIN' in text else r"""
static void Qol_WindEventsNew(BattleContext *c){}
static void Qol_WindEventsDelete(BattleContext *c){}
static void Qol_WindEventsReset(BattleContext *c){}
static void Qol_QueueTailwindStart(BattleSystem *s,BattleContext *c,int side){}
static int Qol_BeginWindRiderEntry(BattleSystem *s,BattleContext *c,int b){return 0;}
static int Qol_ContinueWindRider(BattleSystem *s,BattleContext *c){return 0;}
""")
    return base()+event+r"""
#define msg_0197_00750 750
#define msg_0197_00753 753
static int CreateNicknameTag(BattleContext *c,int b){return b;}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){
 if(side==BATTLER_CATEGORY_ATTACKER)return c->battlerIdAttacker;
 if(side==BATTLER_CATEGORY_DEFENDER)return c->battlerIdTarget;
 if(side==BATTLER_CATEGORY_SIDE_EFFECT_MON)return c->battlerIdStatChange;
 if(side==BATTLER_CATEGORY_MSG_TEMP)return c->battlerIdTemp;
 if(side==BATTLER_CATEGORY_MSG_DEFENDER)return c->battlerIdLeechSeeded;
 return side&3;
}
static int MaskOfFlagNo(int bit){return 1u<<bit;}
static BOOL BattleScript_Return(BattleContext *c);
"""+''.join(native(n,COMMAND) for n in ('BattleScriptReadWord','BattleScriptIncrementPointer','BattleScriptGetVarPointer','BtlCmd_UpdateVar','BtlCmd_EndScript'))+native('BattleScript_Return')

def prediction_source():
    return base()+r"""
enum {TYPETABLE_ATTACKER,TYPETABLE_DEFENDER,TYPETABLE_EFFECT};
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return 0;}
static int GetHeldItemModifier(BattleContext *c,int b,int f){return 0;}
static int GetBattlerVar(BattleContext *c,int b,int f,void *p){return f==BMON_DATA_TYPE_1?c->battleMons[b].type1:c->battleMons[b].type2;}
"""+''.join(rules.array(n) for n in ('sTypeEffectiveness','sSoundMoves','sFixedDamageMoveEffects'))+''.join(native(n) for n in (
 'CheckBattlerAbilityIfNotIgnored','CheckChargeMoveHitTurn','CheckFlyingImmunity','ApplyEffectivenessFlags',
 'BattleSystem_IsTypeMatchupActive','IsFixedDamageMove','DamageDivide','ApplyTypeMultiplier',
 'Qol_PreviewTypeEffectiveness','CalcTypeEffectivenessFlags','BattleSystem_ApplyTypeEffectiveness'))


def entry_source():
    text=(ROOT/UTIL).read_text().split('int TryAbilityOnEntry(')[1]
    case=text[text.index('        case 2: // Weather from abilities'):text.index('        case 3: // Intimidate')]
    return event_source()+r"""
static void Qol_SetProtectSuccessTurns(MoveEffectData *m,int n){m->protectSuccessTurns=n;}
"""+native('SetBattlerVar')+r"""
static int entry(BattleSystem *battleSystem,BattleContext *ctx){
 int i,battlerId,script=0,flag=0,maxBattlers=4;
 switch(ctx->sendOutState){
"""+case+r"""
 default:break;}return script;
}
"""

def vm_source(cast, presentation, extra=None):
    extra=extra or {}
    source=event_source().replace('static void ReadBattleScriptFromNarc(BattleContext *c,int n,int f){c->scriptNarcId=n;c->scriptFileId=f;c->scriptSeqNo=0;}',
                                 'static void ReadBattleScriptFromNarc(BattleContext *c,int n,int f);')
    source+=tailwind.c_array('cast',cast)+tailwind.c_array('presentation',presentation)
    source+=''.join(tailwind.c_array('member'+str(i),data) for i,data in extra.items())
    source+=r"""
static int abilityAfterAnimation;
static int messages,animations,packetIds[20],packetRecipient[20],packetAbility[20],packetStat[20];
static int Link_QueueNotEmpty(BattleContext *c){return 1;}
static void Link_CheckTimeout(BattleContext *c){assert(0);}
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static struct {int newKeys;} gSystem;
static int System_GetTouchNew(void){return 0;}
static int BattleSystem_AreBattleAnimationsOn(BattleSystem *s){return 1;}
static int CheckStatusEffectsSubstitute(BattleContext *c,int b,int status){return 1;}
static void BattleController_EmitSetStatus2Effect(BattleSystem *s,BattleContext *c,int b,int status){assert(b==(c->scriptFileId==182?c->battlerIdTarget:c->battlerIdStatChange));assert(status==BATTLE_ANIMATION_STAT_BOOST);animations++;if(c->scriptFileId==182&&abilityAfterAnimation)c->battleMons[b].ability=abilityAfterAnimation;}
static void BattleController_EmitPacket(BattleSystem *s,int channel,int b,void *data,int size){
 BattleMessage *m=data;assert(channel==1&&size==sizeof(BattleMessage)&&m->command==21);
 packetIds[messages]=m->id;packetRecipient[messages]=m->param[0];
 packetAbility[messages]=m->param[1];packetStat[messages]=m->param[2];messages++;
}
static void ReadBattleScriptFromNarc(BattleContext *c,int n,int f){
 c->scriptNarcId=n;c->scriptFileId=f;c->scriptSeqNo=0;
 if(f==160)memcpy(c->battleScriptBuffer,cast,sizeof(cast));
 else if(f==304)memcpy(c->battleScriptBuffer,presentation,sizeof(presentation));
 EXTRA_MEMBERS
 else c->battleScriptBuffer[0]=224;
}
"""
    source=source.replace('EXTRA_MEMBERS',''.join(f'else if(f=={i})memcpy(c->battleScriptBuffer,member{i},sizeof(member{i}));' for i in extra))
    # Other formatter cases are outside this presentation. Assert if reached.
    for name in ('GetItemMessageNo','GetNumberMessageNo','GetTypeMessageNo','GetStatusMessageNo','GetPoffinMessageNo','GetFlavorMessageNo'):
        source+=f'static int {name}(BattleContext *c,int b){{assert(0);return 0;}}\n'
    for name in ('GetPokemonMessageNo','GetTrainerNameMessageNo','GetTrainerClassMessageNo'):
        source+=f'static int {name}(BattleSystem *s,BattleContext *c,int b){{assert(0);return 0;}}\n'
    source+=r"""
typedef int String;
static int Battler_GetType(BattleContext *c,int b,int f){return f==BMON_DATA_TYPE_1?c->battleMons[b].type1:c->battleMons[b].type2;}
u8 GetMoveMaxPP(u16 m,u8 n){assert(0);return 0;}
static void CopyU16ArrayToString(String *s,u16 *p){assert(0);}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int b){}
static void TrainerAIData_ClearMoves(BattleContext *c,int b){}
static void TrainerAIData_ClearAbility(BattleContext *c,int b){}
static void TrainerAIData_ClearHeldItem(BattleContext *c,int b){}
"""+''.join(native(n) for n in ('Qol_GetProtectSuccessTurns','Qol_SetProtectSuccessTurns','GetBattlerVar','SetBattlerVar','Qol_GetActualStatStageDelta'))
    source+=native('BattleController_EmitPrintMessage','src/battle/battle_controller.c')
    source+=''.join(native(n,COMMAND) for n in ('BattlerSetAbility','GetMoveMessageNo','GetNicknameMessageNo','GetAbilityMessageNo','GetStatMessageNo','InitBattleMsgData','InitBattleMsg','BtlCmd_PrintMessage','BtlCmd_PlayBattleAnimation','BtlCmd_Wait','BtlCmd_WaitButtonABTime','BtlCmd_CompareVarToValue','BtlCmd_CompareMonDataToValue','BtlCmd_CheckAbility','BtlCmd_UpdateMonData','BtlCmd_UpdateMonDataFromVar','BtlCmd_UpdateVar2','BtlCmd_Goto','BtlCmd_CheckSubstitute','BtlCmd_Transform'))
    return source+r"""
static void vm(BattleContext *c,int member){
 BattleSystem system={0};ReadBattleScriptFromNarc(c,1,member);
 for(int step=0;step<1000;step++){
 switch(c->battleScriptBuffer[c->scriptSeqNo]){
 case 14:BtlCmd_Wait(&system,c);break;
 case 17:c->scriptSeqNo++;break;
 case 18:BtlCmd_PrintMessage(&system,c);break;
 case 30:BtlCmd_WaitButtonABTime(&system,c);break;
 case 32:BtlCmd_CompareVarToValue(&system,c);break;
 case 33:BtlCmd_CompareMonDataToValue(&system,c);break;
 case 50:BtlCmd_UpdateVar(&system,c);break;
 case 52:BtlCmd_UpdateMonData(&system,c);break;
 case 55:BtlCmd_CheckAbility(&system,c);break;
 case 57:BtlCmd_UpdateVar2(&system,c);break;
 case 58:BtlCmd_UpdateMonDataFromVar(&system,c);break;
 case 59:BtlCmd_Goto(&system,c);break;
 case 210:BtlCmd_CheckSubstitute(&system,c);break;
 case 60:assert(c->battleScriptBuffer[c->scriptSeqNo+1]==76);c->scriptSeqNo+=2;break;
 case 69:BtlCmd_PlayBattleAnimation(&system,c);break;
 case 224:{int depth=c->scriptStackDepth;int done=BtlCmd_EndScript(&system,c);if(done||c->scriptStackDepth<depth)return;break;}
 default:fprintf(stderr,"VM unexpected %u in %d at %d\n",c->battleScriptBuffer[c->scriptSeqNo],c->scriptFileId,c->scriptSeqNo);assert(0);
 }
 }assert(0);
}
"""

class WindRiderTests(unittest.TestCase):
    def compile_run(self,source,*flags):
        # The native signed bit31 macro is a known legacy host-UB issue.
        # Normalize only the host fixture while asserting the identical pattern.
        source=source.replace('#include \"constants/battle.h\"', '#include \"constants/battle.h\"\n#undef MOVE_STATUS_NO_MORE_WORK\n#define MOVE_STATUS_NO_MORE_WORK (1u << 31)\ntypedef char HostNoMoreWorkPattern[(MOVE_STATUS_NO_MORE_WORK==0x80000000u)?1:-1];')
        if os.environ.get('WIND_SANITIZE')=='1':
            flags+=('-fsanitize=address,undefined','-fno-omit-frame-pointer')
        game.GameLogicTests.compile_run(self,source,*flags,'-Wno-unused-function','-Wno-unused-variable','-Wno-unused-but-set-variable','-Wno-sign-compare')

    def variants(self,source):
        for t,b,m in itertools.product((0,1),repeat=3):
            with self.subTest(types=t,battle=b,moves=m):
                self.compile_run(source,f'-DQOL_MODERN_TYPES={t}',f'-DQOL_MODERN_BATTLE={b}',f'-DQOL_MODERN_MOVES={m}')

    def test_actual_attack_immunity_precedes_damage_and_target_secondaries(self):
        self.variants(immunity()+r'''
int main(void){
 const int wind[]={16,18,59,177,196,239,257,314,575,587};
 for(int w=0;w<10;w++)for(int target=0;target<4;target++)for(int stage=0;stage<=12;stage++)
 for(int mold=0;mold<2;mold++)for(int suppress=0;suppress<2;suppress++)for(int charge=0;charge<2;charge++){
  // The legacy battle API requires a supported move; its embedded table is468.
  // Exhaustive unsupported-ID rejection is covered by the pure classifier.
  if(!Qol_IsSupportedMove(wind[w]))continue;
  BattleContext c={0};c.moveNoCur=wind[w];c.battleMons[target].hp=100;
  c.battleMons[target].ability=ABILITY_WIND_RIDER;c.battleMons[target].statChanges[STAT_ATK]=stage;
  c.battleMons[0].ability=target==0?ABILITY_WIND_RIDER:(mold?ABILITY_MOLD_BREAKER:0);
  c.battleMons[target].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleStatus=charge?BATTLE_STATUS_CHARGE_TURN:0;
  int expected=QOL_MODERN_BATTLE && target!=0 && (w<8||QOL_MODERN_MOVES)&&!mold&&!suppress&&!charge;
  int got=BattleContext_CheckMoveImmunityFromAbility(&c,0,target);
  if(got!=(expected?182:0)){fprintf(stderr,"Wind immunity move=%d target=%d actual=%d expected=%d\n",wind[w],target,got,expected?182:0);return 1;}
 }
 for(int fail=0;fail<4;fail++){
  BattleContext c={0};c.moveNoCur=MOVE_WHIRLWIND;c.battleMons[1].hp=100;c.battleMons[1].ability=ABILITY_WIND_RIDER;c.battlerIdTarget=1;
  c.moveStatusFlag=MOVE_STATUS_NO_EFFECT|(fail==1?MOVE_STATUS_PROTECTED:fail==2?MOVE_STATUS_SEMI_INVULNERABLE:fail==3?MOVE_STATUS_MISSED:0);
  int got=BattleControllerPlayer_CheckMoveImmunity(NULL,&c);assert(got==(QOL_MODERN_BATTLE&&!fail));
  if(got){assert(c.scriptFileId==182);assert(c.moveStatusFlag&MOVE_STATUS_NO_MORE_WORK);assert(!(c.moveStatusFlag&MOVE_STATUS_NO_EFFECT));}
 }
 return 0;}
''')

    def test_real_tailwind_write_and_end_tail_chain_restore_native_stack(self):
        self.compile_run(event_source()+r"""
int main(void){
 for(int depth=0;depth<=4;depth++){
  BattleContext c={0};Qol_WindEventsNew(&c);c.battlerIdAttacker=0;
  c.battleMons[0].hp=c.battleMons[2].hp=100;c.battleMons[0].ability=c.battleMons[2].ability=241;
  c.battleMons[0].statChanges[STAT_ATK]=c.battleMons[2].statChanges[STAT_ATK]=6;
  c.turnOrder[0]=2;c.turnOrder[1]=1;c.turnOrder[2]=0;c.turnOrder[3]=3;
  c.scriptStackDepth=depth;for(int i=0;i<4;i++){c.scriptStackNarcId[i]=1;c.scriptStackFileId[i]=77+i;c.scriptStackSeqNo[i]=100+i;}
  c.battlerIdTemp=3;c.battlerIdStatChange=1;c.msgTemp=77;c.waitCounter=999;c.statChangeFlag=QOL_STAT_CHANGE_COMPETITIVE_PENDING;
  c.scriptNarcId=1;c.scriptFileId=160;c.scriptSeqNo=0;
  u32 words[]={50,OPCODE_FLAG_ON,BSCRIPT_VAR_SIDE_CONDITION_ATTACKER,0xb00};memcpy(c.battleScriptBuffer,words,sizeof(words));
  BtlCmd_UpdateVar(NULL,&c);assert(c.fieldSideConditionFlags[0]==0xb00);
  assert(c.battleMons[0].statChanges[STAT_ATK]==6);
  BtlCmd_EndScript(NULL,&c);
  if(c.battleMons[2].statChanges[STAT_ATK]!=7){fprintf(stderr,"Tailwind event missing Attack boost: actual %d expected 7\n",c.battleMons[2].statChanges[STAT_ATK]);return 1;}
  assert(c.scriptFileId==304&&c.scriptStackDepth==depth&&c.battlerIdTemp==2&&c.waitCounter==0);
  BtlCmd_EndScript(NULL,&c);assert(c.battleMons[0].statChanges[STAT_ATK]==7&&c.battlerIdTemp==0&&c.waitCounter==0);
  BtlCmd_EndScript(NULL,&c);assert(c.battlerIdTemp==3&&c.battlerIdStatChange==1&&c.msgTemp==77&&c.waitCounter==999);
  assert(c.scriptStackDepth==(depth?depth-1:0));assert(c.statChangeFlag==QOL_STAT_CHANGE_COMPETITIVE_PENDING);
  if(depth){assert(c.scriptFileId==77+depth-1&&c.scriptSeqNo==100+depth-1);}
  for(int i=0;i<4;i++){assert(c.scriptStackNarcId[i]==1&&c.scriptStackFileId[i]==77+i&&c.scriptStackSeqNo[i]==100+i);}
  Qol_WindEventsReset(&c);Qol_WindEventsDelete(&c);
 }
 return 0;}
""",'-DQOL_MODERN_BATTLE=1')

    def test_classifier_exhaustive_u16_independent_flags(self):
        self.variants(moves.ModernMoveTests().source()+r"""
int main(void){for(int id=0;id<=65535;id++){
 int wind=id==16||id==18||id==59||id==177||id==196||id==201||id==239||id==257||id==314||id==366;
 wind|=QOL_MODERN_MOVES&&(id==575||id==587);
 assert(Qol_IsWindMove(id)==wind);assert(Qol_WindMoveCanBeAbsorbed(id)==(wind&&id!=201&&id!=366));
 }
 return 0;}
""")

    def test_prediction_real_damage_flags_preview_use_known_abilities_without_writes(self):
        self.variants(prediction_source()+r"""
int main(void){
 for(int mold=0;mold<2;mold++)for(int sup=0;sup<2;sup++)for(int self=0;self<2;self++){
 BattleContext c={0};c.battleMons[0].hp=c.battleMons[1].hp=100;
 c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:0;c.battleMons[1].ability=241;
 c.battleMons[1].moveEffectFlags=sup?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
 c.trainerAIData.moveData[16].type=TYPE_FLYING;c.trainerAIData.moveData[16].power=40;
 c.trainerAIData.moveData[18].category=CATEGORY_STATUS;
 int immune=QOL_MODERN_BATTLE&&!mold&&!sup&&!self;BattleContext before=c;u32 flags=0;
 int damage=BattleSystem_ApplyTypeEffectiveness(NULL,&c,16,TYPE_NORMAL,self?1:0,1,40,&flags);
 if(immune&&damage!=0){fprintf(stderr,"AI type application failed Wind immunity: actual damage %d expected 0\n",damage);return 1;}
 assert(damage==(immune?0:40));assert(flags==(immune?MOVE_STATUS_NO_EFFECT:0));
 assert(!memcmp(&c,&before,sizeof(c)));
 assert(Qol_PreviewTypeEffectiveness(&c,16,self?1:0,1)==(immune?0:40));assert(Qol_PreviewTypeEffectiveness(&c,18,0,1)==-1);
 for(int known=0;known<2;known++){
 flags=0;CalcTypeEffectivenessFlags(&c,16,TYPE_NORMAL,mold?ABILITY_MOLD_BREAKER:0,known?241:0,0,0,0,&flags);
 assert(flags==((QOL_MODERN_BATTLE&&!mold&&known)?MOVE_STATUS_NO_EFFECT:0));
 }
 assert(!memcmp(&c,&before,sizeof(c)));
 }
 return 0;}
""")

    def test_registry_lifetime_reset_reentrancy_and_snapshot_consumption(self):
        self.compile_run(event_source()+r"""
int main(void){
 BattleContext c={0},other={0};
 for(int i=0;i<100;i++){Qol_WindEventsNew(&c);Qol_WindEventsReset(&c);Qol_WindEventsDelete(&c);}
 assert(allocs==100&&frees==100);Qol_WindEventsNew(&c);QolWindEvents zero={0};zero.magic=QOL_WIND_MAGIC;
 assert(!memcmp(sQolWindOwner.state,&zero,sizeof(zero)));
 int n=assertions;Qol_WindEventsNew(&c);Qol_WindEventsNew(&other);assert(assertions==n+2&&allocs==101);
 Qol_WindEventsDelete(&other);assert(assertions==n+3&&sQolWindOwner.owner==&c);
 c.turnOrder[0]=2;c.turnOrder[1]=0;c.turnOrder[2]=1;c.turnOrder[3]=3;
 c.battleMons[0].hp=c.battleMons[2].hp=100;c.battleMons[0].ability=c.battleMons[2].ability=241;
 c.battleMons[0].statChanges[1]=c.battleMons[2].statChanges[1]=6;c.fieldSideConditionFlags[0]=0xb00;
 Qol_QueueTailwindStart(NULL,&c,0);QolWindEvents saved=*sQolWindOwner.state;
 Qol_WindEventsReset(&c);assert(!memcmp(&saved,sQolWindOwner.state,sizeof(saved)));
 Qol_QueueTailwindStart(NULL,&c,1);assert(!memcmp(&saved,sQolWindOwner.state,sizeof(saved)));
 c.scriptFileId=160;Qol_ContinueWindRider(NULL,&c);assert(c.battleMons[2].statChanges[1]==7);
 assert(!(sQolWindOwner.state->pendingMask&4));saved=*sQolWindOwner.state;BattleContext snapshot=c;
 assert(Qol_ContinueWindRider(NULL,&c));assert(c.battleMons[0].statChanges[1]==7);
 c=snapshot;*sQolWindOwner.state=saved;assert(Qol_ContinueWindRider(NULL,&c));
 assert(c.battleMons[2].statChanges[1]==7&&c.battleMons[0].statChanges[1]==7);
 assert(!Qol_ContinueWindRider(NULL,&c));Qol_WindEventsReset(&c);
 Qol_WindEventsDelete(&c);n=assertions;Qol_WindEventsReset(&c);Qol_WindEventsDelete(&c);assert(assertions==n+2);
 allocationFails=1;Qol_WindEventsNew(&c);assert(!sQolWindOwner.owner&&!sQolWindOwner.state);assert(allocs==frees);
 return 0;}
""",'-DQOL_MODERN_BATTLE=1')

    def test_entry_once_raw_suppressed_no_tailwind_caps_and_real_ability_gain(self):
        self.compile_run(entry_source()+r"""
int main(void){
 for(int suppress=0;suppress<2;suppress++)for(int side=0;side<2;side++)for(int stage=6;stage<=12;stage++){
 BattleContext c={0};Qol_WindEventsNew(&c);for(int i=0;i<4;i++)c.turnOrder[i]=i;
 c.sendOutState=2;c.battleMons[0].hp=100;c.battleMons[0].ability=241;c.battleMons[0].statChanges[1]=stage;
 c.battleMons[0].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;c.fieldSideConditionFlags[side]=0xb00;
 c.battlerIdTemp=3;c.waitCounter=90;int expected=!suppress&&!side&&stage<12;
 assert(entry(NULL,&c)==(expected?304:0));assert(c.battleMons[0].sendOutFlag);
 if(expected){c.scriptFileId=304;assert(!Qol_ContinueWindRider(NULL,&c));assert(c.battlerIdTemp==3&&c.waitCounter==90);}
 c.sendOutState=2;assert(entry(NULL,&c)==0);assert(c.battleMons[0].statChanges[1]==stage+expected);
 u8 ability=241;SetBattlerVar(&c,0,BMON_DATA_ABILITY,&ability);assert(c.battleMons[0].sendOutFlag);
 ability=1;SetBattlerVar(&c,0,BMON_DATA_ABILITY,&ability);assert(c.battleMons[0].sendOutFlag);
 c.tempData=BMON_DATA_ABILITY;ability=241;SetBattlerVar(&c,0,BMON_DATA_TEMP,&ability);assert(!c.battleMons[0].sendOutFlag);
 c.battleMons[0].hp=0;c.sendOutState=2;assert(!entry(NULL,&c)&&!c.battleMons[0].sendOutFlag);
 Qol_WindEventsDelete(&c);
 }
 return 0;}
""",'-DQOL_MODERN_BATTLE=1')

    def test_absorption_adds_attack_path_before_native_speed_cap(self):
        from absorption_scripts import modern_absorption_source,SOURCE
        source=(ROOT/SOURCE).read_text();after=modern_absorption_source(source)
        self.assertIn('ABILITY_WIND_RIDER, _QolWindAttack',after)
        self.assertIn('_QolWindAttack:\n    CompareMonDataToValue OPCODE_EQU, BATTLER_CATEGORY_DEFENDER, BMON_DATA_STAT_CHANGE_ATK, 12, _032',after)
        self.assertIn('BSCRIPT_VAR_MESSAGE, 1',after)

    def test_pipeline_appends_presentation_after_old_299_owners(self):
        from contextlib import ExitStack
        from unittest.mock import patch
        from nitro_data import pack_narc,unpack_narc
        import modern_rom
        members=[struct.pack('<I',224)]*299
        members[12]=tailwind.script_words(12)
        archive=pack_narc(members)
        # Existing owners are already independently guarded. This first RED
        # isolates the absent append using an otherwise valid 299-member input.
        with ExitStack() as stack:
            stack.enter_context(patch('modern_rom.rom_files',return_value={'a/0/0/1':(0,0,len(archive)),'a/0/2/7':(0,0,0),'a/0/3/0':(0,0,0)}))
            stack.enter_context(patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:replacements))
            for name in ('modern_battle_resources','modern_paralysis_resources','modern_weather_resources','modern_absorption_resources',
                         'modern_sturdy_resources','modern_cursed_body_resources','modern_competitive_resources','modern_oblivious_intimidate_resources',
                         'modern_simple_resources','modern_tailwind_resources','modern_snow_effect_resources'):
                stack.enter_context(patch('modern_rom.'+name,side_effect=lambda data:data))
            for name in ('modern_ability_description_resources','modern_simple_message_resources','modern_snow_message_resources','modern_soul_dew_message_resources','modern_tailwind_message_resources'):
                stack.enter_context(patch('modern_rom.'+name,side_effect=lambda data,charmap:data))
            # Avoid invoking the SDK in this host-only ownership check once the
            # owner exists; genuine parity and compilation live in the SDK class.
            if hasattr(modern_rom,'modern_wind_rider_resources'):
                stack.enter_context(patch('wind_rider_scripts.wind_rider_script',return_value=struct.pack('<2I',14,224)))
            result=modern_rom.make_modern_rom(archive,None,types=False,battle_rules=True)
        after,_=unpack_narc(result['a/0/0/1']);self.assertEqual(len(after),305)
        self.assertEqual(after[:299],members);self.assertEqual(after[299:304],[struct.pack('<I',224)]*5)

    def test_actual_trainer_ai_route_zero_damage_without_knowledge_rng_or_event_writes(self):
        source=prediction_source()+r"""
#define MOVE_STATUS_IMMUNE (MOVE_STATUS_NO_EFFECT|MOVE_STATUS_LEVITATE_IMMUNE|MOVE_STATUS_WONDER_GUARD_IMMUNE|MOVE_STATUS_MAGNET_RISE_IMMUNE)
static int rngCalls;
static int BattleSystem_Random(BattleSystem *s){rngCalls++;return 9;}
static int CheckAbilityActive(BattleSystem *s,BattleContext *c,int scope,int b,int ability){return 0;}
static int GetItemVar(BattleContext *c,int i,int f){return 0;}
static int TrainerAI_MoveType(BattleSystem *s,BattleContext *c,int b,int m){return TYPE_NORMAL;}
static int CalcMoveDamage(BattleSystem *s,BattleContext *c,int m,int side,int field,int power,int type,int a,int d,int crit){return 50;}
enum {WEIGHT_TO_POWER_WEIGHT,WEIGHT_TO_POWER_POWER};
static const u16 sWeightToPower[][2]={{0xffff,0xffff}};
"""+native('TrainerAI_CalcDamage','src/battle/trainer_ai.c')
        self.variants(source+r"""
int main(void){
 for(int mold=0;mold<2;mold++)for(int suppress=0;suppress<2;suppress++)for(int roll=85;roll<=100;roll++){
 BattleContext c={0};c.battleMons[0].hp=c.battleMons[1].hp=100;c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:0;
 c.battleMons[1].ability=241;c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
 c.trainerAIData.battlerIdTarget=1;c.trainerAIData.moveData[16].power=40;c.trainerAIData.moveData[16].type=TYPE_FLYING;
 c.trainerAIData.abilities[1]=78;c.tempData=77;c.calcTemp=42;
 BattleContext before=c;u8 ivs[6]={0};int n=rngCalls;
 int got=TrainerAI_CalcDamage(NULL,&c,16,0,ivs,0,c.battleMons[0].ability,0,roll);
 assert(got==((QOL_MODERN_BATTLE&&!mold&&!suppress)?0:50*roll/100));assert(rngCalls==n&&allocs==0);
 assert(!memcmp(&before,&c,sizeof(c)));
 // This legacy function always clears its calculation scratch bit. Prove and
 // document that preexisting write instead of asserting whole-AI purity.
 c.battleStatus=BATTLE_STATUS_IGNORE_TYPE_EFFECTIVENESS;before=c;
 (void)TrainerAI_CalcDamage(NULL,&c,16,0,ivs,0,c.battleMons[0].ability,0,roll);
 before.battleStatus=0;assert(!memcmp(&before,&c,sizeof(c))&&rngCalls==n&&allocs==0);
 }
 return 0;}
""")

    def test_actual_preaccuracy_wind_bypass_preserves_rng_micle_and_mold_flags(self):
        from test_modern_original_abilities import accuracy_source
        self.variants(accuracy_source()+r"""
int main(void){
 for(int mold=0;mold<2;mold++)for(int sup=0;sup<2;sup++)for(int charge=0;charge<2;charge++){
 BattleContext c={0};c.battleMons[0].hp=c.battleMons[1].hp=100;
 c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:0;c.battleMons[1].ability=241;
 c.battleMons[1].moveEffectFlags=sup?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
 c.battleStatus=charge?BATTLE_STATUS_CHARGE_TURN:0;
 for(int i=0;i<8;i++)c.battleMons[0].statChanges[i]=c.battleMons[1].statChanges[i]=6;
 c.trainerAIData.moveData[16].accuracy=50;c.trainerAIData.moveData[16].power=40;c.trainerAIData.moveData[16].type=TYPE_FLYING;
 c.battleMons[0].moveEffectData.micleBerryFlag=1;randomCalls=0;randomValue=99;
 (void)BattleSystem_CheckMoveHit(NULL,&c,0,1,16);
 int immune=QOL_MODERN_BATTLE&&!mold&&!sup&&!charge;
 assert(randomCalls==!(immune||charge)&&c.battleMons[0].moveEffectData.micleBerryFlag==(immune||charge));
 if(immune)assert(!c.selfTurnData[0].moldBreakerFlag);
 }
 return 0;}
""")

    def test_real_new_init_delete_owns_one_payload_for_each_of_100_battles(self):
        source=event_source()+native('BattleContext_Init')+r"""
static void BattleContext_InitBattleStart(BattleSystem *s,BattleContext *c){}
static void BattleControllerPlayer_InitTrainerAIData(BattleSystem *s,BattleContext *c){}
void LoadMoveTbl(MoveTbl *m){}
static ItemData *LoadAllItemData(int heap){return Heap_Alloc(heap,4);}
"""+native('BattleContext_New',PLAYER)+native('BattleContext_Delete',PLAYER)
        self.compile_run(source+r"""
int main(void){for(int i=0;i<100;i++){
 BattleContext *c=BattleContext_New(NULL);assert(sQolWindOwner.owner==c&&sQolWindOwner.state);
 assert(sQolWindOwner.state->magic==QOL_WIND_MAGIC&&sQolWindOwner.state->phase==QOL_WIND_IDLE);
 BattleContext_Init(c);assert(sQolWindOwner.owner==c);BattleContext_Delete(c);
 assert(!sQolWindOwner.owner&&!sQolWindOwner.state);
 }assert(allocs==300&&frees==300&&assertions==0);return 0;}
""",'-DQOL_MODERN_BATTLE=1')

    def test_recipient_rechecks_caps_identity_and_competitive_before_after(self):
        self.compile_run(event_source()+r"""
int main(void){
 for(int skip=0;skip<6;skip++){
 BattleContext c={0};Qol_WindEventsNew(&c);for(int i=0;i<4;i++)c.turnOrder[i]=3-i;
 c.battleMons[0].hp=c.battleMons[2].hp=100;c.battleMons[0].ability=c.battleMons[2].ability=241;
 c.battleMons[0].statChanges[1]=c.battleMons[2].statChanges[1]=6;
 c.battlerIdStatChange=1;c.battleMons[1].hp=100;c.battleMons[1].ability=172;c.battleMons[1].statChanges[4]=6;
 // The actual existing End12 hook dispatches Competitive298 before Wind.
 c.scriptNarcId=1;c.scriptFileId=12;c.statChangeFlag=1;assert(!BtlCmd_EndScript(NULL,&c));
 assert(c.scriptFileId==298&&c.battleMons[1].statChanges[4]==8&&!c.statChangeFlag);
 c.fieldSideConditionFlags[0]=0xb00;Qol_QueueTailwindStart(NULL,&c,0);c.scriptFileId=160;
 assert(!BtlCmd_EndScript(NULL,&c));assert(c.battleMons[2].statChanges[1]==7);
 QolWindEvents state=*sQolWindOwner.state;BattleContext before=c;int n=assertions;
 assert(!Qol_BeginWindRiderEntry(NULL,&c,0));assert(assertions==n+1&&!memcmp(&before,&c,sizeof(c))&&!memcmp(&state,sQolWindOwner.state,sizeof(state)));
 switch(skip){case 0:c.battleMons[0].hp=0;break;case 1:c.battleMons[0].ability=1;break;
 case 2:c.battleMons[0].moveEffectFlags=MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED;break;
 case 3:c.selectedMonIndex[0]=1;break;case 4:c.fieldSideConditionFlags[0]=0;break;
 case 5:c.battleMons[0].statChanges[1]=12;break;}
 BtlCmd_EndScript(NULL,&c);assert(c.battleMons[0].statChanges[1]==(skip==5?12:6));
 assert(c.battlerIdStatChange==1&&c.buffMsg.id==753&&c.battleMons[1].statChanges[4]==8);
 // Restored recipient/pending state lets Competitive298 still run after Wind.
 c.scriptFileId=12;c.statChangeFlag=1;BtlCmd_EndScript(NULL,&c);
 assert(c.scriptFileId==298&&c.battleMons[1].statChanges[4]==10&&!c.statChangeFlag);
 Qol_WindEventsDelete(&c);
 }
 return 0;}
""",'-DQOL_MODERN_BATTLE=1')

    def test_arm_private_payload_registry_layout_and_native_header_identity(self):
        import subprocess,tempfile
        text=(ROOT/UTIL).read_text().split('// QOL_WIND_EVENTS_BEGIN\n')[1]
        types=text[text.index('enum {'):text.index('static QolWindEvents *Qol_GetWindEvents')]
        declarations=rules.COMMON.split('static unsigned rng')[0].replace('#include <assert.h>','').replace('#include <stdio.h>','').replace('#include <string.h>','').replace('#define GF_ASSERT assert','#define GF_ASSERT(x)')
        source=declarations+tailwind.context_types()+types+r"""
typedef char ArmPointer[(sizeof(void *)==4)?1:-1];
typedef char PayloadSize[(sizeof(QolWindEvents)==88)?1:-1];
typedef char RegistrySize[(sizeof(sQolWindOwner)==8)?1:-1];
typedef char OwnerOffset[(__builtin_offsetof(__typeof__(sQolWindOwner),state)==4)?1:-1];
typedef char TupleOffset[(__builtin_offsetof(QolWindEvents,savedBattlerIdTemp)==20)?1:-1];
typedef char StackOffset[(__builtin_offsetof(QolWindEvents,savedStackDepth)==36)?1:-1];
typedef char ArraysOffset[(__builtin_offsetof(QolWindEvents,savedStackNarcId)==40)?1:-1];
"""
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'arm.c';path.write_text(source)
            result=subprocess.run([os.environ.get('CC','cc'),'-target','armv5te-none-eabi','-std=c99','-Werror','-fsyntax-only','-iquote',str(ROOT/'include'),str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
        for path in ('include/battle/battle.h','include/battle/battle_util.h','include/pokemon_types_def.h','include/move.h'):
            self.assertEqual((ROOT/path).read_bytes(),subprocess.check_output(['git','show','103d88b4d396554aa9dbde1cd914e7d1730003e0:'+path]))

    def test_capacity_one_source_allocation_overlay_and_entry_scan_audit(self):
        source='\n'.join(p.read_text() for p in (ROOT/'src/battle').glob('*.c'))
        self.assertEqual(len(re.findall(r'\bBattleContext_New\(',source)),2)
        self.assertEqual(len(re.findall(r'\bBattleContext_Delete\(',source)),2)
        self.assertEqual(len(re.findall(r'\bBattleSystem_InitFromSetup\(',source)),2)
        main=(ROOT/'src/battle/battle_main.c').read_text()
        self.assertEqual(main.count('battleSystem->ctx = BattleContext_New(battleSystem);'),1)
        self.assertEqual(main.count('BattleContext_Delete(battleSystem->ctx);'),1)
        overlay=(ROOT/'main.lsf').read_text().split('Overlay OVY_12')[1].split('Overlay OVY_13')[0]
        for unit in ('battle_main','battle_util','battle_command','battle_controller_player','battle_022378C0'):
            self.assertIn(unit,overlay)
        asm='\n'.join(p.read_text(errors='ignore') for p in (ROOT/'asm').rglob('*.s'))
        self.assertNotRegex(asm,r'\b(?:BattleContext_New|BattleContext_Delete|BattleSystem_InitFromSetup)\b')
        self.assertNotIn('Qol_',native('BattlerSetAbility',COMMAND))
        for fn in ('BattleControllerPlayer_AfterMoveEffects','BattleControllerPlayer_ActionEnd'):
            self.assertIn('TryAbilityOnEntry',native(fn,PLAYER))

    def test_forced_stack_corruption_asserts_without_popping_active_presentation(self):
        self.compile_run(event_source()+r"""
int main(void){BattleContext c={0};Qol_WindEventsNew(&c);c.battleMons[0].hp=100;c.battleMons[0].ability=241;
 c.battleMons[0].statChanges[1]=6;c.fieldSideConditionFlags[0]=0xb00;
 assert(Qol_BeginWindRiderEntry(NULL,&c,0));c.scriptNarcId=1;c.scriptFileId=304;
 c.scriptStackDepth=1;c.scriptStackNarcId[0]=1;c.scriptStackFileId[0]=77;c.scriptStackSeqNo[0]=100;
 BattleContext before=c;QolWindEvents payload=*sQolWindOwner.state;int n=assertions;
 assert(!BtlCmd_EndScript(NULL,&c));assert(assertions>n);
 assert(!memcmp(&before,&c,sizeof(c)));assert(!memcmp(&payload,sQolWindOwner.state,sizeof(payload)));
 Qol_WindEventsDelete(&c);return 0;}
""",'-DQOL_MODERN_BATTLE=1')

    def test_actual_following_effect_phase_blocks_protect_and_hidden_states(self):
        from test_modern_original_abilities import accuracy_source
        self.variants(accuracy_source()+r"""
int main(void){
 const u32 hidden[]={0,MOVE_EFFECT_FLAG_FLY,MOVE_EFFECT_FLAG_DIG,MOVE_EFFECT_FLAG_DIVE};
 for(int protect=0;protect<2;protect++)for(int state=0;state<4;state++){
 BattleContext c=fixture(59);c.battleMons[1].ability=241;c.battleMons[0].moveEffectData.micleBerryFlag=1;
 c.trainerAIData.moveData[59].flags=2;c.turnData[1].protectFlag=protect;c.battleMons[1].moveEffectFlags=hidden[state];
 randomCalls=0;randomValue=0;(void)BattleSystem_CheckMoveHit(NULL,&c,0,1,59);
 if(QOL_MODERN_BATTLE)assert(!randomCalls&&c.battleMons[0].moveEffectData.micleBerryFlag);
 (void)BattleSystem_CheckMoveEffect(NULL,&c,0,1,59);
 int blocked=protect||state;assert(BattleControllerPlayer_CheckMoveImmunity(NULL,&c)==(QOL_MODERN_BATTLE&&!blocked));
 if(protect)assert(c.moveStatusFlag&MOVE_STATUS_PROTECTED);
 if(state&&!protect)assert(c.moveStatusFlag&MOVE_STATUS_SEMI_INVULNERABLE);
 }
 return 0;}
""")

    def test_actual_ai_switch_flags_route_uses_supplied_party_ability_and_type_override(self):
        source=prediction_source().replace('void CalcTypeEffectivenessFlags(', 'void realCalcTypeEffectivenessFlags(',1)+r"""
#include "constants/species.h"
static int flagCalls,firstFlags,rngCalls;
static void CalcTypeEffectivenessFlags(BattleContext *c,int m,int t,int a,int d,int item,int t1,int t2,u32 *f){
 realCalcTypeEffectivenessFlags(c,m,t,a,d,item,t1,t2,f);if(!flagCalls)firstFlags=*f;flagCalls++;
}
typedef struct {int ability;} Pokemon;
static Pokemon bench={241};
static int BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static int BattleSystem_GetBattlerIdPartner(BattleSystem *s,int b){return 3;}
static int BattleSystem_GetPartySize(BattleSystem *s,int b){return 2;}
static Pokemon *BattleSystem_GetPartyMon(BattleSystem *s,int b,int i){return &bench;}
static int GetMonData(Pokemon *p,int f,void *out){
 if(f==MON_DATA_HP)return 100;if(f==MON_DATA_SPECIES_OR_EGG)return 275;
 if(f==MON_DATA_ABILITY)return p->ability;if(f>=MON_DATA_MOVE1&&f<=MON_DATA_MOVE4)return MOVE_TACKLE;
 return 0;
}
static int GetItemVar(BattleContext *c,int item,int field){return 0;}
static int TrainerAI_MoveType(BattleSystem *s,BattleContext *c,int b,int m){return TYPE_FIRE;}
static int TrainerAI_GetMoveType(BattleSystem *s,BattleContext *c,Pokemon *p,int m){return TYPE_NORMAL;}
static int BattleSystem_Random(BattleSystem *s){rngCalls++;return 0;}
"""+native('AI_HasPartyMemberWithSuperEffectiveMove','src/battle/trainer_ai.c')
        self.variants(source+r"""
int main(void){for(int mold=0;mold<2;mold++){
 BattleContext c={0};c.moveNoHit[1]=16;c.moveNoHitBattler[1]=0;c.battleMons[0].hp=100;
 c.battleMons[0].type1=c.battleMons[0].type2=TYPE_GHOST;c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:0;
 c.battleMons[1].ability=19;c.trainerAIData.moveData[16].power=40;c.aiSwitchedPartySlot[1]=c.aiSwitchedPartySlot[3]=0xff;
 c.trainerAIData.abilities[1]=78;BattleContext before=c;flagCalls=rngCalls=0;
 assert(!AI_HasPartyMemberWithSuperEffectiveMove(NULL,&c,1,MOVE_STATUS_NO_EFFECT,2));
 int immune=QOL_MODERN_BATTLE&&!mold;assert(firstFlags==(immune?MOVE_STATUS_NO_EFFECT:0));
 assert(flagCalls==(immune?5:1)&&!rngCalls&&!allocs);assert(!memcmp(&before,&c,sizeof(c)));
 }
 return 0;}
""")

class WindAssignmentTests(unittest.TestCase):
    compile_run=WindRiderTests.compile_run
    variants=WindRiderTests.variants

    def test_selective_shiftry_pair_support_and_every_saved_byte_pid_form(self):
        source=moves.ModernMoveTests().source()+r"""
#include "constants/abilities.h"
#include "constants/species.h"
typedef struct {u8 abilities[2];} BASE_STATS;
"""+moves.no_includes((ROOT/'src/qol_abilities.c').read_text())
        self.variants(source+r"""
int main(void){
 assert(Qol_IsSupportedAbility(241)==QOL_MODERN_BATTLE);assert(!Qol_IsSupportedAbility(240));
 for(int form=0;form<32;form++)for(int byte=0;byte<256;byte++)for(int pid=0;pid<2;pid++){
 int expected=QOL_MODERN_BATTLE&&!form&&byte==48&&pid?241:byte;
 assert(Qol_GetStoredAbility(275,form,byte,pid)==expected);
 }
 BASE_STATS p={{34,48}};Qol_ApplyModernMonAbilities(275,&p);assert(p.abilities[0]==34&&p.abilities[1]==(QOL_MODERN_BATTLE?241:48));
 return 0;}
""")

    def test_encrypted_shiftry_getter_constructor_permutations_checksum_and_forms(self):
        from test_modern_cursed_body import ModernAbilityStorageTests
        source=ModernAbilityStorageTests().encrypted_ability_source()
        source=source.replace('SPECIES_WINGULL,SPECIES_PELIPPER,SPECIES_TORKOAL,SPECIES_FEEBAS,SPECIES_GALLADE','SPECIES_SHIFTRY')
        source=source.replace('first[]={51,51,73,33,80},second[]={93,2,70,12,242}', 'first[]={34},second[]={241}')
        source=source.replace('i<5','i<1').replace('row<5','row<1').replace('form<2','form<32')
        source=source.replace('p.abilities[1]=species==SPECIES_GALLADE?80:0', 'p.abilities[1]=48')
        source=source.replace('parity&&byte==first[row]', 'parity&&byte==48')
        source=source.replace('QOL_MODERN_BATTLE&&(pid&1)?second[row]:first[row]', '(pid&1)?(QOL_MODERN_BATTLE?241:48):34')
        for flags in ModernAbilityStorageTests().flags():
            self.compile_run(source,*flags)

    def test_sparse_banks_original_prefix_keys_fonts_and_unimplemented_gas_hole(self):
        from ability_descriptions import modern_ability_description_resources
        from nitro_data import unpack_narc,unpack_messages
        from game_text import game_text
        archive=(ROOT/'files/msgdata/msg.narc').read_bytes()
        after,names=unpack_narc(modern_ability_description_resources(archive,ROOT/'charmap.txt'))
        before,oldnames=unpack_narc(archive);self.assertEqual(names,oldnames)
        texts={720:'Wind Rider',721:'WIND RIDER',722:'Wind moves and Tailwind\nraise Attack. Blocks wind.'}
        font=(ROOT/'files/graphic/font/font_00000000.bin').read_bytes();widths=struct.unpack_from('<I',font,4)[0]
        for bank,key in ((720,7280),(721,50258),(722,26692)):
            words,k=unpack_messages(after[bank]);self.assertEqual((len(words),k),(243,key))
            self.assertEqual(words[241],game_text(texts[bank],ROOT/'charmap.txt'))
            self.assertEqual(words[240],game_text(' -',ROOT/'charmap.txt'))
            if bank!=722:self.assertEqual(words[:124],unpack_messages(before[bank])[0])
            for line in texts[bank].split('\n'):
                glyphs=game_text(line,ROOT/'charmap.txt')[:-1]
                self.assertLessEqual(sum(font[widths+g-1] for g in glyphs),149)
        with self.assertRaises(ValueError):modern_ability_description_resources(modern_ability_description_resources(archive,ROOT/'charmap.txt'),ROOT/'charmap.txt')

class WindRiderSdkTests(unittest.TestCase):
    compile_run=WindRiderTests.compile_run

    @classmethod
    def setUpClass(cls):
        from battle_scripts import battle_script_tools
        battle_script_tools()  # Required here: a missing SDK is a failure, not a skip.
        from absorption_scripts import modern_absorption_script
        from tailwind_resources import modern_tailwind_script
        from wind_rider_scripts import wind_rider_script
        cls.stage=tailwind.script_words(12)
        cls.presentation=wind_rider_script(cls.stage)
        cls.absorption=modern_absorption_script(tailwind.script_words(182))
        cls.cast=modern_tailwind_script(tailwind.script_words(160))

    def test_original_parities_and_call_free_304_command_profile(self):
        import hashlib
        from battle_scripts import compile_battle_script
        from absorption_scripts import SOURCE
        from wind_rider_scripts import ORIGINAL_STAGE_SOURCE,ORIGINAL_STAGE_SHA256,WIND_RIDER_SOURCE
        self.assertEqual(hashlib.sha256((ROOT/ORIGINAL_STAGE_SOURCE).read_bytes()).hexdigest(),ORIGINAL_STAGE_SHA256)
        self.assertEqual(compile_battle_script((ROOT/ORIGINAL_STAGE_SOURCE).read_text()),self.stage)
        self.assertEqual(compile_battle_script((ROOT/SOURCE).read_text()),tailwind.script_words(182))
        words=struct.unpack('<'+'I'*(len(self.presentation)//4),self.presentation)
        self.assertEqual(words,(69,7,12,14,18,622,39,7,7,255,14,30,30,224))
        self.assertNotIn('Call ',WIND_RIDER_SOURCE);self.assertNotIn('ChangeStatStage',WIND_RIDER_SOURCE)
        from unittest.mock import patch
        import wind_rider_scripts as module
        with patch.object(module,'compile_battle_script',return_value=b'wrong') as compiler:
            with self.assertRaisesRegex(ValueError,'member12'):module.wind_rider_script(self.stage)
        self.assertEqual(compiler.call_count,1)
        from nitro_data import pack_narc
        for count in (297,298,300,303,305):
            with self.assertRaises(ValueError):module.modern_wind_rider_resources(pack_narc([b'']*count))

    def test_vm_completed_cast_tailchains_two_recipients_at_every_native_stack_depth(self):
        self.compile_run(vm_source(self.cast,self.presentation)+r"""
int main(void){
 for(int depth=0;depth<=4;depth++){
 BattleContext c={0};Qol_WindEventsNew(&c);for(int i=0;i<4;i++){c.turnOrder[i]=3-i;c.selectedMonIndex[i]=i;}
 c.battleMons[0].hp=c.battleMons[2].hp=100;c.battleMons[0].ability=c.battleMons[2].ability=241;
 c.battleMons[0].statChanges[1]=c.battleMons[2].statChanges[1]=6;
 c.scriptStackDepth=depth;for(int i=0;i<4;i++){c.scriptStackNarcId[i]=1;c.scriptStackFileId[i]=77+i;c.scriptStackSeqNo[i]=100+i;}
 c.battlerIdTemp=3;c.battlerIdStatChange=1;c.msgTemp=77;c.waitCounter=999;
 c.statChangeFlag=QOL_STAT_CHANGE_COMPETITIVE_PENDING;c.moveTemp=123;c.calcTemp=987;c.tempData=456;c.itemTemp=321;c.abilityTemp=789;c.hpCalc=-88;c.damage=-999;c.battlerIdTarget=1;
 BattleContext before=c;messages=animations=0;vm(&c,160);
 assert(c.battleMons[0].statChanges[1]==7&&c.battleMons[2].statChanges[1]==7);
 assert(messages==3&&animations==2&&packetIds[0]==1230&&packetIds[1]==622&&packetIds[2]==622);
 assert(packetRecipient[1]==(2|(2<<8))&&packetRecipient[2]==0&&packetAbility[1]==241&&packetAbility[2]==241&&packetStat[1]==1&&packetStat[2]==1);
 assert(c.trainerAIData.abilities[0]==241&&c.trainerAIData.abilities[2]==241);
 assert(c.battlerIdTemp==3&&c.battlerIdStatChange==1&&c.msgTemp==77&&c.waitCounter==0);
 // 160's own WaitButton resets the incoming wait to zero before the queue saves it.
 assert(c.scriptStackDepth==(depth?depth-1:0));if(depth)assert(c.scriptFileId==77+depth-1&&c.scriptSeqNo==100+depth-1);
 before.battleMons[0].statChanges[1]=before.battleMons[2].statChanges[1]=7;
 before.fieldSideConditionFlags[0]=0xb00;before.waitCounter=0;
 before.trainerAIData.abilities[0]=before.trainerAIData.abilities[2]=241;
 // Normalize only legitimate VM flow and its loaded buffer. All semantic scratch,
 // Competitive state, native stack frames, and unrelated event state compare bytewise.
 before.scriptNarcId=c.scriptNarcId;before.scriptFileId=c.scriptFileId;before.scriptSeqNo=c.scriptSeqNo;
 before.scriptStackDepth=c.scriptStackDepth;before.battleContinueFlag=c.battleContinueFlag;
 memcpy(before.battleScriptBuffer,c.battleScriptBuffer,sizeof(c.battleScriptBuffer));
 assert(!memcmp(&before,&c,sizeof(c)));assert(assertions==0);
 c.battleMons[0].sendOutFlag=c.battleMons[2].sendOutFlag=1;
 messages=animations=0;vm(&c,160);assert(c.moveStatusFlag&MOVE_STATUS_FAILED);
 assert(c.battleMons[0].statChanges[1]==7&&c.battleMons[2].statChanges[1]==7&&messages==0&&animations==0);
 c.fieldSideConditionFlags[0]=0;c.moveStatusFlag=0;messages=animations=0;vm(&c,160);
 assert(c.battleMons[0].statChanges[1]==8&&c.battleMons[2].statChanges[1]==8&&messages==3&&animations==2);
 assert(c.battleMons[0].sendOutFlag&&c.battleMons[2].sendOutFlag);Qol_WindEventsDelete(&c);
 }
 return 0;}
""",'-DQOL_MODERN_BATTLE=1','-Wno-return-type')

    def test_vm_wind_absorption_cap_and_original_absorbers(self):
        self.compile_run(vm_source(self.cast,self.presentation,{182:self.absorption})+r"""
int main(void){
 const int abilities[]={78,31,114,241};const int stats[]={3,4,4,1};
 for(int a=0;a<4;a++)for(int stage=0;stage<=12;stage++){
 BattleContext c={0};Qol_WindEventsNew(&c);c.battlerIdTarget=1;c.battleMons[1].ability=abilities[a];
 c.battleMons[0].ability=ABILITY_MOLD_BREAKER;c.battleMons[1].statChanges[stats[a]]=stage;
 c.statChangeType=SIDE_EFFECT_TYPE_INDIRECT;messages=0;vm(&c,182);
 assert(c.battleMons[1].statChanges[stats[a]]==stage+(stage<12));assert(messages==1&&packetIds[0]==(stage<12?622:638));
 if(stage<12)assert(c.msgTemp==stats[a]);assert(!c.selfTurnData[0].moldBreakerFlag);Qol_WindEventsDelete(&c);
 }
 // Once absorption has activated, native UpdateMonData uses the current
 // recipient's real Simple arithmetic and ignores opposing Mold Breaker or
 // Shield Dust. This is the existing absorber-to-Simple transition seam.
 for(int ability=0;ability<2;ability++)for(int stage=6;stage<12;stage++){
 BattleContext c={0};Qol_WindEventsNew(&c);c.battlerIdTarget=1;c.battleMons[1].ability=241;
 c.battleMons[0].ability=ABILITY_MOLD_BREAKER;c.battleMons[1].statChanges[1]=stage;
 abilityAfterAnimation=ability?ABILITY_SHIELD_DUST:ABILITY_SIMPLE;messages=0;vm(&c,182);
 int expected=stage+(ability?1:2);if(expected>12)expected=12;
 assert(c.battleMons[1].statChanges[1]==expected&&!c.selfTurnData[0].moldBreakerFlag);
 Qol_WindEventsDelete(&c);
 }
 return 0;}
""",'-DQOL_MODERN_BATTLE=1','-Wno-return-type')

    def test_original_gain_scripts_real_setters_reentry_and_transform(self):
        text=(ROOT/UTIL).read_text().split('int TryAbilityOnEntry(')[1]
        case=text[text.index('        case 2: // Weather from abilities'):text.index('        case 3: // Intimidate')]
        entry='static int entry(BattleSystem *battleSystem,BattleContext *ctx){int i,battlerId,script=0,flag=0,maxBattlers=4;switch(ctx->sendOutState){'+case+'default:break;}return script;}\n'
        source=vm_source(self.cast,self.presentation,{i:tailwind.script_words(i) for i in (135,143,167,187)})+entry
        self.compile_run(source+r"""
int main(void){
 for(int member=0;member<4;member++)for(int fail=0;fail<2;fail++){
 const int scripts[]={135,143,167,187};BattleContext c={0};Qol_WindEventsNew(&c);
 for(int i=0;i<4;i++)c.turnOrder[i]=i;c.fieldSideConditionFlags[0]=0xb00;
 c.battleMons[0].hp=c.battleMons[1].hp=100;c.battleMons[0].ability=scripts[member]==187?ABILITY_TRACE:1;
 c.battleMons[1].ability=241;c.battleMons[0].sendOutFlag=1;c.battleMons[1].sendOutFlag=1;
 c.battleMons[0].statChanges[1]=c.battleMons[1].statChanges[1]=6;c.battlerIdTarget=1;c.battlerIdTemp=0;c.battlerIdLeechSeeded=1;
 if(fail&&scripts[member]!=187)c.moveStatusFlag=MOVE_STATUS_MISSED;
 vm(&c,scripts[member]);
 int gain=(!fail||scripts[member]==187)&&scripts[member]!=167;
 assert((c.battleMons[0].ability==241)==gain);assert(c.battleMons[0].sendOutFlag==!gain);
 c.sendOutState=2;int script=entry(NULL,&c);assert(script==(gain?304:0));
 if(script)vm(&c,304);assert(c.battleMons[0].statChanges[1]==6+gain);
 c.sendOutState=2;assert(!entry(NULL,&c));assert(c.battleMons[0].sendOutFlag);
 // No-op Role Play/Trace cannot reset an already consumed 241 latch.
 if(gain&&scripts[member]!=143){vm(&c,scripts[member]);c.sendOutState=2;assert(!entry(NULL,&c));}
 // Transform's native first40-byte copy resets the physical-entry latch.
 c.battleMons[1].ability=241;c.scriptSeqNo=0;BtlCmd_Transform(NULL,&c);
 assert(c.battleMons[0].ability==241&&!c.battleMons[0].sendOutFlag);
 c.sendOutState=2;assert(entry(NULL,&c)==304);vm(&c,304);Qol_WindEventsDelete(&c);
 }
 return 0;}
""",'-DQOL_MODERN_BATTLE=1','-Wno-return-type')

    def test_all_eight_real_resource_pipelines_preserve_owner_order_counts_names_and_holes(self):
        from contextlib import ExitStack
        from functools import lru_cache
        from unittest.mock import patch
        import sys
        import battle_scripts,modern_rom
        from nitro_data import unpack_narc,unpack_messages
        from game_text import game_text
        originals={
          'a/0/0/1':(ROOT/'files/battledata/script/subscript.narc').read_bytes(),
          'a/0/3/0':(ROOT/'files/battledata/script/effect_script.narc').read_bytes(),
          'a/0/2/7':(ROOT/'files/msgdata/msg.narc').read_bytes(),
          'a/0/1/1':(ROOT/'files/poketool/waza/waza_tbl.narc').read_bytes(),
          'a/0/0/0':(ROOT/'files/a/0/0/0').read_bytes(),
        }
        for path in ('a/0/0/8','a/0/6/8'):originals[path]=(ROOT/'files'/path).read_bytes()
        rom=b'';paths={}
        for path,data in originals.items():paths[path]=(0,len(rom),len(rom)+len(data));rom+=data
        compile_real=battle_scripts.compile_battle_script
        import hashlib,json
        fingerprint=hashlib.sha256()
        dependencies=[ROOT/'tools/qol/battle_scripts.py',ROOT/'asm/macros/btlcmd.inc',ROOT/'files/msgdata/msg/msg_0197.h']
        dependencies+=sorted((ROOT/'include/constants').rglob('*.h'))
        dependencies+=[Path(p) for p in battle_scripts.battle_script_tools() if Path(p).is_file()]
        for dependency in dependencies:
            fingerprint.update(str(dependency).encode());fingerprint.update(dependency.read_bytes())
        profile=fingerprint.digest()
        cache=Path(os.environ.get('WIND_SDK_CACHE',str(ROOT/'.local-tools/validation/wind-rider-sdk-cache')));cache.mkdir(parents=True,exist_ok=True)
        compiled=[];fresh=[]
        @lru_cache(None)
        def compile_once(source,root=battle_scripts.ROOT):
            key=hashlib.sha256(profile+source.encode()).hexdigest();path=cache/(key+'.json')
            if path.exists():
                record=json.loads(path.read_text());data=bytes.fromhex(record['binary'])
                if record['sha256']==hashlib.sha256(data).hexdigest():
                    compiled.append(data);return data
            data=compile_real(source,root);compiled.append(data);fresh.append(key)
            path.write_text(json.dumps({'binary':data.hex(),'sha256':hashlib.sha256(data).hexdigest()}))
            return data
        owners=('modern_battle_resources','modern_paralysis_resources','modern_weather_resources','modern_absorption_resources',
                'modern_sturdy_resources','modern_cursed_body_resources','modern_competitive_resources','modern_oblivious_intimidate_resources',
                'modern_simple_resources','modern_tailwind_resources','modern_drain_resources','modern_move_stat_resources','modern_wind_rider_resources')
        # Every cache miss uses genuine serial SDK assembly. Repeated branches
        # reuse that exact source/profile result; no substitute bytecode exists.
        with ExitStack() as stack:
            for module in list(sys.modules.values()):
                if module is not None and getattr(module,'compile_battle_script',None) is compile_real:
                    stack.enter_context(patch.object(module,'compile_battle_script',compile_once))
            stack.enter_context(patch('modern_rom.rom_files',return_value=paths))
            stack.enter_context(patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:replacements))
            before,names=unpack_narc(originals['a/0/0/1'])
            for types,battle,moves_flag in itertools.product((False,True),repeat=3):
                calls=[]
                with self.subTest(types=types,battle=battle,moves=moves_flag),ExitStack() as tracking:
                    for name in owners:
                        fn=getattr(modern_rom,name)
                        def owner(*args,name=name,fn=fn):calls.append(name);return fn(*args)
                        tracking.enter_context(patch.object(modern_rom,name,side_effect=owner))
                    result=modern_rom.make_modern_rom(rom,ROOT/'charmap.txt',types=types,battle_rules=battle,moves=moves_flag)
                after,after_names=unpack_narc(result.get('a/0/0/1',originals['a/0/0/1']))
                self.assertEqual(after_names,names);self.assertEqual(len(after),305 if battle else 304 if moves_flag else 297)
                self.assertEqual(after[12],before[12]);self.assertEqual(after[160],self.cast if battle else before[160])
                if battle:
                    self.assertEqual(after[304],self.presentation)
                    expected=list(owners[:10])+(list(owners[10:12]) if moves_flag else [])+[owners[12]]
                    self.assertEqual(calls,expected)
                    if not moves_flag:self.assertEqual(after[299:304],[struct.pack('<I',224)]*5)
                else:
                    self.assertNotIn('modern_wind_rider_resources',calls)
                    if moves_flag:self.assertEqual(after[297:299],[struct.pack('<I',224)]*2)
                if moves_flag:self.assertTrue(all(member!=struct.pack('<I',224) for member in after[299:304]))
                banks,banknames=unpack_narc(result.get('a/0/2/7',originals['a/0/2/7']))
                oldbanks,oldnames=unpack_narc(originals['a/0/2/7']);self.assertEqual(banknames,oldnames)
                for bank,key in ((720,7280),(721,50258),(722,26692)):
                    words,k=unpack_messages(banks[bank]);self.assertEqual(k,key);self.assertEqual(len(words),243 if battle else 124)
                    if battle:
                        # Names retain every original row; descriptions have the
                        # separately adopted original-ability edits only.
                        if bank!=722:self.assertEqual(words[:124],unpack_messages(oldbanks[bank])[0])
                        self.assertEqual(words[240],game_text(' -',ROOT/'charmap.txt'))
                self.assertEqual(len(unpack_messages(banks[749])[0]),899 if moves_flag else 468)
        self.assertGreater(len(compiled),20)
        print(f'Wind SDK pipeline: {len(compiled)} unique sources, {len(fresh)} fresh serial assemblies, {len(compiled)-len(fresh)} exact-profile cached results',flush=True)

    def test_original_skill_swap_noop_and_worry_seed_loss_gain_latch(self):
        text=(ROOT/UTIL).read_text().split('int TryAbilityOnEntry(')[1]
        case=text[text.index('        case 2: // Weather from abilities'):text.index('        case 3: // Intimidate')]
        entry='static int entry(BattleSystem *battleSystem,BattleContext *ctx){int i,battlerId,script=0,flag=0,maxBattlers=4;switch(ctx->sendOutState){'+case+'default:break;}return script;}\n'
        self.compile_run(vm_source(self.cast,self.presentation,{i:tailwind.script_words(i) for i in (143,167)})+entry+r"""
int main(void){BattleContext c={0};Qol_WindEventsNew(&c);for(int i=0;i<4;i++)c.turnOrder[i]=i;
 c.battleMons[0].hp=c.battleMons[1].hp=100;c.battleMons[0].ability=c.battleMons[1].ability=241;
 c.battleMons[0].sendOutFlag=c.battleMons[1].sendOutFlag=1;c.battleMons[0].statChanges[1]=6;c.fieldSideConditionFlags[0]=0xb00;c.battlerIdTarget=1;
 vm(&c,143);assert(c.battleMons[0].ability==241&&c.battleMons[1].ability==241);
 assert(c.battleMons[0].sendOutFlag&&c.battleMons[1].sendOutFlag);c.sendOutState=2;assert(!entry(NULL,&c));
 c.battlerIdAttacker=1;c.battlerIdTarget=0;vm(&c,167);assert(c.battleMons[0].ability==ABILITY_INSOMNIA&&c.battleMons[0].sendOutFlag);
 vm(&c,167);assert(c.battleMons[0].ability==ABILITY_INSOMNIA&&c.battleMons[0].sendOutFlag);
 u8 ability=241;SetBattlerVar(&c,0,BMON_DATA_ABILITY,&ability);assert(!c.battleMons[0].sendOutFlag);
 c.sendOutState=2;assert(entry(NULL,&c)==304);vm(&c,304);assert(c.battleMons[0].statChanges[1]==7&&c.battleMons[0].sendOutFlag);
 Qol_WindEventsDelete(&c);return 0;}
""",'-DQOL_MODERN_BATTLE=1','-Wno-return-type')

if __name__=='__main__':unittest.main()
