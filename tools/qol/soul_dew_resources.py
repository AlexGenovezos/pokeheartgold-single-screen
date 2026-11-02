"""Correct modern Soul Dew's item text after Snow owns the original bank221.

Only the accumulated, exact post-Snow bank is accepted; source message files
remain original. No script compilation or archive work happens during import.
"""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

from game_text import game_text
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc
from snow_resources import SNOW_TEXT

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'files/msgdata/msg/msg_0221.gmm'
SOURCE_SHA256 = '72a2c890304ebcab65f70d487423e402572301ec208936888061db5ff137748d'
BINARY_SHA256 = 'd5504272b9fb1fa8bd735266ea630a2a6e42e038415d4716d0eabc2019db5a01'
MESSAGE_COUNT = 537
MESSAGE_KEY = 24316
ORIGINAL_TEXT = 'A wondrous orb to be held by LATIOS\nor LATIAS. It raises both the\nSp. Atk and Sp. Def stats.'
SOUL_DEW_TEXT = 'LATIOS or LATIAS: boosts\nPsychic- and Dragon-type\nmoves by 20%.'


def modern_soul_dew_message_resources(archive, charmap, root=ROOT):
    banks, names = unpack_narc(archive)
    if len(banks) <= 221:
        raise ValueError('Soul Dew message bank221 is absent')
    source = (Path(root) / SOURCE).read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('Soul Dew bank221 differs from the expected source')
    rows = ET.fromstring(source).findall('row')
    original = [game_text((row.find('language').text or '').replace('\\n', '\n'), charmap) for row in rows]
    if (len(original) != MESSAGE_COUNT or original[225] != game_text(ORIGINAL_TEXT, charmap)
        or hashlib.sha256(pack_messages(original, MESSAGE_KEY)).hexdigest() != BINARY_SHA256):
        raise ValueError('Soul Dew bank221 does not match the original encoded source')
    expected = list(original)
    for row, text in SNOW_TEXT[221].items():
        expected[row] = game_text(text, charmap)
    if banks[221] != pack_messages(expected, MESSAGE_KEY):
        raise ValueError('Soul Dew requires the exact post-Snow bank221')
    words, key = unpack_messages(banks[221])
    words[225] = game_text(SOUL_DEW_TEXT, charmap)
    banks[221] = pack_messages(words, key)
    return pack_narc(banks, names)
