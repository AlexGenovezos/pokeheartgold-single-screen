# Next14 ordinary Gen IX moves (A14)

Approved development scope: extend the default-off `QOL_MODERN_MOVES` adapter
from52 to66 IDs for the original493 roster/story. Preserve the reviewed Snow
changes, original move IDs, `NUM_MOVES=467`,16-byte `MoveTbl`,468-entry embedded
AI table, saved structures and the existing private learnset capacity28.

The cohort is Hone Claws471, Quiver Dance486, Coil492, Work Up529, Shell
Smash507, Cotton Guard541, Acid Spray494, Flame Charge491, Trailblaze888,
Venoshock477, Hex509, Stored Power503, Power Trip684 and Acrobatics515.
These are hg-engine IDs (official IDs plus its three placeholders).

- [x] Observe focused failures before production implementation for metadata,
  actual stat events, intrinsic power, learnsets and guarded script composition.
- [x] Add literal metadata, full names/descriptions and independently checked
  plain native animation aliases. Keep archive extent899 and private card829.
- [x] Regenerate318 overlay rows for223 species; preserve max5 additions,
  max22 actual merged moves plus sentinel, and capacity28. Stop native packed
  parsing at0xFFFF before alignment padding. Retain level0/level1 evolution
  rows, form boundaries and all creation/relearner/daycare/field readers.
- [x] Append private effects277..283 and descriptors145..150. Native Acid
  Spray effect271 is reused unchanged. Cotton descriptor150 is decoded before
  the native >=46 formula and requests one Defense+3 event, with actual delta
  clipping and the modern Simple foundation when that separate flag is enabled.
- [x] Generate five stat scripts299..303 with all-stat prechecks, silent capped
  skips, sequential central12 calls and native announcement/animation flags.
  Shell Smash drops Def/SpDef first, then raises Atk/SpAtk/Speed2. Item handling
  occurs after the full script; self drops cannot trigger Competitive.
- [x] Guard full original template sources and unchanged SDK/NARC parity before
  adapting native10,138 and Bulk Up150. New scripts receive explicit SDK
  compilation and native-command VM checks; original `.s` files are unchanged.
- [x] Preserve independent flag composition: moves-only reserves297/298 as safe
  End members; combined applies Cursed/Competitive, Oblivious and Simple at
  exactly299 before the A14 append. Both move-enabled paths end at304 subscripts
  and284 effects. Default/type-only archives remain original; battle-only stays299.
- [x] Supply the existing nine stat-message triplets in moves-only too. Combined
  produces them once before Snow, leaving bank197 at1285 messages and retaining
  its key/encoded control words. Ability descriptions remain battle-only.
- [x] Resolve intrinsic conditional power in shared `CalcMoveDamage`, before
  external multipliers and Technician. Honor explicit power overrides; execute
  the actual trainer AI caller against the same shared path, without new RNG.
- [x] Ban Trailblaze from Metronome after the Mimic separator. None of this
  cohort is a sound/punch/Substitute-bypassing move.
- [x] Complete focused SDK VM verification, self-review and documentation.
  Parent owns fresh independent spec/quality reviews, the combined suite and
  paired native validation.

Power semantics: Venoshock doubles only for poison/toxic; Hex only for major
status. Stored Power/Power Trip read all seven stored stages once, count only
positive boosts and reach860. They neither cancel boosts with drops nor
reinterpret Simple/Unaware. Acrobatics doubles only when the raw held item is
absent, including after consumption/removal; Klutz/Embargo do not remove items.
Technician eligibility uses resolved intrinsic power, including the native
`POWER_MULTI` conditional-power step, before Charge/Helping Hand. Its multiplier
stays at the existing application/rounding point. Thus item-held Acrobatics55
with Helping Hand becomes82 then123, Stored Power60 becomes90 then135, and
Stored Power80 becomes120 without Technician. Charge40 becomes80 then120.
Native doubled Pursuit40→80, Payback50→100 and Revenge60→120 remain ineligible.
Explicit supplied power still bypasses the new intrinsic-power helper; its
resolved value participates in the same native threshold calculation.

Access boundary: the new109 level rows provide the pinned original-roster
level/evolution routes. Trailblaze has no level rows. No TM reassignment, tutor
expansion or egg conversion is included; battle support does not imply every
move is obtainable yet. The six selected-stat B6 moves, weight-ratio moves,
future abilities and complete Gen IX damage/modifier ordering remain separate.
No native AI setup-scoring policy is added for the private status effects.

Sources and credit remain BluRosie's hg-engine
`61b510cfb6cf7d77c3b083150fad3499f82fd326` and rh-hideout's
pokeemerald-expansion `c460a8661dfa0598ae25d42a968c690ecbf489c6`.
Shell Smash deliberately follows expansion's Gen IX drop-first order rather
than hg-engine's boost-first subscript. Private IDs are local allocations,
not claims that upstream effect numbers are interchangeable native scripts.

Existing d56188b6c built artifacts predate Snow and A14. This source has not
been installed, and no real save or live application was changed. Focused logs
are ignored `.local-tools/validation/gen9-next14-focused-*.log` artifacts.

Focused verification before handoff:

- After the Technician review correction,67 affected host tests passed
  in28.861s, including the strengthened evolution/creation cases and new
  exact-value intrinsic/external-power boundary regressions.
- Explicit serialized SDK assembly of all new sources and unchanged native
  templates completed in the initial138.751s lane. Original SDK/NARC parity
  passed. The first semantic run exposed an instrumentation counter using
  the wrong presentation opcode; production scripts required no correction.
- Four SDK/native-command semantic tests passed in2.122s after correcting the
  fixture. This run reused18 assembled bytecodes from a source/macro/constants/
  tool fingerprint and output-SHA cache; native C compilation and VM execution
  ran fresh. It is semantic evidence, not a second fresh SDK build.
- The real encoded-message matrix passed separately: bank197 stays1276 with
  both flags off and1285 with either flag enabled, preserving all nine triplets.
  Only Snow's six reviewed original rows differ in combined mode.
- All17 frozen reviewed Snow index hashes matched. `git diff --check` passed.
  A14 remains unstaged; no native/global build, installation, commit or save
  mutation was performed.

A14 review correction: Technician eligibility is now captured after native
`ctx->powerMultiplier` resolves conditional power, but before Charge and Helping
Hand. Pinned expansionc460a8661dfa0598ae25d42a968c690ecbf489c6 resolves
Pursuit/Revenge/Payback in `CalcMoveBasePower`, then tests the unmodified result
in `CalcMoveBasePowerAfterModifiers`'s Technician branch. Native subscript153
sets `POWER_MULTI=20` for switching-target Pursuit. Source evidence is recorded
in `gen9-next14-technician-reference.log`. Regression RED/GREEN logs cover the
HH/Charge boundary, explicit60/80 overrides and all three doubled native moves,
through actual combat/AI C with both battle-flag settings. Only the eligibility
snapshot changed; external modifier grouping and rounding remain deferred.

Final review-correction verification supersedes the earlier focused semantic
run:67 affected host checks (28.861s) and4 fresh native-C/VM checks (2.122s)
passed. No SDK bytecode was reassembled because script/constants inputs were
unchanged; the existing18 source/profile/output-hashed bytecodes were reused.
RED logs separately show the missed HH threshold and the too-early-capture
native conditional counterexample; final GREEN covers both battle flags.
All17 reviewed Snow index hashes remained unchanged, and source remains
unstaged for fresh spec re-review followed by quality review.


## Integrated validation

The combined253-test suite passed in661.343s and the matching paired build
passed. Native Cotton Guard stored+6 Defense with Simple versus+3 for its
control, with readable drastic-rise text. Shell Smash stored+4 Attack, Special
Attack and Speed; White Herb restored both defensive drops and was consumed
after the sequence. These6400 compared frames had zero fallbacks/guards.

See [QOL-REUSE.md](../../QOL-REUSE.md#combined-snow-and-twenty-move-integration)
for all seven comparisons, routing-test corrections and evidence boundaries.
No installation or real-save mutation occurred; remaining move access and
complete Gen IX damage grouping remain separate work.
