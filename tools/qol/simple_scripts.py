"""Guarded modern Simple / X-item presentation; preserve all original resources.

The original encoded bank197 contains format-control words, so clone its three
side-aware templates and change only a uniquely matched plain-text adjective.
No XML STRVAR expression is ever passed to the literal font encoder.
"""
import hashlib
from pathlib import Path
from battle_scripts import ROOT, compile_battle_script
from game_text import game_text
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc

SIMPLE_SCRIPTS = {
    210: ('HeldItemSharplyRaiseStat', 'f2997124db740fadb9c79b0687f8ccfb011bbacc5e28da370b1fc1e66346aba5'),
    269: ('XItem', '6373af0d65bd3bf5598b59aa81b17225d284d281f84281f65ed0ff35ae721b30'),
}
MESSAGE_SOURCE_SHA256 = '3311dd2b5be57f471ae62fcc26851ca41e131b393f9f697deff7ee62927a494f'
MESSAGE_BINARY_SHA256 = 'cd45ea9f6ad249508c562c7c8967ee3929bec616a6aaa2034d329131180780bf'
MESSAGE_COUNT = 1276
MESSAGE_KEY = 47860
MESSAGE_TRIPLETS = ((1276, 753, 'sharply', 'drastically'),
                    (1279, 765, 'harshly', 'severely'),
                    (1282, 759, 'sharply', 'drastically'))


def modern_simple_source(source, member):
    if member not in SIMPLE_SCRIPTS:
        raise ValueError(f'Unknown Simple/X-item subscript {member}')
    if hashlib.sha256(source.encode()).hexdigest() != SIMPLE_SCRIPTS[member][1]:
        raise ValueError(f'Simple/X-item subscript {member} differs from the expected source')
    if member == 269:
        return source.replace('    PrintMessage msg_0197_00756, TAG_NICKNAME_ITEM_STAT, BATTLER_CATEGORY_ATTACKER, BATTLER_CATEGORY_MSG_TEMP, BATTLER_CATEGORY_MSG_TEMP',
                              '    PrintBufferedMessage', 1)
    # Same sequential Call12 / Call290 shape as original stat-berry208.
    # Held/Pluck/Fling callers retain their frames; neither call nests the other.
    first = source.index('    PlayBattleAnimation BATTLER_CATEGORY_MSG_TEMP, BATTLE_ANIMATION_STAT_BOOST')
    last = source.index('    Call BATTLE_SUBSCRIPT_PLUCK_CHECK')
    return source[:first] + '''    UpdateVar OPCODE_SET, BSCRIPT_VAR_SIDE_EFFECT_PARAM, MOVE_SUBSCRIPT_PTR_ATTACK_UP_2_STAGES-1
    UpdateVarFromVar OPCODE_ADD, BSCRIPT_VAR_SIDE_EFFECT_PARAM, BSCRIPT_VAR_MESSAGE
    UpdateVar OPCODE_SET, BSCRIPT_VAR_SIDE_EFFECT_TYPE, SIDE_EFFECT_TYPE_HELD_ITEM
    UpdateVarFromVar OPCODE_SET, BSCRIPT_VAR_BATTLER_STAT_CHANGE, BSCRIPT_VAR_MSG_BATTLER_TEMP
    Call BATTLE_SUBSCRIPT_UPDATE_STAT_STAGE
''' + source[last:]


def modern_simple_script(original, member, root=ROOT):
    if member not in SIMPLE_SCRIPTS:
        raise ValueError(f'Unknown Simple/X-item subscript {member}')
    name = SIMPLE_SCRIPTS[member][0]
    source = (Path(root) / f'files/battledata/script/subscript/subscript_{member:04}_{name}.s').read_text()
    modern = modern_simple_source(source, member)
    if compile_battle_script(source, root) != original:
        raise ValueError(f'The unchanged Simple/X-item source does not match NARC member {member}; check the SDK/compiler profile')
    return compile_battle_script(modern, root)


def modern_simple_message_resources(archive, charmap, root=ROOT):
    source = (Path(root) / 'files/msgdata/msg/msg_0197.gmm').read_bytes()
    if hashlib.sha256(source).hexdigest() != MESSAGE_SOURCE_SHA256:
        raise ValueError('Battle message bank197 differs from the expected source')
    banks, names = unpack_narc(archive)
    if len(banks) <= 197 or hashlib.sha256(banks[197]).hexdigest() != MESSAGE_BINARY_SHA256:
        raise ValueError('Battle message bank197 does not match the unchanged encoded source')
    original, key = unpack_messages(banks[197])
    if len(original) != MESSAGE_COUNT or key != MESSAGE_KEY:
        raise ValueError('Unexpected original battle message count/key')
    updated = list(original)
    for index, template, adjective, replacement in MESSAGE_TRIPLETS:
        if len(updated) != index:
            raise ValueError('Unexpected modern battle message ordering')
        old, new = game_text(adjective, charmap)[:-1], game_text(replacement, charmap)[:-1]
        for side in range(3):
            row = original[template + side]
            matches = [i for i in range(len(row)) if row[i:i + len(old)] == old]
            if len(matches) != 1:
                raise ValueError('Expected one literal adjective in encoded stat template')
            start = matches[0]
            updated.append(row[:start] + new + row[start + len(old):])
    encoded = pack_messages(updated, key)
    check, check_key = unpack_messages(encoded)
    if check_key != key or check[:MESSAGE_COUNT] != original or len(check) != MESSAGE_COUNT + 9:
        raise ValueError('Original battle message prefix/key changed')
    banks[197] = encoded
    return pack_narc(banks, names)
