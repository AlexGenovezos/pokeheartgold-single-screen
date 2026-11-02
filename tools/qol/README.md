# QoL development tools

The first four QoL features are built and installed in the local Mac app.
See [the installed checkpoint](../../docs/QOL.md) for source revisions and
validation limits. Generation IX/Fairy is still pending.

## Host regression tests

From the repository root, with Python 3 and a host C compiler:

```sh
python3 -m unittest discover -s tools/qol -p 'test_*.py' -v
python3 -m unittest discover -s tools/progress -p 'test_*.py' -v
```

The C harnesses compile selected actual game functions against minimal host
edges because the normal headers depend on the Nitro SDK. The page-wait
regressions execute the real text renderer and simulate the two print-queue
runs per input sample used by the game. These tests do not substitute for a
complete ROM build, visual inspection or gameplay testing.

## Building the opt-in features

The original behavior is the default. Once the compiler, SDK/library sources
and game assets documented in INSTALL.md are supplied:

```sh
./scripts/build.sh GAME_VERSION=SOULSILVER COMPARE=0 CLI_DEFINES="-DQOL_MODS=1"
```

`QOL_MODS=1` currently enables `QOL_INSTANT_TEXT`, `QOL_REUSABLE_TMS`,
`QOL_HM_ACTIONS`, `QOL_EFFECTIVENESS` and `QOL_LEVEL_CAPS` support. Level caps
start Off in each save; see [level-cap behavior](../../docs/LEVEL-CAPS.md).
Override each macro individually with 0 or 1 to test it in isolation.
Select the new Instant text-speed choice in the in-game Options menu; this is
not automatic dialog advancement. HM actions require their original item and
badge, with existing field restrictions. Battle modernization is still pending.
The controls cleanup source omits effectiveness labels for status moves.
Damaging moves retain type multipliers, including neutral `1x`; `?` means a
target must be chosen or a reliable forecast is unavailable (for example,
fixed-damage or variable-type moves). Native visual/input acceptance is pending.

The Makefile tracks gameplay definitions and rebuilds game objects when they
change. Identical invocations reuse objects. The three fixed-profile C++ library
producers exclude gameplay-only QoL flags; their strict checks stay enabled.
A modified build cannot pass the retail ROM checksum comparison.
Byte-for-byte baseline equivalence with the QoL flags off has not been verified.

## BPS patches

Create a patch from a clean ROM and a separately built modified ROM:

```sh
python3 tools/qol/rom_patch.py create "/path/to/clean.nds" "/path/to/modified.nds" "/path/to/qol.bps" --source-sha1 f8dc38ea20c17541a43b58c5e6d18c1732c7e582
python3 tools/qol/rom_patch.py apply "/path/to/clean.nds" "/path/to/qol.bps" "/path/to/patched.nds"
```

The creator checks the exact source SHA-1 and verifies the patch round trip.
Application checks BPS source, target and patch CRCs. Both commands refuse to
overwrite an existing output, including an input alias or symlink. Creation
uses standard SourceRead/TargetRead actions; application also supports
SourceCopy and overlapping TargetCopy. Patches with many moved/repacked bytes
can be large; this creator prioritizes simplicity over minimum patch size.

A successful packaging test does not establish that a ROM is playable.
Keep the clean ROM and back up saves; never commit ROMs, saves, SDKs or generated
native game code. Native recompilation still needs a matching layout; see
[the backlog](../../docs/QOL.md) and [reuse research](../../docs/QOL-REUSE.md).


## Native build

Use the paired `qol-mods` branch of AlexGenovezos/ssrecomp in a sibling
`ssrecomp-qol` directory. Install `pyelftools` in its local `.venv`, then run:

```sh
./scripts/build-qol-native.sh ../ssrecomp-qol
```

This opt-in wrapper also defaults to skipping the Route 29 catching lesson.
Set `QOL_SKIP_CATCHING_TUTORIAL=0` to retain it:

```sh
QOL_SKIP_CATCHING_TUTORIAL=0 ./scripts/build-qol-native.sh ../ssrecomp-qol
```

Tutorial skipping is a separate data transform, not a C definition. It writes
`pokesoulsilver-qol.us.nds` after any modern resource transforms and passes that
same ROM into layout generation and native translation. The raw source ROM is
retained. It keeps the original five-ball reward and story completion; saves
that already completed the event do not replay it. Gameplay acceptance and
installation of the skip remain pending.

To create a separate tutorial-skip ROM from an existing USA SoulSilver build:

```sh
python3 tools/qol/skip_catching_tutorial.py /path/to/base.nds /path/to/new-skip.nds
```

The transform accepts only the reviewed original Route 29 script or its exact
patched form. It changes two bounded script regions in place, preserves
all executable and layout bytes, and refuses existing output paths. Confirm
compatibility with the actual native layout before reusing an executable.

This builds the opt-in QoL ROM, generates layout metadata from its own ELF/NEF and
ROM, verifies every section against that layout, and compiles the native app.
The output paths are printed; the script does not replace your installed game
or touch saves. A clean ROM remains necessary for making a distributable BPS
patch. Existing in-game saves can be copied for testing; old memory snapshots
must not be reused after game-code changes.

The supplied library snapshot used for this fork is
`ctrl-cheeb-del/pokeheartgold@d414e429ec36d1ac629efdfb28c6353f470e60e5`. A newer
library/header checkout is not interchangeable, even when filenames match.

## Modern battle development

The approved next target includes modern moves and updated abilities for the
original roster. Independent development flags are default-off:

```sh
QOL_MODERN_TYPES=1 QOL_MODERN_BATTLE=1 ./scripts/build-qol-native.sh ../ssrecomp-qol
```

This currently builds a **type/core-rule foundation**, not complete Gen IX.
The type resource transform writes a separate `pokesoulsilver-modern.us.nds`,
leaving the built source ROM and input filesystem assets intact. It updates type
names and both shared/Pokédex icons; Normal's shared Dex icon and Hall Matron's
special `???` label remain intact. Runtime validation is still required before
installation. Pokédex Fairy search and the remaining move/ability/status/weather
ports remain tracked in issue #6 and `docs/QOL-REUSE.md`.

The pinned hg-engine export tool emits review data without changing the game:

```sh
python3 tools/qol/hg_import.py .local-tools/hg-engine .local-tools/gen9-profile.json
```

Generated exports contain move/species data and stay ignored locally. This tool
requires a host C compiler and the exact reviewed upstream revision; it disables
the five Champions switches, records official versus engine move IDs, validates
byte-sized ability aliases and checks wider level-up encoding. Existing native
bit 0x20 means item-flinch eligibility; upstream's same bit marks unimplemented
moves. Do not copy it without translation. Ability names/data are not evidence
that their mechanics are implemented. Retain upstream credits/reuse terms in
`docs/third-party/` when porting work.
