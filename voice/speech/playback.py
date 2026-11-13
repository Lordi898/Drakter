"""PlaybackTracker: qué se ha oído de verdad (plan de voz v2 V-32). Va DESPUÉS de `transport.output()`.

Después de la salida, los `TTSTextFrame` llegan al ritmo del audio (el transporte los suelta tras
el audio de su frase), así que lo que pasa por aquí es lo que ya sonó. Mantiene en `ctl.state`:
`bot_speaking`, `spoken_tail` (últimos 200 caracteres dichos) y `awaiting_answer` (la última frase
dicha acaba en «?»). Emite `voice.playback` (`started`, `sentence_done`, `finished`, `interrupted`)
del `speech_id` activo del puente; ante una interrupción añade `heard_tail` (≤80) y
`pending_head` (≤200).

`text_source` devuelve el texto acumulado del speech (p. ej. `SpeechGuard.speech_text`): de ahí sale
`pending_head`, localizando `heard_tail` con `rfind` o, si no aparece, por recuento de caracteres.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from drakter_contracts.speech_markup import strip_tags
from loguru import logger
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TTSTextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from voice.ports import Ctl

TAIL_STATE: Final = 200
HEARD_TAIL: Final = 80
PENDING_HEAD: Final = 200


def pending_after(full: str, heard: str, tail: str) -> str:
    """Los `PENDING_HEAD` caracteres del texto completo que siguen a lo oído."""
    if not full:
        return ""
    idx = full.rfind(tail) if tail else -1
    start = idx + len(tail) if idx >= 0 else min(len(heard), len(full))
    return full[start:].strip()[:PENDING_HEAD]


class PlaybackTracker(FrameProcessor):
    def __init__(self, ctl: Ctl, text_source: Callable[[], str] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._ctl = ctl
        self._text_source = text_source
        self._reset_speech()
        self._last_closed: int | None = None

    def _reset_speech(self) -> None:
        self._speech: tuple[str, int] | None = None  # (turn_id, speech_id) en curso
        self._index = 0
        self._heard = ""
        self._closed = False

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        try:
            await self._track(frame, direction)
        except Exception as exc:  # el seguimiento nunca corta el audio
            logger.warning(f"PlaybackTracker: {exc}")
        await self.push_frame(frame, direction)

    async def _track(self, frame: Frame, direction: FrameDirection) -> None:
        state = self._ctl.state
        if isinstance(frame, BotStartedSpeakingFrame):
            state.bot_speaking = True
            await self._open_if_needed()
        elif isinstance(frame, BotStoppedSpeakingFrame):
            state.bot_speaking = False
            if self._speech and self._closed:
                await self._finish("finished")
        elif direction != FrameDirection.DOWNSTREAM:
            return
        elif isinstance(frame, LLMFullResponseStartFrame):
            await self._open_if_needed()
        elif isinstance(frame, TTSTextFrame):
            text = " ".join(strip_tags(frame.text).split())
            if not text:
                return
            self._heard = f"{self._heard} {text}".strip()
            state.spoken_tail = f"{state.spoken_tail} {text}".strip()[-TAIL_STATE:]
            state.awaiting_answer = text.rstrip(" »\"')").endswith("?")
            if self._speech:
                await self._emit("sentence_done")
                self._index += 1
        elif isinstance(frame, LLMFullResponseEndFrame):
            if self._speech:
                self._closed = True
                if not state.bot_speaking:
                    await self._finish("finished")
        elif isinstance(frame, InterruptionFrame):
            state.bot_speaking = False
            if self._speech:
                await self._finish("interrupted")

    async def _open_if_needed(self) -> None:
        state = self._ctl.state
        if self._speech or state.turn_id is None or state.speech_id is None:
            return
        if state.speech_id == self._last_closed:
            return  # p. ej. una frase fija tras el cierre: no es un tramo nuevo
        self._speech = (state.turn_id, state.speech_id)
        await self._emit("started")

    async def _finish(self, kind: str) -> None:
        extra: dict[str, str] = {}
        if kind == "interrupted":
            tail = self._heard[-HEARD_TAIL:]
            full = self._text_source() if self._text_source else ""
            extra = {"heard_tail": tail, "pending_head": pending_after(full, self._heard, tail)}
        await self._emit(kind, **extra)
        self._last_closed = self._speech[1] if self._speech else None
        self._reset_speech()

    async def _emit(self, kind: str, **extra: str) -> None:
        if not self._speech:
            return
        turn_id, speech_id = self._speech
        await self._ctl.emit(
            "voice.playback",
            {"turn_id": turn_id, "speech_id": speech_id, "state": kind, "sentence_index": self._index, **extra},
        )


def create(cfg: object, ctl: Ctl) -> PlaybackTracker:
    """Fábrica para el núcleo (`VoiceConfig.playback`). El texto del speech lo acumula el puente
    en `ctl.speech_text` (sin etiquetas, todo lo recibido): de ahí sale `pending_head`."""
    return PlaybackTracker(ctl, text_source=lambda: getattr(ctl, "speech_text", ""))
