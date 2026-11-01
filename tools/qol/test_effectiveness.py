"""Read-only preview rules execute against the same chart as battle damage."""
from pathlib import Path
import re
import struct
import unittest
import xml.etree.ElementTree as ET
import test_game_logic as game

ROOT = Path(__file__).resolve().parents[2]


class EffectivenessTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_move_name_and_indicator_fit_the_supplied_game_font(self):
        font_path = ROOT / "files/graphic/font/font_00000000.bin"
        names_path = ROOT / "files/msgdata/msg/msg_0750.gmm"
        if not font_path.exists() or not names_path.exists():
            self.skipTest("Requires the locally supplied game font and message assets")
        font = font_path.read_bytes()
        width_offset = struct.unpack_from("<I", font, 4)[0]
        widths = font[width_offset:]
        header = (ROOT / "include/constants/charcode.h").read_text()
        codes = {name: int(value) for name, value in re.findall(r"#define (CHAR_\w+)\s+(\d+)", header)}
        mapping = {c: codes["CHAR_" + c] for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"}
        mapping.update({" ": codes["CHAR_SPACE"], "-": codes["CHAR_HYPHEN"], ".": codes["CHAR_PERIOD"]})
        names = [row.find("language").text for row in ET.parse(names_path).getroot().findall("row")][:468]
        name_width = max(sum(widths[mapping[c] - 1] for c in name) for name in names)
        ui = (ROOT / "src/battle/battle_input.c").read_text()
        label_table = re.search(r"static const u16 labels\[\]\[6\] = \{(.*?)\n    \};", ui, re.S)[1]
        label_width = max(sum(widths[codes[code] - 1] for code in re.findall(r"CHAR_\w+", row))
                          for row in re.findall(r"\{([^{}]+)\}", label_table))
        # The name starts 4px inside the left edge; the indicator ends 4px
        # inside the right edge. Preserve at least 4px between the strings.
        self.assertLessEqual(name_width + label_width + 12, 108)

    def test_preview_handles_matchups_field_rules_and_has_no_state_changes(self):
        source = (ROOT / "src/battle/battle_util.c").read_text()
        arrays = "\n".join(re.search(r"static (?:const )?u(?:8|16) " + name +
                                     r"\[.*?\n\};", source, re.S)[0]
                           for name in ("sTypeEffectiveness", "sSoundMoves", "sFixedDamageMoveEffects"))
        declarations = r'''
#include <assert.h>
#include <stddef.h>
#include <string.h>
#include "constants/pokemon.h"
#include "constants/moves.h"
// Legacy-sized extracted-function fixtures use the production feature-off accessor.
#define BATTLE_MOVE_DATA(ctx, moveId) ((ctx)->trainerAIData.moveData[(moveId)])
#define Qol_IsSupportedMove(moveId) ((moveId) <= NUM_MOVES)
#include "constants/abilities.h"
#include "constants/items.h"
#include "constants/battle.h"
#include "constants/move_effects.h"
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define NELEMS(a) (sizeof(a)/sizeof((a)[0]))
typedef struct { int category, power, type, effect; } Move;
typedef struct { int hp, type1, type2, ability, itemEffect, useTypeOverride, typeOverride; u32 status, status2, moveEffectFlags;
                 struct { int magnetRiseTurns; } moveEffectData; } Mon;
typedef struct { Mon battleMons[4]; struct { Move moveData[NUM_MOVES+1]; } trainerAIData;
                 u32 fieldCondition; struct { int roostFlag; } turnData[4]; } BattleContext;
int GetBattlerHeldItemEffect(BattleContext *ctx, int battler) { return ctx->battleMons[battler].itemEffect; }
int GetBattlerVar(BattleContext *ctx, int battler, int field, void *unused) {
    Mon *mon = &ctx->battleMons[battler];
    return mon->useTypeOverride ? mon->typeOverride : field == BMON_DATA_TYPE_1 ? mon->type1 : mon->type2;
}
'''
        actual = arrays + "\n" + "\n".join(game.function_source("src/battle/battle_util.c", name) for name in
            ("GetBattlerAbility", "BattleSystem_IsTypeMatchupActive", "IsFixedDamageMove",
             "Qol_PreviewTypeEffectiveness"))
        checks = r'''
int main(void) {
    BattleContext ctx = {0}; ctx.battleMons[0].hp = ctx.battleMons[1].hp = ctx.battleMons[3].hp = 100;
    ctx.trainerAIData.moveData[MOVE_FLAMETHROWER] = (Move){1,90,TYPE_FIRE,0};
    ctx.trainerAIData.moveData[MOVE_EARTHQUAKE] = (Move){0,100,TYPE_GROUND,0};
    ctx.trainerAIData.moveData[MOVE_TACKLE] = (Move){0,40,TYPE_NORMAL,0};
    ctx.trainerAIData.moveData[MOVE_THUNDERBOLT] = (Move){1,90,TYPE_ELECTRIC,0};
    ctx.trainerAIData.moveData[MOVE_SURF] = (Move){1,90,TYPE_WATER,0};
    ctx.trainerAIData.moveData[MOVE_BUG_BUZZ] = (Move){1,90,TYPE_BUG,0};
    ctx.trainerAIData.moveData[MOVE_PSYCHIC] = (Move){1,90,TYPE_PSYCHIC,0};
    ctx.trainerAIData.moveData[MOVE_SWORDS_DANCE] = (Move){2,0,TYPE_NORMAL,0};
    ctx.trainerAIData.moveData[MOVE_SEISMIC_TOSS] = (Move){0,1,TYPE_FIGHTING,MOVE_EFFECT_LEVEL_DAMAGE_FLAT};
    ctx.trainerAIData.moveData[MOVE_HIDDEN_POWER] = (Move){1,1,TYPE_NORMAL,0};
    ctx.trainerAIData.moveData[MOVE_SUPER_FANG] = (Move){0,1,TYPE_NORMAL,MOVE_EFFECT_HALVE_HP};
    ctx.trainerAIData.moveData[MOVE_ENDEAVOR] = (Move){0,1,TYPE_NORMAL,MOVE_EFFECT_SET_HP_EQUAL_TO_USER};
    ctx.trainerAIData.moveData[MOVE_BIDE] = (Move){0,1,TYPE_NORMAL,MOVE_EFFECT_BIDE};
    ctx.trainerAIData.moveData[MOVE_PRESENT] = (Move){0,1,TYPE_NORMAL,MOVE_EFFECT_RANDOM_POWER_MAYBE_HEAL};
    ctx.trainerAIData.moveData[MOVE_SONIC_BOOM] = (Move){1,1,TYPE_NORMAL,MOVE_EFFECT_10_DAMAGE_FLAT};
    ctx.battleMons[1].type1 = TYPE_GRASS; ctx.battleMons[1].type2 = TYPE_STEEL;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_FLAMETHROWER,0,1) == 160);
    ctx.battleMons[1].type1 = TYPE_FIRE; ctx.battleMons[1].type2 = TYPE_DRAGON;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_FLAMETHROWER,0,1) == 10);
    ctx.battleMons[1].type1 = TYPE_GRASS; ctx.battleMons[1].type2 = TYPE_WATER;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_FLAMETHROWER,0,1) == 40);
    ctx.battleMons[1].type1 = ctx.battleMons[1].type2 = TYPE_GHOST;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_TACKLE,0,1) == 0);
    ctx.battleMons[1].status2 = STATUS2_FORESIGHT;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_TACKLE,0,1) == 40);
    ctx.battleMons[1].status2 = 0; ctx.battleMons[0].ability = ABILITY_SCRAPPY;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_TACKLE,0,1) == 40);
    ctx.battleMons[0].ability = ABILITY_NONE;
    ctx.battleMons[1].type1 = ctx.battleMons[1].type2 = TYPE_FLYING;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_EARTHQUAKE,0,1) == 0);
    ctx.fieldCondition = FIELD_CONDITION_GRAVITY;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_EARTHQUAKE,0,1) == 40);
    ctx.fieldCondition = 0; ctx.battleMons[1].itemEffect = HOLD_EFFECT_SPEED_DOWN_GROUNDED;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_EARTHQUAKE,0,1) == 40);
    ctx.battleMons[1].itemEffect = 0;
    ctx.battleMons[1].type1 = ctx.battleMons[1].type2 = TYPE_NORMAL;
    ctx.battleMons[1].ability = ABILITY_LEVITATE;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_EARTHQUAKE,0,1) == 0);
    ctx.battleMons[0].ability = ABILITY_MOLD_BREAKER;
    BattleContext before = ctx;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_EARTHQUAKE,0,1) == 40);
    assert(!memcmp(&before,&ctx,sizeof(ctx)));
    ctx.battleMons[0].ability = ABILITY_NONE;
    ctx.battleMons[1].moveEffectFlags = MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_EARTHQUAKE,0,1) == 40);
    ctx.battleMons[1].moveEffectFlags = 0;
    ctx.battleMons[1].ability = ABILITY_VOLT_ABSORB;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_THUNDERBOLT,0,1) == 0);
    ctx.battleMons[1].ability = ABILITY_WATER_ABSORB;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_SURF,0,1) == 0);
    ctx.battleMons[1].ability = ABILITY_FLASH_FIRE;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_FLAMETHROWER,0,1) == 0);
    ctx.battleMons[1].ability = ABILITY_SOUNDPROOF;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_BUG_BUZZ,0,1) == 0);
    ctx.battleMons[1].ability = ABILITY_WONDER_GUARD;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_FLAMETHROWER,0,1) == 0);
    ctx.battleMons[1].type1 = ctx.battleMons[1].type2 = TYPE_GRASS;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_FLAMETHROWER,0,1) == 80);
    ctx.battleMons[1].ability = ABILITY_NONE;
    ctx.battleMons[3].type1 = ctx.battleMons[3].type2 = TYPE_WATER;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_FLAMETHROWER,0,3) == 20);
    ctx.battleMons[3].useTypeOverride = 1; ctx.battleMons[3].typeOverride = TYPE_GRASS;
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_FLAMETHROWER,0,3) == 80);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_SWORDS_DANCE,0,1) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_SEISMIC_TOSS,0,1) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_HIDDEN_POWER,0,1) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_SUPER_FANG,0,1) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_ENDEAVOR,0,1) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_BIDE,0,1) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_PRESENT,0,1) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_SONIC_BOOM,0,1) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_TACKLE,0,-1) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_TACKLE,0,4) == -1);
    assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_TACKLE,0,2) == -1);
    before = ctx;
    for(int move=0;move<=NUM_MOVES;move++) Qol_PreviewTypeEffectiveness(&ctx,move,0,1);
    assert(!memcmp(&before,&ctx,sizeof(ctx)));
    return 0;
}
'''
        self.compile_run(declarations + actual + checks, "-Wno-sign-compare")
