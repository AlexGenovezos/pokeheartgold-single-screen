# Gen IX offensive stage order — Phase D1a

Approved scope: correct selected offensive stage order in the existing shared
`CalcMoveDamage`, on top of `f67386570e965c967990eae3fd8ad68a3fb539c6`.
Modern battle alone enables this original-rule correction; moves and types
remain independent. No resource, species, learnset, save, context or ABI change.

## Implementation contract

- Select raw offense and stage first: ordinary user Attack, Foul Play target
  Attack, Body Press user Defense, or ordinary user Special Attack. The user
  continues to own offensive abilities/items/status, level and STAB.
- Defending Unaware ignores the selected offensive stage unless suppressed or
  bypassed by active user Mold Breaker. User Unaware still filters defensive
  stages and does not discard Foul Play's selected Attack stage.
- Critical markers 2 and 3 ignore negative offensive stages. Apply the filtered
  stage with one integer floor before existing offensive modifiers. Reset only
  local stage offsets to zero so the later formula cannot apply them again.
  Modern Simple already stores its doubled changes; never reinterpret them.
- Move the existing defending-Unaware query rather than adding another query.
  Retain its native causal Mold Breaker flag behavior and retain the late user
  Unaware defensive branch. No RNG or stored stat/stage mutation is added.
- Use `u32` modern local Attack/Special Attack without implicit `u16`
  reassignment narrowing. Battle-off keeps native `u16` and modifier-first
  behavior. Legitimate original-roster raw non-HP stats are bounded by 614
  (base 230, level 100, maximum IV/EV, positive nature). A conservative offense
  bound through the retained stage/ability/item/Flower Gift sequence is
  `614 * 4 * 2 * 2 * 3 / 2 = 14736`; stat-stage and percentage products fit
  `u32`. This phase adds no synthetic intermediate wrap/minimum contract and
  does not claim exactness for hypothetical raw 65535, downstream formula
  overflow, or the disputed cartridge intermediate wrap boundaries.
- Preserve Snow's physical defensive sequence, special-defense/Sand placement,
  intrinsic power/Technician snapshot, critical-before-random and final Sniper.
  Existing sequential offensive modifier grouping/locations remain separate
  D1b work. Burn/screens, +2, BP/final groups and berry lifecycle are unchanged.

## References

Pinned hg-engine `61b510cfb6cf7d77c3b083150fad3499f82fd326`,
`src/individual/CalcBaseDamage.c`, corroborates stage-before-offensive-modifier
placement; its Unaware-before-Foul-Play selection is deliberately not copied.
Expansion `c460a8661dfa0598ae25d42a968c690ecbf489c6`,
`CalcAttackStat`, selects source, filters crit/Unaware, applies stage, then
modifiers. Showdown `82f129e0b847bf23395d552f9bb48eb82e53a0ec`,
`pokemon.calculateStat`, `battle-actions` and ability callbacks establish the
modern stage floor and modifier ownership. The ignored damage-layers roadmap
contains the broader unresolved arithmetic and route work; it is not changed
by this prerequisite.

## Verification and handoff

- [x] Add meaningful failing actual-production-function and real trainer-AI
  tests before production changes. The clean RED run has 26 modern-only
  assertion failures across seven test methods; legacy cases pass.
- [x] Pass those seven methods across all eight independent flag combinations
  after the implementation (14.710s). Literal L50/BP100/Defense100/no STAB,
  neutral/roll100: raw101, stage+1, Huge/Pure Power gives 134 modern versus
  135 legacy; special offense with Deep Sea Tooth has the same discriminator.
- [x] Cover all 13 stages, crit markers 1/2/3, abilities plus original items,
  Foul/Body source ownership, both Unaware owners, Mold Breaker/suppression,
  Simple stored changes/suppression/loss, Solar Power/Plus/Minus, all seven
  stored intrinsic-power stages, real trainer AI with supplied variance100,
  unchanged raw/stored stats and zero added RNG. The retained sequential-group
  oracle deliberately isolates this phase from future full modifier rounding.
- [x] Pass 51 affected SDK-free host checks in 61.624s: D1a, selected stats,
  rules, Snow native paths, Simple native paths, original ability native paths
  and A14 native paths. Log:
  `.local-tools/validation/gen9-stage-order-focused-final.log`. RED and initial
  GREEN logs use the same prefix with `red.log` and `green.log`. Tracked diff
  checks and explicit whitespace checks include both new untracked files;
  source/test/document hashes are frozen in the local handoff JSON.
- [x] Fresh independent specification and quality reviews passed. Each reviewer
  independently ran the six D1a methods and selected-stat boundary check across all eight flag combinations; the
  quality review also verified all five frozen hashes and whitespace.
- [x] Parent-owned SDK game compile and paired ROM/resource/layout/native build
  passed. A fresh matching, data-only RAM fixture produced 134 damage versus
  the baseline 135, with the same seed12, 18 RNG calls and final RNG state.
  All 1700 compared native battle frames matched every ARM9 instruction, with
  zero fallbacks, guard failures or evictions. All seven validation saves and
  frozen production/test hashes remained unchanged.

The 253-test sweep belongs to the preceding f673 integration. D1a was verified
with the 51 affected host checks, both reviews, paired build and native proof;
it does not claim a new full-suite run. Dedicated confusion damage,
delayed Future Sight and Beat Up remain separate compatibility-route gaps;
this change does not establish full Gen IX damage or all-route parity.
