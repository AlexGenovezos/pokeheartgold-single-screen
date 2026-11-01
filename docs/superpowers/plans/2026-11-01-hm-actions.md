# HM actions implementation plan

**Goal:** All eight HMs work after their normal acquisition and badge gates,
without learning the move, including saves that already own the HMs.

**Architecture:** Keep actual learned-move queries truthful. A shared helper
checks HM ownership, badge and a valid non-egg animation actor. Use it only in
the seven standard field scripts and the Surf/Waterfall movement checks. Add
currently usable HM actions to the existing party menu (Fly included), reusing
the existing field checks and execution paths. Keep four field-action slots
and eight total entries; remaining slots retain learned non-HM actions.

**Validation:** Host C regressions execute the real unlock/helper/script/menu
functions. Cover every HM with neither/item-only/badge-only/both prerequisites,
wrong badges, eggs/empty party, original query behavior, full menu bounds and
existing non-HM moves. Compile the ROM and generate matching native layout.

- [x] Write and run failing unlock, script-scoping and party-menu regressions.
- [x] Add `include/qol_field_moves.h` and `src/qol_field_moves.c`, register the
  object in `main.lsf`, and enable `QOL_HM_ACTIONS` under `QOL_MODS`.
- [x] Integrate the shared actor check into `src/scrcmd_party.c` only for the
  corresponding standard field script. Integrate Surf/Waterfall checks in
  `src/field/field_control.c`.
- [x] Add available actions in `PartyMenu_SetContextMenuItems_Field`, preserving
  menu capacity, optional HM teaching and learned non-HM field actions.
- [x] Run host tests and the full ROM build; investigate all compiler failures.
- [x] Regenerate native output from this build's NEF/layout, build and test with
  copied save data. Deploy only verified output and retain rollback files.

Independent review found no blocking logic issues. A Whirlpool-only menu
regression and allocation-free HM pocket lookup were added after review. The
full QoL suite now has 22 checks; the full ROM and matching native builds pass.
The native build is installed with a backup and unchanged real save. The current
early-game test save has no HMs/badges; all eight late-game field environments
remain gameplay checks in issue #4 rather than being inferred from host tests.
