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
    476: dict(name='Psyshock', card='Psyshock', description='A psychic attack strikes the\ntarget’s Defense instead\nof its Sp. Def.'),
    543: dict(name='Psystrike', card='Psystrike', description='A psychic wave strikes the\ntarget’s Defense instead\nof its Sp. Def.'),
    495: dict(name='Foul Play', card='Foul Play', description='The user turns the target’s\nAttack stat against it.'),
    779: dict(name='Body Press', card='Body Press', description='The user attacks using its\nDefense stat in place\nof its Attack stat.'),
    536: dict(name='Sacred Sword', card='Sacred Sword', description='The user slashes, ignoring\nthe target’s Defense and\nevasion stat changes.'),
    666: dict(name='Darkest Lariat', card='Dark Lariat', description='The user swings its arms,\nignoring the target’s Defense\nand evasion stat changes.'),

    471: dict(name='Hone Claws', card='Hone Claws', description='The user sharpens its claws,\nraising its Attack\nand accuracy.'),
    486: dict(name='Quiver Dance', card='Quiver Dance', description='A graceful dance raises the\nuser’s Sp. Atk, Sp. Def,\nand Speed.'),
    492: dict(name='Coil', card='Coil', description='The user coils up, raising\nits Attack, Defense,\nand accuracy.'),
    529: dict(name='Work Up', card='Work Up', description='The user gets worked up,\nraising its Attack\nand Sp. Atk.'),
    507: dict(name='Shell Smash', card='Shell Smash', description='The user lowers its Defense\nand Sp. Def, then sharply raises\nits Attack, Sp. Atk, and Speed.'),
    541: dict(name='Cotton Guard', card='Cotton Guard', description='The user wraps itself in cotton,\ndrastically raising\nits Defense.'),
    494: dict(name='Acid Spray', card='Acid Spray', description='A corrosive liquid attacks,\nharshly lowering the\ntarget’s Sp. Def.'),
    491: dict(name='Flame Charge', card='Flame Charge', description='The user attacks with flames\nand raises its Speed.'),
    888: dict(name='Trailblaze', card='Trailblaze', description='The user attacks with energy\nfrom the ground and\nraises its Speed.'),
    477: dict(name='Venoshock', card='Venoshock', description='This attack’s power doubles\nif the target is poisoned.'),
    509: dict(name='Hex', card='Hex', description='This attack’s power doubles\nif the target has a\nmajor status condition.'),
    503: dict(name='Stored Power', card='Stored Power', description='The user attacks with stored\npower. Its stat boosts\nincrease this move’s power.'),
    684: dict(name='Power Trip', card='Power Trip', description='The user boasts of its strength.\nIts stat boosts increase\nthis move’s power.'),
    515: dict(name='Acrobatics', card='Acrobatics', description='A nimble strike doubles in\npower if the user isn’t\nholding an item.'),
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
    485: dict(name='Sludge Wave', card='Sludge Wave', description=
              'A wave of sludge strikes\neverything around the user.\nIt may poison those hit.'),
    493: dict(name='Low Sweep', card='Low Sweep', description=
              'The user strikes the target’s\nlegs, lowering its Speed.'),
    506: dict(name='Scald', card='Scald', description=
              'The user attacks with boiling\nwater. It may burn the target\nand thaws frozen Pokémon.'),
    520: dict(name='Inferno', card='Inferno', description=
              'An intense fire engulfs the\ntarget, leaving it with a burn\nif the attack hits.'),
    524: dict(name='Volt Switch', card='Volt Switch', description=
              'After an electric attack, the\nuser switches places with a\nPokémon in the party.'),
    525: dict(name='Struggle Bug', card='Struggle Bug', description=
              'The user attacks all opposing\nPokémon, lowering their\nSp. Atk stats.'),
    530: dict(name='Electroweb', card='Electroweb', description=
              'An electric net strikes all\nopposing Pokémon, lowering\ntheir Speed stats.'),
    531: dict(name='Wild Charge', card='Wild Charge', description=
              'The user makes an electric\ntackle, taking recoil equal to\na quarter of the damage dealt.'),
    533: dict(name='Dual Chop', card='Dual Chop', description=
              'The user strikes the target\ntwice in a row.'),
    537: dict(name='Razor Shell', card='Razor Shell', description=
              'The user cuts with sharp\nshells. This may also lower\nthe target’s Defense stat.'),
    539: dict(name='Leaf Tornado', card='Leaf Tornado', description=
              'Sharp leaves circle the\ntarget. This may also lower\nthe target’s accuracy.'),
    558: dict(name='Snarl', card='Snarl', description=
              'A menacing bark strikes all\nopposing Pokémon, lowering\ntheir Sp. Atk stats.'),
    559: dict(name='Icicle Crash', card='Icicle Crash', description=
              'Icicles crash into the target.\nThis may also make the\ntarget flinch.'),
    592: dict(name='Play Nice', card='Play Nice', description=
              'The user befriends the target\nto lower its Attack. It bypasses\nProtect and Substitute.'),
    598: dict(name='Mystical Fire', card='Mystic Fire', description=
              'A special fire strikes the\ntarget, lowering its\nSp. Atk stat.'),
    611: dict(name='Baby-Doll Eyes', card='Baby Eyes', description=
              'The user’s endearing gaze\nlowers the target’s Attack.\nThis move has priority.'),
    612: dict(name='Nuzzle', card='Nuzzle', description=
              'The user nuzzles the target\nwith electrified cheeks,\nleaving it with paralysis.'),
    615: dict(name='Power-Up Punch', card='Power Punch', description=
              'A punch strikes the target\nand raises the user’s\nAttack stat.'),
    623: dict(name='Dragon Ascent', card='Drgn Ascent', description=
              'The user dives from the sky\nto attack. This also lowers\nits Defense and Sp. Def.'),
    682: dict(name='Lunge', card='Lunge', description=
              'The user lunges at the\ntarget, lowering its\nAttack stat.'),
    709: dict(name='Psychic Fangs', card='Psy Fangs', description=
              'A psychic bite attacks and\nbreaks the target’s\nReflect and Light Screen.'),
    713: dict(name='Liquidation', card='Liquidation', description=
              'The user slams into the target\nwith water. This may also\nlower the target’s Defense.'),
    787: dict(name='Breaking Swipe', card='Break Swipe', description=
              'A sweeping tail strikes all\nopposing Pokémon, lowering\ntheir Attack stats.'),
    809: dict(name='Skitter Smack', card='Skitter Hit', description=
              'The user skitters behind\nthe target to attack,\nlowering its Sp. Atk stat.'),
    815: dict(name='Flip Turn', card='Flip Turn', description=
              'After a water attack, the\nuser switches places with a\nPokémon in the party.'),
    817: dict(name='Dual Wingbeat', card='Dual Wingbeat', description=
              'The user strikes the target\nwith its wings twice in a row.'),
    818: dict(name='Scorching Sands', card='Scorch Sands', description=
              'Hot sand may burn the target.\nThis move also thaws\nfrozen Pokémon.'),
    831: dict(name='Psyshield Bash', card='Psy Bash', description=
              'A psychic bash strikes the\ntarget and raises the\nuser’s Defense stat.'),
    836: dict(name='Raging Fury', card='Raging Fury', description=
              'The user rampages with flames\nfor two to three turns, then\nbecomes confused.'),
    837: dict(name='Wave Crash', card='Wave Crash', description=
              'The user slams into the target\nwith water, taking recoil of\none third of the damage dealt.'),
    841: dict(name='Headlong Rush', card='Headlong', description=
              'The user attacks at full force.\nThis also lowers the user’s\nDefense and Sp. Def.'),
    876: dict(name='Raging Bull', card='Raging Bull', description=
              'A Normal-type tackle breaks\nthe target’s Reflect and\nLight Screen.'),
    887: dict(name='Pounce', card='Pounce', description=
              'The user pounces on the\ntarget, lowering its\nSpeed stat.'),
    889: dict(name='Chilling Water', card='Chill Water', description=
              'Cold water showers the\ntarget, lowering its\nAttack stat.'),
    891: dict(name='Twin Beam', card='Twin Beam', description=
              'The user fires two mystical\nbeams at the target,\nstriking twice in a row.'),

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
