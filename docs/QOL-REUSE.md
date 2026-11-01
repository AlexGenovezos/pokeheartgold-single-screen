# Existing work to reuse

Research checked on 2026-11-01. The requested battle target is **Generation IX**,
including Fairy typing for existing Pokémon. Additional Pokémon are a separate
scope. Implementation completeness must be checked feature by feature rather
than inferred from a project's generation label.

## hg-engine

Sources:
- [Project README](https://github.com/BluRosie/hg-engine/blob/main/README.md)
- [Configuration](https://github.com/BluRosie/hg-engine/blob/main/CONFIG.md)
- [C configuration](https://github.com/BluRosie/hg-engine/blob/main/include/config.h)

Reviewed main revision: `61b510cfb6cf7d77c3b083150fad3499f82fd326`.

The project already offers Fairy typing, reusable TMs, fast text, expanded moves
and abilities, and configurable later-generation behavior. Its current README
still describes some expansions as incomplete; this is not evidence of complete
Gen IX parity. Its documented input is English HeartGold, so it is an engineering
reference, not a drop-in SoulSilver patch. Retain its required credits and follow
its published reuse terms when porting any implementation. No hg-engine code
has been copied into this branch yet.

## HM-without-teaching precedents

[MoemonHGSS](https://github.com/KurisuArs/MoemonHGSS/blob/main/README.md) documents
reusable TMs and several field actions without learning their moves. Its listed
actions omit Surf and Fly, and the full patch intentionally changes sprites to
Moémon. It is a reference for the individual changes, not a recommendation to
install the whole patch for this project.

## Why these are not immediate native-app installs

The installed ssrecomp v0.4.2 recompiler's
[`load_sections_from_layout`](https://github.com/ClickingMaster/ssrecomp/blob/v0.4.2/tools/recomp.py)
checks each decompressed code section against a SHA-1 from the supplied layout.
It explicitly rejects changed sections. Copying a ROM hack into the app does
not provide matching translated native code or layout metadata.

Prefer reusing an established implementation over independently recreating
modern mechanics. Port only changes that match the chosen SoulSilver behavior,
generate matching native metadata/code, then verify them on a copy of the save.
If playing an existing complete ROM hack in an emulator is preferred, that is a
different route and should be an explicit choice; do not silently replace the
single-screen native game or its save.

## Remaining source investigations

- HM paths: `src/field/field_control.c` checks Surf and Waterfall before scripts;
  `src/scrcmd_party.c` queries known moves; the standard actions are in fetched
  `files/fielddata/script/scr_seq/scr_seq_0146.s`. Keep unrelated known-move
  queries truthful. Existing animations also require a valid actor.
- Fly: `src/field_move.c`, `src/start_menu.c` and the Pokegear map need an
  accessible field-action entry point without selecting a learned move.
- Menu bounds: `PartyMenu_OpenMonContextMenu` allocates only eight entries,
  the party menu reserves only four field-move strings, and its navigation
  tables depend on item counts. Adding eight HMs to every Pokémon's menu would
  overflow these structures. Use a dedicated field-action flow.
- Effectiveness: reuse active battle rules in `src/battle/battle_util.c`;
  `BattleControllerPacketSelectMove` currently carries move/PP data but no
  effectiveness values. The move-selection and target-selection stages are
  separate. Avoid inventing a selected target during double battles.


## Generation IX audit checkpoint (2026-11-01)

No modern rules have been enabled in the installed game. The installed
indicators currently use the original Generation IV battle chart. The hg-engine
configuration defaults to generation 9, but its default configuration also
expands abilities, items, saves and battle gimmicks. Importing those defaults
wholesale would change the agreed game/story and save boundaries.

Existing-roster Fairy typing covers 20 species:
Clefairy, Clefable, Jigglypuff, Wigglytuff, Mr. Mime, Cleffa, Igglybuff,
Togepi, Togetic, Marill, Azumarill, Snubbull, Granbull, Ralts, Kirlia,
Gardevoir, Azurill, Mawile, Mime Jr. and Togekiss. Reference:
`hg-engine/data/Species.c` at the reviewed revision.

The move-data comparison found 109 existing moves with numeric differences:
61 power, 30 accuracy, 29 PP, seven priority, four type and three effect-chance
changes (some moves have several). Updating numbers alone would leave incorrect
effect scripts, abilities and AI behavior. Examples include Knock Off, Leech
Life, Hidden Power and recovery moves. Move expansion needs an explicit decision
about newer moves/updated abilities; no later-generation Pokémon are required.
That clarification is pending, not silently treated as approval.

Port boundaries, to implement and validate before enabling a modern build:

| Area | Source integration and required checks |
| --- | --- |
| Fairy/chart | `include/constants/pokemon.h`, `src/battle/battle_util.c`: slot 9 can follow hg-engine's Fairy convention; add all Fairy interactions and remove Steel's Ghost/Dark resistances. Damage, AI and previews must share one chart. Test all 18×18 matchups plus dual types/immunities. |
| Species typing | `src/pokemon.c` personal loaders, including the open-NARC/form path, or a reproducible personal-data build transform. Cover all 20 species in existing saves, new encounters, summaries and AI. No save structure growth. |
| Move typing | Update Charm, Sweet Kiss and Moonlight to Fairy; Curse becomes Ghost. Preserve Hidden Power's exclusion of slot 9. Audit Conversion/random-type paths, not just direct move loads. |
| Type presentation | Type names use message bank 0735; sprite icons use `src/type_icon_resources.c`, NARC `a/0/0/8`, slot-9 character member 236. Supply source-generated Fairy artwork/name and test palettes, summary, Pokédex and battle menus. No ignored asset-only edits. |
| Critical hits | `TryCriticalHit`, damage commands and AI: base chance 1/24, +1 1/8, +2 1/2, +3 guaranteed; damage 1.5× and correct Sniper multiplication/rounding. Retain stat-stage bypass, armor/Lucky Chant and RNG semantics. |
| Status/turn rules | Burn 1/16, paralysis half speed, modern poison/Steel/Electric status immunities, powder immunity and Protect odds. Audit battle controller/scripts and AI together; do not add independent cosmetic approximations. |
| Weather/abilities | Port finite ability weather, changed ability effects, move-specific interactions and turn ordering from established implementations with focused differential tests. Hail versus Gen IX snow needs all consumers, not a text rename. |
| Data and save compatibility | Keep roster/story, learned-move IDs and save layout stable unless an explicit expansion requires migration. Test existing PP above newly reduced maxima, stored abilities/stats and old saves. Audit move effect/script changes alongside the 109 numeric differences. |

Retain hg-engine credits/reuse terms with any actual code or asset port. Do not
claim Generation IX parity until the individual mechanics and full native build
have been tested. Mega Evolution, Z-Moves, Dynamax and Terastallization are
separate features, not implied by updating the ordinary battle rules.
