"""Puente entre el pipeline de Pipecat y el backend (por IPC, a través de `Session`).

Hacia el backend: cierra el turno de usuario y emite `voice.user_turn`. Desde el backend: traduce
`speak.*` a los frames que el TTS entiende como una respuesta de LLM. El agente vive fuera de
Pipecat: aquí no hay LLM ni agregador de contexto.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from drakter_contracts.speech_markup import IncrementalStripper, strip_tags
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

_WAKE_WORD = frozenset({"jarvis"})
_WAKE_LEAD = frozenset({"hey", "ey", "hei", "oye"})


def _wake_lists() -> tuple[frozenset[str], frozenset[str]]:
    """Variantes de «jarvis» y del «hey» en datos (`layer0.es.toml`, sección `[wake]`)."""
    try:
        from voice.conversation.layer0 import wake_words
    except ImportError:
        return _WAKE_WORD, _WAKE_LEAD
    return wake_words()


def _fold(token: str) -> str:
    """Minúsculas, sin tildes ni puntuación: para comparar palabras, no para mostrar."""
    plain = unicodedata.normalize("NFKD", token.lower())
    return "".join(ch for ch in plain if ch.isalnum())


def _wake_key(word: str) -> str:
    """Clave fonética aproximada del castellano: «y ya revish», «llarvis» y «jarvis» se acercan."""
    k = _fold(word)
    for a, b in (("sh", "s"), ("ch", "y"), ("ll", "y"), ("j", "y"), ("z", "s"), ("v", "b"), ("h", "")):
        k = k.replace(a, b)
    return "".join(ch for i, ch in enumerate(k) if i == 0 or ch != k[i - 1])


def _distance(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


_WAKE_KEY = _wake_key("jarvis")  # «yarbis»
_WAKE_MAX_JOIN = 3  # el STT parte «Jarvis» hasta en tres palabras («y ya revish»)


def is_wake(word: str, wake: frozenset[str]) -> bool:
    """Variante de la lista, o a distancia de edición ≤ 1 de «jarvis» (solo con 5+ letras)."""
    key = _wake_key(word)
    if _fold(word) in wake or key in {_wake_key(w) for w in wake}:
        return True
    return len(key) >= 5 and _distance(key, _WAKE_KEY) <= 1


def strip_wake_word(text: str) -> str | None:
    """Quita «jarvis» o «hey jarvis» del inicio. `None` si el texto no empieza así.

    Tolera cómo lo parte el STT («y ya revish», «ya revish», «llarvis»): se prueban las 1-3
    primeras palabras unidas, tras una muletilla opcional («hey», «oye»).
    """
    wake, lead = _wake_lists()
    tokens = text.split()
    words = [(i, w) for i, w in enumerate(map(_fold, tokens)) if w]
    starts = [0]
    if len(words) > 1 and words[0][1] in lead and words[0][1] not in wake:
        starts.append(1)
    for start in starts:
        for n in range(1, _WAKE_MAX_JOIN + 1):
            group = words[start : start + n]
            if len(group) < n:
                break
            if is_wake("".join(w for _, w in group), wake):
                return " ".join(tokens[group[-1][0] + 1 :]).lstrip(" ,.;:!?")
    return None


def _classify(text: str, bot_speaking: bool, awaiting_answer: bool) -> str | None:
    """Capa 0 (WP4). Si el módulo aún no está, el turno sigue sin clasificar."""
    try:
        from voice.conversation.layer0 import classify
    except ImportError:
        return None
    return classify(text, bot_speaking, awaiting_answer)


def _classify_ui(text: str) -> str | None:
    """Capa 0 del modo de interfaz (W5): `ui_jarvis`, `ui_drakter` o `None`."""
    try:
        from voice.conversation.layer0 import classify_ui
    except ImportError:
        return None
    return classify_ui(text)


def _classify_floating(text: str) -> str | None:
    """Capa 0 del modo flotante: `ui_floating_on`, `ui_floating_off` o `None`."""
    try:
        from voice.conversation.layer0 import classify_floating
    except ImportError:
        return None
    return classify_floating(text)


def _classify_appearance(text: str) -> tuple[str, str] | None:
    """Capa 0 de la apariencia (V1): `("avatar"|"layout", id)` o `None`."""
    try:
        from voice.conversation.layer0 import classify_appearance
    except ImportError:
        return None
    return classify_appearance(text)


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


@dataclass
class _Pending:
    """Tramo en cola detrás del que suena (modo flotante, docs/floating/CONTRACT.md §10).

    `beat`: un `speak.beat` (texto entero, ya cerrado). `open`: un `speak.open` del mismo turno que
    llegó con beats sonando o en cola; guarda sus deltas y su cierre hasta que le toque.
    """

    turn_id: str
    speech_id: int
    kind: str  # "beat" | "open"
    deltas: list[str] = field(default_factory=list)
    seq: int | None = None
    closed: bool = False


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
        # Contexto de respuesta abierto aguas abajo. Se abre con el primer texto, no con
        # speak.open: una frase fija (TTSSpeakFrame) dentro de un contexto abierto deja a
        # Fish sin audio para la respuesta (comprobado en WP9).
        self._ctx = False
        self._cut = False  # lo cortó una interrupción: sus deltas se ignoran
        self._seq: int | None = None
        self._stripper = IncrementalStripper()
        # FIFO por turno (speak.beat): lo que espera detrás del tramo activo, en orden de llegada.
        self._queue: deque[_Pending] = deque()
        self._active_kind = "open"

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
            if not self._open:
                self._session.speech_open = False
            await self._session.apply_pending_voice()
        elif isinstance(frame, (EndFrame, CancelFrame)):
            await self._cancel_final_timer()
        await self.push_frame(frame, direction)

    # ── turno de usuario ────────────────────────────────────────────────────
    async def _on_user_started(self) -> None:
        await self._cancel_final_timer()
        # El turno anterior aún esperaba su texto final y no ha salido al backend: el usuario
        # solo hizo una pausa. Su texto pasa al turno nuevo (antes se perdía).
        pending = self._utt if self._utt is not None and self._utt.stopped is not None else None
        state = self._session.state
        if state.bot_speaking or (self._open and not self._cut):
            overlap = "bot_speaking"
        elif state.turn_phase in ("thinking", "executing"):
            overlap = "agent_busy"
        else:
            overlap = "none"
        self._utt = _Utterance(overlap=overlap)
        if pending is not None and pending.texts:
            self._utt.texts = list(pending.texts)
            self._utt.started = pending.started
            self._utt.overlap = pending.overlap
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
        # Con texto pero sin `finalized` (Deepgram no lo marca si su respuesta a `Finalize` llega
        # vacía) basta un margen corto para recoger lo que venga en cola; sin texto, el tope entero.
        if utt.texts and utt.last_final:
            await self._finish(utt)
        else:
            wait = self._cfg.turn_final_timeout_s
            if utt.texts:
                wait = min(wait, float(getattr(self._cfg, "turn_final_grace_s", 0.3)))
            self._final_timer = self.create_task(self._final_timeout(utt, wait), "final_transcript_timeout")

    async def _final_timeout(self, utt: _Utterance, wait: float) -> None:
        await asyncio.sleep(wait)
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
        # openWakeWord va a umbral bajo: la confirmación es el texto. En conversación,
        # un «hey jarvis» inicial también se quita (no llega al chat).
        rest = strip_wake_word(text)
        # En reposo, «activa el modo Jarvis» despierta por la palabra del FINAL: no empieza por ella,
        # pero es una orden local válida. Se atiende y se vuelve a reposo, como si no hubiera turno.
        wake_inside = trigger == "wake" and rest is None and (
            _classify_ui(text) is not None or _classify_floating(text) is not None
        )
        if trigger == "wake" and rest is None and not wake_inside:
            await session.set_mode("standby", "wake")  # falso positivo: sin sonido
            return
        if rest is not None:
            text = rest
            if not text:
                return

        # Modo de interfaz (Drakter/Jarvis): frase cerrada, sin agente ni turno. El backend publica `ui.mode`.
        ui = _classify_ui(text)
        if ui is not None:
            await session.emit("voice.local_command", {"command": ui, "utt_id": utt.utt_id})
            await session.play_phrase(ui)
            if wake_inside:
                await session.set_mode("standby", trigger)
            return

        # Modo flotante: frase cerrada, sin agente ni turno. El backend publica `ui.floating` y dice la
        # frase (`ui_floating_on|off`, o `floating_unavailable` si la extensión no está lista).
        floating = _classify_floating(text)
        if floating is not None:
            await session.emit("voice.local_command", {"command": floating, "utt_id": utt.utt_id})
            if wake_inside:
                await session.set_mode("standby", trigger)
            return

        # Avatar o interfaz Jarvis: frase cerrada, sin agente ni turno. El backend publica `ui.appearance`.
        appearance = _classify_appearance(text)
        if appearance is not None:
            kind, target = appearance
            await session.emit(
                "voice.local_command", {"command": "ui_appearance", "utt_id": utt.utt_id, kind: target}
            )
            await session.play_phrase("ui_avatar" if kind == "avatar" else "ui_layout")
            return

        # Con un turno del agente en curso (aún sin audio, o entre el acuse y la respuesta),
        # «para …» también es una orden de parada.
        busy = state.bot_speaking or utt.overlap != "none" or state.turn_phase in ("thinking", "executing")
        command = _classify(text, busy, state.awaiting_answer)
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
        session.arm_filler()

    # ── habla: comandos speak.* del backend ─────────────────────────────────
    def _alive(self) -> bool:
        """El tramo activo sigue abierto o sonando (no cortado)."""
        session = self._session
        return self._speech_id is not None and not self._cut and (
            self._open or session.speech_open or session.speech_playing
        )

    def _busy_with(self, turn_id: str) -> bool:
        """Hay beats o tramos de `turn_id` sonando o en cola: lo nuevo del mismo turno va detrás."""
        if self._queue:
            return self._queue[-1].turn_id == turn_id
        return self._alive() and self._session.state.turn_id == turn_id

    async def speak_open(self, turn_id: str, speech_id: int) -> None:
        if self._busy_with(turn_id) and speech_id != self._speech_id:
            self._queue.append(_Pending(turn_id, speech_id, "open"))
            return
        # Nunca dos respuestas a la vez: si la anterior sigue abierta o sonando, se corta antes.
        # Si no, Fish mezcla los dos textos en el mismo WebSocket (el audio va al contexto activo).
        if self._alive() and speech_id != self._speech_id:
            await self.interrupt("new_turn")
        self._queue.clear()
        self._start(turn_id, speech_id, "open")

    def _start(self, turn_id: str, speech_id: int, kind: str) -> None:
        self._ctx = False
        state = self._session.state
        state.turn_id, state.speech_id = turn_id, speech_id
        self._speech_id, self._open, self._cut, self._seq = speech_id, True, False, None
        self._active_kind = kind
        self._stripper = IncrementalStripper()
        self._session.speech_text = ""
        self._session.speech_open = True

    async def speak_beat(self, turn_id: str, speech_id: int, text: str) -> bool:
        """`speak.beat`: open + delta + close(completed) en un tramo propio, en FIFO por turno.

        Devuelve `True` si se ignora: voz silenciada, `speech_id` ya usado o texto sin nada que decir.
        Un beat de otro turno corta lo de antes, como un `speak.open` nuevo.
        """
        if not self._session.state.tts_enabled or not strip_tags(text).strip():
            return True
        if speech_id == self._speech_id or any(p.speech_id == speech_id for p in self._queue):
            return True
        if self._busy_with(turn_id):
            self._queue.append(_Pending(turn_id, speech_id, "beat", deltas=[text], seq=0, closed=True))
            return False
        if self._alive():
            await self.interrupt("new_turn")
        self._queue.clear()
        await self._play(_Pending(turn_id, speech_id, "beat", deltas=[text], seq=0, closed=True))
        return False

    async def _play(self, item: _Pending) -> None:
        """Pone `item` como tramo activo y le pasa lo que ya tenga (deltas y cierre)."""
        self._start(item.turn_id, item.speech_id, item.kind)
        for seq, text in enumerate(item.deltas):
            await self.speak_delta(item.speech_id, seq, text)
        if item.seq is not None:
            self._seq = item.seq
        if item.closed:
            await self.speak_close(item.speech_id)

    async def on_playback_done(self, speech_id: int) -> None:
        """El PlaybackTracker cerró un tramo (`finished`): suena el siguiente de la cola."""
        if speech_id == self._speech_id and not self._open:
            self._session.speech_open = False
            self._session.speech_playing = False
            await self._advance()

    async def _advance(self) -> None:
        while self._queue and not self._alive():
            await self._play(self._queue.popleft())

    def _queued(self, speech_id: int) -> _Pending | None:
        return next((p for p in self._queue if p.speech_id == speech_id), None)

    async def speak_delta(self, speech_id: int, seq: int, text: str) -> bool:
        """Devuelve `True` si se ignora: speech desconocido, cortado, cerrado o `seq` repetido."""
        pending = self._queued(speech_id)
        if pending is not None:
            if pending.closed or (pending.seq is not None and seq <= pending.seq):
                return True
            pending.seq = seq
            pending.deltas.append(text)
            return False
        if speech_id != self._speech_id or not self._open or self._cut:
            return True
        if self._seq is not None and seq <= self._seq:
            return True
        self._seq = seq
        clean = self._stripper.feed(text)
        self._session.speech_text += clean
        spoken = clean if self._session.state.expression == "off" else text
        if spoken:
            if not self._ctx:
                self._ctx = True
                await self.push_frame(LLMFullResponseStartFrame())
            await self.push_frame(LLMTextFrame(spoken))
        return False

    async def speak_flush(self, speech_id: int) -> None:
        """Cierra la frase parcial (p. ej. al empezar una herramienta) sin cerrar el speech."""
        if speech_id == self._speech_id and self._open and not self._cut:
            if self._ctx:  # se reabre con el siguiente texto
                self._ctx = False
                await self.push_frame(LLMFullResponseEndFrame())

    async def speak_close(self, speech_id: int) -> None:
        pending = self._queued(speech_id)
        if pending is not None:
            pending.closed = True
            return
        if speech_id != self._speech_id or not self._open:
            return
        self._open = False
        silent = not self._session.speech_text.strip() and not self._ctx
        if silent:
            self._session.speech_open = False  # tramo sin texto: no va a sonar nada
        if not self._cut:
            self._session.speech_text += self._stripper.flush()
            if self._ctx:
                self._ctx = False
                await self.push_frame(LLMFullResponseEndFrame())
        if silent and not self._session.speech_playing:
            await self._advance()  # no habrá `finished` de este tramo: pasa el siguiente

    async def speak_stop(self, speech_id: int | None, reason: str) -> None:
        pending = self._queued(speech_id) if speech_id is not None else None
        if pending is not None:
            self._queue.remove(pending)  # aún no sonaba: basta con quitarlo de la cola
            return
        if speech_id is None or speech_id == self._speech_id:
            await self.interrupt(reason)

    async def interrupt(self, reason: str) -> None:
        log.info("interrupt", extra={"data": {"reason": reason}})
        # Un turno nuevo corta la respuesta anterior, no el acuse que acaba de armarse para él.
        if reason == "new_turn":
            self._session.keep_filler()
        self._mark_cut()
        await self.broadcast_interruption()

    def _mark_cut(self) -> None:
        """Regla de corte: cualquier interrupción corta el speech abierto y vacía la cola de beats."""
        if self._open:
            self._cut = True
        self._queue.clear()
        self._ctx = False  # la interrupción descarta el contexto aguas abajo
        self._session.speech_open = False

    async def turn_phase(self, phase: str) -> None:
        """Mientras el agente piensa o ejecuta, el silencio del usuario no cuenta como inactividad."""
        timeout = 0.0 if phase in ("thinking", "executing") else self._cfg.idle_nudge_s
        await self.push_frame(UserIdleTimeoutUpdateFrame(timeout=timeout), FrameDirection.UPSTREAM)
