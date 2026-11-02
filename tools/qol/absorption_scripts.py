"""Keep Motor Drive's shared script and add modern Sp. Atk absorption paths."""
import hashlib
from pathlib import Path
from battle_scripts import compile_battle_script, ROOT

SOURCE=Path('files/battledata/script/subscript/subscript_0182_MotorDrive.s')
SOURCE_SHA256='53c7b40bbf5522a595e578cc63f53c52eb4024346b4204705b6f5b7d0a8dc7cd'


def modern_absorption_source(source):
    if hashlib.sha256(source.encode()).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Absorption subscript differs from the expected source')
    anchor='    CompareMonDataToValue OPCODE_EQU, BATTLER_CATEGORY_DEFENDER, BMON_DATA_STAT_CHANGE_SPEED, 12, _032\n'
    checks='    CheckAbility CHECK_OPCODE_HAVE, BATTLER_CATEGORY_DEFENDER, ABILITY_WIND_RIDER, _QolWindAttack\n' + ''.join(f'    CheckAbility CHECK_OPCODE_HAVE, BATTLER_CATEGORY_DEFENDER, ABILITY_{ability}, _QolSpAttack\n'
                   for ability in ('LIGHTNINGROD','STORM_DRAIN'))
    # Reuse the original capped-stat message and presentation. Relative jumps
    # are assembled from labels; Motor Drive's complete path remains intact.
    boost=source[source.index(anchor):source.index('\n_032:')]
    boost=boost.replace('BMON_DATA_STAT_CHANGE_SPEED','BMON_DATA_STAT_CHANGE_SPATK')
    boost=boost.replace('BSCRIPT_VAR_MESSAGE, 3','BSCRIPT_VAR_MESSAGE, 4')
    wind=boost.replace('BMON_DATA_STAT_CHANGE_SPATK','BMON_DATA_STAT_CHANGE_ATK').replace('BSCRIPT_VAR_MESSAGE, 4','BSCRIPT_VAR_MESSAGE, 1')
    return source.replace(anchor,checks+anchor)+'\n_QolSpAttack:\n'+boost+'\n_QolWindAttack:\n'+wind


def modern_absorption_script(original,root=ROOT):
    source=(Path(root)/SOURCE).read_text()
    updated=modern_absorption_source(source)
    if compile_battle_script(source,root)!=original:
        raise ValueError('The unchanged absorption source does not match NARC member 182; check the SDK/compiler profile')
    return compile_battle_script(updated,root)
