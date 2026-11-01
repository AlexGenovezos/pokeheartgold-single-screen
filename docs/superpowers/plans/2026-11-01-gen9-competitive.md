# Competitive Implementation Plan

> **For agentic workers:** Execute inline using the existing approved ability plan and TDD. No delegation, commits, native build, installation or push in this milestone.

**Goal:** Add Competitive (172) to ordinary modern battles and its four standard species pairs while preserving native layouts and default behavior.

**Architecture:** Mark an actual opposed stat reduction in unused low bit0 of the existing statChangeFlag. At the end of native subscript12, consume the marker and tail-jump to presentation298 so the original script caller and four-frame stack remain intact. Adapt only original stored standard ability bytes using personality parity.

**Tech Stack:** Native C, Python unittest host extraction, original SDK battle script assembler and NARC/message resource transforms.

- [x] Add failing actual-C checks in `tools/qol/test_modern_competitive.py` for reductions, provenance, suppression, stack/caller preservation, caps and marker lifetime. Execute in flag-off and modern configurations.
- [x] Implement the mutation marker and end-script tail dispatch in `src/battle/battle_command.c`; add only constants in `include/constants/abilities.h` and `include/constants/battle_subscript.h`. Keep BattleContext unchanged.
- [x] Add resource tests first, then guarded `tools/qol/competitive_scripts.py` and `tools/qol/modern_rom.py` composition. Preserve all original297 members and Cursed Body297; append298. Verify source hash and original SDK parity.
- [x] Extend bank720/721/722 tests first, then `tools/qol/ability_descriptions.py` to173 entries preserving originals, Cursed Body and unused placeholders.
- [x] Extend all-loader/all-byte/parity/form storage checks first, then `src/qol_abilities.c`, `include/qol_abilities.h`, and the getter in `src/pokemon.c`: Jigglypuff/Wigglytuff/Igglybuff [56,172], Milotic [63,172]. Gengar conversion retained; other bytes/species/forms unchanged.
- [x] Run real SDK Tickle, Memento and Intimidate scripts through native stack paths, including two recipients and attacker restoration. Verify ability message1087 reveals Competitive to AI without claiming bespoke AI scoring.
- [x] Run focused then complete serialized host/SDK suite, log `.local-tools/validation/gen9-competitive-tests.log`, inspect diff and whitespace. Update coverage/reuse notes with limits; leave edits unstaged for independent review.


Verification notes:
- Focused 20-test Cursed Body/Competitive/resource batch passed before independent review.
- The first complete run passed146/147 tests; the sole failure was a flag-off test-harness compile warning for unused `boxMon` and `blockB` pointers. The production getter never executed in that failing case. An isolated missing-casts/repaired-casts reproduction confirmed the cause; the repaired harness retains explicit nonmutation assertions and passes both configurations. Evidence: `.local-tools/validation/gen9-competitive-storage-regression.log`.
- The separate progress-tool suite passed36/36 tests.
- Independent spec review found an inactive-recipient guard gap. The added active-slot guards and failing-then-passing regression cover two-battler inactive slots and invalid End recipients before any new pointer access.
- Final serialized QOL host/SDK suite:149 tests passed in260.647s, exit0; `.local-tools/validation/gen9-competitive-tests.log`. This includes nine new Competitive cases and actual SDK presentation depth0–4. The separate focused SDK class passed2/2 tests.
- `git diff --check` passed. All changes remain unstaged; no full native build, commit, push or installation was performed. Independent quality review and matching native/copied-save validation remain integration work.

Combined native verification passed: odd-PID stored Cute Charm loads Competitive
and gains Special Attack+2 from Intimidate; the even-PID control retains Cute
Charm without a boost. Both2500-frame entry comparisons match the interpreter.
The full combined177-test suite and paired native build passed.
