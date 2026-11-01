# Modern abilities for the original roster

The approved target is ordinary Generation IX battles. Preserve the story,
roster, byte-sized stored ability fields and native battle/save layouts. Port
behavior before assigning any new ability to a species. The installed four-QoL
build remains playable during development.

## Verified existing-ability changes

- [x] Finite Drizzle/Sand Stream/Drought/Snow Warning: 5 turns, 8 with the
  matching active weather rock. Existing matching weather does not restart.
  The original held-item helper supplies Klutz/Embargo suppression. Magic Room
  state is not yet present and will join that shared helper when implemented.
- [x] Lightning Rod and Storm Drain: absorb matching damage/status moves and
  raise Special Attack by one, including capped-stat immunity. Keep native
  redirection, Soundproof/Mold Breaker, suppression and the original Motor Drive
  path. Absorption precedes Ground's Electric immunity and accuracy, but cannot
  bypass Protect or semi-invulnerable states.
- [x] Sturdy: survive direct lethal damage at full HP, with Endure before
  Sturdy before survival items. Cover Substitute, sound bypass, False Swipe,
  multihit and intercepting Pursuit, using the existing battle/save layouts.
  Source-generated messages reuse message625, and descriptions for Sturdy,
  Lightning Rod and Storm Drain replace only their entries in bank722.
- [x] Fairy Pokédex search/filtering uses the same current species types as
  summaries and battles, including caught checks and both selected types.

The source-compiled weather and absorption transforms require exact original
byte parity and fail on source drift. Existing ROM resources are preserved.
The earlier weather/absorption milestone passed 113 host tests and a full native
build. Native lockstep also passed
Ground/Lightning Rod, Fairy search, and 5/8-turn weather setup fixtures; see
`docs/QOL-REUSE.md` for the measured frame counts and evidence limits.

## Remaining implementation

- [ ] Port modern Flash Fire/absorption details, Oblivious
  Taunt immunity, Intimidate immunities and other changed original abilities.
- [ ] Convert Future Sight/Doom Desire to modern delayed-hit mechanics. Their
  retained Gen IV machinery stores precomputed damage and only the caster's
  battler slot, without caster identity or ability provenance. Sturdy currently
  reads the active delayed-hit recipient's ability, including suppression,
  without borrowing Mold Breaker from the current occupant of the caster slot.
- [x] Implement Cursed Body (130), including reactive on-hit behavior, the
  original Gengar save adapter, four-phase Disable and extended native messages.
  Both independent reviews, all140 host tests and the paired native build passed.
  Copied-save Gengar activated Cursed Body against Water Gun, with the expected
  disabled move55 and three residual phases remaining after that turn.
- [x] Implement Competitive (172), its four standard pairs, odd-PID original-save
  adapter and extended banks through172. Native stat reductions tail-dispatch
  presentation298 without stack/layout growth. Host/SDK verification is recorded
  in `2026-11-01-gen9-competitive.md`; independent review and native validation
  remain required before installation.
- [ ] Implement Neutralizing Gas (internal 240), Wind Rider
  (241) and Sharpness (242), including ability suppression,
  reactivation, move classifications, AI and descriptions. Upstream's empty
  Neutralizing Gas handler is not an implementation.
- [ ] Extend ability name/description resources with native internal IDs while
  preserving old bank entries. Keep full credits for reused implementations.
- [ ] Apply the remaining changed standard species slot pairs only after their
  effects are ready (Gengar is implemented): Jigglypuff, Wigglytuff, Koffing,
  Weezing, Igglybuff, Shiftry,
  Wingull, Pelipper, Torkoal, Feebas, Milotic and Gallade.
- [ ] Test a deliberate existing-save slot adapter. Preserve explicitly stored
  nonstandard choices; disambiguate original identical slots using the original
  personality rule. Do not blindly recompute every stored ability from PID.
- [ ] Complete Snow, modern turn ordering and the remaining core rules, with
  resource scripts, calculations, AI and UI using the same behavior.
- [ ] Rebuild and validate each integrated milestone on copied saves, then
  install only the complete verified ruleset with a recoverable backup.

The pinned hg-engine export contains 129 distinct standard ability IDs for
species 1–493. Five are newer than Generation IV; its wider standard-plus-hidden
union contains 162. Hidden-ability data does not add new story rewards or make
those abilities obtainable automatically.

Sturdy native validation: the matching source/ROM/native build and full131-test
host suite passed. Isolated full/chipped Geodude fixtures each passed1700 native
lockstep frames with zero fallbacks and guard failures. Full HP survived at1/21
and retained Focus Sash275; chipped HP fainted. Spec and quality reviews approved
the scoped implementation. The real save and installed artifacts were unchanged.
