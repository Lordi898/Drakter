"""Queued player: one thread, utterances in order, instant cancellation, mouth levels.

Rules worth knowing (see CONTRACT.md for the interface):
- Audio is written to the sink in blocks of BLOCK_MS. Writes are paced against the wall clock so
  the sink never holds more than about LEAD_S of audio ahead: that keeps levels in sync with
  sound and keeps interrupt() fine-grained even when the OS pipe is large.
- `position_ms` = audio written so far - output_latency_ms (never below 0): the sound the user
  is hearing now. Written audio runs at most LEAD_S + one block ahead of the speaker.
- Level: RMS of the block (after gain and clipping), curve sqrt(min(1, rms / LEVEL_FULL_SCALE)),
  then one-pole smoothing per block (fast attack, slower release). Emitted at most level_hz per
  second. One last level of 0.0 precedes every on_playback_stopped so the mouth closes.
- on_playback_started fires with the first real audio of an utterance. An utterance that never
  produced audio (only silence, or discarded) emits neither started nor stopped.
- "completed" fires after finish() and after the sink drained. If another item is already
  queued the sink is not drained (no gap between sentences) and "completed" fires when the last
  block is written, up to the sink buffer earlier than the sound ends.
- interrupt() bumps a generation counter: anything the thread was doing for an older generation
  is dropped and no callback of that generation fires after interrupt() emitted its events.
- Ids dropped by interrupt() or by a sink error are ignored if more audio for them arrives later.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from voice.contracts import Pcm, PcmChunk, PlayerListener, StopReason

log = logging.getLogger(__name__)

BLOCK_MS = 30
LEAD_S = 0.06
LEVEL_FULL_SCALE = 0.3  # speech RMS rarely exceeds this; maps to level 1.0
_ATTACK = 0.7
_RELEASE = 0.3
_DEAD_MAX = 256


@dataclass
class _State:
    started: bool = False
    written_s: float = 0.0
    rate: int = 0
    level: float = 0.0


@dataclass
class _Item:
    kind: str  # "audio" | "silence" | "finish"
    uid: str
    pcm: Pcm | None = None
    rate: int = 0
    gain: float = 1.0
    ms: int = 0


class Player:
    def __init__(self, sink, listener: PlayerListener, *, level_hz: int, output_latency_ms: int) -> None:  # noqa: ANN001
        self._sink = sink
        self._listener = listener
        self._level_period = 1.0 / level_hz if level_hz > 0 else float("inf")
        self._latency_ms = max(0, output_latency_ms)
        self._cond = threading.Condition()
        self._emit_lock = threading.RLock()
        self._queue: deque[_Item] = deque()
        self._states: dict[str, _State] = {}
        self._dead: OrderedDict[str, None] = OrderedDict()
        self._gen = 0
        self._closed = False
        self._thread: threading.Thread | None = None
        # touched only by the player thread (and reset by it)
        self._opened_rate: int | None = None
        self._dirty = False  # set under _cond by interrupt/error: sink must be closed before reuse
        self._anchor = 0.0
        self._anchor_w = 0.0
        self._paced = False
        self._last_level_at = 0.0

    # ---- public API -------------------------------------------------------------------------

    def start(self) -> None:
        with self._cond:
            if self._thread is not None or self._closed:
                return
            self._thread = threading.Thread(target=self._run, name="voice-player", daemon=True)
            self._thread.start()

    def enqueue(self, utterance_id: str, chunk: PcmChunk, gain: float = 1.0) -> None:
        pcm = np.asarray(chunk.pcm, dtype=np.float32).reshape(-1)
        if pcm.size == 0:
            return
        self._put(_Item("audio", utterance_id, pcm=pcm, rate=chunk.sample_rate, gain=gain))

    def add_silence(self, utterance_id: str, ms: int) -> None:
        if ms > 0:
            self._put(_Item("silence", utterance_id, ms=ms))

    def finish(self, utterance_id: str) -> None:
        self._put(_Item("finish", utterance_id))

    def interrupt(self) -> tuple[str, ...]:
        """Cuts sound now, drops everything, returns the affected utterance ids."""
        with self._cond:
            return self._drop_all_locked("interrupted", abort_sink=True)

    def close(self) -> None:
        with self._cond:
            if self._closed:
                return
            self._closed = True
            thread = self._thread
            self._drop_all_locked("interrupted", abort_sink=True)
            self._cond.notify_all()
        if thread is not None and thread is not threading.current_thread():
            thread.join(5.0)
        try:
            self._sink.close()
        except Exception:
            log.exception("sink close failed")

    # ---- shared bookkeeping -----------------------------------------------------------------

    def _put(self, item: _Item) -> None:
        with self._cond:
            if self._closed or item.uid in self._dead:
                return
            self._states.setdefault(item.uid, _State())
            self._queue.append(item)
            self._cond.notify_all()

    def _drop_all_locked(self, reason: StopReason, *, abort_sink: bool) -> tuple[str, ...]:
        """Caller holds _cond. Bumps the generation, clears everything and emits the stops."""
        self._gen += 1
        ids = tuple(self._states)
        started = [(u, s) for u, s in self._states.items() if s.started]
        for u in ids:
            self._dead[u] = None
        while len(self._dead) > _DEAD_MAX:
            self._dead.popitem(last=False)
        self._states.clear()
        self._queue.clear()
        self._dirty = True
        if abort_sink:
            try:
                self._sink.abort()
            except Exception:
                log.exception("sink abort failed")
        self._cond.notify_all()
        # Emit outside the condition lock only for ordering with the player thread: the
        # emit lock serialises with any callback the thread is running right now.
        if started:
            self._cond.release()
            try:
                with self._emit_lock:
                    for uid, st in started:
                        self._safe(self._listener.on_level, uid, 0.0, self._pos_ms(st))
                        self._safe(self._listener.on_playback_stopped, uid, reason, self._played_ms(st))
            finally:
                self._cond.acquire()
        return ids

    @staticmethod
    def _safe(fn: Callable[..., None], *args: object) -> None:
        try:
            fn(*args)
        except Exception:  # a listener must never kill the player
            log.exception("player listener failed")

    def _pos_ms(self, st: _State) -> int:
        return max(0, int(st.written_s * 1000) - self._latency_ms)

    def _played_ms(self, st: _State) -> int:
        return self._pos_ms(st)

    def _emit(self, gen: int, fn: Callable[..., None], *args: object) -> bool:
        """Runs a callback only if no interrupt happened since `gen`. Returns False if dropped."""
        with self._emit_lock:
            if self._gen != gen:
                return False
            self._safe(fn, *args)
            return True

    # ---- player thread ----------------------------------------------------------------------

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._queue and not self._closed:
                    self._cond.wait()
                if self._closed:
                    return
                item = self._queue.popleft()
                gen = self._gen
            try:
                self._process(item, gen)
            except Exception as exc:
                log.warning("player sink error: %s", exc)
                self._fail(gen)

    def _fail(self, gen: int) -> None:
        with self._cond:
            if self._gen != gen:
                return  # interrupt() got there first and the error is just its aftermath
            self._drop_all_locked("error", abort_sink=True)

    def _ensure_sink(self, rate: int, gen: int) -> bool:
        with self._cond:
            if self._gen != gen:
                return False
            dirty, self._dirty = self._dirty, False
        if dirty and self._opened_rate is not None:
            self._sink.close()
            self._opened_rate = None
            self._paced = False
        if self._opened_rate == rate:
            return True
        if self._opened_rate is not None:  # sample rate changed: let the old audio finish
            self._sink.drain()
            self._sink.close()
            self._opened_rate = None
        if self._gen != gen:
            return False
        self._sink.open(rate)
        self._opened_rate = rate
        self._paced = False
        return True

    def _process(self, item: _Item, gen: int) -> None:
        with self._cond:
            st = self._states.get(item.uid)
            if st is None or self._gen != gen:
                return
        if item.kind == "finish":
            self._finish(item.uid, st, gen)
            return
        if item.kind == "audio":
            assert item.pcm is not None
            self._play(item.uid, st, item.pcm, item.rate, item.gain, gen)
        else:
            rate = st.rate or self._opened_rate or 16_000
            self._play(item.uid, st, np.zeros(rate * item.ms // 1000, dtype=np.float32), rate, 1.0, gen, silent=True)

    def _play(self, uid: str, st: _State, pcm: Pcm, rate: int, gain: float, gen: int, silent: bool = False) -> None:
        if pcm.size == 0 or not self._ensure_sink(rate, gen):
            return
        st.rate = rate
        step = max(1, rate * BLOCK_MS // 1000)
        for i in range(0, pcm.size, step):
            block = pcm[i : i + step]
            if gain != 1.0:
                block = np.clip(block * gain, -1.0, 1.0)
            if not silent and not st.started:
                if not self._emit_start(uid, st, gen):
                    return
            if not self._pace(st, gen):
                return
            self._sink.write(block)
            if self._gen != gen:
                return
            st.written_s += block.size / rate
            self._anchor_w += block.size / rate
            self._level(uid, st, block, gen)

    def _emit_start(self, uid: str, st: _State, gen: int) -> bool:
        with self._emit_lock:
            with self._cond:
                if self._gen != gen:
                    return False
                st.started = True
            self._safe(self._listener.on_playback_started, uid, time.perf_counter_ns())
        return True

    def _pace(self, st: _State, gen: int) -> bool:
        """Waits so written audio does not run more than LEAD_S ahead of the wall clock."""
        now = time.monotonic()
        if not self._paced or now - self._anchor > self._anchor_w:  # first block or underrun
            self._anchor, self._anchor_w, self._paced = now, 0.0, True
        with self._cond:
            while True:
                if self._gen != gen:
                    return False
                wait = self._anchor_w - LEAD_S - (time.monotonic() - self._anchor)
                if wait <= 0:
                    return True
                self._cond.wait(wait)

    def _level(self, uid: str, st: _State, block: Pcm, gen: int) -> None:
        rms = float(np.sqrt(np.mean(np.square(block, dtype=np.float32)))) if block.size else 0.0
        raw = min(1.0, rms / LEVEL_FULL_SCALE) ** 0.5
        st.level += (raw - st.level) * (_ATTACK if raw > st.level else _RELEASE)
        now = time.monotonic()
        if now - self._last_level_at < self._level_period:
            return
        self._last_level_at = now
        self._emit(gen, self._listener.on_level, uid, round(st.level, 4), self._pos_ms(st))

    def _finish(self, uid: str, st: _State, gen: int) -> None:
        with self._cond:
            more = bool(self._queue)
        if not more and self._opened_rate is not None:
            self._sink.drain()
            if self._gen != gen:
                return
            self._sink.close()
            self._opened_rate = None
            self._paced = False
        with self._emit_lock:
            with self._cond:
                if self._gen != gen:
                    return
                self._states.pop(uid, None)
            if st.started:
                self._safe(self._listener.on_level, uid, 0.0, int(st.written_s * 1000))
                self._safe(self._listener.on_playback_stopped, uid, "completed", int(st.written_s * 1000))
