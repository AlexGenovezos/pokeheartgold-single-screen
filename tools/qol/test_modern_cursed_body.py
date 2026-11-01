"""Execute native on-hit, Disable and saved-ability paths with SDK edges stubbed."""
from pathlib import Path
import importlib.util
import json
import re
import struct
import unittest
from unittest.mock import patch

import test_game_logic as game
import test_modern_moves

ROOT = Path(__file__).resolve().parents[2]


def hit_source():
    source = test_modern_moves.ModernMoveTests().source() + r'''
#include "constants/abilities.h"
#include "constants/battle.h"
#include "constants/battle_script.h"
#include "constants/battle_subscript.h"
#include "constants/move_effects.h"
#ifndef ABILITY_CURSED_BODY
#define ABILITY_CURSED_BODY 130
#endif
typedef int BattleSystem;
enum {NARC_a_0_0_1,NARC_a_0_0_0};
typedef struct {
    int hp,maxHp,ability,status,status2,moveEffectFlags,type1,type2;
    u16 moves[4];u8 movePPCur[4];
    struct {u16 disabledMove;unsigned disabledTurns:3;} moveEffectData;
} Mon;
typedef struct {
    Mon battleMons[4];
    struct {MoveTbl moveData[NUM_MOVES+1];int abilities[4];} trainerAIData;
    struct {int statusFlags,physicalDamage,specialDamage;} selfTurnData[4];
    int battlerIdTarget,battlerIdAttacker,battlerIdFainted,battlerIdTemp,battlerIdStatChange,
        statChangeType,moveNoCur,moveNoTemp,moveTemp,moveType,msgTemp,hpCalc,abilityTemp,
        scriptNarcId,scriptFileId,tempData,pos,words[4],fieldCondition;
    unsigned battleStatus,battleStatus2,moveStatusFlag;
} BattleContext;
static int randomResult,randomCalls;
static int BattleSystem_Random(BattleSystem *s){randomCalls++;return randomResult;}
static int BattleMon_GetMoveIndex(Mon *m,int move){for(int i=0;i<4;i++)if(m->moves[i]==move)return i;return 4;}
static int DamageDivide(int n,int d){return n/d;}
static int CheckAbilityActive(BattleSystem *s,BattleContext *c,int a,int b,int ability){return 0;}
static int GetBattlerVar(BattleContext *c,int b,int v,void *unused){return v==BMON_DATA_TYPE_1?c->battleMons[b].type1:c->battleMons[b].type2;}
static void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;}
static int BattleScriptReadWord(BattleContext *c){return c->words[c->pos++];}
'''
    util = (ROOT/'src/battle/battle_util.c').read_text()
    functions = ['GetBattlerAbility', 'BattlerCheckSubstitute']
    if 'static u16 Qol_GetCursedBodyMove(' in util:
        functions += ['Qol_GetCursedBodyMove']
    functions += ['CheckAbilityEffectOnHit']
    return source + '\n'.join(game.function_source('src/battle/battle_util.c', f) for f in functions) + r'''
static BattleContext fixture(void) {
    BattleContext c={0};c.battlerIdTarget=1;c.battlerIdFainted=BATTLER_NONE;
    c.battleMons[0].hp=100;c.battleMons[1].hp=100;c.battleMons[1].ability=ABILITY_CURSED_BODY;
    c.moveNoCur=c.moveNoTemp=MOVE_TACKLE;c.battleMons[0].moves[0]=MOVE_TACKLE;
    c.battleMons[0].movePPCur[0]=10;c.selfTurnData[1].physicalDamage=-20;
    c.trainerAIData.moveData[MOVE_TACKLE].power=40;
    randomResult=randomCalls=0;return c;
}
'''


class CursedBodyTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def check(self, checks):
        for flags in ((), ('-DQOL_MODERN_BATTLE=1','-DQOL_MODERN_MOVES=1')):
            self.compile_run(hit_source()+checks,*flags,'-Wno-unused-function')

    def test_probability_suppression_mold_breaker_and_fainted_holder(self):
        self.check(r'''
int main(void) {
    for(int r=0;r<10;r++)for(int mold=0;mold<2;mold++)for(int suppress=0;suppress<2;suppress++)
    for(int fainted=0;fainted<2;fainted++)for(int special=0;special<2;special++) {
        BattleContext c=fixture();randomResult=r;
        c.battleMons[0].ability=mold?ABILITY_MOLD_BREAKER:ABILITY_NONE;
        c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
        c.battleMons[1].hp=fainted?0:100;
        if(special){c.selfTurnData[1].physicalDamage=0;c.selfTurnData[1].specialDamage=-20;}
        int script=-1,expected=QOL_MODERN_BATTLE&&!suppress&&r<3;
        assert(CheckAbilityEffectOnHit(NULL,&c,&script)==expected);
        assert(randomCalls==(QOL_MODERN_BATTLE&&!suppress));
        assert(c.battleMons[0].moveEffectData.disabledMove==(expected?MOVE_TACKLE:0));
        assert(c.battleMons[0].moveEffectData.disabledTurns==(expected?4:0));
        if(expected){assert(script==297);assert(c.moveTemp==MOVE_TACKLE);}
    }
    return 0;
}
''')

    def test_ineligible_hits_consume_no_rng_and_never_replace_disable(self):
        self.check(r'''
int main(void) {
    for(int reason=0;reason<13;reason++) {
        BattleContext c=fixture();
        switch(reason) {
        case 0:c.battlerIdTarget=BATTLER_NONE;break;
        case 1:c.battleMons[0].hp=0;break;
        case 2:c.selfTurnData[1].physicalDamage=0;break;
        case 3:c.selfTurnData[1].statusFlags=8;c.selfTurnData[1].physicalDamage=0;break;
        case 4:c.moveStatusFlag=MOVE_STATUS_FAILED;break;
        case 5:c.battleStatus=BATTLE_STATUS_CHARGE_TURN;break;
        case 6:c.moveNoTemp=MOVE_STRUGGLE;c.battleMons[0].moves[0]=MOVE_STRUGGLE;break;
        case 7:c.moveNoTemp=0;break;
        case 8:c.battleMons[0].moves[0]=MOVE_POUND;break;
        case 9:c.moveNoTemp=65535;break;
        case 10:c.battleMons[0].moveEffectData.disabledMove=MOVE_POUND;c.battleMons[0].moveEffectData.disabledTurns=2;break;
        case 11:c.moveNoCur=MOVE_FUTURE_SIGHT;break;
        case 12:c.battleStatus2=BATTLE_STATUS2_UTURN;break;
        }
        int script=-1;assert(!CheckAbilityEffectOnHit(NULL,&c,&script));
        assert(!randomCalls&&script==-1);
        assert(c.battleMons[0].moveEffectData.disabledMove==(reason==10?MOVE_POUND:0));
        assert(c.battleMons[0].moveEffectData.disabledTurns==(reason==10?2:0));
    }
    return 0;
}
''')

    def test_real_damage_substitute_break_sound_bypass_and_multihit_continuation(self):
        import test_modern_sturdy
        source=test_modern_sturdy.damage_source().replace('NARC_a_0_0_1,GAME_STAT_ALLIES_DAMAGED','NARC_a_0_0_1,NARC_a_0_0_0,GAME_STAT_ALLIES_DAMAGED')
        source=source.replace('int hp,maxHp,hitCount,ability,item,itemMod;',
            'int hp,maxHp,hitCount,ability,item,itemMod;u16 moves[4];u8 movePPCur[4];')
        source=source.replace('struct {int substituteHp;} moveEffectData;',
            'struct {int substituteHp,disabledMove;unsigned disabledTurns:3;} moveEffectData;')
        source=source.replace('hitDamage,battlerIdTemp,command,commandNext,moveNoCur,storedDamage[4],hpCalc,script,',
            'hitDamage,battlerIdTemp,command,commandNext,moveNoCur,storedDamage[4],hpCalc,script,\n'
            '        moveNoTemp,moveTemp,moveType,msgTemp,statChangeType,battlerIdStatChange,battleStatus2,multiHitLoop,moveCheckSkipFlags,checkMultiHit,')
        source+=r'''
static int BattleMon_GetMoveIndex(Mon *m,int move){for(int i=0;i<4;i++)if(m->moves[i]==move)return i;return 4;}
static int GetBattlerVar(BattleContext *c,int b,int v,void *unused){return TYPE_NORMAL;}
static int CheckAbilityActive(BattleSystem *s,BattleContext *c,int a,int b,int ability){return 0;}
static int DamageDivide(int n,int d){return n/d;}
static void BattleController_EmitBlankMessage(BattleSystem *s){}
'''
        source+='\n'.join(game.function_source('src/battle/battle_util.c',f) for f in (
            'BattlerCheckSubstitute','Qol_GetCursedBodyMove','CheckAbilityEffectOnHit'))+'\n'
        source+=game.function_source('src/battle/battle_controller_player.c','BattleControllerPlayer_CheckMultiHit')+r'''
int main(void) {
    BattleContext c=fixture(100,-10);c.battleMons[1].ability=ABILITY_CURSED_BODY;
    c.battleMons[0].hp=100;c.battleMons[0].moves[0]=MOVE_TACKLE;c.moveNoTemp=MOVE_TACKLE;
    c.battleMons[1].status2=STATUS2_SUBSTITUTE;c.battleMons[1].moveEffectData.substituteHp=10;
    c.multiHitCount=c.multiHitCountTemp=3;int script=-1;
    BattleControllerPlayer_HpCalc(NULL,&c);
    assert(!c.battleMons[1].moveEffectData.substituteHp);
    assert(!CheckAbilityEffectOnHit(NULL,&c,&script)&&!randomCalls);
    BattleControllerPlayer_CheckMultiHit(NULL,&c);assert(c.multiHitCount==2);
    // A broken Substitute's per-action marker persists in the native state;
    // actual damage from the following hit must still activate Cursed Body.
    c.damage=-20;BattleControllerPlayer_HpCalc(NULL,&c);
    assert(CheckAbilityEffectOnHit(NULL,&c,&script)==QOL_MODERN_BATTLE);
    BattleControllerPlayer_CheckMultiHit(NULL,&c);assert(c.multiHitCount==1);
    int calls=randomCalls;c.damage=-20;BattleControllerPlayer_HpCalc(NULL,&c);
    assert(!CheckAbilityEffectOnHit(NULL,&c,&script));assert(randomCalls==calls);
    c=fixture(100,-20);c.battleMons[0].hp=100;c.battleMons[1].ability=ABILITY_CURSED_BODY;
    c.moveNoCur=c.moveNoTemp=MOVE_HYPER_VOICE;c.battleMons[0].moves[0]=MOVE_HYPER_VOICE;
    c.trainerAIData.moveData[MOVE_HYPER_VOICE].category=CATEGORY_SPECIAL;
    c.battleMons[1].status2=STATUS2_SUBSTITUTE;c.battleMons[1].moveEffectData.substituteHp=10;
    BattleControllerPlayer_HpCalc(NULL,&c);
    assert(CheckAbilityEffectOnHit(NULL,&c,&script)==QOL_MODERN_BATTLE);
    assert(c.battleMons[1].moveEffectData.substituteHp==(QOL_MODERN_BATTLE?10:0));
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source,*flags,'-Wno-unused-function')

    def test_called_copied_extended_moves_zero_pp_and_repeated_hits(self):
        self.check(r'''
int main(void) {
    const int callers[]={MOVE_SLEEP_TALK,MOVE_METRONOME,MOVE_MIRROR_MOVE,MOVE_COPYCAT,MOVE_MIMIC,MOVE_TACKLE,898};
    for(int i=0;i<7;i++) {
        BattleContext c=fixture();c.moveNoTemp=callers[i];c.battleMons[0].moves[0]=callers[i];
        c.battleMons[0].movePPCur[0]=0;int script=-1;
        int expected=QOL_MODERN_BATTLE&&(i!=6||QOL_MODERN_MOVES);
        assert(CheckAbilityEffectOnHit(NULL,&c,&script)==expected);
        assert(c.battleMons[0].moveEffectData.disabledMove==(expected?callers[i]:0));
        int calls=randomCalls;assert(!CheckAbilityEffectOnHit(NULL,&c,&script));assert(randomCalls==calls);
    }
    BattleContext c=fixture();c.moveNoCur=MOVE_PURSUIT;c.scriptNarcId=NARC_a_0_0_1;
    c.scriptFileId=BATTLE_SUBSCRIPT_PURSUIT;c.moveNoTemp=MOVE_U_TURN;c.battleMons[0].moves[0]=MOVE_PURSUIT;
    int script=-1;assert(CheckAbilityEffectOnHit(NULL,&c,&script)==QOL_MODERN_BATTLE);
    assert(c.battleMons[0].moveEffectData.disabledMove==(QOL_MODERN_BATTLE?MOVE_PURSUIT:0));
    // Called Pursuit outside the intercept script must disable its caller.
    c=fixture();c.moveNoCur=MOVE_PURSUIT;c.moveNoTemp=MOVE_METRONOME;c.battleMons[0].moves[0]=MOVE_METRONOME;
    assert(CheckAbilityEffectOnHit(NULL,&c,&script)==QOL_MODERN_BATTLE);
    assert(c.battleMons[0].moveEffectData.disabledMove==(QOL_MODERN_BATTLE?MOVE_METRONOME:0));
    return 0;
}
''')

    def test_disable_blocks_actions_until_the_fourth_residual_phase(self):
        controller=(ROOT/'src/battle/battle_controller_player.c').read_text()
        residual=controller.split('        case UMC_STATE_DISABLE:\n',1)[1].split('        case UMC_STATE_ENCORE:',1)[0]
        action=controller.split('        case 6:\n            if (ctx->battleMons[ctx->battlerIdAttacker].moveEffectData.disabledMove',1)[1]
        action='            if (ctx->battleMons[ctx->battlerIdAttacker].moveEffectData.disabledMove'+action.split('        case 7:',1)[0]
        source=hit_source().replace('scriptNarcId,scriptFileId,tempData,pos,words[4],fieldCondition;',
            'scriptNarcId,scriptFileId,tempData,pos,words[4],fieldCondition,moveNoBattlerPrev[4],command,commandNext,stateUpdateMonCondition,checkAttackerStatusState;\n'
            '    struct {int disabled;} moveFail[4];')
        source+=r'''
static void ReadBattleScriptFromNarc(BattleContext *c,int narc,int script){c->scriptFileId=script;}
'''+game.function_source('src/battle/battle_command.c','BtlCmd_TryDisable')
        source+='\nstatic void residual(BattleContext *ctx) {\nint i,battlerId=0,flag=0;switch(0){case 0:\n'+residual+'}\n(void)flag;}\n'
        source+='\nstatic int action(BattleContext *ctx) {\nint ret=0;switch(0){case 0:\n'+action+'}\nreturn ret;}\n'
        source+=r'''
int main(void) {
    // Ordinary Disable before the target acts: the current action is included.
    BattleContext c=fixture();c.battlerIdTarget=0;c.moveNoBattlerPrev[0]=MOVE_TACKLE;
    randomResult=3;BtlCmd_TryDisable(NULL,&c);
    assert(c.battleMons[0].moveEffectData.disabledTurns==(QOL_MODERN_BATTLE?4:6));
    assert(action(&c));
    for(int end=1;end<=4;end++) {
        residual(&c);
        assert(!!c.battleMons[0].moveEffectData.disabledMove==(!QOL_MODERN_BATTLE||end<4));
        assert(action(&c)==(!QOL_MODERN_BATTLE||end<4));
    }
    if(QOL_MODERN_BATTLE)assert(c.scriptFileId==BATTLE_SUBSCRIPT_DISABLE_END);
    // Cursed Body activates after its attack, so only three later actions are
    // blocked. The activation turn is the first of the four residual phases.
    c=fixture();int script=-1;CheckAbilityEffectOnHit(NULL,&c,&script);
    if(QOL_MODERN_BATTLE) {
        for(int end=1;end<=4;end++){residual(&c);assert(action(&c)==(end<4));}
        assert(c.scriptFileId==BATTLE_SUBSCRIPT_DISABLE_END);
    }
    // Native zero clears immediately, and a copied move disappearing expires
    // at the next residual phase rather than retaining an invalid move ID.
    c=fixture();c.battleMons[0].moveEffectData.disabledMove=MOVE_POUND;
    c.battleMons[0].moveEffectData.disabledTurns=4;residual(&c);
    assert(!c.battleMons[0].moveEffectData.disabledMove);
    assert(c.scriptFileId==BATTLE_SUBSCRIPT_DISABLE_END);
    c=fixture();c.battleMons[0].moveEffectData.disabledMove=MOVE_TACKLE;
    c.battleMons[0].moveEffectData.disabledTurns=0;residual(&c);
    assert(!c.battleMons[0].moveEffectData.disabledMove);
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source,*flags,'-Wno-unused-function')


class CursedBodyResourceTests(unittest.TestCase):
    def test_script_append_is_guarded_and_preserves_every_original_member(self):
        self.assertIsNotNone(importlib.util.find_spec('cursed_body_scripts'), 'Cursed Body script generation is missing')
        import cursed_body_scripts as scripts
        import modern_rom
        from nitro_data import pack_narc,unpack_narc
        members=[bytes([i%256])*4 for i in range(297)]
        with patch.object(scripts,'compile_battle_script',side_effect=[members[71],b'cursed']) as compiler:
            result,names=unpack_narc(modern_rom.modern_cursed_body_resources(pack_narc(members)))
        self.assertEqual(result[:297],members);self.assertEqual(result[297],b'cursed')
        self.assertEqual(names,unpack_narc(pack_narc(members))[1]);self.assertEqual(compiler.call_count,2)
        with patch.object(scripts,'compile_battle_script',return_value=b'wrong') as compiler:
            with self.assertRaisesRegex(ValueError,'unchanged.*match.*71'):
                modern_rom.modern_cursed_body_resources(pack_narc(members))
            self.assertEqual(compiler.call_count,1)
        for count in (296,298):
            with patch.object(scripts,'compile_battle_script') as compiler:
                with self.assertRaisesRegex(ValueError,'297'):
                    modern_rom.modern_cursed_body_resources(pack_narc(members[:count] if count<297 else members+[b'extra']))
                compiler.assert_not_called()


class ModernAbilityStorageTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_all_personal_read_paths_and_stored_choices_preserve_native_layout(self):
        self.assertTrue((ROOT/'src/qol_abilities.c').is_file(), 'Modern ability adapter is missing')
        data=json.loads((ROOT/'files/poketool/personal/personal.json').read_text())['baseStats']
        header=(ROOT/'include/constants/abilities.h').read_text()
        ids={name:int(number) for name,number in re.findall(r'#define (ABILITY_\w+)\s+(\d+)',header)}
        original=','.join('{'+','.join(str(ids[a]) for a in r['abilities'])+'}' for r in data)
        source=r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "qol_config.h"
#include "constants/abilities.h"
#include "constants/species.h"
#include "constants/pokemon.h"
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int BOOL;
#define TRUE 1
#define FALSE 0
enum {HEAP_ID_DEFAULT,NARC_poketool_personal_personal};
typedef struct {u8 abilities[2];} BASE_STATS;
typedef int NARC;
'''+f'static const u8 original[][2]={{{original}}};\n'
        adapter=(ROOT/'src/qol_abilities.c').read_text()
        source+=test_modern_moves.no_includes(adapter)+r'''
static int ResolveMonForm(int species,int form){return species==SPECIES_GIRATINA&&form==1?501:species;}
static void ReadWholeNarcMemberByIdPair(BASE_STATS *p,int narc,int species){memcpy(p->abilities,original[species],2);}
static void NARC_ReadWholeMember(NARC *n,int species,BASE_STATS *p){ReadWholeNarcMemberByIdPair(p,0,species);}
static void *Heap_Alloc(int heap,size_t size){return malloc(size);}
static void Heap_Free(void *p){free(p);}
static int GetPersonalAttr(BASE_STATS *p,int attr){return p->abilities[attr==BASE_ABILITY_2];}
'''
        for function in ('LoadMonPersonal','LoadMonBaseStats_HandleAlternateForm','GetMonBaseStatEx_HandleAlternateForm'):
            source+=game.function_source('src/pokemon.c',function)+'\n'
        getter=(ROOT/'src/pokemon.c').read_text().split('static u32 GetBoxMonDataInternal(BoxPokemon *boxMon, int attr, void *dest) {',1)[1]
        ability_case=getter.split('    case MON_DATA_ABILITY:\n',1)[1].split('    case ',1)[0]
        source+='\nstatic int stored(int species,int form,int ability,u32 personality) {\nstruct {u32 personality;} box={personality},*boxMon=&box;\nstruct {int species,ability;} a={species,ability},*blockA=&a;\nstruct {int form;} b={form},*blockB=&b;int ret=0;\nswitch(0){case 0:\n'+ability_case+'}\n(void)blockB;(void)boxMon;assert(a.ability==ability&&a.species==species&&b.form==form&&box.personality==personality);return ret;}\n'
        source+=r'''
int main(void) {
    for(unsigned species=0;species<sizeof(original)/sizeof(original[0]);species++) {
        BASE_STATS p;LoadMonPersonal(species,&p);
        for(int slot=0;slot<2;slot++) {
            int expected=original[species][slot];
            if(QOL_MODERN_BATTLE) {
                if(species==SPECIES_GENGAR)expected=130;
                if(slot==1&&(species==SPECIES_JIGGLYPUFF||species==SPECIES_WIGGLYTUFF||species==SPECIES_IGGLYBUFF||species==SPECIES_MILOTIC))expected=172;
            }
            assert(p.abilities[slot]==expected);
            assert(GetMonBaseStatEx_HandleAlternateForm(NULL,species,0,slot?BASE_ABILITY_2:BASE_ABILITY_1)==expected);
        }
        LoadMonBaseStats_HandleAlternateForm(species,0,&p);
        for(int slot=0;slot<2;slot++) {
            int expected=original[species][slot];
            if(QOL_MODERN_BATTLE) {
                if(species==SPECIES_GENGAR)expected=130;
                if(slot==1&&(species==SPECIES_JIGGLYPUFF||species==SPECIES_WIGGLYTUFF||species==SPECIES_IGGLYBUFF||species==SPECIES_MILOTIC))expected=172;
            }
            assert(p.abilities[slot]==expected);
        }
    }
    // Alternate records stay native, including Giratina's ability form switch.
    BASE_STATS p;LoadMonBaseStats_HandleAlternateForm(SPECIES_GIRATINA,1,&p);
    assert(!memcmp(p.abilities,original[501],2));
    for(int species=1;species<=493;species++)for(int form=0;form<2;form++)for(int ability=0;ability<256;ability++)for(u32 pid=0;pid<4;pid++) {
        int expected=QOL_MODERN_BATTLE&&species==SPECIES_GENGAR&&form==0&&ability==26?130:ability;
        if(QOL_MODERN_BATTLE&&form==0&&(pid&1)) {
            if((species==SPECIES_JIGGLYPUFF||species==SPECIES_WIGGLYTUFF||species==SPECIES_IGGLYBUFF)&&ability==56)expected=172;
            if(species==SPECIES_MILOTIC&&ability==63)expected=172;
        }
        assert(Qol_GetStoredAbility(species,form,ability,pid)==expected);
        assert(stored(species,form,ability,pid)==expected);
    }
    for(int id=0;id<=65535;id++)assert(Qol_IsSupportedAbility(id)==(id<=123||(QOL_MODERN_BATTLE&&(id==130||id==172))));
    assert(NUM_ABILITIES==123);
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source,*flags,'-Wno-unused-function')


class CursedBodySdkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import cursed_body_scripts as scripts
        from battle_scripts import battle_script_tools
        from nitro_data import unpack_narc
        try:battle_script_tools()
        except FileNotFoundError as error:raise unittest.SkipTest(str(error))
        path=ROOT/'files/battledata/script/subscript.narc'
        if not path.is_file():raise unittest.SkipTest('Original battle subscripts unavailable')
        originals=unpack_narc(path.read_bytes())[0]
        if len(originals)!=297:raise AssertionError('Expected exactly 297 original subscripts')
        cls.scripts={i:originals[i] for i in (70,71,72,153,175)}
        cls.scripts[297]=scripts.modern_cursed_body_script(originals[71])

    def test_native_script_stack_trigger_messages_and_ai_revelation(self):
        source=hit_source()
        source=source.replace('int hp,maxHp,ability,', 'int statChanges[8];int hp,maxHp,ability,')
        source=source.replace('Mon battleMons[4];', 'Mon battleMons[4];int statChangeFlag;struct {int id,tag,param[6];} buffMsg;')
        source=source.replace('} Mon;', '} Mon;typedef Mon BattleMon;')
        source=source.replace('tempData,pos,words[4],fieldCondition;',
            'tempData,scriptSeqNo,fieldCondition,scriptStackDepth,battleContinueFlag,selectedMonIndex[4],switchMonIndex[4];\n'
            '    int scriptStackNarcId[4],scriptStackFileId[4],scriptStackSeqNo[4];u32 battleScriptBuffer[400];')
        source=re.sub(r'static void BattleScriptIncrementPointer\([^\n]+\n','',source)
        source=re.sub(r'static int BattleScriptReadWord\([^\n]+\n','',source)
        source+=r'''
#include "constants/message_tags.h"
#define QOL_STAT_CHANGE_COMPETITIVE_PENDING 1
enum {msg_0197_00750=750,msg_0197_00753=753};
static int CreateNicknameTag(BattleContext *c,int b){return b;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return 4;}
#define GF_ASSERT assert
typedef int NarcId;
typedef struct {int id,tag,params[6];} BattleMessageData;
static void BattlerSetAbility(BattleContext *c,u8 id,u8 ability);
'''
        for member,data in self.scripts.items():
            words=','.join(str(w)+'u' for w in struct.unpack('<'+'I'*(len(data)//4),data))
            source+=f'static const u32 script{member}[]={{ {words} }};\n'
        source+=r'''
static const u32 *archive(int member,int *size) {
    switch(member) {
#define MEMBER(n) case n:*size=sizeof(script##n);return script##n
    MEMBER(70);MEMBER(71);MEMBER(72);MEMBER(153);MEMBER(175);MEMBER(297);
#undef MEMBER
    default:assert(0);return NULL;
    }
}
static int GetNarcMemberSizeByIdPair(int narc,int member){int size;archive(member,&size);return size;}
static void ReadWholeNarcMemberByIdPair(void *out,int narc,int member){int size;const u32 *p=archive(member,&size);memcpy(out,p,size);}
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side) {
    if(side==BATTLER_CATEGORY_ATTACKER)return c->battlerIdAttacker;
    if(side==BATTLER_CATEGORY_DEFENDER)return c->battlerIdTarget;
    assert(side==BATTLER_CATEGORY_MSG_TEMP);return c->battlerIdTemp;
}
static void *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int var){assert(var==BSCRIPT_VAR_TEMP_DATA);return &c->tempData;}
'''
        source+='\n'.join(game.function_source('src/battle/battle_command.c',f) for f in (
            'BattleScriptReadWord','BattleScriptIncrementPointer'))+'\n'
        source+='\n'.join(game.function_source('src/battle/battle_util.c',f) for f in (
            'ReadBattleScriptFromNarc','BattleScript_Call','BattleScript_Return'))+'\n'
        source+='\n'.join(game.function_source('src/battle/battle_command.c',f) for f in (
            'BattleScriptGotoSubscript','BtlCmd_CallFromVar','BtlCmd_TriggerAbilityOnHit','BtlCmd_EndScript',
            'InitBattleMsgData','GetNicknameMessageNo','GetAbilityMessageNo','GetMoveMessageNo','BattlerSetAbility'))+'\n'
        source+=r'''
static void presentation(BattleContext *c) {
    int count=0;
    for(int steps=0;steps<40;steps++) {
        switch(c->battleScriptBuffer[c->scriptSeqNo]) {
        case 14:c->scriptSeqNo++;break;
        case 18:{
            c->scriptSeqNo++;BattleMessageData msg={0};InitBattleMsgData(c,&msg);
            assert(msg.id==(count?366:1087));
            if(!count) {
                assert(msg.tag==TAG_NICKNAME_ABILITY);
                assert(GetNicknameMessageNo(NULL,c,msg.params[0])==(1|(3<<8)));
                assert(GetAbilityMessageNo(NULL,c,msg.params[1])==ABILITY_CURSED_BODY);
                assert(c->trainerAIData.abilities[1]==ABILITY_CURSED_BODY);
                assert(c->trainerAIData.abilities[0]==0);
            } else {
                assert(msg.tag==TAG_NICKNAME_MOVE);
                assert(GetNicknameMessageNo(NULL,c,msg.params[0])==(0|(2<<8)));
                assert(GetMoveMessageNo(c,msg.params[1])==c->battleMons[0].moveEffectData.disabledMove);
            }
            count++;break;
        }
        case 30:c->scriptSeqNo+=2;break;
        case 224:assert(count==2);assert(!BtlCmd_EndScript(NULL,c));return;
        default:assert(0);
        }
    }
    assert(0);
}
int main(void) {
    for(int member=153;member<=175;member+=22)for(int eligible=0;eligible<2;eligible++) {
        BattleContext c=fixture();c.selectedMonIndex[0]=2;c.selectedMonIndex[1]=3;
        c.abilityTemp=ABILITY_PRESSURE;c.battlerIdTemp=3;
        c.moveNoTemp=MOVE_U_TURN;c.moveNoCur=member==153?MOVE_PURSUIT:MOVE_U_TURN;
        c.battleMons[0].moves[0]=c.moveNoCur;
        if(!eligible)c.selfTurnData[1].physicalDamage=0;
        ReadBattleScriptFromNarc(&c,NARC_a_0_0_1,member);
        int length=GetNarcMemberSizeByIdPair(0,member)/4,found=0;
        for(int pos=0;pos+3<length;pos++)if(c.battleScriptBuffer[pos]==197&&c.battleScriptBuffer[pos+2]==61) {
            found++;c.scriptSeqNo=pos;BtlCmd_TriggerAbilityOnHit(NULL,&c);
            if(eligible) {
                assert(c.scriptSeqNo==pos+2);assert(c.tempData==297);
                BtlCmd_CallFromVar(NULL,&c);assert(c.scriptFileId==297&&c.scriptStackDepth==1);
                presentation(&c);assert(!c.scriptStackDepth&&c.scriptFileId==member);
                assert(c.scriptSeqNo==pos+4&&randomCalls==1);
                assert(c.battleMons[0].moveEffectData.disabledMove==c.moveNoCur);
                break;
            } else assert(c.scriptSeqNo==pos+4&&!randomCalls);
        }
        assert(found);
    }
    return 0;
}
'''
        game.GameLogicTests.compile_run(self,source,'-DQOL_MODERN_BATTLE=1','-DQOL_MODERN_MOVES=1','-Wno-unused-function','-Wno-return-type')


if __name__ == '__main__':
    unittest.main()
