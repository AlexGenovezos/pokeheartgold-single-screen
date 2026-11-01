# SoulSilver quality-of-life mods

Work is tracked on the `qol-mods` branch of
[AlexGenovezos/pokeheartgold-single-screen](https://github.com/AlexGenovezos/pokeheartgold-single-screen).
The original project remains the `upstream` remote; `origin` points to this fork.

## Backlog

The patch utility and opt-in instant-text/reusable-TM source changes now have
host regression tests. None of the gameplay changes are installed in the current
game. See [development commands](../tools/qol/README.md).

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
field-action access. There is no universal first-badge license and no early
grant of all field actions.

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
local paths. Library retrieval from iCloud timed out: most source files remain
marked dataless, and only a small partial copy exists locally. The build is
not ready until these library sources are available offline. The installed
native app was generated directly from the retail ROM using
`ssrecomp` v0.4.2; it is not evidence that this decompilation checkout can build
a modified ROM. Resolve the build prerequisites or validate an alternative
native modification path before promising an installable gameplay mod.

Instant-text starting points are `src/options.c`, `include/options.h`,
`src/options_app.c`, `src/text.c`, `src/render_text.c` and
`src/battle/battle_system.c`. Verify text-printer callbacks and waits before
using the existing `TEXT_SPEED_INSTANT` rendering mode.

## Existing implementations

[Reuse research](QOL-REUSE.md) records hg-engine and HM-patch precedents, the
native compatibility constraint, and the source paths for the remaining HM and
effectiveness work. Prefer porting established modern battle behavior rather
than building a second battle engine from scratch.
