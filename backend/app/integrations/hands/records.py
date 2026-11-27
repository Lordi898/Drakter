"""What the model saw this turn: captures (`ShotRecord`) and window reads (`ReadRecord`), CONTRACT §8.2.

In memory only, per turn. A record goes stale when the focus changes, a window moves or closes, or the
user clicks in a guide (`invalidate_turn_views`). Pixels are never kept: a zoom captures again.
Thread-safe: handlers approved through the confirmation pipeline run in a worker thread.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final
from uuid import UUID

from drakter_contracts.floating import LogicalRect
from drakter_contracts.hands_ipc import AtspiControl, HEvtWindowsChanged

MAX_SHOTS_PER_TURN: Final = 8
MAX_SHOTS_TOTAL_PER_TURN: Final = 30
MAX_SHOTS_PER_SECOND: Final = 4
MAX_READS_PER_TURN: Final = 8
MAX_TURNS: Final = 16
_TURN_TTL_S: Final = 3600.0

_lock = threading.RLock()
_epoch = 0


def _bump() -> None:
    global _epoch
    with _lock:
        _epoch += 1


def current_epoch() -> int:
    return _epoch


@dataclass(frozen=True, slots=True)
class ShotRecord:
    shot_id: UUID
    turn_id: UUID
    origin: tuple[int, int]
    scale_to_logical: float
    window_id: str | None
    frame: LogicalRect | None
    taken_at: datetime
    width: int
    height: int
    epoch: int = field(default_factory=current_epoch)

    @property
    def stale(self) -> bool:
        return self.epoch != _epoch

    def to_logical(self, x: float, y: float) -> tuple[float, float]:
        return self.origin[0] + x * self.scale_to_logical, self.origin[1] + y * self.scale_to_logical


@dataclass(frozen=True, slots=True)
class ReadRecord:
    read_id: UUID
    turn_id: UUID
    window_id: str
    frame: LogicalRect
    controls: tuple[AtspiControl, ...]
    epoch: int = field(default_factory=current_epoch)

    @property
    def stale(self) -> bool:
        return self.epoch != _epoch

    def by_id(self) -> dict[int, AtspiControl]:
        return {c.id: c for c in self.controls}


@dataclass(slots=True)
class _Turn:
    shots: OrderedDict[UUID, ShotRecord] = field(default_factory=OrderedDict)
    reads: OrderedDict[UUID, ReadRecord] = field(default_factory=OrderedDict)
    taken: int = 0
    touched: float = field(default_factory=time.monotonic)


_turns: OrderedDict[UUID, _Turn] = OrderedDict()
_recent_shots: deque[float] = deque(maxlen=MAX_SHOTS_PER_SECOND)


def _turn(turn_id: UUID) -> _Turn:
    now = time.monotonic()
    for tid in [t for t, v in _turns.items() if now - v.touched > _TURN_TTL_S]:
        _turns.pop(tid, None)
    t = _turns.get(turn_id)
    if t is None:
        t = _turns[turn_id] = _Turn()
        while len(_turns) > MAX_TURNS:
            _turns.popitem(last=False)
    t.touched = now
    _turns.move_to_end(turn_id)
    return t


def shot_allowed(turn_id: UUID) -> bool:
    """4 per second (all turns) and 30 per turn. Counts the attempt when allowed."""
    with _lock:
        now = time.monotonic()
        if len(_recent_shots) == MAX_SHOTS_PER_SECOND and now - _recent_shots[0] < 1.0:
            return False
        t = _turn(turn_id)
        if t.taken >= MAX_SHOTS_TOTAL_PER_TURN:
            return False
        t.taken += 1
        _recent_shots.append(now)
        return True


def save_shot(rec: ShotRecord) -> None:
    with _lock:
        t = _turn(rec.turn_id)
        t.shots[rec.shot_id] = rec
        while len(t.shots) > MAX_SHOTS_PER_TURN:
            t.shots.popitem(last=False)


def save_read(rec: ReadRecord) -> None:
    with _lock:
        t = _turn(rec.turn_id)
        t.reads[rec.read_id] = rec
        while len(t.reads) > MAX_READS_PER_TURN:
            t.reads.popitem(last=False)


# ── CONTRACT §8.1 bis ────────────────────────────────────────────────────────
def latest_shot(turn_id: UUID) -> ShotRecord | None:
    with _lock:
        t = _turns.get(turn_id)
        return next(reversed(t.shots.values()), None) if t and t.shots else None


def shot_record(turn_id: UUID, shot_id: UUID) -> ShotRecord | None:
    with _lock:
        t = _turns.get(turn_id)
        return t.shots.get(shot_id) if t else None


def find_shot(shot_id: UUID) -> ShotRecord | None:
    """Any turn: an approved plan runs in a context of its own (permissions/wiring.py)."""
    with _lock:
        for t in _turns.values():
            if shot_id in t.shots:
                return t.shots[shot_id]
    return None


def read_record(read_id: UUID) -> ReadRecord | None:
    with _lock:
        for t in _turns.values():
            if read_id in t.reads:
                return t.reads[read_id]
    return None


def latest_read(turn_id: UUID) -> ReadRecord | None:
    with _lock:
        t = _turns.get(turn_id)
        return next(reversed(t.reads.values()), None) if t and t.reads else None


def invalidate_turn_views(turn_id: UUID) -> None:
    """After a guide click (B2): the screen changed, so every capture and read so far is stale."""
    _bump()


def purge_turn(turn_id: UUID) -> None:
    """At the end of a turn."""
    with _lock:
        _turns.pop(turn_id, None)


# ── helper events ────────────────────────────────────────────────────────────
def _on_focus(_evt: Any) -> None:
    _bump()


def _on_windows(evt: Any) -> None:
    if isinstance(evt, HEvtWindowsChanged) and evt.reason in ("geometry", "closed", "monitors", "workspace"):
        _bump()


def attach(client: Any) -> None:
    client.on_event("focus.changed", _on_focus)
    client.on_event("windows.changed", _on_windows)
