"""Private A14 effects and sequential native stat events, without ABI growth.

Effect templates are unchanged native10/138, and multi-stat control follows
native Bulk Up150. Require full source hashes and SDK/NARC parity before using
those templates. New commands are compiled explicitly, never copied as assumed
binary-compatible upstream hg-engine scripts. Gen IX Shell Smash drops first.
"""
import hashlib
from pathlib import Path
import struct
from battle_scripts import ROOT, compile_battle_script
from nitro_data import pack_narc, unpack_narc

STATUS_EFFECT_SOURCE='files/battledata/script/effect_script/effect_script_0010.s'
SELF_EFFECT_SOURCE='files/battledata/script/effect_script/effect_script_0138.s'
MULTI_SOURCE='files/battledata/script/subscript/subscript_0150_BulkUp.s'
SOURCE_HASHES={
 STATUS_EFFECT_SOURCE:'d50993000decb1993721091d7bfd59e8bbc6266a8f21b0e9dc33ff7ce2e8602b',
 SELF_EFFECT_SOURCE:'58824de08b95618a00326581ebbd25b18aea668ef751f2bc4f338a32530e16ba',
 MULTI_SOURCE:'c04443662d8ffa2429ecf68725239fac317fe9c230aa87add73d626076c80cff',
}
# (battle stat, signed requested delta), in causal order. Native stat12 clamps
# once and owns Simple, immunities, Competitive, and the actual-delta message.
STAT_EVENTS={
 299:(('ATK',1),('ACC',1)),
 300:(('SPATK',1),('SPDEF',1),('SPEED',1)),
 301:(('ATK',1),('DEF',1),('ACC',1)),
 302:(('ATK',1),('SPATK',1)),
 303:(('DEF',-1),('SPDEF',-1),('ATK',2),('SPATK',2),('SPEED',2)),
}
STAT_PARAMS={('ATK',1):15,('DEF',1):16,('SPEED',1):17,('SPATK',1):18,
             ('SPDEF',1):19,('ACC',1):20,('DEF',-1):23,('SPDEF',-1):26,
             ('ATK',2):39,('SPATK',2):42,('SPEED',2):41}


def _guard(source,path):
    if hashlib.sha256(source.encode()).hexdigest()!=SOURCE_HASHES[path]:
        raise ValueError(f'A14 template {path} differs from the expected source')


def modern_move_effect_source(source,member):
    if not 277<=member<=283:raise ValueError('Unknown A14 effect member')
    path=SELF_EFFECT_SOURCE if member==283 else STATUS_EFFECT_SOURCE
    _guard(source,path)
    if member==283:
        # Same successful-hit/attacker timing as native Defense-up effect138.
        return source.replace('MOVE_SUBSCRIPT_PTR_DEFENSE_UP_1_STAGE','MOVE_SUBSCRIPT_PTR_SPEED_UP_1_STAGE',1)
    return source.replace('MOVE_SUBSCRIPT_PTR_ATTACK_UP_1_STAGE',str(145+member-277),1)


def modern_move_stat_source(source,member):
    if member not in STAT_EVENTS:raise ValueError('Unknown A14 stat subscript')
    _guard(source,MULTI_SOURCE)
    events=STAT_EVENTS[member]
    result='    .include "macros/btlcmd.inc"\n\n    .data\n\n_000:\n'
    # Any possible event makes the whole move succeed, even if others cap out.
    for stat,delta in events:
        result+=f'    CompareMonDataToValue OPCODE_NEQ, BATTLER_CATEGORY_SIDE_EFFECT_MON, BMON_DATA_STAT_CHANGE_{stat}, {12 if delta>0 else 0}, _QolStart\n'
    result+='    GoTo _QolFail\n\n_QolStart:\n'
    result+='''    Call BATTLE_SUBSCRIPT_ATTACK_MESSAGE_AND_ANIMATION
    UpdateVar OPCODE_FLAG_ON, BSCRIPT_VAR_BATTLE_STATUS, BATTLE_STATUS_MESSAGES_OFF
    UpdateVar OPCODE_FLAG_ON, BSCRIPT_VAR_BATTLE_STATUS, BATTLE_STATUS_NO_ATTACK_MESSAGE|BATTLE_STATUS_MOVE_ANIMATIONS_OFF
    UpdateVar OPCODE_FLAG_ON, BSCRIPT_VAR_BATTLE_STATUS_2, BATTLE_STATUS2_STAT_STAGE_CHANGE_SHOWN
'''
    for i,(stat,delta) in enumerate(events):
        # Skip capped events silently so the final event cannot overwrite a
        # partial success with a failure, and no duplicate cap message appears.
        result+=f'''    CompareMonDataToValue OPCODE_EQU, BATTLER_CATEGORY_SIDE_EFFECT_MON, BMON_DATA_STAT_CHANGE_{stat}, {12 if delta>0 else 0}, _QolNext{i}
    UpdateVar OPCODE_SET, BSCRIPT_VAR_SIDE_EFFECT_PARAM, {STAT_PARAMS[stat,delta]}
    Call BATTLE_SUBSCRIPT_UPDATE_STAT_STAGE
_QolNext{i}:
'''
    result+='''    UpdateVar OPCODE_FLAG_OFF, BSCRIPT_VAR_BATTLE_STATUS_2, BATTLE_STATUS2_UPDATE_STAT_STAGES
    UpdateVar OPCODE_FLAG_OFF, BSCRIPT_VAR_BATTLE_STATUS_2, BATTLE_STATUS2_STAT_STAGE_CHANGE_SHOWN
    End

_QolFail:
    PrintAttackMessage
    Wait
    WaitButtonABTime 30
'''
    result+=('    PrintMessage msg_0197_00796, TAG_NONE\n' if member==303 else
             '    PrintMessage msg_0197_00768, TAG_NICKNAME, BATTLER_CATEGORY_SIDE_EFFECT_MON\n')
    result+='''    Wait
    WaitButtonABTime 30
    UpdateVar OPCODE_FLAG_ON, BSCRIPT_VAR_MOVE_STATUS_FLAGS, MOVE_STATUS_NO_MORE_WORK
    End
'''
    return result


def _validated_source(path,original,root):
    source=(Path(root)/path).read_text()
    _guard(source,path)
    if compile_battle_script(source,root)!=original:
        raise ValueError(f'The unchanged A14 template does not match NARC member {path}; check the SDK/compiler profile')
    return source


def modern_move_effect_resources(archive,root=ROOT):
    members,names=unpack_narc(archive)
    if len(members)!=277:raise ValueError('A14 requires exactly 277 native effects')
    status=_validated_source(STATUS_EFFECT_SOURCE,members[10],root)
    secondary=_validated_source(SELF_EFFECT_SOURCE,members[138],root)
    members.extend(compile_battle_script(modern_move_effect_source(secondary if i==283 else status,i),root)
                   for i in range(277,284))
    return pack_narc(members,names)


def modern_move_stat_resources(archive,battle_rules=False,root=ROOT):
    members,names=unpack_narc(archive)
    expected=299 if battle_rules else 297
    if len(members)!=expected:
        raise ValueError(f'A14 requires exactly {expected} subscripts after existing battle transforms')
    source=_validated_source(MULTI_SOURCE,members[150],root)
    if not battle_rules:
        # Reserve the independently enabled Cursed Body/Competitive IDs safely.
        members.extend([struct.pack('<I',224)]*2)
    members.extend(compile_battle_script(modern_move_stat_source(source,i),root) for i in range(299,304))
    return pack_narc(members,names)
