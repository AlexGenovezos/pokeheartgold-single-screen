# Pixel Battle Controls Implementation Plan

> **For agentic workers:** Execute the approved tasks inline with the executing-plans skill. Root coordinates source review, the exclusive SDK lane and runtime acceptance; do not spawn workers or build/install without its release. Steps use checkboxes for tracking.

**Goal:** Keep the pixel-art 2×2 move grid while improving focus, labels and empty slots, making touches select the shown card, and keeping doubles HP bars clear of the panel.

**Architecture:** Game C owns move metadata, rendered labels and input. The native frontend composes those same pixels with a thin gold selection frame. Keep original battle-menu templates, callbacks, keyboard cancellation and battle rules intact; use a private visible-card touch list only in the ordinary SINGLE_SCREEN FIGHT query.

**Tech Stack:** C99 game code, C++17 native frontend, Python unittest and host clang for extracted production C; root-owned Nitro SDK, recompiler and native runtime acceptance later.

## Ownership and scope

Create `tools/qol/test_battle_move_labels.py`, `tools/qol/test_battle_controls_geometry.py` and this plan. Modify only `src/battle/battle_input.c`, `src/battle/battle_hp_bar.c`, `frontend/main.cpp`, sibling `../ssrecomp-qol/frontend/main.cpp`, sibling `../ssrecomp-qol/CHANGELOG.md`, `docs/QOL.md` and `tools/qol/README.md`. Keep pending modern move work, optional level-cap work, generated output, live saves/configuration and installed application files untouched. Root stages/commits source and manages delivery.

The sibling `AGENTS.md` requires visible changes under `## Unreleased`; preserve existing release headings and asset filenames. No new font, artwork, public structure, native input remapping or rendering engine change is needed.

## Task 1: Establish real-C RED before source changes

- [x] Add the two focused unittest modules. Import only host-safe metadata/resource helpers and `test_game_logic`; do not import or call SDK assembler helpers.
- [x] Execute actual `GetMoveAttr`/`LoadMoveEntry` with original NARC move bytes and real extended metadata; execute the actual effectiveness helper. Assert Leer/Tailwind and enabled Cotton Guard541/Shell Smash507 yield empty strings and skip preview; Tackle/Seismic Toss/Hidden Power and enabled Fairy Wind587 retain unknown `?`; values0/10/20/40/80/160 retain the exact multiplier text, including neutral `1x`.
- [x] Extract the literal FIGHT case from `BattleInput_SingleScreen_BuildItems`, preserving its source item structure and feature guards. Supply only message/format/font/allocation SDK boundaries. Measure actual game font widths; exercise FIGHTING/ELECTRIC type strings, real0PP, four slots, invalid remembered empty selection, empty metadata omission and string cleanup. Compile effectiveness0/1 and modern0/1, including all-modern1.
- [x] Execute actual `BattleInput_CheckTouch`, real touchscreen point/new-touch functions, original fight mapping/palette/template and real fight callback. Record visible card centres, top/left and right/bottom edges, gaps, margins, old coordinates, empty/0PP, disabled/held/no-new touch, tutorial and keyboard fallback. A separate actual cursor function test verifies A/B and the empty-slot mask passed into cursor navigation; it does not claim to execute the cursor navigation engine.
- [x] Decode actual NCER/NCGR resources from NARC `files/a/0/0/8`, combining nonzero pixel bounds with actual selected templates and position routes. Execute HP creation, offset, slide, bob and stop/reset using SDK sprite/task edges. Sine is bounded at±1 by a supplied edge; this tests route arithmetic rather than the sine library.
- [x] Run `python3 -m unittest discover -s tools/qol -p 'test_battle_*.py' -v`. Expected current-source failures: wrong visible touch mapping, old overlapping cancel, lower HP pixels reaching the panel, status `?`, pill/type spacing and bright empty raster. Existing ordinary geometry and unknown/numeric labels must pass. Keep ignored RED logs before source changes.

## Task 2: Status badges and card layout

**File:** `src/battle/battle_input.c`.

- [x] In `BattleInput_SingleScreen_Effectiveness`, create the existing String before checking actual move class:

```c
    BattleSystem *system = battleInput->battleSystem;
    String *string = String_New(8, HEAP_ID_BATTLE);
    if (GetMoveAttr(move, MOVEATTR_CLASS) == CATEGORY_STATUS) {
        return string;
    }
```

Remove the later duplicate declaration; preserve preview, unknown and multiplier switch. FIGHT and TARGET callers receive owned, non-null empty Strings.

- [x] In the literal FIGHT builder, set `BOOL empty = menu->moveNo[i] == MOVE_NONE`. Empty gets `String_New(2, HEAP_ID_BATTLE)` containing `{ CHAR_HYPHEN, EOS }`; real names retain `BattleInput_SingleScreen_MoveName`. Set `button = empty ? 6 : 5`, `topLabel = !empty`, `selected = !empty && selectedMove == i`, `grey = empty`. Preserve x/y and108×29 geometry. Keep metadata guarded by real MOVE_NONE, independently of PP.
- [x] Type text moves to `bx + 5`, keeps `by + 14`, and no longer sets pill. Number right edge becomes `bx + 103`; PP begins at `bx + 103 - numbersWidth - 3 - ppWidth`. Preserve name inset4 and badge right edge104; the measured72px name plus24px badge retains4px separation inside108px.
- [x] Document local style6 as empty move. In the raster painter, before selected handling:

```c
            if (style == 6) {
                color = border ? 12 : 15;
            } else if (selected && (border || i == 1 || j == 1 || i == w - 2 || j == h - 2)) {
```

Preserve corner clipping, text pixels, selected real-card gold and command palettes. Button labels use `items[i].grey ? MAKE_TEXT_COLOR(12, 15, 15) : SS_BUTTON_TEXT_COLOR`; empty topLabel false uses existing centred placement.
- [x] Re-run `python3 -m unittest discover -s tools/qol -p 'test_battle_move_labels.py' -v`; expect all cases to pass.

## Task 3: Visible FIGHT touch geometry

**File:** `src/battle/battle_input.c`.

- [x] Add under SINGLE_SCREEN near the original fight list:

```c
static const TouchscreenHitbox sSingleScreenFightTouchRects[] = {
    { .rect = { .top = 131, .bottom = 160, .left = 14, .right = 122 } },
    { .rect = { .top = 131, .bottom = 160, .left = 134, .right = 242 } },
    { .rect = { .top = 163, .bottom = 192, .left = 14, .right = 122 } },
    { .rect = { .top = 163, .bottom = 192, .left = 134, .right = 242 } },
    { .rect = { .top = TOUCHSCREEN_RECTLIST_END, .bottom = 0, .left = 0, .right = 0 } },
};
```

- [x] Replace only the nontutorial touch-query statement:

```c
#ifdef SINGLE_SCREEN
        if (battleInput->curMenuId == BATTLE_MENU_FIGHT) {
            rectHit = TouchscreenHitbox_FindRectAtTouchNew(sSingleScreenFightTouchRects);
            if (rectHit != TOUCH_MENU_NO_INPUT) {
                rectHit++; // Original template index0 is cancel, moves are1..4.
            }
        } else
#endif
        {
            rectHit = TouchscreenHitbox_FindRectAtTouchNew(menuTemplate->touchscreenRect);
        }
```

Leave tutorial, disabled-touch, keyboard fallback, templates, feedback hitboxes, palettes and callbacks unchanged. Outside cards there is no new touch action; B remains cancel. Empty rejection comes from the real callback, while0PP remains an attempted move choice for existing downstream rejection.
- [x] Re-run geometry tests; visible touch tests pass and ordinary-build tests remain green.

## Task 4: Doubles HP clearance through existing position routes

**File:** `src/battle/battle_hp_bar.c`.

- [x] Add SINGLE_SCREEN-only y values81 (`0x51`) and110 (`0x6E`) to player LHS/RHS templates; retain original103/132 in the `#else` branches. This22px shift supersedes the earlier ignored research's32px proposal. Keep x192/198, gap29, priorities and every other field.
- [x] Keep other templates and all arrow/offset/slide/bob code unchanged. Actual opaque pixel bounds are y[-18,16] inclusive; lower bar at110 plus16 plus maximum bob1 ends at127, above panel128. Its padded transparent OAM extends lower and is not a claim about visible pixels.
- [x] Re-run `python3 -m unittest discover -s tools/qol -p 'test_battle_controls_geometry.py' -v`; ordinary coordinates, unrelated templates, arrow following, slide endpoints and opaque clearance must pass.

## Task 5: Native focus and player documentation

- [x] Apply the same small SINGLE_SCREEN move-loop hunk in both tracked frontend copies:

```cpp
                        b.border = !moves || i == shown;
                        b.borderColor = moves ? 0xFFDE6B : (i == shown ? 0xF04040 : 0x101218);
                        b.borderWidth = moves ? 8 : (i == shown ? 16 : 6);
                        b.borderRadius = moves ? 3 : 0;
```

Keep command appearance and the later original-ROM horizontal strip unchanged. No cosmetic constant tests; actual composed screenshots verify the result.
- [x] Native Unreleased entry explains thinner gold focus, clearer spacing, quiet empty slots, correct card touches and doubles HP clearance. Update QOL/README label descriptions: status has no multiplier, `?` means unavailable damaging forecast, neutral remains `1x`. Do not claim the installed build changed until root accepts delivery.
- [x] Run the new two modules, existing `test_move_cards.py` and `test_effectiveness.py` host tests. Root separately owns required resource/SDK checks; do not run broad discovery. Inspect `git diff --check` and each bounded diff. Release owned files for fresh specification then quality review; no staging/commit by implementation worker.

Source checkpoint: the focused host suite passed12 new tests plus the existing move-card helper and two effectiveness checks (15 total). The RED log records semantic current-source failures; separate in-memory baseline-render and unknown-suppression mutation checks verify those regressions. No SDK compilation, native build, emulator, staging, commit or install was performed by this worker. Runtime acceptance below remains open.

## Root-owned paired classic acceptance and delivery

### Compact doubles HUD correction

The first SDK/interpreter preflight rejected the 22px upward shift: the stock
player panels covered an opposing Shuckle. The replacement keeps both player
panels in a single 24px row at y104–127, with centers (64,116) and (192,116).
It reuses the existing two-object cells and 0x1000-byte allocations, rendering
the original nickname, gender, level, status, HP digits and 48-unit gauge into
the compact area. Arrows use a 48px offset; compact panels do not bob and slide
256px out of view. Ordinary builds and other panel types retain their routes.

Code review approved the frozen replacement with no critical or important
findings. The root reran ten compact HUD tests, seven geometry tests and five
move-label tests; all passed. The reviewer independently ran the 17 compact
and geometry checks, including sanitizer coverage, with zero SDK calls. These
checks do not establish composed visual or native acceptance; the gates below
remain required for the replacement.

- [x] After source review and SDK-lane release, explicitly set QOL_MODS1 and MODERN_TYPES/BATTLE/MOVES0. Build with isolated `BUILD_DIR=build/soulsilver-qol-ui.us`; inspect producer logs before assuming isolation works. Preserve current Wind/modern outputs and installed family. Do not run the modern resource postprocessor.
- [x] Generate matching layout, `gen-qol-ui` and `build-macos-arm64-qol-ui`, retaining the native `.incbin` dependency fix. Record source revisions, defines and ROM/ELF/layout/native hashes; confirm legacy resource shapes and no extended message-bank dependency.
- [x] Fresh-boot copied-save fixtures from the exact new family. Do not reuse mismatched states or forced `--layout`. Confirm SINGLE_SCREEN recognition and battle-moves scene. Regenerate genuine doubles fixtures from the classic UI base, preserving live save/configuration.
- [ ] Inspect composed1280×720,1280×800,1920×1080, reduced-window and4:3 views; compare CPU/GPU and private smoothing0/1. Cover longest names/types, status, unknown damaging, neutral/fractional/immunity labels, real0PP, empty slots and several focus positions.
- [ ] Verify actual D-pad/keyboard/controller A/B, remembered choice, empty skipping,0PP rejection/Struggle, visible touch centres/edges/gaps and right-stick cursor. In genuine doubles inspect both active bars, arrows/bob, HP digits/gauge/status/name, slides, target selection and transitions; refine only if composed evidence requires it.
- [ ] Root installs only the accepted matched executable/ROM/layout through its guarded transaction. Preserve current live saves/configuration and launcher/controller setup; never restore validation saves over live play. Record accepted paired revisions in docs and issue7. Keep generated code/assets/ROM/saves/states/SDK/binaries ignored; do not close the issue while required acceptance remains incomplete.

Native smoke checkpoint (2026-11-02): base boot2400 and genuine doubles2850
passed instruction lockstep. All ten runtime processes exited0. Six CPU
compositions retained both complete player cards, foes and move/type/PP cards
at the requested sizes with private smoothing0/1. This is partial runtime
acceptance, not installation or a hardware/GPU coverage claim.

The arrow offset routes above are preserved source behavior, not evidence that
arrows exist. Native inspection found both player `arrowObj` pointers null;
the upstream `BattleHpBar_LoadResources` already loads resources without
creating/assigning arrow sprites. Keep this preexisting omission explicit.
Button highlighting and the separate active-Pokepic effect remain intact.
