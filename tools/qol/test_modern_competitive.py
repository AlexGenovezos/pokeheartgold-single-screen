"""Execute native stat mutation, script return, species and Competitive resources."""
from pathlib import Path
import re
import struct
import unittest
from unittest.mock import patch
import test_game_logic as game
import test_modern_moves

ROOT = Path(__file__).resolve().parents[2]


def stat_source():
    source = test_modern_moves.ModernMoveTests().source() + r'''
#include "constants/abilities.h"
#include "constants/battle.h"
#include "constants/battle_script.h"
#include "constants/battle_subscript.h"
#include "constants/message_tags.h"
#include "constants/qol_stat_stages.h"
#ifndef ABILITY_COMPETITIVE
#define ABILITY_COMPETITIVE 172
#endif
#define QOL_STAT_CHANGE_COMPETITIVE_PENDING 1
#define GF_ASSERT assert
typedef int BattleSystem;
typedef int NarcId;
enum {NARC_a_0_0_0,NARC_a_0_0_1};
enum {msg_0197_00607=607,msg_0197_00142=142,msg_0197_00622=622,msg_0197_00756=756,
msg_0197_00759=759,msg_0197_00750=750,msg_0197_00753=753,msg_0197_00273=273,msg_0197_00727=727,
msg_0197_00669=669,msg_0197_00704=704,msg_0197_00145=145,msg_0197_00662=662,
msg_0197_00762=762,msg_0197_00765=765};
typedef struct {int hp,ability,moveEffectFlags,status2,statChanges[8];} BattleMon;
typedef struct {
 BattleMon battleMons[4];
 struct {int mistTurns;} fieldSideConditionData[2];
 struct {int moldBreakerFlag;} selfTurnData[4];
 struct {int id,tag,param[6];} buffMsg;
 int battlerIdStatChange,battlerIdAttacker,battlerIdTarget,battlerIdTemp,statChangeParam,
 statChangeType,statChangeFlag,tempData,msgTemp,changeType,changeParam,moveNoCur,itemTemp,
 battleStatus,battleStatus2,fieldCondition,battleContinueFlag,scriptNarcId,scriptFileId,scriptSeqNo,scriptStackDepth;
 int scriptStackNarcId[4],scriptStackFileId[4],scriptStackSeqNo[4];u32 battleScriptBuffer[400];
} BattleContext;
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
static int maxBattlers=4;
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return maxBattlers;}
static int CreateNicknameTag(BattleContext *c,int b){return b+100;}
static int GetNarcMemberSizeByIdPair(int n,int m){return 4;}
static void ReadWholeNarcMemberByIdPair(void *out,int n,int m){memset(out,0,4);}
'''
    for file, functions in (
        ('battle_util',('GetBattlerAbility','Qol_GetActualStatStageDelta','CheckBattlerAbilityIfNotIgnored','ReadBattleScriptFromNarc','BattleScript_Return')),
        ('battle_command',('BattleScriptReadWord','BattleScriptIncrementPointer','BtlCmd_ChangeStatStage','BtlCmd_EndScript'))):
        source += '\n'.join(game.function_source(f'src/battle/{file}.c',f) for f in functions)+'\n'
    return source + r'''
static BattleContext fixture(void) {
 BattleContext c={0};maxBattlers=4;c.battlerIdStatChange=c.battlerIdTarget=1;c.battlerIdTemp=3;
 c.battleMons[0].hp=c.battleMons[1].hp=100;c.battleMons[1].ability=ABILITY_COMPETITIVE;
 for(int b=0;b<4;b++)for(int s=0;s<8;s++)c.battleMons[b].statChanges[s]=6;
 c.statChangeType=SIDE_EFFECT_TYPE_DIRECT;c.statChangeParam=22;c.scriptNarcId=NARC_a_0_0_1;
 c.scriptFileId=BATTLE_SUBSCRIPT_UPDATE_STAT_STAGE;c.moveNoCur=MOVE_LEER;
 c.battleScriptBuffer[1]=10;c.battleScriptBuffer[2]=20;c.battleScriptBuffer[3]=30;
 return c;
}
static void mutate(BattleContext *c,int param){c->scriptSeqNo=0;c->statChangeParam=param;BtlCmd_ChangeStatStage(NULL,c);}
'''


class CompetitiveTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    def check(self,checks):
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(stat_source()+checks,*flags,'-Wno-unused-function')

    def test_all_seven_actual_reductions_boost_once_without_growing_stack(self):
        self.check(r'''
int main(void) {
 for(int stat=0;stat<7;stat++)for(int change=1;change<=2;change++)for(int depth=0;depth<=4;depth++) {
  BattleContext c=fixture();c.scriptStackDepth=depth;
  for(int d=0;d<depth;d++){c.scriptStackNarcId[d]=NARC_a_0_0_0;c.scriptStackFileId[d]=77+d;c.scriptStackSeqNo[d]=44+d;}
  c.msgTemp=90;c.changeType=91;c.changeParam=92;c.battleStatus2=0x12345678;
  mutate(&c,(change==1?22:46)+stat);
  assert(c.battleMons[1].statChanges[stat+1]==6-change);
  assert(!!(c.statChangeFlag&1)==QOL_MODERN_BATTLE);
  int temp=c.tempData,param=c.statChangeParam,type=c.statChangeType,status=c.battleStatus;
  int expected=6-(stat+1==STAT_SPATK?change:0)+(QOL_MODERN_BATTLE?2:0);
  BtlCmd_EndScript(NULL,&c);
  assert(c.battleMons[1].statChanges[STAT_SPATK]==expected);
  if(QOL_MODERN_BATTLE) {
   assert(c.scriptFileId==298&&c.scriptStackDepth==depth&&!c.battleContinueFlag);
   assert(c.buffMsg.id==753&&c.buffMsg.tag==TAG_NICKNAME_STAT);
   assert(c.buffMsg.param[0]==101&&c.buffMsg.param[1]==STAT_SPATK);
   assert(BtlCmd_EndScript(NULL,&c)==(depth==0));
  }
  assert(c.scriptStackDepth==(depth?depth-1:0));
  if(depth)assert(c.scriptFileId==77+depth-1&&c.scriptSeqNo==44+depth-1);
  assert(!(c.statChangeFlag&1)&&c.battlerIdAttacker==0&&c.battlerIdTarget==1&&c.battlerIdTemp==3&&c.battlerIdStatChange==1);
  assert(c.tempData==temp&&c.statChangeParam==param&&c.statChangeType==type&&c.battleStatus==status&&c.battleStatus2==0x12345678);
  assert(c.msgTemp==90&&c.changeType==91&&c.changeParam==92);
 }
 return 0;
}
''')

    def test_blocked_capped_self_ally_suppressed_unowned_and_invalid_sources(self):
        self.check(r'''
int main(void) {
 for(int reason=0;reason<22;reason++) {
  BattleContext c=fixture();
  switch(reason) {
   case 0:c.fieldSideConditionData[1].mistTurns=1;break;
   case 1:c.battleMons[1].status2=STATUS2_SUBSTITUTE;break;
   case 2:c.battleMons[1].ability=ABILITY_SHIELD_DUST;c.statChangeType=2;break;
   case 3:c.battleMons[1].statChanges[1]=0;break;
   case 4:c.battlerIdAttacker=1;break;
   case 5:c.battlerIdAttacker=3;break;
   case 6:c.battleMons[1].moveEffectFlags=MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED;break;
   case 7:c.battleMons[1].hp=0;break;
   case 8:c.statChangeType=SIDE_EFFECT_TYPE_NONE;break;
   case 9:c.statChangeType=SIDE_EFFECT_TYPE_HELD_ITEM;break;
   case 10:c.statChangeType=SIDE_EFFECT_TYPE_DISOBEDIENCE;break;
   case 11:c.statChangeType=SIDE_EFFECT_TYPE_TOXIC_SPIKES;break;
   case 12:c.statChangeType=SIDE_EFFECT_TYPE_MOVE_EFFECT;break;
   case 13:c.statChangeType=SIDE_EFFECT_TYPE_ABILITY;c.battleMons[0].ability=ABILITY_INTIMIDATE;break;
   case 14:c.battlerIdAttacker=BATTLER_NONE;c.statChangeFlag=1<<27;break;
   case 15:c.battlerIdAttacker=-1;c.statChangeFlag=1<<27;break;
   case 16:c.battleMons[1].ability=ABILITY_CLEAR_BODY;break;
   case 17:c.battleMons[1].ability=ABILITY_HYPER_CUTTER;break;
   case 18:c.battlerIdAttacker=2;maxBattlers=2;break;
   case 19:c.statChangeType=3;c.battleMons[0].ability=ABILITY_INTIMIDATE;
    c.scriptStackDepth=1;c.scriptStackNarcId[0]=NARC_a_0_0_1;c.scriptStackFileId[0]=71;break;
   case 20:c.statChangeType=3;c.battleMons[0].ability=ABILITY_INTIMIDATE;
    c.scriptStackDepth=1;c.scriptStackNarcId[0]=NARC_a_0_0_0;c.scriptStackFileId[0]=186;break;
   case 21:c.statChangeType=3;c.scriptStackDepth=1;c.scriptStackNarcId[0]=NARC_a_0_0_1;c.scriptStackFileId[0]=186;break;
  }
  if(QOL_MODERN_BATTLE)c.statChangeFlag|=1;mutate(&c,22);assert(!(c.statChangeFlag&1));
  BtlCmd_EndScript(NULL,&c);assert(c.battleMons[1].statChanges[STAT_SPATK]==6);
 }
 return 0;
}
''')

    def test_memento_mold_breaker_clipping_intimidate_provenance_and_lifetime(self):
        self.check(r'''
int main(void) {
 for(int source=0;source<3;source++)for(int spa=10;spa<=12;spa++) {
  BattleContext c=fixture();c.battleMons[1].statChanges[STAT_SPATK]=spa;
  if(source==0)c.battleMons[0].hp=0; // fainted Memento caster remains causal
  if(source==1)c.battleMons[0].ability=ABILITY_MOLD_BREAKER;
  if(source==2){c.statChangeType=3;c.battleMons[0].ability=ABILITY_INTIMIDATE;
   c.scriptStackDepth=1;c.scriptStackNarcId[0]=NARC_a_0_0_1;c.scriptStackFileId[0]=186;}
  mutate(&c,46);BtlCmd_EndScript(NULL,&c);
  assert(c.battleMons[1].statChanges[STAT_SPATK]==(QOL_MODERN_BATTLE?12:spa));
  if(QOL_MODERN_BATTLE&&spa<12)assert(c.buffMsg.id==(spa==11?750:753));
  assert(!(c.statChangeFlag&1));
 }
 BattleContext c=fixture();mutate(&c,22);mutate(&c,15);BtlCmd_EndScript(NULL,&c);
 assert(c.battleMons[1].statChanges[STAT_SPATK]==6); // positive next mutation clears marker
 c=fixture();mutate(&c,22);c.battleMons[1].moveEffectFlags=MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED;
 BtlCmd_EndScript(NULL,&c);assert(c.battleMons[1].statChanges[STAT_SPATK]==6&&!(c.statChangeFlag&1));
 c=fixture();mutate(&c,22);c.scriptFileId=71;BtlCmd_EndScript(NULL,&c);
 assert(c.battleMons[1].statChanges[STAT_SPATK]==6); // only native stat-script End owns dispatch
 c=fixture();c.battleMons[1].statChanges[STAT_SPATK]=12;mutate(&c,22+STAT_SPATK-1);BtlCmd_EndScript(NULL,&c);
 assert(c.battleMons[1].statChanges[STAT_SPATK]==(QOL_MODERN_BATTLE?12:11));
 return 0;
}
''')

    def test_clamped_decreases_and_indirect_moves_use_actual_final_stages(self):
        self.check(r'''
int main(void) {
 for(int stat=0;stat<7;stat++)for(int stage=0;stage<=12;stage++)for(int drop=1;drop<=2;drop++)for(int type=1;type<=2;type++) {
  BattleContext c=fixture();c.statChangeType=type;c.battleMons[1].statChanges[stat+1]=stage;
  int beforeSpa=c.battleMons[1].statChanges[STAT_SPATK];
  mutate(&c,(drop==1?22:46)+stat);
  int actual=stage<drop?0:stage-drop;
  assert(c.battleMons[1].statChanges[stat+1]==actual);
  int expected=stat+1==STAT_SPATK?actual:beforeSpa;
  if(QOL_MODERN_BATTLE&&actual<stage){expected+=2;if(expected>12)expected=12;}
  BtlCmd_EndScript(NULL,&c);assert(c.battleMons[1].statChanges[STAT_SPATK]==expected);
 }
 return 0;
}
''')

    def test_inactive_recipients_cannot_mark_or_dispatch_competitive(self):
        self.check(r'''
int main(void) {
 for(int recipient=2;recipient<4;recipient++) {
  BattleContext c=fixture();maxBattlers=2;c.battlerIdAttacker=1;
  c.battlerIdStatChange=recipient;c.battleMons[recipient].hp=100;
  c.battleMons[recipient].ability=ABILITY_COMPETITIVE;
  mutate(&c,22);
  assert(!(c.statChangeFlag&1));
  BtlCmd_EndScript(NULL,&c);
  assert(c.battleMons[recipient].statChanges[STAT_SPATK]==6);
  c=fixture();maxBattlers=2;c.battlerIdStatChange=recipient;
  c.battleMons[recipient].hp=100;c.battleMons[recipient].ability=ABILITY_COMPETITIVE;
  c.statChangeFlag=QOL_MODERN_BATTLE;
  BtlCmd_EndScript(NULL,&c);
  assert(!(c.statChangeFlag&1));
  assert(c.battleMons[recipient].statChanges[STAT_SPATK]==6);
 }
 if(QOL_MODERN_BATTLE) {
  const int invalid[]={-1,4,BATTLER_NONE};
  for(int i=0;i<3;i++) {
   BattleContext c=fixture();c.battlerIdStatChange=invalid[i];c.statChangeFlag=1;
   assert(BtlCmd_EndScript(NULL,&c));assert(!(c.statChangeFlag&1));
  }
 }
 return 0;
}
''')

    def test_private_marker_has_no_native_or_script_variable_owner(self):
        util=(ROOT/'src/battle/battle_util.c').read_text()
        self.assertIn('ctx->statChangeFlag = flag & (0xFF800000);',util)
        for name in ('BtlCmd_ChangeStatStage','BtlCmd_EndScript'):
            self.assertNotIn('Random',game.function_source('src/battle/battle_command.c',name))
        header=(ROOT/'include/battle/battle.h').read_text()
        self.assertIn('int statChangeFlag;',header)
        command=(ROOT/'src/battle/battle_command.c').read_text()
        owners={str(p.relative_to(ROOT)) for p in (ROOT/'src').rglob('*.c') if 'ctx->statChangeFlag' in p.read_text()}
        self.assertEqual(owners,{'src/battle/battle_command.c','src/battle/battle_util.c'})
        self.assertEqual(util.count('ctx->statChangeFlag'),1)
        self.assertEqual(command.count('ctx->statChangeFlag'),5)
        self.assertIn('ctx->statChangeFlag & (1 << 27)',command)
        getter=game.function_source('src/battle/battle_command.c','BattleScriptGetVarPointer')
        self.assertNotIn('statChangeFlag',getter)
        callers=list((ROOT/'files/battledata/script').rglob('*.s'))
        self.assertEqual([p.name for p in callers if '    ChangeStatStage ' in p.read_text()],['subscript_0012_UpdateStatStage.s'])
        self.assertTrue('QOL_STAT_CHANGE_COMPETITIVE_PENDING' in command)


class CompetitiveResourceTests(unittest.TestCase):
    def test_append_checks_count_source_and_sdk_parity(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('competitive_scripts'), 'Competitive script generation is missing')
        import competitive_scripts as scripts
        import modern_rom
        from nitro_data import pack_narc,unpack_narc
        members=[bytes([i%256])*4 for i in range(298)]
        with patch.object(scripts,'compile_battle_script',side_effect=[members[12],b'competitive']) as compiler:
            result,names=unpack_narc(modern_rom.modern_competitive_resources(pack_narc(members)))
        self.assertEqual(result[:298],members);self.assertEqual(result[298],b'competitive')
        self.assertEqual(names,unpack_narc(pack_narc(members))[1]);self.assertEqual(compiler.call_count,2)
        with patch.object(scripts,'compile_battle_script',return_value=b'wrong') as compiler:
            with self.assertRaisesRegex(ValueError,'unchanged.*match.*12'):
                modern_rom.modern_competitive_resources(pack_narc(members))
            self.assertEqual(compiler.call_count,1)
        read_text=Path.read_text
        def drift(path,*args,**kwargs):
            text=read_text(path,*args,**kwargs)
            return text+'\n' if path.name=='subscript_0012_UpdateStatStage.s' else text
        with patch.object(Path,'read_text',drift),patch.object(scripts,'compile_battle_script') as compiler:
            with self.assertRaisesRegex(ValueError,'expected source'):
                modern_rom.modern_competitive_resources(pack_narc(members))
            compiler.assert_not_called()
        for count in (297,299):
            with patch.object(scripts,'compile_battle_script') as compiler:
                with self.assertRaisesRegex(ValueError,'298'):
                    modern_rom.modern_competitive_resources(pack_narc((members+[b'extra'])[:count]))
                compiler.assert_not_called()

class CompetitiveSdkTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    @classmethod
    def setUpClass(cls):
        from battle_scripts import battle_script_tools
        from competitive_scripts import modern_competitive_script
        from nitro_data import unpack_narc
        try:battle_script_tools()
        except FileNotFoundError as error:raise unittest.SkipTest(str(error))
        path=ROOT/'files/battledata/script/subscript.narc'
        if not path.is_file():raise unittest.SkipTest('Original subscripts unavailable')
        original=unpack_narc(path.read_bytes())[0]
        if len(original)!=297:raise AssertionError('Expected original297 subscripts')
        cls.scripts={i:original[i] for i in (12,129,148,186)}
        cls.scripts[298]=modern_competitive_script(original[12])

    def source(self):
        source=stat_source().replace('#include "constants/message_tags.h"','#include "constants/message_tags.h"\n#include "constants/opcode.h"')
        source=source.replace('int moldBreakerFlag;','int moldBreakerFlag,statusFlags;')
        source=source.replace('battleStatus,battleStatus2,fieldCondition,','battleStatus,battleStatus2,moveStatusFlag,fieldCondition,abilityTemp,moveTemp,lastBattlerId,turnOrderIndexTemp,turnOrder[4],selectedMonIndex[4],switchMonIndex[4],')
        source=source.replace('BattleMon battleMons[4];','BattleMon battleMons[4];\n struct {int abilities[4];} trainerAIData;')
        source=source.replace('static int GetNarcMemberSizeByIdPair(int n,int m){return 4;}','static int GetNarcMemberSizeByIdPair(int n,int m);')
        source=source.replace('static void ReadWholeNarcMemberByIdPair(void *out,int n,int m){memset(out,0,4);}','static void ReadWholeNarcMemberByIdPair(void *out,int n,int m);')
        for member,data in self.scripts.items():
            words=','.join(str(w)+'u' for w in struct.unpack('<'+'I'*(len(data)//4),data))
            source+=f'static const u32 script{member}[]={{ {words} }};\n'
        source+=r'''
static const u32 *archive(int member,int *size) {
 switch(member) {
#define MEMBER(n) case n:*size=sizeof(script##n);return script##n
 MEMBER(12);MEMBER(129);MEMBER(148);MEMBER(186);MEMBER(298);
#undef MEMBER
 default:assert(0);return NULL;
 }
}
static int GetNarcMemberSizeByIdPair(int n,int m){int size;archive(m,&size);return size;}
static void ReadWholeNarcMemberByIdPair(void *out,int n,int m){int size;const u32 *p=archive(m,&size);memcpy(out,p,size);}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side) {
 switch(side) {
 case BATTLER_CATEGORY_ATTACKER:return c->battlerIdAttacker;
 case BATTLER_CATEGORY_DEFENDER:return c->battlerIdTarget;
 case BATTLER_CATEGORY_SIDE_EFFECT_MON:return c->battlerIdStatChange;
 case BATTLER_CATEGORY_MSG_BATTLER_TEMP:return c->battlerIdTemp;
 default:assert(0);return -1;
 }
}
static void *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int var) {
 switch(var) {
#define VAR(key,field) case key:return &c->field
 VAR(BSCRIPT_VAR_SIDE_EFFECT_TYPE,statChangeType);VAR(BSCRIPT_VAR_SIDE_EFFECT_PARAM,statChangeParam);
 VAR(BSCRIPT_VAR_BATTLE_STATUS,battleStatus);VAR(BSCRIPT_VAR_BATTLE_STATUS_2,battleStatus2);
 VAR(BSCRIPT_VAR_MOVE_STATUS_FLAGS,moveStatusFlag);VAR(BSCRIPT_VAR_BATTLER_STAT_CHANGE,battlerIdStatChange);
 VAR(BSCRIPT_VAR_BATTLER_ATTACKER,battlerIdAttacker);VAR(BSCRIPT_VAR_BATTLER_TARGET,battlerIdTarget);
 VAR(BSCRIPT_VAR_BATTLER_SPEED_TEMP,turnOrderIndexTemp);VAR(BSCRIPT_VAR_LAST_BATTLER_ID,lastBattlerId);
 VAR(BSCRIPT_VAR_MSG_BATTLER_TEMP,battlerIdTemp);VAR(BSCRIPT_VAR_TEMP_DATA,tempData);
#undef VAR
 default:assert(0);return NULL;
 }
}
static int GetBattlerVar(BattleContext *c,int b,int var,void *unused) {
 if(var==BMON_DATA_HP)return c->battleMons[b].hp;
 assert(var>=BMON_DATA_STAT_CHANGE_ATK&&var<=BMON_DATA_STAT_CHANGE_EVASION);
 return c->battleMons[b].statChanges[1+var-BMON_DATA_STAT_CHANGE_ATK];
}
static int MaskOfFlagNo(int bit){return 1u<<bit;}
typedef struct {int id,tag,params[6];} BattleMessageData;
static void BattlerSetAbility(BattleContext *c,u8 id,u8 ability);
'''
        source+=game.function_source('src/battle/battle_util.c','BattleScript_Call')+'\n'
        for function in ('BattleScriptGotoSubscript','BtlCmd_Call','BtlCmd_CompareVarToValue','BtlCmd_CompareMonDataToValue',
                         'BtlCmd_UpdateVar','BtlCmd_UpdateVar2','BtlCmd_GetTurnOrderBySpeed','BtlCmd_GoToIfValidMon',
                         'BtlCmd_IfSameSide','BtlCmd_CheckSubstitute','InitBattleMsgData','GetNicknameMessageNo',
                         'GetAbilityMessageNo','BattlerSetAbility'):
            source+=game.function_source('src/battle/battle_command.c',function)+'\n'
        return source+r'''
static int events[30],holders[30],spas[30],count,animations,stopDepth=-1;
static void event(BattleContext *c,int message) {
 assert(count<30);events[count]=message;holders[count]=c->battlerIdStatChange;
 spas[count++]=c->battleMons[c->battlerIdStatChange].statChanges[STAT_SPATK];
}
static void run(BattleContext *c,int member) {
 count=animations=0;ReadBattleScriptFromNarc(c,NARC_a_0_0_1,member);
 for(int step=0;step<500;step++) {
  switch(c->battleScriptBuffer[c->scriptSeqNo]) {
   case 14:case 17:c->scriptSeqNo++;break; // wait / attack presentation edge
   case 18:{c->scriptSeqNo++;BattleMessageData msg={0};InitBattleMsgData(c,&msg);
    assert(msg.id==1087&&msg.tag==TAG_NICKNAME_ABILITY);
    int b=c->battlerIdStatChange;
    assert(GetNicknameMessageNo(NULL,c,msg.params[0])==(b|(c->selectedMonIndex[b]<<8)));
    assert(GetAbilityMessageNo(NULL,c,msg.params[1])==172&&c->trainerAIData.abilities[b]==172);
    event(c,msg.id);break;}
   case 20:event(c,c->buffMsg.id);c->scriptSeqNo++;break;
   case 30:c->scriptSeqNo+=2;break;
   case 32:BtlCmd_CompareVarToValue(NULL,c);break;
   case 33:BtlCmd_CompareMonDataToValue(NULL,c);break;
   case 50:BtlCmd_UpdateVar(NULL,c);break;
   case 51:BtlCmd_ChangeStatStage(NULL,c);break;
   case 57:BtlCmd_UpdateVar2(NULL,c);break;
   case 60:BtlCmd_Call(NULL,c);break;
   case 69:assert(c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLER_CATEGORY_SIDE_EFFECT_MON);
    assert(c->battleScriptBuffer[c->scriptSeqNo+2]==12);animations++;c->scriptSeqNo+=3;break;
   case 71:c->scriptSeqNo+=3;break;
   case 23:c->scriptSeqNo+=2;break; // move animation presentation edge
   case 107:BtlCmd_GetTurnOrderBySpeed(NULL,c);break;
   case 108:BtlCmd_GoToIfValidMon(NULL,c);break;
   case 162:BtlCmd_IfSameSide(NULL,c);break;
   case 210:BtlCmd_CheckSubstitute(NULL,c);break;
   case 224:{int depth=c->scriptStackDepth;if(BtlCmd_EndScript(NULL,c))return;
    if(c->scriptStackDepth<depth&&c->scriptStackDepth==stopDepth)return;break;}
   default:assert(0);
  }
 }
 assert(0);
}
'''

    def test_real_presentation_returns_exact_original_frame_at_all_stack_depths(self):
        checks=r'''
int main(void) {
 for(int depth=0;depth<=4;depth++) {
  BattleContext c=fixture();c.scriptStackDepth=depth;c.statChangeType=SIDE_EFFECT_TYPE_INDIRECT;
  c.battlerIdTemp=3;c.msgTemp=101;c.abilityTemp=ABILITY_PRESSURE;c.selectedMonIndex[1]=4;
  c.battleStatus2=BATTLE_STATUS2_STAT_STAGE_CHANGE_SHOWN|BATTLE_STATUS2_UPDATE_STAT_STAGES;
  for(int d=0;d<4;d++){c.scriptStackNarcId[d]=NARC_a_0_0_1;c.scriptStackFileId[d]=129;c.scriptStackSeqNo[d]=30+d;}
  stopDepth=depth-1;run(&c,12);
  assert(c.scriptStackDepth==(depth?depth-1:0));
  if(depth)assert(c.scriptNarcId==NARC_a_0_0_1&&c.scriptFileId==129&&c.scriptSeqNo==30+depth-1);
  for(int d=0;d<4;d++)assert(c.scriptStackNarcId[d]==NARC_a_0_0_1&&c.scriptStackFileId[d]==129&&c.scriptStackSeqNo[d]==30+d);
  assert(count==3&&events[0]==762&&events[1]==1087&&events[2]==753&&animations==1);
  assert(c.battleMons[1].statChanges[STAT_ATK]==5&&c.battleMons[1].statChanges[STAT_SPATK]==8);
  assert(c.battlerIdAttacker==0&&c.battlerIdTarget==1&&c.battlerIdTemp==3&&c.battlerIdStatChange==1);
  assert(c.statChangeType==SIDE_EFFECT_TYPE_INDIRECT&&c.statChangeParam==22&&c.tempData==13);
  assert(c.msgTemp==101&&c.abilityTemp==ABILITY_PRESSURE&&c.battleStatus2==(BATTLE_STATUS2_STAT_STAGE_CHANGE_SHOWN|BATTLE_STATUS2_UPDATE_STAT_STAGES));
  assert(!c.statChangeFlag);
 }
 return 0;
}
'''
        self.compile_run(self.source()+checks,'-DQOL_MODERN_BATTLE=1','-Wno-unused-function','-Wno-sign-compare')

    def test_original_tickle_memento_and_intimidate_ordering_and_restoration(self):
        checks=r'''
int main(void) {
 for(int move=0;move<2;move++) {
  BattleContext c=fixture();c.moveNoCur=move?MOVE_MEMENTO:MOVE_TICKLE;
  if(move)c.battleMons[0].hp=0;
  c.selectedMonIndex[1]=4;c.tempData=999;
  run(&c,move?129:148);
  assert(c.battleMons[1].statChanges[STAT_ATK]==(move?4:5));
  assert(c.battleMons[1].statChanges[STAT_DEF]==(move?6:5));
  assert(c.battleMons[1].statChanges[STAT_SPATK]==(QOL_MODERN_BATTLE?(move?8:10):(move?4:6)));
  assert(c.battlerIdAttacker==0&&c.battlerIdTarget==1&&c.battlerIdTemp==3&&!c.scriptStackDepth);
  assert(count==(QOL_MODERN_BATTLE?6:2));
  if(QOL_MODERN_BATTLE) {
   assert(events[0]==(move?765:762)&&events[1]==1087&&events[2]==753);
   assert(events[3]==(move?765:762)&&events[4]==1087&&events[5]==753);
   assert(spas[0]==6&&spas[1]==8&&spas[2]==8);
   assert(spas[3]==(move?6:8)&&spas[4]==(move?8:10));
   assert(animations==2);
  }
 }
 for(int spa=0;spa<=12;spa++) {
  BattleContext c=fixture();c.battleMons[1].statChanges[STAT_SPATK]=spa;c.battleMons[0].hp=0;
  c.moveNoCur=MOVE_MEMENTO;run(&c,129);
  int first=spa+2;if(first>12)first=12;
  int second=first-2;if(second<0)second=0;second+=2;
  assert(c.battleMons[1].statChanges[STAT_SPATK]==(QOL_MODERN_BATTLE?second:(spa<2?0:spa-2)));
 }
 BattleContext c=fixture();c.battlerIdAttacker=3;c.battlerIdTarget=0;c.battlerIdTemp=2;
 c.battleMons[2].hp=c.battleMons[3].hp=100;c.battleMons[2].ability=ABILITY_INTIMIDATE;
 c.battleMons[3].ability=ABILITY_COMPETITIVE;c.turnOrder[0]=3;c.turnOrder[1]=0;c.turnOrder[2]=1;c.turnOrder[3]=2;
 c.selectedMonIndex[1]=4;c.selectedMonIndex[3]=5;
 run(&c,186);
 assert(c.battlerIdAttacker==3&&c.battlerIdTarget==0&&c.battlerIdTemp==2&&!c.scriptStackDepth);
 assert(c.battleMons[0].statChanges[STAT_ATK]==6&&c.battleMons[2].statChanges[STAT_ATK]==6);
 assert(c.battleMons[1].statChanges[STAT_ATK]==5&&c.battleMons[3].statChanges[STAT_ATK]==5);
 assert(c.battleMons[1].statChanges[STAT_SPATK]==(QOL_MODERN_BATTLE?8:6));
 assert(c.battleMons[3].statChanges[STAT_SPATK]==(QOL_MODERN_BATTLE?8:6));
 assert(count==(QOL_MODERN_BATTLE?6:2));
 if(QOL_MODERN_BATTLE){assert(holders[0]==3&&holders[3]==1);assert(events[0]==662&&events[3]==662);}
 return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(self.source()+checks,*flags,'-Wno-unused-function','-Wno-sign-compare')


if __name__=='__main__':unittest.main()
