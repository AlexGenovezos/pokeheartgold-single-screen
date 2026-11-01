# Effectiveness indicators implementation plan

**Goal:** Show numeric type matchups beside move names and per target when
choosing a target, without changing battle state or consuming random numbers.

**Architecture:** A read-only helper in `battle_util.c` uses the same
`sTypeEffectiveness` table and active-matchup checks as damage. It accounts for
current types, grounding, Foresight, Miracle Eye, suppressed abilities,
Normalize, Mold Breaker, absorption, Soundproof and Wonder Guard. Multipliers
describe type effectiveness, not STAB or final damage. Fixed-damage/status and
unpredictable variable-type moves show `?`, rather than a misleading multiplier.

For a single living opposing target, show each move's multiplier. With multiple
opponents, show `?` on the move cards and individual multipliers in the target
menu. Never use the previous turn's target. The information is always visible;
there is no new Pokédex-knowledge gate.

- [x] Add host C regressions for dual types, immunity, current target changes,
  state immutability, invalid targets, non-damaging moves and ability/field rules.
- [x] Implement the helper using the shared chart, without the damage helper's
  Mold Breaker message mutation or damage modifiers.
- [x] Add text labels to single-screen move cards and target selection. Increase
  local item storage together with the number of displayed strings; verify
  names, type, PP and indicators fit the real font/window dimensions.
- [x] Compile the ROM, verify a single-battle move menu and execution, and pass
  700 battle frames in instruction lockstep before installation.
- [ ] Verify double-battle target menus in native gameplay (host logic and
  independent review have passed).
- [ ] Keep labels on the same chart as the subsequent Fairy/Gen IX port.

Independent review confirmed target/state/menu-capacity handling and font fit.
Fixed-damage review findings now have regressions (Super Fang, Endeavor, Bide,
SonicBoom and Present). Existing font0 move names are at most 72px; fractional
labels are at most 24px, leaving a 4px gap inside the existing 108px cards.
The full QoL suite has 22 checks. Single-battle runtime/UI verification passed;
the paired native build is installed. Doubles runtime coverage remains open.
