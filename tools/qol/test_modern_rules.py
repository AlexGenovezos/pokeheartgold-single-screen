"""Host C harnesses execute the battle-rule source under independent build flags."""
from pathlib import Path
import re
import unittest

import test_game_logic as game

ROOT = Path(__file__).resolve().parents[2]
UTIL = 'src/battle/battle_util.c'
COMMAND = 'src/battle/battle_command.c'
PLAYER = 'src/battle/battle_controller_player.c'
COMMON = r'''
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "qol_config.h"
#include "constants/abilities.h"
#include "constants/battle.h"
#include "constants/battle_subscript.h"
#include "constants/items.h"
#include "constants/moves.h"
// Legacy-sized extracted-function fixtures use the production feature-off accessor.
#define BATTLE_MOVE_DATA(ctx, moveId) ((ctx)->trainerAIData.moveData[(moveId)])
#define Qol_IsSupportedMove(moveId) ((moveId) <= NUM_MOVES)
#include "constants/move_effects.h"
#include "constants/pokemon.h"
#include "constants/species.h"
typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef signed short s16;
typedef unsigned int u32;
typedef int s32;
typedef int BOOL;
typedef int BattleSystem;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
#define NELEMS(a) (sizeof(a)/sizeof((a)[0]))
// The original source must compile and expose missing behavior in the red run.
#ifndef QOL_MODERN_BATTLE
#define QOL_MODERN_BATTLE 0
#endif
static unsigned rng, rngCalls;
static int BattleSystem_Random(BattleSystem *bs) { rngCalls++; return rng; }
'''


def array(name, path=UTIL):
    return re.search(r'(?:static )?(?:const )?u(?:8|16) ' + name + r'\[[^;=]*= \{.*?\n\};',
                     (ROOT / path).read_text(), re.S)[0] + '\n'


def helper(name, path=COMMAND):
    if not re.search(r'\b' + name + r'\s*\(', (ROOT / path).read_text()):
        return ''
    return game.function_source(path, name) + '\n'


class ModernRulesTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def variants(self, source, *flags):
        for variant in ((), ('-DQOL_MODS=1',), ('-DQOL_MODERN_BATTLE=0',),
                        ('-DQOL_MODERN_BATTLE=1',),
                        ('-DQOL_MODS=1', '-DQOL_MODERN_BATTLE=1')):
            with self.subTest(flags=variant):
                self.compile_run(source, *variant, *flags)

    def test_independent_flag_and_consumer_includes(self):
        self.assertRegex((ROOT / 'include/qol_config.h').read_text(),
                         r'#ifndef QOL_MODERN_BATTLE\s+#define QOL_MODERN_BATTLE 0\s+#endif')
        for path in (UTIL, COMMAND, PLAYER):
            self.assertIn('#include "qol_config.h"', (ROOT / path).read_text())

    def test_critical_chance_boundaries_armor_lucky_chant_sniper(self):
        declarations = r'''
typedef struct { int species, status2, moveEffectFlags, ability, item; } Mon;
typedef struct { Mon battleMons[4]; } BattleContext;
static int GetBattlerHeldItem(BattleContext *ctx, int id) { return ctx->battleMons[id].item; }
static int GetItemVar(BattleContext *ctx, int item, int field) { return item; }
int GetBattlerAbility(BattleContext *ctx, int id) { return ctx->battleMons[id].ability; }
static int CheckBattlerAbilityIfNotIgnored(BattleContext *ctx,int a,int d,int ability) { return ctx->battleMons[d].ability == ability; }
'''
        actual = array('sCritChance') + game.function_source(UTIL, 'TryCriticalHit')
        checks = r'''
int main(void) {
    const int modern[] = {24,8,2,1,1}, legacy[] = {16,8,4,3,2};
    const int *rates = QOL_MODERN_BATTLE ? modern : legacy;
    BattleContext ctx = {0};
    for (int stage = 0; stage < 8; stage++) {
        int denominator = rates[stage > 4 ? 4 : stage];
        for (rng = 0; rng < 96; rng++) {
            rngCalls = 0;
            assert(TryCriticalHit(NULL,&ctx,0,1,stage,0) == (rng % denominator == 0 ? 2u : 1u));
            assert(rngCalls == 1);
        }
    }
    rng = 0;
    ctx.battleMons[0].ability = ABILITY_SNIPER;
    assert(TryCriticalHit(NULL,&ctx,0,1,0,0) == 3);
    int armor[] = {ABILITY_BATTLE_ARMOR,ABILITY_SHELL_ARMOR};
    for (size_t i=0; i<NELEMS(armor); i++) {
        ctx.battleMons[1].ability = armor[i];
        assert(TryCriticalHit(NULL,&ctx,0,1,4,0) == 1);
    }
    ctx.battleMons[1].ability = ABILITY_NONE;
    assert(TryCriticalHit(NULL,&ctx,0,1,4,SIDE_CONDITION_LUCKY_CHANT) == 1);
    ctx.battleMons[1].moveEffectFlags = MOVE_EFFECT_FLAG_LUCKY_CHANT;
    assert(TryCriticalHit(NULL,&ctx,0,1,4,0) == 1);
    ctx.battleMons[1].moveEffectFlags = 0;
    ctx.battleMons[0].ability = ABILITY_SUPER_LUCK;
    ctx.battleMons[0].status2 = STATUS2_FOCUS_ENERGY;
    rng = 1;
    assert(TryCriticalHit(NULL,&ctx,0,1,0,0) == (QOL_MODERN_BATTLE ? 2u : 1u));
    return 0;
}
'''
        self.variants(COMMON + declarations + actual + checks)

    def test_both_speed_operands_and_quick_feet(self):
        declarations = r'''
typedef struct { int priority; } Move;
typedef struct {
    int hp, maxHp, speed, statChanges[8], item, species, ability, status;
    struct { int slowStartTurns, knockOffFlag, quickClawFlag, custapBerryFlag; } moveEffectData;
} Mon;
typedef struct {
    Mon battleMons[4];
    unsigned fieldCondition, fieldSideConditionFlags[2], effectiveSpeed[4];
    int totalTurns, quickClawRandom[4], movePos[4];
    struct { int inputSelection; } playerActions[4];
    struct { int struggleFlag; } turnData[4];
    struct { Move moveData[NUM_MOVES+1]; int calcTemp; } trainerAIData;
} BattleContext;
int GetBattlerAbility(BattleContext *ctx, int id) { return ctx->battleMons[id].ability; }
static int GetBattlerHeldItemEffect(BattleContext *ctx, int id) { return 0; }
static int GetHeldItemModifier(BattleContext *ctx,int id,int field) { return 1; }
static int GetItemVar(BattleContext *ctx,int item,int field) { return 0; }
static int GetBattlerVar(BattleContext *ctx,int id,int field,void *unused) { return MOVE_TACKLE; }
static int BattleSystem_GetFieldSide(BattleSystem *bs,int id) { return id & 1; }
static int CheckAbilityActive(BattleSystem *bs,BattleContext *ctx,int scope,int id,int ability) { return 0; }
'''
        actual = array('sSpeedHalvingItemEffects') + array('sStatChangeTable') + game.function_source(UTIL, 'CheckSortSpeed')
        checks = r'''
int main(void) {
    BattleContext ctx = {0};
    for (int id=0; id<2; id++) {
        ctx.battleMons[id].hp = ctx.battleMons[id].maxHp = 100;
        ctx.battleMons[id].speed = 101;
        ctx.battleMons[id].statChanges[3] = 6;
        ctx.battleMons[id].status = STATUS_PARALYSIS;
    }
    CheckSortSpeed(NULL,&ctx,0,1,1);
    assert(ctx.effectiveSpeed[0] == (QOL_MODERN_BATTLE ? 50u : 25u));
    assert(ctx.effectiveSpeed[1] == ctx.effectiveSpeed[0]);
    ctx.battleMons[0].ability = ABILITY_QUICK_FEET;
    ctx.battleMons[1].speed = 40;
    assert(CheckSortSpeed(NULL,&ctx,0,1,1) == 0);
    assert(ctx.effectiveSpeed[0] == 151);
    ctx.battleMons[0].ability = ABILITY_NONE;
    ctx.battleMons[0].status = 0;
    ctx.battleMons[0].speed = 40;
    ctx.battleMons[1].speed = 100;
    assert(CheckSortSpeed(NULL,&ctx,0,1,1) == (QOL_MODERN_BATTLE ? 1 : 0));
    ctx.fieldCondition = FIELD_CONDITION_TRICK_ROOM;
    assert(CheckSortSpeed(NULL,&ctx,0,1,1) == (QOL_MODERN_BATTLE ? 0 : 1));
    return 0;
}
'''
        self.variants(COMMON + declarations + actual + checks, '-Wno-sign-compare')

    def test_critical_damage_paths_and_final_sniper_rounding(self):
        declarations = r'''
typedef struct { int power, type, range; } Move;
typedef struct {
    int species, form;
    struct { int metronomeTurns, meFirstFlag, meFirstCount; } moveEffectData;
} Mon;
typedef struct {
    Mon battleMons[4];
    struct { Move moveData[NUM_MOVES+1]; int calcTemp; } trainerAIData;
    struct { int helpingHandFlag; } turnData[4];
    int damage, criticalMultiplier, battlerIdAttacker, battlerIdTarget;
    int moveType, moveNoCur, movePower, fieldSideConditionFlags[2], fieldCondition;
    int meFirstTotal, multiHitCountTemp, checkMultiHit, beatUpCount, selectedMonIndex[4], multiHitCount;
    struct { int id, tag, param[4]; } buffMsg;
    unsigned moveStatusFlag;
    unsigned battleStatus;
    struct { int noEffect; } moveFail[4];
} BattleContext;
typedef int Pokemon;
enum { msg_0197_00481, TAG_NICKNAME };
static int baseDamage, lastCrit, effectiveness=10;
int GetBattlerAbility(BattleContext *ctx,int id) { return ABILITY_NONE; }
static int GetBattlerHeldItemEffect(BattleContext *ctx,int id) { return 0; }
static int GetHeldItemModifier(BattleContext *ctx,int id,int unused) { return 0; }
static int BattleSystem_GetFieldSide(BattleSystem *bs,int id) { return id&1; }
static int CalcMoveDamage(BattleSystem *bs,BattleContext *ctx,int move,int side,int field,int power,int type,int a,int d,int crit) { lastCrit=crit; return baseDamage; }
static void BattleScriptIncrementPointer(BattleContext *ctx,int count) {}
static int ApplyDamageRange(BattleSystem *bs,BattleContext *ctx,int damage) { return damage*(100-BattleSystem_Random(bs)%16)/100; }
static int BattleSystem_GetPartySize(BattleSystem *bs,int id) { return 1; }
static Pokemon *BattleSystem_GetPartyMon(BattleSystem *bs,int id,int slot) { return NULL; }
static int GetMonData(Pokemon *mon,int field,void *unused) { return field==MON_DATA_LEVEL ? 50 : 100; }
static int GetMonBaseStat_HandleAlternateForm(int species,int form,int attr) { return attr==BASE_ATK ? baseDamage : 100; }
static int BattleSystem_ApplyTypeEffectiveness(BattleSystem *bs,BattleContext *ctx,int move,int type,int a,int d,int damage,unsigned *flags) { return damage*effectiveness/10; }
'''
        actual = helper('Qol_ApplyCriticalDamage') + '\n'.join(game.function_source(COMMAND, name) for name in
            ('DamageCalcDefault', 'BtlCmd_CalcDamage', 'BtlCmd_CalcDamageRaw', 'BtlCmd_BeatUp', 'BtlCmd_ApplyTypeEffectiveness'))
        actual += game.function_source(PLAYER, 'BattleControllerPlayer_ApplyTypeEffectiveness')
        checks = r'''
int main(void) {
    BattleContext ctx={0}; ctx.battlerIdTarget=1;
    ctx.trainerAIData.moveData[0].power=50;
    for (int crit=1; crit<=3; crit++) for (baseDamage=1; baseDamage<40; baseDamage++) {
        ctx.criticalMultiplier=crit; rng=0;
        BtlCmd_CalcDamageRaw(NULL,&ctx);
        int expected=QOL_MODERN_BATTLE && crit>1 ? baseDamage*3/2 : baseDamage*crit;
        assert(ctx.damage==-expected && lastCrit==crit && ctx.criticalMultiplier==crit);
        for (int sign=-1; sign<=1; sign+=2) for(int amount=1; amount<40; amount++) {
            ctx.damage=sign*amount;
            effectiveness=5;
            int want=sign*(amount/2);
            if (QOL_MODERN_BATTLE && crit==3) want=want*3/2;
            BtlCmd_ApplyTypeEffectiveness(NULL,&ctx);
            assert(ctx.damage==want);
            ctx.damage=sign*amount;
            BattleControllerPlayer_ApplyTypeEffectiveness(NULL,&ctx);
            assert(ctx.damage==want);
        }
        effectiveness=10;
        rng=15; BtlCmd_CalcDamage(NULL,&ctx);
        assert(ctx.damage==-(expected*85/100));
        if (QOL_MODERN_BATTLE && crit==3) {
            int afterRandom=expected*85/100;
            BtlCmd_ApplyTypeEffectiveness(NULL,&ctx);
            assert(ctx.damage==-(afterRandom*3/2));
        }
        // Beat Up has its own damage command: exercise that whole path too.
        ctx.multiHitCountTemp=1; ctx.beatUpCount=0; rng=0;
        int beatBase=baseDamage*50*22/100/50+2;
        int beatExpected=QOL_MODERN_BATTLE && crit>1 ? beatBase*3/2 : beatBase*crit;
        if(QOL_MODERN_BATTLE && crit==3) beatExpected=beatExpected*3/2;
        BtlCmd_BeatUp(NULL,&ctx);
        assert(ctx.damage==-beatExpected);
        // Beat Up's source script skips effectiveness, so it must finish Sniper
        // in its own damage command. The controller must leave it alone.
        ctx.battleStatus=BATTLE_STATUS_IGNORE_TYPE_IMMUNITY;
        BattleControllerPlayer_ApplyTypeEffectiveness(NULL,&ctx);
        assert(ctx.damage==-beatExpected);
        ctx.battleStatus=0;
    }
    return 0;
}
'''
        self.variants(COMMON + declarations + actual + checks)

    def test_facade_burn_exception_and_critical_stage_screen_bypass(self):
        import test_modern_snow as snow
        source = snow.damage_source()
        checks = r'''
int main(void) {
    // Force linkage of the common RNG stub; base damage itself does not roll.
    (void)BattleSystem_Random(NULL);
    BattleContext ctx={0}; ctx.powerMultiplier=10;
    for (int id=0; id<2; id++) {
        vars[id][BMON_DATA_ATK]=vars[id][BMON_DATA_SPATK]=100;
        vars[id][BMON_DATA_DEF]=vars[id][BMON_DATA_SPDEF]=100;
        vars[id][BMON_DATA_LEVEL]=50;
        vars[id][BMON_DATA_GENDER]=MON_GENDERLESS;
        vars[id][BMON_DATA_STAT_CHANGE_ATK]=vars[id][BMON_DATA_STAT_CHANGE_SPATK]=6;
        vars[id][BMON_DATA_STAT_CHANGE_DEF]=vars[id][BMON_DATA_STAT_CHANGE_SPDEF]=6;
    }
    int moves[]={MOVE_TACKLE,MOVE_FACADE};
    for(size_t i=0;i<NELEMS(moves);i++) {
        int move=moves[i]; ctx.trainerAIData.moveData[move]=(Move){100,TYPE_NORMAL,CATEGORY_PHYSICAL,0,0};
        vars[0][BMON_DATA_STATUS]=0;
        assert(CalcMoveDamage(NULL,&ctx,move,0,0,0,0,0,1,1)==46);
        vars[0][BMON_DATA_STATUS]=STATUS_BURN;
        assert(CalcMoveDamage(NULL,&ctx,move,0,0,0,0,0,1,1)==(QOL_MODERN_BATTLE && move==MOVE_FACADE ? 46 : 24));
    }
    vars[0][BMON_DATA_STATUS]=0;
    vars[0][BMON_DATA_STAT_CHANGE_ATK]=vars[0][BMON_DATA_STAT_CHANGE_SPATK]=0;
    vars[1][BMON_DATA_STAT_CHANGE_DEF]=vars[1][BMON_DATA_STAT_CHANGE_SPDEF]=12;
    for(int category=0;category<2;category++) {
        ctx.trainerAIData.moveData[MOVE_TACKLE].category=category;
        unsigned screen=category==CATEGORY_PHYSICAL ? SIDE_CONDITION_REFLECT : SIDE_CONDITION_LIGHT_SCREEN;
        for(int crit=2;crit<=3;crit++) assert(CalcMoveDamage(NULL,&ctx,MOVE_TACKLE,screen,0,0,0,0,1,crit)==46);
        assert(CalcMoveDamage(NULL,&ctx,MOVE_TACKLE,screen,0,0,0,0,1,1)<46);
    }
    return 0;
}
'''
        self.variants(source + checks, '-Wno-sign-compare', '-Wno-unused-function')

    def test_protect_full_streak_shared_moves_bounds_and_storage(self):
        header = (ROOT / 'include/battle/battle.h').read_text()
        structure = header[header.index('typedef struct MoveEffectData {'):header.index('} MoveEffectData;')+len('} MoveEffectData;')]
        declarations = r'''
enum { msg_0197_00282, msg_0197_00442, TAG_NICKNAME };
typedef struct { int effect; } Move;
typedef struct { MoveEffectData moveEffectData; } Mon;
typedef struct {
    Mon battleMons[4];
    int battlerIdAttacker, moveNoProtect[4], battlersOnField, moveNoCur;
    struct { Move moveData[NUM_MOVES+1]; int calcTemp; } trainerAIData;
    struct { int protectFlag, endureFlag; } turnData[4];
    struct { int id, tag, param[4]; } buffMsg;
} BattleContext;
static int jumps;
static void BattleScriptIncrementPointer(BattleContext *ctx,int count) { jumps+=count; }
static int BattleScriptReadWord(BattleContext *ctx) { return 10; }
static int CreateNicknameTag(BattleContext *ctx,int id) { return id; }
static void AIScript_IncrementCursor(BattleContext *ctx,int count) {}
static int AIScript_Read(BattleContext *ctx) { return 0; }
static int AIScript_Battler(BattleContext *ctx,int id) { return id; }
u16 sProtectSuccessChance[4]={65535,32767,16383,8191};
'''
        actual = '\n'.join(helper(name, UTIL) for name in ('Qol_GetProtectSuccessTurns', 'Qol_SetProtectSuccessTurns'))
        # Execute the actual switch cases used by scripts, resets, and AI.
        for function, wrapper, args, prefix, suffix in (
            ('GetBattlerVar','GetBattlerVar','BattleContext *ctx,int id,int field,void *unused','Mon *mon=&ctx->battleMons[id];','return 0;'),
            ('SetBattlerVar','SetBattlerVar','BattleContext *ctx,int id,int field,void *data','Mon *mon=&ctx->battleMons[id]; u8 *data8=data;',''),
            ('BattleMon_AddVar','AddBattlerVar','BattleContext *ctx,int id,int field,int data','Mon *mon=&ctx->battleMons[id];','')):
            source = game.function_source(UTIL, function)
            start = source.index('    case BMON_DATA_PROTECT_SUCCESS_COUNT:')
            end = source.index('    case ', start+10)
            actual += ('static '+('int' if wrapper.startswith('Get') else 'void')+' '+wrapper+'('+args+') {'+prefix+'switch(field){\n'+source[start:end]+'}\n'+suffix+'}\n')
        actual += helper('Qol_TryProtection')
        # Include the modern denominator table when it exists.
        if 'sModernProtectDenominators' in (ROOT / COMMAND).read_text():
            actual = array('sModernProtectDenominators', COMMAND) + actual
        actual += game.function_source(COMMAND, 'BtlCmd_TryProtection')
        actual += game.function_source('src/battle/trainer_ai.c', 'AICmd_LoadProtectSuccessChain')
        checks = r'''
int main(void) {
    BattleContext ctx={0}; ctx.battlersOnField=2;
    const int denominators[]={1,3,9,27,81,243,729};
    const int moves[]={MOVE_PROTECT,MOVE_DETECT,MOVE_ENDURE};
    // Original two-word bitfield layout and following data remain unchanged.
    assert(sizeof(MoveEffectData)==56);
    assert(offsetof(MoveEffectData,rechargeCount)==8);
    assert(offsetof(MoveEffectData,heldItemRestoreHp)==52);
    // A full streak reaches 6 without wrapping the original two-bit field.
    for(int streak=0;streak<9;streak++) {
        int move=moves[streak%3];
        ctx.moveNoCur=move;
        ctx.trainerAIData.moveData[move].effect=move==MOVE_ENDURE ? MOVE_EFFECT_SURVIVE_WITH_1_HP : MOVE_EFFECT_PROTECT;
        rng=0; jumps=0;
        BtlCmd_TryProtection(NULL,&ctx);
        int wanted=streak+1;
        if(wanted>(QOL_MODERN_BATTLE ? 6 : 3)) wanted=QOL_MODERN_BATTLE ? 6 : 3;
        assert(GetBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,NULL)==wanted);
        assert(jumps==1);
        ctx.moveNoProtect[0]=move;
        AICmd_LoadProtectSuccessChain(NULL,&ctx);
        assert(ctx.trainerAIData.calcTemp==wanted);
    }
    for(int stage=0;stage<7;stage++) {
        u8 count=stage;
        SetBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,&count);
        assert(GetBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,NULL)==(QOL_MODERN_BATTLE ? stage : stage%4));
        if(!QOL_MODERN_BATTLE) continue;
        for(rng=0;rng<(unsigned)(denominators[stage]*2);rng++) {
            SetBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,&count);
            jumps=0; BtlCmd_TryProtection(NULL,&ctx);
            assert((jumps==1)==(rng%denominators[stage]==0));
        }
    }
    u8 count=255;
    SetBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,&count);
    assert(GetBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,NULL)==(QOL_MODERN_BATTLE ? 6 : 3));
    AddBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,1);
    assert(GetBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,NULL)==(QOL_MODERN_BATTLE ? 6 : 0));
    ctx.moveNoProtect[0]=MOVE_TACKLE; rng=0;
    AICmd_LoadProtectSuccessChain(NULL,&ctx);
    assert(ctx.trainerAIData.calcTemp==0);
    BtlCmd_TryProtection(NULL,&ctx);
    assert(GetBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,NULL)==1);
    ctx.moveNoProtect[0]=MOVE_PROTECT;ctx.battlersOnField=1;
    BtlCmd_TryProtection(NULL,&ctx);
    assert(GetBattlerVar(&ctx,0,BMON_DATA_PROTECT_SUCCESS_COUNT,NULL)==0);
    return 0;
}
'''
        self.variants(COMMON + structure + declarations + actual + checks, '-Wno-unused-function', '-Wno-sign-compare')

    def test_conversion_preserves_fairy_slot_nine(self):
        declarations = r'''
typedef struct {
    struct { int type1,type2,moves[4]; } battleMons[4];
    struct { struct { int type; } moveData[NUM_MOVES+1]; } trainerAIData;
    int battlerIdAttacker, msgTemp;
} BattleContext;
int GetBattlerAbility(BattleContext *ctx,int id) { return ABILITY_NONE; }
static int GetBattlerVar(BattleContext *ctx,int id,int field,void *unused) { return field==BMON_DATA_TYPE_1 ? ctx->battleMons[id].type1 : ctx->battleMons[id].type2; }
static void BattleScriptIncrementPointer(BattleContext *ctx,int count) {}
static int BattleScriptReadWord(BattleContext *ctx) { return 10; }
'''
        checks = r'''
int main(void) {
    BattleContext ctx={0}; ctx.battleMons[0].type1=ctx.battleMons[0].type2=TYPE_FIRE;
    ctx.battleMons[0].moves[0]=MOVE_CHARM;
    ctx.trainerAIData.moveData[MOVE_CHARM].type=TYPE_FAIRY;
    BtlCmd_TryConversion(NULL,&ctx);
    int expected=QOL_MODERN_TYPES ? TYPE_FAIRY : TYPE_NORMAL;
    assert(ctx.battleMons[0].type1==expected && ctx.battleMons[0].type2==expected);
    return 0;
}
'''
        for types in ('-DQOL_MODERN_TYPES=0', '-DQOL_MODERN_TYPES=1'):
            self.variants(COMMON + declarations + game.function_source(COMMAND, 'BtlCmd_TryConversion') + checks, types)

    def test_confusion_and_paralysis_execute_actual_controller_cases(self):
        declarations = r'''
#include "constants/battle_subscript.h"
enum { NARC_a_0_0_1 };
typedef struct {
    struct { int status2, status, ability; } battleMons[4];
    struct { int confusion, paralysis; } moveFail[4];
    int battlerIdAttacker, battlerIdTarget, battlerIdTemp, hpCalc;
    int command, commandNext, checkAttackerStatusState;
} BattleContext;
static int script;
static void ReadBattleScriptFromNarc(BattleContext *ctx,int narc,int id) { script=id; }
int GetBattlerAbility(BattleContext *ctx,int id) { return ctx->battleMons[id].ability; }
static int CalcMoveDamage(BattleSystem *bs,BattleContext *ctx,int move,int side,int field,int power,int type,int a,int d,int crit) { assert(power==40 && a==d && crit==1); return 20; }
static int ApplyDamageRange(BattleSystem *bs,BattleContext *ctx,int damage) { return damage; }
'''
        source = game.function_source(PLAYER, 'BattleControllerPlayer_CheckAttackerStatus')
        cases = source[source.index('        case 11:'):source.index('        case 13:')]
        actual = 'static int Check(BattleSystem *battleSystem,BattleContext *ctx) { int ret=0; switch(ctx->checkAttackerStatusState) {\n' + cases + '\n} return ret; }\n'
        checks = r'''
int main(void) {
    for (rng=0; rng<12; rng++) {
        BattleContext ctx={0}; ctx.battleMons[0].status2=3; ctx.checkAttackerStatusState=11;
        int hurt = QOL_MODERN_BATTLE ? rng%3==0 : rng%2==0;
        assert(Check(NULL,&ctx) == (hurt ? 1 : 2));
        assert(ctx.moveFail[0].confusion == hurt);
        assert(script == (hurt ? BATTLE_SUBSCRIPT_HURT_SELF_IN_CONFUSION : BATTLE_SUBSCRIPT_CONFUSED));
        assert(ctx.battleMons[0].status2 == 2);
    }
    BattleContext ctx={0}; ctx.battleMons[0].status2=1; ctx.checkAttackerStatusState=11;
    rngCalls=0; assert(Check(NULL,&ctx)==2 && rngCalls==0);
    assert(script==BATTLE_SUBSCRIPT_SNAP_OUT_OF_CONFUSION);
    for (int guard=0; guard<2; guard++) for(rng=0; rng<4; rng++) {
        memset(&ctx,0,sizeof(ctx)); ctx.checkAttackerStatusState=12;
        ctx.battleMons[0].status=STATUS_PARALYSIS;
        ctx.battleMons[0].ability=guard ? ABILITY_MAGIC_GUARD : ABILITY_NONE;
        int stopped=rng==0 && (QOL_MODERN_BATTLE || !guard);
        assert(Check(NULL,&ctx)==stopped);
        assert(ctx.moveFail[0].paralysis==stopped);
    }
    return 0;
}
'''
        self.variants(COMMON + declarations + actual + checks)


if __name__ == '__main__':
    unittest.main()
