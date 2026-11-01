"""Compile Competitive presentation after original stat-script SDK parity."""
import hashlib
from pathlib import Path
from battle_scripts import ROOT, compile_battle_script

COMPETITIVE_SUBSCRIPT = 298
PARITY_SOURCE = Path('files/battledata/script/subscript/subscript_0012_UpdateStatStage.s')
PARITY_SHA256 = 'ba9ac6363a1fbff29b678ddd7189f4245bf4b894c6fcdba8d3947b8e62125336'
COMPETITIVE_SOURCE = '''    .include "macros/btlcmd.inc"

    .data

_000:
    // SIDE_EFFECT_MON preserves the causal attacker and reveals the holder to AI.
    PrintMessage msg_0197_01087, TAG_NICKNAME_ABILITY, BATTLER_CATEGORY_SIDE_EFFECT_MON, BATTLER_CATEGORY_SIDE_EFFECT_MON
    Wait
    WaitButtonABTime 30
    PlayBattleAnimation BATTLER_CATEGORY_SIDE_EFFECT_MON, BATTLE_ANIMATION_STAT_BOOST
    Wait
    PrintBufferedMessage
    Wait
    WaitButtonABTime 30
    End
'''


def modern_competitive_script(original_stat_script, root=ROOT):
    source = (Path(root) / PARITY_SOURCE).read_text()
    if hashlib.sha256(source.encode()).hexdigest() != PARITY_SHA256:
        raise ValueError('Stat-stage subscript differs from the expected source')
    if compile_battle_script(source, root) != original_stat_script:
        raise ValueError('The unchanged stat-stage source does not match NARC member 12; check the SDK/compiler profile')
    return compile_battle_script(COMPETITIVE_SOURCE, root)
