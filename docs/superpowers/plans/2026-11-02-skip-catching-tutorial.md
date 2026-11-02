# Catching tutorial skip implementation plan

> **For agentic workers:** Use the executing-plans workflow. Keep the currently
> compiling controls/caps artifact family frozen; this change adds a separate
> data transform and never edits compiled game code or imported game assets.

**Goal:** Skip the Route 29 lesson while retaining the original five-ball
reward, NPC removal, route-state update, story flags and restored controls.

**Architecture:** Patch only two bounded regions (six and eight bytes) in script
member225 of `a/0/1/2`. Preserve follower reset/LockAll, jump to the original
reward at0x513, close its final textbox at0x523, then jump from0x525 to the
original completion at0x53B. The
known2580-byte input script has SHA256
`3ed238656dbe0c565a3c5ad8cafd29e1fea97d46ea70543c1aa4e4656f37aee6`.
Accept its exact patched form idempotently and reject every other script.
Write the same-size member in place so ROM layout, headers, executable and
overlay bytes remain identical. A separate CLI creates a new ROM exclusively.

**Tech stack:** Python3/Nitro parsers, existing field-script commands, host C
compiler for actual interpreter/branching checks; matching native runtime later.

## Research and scope

Research is recorded in `docs/QOL-REUSE.md` and issue9. Existing intro-skip
bundles change more story/UI behavior, and the inspected skipIntro source still
calls the catching tutorial. Use the original reward/completion implementation;
no third-party implementation or imported game asset is copied into tracked
source. `AGENTS.md` makes research-before-implementation a continuing rule.

## Task 1: Establish behavior and safety regressions

- [x] Add `tools/qol/test_skip_catching_tutorial.py` with semantic identity
  fallback before the module exists.
- [x] Run `python3 -m unittest discover -s tools/qol -p test_skip_catching_tutorial.py -v`.
  Baseline: six tests, nine intended failures; no import/compiler errors. The
  actual C interpreter reaches a forbidden old tutorial command without a patch.
- [x] Execute actual `RunScriptCommand`, read/jump/flag/variable handlers for
  both genders. SDK graphics/follower/item delivery are explicit boundaries;
  this does not claim to execute the bag or native field task manager.
- [x] Check exact patch ranges/size, existing reward/completion reachability,
  unknown/partial input rejection, idempotence, synthetic-ROM byte preservation,
  executable overlap rejection and exclusive-output CLI behavior.

## Task 2: Implement the isolated data transform

- [x] Create `tools/qol/skip_catching_tutorial.py`. Expose `patch_script(data)`
  and `patch_rom(data)`; the latter validates the NARC and locates its existing
  BTAF/GMIF member range rather than repacking or appending files.
- [x] Generate the two forward branches with
  `struct.pack('<Hi',22,target-(offset+6))` at0x1B6→0x513 and0x525→0x53B,
  placing the existing CloseMsg opcode53 at0x523 first.
  Require the exact original or patched whole-script hash,965 members and no
  intersection between the script resource and executable/header/table ranges.
- [x] Add a CLI accepting input and new output paths, refusing existing output
  or aliases, printing hashes and changed-byte counts. The original is read-only.
- [x] Rerun the focused suite and verify `git diff --check`.

## Task 3: Build integration and delivery

- [x] Add an explicit `QOL_SKIP_CATCHING_TUTORIAL` build option to the native
  QoL build wrapper, default1 for that opt-in wrapper, with0 retaining the demo.
  Apply the transform to a new output path after optional modern resources and
  before layout generation. Preserve the current in-flight build/fixtures.
- [ ] Run source review and apply to a private current-ROM copy. Verify every
  byte outside the two script instructions is identical, including all code.
- [ ] After the frozen controls/caps native family completes, reuse its native
  executable/layout only after code-byte compatibility is proven. Fresh-boot
  before-tutorial fixtures for both genders; check five balls once, correct
  flags/state, NPC removal, follower/player controls and no demo battle.
- [ ] Save/reload and cross the trigger again; verify no repeated reward.
  Existing completed saves retain their state. Check an ordinary capture.
- [ ] Update source/docs/issue9 with actual evidence and include only accepted
  artifacts in the guarded app update. No install or gameplay-complete claim
  before these runtime checks. Keep generated ROMs, assets and saves ignored.

## Source verification and review correction

The initial six tests passed before review. Review then identified that the
standard reward returns with its final message window open, while the first
candidate jumped past CloseMsg. An added message-open assertion failed on that
candidate. The corrected second region contains CloseMsg followed by GoTo.
The test now executes the actual CloseMsg handler with graphics edges stubbed,
and asserts both textbox flags are clear before releasing map objects.
Existing original scripts also use GiveItemNoCheck immediately followed by
CloseMsg; no new message format or button wait is introduced.

Final source verification: ten tests passed in17.704s, including the actual C
interpreter/cleanup and isolated build-wrapper routing/disable/invalid-option
checks. Shell syntax and whitespace checks passed. This is source/host evidence;
actual field control, bag delivery and save/reload remain runtime gates above.
