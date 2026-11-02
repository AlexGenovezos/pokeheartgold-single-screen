"""Host-only checks for the real save adapter, with synthetic SDK edges.

The absent-adapter fallback deliberately retains today's uncapped behavior. It
allows a semantic RED before the new production API exists; no SDK entrypoint
or existing test module is imported. GREEN compiles the complete adapter body.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "src/qol_level_cap_save.c"
HEADER = ROOT / "include/qol_level_cap_save.h"


def without_includes(source):
    """Replace SDK includes only; keep all production declarations and logic."""
    return re.sub(r'^\s*#include[^\n]*', '', source, flags=re.MULTILINE)


def function_source(path, name):
    source = (ROOT / path).read_text()
    match = re.search(r'^[\w *]+\b' + re.escape(name) + r'\([^;{}]*\)\s*\{',
                      source, re.MULTILINE)
    if match is None:
        raise AssertionError(f"function definition not found: {path}:{name}")
    cursor, depth = match.end(), 1
    while depth:
        depth += (source[cursor] == '{') - (source[cursor] == '}')
        cursor += 1
    return source[match.start():cursor]


def host_run(test, program, enabled=1, extra_flags=()):
    # Pin a host compiler. In particular, do not inherit an SDK CC/Wine wrapper.
    compiler = shutil.which('clang')
    test.assertIsNotNone(compiler, 'host clang is required')
    with tempfile.TemporaryDirectory(prefix='qol-cap-host-') as folder:
        temp = Path(folder)
        (temp / 'check.c').write_text(program)
        command = [compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                   '-Wno-unused-parameter', '-Wno-unused-function',
                   '-Wno-unused-variable', '-Wno-sign-compare',
                   '-iquote', str(ROOT / 'include'), f'-DQOL_LEVEL_CAPS={enabled}']
        sanitize = os.environ.get('LEVEL_CAP_SANITIZE') == '1'
        if sanitize:
            command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        command += [*extra_flags, str(temp / 'check.c'), '-o', str(temp / 'check')]
        result = subprocess.run(command, capture_output=True, text=True)
        test.assertEqual(result.returncode, 0, 'host compile failed:\n' + result.stderr)
        env = dict(os.environ)
        if sanitize:
            env['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
            env['UBSAN_OPTIONS'] = 'halt_on_error=1'
        result = subprocess.run([str(temp / 'check')], capture_output=True, text=True, env=env)
        test.assertEqual(result.returncode, 0, 'semantic C assertion failed:\n' + result.stderr)


HOST_TYPES = r'''
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t s32;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define NELEMS(a) (sizeof(a) / sizeof((a)[0]))
#include "constants/badge.h"
#include "constants/pokemon.h"
#include "constants/trainers.h"
#include "constants/vars.h"
#include "constants/flags.h"
'''

SAVE_EDGES = r'''
/* Only fallback names for pre-integration RED. Production allocation is checked
 * separately, and these definitions disappear after the actual rename. */
#ifndef VAR_QOL_DAYCARE_BREEDING_PHASE
#define VAR_QOL_DAYCARE_BREEDING_PHASE 0x416e
#endif
#ifndef VAR_QOL_LEVEL_CAP_CONFIG
#define VAR_QOL_LEVEL_CAP_CONFIG 0x416f
#endif
typedef struct PlayerProfile { u16 badges; } PlayerProfile;
typedef struct Pokemon { u16 species; u32 exp; u32 level; } Pokemon;
typedef Pokemon BoxPokemon;
typedef struct DaycareMon { BoxPokemon mon; u32 steps; } DaycareMon;
typedef struct SaveData {
    SaveVarsFlags varsFlags;
    PlayerProfile profile;
    BOOL clear;
    u8 defeated;
} SaveData;
static SaveData saved;
static unsigned slotReads, progressionReads, growthReads, monWrites;
static unsigned badgeReads[16];
static u16 lastSpecies;
static u32 lastLevel;
SaveVarsFlags *Save_VarsFlags_Get(SaveData *save) { return &save->varsFlags; }
u16 *Save_VarsFlags_GetVarAddr(SaveVarsFlags *vars, u16 id) {
    assert(id == VAR_QOL_DAYCARE_BREEDING_PHASE || id == VAR_QOL_LEVEL_CAP_CONFIG);
    slotReads++; return &vars->vars[id - VAR_BASE];
}
PlayerProfile *Save_PlayerData_GetProfile(SaveData *save) { progressionReads++; return &save->profile; }
BOOL PlayerProfile_TestBadgeFlag(PlayerProfile *profile, s32 index) {
    assert(index >= 0 && index < 16); badgeReads[index]++;
    progressionReads++; return !!(profile->badges & (1u << index));
}
BOOL CheckGameClearFlag(SaveVarsFlags *vars) {
    progressionReads++; return ((SaveData *)vars)->clear;
}
BOOL Save_VarsFlags_CheckFlagInArray(SaveVarsFlags *vars, u16 id) {
    assert(id >= FLAG_DEFEATED_WILL && id <= FLAG_DEFEATED_KAREN);
    progressionReads++; return !!(((SaveData *)vars)->defeated & (1u << (id - FLAG_DEFEATED_WILL)));
}
u32 GetMonExpBySpeciesAndLevel(u16 species, u32 level) {
    growthReads++; lastSpecies = species; lastLevel = level;
    /* Deliberately species-sensitive test growth edge. Native curves are
     * independently checked by the frozen core fixture. */
    return level * 100 + species;
}
u32 GetMonData(Pokemon *mon, int field, void *out) {
    switch (field) {
    case MON_DATA_SPECIES: return mon->species;
    case MON_DATA_EXPERIENCE: return mon->exp;
    case MON_DATA_LEVEL: return mon->level;
    case MON_DATA_SPECIES_EXISTS: return mon->species != 0;
    case MON_DATA_HP: case MON_DATA_MAX_HP: case MON_DATA_ATK:
    case MON_DATA_DEF: case MON_DATA_SP_ATK: case MON_DATA_SP_DEF: case MON_DATA_SPEED: return 100;
    default: assert(0); return 0;
    }
}
u32 GetBoxMonData(BoxPokemon *mon, int field, void *out) { return GetMonData(mon, field, out); }
u32 CalcMonExpToNextLevel(Pokemon *mon) { return (mon->level + 1) * 100 + mon->species - mon->exp; }
BoxPokemon *DaycareMon_GetBoxMon(DaycareMon *mon) { return &mon->mon; }
u32 DaycareMon_GetSteps(DaycareMon *mon) { return mon->steps; }
SaveData *SaveData_Get(void) { return &saved; }
static void reset_spies(void) {
    slotReads = progressionReads = growthReads = monWrites = 0;
    memset(badgeReads, 0, sizeof(badgeReads));
}
static void set_raw(u16 config, u16 phase) {
    saved.varsFlags.vars[VAR_QOL_LEVEL_CAP_CONFIG - VAR_BASE] = config;
    saved.varsFlags.vars[VAR_QOL_DAYCARE_BREEDING_PHASE - VAR_BASE] = phase;
    reset_spies();
}
static u16 raw_phase(void) { return saved.varsFlags.vars[VAR_QOL_DAYCARE_BREEDING_PHASE - VAR_BASE]; }
'''

ABSENT_API = r'''
QolLevelCap Qol_LevelCapForSave(SaveData *save);
BOOL Qol_LevelCapEnabledForSave(SaveData *save);
void Qol_LevelCapSetEnabledForSave(SaveData *save, BOOL enabled);
u32 Qol_LevelCapLimitPlayerExp(SaveData *save, u16 species, u32 oldExp, u32 requestedExp);
BOOL Qol_LevelCapCanUseRareCandy(SaveData *save, Pokemon *mon);
u8 Qol_LevelCapAdvanceDaycarePhase(SaveData *save, DaycareMon *second);
void Qol_LevelCapResetDaycarePhase(SaveData *save);
'''
ABSENT_ADAPTER = r'''
/* Explicit representation of the current uncapped game, not a cap model. */
QolLevelCap Qol_LevelCapForSave(SaveData *save) { QolLevelCap cap = {TRAINER_NONE, MAX_LEVEL}; return cap; }
BOOL Qol_LevelCapEnabledForSave(SaveData *save) { return FALSE; }
void Qol_LevelCapSetEnabledForSave(SaveData *save, BOOL enabled) {}
u32 Qol_LevelCapLimitPlayerExp(SaveData *save, u16 species, u32 oldExp, u32 request) { return request; }
BOOL Qol_LevelCapCanUseRareCandy(SaveData *save, Pokemon *mon) { return TRUE; }
u8 Qol_LevelCapAdvanceDaycarePhase(SaveData *save, DaycareMon *second) {
    return second->mon.species ? (u8)(second->steps + 1) : 0;
}
void Qol_LevelCapResetDaycarePhase(SaveData *save) {}
'''


def adapter_program():
    layout = (ROOT / 'include/save_vars_flags.h').read_text()
    layout = re.search(r'typedef struct SaveVarsFlags \{.*?\} SaveVarsFlags;', layout, re.S)[0]
    core_header = without_includes((ROOT / 'include/qol_level_caps.h').read_text())
    core = without_includes((ROOT / 'src/qol_level_caps.c').read_text())
    if ADAPTER.exists() != HEADER.exists():
        raise AssertionError('save adapter header/source must appear together')
    api = without_includes(HEADER.read_text()) if HEADER.exists() else ABSENT_API
    body = without_includes(ADAPTER.read_text()) if ADAPTER.exists() else ABSENT_ADAPTER
    return HOST_TYPES + layout + SAVE_EDGES + core_header + api + core + body


class LevelCapSaveTests(unittest.TestCase):
    def run_checks(self, checks, enabled=1):
        host_run(self, adapter_program() + '\nint main(void) {\n' + checks + '\nreturn 0;\n}', enabled)

    def test_disabled_support_touches_no_reserved_or_progression_state(self):
        self.run_checks(r'''
set_raw(0xc701, 0xd1fe); saved.profile.badges = 0xffff; saved.clear = TRUE;
DaycareMon second = {{25, 1300, 13}, 254};
Pokemon mon = {25, 1325, 13};
QolLevelCap cap = Qol_LevelCapForSave(&saved);
assert(cap.trainerId == TRAINER_NONE && cap.level == MAX_LEVEL);
assert(!Qol_LevelCapEnabledForSave(&saved));
Qol_LevelCapSetEnabledForSave(&saved, FALSE);
assert(Qol_LevelCapLimitPlayerExp(&saved, 25, UINT_MAX, 900) == 900);
assert(Qol_LevelCapCanUseRareCandy(&saved, &mon));
assert(Qol_LevelCapAdvanceDaycarePhase(&saved, &second) == 255);
Qol_LevelCapResetDaycarePhase(&saved);
assert(slotReads == 0 && progressionReads == 0 && growthReads == 0);
assert(raw_phase() == 0xd1fe);
assert(saved.varsFlags.vars[0x16f] == 0xc701);
''', enabled=0)

    def test_exact_config_roundtrip_and_unknown_values_preserve_off(self):
        self.run_checks(r'''
const u16 invalid[] = {0, 1, 0xc700, 0xc702, 0xffff, 0xd100};
for (unsigned i = 0; i < NELEMS(invalid); i++) {
    set_raw(invalid[i], 0x1234);
    assert(!Qol_LevelCapEnabledForSave(&saved));
    assert(saved.varsFlags.vars[0x16f] == invalid[i]);
    assert(Qol_LevelCapLimitPlayerExp(&saved, 7, 2000, 150) == 150);
    assert(progressionReads == 0 && growthReads == 0);
}
set_raw(0xc701, 0x1234);
assert(Qol_LevelCapEnabledForSave(&saved));
Qol_LevelCapSetEnabledForSave(&saved, FALSE);
assert(saved.varsFlags.vars[0x16f] == 0);
Qol_LevelCapSetEnabledForSave(&saved, TRUE);
assert(saved.varsFlags.vars[0x16f] == 0xc701 && raw_phase() == 0x1234);
''')

    def test_resolver_reads_each_badge_and_first_league_flags_with_clear_precedence(self):
        self.run_checks(r'''
set_raw(0, 0); /* Prospective display must work even while Off. */
saved.profile.badges = 0xbf; saved.defeated = 15;
QolLevelCap cap = Qol_LevelCapForSave(&saved);
assert(cap.trainerId == TRAINER_LEADER_PRYCE_PRYCE && cap.level == 34);
for (unsigned i = 0; i < 16; i++) assert(badgeReads[i] == 1);
saved.profile.badges = 0xdf;
cap = Qol_LevelCapForSave(&saved);
assert(cap.trainerId == TRAINER_LEADER_JASMINE_JASMINE && cap.level == 35);
saved.profile.badges = 0xff;
for (unsigned flags = 0; flags < 16; flags++) {
    saved.defeated = flags;
    QolLevelCap expected = Qol_GetLevelCap(0xff, FALSE, flags);
    cap = Qol_LevelCapForSave(&saved);
    assert(cap.trainerId == expected.trainerId && cap.level == expected.level);
}
saved.clear = TRUE; saved.defeated = 0;
cap = Qol_LevelCapForSave(&saved);
assert(cap.trainerId == TRAINER_LEADER_JANINE_JANINE && cap.level == 50);
''')

    def test_limiter_forwards_species_threshold_and_preserves_existing_exp(self):
        self.run_checks(r'''
set_raw(0xc701, 0); saved.profile.badges = 0;
u32 oldExp = 1324;
assert(Qol_LevelCapLimitPlayerExp(&saved, 25, oldExp, UINT_MAX) == 1);
assert(oldExp == 1324 && lastSpecies == 25 && lastLevel == 13 && growthReads == 1);
assert(Qol_LevelCapLimitPlayerExp(&saved, 25, 1325, 100) == 0);
assert(Qol_LevelCapLimitPlayerExp(&saved, 25, 9999, 100) == 0);
saved.profile.badges = 0xffff; saved.clear = TRUE; reset_spies();
assert(Qol_LevelCapLimitPlayerExp(&saved, 25, UINT_MAX, 100) == 100);
assert(growthReads == 0);
''')

    def test_candy_requires_the_complete_positive_next_level_award(self):
        self.run_checks(r'''
set_raw(0xc701, 0);
Pokemon mon = {25, 1225, 12};
assert(Qol_LevelCapCanUseRareCandy(&saved, &mon));
mon.exp = 1325; mon.level = 13;
assert(!Qol_LevelCapCanUseRareCandy(&saved, &mon));
mon.exp = 1400; mon.level = 12; /* Cached-level inconsistency cannot bypass cap. */
assert(!Qol_LevelCapCanUseRareCandy(&saved, &mon));
mon.exp = 10025; mon.level = 100;
assert(!Qol_LevelCapCanUseRareCandy(&saved, &mon));
mon.exp = 1425; mon.level = 14; set_raw(0, 0);
assert(Qol_LevelCapCanUseRareCandy(&saved, &mon));
assert(monWrites == 0);
''')

    def test_phase_migrates_before_growth_and_continues_after_disable_and_reload(self):
        self.run_checks(r'''
DaycareMon second = {{25, 1325, 13}, 254};
set_raw(0, 0x1234);
assert(Qol_LevelCapAdvanceDaycarePhase(&saved, &second) == 255);
assert(raw_phase() == 0x1234); /* Untouched Off saves are not migrated. */
set_raw(0xc701, 0x1234);
assert(Qol_LevelCapAdvanceDaycarePhase(&saved, &second) == 255);
assert(raw_phase() == 0xd1ff && second.steps == 254);
assert(Qol_LevelCapAdvanceDaycarePhase(&saved, &second) == 0);
assert(raw_phase() == 0xd100 && second.steps == 254);
Qol_LevelCapSetEnabledForSave(&saved, FALSE);
SaveData snapshot = saved; memset(&saved, 0, sizeof(saved)); saved = snapshot;
assert(Qol_LevelCapAdvanceDaycarePhase(&saved, &second) == 1);
assert(raw_phase() == 0xd101);
Qol_LevelCapResetDaycarePhase(&saved); assert(raw_phase() == 0xd100);
second.mon.species = 0;
assert(Qol_LevelCapAdvanceDaycarePhase(&saved, &second) == 0);
assert(raw_phase() == 0xd100);
set_raw(0, 0x5678); Qol_LevelCapResetDaycarePhase(&saved);
assert(raw_phase() == 0x5678);
''')

    def test_reserved_slots_have_no_shipped_script_or_frontier_claim(self):
        declarations = (ROOT / 'include/constants/vars.h').read_text()
        for name, value in (('DAYCARE_BREEDING_PHASE', '416E'), ('LEVEL_CAP_CONFIG', '416F')):
            self.assertRegex(declarations, rf'#define\s+VAR_QOL_{name}\s+0x{value}\b')
            self.assertNotIn(f'VAR_UNK_{value}', declarations)
        claims = []
        for folder, pattern in (('files/fielddata/script/scr_seq', '*.s'),
                                ('files/fielddata/eventdata/zone_event', '*.json')):
            for path in (ROOT / folder).glob(pattern):
                if re.search(r'VAR_QOL_(?:DAYCARE_BREEDING_PHASE|LEVEL_CAP_CONFIG)|\b0x416[ef]\b|\b1675[01]\b',
                             path.read_text(), re.I):
                    claims.append(str(path.relative_to(ROOT)))
        self.assertEqual(claims, [])
        frontier = (ROOT / 'files/a/1/8/2').read_bytes()
        self.assertNotIn(b'\x6e\x41', frontier)
        self.assertNotIn(b'\x6f\x41', frontier)

    def test_feature_default_is_independent_of_all_modern_flags(self):
        for qol in (0, 1):
            for modern in (0, 1):
                with self.subTest(qol=qol, modern=modern):
                    host_run(self, '#include <assert.h>\n#include "qol_config.h"\n'
                             f'int main(void) {{ assert(QOL_LEVEL_CAPS == {qol}); return 0; }}',
                             extra_flags=('-UQOL_LEVEL_CAPS', f'-DQOL_MODS={qol}',
                                          f'-DQOL_MODERN_TYPES={modern}',
                                          f'-DQOL_MODERN_BATTLE={modern}',
                                          f'-DQOL_MODERN_MOVES={modern}'))


if __name__ == '__main__':
    unittest.main()
