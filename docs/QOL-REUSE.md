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

