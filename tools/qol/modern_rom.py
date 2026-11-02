#!/usr/bin/env python3
"""Produce a separate ROM with source-generated modern presentation resources."""
import argparse
from pathlib import Path
import struct

from battle_scripts import modern_paralysis_script, modern_drain_script, modern_weather_script, WEATHER_SCRIPTS
from snow_resources import modern_snow_effect_resources, modern_snow_message_resources
from soul_dew_resources import modern_soul_dew_message_resources
from wind_rider_scripts import modern_wind_rider_resources
from tailwind_resources import modern_tailwind_resources, modern_tailwind_message_resources
from next14_scripts import modern_move_stat_resources, modern_move_effect_resources
from game_text import game_text
from simple_scripts import SIMPLE_SCRIPTS, modern_simple_script, modern_simple_message_resources
from move_resources import extended_move_resources, read_entries
from absorption_scripts import modern_absorption_script
from sturdy_scripts import STURDY_SCRIPTS, modern_sturdy_script
from ability_descriptions import modern_ability_description_resources
from competitive_scripts import COMPETITIVE_SUBSCRIPT, modern_competitive_script
from cursed_body_scripts import ORIGINAL_SUBSCRIPT_COUNT, modern_cursed_body_script
from oblivious_intimidate_scripts import ABILITY_SCRIPTS, modern_oblivious_intimidate_script

from nitro_data import (lz10_decompress, lz10_literals, pack_messages, pack_narc,
                       replace_rom_files, rom_files, unpack_messages, unpack_narc)


def fairy_icon_pixels(width=32, colors=(5, 6, 13, 15)):
    # Original artwork, using existing palette 2. No shared palette is changed.
    # Four-pixel glyphs fit the original 32x16 type-icon sprite cell.
    glyphs = {
        'F': ('1111', '1000', '1110', '1000', '1000', '1000'),
        'A': ('0110', '1001', '1001', '1111', '1001', '1001'),
        'I': ('1110', '0100', '0100', '0100', '0100', '1110'),
        'R': ('1110', '1001', '1110', '1010', '1001', '1001'),
        'Y': ('1001', '1001', '0110', '0100', '0100', '0100'),
    }
    border, background, shadow_color, text_color = colors
    pixels = [[0] * width for _ in range(16)]
    for y in range(1, 15):
        for x in range(1, width - 1):
            pixels[y][x] = border if y in (1, 14) or x in (1, width - 2) else background
    for shadow in (True, False):
        for i, letter in enumerate('FAIRY'):
            for y, row in enumerate(glyphs[letter]):
                for x, on in enumerate(row):
                    if on == '1':
                        pixels[5 + y + shadow][(width - 24) // 2 + i * 5 + x + shadow] = shadow_color if shadow else text_color
    return pixels


def fairy_icon(character, width=32, colors=(5, 6, 13, 15)):
    if (width not in (32, 48) or len(character) != 48 + width * 8
            or character[:4] != b'RGCN' or character[16:20] != b'RAHC'
            or struct.unpack_from('<I', character, 40)[0] != width * 8
            or struct.unpack_from('<I', character, 28)[0] != 3):
        raise ValueError('Expected the original four-bit type icon geometry')
    pixels = fairy_icon_pixels(width, colors)
    tiled = bytearray()
    for tile_y in range(2):
        for tile_x in range(width // 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    left = pixels[tile_y * 8 + y][tile_x * 8 + x]
                    right = pixels[tile_y * 8 + y][tile_x * 8 + x + 1]
                    tiled.append(left | right << 4)
    return character[:48] + tiled


def modern_type_resources(icons, messages, charmap):
    characters, names = unpack_narc(icons)
    if len(characters) != 346:
        raise ValueError('Unexpected type resource archive')
    character = lz10_decompress(characters[236])
    characters[236] = lz10_literals(fairy_icon(character))
    banks, bank_names = unpack_narc(messages)
    if len(banks) <= 735:
        raise ValueError('Type-name message bank is absent')
    words, key = unpack_messages(banks[735])
    if len(words) != 18:
        raise ValueError('Unexpected type-name count')
    words[9] = game_text('FAIRY', charmap)
    banks[735] = pack_messages(words, key)
    return pack_narc(characters, names), pack_narc(banks, bank_names)


def modern_pokedex_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) != 123:
        raise ValueError('Unexpected Pokédex resource archive')
    original = lz10_decompress(members[36])
    # Pokédex type cells are 48x16 and use its existing pink palette 1.
    members.append(lz10_literals(fairy_icon(original, 48, (3, 2, 13, 14))))
    return pack_narc(members, names)


def modern_battle_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) <= 26:
        raise ValueError('Battle subscript archive is incomplete')
    # Fixed-width operand replacements preserve every relative script jump.
    # Opcodes/variables are defined by asm/macros/btlcmd.inc and battle_script.h.
    # These two Gen V+/VII+ changes follow hg-engine at the pinned revision.
    changes = ((26, (85, 32, 8), (85, 32, 16)),  # Burn: max HP /16, retain Heatproof.
               (18, (56, 3, 2), (56, 2, 2)))    # Sleep: 2..4 counter, 1..3 active turns.
    for member, before, after in changes:
        old, new = struct.pack('<3I', *before), struct.pack('<3I', *after)
        if members[member].count(old) != 1:
            raise ValueError(f'Battle subscript {member} differs from the expected source')
        members[member] = members[member].replace(old, new)
    return pack_narc(members, names)


def modern_paralysis_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) <= 31:
        raise ValueError('Battle paralysis subscript is absent')
    members[31] = modern_paralysis_script(members[31])
    return pack_narc(members, names)


def modern_drain_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) <= 24:
        raise ValueError('Battle drain subscript is absent')
    members[24] = modern_drain_script(members[24])
    return pack_narc(members, names)


def modern_weather_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) <= max(WEATHER_SCRIPTS):
        raise ValueError('Battle ability-weather subscript is absent')
    for member in WEATHER_SCRIPTS:
        members[member] = modern_weather_script(members[member], member)
    return pack_narc(members, names)


def modern_absorption_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) <= 182:
        raise ValueError('Battle ability absorption subscript is absent')
    members[182] = modern_absorption_script(members[182])
    return pack_narc(members, names)


def modern_sturdy_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) <= max(STURDY_SCRIPTS):
        raise ValueError('Battle Sturdy subscript is absent')
    for member in STURDY_SCRIPTS:
        members[member] = modern_sturdy_script(members[member], member)
    return pack_narc(members, names)


def modern_cursed_body_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) != ORIGINAL_SUBSCRIPT_COUNT:
        raise ValueError('Cursed Body requires exactly 297 original battle subscripts')
    members.append(modern_cursed_body_script(members[71]))
    return pack_narc(members, names)


def modern_competitive_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) != COMPETITIVE_SUBSCRIPT:
        raise ValueError('Competitive requires exactly 298 battle subscripts after Cursed Body')
    members.append(modern_competitive_script(members[12]))
    return pack_narc(members, names)


def modern_oblivious_intimidate_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) != COMPETITIVE_SUBSCRIPT + 1:
        raise ValueError('Oblivious/Intimidate requires exactly 299 battle subscripts after Competitive')
    for member in ABILITY_SCRIPTS:
        members[member] = modern_oblivious_intimidate_script(members[member], member)
    return pack_narc(members, names)


def modern_simple_resources(archive):
    members, names = unpack_narc(archive)
    if len(members) != COMPETITIVE_SUBSCRIPT + 1:
        raise ValueError('Simple/X-item requires exactly 299 battle subscripts after Competitive')
    for member in SIMPLE_SCRIPTS:
        members[member] = modern_simple_script(members[member], member)
    return pack_narc(members, names)


def make_modern_rom(rom, charmap, types=True, battle_rules=False, moves=False):
    files = rom_files(rom)
    replacements = {}
    def read(path):
        if path in replacements:
            return replacements[path]
        try:
            return rom[files[path][1]:files[path][2]]
        except KeyError as error:
            raise ValueError(f'SoulSilver resource is absent: {path}') from error
    if types:
        paths = ('a/0/0/8', 'a/0/2/7', 'a/0/6/8')
        source = [read(p) for p in paths]
        updated = (*modern_type_resources(*source[:2], charmap), modern_pokedex_resources(source[2]))
        replacements.update(zip(paths, updated))
    if battle_rules:
        archive = read('a/0/0/1')
        for transform in (modern_battle_resources, modern_paralysis_resources,
                          modern_weather_resources, modern_absorption_resources,
                          modern_sturdy_resources, modern_cursed_body_resources, modern_competitive_resources,
                          modern_oblivious_intimidate_resources, modern_simple_resources, modern_tailwind_resources):
            archive = transform(archive)
        replacements['a/0/0/1'] = archive
        replacements['a/0/3/0'] = modern_snow_effect_resources(read('a/0/3/0'))
        replacements['a/0/2/7'] = modern_snow_message_resources(
            modern_simple_message_resources(
                modern_ability_description_resources(read('a/0/2/7'), charmap), charmap), charmap)
        replacements['a/0/2/7'] = modern_soul_dew_message_resources(read('a/0/2/7'), charmap)
        replacements['a/0/2/7'] = modern_tailwind_message_resources(read('a/0/2/7'), charmap)
    if moves:
        paths = ('a/0/1/1', 'a/0/0/0', 'a/0/2/7')
        entries = read_entries(Path(__file__).resolve().parents[2] / 'include/data/qol_move_entries.inc')
        updated = extended_move_resources(*(read(p) for p in paths), charmap, entries)
        replacements.update(zip(paths, updated))
        replacements['a/0/0/1'] = modern_move_stat_resources(
            modern_drain_resources(read('a/0/0/1')), battle_rules)
        replacements['a/0/3/0'] = modern_move_effect_resources(read('a/0/3/0'))
        if not battle_rules:
            # Cotton's +3 event needs the same nine encoded message templates.
            # Combined mode already produced them before Snow; do not duplicate.
            replacements['a/0/2/7'] = modern_simple_message_resources(read('a/0/2/7'), charmap)
    if battle_rules:
        # All original exact-299 owners and optional 299..303 moves run first.
        replacements['a/0/0/1'] = modern_wind_rider_resources(read('a/0/0/1'), moves)
    return replace_rom_files(rom, replacements)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--charmap', type=Path, default=Path(__file__).resolve().parents[2] / 'charmap.txt')
    parser.add_argument('--no-types', action='store_true')
    parser.add_argument('--battle-rules', action='store_true')
    parser.add_argument('--moves', action='store_true')
    args = parser.parse_args()
    # Exclusive creation prevents overwriting the built source, a clean ROM or a save.
    output = make_modern_rom(args.source.read_bytes(), args.charmap, not args.no_types, args.battle_rules, args.moves)
    with args.output.open('xb') as stream:
        stream.write(output)
    print(f'{args.output}: selected modern resources, {len(output)} bytes')


if __name__ == '__main__':
    main()
