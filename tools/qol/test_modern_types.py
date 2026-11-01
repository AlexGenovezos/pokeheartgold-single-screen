"""Execute the source type chart and data loaders, with only NARC/heap I/O stubbed."""
from pathlib import Path
import re
import unittest

import test_game_logic as game

ROOT = Path(__file__).resolve().parents[2]

# Independent full modern matrix: attacker rows, defender columns. Values are
# quarter-neutral units: 0 immune, 1 resisted, 2 neutral, 4 super effective.
# Keep this in conventional chart order, separate from the game's type IDs and
# sparse exception table. This fixture is not generated from production data.
TYPES = "NORMAL FIRE WATER ELECTRIC GRASS ICE FIGHTING POISON GROUND FLYING PSYCHIC BUG ROCK GHOST DRAGON DARK STEEL FAIRY".split()
MODERN_MATRIX = """
2 2 2 2 2 2 2 2 2 2 2 2 1 0 2 2 1 2
2 1 1 2 4 4 2 2 2 2 2 4 1 2 1 2 4 2
2 4 1 2 1 2 2 2 4 2 2 2 4 2 1 2 2 2
2 2 4 1 1 2 2 2 0 4 2 2 2 2 1 2 2 2
2 1 4 2 1 2 2 1 4 1 2 1 4 2 1 2 1 2
2 1 1 2 4 1 2 2 4 4 2 2 2 2 4 2 1 2
4 2 2 2 2 4 2 1 2 1 1 1 4 0 2 4 4 1
2 2 2 2 4 2 2 1 1 2 2 2 1 1 2 2 0 4
2 4 2 4 1 2 2 4 2 0 2 1 4 2 2 2 4 2
2 2 2 1 4 2 4 2 2 2 2 4 1 2 2 2 1 2
2 2 2 2 2 2 4 4 2 2 1 2 2 2 2 0 1 2
2 1 2 2 4 2 1 1 2 1 4 2 2 1 2 4 1 1
2 4 2 2 2 4 1 2 1 4 2 4 2 2 2 2 1 2
0 2 2 2 2 2 2 2 2 2 4 2 2 4 2 1 2 2
2 2 2 2 2 2 2 2 2 2 2 2 2 2 4 2 1 0
2 2 2 2 2 2 1 2 2 2 4 2 2 4 2 1 2 1
2 1 1 1 2 4 2 2 2 2 2 2 4 2 2 2 1 4
2 1 2 2 2 2 4 1 2 2 2 2 2 2 4 4 1 2
"""

# Species, original type pair, modern type pair. All twenty existing-roster
# Fairy changes; unrelated metadata and every other species must be preserved.
SPECIES_TYPES = """
CLEFAIRY NORMAL NORMAL FAIRY FAIRY
CLEFABLE NORMAL NORMAL FAIRY FAIRY
JIGGLYPUFF NORMAL NORMAL NORMAL FAIRY
WIGGLYTUFF NORMAL NORMAL NORMAL FAIRY
MR_MIME PSYCHIC PSYCHIC PSYCHIC FAIRY
CLEFFA NORMAL NORMAL FAIRY FAIRY
IGGLYBUFF NORMAL NORMAL NORMAL FAIRY
TOGEPI NORMAL NORMAL FAIRY FAIRY
TOGETIC NORMAL FLYING FAIRY FLYING
MARILL WATER WATER WATER FAIRY
AZUMARILL WATER WATER WATER FAIRY
SNUBBULL NORMAL NORMAL FAIRY FAIRY
GRANBULL NORMAL NORMAL FAIRY FAIRY
RALTS PSYCHIC PSYCHIC PSYCHIC FAIRY
KIRLIA PSYCHIC PSYCHIC PSYCHIC FAIRY
GARDEVOIR PSYCHIC PSYCHIC PSYCHIC FAIRY
AZURILL NORMAL NORMAL NORMAL FAIRY
MAWILE STEEL STEEL STEEL FAIRY
MIME_JR PSYCHIC PSYCHIC PSYCHIC FAIRY
TOGEKISS NORMAL FLYING FAIRY FLYING
"""

COMMON = r'''
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qol_config.h"
#include "constants/pokemon.h"
#include "constants/species.h"
#include "constants/moves.h"
// Legacy-sized extracted-function fixtures use the production feature-off accessor.
#define BATTLE_MOVE_DATA(ctx, moveId) ((ctx)->trainerAIData.moveData[(moveId)])
#define Qol_IsSupportedMove(moveId) ((moveId) <= NUM_MOVES)
typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
// Let the preimplementation chart/loaders execute and fail on their behavior.
#ifndef TYPE_FAIRY
#define TYPE_FAIRY 9
#endif
#define NELEMS(a) (sizeof(a) / sizeof((a)[0]))
'''


def optional_helper(path, name):
    """A missing new helper must not prevent observing the original loaders."""
    if not re.search(r"\b" + name + r"\s*\(", (ROOT / path).read_text()):
        return ""
    return "\n#if QOL_MODERN_TYPES\n" + game.function_source(path, name) + "\n#endif\n"


class ModernTypeTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def run_variants(self, source, *extra_flags):
        for flags in ((), ("-DQOL_MODS=1",), ("-DQOL_MODERN_TYPES=0",),
                      ("-DQOL_MODERN_TYPES=1",),
                      ("-DQOL_MODS=1", "-DQOL_MODERN_TYPES=1")):
            with self.subTest(flags=flags):
                self.compile_run(source, *flags, *extra_flags)

    def test_fairy_alias_and_independent_default_off_flag(self):
        self.assertRegex((ROOT / "include/constants/pokemon.h").read_text(),
                         r"#define\s+TYPE_FAIRY\s+(?:9|TYPE_MYSTERY)\b")
        self.assertRegex((ROOT / "include/qol_config.h").read_text(),
                         r"#ifndef QOL_MODERN_TYPES\s+#define QOL_MODERN_TYPES 0\s+#endif")
        self.compile_run(COMMON + r'''
int main(void) {
    assert(TYPE_FAIRY == 9 && TYPE_MYSTERY == 9);
    assert(NUMBER_OF_MON_TYPES == 18 && QOL_MODERN_TYPES == 0);
    return 0;
}
''', "-DQOL_MODS=1")

    def test_production_consumers_include_flag_defaults(self):
        for path in ("src/move.c", "src/pokemon.c", "src/battle/battle_util.c"):
            with self.subTest(path=path):
                self.assertTrue('#include "qol_config.h"' in (ROOT / path).read_text(), path)

    def test_all_single_and_dual_type_matchups_against_full_matrix(self):
        table = re.search(r"static const u8 sTypeEffectiveness\[\]\[3\] = \{.*?\n\};",
                          (ROOT / "src/battle/battle_util.c").read_text(), re.S)[0]
        rows = [line.split() for line in MODERN_MATRIX.strip().splitlines()]
        self.assertEqual(len(rows), 18)
        self.assertTrue(all(len(row) == 18 for row in rows))
        expected = "static const int expected[18][18] = {\n" + ",\n".join(
            "{" + ",".join(str(int(value) * 20) for value in row) + "}" for row in rows) + "\n};\n"
        types = "static const int types[] = {" + ",".join("TYPE_" + t for t in TYPES) + "};\n"
        actual = table + "\n" + game.function_source("src/battle/battle_util.c", "CalculateTypeEffectiveness")
        checks = r'''
static int Expected(int attacker, int defender) {
#if !QOL_MODERN_TYPES
    if (types[attacker] == TYPE_FAIRY || types[defender] == TYPE_FAIRY) return 40;
    if ((types[attacker] == TYPE_GHOST || types[attacker] == TYPE_DARK) && types[defender] == TYPE_STEEL) return 20;
#endif
    return expected[attacker][defender];
}
int main(void) {
    // No duplicated pairs; immunity to Dragon must not be placed after the
    // Foresight sentinel (which bypasses only Normal/Fighting vs Ghost).
    int seenForesight = 0;
    for (size_t row = 0; row < NELEMS(sTypeEffectiveness); row++) {
        if (sTypeEffectiveness[row][0] == TYPE_FORESIGHT) seenForesight = 1;
        if (sTypeEffectiveness[row][0] == TYPE_DRAGON && sTypeEffectiveness[row][1] == TYPE_FAIRY) assert(!seenForesight);
        for (size_t other = row + 1; other < NELEMS(sTypeEffectiveness); other++) {
            assert(sTypeEffectiveness[row][0] != sTypeEffectiveness[other][0] ||
                   sTypeEffectiveness[row][1] != sTypeEffectiveness[other][1]);
        }
    }
    for (int a = 0; a < 18; a++) for (int d = 0; d < 18; d++) {
        int found = CalculateTypeEffectiveness(types[a], types[d], types[d]);
        if (found != Expected(a,d)) fprintf(stderr,"attack=%d defender=%d got=%d expected=%d\n",types[a],types[d],found,Expected(a,d));
        assert(found == Expected(a,d));
        for (int second = 0; second < 18; second++) {
            int want = Expected(a,d);
            if (second != d) want = want * Expected(a,second) / 40;
            assert(CalculateTypeEffectiveness(types[a],types[d],types[second]) == want);
        }
    }
    return 0;
}
'''
        self.run_variants(COMMON + expected + types + actual + checks)

    def test_all_personal_loaders_override_only_twenty_species_types(self):
        header = (ROOT / "include/pokemon_types_def.h").read_text()
        stats = header[header.index("typedef struct BaseStats {"):header.index("} BASE_STATS;") + len("} BASE_STATS;")]
        fixture = "static const int changes[][5] = {\n" + ",\n".join(
            "{SPECIES_" + row[0] + "," + ",".join("TYPE_" + t for t in row[1:]) + "}"
            for row in map(str.split, SPECIES_TYPES.strip().splitlines())) + "\n};\n"
        declarations = r'''
enum HeapID { HEAP_ID_DEFAULT };
typedef int NARC;
enum { NARC_poketool_personal_personal };
static int lastRead;
static void Original(int species, BASE_STATS *data) {
    memset(data, 0x35, sizeof(*data));
    data->types[0] = TYPE_FIRE; data->types[1] = TYPE_DRAGON;
    for (size_t i = 0; i < NELEMS(changes); i++) if (species == changes[i][0]) {
        data->types[0] = changes[i][1]; data->types[1] = changes[i][2];
    }
}
static void ReadWholeNarcMemberByIdPair(void *dest, int narc, int member) {
    lastRead = member; Original(member, dest);
}
static void NARC_ReadWholeMember(NARC *narc, int member, void *dest) {
    lastRead = member; Original(member, dest);
}
static void *Heap_Alloc(enum HeapID heap, size_t size) { return malloc(size); }
static void Heap_Free(void *data) { free(data); }
'''
        names = ("ResolveMonForm", "LoadMonPersonal", "LoadMonBaseStats_HandleAlternateForm",
                 "AllocAndLoadMonPersonal", "AllocAndLoadMonPersonal_HandleAlternateForm",
                 "GetPersonalAttr", "FreeMonPersonal", "GetMonBaseStat",
                 "GetMonBaseStat_HandleAlternateForm", "GetMonBaseStatEx_HandleAlternateForm")
        actual = optional_helper("src/pokemon.c", "Qol_ApplyModernMonTypes") + "\n".join(
            game.function_source("src/pokemon.c", name) for name in names)
        checks = r'''
int main(void) {
    assert(NELEMS(changes) == 20);
    for (int species = 0; species <= SPECIES_ROTOM_MOW; species++) {
        for (int form = 0; form <= 5; form++) {
            int resolved = ResolveMonForm(species,form);
            BASE_STATS expected;
            Original(resolved,&expected);
#if QOL_MODERN_TYPES
            for (size_t i = 0; i < NELEMS(changes); i++) if (resolved == changes[i][0]) {
                expected.types[0] = changes[i][3]; expected.types[1] = changes[i][4];
            }
#endif
            BASE_STATS actual;
            LoadMonPersonal(resolved,&actual);
            assert(lastRead == resolved);
            if (memcmp(&actual,&expected,sizeof(actual))) fprintf(stderr,"personal species=%d form=%d\n",species,form);
            assert(!memcmp(&actual,&expected,sizeof(actual)));
            LoadMonBaseStats_HandleAlternateForm(species,form,&actual);
            assert(lastRead == resolved && !memcmp(&actual,&expected,sizeof(actual)));
            BASE_STATS *allocated = AllocAndLoadMonPersonal(resolved,HEAP_ID_DEFAULT);
            assert(!memcmp(allocated,&expected,sizeof(actual))); Heap_Free(allocated);
            allocated = AllocAndLoadMonPersonal_HandleAlternateForm(species,form,HEAP_ID_DEFAULT);
            assert(!memcmp(allocated,&expected,sizeof(actual))); Heap_Free(allocated);
            for (int attr = BASE_HP; attr <= BASE_TYPE2; attr++) {
                int wanted = GetPersonalAttr(&expected,attr);
                assert(GetMonBaseStat(resolved,attr) == wanted);
                assert(GetMonBaseStat_HandleAlternateForm(species,form,attr) == wanted);
                assert(GetMonBaseStatEx_HandleAlternateForm(NULL,species,form,attr) == wanted);
                assert(lastRead == resolved);
            }
        }
    }
    return 0;
}
'''
        self.run_variants(COMMON + stats + fixture + declarations + actual + checks)

    def test_damage_ai_flags_and_preview_share_modern_chart(self):
        source = (ROOT / "src/battle/battle_util.c").read_text()
        arrays = "\n".join(re.search(r"static (?:const )?u(?:8|16) " + name +
                                     r"\[.*?\n\};", source, re.S)[0]
                           for name in ("sTypeEffectiveness", "sSoundMoves", "sFixedDamageMoveEffects"))
        declarations = r'''
#include "constants/items.h"
#include "constants/abilities.h"
#include "constants/battle.h"
#include "constants/move_effects.h"
typedef int BattleSystem;
enum { TYPETABLE_ATTACKER, TYPETABLE_DEFENDER, TYPETABLE_EFFECT };
typedef struct { int category, power, type, effect; } Move;
typedef struct {
    int hp, type1, type2, ability, itemEffect;
    u32 status, status2, moveEffectFlags;
    struct { int magnetRiseTurns; } moveEffectData;
} Mon;
typedef struct {
    Mon battleMons[4];
    struct { Move moveData[NUM_MOVES+1]; } trainerAIData;
    u32 fieldCondition, battleStatus;
    struct { int roostFlag; } turnData[4];
    struct { int moldBreakerFlag; } selfTurnData[4];
} BattleContext;
static int GetBattlerHeldItemEffect(BattleContext *ctx, int battler) { return ctx->battleMons[battler].itemEffect; }
static int GetHeldItemModifier(BattleContext *ctx, int battler, int unused) { return 0; }
static int GetBattlerVar(BattleContext *ctx, int battler, int field, void *unused) {
    return field == BMON_DATA_TYPE_1 ? ctx->battleMons[battler].type1 : ctx->battleMons[battler].type2;
}
'''
        functions = ("GetBattlerAbility", "CheckBattlerAbilityIfNotIgnored", "DamageDivide",
                     "ApplyTypeMultiplier", "CheckChargeMoveHitTurn", "CheckFlyingImmunity",
                     "ApplyEffectivenessFlags", "BattleSystem_IsTypeMatchupActive",
                     "CalculateTypeEffectiveness", "BattleSystem_ApplyTypeEffectiveness",
                     "CalcTypeEffectivenessFlags", "IsFixedDamageMove", "Qol_PreviewTypeEffectiveness")
        actual = arrays + "\n" + "\n".join(game.function_source("src/battle/battle_util.c", name)
                                             for name in functions)
        checks = r'''
int main(void) {
    BattleContext ctx = {0};
    ctx.battleMons[0].hp = ctx.battleMons[1].hp = 100;
    // Avoid STAB while testing the type multiplier alone.
    ctx.battleMons[0].type1 = ctx.battleMons[0].type2 = TYPE_NONE;
    for (int attacker = 0; attacker < NUMBER_OF_MON_TYPES; attacker++) {
        ctx.trainerAIData.moveData[MOVE_TACKLE] = (Move){1,80,attacker,0};
        for (int first = 0; first < NUMBER_OF_MON_TYPES; first++) {
            for (int second = 0; second < NUMBER_OF_MON_TYPES; second++) {
                ctx.battleMons[1].type1 = first; ctx.battleMons[1].type2 = second;
                int wanted = CalculateTypeEffectiveness(attacker,first,second);
                BattleContext before = ctx;
                assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_TACKLE,0,1) == wanted);
                assert(!memcmp(&ctx,&before,sizeof(ctx)));
                u32 flags = 0, aiFlags = 0;
                assert(BattleSystem_ApplyTypeEffectiveness(NULL,&ctx,MOVE_TACKLE,0,0,1,40,&flags) == wanted);
                CalcTypeEffectivenessFlags(&ctx,MOVE_TACKLE,0,ABILITY_NONE,ABILITY_NONE,0,first,second,&aiFlags);
                assert(flags == aiFlags);
                assert(!!(flags & MOVE_STATUS_NO_EFFECT) == (wanted == 0));
                if (wanted) {
                    assert(!!(flags & MOVE_STATUS_SUPER_EFFECTIVE) == (wanted > 40));
                    assert(!!(flags & MOVE_STATUS_NOT_VERY_EFFECTIVE) == (wanted < 40));
                }
            }
        }
    }
    // Scrappy and Foresight bypass the two Ghost immunities, never Dragon/Fairy.
    ctx.trainerAIData.moveData[MOVE_TACKLE].type = TYPE_DRAGON;
    ctx.battleMons[1].type1 = ctx.battleMons[1].type2 = TYPE_FAIRY;
    for (int mode = 0; mode < 2; mode++) {
        ctx.battleMons[0].ability = mode ? ABILITY_SCRAPPY : ABILITY_NONE;
        ctx.battleMons[1].status2 = mode ? 0 : STATUS2_FORESIGHT;
        u32 flags = 0, aiFlags = 0;
        int wanted = QOL_MODERN_TYPES ? 0 : 40;
        assert(BattleSystem_ApplyTypeEffectiveness(NULL,&ctx,MOVE_TACKLE,0,0,1,40,&flags) == wanted);
        assert(Qol_PreviewTypeEffectiveness(&ctx,MOVE_TACKLE,0,1) == wanted);
        CalcTypeEffectivenessFlags(&ctx,MOVE_TACKLE,0,ctx.battleMons[0].ability,ABILITY_NONE,0,TYPE_FAIRY,TYPE_FAIRY,&aiFlags);
        assert(flags == aiFlags);
    }
    return 0;
}
'''
        # Source damage functions contain original matching-only unused locals.
        self.run_variants(COMMON + declarations + actual + checks,
                          "-Wno-sign-compare", "-Wno-unused-but-set-variable")

    def test_bulk_and_single_move_loaders_preserve_all_other_bytes(self):
        header = (ROOT / "include/move.h").read_text()
        move = header[header.index("typedef struct MoveTbl {"):header.index("} MoveTbl;") + len("} MoveTbl;")]
        declarations = r'''
enum { NARC_poketool_waza_waza_tbl };
static void Original(u16 move, MoveTbl *data) {
    memset(data, 0x27, sizeof(*data));
    data->type = move == MOVE_CURSE ? TYPE_MYSTERY : TYPE_NORMAL;
}
static void ReadWholeNarcMemberByIdPair(void *dest, int narc, int member) { Original(member,dest); }
static void ReadFromNarcMemberByIdPair(void *dest, int narc, int member, int offset, size_t size) {
    assert(offset == 0 && size == (NUM_MOVES+1)*sizeof(MoveTbl));
    for (int move = 0; move <= NUM_MOVES; move++) Original(move,&((MoveTbl *)dest)[move]);
}
'''
        actual = optional_helper("src/move.c", "Qol_ApplyModernMoveType") + "\n".join(
            game.function_source("src/move.c", name) for name in ("LoadMoveTbl", "LoadMoveEntry"))
        checks = r'''
int main(void) {
    MoveTbl moves[NUM_MOVES + 1];
    LoadMoveTbl(moves);
    for (int move = 0; move <= NUM_MOVES; move++) {
        MoveTbl original, single;
        Original(move,&original);
#if QOL_MODERN_TYPES
        if (move == MOVE_CHARM || move == MOVE_SWEET_KISS || move == MOVE_MOONLIGHT) original.type = TYPE_FAIRY;
        if (move == MOVE_CURSE) original.type = TYPE_GHOST;
#endif
        LoadMoveEntry(move,&single);
        if (memcmp(&single,&original,sizeof(single))) fprintf(stderr,"move=%d\n",move);
        assert(!memcmp(&single,&original,sizeof(single)));
        assert(!memcmp(&moves[move],&original,sizeof(original)));
    }
    return 0;
}
'''
        self.run_variants(COMMON + move + declarations + actual + checks)

    def test_hidden_power_still_excludes_slot_nine_for_all_iv_parities(self):
        declarations = r'''
#include "constants/items.h"
#include "constants/abilities.h"
#include "constants/battle.h"
typedef int BattleSystem;
typedef struct { int hpIV, atkIV, defIV, speedIV, spAtkIV, spDefIV; } Mon;
typedef struct { Mon battleMons[4]; u32 fieldCondition; } BattleContext;
static int GetNaturalGiftType(BattleContext *ctx, int battler) { return TYPE_NORMAL; }
static int GetBattlerHeldItemEffect(BattleContext *ctx, int battler) { return 0; }
static int CheckAbilityActive(BattleSystem *bs, BattleContext *ctx, int scope, int battler, int ability) { return 0; }
'''
        actual = game.function_source("src/battle/battle_util.c", "GetDynamicMoveType")
        checks = r'''
int main(void) {
    BattleContext ctx = {0};
    int seen[18] = {0};
    for (int iv = 0; iv < 64; iv++) {
        ctx.battleMons[0] = (Mon){iv&1,(iv>>1)&1,(iv>>2)&1,(iv>>3)&1,(iv>>4)&1,(iv>>5)&1};
        int expected = (iv * 15 / 63) + 1;
        if (expected >= 9) expected++;
        int type = GetDynamicMoveType(NULL,&ctx,0,MOVE_HIDDEN_POWER);
        assert(type == expected && type != TYPE_FAIRY && type != TYPE_NORMAL);
        seen[type] = 1;
    }
    for (int type = 1; type < 18; type++) assert(seen[type] == (type != TYPE_FAIRY));
    return 0;
}
'''
        # The untouched Weather Ball branch documents a preexisting uninitialized
        # return in fog. This test executes only Hidden Power's initialized path.
        self.run_variants(COMMON + declarations + actual + checks, "-Wno-uninitialized")


if __name__ == "__main__":
    unittest.main()
