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

The second ordinary-move batch expands support to17 extended moves and106
base-form level entries. It adds Fairy Wind, Leafage, High Horsepower, Brutal
Swing, Drill Run, Smart Strike, Aqua Cutter, Precipice Blades, Origin Pulse,
Petal Blizzard, Boomburst and ordinary non-Terastallized Tera Blast. Full names
stay in the existing name banks; private bank829 supplies short card labels.
Both private full-name destinations allow32 slots with modern moves enabled,
including the battle party menu previously limited to15 glyphs plus terminator.
All120 host tests passed. The matching native rebuild passed1700 lockstep
attack frames and600 Check Moves frames with zero fallbacks/guard failures,
and rendered Precipice Blades in full. Spec and quality reviews approved the
batch after the text-capacity regression was fixed.

Modern Sturdy is also verified: it preserves1HP from a lethal hit at full HP,
honors Endure and ability suppression/Mold Breaker, and precedes survival items
without consuming their RNG or item. The shared survival command covers Pursuit
and retained delayed-hit scripts while excluding confusion. Multihit messages
announce an early Sturdy survival without duplicating final effectiveness text.
Ability descriptions in722 reflect Sturdy and modern Rod/Storm Drain behavior.
All131 host tests passed after serializing SDK checks with the game build;
concurrent Wine jobs had caused a transient timeout, which passed on retry.
The full native build and two1700-frame lockstep comparisons passed with zero
fallbacks/guard failures: full-HP Geodude ended at1/21HP with Focus Sash275 still
held; the chipped control fainted with its unused Sash still held. The snapshot
checks used the compiler's member offsets. Full Future Sight/Doom Desire rules
remain part of the remaining delayed-hit conversion.


## Cursed Body and original-save Gengar milestone

The development ruleset implements Cursed Body130 before assigning it to
Gengar. It activates on actual damaging hits, including non-contact attacks
and fainted holders, respects suppression, and keeps reactive behavior against
Mold Breaker. Called-move attribution, intercepting Pursuit, later multihit
strikes after Substitute breaks, and completed U-turn replacement protection
have focused executable coverage. Cursed Body and ordinary modern Disable use
four residual phases. Full delayed-hit modernization remains pending.

All three personal-data loaders return Gengar's supported modern ability pair.
The existing-save getter maps only base Gengar's stored Levitate to Cursed Body
without changing saved data or native layouts. Nonstandard stored choices are
preserved. Full names, uppercase names and descriptions extend banks720/721/722
through130 with original-source/binary parity checks. Easy Chat's original
ability words and the original ability count remain unchanged.

Both independent reviews approved this scope. The final140-test host suite
and full matching ROM/native build passed. A copied-save Gengar with raw stored
Levitate loaded ability130, activated against non-contact Water Gun, and left
move55 disabled with three residual phases remaining after the activation turn.
The1700-frame native/interpreter comparison passed with zero fallbacks and
zero guard failures. The broader boot fixture had1.63% fallback and54 overlay
evictions, so the zero-fallback observation applies to the stable battle
comparison. Save hashes remained unchanged; installed artifacts and the real
save were not replaced.

## Competitive development milestone

Competitive172 now follows each actual opposed stat reduction with a two-stage
Special Attack increase, including each separate Tickle/Memento reduction and
Intimidate recipients. The native stat command checks final clamped stages;
blocked reductions, allies, self reductions, unowned side effects and fainted or
suppressed holders do not activate it. Reactive Competitive remains active
against Mold Breaker. Intimidate provenance is checked while its owner is the
causal attacker, before its script restores the original attacker.

The implementation uses bit0 of native statChangeFlag: its original producer
masks to bits23–31, its original reader checks bit27, and no script variable
exposes it. The marker is cleared before every stat-command early return and
consumed only at subscript12's End. Presentation298 replaces the completed12
without growing the native four-frame stack. Native layouts and Easy Chat's
original ability count remain unchanged. Names/descriptions extend banks720,
721 and722 through172; unused IDs retain placeholders, Cursed Body130 survives,
and original source hashes and SDK/binary parity guard resource generation.

All three personal loaders expose [Cute Charm, Competitive] for Jigglypuff,
Wigglytuff and Igglybuff, and [Marvel Scale, Competitive] for Milotic. The save
getter reads the raw personality directly and converts only base-form odd-PID
original standard ability bytes. Other stored bytes, forms and species remain
unchanged; no saved data is rewritten. Gengar's existing Cursed Body adapter
continues to apply.

Behavior was cross-checked against BluRosie's hg-engine revision
`61b510cfb6cf7d77c3b083150fad3499f82fd326`, particularly
`src/individual/btl_scr_cmd_33_statbuffchange.c`,
`src/battle/battle_script_commands.c` and subscript12, and the
rh-hideout pokeemerald-expansion revision
`c460a8661dfa0598ae25d42a968c690ecbf489c6` Competitive script handler.
This milestone uses new native-layout integration rather than their expanded
battle state, opcode tables or addresses. Existing upstream credits and reuse
terms remain applicable to the broader project.

Focused host tests execute native stat mutation/return commands and the original
SDK Tickle, Memento and Intimidate bytecode. They cover per-stat ordering, two
Intimidate opponents, restored attacker, full stack depth, clipped boosts and
message1087 revealing the correct ability holder to trainer AI. This is ability
knowledge integration; no Competitive-specific AI scoring is claimed. A complete
matching ROM/native build and copied-save gameplay validation passed with the
combined52-move milestone recorded below. Installation awaits the complete
modern ruleset.

The final serialized host/SDK suite passed149 tests in260.647s, including the
inactive-recipient regression found during spec review and real presentation298
returns at depths0–4. All36 progress-tool tests also passed. Evidence is in
`.local-tools/validation/gen9-competitive-tests.log`; the isolated storage-harness
compile regression and strict nonmutation checks are recorded in
`gen9-competitive-storage-regression.log`. The installed game remains separate from these development artifacts.

## Targeted original-ability calculations and Flash Fire

Under `QOL_MODERN_BATTLE`, Keen Eye and Illuminate ignore all target evasion
stages while retaining the user's accuracy stages and other accuracy factors.
Illuminate also shares Keen Eye's accuracy-drop protection, including native
suppression and Mold Breaker handling. Their bank722 summary descriptions now
state both battle effects, with original source/binary parity and font bounds
still checked. Name banks and ability IDs are unchanged by this batch.

Plus and Minus accept either ability on a distinct living active ally. The
shared damage calculation bounds its scan to actual battler slots and excludes
the user, inactive slots, fainted partners, opposing battlers and suppressed
abilities. This also covers callers that estimate damage for trainer AI without
inventing an ally in singles or changing native battle layouts.

Flash Fire absorbs damaging Fire moves and Will-O-Wisp while frozen and before
accuracy is rolled. The following controller phase still blocks absorption for
Protect and semi-invulnerable states. Normalize, dynamic move-type overrides,
suppression, Mold Breaker and charge turns retain their native handling. The
read-only effectiveness preview agrees about frozen Flash Fire without changing
Mold Breaker flags. The unchanged original subscript179 handles first and repeated
activations; SDK assembly must match the original archive before execution tests.

Behavior references and credits: rh-hideout pokeemerald-expansion
`c460a8661dfa0598ae25d42a968c690ecbf489c6`, `src/battle_util.c` (evasion,
Plus/Minus and Flash Fire) and `src/battle_stat_change.c` (Illuminate), and
BluRosie's hg-engine `61b510cfb6cf7d77c3b083150fad3499f82fd326` damage and
Flash Fire handlers. The implementation adapts these rules to the retained
native SoulSilver structures rather than importing expanded battle state.
Existing upstream credits and reuse terms remain applicable. This batch does
not implement later original-ability updates or change species ability pairs.

Both independent review stages approved this batch. The final156-test
host/SDK suite passed in271.518s, including a regression ensuring unrelated
stat drops cannot announce a Keen Eye/Illuminate Mold Breaker bypass. Modern
mode checks accuracy before querying those abilities; default mode retains
the original ordering. Combined native validation is recorded below.

## Next 35 ordinary modern moves

The development move adapter now supports52 extended IDs: the prior17 plus
Sludge Wave, Low Sweep, Scald, Inferno, Volt Switch, Struggle Bug, Electroweb,
Wild Charge, Dual Chop, Razor Shell, Leaf Tornado, Snarl, Icicle Crash, Play Nice,
Mystical Fire, Baby-Doll Eyes, Nuzzle, Power-Up Punch, Dragon Ascent, Lunge,
Psychic Fangs, Liquidation, Breaking Swipe, Skitter Smack, Flip Turn,
Dual Wingbeat, Scorching Sands, Psyshield Bash, Raging Fury, Wave Crash,
Headlong Rush, Raging Bull, Pounce, Chilling Water and Twin Beam.

The shared literal rows retain hg-engine revision
61b510cfb6cf7d77c3b083150fad3499f82fd326 and its existing reuse credits/terms.
Three corrections are explicit: Wild Charge uses native effect48 for quarter
recoil (Wave Crash retains198 for one third); Scorching Sands uses125 so both
native frozen-attacker branches recognize self thaw; Psychic Fangs has15PP,
verified against pokeemerald-expansion revision
c460a8661dfa0598ae25d42a968c690ecbf489c6 rather than hg-engine's10PP.
All35 aliases contain only GoToEffectScript. Native King's Rock flags are
translated explicitly rather than copied from the upstream flag namespace.

Snarl is registered in both sound consumers and bypasses Substitute; Play Nice
has an explicit visual Substitute bypass, Protect bypass and Magic Coat
eligibility. Power-Up Punch and Headlong Rush use Iron Fist. The eight native
Metronome exclusions follow the Mimic sentinel, retaining Mimic legality.
Modern screen-breaking attacks leave screens intact on immunity, protection
and misses; successful screen breaks still run before HP damage, and their
native damage effect bypasses screen reduction. Successful Scald and
Scorching Sands hits thaw frozen targets only after actual HP damage. Completed
pivot protection uses the flag set by native subscript175 after withdrawal:
called pivots and intervening Pursuit can leave both move IDs naming the caller,
so the replacement Pokémon must not acquire the caller's Choice lock. The
subscript's contact and item timing and the completed-pivot Cursed Body guard
remain intact. A later multi-hit strike that reaches actual Pokémon HP clears
only the stale Substitute-hit marker, so contact abilities and reactive items
can activate after the first strike breaks Substitute. The marker still blocks
the breaking strike, other self-turn flags remain intact, and feature-off
behavior is preserved.

The reproducible pinned-profile overlay contains209 rows across160 base
species, with at most5 additions (Gardevoir). The preliminary193-row/149-species
audit omitted16 legitimate Baby-Doll Eyes rows by not converting its name's
hyphen to an underscore. The actual original NARC plus overlay needs at most22
moves and a sentinel (23 records), within capacity28. Original packed learnset
members, saved IDs, native467 move limit, sixteen-byte MoveTbl and embedded
468-entry AI table remain unchanged. Full names, uppercase names, descriptions
and compact card labels use the existing private resource adapters.

Eleven new moves have no base-roster level rows in this profile: Scald,
Electroweb, Power-Up Punch, Psychic Fangs, Breaking Swipe, Skitter Smack,
Flip Turn, Scorching Sands, Psyshield Bash, Pounce and Chilling Water. The
prior Brutal Swing and Tera Blast also lack level rows. Battle support does
not imply TM, tutor or egg accessibility, or completion of all178 imported
candidates. Raging Bull implements base Tauros's Normal attack; Paldean
breeds are outside the roster. Future Sharpness and Strong Jaw handlers must
classify Razor Shell as slicing and Psychic Fangs as biting; the native flag
byte cannot express these classifications. No powder move is added here.

Deferred candidates retain their audited limits: Eerie Impulse's native61
script is empty; Tail Slap needs the modern multi-hit distribution; Infestation
needs modern binding damage/duration; Bulldoze needs Grassy Terrain handling;
Solar Blade needs its charge preamble and adverse-weather handling. These IDs
remain unsupported. The combined validation below covers this scoped milestone;
the installed app and real save remain unchanged.


## Combined52-move and ability validation

Both independent review stages approved Competitive, the targeted original
ability changes, and the35-move batch, including the post-Substitute regression
fix. The final177-test host/SDK suite passed in702.580s. The matching source ROM,
resource transforms, native layout/code generation and macOS native build passed.
A frozen source-hash record matched throughout verification.

Copied-save native/interpreter comparisons passed:

| Fixture | Measured result | Comparison frames |
| --- | --- | ---: |
| Odd-PID legacy Cute Charm Jigglypuff | Competitive172; Intimidate Attack−1, Special Attack+2 |2500|
| Even-PID legacy Cute Charm control | Cute Charm56; Attack−1, Special Attack unchanged |2500|
| Frozen Flash Fire Flareon versus Will-O-Wisp | Boost activated; freeze0x20 retained; HP24/24 |1700|
| Power-Up Punch | Attack+1 after a successful hit |1700|
| Twin Beam | Two-hit message/count2; target HP40→34 |1700|
| Wild Charge | Target damage10, user recoil2, matching quarter recoil |1700|

The four stable battle comparisons had zero interpreter fallbacks and zero
guard failures. The two entry comparisons include overworld-to-battle loading:
all instructions matched with0.38% fallback and14/13 overlay evictions. These
metrics must not be presented as zero fallback across all six runs. Snapshot
fields were decoded using the matching compiler's DWARF offsets. Original and
fixture save hashes remained unchanged after all runs, which used `--no-save`.

Evidence lives in ignored `.local-tools/validation/gen9-52-moves-tests.log`,
`gen9-52-moves-build.log`, fixture lockstep logs and matching artifact manifest.
The implemented52 moves and ability checkpoints remain a subset of the approved
Gen IX conversion;126 additional imported move IDs and other rules still need
work. No modern development artifacts have replaced the playable installed game.

## Oblivious, Intimidate and four ready species pairs

This development subset remains behind default-off `QOL_MODERN_BATTLE`.
Oblivious prevents move-based Taunt unless the move legitimately ignores its
ability. The existing entry/action-end cure selector retains Attract priority,
then clears Taunt on a second pass when both are present. Suppression delays
these cures; gaining or recovering Oblivious permits them. The selector uses
the active ability without borrowing an unrelated battler's Mold Breaker.

Subscript221 branches message7 before the native status-name formatter, which
only accepts0–6. Its Taunt cure preserves primary status and icon, reveals the
holder's ability through message1087, then uses native Taunt-end message1257.
The first two categories in the original status-cure message740 now explicitly
name the holder, recording the ability for AI. Confusion/Attract cures also
preserve an unrelated primary-status icon. Primary cures and sleeping
Nightmare cleanup retain their original paths. The Taunt end is inline, with
no new subscript or additional Call/stack frame.

Intimidate skips Inner Focus, Own Tempo, Oblivious and Scrappy after the
original same-side, Substitute and fainted checks. Plain native CheckAbility
uses the active, suppression-aware getter for this ability event. It cannot
inherit a move's Mold Breaker. Message727 identifies both holders through
explicit nickname/ability categories. The blocked path does not call the stat
subscript or create a Competitive event; the other doubles opponent still
receives its reduction and may activate Competitive once. Temporary Intimidate
owner attribution, speed order and original-attacker restoration stay native.
Ordinary Growl reductions remain unaffected by these Intimidate immunities.

The source generator pins complete original source hashes and checks unchanged
SDK output against original NARC bytes before compiling modified members132,
186 and221. The resource chain applies it after Competitive, preserving299
members, names, Cursed Body297 and Competitive298. Default/type-only paths do
not compile these scripts. Bank722 updates only Oblivious, Own Tempo, Inner
Focus and Scrappy descriptions; original bank parity, font bounds and all
existing extended names/descriptions through172 remain checked.

After native Hydration/weather readiness tests passed, the three existing
personal-data loaders enable Wingull [Keen Eye, Hydration], Pelipper [Keen Eye,
Drizzle], Torkoal [White Smoke, Drought] and Feebas [Swift Swim, Oblivious].
The stored getter converts only a base-form original first-ability byte with
odd raw personality to the new second slot. Even personalities, other stored
bytes and forms are preserved; Gengar and Competitive adapters remain intact.
No save bytes, personality values, native fields or ability IDs change.

References retain all existing credits and reuse terms: BluRosie's hg-engine
`61b510cfb6cf7d77c3b083150fad3499f82fd326`, particularly
`src/individual/ServerDoPostMoveEffects.c:Activate_AbilityHealingStatusCondition`,
`src/individual/BattleController_BeforeMove.c` and
`data/battle_scripts/subscripts/subscript_0186_INTIMIDATE.s`; and
pokeemerald-expansion `c460a8661dfa0598ae25d42a968c690ecbf489c6`,
`src/battle_script_commands.c:Cmd_settaunt` and
`src/battle_stat_change.c:IsIntimidateBlocked`. Native integration deliberately
uses suppression-aware checks instead of the hg-engine script's raw ability
comparison, retains Attract priority, and avoids its extra block-subscript Call.

Focused validation is recorded in ignored
`.local-tools/validation/gen9-oblivious-intimidate-focused.log`:46 final host,
resource, loader, encrypted-save and pipeline regressions passed; four actual
SDK/native-command VM tests passed; two existing finite-weather SDK tests and
pre-enable Hydration/reentry checks passed. Native encrypted getter tests cover
all256 stored bytes, both PID parities and all32 block permutations without
changing the encrypted136-byte record. All nonzero raw form bytes are preserved
by the four-pair adapter. Actual constructor selection and ability-update paths
agree. Script tests cover cure stack depths0–4, ability gain/recovery,
Taunt suppression/Mold Breaker/failures/duration/Protect, both doubles sides and
orders, unrelated Mold Breaker, correct AI holders and a single Competitive
activation on the other opponent. Hydration104→190 covers every primary status,
toxic counters, sleep/Nightmare, no rain, suppression, Cloud Nine/Air Lock and
fainted holders; existing weather tests cover5/8 turns, active source rocks,
expiration and no restart under matching weather.

These are focused host/SDK checks, not full native gameplay validation or
specialized AI move scoring. Independent reviews, the global suite and a
matching native build/copied-save comparison remain the parent workflow's next
steps. This task does not build, install, stage, commit or push. Taunt/Encore
duration modernization, Snow and later abilities/moves remain separate work;
the installed playable four-QoL game is unchanged.

### Modern Simple and X items

The next scoped modern-battle change stores Simple's doubled semantic changes
once, then uses the ordinary stored stage for damage, speed and accuracy. A pure
clamped-delta helper serves central move changes, audited self script arithmetic,
Rage and six X items. The latter use base+2 (Simple+4); Dire Hit retains Focus
Energy. Existing setters, exact copies/resets, stage swaps and native/save layouts
are unchanged. External move Mold Breaker can bypass Simple when the new change
happens, including positive Swagger/Flatter, and cannot erase an existing boost.

Behavior references retain BluRosie's hg-engine revision
`61b510cfb6cf7d77c3b083150fad3499f82fd326` and pokeemerald-expansion revision
`c460a8661dfa0598ae25d42a968c690ecbf489c6`, especially
`src/battle_stat_change.c:StatChanged` and
`src/battle_move_resolution.c:HandleMoveEffects`: Stockpile's Defense and Special
Defense counters count successful events once, while consumption sends their
negative counts through the current ability's semantic stat-change path. This
port keeps the existing counters and does not mistake effect161/162
(Spit Up/Swallow) for subscript161 (Close Combat).

Modern-only generated Starf210 routes through central12 and existing item
consumption290; X-item269 prints the locally captured actual item boost. Native
four-frame Call/Return checks cover held, Pluck and Fling chains. Nine new
side-aware messages append to bank197, cloning original encoded format controls
and replacing one literal adjective per row. Whole original source/binary hashes,
1276-row/key47860 checks and unchanged SDK parity protect the original resources;
all original rows, other banks, names and subscript299-member layout remain.
The bank829 trainer card, Cursed Body297, Competitive298 and the existing
Oblivious/Intimidate transformations are preserved.

The focused plan and evidence limits are recorded in
`docs/superpowers/plans/2026-11-01-gen9-simple-xitems.md`. These focused native C
and SDK tests are not a claim of complete Gen IX rules or full native gameplay
verification. The parent integration still owns independent reviews, the global
suite, paired native build and copied-save checks before any installation.


## Combined integration verification

The final combined Oblivious/Intimidate and Simple/X-item snapshot passed all
209 host/SDK tests in735.207s and a fresh paired game/resource/layout/native build.
Both independent spec and quality reviews passed before integration. The added
player-bag test executes selection, recovery and consumption for all six X items,
including successful use, cap/no-op behavior and exactly-once consumption.

Nine copied-save native/interpreter comparisons passed every ARM9 instruction.
Six stable battle segments (1700 frames each) had zero fallbacks or guard failures:
Taunt was blocked by Oblivious but affected its control (counter4); Simple Defense
Curl stored+2 Defense versus the control's+1; Simple Swords Dance stored+4 Attack
and visibly printed “drastically rose”; Pelipper's Drizzle with Damp Rock produced
rain with8 turns. Three entry segments (2500 frames each) matched instructions
with0.25% interpreter fallback and10 overlay evictions: Oblivious blocked
Intimidate while its control lost1 Attack, and Pelipper loaded Drizzle before its
rain script completed in the final stable segment.

All22 frozen source/test hashes and all six validation save hashes matched.
The native source remains b602f2d. This milestone is development verification,
not complete Gen IX parity or an installation; the playable four-QoL app and real
save remain unchanged. Remaining move/ability, Snow, timing and delayed-hit work
continues separately. Logs and isolated artifacts are ignored local validation
files and are not committed.
