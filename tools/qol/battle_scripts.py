"""Compile generated battle scripts without changing the source filesystem.

Battle-rule ROM generation uses the user's original Metrowerks assembler, Wine,
and GNU ARM objcopy. An unchanged-source byte comparison guards the SDK/profile
before a transformed script can be used. Default and type-only builds never call
this module's compiler. WINE, WINEPREFIX, MWAS and OBJCOPY may select user tools.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PARALYSIS_SOURCE = Path('files/battledata/script/subscript/subscript_0031_Paralyze.s')
DRAIN_SOURCE = Path('files/battledata/script/subscript/subscript_0024_DrainHalfDamageDealt.s')
# Pin the entire original source, including the Big Root and ability branches.
_DRAIN_SOURCE_SHA256 = '9abd94d77c6cff3a3ee46aac798ae5615c16db9e084afda29c00d00d12fdff41'

# Member, source name, weather flag/rock effect, and complete original-source hash.
# Snow Warning retains hail here; the Snow rules are a separate change.
WEATHER_SCRIPTS = {
    183: ('Drizzle', 'RAIN', '5d576755c534d6c7473e60a923b557b680a5ce19a2794be1d39db5ea01b5c40f'),
    184: ('SandStream', 'SANDSTORM', '40d16e34286d1a83569d1b43e033061d5221179d4971d2fe7c7088622f392b10'),
    185: ('Drought', 'SUN', 'a5d7d8f67ec08203832a4e6bdc0df3fb63dbad9ed3dcd3d50f0840ec07b593d5'),
    252: ('SnowWarning', 'HAIL', 'ff462c4a99f1084f342046bfeeb2d4f517a91a245eb205e0dd0631fd95cb15a9'),
}


def modern_weather_source(source, member):
    """Generate finite ability weather using the source battler's active rock."""
    if member not in WEATHER_SCRIPTS:
        raise ValueError(f'Unknown ability-weather subscript {member}')
    _, weather, digest = WEATHER_SCRIPTS[member]
    if hashlib.sha256(source.encode()).hexdigest() != digest:
        raise ValueError(f'Weather subscript {member} differs from the expected source')
    permanent = f'FIELD_CONDITION_{weather}_PERMANENT'
    turns = (
        '    UpdateVar OPCODE_SET, BSCRIPT_VAR_WEATHER_TURNS, 5\n'
        '    CheckItemHoldEffect CHECK_OPCODE_NOT_HAVE, BATTLER_CATEGORY_MSG_BATTLER_TEMP, '
        f'HOLD_EFFECT_EXTEND_{weather}, _QolWeatherEnd\n'
        '    UpdateVar OPCODE_SET, BSCRIPT_VAR_WEATHER_TURNS, 8\n\n'
        '_QolWeatherEnd:\n')
    return source.replace(permanent, f'FIELD_CONDITION_{weather}').replace('    End ', turns + '    End ', 1)


def modern_weather_script(original, member, root=ROOT):
    """Require exact original NARC parity before assembling finite weather."""
    if member not in WEATHER_SCRIPTS:
        raise ValueError(f'Unknown ability-weather subscript {member}')
    name = WEATHER_SCRIPTS[member][0]
    path = f'files/battledata/script/subscript/subscript_{member:04}_{name}.s'
    source = (Path(root) / path).read_text()
    transformed = modern_weather_source(source, member)
    if compile_battle_script(source, root) != original:
        raise ValueError(f'The unchanged weather source does not match NARC member {member}; check the SDK/compiler profile')
    return compile_battle_script(transformed, root)


def modern_drain_source(source):
    """Give move 580 three-quarter drain while preserving legacy drain paths."""
    if hashlib.sha256(source.encode()).hexdigest() != _DRAIN_SOURCE_SHA256:
        raise ValueError('Drain subscript differs from the expected source')
    division = '    DivideVarByValue BSCRIPT_VAR_HP_CALC, 2\n'
    # HIT_DAMAGE is negative. Multiply before dividing to avoid double rounding;
    # DivideVarByValue calls DamageDivide, preserving the minimum one HP drain.
    # The existing zero-damage branch still skips both recovery calculations.
    calculation = (
        '    CompareVarToValue OPCODE_EQU, BSCRIPT_VAR_MOVE_NO_CUR, 580, _QolDrainingKiss\n'
        + division +
        '    GoTo _011\n\n'
        '_QolDrainingKiss:\n'
        '    UpdateVar OPCODE_MUL, BSCRIPT_VAR_HP_CALC, 3\n'
        '    DivideVarByValue BSCRIPT_VAR_HP_CALC, 4\n')
    return source.replace(division, calculation, 1)


def modern_paralysis_source(source):
    """Add current-type immunity at the Gen IX priority, retaining old paths."""
    status = ('    CompareMonDataToValue OPCODE_FLAG_SET, BATTLER_CATEGORY_SIDE_EFFECT_MON, '
              'BMON_DATA_STATUS, STATUS_PARALYSIS, _139\n')
    immunity = ('    GoTo _211\n'
                '    CompareVarToValue OPCODE_EQU, BSCRIPT_VAR_SIDE_EFFECT_TYPE, '
                'SIDE_EFFECT_TYPE_INDIRECT, _218\n')
    priority = ('_041:\n' + status +
                '    CompareMonDataToValue OPCODE_NEQ, BATTLER_CATEGORY_SIDE_EFFECT_MON, '
                'BMON_DATA_STATUS, STATUS_NONE, _123\n')
    message = (immunity + '    WaitButtonABTime 30\n'
               '    // It doesn’t affect {0}...\n'
               '    PrintMessage msg_0197_00027, TAG_NICKNAME, BATTLER_CATEGORY_SIDE_EFFECT_MON\n'
               '    GoTo _211\n\n_170:\n')
    if (source.count(priority) != 1 or source.count(message) != 1
            or source.count(status) != 1 or source.count(immunity) != 1
            or '_QolElectricImmune' in source):
        raise ValueError('Paralysis subscript differs from the expected source')
    checks = ''.join(
        '    CompareMonDataToValue OPCODE_EQU, BATTLER_CATEGORY_SIDE_EFFECT_MON, '
        f'BMON_DATA_TYPE_{slot}, TYPE_ELECTRIC, _QolElectricImmune\n'
        for slot in (1, 2))
    return source.replace(status, status + checks).replace(
        immunity, immunity.replace('    GoTo _211\n', '    GoTo _211\n\n_QolElectricImmune:\n', 1))


def battle_script_tools(root=ROOT):
    """Resolve the same user-supplied toolchain as the normal script build."""
    local_wine = root / '.local-tools/Wine Devel.app/Contents/Resources/wine/bin/wine'
    wine = os.environ.get('WINE') or shutil.which('wine') or str(local_wine)
    assembler = os.environ.get('MWAS') or str(root / 'tools/mwccarm/2.0/sp2p2/mwasmarm.exe')
    objcopy = os.environ.get('OBJCOPY') or shutil.which('arm-none-eabi-objcopy')
    for name, path in (('Wine', wine), ('Metrowerks assembler', assembler), ('GNU ARM objcopy', objcopy)):
        if not path or not (Path(path).is_file() or shutil.which(path)):
            raise FileNotFoundError(f'Modern battle scripts require the user-supplied {name}')
    return wine, assembler, objcopy


def compile_battle_script(source, root=ROOT):
    """Assemble in a disposable directory; all emitted files stay outside files/."""
    root = Path(root).resolve()
    wine, assembler, objcopy = battle_script_tools(root)
    environment = os.environ.copy()
    environment['PATH'] = str(Path(wine).resolve().parent) + os.pathsep + environment.get('PATH', '')
    environment.setdefault('WINEPREFIX', str(root / '.local-tools/wineprefix'))
    environment.setdefault('WINEDLLOVERRIDES', 'winex11.drv,winewayland.drv=d')
    environment.setdefault('WINEDEBUG', '-all')
    includes = ('.', 'include', 'asm/include', 'files', 'lib/asm/include',
                'lib/NitroDWC/asm/include', 'lib/MSL_C/asm/include',
                'lib/NitroSDK/asm/include', 'lib/syscall/asm/include', 'asm', 'files/msgdata')
    arguments = ['-DSOULSILVER', '-DGAME_REMASTER=0', '-DENGLISH', '-DPM_KEEP_ASSERTS',
                 '-DSDK_ARM9', '-DSDK_CODE_ARM', '-DSDK_FINALROM', '-proc', 'arm5te', '-g', '-gccinc']
    for include in includes:
        arguments += ['-i', include]
    arguments += ['-Ilib/include', '-DSDK_ASM', '-DPM_ASM']
    with tempfile.TemporaryDirectory(prefix='qol-battle-') as folder:
        temporary = Path(folder)
        script, obj, binary = (temporary / name for name in ('script.s', 'script.o', 'script.bin'))
        script.write_text(source)
        # Wine's default Z: drive exposes Unix absolute paths, including spaces.
        def windows_path(path):
            return 'Z:' + str(path.resolve()).replace('/', '\\')
        commands = ([wine, assembler, *arguments, '-o', windows_path(obj), windows_path(script)],
                    [objcopy, '-O', 'binary', '--file-alignment', '4', str(obj), str(binary)])
        for command in commands:
            result = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise RuntimeError(f'Battle script compiler failed ({Path(command[0]).name}):\n{result.stdout}{result.stderr}')
        return binary.read_bytes()


def modern_paralysis_script(original, root=ROOT):
    """Require exact original NARC parity before returning relocated bytecode."""
    source = (Path(root) / PARALYSIS_SOURCE).read_text()
    transformed = modern_paralysis_source(source)
    if compile_battle_script(source, root) != original:
        raise ValueError('The unchanged paralysis source does not match NARC member 31; check the SDK/compiler profile')
    return compile_battle_script(transformed, root)


def modern_drain_script(original, root=ROOT):
    """Require original member 24 parity before assembling relocated drain code."""
    source = (Path(root) / DRAIN_SOURCE).read_text()
    transformed = modern_drain_source(source)
    if compile_battle_script(source, root) != original:
        raise ValueError('The unchanged drain source does not match NARC member 24; check the SDK/compiler profile')
    return compile_battle_script(transformed, root)
