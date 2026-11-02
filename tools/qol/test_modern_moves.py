"""Execute extended move production data/accessors without the DS SDK."""
from pathlib import Path
import re
import unittest
import test_game_logic as game

ROOT = Path(__file__).resolve().parents[2]
BATTLE_FILES = ('battle_controller_player', 'battle_controller_opponent', 'battle_util',
                'battle_command', 'trainer_ai', 'battle_controller')


def no_includes(text):
    return re.sub(r'^#include (?!"data/)[^\n]*$', '', text, flags=re.M)


class ModernMoveTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def source(self):
        for path in ('include/qol_moves.h', 'include/constants/qol_moves.h', 'src/qol_moves.c'):
            self.assertTrue((ROOT / path).exists(), 'Missing extended move foundation: ' + path)
        return r'''
#include <assert.h>
#include <stddef.h>
#include <string.h>
#include "qol_config.h"
#include "constants/moves.h"
#include "constants/pokemon.h"
#include "constants/qol_moves.h"
typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define NELEMS(a) (sizeof(a)/sizeof((a)[0]))
''' + no_includes((ROOT / 'include/move.h').read_text()) + no_includes(
            (ROOT / 'include/qol_moves.h').read_text()) + no_includes((ROOT / 'src/qol_moves.c').read_text())

    def test_metadata_accessors_preserve_original_array_and_reject_unknown_ids(self):
        checks = r'''
int main(void) {
    MoveTbl legacy[NUM_MOVES+1] = {{0}};
    struct { struct { MoveTbl moveData[NUM_MOVES+1]; } trainerAIData; } ctx = {0};
    assert(NUM_MOVES == 467 && sizeof(MoveTbl) == 16 && NELEMS(legacy) == 468);
    for (int id = 0; id <= NUM_MOVES; id++) {
        legacy[id].power = id % 256;
        assert(Qol_IsSupportedMove(id));
        assert(Qol_GetBattleMoveData(legacy,id) == &legacy[id]);
    }
    assert(&BATTLE_MOVE_DATA(&ctx, MOVE_TACKLE) == &ctx.trainerAIData.moveData[MOVE_TACKLE]);
    const int ids[] = {577,580,586,588,608};
    // Independent native metadata expectations, including native King's Rock bit.
    const int expected[][11] = {
        {17,1,40,9,0,15,0,4,0,0x32,304},
        {3,1,50,9,100,10,0,0,0,0x53,72},
        {68,0,90,9,90,10,10,0,0,0x53,242},
        {71,1,95,9,100,15,30,0,0,0x52,296},
        {0,1,80,9,100,10,0,4,0,0x72,324}
    };
    for (int i=0; i<5; i++) {
#if QOL_MODERN_MOVES
        const MoveTbl *entry=Qol_GetExtendedMoveData(ids[i]);
        assert(entry && Qol_IsSupportedMove(ids[i]));
        assert(Qol_GetBattleMoveData(legacy,ids[i])==entry);
        const int actual[]={entry->effect,entry->category,entry->power,entry->type,
            entry->accuracy,entry->pp,entry->effectChance,entry->range,entry->priority,entry->flags};
        for (int a=0;a<10;a++) assert(actual[a]==expected[i][a]);
        assert(Qol_GetMoveAnimation(ids[i])==expected[i][10]);
#else
        (void)expected;
        assert(!Qol_IsSupportedMove(ids[i]) && !Qol_GetExtendedMoveData(ids[i]));
        assert(Qol_GetMoveAnimation(ids[i])==ids[i]);
#endif
    }
    const int invalid[]={468,500,576,578,579,581,590,591,607,609,65535};
    for (unsigned i=0;i<NELEMS(invalid);i++) {
        assert(!Qol_IsSupportedMove(invalid[i]));
        assert(!Qol_GetExtendedMoveData(invalid[i]));
        assert(Qol_GetBattleMoveData(legacy,invalid[i])==&legacy[0]);
    }
    assert(Qol_GetMoveAnimation(MOVE_POUND)==MOVE_POUND);
    assert(Qol_IsSoundMove(MOVE_HYPER_VOICE));
    assert(!Qol_IsSoundMove(MOVE_TACKLE));
    assert(Qol_IsSoundMove(577)==QOL_MODERN_MOVES);
    for (int i=0;i<NUM_MOVES;i++) assert(Qol_GetMetronomeMove(i)==i+1);
#if QOL_MODERN_MOVES
    assert(QOL_METRONOME_MOVE_COUNT==539);
    for(int i=0;i<5;i++) assert(Qol_GetMetronomeMove(NUM_MOVES+i)==ids[i]);
#else
    assert(QOL_METRONOME_MOVE_COUNT==467);
#endif
    assert(Qol_GetMetronomeMove(QOL_METRONOME_MOVE_COUNT)==MOVE_NONE);
    return 0;
}
'''
        source = self.source() + checks
        for flags in ((), ('-DQOL_MODS=1',), ('-DQOL_MODERN_MOVES=1',),
                      ('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_TYPES=0'),
                      ('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_TYPES=1')):
            with self.subTest(flags=flags):
                self.compile_run(source,*flags)

    def test_loaders_and_pp_read_extended_entries_without_reading_archive(self):
        declarations = r'''
enum { NARC_poketool_waza_waza_tbl };
static int reads;
static MoveTbl original[NUM_MOVES+1];
static void ReadFromNarcMemberByIdPair(void *dest,int narc,int member,int offset,int length) {
    assert(length == sizeof(original)); reads++; memcpy(dest,original,length);
}
static void ReadWholeNarcMemberByIdPair(void *dest,int narc,int member) {
    assert(member<=NUM_MOVES); reads++; memcpy(dest,&original[member],sizeof(MoveTbl));
}
'''
        source = self.source() + declarations + no_includes((ROOT / 'src/move.c').read_text())
        checks = r'''
int main(void) {
    original[MOVE_TACKLE].pp=35;
    MoveTbl loaded[NUM_MOVES+2]; memset(loaded,0x5a,sizeof(loaded));
    LoadMoveTbl(loaded); assert(reads==1 && loaded[NUM_MOVES+1].power==0x5a);
    assert(GetMoveMaxPP(MOVE_TACKLE,3)==56 && reads==2);
#if QOL_MODERN_MOVES
    const int ids[]={577,580,586,588,608,587,673,670,696,532,687,898,622,621,575,589,854,476,543,495,779,536,666};
    for(unsigned i=0;i<NELEMS(ids);i++) {
        int before=reads; MoveTbl entry; LoadMoveEntry(ids[i],&entry);
        assert(reads==before && entry.pp==Qol_GetExtendedMoveData(ids[i])->pp);
        for(int attr=0;attr<=MOVEATTR_CONTEST_TYPE;attr++)
            assert(GetMoveAttr(ids[i],attr)==GetMoveTblAttr(&entry,attr));
        for(int ups=0;ups<8;ups++)
            assert(GetMoveMaxPP(ids[i],ups)==entry.pp+(entry.pp*20*(ups>3?3:ups))/100);
        assert(reads==before);
    }
    MoveTbl entry; LoadMoveEntry(65535,&entry); assert(entry.pp==0);
#endif
    return 0;
}
'''
        for flags in ((), ('-DQOL_MODERN_MOVES=1',), ('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_TYPES=1')):
            self.compile_run(source+checks,*flags,"-Wno-pointer-to-int-cast")

    def test_ordinary_batch_metadata_pp_and_sound_classification(self):
        checks = r"""
int main(void) {
    const int ids[] = {587,673,670,696,532,687,898,622,621,575,589,854};
    const int expected[][11] = {
        {0,1,40,9,100,30,0,0,0,0x72,345},
        {0,0,40,12,100,40,0,0,0,0x32,75},
        {0,0,95,4,95,10,0,0,0,0x33,414},
        {0,0,60,17,100,20,0,8,0,0x33,399},
        {43,0,80,4,95,10,0,0,0,0x33,163},
        {17,0,70,8,0,10,0,0,0,0x33,442},
        {43,0,70,11,100,20,0,0,0,0x32,352},
        {0,0,120,4,85,10,0,4,0,0x72,89},
        {0,1,110,11,85,10,0,4,0,0x72,352},
        {0,0,90,12,100,15,0,8,0,0x32,75},
        {0,1,140,0,100,10,0,8,0,0x72,304},
        {0,1,80,0,100,10,0,0,0,0x72,161}
    };
    for(unsigned i=0;i<NELEMS(ids);i++) {
        const MoveTbl *entry=Qol_GetExtendedMoveData(ids[i]);
        assert(Qol_IsSupportedMove(ids[i])==QOL_MODERN_MOVES);
#if QOL_MODERN_MOVES
        assert(entry);
        const int actual[]={entry->effect,entry->category,entry->power,entry->type,
            entry->accuracy,entry->pp,entry->effectChance,entry->range,entry->priority,entry->flags};
        for(int j=0;j<10;j++) assert(actual[j]==expected[i][j]);
        assert(Qol_GetMoveAnimation(ids[i])==expected[i][10]);
        assert(Qol_GetMetronomeMove(NUM_MOVES+5+i)==ids[i]);
#else
        assert(!entry);
        (void)expected;
#endif
        assert(Qol_IsSoundMove(ids[i])==(QOL_MODERN_MOVES && ids[i]==589));
        assert(Qol_MoveBypassesSubstitute(ids[i])==(QOL_MODERN_MOVES && ids[i]==589));
    }
    return 0;
}
"""
        for flags in ((), ('-DQOL_MODERN_MOVES=1',), ('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_TYPES=1')):
            self.compile_run(self.source()+checks,*flags)

    def test_full_move_names_and_private_card_bank_use_real_helpers(self):
        declarations = r"""
#include <assert.h>
#include <stddef.h>
#include "qol_config.h"
#include "constants/qol_moves.h"
typedef unsigned int u32;
typedef unsigned short u16;
#include "constants/charcode.h"
enum HeapID { HEAP_ID_BATTLE };
enum { MSGDATA_LOAD_LAZY, NARC_msgdata_msg, NARC_msg_msg_0750_bin=750 };
typedef struct { int capacity, bank, move; } String;
typedef struct { int bank; } MsgData;
static String storage;
static MsgData messages;
static MsgData *NewMsgDataFromNarc(int mode,int narc,int bank,enum HeapID heap) {
    messages.bank=bank; return &messages;
}
static String *String_New(int capacity,enum HeapID heap) {
    storage.capacity=capacity; return &storage;
}
static void ReadMsgDataIntoString(MsgData *msg,u32 move,String *out) {
    out->bank=msg->bank; out->move=move;
}
static String *NewString_ReadMsgData(MsgData *msg,u32 move) {
    String *out=String_New(32,HEAP_ID_BATTLE); ReadMsgDataIntoString(msg,move,out); return out;
}
static void CopyU16ArrayToString(String *out,const u16 *chars) {}
static void DestroyMsgData(MsgData *msg) {}
static int Qol_IsSupportedMove(u16 move) { return move<=467 || move==622 || move==577; }
#define NUM_MOVES 467
"""
        actual=game.function_source('src/msgdata.c','GetMoveName')+'\n'+game.function_source(
            'src/battle/battle_input.c','BattleInput_SingleScreen_MoveName')
        checks=r"""
int main(void) {
    String *name=GetMoveName(622,HEAP_ID_BATTLE);
    assert(name->capacity==(QOL_MODERN_MOVES?32:16));
    assert(name->bank==750 && name->move==622);
    const int ids[]={33,467,577,622,623};
    for(unsigned i=0;i<sizeof(ids)/sizeof(ids[0]);i++) {
        name=BattleInput_SingleScreen_MoveName(ids[i]);
        int extended=QOL_MODERN_MOVES && (ids[i]==577 || ids[i]==622);
        assert(name->bank==(extended?829:750));
        assert(name->move==ids[i]);
    }
    return 0;
}
"""
        for enabled in (0,1):
            self.compile_run(declarations+actual+checks,f'-DQOL_MODERN_MOVES={enabled}',
                             '-Wno-unused-function')

    def test_actual_ai_embedded_table_size_is_unchanged(self):
        header=(ROOT/'include/battle/battle.h').read_text()
        ai=re.search(r'typedef struct TrainerAIData \{.*?\} TrainerAIData;',header,re.S)[0]
        self.compile_run(self.source()+r'''
#include "constants/battle.h"
typedef void ItemData;
'''+ai+r'''
int main(void) {
    assert(sizeof(((TrainerAIData *)0)->moveData) == 468 * 16);
    return 0;
}
''')

    def test_all_battle_reads_use_accessor_and_legacy_layout_stays_468(self):
        self.assertRegex((ROOT/'include/battle/battle.h').read_text(),r'MoveTbl moveData\[NUM_MOVES \+ 1\]')
        for name in BATTLE_FILES:
            path=ROOT/f'src/battle/{name}.c'
            text=path.read_text()
            self.assertTrue('#include "qol_moves.h"' in text,str(path))
            self.assertNotRegex(text,r'ctx->trainerAIData\.moveData\[',str(path))
        self.assertIn('Object src/qol_moves.o',(ROOT/'main.lsf').read_text())

    def test_animation_preview_record_and_metronome_use_supported_move_helpers(self):
        for path in ('src/battle/battle_anim_system.c','src/battle_record.c'):
            self.assertTrue('#include "qol_moves.h"' in (ROOT/path).read_text(),path)
        anim=(ROOT/'src/battle/battle_anim_system.c').read_text()
        self.assertLess(anim.index('Qol_GetMoveAnimation(animId)'),anim.index('animId > NUM_MOVES'))
        preview=game.function_source('src/battle/battle_util.c','Qol_PreviewTypeEffectiveness')
        self.assertIn('Qol_IsSupportedMove(moveNo)',preview)
        self.assertIn('Qol_IsSupportedMove(mon->moves[k])',(ROOT/'src/battle_record.c').read_text())
        command=game.function_source('src/battle/battle_command.c','BtlCmd_Metronome')
        self.assertIn('Qol_GetMetronomeMove',command)
        self.assertIn('CheckLegalMetronomeMove',command)
        self.assertIn('moveNo = (BattleSystem_Random(battleSystem) % 0x1d3) + 1;',command)
        self.assertIn('MOVE_DISARMING_VOICE',(ROOT/'src/battle/battle_util.c').read_text())


    def test_real_damage_ai_and_preview_read_all_extended_entries(self):
        declarations = r'''
#include "constants/items.h"
#include "constants/abilities.h"
#include "constants/battle.h"
#include "constants/move_effects.h"
typedef int BattleSystem;
enum { TYPETABLE_ATTACKER, TYPETABLE_DEFENDER, TYPETABLE_EFFECT };
typedef struct {
    int hp,type1,type2,ability,itemEffect;
    u32 status,status2,moveEffectFlags;
    struct { int magnetRiseTurns; } moveEffectData;
} Mon;
typedef struct {
    Mon battleMons[4];
    struct { MoveTbl moveData[NUM_MOVES+1]; } trainerAIData;
    u32 fieldCondition,battleStatus;
    struct { int roostFlag; } turnData[4];
    struct { int moldBreakerFlag; } selfTurnData[4];
} BattleContext;
static int GetBattlerHeldItemEffect(BattleContext *ctx,int battler) { return ctx->battleMons[battler].itemEffect; }
static int GetHeldItemModifier(BattleContext *ctx,int battler,int unused) { return 0; }
static int GetBattlerVar(BattleContext *ctx,int battler,int field,void *unused) {
    return field==BMON_DATA_TYPE_1 ? ctx->battleMons[battler].type1 : ctx->battleMons[battler].type2;
}
'''
        util=(ROOT/'src/battle/battle_util.c').read_text()
        arrays='\n'.join(re.search(r'static (?:const )?u(?:8|16) '+name+r'\[.*?\n\};',util,re.S)[0]
                         for name in ('sTypeEffectiveness','sSoundMoves','sFixedDamageMoveEffects'))
        functions=('GetBattlerAbility','CheckBattlerAbilityIfNotIgnored','DamageDivide',
                   'ApplyTypeMultiplier','CheckChargeMoveHitTurn','CheckFlyingImmunity',
                   'ApplyEffectivenessFlags','BattleSystem_IsTypeMatchupActive',
                   'CalculateTypeEffectiveness','BattleSystem_ApplyTypeEffectiveness',
                   'CalcTypeEffectivenessFlags','IsFixedDamageMove','Qol_PreviewTypeEffectiveness')
        actual=arrays+'\n'+'\n'.join(game.function_source('src/battle/battle_util.c',name) for name in functions)
        checks=r'''
int main(void) {
    BattleContext ctx={0}; ctx.battleMons[0].hp=ctx.battleMons[1].hp=100;
    ctx.battleMons[0].type1=ctx.battleMons[0].type2=TYPE_NONE;
    const int ids[]={577,580,586,588,608,587,673,670,696,532,687,898,622,621,575,589,854,476,543,495,779,536,666};
    const int types[]={9,9,9,9,9,9,12,4,17,4,8,11,4,11,12,0,0,14,14,17,1,1,17};
    const int abilities[]={80,242};
    for(int user=0;user<2;user++)for(int target=0;target<2;target++) {
    ctx.battleMons[0].ability=abilities[user];ctx.battleMons[1].ability=abilities[target];
    for(unsigned i=0;i<NELEMS(ids);i++) {
        for(int type=0;type<NUMBER_OF_MON_TYPES;type++) {
            ctx.battleMons[1].type1=ctx.battleMons[1].type2=type;
            int expected=CalculateTypeEffectiveness(types[i],type,type);
            BattleContext before=ctx;
#if QOL_MODERN_MOVES
            assert(Qol_PreviewTypeEffectiveness(&ctx,ids[i],0,1)==expected);
            u32 flags=0,aiFlags=0;
            assert(BattleSystem_ApplyTypeEffectiveness(NULL,&ctx,ids[i],0,0,1,40,&flags)==expected);
            CalcTypeEffectivenessFlags(&ctx,ids[i],0,ABILITY_NONE,ABILITY_NONE,0,type,type,&aiFlags);
            assert(flags==aiFlags);
#else
            (void)expected;
            assert(Qol_PreviewTypeEffectiveness(&ctx,ids[i],0,1)==-1);
#endif
            assert(!memcmp(&ctx,&before,sizeof(ctx)));
        }
    }
    }
    assert(Qol_PreviewTypeEffectiveness(&ctx,65535,0,1)==-1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,578,0,1)==-1);
    ctx.battleMons[1].type1=ctx.battleMons[1].type2=TYPE_NORMAL;
    ctx.battleMons[1].ability=ABILITY_SOUNDPROOF;
#if QOL_MODERN_MOVES
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_DISARMING_VOICE,0,1)==0);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_BOOMBURST,0,1)==0);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_MOONBLAST,0,1)==40);
    ctx.battleMons[0].ability=ABILITY_MOLD_BREAKER;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_DISARMING_VOICE,0,1)==40);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_BOOMBURST,0,1)==40);
#endif
    return 0;
}
'''
        import itertools
        for bits in itertools.product((0,1),repeat=3):
            flags=tuple(f'-DQOL_MODERN_{name}={value}' for name,value in zip(('TYPES','BATTLE','MOVES'),bits))
            self.compile_run(self.source()+declarations+actual+checks,*flags,
                             '-Wno-sign-compare','-Wno-unused-but-set-variable')

    def test_actual_metronome_pool_filters_known_moves_illegal_moves_and_heal_block(self):
        declarations=r'''
#define MAX_MON_MOVES 4
typedef int BattleSystem;
typedef struct {
    struct { u16 moves[4]; } battleMons[4];
    int battlerIdAttacker,moveTemp,pointer;
} BattleContext;
static int randomCalls;
static int BattleSystem_Random(BattleSystem *system) {
#if QOL_MODERN_MOVES
    const int values[]={467,117,468,469};
#else
    const int values[]={32,117,70,21};
#endif
    assert(randomCalls<4); return values[randomCalls++];
}
static void BattleScriptIncrementPointer(BattleContext *ctx,int amount) { ctx->pointer+=amount; }
static BOOL BattleContext_CheckMoveUnuseableInGravity(BattleSystem *system,BattleContext *ctx,int battler,u16 move) { return FALSE; }
static BOOL BattleContext_CheckMoveHealBlocked(BattleSystem *system,BattleContext *ctx,int battler,u16 move) {
    return move==MOVE_DRAINING_KISS || move==MOVE_ABSORB;
}
'''
        util=(ROOT/'src/battle/battle_util.c').read_text()
        table=re.search(r'static const u16 sMetronomeUnuseableMoves\[\].*?\n\};',util,re.S)[0]
        actual=table+'\n'+game.function_source('src/battle/battle_util.c','CheckLegalMetronomeMove')
        actual+='\n'+game.function_source('src/battle/battle_command.c','BtlCmd_Metronome')
        checks=r'''
int main(void) {
    BattleContext ctx={0};
#if QOL_MODERN_MOVES
    ctx.battleMons[0].moves[0]=MOVE_DISARMING_VOICE;
#else
    ctx.battleMons[0].moves[0]=MOVE_TACKLE;
#endif
    assert(!BtlCmd_Metronome(NULL,&ctx));
    assert(randomCalls==4 && ctx.pointer==1);
#if QOL_MODERN_MOVES
    assert(ctx.moveTemp==MOVE_PLAY_ROUGH);
#else
    assert(ctx.moveTemp==MOVE_VINE_WHIP);
#endif
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_MOVES=1',)):
            self.compile_run(self.source()+declarations+actual+checks,*flags)

    def test_actual_heal_block_rejects_new_drain_and_modern_legacy_drains(self):
        declarations=r'''
typedef int BattleSystem;
typedef struct { struct { struct { int healBlockTurns; } moveEffectData; } battleMons[4]; } BattleContext;
'''
        util=(ROOT/'src/battle/battle_util.c').read_text()
        table=re.search(r'static const u16 sHealBlockUnusableMoves\[\].*?\n\};',util,re.S)[0]
        actual=table+'\n'+game.function_source('src/battle/battle_util.c','BattleContext_CheckMoveHealBlocked')
        checks=r'''
int main(void) {
    BattleContext ctx={0};
    const int drains[]={MOVE_ABSORB,MOVE_MEGA_DRAIN,MOVE_GIGA_DRAIN,MOVE_DREAM_EATER,MOVE_LEECH_LIFE,MOVE_DRAIN_PUNCH};
    for(int blocked=0;blocked<2;blocked++) {
        ctx.battleMons[0].moveEffectData.healBlockTurns=blocked;
        assert(BattleContext_CheckMoveHealBlocked(NULL,&ctx,0,MOVE_RECOVER)==blocked);
        assert(!BattleContext_CheckMoveHealBlocked(NULL,&ctx,0,MOVE_MOONBLAST));
        assert(BattleContext_CheckMoveHealBlocked(NULL,&ctx,0,MOVE_DRAINING_KISS)==(blocked&&QOL_MODERN_MOVES));
        for(unsigned i=0;i<NELEMS(drains);i++)
            assert(BattleContext_CheckMoveHealBlocked(NULL,&ctx,0,drains[i])==(blocked&&QOL_MODERN_BATTLE));
    }
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_MOVES=1',),('-DQOL_MODERN_BATTLE=1',),
                      ('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1')):
            self.compile_run(self.source()+declarations+actual+checks,*flags,'-Wno-sign-compare')

    def test_script_loader_bounds_extended_move_ids_before_archive_access(self):
        declarations=r'''
#define GF_ASSERT assert
typedef int NarcId;
enum {NARC_a_0_0_0,NARC_a_0_0_1};
typedef struct {int scriptNarcId,scriptFileId,scriptSeqNo,battleScriptBuffer;} BattleContext;
static int readId,sizeId;
static int GetNarcMemberSizeByIdPair(int narc,int id) {sizeId=id;return 4;}
static void ReadWholeNarcMemberByIdPair(void *out,int narc,int id) {readId=id;}
'''
        actual=game.function_source('src/battle/battle_util.c','ReadBattleScriptFromNarc')
        checks=r'''
int main(void) {
    const int ids[]={33,467,577,580,586,588,608,587,673,670,696,532,687,898,622,621,575,589,854,468,500,609,65535,65536,-1};
    for(unsigned i=0;i<NELEMS(ids);i++) {
        BattleContext ctx={0}; int expected=ids[i];
#if QOL_MODERN_MOVES
        if(i>=19) expected=0;
#endif
        ReadBattleScriptFromNarc(&ctx,NARC_a_0_0_0,ids[i]);
        assert(readId==expected && sizeId==expected && ctx.scriptFileId==expected);
        assert(ctx.scriptSeqNo==0);
    }
    BattleContext ctx={0};
    ReadBattleScriptFromNarc(&ctx,NARC_a_0_0_1,500);
    assert(readId==500 && ctx.scriptFileId==500);
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_MOVES=1',)):
            self.compile_run(self.source()+declarations+actual+checks,*flags)

if __name__=='__main__':
    unittest.main()
