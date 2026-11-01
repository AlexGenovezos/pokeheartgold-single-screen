# QoL development tools

These tools and source changes are in development; they have not been installed
in the current native game.

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

`QOL_MODS=1` currently enables `QOL_INSTANT_TEXT` and `QOL_REUSABLE_TMS`.
Override either macro individually with 0 or 1 to test it in isolation.
Select the new Instant text-speed choice in the in-game Options menu; this is
not automatic dialog advancement. HM changes and battle modernization are not
implemented by these flags.

When changing compile flags, use a fresh build directory or rebuild all affected
objects: the existing Make rules do not track changes to flag values as file
dependencies. A modified build cannot pass the retail ROM checksum comparison.
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

