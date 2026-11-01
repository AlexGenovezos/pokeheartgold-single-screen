"""Modern Oblivious and Intimidate, guarded by full source/SDK byte parity.

Behavior references: hg-engine61b510cfb6cf7d77c3b083150fad3499f82fd326 and
pokeemerald-expansion c460a8661dfa0598ae25d42a968c690ecbf489c6; see QOL-REUSE.
Only existing members132/186/221 change. No new script or native context fields.
"""
import hashlib
from pathlib import Path
from battle_scripts import ROOT, compile_battle_script

ABILITY_SCRIPTS = {
    132: ('TauntStart', '04d6e3df5c1be258736f622b84877cb87a25e93c643faffae3d1b2211f8f4d04'),
    186: ('Intimidate', 'd327ba1e575a8cac64a7205eac948d839f17c4555f6b5a9a5acd9bbc43de4f9e'),
    221: ('NoStatusAbility', '56e4c66a3de2ddd299b9202d1c9cac63ea0ce21031f7b6b7db0908d3a4a30dc9'),
}


def _validate_source(source, member):
    if member not in ABILITY_SCRIPTS:
        raise ValueError(f'Unknown Oblivious/Intimidate subscript {member}')
    if hashlib.sha256(source.encode()).hexdigest() != ABILITY_SCRIPTS[member][1]:
        raise ValueError(f'Ability subscript {member} differs from the expected source')


def modern_oblivious_intimidate_source(source, member):
    """Relocate original branches by reassembly, retaining all other paths."""
    _validate_source(source, member)
    if member == 132:
        check = ('    CheckIgnorableAbility CHECK_OPCODE_HAVE, BATTLER_CATEGORY_DEFENDER, '
                 'ABILITY_OBLIVIOUS, _QolOblivious\n')
        return source.replace('_000:\n', '_000:\n' + check, 1) + '''
_QolOblivious:
    PrintAttackMessage
    Wait
    PrintMessage msg_0197_00714, TAG_NICKNAME_ABILITY_MOVE, BATTLER_CATEGORY_DEFENDER, BATTLER_CATEGORY_DEFENDER, BATTLER_CATEGORY_ATTACKER
    Wait
    WaitButtonABTime 30
    UpdateVar OPCODE_FLAG_ON, BSCRIPT_VAR_MOVE_STATUS_FLAGS, MOVE_STATUS_NO_MORE_WORK
    End
'''
    if member == 186:
        checks = ''.join(
            '    CheckAbility CHECK_OPCODE_HAVE, BATTLER_CATEGORY_SIDE_EFFECT_MON, '
            f'ABILITY_{ability}, _QolIntimidateBlocked\n'
            for ability in ('INNER_FOCUS', 'OWN_TEMPO', 'OBLIVIOUS', 'SCRAPPY'))
        anchor = '    UpdateVar OPCODE_SET, BSCRIPT_VAR_SIDE_EFFECT_PARAM, MOVE_SUBSCRIPT_PTR_ATTACK_DOWN_1_STAGE\n'
        # Plain CheckAbility reads the active ability, without borrowing a move's
        # Mold Breaker. The existing owner/target/doubles loop stays intact.
        return source.replace(anchor, checks + anchor, 1) + '''
_QolIntimidateBlocked:
    PrintMessage msg_0197_00727, TAG_NICKNAME_ABILITY_NICKNAME_ABILITY, BATTLER_CATEGORY_SIDE_EFFECT_MON, BATTLER_CATEGORY_SIDE_EFFECT_MON, BATTLER_CATEGORY_ATTACKER, BATTLER_CATEGORY_ATTACKER
    Wait
    WaitButtonABTime 30
    GoTo _038
'''
    # Message7 is a volatile cure, outside the native status names0..6. Branch
    # before formatting740 and keep both the primary status and its icon intact.
    source = source.replace('_000:\n', '_000:\n    CompareVarToValue OPCODE_EQU, BSCRIPT_VAR_MESSAGE, 7, _QolTaunt\n', 1)
    source = source.replace(
        'TAG_NICKNAME_ABILITY_STATUS, BATTLER_CATEGORY_MSG_TEMP, BATTLER_CATEGORY_MSG_TEMP, BATTLER_CATEGORY_MSG_TEMP',
        'TAG_NICKNAME_ABILITY_STATUS, BATTLER_CATEGORY_MSG_BATTLER_TEMP, BATTLER_CATEGORY_MSG_BATTLER_TEMP, BATTLER_CATEGORY_MSG_TEMP', 1)
    source = source.replace('    SetHealthbarStatus BATTLER_CATEGORY_MSG_TEMP, BATTLE_ANIMATION_NONE\n',
        '    CompareVarToValue OPCODE_EQU, BSCRIPT_VAR_MESSAGE, 5, _QolCureWait\n'
        '    CompareVarToValue OPCODE_EQU, BSCRIPT_VAR_MESSAGE, 6, _QolCureWait\n'
        '    SetHealthbarStatus BATTLER_CATEGORY_MSG_TEMP, BATTLE_ANIMATION_NONE\n\n_QolCureWait:\n', 1)
    # Inline the native288 Taunt-end text: no Call, stack growth or primary cure.
    return source + '''
_QolTaunt:
    UpdateMonData OPCODE_SET, BATTLER_CATEGORY_MSG_BATTLER_TEMP, BMON_DATA_TAUNTED_TURNS, 0
    PrintMessage msg_0197_01087, TAG_NICKNAME_ABILITY, BATTLER_CATEGORY_MSG_BATTLER_TEMP, BATTLER_CATEGORY_MSG_BATTLER_TEMP
    Wait
    WaitButtonABTime 30
    UpdateVar OPCODE_SET, BSCRIPT_VAR_MSG_MOVE_TEMP, MOVE_TAUNT
    PrintMessage msg_0197_01257, TAG_NICKNAME_MOVE, BATTLER_CATEGORY_MSG_BATTLER_TEMP, BATTLER_CATEGORY_MSG_TEMP
    Wait
    WaitButtonABTime 30
    End
'''


def modern_oblivious_intimidate_script(original, member, root=ROOT):
    """Fail before modified compilation if source, member or SDK parity drifts."""
    if member not in ABILITY_SCRIPTS:
        raise ValueError(f'Unknown Oblivious/Intimidate subscript {member}')
    name = ABILITY_SCRIPTS[member][0]
    source = (Path(root) / f'files/battledata/script/subscript/subscript_{member:04}_{name}.s').read_text()
    _validate_source(source, member)
    if compile_battle_script(source, root) != original:
        raise ValueError(f'The unchanged ability source does not match NARC member {member}; check the SDK/compiler profile')
    return compile_battle_script(modern_oblivious_intimidate_source(source, member), root)
