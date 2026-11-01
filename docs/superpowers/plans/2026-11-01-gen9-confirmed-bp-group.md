# Gen IX confirmed BP group (D2a1)

## Contract and scope

Approved bounded prerequisite on `qol-mods`, based on
`f72c6de184a9f5d808caaa8a68115f64ce8c9540`. Modern battle owns this numerical
migration. Modern moves still owns A14 intrinsic callbacks; explicit nonzero
public power bypasses those callbacks. Modern types remains independent. All
flags remain default off. No ability242/Sharpness assignment, item catalog,
resources, species, learnsets, public signature, context/save/packet layout,
persistent side channel, native script or RNG owner changes.

Arithmetic authority is Showdown
`82f129e0b847bf23395d552f9bb48eb82e53a0ec`, cached in
`.local-tools/validation/status-reference`: `battle.ts` chain/apply, `abilities`,
`items`, `moves`, `conditions`, and `battle-actions`. hg-engine
`61b510cfb6cf7d77c3b083150fad3499f82fd326` and expansion
`c460a8661dfa0598ae25d42a968c690ecbf489c6` corroborate ownership, not rounding.
Use literal Q12 constants, never percentages recomputed as approximations.

## Numerical ownership ledger

Intrinsic resolution precedes the external group: explicit power, otherwise
move table/A14 callback, then genuine native intrinsic POWER_MULTI. Pursuit,
Revenge/Avalanche, Smelling Salts and Wake-Up Slap retain native early doubles.
Actual Payback writes `movePower`, not POWER_MULTI; its existing command and
explicit override contract remain intact. Technician tests this resolved power.

| Priority | Confirmed owner | Q12 and eligibility |
| --- | --- | --- |
| 30 | Technician | 6144; nonzero intrinsic BP<=60, damaging category, excluding Struggle |
| 24 | Rivalry | 5120/3072 for same/opposite non-genderless users/targets |
| 23 | Iron Fist | 4915; existing enabled punching-move table |
| 23 | Reckless | 4915; active ability and native crash/recoil effect45/48/198/253/262/269 |
| 17 | Target Dry Skin | 5120; effective Fire, native bypass/suppression-aware query |
| 16 | Muscle Band/Wise Glasses | 4505; matching Physical/Special category |
| 15 | Type items/plates | 4915; existing held effect and effective move type |
| 15 | Adamant/Lustrous/Griseous Orb | 4915; original/base Dialga/Palkia/Giratina and matching type |
| 15 | Soul Dew | 4915; original/base Latios/Latias and Psychic/Dragon, including Frontier |
| 10 | Helping Hand | 6144; existing turn flag |
| 9 | Charge | 8192; existing user flag and effective Electric type |
| 1 | Mud/Water Sport | 1352; existing field-effect accessor and Electric/Fire type |
| default0 | Solar Beam | 2048; supplied adverse weather, active Cloud Nine/Air Lock respected |
| default0 | Facade/Brine | 8192; existing native status mask/target-half-HP condition |

The pinned Muscle Band/Wise Glasses priority is **16**, correcting the roadmap's
15; no two held items coexist, so this correction does not change supported
relative ordering. Source conditions obtain active abilities/items through the
existing getters. Normalize and caller-supplied effective type retain their
existing precedence. Species items use the existing original-party lookup only
under actual Transform. Modern Griseous Orb therefore no longer inherits the
legacy blanket Transform rejection. Modern Soul Dew removes **both** old SpAtk
and SpDef bonuses atomically, including their old Frontier exclusion. Battle-off
retains both original floors, current-species ownership and Frontier restriction.

The private script classifier accepts default10 for snapshot projection or the
exact native12/20 value, plus matching effect and prerequisite. Only confirmed
native external values are removed from the early multiply; the group applies
their effect once. Ineligible/mismatched/unknown values retain an explicit legacy
early multiplication. The calculator never rewrites `ctx->powerMultiplier`.
Default10 projections can derive these three supported effects from snapshots;
this does not establish native command provenance or general AI projection.

Chain each eligible modifier using `(u64(a)*b+2048)>>12`; apply the completed
group once using `(u64(power)*modifier+2047)>>12`. Clamp to BP1 only after a valid
nonzero damaging BP enters the group. Zero power and status-category helper
inputs remain unchanged. Modern BP locals are u32 and products u64. Bounded
original-roster arithmetic is supported; arbitrary overflow/cartridge wrap
parity and later formula boundaries are separate work. D1a/b/c selected-stage,
offensive, defensive, weather and stat-modifier owners remain intact.

## Compatibility ledger and deferred work

- Player-facing Soul Dew description is a deferred resource/UI owner. Native
  `GetItemDescIntoString` reads bank221/item225; both source
  `files/msgdata/msg/msg_0221.gmm` row225 and packed `msg.narc` still say:
  "A wondrous orb to be held by LATIOS\nor LATIAS. It raises both the\nSp. Atk and Sp. Def stats."
  Their encoded words were inspected and match. No existing modern message
  transform changes this row. A separate battle-flagged item-description
  transform and UI validation must replace it before claiming complete item UI
  parity; this source-only phase deliberately does not broaden that pipeline.
- Me First retains **both** its existing post-formula numerical1.5 and execution
  lifecycle owner, unchanged. D2a2 must introduce explicit local command versus
  projection/exceptional-route inputs before moving its numerical owner.
- Dig/Dive/Minimize and airborne native doubles retain early placement **and**
  existing Technician eligibility. No partial eligibility correction occurs.
  Pinned Fly/Bounce callbacks conflict with hg/expansion; the split is not
  established cartridge fact. D3 resolves reference and final-layer ownership.
- Sports retains existing field lifetime; Charge retains existing consumption
  timing. This patch only changes confirmed arithmetic, not those lifecycles.
- Public shared-formula callers retain their existing applicability. Confusion,
  delayed cast calculation, Beat Up, fixed damage, chart-only paths, full final
  layers, +2/weather/spread/burn/screens, Metronome and final/berry ordering remain
  distinct contracts. No new ordinary-route provenance is guessed from damage,
  override presence or move ID.
- Trainer AI runs the same shared confirmed math but still uses native snapshot
  abilities/items/ambient multiplier and lacks general candidate script
  projection. A candidate with unrelated ambient12/20 retains that compatibility
  behavior. Switching's hypothetical candidate/effective-type limitations also
  remain. Existing AI Magnitude/Psywave RNG is not removed; new pure helpers draw
  none. Shared native Mold Breaker announcement writes remain caller-owned.

This is confirmed BP subset support, **not** complete BP, all-route or complete
Generation IX damage parity. Sharpness remains disabled pending D2a2 and its own
review/integration gates.

## Verification plan and evidence

Tests execute production `CalcMoveDamage`, real `TrainerAI_CalcDamage`, real
Payback/Revenge/Pursuit commands, and original effect bytecode with actual native
control/arithmetic commands. Platform/script presentation boundaries are stubbed
explicitly. Pursuit's reset/copy platform boundaries are counted; the test checks
native PP/Pressure/Encore/selection/Choice state and intrinsic Technician exclusion.
Revenge covers physical/special positive damage and correct/wrong target bits.
Payback proves explicit power50/100 with multiplier10, rather than a synthetic20.
All six Reckless producer scripts plus Facade/Brine run from original cached
archives; recoil/status/accuracy/reset/script ownership stays unchanged.

Independent Python Q12 literal rows cover 1,320 attainable BP combinations per
modern flag variant (5,280 modern executions): Technician/Rivalry/Iron Fist/
Reckless, type item/Muscle Band, HH, Charge, Sports and BP boundaries through65535.
Further actual-C tests cover all eight flags, all target slots, halfUP/halfDOWN,
zero/status/minimum, >32bit products, pure injected75*1.5*1.5=>169 versus168,
weather/suppression/Mold Breaker, species Transform, legacy fallbacks, A14 explicit
bypass/all-seven-stage max860, Struggle and actual AI all16 variance rolls.

Discriminators include intrinsic55+Technician+type item=>BP99 (old98), and adding
HH=>BP149 (old147 with moves-only eligibility). Native fixtures use Attack102,
Defense100, L50 to distinguish damage46 vs45. Atomic Soul Dew uses SpAtk99,
SpDef100, Psychic90, both items and current Normal types: modern49 versus old41;
retaining both stat bonuses plus new BP would yield48, one retained bonus72/33,
and missing BP41. Frontier, each side independently and nonmatching type are
separate cases. Existing D1 Soul Dew and A14 sequential fixtures were changed only
after their meaningful expected RED assertions were captured.

Initial corrected red command:

```sh
PYTHONPATH=tools/qol python3 -m unittest test_modern_base_power.ConfirmedBasePowerTests -v
```

Before production edits: 3 methods, 6.306s, **12 expected modern assertion
failures**, zero compiler/battle-off failures. Corrected-oracle replay against
frozen f72c: 3 methods, 7.800s, the same12 modern assertions and zero legacy/
compiler failures (`d2a1-baseline-red.log`). Log: ignored
`.local-tools/validation/d2a1-red.log`. An initial test-oracle draft incorrectly
predicted148 for the three-factor chain; independent integer calculation proves
chain11060/apply55=>149. The corrected oracle retains the intended baseline RED.

Old-expectation proof: `.local-tools/validation/d2a1-legacy-expectation-red.log`
records eight modern D1 Soul Dew assertions; that preliminary run also exposed
an unused local warning, fixed before the separate A14 assertion RED in
`d2a1-a14-expectation-red.log`. Script-VM harness development separately corrected
a prototype/pointer-boundary mismatch and the verified opcode79 dispatch; these
were harness errors, not production feature RED evidence.

Focused SDK-free command (the final seven IDs explicitly exclude the SDK method
mixed into `NextMoveEffectTests`):

```sh
PYTHONPATH=tools/qol python3 -m unittest \
 test_modern_base_power.ConfirmedBasePowerTests \
 test_modern_rules.ModernRulesTests \
 test_modern_selected_stats.SelectedStatTests \
 test_modern_snow.SnowNativeTests test_modern_snow.SnowResourceTests \
 test_modern_snow.SnowConsumerTests \
 test_modern_next14.Next14NativeTests test_modern_next14.Next14SourceTests \
 test_modern_offensive_modifiers.OffensiveModifierTests \
 test_modern_damage_layers.OffensiveStageOrderTests \
 test_modern_defensive_modifiers.DefensiveModifierTests \
 test_modern_next_move_effects.NextMoveEffectTests.test_actual_stat_command_applies_self_boosts_and_both_defensive_drops \
 test_modern_next_move_effects.NextMoveEffectTests.test_fixed_two_hits_never_roll_skill_link_or_variable_hit_distribution \
 test_modern_next_move_effects.NextMoveEffectTests.test_native_self_stat_effects_require_a_hit_and_survive_target_ko \
 test_modern_next_move_effects.NextMoveEffectTests.test_nuzzle_dispatches_the_existing_modern_paralysis_subscript \
 test_modern_next_move_effects.NextMoveEffectTests.test_quarter_and_third_recoil_rounding_rock_head_reckless_substitute_ko_and_immunity \
 test_modern_next_move_effects.NextMoveEffectTests.test_raging_fury_two_or_three_turn_lock_and_native_confusion_residual \
 test_modern_next_move_effects.NextMoveEffectTests.test_screen_subscript_clears_both_timers_before_hp_damage -v
```

Final focused, sanitizer and legacy-token results are recorded below.
Fresh independent specification/quality reviews and matching SDK/game/
resource/native integration remain root-owned gates. A preliminary class-based
sweep accidentally entered the SDK method mixed into `NextMoveEffectTests` and
was immediately interrupted (exit130); it is **not** a passing sweep. Root was
notified and confirmed no competing lane; ignored output was retained, persistent
wineserver left alone. No game/native build, install, staging, commit or push was
run. The corrected runner prints89 inspected SDK-free method IDs, explicitly
excludes that method, and guards `battle_script_tools` against any SDK entry.
The interrupted log is `d2a1-affected-green.log`; the clean run has its own
`d2a1-affected-sdk-free-green.log`. Installed game, real ROM and save were untouched.

The additional old D1b Soul Dew fixture produced four expected modern assertion
failures before updating its modern expectation (`d2a1-offensive-soul-expectation-red.log`,
1 method in2.188s). Both stat owners remain explicitly asserted for battle-off;
Normal Swift receives no modern Soul Dew BP boost. The11 new methods passed
address/undefined-behavior sanitizers in29.240s (`d2a1-sanitizer-green.log`), using:

```sh
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d2a1-bp.py sanitize
```

All four battle-off preprocessed `CalcMoveDamage` lexical token streams equal
f72c exactly:3591 tokens with moves-off,3735 with moves-on, for either types flag.
Host assertion line metadata is excluded; expressions and order are compared.
Token command/log:

```sh
PYTHONPATH=tools/qol python3 .local-tools/validation/check-d2a1-bp.py tokens
# .local-tools/validation/d2a1-legacy-tokens.log
```

The first guarded89-method host sweep completed in130.746s with two expected
modern/moves-on assertions in the older B6 Wise Glasses fixture, which supplied a
synthetic native modifier20 and expected BP120. Modern4505 correctly yields110;
battle-off still expects120. Its RED is retained in
`d2a1-wise-glasses-expectation-red.log` before updating the modern literal.

Final guarded SDK-free sweep: **89 methods passed in127.184s**, zero failures,
errors or skips. It enumerated each inspected ID and explicitly excluded the
mixed SDK method; guarded SDK entry was never called. Actual command and log:

```sh
PYTHONPATH=tools/qol python3 .local-tools/validation/run-d2a1-sdk-free.py
# .local-tools/validation/d2a1-affected-sdk-free-green.log
```

The equivalent explicit unittest command above includes the same89 methods.
`git diff --check` passed. The final four legacy token comparisons were rerun
successfully after the comment-only removal of the obsolete D1c Soul Dew note.
The final source/test/doc SHA256 manifest is
`.local-tools/validation/d2a1-source-freeze.sha256`; no further edits are authorized
in this implementation lane until root releases the freeze. Fresh spec/quality
reviews and root-owned matching SDK/native proofs remain required before
integration. No full BP/all-route or item UI parity claim is made.


## Integrated verification

Fresh independent specification and quality reviews passed. Each independently
ran16 selected methods across all eight flag combinations: the11 new methods
plus five changed regressions (31.896s and32.172s). Both confirmed all four exact
battle-off token streams, all ten frozen hashes and tracked/untracked whitespace.

The parent-owned paired SDK game/resource/layout/native build passed. Two fresh
matching data-only RAM fixtures confirmed project Acrobatics515 with Technician/
Sharp Beak45→46 damage and atomic Soul Dew41→49. The latter is disjoint from
retaining both old stat bonuses with the new BP effect48, retaining only the
attacker bonus72, only the defender bonus33, or omitting the BP effect41. The
current Normal types deliberately isolate neutral/no-STAB arithmetic; these raw
fixtures do not claim natural species stats.

Both used seed12 and retained their respective18/19 combat RNG calls and final
RNG states. Each1700-frame battle segment matched every ARM9 instruction against
the interpreter, with zero fallbacks, guard failures or overlay evictions (3400
total). The6500-frame boot is separate from those measured segments. Inspected
raw stats/stages/types/abilities/items/status/weather matched before comparisons.

All seven validation save hashes, eight frozen production/test hashes and three
tested artifact hashes matched after integration. This phase uses the89 guarded
SDK-free checks,11 sanitizer checks, independent reviews, paired build and two
native proofs. The253-test full sweep belongs to f673 and was not rerun here.
Me First, final routes, lifecycle/projection gaps and Soul Dew item text remain
explicitly pending. No incomplete modern ruleset was installed.
