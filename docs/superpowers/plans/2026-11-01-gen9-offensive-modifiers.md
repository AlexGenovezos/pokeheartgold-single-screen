# Gen IX offensive modifiers (D1b)

Implementation contract: only `QOL_MODERN_BATTLE` consumes D1a's selected,
stage-floored offense through a bounded Q12 stat group. Chain rounds halves up
(`((u64)a*b+2048)>>12`); applying the group rounds halves down
(`((u64)stat*modifier+2047)>>12`), then clamps effective offense to at least one.
Original-roster bounds fit u32; this is not a synthetic overflow parity claim.
Hustle floors directly after stage, outside the group. No ABI, context or save
fields, imported data, resources, public entry points or feature defaults change.
Battle-off retains the native u16 assignments and operation order.

Pinned arithmetic/eligibility authority: Showdown
`82f129e0b847bf23395d552f9bb48eb82e53a0ec`, cached locally under
`.local-tools/validation/status-reference`. `sim/battle.ts` establishes chain vs
apply and `alliesAndSelf` event dispatch. `data/abilities.ts` establishes target
Thick Fat/Heatproof priority6 for Attack,5 for Sp. Atk; user abilities priority5;
Flower Gift Attack priority3. `data/items.ts` puts the migrated items at priority1.
hg-engine `61b510cfb6cf7d77c3b083150fad3499f82fd326` and expansion
`c460a8661dfa0598ae25d42a968c690ecbf489c6` corroborate ownership; their different
rounding is not imported.

Single-owner migration ledger:

| Effect | Modern owner | Legacy owner gated off only in modern battle |
| --- | --- | --- |
| Huge/Pure Power, Slow Start, Guts | Offensive stat group, user ability | Sequential Attack modifications |
| Hustle | Direct floor after selected stage | Late Attack modification |
| Plus/Minus, Solar Power | Offensive stat group, user ability and eligible ally/weather | Sequential Sp. Atk modifications |
| Flower Gift Attack | Each actual live same-side base Cherrim provider at priority3 | Generic native ability scan/Attack multiplication |
| Overgrow/Blaze/Torrent/Swarm | Offensive stat group, user's HP/type/ability | BP multiplication |
| Flash Fire | Offensive stat group, user's active ability and activation flag | Post-formula flag-only multiplier |
| Thick Fat/Heatproof | Offensive stat group, target active ability unless ignored | BP division |
| Choice Band/Specs, Thick Club/Deep Sea Tooth | Offensive stat group, user item/category/base species | Sequential stat modifications |
| Light Ball | Offensive stat group, both categories, user's base Pikachu | BP doubling |
| Soul Dew | Retained legacy Sp. Atk/Sp. Def behavior, including Frontier restriction | Remains until atomic BP+D2 migration |

Foul Play borrows target raw Attack/stage; Body Press borrows user raw
Defense/stage. Offensive modifiers, HP/status/items/level remain user-owned.
Psyshock remains special category. Weather is caller-supplied with active Cloud
Nine/Air Lock suppression. Item access remains Klutz/Embargo aware. Self boosts
are not disabled by opposing Mold Breaker. Target reductions retain the causal
native Mold Breaker query. Flower Gift uses actual active providers, including
self and multiple eligible Cherrim, with original species recovered from the
selected party member only after Transform. A hypothetical ability argument in
trainer AI cannot manufacture a provider. Existing ordinary AI uses live battle
context; candidate-stat/context projection remains a separate limitation.

Verification plan: first execute literal real-C damage discriminators and watch
modern assertions fail without production changes. Rework retained D1a sequential
oracles into independent rational grouped expectations for modern builds while
retaining their exact legacy oracle. Exercise all eight feature combinations
through actual CalcMoveDamage and TrainerAI_CalcDamage, ability/item/source and
category pairs, every stage/critical marker, suppression/Mold Breaker,
weather/provider/species/Transform, Klutz/Embargo, HP/turn/activation boundaries,
minimum stat and independent literal Q12 half boundaries. Run affected SDK-free
Snow/Simple/original-ability/A14/selected-stat/rules checks. Freeze source and
test hashes for fresh specification/quality review. Owner coordinates SDK/native
paired build and data-only copied-state fixtures; no installed app/ROM or real
save is modified.

## Verification record

The initial pre-implementation real-C literal failed with expected153/got152;
no production code existed for the group at that point. A later clean replay
extracts `CalcMoveDamage` and dependencies from `git show 2b23b496d` without
rewriting the working tree; final tests preserve every legacy expectation.

The affected SDK-free suite passed57 methods in80.856s with this command:

```sh
PYTHONPATH=tools/qol python3 -m unittest test_modern_offensive_modifiers test_modern_damage_layers test_modern_selected_stats.SelectedStatTests test_modern_snow.SnowNativeTests test_modern_simple.SimpleNativeTests test_modern_original_abilities.OriginalAbilityTests test_modern_rules.ModernRulesTests test_modern_next14.Next14NativeTests.test_shared_damage_and_actual_ai_resolve_before_technician_and_honor_override -v
```

Log: `.local-tools/validation/d1b-regression-final.log`. The10 D1b methods and
six retained D1a methods exercise all eight independent flag combinations.
Three older damage fixtures now share the Snow factory so they extract the
actual private production helpers consistently. The AI fixture uses a900-entry
test-only setup buffer: assigning extended IDs into its former468-entry native
array was out of bounds, even though the actual extended accessor was correct.
Independent numeric expectations exposed that harness defect; the fixed AI
matrix is additionally checked with address/undefined behavior sanitizers.

The ignored validation driver records the clean baseline RED and sanitizer
checks without modifying production:

```sh
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d1b-offense.py baseline
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d1b-offense.py sanitize
```

Logs: `d1b-red-2b23-extraction.log` and `d1b-ai-sanitizers.log` in the same local
validation directory. The pure-helper test is excluded from baseline replay
because those functions did not exist in2b23. Four preprocessed token comparisons
confirm battle-off CalcMoveDamage is exactly identical to2b23 with all four
types/moves flag settings (`d1b-legacy-preprocessed.log`). `git diff --check`
passes. Source freezes and independent specification/quality reviews precede
owner-coordinated paired SDK/native validation; no SDK/native/install command
was run by the implementation worker.


## Integrated verification

Both fresh independent reviews passed. The specification reviewer independently
passed all16 D1b/D1a methods in33.465s across eight flag combinations and exact
battle-off token comparisons. Quality review independently passed those16
methods in34.534s, the three retained fixture methods in2.533s, and the AI
sanitizer matrix in3.058s. All nine frozen hashes and whitespace checks matched.

The parent-owned paired SDK game/resource/layout/native build passed. Two fresh
matching data-only RAM fixtures confirmed Guts/Choice Band152→153 damage and
Flash Fire54→55. Each retained its seed12, respectively18/19 combat RNG calls,
and final RNG state. Both1700-frame segments matched every ARM9 instruction
against the interpreter (3400 total), with zero fallbacks, guard failures or
overlay evictions. The initial6500-frame boot is separate from these measured
battle segments. Seven validation saves and all three tested artifact hashes
remained unchanged; production/test hashes still matched after integration.

This C-only phase uses the57 affected SDK-free checks, both independent reviews,
paired build and two native proofs. The preceding253-test full sweep belongs to
f673; it was not rerun for D1b. No incomplete modern ruleset was installed.
