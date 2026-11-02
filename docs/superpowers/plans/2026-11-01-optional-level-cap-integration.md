# Optional Level Cap Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement these tasks in order. Steps use checkbox syntax. The root owns fresh specification/quality reviews at milestones A, B and C. No parallel writers or standard build/native jobs are authorized by this plan.

**Goal:** Deliver the confirmed optional automatic Johto + first League + Kanto cap with classic four QoL features, modern flags0, in-game configuration, and complete player EXP producer coverage.

**Architecture:** Keep `include/qol_level_caps.h` and `src/qol_level_caps.c` frozen. Add one small game-owned save adapter, explicit field item wrappers, source-level producer hooks, and a second page inside the existing Options overlay. Persistent values use the audited existing slots416E/F without changing any save/packet structure.

**Tech Stack:** Existing C/Nitro SDK source and localized GMM resources; existing host C harness approach; matched-ROM static recompiler/native build pipeline.


## Frozen core contract and policy

Use the existing exact APIs: `Qol_GetLevelCap(badges,gameClear,defeatedEliteFour)`, `Qol_LevelCapConfigEnabled`, `Qol_LevelCapConfigValue`, and `Qol_LevelCapAllowedExp(enabled,oldExp,requestedExp,capExp)`. `QolLevelCap` contains `trainerId` and `level`; `TRAINER_NONE/MAX_LEVEL` means ordinary growth rules. The core resolves individual badge bits, uses original aces (Chuck31, Clair41), chooses lowest remaining leader, uses first-League42/44/46/47/50, and gives game-clear precedence over resettable League flags. It deliberately resolves while Off for prospective cap display. Add no second boss table or different progression algorithm.

Preserve all existing over-cap EXP and levels, including captures, trades/gifts/imports and preexisting daycare growth steps. Suppressed new EXP is discarded, not stored for later. Cap increases/disable permit new gains from that point. Do not modify generic Pokémon storage, level/stat recalculation, creation, evolution, or temporary facility scaling functions.

## Task1: explicit persistence and game-side adapters

**Files:** Modify `include/constants/vars.h`, `include/qol_config.h`, `main.lsf`; create `include/qol_level_cap_save.h`, `src/qol_level_cap_save.c`; create integration tests in `tools/qol/test_level_cap_save.py`. Do not change the frozen pure-core files.

- [ ] Rename the two unknown constant declarations unconditionally, not behind a feature flag and not as silent aliases:

```c
#define VAR_QOL_DAYCARE_BREEDING_PHASE 0x416E
#define VAR_QOL_LEVEL_CAP_CONFIG      0x416F
```

Document exact format at the declarations: config0000 Off/C701 On-schema1/anything else reads Off; phaseD100..D1FF means schema1 and low8 phase, other values uninitialized. These names remain reserved even in feature-disabled builds. Existing `SaveVarsFlags`, `NUM_VARS`, Options, PlayerProfile, Daycare and packet layouts remain unchanged.

- [ ] Add independent `#ifndef QOL_LEVEL_CAPS / #define QOL_LEVEL_CAPS QOL_MODS / #endif` to `include/qol_config.h`, alongside classic QoL switches. It must not depend on modern types, battle, or moves. Add compile-time guards for boolean flag, IDs416E/F, distinct persistent in-range IDs, `VAR_BASE==0x4000`, `NUM_VARS==0x170`, vars array size0x2E0, flags offset0x2E0, block size0x44C. Use the SDK-supported typedef-array assertion pattern if C11 assertions are unavailable. Root can place/link assertions in the adapter implementation.

- [ ] Add the following **new adapter API**. Include `save.h`, `pokemon_types_def.h`, `daycare.h`, and frozen core header as required; no existing struct expands.

```c
QolLevelCap Qol_LevelCapForSave(SaveData *saveData);
BOOL Qol_LevelCapEnabledForSave(SaveData *saveData);
void Qol_LevelCapSetEnabledForSave(SaveData *saveData, BOOL enabled);
u32 Qol_LevelCapLimitPlayerExp(SaveData *saveData, u16 species,
    u32 oldExp, u32 requestedExp);
BOOL Qol_LevelCapCanUseRareCandy(SaveData *saveData, Pokemon *mon);
u8 Qol_LevelCapAdvanceDaycarePhase(SaveData *saveData, DaycareMon *second);
void Qol_LevelCapResetDaycarePhase(SaveData *saveData);
```

`ForSave` constructs16badge bits by `PlayerProfile_TestBadgeFlag` over0..15; system `CheckGameClearFlag(Save_VarsFlags_Get(saveData))`; four named flag reads `Save_VarsFlags_CheckFlagInArray` form the existing core bit mask. Return `Qol_GetLevelCap` directly. Config reads/writes use only `Save_VarsFlags_GetVarAddr` and core config helpers. No host state/bridge.

`LimitPlayerExp`: check compile support and runtime enable first. Disabled returns requested unchanged without reading progression/growth tables. Enabled resolves cap; no-boss/MAX_LEVEL also returns requested. Otherwise obtain `GetMonExpBySpeciesAndLevel(species,cap.level)` and call frozen allowed-award helper with enabledTRUE. Return accepted delta only; never set mon data here. Callers retain original100 bounds.

`CanUseRareCandy`: feature-disabled returnsTRUE (let existing utility decide normal legality). With support enabled, already100 returnsFALSE; otherwise request `CalcMonExpToNextLevel`, read species/EXP, and require accepted delta to equal the positive full next-level request. This rejects an already-over-cap or inconsistent cached-level mon without rewriting it. Runtime Off preserves the original request and generic legality checks.

Phase helper behavior is specified in Task4. A feature-disabled build must perform **zero new reserved-variable or progression-state reads/writes** through every adapter: `ForSave` returns `{TRAINER_NONE,MAX_LEVEL}`, enabledFALSE, setter/reset no-op, limiter identity, CandyTRUE, and phase returns the original next-walk low8 from its supplied daycare steps without touching save slots. Compile out producer hooks/UI where useful so vanilla behavior remains byte-for-byte straightforward.

- [ ] Register BOTH `src/qol_level_caps.o` and `src/qol_level_cap_save.o` exactly once in `main.lsf`: inspection confirmed neither was registered before integration.
- [ ] TDD adapter harness: both compile flag values, synthetic save state and spy counters; zero reserved-slot access disabled; unknown config disabled; exact setter roundtrip; individual badge resolution; system-clear precedence after League reset; threshold species forwarding; no-boss identity. Preserve the existing core test suite unchanged. Later commands: `python3 -m unittest discover -s tools/qol -p 'test_level_cap_save.py'` and the existing core suite, expecting pass. These are future verification steps, not execution performed here.

## Task2: battle award integration and field-only Rare Candy

**Files:** `src/battle/battle_command.c`, `include/use_item_on_mon.h`, `src/use_item_on_mon.c`, `src/party_menu.c`, `src/party_menu_items.c`; new `tools/qol/test_level_cap_producers.py`; narrowly scoped guard normalization in `tools/qol/test_modern_me_first.py` if its protected command inventory compares this producer.

- [ ] In `Task_GetExp`'s `STATE_GET_EXP_START`, after participation/EXP Share/Lucky Egg/trainer/foreign-OT multiplication, read existing EXP as today, then limit **`totalExp` itself before `newExp += totalExp`**. Use game-side `SaveData_Get()` only on ordinary local EXP battles; guard `battleType & (BATTLE_TYPE_NO_EXP | BATTLE_TYPE_TUTORIAL)` so excluded/link/frontier modes do not read cap settings. This task already enumerates player party slots0/2, not enemy Pokémon; do not introduce a global NPC cap.

```c
u32 newExp = GetMonData(mon, MON_DATA_EXPERIENCE, NULL);
/* existing previous-gauge-progress calculation remains here */
#if QOL_LEVEL_CAPS
if (!(battleType & (BATTLE_TYPE_NO_EXP | BATTLE_TYPE_TUTORIAL))) {
    totalExp = Qol_LevelCapLimitPlayerExp(SaveData_Get(),
        GetMonData(mon, MON_DATA_SPECIES, NULL), newExp, totalExp);
}
#endif
newExp += totalExp;
```

Keep both original writes below the hook: active `ctx->battleMons[expBattler].exp = newExp` and `SetMonData(...EXPERIENCE...)`. The message already uses `totalExp`, so it displays the accepted amount. Keep `BattleScript_CalcEffortValues` inside the original live/non100 eligibility block even when accepted EXP becomes0. Do not add an early return that removes EVs. Existing `if(totalExp)` skips zero-gain animation/message and the rest of the state machine handles accepted multilevel gains, stats, moves and evolution normally.

- [ ] Preserve the precise Me First source contracts in `tools/qol/test_modern_me_first.py`. Its existing Tailwind helper allowlist and Wind additions dictionary (`:527-554`) demonstrate the correct pattern: define the **exact newly inserted `#if QOL_LEVEL_CAPS ... #endif` text**, require `current.count(capBlock)==1`, remove just that block once, then compare every remaining original Task_GetExp byte/token against the protected baseline. Do not exclude Task_GetExp, skip the whole EXP function, broadly strip arbitrary preprocessor text, or remove function inventory assertions. This plan adds **no new functions in battle_command.c**, so its function-name set must remain unchanged. If implementation chooses a new command-file helper anyway, permit only its explicit cap-owned name in the inventory subtraction and test that helper separately. Likewise normalize an exact cap header include only if a whole-file contract requires it; do not erase unrelated includes. Keep all existing Wind/Tailwind normalization cases and exceptional-damage protections intact. The currently inspected Me First inventory branch is centered on controller files; keep it intact and place the Task_GetExp normalization at its applicable producer comparison (or the new producer source-contract test), rather than weakening that existing controller guard to accommodate an unrelated file.

Add a negative regression for the normalizer: after removing the known cap block, a synthetic changed `BattleScript_CalcEffortValues`, cache assignment, message total, or level-up token must still fail the baseline comparison. Run the focused Me First module together with cap producer tests at milestoneA; do not wait for the full SDK build to discover a source-contract failure.

- [ ] Add explicit field-context item wrappers; leave all existing generic item functions untouched for Frontier and other copied Pokémon:

```c
BOOL CanUseItemOnMonInPartyField(SaveData *saveData, Party *party,
    u16 itemID, s32 partyIdx, s32 moveIdx, enum HeapID heapID);
BOOL UseItemOnMonInPartyField(SaveData *saveData, Party *party,
    u16 itemID, s32 partyIdx, u8 moveIdx, u16 location, enum HeapID heapID);
```

Each wrapper: if `itemID==ITEM_RARE_CANDY` and the adapter rejects that selected mon, returnFALSE; else delegate to the existing corresponding generic function. In disabled builds the added restriction is compiled out. This avoids changing the enormous generic item's existing healing, friendship and effect ordering. Include SaveData type in the header through the established save header.

- [ ] In `PartyMenu_HandleUseItemOnMon`, use the field usability wrapper only for the actual field `PARTY_MENU_CONTEXT_USE_ITEM` path; save comes from `partyMenu->args->fieldSystem->saveData` when fieldSystem exists. A copied/battle context or NULL fieldSystem keeps the generic call. Apply this predicate before the existing `Bag_TakeItem`, so rejected Candy is never consumed. Use the existing no-effect message/exit path.
- [ ] In `PartyMenu_ItemUseFunc_LevelUp`, use the matching field application wrapper under the same context predicate. If application unexpectedly returnsFALSE, do not print grew-to-level/stats/move success UI. This callback is reached only after the bag path consumed exactly one Candy; restore it with `Bag_AddItem(...,ITEM_RARE_CANDY,1,HEAP_ID_PARTY_MENU)`, print existing `msg_0300_00102`, set `partyMonIndex=PARTY_MON_SELECTION_CONFIRM`, set `itemUseCallback=PartyMenu_ItemUseFunc_WaitTextPrinterThenExit`, and return `PARTY_MENU_STATE_ITEM_USE_CB`. This is a defensive rollback, not a second consumption. Generic-context application retains original behavior. No story/config mutation can ordinarily occur between the two calls, but both entry points enforce the rule.
- [ ] Producer TDD: actual extracted Task_GetExp start case with stubs; accepted display and both EXP writes agree; EXP Share and all multipliers before clamp; active/inactive party recipients; zero EXP still awards EVs; excluded modes never read settings; disabled path same requested amount. Candy field usability/application rejects without EXP/friendship writes, item count unchanged; one below cap performs original level/move/evolution flow; direct `UseItemOnPokemon` used by Battle Castle remains uncapped.

**Review milestoneA:** adapters + battle/Candy pass focused host harnesses before adding daycare/UI. This is a code-review checkpoint within authorized work, not a new user-permission request.

## Task3: Pokéwalker accepted EXP and level-up friendship

**Files:** `src/application/pokewalker/pokewalker_stroll.c`, declaration in `include/application/pokewalker/pokewalker_app.h` (existing prototype at line442), producer harness.

- [ ] Change the single internally called `PokewalkerApp_AddStrollExp` signature to take explicit `SaveData *saveData` first; update its declaration and sole caller at `PokewalkerApp_ReturnStrollMon` to pass `app->saveData`. This is a C API change only; no packet/app persisted layout changes. It is clearer than a singleton when the real save is already present.
- [ ] Preserve clamping signed negative input to0 and original at-most-next-level limit. After that cap, pass species, old boxed EXP and the resulting positive request through `Qol_LevelCapLimitPlayerExp`. Copy boxed mon to output Pokémon even if accepted0, because the caller still needs a populated return mon. Set total to old+accepted and run existing level/stat calculation. Record old derived boxed level and set `leveledUp` from actual new level>old, not the pre-limit request. Apply `MonApplyFriendshipMod` only for that actual level-up.
- [ ] Keep `PokewalkerApp_AddStrollFriendship` at the caller unchanged: ordinary walking friendship is separate from level-up friendship and still applies at a cap. Incoming generated walker Pokémon in the `peerIdentity.hasWalkerMon` branch are acquisition and retain their original level/EXP.
- [ ] TDD: cap exactly reached, above cap zero acceptance, under cap partial stroll, negative input, input larger than next level, Off behavior, output mon copy at zero gain; no level-up friendship for suppressed award; ordinary stroll friendship and acquired walker mon branch unchanged.

## Task4: daycare accepted growth with an independent breeding phase

**Files:** `src/get_egg.c`, adapter module/header, producer harness. Do not change Daycare/DaycareMon/Mail layouts or padding, and do not add a second retrieval clamp.

- [ ] Implement `Qol_LevelCapAdvanceDaycarePhase(save,second)` so it runs **before** the current walk changes either parent's growth counter. It checks whether slot1 is occupied. If no second parent, return0; reset active phase to0 via reset helper if needed. For an occupied second parent:

  - Read416E and runtime enable only inside feature-enabled adapter code. If phase tag is alreadyD1, take its low8 previous phase; increment modulo256 and saveD100|newphase. Do this whether runtime cap is On or Off, because a previously frozen growth counter no longer matches breeding time.
  - If tag is unknown and runtime cap is On, migrate previous phase from `(u8)DaycareMon_GetSteps(second)` and increment/save once.
  - If tag is unknown and runtime cap is Off, return `(u8)(oldSteps+1)` and **do not write416E**. This preserves wholly untouched original timing/saves until the feature is first used.

`Qol_LevelCapResetDaycarePhase(save)`: writeD100 only if runtime cap is On or416E already has the recognizedD1 tag; otherwise no write. Its compile-disabled form never reads save slots. Reset does not alter any parent's EXP or steps.

- [ ] `HandleDaycareStep`: save `breedingPhase = AdvanceDaycarePhase(fieldSystem->saveData,second)` before the per-parent increment loop. For each occupied parent, request exactly1 growth EXP against `base boxed EXP + existing steps`; use saturated addition for this *calculation* if old pending sum exceedsu32, but never rewrite existing steps. `accepted = LimitPlayerExp(save,species,pendingTotal,1)`; add only accepted steps. Continue incrementing `monsInDaycare` for every occupied parent, including frozen ones.
- [ ] In the existing two-parent/no-egg breeding condition, use `breedingPhase` instead of casting slot1 growth steps. Preserve `phase==255`, compatibility calculation, RNG call sequence, GenerateEggPID and call notification exactly. The phase continues advancing while an egg already waits, just as original growth steps did; egg hatch cycle/friendship step machinery below remains unchanged.
- [ ] `Save_Daycare_PutMonIn`: store `availableSlot` once, then copy to it as today; when it is slot1, reset the independent phase **after** deposit. New slot1's growth steps are0, so phase0 matches original semantics.
- [ ] `Save_Daycare_RetrieveMon`: after current retrieval/compaction, call reset helper. Either withdrawal leaves at most one parent and slot1 empty, so this cannot discard an active two-parent clock. Compaction continues copying all original mon/steps as today; no special metadata follows a parent because the independent phase belongs only to the current slot1 breeding clock. New second deposit resets it again.
- [ ] Keep withdrawal, `GetDaycareUpdatedLevel`, `DaycareMon_CalcLevelGrowth`, price and stat preview unchanged: all already derive from the accepted stored steps. Preserve preexisting pending steps even when their implied level exceeds a newly enabled cap; freeze subsequent increments and retrieve their existing implied EXP intact. Never clamp retrieval to the new lower threshold, and never store suppressed new steps for later release.
- [ ] TDD exact sequences: original Off/untagged saves same phase and RNG timing; On migrate at oldsteps254→roll255,255→0 no roll; reach cap then256more walks still rolls breeding; waiting egg does not pause phase; disable after freeze advances both accepted growth and independent phase without restoring suppressed growth; cap increase resumes1pernewwalk; old pending over-cap steps unchanged; save/reload; deposit slot1, retrieve slot0 with compaction, retrieve slot1, new second deposit; all preview/price/retrieval calculations agree. Test huge pending sum never grants extra capped growth. No test should claim a vanilla-ROM downgrade preserves exact breeding phase: the old ROM derives phase from growth steps, as documented.

**Review milestoneB:** all producer hooks plus daycare state transition harnesses pass. Audit modified calls and data layouts before starting UI; no SDK/native run until the SDK owner releases the lane.

## Task5: compact second page inside existing Options overlay

**Files:** `src/options_app.c`, `files/msgdata/msg/msg_0045.gmm`, `tools/qol/test_level_cap_options.py`. No new overlay, menu framework, BG assets, or persistent Options fields.

### Concrete window/layout design

Keep original first page: six24px rows, existing values, border BG, text-speed preview, frame selector, and confirm/quit buttons. `MENU_ENTRY_6` remains confirm/quit; `currentMenuEntryId` stays0..6, so its3-bit field needs no change.

Add transient fields under `QOL_LEVEL_CAPS` to `OptionsApp_Data`: page0/1, remembered first-page row, cap focus row0or6, pending capBOOL, one `MessageFormat *` and two reusable `String *` buffers. No stored save/packet type changes. Add `Window pageHint` after existing windows and change window union/asArray length5→6 **only when enabled**.

`OptionsApp_SetupWindows` adds a header hint window on MAIN_1 at tilex14,y0,width17,height3,palette13,baseTile**0x274**. This is the first free tile after confirm's0x25F+7*3; end0x2A7 is below the1024tile BG limit. Existing window tile bases remain unchanged. The touch area is screenx112..247,y0..23. Page0 says `X: CAPS`; page1 says `X: OPTIONS`. X is unused by the existing Options input logic. Do not rely on L/R, because L=A button mode remaps/hides shoulder keys (`src/system.c:346-350`). Existing96px title window can hold `LEVEL CAPS` on page1. Existing selectedOption window remains x8,y24,size240x144.

On page1, hide only MAIN_2's original six-row artwork and MAIN_0 border via `ToggleBgLayer`; preserve their tilemaps for return. Hide sprites0..6 (choice highlights/frame arrows). Keep confirm/quit sprites7/8. Fill selectedOption with palette color5, which existing Instant text buttons already use as opaque background. Change only the existing `speedButtonColors` palette-initialization guard in `OptionsApp_SetupWindows` from `#if QOL_INSTANT_TEXT` to `#if QOL_INSTANT_TEXT || QOL_LEVEL_CAPS`, so cap-only builds initialize colors3..5 too; retain the color values and every actual Instant-button draw/input guard unchanged. Draw cap label at local(4,5), Off choice at(120,5), On at(176,5); current pending value has the existing Instant-button-style opaque highlight and text colors. Draw `NEXT BOSS` at(4,37), expanded localized `trainer-name  Lv. N` at(4,61), and a short `CONFIRM TO APPLY` hint at(4,109). If core result isTRAINER_NONE, show `NO CAP` instead of looking up trainer0. PendingOff still shows the prospective automatic next boss, with the toggle visiblyOff.

Screen touch choices: Off x128..171,y26..46; On x184..227,y26..46. Both fit within the existing240px window. Header hint is touchable from either page, so the second page is discoverable and usable with every existing button mode.

### Exact lifecycle and handler changes

- [ ] `OptionsMenu_Init`: load `pendingCap` from `Qol_LevelCapEnabledForSave(SaveData_Get())`, page0, remembered row0; allocate formatting buffers under the feature flag. Do not write save config while opening or previewing. `SaveData_Get` is the game-owned singleton already initialized before this overlay; no OptionsApp_Args expansion is needed.
- [ ] `OptionsApp_LoadMenuEntriesData`: leave all existing strings/values untouched. No seventh real row inserted; no renumbered message indices. `OptionsApp_SetupInterfaceText` keeps page0 rendering and draws new pageHint.
- [ ] Add small static helpers `OptionsApp_SwitchPage`, `OptionsApp_DrawCapPage`, `OptionsApp_DrawPageHint`, and `OptionsApp_HandleCapTouch`. `SwitchPage` remembers/restores main row, uses cap row0 initially, toggles BG/sprite visibility and redraws. Returning to page0 calls the existing `SetupInterfaceText` to restore its transparent window pixels and values, restores MAIN_2 and appropriate border, and restores sprites0..6 except sprite0 remains hidden under `QOL_INSTANT_TEXT` as today. `SetActiveButtonsXPosition` runs after return. Do not reload graphic resources or recreate sprite renderer on every page flip.
- [ ] `OptionsApp_HandleInput`: **before** legacy touch-index switch, consume X (PAD_BUTTON_X) or a new header-hint touch as a page flip and return, preventing the same event changing a first-page option. Page1 routes touch directly to the two cap rectangles or the existing confirm/quit rectangles; it never interprets original text-speed/frame hitbox indexes. Confirm/quit touch uses the same exitChoice, menu-input state and sprites7/8 animation logic as today.
- [ ] `OptionsApp_HandleKeyInput`: on cap page when row0, left/right chooseOff/On and A toggles pending; redraw cap page, play existing select sound. Up/down toggle row0↔MENU_ENTRY_6, rather than modulo7 through invisible rows. When row6, retain existing left/right confirm/quit selection and A confirmation logic. B on either page remains whole-menu cancel (`exitChoice=2`). Page flip is navigation only; it never confirms or cancels and pending value survives switching back and forth.
- [ ] `OptionsApp_UpdateSelectionHighlight` and `OptionsApp_HideBorderOnConfirmRow`: on cap page keep MAIN_0 off; still update sprites7/8 for confirm/quit selection and redraw cap toggle focus as needed. First page continues existing behavior. `OptionsApp_SetActiveButtonsXPosition`: return immediately on cap page so hidden first-page sprites are not accidentally indexed as cap choices. Existing update-menu-entry functions should only render first-page values; the cap page owns its own pending state.
- [ ] `OptionsMenu_Exit`: in existing `exitChoice==1` branch, after original six setting writes, call `Qol_LevelCapSetEnabledForSave(SaveData_Get(),pendingCap)`. On cancel do not touch416F. Existing sound/button/text preview rollback remains intact. Confirm on either page commits all edited original settings and cap setting together; cancel on either discards cap while following existing original preview rollback.
- [ ] Setup allocates message formatter/strings, renders hint with existing windows; Free deletes formatter/strings once and existing window loop frees the sixth window. Phase migration never occurs in Options preview/confirm; it belongs to actual daycare steps/deposit/reset.

### Localization and boss-name source

Append GMM rows60..69 with existing IDs0..59 unchanged. Exact English text mapping:60 `LEVEL CAPS`,61 `LEVEL CAP`,62 `OFF`,63 `ON`,64 `NEXT BOSS`,65 `NO CAP`,66 `CONFIRM TO APPLY`,67 `X: CAPS`,68 `X: OPTIONS`,69 `{STRVAR_1 0, 0, 0}  Lv. {STRVAR_1 52, 1, 0}`. Page0 reuses existing title row0. Use generated message constants from the normal resource pipeline, never hand-edit generated msg headers. Text is source-localized in the existing US English GMM, with no hardcoded English trainer names or per-boss label table.

For row69, `BufferTrainerName(format,0,cap.trainerId)` uses existing trainer-name message bank729 (`src/message_format.c:306-313`); `BufferIntegerAsString(format,1,cap.level,3,PRINTING_MODE_LEFT_ALIGN,TRUE)` fills level; `StringExpandPlaceholders` formats into reusable output. Resolve cap via `Qol_LevelCapForSave` regardless of pendingOff so player can see the next rule. This gives proper names including Lt. Surge, and no duplicated story data.

- [ ] UI harness covers state/input transactions (X/header flip, pending value preserved, hidden row navigation impossible, L=A mode still reaches page with X, cap touch does not change speed/frame, B and Quit cancel from both pages, Confirm commits once, disabled builds no new windows/settings access). Layout checks assert tile ranges nonoverlapping and touch rectangles inside the rendered controls. Existing Instant four-button tests continue to pass.
- [ ] Required runtime UI check later: controller-only, keyboard and touch; first-page Instant selection and frame arrows still correct; page flip redraw has no old-art bleed; long boss name fits; no-boss state; Confirm/Quit animations; text-preview rollback; normal save/reload persists cap. A source harness alone cannot validate sprites/BG composition.

**Review milestoneC:** review Options resource/input/layout diff separately from gameplay hooks, then run approved private runtime checks once root releases build lane. No new product approval question is required.

## Task6: focused acceptance and classic build delivery

**Files:** create `docs/LEVEL-CAPS.md` for player behavior and the save-format note. Do not edit the separate controls worker's `docs/QOL.md`. Normal build scripts change only if a real integration requirement arises. No native host gameplay setting or bridge file is expected to change.

- [ ] Run focused new adapter/producer/daycare/UI tests plus existing pure-core and baseline QoL suites once after integration. Include `test_modern_me_first.py` and preserve its exact-source/function-inventory guards as specified in Task2. Add only meaningful state-transition/integration cases; do not rewrite pure-core tests to mirror unchanged code.
- [ ] Build feature support0/1 against modern flags0; focused compile coverage can also exercise independent modern combinations without installing them. Verify original saved structure/packet sizes. Use audited tagged variable formats; unknown config remainsOff.
- [ ] After root releases SDK lane, build with `QOL_MODS=1`, `QOL_MODERN_TYPES=0`, `QOL_MODERN_BATTLE=0`, `QOL_MODERN_MOVES=0`, cap support enabled/runtime defaultOff. Preserve accepted Wind/Gen IX source checkpoint but keep incomplete Gen IX uninstalled. Regenerate `qol-layout.json` and matching native code through existing `scripts/build-qol-native.sh` for this classic source selection; matching ROM, linked symbols and native output must agree.
- [ ] Use only old private validation copies for runtime saves. Exercise actual battle cap crossing/move learning, zero-gain EVs, Rare Candy no-consumption, daycare freeze plus breeding, first-League cap advance/reset, game-clear→Kanto transition, all16badges→ordinary100, Off/save/reload. Compare interpreter and recompiled results on matching artifacts. No recompiler/runtime/CPU changes are proposed; if those components change, obey native AGENTS mandatory full lockstep gate.
- [ ] macOS native smoke and Linux/Steam Deck build/smoke where available; report any platform not exercised. Ordinary emulator smoke proves game-side portability. Installation/delivery must use the explicitly authorized classic four-QoL path and preserve current real saves, ROMs, metadata and rollback artifacts.

No unresolved product choice remains for this integration plan. Remaining technical verification is actual code integration and runtime UI/producer behavior; nothing in this research claims those gates already passed.

## Recorded test-first preparation and work ownership

- [x] Read the approved design/ownership audit and exact integration specification.
- [x] Add host-only `tools/qol/test_level_cap_save.py`; compile the complete frozen core with synthetic SDK edges and an explicit uncapped fallback until the adapter exists.
- [x] Run save tests before production edits: 6 tests, 5 semantic assertion failures, 1 disabled-support zero-access pass.
- [x] Add `tools/qol/test_level_cap_producers.py`; execute the actual extracted battle START case, full Pokéwalker producer, and full daycare walk producer, plus explicit missing field-wrapper fallback.
- [x] Run producer tests before production edits: 12 tests, 6 semantic C failures and 1 precise missing-hook source guard failure; 5 passes including Off/exclusions/disabled behavior and normalizer mutation detection. No compiler failure remains.
- [x] Add `tools/qol/test_level_cap_options.py`; execute actual input and exit functions with graphics edges stubbed.
- [x] Run Options tests before production edits: 7 tests, 6 failing tests (7 failure reports including two confirmation-page subtests); disabled-support passes. Failures prove absent page navigation, pending state, commit and localization.
- [x] Root grants phase2 after accepted Wind commit `c7ea0fdd6` and pure-core commit `3b6484aa8`. The core C/header/tests remain frozen.
- [ ] Finish milestone A: save adapters, battle and field Candy, focused host/sanitizer evidence and genuine focused SDK compile if needed; release frozen hashes for root's fresh specification then quality review.
- [ ] Finish milestone B: Pokéwalker and daycare including deposit/withdraw transitions; release frozen hashes for fresh reviews.
- [ ] Finish milestone C: Options/resources and public behavior/save-format note; release frozen hashes for fresh reviews.
- [ ] Root performs isolated classic all-modern-flags-0 paired build, resource/link/native/runtime checks and authorized installation. This worker makes no playable/install claim.

This worker owns cap producer/Options sources and the three new host modules. A separate worker owns battle input, HP bars, both native frontend copies, controls tests/docs and native changelog. The root owns index/stage/commit/push, broad suites, standard ROM/native build, emulator/runtime and live files. After phase2 authorization this worker may exclusively run serialized focused SDK C/resource checks into ignored validation paths; no standard accepted Wind outputs may be replaced.

## Milestone A acceptance and B implementation evidence

The root accepted A after fresh specification and quality reviews (30 host tests each, no SDK attempts, all 14 frozen hashes unchanged). The implementation worker separately collected 16 ASan/UBSan checks and ten genuine SDK C compilations for support0/1 with modern flags0. These are focused compile/host gates, not a linked build or runtime acceptance.

Before B production edits, the existing walker/daycare semantic failures remained reproducible; additional tests showed missing level100 output population and missing retrieval-phase reset. B now passes 19 producer tests, including actual input functions, phase migration before growth, continued breeding with a waiting egg, cap increase/disable without banking, huge pending totals, save/reload, withdrawal/compaction/redeposit and original preview/price consumers. Exact hashes preserve the unchanged retrieval/preview/price and ordinary walker friendship functions, and normalize only the new explicit save argument at the sole walker call.

B modifies only `src/get_egg.c`, `src/application/pokewalker/pokewalker_stroll.c`, its app declaration, producer tests and this plan. The A adapter phase helpers are reused unchanged. All SDK compiler invocations remain serialized and write private temporary objects. Fresh expanded-scope specification/quality review is required before Options implementation.

Milestone B verification: 36/36 focused host checks and 36/36 ASan/UBSan checks passed with zero skips and SDK entrypoints blocked before test imports. Four genuine serialized SDK C compilations passed for the walker/daycare units with support0/1 and modern flags0. No standard build/link/native/emulator was invoked. Source is now frozen for the root's fresh B specification then quality reviews.

## Milestone B acceptance and final Options integration

The root accepted B after fresh specification and quality reviews, each with 41 passing host checks, zero skips/SDK attempts and all 17 frozen hashes unchanged.

C adds the compact Options page, header touch/X navigation, pending-only editing, existing Confirm/Quit transaction, localized trainer-name formatting, guarded transient buffers/window cleanup and cap-only palette initialization. Eleven host UI tests cover actual input/exit/init/switch/highlight/renderer functions, lifecycle allocation/freeing, first-page sprite/BG restoration, no trainer0 lookup, tile allocation and the support/Instant matrix. Actual composed visuals remain a root-owned runtime gate.

### Reproducible imported messages (approved scope correction)

The imported GMM and generated message header are ignored assets. Stock rows0..59 all belong to the original game:56..59 are WINDOW TYPE17..20, while Instant text creates its label in C. The tracked `tools/qol/options_messages.py` therefore preserves the entire stock60 prefix byte-for-byte and appends/removes only the exact owned caps60..69 tail. It resolves literal `CLI_DEFINES` including the `QOL_MODS` default, preserves unchanged-file mtimes, and rejects partial, changed, nested or unknown tails before any write. Tests first recorded semantic RED against the previous no-preparation behavior.

`scripts/build.sh` runs preparation before make. The exact `Makefile` prerequisite for `$(BUILD_DIR)/src/options_app.o` ensures the existing message header→binary→GMM dependency chain runs even in a fresh build directory without C depfiles; no other source dependency is weakened. No original game content is force-added.

Real encoder checks cover cap support0/1 × Instant0/1 with all modern flags0. Every case uses key0xB90F, round-trips, is idempotent, and restores exactly the original stock source on support disable. The stock re-encode is byte-identical to the imported message binary. Stock prefix SHA-256: `5715e98ffd3a6d5dee85f5f92a280e739d34a64b8ea065c34d297632ec83a9c8`. Four initial genuine overlay SDK compiles passed against a private70-row header; a second focused matrix verifies independently prepared60/70-row headers. No standard ROM, linked output, native generation or emulator is run by this worker.

Root-owned remaining acceptance: isolated classic all-modern0 paired build, linked resource verification, controller/keyboard/touch composition, save/reload and actual battle/Candy/daycare/walker behavior, then authorized installation preserving the live save/ROM rollback state.
