# Modern core-rule foundation

**Approved scope:** Generation IX ordinary battle rules, modern moves/abilities,
existing roster/story; see the Gen IX battle spec. This checkpoint is a tested
subset behind `QOL_MODERN_BATTLE=0` by default. It is not a complete ruleset and
is not installed in the player's current app.

- [x] Red/green actual-source C regressions for critical odds and armor/Lucky
  Chant/Sniper; damage commands/controller routes; both paralysis speed paths;
  confusion, Magic Guard, Facade, Protect state and Conversion Fairy handling.
- [x] Change critical chances to 1/24, 1/8, 1/2, guaranteed from +3.
- [x] Apply 1.5 critical damage before the random roll in default and Beat Up
  paths, preserving the original critical marker for stat/screen bypass.
- [x] Apply Sniper as a separate final 1.5 modifier in normal, Pursuit and
  Beat Up paths, including integer/negative-damage half ties.
- [x] Halve paralysis speed; use one-in-three confusion self-hit; remove the
  old Magic Guard full-paralysis exemption; exempt Facade from burn's attack penalty.
- [x] Implement 1/3 consecutive Protect/Detect/Endure odds through six repeats.
  Preserve `MoveEffectData` layout by using its proven-unused high bit along
  with the existing two-bit count. Update get/set/add/reset and AI consumers.
- [x] Preserve the legacy behavior with the flag off, and keep the type flag
  independent. Conversion's old Curse/slot-9 rewrite cannot affect Fairy.
- [x] Independent spec and code-quality review approved this scoped foundation.
- [ ] Complete full ROM/native build and copied-save instruction/runtime checks.
- [ ] Port the remaining modern combined final-damage modifier chain. Filter,
  Expert Belt, Life Orb, Metronome and other modifiers still follow legacy
  positions/rounding. Do not infer exact Gen IX combinations from isolated tests.
- [ ] Continue status scripts (burn, sleep, Electric immunity, powder immunity),
  weather/snow/duration, dynamic turn ordering and updated ability/move effects.

Affected source: `include/battle/battle.h`, `include/qol_config.h`,
`src/battle/battle_util.c`, `battle_command.c`, `battle_controller_player.c`,
`trainer_ai.c`. Tests: `tools/qol/test_modern_rules.py`.

The installed four-feature build and real save remain separate from these
uninstalled development artifacts. Native generation uses the modified ROM's
own layout and must be repeated after further game-code changes.
