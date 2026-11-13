"""Characters that render as nothing. Untrusted text drops them before it is shown or compared."""

from __future__ import annotations

import unicodedata
from typing import Final

KEPT_CONTROLS: Final = frozenset("\n\t")
# Cc controls, Cf format (bidi, zero width, soft hyphen), Cs lone surrogates, Cn unassigned.
DROPPED_CATEGORIES: Final = frozenset({"Cc", "Cf", "Cs", "Cn"})
# Letters and marks that are blank or invisible although their category is not Cf.
INVISIBLE: Final = frozenset(
    chr(code)
    for code in (
        0x034F,  # combining grapheme joiner
        0x115F, 0x1160, 0x3164, 0xFFA0,  # hangul fillers
        0x17B4, 0x17B5,  # khmer inherent vowels
        *range(0x180B, 0x1810),  # mongolian variation selectors and vowel separator
        0x2800,  # braille blank
        *range(0xFE00, 0xFE10),  # variation selectors
        *range(0xE0100, 0xE01F0),  # variation selectors supplement
    )
)  # fmt: skip


def is_invisible(char: str) -> bool:
    if char in KEPT_CONTROLS:
        return False
    return char in INVISIBLE or unicodedata.category(char) in DROPPED_CATEGORIES


def strip_invisible(text: str) -> str:
    """Drop every invisible character; keeps newlines and tabs. No other normalisation."""
    return "".join(char for char in text if not is_invisible(char))
