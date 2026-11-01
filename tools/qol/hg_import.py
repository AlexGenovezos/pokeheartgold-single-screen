#!/usr/bin/env python3
"""Export a pinned Gen IX data profile for review, without modifying the game."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ENGINE_REVISION = '61b510cfb6cf7d77c3b083150fad3499f82fd326'
CHAMPIONS_FIELDS = ('POWER', 'TYPE', 'ACC', 'PP', 'EFFECT_CHANCE')
ABILITY_ALIASES = {256: 240, 274: 241, 292: 242}
MOVE_FIELDS = ('effect', 'category', 'power', 'type', 'accuracy', 'pp',
               'effectChance', 'range', 'priority', 'source_flags')


def gen9_config(text):
    if '#ifndef CONFIG_H' not in text:
        raise ValueError('Upstream configuration guard changed')
    for field in CHAMPIONS_FIELDS:
        pattern = rf'(^#define CHAMPIONS_{field}_CHANGES\s+)\d+\b'
        text, count = re.subn(pattern, r'\g<1>0', text, flags=re.M)
        if count != 1:
            raise ValueError(f'Upstream Champions switch changed: {field}')
    return '#undef DEBUG_BATTLE_SCENARIOS\n' + text


def ability_mapping(abilities):
    result = {}
    for ability in sorted(abilities):
        if ability in ABILITY_ALIASES:
            result[ability] = ABILITY_ALIASES[ability]
        elif 0 <= ability <= 255:
            result[ability] = ability
        else:
            raise ValueError(f'Ability needs an explicit byte mapping: {ability}')
    if len(set(result.values())) != len(result):
        raise ValueError('Internal ability IDs collide with the selected roster')
    return result


def translate_move_flags(flags, legacy_flags=None):
    # hg-engine bit0x20 means unavailable/unimplemented. Native uses it for
    # item-induced flinching, so keep the existing move's bit independently.
    return (flags & ~0x20) | (0 if legacy_flags is None else legacy_flags & 0x20)


def pack_level_entries(entries):
    output, previous = [], -1
    for level, move in entries:
        if not 0 <= level <= 100 or level < previous or not 0 <= move <= 0xFFFF:
            raise ValueError('Invalid modern level-up entry')
        output.append(level << 16 | move)
        previous = level
    return output + [0xFFFFFFFF]


def _defines(file, prefix):
    return {key: int(value) for key, value in re.findall(
        rf'^#define\s+({prefix}\w+)\s+(\d+)\s*$', file.read_text(), re.M)}


DUMP_SOURCE = r'''
#include <stdio.h>
#include "data/Moves.c"
#include "data/Species.c"
#if GEN_LATEST != 9
#error Expected the ordinary Generation IX profile.
#endif
static void hex_string(const char *s) {
    if(s) while(*s) printf("%02x", (unsigned char)*s++);
}
int main(void) {
    for(int i=0;i<NUM_OF_MOVES;i++) {
        const MoveSourceEntry *m=&sMoveSource[i];
        printf("M\t%d\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%d\t%u\t",i,
            m->data.effect,m->data.split,m->data.power,m->data.type,m->data.accuracy,
            m->data.pp,m->data.effectChance,m->battle.target,m->battle.priority,m->battle.flags);
        hex_string(m->names.name);putchar('\t');hex_string(m->names.capsName);
        putchar('\t');hex_string(m->description);putchar('\n');
    }
    for(int i=1;i<=493;i++) {
        const SpeciesData *s=&sSpeciesData[i].speciesData;
        printf("S\t%d\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\n",i,
            s->baseStats.hp,s->baseStats.attack,s->baseStats.defense,
            s->baseStats.spAttack,s->baseStats.spDefense,s->baseStats.speed,
            s->types[0],s->types[1],s->abilities[0],s->abilities[1]);
    }
    return 0;
}
'''


def export_profile(engine, compiler='cc'):
    engine = Path(engine).resolve()
    revision = subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != ENGINE_REVISION:
        raise ValueError(f'Expected hg-engine revision {ENGINE_REVISION}; found {revision}')
    subprocess.run(['git', '-C', str(engine), 'diff', '--quiet', 'HEAD', '--', 'include', 'data', 'scripts'], check=True)
    with tempfile.TemporaryDirectory(prefix='ssr-gen9-') as temp:
        temp = Path(temp)
        config = temp / 'config-gen9.h'
        config.write_text(gen9_config((engine / 'include/config.h').read_text()))
        source = temp / 'dump.c'
        source.write_text(DUMP_SOURCE)
        executable = temp / 'dump'
        subprocess.run([compiler, '-std=c11', '-I', str(engine), '-include', str(config),
                        str(source), '-o', str(executable)], check=True)
        raw = subprocess.check_output([str(executable)], text=True)
    moves, species = [], []
    for row in raw.splitlines():
        values = row.split('\t')
        if values[0] == 'M':
            move_id = int(values[1])
            move = dict(zip(MOVE_FIELDS, map(int, values[2:12])))
            move.update(engine_id=move_id, official_id=move_id if move_id <= 467 else move_id - 3)
            for key, value in zip(('name', 'caps_name', 'description'), values[12:]):
                move[key] = bytes.fromhex(value).decode('utf-8')
            move['upstream_unimplemented'] = bool(move['source_flags'] & 0x20)
            moves.append(move)
        elif values[0] == 'S':
            numbers = list(map(int, values[1:]))
            species.append(dict(species=numbers[0], base_stats=numbers[1:7],
                                types=numbers[7:9], standard_abilities=numbers[9:11]))
    if len(moves) != 923 or [s['species'] for s in species] != list(range(1, 494)):
        raise ValueError('Pinned source export shape changed')
    # Keep original placeholder records explicit; they have no official move ID.
    for move in moves[468:471]:
        move['official_id'] = None
    ability_ids = _defines(engine / 'include/constants/ability.h', 'ABILITY_')
    hidden = dict(re.findall(r'\[(SPECIES_\w+)\s*\]\s*=\s*(ABILITY_\w+)',
                             (engine / 'data/HiddenAbilityTable.c').read_text()))
    species_ids = _defines(engine / 'include/constants/species.h', 'SPECIES_')
    by_id = {value: key for key, value in species_ids.items() if 1 <= value <= 493}
    for entry in species:
        entry['constant'] = by_id[entry['species']]
        entry['hidden_ability'] = ability_ids[hidden[entry['constant']]]
    all_abilities = {a for s in species for a in (*s['standard_abilities'], s['hidden_ability'])}
    internal = ability_mapping(all_abilities)
    spec = importlib.util.spec_from_file_location('hg_learnsets', engine / 'scripts/build_learnsets.py')
    merge_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(merge_module)
    excluded = {'17_lgpe.json', '20_la.json', '22_za.json', '99_go.json', 'custom.json'}
    sources = [(str(p), json.loads(p.read_text())) for p in sorted((engine / 'data/learnsets/base').glob('*.json'))
               if p.name not in excluded]
    merged = merge_module.merge_learnsets(sources, 'sv', True, True, True, True)
    learnsets = {entry['constant']: merged[entry['constant']] for entry in species}
    move_ids = _defines(engine / 'include/constants/moves.h', 'MOVE_')
    required = set()
    for entry in learnsets.values():
        levels = [(item['Level'], move_ids[item['Move']]) for item in entry.get('LevelMoves', [])]
        pack_level_entries(levels)
        for field in ('LevelMoves', 'EggMoves', 'MachineMoves', 'TutorMoves'):
            required.update(move_ids[m['Move'] if isinstance(m, dict) else m] for m in entry.get(field, []))
    new_ids = sorted(i for i in required if i > 467)
    return {
        'engine_revision': revision, 'target_generation': 9,
        'champions_changes': False, 'roster': 'Original species 1..493; base forms',
        'move_id_policy': 'Original 0..467 unchanged; preserve hg-engine 468..470 placeholders and Gen V+ engine IDs',
        'ability_internal_ids': internal, 'moves': moves, 'species': species, 'learnsets': learnsets,
        'required_new_engine_move_ids': new_ids,
        'upstream_unimplemented_required_move_ids': [i for i in new_ids if moves[i]['upstream_unimplemented']],
        'notes': [
            'Data only; does not establish move/ability implementation completeness.',
            'Alternate forms require a separate native form mapping before import.',
            'Do not copy source_flags bit0x20 into native item-flinch eligibility.',
            'Descriptions must be checked against actual implemented behavior.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--compiler', default='cc')
    args = parser.parse_args()
    profile = export_profile(args.engine, args.compiler)
    with args.output.open('x') as output:
        json.dump(profile, output, indent=2)
        output.write('\n')
    print(f'{args.output}: {len(profile["required_new_engine_move_ids"])} new roster moves; '
          f'{len(profile["upstream_unimplemented_required_move_ids"])} explicitly unfinished upstream')


if __name__ == '__main__':
    main()
