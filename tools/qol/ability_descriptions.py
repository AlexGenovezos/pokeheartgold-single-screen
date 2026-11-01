"""Generate updated original-ability descriptions in the summary's bank722."""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from game_text import game_text
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('files/msgdata/msg/msg_0722.gmm')
SOURCE_SHA256 = 'd364bd67c8c67554ea54654e0ceb372bf95d353efb4c2706664044e9d6306682'
DESCRIPTIONS = {
    5: 'At full HP, survives a hit.\nBlocks 1-hit KO moves.',
    31: 'Draws in Electric moves.\nAbsorbs them for Sp. Atk.',
    114: 'Draws in Water moves.\nAbsorbs them for Sp. Atk.',
}


def modern_ability_description_source(source, charmap):
    """Encode the pinned original source and the three modern replacements."""
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Ability descriptions differ from the expected source')
    rows = ET.fromstring(source).findall('row')
    original = [game_text(row.find('language').text.replace('\\n', '\n'), charmap) for row in rows]
    updated = list(original)
    for ability, text in DESCRIPTIONS.items():
        updated[ability] = game_text(text, charmap)
    return original, updated


def modern_ability_description_resources(archive, charmap, root=ROOT):
    banks, names = unpack_narc(archive)
    if len(banks) <= 722:
        raise ValueError('Ability-description message bank722 is absent')
    source = (Path(root) / SOURCE).read_text()
    original, updated = modern_ability_description_source(source, charmap)
    words, key = unpack_messages(banks[722])
    if words != original:
        raise ValueError('Ability-description bank722 does not match the unchanged source')
    banks[722] = pack_messages(updated, key)
    return pack_narc(banks, names)
