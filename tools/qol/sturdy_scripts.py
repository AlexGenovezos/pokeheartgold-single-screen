"""Generate modern Sturdy messages from unchanged battle-script sources."""
import hashlib
from pathlib import Path
from battle_scripts import ROOT, compile_battle_script

STURDY_SCRIPTS = {
    21: ('MoveFollowupMessage', '8e407af293bb3d6e1fa08c0482d2839f62c00ec4b924638f79bb659d4de4a093'),
    121: ('FutureSightDamage', '84e10f3aa5d00ecefd6e562ef7335b9d9306a2cf3194b2708f026b21760286e3'),
}


def modern_sturdy_source(source, member):
    """Insert ability survival before item presentation/removal, with no assets."""
    if member not in STURDY_SCRIPTS:
        raise ValueError(f'Unknown Sturdy subscript {member}')
    if hashlib.sha256(source.encode()).hexdigest() != STURDY_SCRIPTS[member][1]:
        raise ValueError(f'Sturdy subscript {member} differs from the expected source')
    battler = 'BATTLER_CATEGORY_DEFENDER' if member == 21 else 'BATTLER_CATEGORY_MSG_TEMP'
    # MSG_TEMP means abilityTemp to GetAbilityMessageNo, whereas the explicit
    # battler category reads the delayed recipient's current ability.
    ability_battler = battler if member == 21 else 'BATTLER_CATEGORY_MSG_BATTLER_TEMP'
    finish = '_067' if member == 21 else '_116'
    label = '_011' if member == 21 else '_092'
    after = '_QolHeldItem' if member == 21 else '_QolEndure'
    completion = f'    GoTo {finish}\n'
    if member == 21:
        completion = (
            '    CompareVarToValue OPCODE_FLAG_NOT, BSCRIPT_VAR_MOVE_STATUS_FLAGS, MOVE_STATUS_STURDY_SKIP_EFFECTIVENESS, _067\n'
            '    UpdateVar OPCODE_FLAG_OFF, BSCRIPT_VAR_MOVE_STATUS_FLAGS, MOVE_STATUS_STURDY_SKIP_EFFECTIVENESS\n'
            '    GoTo _098\n')
    ability = (
        f'    CompareVarToValue OPCODE_FLAG_NOT, BSCRIPT_VAR_MOVE_STATUS_FLAGS, MOVE_STATUS_ENDURED_ABILITY, {after}\n'
        f'    PrintMessage msg_0197_00625, TAG_NICKNAME_ABILITY, {battler}, {ability_battler}\n'
        '    Wait \n'
        '    WaitButtonABTime 30\n'
        '    UpdateVar OPCODE_FLAG_OFF, BSCRIPT_VAR_MOVE_STATUS_FLAGS, MOVE_STATUS_ENDURED_ABILITY\n'
        + completion + f'\n{after}:\n')
    if member == 121:
        # Field damage runs after ordinary moves and can hit multiple slots.
        # A miss or Substitute must not reuse another move's survival flags.
        clear = ('    UpdateVar OPCODE_FLAG_OFF, BSCRIPT_VAR_MOVE_STATUS_FLAGS, '
                 'MOVE_STATUS_ENDURED|MOVE_STATUS_ENDURED_ITEM|MOVE_STATUS_ENDURED_ABILITY|MOVE_STATUS_STURDY_SKIP_EFFECTIVENESS\n')
        source = source.replace('_000:\n', '_000:\n' + clear, 1)
        ability += (
            '    CompareVarToValue OPCODE_FLAG_NOT, BSCRIPT_VAR_MOVE_STATUS_FLAGS, MOVE_STATUS_ENDURED, _QolHeldItem\n'
            f'    PrintMessage msg_0197_00445, TAG_NICKNAME, {battler}\n'
            '    Wait \n'
            '    WaitButtonABTime 30\n'
            f'    GoTo {finish}\n\n_QolHeldItem:\n')
    return source.replace(f'{label}:\n', f'{label}:\n' + ability, 1)


def modern_sturdy_script(original, member, root=ROOT):
    if member not in STURDY_SCRIPTS:
        raise ValueError(f'Unknown Sturdy subscript {member}')
    name = STURDY_SCRIPTS[member][0]
    source = (Path(root) / f'files/battledata/script/subscript/subscript_{member:04}_{name}.s').read_text()
    updated = modern_sturdy_source(source, member)
    if compile_battle_script(source, root) != original:
        raise ValueError(f'The unchanged Sturdy source does not match NARC member {member}; check the SDK/compiler profile')
    return compile_battle_script(updated, root)
