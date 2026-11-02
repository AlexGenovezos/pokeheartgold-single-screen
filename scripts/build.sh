#!/usr/bin/env bash
# Run from any directory. Keep Wine's state within this checkout.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

make_bin=make
if [[ "$(uname -s)" == Darwin ]]; then
    make_bin=gmake
    local_wine="$repo_root/.local-tools/Wine Devel.app/Contents/Resources/wine/bin"
    if [[ -x "$local_wine/wine" ]]; then
        export PATH="$local_wine:$PATH"
    fi
fi
export WINEPREFIX="${WINEPREFIX:-$repo_root/.local-tools/wineprefix}"
export WINEDEBUG="${WINEDEBUG:--all}"
for program in "$make_bin" wine winepath arm-none-eabi-objcopy python3; do
    if ! command -v "$program" >/dev/null; then
        echo "Missing $program. See docs/FORK.md for setup." >&2
        exit 1
    fi
done
if [[ ! -f tools/mwccarm/2.0/sp2p2/mwccarm.exe || ! -f tools/bin/makelcf.exe ]]; then
    echo 'Compiler/SDK tools are missing. See docs/FORK.md for setup.' >&2
    exit 1
fi
# Imported game messages are ignored assets. Recreate only our owned labels
# before make evaluates header/resource dependencies, including profile changes.
if [[ -f files/msgdata/msg/msg_0045.gmm ]]; then
    python3 tools/qol/options_messages.py -- "$@"
fi
exec "$make_bin" -j"${JOBS:-8}" "$@"
