# Existing work to reuse

Research checked on 2026-11-01. The requested battle target is **Generation IX**,
including Fairy typing for existing Pokémon. Additional Pokémon are a separate
scope. Implementation completeness must be checked feature by feature rather
than inferred from a project's generation label.

Before each new mod, search existing implementations and record the inspected
sources, revision, compatibility and reuse decision here and in its issue.

## X-menu input recovery (2026-11-02)

The existing `FieldSystem_SwitchBottomScreenApp` deliberately ignores a request
while an app is switching. The single-screen X-menu input gate can then reject
every key if the original return request was ignored. The source-level
reproducer executes those real menu and app-manager state machines, including
panel creation and cleanup call ordering. It does not establish the natural
trigger of the user's intermittent Instant-text report.

A private native fixture subsequently makes one ordinary app-switch call
while the X menu is open, then restores its original task. The older build
remains on app3 and rejects keyboard actions and closing; recovery returns to
app0, opens Options and closes to the field with Instant selected. The native
comparison passes instruction lockstep. This is an injected transition for
validation, not a captured player incident; its callback is never installed.

Scoped upstream issue searches did not identify a compatible existing fix.
Reuse the game's existing app-switch API, menu-panel destructor and `STATE_2`
initialization handshake for recovery; leave the global switch contract and
normal-build menu unchanged. No external implementation was copied. Track
native validation and the unresolved incident reproduction in
[issue #2](https://github.com/AlexGenovezos/pokeheartgold-single-screen/issues/2).

## Catching tutorial skip (2026-11-02)

[IronMONHGSS](https://github.com/PyroMikeGit/IronMONHGSS/blob/main/README.md)
documents SilverstarStream's intro-skip patch alongside broader dialogue,
frame-limit and story-scene changes. Its linked PokéCommunity page was not
accessible during this audit, so no claim is made about its internal tutorial
implementation or direct compatibility with the native app.

The public
[pokeheartgold-skipIntro Route 29 source](https://github.com/rahe3431/pokeheartgold-skipIntro/blob/a0bc795a057169f6b9b290ce39e5e3b68f2914de/files/fielddata/script/scr_seq/scr_seq_0225_R29.s)
still contains `catching_tutorial`; its inspected `ScrCmd_CatchingTutorial`
also calls `SetupAndStartTutorialBattle`. The repository name therefore does
not establish a reusable catching-only skip. The local pinned hg-engine source
was searched without finding an applicable isolated implementation.

Use the existing Route 29 reward and completion sequence for a small data-only
change: branch after follower reset/LockAll to the five-ball reward, then to
the original NPC hiding, route state, story flags and ReleaseAll. Close the
reward textbox before that second branch: the standard gift script returns
with it open, and ReleaseAll does not close it. Skip the
lesson dialogue, demonstration and movements that assume the old demonstration
positions. Keep script size and all executable/overlay bytes unchanged so this
change can use the matching native code. Validate both genders, reward-once,
control restoration and save/reload. Implementation and runtime acceptance are
tracked separately from the currently compiling controls/level-cap family.

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


### Gen IX Snow foundation (source awaiting native validation)

`QOL_MODERN_BATTLE=1` now interprets the original temporary/permanent Hail
bits as Snow. Hail258, its compatibility name, TM07, Pryce's story reward,
weather counters, overworld IDs and animation20 remain native. Default,
type-only and move-only profiles retain Hail behavior. No new move/ability IDs,
save fields or battle layout are introduced by this foundation.

Current Ice typing in either slot receives a Defense boost after the applicable
stage (including crit/attacking Unaware), with integer truncation before later
defensive abilities/items. Defense101 at+2 becomes303; neutral Snow followed by
Marvel Scale becomes226. The calculation honors its supplied weather argument,
so confusion/disobedience callers passing0 receive no Snow boost. Living active
Cloud Nine/Air Lock suppress weather; Mold Breaker does not erase Snow itself.
Ordinary special damage and existing Sand Sp. Def ordering remain separate.
Only non-Ice Hail chip is disabled; Ice Body and its native HP, hidden-position
and weather guards remain. Counter/Mirror Coat retain fixed returned damage.

The source-compiled effect164 duplicate check now covers both Hail bits, after
full-source hashing and unchanged SDK/NARC parity. Its native5/8-turn duration
still uses the attacker's active Icy Rock. Snow Warning252 stays with the
existing finite-weather owner, including source-holder rock ownership.
Blizzard, Snow Cloak, Forecast/Cherrim, Solar Beam and weather healing retain
native consumers of the same bits. Focused execution exposed two prior audit
assumptions that needed correction: AI damage had omitted Weather Ball's power
and type, and three type-query helpers left its no/suppressed-weather fallback
uninitialized. Modern-only paths now use weather power100/Ice or ordinary
power50/Normal; explicit supplied power is not doubled in the shared damage
function. Other active weather types remain selected by the existing queries.

Snow message generation follows Simple's guarded bank197 producer and validates
all nine appended templates exactly. It replaces only197 rows701–703/810–812,
221 rows282/334,622 row4,426 row43,157 row47 and749 row258. Source/binary hashes
pin each original bank, and encoded STRVAR/page controls, keys and unrelated
rows/names survive. Ability descriptions81/115/117 are updated by the existing
bank722 owner. No global Hail replacement occurs. The numeric trainer AI source
is also fully pinned; a generated modern assembly copy changes only the
same-width comparison operand at word5747 to-1, disabling the obsolete Hail-chip
heuristic without relocating jumps. Raw weather queries remain available for
duplicate-setter logic, including under weather suppression.

Focused host/SDK evidence is recorded in ignored
`.local-tools/validation/gen9-snow-focused-*.log`. Tests execute actual C damage,
weather, accuracy/type/form/healing/AI and Counter commands, compiled effect164
bytecode, existing finite-weather bytecode and guarded resource composition.
Flag matrices cover default, type-only, move-only, battle-only and combined
profiles; malformed inputs, source/binary drift and repeated transforms fail.
The existing52 extended moves/209 learnset rows remain untouched.

This source is newer than verified d56188b6c artifacts. Independent review,
global verification and a matching paired ROM/layout/native build with copied
saves remain pending. No installation or real-save change occurred. Snowscape,
Aurora Veil, Slush Rush, Chilly Reception and broader end-turn ordering are
separate work. Hydration's existing104→190 cure before poison/burn residuals is
correct for Gen IX and is unchanged.

### A14 ordinary modern moves (development source)

`QOL_MODERN_MOVES` now supports66 extended IDs: the previous52 plus Hone Claws,
Quiver Dance, Coil, Work Up, Shell Smash, Cotton Guard, Acid Spray, Flame Charge,
Trailblaze, Venoshock, Hex, Stored Power, Power Trip and Acrobatics. The literal
metadata, full names/descriptions, animation aliases and private card bank829
share the existing adapter. Archive extent899, original names750/751,
`NUM_MOVES=467`,16-byte `MoveTbl`,468-entry AI table and saved layouts remain.

Private effects277..283 and descriptors145..150 route through existing native
commands. Five generated scripts299..303 precheck every affected stat, skip
capped events, and call central12 sequentially. Cotton descriptor150 is decoded
before the legacy >=46 arithmetic and applies Defense+3 as one actual event;
modern Simple gives+6, while clipping can yield actual+1/+2. Moves-only retains
legacy Simple's derived interpretation and still receives correct Cotton text.
Shell Smash lowers Def/SpDef before raising Atk/SpAtk/Speed2; held-item processing
follows the entire sequence, and self drops do not trigger Competitive. Acid
Spray reuses existing native271; Flame Charge/Trailblaze use native138's
successful-hit attacker timing with a Speed+1 parameter.

All source templates are fully hashed and unchanged SDK/NARC parity is required
before adaptation. Original script sources stay intact. Move-only builds reserve
297/298 as safe End members; combined builds run the existing exact299 Cursed,
Competitive, Oblivious and Simple transforms before appending A14. Move-enabled
outputs have304 subscripts and284 effects. Battle-only stays299, and default/
type-only archives remain original. The original nine encoded stat-message
triplets are supplied once in either move-enabled or battle-enabled paths;
combined Snow retains its six reviewed replacements and bank197 stays1285.
Ability descriptions remain the battle-rule owner's responsibility.

A pure intrinsic-power helper runs in shared damage before existing external
multipliers/Technician, and explicit supplied power bypasses resolution.
Venoshock doubles for poison/toxic, Hex for major status, Stored Power/Power Trip
count positive stored stages across all seven stats through860, and Acrobatics
checks raw item absence. Simple is read once through stored stages; Unaware
does not erase intrinsic power. Technician55→82/60→90 and80/110 boundaries are
covered through the actual shared calculation and trainer AI caller, without
new RNG. This does not refactor broader Gen IX modifier grouping or ordering.

The regenerated overlay contains318 rows across223 base species, max5 additions
and max22 actual merged moves plus sentinel within capacity28. Native packed
learnset audits now stop at0xFFFF instead of counting alignment padding as a
level0/move0 entry. Quiver Dance's distinct level0/level1 entries and existing
form/evolution/relearner/creation/daycare/field-reader paths are retained.
Trailblaze has no level rows and is banned from Metronome after the Mimic
separator. No TM/tutor/egg expansion is included. Battle support and current
obtainability are separate milestones.

BluRosie's hg-engine61b510cfb6cf7d77c3b083150fad3499f82fd326 and
rh-hideout's pokeemerald-expansionc460a8661dfa0598ae25d42a968c690ecbf489c6 remain
credited/pinned sources. Shell Smash uses Gen IX drop-first ordering from the
expansion; the private effects are local native allocations. B6 selected-stat
moves, effective-weight moves, future abilities and full Gen IX completion are
separate work. See `docs/superpowers/plans/2026-11-01-gen9-next14-moves.md`.
Current d56188b6c artifacts predate Snow/A14; matching combined/native verification
and fresh independent reviews remain parent-owned. No installation or real-save
change occurred.

A14 focused verification after the Technician review correction:67 affected
host checks passed (28.861s), including strengthened evolution-fixture and
power-boundary regressions. Four SDK/native-command checks passed (2.122s);
the latter used18 source/profile/output-
hashed SDK bytecodes assembled in the initial serialized138.751s lane and ran
native C/VM semantics fresh. Original SDK/NARC parity and generated-source
assembly are distinct from this cached semantic rerun. All17 reviewed Snow
index hashes remained unchanged, and `git diff --check` passed. Logs remain
local ignored validation artifacts; fresh independent/combined/native checks
are still pending.

A14 review correction: modern Technician eligibility is captured after the
native intrinsic `POWER_MULTI` step and before Charge/Helping Hand, while its
multiplier remains at the existing native application/rounding point. With
Helping Hand, held-item Acrobatics55→82→123 and Stored Power60→90→135 qualify;
Stored Power80→120 does not. Charge40→80→120 qualifies. Doubled native
Pursuit40→80, Payback50→100 and Revenge60→120 remain ineligible. Explicit
supplied-power handling remains intact. This follows pinned expansion's
`CalcMoveBasePower`→`CalcMoveBasePowerAfterModifiers` separation and native
Pursuit153's `POWER_MULTI=20` source; it does not introduce the future general
modifier-chain refactor. Default/type-only retain native Technician behavior.

### B6 selected-stat ordinary modern moves (development working tree)

The adapter now supports72 extended moves after Psyshock, Psystrike, Foul Play,
Body Press, Sacred Sword and Darkest Lariat. Full names/descriptions/cards and
plain existing aliases use the shared literal rows. No effect/subscript/ASM or
message transform was added: move-enabled counts stay284/304, bank1971285,
archive extent899 and private cards829. Body Press's Metronome ban follows the
Mimic separator; none of these six is sound/punching/Substitute bypassing. A
future Sharpness classifier must include Sacred Sword.

Pure raw-offense/processed-defense/stage-ignore selectors feed shared native
damage and the real hit check without changing damage category. Psyshock and
Psystrike use Def stage → Snow → defensive modifiers while remaining special
for screens/items/history. Foul Play selects target raw Atk/stage, Body Press
user raw Def/stage, then both use the user's offensive modifiers. Crit and
Unaware apply after source selection: user Unaware does not erase Foul Play's
selected Attack stage; defending Unaware does. Sacred Sword/Lariat ignore all
target Defense/evasion stages while retaining user accuracy, Hustle, defensive
abilities/items and ordinary accuracy RNG. Moves-only retains legacy battle
modifiers and all three build flags stay independent.

The regenerated overlay has336 rows across237 base species (+18 rows), max5
additions and22 actual merged moves plus sentinel within28 slots. Mewtwo gets
Psystrike72, Gallade Sacred Sword1, Regigigas Body Press42. Darkest Lariat has0
level rows; its8 machine-compatible species need a future access port. Original
moves/roster/story/forms and native16-bit move/save/context/AI layouts remain.

The pinned hg-engine61b510cfb6cf7d77c3b083150fad3499f82fd326 and expansion
c460a8661dfa0598ae25d42a968c690ecbf489c6 remain credited. Expansion and pinned
Showdown82f129e0b847bf23395d552f9bb48eb82e53a0ec corroborate selecting raw
stat/stage before crit/defending Unaware; hg-engine's clear-before-replace
ordering is intentionally corrected. This does not complete Gen IX damage
ordering. Inherited offensive modifiers precede stages:101,+1,Huge Power gives
303 rather than Gen IX stage-first302, including Foul Play/Body Press. A future
shared offensive-stage/modifier correction, broader base-power/final-modifier
grouping/rounding and Sharpness base-power placement remain prerequisites to a
full-ruleset installation claim. Wonder Room, effective weights, future abilities
and access ports remain separate work.

Focused verification passed52 affected host C/data/resource/learnset checks in
`.local-tools/validation/gen9-next6-focused-final2.log`; fresh independent spec/quality
reviews, combined full-suite checks and matching native/copied-save proof remain
parent-owned and pending. d56188b6c artifacts predate Snow/A14/B6. No installation
or real-save/live-app write occurred. See
`docs/superpowers/plans/2026-11-01-gen9-selected-stat-moves.md` for scope and gates.


## Combined Snow and twenty-move integration

Fresh final integration passed all253 host/SDK tests in661.343s. Each of Snow,
A14 and B6 passed independent spec and quality review before the combined build.
The game, transformed resources, layout and matching native executable build
passed. The built ROM has899 move/data-script members,304 subscripts,284 effects,
830 message banks and1285 battle messages with original key47860.

Seven copied-save native/interpreter comparisons passed every ARM9 instruction
across15000 battle frames; all seven had zero interpreter fallbacks, guard
failures and overlay evictions. Measured outcomes:

- Snow/Icy Rock:8 total turns,7 after the first turn; both participants retained
  full HP, including the non-Ice target. The native “It started to snow!” message
  displayed correctly. Hail258 retains its compatibility name.
- Cotton Guard: stored Defense+6 with Simple versus+3 for its control; the
  native drastic-rise message displayed correctly.
- Shell Smash/Simple/White Herb: Attack, Special Attack and Speed+4, Defense and
  Special Defense returned to neutral, item consumed after the full sequence.
  The native White Herb recovery text displayed correctly.
- Psyshock:6 damage, inside the physical-Defense outcomes6/7 and outside the
  incorrect Special Defense outcomes9/10/12.
- Foul Play:3 damage, inside the target-Attack outcomes3/4 and outside the
  incorrect user-Attack outcomes5/6.
- Body Press:8 damage, inside the user-Defense outcomes7/8/9 and outside the
  incorrect user-Attack outcomes2/3.

These damage ranges use the inspected raw stats of deliberately edited test
saves, all16 random rolls and confirmed non-critical hits. They do not infer
natural species stats from the fixture labels. Native after-turn damage-history
scratch is reset; category/history and Substitute behavior are verified by the
actual-C host tests, rather than claimed from those final native snapshots.

The integration sweep exposed stale mocks in two routing tests after the A14
resource steps were added. Test-only corrections now mock those steps and assert
their enable flags, ordering and Snow input. Sixteen related host checks passed
before the final clean253-test run. No runtime code or tested artifacts changed
for those corrections. All35 frozen source/test/document hashes, seven copied-
save hashes and tested ROM/native/layout hashes matched before documentation.
Validation artifacts and logs remain ignored local files. Native source remains
b602f2d; the installed four-QoL app, real ROM and real save remain unchanged.

This milestone provides72 supported later-generation moves and336 level-learning
rows across237 base species. It does not establish complete Gen IX parity:
remaining abilities,106 imported move IDs, old-move and species-stat updates,
move access, status/turn/delayed-hit behavior and exact damage layers are separate
work. The inherited offensive-stage/modifier ordering at this integration point
is documented above; the D1a working-tree correction follows below. No incomplete
modern ruleset was installed.

## Offensive stage-order prerequisite (D1a)

Modern battle now floors the selected raw offensive stat's crit/defending-Unaware
filtered stage before the existing offensive modifiers. Foul Play keeps the
target's raw Attack/stage and Body Press the user's raw Defense/stage; the user
owns offensive modifiers and level. Modern Simple's stored changes remain
unchanged. Only local stages are consumed, once. The existing defending-Unaware
query moves earlier without adding RNG or duplicate ability queries; causal Mold
Breaker behavior and the user's late defensive Unaware branch are retained.
Battle-off, including moves-only and type-only, keeps legacy ordering and u16
offense. Modern local offense uses u32 without implicit u16 narrowing; synthetic
overflow exactness remains unresolved rather than inferred from widened locals.

The actual shared damage and real trainer-AI tests distinguish raw101,+1,Huge
Power: stage151 then doubled302 gives134 damage at L50/BP100/Defense100, versus
legacy stage-after-modifier303 giving135. Special offense with Deep Sea Tooth
and selected Foul Play/Body Press offense cover the same boundary. All eight
independent flag combinations retain their intended behavior. The test matrix
also covers every stage, crit markers1/2/3, offensive ability/item combinations,
Unaware/Mold Breaker/suppression, stored Simple stages and intrinsic-power stages.

This resolves offensive stage order only. Offensive and BP modifier grouping,
special-defense/Sand order, +2/spread/weather, burn/screens/final modifiers,
berries, AI variance/type placement, dedicated confusion, delayed Future Sight
and Beat Up remain separate work. Snow, Technician's intrinsic snapshot and
critical/Sniper placement are preserved. No move/resource/learnset counts change
(72 moves,336 rows,237 species), and no ABI/save/context fields change.

Focused verification passed51 affected SDK-free host checks in61.624s, including
Snow, Simple, original abilities, selected stats, core rules and A14 regressions.
Fresh independent specification and quality reviews passed, each independently
checking the six D1a methods and selected-stat boundary check across all eight
flag combinations. The paired
SDK game/resource/layout/native build passed. A fresh data-only RAM fixture
confirmed135 damage before the correction and134 after it, with the same seed12,
18 RNG calls and final RNG state. All1700 native battle frames matched every
ARM9 instruction, with zero fallbacks, guard failures or evictions. The seven
validation save hashes and frozen production/test hashes remained unchanged.
The full253-test sweep above belongs to f673; D1a uses the focused51 checks,
independent reviews, paired build and controlled native proof.
No installation, live app/ROM or real-save change occurred. See
`docs/superpowers/plans/2026-11-01-gen9-offensive-stage-order.md`.

## Offensive stat modifier group (D1b)

Modern battle now applies the selected offensive stage, direct Hustle floor,
then one Q12 offensive modifier group. Chain multiplication rounds halves up;
the completed stat application rounds halves down and clamps effective offense
to at least one. The original-roster path uses widened local arithmetic without
claiming synthetic overflow parity. Battle-off CalcMoveDamage preprocesses to
the exact prior tokens for all four types/moves flag combinations, retaining
its native u16 assignments and operation order. All three flags remain
independent and default off.

The group owns Huge/Pure Power, Slow Start, Guts, Plus/Minus, Solar Power,
Flower Gift Attack, the low-HP type abilities, activated active Flash Fire,
target Thick Fat/Heatproof, Choice Band/Specs, Thick Club, Deep Sea Tooth and
Light Ball. Every migrated legacy stat/BP/post-formula owner is gated off only
under modern battle. Flower Gift counts each actual living same-side base
Cherrim, including self, at its pinned priority between user abilities and
items. Original species after Transform also controls the migrated species
items. Active suppression, target Mold Breaker bypass, supplied weather and
Cloud Nine/Air Lock, and the existing Klutz/Embargo item accessor are preserved.
Foul Play/Body Press retain their selected raw stat/stage and user-owned
offensive modifiers; Psyshock retains its special category.

Soul Dew deliberately retains both legacy stat effects and the Frontier
restriction until its BP and defensive migration can land atomically. Flower
Gift's defensive branch, BP grouping, defensive grouping/Sand, +2 and final
damage ordering remain separate phases. Flash Fire's active-ability gate is an
arithmetic correction; activation-flag clearing/restoration after ability loss
or suppression still needs a lifecycle audit. Trainer AI executes the shared
group through its existing live battle context; ordinary hypothetical candidate
stat/context projection remains separate, and a supplied ability argument
cannot manufacture a Flower Gift provider. No ABI, save/context fields,
resources, move/learnset counts or installed app/ROM/save change occurs.

Actual-C discriminators give153 damage for raw101,+1,Guts+Choice Band against
Defense99 (sequential152), and55 for raw101,activated Flash Fire,BP80 against
Defense100 (legacy post-formula54). The focused tests use independent rational
modern expectations and preserve the legacy oracle across all eight flag
combinations. They cover stages/crit/Unaware, ownership/category, migrated
ability/item combinations, suppression, species/Transform, live providers,
weather, HP/turn/activation boundaries, minimum effective stat and literal Q12
half boundaries. The real trainer-AI matrix also passes address/undefined
behavior sanitizers; its test-only expanded move setup now stays in bounds.
See the migration ledger and verification record in
`docs/superpowers/plans/2026-11-01-gen9-offensive-modifiers.md`.

D1b integration passed57 affected SDK-free checks in80.856s and fresh independent
specification and quality review. Both reviewers independently passed16 methods
across all eight flag combinations; quality also checked the three changed
retained fixtures and the actual-AI sanitizer matrix. The matching SDK game,
transformed resources, layout and native executable build passed. Two fresh
matching RAM fixtures confirmed152→153 Guts/Choice Band damage and54→55 Flash
Fire damage, with the same seed12, respectively18/19 RNG calls and final RNG
states. Both1700-frame battle comparisons matched every ARM9 instruction, with
zero fallbacks, guard failures or evictions (3400 total compared frames). The
initial boot is separate from those measured segments. Seven validation save
hashes, frozen production/test hashes and all three tested artifact hashes
remained unchanged. The253-test sweep above belongs to f673 and was not rerun
for this C-only phase. The installed game and real save remain unchanged.

## Selected defensive stat and modifier group (D1c)

Modern battle now selects the defensive stat once, floors its crit/Unaware/
ignore-stage-filtered stage, applies direct current-type Snow Defense or Sand
SpDef, then applies one Q12 defensive modifier group and clamps the effective
stat to at least one. Weather uses the caller's flags and living active Cloud
Nine/Air Lock. The shared private stat helpers chain halves up and apply the
completed group with halves down. Modern defensive locals remain wide for
bounded original-roster arithmetic; synthetic overflow parity is not claimed.
Battle-off retains its original u16 assignments and exact operation order.

The selected group owns status Marvel Scale (Defense), base Clamperl Deep Sea
Scale (SpDef), untransformed current Ditto Metal Powder (Defense), and each
actual live same-side base Cherrim Flower Gift provider (SpDef), including self.
Species items/providers use the original party species only under actual
Transform, except Metal Powder which requires no Transform. Defensive Flower
Gift checks each eligible provider through native suppression/Mold Breaker
handling. Irrelevant or ineligible selected-defense abilities do not announce
Mold Breaker. Modern Explosion/Selfdestruct no longer halve Defense. Every
migrated old owner is disabled only under modern battle.

Psyshock/Psystrike retain Special category, screens and history while selecting
Defense. Body Press continues using its user's raw Defense and stage offensively,
without inheriting defensive weather, Marvel Scale or Metal Powder. D1b offense
remains shared through the renamed private numerical/base-species helpers.

Soul Dew remains an explicit compatibility exception: BOTH old stat bonuses,
the Frontier restriction and current-species ownership stay until atomic D2 BP
migration. Its defensive raw-SpDef floor precedes selected stage, direct weather
and the modern group; its offensive floor retains D1b placement after stage and
before its offensive group. This is not a claim of modern Soul Dew support.

Actual-C literal discriminators include stage151 -> Sand226 -> Deep Sea Scale452
instead of454 (neutral16 vs15 at L50/SpAtk103/explicit BP140); direct Snow151 then
Marvel Scale/Metal Powder group3 gives453 instead of452 (neutral12 vs13 at
L50/Atk113/BP100). Both use deliberately assigned raw stats/current types and do
not claim natural species stats or updated Overheat BP. Two eligible Flower Gift
providers on raw101 give227, and Marvel Scale plus Metal Powder on raw101 give303.
These are independent rational expectations executed by production
`CalcMoveDamage`, with real `TrainerAI_CalcDamage` matrices and retained legacy
expectations across all eight flags. Host assertions also check unchanged raw
stats, battle mons and RNG, and expected causal Mold Breaker writes.

The defensive contract, commands and evidence are recorded in
`docs/superpowers/plans/2026-11-01-gen9-defensive-modifiers.md`. Full BP/formula/
final/berry and AI variance ordering, hypothetical candidate-context projection,
Flash Fire activation-flag lifecycle, delayed hits, Beat Up and confusion remain
separate work. No ABI/context/save fields, resources, species/learnset counts,
flag defaults or installed app/real-ROM/real-save change occurs in this phase.


D1c implementation verification passed107 affected methods in199.654s, comprising
94 SDK-free methods and13 existing SDK script/VM methods. The broad regression
command accidentally included the SDK classes; root granted its already-running
sweep exclusive lane ownership to finish. No additional SDK/global/native/build
job was started. All10 D1c methods also passed address/undefined sanitizers in
27.706s. Before production edits, corrected actual-C tests failed only on modern
behavior; the expanded frozen-baseline run confirms36 expected modern assertion
failures with zero compiler/battle-off failures. All four battle-off types/moves
preprocessed token streams equal40aad (host assertion line metadata excluded).
Fresh independent reviews and paired game/native GREEN proof remain root-owned
integration gates; these host/script results alone do not establish complete
modern damage parity or native integration.

D1c integration passed the107 affected checks (94 SDK-free and13 existing SDK)
in199.654s, plus10 D1c sanitizer checks in27.706s. Fresh independent spec and
quality reviews each passed20 D1c/D1b methods across eight flags, verified all
four legacy token streams, all six hashes and whitespace; quality also tested
Transform lookup for every battler/party index. The matching SDK game/resource/
layout/native build passed. Two fresh data-only RAM fixtures confirmed7→8
Sand/Scale damage and13→12 Snow/Marvel Scale/Metal Powder damage with the same
seed12, respectively19/17 RNG calls and final RNG states. Both1700-frame battle
segments matched every ARM9 instruction with zero fallbacks, guard failures or
evictions (3400 total); the initial boot is separate. Raw stats, stages, current
types, abilities/items/status/weather were independently inspected and equal
before comparisons. Seven save, frozen production/test and all three tested
artifact hashes matched. The253-test full sweep belongs to f673; D1c uses the
107 affected checks, sanitizer/review checks, paired build and native proofs.
The installed app, real ROM and real save remain unchanged.

## Confirmed external base-power group (D2a1)

Modern battle now chains the confirmed external BP effects once in pinned Q12
priority order, then applies the completed group with halves down. Intrinsic
power, explicit overrides, A14 dynamic callbacks and legitimate native doubles
remain before Technician eligibility. The group owns Technician, Rivalry, Iron
Fist, Reckless, target Dry Skin, existing type/species/category items, Soul Dew,
Helping Hand, Charge, Sports, Solar Beam adverse weather and confirmed native
Facade/Brine BP events. Muscle Band/Wise Glasses use pinned priority16 and4505;
type items/orbs/Soul Dew use priority15 and4915. Sports uses1352. Active ability,
held-item suppression, effective move type and supplied weather remain native
inputs. Pure numeric helpers add no RNG or state mutation.

Soul Dew migrates atomically: modern original/base Latios/Latias gain Psychic/
Dragon BP4915, including Frontier, and both old SpAtk/SpDef bonuses are removed.
Other species orbs also use original/base species under actual Transform;
modern Griseous Orb no longer inherits the legacy blanket Transform exclusion.
Battle-off keeps the complete old Soul Dew and item behavior. Flags remain
independent/default off; no ABI/context/save/packet/resource/catalog changes or
Sharpness242 enabling occurs.

Exact native Reckless12 and Facade/Brine20 values are consumed once only with
their effect/state prerequisites; unknown multipliers preserve a legacy fallback.
D2a1 retained both old Me First owners; the D2a2 section below supersedes its
ordinary-command numerical owner with explicit local route provenance. Semi-invulnerable/Minimize doubles
retain old placement and Technician eligibility until D3; conflicting pinned
Fly/Bounce reference placement remains unresolved. Sports lifetime, Charge
consumption, hypothetical AI/ambient-multiplier projection, exceptional routes
and later formula/final layers remain explicit compatibility limits. This is
confirmed BP subset support, not full BP or all-route Generation IX parity.

Actual production damage/AI, original producer commands/scripts, independent
integer oracles and verification evidence are detailed in
`docs/superpowers/plans/2026-11-01-gen9-confirmed-bp-group.md`. The earlier D1c
Soul Dew exception above describes that historical phase and is superseded here.
Fresh reviews and paired SDK/native integration remain root-owned gates.

Soul Dew's player-facing description remains a deferred resource/UI task:
`GetItemDescIntoString` reads bank221/item225, whose source row and packed words
still advertise raising Sp. Atk/Sp. Def. This source-only phase changes neither
that text nor the resource pipeline. A battle-flagged description update and UI
validation remain necessary before claiming full item UI parity.

D2a1 host verification passed89 inspected SDK-free methods in127.184s and the11
new methods under address/undefined sanitizers in29.240s. Corrected primary
fixtures replayed against frozen f72c fail with12 intended modern assertions,
zero compiler/battle-off failures. All four battle-off calculator token streams
match f72c exactly. A preliminary run was interrupted after a mixed host class
entered its SDK method; it is not counted as passing evidence. The clean runner
explicitly excludes that method and guards SDK entry. Contract/log references
and the source freeze manifest are in the D2a1 plan. Fresh independent reviews
and paired SDK/native integration remain outstanding root-owned gates; the
installed app, real ROM and real save remain unchanged.

D2a1 integration passed89 guarded SDK-free checks in127.184s and11 new sanitizer
checks in29.240s. Fresh independent spec and quality reviews each passed16
selected methods across eight flags (new11 plus five changed regressions), all
four legacy token comparisons, ten hashes and whitespace. The matching SDK
ROM/resources/layout/native build passed. Two fresh data-only RAM fixtures
confirmed Acrobatics/Technician/Sharp Beak45→46 damage and Soul Dew41→49. The
Soul Dew result excludes keeping both old bonuses with new BP48, only attacker72,
only defender33 or missing BP41. Current Normal types deliberately isolate the
fixture's neutral/no-STAB arithmetic. Both seed12 runs retained their18/19 RNG
calls and final states. Each1700-frame battle comparison matched every ARM9
instruction with zero fallbacks, guard failures or evictions (3400 total); the
initial boot is separate. Seven save, eight frozen production/test and three
artifact hashes matched. The253-test sweep belongs to f673; no full rerun was
claimed for D2a1. Remaining Me First/final/lifecycle/projection/UI scope above
still blocks installing the complete modern ruleset. Live app/ROM/save untouched.

## Me First ordinary-command BP routes (D2a2)

The single shared damage formula now has a private, unconditional origin and
local eligibility interface. The unchanged public CalcMoveDamage ABI wraps it
with compatibility/FALSE. Only DamageCalcDefault opts into ordinary-command
provenance, using a pure signed64 predicate over existing flag/count/total. The
worker never infers eligibility from ambient state, move identity, damage or an
override. CalcDamage, CalcDamageRaw, Pursuit and called ordinary moves share that
gateway; actual copied dispatch still installs moveNoCur.

With modern battle enabled, Me First6144 joins the BP chain at priority12,
between items15 and Helping Hand10, and only the old late numerical multiply is
disabled. Equal-count decrement and stale-expiry clearing remain at their
original execution boundary. Repeated hits/reset retain existing flag/count,
Pursuit's producer/subscript SET20 stays2×, and PP/Pressure/Choice/acquisition/
order/legality/RNG behavior stays intact. Future counts retain legacy negative
delta math; corrupted counters that overflow the native lifecycle remain
unsupported. Battle-off formula bodies and command tokens match accepted25716
for all four type/move combinations. Flags remain independent/default off;
public header, battle/context/save/packet layouts and resources do not change.

AI, switching, confusion and Future Sight keep the public compatibility path.
Beat Up/fixed/OHKO/returned damage keep independent routes without a new event
or lifecycle. Copied exceptional moves retain that existing behavior. Numerical
oracles include intrinsic41/Technician/Me First grouped92 versus sequential91,
and native Ember40/Technician command42→41. Public/compatibilityTRUE/ordinaryFALSE
match baseline over80,640 representative all-flag formula cases with state/RNG
comparison. Focused actual-C acquisition/dispatcher/Pursuit/AI/exception tests,
rolls/crits/repeated hits and the host/sanitizer commands are recorded in
`docs/superpowers/plans/2026-11-01-gen9-me-first-routes.md`.

This is source-only ordinary-command numerical support. Hypothetical AI/copied
forecasting, delayed/confusion/Beat Up modernization, final Life Orb/Metronome/
berry groups, semi-invulnerable/Minimize placement and Sharpness remain deferred.
D2a1 Soul Dew stays intact; its bank221/item225 description remains pending.
The final guarded SDK-free sweep passed120 methods in175.112s; the25 focused
Me First/BP sanitizer methods passed in66.381s. Baseline replay retains exactly
four intended modern numerical failures with no legacy/compiler failures, and
all four battle-off body-token checks pass. Root owns fresh reviews and matching
SDK/native41 validation before landing.
The installed application, real ROM and real save are unchanged.

D2a2 integration passed120 guarded SDK-free checks in175.112s and25 sanitizer
checks in66.381s. Both fresh independent reviews passed31 selected methods
across all eight flags (14 Me First,11 BP,six affected),80,640 differential rows,
public ABI, four legacy body/command token comparisons and hashes/whitespace.
The paired SDK ROM/resources/layout/native build passed. A fresh data-only
ordinary-command RAM fixture confirmed42→41 damage with the same seed12,
19 RNG calls/final state4175436897 and flag/count/total1/1/1→1/0/2. All1700
compared battle frames matched every ARM9 instruction with zero fallbacks,
guard failures or evictions. Initial boot is separate; actual acquisition and
dispatch are host-tested, not inferred from this native command-state fixture.
Ten frozen files, seven prior plus two new validation saves and three tested
artifact hashes matched. No253-test full-suite rerun was claimed for D2a2.
The installed four-QoL app, real ROM and real save remain untouched.


## Sharpness and Soul Dew text (D2b)

The shared modern BP collector supports Sharpness242 at priority19 using the
active attacker snapshot and an explicit slicing classifier. The twelve original
slicing IDs work with battle alone; Sacred Sword536/Razor Shell537/Aqua Cutter898
also require modern moves. Every other u16 is false, including Champions-only
claws. Air Cutter314/Air Slash403 remain Special. No native move flag/contest
byte/table/ABI is widened. Public/AI paths receive Sharpness while Me First still
requires explicit ordinary-command origin and eligibility.75+Sharpness+Helping
Hand groups to169 (base76 at L50/SpA100/SpDef100); adding a20% type item groups
to203 under the pinned Q12 arithmetic. The old ready-plan202 expectation was an
exact-rational boundary error. Explicit41+Sharpness+Me First+Helping Hand gives
138 instead of sequential136.

Modern Gallade uses[Steadfast80,Sharpness242]. The original source pair is
[80,80]. On read only, original stored80/oddPID/baseform maps to242; even80,
zero/custom/242, other species/forms survive. Native constructor/explicit update
slot selection is unchanged. The actual encrypted getter preserves all bytes,
checksums and block permutations; no save migration or silent unrelated
normalization is introduced. NUM_ABILITIES/Easy Chat limits and byte layouts
remain original.

Ability banks720/721/722 now have243 rows with sparse130/172/242 and placeholders
for all unsupported gaps. Sharpness reads “Powers up slicing moves\nby 50%.”
Full source-byte/encoded-row/key guards preserve existing names/descriptions.
Soul Dew's original source bank221 stays unchanged; a battle-only resource
transform validates the full exact post-Snow bank, then replaces only item225
with the20% Psychic/Dragon move wording. It preserves Snow282/334, all536 other
incoming rows, keys and NARC members/names. The63-character three-line text
measures137/137/73px and stays within the149px/130-character bounds. All eight
message-pipeline flag combinations are host-tested with script edges isolated.

The contract, source pins, RED/GREEN commands, resource owners, guarded host and
ASan/UBSan coverage are in
`docs/superpowers/plans/2026-11-01-gen9-sharpness-and-item-text.md`.
Fresh specification/quality reviews, complete SDK/resource integration and
matching native/summary/bag acceptance remain root gates. Full Gen IX support
is still incomplete; the installed app, real ROM and real save remain untouched.

D2b source verification passed164 explicitly guarded SDK-free methods in221.926s
plus four updated routing-owner checks. The38-method ASan/UBSan sweep passed
in104.827s; a latest9-method Sharpness sanitizer rerun passed in22.330s. The
accepted-d375 numerical replay has exactly16 intended modern failures across
four methods/all eight flags, zero legacy failures and zero compiler errors.
All four accepted-d375 battle-off worker/default/raw command token comparisons
and the original public header guard pass. The source/test/doc freeze manifest
is `.local-tools/validation/sharpness-frozen-hashes.json`. These are host results;
complete SDK/resource integration, matching native and UI gates remain pending.


D2b integration is verified. Both fresh independent reviews passed22 focused
methods plus8/10 routing checks. The complete319-test host/SDK suite passed
in1058.774s without failures/errors/skips, and the matching SDK ROM/resources/
layout/native build passed. Built ability banks have243 rows; Soul Dew225 has
the20% Psychic/Dragon text while retaining Snow282/334 and all other bank221
rows. Fresh native constructor boots observed odd Gallade80→242 and even80→80.
Six data-only neutral/no-STAB battle fixtures confirmed Sacred Sword61 versus
control41, Air Slash51 versus35, suppressed Air Slash35 and non-slicing
Earthquake46. Seed12 retained18/19 RNG calls and the expected final states.
All10200 compared battle frames matched every ARM9 instruction, with zero
fallbacks, guard failures or evictions. Root accepted both Gallade ability
screens and the three-line Soul Dew item description without clipping. Ten
validation saves, frozen production/test hashes and tested ROM/native/layout
hashes matched. Evidence is in `sharpness-native-green-proof.json` and the
Sharpness plan above. Support stays72 moves/336 learning rows/237 species;
Wind Rider, Neutralizing Gas and other remaining Gen IX scope are unfinished.
The installed four-QoL app, real ROM and real save remain unchanged.


Tailwind's bounded modern duration change is implemented: battle-on starts at
four turns including the casting turn; battle-off retains three. Public
presence remains0x300, with private bit11 encoding the fourth turn as0xB00.
Speed/AI masks, context/save layouts, roster/story, and the72/336/237 support
counts remain unchanged. The script owner guards original160 SDK parity and
changes only its successful OR operand. The message owner validates exact
post-Snow bank749/key27800/468rows, changes only description366 to four turns,
and runs after Soul Dew before move extension. Snow258, Soul Dew225, names,
keys, archive members and ability banks243/124 retain their owners.

The source contract and evidence are in
`docs/superpowers/plans/2026-11-01-gen9-tailwind-four-turns.md`. Numerical RED
proved three actual residual ticks versus four expected for all battle-on flag
pairs. Final focused host17 passed in36.510s, ASan/UBSan11 in23.028s, SDK2 in
25.212s and nine neighboring routing methods in11.225s. Host coverage includes
all eight flags, real message pipelines, every other allocated side-bit
combination/storage pattern/setter value, high bits, actual speed/AI/Gyro Ball,
Snatch, hazards, context lifecycle, ARM declarations and accepted-b385 battle-off
tokens. SDK verified unchanged96-byte160 parity, sole word17=0x300→0xB00,
actual225→121→160 VM routing and expiry233. The Snatch sanitizer fixture alone
normalizes a pre-existing signed1<<31 macro to unsigned0x80000000; production
is unchanged and the original-literal sanitizer failure is retained. Leak
detection is disabled on macOS; no leak or full native matrix claim is made.
The freeze manifest is `.local-tools/validation/tailwind-frozen-hashes.json`.
Fresh root reviews, broad suite, matching SDK/native build, four-versus-three
native duration/speed, summary UI and save/artifact acceptance remain pending.
The installed app and real ROM/save are untouched. Wind Rider and Neutralizing
Gas remain separate unfinished work.


Tailwind integration passed fresh independent specification/quality reviews,
the matching SDK ROM/resources/layout/native build and the complete338-test
host/SDK suite in861.705s without failures/errors/skips. One historical Me First
whole-controller source guard was narrowed to74 protected function bodies plus
its75-function inventory, allowing only the Tailwind owner/two new helpers;
fresh spec/quality mutation checks passed. The interrupted earlier broad run is
retained and not counted as green. Runtime/artifact hashes did not change for
that test-only correction.

Five native restored turns preserve modern Tailwind's fourth-turn Speed/order,
then expire before turn5. A failed recast does not refresh it; a staggered-side
hazard fixture preserves two layers each of Spikes/Toxic Spikes while the foe's
Tailwind and Lucky Chant expire independently. All seven comparisons match
every ARM9 instruction over12100 frames, with zero fallbacks, guard failures or
evictions. Normal turns retain15 RNG calls each and the control's first four
final states. The four-turn Summary text fits cleanly. Fourteen validation saves,
frozen production/test hashes, tested ROM/native/layout and the installed game/
current real-save guards matched. See the Tailwind plan and ignored
`tailwind-native-green-proof.json` for measured scope; initialB00 is binary/SDK
VM evidence rather than a native-frame capture. Wind Rider/Gas, dynamic mid-turn
ordering and remaining Gen IX work are still unfinished; the installed four-QoL
app and real game files remain unchanged.

### Wind Rider241 and Shiftry's second ability

The bounded Wind Rider implementation adds eligible wind-attack absorption,
own-side Tailwind-start boosts and one entry/real ability-gain activation, then
selectively assigns Shiftry's second slot. Stored form0 Early Bird48 maps only
for odd original PIDs; explicit other choices and alternate forms stay intact.
The separate88-byte ARM battle-heap payload and eight-byte owner registry preserve
native battle/save/packet layouts. Completed160 tail-chains call-free304 while
preserving all four native stack frames and the original return.

The [implementation and validation record](superpowers/plans/2026-11-01-gen9-wind-rider.md)
documents actual C/SDK execution, all eight resource branches, encrypted read
nonmutation, scratch/AI boundaries and required root native acceptance. Sparse
ability banks remain243 rows;240 is unsupported,242 stays Sharpness, and the
72-move/336-row/237-species bounds remain unchanged. Gas recovery, dynamic
mid-turn ordering and unsupported wind moves are future milestones. This change
does not claim full Gen IX rules or authorize an installation.

Worker focused gates:95 guarded host tests,26 serial ASan/UBSan/SDK tests
with52 fresh pipeline assemblies, and10 genuine SDK C compilations passed.
LSan is disabled on macOS; native paired-ROM/layout/snapshot acceptance and
fresh root specification then quality reviews remain required before release.

Fresh root spec and quality reviews passed with 60/21 guarded host tests plus
independent actual-C edges. The matching all-three-modern-flags SDK/resources/
layout/native build passed. The initial 364-test run found 21 compilation
subtest failures across nine old fixture methods. Six test-only dependency fixes
passed fresh spec/quality review, then 91 affected tests passed in 358.472 s
and three additional Sharpness consumers passed in 13.111 s. Together with 355
initial passing methods, these cover the complete 364-case collection; there is
no claim of a single fully green 364-case rerun. The Wind resource matrix reused
52 exact-profile genuine SDK assemblies; the focused final run assembled all 52
freshly.

Seven genuine trainer-doubles cases cover wind absorption, both Tailwind allies,
Mold Breaker, Petal Blizzard spread, opposing Tailwind and blocked Whirlwind.
Capped/suppressed holders and failed recast retain the correct independent
behavior. Three restored yielding/drained queue phases preserve BSS/heap state
and produce byte-identical full 4 MiB ARM RAM at the accepted endpoint. All 13
stable comparisons matched every ARM 9 instruction across 46400 frames, with
zero fallback/guards/evictions. Separate cold boot 2500 also matched every ARM 9
instruction but had 1.24% fallback and 42 guards/evictions during loading.

Fresh singles confirm Shiftry odd 241/even 34/custom even 48; its Summary text and
Attack-rise message fit cleanly. Six copied-save hashes, frozen production/tests,
tested artifacts and installed/current real-save/config guards matched. Native
gain-route coverage is not claimed; actual SDK VM tests cover entry/gain and
synchronous queue transitions. See the Wind plan for exact scope and evidence.
The complete Gen IX ruleset remains unfinished and is not installed.
