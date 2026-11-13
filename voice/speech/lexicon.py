"""Léxico de pronunciación en castellano: siglas y abreviaturas que el TTS leería mal.

Tabla cerrada en código; ampliarla es añadir una línea. Solo palabras completas.
"""

from __future__ import annotations

import re
from typing import Final

LEXICON: Final[dict[str, str]] = {
    "API": "a pe i",
    "APIs": "a pe is",
    "URL": "u erre ele",
    "PDF": "pe de efe",
    "UUID": "u u i de",
    "CPU": "ce pe u",
    "RAM": "ram",
    "USB": "u ese be",
    "IA": "i a",
    "TTS": "te te ese",
    "STT": "ese te te",
    "e.g.": "por ejemplo",
    "p. ej.": "por ejemplo",
    "etc.": "etcétera",
    "aprox.": "aproximadamente",
    "Sr.": "señor",
    "Dr.": "doctor",
}

_PATTERN: Final = re.compile(
    r"(?<![\w.])(" + "|".join(re.escape(k) for k in sorted(LEXICON, key=len, reverse=True)) + r")(?!\w)"
)


def apply_lexicon(text: str) -> str:
    return _PATTERN.sub(lambda m: LEXICON[m.group(1)], text)


async def lexicon(text: str, _text_type: object = None) -> str:
    """`TextTransform` de Pipecat: `(texto, tipo) -> texto`."""
    return apply_lexicon(text)
