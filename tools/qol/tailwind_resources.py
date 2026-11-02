"""Generate the modern four-turn Tailwind cast and its post-Snow description.

The original source and encoded resources are pinned before transforming them.
Public presence checks and every other resource member remain unchanged.
"""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

from battle_scripts import compile_battle_script
from game_text import game_text
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc
from snow_resources import SNOW_TEXT

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_SOURCE = 'files/battledata/script/subscript/subscript_0160_TailwindStart.s'
SCRIPT_SHA256 = 'c8457cc7a3ae9e1d6bc291e70c96e6a58fdcec979abfb1ea64c2a95ef98662b7'
MESSAGE_SOURCE = 'files/msgdata/msg/msg_0749.gmm'
MESSAGE_SHA256 = 'f0763a0583c68cae0c4ec967c202ccae643700147887389c194ffc509670c796'
BINARY_SHA256 = '2dd75559a6057016bc5fb3d577b9eaaeb5541d2ac15cc6774750668458f31f77'
MESSAGE_COUNT = 468
MESSAGE_KEY = 27800
ORIGINAL_TEXT = 'The user whips up a\nturbulent whirlwind\nthat ups the Speed\nof all party Pokémon\nfor three turns.'
TAILWIND_TEXT = 'The user whips up a\nturbulent whirlwind\nthat ups the Speed\nof all party Pokémon\nfor four turns.'


def modern_tailwind_source(source):
    if hashlib.sha256(source.encode()).hexdigest() != SCRIPT_SHA256:
        raise ValueError('Tailwind subscript differs from the expected source')
    before = '    UpdateVar OPCODE_FLAG_ON, BSCRIPT_VAR_SIDE_CONDITION_ATTACKER, SIDE_CONDITION_TAILWIND\n'
    after = before.replace('SIDE_CONDITION_TAILWIND\n', 'SIDE_CONDITION_TAILWIND | QOL_TAILWIND_FOURTH_TURN\n')
    return source.replace(before, after, 1)


def modern_tailwind_script(original, root=ROOT):
    source = (Path(root) / SCRIPT_SOURCE).read_text()
    transformed = modern_tailwind_source(source)
    if compile_battle_script(source, root) != original:
        raise ValueError('The unchanged Tailwind source does not match NARC member 160; check the SDK/compiler profile')
    return compile_battle_script(transformed, root)


def modern_tailwind_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) != 299:
        raise ValueError('Tailwind requires exactly 299 battle subscripts after Competitive/Simple')
    members[160] = modern_tailwind_script(members[160])
    return pack_narc(members, names)


def modern_tailwind_message_resources(archive, charmap, root=ROOT):
    banks, names = unpack_narc(archive)
    if len(banks) <= 749:
        raise ValueError('Tailwind message bank749 is absent')
    source = (Path(root) / MESSAGE_SOURCE).read_bytes()
    if hashlib.sha256(source).hexdigest() != MESSAGE_SHA256:
        raise ValueError('Tailwind bank749 differs from the expected source')
    rows = ET.fromstring(source).findall('row')
    original = [game_text((row.find('language').text or '').replace('\\n', '\n'), charmap) for row in rows]
    if (len(original) != MESSAGE_COUNT or original[366] != game_text(ORIGINAL_TEXT, charmap)
            or hashlib.sha256(pack_messages(original, MESSAGE_KEY)).hexdigest() != BINARY_SHA256):
        raise ValueError('Tailwind bank749 does not match the original encoded source')
    expected = list(original)
    for row, text in SNOW_TEXT[749].items():
        expected[row] = game_text(text, charmap)
    if banks[749] != pack_messages(expected, MESSAGE_KEY):
        raise ValueError('Tailwind requires the exact post-Snow bank749 before move extension')
    words, key = unpack_messages(banks[749])
    words[366] = game_text(TAILWIND_TEXT, charmap)
    banks[749] = pack_messages(words, key)
    return pack_narc(banks, names)
