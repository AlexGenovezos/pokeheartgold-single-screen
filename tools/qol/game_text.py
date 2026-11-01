"""Encode original text using the locally supplied game character map."""
from pathlib import Path


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
