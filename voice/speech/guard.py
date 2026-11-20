"""SpeechGuard: lo que cruza frases y no se puede hablar (plan de voz v2 V-13, WP3).

Va delante del TTS, sobre los `LLMTextFrame` que llegan a trozos:
- los bloques de código (``` o ~~~) se omiten enteros;
- las líneas de tabla (empiezan por `|`) se omiten;
- las URL sueltas (`http…`, `www.…`) se sustituyen por «el enlace»;
- los dominios sin esquema (`ejemplo.com`, `github.com/usuario`) se dicen por el nombre del sitio
  («ejemplo») o, si llevan ruta, «el enlace de github». Solo con un TLD conocido (`_TLDS`), así que
  `3.5`, `p. ej.`, `EE.UU.` o `main.py` no se tocan.
Lo demás (Markdown en línea, etiquetas, normalización) lo hace cada proveedor con sus
`text_transforms`. No sabe qué TTS está activo ni mira `tts_enabled`.

Acumula el texto que deja pasar en cada respuesta (sin etiquetas): `speech_text()` es la fuente
de `pending_head` para `PlaybackTracker`.
"""

from __future__ import annotations

import re
from typing import Final

from drakter_contracts.speech_markup import strip_tags
from pipecat.frames.frames import (
    Frame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

LINK_WORD: Final = "el enlace"
_URL_PREFIXES: Final = ("http://", "https://", "www.")
_URL_TAIL: Final = ".,;:!?)»\"'*_`"
_WORD_LEAD: Final = "(«\"'<*_`"
_MAX_HELD: Final = 4096  # una «palabra» más larga se suelta tal cual
# Caracteres que puede tener una URL o un dominio: mientras la palabra solo tenga estos, se retiene.
_URLISH: Final = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-/_:?=&%#~+@!,;)»\"'*`(«<")
# TLD habituales. Fuera a propósito los que casi siempre son extensiones de archivo (py, md, sh,
# rs, js, ts, pl, so…) para no tocar nombres de archivo.
_TLDS: Final = frozenset(
    "com es org net io dev ai app eu info co me uk de fr it pt nl be ch at se no dk fi ie pl ru "
    "us ca mx ar cl pe uy br cat gal eus edu gov int tv xyz gg ly fm site online tech page blog".split()
)
_DOMAIN: Final = re.compile(
    r"(?P<host>(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?P<tld>[a-z]{2,6}))(?::\d{1,5})?(?P<path>[/?#]\S*)?",
    re.IGNORECASE,
)


def _site_name(host: str) -> str | None:
    """`docs.github.com` → `github`; None si no parece un dominio (TLD desconocido o sin letras)."""
    labels = host.lower().split(".")
    if labels[-1] not in _TLDS:
        return None
    name = labels[-2]
    if name in ("co", "com", "org", "gob", "gov", "edu") and len(labels) > 2:  # bbc.co.uk
        name = labels[-3]
    if name == "www" or not any(c.isalpha() for c in name):
        return None
    return name


def _may_be_url(word: str) -> bool:
    w = word.lstrip(_WORD_LEAD).lower()
    return any(p.startswith(w) or w.startswith(p) for p in _URL_PREFIXES) if w else False


def _speak_word(word: str) -> str:
    """Una palabra completa: URL suelta → «el enlace»; dominio → su nombre o «el enlace de X»."""
    lead_len = len(word) - len(word.lstrip(_WORD_LEAD))
    lead, body = word[:lead_len], word[lead_len:]
    core = body.rstrip(_URL_TAIL)
    tail = body[len(core):]
    if body.lower().startswith(_URL_PREFIXES) and len(body) > 4:
        return f"{lead}{LINK_WORD}{tail}"
    m = _DOMAIN.fullmatch(core) if "." in core else None
    if m is not None:
        name = _site_name(m.group("host"))
        if name is not None:
            path = (m.group("path") or "").strip("/?#")
            return f"{lead}{f'{LINK_WORD} de {name}' if path else name}{tail}"
    return word


class GuardFilter:
    """Máquina de estados pura (sin Pipecat), para poder probarla aparte."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._line_start = True
        self._head = ""  # inicio de línea pendiente de decidir (espacios + marcadores)
        self._mode = "text"  # text | fence | table
        self._fence = ""
        self._word = ""  # palabra retenida por si es una URL o un dominio
        self._plain = False  # la palabra en curso ya no puede serlo: pasa tal cual

    def feed(self, text: str) -> str:
        out: list[str] = []
        for ch in text:
            self._char(ch, out)
        return "".join(out)

    def flush(self) -> str:
        out: list[str] = []
        if self._mode == "text":
            if self._head:
                self._decide_head(out, final=True)
            if self._word:
                out.append(_speak_word(self._word))
        self.reset()
        return "".join(out)

    # --- internos ---

    def _char(self, ch: str, out: list[str]) -> None:
        if self._mode in ("fence", "table") and not self._line_start:
            if ch == "\n":
                self._line_start = True
                if self._mode == "table":
                    self._mode = "text"
            return
        if self._line_start:
            if ch == "\n":
                if self._mode == "text":
                    self._emit(out, self._head + "\n")
                self._head = ""
                return
            self._head += ch
            self._decide_head(out, final=False)
            return
        self._text_char(ch, out)

    def _decide_head(self, out: list[str], *, final: bool) -> None:
        s = self._head.lstrip(" \t")
        if not s and not final:
            return
        if self._mode == "fence":
            if s.startswith(self._fence):
                self._mode, self._fence = "text", ""
                self._enter_skip_line()
            elif len(s) >= 3 or not self._fence.startswith(s):
                self._enter_skip_line()
            return
        for fence in ("```", "~~~"):
            if s.startswith(fence):
                self._mode, self._fence = "fence", fence
                self._enter_skip_line()
                return
            if fence.startswith(s) and not final:
                return  # todavía puede ser una valla
        if s.startswith("|"):
            self._mode = "table"
            self._enter_skip_line()
            return
        head, self._head, self._line_start = self._head, "", False
        for c in head:
            self._text_char(c, out)

    def _enter_skip_line(self) -> None:
        self._head = ""
        self._line_start = False
        if self._mode == "text":  # una valla de cierre: el resto de la línea se omite
            self._mode = "table"

    def _text_char(self, ch: str, out: list[str]) -> None:
        if ch.isspace():
            if self._word:
                self._emit(out, _speak_word(self._word))
                self._word = ""
            self._plain = False
            self._emit(out, ch)
            if ch == "\n":
                self._line_start = True
            return
        if not self._plain and ch in _URLISH:
            self._word += ch
            if len(self._word) > _MAX_HELD:
                self._emit(out, self._word)
                self._word, self._plain = "", True
            return
        if self._word and _may_be_url(self._word):  # una URL acaba en el primer carácter raro
            self._emit(out, _speak_word(self._word))
        else:
            self._emit(out, self._word)
        self._word, self._plain = "", True
        self._emit(out, ch)

    @staticmethod
    def _emit(out: list[str], text: str) -> None:
        if text:
            out.append(text)


class SpeechGuard(FrameProcessor):
    """Filtra los `LLMTextFrame` antes del TTS y acumula el texto de la respuesta."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._filter = GuardFilter()
        self._spoken: list[str] = []

    def speech_text(self) -> str:
        """Texto (sin etiquetas) que la respuesta en curso ha mandado al TTS hasta ahora."""
        return strip_tags("".join(self._spoken))

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return
        if isinstance(frame, LLMFullResponseStartFrame):
            self._filter.reset()
            self._spoken = []
        elif isinstance(frame, LLMTextFrame):
            text = self._filter.feed(frame.text)
            if not text:
                return
            self._spoken.append(text)
            frame.text = text
        elif isinstance(frame, LLMFullResponseEndFrame):
            rest = self._filter.flush()
            if rest:
                self._spoken.append(rest)
                await self.push_frame(LLMTextFrame(rest), direction)
        elif isinstance(frame, InterruptionFrame):
            self._filter.reset()
        await self.push_frame(frame, direction)


def create(cfg: object, ctl: object) -> SpeechGuard:
    """Fábrica para el núcleo (`VoiceConfig.guard`)."""
    return SpeechGuard()
