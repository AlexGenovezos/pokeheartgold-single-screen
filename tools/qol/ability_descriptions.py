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
SHARPNESS_BANKS = {
    720: 'Sharpness',
    721: 'SHARPNESS',
    722: 'Powers up slicing moves\nby 50%.',
}
SPARSE_ABILITIES = {130: {bank: entry[1] for bank, entry in ABILITY_BANKS.items()},
                    172: COMPETITIVE_BANKS, 242: SHARPNESS_BANKS}
ABILITY_KEYS = {720: 7280, 721: 50258, 722: 26692}


DESCRIPTIONS = {
    81: 'Raises evasion when\nit is snowing.',
    115: 'Restores HP when\nit is snowing.',
    117: 'Summons snow for\nfive turns in battle.',
    12: 'Blocks infatuation,\nTaunt and Intimidate.',
    20: "Prevents confusion and\nIntimidate’s stat loss.",
    39: "Prevents flinching and\nIntimidate’s stat loss.",
    113: "Hits Ghosts. Blocks\nIntimidate’s stat loss.",
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
    updated.extend([game_text(' -', charmap)] * (243 - len(updated)))
    for ability, banks in SPARSE_ABILITIES.items():
        updated[ability] = game_text(banks[722], charmap)
    return original, updated


def modern_ability_description_resources(archive, charmap, root=ROOT):
    banks, names = unpack_narc(archive)
    if len(banks) <= 722:
        raise ValueError('Ability-description message bank722 is absent')
    for bank, (digest, label) in ABILITY_BANKS.items():
        source_bytes = (Path(root) / f'files/msgdata/msg/msg_{bank:04}.gmm').read_bytes()
        if hashlib.sha256(source_bytes).hexdigest() != digest:
            raise ValueError(f'Ability bank{bank} differs from the expected source')
        source = source_bytes.decode()
        rows = ET.fromstring(source).findall('row')
        original = [game_text(row.find('language').text.replace('\\n', '\n'), charmap) for row in rows]
        words, key = unpack_messages(banks[bank])
        if len(original) != 124 or words != original or key != ABILITY_KEYS[bank]:
            raise ValueError(f'Ability bank{bank} does not match the unchanged source')
        if bank == 722:
            _, updated = modern_ability_description_source(source, charmap)
        else:
            updated = original + [game_text(' -', charmap)] * (243 - len(original))
            for ability, labels in SPARSE_ABILITIES.items():
                updated[ability] = game_text(labels[bank], charmap)
        banks[bank] = pack_messages(updated, key)
    return pack_narc(banks, names)
