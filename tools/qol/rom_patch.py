#!/usr/bin/env python3
"""Create/apply standard BPS patches without distributing game ROMs.

Creation uses SourceRead and TargetRead; application accepts all four BPS
actions, including overlapping TargetCopy. Existing files are never overwritten.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import sys
import zlib

MAX_TARGET_SIZE = 1024 * 1024 * 1024


def _number(value):
    encoded = bytearray()
    while True:
        digit = value & 0x7f
        value >>= 7
        if not value:
            encoded.append(digit | 0x80)
            return bytes(encoded)
        encoded.append(digit)
        value -= 1


def _read_number(data, offset, end):
    value, shift = 0, 1
    for _ in range(10):
        if offset >= end:
            raise ValueError("truncated BPS integer")
        digit = data[offset]
        offset += 1
        value += (digit & 0x7f) * shift
        if digit & 0x80:
            return value, offset
        shift <<= 7
        value += shift
    raise ValueError("BPS integer exceeds supported size")


def create_patch(source, target):
    """Generate a BPS patch; unchanged bytes are read from the source."""
    commands = []
    run_start, run_equal, offset = 0, None, 0

    def emit(start, end, equal):
        if end > start:
            commands.append(_number(((end - start - 1) << 2) | (0 if equal else 1)))
            if not equal:
                commands.append(target[start:end])

    def advance(equal, next_offset):
        nonlocal run_start, run_equal, offset
        if equal != run_equal:
            emit(run_start, offset, run_equal)
            run_start, run_equal = offset, equal
        offset = next_offset

    while offset < len(target):
        # Most of a ROM is unchanged: skip matching blocks without a byte loop.
        end = min(offset + 65536, len(target))
        if source[offset:end] == target[offset:end]:
            advance(True, end)
        else:
            for index in range(offset, end):
                advance(index < len(source) and source[index] == target[index], index + 1)
    emit(run_start, offset, run_equal)
    payload = (b"BPS1" + _number(len(source)) + _number(len(target)) +
               _number(0) + b"".join(commands))
    payload += struct.pack("<II", zlib.crc32(source), zlib.crc32(target))
    return payload + struct.pack("<I", zlib.crc32(payload))


def apply_patch(source, patch):
    """Apply BPS with bounds, size and all three CRCs checked."""
    if len(patch) < 19 or patch[:4] != b"BPS1":
        raise ValueError("invalid or truncated BPS patch")
    source_crc, target_crc, patch_crc = struct.unpack_from("<III", patch, len(patch) - 12)
    if zlib.crc32(patch[:-4]) != patch_crc:
        raise ValueError("patch CRC mismatch")
    end = len(patch) - 12
    source_size, offset = _read_number(patch, 4, end)
    target_size, offset = _read_number(patch, offset, end)
    metadata_size, offset = _read_number(patch, offset, end)
    if source_size != len(source) or zlib.crc32(source) != source_crc:
        raise ValueError("source ROM size or CRC mismatch")
    if target_size > MAX_TARGET_SIZE:
        raise ValueError("target exceeds 1 GiB limit")
    offset += metadata_size
    if offset > end:
        raise ValueError("truncated BPS metadata")
    target = bytearray()
    source_relative, target_relative = 0, 0
    while len(target) < target_size:
        command, offset = _read_number(patch, offset, end)
        action, length = command & 3, (command >> 2) + 1
        if length > target_size - len(target):
            raise ValueError("BPS action exceeds target size")
        if action == 0:
            start = len(target)
            if start + length > len(source):
                raise ValueError("source read exceeds source size")
            target.extend(source[start:start + length])
        elif action == 1:
            if offset + length > end:
                raise ValueError("truncated BPS literal")
            target.extend(patch[offset:offset + length])
            offset += length
        else:
            delta, offset = _read_number(patch, offset, end)
            delta = -(delta >> 1) if delta & 1 else delta >> 1
            if action == 2:
                source_relative += delta
                if source_relative < 0 or source_relative + length > len(source):
                    raise ValueError("source copy exceeds source size")
                target.extend(source[source_relative:source_relative + length])
                source_relative += length
            else:
                target_relative += delta
                if target_relative < 0 or target_relative >= len(target):
                    raise ValueError("target copy reads unavailable output")
                # Append incrementally because BPS permits overlapping target copies.
                for _ in range(length):
                    target.append(target[target_relative])
                    target_relative += 1
    if offset != end:
        raise ValueError("trailing BPS commands after target")
    if zlib.crc32(target) != target_crc:
        raise ValueError("target CRC mismatch")
    return bytes(target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create a patch against an explicitly identified clean ROM")
    create.add_argument("source", type=Path)
    create.add_argument("target", type=Path)
    create.add_argument("output", type=Path)
    create.add_argument("--source-sha1", required=True, help="expected clean ROM SHA-1")
    apply = commands.add_parser("apply", help="apply a patch with BPS source/target CRC verification")
    apply.add_argument("source", type=Path)
    apply.add_argument("patch", type=Path)
    apply.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        # Reject an existing file, symlink or input alias before reading game data.
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("output already exists; choose a new filename")
        source = args.source.read_bytes()
        if args.command == "create":
            if hashlib.sha1(source).hexdigest() != args.source_sha1.lower():
                raise ValueError("source SHA-1 mismatch")
            target = args.target.read_bytes()
            result = create_patch(source, target)
            if apply_patch(source, result) != target:
                raise ValueError("generated patch failed round-trip verification")
        else:
            result = apply_patch(source, args.patch.read_bytes())
        # Exclusive creation also prevents overwrite if a file appears during work.
        with args.output.open("xb") as out:
            out.write(result)
        print(f"{args.output}: {len(result)} bytes; SHA-256 {hashlib.sha256(result).hexdigest()}")
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

