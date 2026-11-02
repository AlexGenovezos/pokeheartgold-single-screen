# Gen IX Me First ordinary-command routes (D2a2)

Approved bounded follow-up to D2a1, based on
`25716c38fdd369c03fa17b50fa294c640c363107` (`qol-mods`). This phase changes
Me First's numerical owner for ordinary commands. It does not complete modern
battles, enable a build flag, install a game, or change the roster/story/save.

## Contract and implementation

The former `CalcMoveDamage` body is the single game-owned
`Qol_CalcMoveDamageInternal` formula. Its unconditional private signature adds
`QolDamageOrigin` and a local `BOOL meFirstEligible`. The private
`include/battle/qol_damage_internal.h` defines compatibility origin0 and ordinary
command origin1, plus worker/predicate declarations. The unchanged public header
and original public function signature remain; its thin wrapper always supplies
compatibility/FALSE. There is no formula copy, signature macro, encoded argument,
new context/monster/save/packet field, or persistent side channel.

`DamageCalcDefault` is the sole ordinary-command gateway. Under
`QOL_MODERN_BATTLE`, it passes ordinary origin and a pure predicate over the
existing attacker's flag/count and context total. The worker only accepts the
event when both ordinary origin and the local eligibility input are true; it
never reads ambient Me First state or identifies provenance from current damage,
selected move, current move ID, or an override. Called ordinary moves therefore
use the copied `moveNoCur` normally. Both CalcDamage and CalcDamageRaw use this
gateway; Raw is an ordinary formula without the existing range roll.

The predicate uses signed64 arithmetic:

```c
s64 localCount = (s64)count - (total == count);
return flag && (s64)total - localCount < 2;
```

Future counts preserve the original negative-delta eligibility. No new lower
bound is imposed. Pure malformed-counter tests include INT_MIN/MAX safely in
this predicate only. Corrupted extremes that overflow the unchanged native
normalization/expiry arithmetic are unsupported; sanitizer execution never runs
that old lifecycle with overflowing inputs.

Me First chains6144 at BP priority12, after item/species15 and before Helping
Hand10. The existing intrinsic-power/override/Technician prerequisites and D2a1
Soul Dew owners remain. The old late `damage*15/10` is disabled only with modern
battle rules, atomically with the new BP event. Equal-count decrement and stale
flag clearing stay at their original execution boundary after critical/final
item arithmetic. Acquisition, dispatch, PP, Pressure, Choice, reset, order,
legality and RNG code are unchanged. The three modern flags remain independent
and default off. New production declarations use C89 placement.

## Route boundaries

| Route | This phase's behavior |
| --- | --- |
| CalcDamage / CalcDamageRaw / CalcMaxDamage | Ordinary gateway and local eligibility. CalcDamage keeps one existing range roll, Raw none. |
| Copied ordinary move | Actual TryMeFirst sets existing state; actual copied dispatcher installs moveNoCur; ordinary gateway owns the numerical event. |
| Pursuit | Actual producer sets20, subscript153 also SETs20; intrinsic40→80 remains2×. Existing PP/Pressure/Choice handling stays intact. |
| Repeated/multihit command | Existing ResetMoveStatus retains Me First flag/count. Each ordinary hit evaluates local eligibility; count normalizes once. |
| AI / switching / confusion / Future Sight | Public compatibility wrapper, even with an eligible ambient flag or matching candidate ID. No hypothetical copied-move forecast. |
| Beat Up / fixed / OHKO / returned damage | Existing independent assignments/formulas. No new boost or lifecycle. Current legality can still copy exceptional moves. |

Compatibility retains existing A14/D2a1/Helping Hand/Charge/ambient
POWER_MULTI quirks. Source equality checks retain all AI/player/switching code
and the exceptional/acquisition/dispatcher commands. Existing ability-query
knowledge writes caused by Mold Breaker are not classified as a new purity bug;
the new predicate and BP arithmetic themselves write nothing and draw no RNG.

## TDD and host proof

Before production edits, the actual accepted DamageCalcDefault, formula and
command were extracted and run under all eight type/battle/move flag
combinations. The native-power Ember discriminator failed numerically in only
the four battle-on builds: old42 versus required41. The four battle-off builds
passed. This was an arithmetic assertion failure, with no missing new API,
parser/compiler failure, or mock formula. Original RED evidence is
`.local-tools/validation/d2a2-command-red.log`. The final guarded baseline replay
replaces only the actual gateway with its pinned original body and reproduces
the same four failures in `d2a2-baseline-red-replay.log`.

`tools/qol/test_modern_me_first.py` executes the production collector, predicate,
worker, wrapper, gateway, range helper, acquisition/legal check, copied
dispatcher, Pursuit, ResetMoveStatus, Future Sight, Beat Up and actual AI.
SDK edges are small stubs. Existing shared host extraction emits the private
header after fixture types, then predicate, worker and public wrapper. The
critical-only fixture has an explicitly ordinary worker stub and is not counted
as numeric BP evidence. Direct collector fixtures pass FALSE; the screen source
assertion now examines the shared worker.

Coverage includes:

- All eight flags; native Ember40/Technician42→41, synthetic explicit intrinsic41
  grouped BP92 versus sequential91, and actual command damage2016→2026.
- Compatibility+TRUE, ordinary+FALSE, public typed function-pointer ABI,
  different selected/current/candidate moves, and ambient flags without leakage.
- Pure equality/repeated/expired/future/wide-counter math; exact original valid
  lifecycle state over totals−3..6, counts−4..7, and both flag values.
- All16 range rolls, crit markers1/2/3, all four attacker slots, negative command
  sign, Raw/Calc RNG counts, repeated hits, reset retention and expiry.
- Actual acquisition before/after target action, Encore match/mismatch,
  Struggle/status/illegal failures, copied dispatcher and exceptional routes.
- Pursuit producer/subscript SET20 contract, PP0..3, Pressure, Encore, Choice,
  normalized count and a single ordinary Me First event.
- Independent Python Q12/rational oracles for Me First with Technician, items,
  Helping Hand, Charge and Sports; actual item/ability accessors covering
  suppression, Mold Breaker, Klutz, Embargo, supplied weather, Cloud Nine/Air Lock.
- Actual AI matching/unrelated candidates, fixed/dynamic power, current move,
  eligible/stale/future flags and identical ambient12/20 inputs; unchanged state
  and RNG. Copied forecasts remain deferred.
- Baseline formula differential:10,080 representative power/override/stat/stage/
  ability/item/weather rows per build (80,640 across eight builds), each compared
  with public, compatibility+TRUE and ordinary+FALSE including state/RNG.
- Preprocessed body-token identity between pinned public formula and current
  worker in all four battle-off type/move combinations. DamageCalcDefault's
  battle-off body tokens also match. Names/signatures alone are excluded from
  formula comparison; the public declaration remains byte-for-byte unchanged.

## Commands and results

Run from repository root; all compiler jobs here are host `cc` extraction jobs.
The ignored driver explicitly enumerates host classes/methods, rejects SDK-named
methods, guards `battle_script_tools`/`compile_battle_script`, and rejects SDK/
Wine/native subprocess entry points before collection. In particular it never
loads the entire mixed NextMoveEffectTests class or any *SdkTests class.

```sh
PYTHONPATH=tools/qol python3 -m unittest test_modern_me_first.MeFirstRouteTests -v
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d2a2-me-first.py baseline
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d2a2-me-first.py sweep
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d2a2-me-first.py sanitize
git diff --check
```

The sweep explicitly includes MeFirstRouteTests, ConfirmedBasePowerTests,
ModernRulesTests, SelectedStatTests, SnowNative/Resource/ConsumerTests,
Next14Native/SourceTests, OffensiveModifierTests, OffensiveStageOrderTests,
DefensiveModifierTests, SimpleNativeTests, OriginalAbilityTests and the seven
non-SDK NextMoveEffectTests methods listed in the bounded implementation plan.
The sanitizer run covers the focused Me First and confirmed BP classes with
`-fsanitize=address,undefined -fno-omit-frame-pointer`.

Final guarded host sweep:120 methods passed in175.112s, no skips/failures, in
`.local-tools/validation/d2a2-sdk-free-sweep-final.log`. Final address/undefined
sanitizer run:25 methods passed in66.381s in `d2a2-sanitize-final.log`. These
include all14 new focused methods and11 confirmed BP regressions. The final
baseline replay in2.414s produced the four intended modern numerical failures
and zero legacy/compiler failures; its driver exits successfully only for that
exact expected failure pattern. `git diff --check` passed. An earlier sweep's
five failures were unused-static linkage warnings in the isolated critical
fixture, corrected before this final run; that earlier sweep is not counted as
passing evidence. No production change was needed for the fixture correction.

The release manifest is ignored local artifact
`.local-tools/validation/d2a2-frozen-manifest.json`; it hashes all ten changed/new
production/test/doc files, the guarded driver and final proof logs. No source
edits follow release to root for fresh spec then quality review.

## Native gate, references and deferred work

Root already recorded a matching accepted-baseline data-only native command RAM
fixture in `.local-tools/validation/me-first-native-red-proof.json`: species399,
L50 SpAtk100/SpDef100, native Ember40, Technician, current Normal target/no STAB,
no item/weather, flag1/count1/total1. Old damage42 gives458/500; lifecycle becomes
flag1/count0/total2. Seed12 keeps19 RNG calls/end4175436897;1700 compared frames
match every ARM9 instruction with zero fallback/guard failure/eviction. This is
deliberate command-state evidence, not native acquisition evidence. Actual
acquisition is exercised by host tests here. Changed code needs a fresh matching
SDK/ELF/boot and root-owned native41 validation; the old boot cannot validate new
code. No SDK/Wine/global/native/game build was run by this implementation phase.

Pinned behavior reference: Showdown
`82f129e0b847bf23395d552f9bb48eb82e53a0ec`, `data/moves.ts` Me First BP priority12,
marked Past. Existing hg-engine
`61b510cfb6cf7d77c3b083150fad3499f82fd326` and pokeemerald-expansion
`c460a8661dfa0598ae25d42a968c690ecbf489c6` credits/terms remain unchanged. This
local route adapter does not copy their complete formulas or expand legality.

Still deferred: hypothetical AI/copy forecasts; confusion/delayed/Beat Up
modernization; Life Orb/Metronome/berries/final groups; semi-invulnerable/Minimize
and the conflicting Fly/Bounce placement; Sharpness enabling; Soul Dew's unchanged
bank221/item225 description; broader Gen IX rules and whole-game installation.
Fresh spec/quality reviews, paired SDK/native integration, source-only commit,
push and GitHub reporting belong to the root integration lane. The installed
application, real ROM and real save are untouched.


## Integrated verification

Fresh independent specification and quality reviews passed31 guarded SDK-free
methods each (57.475s and55.803s):14 new Me First,11 BP and six affected tests,
across all eight flag combinations. Both verified80,640 differential rows,
typed public ABI, four battle-off formula-body/command token comparisons,
baseline replay with exactly four modern failures/no legacy/compiler failures,
and all ten file/five proof-artifact hashes plus whitespace.

The parent-owned paired SDK game/resource/layout/native build passed. A fresh
matching data-only ordinary-command RAM fixture confirmed42→41 damage while
retaining seed12,19 RNG calls, final RNG state4175436897 and the exact Me First
transition flag/count/total1/1/1→1/0/2. It compared every ARM9 instruction across
1700 battle frames with zero fallbacks, guard failures or overlay evictions. The
6500-frame boot is separate. This is command-state/lifecycle evidence; actual
acquisition/dispatch is host-tested, not claimed from the native fixture.

Raw stats/stages/types/abilities/items/status/weather matched the baseline. Ten
frozen files, seven prior validation saves, two new isolated Gallade saves and
all three tested artifact hashes matched after integration. This phase uses
120 guarded host checks,25 sanitizer checks, both reviews, paired build and the
native proof. The253-test full sweep belongs to f673 and was not rerun here.
No incomplete modern ruleset or real-save update was installed.
