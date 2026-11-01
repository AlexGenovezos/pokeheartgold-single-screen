# B6 selected-stat ordinary modern moves

Approved scope, implemented in the development working tree on 2026-11-01.
Fresh specification review, quality review, the combined full suite and matching
native proof remain pending and parent-owned. Existing d56188b6c build artifacts
predate Snow/A14/B6 and cannot validate these move IDs. No installation, live-app
write or real-save write is part of this checkpoint.

## Scope and data

`QOL_MODERN_MOVES` supports72 extended IDs after adding Psyshock476,
Psystrike543, Foul Play495, Body Press779, Sacred Sword536 and Darkest Lariat666.
Their effects are native0 and their nonzero ordinary base powers admit them to
existing trainer AI damage estimation. They use existing plain GoToEffectScript
animation aliases428/94/242/34/427/242. Full names/descriptions and compact cards
share the literal data adapter and private message bank829. Native King's Rock
bit32 is translated deliberately; none is sound, punching or Substitute bypassing.
Body Press is banned from Metronome after the existing Mimic separator, preserving
Mimic legality. A future Sharpness classifier must include Sacred Sword, but this
batch adds neither Sharpness nor an unrelated classification API.

No effect, subscript, ASM or message transform is added. Move-enabled resources
remain284 effects,304 subscripts, bank1971285 messages, and move/name/card extent899
because Aqua Cutter898 remains highest. Original archive prefixes, unsupported
gaps468..470 and other unimplemented IDs stay intact. Default/type-only and
battle-only enable no additional IDs. Moves-only works with legacy battle rules;
all three feature flags remain independent.

`NUM_MOVES=467`,16-byte MoveTbl,468-entry embedded AI move table,16-bit move IDs,
original Pokémon/save/context layouts, original493 roster/story and native forms
are unchanged. No new context field or ability is required.

## Shared selected-stat calculation

Small pure selectors separate raw offense source, processed Defense selection and
ignore-target-stages behavior from damage category. Shared `CalcMoveDamage`
serves actual battle, trainer AI and opponent switching estimates; no duplicate
power resolution or RNG is added. Explicit power/type overrides retain their
existing meanings. A14 intrinsic-power/Technician eligibility remains after
`ctx->powerMultiplier` and before Charge/Helping Hand.

- Psyshock/Psystrike use the user's raw Sp. Atk and its stage against the target's
  Defense and Defense stage. Special category still controls Light Screen,
  category items, burn handling and special-damage history. They reuse the
  reviewed Defense stage → Snow floor → Marvel Scale/Metal Powder path.
  Sand/Deep Sea Scale/Soul Dew/other Sp. Def-only modifiers stay excluded.
  Crit and attacking Unaware ignore the selected stage without erasing weather
  or items. Snow reads the passed field condition, current Ice typing in either
  slot and active weather suppressors.
- Foul Play selects the target's raw Attack and Attack stage before crit and
  defending Unaware. The user's ability/item/status/level/STAB remain owners of
  offensive modifiers; the target's Huge Power, Choice Band and burn do not
  transfer. User Unaware does not erase the selected Attack stage. Defender
  Unaware ignores that stage even though the raw supplier is the defender;
  suppression and Mold Breaker preserve their normal roles.
- Body Press selects the user's raw Defense and Defense stage, then applies
  offensive modifiers such as Huge Power, Choice Band, Slow Start and user burn.
  Snow, Marvel Scale and Metal Powder on the user never boost its offensive
  Defense. Crit ignores negative selected stages; defending Unaware ignores the
  selected stage. This does not invent Wonder Room support.
- Sacred Sword/Darkest Lariat ignore both boosts and drops to target Defense
  and evasion through one pure ID predicate used by damage and the real hit
  check. User accuracy stages, Hustle, target accuracy abilities/items and
  non-stage defensive modifiers still apply. They are not always-hit moves.

Preview remains a pure type-chart query, with Psychic/Fighting/Dark types as
appropriate; it does not predict selected-stat damage or accuracy. No specialized
new AI scoring is claimed.

## Learnsets and access

The pinned profile regenerates336 overlay rows across237 base species, adding18:
Psyshock9, Psystrike1, Foul Play6, Body Press1, Sacred Sword1, Darkest Lariat0.
Mewtwo learns Psystrike72, Gallade Sacred Sword1 and Regigigas Body Press42.
Darkest Lariat's8 machine-compatible species do not make it obtainable without a
future access port. No native TM reassignment, tutor expansion or egg conversion
is included; original story moves remain.

Max additions stay5, actual merged maximum22 plus sentinel, private capacity28.
The generator retains its >5 rejection and Baby-Doll/Precipice spelling guards.
Existing wide creation, level/evolution, relearner, daycare and field tutor readers
remain shared, with native alternate forms and real0xFFFF sentinel boundaries.

## Focused validation and remaining gates

The SDK-free focused tests execute production C selectors, CalcMoveDamage,
TrainerAI_CalcDamage, AI damage-score admission, BattleSystem_CheckMoveHit and
BattleControllerPlayer_HpCalc. They cover all8 feature-flag combinations, disparate
raw stats/stages, positive/negative stage ignoring, crit/Unaware/Mold/suppression,
odd-stat Snow floors, defensive-only versus offensive modifiers, user/target burn,
screens/category history/Substitute, accuracy RNG thresholds, overrides and
no-added-RNG damage/AI paths. Existing data/resource/learnset/preview checks are
updated for72/336/237 and retain archive/layout guards. No unchanged SDK parity
work is repeated because this cohort changes no battle-script/ASM source.

Focused verification:52 affected host tests passed in
`.local-tools/validation/gen9-next6-focused-final2.log`. The initial missing-rule
failures are preserved in `gen9-next6-focused-red.log`. These are host
checks, not combined/native gameplay proof. Parent owns fresh independent
specification → quality reviews, combined full-suite validation and matching
native/interpreter checks using private copied saves. Do not run older native
artifacts against B6 IDs or install an unverified combined build.

This is a bounded selected-stat port, not a complete Gen IX damage calculator.
The inherited offensive ordering still applies offensive ability/item modifiers
before stages: raw101,+1,Huge Power yields303, while Gen IX stage-first yields302.
Foul Play and Body Press deliberately share that existing gap with ordinary
Attack. A focused odd-point fixture records the gap rather than treating an
ordinary-Attack comparison as Gen IX proof. A future shared offensive-stage and
modifier-order correction is required before a full-ruleset installation claim.
Broader base-power/final-damage multiplier grouping/rounding and Sharpness base-
power placement are also separate remaining work. Effective-weight moves,
future abilities/access ports, Wonder Room and full ordinary Gen IX completion
remain outside this cohort.

## Sources and corrections

BluRosie's hg-engine `61b510cfb6cf7d77c3b083150fad3499f82fd326` supplies pinned
IDs/profile/level learnsets. rh-hideout's pokeemerald-expansion
`c460a8661dfa0598ae25d42a968c690ecbf489c6`, especially CalcAttackStat6857..6907,
supports raw/stage selection before crit/defending Unaware. We deliberately do
not copy hg-engine's clear-before-replace ordering for Foul Play/Body Press.
Pokémon Showdown `82f129e0b847bf23395d552f9bb48eb82e53a0ec` corroborates the
source-owner behavior: battle-actions1725..1771 selects raw stat/stage then calls
calculateStat with statUser=the user; pokemon581..618 dispatches ModifyBoost
against that owner, and abilities5216..5233 Unaware matches the selected owner.
Source credits and applicable reuse terms in docs/QOL-REUSE.md remain intact;
this local C adaptation does not assert interchangeable upstream native scripts.


## Integrated validation

The combined253-test suite passed in661.343s and the matching paired build
passed. Three native selected-stat comparisons (5100 frames) had zero
fallbacks/guards. Psyshock dealt6 damage versus correct outcomes6/7 and
incorrect Special Defense outcomes9/10/12; Foul Play dealt3 versus correct3/4
and incorrect user-Attack5/6; Body Press dealt8 versus correct7/8/9 and
incorrect Attack2/3. These ranges use inspected fixture stats and all16 rolls.
After-turn native history scratch resets; category/history proof is in actual-C
host tests. The inherited offensive rounding limitation remains above.

See [QOL-REUSE.md](../../QOL-REUSE.md#combined-snow-and-twenty-move-integration)
for complete evidence. Source/saves/artifacts matched; the live app/save remain
unchanged and complete Gen IX implementation is still in progress.
