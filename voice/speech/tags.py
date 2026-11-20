"""Etiquetas entre corchetes antes del TTS (hallazgo 3 de la verificación del 2026-11-20).

El modelo a veces inventa etiquetas (`[risa]`, `[en voz baja]`) fuera de la lista cerrada de
`drakter_contracts.speech_markup.TAGS`. Aquí se trata como etiqueta cualquier `[..]` corto con
«forma de etiqueta»: solo letras, espacios y `-_'`, hasta 5 palabras y 40 caracteres, y que no sea
el texto de un enlace Markdown (`[texto](url)`). Números (`[1]`), rutas o código no se tocan.

- `strip_all`: Kokoro, Fish con la expresión apagada y frases no expresivas. Quita todas.
- `keep_known`: Fish con expresión. Deja las de `TAGS` (normalizadas) y quita el resto.

No sustituye a `speech_markup.strip_tags`, que es lo que el backend usa para el chat y la BD.
"""

from __future__ import annotations

import re
from typing import Final

from drakter_contracts.speech_markup import TAGS

_TAG: Final = re.compile(r"[ \t]?\[([^\W\d_](?:[^\W\d]|[ \-'])*)\](?!\()")
_MAX_LEN: Final = 40
_MAX_WORDS: Final = 5


def _tag_shaped(inner: str) -> bool:
    return len(inner) <= _MAX_LEN and len(inner.split()) <= _MAX_WORDS


def _sub(text: str, keep: bool) -> str:
    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if not _tag_shaped(inner):
            return m.group(0)
        tag = inner.strip().lower()
        if keep and tag in TAGS:
            return m.group(0)[: m.start(1) - m.start(0) - 1] + f"[{tag}]"
        return ""

    out = _TAG.sub(repl, text)
    return out if text[:1].isspace() else out.lstrip()


def strip_all(text: str) -> str:
    """Quita toda etiqueta con forma de etiqueta (esté o no en `TAGS`)."""
    return _sub(text, keep=False)


def keep_known(text: str) -> str:
    """Deja las etiquetas de `TAGS` y quita las demás con forma de etiqueta."""
    return _sub(text, keep=True)
