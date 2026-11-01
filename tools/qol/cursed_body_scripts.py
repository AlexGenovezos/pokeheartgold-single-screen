"""Compile Cursed Body presentation after verifying the original SDK profile."""
import hashlib
from pathlib import Path
from battle_scripts import ROOT, compile_battle_script

ORIGINAL_SUBSCRIPT_COUNT = 297
CURSED_BODY_SUBSCRIPT = 297
PARITY_SOURCE = Path('files/battledata/script/subscript/subscript_0071_Disabled.s')
PARITY_SHA256 = '790d7dd95606d885592fe43c64da5343aeddf18f6dfca770ee78bab451f5c41d'
CURSED_BODY_SOURCE = '''    .include "macros/btlcmd.inc"

    .data

_000:
    // The explicit defender ability category also reveals it to trainer AI.
    PrintMessage msg_0197_01087, TAG_NICKNAME_ABILITY, BATTLER_CATEGORY_DEFENDER, BATTLER_CATEGORY_DEFENDER
    Wait
    WaitButtonABTime 30
    PrintMessage msg_0197_00366, TAG_NICKNAME_MOVE, BATTLER_CATEGORY_ATTACKER, BATTLER_CATEGORY_MSG_TEMP
    Wait
    WaitButtonABTime 30
    End
'''


def modern_cursed_body_script(original_disabled_script, root=ROOT):
    source = (Path(root) / PARITY_SOURCE).read_text()
    if hashlib.sha256(source.encode()).hexdigest() != PARITY_SHA256:
        raise ValueError('Disable subscript differs from the expected source')
    if compile_battle_script(source, root) != original_disabled_script:
        raise ValueError('The unchanged Disable source does not match NARC member 71; check the SDK/compiler profile')
    return compile_battle_script(CURSED_BODY_SOURCE, root)
