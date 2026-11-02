"""Execute real Sturdy damage hooks and assembled survival-message scripts."""
from pathlib import Path
import importlib.util
import struct
from unittest.mock import patch
import unittest
import test_game_logic as game
import test_modern_moves

ROOT = Path(__file__).resolve().parents[2]


def damage_source():
    return test_modern_moves.ModernMoveTests().source() + r'''
#include "constants/battle.h"
#include "constants/move_effects.h"
#include "constants/items.h"
#include "constants/abilities.h"
#include "constants/battle_subscript.h"
#define GF_ASSERT assert
typedef int BattleSystem;
enum {NARC_a_0_0_1,GAME_STAT_ALLIES_DAMAGED};
typedef struct {
    int hp,maxHp,hitCount,ability,item,itemMod; unsigned status2,moveEffectFlags,status;
    struct {int substituteHp;} moveEffectData;
} Mon;
typedef struct {
    Mon battleMons[4];
    struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
    struct {
        int shellBellDamage,statusFlags,endureItemFlag,physicalDamage,battlerIdPhysicalAttacker,
            specialDamage,battlerIdSpecialAttacker,moldBreakerFlag;
    } selfTurnData[4];
    struct {
        int endureFlag,physicalDamage[4],battlerIdPhysicalDamage,battlerBitPhysicalDamage,
            specialDamage[4],battlerIdSpecialDamage,battlerBitSpecialDamage,lastDamageTaken,battlerIdLastDamage;
    } turnData[4];
    unsigned moveStatusFlag,battleStatus,fieldCondition;
    int damage,battlerIdAttacker,battlerIdTarget,battlerIdStoredDamage[4],
        hitDamage,battlerIdTemp,command,commandNext,moveNoCur,storedDamage[4],hpCalc,script,
        scriptNarcId,scriptFileId,pos,words[2],multiHitCountTemp,multiHitCount,battlerIdFainted,criticalMultiplier;
} BattleContext;
static int randomCalls,randomResult;
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return c->battleMons[b].item;}
static int GetHeldItemModifier(BattleContext *c,int b,int n){return c->battleMons[b].itemMod;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b;}
static void BattleController_EmitIncrementGameStat(BattleSystem *s,int b,int a,int stat){}
static void ReadBattleScriptFromNarc(BattleContext *c,int narc,int script){c->script=script;}
static int BattleSystem_Random(BattleSystem *s){randomCalls++;return randomResult;}
static int MaskOfFlagNo(int n){return 1<<n;}
static void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;}
static int BattleScriptReadWord(BattleContext *c){return c->words[c->pos++];}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){return side==BATTLER_CATEGORY_ATTACKER?c->battlerIdAttacker:c->battlerIdTemp;}
''' + '\n'.join(game.function_source('src/battle/battle_util.c', name) for name in (
        'GetBattlerAbility', 'CheckBattlerAbilityIfNotIgnored', 'BattleContext_ResetMoveStatus')) + '\n' + '\n'.join(
        game.function_source(path, name) for path, name in (
            ('src/battle/battle_controller_player.c', 'BattleControllerPlayer_HpCalc'),
            ('src/battle/battle_controller_player.c', 'BattleControllerPlayer_TryFollowupMessage'),
            ('src/battle/battle_command.c', 'BtlCmd_CheckHoldOnWith1HP'))) + r'''
static BattleContext fixture(int hp,int damage) {
    BattleContext c={0};c.battlerIdTarget=c.battlerIdTemp=1;c.battlerIdFainted=BATTLER_NONE;
    c.moveNoCur=MOVE_TACKLE;c.damage=c.hpCalc=damage;c.battleMons[1].hp=hp;c.battleMons[1].maxHp=100;
    c.battleMons[1].ability=ABILITY_STURDY;c.battleMons[1].itemMod=10;
    c.trainerAIData.moveData[c.moveNoCur].category=CATEGORY_PHYSICAL;
    randomCalls=0;randomResult=0;return c;
}
'''


class SturdyDamageTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def check(self, main):
        for flags in ((), ('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(damage_source() + main, *flags, '-Wno-unused-function')

    def test_direct_lethal_damage_uses_sturdy_before_items_and_respects_existing_guards(self):
        self.check(r'''
int main(void) {
    const int items[]={0,HOLD_EFFECT_ENDURE,HOLD_EFFECT_MAYBE_ENDURE};
    const int hps[]={0,1,99,100};const int damage[]={-1,-99,-100,-150};
    for(int h=0;h<4;h++)for(int d=0;d<4;d++)for(int a=0;a<2;a++)
    for(int mold=0;mold<2;mold++)for(int suppress=0;suppress<2;suppress++)
    for(int endure=0;endure<2;endure++)for(int item=0;item<3;item++)
    for(int sub=0;sub<2;sub++)for(int swipe=0;swipe<2;swipe++) {
        BattleContext c=fixture(hps[h],damage[d]);
        c.battleMons[1].ability=a?ABILITY_STURDY:ABILITY_NONE;
        c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
        c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
        c.battleMons[1].item=items[item];c.turnData[1].endureFlag=endure;
        c.battleMons[1].status2=sub?STATUS2_SUBSTITUTE:0;c.battleMons[1].moveEffectData.substituteHp=20;
        c.trainerAIData.moveData[c.moveNoCur].effect=swipe?MOVE_EFFECT_LEAVE_WITH_1_HP:0;
        int lethal=hps[h]+damage[d]<=0;
        int sturdy=QOL_MODERN_BATTLE&&a&&!mold&&!suppress&&!endure&&!sub&&!swipe&&hps[h]==100&&lethal;
        BattleControllerPlayer_HpCalc(NULL,&c);
        assert(!!(c.moveStatusFlag&(1u<<21))==sturdy);
        if(sub) {assert(c.script==BATTLE_SUBSCRIPT_HIT_SUBSTITUTE);continue;}
        int saved=lethal&&(swipe||endure||sturdy||item==2||(item==1&&hps[h]==100));
        assert(c.hpCalc==(saved?1-hps[h]:damage[d]));
        assert(!!(c.moveStatusFlag&MOVE_STATUS_ENDURED)==(lethal&&!swipe&&endure));
        assert(!!(c.moveStatusFlag&MOVE_STATUS_ENDURED_ITEM)==(lethal&&!swipe&&!endure&&!sturdy&&(item==2||(item==1&&hps[h]==100))));
        if(sturdy) {assert(!c.selfTurnData[1].endureItemFlag);assert(randomCalls==0);}
        assert(!(c.moveStatusFlag&MOVE_STATUS_DID_NOT_HIT));
    }
    return 0;
}
''')

    def test_sturdy_message_runs_on_first_multihit_then_next_hit_can_ko(self):
        self.check(r'''
int main(void) {
    BattleContext c=fixture(100,-100);c.multiHitCountTemp=c.multiHitCount=2;
    BattleControllerPlayer_HpCalc(NULL,&c);
    if(QOL_MODERN_BATTLE) {
        assert(c.hpCalc==-99);assert(BattleControllerPlayer_TryFollowupMessage(NULL,&c));
        assert(c.script==BATTLE_SUBSCRIPT_MOVE_FOLLOWUP_MESSAGE);
        assert(c.moveStatusFlag&(1u<<22));
    }
    c.battleMons[1].hp=1;BattleContext_ResetMoveStatus(NULL,&c);
    assert(!c.moveStatusFlag);c.damage=-100;
    BattleControllerPlayer_HpCalc(NULL,&c);assert(c.hpCalc==-100);assert(!c.moveStatusFlag);
    return 0;
}
''')

    def test_shared_survival_command_covers_pursuit_and_delayed_damage_but_excludes_confusion(self):
        self.check(r'''
int main(void) {
    const int scripts[]={121,153,39};
    for(int script=0;script<3;script++)for(int mold=0;mold<2;mold++)
    for(int suppress=0;suppress<2;suppress++)for(int item=0;item<2;item++) {
        BattleContext c=fixture(100,-150);c.scriptNarcId=NARC_a_0_0_1;c.scriptFileId=scripts[script];
        c.words[1]=script==2?BATTLER_CATEGORY_ATTACKER:BATTLER_CATEGORY_MSG_TEMP;
        if(script==2)c.battleMons[0]=c.battleMons[1];
        c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:(script==2?ABILITY_STURDY:ABILITY_NONE);
        c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
        int target=script==2?0:1;c.battleMons[target].item=item?HOLD_EFFECT_ENDURE:0;
        int sturdy=QOL_MODERN_BATTLE&&script!=2&&!suppress&&(script==0||!mold);
        assert(!BtlCmd_CheckHoldOnWith1HP(NULL,&c));assert(c.pos==2);
        assert(c.hpCalc==((sturdy||item)?-99:-150));
        assert(!!(c.moveStatusFlag&(1u<<21))==sturdy);
        assert(!!(c.moveStatusFlag&MOVE_STATUS_ENDURED_ITEM)==(!sturdy&&item));
    }
    return 0;
}
''')

    def test_single_hp_sound_bypass_and_shared_nonlethal_damage_boundaries(self):
        self.check(r"""
int main(void) {
    BattleContext c=fixture(1,-1);c.battleMons[1].maxHp=1;
    BattleControllerPlayer_HpCalc(NULL,&c);assert(c.hpCalc==(QOL_MODERN_BATTLE?0:-1));
    assert(!!(c.moveStatusFlag&MOVE_STATUS_ENDURED_ABILITY)==QOL_MODERN_BATTLE);
    c=fixture(100,-150);c.moveNoCur=MOVE_HYPER_VOICE;c.battleMons[1].status2=STATUS2_SUBSTITUTE;
    c.battleMons[1].moveEffectData.substituteHp=20;
    BattleControllerPlayer_HpCalc(NULL,&c);
    assert(c.script==(QOL_MODERN_BATTLE?BATTLE_SUBSCRIPT_UPDATE_HP:BATTLE_SUBSCRIPT_HIT_SUBSTITUTE));
    if(QOL_MODERN_BATTLE)assert(c.hpCalc==-99&&(c.moveStatusFlag&MOVE_STATUS_ENDURED_ABILITY));
    for(int script=121;script<=153;script+=32)for(int hp=1;hp<=100;hp++)for(int damage=0;damage<=151;damage++) {
        c=fixture(hp,-damage);c.scriptNarcId=NARC_a_0_0_1;c.scriptFileId=script;
        c.words[1]=BATTLER_CATEGORY_MSG_TEMP;BtlCmd_CheckHoldOnWith1HP(NULL,&c);
        int saved=QOL_MODERN_BATTLE&&hp==100&&damage>=100;
        assert(c.hpCalc==(saved?-99:-damage));
        assert(!!(c.moveStatusFlag&MOVE_STATUS_ENDURED_ABILITY)==saved);
    }
    c=fixture(100,-150);c.scriptNarcId=NARC_a_0_0_1+1;c.scriptFileId=121;
    c.words[1]=BATTLER_CATEGORY_MSG_TEMP;BtlCmd_CheckHoldOnWith1HP(NULL,&c);
    assert(c.hpCalc==-150&&!(c.moveStatusFlag&MOVE_STATUS_ENDURED_ABILITY));
    return 0;
}
""")

    def test_script_transforms_are_available_and_reject_source_drift(self):
        self.assertIsNotNone(importlib.util.find_spec('sturdy_scripts'), 'Sturdy script generation is missing')
        import sturdy_scripts as scripts
        for member, name in ((21, 'MoveFollowupMessage'), (121, 'FutureSightDamage')):
            source=(ROOT/f'files/battledata/script/subscript/subscript_{member:04}_{name}.s').read_text()
            updated=scripts.modern_sturdy_source(source, member)
            self.assertIn('PrintMessage msg_0197_00625, TAG_NICKNAME_ABILITY',updated)
            for changed in (source+'\n',source.replace('    Wait ', '    Wait  ',1),updated):
                with self.assertRaises(ValueError):scripts.modern_sturdy_source(changed, member)
        with self.assertRaises(ValueError):scripts.modern_sturdy_source('',39)


class SturdyResourceTests(unittest.TestCase):
    def test_script_compiler_parity_guard_and_archive_member_isolation(self):
        import sturdy_scripts as scripts
        import modern_rom
        from nitro_data import pack_narc,unpack_narc
        for member in scripts.STURDY_SCRIPTS:
            with patch.object(scripts,'compile_battle_script',return_value=b'wrong') as compiler:
                with self.assertRaisesRegex(ValueError,f'unchanged.*match.*{member}'):
                    scripts.modern_sturdy_script(b'original',member)
                self.assertEqual(compiler.call_count,1)
        members=[bytes([i])*4 for i in range(200)]
        with patch('modern_rom.modern_sturdy_script',side_effect=lambda data,member:b'new'+data):
            updated,names=unpack_narc(modern_rom.modern_sturdy_resources(pack_narc(members)))
        self.assertEqual(names,unpack_narc(pack_narc(members))[1])
        for i,before in enumerate(members):self.assertEqual(updated[i],b'new'+before if i in (21,121) else before)
        with self.assertRaisesRegex(ValueError,'absent'):
            modern_rom.modern_sturdy_resources(pack_narc(members[:121]))


class SturdySdkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sturdy_scripts as scripts
        from battle_scripts import battle_script_tools
        from nitro_data import unpack_narc
        try:battle_script_tools()
        except FileNotFoundError as error:raise unittest.SkipTest(str(error))
        archive=ROOT/'files/battledata/script/subscript.narc'
        if not archive.is_file():raise unittest.SkipTest('Original battle subscript archive is absent')
        originals=unpack_narc(archive.read_bytes())[0]
        cls.bytecode={member:(originals[member],scripts.modern_sturdy_script(originals[member],member))
                      for member in scripts.STURDY_SCRIPTS}

    def test_compiled_messages_consume_items_only_when_items_save_the_recipient(self):
        declarations=r"""
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "qol_config.h"
#include "constants/battle.h"
#include "constants/battle_script.h"
#include "constants/battle_subscript.h"
#include "constants/abilities.h"
#include "constants/items.h"
#include "constants/message_tags.h"
#include "constants/opcode.h"
typedef int BOOL;typedef uint32_t u32;typedef uint8_t u8;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
typedef int BattleSystem;
enum {NARC_a_0_0_1};
typedef struct {u32 id;int tag,params[6];} BattleMessageData;
typedef struct {
    const u32 *words;int pos,length,vars[70];
    struct {int hp,maxHp,item,ability;unsigned status2,moveEffectFlags;} battleMons[4];
    struct {int endureFlag;} turnData[4];
    struct {int moldBreakerFlag;} selfTurnData[4];
    unsigned moveStatusFlag,battleStatus,fieldCondition;int fieldSideConditionFlags[2];
    int hpCalc,scriptNarcId,scriptFileId,battlerIdAttacker,battlerIdTarget,battlerIdTemp,
        abilityTemp,battlerIdAbility,recycleItem[4],selectedMonIndex[4],switchMonIndex[4],
        count,updates,animations,messages[8],tags[8],nicknames[8],abilities[8];
} BattleContext;
static void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;assert(c->pos>=0&&c->pos<=c->length);}
static int BattleScriptReadWord(BattleContext *c){assert(c->pos<c->length);return c->words[c->pos++];}
static void *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int v){
    if(v==BSCRIPT_VAR_MOVE_STATUS_FLAGS)return (int *)&c->moveStatusFlag;
    if(v==BSCRIPT_VAR_BATTLE_STATUS)return (int *)&c->battleStatus;
    if(v==BSCRIPT_VAR_HP_CALC)return &c->hpCalc;
    assert(v>=0&&v<70);return &c->vars[v];}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){
    if(side==BATTLER_CATEGORY_DEFENDER)return c->battlerIdTarget;
    if(side==BATTLER_CATEGORY_ATTACKER)return c->battlerIdAttacker;
    assert(side==BATTLER_CATEGORY_MSG_TEMP||side==BATTLER_CATEGORY_MSG_BATTLER_TEMP);return c->battlerIdTemp;}
static int GetBattlerHeldItemEffect(BattleContext *c,int id){return c->battleMons[id].item;}
static int GetHeldItemModifier(BattleContext *c,int id,int slot){return 10;}
static int BattleSystem_Random(BattleSystem *s){return 0;}
static int MaskOfFlagNo(int n){return 1u<<n;}
static int GetBattlerVar(BattleContext *c,int id,int field,void *unused){
    if(field==BMON_DATA_SUBSTITUTE_HP)return 20;
    if(field==BMON_DATA_HP)return c->battleMons[id].hp;
    if(field==BMON_DATA_STATUS2)return c->battleMons[id].status2;
    assert(0);return 0;}
static void CopyBattleMonToPartyMon(BattleSystem *s,BattleContext *c,int id){}
static void BattlerSetAbility(BattleContext *c,int id,int ability){}
static int BattleSystem_GetFieldSide(BattleSystem *s,int id){return id&1;}
static void Qol_QueueTailwindStart(BattleSystem *s,BattleContext *c,int side){assert(!"Unexpected Tailwind queue in Sturdy fixture");}
"""
        functions='\n'.join(game.function_source('src/battle/battle_util.c',name) for name in (
            'GetBattlerAbility','CheckBattlerAbilityIfNotIgnored'))+'\n'+'\n'.join(
            game.function_source('src/battle/battle_command.c',name) for name in (
                'BtlCmd_CompareVarToValue','BtlCmd_CompareMonDataToValue','BtlCmd_CompareMonDataToVar','BtlCmd_UpdateVar',
                'BtlCmd_Goto','BtlCmd_CheckItemHoldEffect','BtlCmd_RemoveItem','BtlCmd_CheckHoldOnWith1HP',
                'InitBattleMsgData','GetNicknameMessageNo','GetAbilityMessageNo'))
        arrays=[]
        for member,pair in self.bytecode.items():
            for updated,data in enumerate(pair):
                words=','.join(str(word)+'u' for word in struct.unpack('<'+'I'*(len(data)//4),data))
                arrays.append(f'static const u32 script{member}_{updated}[]={{ {words} }};')
        checks=r"""
static BattleContext run(int script,int updated,int flags,int ability,int item,int endure,int sub,int miss) {
    BattleContext c={0};
    if(script==21) {
        c.words=updated?script21_1:script21_0;c.length=updated?sizeof(script21_1)/4:sizeof(script21_0)/4;
    } else {
        c.words=updated?script121_1:script121_0;c.length=updated?sizeof(script121_1)/4:sizeof(script121_0)/4;
    }
    c.scriptNarcId=NARC_a_0_0_1;c.scriptFileId=script;c.hpCalc=-150;
    // Deliberately disagree with the delayed recipient to expose wrong tags.
    c.battlerIdTarget=1;c.battlerIdTemp=3;c.abilityTemp=ABILITY_PRESSURE;
    int target=script==21?1:3;
    c.battleMons[target].hp=script==21?1:100;c.battleMons[target].maxHp=100;
    c.battleMons[target].ability=ability;c.battleMons[target].item=item;c.turnData[target].endureFlag=endure;
    c.battleMons[target].status2=sub?STATUS2_SUBSTITUTE:0;c.moveStatusFlag=flags;
    for(int steps=0;steps<200;steps++) {
        assert(c.pos<c.length);
        switch(c.words[c.pos]) {
        case 14:case 20:c.pos++;break;
        case 18:{c.pos++;BattleMessageData msg={0};InitBattleMsgData(&c,&msg);assert(c.count<8);
            int i=c.count++;c.messages[i]=msg.id;c.tags[i]=msg.tag;
            if(msg.tag==TAG_NICKNAME_ABILITY) {
                c.nicknames[i]=GetNicknameMessageNo(NULL,&c,msg.params[0]);
                c.abilities[i]=GetAbilityMessageNo(NULL,&c,msg.params[1]);
            }break;}
        case 30:c.pos+=2;break;
        case 32:BtlCmd_CompareVarToValue(NULL,&c);break;
        case 33:BtlCmd_CompareMonDataToValue(NULL,&c);break;
        case 50:BtlCmd_UpdateVar(NULL,&c);break;
        case 52:case 58:assert(sub);c.pos+=5;break;
        case 59:BtlCmd_Goto(NULL,&c);break;
        case 60:{c.pos++;int callee=BattleScriptReadWord(&c);
            if(callee==BATTLE_SUBSCRIPT_UPDATE_HP) {c.battleMons[target].hp+=c.hpCalc;c.updates++;}
            else assert(callee==BATTLE_SUBSCRIPT_HIT_SUBSTITUTE);break;}
        case 69:c.animations++;c.pos+=3;break;
        case 24:c.pos+=4;break;
        case 79:BtlCmd_CompareMonDataToVar(NULL,&c);break;
        case 122:{c.pos+=4;int skip=BattleScriptReadWord(&c);if(miss)BattleScriptIncrementPointer(&c,skip);break;}
        case 166:BtlCmd_CheckItemHoldEffect(NULL,&c);break;
        case 202:BtlCmd_RemoveItem(NULL,&c);break;
        case 208:BtlCmd_CheckHoldOnWith1HP(NULL,&c);break;
        case 224:return c;
        default:assert(0);
        }
    }
    assert(0);return c;
}
int main(void) {
    const int items[]={0,HOLD_EFFECT_ENDURE,HOLD_EFFECT_MAYBE_ENDURE};
    for(int remaining=0;remaining<=2;remaining++) {
        BattleContext c=run(21,1,MOVE_STATUS_ENDURED_ABILITY|MOVE_STATUS_SUPER_EFFECTIVE|(remaining>1?(1u<<22):0),
            ABILITY_STURDY,HOLD_EFFECT_ENDURE,0,0,0);
        assert(c.messages[0]==625);assert(c.count==(remaining>1?1:2));
        if(remaining<=1)assert(c.messages[1]==780);
    }
    for(int i=0;i<3;i++) {
        BattleContext c=run(21,1,MOVE_STATUS_ENDURED_ABILITY,ABILITY_STURDY,items[i],0,0,0);
        assert(c.count==1&&c.messages[0]==625&&c.tags[0]==TAG_NICKNAME_ABILITY);
        assert(c.nicknames[0]==1&&c.abilities[0]==ABILITY_STURDY);
        assert(c.battleMons[1].item==items[i]&&c.animations==0);
        assert(!(c.moveStatusFlag&MOVE_STATUS_ENDURED_ABILITY));
    }
    for(int script=21;script<=121;script+=100)for(int i=0;i<3;i++)for(int endure=0;endure<2;endure++) {
        BattleContext c=run(script,1,script==21?MOVE_STATUS_ENDURED_ABILITY:MOVE_STATUS_ENDURED_ITEM,
            ABILITY_STURDY,items[i],endure,0,0);
        int target=script==21?1:3;
        assert(c.count==1&&c.messages[0]==(script==121&&endure?445:625));
        if(c.messages[0]==625)assert(c.nicknames[0]==target&&c.abilities[0]==ABILITY_STURDY);
        assert(c.battleMons[target].item==items[i]);assert(c.animations==0);
        if(script==121)assert(c.updates==1&&c.battleMons[target].hp==1);
    }
    // Item and ordinary type-effectiveness presentation remains bytecode-equivalent.
    const int flags[]={0,MOVE_STATUS_ENDURED_ITEM,MOVE_STATUS_ENDURED,MOVE_STATUS_SUPER_EFFECTIVE,
        MOVE_STATUS_NOT_VERY_EFFECTIVE,MOVE_STATUS_SPLASH,MOVE_STATUS_ONE_HIT_KO};
    for(int f=0;f<7;f++)for(int i=0;i<3;i++) {
        BattleContext old=run(21,0,flags[f],ABILITY_NONE,items[i],0,0,0);
        BattleContext now=run(21,1,flags[f],ABILITY_NONE,items[i],0,0,0);
        assert(old.count==now.count&&old.animations==now.animations);
        assert(!memcmp(old.messages,now.messages,sizeof(old.messages)));
        assert(old.battleMons[1].item==now.battleMons[1].item);
    }
    for(int i=1;i<3;i++) {
        BattleContext c=run(121,1,MOVE_STATUS_ENDURED_ABILITY,ABILITY_NONE,items[i],0,0,0);
        assert(c.count==1&&c.messages[0]==912&&c.animations==1);
        assert(c.battleMons[3].item==(i==1?0:items[i]));
    }
    // Stale markers must be cleared even on a miss or a Substitute-only hit.
    for(int sub=0;sub<2;sub++)for(int miss=0;miss<2;miss++)if(sub||miss) {
        BattleContext c=run(121,1,MOVE_STATUS_ENDURED_ABILITY|MOVE_STATUS_ENDURED_ITEM,
            ABILITY_STURDY,HOLD_EFFECT_ENDURE,0,sub,miss);
        assert(c.count==(miss?1:0));if(miss)assert(c.messages[0]==796);
        assert(c.battleMons[3].item==HOLD_EFFECT_ENDURE&&c.updates==0);
        assert(!(c.moveStatusFlag&(MOVE_STATUS_ENDURED_ABILITY|MOVE_STATUS_ENDURED_ITEM)));
    }
    return 0;
}
"""
        game.GameLogicTests.compile_run(self,declarations+functions+'\n'+'\n'.join(arrays)+checks,
                                        '-DQOL_MODERN_BATTLE=1','-Wno-unused-function')


if __name__ == '__main__':
    unittest.main()
