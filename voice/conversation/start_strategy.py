"""Barge-in «bajar primero, decidir después» (V-08), como estrategia de inicio del UserTurnProcessor.

- Bot callado: el VAD abre turno al instante.
- Bot hablando y VAD de voz: baja el volumen (`ctl.set_duck(True)`) y decide con la transcripción
  parcial, porque por los altavoces llega eco:
    (a) capa 0 → `stop_speech`: corta la voz (`ctl.interrupt("user")`) y emite
        `voice.local_command{stop_speech}`, sin abrir turno;
    (b) asentimiento (si el bot no espera respuesta): restaura el volumen y descarta;
    (c) ≥ `bargein_min_words` palabras con solapamiento < 60 % frente a `state.spoken_tail`
        (no es eco): abre turno con interrupción; `turn_overlap = "bot_speaking"`;
    (d) vence `bargein_decide_ms` sin texto: restaura el volumen (falso ducking, se cuenta y se
        emite en `voice.metrics.false_ducks`).
  `rest`/`close` abren turno: el puente aplica la capa 0 al turno final.

Verificado en Pipecat 1.16.0: el `UserTurnController` pasa todos los frames (VAD, parciales y
`BotStarted/StoppedSpeakingFrame`, que suben desde la salida) a las estrategias de inicio.
`trigger_reset_aggregation()` solo lo escucha el agregador de LLM, que aquí no hay: no tiene efecto,
pero se llama por contrato. Lo que de verdad evita arrastrar el texto descartado es que la estrategia
de fin (`TurnAnalyzerUserTurnStopStrategy`) vacía su texto en `handle_user_turn_started`. El puente
(WP1) debe ignorar las transcripciones que lleguen sin turno abierto.
"""

from __future__ import annotations

from loguru import logger

import asyncio
import uuid
from typing import TYPE_CHECKING, Literal

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.turns.user_start import BaseUserTurnStartStrategy

from voice.conversation.layer0 import classify, normalize

if TYPE_CHECKING:
    from voice.config import VoiceConfig
    from voice.ports import Ctl

ECHO_OVERLAP = 0.6


def echo_overlap(text: str, spoken_tail: str) -> float:
    """Fracción de palabras de `text` que aparecen en lo último que dijo el bot."""
    words = normalize(text)
    if not words:
        return 0.0
    tail = set(normalize(spoken_tail))
    return sum(w in tail for w in words) / len(words)


class DrakterStartStrategy(BaseUserTurnStartStrategy):
    def __init__(self, cfg: VoiceConfig, ctl: Ctl) -> None:
        super().__init__(enable_interruptions=True)
        self._ctl = ctl
        self._min_words = int(getattr(cfg, "bargein_min_words", 3))
        self._decide_s = float(getattr(cfg, "bargein_decide_ms", 700)) / 1000
        self._bot_speaking = False
        self._user_speaking = False  # según el VAD
        self._turn_open = False
        self._deciding = False  # VAD con el bot hablando, aún sin veredicto
        self._ducked = False
        self._heard = ""  # última transcripción del tramo en decisión
        self._timer: asyncio.Task | None = None
        self.false_ducks = 0
        # Lo lee el puente (WP1) al cerrar el turno para `voice.user_turn.overlap`.
        self.turn_overlap: Literal["none", "bot_speaking"] = "none"

    # ---- ciclo del turno -------------------------------------------------------------------
    async def handle_user_turn_started(self) -> None:
        self._turn_open = True
        await self._end_decision()

    async def handle_user_turn_stopped(self) -> None:
        self._turn_open = False

    async def cleanup(self) -> None:
        await self._cancel_timer()
        await super().cleanup()

    # ---- frames ----------------------------------------------------------------------------
    async def process_frame(self, frame: Frame) -> None:
        if isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
            if self._deciding:
                # El bot terminó mientras se decidía: si no era eco, el usuario sigue con su turno.
                is_echo = bool(self._heard) and self._is_echo(self._heard)
                await self._end_decision()
                if self._user_speaking and not is_echo:
                    await self._open(interrupt=False)
        elif isinstance(frame, VADUserStartedSpeakingFrame):
            self._user_speaking = True
            await self._on_vad_start()
        elif isinstance(frame, VADUserStoppedSpeakingFrame):
            self._user_speaking = False
            if self._deciding:
                self._arm_timer()  # margen para que llegue la transcripción final
        elif isinstance(frame, (InterimTranscriptionFrame, TranscriptionFrame)):
            if self._deciding:
                await self._decide(frame.text, final=isinstance(frame, TranscriptionFrame))

    async def _on_vad_start(self) -> None:
        if self._turn_open or self._deciding:
            return
        state = self._ctl.state
        busy = getattr(self._ctl, "speech_open", False) or state.turn_phase in ("thinking", "executing")
        if not self._bot_speaking and not busy:
            await self._open()
            return
        self._deciding = True
        self._heard = ""
        self._duck(True)
        self._arm_timer()

    # ---- decisión ---------------------------------------------------------------------------
    async def _decide(self, text: str, *, final: bool) -> None:
        text = text.strip()
        if not text:
            if final:
                await self._discard()
            return
        self._heard = text
        state = self._ctl.state
        # Con el bot hablando, `awaiting_answer` no es fiable: los TTSTextFrame de toda la
        # respuesta (también su «¿…?» final) llegan antes que su audio. Solo cuenta ya callado.
        awaiting = state.awaiting_answer and not self._bot_speaking
        kind = classify(text, True, awaiting)
        logger.debug(
            f"barge-in: kind={kind} words={len(normalize(text))} final={final} "
            f"awaiting={awaiting} echo={self._is_echo(text)}"
        )
        if kind == "stop_speech":
            await self._stop_speech()
        elif kind == "backchannel":
            await self._discard()
        elif kind in ("rest", "close"):
            await self._open()
        elif self._is_echo(text):
            # Eco del propio TTS: no abre. Se sube el volumen pero se sigue escuchando el tramo,
            # por si el usuario habla encima del eco.
            self._duck(False)
            if final:
                await self._discard()
        elif len(normalize(text)) >= self._min_words:
            await self._open()
        elif final:
            # Pocas palabras al acabar el tramo: solo cuentan si el bot esperaba respuesta («sí»).
            if awaiting:
                await self._open()
            else:
                await self._discard()

    def _is_echo(self, text: str) -> bool:
        return echo_overlap(text, self._ctl.state.spoken_tail) >= ECHO_OVERLAP

    async def _stop_speech(self) -> None:
        await self._end_decision(restore=False)
        await self._ctl.interrupt("user")
        self._duck(False)
        await self._ctl.emit(
            "voice.local_command", {"command": "stop_speech", "utt_id": uuid.uuid4().hex}
        )
        await self.trigger_reset_aggregation()

    async def _discard(self) -> None:
        await self._end_decision()
        await self.trigger_reset_aggregation()

    async def _open(self, *, interrupt: bool = True) -> None:
        self.turn_overlap = "bot_speaking" if self._bot_speaking else "none"
        await self._end_decision(restore=False)
        await self.report_user_turn_started(enable_interruptions=interrupt)
        self._duck(False)  # la interrupción ya ha vaciado la salida

    async def _end_decision(self, *, restore: bool = True) -> None:
        self._deciding = False
        self._heard = ""
        await self._cancel_timer()
        if restore:
            self._duck(False)

    # ---- volumen y temporizador -------------------------------------------------------------
    def _duck(self, on: bool) -> None:
        if on != self._ducked:
            self._ducked = on
            self._ctl.set_duck(on)

    def _arm_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self._timer = self.create_task(self._timer_expired(), "bargein_decide")

    async def _cancel_timer(self) -> None:
        timer, self._timer = self._timer, None
        if timer is not None and timer is not asyncio.current_task():
            await self.cancel_task(timer)

    async def _timer_expired(self) -> None:
        await asyncio.sleep(self._decide_s)
        self._timer = None
        if not self._deciding:
            return
        if not self._heard:
            # (d) Falso ducking: nada que decida. Se restaura el volumen; si el VAD sigue activo,
            # se sigue escuchando por si llega texto tarde.
            if self._ducked:
                self.false_ducks += 1
                self._duck(False)
                await self._ctl.emit("voice.metrics", {"false_ducks": self.false_ducks})
            if not self._user_speaking:
                await self._end_decision()
        elif not self._user_speaking:
            # Acabó el tramo y no llegó la transcripción final: se decide con la última parcial.
            await self._decide(self._heard, final=True)


def create(cfg: VoiceConfig, ctl: Ctl) -> list[BaseUserTurnStartStrategy]:
    """Fábrica del registro: `("turn_start", "drakter")`."""
    return [DrakterStartStrategy(cfg, ctl)]
