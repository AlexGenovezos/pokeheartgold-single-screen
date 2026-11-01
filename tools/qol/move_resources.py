"""Extend move archives from the same literal metadata consumed by native C."""
from pathlib import Path
import re
import struct

from game_text import game_text
from nitro_data import pack_messages, pack_narc, unpack_messages, unpack_narc

CARD_MESSAGE_BANK = 829

FIELDS = ('id', 'effect', 'category', 'power', 'type', 'accuracy', 'pp',
          'chance', 'range', 'priority', 'flags', 'animation')
PRESENTATION = {
    577: dict(name='Disarming Voice', card='Disarm Voice', description=
              'The user lets out a charming cry\nthat never misses. It strikes\nall opposing Pokémon.'),
    580: dict(name='Draining Kiss', card='Draining Kiss', description=
              'The user steals HP with a kiss.\nIt restores three quarters of\nthe damage dealt as HP.'),
    586: dict(name='Play Rough', card='Play Rough', description=
              'The user plays roughly with the\ntarget. This may also lower\nthe target’s Attack stat.'),
    588: dict(name='Moonblast', card='Moonblast', description=
              'The user attacks with moonlight.\nThis may also lower the\ntarget’s Sp. Atk stat.'),
    608: dict(name='Dazzling Gleam', card='Dazzle Gleam', description=
              'The user emits a powerful flash\nof light that damages all\nopposing Pokémon.'),
    587: dict(name='Fairy Wind', card='Fairy Wind', description=
              'The user stirs up a fairy wind\nto strike the target.'),
    673: dict(name='Leafage', card='Leafage', description=
              'The user attacks by pelting\nthe target with leaves.'),
    670: dict(name='High Horsepower', card='High Horse', description=
              'The user fiercely attacks the\ntarget using its entire body.'),
    696: dict(name='Brutal Swing', card='Brutal Swing', description=
              'The user swings its body around\nviolently to damage everything\naround it.'),
    532: dict(name='Drill Run', card='Drill Run', description=
              'The user rotates its body like\na drill. This move has a high\ncritical-hit ratio.'),
    687: dict(name='Smart Strike', card='Smart Strike', description=
              'The user stabs the target with\na sharp horn. This attack\nnever misses.'),
    898: dict(name='Aqua Cutter', card='Aqua Cutter', description=
              'The user cuts with pressurized\nwater. This move has a high\ncritical-hit ratio.'),
    622: dict(name='Precipice Blades', card='Precip Blades', description=
              'The user manifests fearsome\nstone blades to strike all\nopposing Pokémon.'),
    621: dict(name='Origin Pulse', card='Origin Pulse', description=
              'The user fires deep blue beams\nof light at all opposing\nPokémon.'),
    575: dict(name='Petal Blizzard', card='Petal Storm', description=
              'The user stirs up a violent\nblizzard of petals to damage\neverything around it.'),
    589: dict(name='Boomburst', card='Boomburst', description=
              'The user attacks everything\naround it with a destructive\nexplosive sound.'),
    854: dict(name='Tera Blast', card='Tera Blast', description=
              'The user releases energy as a\nNormal-type special attack.\nTerastallization is unavailable.'),
}


def parse_entries(source):
    """Accept only literal rows: no C expressions or silently skipped content."""
    entries = []
    for line in source.splitlines():
        line = line.partition('//')[0].strip()
        if not line:
            continue
        match = re.fullmatch(r'QOL_EXTRA_MOVE\(([^()]*)\)', line)
        if not match:
            raise ValueError('Expected a literal QOL_EXTRA_MOVE row')
        values = [part.strip() for part in match[1].split(',')]
        if len(values) != len(FIELDS) or any(not re.fullmatch(r'-?\d+', v) for v in values):
            raise ValueError('Move metadata must contain twelve decimal integers')
        row = dict(zip(FIELDS, map(int, values)))
        bounds = {'id': (471, 65534), 'effect': (0, 65535), 'category': (0, 2),
                  'power': (0, 255), 'type': (0, 17), 'accuracy': (0, 100),
                  'pp': (1, 255), 'chance': (0, 100), 'range': (0, 65535),
                  'priority': (-128, 127), 'flags': (0, 255), 'animation': (0, 467)}
        if any(not low <= row[key] <= high for key, (low, high) in bounds.items()):
            raise ValueError('Move metadata is outside the native field range')
        if any(previous['id'] == row['id'] for previous in entries):
            raise ValueError('Duplicate extended move ID')
        entries.append(row)
    if not entries:
        raise ValueError('No extended moves supplied')
    return entries


def read_entries(path):
    return parse_entries(Path(path).read_text())


def extended_move_resources(movedata, scripts, messages, charmap, entries):
    data, data_names = unpack_narc(movedata)
    moves, script_names = unpack_narc(scripts)
    banks, bank_names = unpack_narc(messages)
    if len(data) != 471 or any(len(member) != 16 for member in data):
        raise ValueError('Unexpected original movedata archive')
    if len(moves) != 501 or len(banks) != CARD_MESSAGE_BANK:
        raise ValueError('Unexpected original move script/message archive')
    ids = {row['id'] for row in entries}
    if ids != PRESENTATION.keys():
        raise ValueError('Move metadata and presentation do not match')
    count = max(ids) + 1
    # Empty gaps are never selectable: all C consumers validate supported IDs.
    data.extend([bytes(16)] * (count - len(data)))
    moves.extend([moves[0]] * (count - len(moves)))
    for row in entries:
        if moves[row['animation']] != struct.pack('<I', 36):
            raise ValueError('Expected a plain GoToEffectScript animation alias')
        data[row['id']] = struct.pack('<H6BHbB2BH', *(row[key] for key in FIELDS[1:11]), 0, 0, 0)
        moves[row['id']] = moves[row['animation']]
    for bank, field in ((749, 'description'), (750, 'name'), (751, 'name')):
        words, key = unpack_messages(banks[bank])
        if len(words) != 468:
            raise ValueError(f'Unexpected move message count in bank {bank}')
        words.extend([[0xFFFF] for _ in range(count - len(words))])
        for move_id, presentation in PRESENTATION.items():
            value = presentation[field]
            if bank == 751:
                value = value.upper()
            words[move_id] = game_text(value, charmap)
        banks[bank] = pack_messages(words, key)
    cards = [[0xFFFF] for _ in range(count)]
    for move_id, presentation in PRESENTATION.items():
        cards[move_id] = game_text(presentation['card'], charmap)
    banks.append(pack_messages(cards, 0))
    return pack_narc(data, data_names), pack_narc(moves, script_names), pack_narc(banks, bank_names)
