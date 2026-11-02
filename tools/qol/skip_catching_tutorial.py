#!/usr/bin/env python3
"""Skip only the known USA SoulSilver Route 29 lesson; retain its reward/tail.

The replacements fit two existing script regions. Patch the member in place so
no executable, overlay, file offset, archive table or ROM header is rewritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from nitro_data import rom_files, unpack_narc

SCRIPT_PATH = 'a/0/1/2'
SCRIPT_INDEX = 225
ORIGINAL_SHA256 = '3ed238656dbe0c565a3c5ad8cafd29e1fea97d46ea70543c1aa4e4656f37aee6'
PATCHED_SHA256 = 'e7ddaed8dc238bd3f03096ffda9ae450e873191263409c440b263b4dad288e6d'
BRANCHES = ((0x1b6, 0x513), (0x525, 0x53b))


def patch_script(data):
    data = bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    if digest == PATCHED_SHA256:
        return data
    if len(data) != 2580 or digest != ORIGINAL_SHA256:
        raise ValueError('Unknown Route 29 script; refusing an unverified tutorial patch')
    output = bytearray(data)
    # The standard gift returns with its final textbox open. Close it before
    # skipping farewell/movement; ReleaseAll only resumes map objects.
    struct.pack_into('<H', output, 0x523, 53)
    for offset, target in BRANCHES:
        output[offset:offset + 6] = struct.pack('<Hi', 22, target - (offset + 6))
    if hashlib.sha256(output).hexdigest() != PATCHED_SHA256:
        raise ValueError('Tutorial patch did not produce the reviewed script')
    return bytes(output)


def _region(data, start, size):
    if start < 0 or size < 0 or start + size > len(data):
        raise ValueError('ROM region exceeds its container')
    return start, start + size


def _protected_regions(data):
    regions = [(0, 0x200)]
    for pointer, length in ((0x20, 0x2c), (0x30, 0x3c), (0x40, 0x44),
                            (0x48, 0x4c), (0x50, 0x54), (0x58, 0x5c)):
        start = struct.unpack_from('<I', data, pointer)[0]
        size = struct.unpack_from('<I', data, length)[0]
        if size:
            regions.append(_region(data, start, size))
    fat, fat_size = struct.unpack_from('<II', data, 0x48)
    for pointer in (0x50, 0x58):
        start, size = struct.unpack_from('<II', data, pointer)
        if size % 32:
            raise ValueError('Invalid overlay table size')
        for entry in range(start, start + size, 32):
            file_id = struct.unpack_from('<I', data, entry + 24)[0]
            if file_id >= fat_size // 8:
                raise ValueError('Overlay file ID exceeds the FAT')
            first, last = struct.unpack_from('<II', data, fat + file_id * 8)
            regions.append(_region(data, first, last - first))
    return regions


def patch_rom(data):
    files = rom_files(data)
    if data[12:16] != b'IPGE':
        raise ValueError('Expected a USA SoulSilver ROM')
    if SCRIPT_PATH not in files:
        raise ValueError('ROM has no field-script archive')
    script_file_id, start, end = files[SCRIPT_PATH]
    for first, last in _protected_regions(data):
        if start < last and first < end:
            raise ValueError('Field-script archive overlaps an executable or ROM table')
    fat, fat_size = struct.unpack_from('<II', data, 0x48)
    for file_id in range(fat_size // 8):
        if file_id == script_file_id:
            continue
        first, last = struct.unpack_from('<II', data, fat + file_id * 8)
        _region(data, first, last - first)
        if start < last and first < end:
            raise ValueError('Field-script archive aliases another ROM file')
    archive = data[start:end]
    members, _ = unpack_narc(archive)
    if len(members) != 965:
        raise ValueError('Unknown field-script archive shape')
    original = members[SCRIPT_INDEX]
    patched = patch_script(original)
    # unpack_narc has already validated all block sizes and member boundaries.
    blocks = {}
    pos = 16
    for _ in range(3):
        magic, size = struct.unpack_from('<4sI', archive, pos)
        blocks[magic] = pos
        pos += size
    first, last = struct.unpack_from('<II', archive, blocks[b'BTAF'] + 12 + SCRIPT_INDEX * 8)
    offset = start + blocks[b'GMIF'] + 8 + first
    if data[offset:offset + last - first] != original:
        raise ValueError('Route 29 member location does not match the archive')
    output = bytearray(data)
    output[offset:offset + len(patched)] = patched
    return bytes(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError('Output already exists; choose a new filename')
        source = args.input.read_bytes()
        output = patch_rom(source)
        with args.output.open('xb') as stream:
            stream.write(output)
        print(json.dumps(dict(output=str(args.output),
                              input_sha256=hashlib.sha256(source).hexdigest(),
                              output_sha256=hashlib.sha256(output).hexdigest(),
                              rom_size=len(output), script_index=SCRIPT_INDEX,
                              script_sha256=PATCHED_SHA256,
                              executable_and_layout_bytes_unchanged=True), indent=2))
    except (OSError, ValueError, struct.error) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
