# Optional Level Cap Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Provide a pure, portable boss resolver, tagged option codec and EXP-award limiter for the approved optional level cap.

**Architecture:** New game C functions consume explicit story state and EXP values; they neither read nor write saves, Pokémon, battle state or frontend settings. Later game entry points will resolve story state and growth-curve thresholds, call this core, and retain their existing level-up behavior. This checkpoint leaves the module unregistered so the concurrent Wind Rider build inputs stay unchanged.

**Tech Stack:** Existing C99 game constants; Python unittest; host C compiler with optional ASan/UBSan. SDK, native builds, installations and live saves are outside this checkpoint.

---

## Approved behavior and boundaries

The setting defaults Off. Only encoded value `0xC701` enables it; zero and every other value decode Off. Encoding an Off confirmation returns zero. The current boss is derived, never persisted.

With caps enabled, choose the lowest-ace unbeaten Johto leader using individual badge bits, then the next first-story League member. The League caps are Will42, Koga44, Bruno46, Karen47 and Lance50. The existing four defeated-member bits are input bits0..3 in that order. A new League attempt can reset those bits and return the cap to42; existing over-cap Pokémon remain intact.

Game-clear takes precedence over all Johto and League inputs: choose the lowest-ace unbeaten Kanto leader. Use badge ID to break the Brock/Misty54 tie. All Kanto badges yield trainer `TRAINER_NONE`, level100, meaning the original level100 rules apply. There is no Red/rematch cap. This pure resolver is independent of whether the option is enabled, allowing the UI to display the next boss while Off.

The EXP limit is the existing species growth-table EXP needed to **reach** the ace's level. The pure helper receives that threshold, current EXP and requested positive award. Disabled returns the request unchanged. Enabled returns zero at/above threshold, otherwise the lesser of the request and threshold minus existing EXP. It returns an accepted award and never rewrites prior EXP. Suppressed EXP is discarded. Caller-owned original level100 bounds remain authoritative when no progression boss remains.

## File map

- Create `include/qol_level_caps.h`: result type, exact config values, League input-bit names and four public pure functions.
- Create `src/qol_level_caps.c`: original boss tables in badge order, minimum resolver, option codec and overflow-safe award arithmetic.
- Create `tools/qol/test_level_caps.py`: actual complete production C compilation, original trainer/growth data oracles and focused semantic cases.
- No existing source, constants, build list or save layouts change in this checkpoint.

### Task 1: Pin the pure API and semantic RED cases

- [x] Write focused tests using this public API:

```c
typedef struct QolLevelCap {
    u16 trainerId;
    u8 level;
} QolLevelCap;

QolLevelCap Qol_GetLevelCap(u16 badges, BOOL gameClear, u8 defeatedEliteFour);
BOOL Qol_LevelCapConfigEnabled(u16 value);
u16 Qol_LevelCapConfigValue(BOOL enabled);
u32 Qol_LevelCapAllowedExp(BOOL enabled, u32 oldExp, u32 requestedExp, u32 capExp);
```

- [x] Compile the real C translation unit when present; only the preimplementation RED fixture supplies the absent feature's ordinary uncapped behavior. Define SDK scalar types behind the existing `global.h` include guard; do not mock the core functions during GREEN.
- [x] Run `python3 -m unittest discover -s tools/qol -p test_level_caps.py -v` and record semantic failures for the missing boss/config/award behavior under `.local-tools/validation/level-cap-core-red.log`. This focused pattern must not enter the SDK lane.

### Task 2: Implement the original boss resolver

- [x] Add the header and C module. Johto rows in badge order are Falkner13, Bugsy17, Whitney19, Morty25, Chuck31, Jasmine35, Pryce34, Clair41. Kanto rows are Brock54, Misty54, Surge53, Erika56, Janine50, Sabrina55, Blaine59, Blue60. Use existing `BADGE_*` and original `TRAINER_*` constants.
- [x] Scan missing badges and replace the result only when a candidate has a strictly smaller level. This preserves badge-ID ties. Resolve game-clear/Kanto before inspecting Johto or the four League input bits.
- [x] Select the first unset Will/Koga/Bruno/Karen input bit after all Johto badges; if none is unset, return Lance50.
- [x] Test every Johto badge mask, every Kanto badge mask and all16 League input combinations against an independent oracle formed from original trainer JSON, not a duplicate production table. Include equal-count/different-badge states and stale post-clear League resets.

### Task 3: Implement exact option values and award arithmetic

- [x] Decode only `0xC701`, encode truthy On as `0xC701` and Off as zero. Test every16-bit raw config input to ensure unknown versions stay Off.
- [x] Implement the award limiter with subtraction before addition:

```c
if (!enabled) {
    return requestedExp;
}
if (oldExp >= capExp) {
    return 0;
}
return requestedExp < capExp - oldExp ? requestedExp : capExp - oldExp;
```

- [x] Use every checked-in row of `files/poketool/personal/growtbl.csv` and every progression ace to test below/at/above/crossing awards. Include `UINT_MAX`, zero threshold/request, nonzero progress within the capped level, and disabled original behavior. Callers must not invoke enabled progression limiting for the final100/no-boss result.
- [x] Run the focused module with optional sanitizers using `LEVEL_CAP_SANITIZE=1 ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1`. Report ASan/UBSan scope without claiming leak detection.

### Task 4: Release the independent core for review

- [x] Record exact commands, counts, durations and hashes of the four new files plus focused evidence in an ignored validation manifest.
- [x] Run `git diff --check --` on these new paths and independently verify that every frozen Wind source/test/doc hash remains unchanged.
- [x] Release writes to root for fresh specification and quality review. Do not stage, commit, build or install this checkpoint.

## Required later integration, outside this core checkpoint

The full feature still needs explicit audited save-variable allocation (`416F` config, `416E` independent daycare breeding phase), independent `QOL_LEVEL_CAPS` gating and `main.lsf` registration. The variable audit and format note must precede save integration; no Pokémon/Options/save-block sizes may change.

Battle awards must clamp the displayed award and both Pokémon/battle EXP caches after all multipliers, while retaining EV gains. Rare Candy must reject usability and application without consuming an item at cap. Pokéwalker must derive level-up friendship from accepted EXP. Daycare must suppress new growth while its separate clock preserves egg-roll timing, migrations, previews, prices, retrieval and parent compaction. Acquired or previously over-cap Pokémon and preexisting pending daycare EXP remain intact.

An in-game Options control must show Off/On and current boss/level, write the exact codec only on confirmation, and roll back on cancel. Final focused producer tests, save compatibility, genuine SDK builds, matching native/interpreter battle and menu acceptance, and source-only review/commit are separate gates. The installed four-QoL app and live save must remain safe; the incomplete Gen IX ruleset is not an installation candidate.

## Core checkpoint verification

The nine focused tests first failed semantically against absent-feature ordinary uncapped behavior (`level-cap-core-red.log`, 2.570s). A preceding include-path harness error is retained separately and is not semantic RED evidence. The complete new production C translation unit then passed all nine tests.

The final fail-closed host gate forbids both battle SDK entry points before importing the test module: **9/9 tests passed in4.507s**, no failures/errors/skips and zero SDK attempts. The same final guarded module with ASan/UBSan passed **9/9 in8.079s**, again zero SDK attempts. ASan uses `detect_leaks=0`; leak-detector coverage is not claimed. The original trainer JSON supplies all21 story-team ace checks; all256 Kanto masks, all255 incomplete Johto masks, all16 League flag combinations, all65,536 configuration words, all eight checked-in growth rows and overflow/resume boundaries are covered.

All176 previously frozen Wind Rider source/evidence/ABI hashes were independently confirmed unchanged. Only this plan, the new header, the new core C module and its new focused test file were written outside ignored validation. No build registration, caller hook, save allocation, runtime setting, SDK/native build, emulator run, staging, commit or installation is part of this checkpoint. Fresh root specification and quality reviews, then the full integration gates above, remain required before this feature can be claimed playable.


## Root core acceptance

Fresh specification review passed 9 guarded host tests in 2.622 seconds. Fresh
quality review passed 9 host checks in 10.015 seconds and 9 ASan/UBSan checks
in 17.128 seconds, with leak detection disabled and no SDK entry attempts.
Root then compiled the unchanged complete core C unit with the genuine SDK
compiler in both all-modern-flags-disabled and enabled profiles; both temporary
objects passed. No standard build or link ran for this core checkpoint.

The reviewed core remains unlinked. Producer hooks, save adapters and the
Options interface are the next implementation milestone; these results do not
claim an active or installed level cap.
