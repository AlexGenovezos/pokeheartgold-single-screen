# Gen IX Sharpness and Soul Dew presentation (D2b)

Approved source contract, based on accepted Me First routes at
`d37566880c390cf485f4d286a81ba174a5e4dff9` on `qol-mods`.
This slice adds Sharpness/Gallade and the deferred Soul Dew description. It does
not complete the full Gen IX ruleset. SDK/resource integration, matching native
fixtures and UI acceptance belong to root after fresh specification and quality
reviews. No installation, real ROM/save changes, roster/story expansion or new
move-learning rows are authorized by this slice.

## Classification and reference contract

`Qol_IsSlicingMove(u16)` executes a switch in `src/qol_moves.c`; it never interprets
contact, native King's Rock bit0x20, names or contest bytes. It accepts precisely
these twelve original IDs under every flag combination:

| IDs | Moves | Native category |
| --- | --- | --- |
| 15,75,163,210 | Cut, Razor Leaf, Slash, Fury Cutter | Physical |
| 314,403 | Air Cutter, Air Slash | Special |
| 332,348,400,404,427,440 | Aerial Ace, Leaf Blade, Night Slash, X-Scissor, Psycho Cut, Cross Poison | Physical |

Only with `QOL_MODERN_MOVES=1`, it also accepts536 Sacred Sword (official533),
537 Razor Shell (official534), and898 Aqua Cutter (official895), all Physical.
All other u16 values are false. This includes unsupported slicing moves, engine
placeholders468..470,65535, Champions-only232/306/337/421 and Dire Claw.
Sacred Sword is already part of the accepted72 supported later moves; this slice
changes neither their data nor the336 learning rows/237 species.

Pinned references: pokeemerald-expansion
`c460a8661dfa0598ae25d42a968c690ecbf489c6` (moves `.slicingMove`, ability metadata,
BP handling); Showdown `5b01be81011ec12efa25dcfff49ea279a6029d6f` (slicing flags,
Sharpness priority19,1.5 factor, empty ability flags). Cached Showdown82f129e
moves/abilities bytes match that newer accepted pin. Profile target_generation9
and champions_changes:false remain unchanged; profile ability292 maps to242.

| Reference | SHA256 |
| --- | --- |
| expansion moves_info.h | 31c841954be8ca3f24b48c49dc447cd90678c9530045f7c43772dcaea95ade1f |
| expansion abilities.h | c3b041279967171e55b55b8bd5fcd7d3c904cdf93120736cb98d211d331c97be |
| Showdown moves.ts | 43b516fdc01721f53f01de555479dd3d248e5e29d2a6f5072a7bd4a3585a5027 |
| Showdown abilities.ts | e942ef6a75cdd50095f6b68c27e772ea91f2202714a30b04539ff17b7b93c065 |

Local reference audit: `python3 .local-tools/validation/check-sharpness-references.py`;
output `.local-tools/validation/sharpness-reference-proof.json` validates all
four hashes, all fifteen memberships, special categories, the five excluded
Champions claws, priority, factor and profile generation flags.

## Shared numerical event

`ABILITY_SHARPNESS=242` joins `Qol_ModernBasePower` only under modern battle.
Its6144 factor follows Iron Fist/Reckless23 and precedes Dry Skin17. The existing
active attacker snapshot owns the boost. Suppression disables it; defending
Mold Breaker cannot ignore it; target Sharpness supplies no defensive effect.
There is no new state, RNG, message or immunity event.

The collector preserves zero/status power, explicit overrides, intrinsic Fury
Cutter multipliers, wide Q12 products, half-up modifier chaining, masked
half-down application and valid-power minimum1. Existing stat/type/Normalize,
item suppression, critical, burn, screen and knowledge-write owners remain.
Public compatibility calls and actual AI receive Sharpness from that same
collector. Me First still requires explicit ordinary-command provenance plus
local eligibility; ambient flag/count state never grants it to public/AI paths.
Default and Raw command routes combine Sharpness, Me First and Helping Hand once.

Literal boundaries:

- Air Slash75 + Sharpness6144 ->112.
- 75 + Sharpness + Helping Hand, combined9216 ->169 (sequential floors168).
- L50/SpA100/SpDef100, neutral/no STAB, that169 BP ->76 base damage.
- 75 + Sharpness +20% type item4915 + Helping Hand: chain7373 then11060 ->203.
- Explicit41 + Sharpness + Me First + Helping Hand: group13824 ->138
  (sequential floors136).

The ready-plan202 expectation for the20% item case was an exact-rational-only
mistake, independently confirmed with root. Exact2.7 gives a half tie202.5,
but the pinned Q12 approximation11060/4096 yields202.5146484375, so the real
masked half-down result is203. The established Q12 implementation is preserved.
No simultaneous Technician/Sharpness holder is used as an attainable case.

Confusion, Future Sight, switching and AI keep their accepted public projection
contracts. Beat Up, fixed/OHKO/returned damage and delayed lifecycle remain
separate existing owners. Wind/Gas/Tailwind, final modifier groups and the other
previously documented modernization limits remain deferred.

## Gallade and persistence

Only after the numerical green gate, modern battle enables supported242 and
Gallade475's personal pair[80,242]. Original personal.json is unchanged and
contains duplicate[80,80], not[80,0]. The read adapter maps only species475,
form0, stored80, odd personality to242. Even80, zero, already242, custom choices,
other species and nonzero forms are preserved on reads. This never writes the
encrypted core or checksum. Native constructors and explicit ability-update
lifecycle still select standard slots by personality parity.

The host storage harness executes all three real personal loader hooks, the
actual constructor, native update, actual ability getter branch with real
GetBoxMonData/encryption/checksum/lock/permutation functions, and the complete
BattleSystem_GetBattleMon consumer. Unrelated constructor/stat/presentation
edges are stubbed. It checks all256 stored ability bytes, both PID parities,
32 block permutations, native no-ability battle modes and read-byte preservation.
Read-adapter controls cover all nonzero u8 forms; the native encrypted form field
retains its original width. Breeding/evolution/form/stat sources and consumers
are guarded unchanged against accepted d375; no full native breeding/evolution
session is inferred from those source contracts.

NUM_ABILITIES remains123, Easy Chat ability count remains124, and byte fields,
MoveTbl16,468-entry legacy move table, public damage ABI, save/context/packet
layouts and move counts do not grow. All three flags remain independent and
default off: battle-only exposes Sharpness for original slicing moves; moves-only
classifies the three later moves but gives no ability bonus or Gallade mapping.

## Resource owners and composition

`ability_descriptions.py` encodes sparse IDs130,172,242 in banks720/721/722.
Each becomes exactly243 rows. Every unsupported gap, including240/241, is ` -`.
Original0..123 and existing130/172 survive, apart from already-owned modern722
replacements. Full source bytes, original124 encoded rows and original keys
(720:7280,721:50258,722:26692) are guarded. Missing/count/key/row/source drift and
repeated transformation fail; NARC names and unrelated members are preserved.
Sharpness/SHARPNESS are the two names; the two-line description is:

```text
Powers up slicing moves
by 50%.
```

Font0 checks retain the existing149px summary bound. Actual BufferAbilityName
executes with242; Summary and battle-party722 consumers and unchanged Easy Chat
bounds are covered. No summary/window/name buffer growth is introduced.

Soul Dew's source `msg_0221.gmm` remains unchanged. The new
`soul_dew_resources.py` owner validates its source SHA256
`72a2c890304ebcab65f70d487423e402572301ec208936888061db5ff137748d`,537 rows,
key24316, exact original225, and entire encoded original SHA256
`d5504272b9fb1fa8bd735266ea630a2a6e42e038415d4716d0eabc2019db5a01`.
It derives the exact accepted post-Snow bank using the validated original plus
Snow's221 rows282/334 and the existing encoder. It then requires byte equality
for the entire incoming bank. Only225 changes; the other536 incoming rows, key,
NARC names and members are preserved. Original/pre-Snow input, duplicate
transformation, missing bank, source/count/key/row drift all fail closed.
No compiler or archive generation runs at import.

`make_modern_rom` calls this owner in the battle-only branch, after Simple/Snow
and before extended moves, reading the accumulated replacements. Snow's whole
original-bank guard remains unchanged. New text:

```text
LATIOS or LATIAS: boosts
Psychic- and Dragon-type
moves by 20%.
```

The63-character text has font0 widths137/137/73px (all <=149) and fits the
existing130-character String. Item225 mechanics already modernize the current
Psychic/Dragon move type, both categories, for original/base Latios/Latias,
including Frontier; no special stat boosts remain under modern battle. Bank221
is unchanged when battle is off regardless of moves/types. Actual message
composition runs all eight flag outputs with script compilation edges isolated;
root still owns the complete SDK integration and in-game UI fit gate.

## Verification ledger and commands

RED evidence was captured before each production behavior change:

- `sharpness-red.log`: missing classifier declaration assertion plus actual
  CalcMoveDamage numerical failures for242; no classifier compiler failure is
  counted as a semantic RED.
- `sharpness-clean-baseline-red.log`: actual accepted d375 formula/commands,
  four methods/all eight flags, exactly16 intended modern numerical failures,
  zero legacy failures, zero compiler errors.
- `sharpness-storage-red.log`: modern pair and encrypted getter expectations fail.
- `sharpness-resource-red.log`: ability bank length173 !=243.
- `soul-dew-red.log`: requested resource owner is absent.
- `sharpness-source-bytes-red.log`: newline byte drift was incorrectly accepted;
  the resource guard now checks bytes before decoding.

Focused green commands/logs include:

```sh
PYTHONPATH=tools/qol python3 -m unittest test_modern_sharpness -v
PYTHONPATH=tools/qol python3 -m unittest test_modern_cursed_body.ModernAbilityStorageTests -v
PYTHONPATH=tools/qol python3 -m unittest test_ability_descriptions test_soul_dew_resources -v
PYTHONPATH=tools/qol python3 .local-tools/validation/replay-sharpness-red.py
PYTHONPATH=tools/qol python3 .local-tools/validation/run-sharpness-host.py
PYTHONPATH=tools/qol python3 .local-tools/validation/run-sharpness-sanitizers.py
```

The explicit host driver starts with accepted D2a2's120-method command, adds
Sharpness/Soul Dew/ability/storage/moves/ROM/learnset classes, and replaces
battle_scripts.compile_battle_script and battle_script_tools with failures
before importing tests. It enumerates the seven permitted NextMoveEffectTests
methods individually; its mixed SDK method is excluded. Unexpected skips fail.
SDK classes and game/ROM/native builds are excluded. Routing mocks now name
Soul Dew (Snow/Soul use one patch.multiple where needed to remain below Python’s
20-static-context limit); three AI source factories remove the standalone classifier before
including its full production translation unit, so the real function is linked
exactly once. The initial162-method run exposed those two remaining duplicate
factory sites; focused corrected checks pass before the final sweep.

The38-method ASan/UBSan driver covers9 Sharpness,3 storage,14 Me First,11 BP
and the expanded actual type-preview test. Address/undefined sanitizers,
fno-sanitize-recover and halt_on_error are active; detect_leaks=0 is required by
this macOS toolchain. The unsupported detect_leaks=1 environment attempt is kept
as `sharpness-sanitizers-work.log`; no leak-check result is claimed.

Final collection:

| Gate | Result | Evidence under `.local-tools/validation/` |
| --- | --- | --- |
| Explicit guarded affected host suite |164 methods,221.926s, no failures/errors/skips | sharpness-host-final-green.log |
| Additional updated routing owners |4 methods,0.011s, no failures/errors/skips | sharpness-routing-owners-green.log |
| Address/undefined sanitizer suite |38 methods,104.827s, no failures/errors/skips | sharpness-sanitizers-green.log |
| Latest focused Sharpness sanitizer rerun |9 methods,22.330s, no failures/errors/skips | sharpness-sanitizers-final-focused-green.log |
| Accepted d375 numerical replay |4 methods,16 intended modern failures,0 legacy/compiler failures | sharpness-clean-baseline-red.log |
| Corrected AI fixture assembly |2 methods,2.735s | sharpness-fixtures-green.log |
| Whitespace and test-module syntax | `git diff --check` and all QoL test AST parsing pass | final freeze check |

`sharpness-frozen-hashes.json` records every changed/new source, test and document,
plus exact driver/log hashes. The source writer releases ownership at that freeze;
no edits are allowed during fresh specification and quality reviews. No SDK lane
was acquired or used. Root must complete the full host/SDK integration gate for
this resource-pipeline change, then paired matching ROM/native builds and native
ability/damage/summary/Soul Dew bag fixtures before integration. Focused host
checks do not replace those gates. The installed app, real ROM and real save
remain untouched by this worker.


## Root integration acceptance

Both fresh independent reviews passed. Specification independently exercised22
focused methods in42.362s plus8 routing checks in4.988s; quality exercised22
in41.290s plus10 routing checks in6.803s. The complete319-test host/SDK suite
passed in1058.774s, with no failures, errors or skips
(`sharpness-full-suite.log`). The serialized matching SDK ROM/resource/layout
and native build passed (`sharpness-paired-build.log`). Built resources retain
899 move members/scripts,304 subscripts,284 effects,830 message banks and1285
battle messages; ability banks720/721/722 have243 rows. Bank221 retains537
rows/key24316, new Soul Dew225 and Snow282/334.

Fresh copied-save constructor boots observed original stored80 mapping to
Sharpness242 for odd-PID Gallade and staying Steadfast80 for even PID. Six
controlled data-only battle fixtures passed: Sacred Sword61 versus control41,
Air Slash51 versus control35, suppressed Sharpness Air Slash35, and non-slicing
Earthquake46. All used level50/stat100 neutral/no-STAB fixtures, not natural
species stat claims. Sword/Earthquake retained18 RNG calls/end2764480230 and
Air Slash19/end4175436897 from seed12. Each1700-frame comparison matched every
ARM9 instruction,10200 total, with zero interpreter fallbacks, guard failures
and overlay evictions (`sharpness-native-green-proof.json`).

Root visually accepted fresh Gallade Summary screens showing Sharpness with
its50% description and the even-PID Steadfast control, plus the new three-line
Soul Dew20% Psychic/Dragon description without clipping. All41 frozen source,
test, document and evidence paths matched before these doc-only acceptance
edits. Ten unique validation saves and three tested artifact hashes matched;
production/test hashes must still match after these edits. Source-only landing
leaves the installed four-QoL app, real ROM and real save unchanged. Full Gen IX
completion still requires the remaining mechanics/data/access milestones.
