# Next 35 ordinary modern moves implementation plan

> **For agentic workers:** Execute inline against the existing approved Gen IX spec. Parent review checkpoints follow focused validation. No staging, commits, native builds, installation, or additional agents in this task.

**Goal:** Increase supported modern moves from 17 to 52 while preserving original move records, saved IDs, roster, story, and native ABI.

**Architecture:** Extend the shared literal metadata and presentation/learnset adapters. Reuse audited native effects, adding only the missing sound, Substitute, punching, Metronome, thaw, screen, and Choice pivot hooks. Keep generated resources reproducible from the pinned hg-engine profile and original NARCs.

**Tech stack:** Native C battle functions, Python unittest host extraction harnesses, SDK-assembled DS battle scripts and original archive parity checks.

## Tasks

- [x] Add independent 35-row expectations in `tools/qol/test_modern_next_moves.py`; compile actual `src/qol_moves.c` with flags off/on and assert all native fields, aliases, classification, bounds, and unsupported gaps. Run the focused metadata tests and observe missing-entry failures.
- [x] Add actual-function regression tests for `BattleSystem_TryDirectSideEffect`, target thaw in `BattleControllerPlayer_AfterMoveEffects`, and `BattleControllerPlayer_UpdateMoveHistory`; cover failed/immune/protected hits, screen ordering, actual HP damage, and completed versus failed pivots. Observe failures before hook edits.
- [x] Add and execute native effect/script coverage for recoil, fixed two hits, Snarl/Play Nice/stat changes, self thaw, rampage, and pivot eligibility using existing extraction/SDK helpers. Preserve unchanged SDK parity against the original NARCs.
- [x] Append the audited 35 literal entries to `include/data/qol_move_entries.inc`; add constants and count52 to `include/constants/qol_moves.h`; add full names, compact cards, and truthful descriptions in `tools/qol/move_resources.py`. Wild Charge uses48, Scorching Sands125, Psychic Fangs15PP.
- [x] Add only the audited native hooks in `src/qol_moves.c`, `src/battle/battle_util.c`, and `src/battle/battle_controller_player.c`. Keep existing Competitive, ability helpers, completed U-turn guard, and pivot source timing intact.
- [x] Expand `tools/qol/learnset_import.py` supported IDs, regenerate `include/data/qol_learnsets.inc` from `.local-tools/validation/gen9-import-profile.json`, update existing expected counts and exercise the five-addition Gardevoir boundary with real consumers. The corrected profile import produces209 rows/160 species (hyphenated Baby-Doll Eyes included); capacity28/maxAdd5 remains unchanged.
- [x] Run focused and relevant SDK/source/resource/learnset checks serially, logging to `.local-tools/validation/gen9-next-35-moves-focused.log`. Do not run the full global suite before parent reviews.
- [x] Document 52 implemented moves, source overrides, missing level access for11 new moves plus2 prior moves, deferred unsafe moves, and future slicing/biting ability classifiers in `docs/QOL-REUSE.md`. Review `git diff --check` and the unstaged diff; notify parent when ready for spec/quality reviews.

## Validation commands

`PYTHONPATH=tools/qol python3 -m unittest test_modern_next_moves test_modern_next_move_effects -v`

`PYTHONPATH=tools/qol python3 -m unittest test_modern_moves test_move_resources test_modern_learnsets test_modern_substitute test_modern_status_scripts test_modern_drain_script -v`

`python3 tools/qol/learnset_import.py --profile .local-tools/validation/gen9-import-profile.json --check`

`git diff --check`

Full host suite, combined ROM/native build, copied-save fixtures, and release are parent-owned after reviews.

## Focused results

The final focused log records separate completed command groups, not one global invocation. The new regressions include real post-Substitute contact and item dispatch; HpCalc clears only bit8 on a subsequent real-HP strike in modern modes, preserving other bits and original behavior. Focused Cursed Body, Substitute, and Sturdy checks were rerun after that fix. SDK parity covers26 unchanged original effect/subscript members; compiled modern paralysis control flow uses Nuzzle. No script source changed after SDK verification. Both review stages and the combined full suite/native validation have passed.

The separate passing groups cover63 distinct focused tests;20 new host regressions pass after the final marker fix. SDK parity passed198.772s; the modern paralysis execution check passed23.295s. `.local-tools/validation/gen9-next-35-moves-focused.log` retains labeled group outputs; earlier red/pre-final logs remain separate.

Combined verification:177 host/SDK tests passed in702.580s; the paired native
build and six copied-save comparisons passed. Native Twin Beam reports two hits,
Power-Up Punch raises Attack, and Wild Charge causes2 recoil from10 target
damage. See `docs/QOL-REUSE.md` for entry fallback counts and evidence limits.
