#!/usr/bin/env python3
"""Produce a separate ROM with source-generated modern presentation resources."""
import argparse
from pathlib import Path
import struct

from nitro_data import (lz10_decompress, lz10_literals, pack_messages, pack_narc,
                       replace_rom_files, rom_files, unpack_messages, unpack_narc)


def game_text(text, charmap):
    mapping = {'\n': 0xE000}
    for line in Path(charmap).read_text().splitlines():
        number, separator, character = line.partition('=')
        if separator and len(character) == 1:
            try:
                mapping.setdefault(character, int(number, 16))
            except ValueError:
                pass
    try:
        return [mapping[c] for c in text] + [0xFFFF]
    except KeyError as error:
        raise ValueError(f'Character absent from game font: {error.args[0]!r}') from error


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


def modern_type_rom(rom, charmap):
    files = rom_files(rom)
    paths = ('a/0/0/8', 'a/0/2/7', 'a/0/6/8')
    try:
        source = [rom[files[p][1]:files[p][2]] for p in paths]
    except KeyError as error:
        raise ValueError(f'SoulSilver resource is absent: {error.args[0]}') from error
    replacements = (*modern_type_resources(*source[:2], charmap), modern_pokedex_resources(source[2]))
    return replace_rom_files(rom, dict(zip(paths, replacements)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--charmap', type=Path, default=Path(__file__).resolve().parents[2] / 'charmap.txt')
    args = parser.parse_args()
    # Exclusive creation prevents overwriting the built source, a clean ROM or a save.
    output = modern_type_rom(args.source.read_bytes(), args.charmap)
    with args.output.open('xb') as stream:
        stream.write(output)
    print(f'{args.output}: modern type resources, {len(output)} bytes')


if __name__ == '__main__':
    main()
