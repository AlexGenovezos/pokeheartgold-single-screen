"""Append a call-free Wind Rider presentation after all original script owners."""
import hashlib
from pathlib import Path
import struct
from battle_scripts import compile_battle_script, ROOT
from nitro_data import pack_narc, unpack_narc

ORIGINAL_STAGE_SOURCE='files/battledata/script/subscript/subscript_0012_UpdateStatStage.s'
ORIGINAL_STAGE_SHA256='ba9ac6363a1fbff29b678ddd7189f4245bf4b894c6fcdba8d3947b8e62125336'
WIND_RIDER_SOURCE='''    .include "macros/btlcmd.inc"

    .data

_000:
    PlayBattleAnimation BATTLER_CATEGORY_SIDE_EFFECT_MON, BATTLE_ANIMATION_STAT_BOOST
    Wait
    PrintMessage msg_0197_00622, TAG_NICKNAME_ABILITY_STAT, BATTLER_CATEGORY_SIDE_EFFECT_MON, BATTLER_CATEGORY_SIDE_EFFECT_MON, BATTLER_CATEGORY_MSG_TEMP
    Wait
    WaitButtonABTime 30
    End
'''


def wind_rider_script(original_stage, root=ROOT):
    source=(Path(root)/ORIGINAL_STAGE_SOURCE).read_text()
    if hashlib.sha256(source.encode()).hexdigest()!=ORIGINAL_STAGE_SHA256:
        raise ValueError('Wind Rider requires the unchanged original subscript12 source')
    if compile_battle_script(source,root)!=original_stage:
        raise ValueError('The unchanged stage source does not match NARC member12; check the SDK/compiler profile')
    return compile_battle_script(WIND_RIDER_SOURCE,root)


def modern_wind_rider_resources(archive, moves=False):
    members,names=unpack_narc(archive)
    expected=304 if moves else 299
    if len(members)!=expected:
        raise ValueError(f'Wind Rider requires exactly {expected} battle subscripts after existing owners')
    presentation=wind_rider_script(members[12])
    if not moves:
        members.extend([struct.pack('<I',224)]*5)
    members.append(presentation)
    return pack_narc(members,names)
