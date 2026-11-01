"""Guarded Snow presentation/effect and fixed-width native AI source edits.

Hail258 remains the compatibility name. Original sources and encoded banks are
validated before touching words; battle templates keep their STRVAR commands.
Snow follows Simple, and ability bank722 remains ability_descriptions' property.
"""
import argparse
import hashlib
from pathlib import Path
import re
import struct

from battle_scripts import ROOT, compile_battle_script
from game_text import game_text
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc
from simple_scripts import MESSAGE_COUNT, MESSAGE_KEY, MESSAGE_BINARY_SHA256, modern_simple_message_resources

EFFECT_SOURCE = 'files/battledata/script/effect_script/effect_script_0164.s'
EFFECT_SHA256 = '9ee9187c81dc83b531cebd1752b0512a0cf70a2871c456117641e7afd2e0203c'
AI_SHA256 = '27545ae40eb1c9285ea915bb85abce1e5dff8da1f38f1b870c82f8dee8fe4766'
# Bank: filename suffix, full original source digest, encoded bank digest.
MESSAGE_BANKS = {
    197: ('', '3311dd2b5be57f471ae62fcc26851ca41e131b393f9f697deff7ee62927a494f', MESSAGE_BINARY_SHA256),
    221: ('', '72a2c890304ebcab65f70d487423e402572301ec208936888061db5ff137748d', 'd5504272b9fb1fa8bd735266ea630a2a6e42e038415d4716d0eabc2019db5a01'),
    622: ('_T28GYM0101', '5a82034236890ce6ed03b3b42032af596c1560a92ad2a7f08f666f6fce479e6c', '20462c27e3649ebeef6f872cbb04667d640cd8d71da7400565418de3733429b3'),
    426: ('', '2bc089d20680ff97496159d8db02a817fce3bdd6693802404645bb12a462640f', '5c5a1d06273ed5c2217d7c1c00f622391c8d589785065cdc042f0be5049290a5'),
    157: ('', '747e954fe56b3deb343ff1b5fcd4320241524144ad38d655221dd6a59e0a15eb', 'e7ff37547d11737c369351c71f868b45b654ceb82405bd21e91ed69d8122995b'),
    749: ('', 'f0763a0583c68cae0c4ec967c202ccae643700147887389c194ffc509670c796', '2dd75559a6057016bc5fb3d577b9eaaeb5541d2ac15cc6774750668458f31f77'),
}
SNOW_TEXT = {
    197: {810:'It started to snow!',811:'Snow continues to fall.',812:'The snow stopped.'},
    221: {282:'A Pokémon held item that extends\nthe duration of snow summoned by\nthe holder.',
          334:'Summons snow for five turns.\nIce-type Pokémon gain a Defense\nboost while it is snowing.'},
    622: {4:'Pryce: That TM contains Hail.\rIt summons snow for five turns.\nIce-type Pokémon gain a\fDefense boost while it snows.'},
    426: {43:'This match will be conducted under\nfalling snow.'},
    157: {47:'Weather: Snow'},
    749: {258:'Summons snow for\nfive turns, boosting\nthe Defense of\nIce-type Pokémon\nby 50 percent.'},
}


def modern_snow_effect_source(source):
    if hashlib.sha256(source.encode()).hexdigest() != EFFECT_SHA256:
        raise ValueError('Snow effect164 differs from the expected source')
    return source.replace('FIELD_CONDITION_HAIL, _036', 'FIELD_CONDITION_HAIL_ALL, _036', 1)


def modern_snow_effect_script(original, root=ROOT):
    source = (Path(root)/EFFECT_SOURCE).read_text()
    modern = modern_snow_effect_source(source)
    if compile_battle_script(source, root) != original:
        raise ValueError('The unchanged Snow effect source does not match NARC member164; check the SDK/compiler profile')
    return compile_battle_script(modern, root)


def modern_snow_effect_resources(archive):
    members,names = unpack_narc(archive)
    if len(members) <= 164:
        raise ValueError('Snow effect164 is absent')
    members[164] = modern_snow_effect_script(members[164])
    return pack_narc(members,names)


def _plain_text(text, charmap):
    # Native page/scroll controls, never XML/STRVAR source strings.
    controls = {'\r':0x25BC, '\f':0x25BD}
    words = []
    for part in re.split('([\r\f])', text):
        words.extend([controls[part]] if part in controls else game_text(part,charmap)[:-1])
    return words+[0xFFFF]


def _replace_literal(row, old, new, charmap):
    before,after = game_text(old,charmap)[:-1],game_text(new,charmap)[:-1]
    positions = [i for i in range(len(row)) if row[i:i+len(before)] == before]
    if len(positions) != 1:
        raise ValueError('Expected one Snow literal in encoded battle template')
    start = positions[0]
    return row[:start]+after+row[start+len(before):]


def modern_snow_message_resources(archive, charmap, root=ROOT):
    banks,names = unpack_narc(archive)
    if len(banks) <= max(MESSAGE_BANKS):
        raise ValueError('Snow message bank is absent')
    for bank,(suffix,digest,binary_digest) in MESSAGE_BANKS.items():
        source = (Path(root)/f'files/msgdata/msg/msg_{bank:04}{suffix}.gmm').read_bytes()
        if hashlib.sha256(source).hexdigest() != digest:
            raise ValueError(f'Snow bank{bank} differs from the expected source')
        words,key = unpack_messages(banks[bank])
        if bank == 197:
            if len(words) != MESSAGE_COUNT+9 or key != MESSAGE_KEY:
                raise ValueError('Snow requires bank197 after Simple')
            original = pack_messages(words[:MESSAGE_COUNT],key)
            if hashlib.sha256(original).hexdigest() != binary_digest:
                raise ValueError('Snow bank197 does not match the unchanged encoded source')
            # Reuse Simple's guarded producer to validate all nine appended
            # templates exactly, including native encoded format arguments.
            expected = unpack_narc(modern_simple_message_resources(
                pack_narc([b'']*197+[original]),charmap,root))[0][197]
            if banks[197] != expected:
                raise ValueError('Snow bank197 does not match the Simple producer')
            words[701] = _replace_literal(words[701],'whipped up a hailstorm!','made it snow!',charmap)
            for row in (702,703):
                words[row] = _replace_literal(words[row],'whipped up','made',charmap)
                words[row] = _replace_literal(words[row],'a hailstorm!','it snow!',charmap)
        elif hashlib.sha256(banks[bank]).hexdigest() != binary_digest:
            raise ValueError(f'Snow bank{bank} does not match the unchanged encoded source')
        for row,text in SNOW_TEXT[bank].items():
            words[row] = _plain_text(text,charmap)
        banks[bank] = pack_messages(words,key)
    return pack_narc(banks,names)


def modern_snow_ai_source(source):
    if hashlib.sha256(source.encode()).hexdigest() != AI_SHA256:
        raise ValueError('Snow trainer AI differs from the expected source')
    start = source.index('gTrainerAITable:\n')+len('gTrainerAITable:\n')
    # Numeric byte table ends at the next public declaration (command pointers).
    end = source.index('\n\t.public',start)
    matches = list(re.finditer(r'0x([0-9A-Fa-f]{2})',source[start:end]))
    data = bytes(int(m.group(1),16) for m in matches)
    if len(data)%4:
        raise ValueError('Unexpected trainer AI word alignment')
    words = struct.unpack('<'+'I'*(len(data)//4),data)
    if words[5742:5749] != (46,19,3,5,19,4,14):
        raise ValueError('Unexpected trainer AI Hail chip comparison operands')
    # AICmd_IfLoadedEqualTo 4, +14 skips into the Ice-immunity Hail-chip
    # heuristic. Weather enum4 is still queried raw elsewhere for duplicates.
    for match in reversed(matches[5747*4:5748*4]):
        lo,hi = start+match.start(),start+match.end()
        source = source[:lo]+'0xFF'+source[hi:]
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--modern',action='store_true')
    args = parser.parse_args()
    source = args.source.read_text()
    args.output.write_text(modern_snow_ai_source(source) if args.modern else source)


if __name__ == '__main__':
    main()
