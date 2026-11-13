"""SpeechGuard: lo que cruza frases y no se puede hablar (plan de voz v2 V-13, WP3).

Va delante del TTS, sobre los `LLMTextFrame` que llegan a trozos:
- los bloques de código (``` o ~~~) se omiten enteros;
- las líneas de tabla (empiezan por `|`) se omiten;
- las URL sueltas (`http…`, `www.…`) se sustituyen por «el enlace».
Lo demás (Markdown en línea, etiquetas, normalización) lo hace cada proveedor con sus
`text_transforms`. No sabe qué TTS está activo ni mira `tts_enabled`.

Acumula el texto que deja pasar en cada respuesta (sin etiquetas): `speech_text()` es la fuente
de `pending_head` para `PlaybackTracker`.
"""

from __future__ import annotations

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
_URL_TAIL: Final = ".,;:!?)»\"'"
_WORD_LEAD: Final = "(«\"'<"
_MAX_HELD: Final = 4096  # una «palabra» más larga se suelta tal cual


def _may_be_url(word: str) -> bool:
    w = word.lstrip(_WORD_LEAD).lower()
    return any(p.startswith(w) or w.startswith(p) for p in _URL_PREFIXES) if w else False


def _speak_word(word: str) -> str:
    """Una palabra completa: si es una URL suelta, «el enlace» con su puntuación final."""
    lead_len = len(word) - len(word.lstrip(_WORD_LEAD))
    lead, body = word[:lead_len], word[lead_len:]
    if body.lower().startswith(_URL_PREFIXES) and len(body) > 4:
        core = body.rstrip(_URL_TAIL)
        return f"{lead}{LINK_WORD}{body[len(core):]}"
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
        self._word = ""  # palabra retenida por si es una URL

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
            self._emit(out, ch)
            if ch == "\n":
                self._line_start = True
            return
        if self._word or _may_be_url(ch):
            self._word += ch
            if not _may_be_url(self._word) or len(self._word) > _MAX_HELD:
                self._emit(out, self._word)
                self._word = ""
            return
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
