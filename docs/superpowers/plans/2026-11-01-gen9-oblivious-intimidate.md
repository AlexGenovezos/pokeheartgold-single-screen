# Oblivious, Intimidate and four ready ability pairs

**Goal:** Implement the approved ordinary Gen IX subset behind the existing default-off modern flag, preserving original roster, story, saved bytes and native layouts.

**Architecture:** Extend the native cure selector; transform only original subscripts132/186/221 after complete source hashes and SDK byte parity; extend the existing loader/save adapter for four already implemented abilities. No new ability IDs, script IDs, fields or stack frames.

**Tech Stack:** native C, Metrowerks battle scripts, Python resource transforms and actual-C host/SDK command tests.

The complete read-only design is `.local-tools/validation/oblivious-intimidate-plan.md`; references are pinned hg-engine61b510cfb6cf7d77c3b083150fad3499f82fd326 and expansionc460a8661dfa0598ae25d42a968c690ecbf489c6. This task is already approved for inline execution; leave every change unstaged and do not build/install/commit.

- [x] Add failing actual-C cure tests to `tools/qol/test_modern_oblivious_intimidate.py`: retain Attract priority, select Taunt message7 only in modern mode, suppression/recovery and repeated checks terminate. Extend `test_modern_cursed_body.py` exhaustive saved-byte/loader checks and `test_ability_descriptions.py` expected descriptions; verify RED.
- [x] Add generator contract tests: full hash drift, wrong member and duplicate rejection, unchanged binary parity before modified compile, exactly299 members with names and297/298 preserved; default/type-only compiler inactivity. Observe RED before adding `tools/qol/oblivious_intimidate_scripts.py` and wiring the chain after Competitive.
- [x] Add native-command VM coverage using existing Competitive harness and original SDK scripts. Verify cure7 branches before status formatter, preserves primary status/icon and no extra Calls; ability holders recorded explicitly. Verify Taunt's ignorable immunity retains Mold Breaker and old duration/failure paths. Verify four Intimidate blockers, suppression, doubles ordering/restoration and unaffected Competitive recipient.
- [x] Execute actual native Hydration weather command and status restore190 through104 with all primary statuses/Nightmare, suppression, weather blockers and KO; reuse existing finite weather5/8-turn/expiration/reentry tests before enabling Wingull/Pelipper/Torkoal/Feebas pairs.
- [x] Implement minimal C selector, generator, descriptions and four-pair adapter. Update existing resource mocks for the added pipeline stage. Verify focused host and SDK groups serially, logging `.local-tools/validation/gen9-oblivious-intimidate-focused.log`; do not repeat expensive unchanged SDK parity after unrelated edits.
- [x] Self-review against complete approved design, `git diff --check`, update `docs/QOL-REUSE.md` and ability coverage plan with precise scope/evidence/limits. Release unstaged production + focused-green tests for parent spec/quality reviews. Parent owns global suite and full native validation.


Focused validation completed without a full build or global-suite run:
- Final host/resource regression group:46 tests passed in8.799s.
- Stable transformed SDK/native VM group:4 tests passed; additional gain/recovery,
  maximum-depth and unrelated-actor checks passed4/4 using the same verified
  bytecode, without repeating the unchanged SDK parity compilations.
- Pre-enable readiness group:4 tests passed in100.997s (Hydration, two finite
  weather SDK cases, and native matching-weather/reentry behavior).
- The encrypted getter and native new-mon selection test failed against the
  original adapter before implementation, then passed alongside the exhaustive
  roster/byte/form/PID loader tests in default and modern modes.

The ignored focused log retains RED failures and harness setup corrections as
separate chronological groups. Production changes are unstaged and released to
the parent for independent spec/quality reviews. Global tests, matching native
build and copied-save validation remain pending; no installation was changed.


## Combined integration verification

The final combined Oblivious/Intimidate and Simple/X-item snapshot passed all
209 host/SDK tests in735.207s and a fresh paired game/resource/layout/native build.
Both independent spec and quality reviews passed before integration. The added
player-bag test executes selection, recovery and consumption for all six X items,
including successful use, cap/no-op behavior and exactly-once consumption.

Nine copied-save native/interpreter comparisons passed every ARM9 instruction.
Six stable battle segments (1700 frames each) had zero fallbacks or guard failures:
Taunt was blocked by Oblivious but affected its control (counter4); Simple Defense
Curl stored+2 Defense versus the control's+1; Simple Swords Dance stored+4 Attack
and visibly printed “drastically rose”; Pelipper's Drizzle with Damp Rock produced
rain with8 turns. Three entry segments (2500 frames each) matched instructions
with0.25% interpreter fallback and10 overlay evictions: Oblivious blocked
Intimidate while its control lost1 Attack, and Pelipper loaded Drizzle before its
rain script completed in the final stable segment.

All22 frozen source/test hashes and all six validation save hashes matched.
The native source remains b602f2d. This milestone is development verification,
not complete Gen IX parity or an installation; the playable four-QoL app and real
save remain unchanged. Remaining move/ability, Snow, timing and delayed-hit work
continues separately. Logs and isolated artifacts are ignored local validation
files and are not committed.
