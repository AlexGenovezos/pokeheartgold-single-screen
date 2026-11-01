# SoulSilver quality-of-life mods

Work is tracked on the `qol-mods` branch of
[AlexGenovezos/pokeheartgold-single-screen](https://github.com/AlexGenovezos/pokeheartgold-single-screen).
The original project remains the `upstream` remote; `origin` points to this fork.

## Backlog

Instant text, reusable TMs, HM actions and effectiveness previews are installed
in the existing Mac app as of 2026-11-01. Generation IX/Fairy is still pending.
The features remain opt-in at build time. See [development commands](../tools/qol/README.md).

| Order | Issue | Intended behavior |
| --- | --- | --- |
| 0 | [Build and patch pipeline #1](https://github.com/AlexGenovezos/pokeheartgold-single-screen/issues/1) | Establish reproducible modified ROM builds, binary patches and native recompilation compatibility. |
| 1 | [Instant text #2](https://github.com/AlexGenovezos/pokeheartgold-single-screen/issues/2) | Select Instant in Options for dialog and battle text; preserve confirmation prompts and intentional waits. |
| 2 | [Reusable TMs #3](https://github.com/AlexGenovezos/pokeheartgold-single-screen/issues/3) | Teaching a move does not consume its TM; acquisition and compatibility rules still apply. |
| 3 | [HM field actions #4](https://github.com/AlexGenovezos/pokeheartgold-single-screen/issues/4) | Receiving each HM unlocks its field action without teaching a party member. Preserve normal badge, story and location requirements. |
| 4 | [Effectiveness indicators #5](https://github.com/AlexGenovezos/pokeheartgold-single-screen/issues/5) | Show move effectiveness against the selected target using the active battle rules. |
| 5 | [Gen IX battle mechanics / Fairy type #6](https://github.com/AlexGenovezos/pokeheartgold-single-screen/issues/6) | Target Generation IX rules and Fairy typing; audit and reuse existing implementations before porting mechanics. |

HM coverage: Cut, Fly, Surf, Strength, Rock Smash, Waterfall, Rock Climb and
Whirlpool. Existing saves that already contain an HM must receive the same
field-action access. Field prompts work as before; currently usable HMs also
appear on any non-egg party member's action menu, including Fly. The member is
only the animation actor and needs no learned move. The action menu retains its
four field-action slots; available HMs take priority over learned non-HM actions.
There is no universal first-badge license and no early grant of all field actions.

## Source and build boundaries

- Game behavior belongs in this repository's `src/`, `include/` and necessary
  data/message files under `files/`. Add focused regression checks as features
  are implemented.
- Any required native frontend changes belong in a separate version-controlled
  `ssrecomp` source checkout. Record the paired source revisions.
- The installed `~/Library/Application Support/ssrecomp` directory is deployment
  output, not the place to maintain source modifications.
- ROMs, saves, generated native game code, compiler/SDK files and build output
  must stay out of commits and pushes. The current ROM and save are in
  `~/Games/SoulSilver Single-Screen/`.

## Patch workflow versus the current native app

For an emulator, the intended release is a binary patch (for example BPS) against
an exact clean SoulSilver USA ROM, rather than a full ROM. Applying that patch
produces a modified ROM that can be run directly in a DS emulator.

For native `ssrecomp`, game-code changes also require regenerating translated
code and rebuilding the native executable. The retail layout metadata may no
longer match a modified ROM; compatibility must be established in issue #1.
Frontend-only changes generally require a native rebuild without rebuilding
the ROM. Builds should be incremental where possible; players need only apply
each released patch once, not compile on every launch.

Clean base ROM SHA-1: `f8dc38ea20c17541a43b58c5e6d18c1732c7e582`.
Preserve the clean ROM and back up saves before testing changes.

## Initial build audit (2026-11-01)

The initial checkout lacked the compiler, Nitro tools, linker templates and
required SDK/library sources. A broader local search found the user's supplied
compiler/SDK archives and an older iCloud checkout containing the libraries.
The archives and public host dependencies have now been prepared in ignored
local paths. Library retrieval from iCloud subsequently completed: all 1,133
supplied library files are now copied into the local ignored `lib/` directory.
The copied checkout had newer library declarations than this fork. The
matching supplied library snapshot is ctrl-cheeb-del/pokeheartgold revision
`d414e429ec36d1ac629efdfb28c6353f470e60e5`; its four networking source files match
this fork byte for byte. Restoring that snapshot fixed networking compilation
without source compatibility workarounds. The full QoL ROM now links successfully.
Matching layout generation found 121 game sections, 97 applications and 21
watched functions. The modified ROM and matching native executable now build
and run successfully. The original installed app used a retail-ROM-generated
`ssrecomp` v0.4.2 executable; that version is retained in the local backup.

Instant-text starting points are `src/options.c`, `include/options.h`,
`src/options_app.c`, `src/text.c`, `src/render_text.c` and
`src/battle/battle_system.c`. Verify text-printer callbacks and waits before
using the existing `TEXT_SPEED_INSTANT` rendering mode.

## Existing implementations

[Reuse research](QOL-REUSE.md) records hg-engine and HM-patch precedents, the
native compatibility constraint, and the source paths for the remaining HM and
effectiveness work. Prefer porting established modern battle behavior rather
than building a second battle engine from scratch.

## Installed Mac checkpoint (2026-11-01)

Paired build revisions:
- Game: `f627ef6077eb8eee71b31ce9219e1b7cffd9ce49`, this fork's `qol-mods` branch.
- Native: `2ec876ee73abccd3c0d91b29566fa1de6d7311f5`,
  [AlexGenovezos/ssrecomp](https://github.com/AlexGenovezos/ssrecomp/tree/qol-mods).

The app keeps its existing name and `/Applications/SoulSilver Single-Screen.app`
path for Steam Input. Its launcher loads `SoulSilver QoL.nds`, the original
`soulsilver.sav`, and `ssrecomp.cfg` from the existing Games folder. Launch through
Steam as before to use the Steam Controller mapping. No compile is needed to play.

For instant text, select **Options → Text Speed → Instant**, choose **Confirm**,
and save normally. Quit discards option changes. Existing saves keep their
previous speed until changed. HM actions require each HM item and its normal
badge, plus the game's existing location/story restrictions. Select an eligible
non-egg party member to access actions such as Fly; the member needs no HM move.
Effectiveness labels are type multipliers; `?` marks status/unpredictable moves
or a target that has not been chosen.

Validation: 22 QoL and 36 progress-tool checks, plus 26 native checks passed.
Fresh native/interpreter instruction comparisons covered 600 boot frames,
1,100 Options frames from a frame-2,400 snapshot, and 700 battle frames from a
frame-7,600 snapshot. Instant was confirmed, saved to an isolated copy and
retained after a fresh boot. Overworld dialog, single-battle move cards and a
move execution were visually checked with Instant selected. The installed
binary/ROM pair passed a fresh 2,400-frame boot using a copied save.
Late-game HM environments and double-battle target menus still need gameplay
coverage; shared logic has host regressions. Keep #3–#5 open for those checks.

Deployment left the clean ROM and real save unchanged (save hash checked before
and after). Backups under `~/Games/SoulSilver Single-Screen/Backups/` contain the
old native binary, both application bundles, settings, save and old memory
snapshot. The old snapshot was removed from the active quickstate name because
snapshots contain code-build-specific memory. `qol-install.json` in Games
records exact revisions, artifact hashes and the backup path. Keep that private.
A final local BPS patch round trip also passed; the patch is generated output,
not committed game content. It is approximately 122 MB because the build repacks
the ROM; it is not a small optimized release patch.
