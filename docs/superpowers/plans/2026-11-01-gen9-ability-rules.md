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
- [x] Fairy Pokédex search/filtering uses the same current species types as
  summaries and battles, including caught checks and both selected types.

The source-compiled weather and absorption transforms require exact original
byte parity and fail on source drift. Existing ROM resources are preserved.
113 host tests and a full native build passed. Native lockstep also passed
Ground/Lightning Rod, Fairy search, and 5/8-turn weather setup fixtures; see
`docs/QOL-REUSE.md` for the measured frame counts and evidence limits.

## Remaining implementation

- [ ] Port Sturdy survival, modern Flash Fire/absorption details, Oblivious
  Taunt immunity, Intimidate immunities and other changed original abilities.
- [ ] Implement Cursed Body (130), Competitive (172), Neutralizing Gas (internal
  240), Wind Rider (241) and Sharpness (242), including ability suppression,
  reactivation, move classifications, AI and descriptions. Upstream's empty
  Neutralizing Gas handler is not an implementation.
- [ ] Extend ability name/description resources with native internal IDs while
  preserving old bank entries. Keep full credits for reused implementations.
- [ ] Apply the 13 changed standard species slot pairs only after their effects
  are ready: Jigglypuff, Wigglytuff, Gengar, Koffing, Weezing, Igglybuff, Shiftry,
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
