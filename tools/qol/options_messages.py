"""Prepare only this fork's Options messages before the normal asset build.

Imported stock rows 0..59 (including all twenty frame labels) remain untouched.
Instant text constructs its existing label in C and needs no resource rows.
"""
import argparse
import os
from pathlib import Path
import re
import shlex
import xml.etree.ElementTree as ET
from xml.parsers import expat

ROOT = Path(__file__).resolve().parents[2]
CAP_LABELS = (
    'LEVEL CAPS', 'LEVEL CAP', 'OFF', 'ON', 'NEXT BOSS', 'NO CAP',
    'CONFIRM TO APPLY', 'X: CAPS', 'X: OPTIONS',
    '{STRVAR_1 0, 0, 0}  Lv. {STRVAR_1 52, 1, 0}',
)


def prepare_options_messages(source, enabled):
    """Return prepared bytes, rejecting any partial, drifted or unknown tail."""
    try:
        document = ET.fromstring(source, parser=ET.XMLParser(
            target=ET.TreeBuilder(insert_comments=True, insert_pis=True)))
    except ET.ParseError as error:
        raise ValueError('Options message source is not valid GMM XML') from error
    rows = list(document)
    if document.tag != 'body' or len(rows) not in (60, 70):
        raise ValueError('Options bank must contain stock 60 rows or the exact owned 70 rows')
    if any(text and text.strip(' \t\r\n') for text in
           (document.text, *(entry.tail for entry in rows))):
        raise ValueError('Options bank contains unowned text outside its rows')
    for index, entry in enumerate(rows):
        if entry.tag != 'row' or entry.attrib.get('index') != str(index) or entry.attrib.get('id') != f'msg_0045_{index:05}':
            raise ValueError('Options stock IDs must remain contiguous and unchanged')
    for index, text in enumerate(CAP_LABELS, 60):
        if len(rows) == 60:
            break
        entry = rows[index]
        children = [(child.tag, child.attrib, child.text) for child in entry]
        expected = [('attribute', {'name': 'window_context_name'}, 'used'),
                    ('language', {'name': 'English'}, text)]
        whitespace_only = not entry.text or entry.text.isspace()
        plain_children = all(not len(child) and (not child.tail or child.tail.isspace()) for child in entry)
        if (entry.attrib != {'id': f'msg_0045_{index:05}', 'index': str(index)}
                or children != expected or not whitespace_only or not plain_children):
            raise ValueError(f'Options cap row {index} differs from the owned label')
    # Expat reports byte offsets of actual tags, excluding lookalikes in comments.
    parser = expat.ParserCreate()
    depth = 0
    close = None

    def start_element(name, attributes):
        nonlocal depth
        depth += 1

    def end_element(name):
        nonlocal depth, close
        depth -= 1
        if depth == 0:
            close = parser.CurrentByteIndex

    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    parser.Parse(source, True)
    if close is None or not source[close:].startswith(b'</body'):
        raise ValueError('Options GMM must have an ordinary closing body tag')
    newline = '\r\n' if b'\r\n' in source else '\n'
    tail = ''.join(
        f'\t<row id="msg_0045_{index:05}" index="{index}">{newline}'
        f'\t\t<attribute name="window_context_name">used</attribute>{newline}'
        f'\t\t<language name="English">{text}</language>{newline}'
        f'\t</row>{newline}' for index, text in enumerate(CAP_LABELS, 60)).encode()
    if len(rows) == 70:
        # Remove only the exact bytes we generated, preserving all stock layout.
        if source.count(tail) != 1 or source[close - len(tail):close] != tail:
            raise ValueError('Cannot identify the owned Options tail without changing stock bytes')
        stock = source[:close - len(tail)] + source[close:]
        if len(ET.fromstring(stock)) != 60:
            raise ValueError('Removing the owned Options tail must leave 60 stock rows')
        return source if enabled else stock
    if not enabled:
        return source
    return source[:close] + tail + source[close:]


def resolve_level_caps(arguments, environ=None):
    """Resolve explicit CLI_DEFINES with the same defaults as qol_config.h."""
    environ = os.environ if environ is None else environ
    defines = environ.get('CLI_DEFINES', '')
    for argument in arguments:
        match = re.fullmatch(r'CLI_DEFINES(\+?[:]?=)(.*)', argument, re.S)
        if match:
            defines = defines + ' ' + match[2] if match[1] == '+=' else match[2]
    if '$' in defines:
        raise ValueError('Options preparation requires literal CLI_DEFINES, not make expressions')
    tokens = shlex.split(defines)
    values = {}
    position = 0
    while position < len(tokens):
        token = tokens[position]
        position += 1
        if token in ('-D', '-U'):
            if position == len(tokens):
                raise ValueError('Missing argument to compiler define/undefine')
            token += tokens[position]
            position += 1
        if token.startswith('-D'):
            name, separator, value = token[2:].partition('=')
            values[name] = value if separator else '1'
        elif token.startswith('-U'):
            values.pop(token[2:], None)

    def flag(name, visiting=()):
        if name in visiting:
            raise ValueError('Circular Options feature defines')
        value = values.get(name, 'QOL_MODS' if name == 'QOL_LEVEL_CAPS' else '0')
        if value in ('QOL_MODS', 'QOL_LEVEL_CAPS'):
            return flag(value, (*visiting, name))
        if not re.fullmatch(r'0[xX][0-9a-fA-F]+|[0-9]+', value):
            raise ValueError('Options feature flags must resolve to literal 0 or 1')
        base = 16 if value.lower().startswith('0x') else 8 if value.startswith('0') and len(value) > 1 else 10
        number = int(value, base)
        if number not in (0, 1):
            raise ValueError('Options feature flags must resolve to 0 or 1')
        return bool(number)

    return flag('QOL_LEVEL_CAPS')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'files/msgdata/msg/msg_0045.gmm')
    parser.add_argument('make_args', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        enabled = resolve_level_caps(args.make_args)
        source = args.source.read_bytes()
        prepared = prepare_options_messages(source, enabled)
        if prepared != source:
            args.source.write_bytes(prepared)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
