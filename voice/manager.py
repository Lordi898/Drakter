"""Voice turn manager: the state machine of CONTRACT.md, owned by the asyncio loop.

Threads, none of which touches manager state directly:
- voice-listen: VAD and wake word, one frame at a time. Owns the session frames and the ring.
- voice-stt, voice-tts: load engines on first use and run them.
- voice-capture: opens and stops the device, which may block.
- voice-ctl: anything else that may block (player interrupt, wake word load, metrics file).
Every result returns through _hop() and is checked against the current turn object, so a late
event of an old turn cannot change the state of a new one.

Privacy rules enforced here: the capture is only open while _capture_wanted() says so, and that
depends on _mic_enabled, which only mic_set(True) raises. Audio stays in RAM and text is never
logged: logs and metrics carry lengths and times.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import queue
import threading
import time
import uuid
from collections import OrderedDict, deque
from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass, field, fields, replace
from enum import Enum
from typing import Any, Final, Generic, TypeVar

import numpy as np

from voice import registry
from voice.config import VoiceConfig
from voice.contracts import (
    EVENTS,
    FRAME_MS,
    SAMPLE_RATE,
    AudioCapture,
    AudioFrame,
    AudioSink,
    CancelToken,
    Pcm,
    STTProvider,
    StopReason,
    TTSProvider,
    VADProvider,
    VoiceContext,
    VoiceError,
    VoiceState,
    WakeDetection,
    WakeWordProvider,
)
from voice.metrics import MetricsSink, TurnMetrics

log = logging.getLogger("voice.manager")

EventEmitter = Callable[[str, dict[str, Any]], None]
T = TypeVar("T")

MAX_SYNTH_AHEAD: Final = 2  # utterances synthesised and not yet played: no generating far ahead
MAX_SYNTH_PENDING: Final = 64  # sentences waiting for synthesis; beyond this they are dropped
MAX_DEAD_TURNS: Final = 256  # closed turn ids remembered to ignore late deltas
MAX_QUEUED_FRAMES: Final = 512  # about 16 s; the oldest frame goes first if listening falls behind
PLAYBACK_START_TIMEOUT_S: Final = 60.0  # queued audio that never starts means a dead sink
SHUTDOWN_TIMEOUT_S: Final = 8.0
INTERRUPT_REASONS: Final = frozenset({"user", "barge_in", "new_turn"})
_FATAL_CODES: Final = frozenset({"model_missing", "dependency_missing"})


class _FrameMode(Enum):
    DROP = "drop"
    ARMED = "armed"
    SESSION = "session"
    BARGE = "barge"


_STOP: Final = object()


class _Worker:
    """One daemon thread running jobs in order. Daemon so a stuck engine cannot block exit."""

    def __init__(self, name: str) -> None:
        self._jobs: queue.SimpleQueue[Callable[[], None] | None] = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        while (job := self._jobs.get()) is not None:
            try:
                job()
            except Exception as exc:  # noqa: BLE001 - jobs report their own errors; this is the last net
                log.error("worker_job_failed", extra={"data": {"error": type(exc).__name__}})

    def submit(self, fn: Callable[..., None], *args: Any) -> None:
        self._jobs.put(lambda: fn(*args))

    def call(self, fn: Callable[..., T], *args: Any) -> asyncio.Future[T]:
        result: concurrent.futures.Future[T] = concurrent.futures.Future()

        def job() -> None:
            try:
                result.set_result(fn(*args))
            except BaseException as exc:  # noqa: BLE001 - handed to the awaiting coroutine
                result.set_exception(exc)

        self._jobs.put(job)
        return asyncio.wrap_future(result)

    def stop(self) -> None:
        self._jobs.put(None)

    def join(self, timeout: float) -> None:
        if self._thread.is_alive():
            self._thread.join(timeout)


class _Lazy(Generic[T]):
    """Builds and loads an engine once, on whichever worker thread needs it first."""

    def __init__(self, factory: Callable[[], T], loader: Callable[[T], None] | None = None) -> None:
        self._factory = factory
        self._loader = loader
        self._lock = threading.Lock()
        self.value: T | None = None

    def get(self) -> T:
        with self._lock:
            if self.value is None:
                engine = self._factory()
                if self._loader is not None:
                    self._loader(engine)
                self.value = engine
            return self.value


class _ListenQueue:
    """Frames, bounded, plus control items that are never dropped and keep their place in line."""

    def __init__(self, max_frames: int) -> None:
        self._items: deque[Any] = deque()
        self._frames = 0
        self._max = max_frames
        self._cond = threading.Condition()
        self.dropped = 0

    def put_frame(self, frame: AudioFrame) -> None:
        with self._cond:
            if self._frames >= self._max:
                self.dropped += 1
                if not isinstance(self._items[0], AudioFrame):
                    return
                self._items.popleft()
                self._frames -= 1
            self._items.append(frame)
            self._frames += 1
            self._cond.notify()

    def put_control(self, item: Any) -> None:
        with self._cond:
            self._items.append(item)
            self._cond.notify()

    def get(self) -> Any:
        with self._cond:
            while not self._items:
                self._cond.wait()
            item = self._items.popleft()
            if isinstance(item, AudioFrame):
                self._frames -= 1
            return item


@dataclass(eq=False)
class _Turn:
    id: str
    metrics: TurnMetrics
    stt_token: CancelToken = field(default_factory=CancelToken)
    tts_token: CancelToken = field(default_factory=CancelToken)
    segmenter: Any = None
    final: bool = False
    played: bool = False
    outstanding: set[str] = field(default_factory=set)
    audio_s: float = 0.0  # written by the TTS thread only
    synth_s: float = 0.0  # written by the TTS thread only


@dataclass(eq=False)
class _Session:
    """One user intervention. Fields below `released` belong to the listen thread."""

    turn: _Turn
    opened_ns: int
    seed_ring: bool
    cancelled: bool = False
    released: bool = False
    begun: bool = False
    done: bool = False
    frames: list[Pcm] = field(default_factory=list)
    first_voiced: int | None = None
    last_voiced: int = 0
    last_voiced_ns: int = 0
    silent_frames: int = 0


@dataclass(eq=False)
class _Utterance:
    id: str
    turn: _Turn
    provider: str = ""
    started: bool = False


@dataclass(frozen=True, slots=True, eq=False)
class _SynthItem:
    turn: _Turn
    utterance: _Utterance
    sentence: str
    context: VoiceContext


def _as_voice_error(exc: BaseException) -> VoiceError:
    if isinstance(exc, VoiceError):
        return exc
    return VoiceError("engine_failed", f"unexpected failure: {type(exc).__name__}")


def _coerce_context(raw: VoiceContext | Mapping[str, Any] | None) -> VoiceContext:
    if raw is None:
        return VoiceContext()
    if isinstance(raw, VoiceContext):
        return raw
    known = {f.name for f in fields(VoiceContext)}
    if set(raw) - known or not all(isinstance(v, str) for v in raw.values()):
        raise VoiceError("invalid_request", "invalid speak context")
    if raw.get("priority", "normal") not in {"low", "normal", "high"}:
        raise VoiceError("invalid_request", "invalid speak context priority")
    return VoiceContext(**raw)


class VoiceManager:
    def __init__(
        self,
        config: VoiceConfig,
        emit: EventEmitter,
        *,
        capture: AudioCapture | None = None,
        sink: AudioSink | None = None,
        vad: VADProvider | None = None,
        wakeword: WakeWordProvider | None = None,
        stt: STTProvider | None = None,
        tts: TTSProvider | None = None,
        metrics_sink: MetricsSink | None = None,
    ) -> None:
        self._config = config
        self._emit_event = emit
        self._injected_capture = capture
        self._injected_sink = sink
        self._loop: asyncio.AbstractEventLoop | None = None
        self._closing = False
        self._started = False

        def load(engine: Any) -> None:
            engine.load()

        self._vad = _Lazy(lambda: vad if vad is not None else registry.build_vad(config), load)
        self._wakeword = _Lazy(lambda: wakeword if wakeword is not None else registry.build_wakeword(config), load)
        self._stt = _Lazy(lambda: stt if stt is not None else registry.build_stt(config), load)
        self._tts = _Lazy(lambda: tts if tts is not None else registry.build_tts(config), load)
        self._player = _Lazy(self._build_player)
        self._personality = _Lazy(self._build_personality)
        self._wakeword_name = wakeword.name if wakeword is not None else config.wakeword_provider
        self._vad_name = vad.name if vad is not None else config.vad_provider
        self._metrics_sink = metrics_sink if metrics_sink is not None else MetricsSink(config.metrics_path)

        # Loop-owned state.
        self._state = VoiceState.OFF
        self._mic_enabled = False
        self._wakeword_on = False
        self._turn: _Turn | None = None
        self._session: _Session | None = None
        self._utterances: dict[str, _Utterance] = {}
        self._playing: str | None = None
        self._dead_turns: OrderedDict[str, None] = OrderedDict()
        self._capture: AudioCapture | None = None
        self._capture_name: str | None = capture.name if capture is not None else None
        self._capture_open = False
        self._capture_epoch = 0
        self._capture_lock = asyncio.Lock()
        self._last_mic_event: tuple[bool, bool] | None = None
        self._tasks: set[asyncio.Task[Any]] = set()

        # Written by the loop, read by the listen thread; a plain attribute swap is enough.
        self._frame_mode = _FrameMode.DROP

        # Listen thread only.
        self._listen_queue = _ListenQueue(MAX_QUEUED_FRAMES)
        self._seen_mode = _FrameMode.DROP
        self._ring: deque[AudioFrame] = deque(maxlen=max(1, config.vad_preroll_ms // FRAME_MS))
        self._active_vad: VADProvider | None = None
        self._vad_is_fallback = False
        self._wake_paused = False
        self._barge_frames = 0
        self._barge_fired = False

        # Shared between the loop and the TTS thread, under _synth_cond.
        self._synth_queue: deque[_SynthItem] = deque()
        self._unplayed: set[str] = set()
        self._synth_cond = threading.Condition()
        self._synth_stop = False

        self._listen_thread = threading.Thread(target=self._listen_loop, name="voice-listen", daemon=True)
        self._tts_thread = threading.Thread(target=self._tts_loop, name="voice-tts", daemon=True)
        self._stt_worker = _Worker("voice-stt")
        self._capture_worker = _Worker("voice-capture")
        self._ctl_worker = _Worker("voice-ctl")

    # ---- lifecycle ------------------------------------------------------------------------------

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._loop = asyncio.get_running_loop()
        for worker in (self._stt_worker, self._capture_worker, self._ctl_worker):
            worker.start()
        self._listen_thread.start()
        self._tts_thread.start()

    async def _ensure_running(self) -> None:
        if self._closing:
            raise VoiceError("invalid_request", "voice service is shutting down")
        await self.start()

    async def close(self) -> None:
        """Stops everything. Never leaves the capture open, even if an engine hangs."""
        if self._closing or not self._started:
            return
        self._mic_enabled = False
        self._wakeword_on = False
        self._cancel_session("cancelled")
        if self._turn is not None:
            self._cut_turn(self._turn)
        self._closing = True  # from here late hops are ignored
        self._refresh_frame_mode()
        try:
            await asyncio.wait_for(self._sync_capture(), SHUTDOWN_TIMEOUT_S)
        except (VoiceError, TimeoutError) as exc:
            log.error("capture_close_failed", extra={"data": {"error": type(exc).__name__}})

        self._listen_queue.put_control(_STOP)
        with self._synth_cond:
            self._synth_stop = True
            self._synth_queue.clear()
            self._synth_cond.notify_all()
        self._stt_worker.stop()
        self._capture_worker.stop()
        try:
            await asyncio.wait_for(self._ctl_worker.call(self._close_engines), SHUTDOWN_TIMEOUT_S)
        except (TimeoutError, Exception) as exc:  # noqa: BLE001 - shutdown goes on regardless
            log.error("engine_close_failed", extra={"data": {"error": type(exc).__name__}})
        self._ctl_worker.stop()
        for task in tuple(self._tasks):
            task.cancel()
        self._tasks.clear()

    def _close_engines(self) -> None:
        self._listen_thread.join(2.0)
        self._tts_thread.join(2.0)
        self._stt_worker.join(2.0)
        for slot in (self._player, self._stt, self._tts, self._vad, self._wakeword):
            engine = slot.value
            if engine is None:
                continue
            try:
                engine.close()
            except Exception as exc:  # noqa: BLE001 - one bad engine must not keep the others open
                log.error("engine_close_failed", extra={"data": {"error": type(exc).__name__}})
        if self._active_vad is not None and self._active_vad is not self._vad.value:
            self._active_vad.close()

    def _build_player(self) -> Any:
        from voice.audio.player import Player

        if self._injected_sink is not None:
            sink = self._injected_sink
        else:
            from voice.audio.backends import open_sink

            sink = open_sink(self._config)
        player = Player(
            sink, self, level_hz=self._config.level_hz, output_latency_ms=self._config.output_latency_ms
        )
        player.start()
        return player

    def _build_personality(self) -> Any:
        from voice.personality.engine import VoicePersonalityEngine

        return VoicePersonalityEngine(self._config)

    # ---- commands -------------------------------------------------------------------------------

    async def handle_command(self, name: str, args: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Runs a command of CONTRACT.md. `args` are already validated by ipc.parse_command."""
        args = args or {}
        match name:
            case "status":
                return self.status()
            case "mic.set":
                return await self.mic_set(args["enabled"])
            case "wakeword.set":
                return await self.wakeword_set(args["enabled"])
            case "listen.start":
                return await self.listen_start()
            case "listen.stop":
                return await self.listen_stop()
            case "listen.cancel":
                return await self.listen_cancel()
            case "speak":
                return await self.speak(args["turn_id"], args["text"], args.get("final", False), args.get("context"))
            case "interrupt":
                return await self.interrupt(args.get("reason", "user"))
        raise VoiceError("invalid_request", "unknown command")

    def status(self) -> dict[str, Any]:
        tts = self._tts.value
        return {
            "state": self._state.value,
            "mic_enabled": self._mic_enabled,
            "listen_mode": "wakeword" if self._wakeword_on else "push_to_talk",
            "wakeword_available": self._wakeword_name != "null",
            "barge_in": self._config.barge_in_enabled,
            "providers": {
                "stt": self._stt.value.name if self._stt.value else self._config.stt_provider,
                "tts": self._config.tts_provider,
                "tts_active": getattr(tts, "active_name", tts.name) if tts else None,
                "vad": self._vad_name,
                "wakeword": self._wakeword_name,
                "audio": self._capture_name or self._config.audio_backend,
            },
            "ready": {
                "stt": self._stt.value is not None,
                "tts": self._tts.value is not None,
                "vad": self._active_vad is not None,
            },
            "turn_id": self._turn.id if self._turn else None,
            "utterance_id": self._playing,
        }

    async def mic_set(self, enabled: bool) -> dict[str, Any]:
        if enabled:
            await self._ensure_running()
            self._mic_enabled = True
            if self._state is VoiceState.OFF:
                self._set_state(VoiceState.IDLE, "mic_enabled")
            self._emit_mic()
            return {"enabled": True, "capture_open": self._capture_open}

        # Everything up to the await is synchronous: from here no path can want the capture.
        await self.start()
        self._mic_enabled = False
        self._wakeword_on = False
        self._cancel_session("mic_disabled")
        if self._state in (VoiceState.IDLE, VoiceState.ARMED):
            self._set_state(VoiceState.OFF, "mic_disabled")
        self._refresh_frame_mode()
        await self._sync_capture()
        self._emit_mic()
        return {"enabled": False, "capture_open": self._capture_open}

    async def wakeword_set(self, enabled: bool) -> dict[str, Any]:
        await self._ensure_running()
        if not enabled:
            self._wakeword_on = False
            if self._state is VoiceState.ARMED:
                self._set_state(self._rest_state(), "wakeword_disabled")
            self._refresh_frame_mode()
            await self._sync_capture()
            return {"enabled": False, "capture_open": self._capture_open}

        if self._wakeword_name == "null":
            raise VoiceError("invalid_request", "no wake word provider configured")
        if not self._mic_enabled:
            raise VoiceError("invalid_request", "microphone is disabled")
        await self._ctl_worker.call(self._wakeword.get)
        if not self._mic_enabled:  # turned off during the load: that decision wins
            raise VoiceError("invalid_request", "microphone is disabled")
        self._wakeword_on = True
        await self._sync_capture()
        if self._wakeword_on and self._state is VoiceState.IDLE:
            self._set_state(VoiceState.ARMED, "wakeword_enabled")
        self._refresh_frame_mode()
        return {"enabled": self._wakeword_on, "capture_open": self._capture_open}

    async def listen_start(self) -> dict[str, Any]:
        await self._ensure_running()
        if not self._mic_enabled:
            raise VoiceError("invalid_request", "microphone is disabled")
        current = self._session
        if current is not None:
            if not current.released:
                return {"turn_id": current.turn.id}
            self._cancel_session("cancelled")  # pressed again before the release settled
        was_cut = self._interrupt_turn("new_turn", settle=False)
        turn = self._begin_listening("push_to_talk", seed_ring=False)
        if was_cut:
            await self._interrupt_player()
        await self._sync_capture()
        return {"turn_id": turn.id}

    async def listen_stop(self) -> dict[str, Any]:
        session = self._session
        if session is None or session.released:
            return {"turn_id": None}
        session.released = True
        try:
            await self._sync_capture()  # push to talk: the device closes on release
        finally:
            self._listen_queue.put_control(lambda: self._finish_session(session, "released"))
        return {"turn_id": session.turn.id}

    async def listen_cancel(self) -> dict[str, Any]:
        session = self._session
        if session is None:
            return {"turn_id": None}
        self._cancel_session("cancelled")
        await self._sync_capture()
        return {"turn_id": session.turn.id}

    async def speak(
        self, turn_id: str, text: str, final: bool = False, context: VoiceContext | Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        await self._ensure_running()
        voice_context = _coerce_context(context)
        if turn_id in self._dead_turns:
            return {"ignored": True}
        turn = self._turn
        if turn is None:  # Drakter speaks without a spoken request, for example a typed message
            turn = self._new_turn(turn_id)
            self._set_state(VoiceState.WAITING, "speak")
        elif turn.id != turn_id or self._state not in (VoiceState.WAITING, VoiceState.SPEAKING):
            return {"ignored": True}

        turn.metrics.mark("text_received")
        if turn.segmenter is None:
            from voice.personality.segmenter import SentenceSegmenter

            turn.segmenter = SentenceSegmenter()
        sentences = list(turn.segmenter.feed(text))
        if final:
            sentences.extend(turn.segmenter.flush())
            turn.final = True
        queued = self._queue_sentences(turn, sentences, voice_context)
        self._maybe_complete(turn)
        return {"queued": queued}

    async def interrupt(self, reason: str = "user") -> dict[str, Any]:
        if reason not in INTERRUPT_REASONS:
            raise VoiceError("invalid_request", "unknown interrupt reason")
        if not self._interrupt_turn(reason, settle=True):
            return {"interrupted": False}
        await self._interrupt_player()
        return {"interrupted": True}

    # ---- state ----------------------------------------------------------------------------------

    def _emit(self, name: str, payload: dict[str, Any]) -> None:
        if name not in EVENTS:
            raise ValueError(f"event outside the contract: {name}")
        try:
            self._emit_event(name, payload)
        except Exception as exc:  # noqa: BLE001 - a broken listener must not stop the pipeline
            log.error("emit_failed", extra={"data": {"event": name, "error": type(exc).__name__}})

    def _emit_error(self, err: VoiceError, stage: str, turn_id: str | None = None, *, recoverable: bool | None = None) -> None:
        payload: dict[str, Any] = {
            "code": err.code,
            "stage": stage,
            "message": err.message,
            "recoverable": err.code not in _FATAL_CODES if recoverable is None else recoverable,
        }
        if turn_id is not None:
            payload["turn_id"] = turn_id
        log.warning("voice_error", extra={"data": {"code": err.code, "stage": stage}})
        self._emit("voice.error", payload)

    def _emit_mic(self) -> None:
        current = (self._mic_enabled, self._capture_open)
        if current != self._last_mic_event:
            self._last_mic_event = current
            self._emit("voice.mic_changed", {"enabled": current[0], "capture_open": current[1]})

    def _rest_state(self) -> VoiceState:
        if not self._mic_enabled:
            return VoiceState.OFF
        return VoiceState.ARMED if self._wakeword_on else VoiceState.IDLE

    def _set_state(self, state: VoiceState, reason: str | None = None) -> None:
        previous = self._state
        self._state = state
        self._refresh_frame_mode()
        if state is previous:
            return
        payload: dict[str, Any] = {"state": state.value, "previous": previous.value}
        if reason is not None:
            payload["reason"] = reason
        self._emit("voice.state_changed", payload)

    def _refresh_frame_mode(self) -> None:
        if self._closing or not self._mic_enabled:
            mode = _FrameMode.DROP
        elif self._session is not None:
            mode = _FrameMode.SESSION
        elif self._state is VoiceState.ARMED:
            mode = _FrameMode.ARMED
        elif self._state is VoiceState.SPEAKING and self._config.barge_in_enabled and self._capture_open:
            mode = _FrameMode.BARGE
        else:
            mode = _FrameMode.DROP  # half duplex: what the mic hears now is dropped
        self._frame_mode = mode

    # ---- turns ----------------------------------------------------------------------------------

    def _new_turn(self, turn_id: str | None = None) -> _Turn:
        turn_id = turn_id or str(uuid.uuid4())
        turn = _Turn(id=turn_id, metrics=TurnMetrics(turn_id))
        self._turn = turn
        return turn

    def _begin_listening(self, mode: str, *, seed_ring: bool, wake: WakeDetection | None = None) -> _Turn:
        turn = self._new_turn()
        if wake is not None:
            turn.metrics.mark("wake")
            self._emit(
                "voice.wakeword_detected", {"keyword": wake.keyword, "score": float(wake.score), "turn_id": turn.id}
            )
        turn.metrics.mark("listen_start")
        self._session = _Session(turn=turn, opened_ns=time.perf_counter_ns(), seed_ring=seed_ring)
        self._set_state(VoiceState.LISTENING, mode)
        self._emit("voice.listening_started", {"turn_id": turn.id, "mode": mode})
        return turn

    def _close_turn(self, turn: _Turn) -> None:
        """A closed turn stays known, so its late deltas are ignored."""
        self._dead_turns[turn.id] = None
        while len(self._dead_turns) > MAX_DEAD_TURNS:
            self._dead_turns.popitem(last=False)
        if turn is self._turn:
            self._turn = None
        snapshot = turn.metrics.snapshot()
        self._emit("voice.metrics", snapshot)
        if not self._closing:
            self._ctl_worker.submit(self._write_metrics, snapshot)

    def _write_metrics(self, snapshot: Mapping[str, object]) -> None:
        try:
            self._metrics_sink.write(snapshot)
        except (OSError, ValueError, TypeError) as exc:
            log.warning("metrics_write_failed", extra={"data": {"error": type(exc).__name__}})

    def _cut_turn(self, turn: _Turn) -> None:
        """Stops all work of `turn`. The player is cut by the caller, which may have to wait for it."""
        turn.stt_token.cancel()
        turn.tts_token.cancel()
        with self._synth_cond:
            self._synth_queue = deque(item for item in self._synth_queue if item.turn is not turn)
            self._unplayed.clear()
            self._synth_cond.notify_all()
        for uid in turn.outstanding:
            utterance = self._utterances.get(uid)
            if utterance is not None and not utterance.started:
                del self._utterances[uid]  # the player reports nothing for what never sounded
        turn.outstanding.clear()
        self._playing = None
        self._close_turn(turn)

    def _interrupt_turn(self, reason: str, *, settle: bool) -> bool:
        """Cuts the turn past the listening stage. False when there is none (idempotent)."""
        turn = self._turn
        if turn is None or self._session is not None:
            return False
        self._cut_turn(turn)
        if settle:
            self._set_state(self._rest_state(), "interrupted")
        self._emit("voice.playback_interrupted", {"turn_id": turn.id, "reason": reason})
        log.info("turn_interrupted", extra={"data": {"reason": reason}})
        return True

    async def _interrupt_player(self) -> None:
        player = self._player.value
        if player is not None:
            await self._ctl_worker.call(player.interrupt)

    def _discard_turn(self, turn: _Turn, err: VoiceError, stage: str) -> None:
        if turn is not self._turn:
            return
        self._emit_error(err, stage, turn.id)
        self._cut_turn(turn)
        self._set_state(self._rest_state(), "error")
        player = self._player.value
        if player is not None and not self._closing:
            self._ctl_worker.submit(player.interrupt)

    def _maybe_complete(self, turn: _Turn) -> None:
        if turn is not self._turn or not turn.final or turn.outstanding:
            return
        if turn.played:
            turn.metrics.mark("playback_end")
        self._close_turn(turn)
        self._set_state(self._rest_state(), "completed")

    def _queue_sentences(self, turn: _Turn, sentences: list[str], context: VoiceContext) -> int:
        from voice.personality.normalize import normalize_for_speech

        queued = 0
        for sentence in sentences:
            clean = normalize_for_speech(sentence)  # after the sentence forms: Markdown spans deltas
            if not clean.strip():
                continue
            utterance = _Utterance(id=str(uuid.uuid4()), turn=turn)
            with self._synth_cond:
                if len(self._synth_queue) >= MAX_SYNTH_PENDING:
                    log.warning("synth_queue_full", extra={"data": {"chars": len(clean)}})
                    continue
                self._utterances[utterance.id] = utterance
                turn.outstanding.add(utterance.id)
                self._synth_queue.append(_SynthItem(turn, utterance, clean, context))
                self._synth_cond.notify_all()
            queued += 1
        return queued

    # ---- capture --------------------------------------------------------------------------------

    def _capture_wanted(self) -> bool:
        if not self._mic_enabled or self._closing:
            return False
        session = self._session
        return self._wakeword_on or (session is not None and not session.released)

    async def _sync_capture(self) -> None:
        """Takes the device to what _capture_wanted() says, one change at a time.

        Whoever returns from here has seen the wish at that moment fulfilled: a mic_set(False)
        that arrives during an open waits for it, then closes.
        """
        async with self._capture_lock:
            while (wanted := self._capture_wanted()) != self._capture_open:
                if wanted:
                    await self._open_capture()
                else:
                    await self._close_capture()

    async def _open_capture(self) -> None:
        self._capture_epoch += 1
        epoch = self._capture_epoch

        def on_frame(frame: AudioFrame) -> None:
            if epoch == self._capture_epoch and self._frame_mode is not _FrameMode.DROP:
                self._listen_queue.put_frame(frame)

        def on_error(err: VoiceError) -> None:
            self._hop(self._on_capture_failed, err, epoch)

        def open_device() -> AudioCapture:
            if self._injected_capture is not None:
                device = self._injected_capture
            else:
                from voice.audio.backends import open_capture

                device = open_capture(self._config)
            device.start(on_frame, on_error)
            return device

        try:
            device = await self._capture_worker.call(open_device)
        except Exception as exc:  # noqa: BLE001 - any failure here means no microphone
            err = _as_voice_error(exc)
            self._fail_capture(err)
            raise err from None
        self._capture = device
        self._capture_name = device.name
        self._capture_open = True
        self._refresh_frame_mode()
        self._emit_mic()

    async def _close_capture(self) -> None:
        device = self._capture
        self._capture_epoch += 1  # late frames of this device are dropped from now on
        self._capture = None
        failure: VoiceError | None = None
        if device is not None:
            try:
                await self._capture_worker.call(device.stop)
                if device.active:
                    failure = VoiceError("audio_device", "capture still active after stop")
            except Exception as exc:  # noqa: BLE001
                failure = _as_voice_error(exc)
        self._capture_open = False
        self._refresh_frame_mode()
        self._emit_mic()
        if failure is not None:
            self._emit_error(failure, "capture", recoverable=False)
            raise failure

    def _fail_capture(self, err: VoiceError) -> None:
        """The promise after a capture failure: closed, mic off, and only the user reopens it."""
        turn = self._session.turn if self._session else None
        self._emit_error(err, "capture", turn.id if turn else None, recoverable=False)
        self._mic_enabled = False
        self._wakeword_on = False
        self._cancel_session("error")
        if self._state in (VoiceState.IDLE, VoiceState.ARMED):
            self._set_state(VoiceState.OFF, "capture_error")
        self._refresh_frame_mode()
        self._emit_mic()
        self._spawn(self._sync_capture())

    def _on_capture_failed(self, err: VoiceError, epoch: int) -> None:
        if epoch == self._capture_epoch and self._mic_enabled:
            self._fail_capture(err)

    def _cancel_session(self, reason: str) -> None:
        session = self._session
        if session is None:
            return
        session.cancelled = True
        self._session = None
        self._emit("voice.listening_stopped", {"turn_id": session.turn.id, "reason": reason})
        self._close_turn(session.turn)
        self._listen_queue.put_control(session.frames.clear)
        if self._state is VoiceState.LISTENING:
            self._set_state(self._rest_state(), reason)

    # ---- hops into the loop ---------------------------------------------------------------------

    def _hop(self, fn: Callable[..., None], *args: Any) -> None:
        """From a worker to the loop. While the loop is closing, late hops just vanish."""
        if self._closing or self._loop is None:
            return
        try:
            self._loop.call_soon_threadsafe(self._run_hop, fn, args)
        except RuntimeError:
            pass  # loop already closed

    def _run_hop(self, fn: Callable[..., None], args: tuple[Any, ...]) -> None:
        if not self._closing:
            fn(*args)

    def _spawn(self, coro: Coroutine[Any, Any, Any]) -> None:
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._task_done)

    def _task_done(self, task: asyncio.Task[Any]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            log.warning("background_task_failed", extra={"data": {"error": type(task.exception()).__name__}})

    # ---- listen thread --------------------------------------------------------------------------

    def _listen_loop(self) -> None:
        while (item := self._listen_queue.get()) is not _STOP:
            try:
                if isinstance(item, AudioFrame):
                    self._on_audio(item)
                else:
                    item()
            except Exception as exc:  # noqa: BLE001 - the thread must survive any single frame
                log.error("listen_frame_failed", extra={"data": {"error": type(exc).__name__}})

    def _on_audio(self, frame: AudioFrame) -> None:
        mode = self._frame_mode
        if mode is not self._seen_mode:
            self._enter_mode(mode)
        if mode is _FrameMode.DROP:
            return
        if mode is _FrameMode.SESSION:
            self._feed_session(frame)
            return
        self._ring.append(frame)
        if mode is _FrameMode.ARMED:
            self._feed_wakeword(frame)
        else:
            self._feed_barge_in(frame)

    def _enter_mode(self, mode: _FrameMode) -> None:
        self._seen_mode = mode
        if mode is _FrameMode.SESSION:
            return  # the session takes what the ring holds, if it was started from it
        self._ring.clear()
        self._wake_paused = False
        self._barge_frames = 0
        self._barge_fired = False
        if mode is _FrameMode.ARMED and self._wakeword.value is not None:
            self._wakeword.value.reset()
        elif mode is _FrameMode.BARGE:
            vad = self._get_vad()
            if vad is not None:
                vad.reset()

    def _feed_wakeword(self, frame: AudioFrame) -> None:
        if self._wake_paused:
            return  # detected: the ring keeps filling until the loop opens the session
        try:
            detection = self._wakeword.get().process(frame)
        except Exception as exc:  # noqa: BLE001
            self._wake_paused = True
            self._hop(self._on_wakeword_failed, _as_voice_error(exc))
            return
        if detection is not None:
            self._wake_paused = True
            self._hop(self._on_wake, detection)

    def _feed_barge_in(self, frame: AudioFrame) -> None:
        if self._barge_fired:
            return
        probability = self._vad_probability(frame)
        if probability is None or probability < self._config.barge_in_threshold:
            self._barge_frames = 0
            return
        self._barge_frames += 1
        if self._barge_frames * FRAME_MS >= self._config.barge_in_min_ms:
            self._barge_fired = True
            self._hop(self._on_barge_in, self._turn)

    def _feed_session(self, frame: AudioFrame) -> None:
        session = self._session
        if session is None or session.cancelled or session.done:
            return
        if frame.captured_ns < session.opened_ns and not session.seed_ring:
            return
        if not session.begun:
            session.begun = True
            vad = self._get_vad()
            if vad is None:
                self._finish_session(session, "error")
                return
            vad.reset()
            if session.seed_ring:
                session.frames.extend(f.pcm for f in self._ring)
            self._ring.clear()

        probability = self._vad_probability(frame)
        if probability is None:
            self._finish_session(session, "error")
            return
        index = len(session.frames)
        session.frames.append(frame.pcm)
        if probability >= self._config.vad_threshold:
            if session.first_voiced is None:
                session.first_voiced = index
                session.turn.metrics.mark("speech_start", frame.captured_ns)
                self._hop(self._on_speech_started, session.turn)
            session.last_voiced = index
            session.last_voiced_ns = frame.captured_ns
            session.silent_frames = 0
        elif session.first_voiced is not None:
            session.silent_frames += 1
            if session.silent_frames * FRAME_MS >= self._config.vad_silence_ms:
                self._finish_session(session, "silence")
                return
        if len(session.frames) * FRAME_MS >= self._config.max_utterance_s * 1000:
            self._finish_session(session, "max_duration")

    def _finish_session(self, session: _Session, reason: str) -> None:
        if session.done or session.cancelled:
            return
        session.done = True
        audio: Pcm | None = None
        if session.first_voiced is not None:
            session.turn.metrics.mark("speech_end", session.last_voiced_ns)
            self._hop(self._on_speech_ended, session.turn)
            preroll = self._ring.maxlen or 0
            low = max(0, session.first_voiced - preroll)
            high = min(len(session.frames), session.last_voiced + 1 + preroll)
            audio = np.concatenate(session.frames[low:high]).astype(np.float32, copy=False)
        elif reason != "error":
            reason = "no_speech"
        session.frames.clear()
        self._hop(self._on_session_done, session, reason, audio)

    def _get_vad(self) -> VADProvider | None:
        """The configured VAD or, if it cannot run, the energy one. The fallback lives here."""
        if self._active_vad is not None or self._vad_is_fallback:
            return self._active_vad
        try:
            self._active_vad = self._vad.get()
            self._hop(self._set_vad_name, self._active_vad.name)
        except Exception as exc:  # noqa: BLE001 - whatever failed, listening can go on without it
            self._degrade_vad(_as_voice_error(exc))
        return self._active_vad

    def _degrade_vad(self, err: VoiceError) -> None:
        self._active_vad = None
        if self._vad_is_fallback:
            self._hop(self._emit_error, err, "vad", None)
            return
        self._vad_is_fallback = True
        try:
            fallback = registry.build_vad(replace(self._config, vad_provider="energy"))
            fallback.load()
        except Exception as exc:  # noqa: BLE001
            self._hop(self._emit_error, _as_voice_error(exc), "vad", None)
            return
        self._active_vad = fallback
        self._hop(self._set_vad_name, fallback.name)
        degraded = VoiceError(err.code, f"VAD degraded to energy: {err.message}")
        self._hop(lambda: self._emit_error(degraded, "vad", recoverable=True))

    def _vad_probability(self, frame: AudioFrame) -> float | None:
        vad = self._get_vad()
        if vad is None:
            return None
        try:
            return float(vad.process(frame))
        except Exception as exc:  # noqa: BLE001
            self._degrade_vad(_as_voice_error(exc))
            vad = self._active_vad
            return float(vad.process(frame)) if vad is not None else None

    # ---- listen results, on the loop ------------------------------------------------------------

    def _set_vad_name(self, name: str) -> None:
        self._vad_name = name

    def _on_wake(self, detection: WakeDetection) -> None:
        if self._state is VoiceState.ARMED and self._wakeword_on:
            self._begin_listening("wakeword", seed_ring=True, wake=detection)

    def _on_wakeword_failed(self, err: VoiceError) -> None:
        self._emit_error(err, "wakeword", recoverable=True)
        self._wakeword_on = False
        if self._state is VoiceState.ARMED:
            self._set_state(self._rest_state(), "wakeword_error")
        self._spawn(self._sync_capture())

    def _on_barge_in(self, turn: _Turn | None) -> None:
        if turn is None or turn is not self._turn or self._state is not VoiceState.SPEAKING:
            return
        self._interrupt_turn("barge_in", settle=False)
        self._begin_listening("wakeword", seed_ring=True)  # barge-in needs the capture wake word keeps open
        self._spawn(self._interrupt_player())

    def _on_speech_started(self, turn: _Turn) -> None:
        if turn is self._turn:
            self._emit("voice.speech_started", {"turn_id": turn.id})

    def _on_speech_ended(self, turn: _Turn) -> None:
        if turn is self._turn:
            self._emit("voice.speech_ended", {"turn_id": turn.id})

    def _on_session_done(self, session: _Session, reason: str, audio: Pcm | None) -> None:
        if session is not self._session:
            return
        self._session = None
        turn = session.turn
        self._emit("voice.listening_stopped", {"turn_id": turn.id, "reason": reason})
        if audio is None:
            self._close_turn(turn)
            self._set_state(self._rest_state(), reason)
        else:
            turn.metrics.note("audio_s", round(audio.size / SAMPLE_RATE, 3))
            self._set_state(VoiceState.TRANSCRIBING, reason)
            self._stt_worker.submit(self._run_stt, turn, audio)
        self._spawn(self._sync_capture())

    # ---- STT ------------------------------------------------------------------------------------

    def _run_stt(self, turn: _Turn, audio: Pcm) -> None:
        token = turn.stt_token
        if token.cancelled:
            return
        try:
            stt = self._stt.get()
            turn.metrics.note("stt_provider", stt.name)
            turn.metrics.note("stt_model", self._config.stt_model)
            turn.metrics.mark("stt_start")
            parts: list[str] = []
            for segment in stt.transcribe(audio, language=self._config.stt_language or None, cancel=token):
                if token.cancelled:
                    return
                if not parts:
                    turn.metrics.mark("stt_first_segment")
                parts.append(segment.text)
                self._hop(self._on_partial, turn, " ".join(parts))
            if token.cancelled:
                return
            turn.metrics.mark("stt_end")
            self._hop(self._on_transcribed, turn, " ".join(parts), round(audio.size * 1000 / SAMPLE_RATE))
        except Exception as exc:  # noqa: BLE001
            err = _as_voice_error(exc)
            if err.code != "cancelled" and not token.cancelled:
                self._hop(self._on_stt_failed, turn, err)

    def _on_partial(self, turn: _Turn, text: str) -> None:
        if turn is self._turn and self._state is VoiceState.TRANSCRIBING:
            self._emit("voice.transcription_partial", {"turn_id": turn.id, "text": text})

    def _on_transcribed(self, turn: _Turn, text: str, audio_ms: int) -> None:
        if turn is not self._turn or self._state is not VoiceState.TRANSCRIBING:
            return
        if not text.strip():  # the VAD heard something the STT did not: nothing to answer
            self._close_turn(turn)
            self._set_state(self._rest_state(), "empty_transcript")
            return
        self._set_state(VoiceState.WAITING, "transcribed")
        self._emit(
            "voice.transcription_completed",
            {"turn_id": turn.id, "text": text, "language": self._config.stt_language, "audio_ms": audio_ms},
        )
        log.info("transcribed", extra={"data": {"chars": len(text), "audio_ms": audio_ms}})

    def _on_stt_failed(self, turn: _Turn, err: VoiceError) -> None:
        if turn is not self._turn:
            return
        self._emit_error(err, "stt", turn.id)
        self._close_turn(turn)
        self._set_state(self._rest_state(), "error")

    # ---- TTS ------------------------------------------------------------------------------------

    def _tts_loop(self) -> None:
        while True:
            with self._synth_cond:
                while not self._synth_stop and not (
                    self._synth_queue and len(self._unplayed) < MAX_SYNTH_AHEAD
                ):
                    self._synth_cond.wait()
                if self._synth_stop:
                    return
                item = self._synth_queue.popleft()
                self._unplayed.add(item.utterance.id)
            self._synthesize(item)

    def _synthesize(self, item: _SynthItem) -> None:
        turn, utterance = item.turn, item.utterance
        token = turn.tts_token
        if token.cancelled:
            return
        stage = "tts"
        try:
            tts = self._tts.get()
            segment = self._personality.get().plan(item.sentence, item.context, tts.capabilities)
            stage = "playback"
            player = self._player.get()
            stage = "tts"
            if token.cancelled or not segment.text.strip():
                self._hop(self._on_utterance_empty, utterance)
                return
            turn.metrics.mark("tts_start")
            audio_s = 0.0
            began = time.perf_counter()
            for chunk in tts.synthesize(segment.text, segment.params, token):
                turn.synth_s += time.perf_counter() - began
                if token.cancelled:
                    return
                if audio_s == 0.0:
                    utterance.provider = getattr(tts, "active_name", tts.name)
                    turn.metrics.note("tts_provider", utterance.provider)
                    turn.metrics.mark("tts_first_audio")
                stage = "playback"
                player.enqueue(utterance.id, chunk, segment.params.gain)
                stage = "tts"
                # Cancel precedes the player cut on the loop side, so either this check sees it
                # or that cut comes after this enqueue. No stale chunk can survive both.
                if token.cancelled:
                    player.interrupt()
                    return
                audio_s += chunk.pcm.size / chunk.sample_rate
                turn.audio_s += chunk.pcm.size / chunk.sample_rate
                began = time.perf_counter()
            if token.cancelled:
                return
            if audio_s == 0.0:
                self._hop(self._on_utterance_empty, utterance)
                return
            turn.metrics.note("tts_audio_s", round(turn.audio_s, 3))
            turn.metrics.note("tts_synth_s", round(turn.synth_s, 3))
            stage = "playback"
            player.add_silence(utterance.id, segment.params.pause_after_ms)
            player.finish(utterance.id)
            self._hop(self._watch_playback, utterance)
        except Exception as exc:  # noqa: BLE001
            err = _as_voice_error(exc)
            if err.code != "cancelled" and not token.cancelled:
                self._hop(self._discard_turn, turn, err, stage)

    def _release_synth_slot(self, utterance_id: str) -> None:
        with self._synth_cond:
            self._unplayed.discard(utterance_id)
            self._synth_cond.notify_all()

    def _on_utterance_empty(self, utterance: _Utterance) -> None:
        self._release_synth_slot(utterance.id)
        self._utterances.pop(utterance.id, None)
        utterance.turn.outstanding.discard(utterance.id)
        self._maybe_complete(utterance.turn)

    def _watch_playback(self, utterance: _Utterance) -> None:
        """The player stays silent if the sink dies before the first block: nothing else would end the turn."""
        if self._loop is not None:
            self._loop.call_later(PLAYBACK_START_TIMEOUT_S, self._check_playback_began, utterance)

    def _check_playback_began(self, utterance: _Utterance) -> None:
        if not self._closing and not utterance.started and utterance.id in self._utterances:
            err = VoiceError("audio_device", "playback did not start")
            self._discard_turn(utterance.turn, err, "playback")

    # ---- PlayerListener: player thread ----------------------------------------------------------

    def on_playback_started(self, utterance_id: str, started_ns: int) -> None:
        self._hop(self._on_started, utterance_id, started_ns)

    def on_level(self, utterance_id: str, level: float, position_ms: int) -> None:
        self._hop(self._on_level, utterance_id, level, position_ms)

    def on_playback_stopped(self, utterance_id: str, reason: StopReason, played_ms: int) -> None:
        self._hop(self._on_stopped, utterance_id, reason, played_ms)

    def _on_started(self, utterance_id: str, started_ns: int) -> None:
        utterance = self._utterances.get(utterance_id)
        if utterance is None or utterance.turn is not self._turn:
            return
        turn = utterance.turn
        utterance.started = True
        turn.played = True
        self._playing = utterance_id
        turn.metrics.mark("playback_start", started_ns)
        if self._state is VoiceState.WAITING:  # the first real audio, not the first text
            self._set_state(VoiceState.SPEAKING, "playback_started")
        self._emit(
            "voice.playback_started",
            {"turn_id": turn.id, "utterance_id": utterance_id, "provider": utterance.provider},
        )

    def _on_level(self, utterance_id: str, level: float, position_ms: int) -> None:
        utterance = self._utterances.get(utterance_id)
        if utterance is not None and utterance.turn is self._turn:
            self._emit(
                "voice.playback_level",
                {"utterance_id": utterance_id, "level": float(level), "position_ms": int(position_ms)},
            )

    def _on_stopped(self, utterance_id: str, reason: StopReason, played_ms: int) -> None:
        self._release_synth_slot(utterance_id)
        utterance = self._utterances.pop(utterance_id, None)
        if utterance is None:
            return
        turn = utterance.turn
        if self._playing == utterance_id:
            self._playing = None
        if utterance.started:
            self._emit(
                "voice.playback_stopped",
                {"turn_id": turn.id, "utterance_id": utterance_id, "reason": reason, "played_ms": int(played_ms)},
            )
        if turn is not self._turn:
            return
        if reason == "error":
            self._discard_turn(turn, VoiceError("audio_device", "playback failed"), "playback")
            return
        turn.outstanding.discard(utterance_id)
        self._maybe_complete(turn)
