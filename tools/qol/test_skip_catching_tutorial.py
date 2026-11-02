"""Tutorial-skip checks use imported script data and the real C interpreter.

No game bytes are embedded in this test. Graphics, bag delivery and follower
commands are SDK edges; branching, dispatch, variable and flag writes run C.
"""
from pathlib import Path
import hashlib
import importlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest

import nitro_data as nitro
import test_game_logic as game

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / 'files/fielddata/script/scr_seq/scr_seq_0225_R29.bin'
try:
    skip = importlib.import_module('skip_catching_tutorial')
except ModuleNotFoundError:
    # Baseline RED must demonstrate unchanged behavior, not a failed import.
    class MissingTransform:
        patch_script = staticmethod(bytes)
        patch_rom = staticmethod(bytes)
    skip = MissingTransform()


def fixture_rom(script):
    archive = nitro.pack_narc([script if i == 225 else b'' for i in range(965)])
    rom = bytearray(0x20000)
    rom[12:16] = b'IPGE'
    names = b''.join(struct.pack('<IHH', offset, 0, parent) for offset, parent in
                     [(32, 4), (37, 0xf000), (42, 0xf001), (47, 0xf002)])
    names += b'\x81a\x01\xf0\0\x810\x02\xf0\0\x811\x03\xf0\0\x012\x05other\0'
    struct.pack_into('<4I', rom, 0x40, 0x200, len(names), 0x280, 16)
    rom[0x200:0x200 + len(names)] = names
    struct.pack_into('<4I', rom, 0x280, 0x400, 0x400 + len(archive), 0x8000, 0x8008)
    rom[0x400:0x400 + len(archive)] = archive
    rom[0x8000:0x8008] = b'keep me!'
    struct.pack_into('<I', rom, 0x80, 0x8008)
    struct.pack_into('<I', rom, 0x20, 0x300)
    struct.pack_into('<I', rom, 0x2c, 16)
    rom[0x300:0x310] = b'unchanged ARM9!!'
    struct.pack_into('<H', rom, 0x15e, nitro.crc16(rom[:0x15e]))
    return bytes(rom)


class SkipCatchingTutorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ASSET.read_bytes()
        assert hashlib.sha256(cls.original).hexdigest() == '3ed238656dbe0c565a3c5ad8cafd29e1fea97d46ea70543c1aa4e4656f37aee6'

    def test_same_size_patch_changes_only_two_script_regions_and_is_idempotent(self):
        output = skip.patch_script(self.original)
        self.assertEqual(len(output), len(self.original))
        changed = {i for i, (a, b) in enumerate(zip(self.original, output)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, set(range(0x1b6, 0x1bc)) | set(range(0x523, 0x52b)))
        self.assertEqual(output[0x1b6:0x1bc], struct.pack('<Hi', 22, 0x513 - 0x1bc))
        self.assertEqual(output[0x523:0x52b], struct.pack('<HHi', 53, 22, 0x53b - 0x52b))
        self.assertEqual(skip.patch_script(output), output)

    def test_unknown_partial_and_drifted_inputs_are_rejected(self):
        patched = skip.patch_script(self.original)
        partial = bytearray(self.original)
        partial[0x1b6:0x1bc] = patched[0x1b6:0x1bc]
        drifted = bytearray(self.original)
        drifted[-1] ^= 1
        for data in (b'', self.original[:-1], partial, drifted):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                skip.patch_script(data)

    def test_real_dispatch_and_branching_reach_existing_reward_and_completion_for_both_genders(self):
        patched = skip.patch_script(self.original)
        functions = '\n'.join(game.function_source('src/script.c', name) for name in
                              ('ScriptReadHalfword', 'ScriptReadWord', 'ScriptJump',
                               'StopScript', 'RunScriptCommand'))
        functions += '\n' + '\n'.join(game.function_source('src/scrcmd_c.c', name) for name in
                                      ('ScrCmd_GoTo', 'ScrCmd_SetVar', 'ScrCmd_SetFlag', 'ScrCmd_End', 'ScrCmd_CloseMsg'))
        source = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
#define ScriptReadByte(ctx) *(ctx->script_ptr++)
enum { SCRIPT_MODE_STOPPED, SCRIPT_MODE_BYTECODE, SCRIPT_MODE_NATIVE };
typedef int Window;
typedef struct { int gender, flags[1024], textbox_open; } FieldSystem;
typedef struct ScriptContext ScriptContext;
typedef BOOL (*ScrCmdFunc)(ScriptContext *);
struct ScriptContext { int mode; const u8 *script_ptr; ScrCmdFunc native_ptr;
    const ScrCmdFunc *cmdTable; u32 cmd_count; FieldSystem *fieldSystem; };
static u16 vars[65536]; static int locked, reset, delivered, balls, hidden[8];
static Window window; static u8 window_open; static int cleared, removed;
enum { SCRIPTENV_WINDOW, SCRIPTENV_FIELD_08 };
static void *FieldSysGetAttrAddr(FieldSystem *f, int key) {
    return key == SCRIPTENV_WINDOW ? (void *)&window : (void *)&window_open;
}
static void ClearFrameAndWindow2(Window *w, int arg) { assert(w == &window); cleared++; }
static void RemoveWindow(Window *w) { assert(w == &window); removed++; }
u16 ScriptReadHalfword(ScriptContext *); u32 ScriptReadWord(ScriptContext *);
void ScriptJump(ScriptContext *, const u8 *); void StopScript(ScriptContext *);
static u16 *ScriptGetVarPointer(ScriptContext *c) { return &vars[ScriptReadHalfword(c)]; }
static void FieldSystem_FlagSet(FieldSystem *f, u16 n) { assert(n < 1024); f->flags[n] = 1; }
''' + functions + r'''
static BOOL unexpected(ScriptContext *c) { assert(!"tutorial, dialogue or movement ran"); return TRUE; }
static BOOL lock_all(ScriptContext *c) { assert(!locked); locked = 1; return FALSE; }
static BOOL release_all(ScriptContext *c) {
    assert(locked && !c->fieldSystem->textbox_open && !window_open);
    locked = 0; return FALSE;
}
static BOOL reset_follower(ScriptContext *c) { reset++; return TRUE; }
static BOOL hide_person(ScriptContext *c) { u16 id = ScriptReadHalfword(c); assert(id == 6 || id == 7); hidden[id]++; return FALSE; }
static BOOL call_standard_reward(ScriptContext *c) {
    assert(ScriptReadHalfword(c) == 2033 && locked);
    assert(vars[0x8004] == 4 && vars[0x8005] == 5);
    delivered++; balls += vars[0x8005];
    c->fieldSystem->textbox_open = TRUE; window_open = 1; return FALSE;
}
static const u8 code[] = {''' + ','.join(map(str, patched)) + r'''};
int main(void) {
    ScrCmdFunc commands[700];
    for (int i = 0; i < 700; i++) commands[i] = unexpected;
    commands[2] = ScrCmd_End; commands[20] = call_standard_reward;
    commands[22] = ScrCmd_GoTo; commands[30] = ScrCmd_SetFlag;
    commands[53] = ScrCmd_CloseMsg;
    commands[41] = ScrCmd_SetVar; commands[96] = lock_all;
    commands[97] = release_all; commands[101] = hide_person;
    commands[609] = reset_follower;
    for (int gender = 0; gender < 2; gender++) {
        FieldSystem f = {.gender = gender};
        ScriptContext c = {SCRIPT_MODE_BYTECODE, code + 0x1b2, NULL, commands, 700, &f};
        memset(vars, 0, sizeof(vars)); memset(hidden, 0, sizeof(hidden));
        locked = reset = delivered = balls = cleared = removed = window_open = 0;
        vars[0x408b] = 1;
        int frames = 0;
        while (RunScriptCommand(&c) && frames++ < 64) {}
        assert(frames < 64 && c.mode == SCRIPT_MODE_STOPPED && c.script_ptr == NULL);
        assert(!locked && reset == 1 && delivered == 1 && balls == 5);
        assert(!f.textbox_open && !window_open && cleared == 1 && removed == 1);
        assert(hidden[6] == 1 && hidden[7] == 1);
        assert(f.flags[0x1a4] && f.flags[0x1a5] && f.flags[0x9a] && vars[0x408b] == 0);
    }
    return 0;
}
'''
        game.GameLogicTests().compile_run(source)

    def test_rom_preserves_all_other_bytes_members_headers_and_code(self):
        original = fixture_rom(self.original)
        output = skip.patch_rom(original)
        self.assertEqual(len(output), len(original))
        self.assertTrue(output != original, 'ROM still contains the original tutorial path')
        files = nitro.rom_files(original)
        _, start, end = files['a/0/1/2']
        self.assertEqual(output[:start], original[:start])
        self.assertEqual(output[end:], original[end:])
        old, names = nitro.unpack_narc(original[start:end])
        new, new_names = nitro.unpack_narc(output[start:end])
        self.assertEqual(names, new_names)
        self.assertEqual(old[:225] + old[226:], new[:225] + new[226:])
        self.assertEqual(new[225], skip.patch_script(old[225]))
        self.assertEqual(skip.patch_rom(output), output)

    def test_target_overlapping_an_executable_is_rejected(self):
        original = bytearray(fixture_rom(self.original))
        struct.pack_into('<I', original, 0x2c, 0x4000)
        with self.assertRaises(ValueError):
            skip.patch_rom(original)

    def test_script_archive_aliasing_another_file_is_rejected(self):
        original = bytearray(fixture_rom(self.original))
        original[0x288:0x290] = original[0x280:0x288]
        with self.assertRaises(ValueError):
            skip.patch_rom(original)

    def test_cli_preserves_inputs_and_refuses_existing_output_and_input_alias(self):
        command = ROOT / 'tools/qol/skip_catching_tutorial.py'
        self.assertTrue(command.is_file(), 'tutorial-skip CLI not implemented')
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'base.nds', Path(folder) / 'skip.nds'
            data = fixture_rom(self.original)
            source.write_bytes(data)
            result = subprocess.run([sys.executable, str(command), str(source), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(source.read_bytes(), data)
            self.assertEqual(output.read_bytes(), skip.patch_rom(data))
            for target in (source, output):
                before = target.read_bytes()
                result = subprocess.run([sys.executable, str(command), str(source), str(target)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(target.read_bytes(), before)


class TutorialSkipBuildTests(unittest.TestCase):
    def pipeline(self, option):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        game_root, native, binary = root / 'game', root / 'native', root / 'bin'
        (game_root / 'scripts').mkdir(parents=True)
        (game_root / 'tools/qol').mkdir(parents=True)
        (native / '.venv/bin').mkdir(parents=True)
        (native / 'tools').mkdir()
        binary.mkdir()
        wrapper = game_root / 'scripts/build-qol-native.sh'
        wrapper.write_bytes((ROOT / 'scripts/build-qol-native.sh').read_bytes())
        for name in ('skip_catching_tutorial.py', 'nitro_data.py'):
            (game_root / 'tools/qol' / name).write_bytes((ROOT / 'tools/qol' / name).read_bytes())
        source = root / 'input.nds'
        source.write_bytes(fixture_rom(ASSET.read_bytes()))
        log = root / 'calls.jsonl'
        executables = {
            game_root / 'scripts/build.sh': '''import os
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'build/soulsilver.us'
p.mkdir(parents=True)
(p/'pokesoulsilver.us.nds').write_bytes(Path(os.environ['QOL_TEST_INPUT']).read_bytes())
with open(os.environ['QOL_TEST_LOG'],'a') as f:f.write('["game-build"]\\n')
''',
            native / '.venv/bin/python': '''import json,os,subprocess,sys
from pathlib import Path
with open(os.environ['QOL_TEST_LOG'],'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')
if Path(sys.argv[1]).name=='skip_catching_tutorial.py':
    raise SystemExit(subprocess.run([sys.executable,*sys.argv[1:]]).returncode)
''',
            binary / 'cmake': 'import sys\n',
        }
        for path, body in executables.items():
            path.write_text('#!/usr/bin/env python3\n' + body)
            path.chmod(0o755)
        for name in ('tools/recomp.py', 'tools/apps.py', 'tools/make_layout.py', 'CMakeLists.txt'):
            (native / name).write_text('')
        env = dict(os.environ, QOL_TEST_INPUT=str(source), QOL_TEST_LOG=str(log),
                   QOL_MODERN_TYPES='0', QOL_MODERN_BATTLE='0', QOL_MODERN_MOVES='0',
                   PATH=str(binary) + os.pathsep + os.environ['PATH'])
        env.pop('QOL_SKIP_CATCHING_TUTORIAL', None)
        if option is not None:
            env['QOL_SKIP_CATCHING_TUTORIAL'] = option
        result = subprocess.run(['bash', str(wrapper), str(native)], cwd=game_root,
                                env=env, capture_output=True, text=True)
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, calls, game_root, source

    def test_default_pipeline_uses_patched_rom_for_layout_and_translation(self):
        result, calls, game_root, source = self.pipeline(None)
        self.assertEqual(result.returncode, 0, result.stderr)
        transforms = [c for c in calls if c[0].endswith('skip_catching_tutorial.py')]
        self.assertEqual(len(transforms), 1)
        layout = next(c for c in calls if c[0].endswith('make_layout.py'))
        translation = next(c for c in calls if c[0].endswith('recomp.py'))
        selected = Path(layout[2])
        self.assertEqual(translation[translation.index('--rom') + 1], str(selected))
        self.assertTrue(selected.read_bytes() == skip.patch_rom(source.read_bytes()))
        self.assertTrue((game_root / 'build/soulsilver.us/pokesoulsilver.us.nds').read_bytes() == source.read_bytes())

    def test_disabled_pipeline_retains_original_tutorial_rom(self):
        result, calls, game_root, source = self.pipeline('0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c[0].endswith('skip_catching_tutorial.py') for c in calls))
        layout = next(c for c in calls if c[0].endswith('make_layout.py'))
        self.assertTrue(Path(layout[2]).read_bytes() == source.read_bytes())

    def test_invalid_option_is_rejected_before_game_build(self):
        result, calls, _, _ = self.pipeline('invalid')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(calls, 'Invalid option reached a build tool')


if __name__ == '__main__':
    unittest.main()
