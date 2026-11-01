"""Small, bounded Nitro data transforms; no game assets are embedded here."""
import struct


def _range(data, offset, size):
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError('Data range exceeds its container')
    return data[offset:offset + size]


def unpack_narc(data):
    if len(data) < 16 or data[:4] != b'NARC':
        raise ValueError('Expected a NARC archive')
    size, header, count = struct.unpack_from('<IHH', data, 8)
    if size != len(data) or header != 16 or count != 3:
        raise ValueError('Invalid NARC header')
    blocks = {}
    pos = header
    for _ in range(count):
        magic, length = struct.unpack('<4sI', _range(data, pos, 8))
        if length < 8 or magic in blocks:
            raise ValueError('Invalid NARC block')
        blocks[magic] = bytes(_range(data, pos, length))
        pos += length
    if pos != len(data) or set(blocks) != {b'BTAF', b'BTNF', b'GMIF'}:
        raise ValueError('Invalid NARC block list')
    table, payload = blocks[b'BTAF'], blocks[b'GMIF'][8:]
    count, reserved = struct.unpack('<HH', _range(table, 8, 4))
    if len(table) != 12 + count * 8:
        raise ValueError('Invalid NARC member table')
    members = []
    previous = 0
    for i in range(count):
        start, end = struct.unpack_from('<II', table, 12 + i * 8)
        if start < previous or end < start:
            raise ValueError('Invalid NARC member order')
        members.append(bytes(_range(payload, start, end - start)))
        previous = end
    return members, blocks[b'BTNF']


def pack_narc(members, names=None):
    if names is None:
        names = b'BTNF' + struct.pack('<III', 16, 4, 0x10000)
    if names[:4] != b'BTNF' or len(names) < 8 or struct.unpack_from('<I', names, 4)[0] != len(names):
        raise ValueError('Invalid NARC name table')
    if len(members) > 0xFFFF:
        raise ValueError('Too many NARC members')
    payload = bytearray()
    entries = bytearray()
    for member in members:
        start = len(payload)
        payload.extend(member)
        entries.extend(struct.pack('<II', start, len(payload)))
        payload.extend(b'\xFF' * (-len(payload) % 4))
    table = b'BTAF' + struct.pack('<IHH', 12 + len(entries), len(members), 0) + entries
    image = b'GMIF' + struct.pack('<I', 8 + len(payload)) + payload
    size = 16 + len(table) + len(names) + len(image)
    return struct.pack('<4sHHIHH', b'NARC', 0xFFFE, 0x100, size, 16, 3) + table + names + image


def unpack_messages(data):
    count, key = struct.unpack('<HH', _range(data, 0, 4))
    table_end = 4 + count * 8
    _range(data, 0, table_end)
    messages = []
    for i in range(count):
        cipher = (key * 765 * (i + 1)) & 0xFFFF
        cipher |= cipher << 16
        offset, length = struct.unpack_from('<II', data, 4 + i * 8)
        offset ^= cipher
        length ^= cipher
        if offset < table_end or offset & 1:
            raise ValueError('Invalid message offset')
        encoded = _range(data, offset, length * 2)
        words = struct.unpack('<' + 'H' * length, encoded)
        seed = ((i + 1) * 596947) & 0xFFFF
        messages.append([word ^ ((seed + n * 18749) & 0xFFFF) for n, word in enumerate(words)])
    return messages, key


def pack_messages(messages, key):
    if not 0 <= key <= 0xFFFF or len(messages) > 0xFFFF:
        raise ValueError('Invalid message header')
    payload = bytearray()
    table = bytearray()
    for i, words in enumerate(messages):
        offset = 4 + len(messages) * 8 + len(payload)
        cipher = (key * 765 * (i + 1)) & 0xFFFF
        cipher |= cipher << 16
        table.extend(struct.pack('<II', offset ^ cipher, len(words) ^ cipher))
        seed = ((i + 1) * 596947) & 0xFFFF
        for n, word in enumerate(words):
            payload.extend(struct.pack('<H', word ^ ((seed + n * 18749) & 0xFFFF)))
    return struct.pack('<HH', len(messages), key) + table + payload


def lz10_decompress(data):
    if len(data) < 4 or data[0] != 0x10:
        raise ValueError('Expected LZ10 data')
    size = int.from_bytes(data[1:4], 'little')
    output = bytearray()
    pos = 4
    while len(output) < size:
        flags = _range(data, pos, 1)[0]
        pos += 1
        for bit in range(7, -1, -1):
            if len(output) == size:
                break
            if flags & (1 << bit):
                first, second = _range(data, pos, 2)
                pos += 2
                length = (first >> 4) + 3
                distance = ((first & 15) << 8 | second) + 1
                if distance > len(output) or len(output) + length > size:
                    raise ValueError('Invalid LZ10 match')
                for _ in range(length):
                    output.append(output[-distance])
            else:
                output.extend(_range(data, pos, 1))
                pos += 1
    return bytes(output)


def lz10_literals(data):
    if len(data) >= 1 << 24:
        raise ValueError('LZ10 image too large')
    return b'\x10' + len(data).to_bytes(3, 'little') + b''.join(b'\0' + data[i:i+8] for i in range(0, len(data), 8))


def rom_files(data):
    fnt, fnt_size, fat, fat_size = struct.unpack('<4I', _range(data, 0x40, 16))
    names, allocations = _range(data, fnt, fnt_size), _range(data, fat, fat_size)
    if fat_size % 8:
        raise ValueError('Invalid ROM file table')
    for offset in range(0, fat_size, 8):
        start, end = struct.unpack_from('<II', allocations, offset)
        _range(data, start, end - start)
    root_count = struct.unpack('<H', _range(names, 6, 2))[0]
    _range(names, 0, root_count * 8)
    result, visited = {}, set()

    def walk(directory, prefix):
        if directory >= root_count or directory in visited:
            raise ValueError('Invalid/cyclic ROM directory')
        visited.add(directory)
        position, file_id, _ = struct.unpack_from('<IHH', names, directory * 8)
        if position < root_count * 8:
            raise ValueError('Invalid ROM directory offset')
        while True:
            tag = _range(names, position, 1)[0]
            position += 1
            if tag == 0:
                break
            length = tag & 127
            name = _range(names, position, length).decode('ascii')
            if not name or name in ('.', '..') or '/' in name or '\\' in name:
                raise ValueError('Invalid ROM filename')
            position += length
            full_name = prefix + name
            if tag & 128:
                child = struct.unpack('<H', _range(names, position, 2))[0]
                position += 2
                if child < 0xF000:
                    raise ValueError('Invalid ROM directory id')
                walk(child - 0xF000, full_name + '/')
            else:
                start, end = struct.unpack('<II', _range(allocations, file_id * 8, 8))
                if full_name in result:
                    raise ValueError('Duplicate ROM filename')
                result[full_name] = (file_id, start, end)
                file_id += 1
    walk(0, '')
    return result


def crc16(data):
    crc = 0xFFFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def replace_rom_files(data, replacements):
    files = rom_files(data)
    if set(replacements) - files.keys():
        raise ValueError('Replacement path absent from ROM')
    if not replacements:
        return bytes(data)
    output = bytearray(data)
    fat, fat_size = struct.unpack_from('<II', data, 0x48)
    used = max(struct.unpack_from('<I', data, fat + i + 4)[0] for i in range(0, fat_size, 8))
    # Never place resources over the executable, tables, banner or existing used region.
    used = max(used, struct.unpack_from('<I', data, 0x80)[0], 0x200)
    if used > len(data):
        raise ValueError('Invalid ROM used size')
    for name, replacement in sorted(replacements.items()):
        start = (used + 3) & ~3
        end = start + len(replacement)
        if end > len(output):
            capacity = max(0x20000, 1 << (end - 1).bit_length())
            output.extend(b'\xFF' * (capacity - len(output)))
        output[start:end] = replacement
        file_id = files[name][0]
        struct.pack_into('<II', output, fat + file_id * 8, start, end)
        used = end
    struct.pack_into('<I', output, 0x80, used)
    output[0x14] = max(0, (len(output) - 1).bit_length() - 17)
    struct.pack_into('<H', output, 0x15E, crc16(output[:0x15E]))
    return bytes(output)
