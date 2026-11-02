"""Host C checks for the pure cap core; no SDK, saves or native builds are used."""
from pathlib import Path
import csv
import json
import os
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / 'include/qol_level_caps.h'
SOURCE = ROOT / 'src/qol_level_caps.c'

# These identify original story teams and their badge/League roles. Ace levels
# come independently from the checked-in trainer data rather than this fixture.
JOHTO = (
    ('BADGE_ZEPHYR', 'TRAINER_LEADER_FALKNER_FALKNER'),
    ('BADGE_HIVE', 'TRAINER_LEADER_BUGSY_BUGSY'),
    ('BADGE_PLAIN', 'TRAINER_LEADER_WHITNEY'),
    ('BADGE_FOG', 'TRAINER_LEADER_MORTY_MORTY'),
    ('BADGE_STORM', 'TRAINER_LEADER_CHUCK_CHUCK'),
    ('BADGE_MINERAL', 'TRAINER_LEADER_JASMINE_JASMINE'),
    ('BADGE_GLACIER', 'TRAINER_LEADER_PRYCE_PRYCE'),
    ('BADGE_RISING', 'TRAINER_LEADER_CLAIR_CLAIR'),
)
KANTO = (
    ('BADGE_BOULDER', 'TRAINER_LEADER_BROCK_BROCK'),
    ('BADGE_CASCADE', 'TRAINER_LEADER_MISTY_MISTY'),
    ('BADGE_THUNDER', 'TRAINER_LEADER_LT_SURGE_LT__SURGE'),
    ('BADGE_RAINBOW', 'TRAINER_LEADER_ERIKA_ERIKA'),
    ('BADGE_SOUL', 'TRAINER_LEADER_JANINE_JANINE'),
    ('BADGE_MARSH', 'TRAINER_LEADER_SABRINA_SABRINA'),
    ('BADGE_VOLCANO', 'TRAINER_LEADER_BLAINE_BLAINE'),
    ('BADGE_EARTH', 'TRAINER_LEADER_BLUE_BLUE'),
)
LEAGUE = (
    'TRAINER_ELITE_FOUR_WILL_WILL', 'TRAINER_ELITE_FOUR_KOGA_KOGA',
    'TRAINER_ELITE_FOUR_BRUNO_BRUNO', 'TRAINER_ELITE_FOUR_KAREN_KAREN',
    'TRAINER_CHAMPION_LANCE',
)


def constants(relative_path):
    return {name: int(value, 0) for name, value in re.findall(
        r'^#define\s+(\w+)\s+(0x[0-9a-fA-F]+|\d+)\s*$',
        (ROOT / relative_path).read_text(), re.MULTILINE)}


class LevelCapCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.badges = constants('include/constants/badge.h')
        cls.trainer_ids = constants('include/constants/trainers.h')
        cls.trainers = json.loads(
            (ROOT / 'files/poketool/trainer/trainers.json').read_text())['trainers']
        with (ROOT / 'files/poketool/personal/growtbl.csv').open(newline='') as stream:
            cls.growth = list(csv.DictReader(stream))
        cls.sanitize = os.environ.get('LEVEL_CAP_SANITIZE') == '1'

    def boss(self, name):
        trainer = self.trainer_ids[name]
        return trainer, max(mon['level'] for mon in self.trainers[trainer]['party'])

    def minimum(self, roles, badges):
        candidates = [(self.boss(name)[1], self.badges[badge], self.boss(name)[0])
                      for badge, name in roles if not badges & (1 << self.badges[badge])]
        level, _, trainer = min(candidates)
        return trainer, level

    def compile_run(self, checks):
        prelude = '''
#ifndef POKEHEARTGOLD_GLOBAL_H
#define POKEHEARTGOLD_GLOBAL_H
#include <stdint.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#endif
'''
        # Before implementation, ordinary uncapped behavior gives semantic RED
        # assertions. GREEN always compiles the complete actual production TU.
        absent_api = '''
typedef struct QolLevelCap { u16 trainerId; u8 level; } QolLevelCap;
QolLevelCap Qol_GetLevelCap(u16 badges, BOOL gameClear, u8 defeatedEliteFour);
BOOL Qol_LevelCapConfigEnabled(u16 value);
u16 Qol_LevelCapConfigValue(BOOL enabled);
u32 Qol_LevelCapAllowedExp(BOOL enabled, u32 oldExp, u32 requestedExp, u32 capExp);
'''
        absent_source = '''
QolLevelCap Qol_GetLevelCap(u16 b, BOOL c, u8 e) {
    QolLevelCap result = {0, 100}; return result;
}
BOOL Qol_LevelCapConfigEnabled(u16 v) { return FALSE; }
u16 Qol_LevelCapConfigValue(BOOL enabled) { return 0; }
u32 Qol_LevelCapAllowedExp(BOOL e, u32 old, u32 request, u32 cap) { return request; }
'''
        self.assertEqual(HEADER.exists(), SOURCE.exists(), 'Core header/source must appear together')
        with tempfile.TemporaryDirectory(prefix='qol-cap-') as folder:
            temp = Path(folder)
            (temp / 'host.h').write_text(prelude)
            api = '#include "qol_level_caps.h"\n' if HEADER.exists() else absent_api
            program = ('#include <assert.h>\n#include <limits.h>\n' + api
                       + ('' if SOURCE.exists() else absent_source) + '\n'
                       + 'int main(void) {\n' + checks + '\nreturn 0;\n}\n')
            (temp / 'check.c').write_text(program)
            command = [os.environ.get('CC', 'cc'), '-std=c99', '-Wall', '-Wextra',
                       '-Werror', '-Wno-unused-parameter', '-include', str(temp / 'host.h'),
                       '-iquote', str(ROOT / 'include')]
            if self.sanitize:
                command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
            if SOURCE.exists():
                command.append(str(SOURCE))
            command += [str(temp / 'check.c'), '-o', str(temp / 'check')]
            compiled = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            env = dict(os.environ)
            if self.sanitize:
                env['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
                env['UBSAN_OPTIONS'] = 'halt_on_error=1'
            result = subprocess.run([str(temp / 'check')], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @staticmethod
    def assertion(badges, game_clear, defeated, boss):
        trainer, level = boss
        return (f'{{ QolLevelCap cap = Qol_GetLevelCap({badges}, {int(game_clear)}, {defeated}); '
                f'assert(cap.trainerId == {trainer} && cap.level == {level}); }}\n')

    def test_only_exact_schema_one_tag_enables_the_option(self):
        self.compile_run('''
for (unsigned value = 0; value <= 65535; value++) {
    assert(!!Qol_LevelCapConfigEnabled((u16)value) == (value == 0xc701));
}
''')

    def test_option_confirmation_encodes_only_off_or_schema_one(self):
        self.compile_run('''
assert(Qol_LevelCapConfigValue(FALSE) == 0);
assert(Qol_LevelCapConfigValue(TRUE) == 0xc701);
assert(Qol_LevelCapConfigValue(-3) == 0xc701);
assert(Qol_LevelCapConfigEnabled(Qol_LevelCapConfigValue(TRUE)));
assert(!Qol_LevelCapConfigEnabled(Qol_LevelCapConfigValue(FALSE)));
''')

    def test_every_original_story_boss_matches_its_trainer_party_ace(self):
        checks = []
        for badge, name in JOHTO:
            checks.append(self.assertion(0xffff ^ (1 << self.badges[badge]), False, 15, self.boss(name)))
        for badge, name in KANTO:
            checks.append(self.assertion(0xffff ^ (1 << self.badges[badge]), True, 0, self.boss(name)))
        for index, name in enumerate(LEAGUE):
            checks.append(self.assertion(0xff, False, (1 << index) - 1, self.boss(name)))
        self.compile_run(''.join(checks))

    def test_every_johto_badge_mask_uses_identity_and_lowest_original_ace(self):
        checks = []
        for mask in range(255):
            expected = self.minimum(JOHTO, mask)
            for stale_elite_flags in (0, 15, 255):
                checks.append(self.assertion(mask | 0xff00, False, stale_elite_flags, expected))
        # Same badge count, different boss; Jasmine/Pryce's badge order differs
        # from their ace order. Badge awards also remain separate from wins.
        checks += [self.assertion(0x7f, False, 0, self.boss('TRAINER_LEADER_CLAIR_CLAIR')),
                   self.assertion(0xbf, False, 0, self.boss('TRAINER_LEADER_PRYCE_PRYCE')),
                   self.assertion(0x9f, False, 0, self.boss('TRAINER_LEADER_PRYCE_PRYCE')),
                   self.assertion(0xdf, False, 0, self.boss('TRAINER_LEADER_JASMINE_JASMINE'))]
        self.compile_run(''.join(checks))

    def test_game_clear_precedes_johto_and_resettable_league_flags_for_every_kanto_mask(self):
        checks = []
        for mask in range(256):
            badges = mask << 8
            expected = self.minimum(KANTO, badges) if mask != 255 else (0, 100)
            for stale_elite_flags in range(16):
                checks.append(self.assertion(badges, True, stale_elite_flags, expected))
        self.compile_run(''.join(checks))

    def test_every_league_flag_combination_follows_first_unbeaten_member(self):
        checks = []
        for flags in range(16):
            next_member = next((i for i in range(4) if not flags & (1 << i)), 4)
            for unrelated_high_bits in (0, 0xf0):
                checks.append(self.assertion(0xffff, False, flags | unrelated_high_bits,
                                             self.boss(LEAGUE[next_member])))
        # New pre-clear attempts reset to Will. Post-clear the same reset enters
        # Kanto instead; above-cap EXP preservation belongs to the award helper.
        checks.append(self.assertion(0xff, False, 0, self.boss(LEAGUE[0])))
        checks.append(self.assertion(0xff, True, 0, self.boss('TRAINER_LEADER_JANINE_JANINE')))
        self.compile_run(''.join(checks))

    def test_kanto_equal_aces_have_stable_badge_ties_and_finished_scope_is_uncapped(self):
        checks = [self.assertion(0xfcff, True, 15, self.boss('TRAINER_LEADER_BROCK_BROCK')),
                  self.assertion(0xfdff, True, 0, self.boss('TRAINER_LEADER_MISTY_MISTY')),
                  self.assertion(0xffff, True, 0, (0, 100)),
                  self.assertion(0xffff, True, 255, (0, 100))]
        self.compile_run(''.join(checks))

    def test_awards_stop_at_existing_growth_thresholds_without_banking_or_rewriting(self):
        levels = sorted({self.boss(name)[1] for _, name in JOHTO + KANTO}
                        | {self.boss(name)[1] for name in LEAGUE})
        checks = []
        for curve in self.growth:
            for level in levels:
                threshold = int(curve[f'lv{level:03}'])
                after = int(curve[f'lv{level + 1:03}'])
                previous = int(curve[f'lv{level - 1:03}'])
                checks += [
                    f'assert(Qol_LevelCapAllowedExp(TRUE, {threshold-1}, 2, {threshold}) == 1);',
                    f'assert(Qol_LevelCapAllowedExp(TRUE, {previous}, UINT_MAX, {threshold}) == {threshold-previous});',
                    f'assert(Qol_LevelCapAllowedExp(TRUE, {threshold}, UINT_MAX, {threshold}) == 0);',
                    f'assert(Qol_LevelCapAllowedExp(TRUE, {threshold+1}, 200, {threshold}) == 0);',
                    f'assert(Qol_LevelCapAllowedExp(TRUE, {after}, 200, {threshold}) == 0);',
                    f'assert(Qol_LevelCapAllowedExp(FALSE, {after}, 200, {threshold}) == 200);',
                    f'assert(Qol_LevelCapAllowedExp(TRUE, {previous}, 0, {threshold}) == 0);',
                ]
        self.compile_run('\n'.join(checks))

    def test_award_overflow_disabled_mode_and_resume_use_only_current_inputs(self):
        self.compile_run('''
assert(Qol_LevelCapAllowedExp(TRUE, UINT_MAX, UINT_MAX, 100) == 0);
assert(Qol_LevelCapAllowedExp(TRUE, UINT_MAX - 1, UINT_MAX, UINT_MAX) == 1);
assert(Qol_LevelCapAllowedExp(TRUE, 0, UINT_MAX, UINT_MAX) == UINT_MAX);
assert(Qol_LevelCapAllowedExp(TRUE, 20, 50, 100) == 50);
assert(Qol_LevelCapAllowedExp(TRUE, 0, 2, 0) == 0);
assert(Qol_LevelCapAllowedExp(FALSE, UINT_MAX, UINT_MAX, 0) == UINT_MAX);
u32 oldExp = 200;
assert(Qol_LevelCapAllowedExp(TRUE, oldExp, 500, 100) == 0);
assert(oldExp == 200);
assert(Qol_LevelCapAllowedExp(TRUE, oldExp, 10, 210) == 10);
assert(Qol_LevelCapAllowedExp(TRUE, oldExp, 10, 300) == 10);
assert(Qol_LevelCapAllowedExp(FALSE, oldExp, 10, 100) == 10);
''')


if __name__ == '__main__':
    unittest.main()
