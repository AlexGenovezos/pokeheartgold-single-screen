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

The corrected Gen IX comparison found 111 existing moves with numeric differences:
61 power, 31 accuracy, 29 PP, seven priority, five target-range, four type and
three effect-chance changes (some moves have several). The earlier 109-move
comparison used upstream's default Champions alterations and was not a valid
Gen IX profile. `tools/qol/hg_import.py` now exports the pinned source with all
five Champions switches explicitly disabled. Updating numbers alone would leave incorrect
effect scripts, abilities and AI behavior. Examples include Knock Off, Leech
Life, Hidden Power and recovery moves. On 2026-11-01 the user explicitly approved modern moves and updated abilities
for the existing Pokémon. No later-generation Pokémon are required. The approved
scope is recorded in `docs/superpowers/specs/2026-11-01-gen9-battles.md`.

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
| Data and save compatibility | Keep roster/story, learned-move IDs and save layout stable unless an explicit expansion requires migration. Test existing PP above newly reduced maxima, stored abilities/stats and old saves. Audit move effect/script changes alongside the 111 numeric differences. |

Retain hg-engine credits/reuse terms with any actual code or asset port. Do not
claim Generation IX parity until the individual mechanics and full native build
have been tested. Mega Evolution, Z-Moves, Dynamax and Terastallization are
separate features, not implied by updating the ordinary battle rules.

## Approved expansion and implementation coverage

The user approved modern moves and updated abilities on 2026-11-01. The
reproducible data export is:

```sh
python3 tools/qol/hg_import.py .local-tools/hg-engine .local-tools/gen9-profile.json
```

It checks the exact Git revision/clean source, compiles an explicit Gen IX data
profile, exports metadata and modern base-roster learnsets, and refuses to
replace an existing output. It is data/export tooling, not automatic gameplay
implementation. The original-roster profile excludes partner-only Let's Go
moves, Legends-only profiles, later-generation Pokémon and custom moves.
178 later-generation moves occur in these level/egg/machine/tutor learnsets;
26 are flagged unimplemented by this upstream configuration. 109 share an
original effect-script ID, but many also need calculator/controller hooks;
69 need 59 distinct additional effect IDs. Sharing a script ID is not proof of
implemented behavior. Neutralizing Gas also has an empty upstream entry handler
and needs an actual suppression/reactivation implementation here.

Keep original move IDs 0–467. hg-engine reserves placeholder members 468–470,
so its later IDs are official IDs plus three (Moonblast is engine 588 / official
585). A single explicit import mapping must cover data, names, animations,
scripts and learnsets. Existing packed level-up entries only hold nine-bit move
IDs; modern entries need a wider format and consumers updated together. Do not
enlarge `TrainerAIData.moveData` casually: it is embedded in `BattleContext`
and would move ABI offsets. Use a separate extended move accessor/table or
fully audit and rebuild every dependent consumer.

The fixed roster's standard+hidden ability union can fit existing byte fields.
The exporter preserves legacy IDs and maps Neutralizing Gas 256→240, Wind Rider
274→241 and Sharpness 292→242, checking for collisions. This avoids changes to
saved Pokémon, battle structs, packets, recordings and summary layouts. Saved
Pokémon still need a deliberate ability-slot migration, and each mapped ability
needs real battle behavior before the updated slot is enabled.

Development source currently adds independently disabled modern-type,
core-rule and expanded-move flags. The first move batch implements Disarming
Voice, Draining Kiss, Play Rough, Moonblast and Dazzling Gleam. Its private wide
learnset adapter adds 66 level-gated entries for base forms while preserving
original moves and the saved Pokémon/battle layouts. Creation, level-up,
evolution, daycare, tutoring checks and relearning share the adapter. Alternate
forms retain their original tables until separately imported. Source-generated
resources extend the original archives without replacing their existing IDs;
short card labels keep the effectiveness indicators readable.

Draining Kiss restores three quarters of damage with the original Big Root,
Liquid Ooze and Heal Block paths retained. Modern sound moves bypass Substitute
for damage and move effects, while Soundproof and Mold Breaker still apply.
The battle-resource transform also adds current Electric-type paralysis
immunity. Original script compilation must exactly match each archive member
before a modified source copy is assembled. Spec and code quality reviews
approved this scoped first batch; full native validation is recorded separately.

Build all three development pieces together with:

```sh
QOL_MODERN_TYPES=1 QOL_MODERN_BATTLE=1 QOL_MODERN_MOVES=1 \
    ./scripts/build-qol-native.sh ../ssrecomp-qol
```

The next development milestone adds a selectable Fairy Pokédex search using
current personal types, finite 5/8-turn ability weather, and modern Lightning Rod
and Storm Drain absorption with Special Attack boosts. The native controller
lets absorption take precedence over Ground's Electric immunity and bypasses
the accuracy roll while preserving Protect and semi-invulnerable failures.
The preview and AI flags recognize both immunities. Hail still uses its original
semantics; the Generation IX Snow conversion remains separate work.

Validation: 113 host tests passed and the full matching source/ROM/native build
succeeded. Native/interpreter lockstep passed 1,700 frames in a Ground-type
Lightning Rod battle, 1,500 selecting and running a Fairy Pokédex search, and
300 for each of the 5/8-turn weather setups. All these comparisons had zero
interpreter fallbacks and guard failures. The isolated test battle displayed
Lightning Rod's Special Attack boost; Fairy search returned Clefairy. Reading
the isolated snapshots using the compiler's struct offsets confirmed temporary
rain with weather counters 5 without Damp Rock and 8 with it. Spec and quality
reviews approved each scoped change.

The modern build is not installed. Remaining known
integration work includes the modern combined
final-damage modifier chain, the remaining new moves/scripts/learnsets, modern status/weather
rules, abilities and saved-slot migration. Record each port's tests and native
runtime evidence before enabling it in the installed app.
