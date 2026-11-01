# Targeted original ability calculations and immunity

The approved ordinary Generation IX battle scope preserves the original roster,
story, native layouts and stored ability bytes. This batch changes behavior only
under `QOL_MODERN_BATTLE`; the default remains off. The existing staged
Competitive implementation is a separate reviewed baseline.

- [x] Execute real accuracy and stat-change C functions: Keen Eye and Illuminate
  ignore every target evasion stage while retaining user accuracy and other
  factors; Illuminate also blocks accuracy drops, respecting suppression and
  opposing Mold Breaker.
- [x] Execute real damage C: Plus/Minus accepts either ability on a distinct,
  living active ally. Bound the scan to actual battlers, preserve singles and
  hypothetical AI calculations, and leave physical damage unchanged.
- [x] Execute real immunity/accuracy C and original Flash Fire script: absorb
  Fire damage and Will-O-Wisp while frozen and before accuracy. Preserve Protect,
  semi-invulnerable failures, suppression, Mold Breaker and charge-turn behavior.
  Preview remains read-only and agrees about frozen Flash Fire.
- [x] Update only Keen Eye/Illuminate entries in bank722, retaining pinned source
  hashes, original binary parity, name banks and extended Cursed Body/Competitive.
- [x] Observe focused tests fail before implementation, then pass modern on/off.
  Run the full host/SDK suite serially, record
  `.local-tools/validation/gen9-original-ability-batch1-tests.log`, inspect the
  diff and whitespace, and retain reuse credits. Leave new edits unstaged for
  independent spec and quality reviews and combined native validation.

References remain pinned in `docs/QOL-REUSE.md`: expansion
`c460a8661dfa0598ae25d42a968c690ecbf489c6` (battle_util accuracy, Plus/Minus,
Flash Fire and stat_change Illuminate) and hg-engine
`61b510cfb6cf7d77c3b083150fad3499f82fd326` (CalcBaseDamage/Flash Fire).
No later original-ability batches, new ability IDs or species pairs are included.

Both review stages approved. The review regression gates modern Keen Eye and
Illuminate on accuracy before querying the mutating Mold Breaker helper; the
flag-off ordering stays original. The final156-test host/SDK suite passed in
271.518s. The paired native build and copied-save validation passed in the combined
52-move milestone; frozen Flash Fire retained freeze and full HP after activation.
