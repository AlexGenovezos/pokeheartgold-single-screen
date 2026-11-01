# Gen IX D1c: selected defensive modifiers

Approved scope: the shared ordinary `CalcMoveDamage` defensive-stat layer on
`qol-mods`, based on `40aadba6c292cfdf70fd196098da1dc5e822d6b4`. The independent
battle, moves and types flags, native ABI, resources, roster, save layout and
installed app remain unchanged. Root owns subsequent SDK/native integration and
source-only commit/push. Host fixtures are SDK-free.

## Contract

Under `QOL_MODERN_BATTLE`, resolve only the move's selected defensive stat:
raw stat -> crit/user-Unaware/ignore-stage-filtered stage floor -> direct current-
type Snow Defense or Sand SpDef floor -> Q12 defensive group -> minimum one.
Use caller-supplied weather and actual living Cloud Nine/Air Lock suppression.
Psyshock/Psystrike select Defense while keeping Special category, screens and
history. Body Press's offensive raw Defense/stage never inherits defensive
weather, Marvel Scale or Metal Powder.

Q12 chains use nearest, half up (`+2048`); applying the completed group uses
nearest, half down (`+2047`). Pinned Showdown callbacks order weather10 (direct),
Marvel Scale6, Flower Gift SpDef4, Deep Sea Scale/Metal Powder2. Eligible effects:
status Marvel Scale only on selected Defense; base Clamperl Deep Sea Scale on
selected SpDef; current untransformed Ditto Metal Powder on selected Defense;
each actual live same-side base Cherrim Flower Gift provider, including self,
with actual active ability and defending Mold Breaker handling. Original species
comes from the actual party mon only when STATUS2_TRANSFORM is set. Current types
control weather. Irrelevant or ineligible defensive abilities must not cause
Mold Breaker knowledge/message state. Modern Explosion/Selfdestruct no longer
halve Defense. Gate every migrated legacy owner in the same change.

Soul Dew deliberately keeps BOTH old stat bonuses, the Frontier exclusion and
current-species ownership until the atomic D2 BP migration. Its defensive raw
SpDef `floor(1.5)` stays BEFORE the selected stage, direct weather and completed
modern group. Its offense stays after the modern offensive stage and before its
group, as established by D1b. This is an explicit compatibility exception, not
modern Soul Dew support.

Modern selected defensive locals are u32 and Q12 products u64 for bounded
legitimate original-roster arithmetic. No synthetic overflow parity claim is
made. Legacy u16/order and all four battle-off moves/types token streams must
remain identical to the baseline.

## Implementation and verification sequence

- [x] Write independent rational/literal actual-C `CalcMoveDamage` and real
  `TrainerAI_CalcDamage` fixtures across eight flag combinations; observe correct
  baseline assertion failures with no compiler or battle-off failures.
- [x] Reuse private numerical/base-species/provider helpers and migrate selected
  defense exactly once; preserve D1b offense, selectors and Snow order.
- [x] Update the old explicit Sand SpDef-order gap only after baseline RED.
- [x] Run focused D1c and affected D1b/D1a/Snow/selected/rules/Simple/original-
  ability/A14 SDK-free regressions, sanitizer fixtures and battle-off token diff.
- [x] Freeze all changed files and release for fresh independent specification
  then quality reviews. Root performs paired SDK/native proof before commit.

Fixtures cover every stage, crit1/2/3, Unaware, Sword/Lariat, suppression/ability
loss, current typing, no supplied weather, each weather flag, active suppression,
item accessor Klutz/Embargo, transformed original/current species, multiple
providers and Mold Breaker causality, grouped rounding, minimum-one effective
stat, retained Soul Dew/Frontier and real AI variance85..100. AI uses a neutral
chart boundary to isolate this layer; candidate projection and full final/berry/
AI variance ordering are deferred. Flash Fire flag lifecycle also stays deferred.

## Reference and arithmetic discriminators

Numerical authority: cached Showdown
`82f129e0b847bf23395d552f9bb48eb82e53a0ec`, `sim/battle.ts`, `data/conditions.ts`,
`data/abilities.ts`, `data/items.ts`. Corroborating owners: hg-engine
`61b510cfb6cf7d77c3b083150fad3499f82fd326`; expansion
`c460a8661dfa0598ae25d42a968c690ecbf489c6`. Expansion's grouped defensive weather
arithmetic is deliberately not adopted.

- Raw101,+1: stage151 -> Sand226 -> Deep Sea Scale452; old item/weather/stage454.
  L50, SpAtk103, explicit BP140 yields neutral16 vs15, then native Rock
  resistance8 vs7. Deliberate raw-stat/current-type fixture; no natural-stat or
  updated Overheat BP claim.
- Raw101, two Flower Gift providers: one grouped `101*9/4` half-down227, versus
  old single provider151; sequential two-provider floors226 would also be wrong.
- Raw101, Marvel Scale plus Metal Powder: grouped303 versus sequential302.
- Snow remains stage floor -> direct floor -> defensive group, never a weather
  factor folded into the Q12 group.

## Evidence and remaining limits

Implementation results, exact commands, logs and frozen hashes will be recorded
below before release. Passing host tests is not SDK/native proof or complete
ordinary Gen IX damage parity. Remaining BP/formula/final modifiers, delayed hits,
Beat Up, confusion, lifecycle and hypothetical AI projection stay separately
scoped in the roadmap.


Initial TDD run exposed a fixture constant typo and an unintended offensive
Flower Gift provider; both test setup errors were corrected before production
edits. The corrected pre-edit run (`d1c-red-corrected.log`) has28 modern assertion
failures and no compiler/battle-off failures across eight tests. Expanded final
fixtures against the captured unmodified40aad C source (`d1c-red-final.log`) have
36 modern assertion failures, no compiler errors and no battle-off failures across
ten tests. These are expected RED results. The native Sand/Scale discriminator
fails15 vs expected16; the modern-only Snow/Marvel/Powder discriminator fails13
vs expected12. Modern-off expected18 in the latter has no Snow boost.

The first full expanded green run passes10 methods in21.653s
(`d1c-green-expanded.log`). The complete D1c address/undefined sanitizer matrix
passes10 methods in27.706s (`d1c-sanitizers.log`), including real trainer AI at
all stage values and variance85..100. Literal/rational expectations do not call
or mirror the production Q12 helpers. The shared extraction fixture includes
all real production private helpers and the actual native ability/item paths.

Exact battle-off `CalcMoveDamage` preprocessed lexical tokens equal40aad for
all four types/moves combinations:3591 tokens with moves off,3735 with moves on
(`d1c-legacy-preprocessed.log`). Only host assertion source-line metadata is
excluded by preserving `GF_ASSERT(expr)` as a stub call rather than expanding
host `assert`'s `__LINE__`; all assertion expressions and production tokens
remain compared.

Commands (all run from repository root; validation driver/logs are ignored):

```sh
PYTHONPATH=tools/qol python3 -m unittest test_modern_defensive_modifiers -v
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d1c-defense.py baseline
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d1c-defense.py sanitize
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d1c-defense.py tokens
```

The baseline driver substitutes only the captured pre-edit shared damage fixture;
its actual production C is40aad. The driver verifies expected baseline failures
instead of treating a red test process as success. The sanitizer mode adds
`-fsanitize=address,undefined -fno-omit-frame-pointer` to all eight flag variants.


The affected regression command passed107 methods in199.654s, exit0
(`d1c-regression.log`):

```sh
PYTHONPATH=tools/qol python3 -m unittest test_modern_defensive_modifiers test_modern_offensive_modifiers test_modern_damage_layers test_modern_snow test_modern_selected_stats test_modern_rules test_modern_simple test_modern_original_abilities test_modern_next14 -v
```

This accidentally broad module command included13 existing SDK assembly/VM
methods. Root explicitly granted the already-running sweep exclusive SDK lane
ownership to finish; no additional SDK/global/native/build job was launched.
The94 non-SDK methods cover D1c, D1b, D1a, Snow, selected stats, rules, Simple,
original abilities and A14. The13 existing SDK methods that actually ran (all
passed) were:

- SnowAISdk: assembled AI byte/comparison parity.
- SnowSdk: compiled hail finite/duplicate/source/rock/suppression; original effect
  SDK parity and duplicate operand.
- SimpleSdk: delayed Rage recipient; exact swaps/Belly Drum/multistat drops;
  Starf/held/Pluck/Fling/pinch berry; Stockpile event counts/ability loss; trainer
  X-item message/application.
- OriginalAbilitySdk: original Flash Fire script boost/frozen status/HP.
- Next14Sdk: compiled appends/prefixes/reserved members; effect dispatch/Acid/
  immunity/Competitive/selfboost/Substitute/KO/failure; multievent caps/Simple/
  suppression/Snatch/stack; Shell Smash drops/immunity/Competitive/White Herb.

Those SDK script checks are not a paired game/native build. Root still owns fresh
independent specification and quality reviews, the matching game/native build,
controlled Sand/Snow native GREEN comparisons, source-only commit and push.
No staging, commit, push, install, native game build, app/real-ROM/real-save edit
was performed by the implementation worker. `git diff --check` passed.


Source release: `.local-tools/validation/d1c-source-freeze.sha256` records the
SHA-256 of all six changed production/test/doc files, including this contract.
The implementation worker stops edits at this release. Review and paired-build
results are intentionally pending and must be appended by the integration owner
only after completion. The installed app and real save remain unchanged.


## Integrated verification

Fresh independent specification and quality reviews passed. Each independently
ran the20 D1c/D1b methods across all eight flag combinations (42.277s and41.962s)
and verified all four battle-off token streams plus six frozen hashes and
whitespace. Quality also tested every battler/party index through Transform
lookup and confirmed no party access without Transform.

The parent-owned paired SDK game/resource/layout/native build passed. Two fresh
matching data-only RAM fixtures confirmed Sand/Scale7→8 damage and
Snow/Marvel Scale/Metal Powder13→12. Both used seed12 and retained their prior
19/17 combat RNG calls and final RNG states. Each1700-frame battle segment
matched every ARM9 instruction against the interpreter, with zero fallbacks,
guard failures or overlay evictions (3400 total compared frames). The6500-frame
boot is separate from the measured battle segments. All inspected raw stats,
stages, current types, abilities/items/status/weather were equal before each
comparison. These deliberate test values do not claim natural species stats.

All seven validation save hashes, frozen production/test hashes and three tested
artifact hashes matched after integration. The107-test affected sweep (94 host,
13 existing SDK) belongs to D1c; the253-test full sweep belongs to f673 and was
not rerun for this phase. No incomplete modern ruleset was installed.
