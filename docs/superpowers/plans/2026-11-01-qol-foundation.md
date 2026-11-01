# QoL foundation implementation plan

**Goal:** Establish the QoL patch/native workflow, then install verified output
with a backup of the original working game.

**Architecture:** Keep the clean ROM and save outside Git. Use standard BPS
patches with source/target/patch CRC verification and explicit source SHA-1.
Game behavior changes stay in C source; native generation must use matching
layout metadata. The original missing-library blocker is resolved. Do not infer
emulator/native gameplay validation from host tests alone.

**Tech stack:** Python standard library for BPS and host test orchestration;
host C compiler for focused game logic tests; existing game build when its
proprietary prerequisites become available.

## Task 1: Build and patch foundation (#1)

- [x] Add `tools/qol/test_rom_patch.py` with a known byte-level BPS fixture,
  source-read/literal round trips, size changes, invalid source, corrupted
  target/patch CRCs, truncated patches and non-overwriting CLI behavior.
- [x] Run `python3 -m unittest discover -s tools/qol -p 'test_*.py' -v` and
  observe missing patch support.
- [x] Add `tools/qol/rom_patch.py` with `create` and `apply` commands. Require
  `--source-sha1` for creation; use BPS format CRCs for patch application.
  Never overwrite inputs or an existing destination.
- [x] Run the host tests and perform a local round trip on a temporary copy
  of the clean ROM with a synthetic edit. Label that as a packaging test,
  not a playable mod.
- [x] Document missing compiler/SDK prerequisites and the native section-hash
  constraint in `docs/QOL.md`; retain #1 as open until real builds are verified.

## Task 2: Reusable TMs (#3)

- [x] Find the successful learn-move consumption path and regression-test its
  actual C function with a host harness, including non-TM/HM item behavior.
- [x] Add a narrowly scoped item-range exception, preserving PP, friendship,
  mood, move compatibility and unrelated consumables.
- [x] Run the host regression; record that a full ROM/playthrough is pending.

## Task 3: Instant text (#2)

- [x] Add a fourth saved speed without enlarging the save's Options struct.
- [x] Keep an asynchronous printer for dialog; a synchronous zero-speed
  printer can discard wait/callback behavior and is not sufficient.
- [x] Test burst rendering, callbacks, waits and completion using the actual
  printer source through a host harness before changing it.
- [x] Update option labels, coordinates, input hitboxes and selection bounds
  together; preserve existing speed values and baseline build behavior.
- [x] Verify with host tests; leave gameplay/UI verification pending a build.

## Subsequent work

HM actions (#4) require coordinated field checks, event scripts, animations
and a Fly entry point; do not fake a party member knowing a move globally.
Effectiveness indicators (#5) must use the active rules and actual target.
Battle modernization (#6) remains a separate ruleset decision; recommend
Gen IX plus Fairy (subsequently selected by the user). Investigate these independently
while build prerequisites are unresolved, recording concrete source findings
in their issues.

## Verification and delivery

- [x] Run existing progress-tool tests and focused new tests.
- [x] Run `git diff --check` and inspect the staged diff for game data/secrets.
- [x] Commit only source, tests and documentation on `qol-mods` and push it.
- [x] Update issue descriptions with completed work and unverified items;
  keep issues open until their acceptance criteria are satisfied.

## Execution checkpoint

- BPS utility implemented with conformance, corruption and CLI safeguards;
  a 128 MiB synthetic edit round trip passed without modifying the clean ROM.
- Reusable TM source logic implemented and host-tested for all 92 TMs across
  all four move slots, repeated teaching and unrelated consumption behavior.
- Instant text source and Options UI implemented and host-tested; independent
  review found and prompted fixes for label clipping and reusing the opening
  input across two print-queue calls. Real renderer regressions cover A and touch.
- Matching supplied libraries were recovered locally; the full ROM and native
  builds pass. Installed game `f627ef607` / native `2ec876e` with original ROM,
  real save and old app/native artifacts preserved. No iCloud action is needed.
- Options/overworld/battle checks and 600 boot + 1,100 Options + 700 battle
  lockstep frames passed. Instant survived a real save/cold-boot test on an
  isolated save; the live save hash did not change during installation.
- 22 QoL, 36 progress and 26 native host checks pass. Broader late-game HM,
  TM-teaching and doubles UI gameplay checks remain tracked in their issues.
- Completed HM/effectiveness source boundaries and remaining Gen IX research
  are in `docs/QOL-REUSE.md`. Reuse hg-engine where appropriate instead of
  independently implementing modern battle mechanics.
