#!/usr/bin/env bash
# Build a modified ROM, generate matching layout/code, and compile the native app.
set -euo pipefail
game_root="$(cd "$(dirname "$0")/.." && pwd)"
native_root="${1:-$game_root/../ssrecomp-qol}"
native_root="$(cd "$native_root" && pwd)"
modern_types="${QOL_MODERN_TYPES:-0}"
modern_rules="${QOL_MODERN_BATTLE:-0}"
case "$modern_types:$modern_rules" in
    0:0|0:1|1:0|1:1) ;;
    *) echo 'QOL_MODERN_TYPES and QOL_MODERN_BATTLE must be 0 or 1.' >&2; exit 1 ;;
esac
game_defines='-DQOL_MODS=1'
if [[ "$modern_types" == 1 ]]; then
    game_defines+=' -DQOL_MODERN_TYPES=1'
fi
if [[ "$modern_rules" == 1 ]]; then
    game_defines+=' -DQOL_MODERN_BATTLE=1'
fi
python_bin="$native_root/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
    echo "Create $native_root/.venv and install pyelftools there first." >&2
    exit 1
fi
for task_file in tools/recomp.py tools/apps.py tools/make_layout.py CMakeLists.txt; do
    [[ -f "$native_root/$task_file" ]] || { echo "Missing native source: $task_file" >&2; exit 1; }
done
"$game_root/scripts/build.sh" GAME_VERSION=SOULSILVER COMPARE=0 "CLI_DEFINES=$game_defines"
game_build="$game_root/build/soulsilver.us"
game_rom="$game_build/pokesoulsilver.us.nds"
if [[ "$modern_types" == 1 ]]; then
    resource_dir="$(mktemp -d "$game_build/qol-resources.XXXXXX")"
    trap 'rm -rf "$resource_dir"' EXIT
    "$python_bin" "$game_root/tools/qol/modern_rom.py" "$game_rom" "$resource_dir/modern.nds"
    game_rom="$game_build/pokesoulsilver-modern.us.nds"
    mv "$resource_dir/modern.nds" "$game_rom"
fi
layout_file="$game_build/qol-layout.json"
generated_dir="$native_root/gen"
(
    cd "$native_root"
    "$python_bin" tools/make_layout.py "$game_build" "$game_rom" "$layout_file"
    "$python_bin" tools/recomp.py --rom "$game_rom" --layout "$layout_file" melonDS/src "$generated_dir"
    "$python_bin" tools/apps.py --layout "$layout_file" "$generated_dir"
)
cmake_args=(-G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo "-DSSR_GENERATED_DIR=$generated_dir")
if [[ "$(uname -s)" == Darwin ]]; then
    native_build="$native_root/build-macos-$(uname -m)"
    cmake_args+=("-DCMAKE_OSX_ARCHITECTURES=$(uname -m)" -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 -DSSR_MACOS_SOURCE_DEPS=ON)
else
    native_build="$native_root/build"
fi
cmake -S "$native_root" -B "$native_build" "${cmake_args[@]}"
cmake --build "$native_build" --parallel "${JOBS:-8}"
echo "Native binary: $native_build/ssrecomp"
echo "Matching ROM: $game_rom"
