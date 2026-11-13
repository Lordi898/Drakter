"""Puente entre el pipeline de Pipecat y el backend (por IPC, a través de `Session`).

Hacia el backend: cierra el turno de usuario y emite `voice.user_turn`. Desde el backend: traduce
`speak.*` a los frames que el TTS entiende como una respuesta de LLM. El agente vive fuera de
Pipecat: aquí no hay LLM ni agregador de contexto.
"""

from __future__ import annotations

import asyncio
import logging
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from drakter_contracts.speech_markup import IncrementalStripper
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    CancelFrame,
    EndFrame,
    Frame,
    InterimTranscriptionFrame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
    UserIdleTimeoutUpdateFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

if TYPE_CHECKING:
    from voice.config import VoiceConfig
    from voice.session import Session

log = logging.getLogger("voice.bridge")

_WAKE_WORD = "jarvis"
_WAKE_LEAD = frozenset({"hey", "ey", "hei", "oye"})  # cómo transcribe el STT el «hey»


def _fold(token: str) -> str:
    """Minúsculas, sin tildes ni puntuación: para comparar palabras, no para mostrar."""
    plain = unicodedata.normalize("NFKD", token.lower())
    return "".join(ch for ch in plain if ch.isalnum())


def strip_wake_word(text: str) -> str | None:
    """Quita «jarvis» o «hey jarvis» del inicio. `None` si el texto no empieza así."""
    tokens = text.split()
    words = [(i, w) for i, w in enumerate(map(_fold, tokens)) if w]
    if words and words[0][1] in _WAKE_LEAD:
        words = words[1:]
    if not words or words[0][1] != _WAKE_WORD:
        return None
    return " ".join(tokens[words[0][0] + 1 :]).lstrip(" ,.;:!?")


def _classify(text: str, bot_speaking: bool, awaiting_answer: bool) -> str | None:
    """Capa 0 (WP4). Si el módulo aún no está, el turno sigue sin clasificar."""
    try:
        from voice.conversation.layer0 import classify
    except ImportError:
        return None
    return classify(text, bot_speaking, awaiting_answer)


@dataclass
class _Utterance:
    overlap: str
    utt_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started: float = field(default_factory=time.monotonic)
    stopped: float | None = None
    texts: list[str] = field(default_factory=list)
    last_final: bool = False
    last_text_at: float = 0.0
    eot_ms: int = 0


class BackendBridgeProcessor(FrameProcessor):
    def __init__(self, session: Session, cfg: VoiceConfig, **kwargs) -> None:
        super().__init__(**kwargs)
        self._session = session
        self._cfg = cfg
        # Turno de usuario
        self._utt: _Utterance | None = None
        self._final_timer: asyncio.Task | None = None
        self._vad_stopped_at: float | None = None
        # Habla del bot: el último speech abierto por el backend
        self._speech_id: int | None = None
        self._open = False  # entre speak.open y speak.close
        self._cut = False  # lo cortó una interrupción: sus deltas se ignoran
        self._seq: int | None = None
        self._stripper = IncrementalStripper()

    # ── frames del pipeline ─────────────────────────────────────────────────
    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, (TranscriptionFrame, InterimTranscriptionFrame)):
            if isinstance(frame, TranscriptionFrame):
                await self._on_transcription(frame)
            return  # lo que dice el usuario no sigue hacia el TTS

        if isinstance(frame, UserStartedSpeakingFrame):
            await self._on_user_started()
        elif isinstance(frame, UserStoppedSpeakingFrame):
            await self._on_user_stopped()
        elif isinstance(frame, VADUserStoppedSpeakingFrame):
            self._vad_stopped_at = time.monotonic()
        elif isinstance(frame, InterruptionFrame):
            self._mark_cut()
        elif isinstance(frame, BotStoppedSpeakingFrame):
            await self._session.apply_pending_voice()
        elif isinstance(frame, (EndFrame, CancelFrame)):
            await self._cancel_final_timer()
        await self.push_frame(frame, direction)

    # ── turno de usuario ────────────────────────────────────────────────────
    async def _on_user_started(self) -> None:
        await self._cancel_final_timer()
        state = self._session.state
        if state.bot_speaking or (self._open and not self._cut):
            overlap = "bot_speaking"
        elif state.turn_phase in ("thinking", "executing"):
            overlap = "agent_busy"
        else:
            overlap = "none"
        self._utt = _Utterance(overlap=overlap)
        await self._session.emit("voice.user_speech", {"utt_id": self._utt.utt_id, "phase": "started"})

    async def _on_transcription(self, frame: TranscriptionFrame) -> None:
        utt = self._utt
        if utt is None:  # fuera de un turno: antes de abrirlo o ya emitido
            return
        if frame.text.strip():
            utt.texts.append(frame.text.strip())
            utt.last_text_at = time.monotonic()
        utt.last_final = frame.finalized
        if utt.stopped is not None and frame.finalized:
            await self._cancel_final_timer()
            await self._finish(utt)

    async def _on_user_stopped(self) -> None:
        utt = self._utt
        if utt is None or utt.stopped is not None:
            return
        utt.stopped = time.monotonic()
        if self._vad_stopped_at is not None:
            utt.eot_ms = max(0, round((utt.stopped - self._vad_stopped_at) * 1000))
        await self._session.emit("voice.user_speech", {"utt_id": utt.utt_id, "phase": "stopped"})
        # El stop es un SystemFrame y adelanta al texto: si falta la transcripción final,
        # se espera un poco y se emite con lo que haya.
        if utt.texts and utt.last_final:
            await self._finish(utt)
        else:
            self._final_timer = self.create_task(self._final_timeout(utt), "final_transcript_timeout")

    async def _final_timeout(self, utt: _Utterance) -> None:
        await asyncio.sleep(self._cfg.turn_final_timeout_s)
        self._final_timer = None
        await self._finish(utt)

    async def _cancel_final_timer(self) -> None:
        timer, self._final_timer = self._final_timer, None
        if timer is not None and timer is not asyncio.current_task():
            await self.cancel_task(timer)

    async def _finish(self, utt: _Utterance) -> None:
        """Cierra el turno: palabra de activación, capa 0 y, si procede, `voice.user_turn`."""
        if self._utt is not utt:
            return
        self._utt = None
        session, state = self._session, self._session.state
        text = " ".join(utt.texts).strip()
        if not text or state.mode != "conversation":
            return  # en reposo nunca sale texto del usuario
        stopped = utt.stopped or time.monotonic()

        trigger = session.consume_trigger()
        if trigger == "wake":
            # openWakeWord va a umbral bajo: la confirmación es el texto.
            rest = strip_wake_word(text)
            if rest is None:
                await session.set_mode("standby", "wake")  # falso positivo: sin sonido
                return
            text = rest
            if not text:
                return

        command = _classify(text, state.bot_speaking, state.awaiting_answer)
        if command in ("rest", "close"):
            await session.emit("voice.local_command", {"command": command, "utt_id": utt.utt_id})
            await session.play_phrase("goodbye")
            await session.set_mode("standby", trigger)
            return
        if command == "stop_speech":
            await session.interrupt("user")
            await session.emit("voice.local_command", {"command": command, "utt_id": utt.utt_id})
            return
        if command == "backchannel":
            return

        await session.emit(
            "voice.user_turn",
            {
                "utt_id": utt.utt_id,
                "text": text,
                "lang": "es",
                "trigger": trigger,
                "overlap": utt.overlap,
                "audio_ms": round((stopped - utt.started) * 1000),
                "stt_ms": max(0, round((utt.last_text_at - stopped) * 1000)),
                "eot_ms": utt.eot_ms,
            },
        )

    # ── habla: comandos speak.* del backend ─────────────────────────────────
    async def speak_open(self, turn_id: str, speech_id: int) -> None:
        if self._open and not self._cut:  # el anterior quedó sin cerrar
            await self.push_frame(LLMFullResponseEndFrame())
        state = self._session.state
        state.turn_id, state.speech_id = turn_id, speech_id
        self._speech_id, self._open, self._cut, self._seq = speech_id, True, False, None
        self._stripper = IncrementalStripper()
        self._session.speech_text = ""
        await self.push_frame(LLMFullResponseStartFrame())

    async def speak_delta(self, speech_id: int, seq: int, text: str) -> bool:
        """Devuelve `True` si se ignora: speech desconocido, cortado, cerrado o `seq` repetido."""
        if speech_id != self._speech_id or not self._open or self._cut:
            return True
        if self._seq is not None and seq <= self._seq:
            return True
        self._seq = seq
        clean = self._stripper.feed(text)
        self._session.speech_text += clean
        spoken = clean if self._session.state.expression == "off" else text
        if spoken:
            await self.push_frame(LLMTextFrame(spoken))
        return False

    async def speak_flush(self, speech_id: int) -> None:
        """Cierra la frase parcial (p. ej. al empezar una herramienta) sin cerrar el speech."""
        if speech_id == self._speech_id and self._open and not self._cut:
            await self.push_frame(LLMFullResponseEndFrame())
            await self.push_frame(LLMFullResponseStartFrame())

    async def speak_close(self, speech_id: int) -> None:
        if speech_id != self._speech_id or not self._open:
            return
        self._open = False
        if not self._cut:
            self._session.speech_text += self._stripper.flush()
            await self.push_frame(LLMFullResponseEndFrame())

    async def speak_stop(self, speech_id: int | None, reason: str) -> None:
        if speech_id is None or speech_id == self._speech_id:
            await self.interrupt(reason)

    async def interrupt(self, reason: str) -> None:
        log.info("interrupt", extra={"data": {"reason": reason}})
        self._mark_cut()
        await self.broadcast_interruption()

    def _mark_cut(self) -> None:
        """Regla de corte: cualquier interrupción corta el speech abierto."""
        if self._open:
            self._cut = True

    async def turn_phase(self, phase: str) -> None:
        """Mientras el agente piensa o ejecuta, el silencio del usuario no cuenta como inactividad."""
        timeout = 0.0 if phase in ("thinking", "executing") else self._cfg.idle_nudge_s
        await self.push_frame(UserIdleTimeoutUpdateFrame(timeout=timeout), FrameDirection.UPSTREAM)
