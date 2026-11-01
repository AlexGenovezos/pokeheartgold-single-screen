# Expanded move support and first Fairy attacks

**Goal:** Support later-generation move IDs without changing saved move fields
or the embedded legacy `TrainerAIData` layout, then introduce the five ordinary
Fairy attacks needed by the original roster.

**Architecture:** Keep `NUM_MOVES=467` for the existing battle struct. A shared
read-only accessor selects its legacy data or a separately stored extended
entry. All battle/AI direct indexing uses that accessor. New IDs follow the
pinned hg-engine scheme (official ID+3 after the original placeholder entries).
An independent default-off `QOL_MODERN_MOVES` flag gates the new game data.

## Move metadata and transport

- [x] Add actual-source tests for IDs577/580/586/588/608 metadata, unknown IDs,
  original-table reads, PP calculations and unchanged structure sizes. Run red
  before introducing the accessor or entries.
- [x] Define Disarming Voice577, Draining Kiss580, Play Rough586, Moonblast588
  and Dazzling Gleam608 in a separate constants header. Add an extended metadata
  table using native effects17/3/68/71/0 and the corrected Gen IX profile.
- [x] Change every battle/AI `trainerAIData.moveData[...]` read to a shared
  accessor; keep the old array size and legacy feature-off expansion unchanged.
  Update preview/recording validation, animation aliases and Metronome's callable
  pool to accept supported new IDs without accepting placeholders/unknown data.
- [x] Register Disarming Voice as sound and implement sound bypass of Substitute
  in every relevant damage/status path, preserving Soundproof/Mold Breaker.

## Resources and learning

- [x] Reproducibly extend movedata, move-script/animation resources, name banks
  750/751 and description bank749. Original members and IDs stay stable.
- [x] Draining Kiss uses the native drain effect with a source-compiled script
  branch for three-quarter recovery, preserving Big Root, Liquid Ooze, Heal Block
  and Magic Guard. Verify original SDK byte parity before modifying source copy.
- [x] Add move-card short labels only where needed to fit full effectiveness
  indicators. Keep full names in descriptions/summary and other dialogs.
- [x] Migrate level-up entries to a wider representation through a private
  adapter; update creation, level-up, daycare and move-relearner consumers and
  capacities together. Existing saved moves remain u16. Import only implemented
  new moves into accessible learnsets until the remaining effects are ported.

## Verification

- [x] Run all existing feature-off tests, extended-move tests and actual C effect
  tests. Review no direct extended-ID indexing remains in legacy arrays.
- [x] Full source/native build with a matching transformed-ROM layout. Check
  learned/saved moves and actual Fairy attacks/immunities/drain/sound behavior
  on isolated fixtures and in native/interpreter instruction lockstep.
- [x] Independent spec/quality review and source-only commits. This is the first
  move batch; continue the remaining178-move profile and abilities before calling
  the full requested Generation IX conversion complete.

Validation on 2026-11-01: 90 QoL host tests passed, including original behavior,
actual source functions, all consumers, compiled drain/paralysis scripts and
resource preservation. Full source/ROM/native build passed with all three
modern flags. Native/interpreter lockstep passed 600 fresh boot frames, 900
battle frames using Disarming Voice, and 1,700 using Draining Kiss; both battle
comparisons had zero interpreter fallbacks and guard failures. An isolated save
loaded all four extended move IDs, displayed their Fairy cards and resistance
labels, and Draining Kiss restored Clefairy from 12/24 to 15/24 HP. Original save
and installed artifacts were untouched. Relearning/evolution/daycare paths were
executed in the actual-source host harness, not through native UI automation.
