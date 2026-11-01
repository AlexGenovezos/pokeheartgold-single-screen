"""Scoped Gen IX ability changes: actual native C and SDK script commands."""
from pathlib import Path
import importlib.util
import struct
import unittest
from unittest.mock import patch
import test_game_logic as game
import test_modern_competitive as competitive

ROOT=Path(__file__).resolve().parents[2]
PATHS={132:'TauntStart',186:'Intimidate',221:'NoStatusAbility'}


def native(name,file='battle_util'):
    return game.function_source(f'src/battle/{file}.c',name)+'\n'


class CureSelectionTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    def test_real_selector_attract_priority_taunt_gain_suppression_recovery_and_no_mold_borrow(self):
        source=r'''
#include <assert.h>
#include <stddef.h>
#include "qol_config.h"
#include "constants/abilities.h"
#include "constants/battle.h"
#define TRUE 1
#define FALSE 0
typedef int BOOL;typedef int BattleSystem;typedef unsigned char u8;
enum {NARC_a_0_0_1};
typedef struct {struct {int ability,status,status2,item,moveEffectFlags;
 struct {int tauntTurns,knockOffFlag;} moveEffectData;} battleMons[4];
 int msgTemp,battlerIdTemp,abilityTemp,commandNext,command,script,fieldCondition;} BattleContext;
static void ReadBattleScriptFromNarc(BattleContext *c,int n,int script){c->script=script;}
'''+native('GetBattlerAbility')+native('CheckStatusHealAbility')+r'''
int main(void) {
 for(int holder=0;holder<4;holder++)for(int attract=0;attract<2;attract++)
 for(int taunt=0;taunt<2;taunt++)for(int suppress=0;suppress<2;suppress++)for(int flag=0;flag<2;flag++) {
  BattleContext c={0};c.command=17;c.script=-1;c.msgTemp=-1;
  c.battleMons[holder].ability=ABILITY_OBLIVIOUS;c.battleMons[holder].status=STATUS_POISON;
  c.battleMons[holder].status2=attract?STATUS2_ATTRACT:0;
  c.battleMons[holder].moveEffectData.tauntTurns=taunt?4:0;
  c.battleMons[holder].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  int expected=!suppress&&(attract||(QOL_MODERN_BATTLE&&taunt));
  assert(CheckStatusHealAbility(NULL,&c,holder,flag)==expected);
  if(expected) {
   assert(c.msgTemp==(attract?6:7)&&c.battlerIdTemp==holder&&c.abilityTemp==ABILITY_OBLIVIOUS);
   assert(c.script==(flag?-1:221));assert(c.command==(flag?17:CONTROLLER_COMMAND_RUN_SCRIPT));
  }
  assert(c.battleMons[holder].status==STATUS_POISON);
  c.battleMons[holder].moveEffectFlags=0;
  assert(CheckStatusHealAbility(NULL,&c,holder,1)==(attract||(QOL_MODERN_BATTLE&&taunt)));
 }
 // Skill Swap/Role Play-style gain and unrelated Mold Breaker do not suppress own cures.
 BattleContext c={0};c.battleMons[0].ability=ABILITY_MOLD_BREAKER;
 c.battleMons[1].moveEffectData.tauntTurns=3;
 assert(!CheckStatusHealAbility(NULL,&c,1,1));
 c.battleMons[1].ability=ABILITY_OBLIVIOUS;
 assert(CheckStatusHealAbility(NULL,&c,1,1)==QOL_MODERN_BATTLE);
 return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source,*flags)

    def test_real_protect_and_semi_invulnerability_gate_taunt_before_effect_script(self):
        import test_modern_original_abilities as original
        source=original.accuracy_source().replace('command,commandNext,script,hpCalc;',
            'command,commandNext,script,hpCalc,sideEffectFlagsDirect,statChangeType,statChangeParam,statChangeFlag,battlerIdStatChange;')
        source+='#define GF_ASSERT assert\n#define NELEMS(a) (sizeof(a)/sizeof((a)[0]))\n'
        util=(ROOT/'src/battle/battle_util.c').read_text()
        table=util[util.index('static const int sMoveStatusChangeScripts'):].split('};',1)[0]+'};\n'
        source+=table
        source+=native('GetMoveStatusChangeScript')+native('BattleSystem_TryDirectSideEffect')
        checks=r'''
int main(void) {
 for(int ability=0;ability<2;ability++)for(int suppress=0;suppress<2;suppress++)for(int mold=0;mold<2;mold++)for(int fail=0;fail<4;fail++) {
  BattleContext c=fixture(MOVE_TAUNT);c.battleMons[1].ability=ability?ABILITY_OBLIVIOUS:0;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:0;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.trainerAIData.moveData[MOVE_TAUNT].power=0;
  c.sideEffectFlagsDirect=MOVE_SIDE_EFFECT_TO_DEFENDER|MOVE_SUBSCRIPT_PTR_TAUNT_START;
  if(fail==1)c.turnData[1].protectFlag=1;
  if(fail==2)c.battleMons[1].moveEffectFlags|=MOVE_EFFECT_FLAG_FLY;
  if(fail==3)c.moveStatusFlag=MOVE_STATUS_MISSED;
  BattleSystem_CheckMoveEffect(NULL,&c,0,1,MOVE_TAUNT);
  if(fail==1)assert(c.moveStatusFlag&MOVE_STATUS_PROTECTED);
  if(fail==2)assert(c.moveStatusFlag&MOVE_STATUS_SEMI_INVULNERABLE);
  int script=-1;assert(BattleSystem_TryDirectSideEffect(NULL,&c,&script)==!fail);
  assert(script==132&&!c.sideEffectFlagsDirect);
 }
 return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source+checks,*flags,'-Wno-unused-function','-Wno-unused-variable','-Wno-unused-but-set-variable','-Wno-sign-compare')


class ObliviousIntimidateResourceTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('oblivious_intimidate_scripts'),'Scoped script generator missing')
        import oblivious_intimidate_scripts
        return oblivious_intimidate_scripts

    def test_full_hash_wrong_member_duplicate_and_binary_drift_before_modified_compile(self):
        scripts=self.module()
        for member,name in PATHS.items():
            source=(ROOT/f'files/battledata/script/subscript/subscript_{member:04}_{name}.s').read_text()
            modern=scripts.modern_oblivious_intimidate_source(source,member)
            for changed in (source+'\n',source.replace('    .data','    .data\n'),modern):
                with self.assertRaisesRegex(ValueError,'expected source'):
                    scripts.modern_oblivious_intimidate_source(changed,member)
            other=next(i for i in PATHS if i!=member)
            with self.assertRaisesRegex(ValueError,'expected source'):
                scripts.modern_oblivious_intimidate_source(source,other)
            with patch.object(scripts,'compile_battle_script',return_value=b'wrong') as compiler:
                with self.assertRaisesRegex(ValueError,f'unchanged.*match.*{member}'):
                    scripts.modern_oblivious_intimidate_script(b'original',member)
                compiler.assert_called_once_with(source,scripts.ROOT)
            with patch.object(scripts,'compile_battle_script',side_effect=[b'original',b'modern']) as compiler:
                self.assertEqual(scripts.modern_oblivious_intimidate_script(b'original',member),b'modern')
                self.assertEqual([c.args[0] for c in compiler.call_args_list],[source,modern])
            original_read=Path.read_text
            def drift(path,*args,**kwargs):
                text=original_read(path,*args,**kwargs)
                return text+'\n' if path.name==f'subscript_{member:04}_{name}.s' else text
            with patch.object(Path,'read_text',drift),patch.object(scripts,'compile_battle_script') as compiler:
                with self.assertRaisesRegex(ValueError,'expected source'):
                    scripts.modern_oblivious_intimidate_script(b'original',member)
                compiler.assert_not_called()
        with self.assertRaises(ValueError):scripts.modern_oblivious_intimidate_source(source,12)

    def test_only_three_of_299_members_change_preserving_names_and_default_type_only(self):
        self.module()
        import modern_rom
        from nitro_data import pack_narc,unpack_narc
        members=[struct.pack('<I',i) for i in range(299)]
        with patch('modern_rom.modern_oblivious_intimidate_script',side_effect=lambda data,member:b'new'+data) as compiler:
            actual,names=unpack_narc(modern_rom.modern_oblivious_intimidate_resources(pack_narc(members)))
        self.assertEqual(compiler.call_count,3);self.assertEqual(names,unpack_narc(pack_narc(members))[1])
        self.assertEqual(len(actual),299)
        for i,before in enumerate(members):self.assertEqual(actual[i],b'new'+before if i in PATHS else before)
        for count in (298,300):
            with patch('modern_rom.modern_oblivious_intimidate_script') as compiler:
                with self.assertRaisesRegex(ValueError,'299'):
                    modern_rom.modern_oblivious_intimidate_resources(pack_narc((members+[b'extra'])[:count]))
                compiler.assert_not_called()
        paths={p:(0,0,3) for p in ('a/0/0/8','a/0/2/7','a/0/6/8')}
        for types in (False,True):
            with patch('modern_rom.rom_files',return_value=paths),patch('modern_rom.modern_type_resources',return_value=(b'i',b'm')),patch('modern_rom.modern_pokedex_resources',return_value=b'd'),patch('modern_rom.modern_oblivious_intimidate_resources') as transform,patch('modern_rom.replace_rom_files',side_effect=lambda rom,replacements:rom):
                self.assertEqual(modern_rom.make_modern_rom(b'rom',None,types=types),b'rom')
            transform.assert_not_called()


class ObliviousIntimidateSdkTests(unittest.TestCase):
    compile_run=game.GameLogicTests.compile_run

    @classmethod
    def setUpClass(cls):
        from battle_scripts import battle_script_tools,compile_battle_script
        from competitive_scripts import COMPETITIVE_SOURCE
        from nitro_data import unpack_narc
        try:battle_script_tools()
        except FileNotFoundError as error:raise unittest.SkipTest(str(error))
        cls.original=unpack_narc((ROOT/'files/battledata/script/subscript.narc').read_bytes())[0]
        cls.scripts={i:cls.original[i] for i in (12,104,132,186,190,221)}
        cls.scripts[298]=compile_battle_script(COMPETITIVE_SOURCE)
        if importlib.util.find_spec('oblivious_intimidate_scripts'):
            from oblivious_intimidate_scripts import modern_oblivious_intimidate_script
            for member in PATHS:cls.scripts[member]=modern_oblivious_intimidate_script(cls.original[member],member)

    def source(self,modern=True):
        helper=competitive.CompetitiveSdkTests()
        helper.scripts=dict(self.scripts)
        if not modern:
            for member in PATHS:helper.scripts[member]=self.original[member]
        source=helper.source().split('static int events[30]')[0]
        source=source.replace('int hp,ability,moveEffectFlags,status2,statChanges[8];',
            'int hp,maxHp,status,item,ability,moveEffectFlags,status2,statChanges[8];struct {int tauntTurns,knockOffFlag;} moveEffectData;')
        source=source.replace('battleStatus,battleStatus2,moveStatusFlag,',
            'battleStatus,battleStatus2,battlerIdAbility,calcTemp,hpCalc,command,commandNext,moveStatusFlag,')
        source=source.replace('MEMBER(12);MEMBER(129);MEMBER(148);MEMBER(186);MEMBER(298);',
            ''.join(f'MEMBER({i});' for i in helper.scripts))
        source=source.replace('case BATTLER_CATEGORY_MSG_BATTLER_TEMP:return c->battlerIdTemp;',
            'case BATTLER_CATEGORY_MSG_BATTLER_TEMP:case BATTLER_CATEGORY_MSG_TEMP:return c->battlerIdTemp;')
        source=source.replace('VAR(BSCRIPT_VAR_MSG_BATTLER_TEMP,battlerIdTemp);VAR(BSCRIPT_VAR_TEMP_DATA,tempData);',
            'VAR(BSCRIPT_VAR_MSG_BATTLER_TEMP,battlerIdTemp);VAR(BSCRIPT_VAR_TEMP_DATA,tempData);VAR(BSCRIPT_VAR_MESSAGE,msgTemp);VAR(BSCRIPT_VAR_CALC_TEMP,calcTemp);VAR(BSCRIPT_VAR_MSG_MOVE_TEMP,moveTemp);VAR(BSCRIPT_VAR_HP_CALC,hpCalc);VAR(BSCRIPT_VAR_FIELD_CONDITION,fieldCondition);')
        source=source.replace('if(var==BMON_DATA_HP)return c->battleMons[b].hp;',r'''
 if(var==BMON_DATA_HP)return c->battleMons[b].hp;
 if(var==BMON_DATA_STATUS)return c->battleMons[b].status;
 if(var==BMON_DATA_STATUS2)return c->battleMons[b].status2;
 if(var==BMON_DATA_TAUNTED_TURNS)return c->battleMons[b].moveEffectData.tauntTurns;
 if(var==BMON_DATA_TYPE_1||var==BMON_DATA_TYPE_2)return TYPE_NORMAL;
''')
        source+=r'''
static int icon[4],iconWrites,randomValue,randomCalls,calls,stopDepth=-1,events[40],params[40][4],count,statusFormats;
static void SetBattlerVar(BattleContext *c,int b,int v,void *p) {
 int val=*(int *)p;
 switch(v) {
 case BMON_DATA_STATUS:c->battleMons[b].status=val;break;
 case BMON_DATA_STATUS2:c->battleMons[b].status2=val;break;
 case BMON_DATA_TAUNTED_TURNS:c->battleMons[b].moveEffectData.tauntTurns=val;break;
 default:assert(0);
 }
}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int b){}
static void BattleController_EmitHealthbarStatus(BattleSystem *s,int b,int status){icon[b]=status;iconWrites++;}
static int BattleSystem_Random(BattleSystem *s){randomCalls++;return randomValue;}

'''
        for function,file in (
            ('CheckStatusHealAbility','battle_util'),('CheckAbilityActive','battle_util'),('DamageDivide','battle_util'),
            ('BtlCmd_Goto','battle_command'),('BtlCmd_CheckAbility','battle_command'),
            ('BtlCmd_CheckIgnorableAbility','battle_command'),('BtlCmd_UpdateMonData','battle_command'),
            ('BtlCmd_UpdateMonDataFromVar','battle_command'),('BtlCmd_Random','battle_command'),
            ('BtlCmd_SetHealthbarStatus','battle_command'),('BtlCmd_EndOfTurnWeatherEffect','battle_command'),
            ('GetMoveMessageNo','battle_command'),('GetStatusMessageNo','battle_command')):
            source+=native(function,file)
        return source+r'''
static void message(BattleContext *c) {
 BattleMessageData m={0};InitBattleMsgData(c,&m);assert(count<40);events[count]=m.id;
 switch(m.tag) {
 case TAG_NICKNAME_ABILITY_STATUS:
  // The native formatter's status names contain exactly seven entries.
  assert(c->msgTemp>=0&&c->msgTemp<=6);statusFormats++;
  params[count][2]=GetStatusMessageNo(c,m.params[2]);
  params[count][0]=GetNicknameMessageNo(NULL,c,m.params[0]);
  params[count][1]=GetAbilityMessageNo(NULL,c,m.params[1]);break;
 case TAG_NICKNAME_ABILITY_NICKNAME_ABILITY:
  for(int i=0;i<4;i++)params[count][i]=(i&1)?GetAbilityMessageNo(NULL,c,m.params[i]):GetNicknameMessageNo(NULL,c,m.params[i]);break;
 case TAG_NICKNAME_ABILITY_MOVE:
  params[count][0]=GetNicknameMessageNo(NULL,c,m.params[0]);
  params[count][1]=GetAbilityMessageNo(NULL,c,m.params[1]);
  params[count][2]=GetMoveMessageNo(c,m.params[2]);break;
 case TAG_NICKNAME_ABILITY:
  params[count][0]=GetNicknameMessageNo(NULL,c,m.params[0]);
  params[count][1]=GetAbilityMessageNo(NULL,c,m.params[1]);break;
 case TAG_NICKNAME_MOVE:
  params[count][0]=GetNicknameMessageNo(NULL,c,m.params[0]);
  params[count][1]=GetMoveMessageNo(c,m.params[1]);break;
 case TAG_NICKNAME:params[count][0]=GetNicknameMessageNo(NULL,c,m.params[0]);break;
 default:assert(0);
 }
 count++;
}
static void run(BattleContext *c,int member) {
 count=calls=iconWrites=statusFormats=randomCalls=0;ReadBattleScriptFromNarc(c,NARC_a_0_0_1,member);
 for(int steps=0;steps<1000;steps++) {
  switch(c->battleScriptBuffer[c->scriptSeqNo]) {
  case 14:case 17:c->scriptSeqNo++;break;
  case 18:c->scriptSeqNo++;message(c);break;
  case 20:events[count++]=c->buffMsg.id;c->scriptSeqNo++;break;
  case 23:c->scriptSeqNo+=2;break;
  case 30:c->scriptSeqNo+=2;break;
  case 32:BtlCmd_CompareVarToValue(NULL,c);break;
  case 33:BtlCmd_CompareMonDataToValue(NULL,c);break;
  case 50:BtlCmd_UpdateVar(NULL,c);break;
  case 51:BtlCmd_ChangeStatStage(NULL,c);break;
  case 52:BtlCmd_UpdateMonData(NULL,c);break;
  case 55:BtlCmd_CheckAbility(NULL,c);break;
  case 56:BtlCmd_Random(NULL,c);break;
  case 57:BtlCmd_UpdateVar2(NULL,c);break;
  case 58:BtlCmd_UpdateMonDataFromVar(NULL,c);break;
  case 59:BtlCmd_Goto(NULL,c);break;
  case 60:
   calls++;
   if(c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLE_SUBSCRIPT_ATTACK_MESSAGE_AND_ANIMATION||c->battleScriptBuffer[c->scriptSeqNo+1]==BATTLE_SUBSCRIPT_SHOW_PREPARED_MESSAGE)c->scriptSeqNo+=2;
   else BtlCmd_Call(NULL,c);break;
  case 69:c->scriptSeqNo+=3;break;
  case 70:c->scriptSeqNo+=3;break;
  case 71:c->scriptSeqNo+=3;break;
  case 66:BtlCmd_SetHealthbarStatus(NULL,c);break;
  case 107:BtlCmd_GetTurnOrderBySpeed(NULL,c);break;
  case 108:BtlCmd_GoToIfValidMon(NULL,c);break;
  case 109:BtlCmd_EndOfTurnWeatherEffect(NULL,c);break;
  case 162:BtlCmd_IfSameSide(NULL,c);break;
  case 210:BtlCmd_CheckSubstitute(NULL,c);break;
  case 161:BtlCmd_CheckIgnorableAbility(NULL,c);break;
  case 224:{int depth=c->scriptStackDepth;if(BtlCmd_EndScript(NULL,c))return;
   if(c->scriptStackDepth<depth&&c->scriptStackDepth==stopDepth)return;break;}
  default:assert(0);
  }
 }
 assert(0);
}
static BattleContext setup(void) {
 BattleContext c=fixture();
 for(int b=0;b<4;b++){c.battleMons[b].hp=c.battleMons[b].maxHp=100;c.battleMons[b].ability=0;c.turnOrder[b]=b;c.selectedMonIndex[b]=b+1;icon[b]=9;}
 return c;
}
'''

    def check(self,checks,modern=True):
        self.compile_run(self.source(modern)+checks,*(['-DQOL_MODERN_BATTLE=1'] if modern else []),'-Wno-unused-function','-Wno-sign-compare','-Wno-misleading-indentation','-Wno-return-type')

    def test_cure_script_volatile_primary_icons_ai_priority_gain_and_termination(self):
        self.check(r'''
int main(void) {
 for(int holder=0;holder<4;holder++)for(int attract=0;attract<2;attract++)for(int taunt=0;taunt<2;taunt++) {
  BattleContext c=setup();c.battleMons[holder].ability=ABILITY_OBLIVIOUS;
  c.battleMons[holder].status=STATUS_POISON;c.battleMons[holder].status2=STATUS2_NIGHTMARE|(attract?STATUS2_ATTRACT:0);
  c.battleMons[holder].moveEffectData.tauntTurns=taunt?4:0;
  int passes=0;
  while(CheckStatusHealAbility(NULL,&c,holder,1)) {
   assert(passes++<2);int msg=c.msgTemp;run(&c,221);
   assert(c.battleMons[holder].status==STATUS_POISON&&icon[holder]==9&&!iconWrites);
   assert(c.battleMons[holder].status2==STATUS2_NIGHTMARE);
   assert(c.trainerAIData.abilities[holder]==ABILITY_OBLIVIOUS&&!calls&&!c.scriptStackDepth);
   assert(params[0][0]==(holder|((holder+1)<<8))&&params[0][1]==ABILITY_OBLIVIOUS);
   if(msg==7){assert(!statusFormats&&count==2&&events[0]==1087&&events[1]==1257);assert(params[1][1]==MOVE_TAUNT);}
   else assert(msg==6&&statusFormats==1&&count==1&&events[0]==740);
  }
  assert(passes==attract+taunt&&!c.battleMons[holder].moveEffectData.tauntTurns);
 }
 // Confusion is volatile too; primary cures still clear icons and sleeping Nightmare.
 int abilities[]={ABILITY_OWN_TEMPO,ABILITY_IMMUNITY,ABILITY_LIMBER,ABILITY_INSOMNIA,ABILITY_VITAL_SPIRIT,ABILITY_WATER_VEIL,ABILITY_MAGMA_ARMOR};
 int statuses[]={STATUS_POISON,STATUS_POISON,STATUS_PARALYSIS,2,3,STATUS_BURN,STATUS_FREEZE};
 for(int i=0;i<7;i++) {
  BattleContext c=setup();c.battleMons[1].ability=abilities[i];c.battleMons[1].status=statuses[i];
  c.battleMons[1].status2=STATUS2_NIGHTMARE|(i==0?STATUS2_CONFUSION:0);
  assert(CheckStatusHealAbility(NULL,&c,1,1));run(&c,221);
  assert(c.battleMons[1].status==(i==0?STATUS_POISON:0));assert(iconWrites==(i!=0));
  assert(icon[1]==(i==0?9:0));if(i==3||i==4)assert(!(c.battleMons[1].status2&STATUS2_NIGHTMARE));
  assert(c.trainerAIData.abilities[1]==abilities[i]&&!CheckStatusHealAbility(NULL,&c,1,1));
 }
 for(int recovery=0;recovery<2;recovery++) {
  BattleContext c=setup();c.battleMons[0].ability=ABILITY_MOLD_BREAKER;
  c.battleMons[1].status=STATUS_POISON;c.battleMons[1].moveEffectData.tauntTurns=4;
  c.battleMons[1].ability=recovery?ABILITY_OBLIVIOUS:ABILITY_NONE;
  c.battleMons[1].moveEffectFlags=recovery?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  assert(!CheckStatusHealAbility(NULL,&c,1,1));
  c.battleMons[1].ability=ABILITY_OBLIVIOUS;c.battleMons[1].moveEffectFlags=0;
  assert(CheckStatusHealAbility(NULL,&c,1,1));run(&c,221);
  assert(c.battleMons[1].status==STATUS_POISON&&icon[1]==9&&!CheckStatusHealAbility(NULL,&c,1,1));
 }
 for(int depth=0;depth<=4;depth++) {
  BattleContext c=setup();c.battleMons[1].ability=ABILITY_OBLIVIOUS;
  c.battleMons[1].moveEffectData.tauntTurns=4;c.scriptStackDepth=depth;
  for(int d=0;d<4;d++){c.scriptStackNarcId[d]=NARC_a_0_0_1;c.scriptStackFileId[d]=12;c.scriptStackSeqNo[d]=100+d;}
  assert(CheckStatusHealAbility(NULL,&c,1,1));stopDepth=depth-1;run(&c,221);
  assert(c.scriptStackDepth==(depth?depth-1:0)&&!calls);
  for(int d=0;d<4;d++)assert(c.scriptStackFileId[d]==12&&c.scriptStackSeqNo[d]==100+d);
  if(depth)assert(c.scriptFileId==12&&c.scriptSeqNo==100+depth-1);
 }
 stopDepth=-1;
 return 0;
}
''')

    def test_taunt_ignorable_ability_priority_existing_failures_and_duration(self):
        checks=r'''
int main(void) {
 for(int ability=0;ability<2;ability++)for(int suppress=0;suppress<2;suppress++)for(int mold=0;mold<2;mold++)
 for(int already=0;already<2;already++)for(int miss=0;miss<3;miss++)for(int roll=0;roll<3;roll++) {
  BattleContext c=setup();c.moveNoCur=MOVE_TAUNT;
  c.battleMons[1].ability=ability?ABILITY_OBLIVIOUS:ABILITY_NONE;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:0;
  c.battleMons[1].moveEffectData.tauntTurns=already?2:0;
  c.moveStatusFlag=miss==1?MOVE_STATUS_MISSED:miss==2?MOVE_STATUS_SEMI_INVULNERABLE:0;randomValue=roll;
  run(&c,132);int immune=QOL_MODERN_BATTLE&&ability&&!suppress&&!mold;
  if(immune) {
   assert(count==1&&events[0]==714&&!calls&&!randomCalls);
   assert(params[0][0]==(1|(2<<8))&&params[0][1]==ABILITY_OBLIVIOUS&&params[0][2]==MOVE_TAUNT);
   assert(c.trainerAIData.abilities[1]==ABILITY_OBLIVIOUS);
   assert(c.moveStatusFlag&MOVE_STATUS_NO_MORE_WORK);
   assert(c.battleMons[1].moveEffectData.tauntTurns==(already?2:0));
  } else if(already||miss)assert(c.moveStatusFlag&MOVE_STATUS_FAILED);
  else assert(c.battleMons[1].moveEffectData.tauntTurns==3+roll&&randomCalls==1&&calls==1&&events[0]==500);
 }
 return 0;
}
'''
        self.check(checks);self.check(checks,False)

    def test_intimidate_immunities_doubles_suppression_other_competitive_and_stack(self):
        self.check(r'''
int main(void) {
 int blockers[]={ABILITY_INNER_FOCUS,ABILITY_OWN_TEMPO,ABILITY_OBLIVIOUS,ABILITY_SCRAPPY};
 for(int a=0;a<4;a++)for(int owner=0;owner<4;owner++)for(int recipient=0;recipient<4;recipient++)
 for(int suppress=0;suppress<2;suppress++)for(int reverse=0;reverse<2;reverse++)for(int reason=0;reason<3;reason++) {
  if((owner&1)==(recipient&1))continue;
  int other=recipient^2;
  BattleContext c=setup();c.battlerIdTemp=owner;c.battlerIdAttacker=owner^2;c.battlerIdTarget=owner^2;
  c.battleMons[owner].ability=ABILITY_INTIMIDATE;c.battleMons[recipient].ability=blockers[a];
  c.battleMons[recipient].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[other].ability=ABILITY_COMPETITIVE;
  c.battleMons[owner^2].ability=ABILITY_MOLD_BREAKER; // unrelated actor cannot suppress this event
  if(reason==1)c.battleMons[recipient].status2=STATUS2_SUBSTITUTE;
  if(reason==2)c.battleMons[recipient].hp=0;
  for(int i=0;i<4;i++)c.turnOrder[i]=reverse?3-i:i;
  run(&c,186);
  int blocked=!suppress||reason;
  assert(c.battleMons[recipient].statChanges[STAT_ATK]==(blocked?6:5));
  assert(c.battleMons[recipient].statChanges[STAT_SPATK]==6);
  assert(c.battleMons[other].statChanges[STAT_ATK]==5&&c.battleMons[other].statChanges[STAT_SPATK]==8);
  assert(c.battleMons[owner].statChanges[STAT_ATK]==6&&c.battleMons[owner^2].statChanges[STAT_ATK]==6);
  assert(c.battlerIdAttacker==(owner^2)&&c.battlerIdTemp==owner&&c.battlerIdTarget==(owner^2)&&!c.scriptStackDepth&&!c.statChangeFlag);
  assert(calls==1+(!blocked)); // blocked branch adds no Call to the native stat subscript
  int found=0,boosts=0;
  for(int e=0;e<count;e++) {
   if(events[e]==727){found++;assert(params[e][0]==(recipient|((recipient+1)<<8))&&params[e][1]==blockers[a]);assert(params[e][2]==(owner|((owner+1)<<8))&&params[e][3]==ABILITY_INTIMIDATE);}
   if(events[e]==1087)boosts++;
  }
  assert(found==(!suppress&&!reason)&&boosts==1);
  if(found)assert(c.trainerAIData.abilities[recipient]==blockers[a]&&c.trainerAIData.abilities[owner]==ABILITY_INTIMIDATE);
 }
 // These abilities do not block an ordinary Growl stat decrease.
 for(int a=0;a<4;a++) {BattleContext c=setup();c.battleMons[1].ability=blockers[a];c.moveNoCur=MOVE_GROWL;c.statChangeType=SIDE_EFFECT_TYPE_DIRECT;run(&c,12);assert(c.battleMons[1].statChanges[STAT_ATK]==5);}
 return 0;
}
''')

    def test_native_hydration_weather_and_original_104_190_cure_all_primary_statuses(self):
        self.check(r'''
int main(void) {
 int statuses[]={1,7,STATUS_POISON,STATUS_BAD_POISON,STATUS_BAD_POISON|(5<<8),STATUS_BURN,STATUS_PARALYSIS,STATUS_FREEZE,0};
 for(int st=0;st<9;st++)for(int suppress=0;suppress<2;suppress++)for(int weather=0;weather<3;weather++)
 for(int blocker=0;blocker<3;blocker++)for(int blockedSuppressed=0;blockedSuppressed<2;blockedSuppressed++)for(int ko=0;ko<2;ko++) {
  BattleContext c=setup();c.battleMons[1].ability=ABILITY_HYDRATION;c.battleMons[1].hp=ko?0:100;
  c.battleMons[1].status=statuses[st];c.battleMons[1].status2=STATUS2_NIGHTMARE;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[2].ability=blocker==1?ABILITY_CLOUD_NINE:blocker==2?ABILITY_AIR_LOCK:0;
  c.battleMons[2].moveEffectFlags=blockedSuppressed?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.fieldCondition=weather==1?FIELD_CONDITION_RAIN:weather==2?FIELD_CONDITION_RAIN_PERMANENT:0;
  // Original104 scans living battlers and calls190 only when the real weather command sets tempData1.
  run(&c,104);int cure=statuses[st]&&!suppress&&weather&&(!blocker||blockedSuppressed)&&!ko;
  assert(c.battleMons[1].status==(cure?0:statuses[st]));
  assert(c.battleMons[1].status2==(cure?0:STATUS2_NIGHTMARE));
  assert(icon[1]==(cure?0:9)&&iconWrites==cure&&!c.scriptStackDepth);
  assert(c.trainerAIData.abilities[1]==(cure?ABILITY_HYDRATION:0));
  assert(count==cure);if(cure)assert(events[0]==717&&params[0][0]==(1|(2<<8))&&params[0][1]==ABILITY_HYDRATION);
 }
 return 0;
}
''')


if __name__=='__main__':unittest.main()
