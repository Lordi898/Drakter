"""Etiquetas de expresión de la voz (sintaxis nativa de Fish: `[etiqueta]`), plan de voz v2 V-15.

Lista cerrada en `TAGS`. Se hablan (Fish) y nunca llegan al chat, la BD ni la auditoría: el backend
limpia los deltas con `IncrementalStripper` y el texto terminal con `strip_tags`, que usa la misma
máquina de estados, así que ambos dan el mismo texto sea cual sea el corte entre deltas.
Cambiar la lista es editar esta constante (se valida al oído en la integración).
"""

from __future__ import annotations

import re
from typing import Final

TAGS: Final[frozenset[str]] = frozenset({
    "calm", "happy", "excited", "curious", "confident", "empathetic", "regretful", "surprised", "sad",
    "speaking slowly", "speaking quickly", "normal pace", "laughing", "chuckling", "sighing", "break",
    "emphasis",
})
MAX_PENDING: Final = 24
"""Un `[` sin cerrar se retiene como mucho estos caracteres (incluido el `[`); luego sale tal cual."""


def _is_tag(inner: str) -> bool:
    return inner.strip().lower() in TAGS


class IncrementalStripper:
    """Quita `[tag]` con tag ∈ TAGS de un texto que llega a trozos.

    Retiene un `[` incompleto hasta `MAX_PENDING` caracteres. Al quitar una etiqueta precedida de
    inicio o espacio, se come el espacio siguiente («Hola [calm] mundo» → «Hola mundo»).
    """

    def __init__(self) -> None:
        self._buf = ""
        self._last = ""
        self._eat = False

    def _emit(self, out: list[str], text: str) -> None:
        if text:
            out.append(text)
            self._last = text[-1]
            self._eat = False

    def feed(self, text: str) -> str:
        out: list[str] = []
        for ch in text:
            if self._buf:
                if ch == "]":
                    inner, self._buf = self._buf[1:], ""
                    if _is_tag(inner):
                        self._eat = not self._last or self._last.isspace()
                    else:
                        self._emit(out, f"[{inner}]")
                    continue
                if ch != "[" and ch != "\n" and len(self._buf) < MAX_PENDING:
                    self._buf += ch
                    continue
                pending, self._buf = self._buf, ""
                self._emit(out, pending)
            if ch == "[":
                self._buf = "["
                continue
            if self._eat:
                self._eat = False
                if ch == " ":
                    continue
            self._emit(out, ch)
        return "".join(out)

    def flush(self) -> str:
        rest = self._buf
        self._buf, self._last, self._eat = "", "", False
        return rest


def strip_tags(text: str) -> str:
    s = IncrementalStripper()
    return s.feed(text) + s.flush()


_BRACKET = re.compile(r"\[([^\[\]\n]{1,60})\](?!\()")


def keep_allowed(text: str) -> str:
    """Para Fish: deja las etiquetas de `TAGS` y borra cualquier otro `[..]` corto (≤3 palabras).

    No toca enlaces Markdown (`[texto](url)`) ni corchetes largos.
    """

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if _is_tag(inner):
            return f"[{inner.strip().lower()}]"
        return "" if len(inner.split()) <= 3 else m.group(0)

    return _BRACKET.sub(repl, text)


def prompt_block() -> str:
    """Texto estable (sin variaciones entre llamadas) para `agent/identity/VOICE.md`."""
    tags = ", ".join(f"[{t}]" for t in sorted(TAGS))
    return (
        "Cuando su respuesta se vaya a oír, puede marcar la expresión de la voz con etiquetas entre "
        f"corchetes, solo de esta lista: {tags}. Póngalas con moderación, delante del fragmento al "
        "que afectan. No use otras etiquetas: el resto se borra. Nunca aparecen en pantalla."
    )
