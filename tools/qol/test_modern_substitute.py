"""Run real move helpers and script command against Substitute fixtures."""
from pathlib import Path
import unittest
import test_game_logic as game
import test_modern_moves

ROOT = Path(__file__).resolve().parents[2]


class SubstituteTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_sound_only_bypasses_in_modern_mode_and_script_reads_still_advance(self):
        source = test_modern_moves.ModernMoveTests().source() + r'''
#include "constants/battle.h"
typedef int BattleSystem;
typedef struct {
    struct { unsigned status2; } battleMons[4];
    struct { unsigned statusFlags; } selfTurnData[4];
    unsigned moveNoCur;
    int statChangeType,pointer,words[4],read;
} BattleContext;
static void BattleScriptIncrementPointer(BattleContext *ctx,int value) { ctx->pointer+=value; }
static int BattleScriptReadWord(BattleContext *ctx) { return ctx->words[ctx->read++]; }
static int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *ctx,int side) { return side; }
''' + game.function_source('src/battle/battle_command.c','BtlCmd_CheckSubstitute') + r'''
int main(void) {
    const int moves[]={MOVE_TACKLE,MOVE_HYPER_VOICE,MOVE_SING,MOVE_METAL_SOUND,MOVE_DISARMING_VOICE};
    for(int m=0;m<5;m++) for(int type=0;type<8;type++) for(int sub=0;sub<4;sub++) {
        BattleContext ctx={0};ctx.moveNoCur=moves[m];ctx.statChangeType=type;
        ctx.words[0]=1;ctx.words[1]=100;
        ctx.battleMons[1].status2=(sub&1)?STATUS2_SUBSTITUTE:0;
        ctx.selfTurnData[1].statusFlags=(sub&2)?8:0;
        int sound=m>0 && (m<4 || QOL_MODERN_MOVES);
        int bypass=(QOL_MODERN_BATTLE || QOL_MODERN_MOVES) && sound;
        assert(Qol_MoveBypassesSubstitute(moves[m])==bypass);
        int blocked=sub && !(bypass && (type==SIDE_EFFECT_TYPE_DIRECT || type==SIDE_EFFECT_TYPE_INDIRECT));
        assert(!BtlCmd_CheckSubstitute(NULL,&ctx));
        assert(ctx.pointer==(blocked?101:1) && ctx.read==2);
    }
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_MOVES=1',),('-DQOL_MODERN_BATTLE=1',),
                      ('-DQOL_MODERN_MOVES=1','-DQOL_MODERN_BATTLE=1')):
            self.compile_run(source,*flags)

    def test_hp_and_stat_substitute_branches_share_the_sound_predicate(self):
        hp=game.function_source('src/battle/battle_controller_player.c','BattleControllerPlayer_HpCalc')
        self.assertIn('!Qol_MoveBypassesSubstitute(ctx->moveNoCur)',hp)
        stat=game.function_source('src/battle/battle_command.c','BtlCmd_ChangeStatStage')
        self.assertIn('Qol_MoveBypassesSubstitute(ctx->moveNoCur)',stat)
        self.assertIn('ctx->statChangeType == SIDE_EFFECT_TYPE_DIRECT',stat)
        self.assertIn('ctx->statChangeType == SIDE_EFFECT_TYPE_INDIRECT',stat)

    def test_real_damage_command_hits_pokemon_or_substitute_and_sets_secondary_hit_flags(self):
        source=test_modern_moves.ModernMoveTests().source()+r'''
#include "constants/battle.h"
#include "constants/move_effects.h"
#include "constants/items.h"
#include "constants/abilities.h"
#include "constants/battle_subscript.h"
#define GF_ASSERT assert
typedef int BattleSystem;
enum {NARC_a_0_0_1,GAME_STAT_ALLIES_DAMAGED};
typedef struct {
    int hp,maxHp,hitCount; unsigned status2;
    struct {int substituteHp;} moveEffectData;
} Mon;
typedef struct {
    Mon battleMons[4];
    struct {MoveTbl moveData[NUM_MOVES+1];} trainerAIData;
    struct {
        int shellBellDamage,statusFlags,endureItemFlag,physicalDamage,battlerIdPhysicalAttacker,
            specialDamage,battlerIdSpecialAttacker;
    } selfTurnData[4];
    struct {
        int endureFlag,physicalDamage[4],battlerIdPhysicalDamage,battlerBitPhysicalDamage,
            specialDamage[4],battlerIdSpecialDamage,battlerBitSpecialDamage,lastDamageTaken,battlerIdLastDamage;
    } turnData[4];
    int moveStatusFlag,damage,battlerIdAttacker,battlerIdTarget,battlerIdStoredDamage[4],
        hitDamage,battlerIdTemp,command,commandNext,moveNoCur,storedDamage[4],hpCalc,battleStatus,script;
} BattleContext;
#if QOL_MODERN_BATTLE
static int CheckBattlerAbilityIfNotIgnored(BattleContext *c,int attacker,int target,int ability){return 0;}
#endif
static int GetBattlerHeldItemEffect(BattleContext *c,int b){return 0;}
static int GetHeldItemModifier(BattleContext *c,int b,int n){return 0;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b;}
static void BattleController_EmitIncrementGameStat(BattleSystem *s,int b,int a,int stat){}
static void ReadBattleScriptFromNarc(BattleContext *c,int narc,int script){c->script=script;}
static int BattleSystem_Random(BattleSystem *s){assert(0);return 0;}
static int MaskOfFlagNo(int n){return 1<<n;}
'''+game.function_source('src/battle/battle_controller_player.c','BattleControllerPlayer_HpCalc')+r'''
int main(void) {
    const int moves[]={MOVE_TACKLE,MOVE_HYPER_VOICE,MOVE_DISARMING_VOICE,MOVE_MOONBLAST};
    for(int m=0;m<4;m++) for(int amount=5;amount<=25;amount+=20) {
        BattleContext c={0}; c.battlerIdTarget=1;c.moveNoCur=moves[m];c.damage=-amount;
        c.battleMons[1].hp=c.battleMons[1].maxHp=100;
        c.battleMons[1].status2=STATUS2_SUBSTITUTE;c.battleMons[1].moveEffectData.substituteHp=20;
        int bypass=(QOL_MODERN_BATTLE || QOL_MODERN_MOVES) &&
            (m==1 || (m==2 && QOL_MODERN_MOVES));
        BattleControllerPlayer_HpCalc(NULL,&c);
        assert(c.command==CONTROLLER_COMMAND_RUN_SCRIPT && c.commandNext==CONTROLLER_COMMAND_29);
        if(bypass) {
            assert(c.script==BATTLE_SUBSCRIPT_UPDATE_HP && c.hpCalc==-amount);
            assert(c.battleMons[1].moveEffectData.substituteHp==20);
            assert(c.battleMons[1].status2&STATUS2_SUBSTITUTE);
            assert(!(c.selfTurnData[1].statusFlags&8));
        } else {
            assert(c.script==BATTLE_SUBSCRIPT_HIT_SUBSTITUTE);
            assert(c.battleMons[1].moveEffectData.substituteHp==(amount>20?0:20-amount));
            assert(c.selfTurnData[1].statusFlags&8);
            assert(c.hitDamage==-(amount>20?20:amount));
        }
    }
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_MOVES=1',),('-DQOL_MODERN_BATTLE=1',)):
            self.compile_run(source,*flags)


if __name__ == '__main__':
    unittest.main()
