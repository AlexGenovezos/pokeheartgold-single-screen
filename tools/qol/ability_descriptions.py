"""Extend native ability banks without changing existing IDs or Easy Chat."""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from game_text import game_text
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('files/msgdata/msg/msg_0722.gmm')
SOURCE_SHA256 = 'd364bd67c8c67554ea54654e0ceb372bf95d353efb4c2706664044e9d6306682'
ABILITY_BANKS = {
    720: ('48aa14d942578e68da6e6ba22985fd39871c0ed4e9b83bd5abb2f6ca22f0f4fa', 'Cursed Body'),
    721: ('7981861e435067d245dc4802e0947649f1b8d31f38f0c11d68781c08175a9251', 'CURSED BODY'),
    722: (SOURCE_SHA256, 'May disable a move that\nhits this Pokémon.'),
}
COMPETITIVE_BANKS = {
    720: 'Competitive',
    721: 'COMPETITIVE',
    722: 'Stat loss from a foe\nsharply raises Sp. Atk.',
}
DESCRIPTIONS = {
    5: 'At full HP, survives a hit.\nBlocks 1-hit KO moves.',
    31: 'Draws in Electric moves.\nAbsorbs them for Sp. Atk.',
    35: 'Prevents accuracy loss.\nIgnores evasion changes.',
    51: 'Prevents accuracy loss.\nIgnores evasion changes.',
    114: 'Draws in Water moves.\nAbsorbs them for Sp. Atk.',
}


def modern_ability_description_source(source, charmap):
    """Encode the pinned original source and the modern replacements."""
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Ability descriptions differ from the expected source')
    rows = ET.fromstring(source).findall('row')
    original = [game_text(row.find('language').text.replace('\\n', '\n'), charmap) for row in rows]
    updated = list(original)
    for ability, text in DESCRIPTIONS.items():
        updated[ability] = game_text(text, charmap)
    updated.extend([game_text(' -', charmap)] * 6)
    updated.append(game_text(ABILITY_BANKS[722][1], charmap))
    updated.extend([game_text(' -', charmap)] * 41)
    updated.append(game_text(COMPETITIVE_BANKS[722], charmap))
    return original, updated


def modern_ability_description_resources(archive, charmap, root=ROOT):
    banks, names = unpack_narc(archive)
    if len(banks) <= 722:
        raise ValueError('Ability-description message bank722 is absent')
    for bank, (digest, label) in ABILITY_BANKS.items():
        source = (Path(root) / f'files/msgdata/msg/msg_{bank:04}.gmm').read_text()
        if hashlib.sha256(source.encode()).hexdigest() != digest:
            raise ValueError(f'Ability bank{bank} differs from the expected source')
        rows = ET.fromstring(source).findall('row')
        original = [game_text(row.find('language').text.replace('\\n', '\n'), charmap) for row in rows]
        words, key = unpack_messages(banks[bank])
        if len(original) != 124 or words != original:
            raise ValueError(f'Ability bank{bank} does not match the unchanged source')
        if bank == 722:
            _, updated = modern_ability_description_source(source, charmap)
        else:
            updated = (original + [game_text(' -', charmap)] * 6 + [game_text(label, charmap)]
                       + [game_text(' -', charmap)] * 41 + [game_text(COMPETITIVE_BANKS[bank], charmap)])
        banks[bank] = pack_messages(updated, key)
    return pack_narc(banks, names)
