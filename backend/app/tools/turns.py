"""Active turn and session taint.

Hermes sends no session identity over MCP (F19). The backend starts every turn, so it admits
one at a time and attributes each MCP call to it. Taint lives here, per session, and does not
expire: context compression erases provenance, so it can never be considered clean again.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID


class TurnBusyError(RuntimeError):
    """Another turn is already active."""


@dataclass(frozen=True, slots=True)
class ActiveTurn:
    session_id: UUID
    turn_id: UUID


class TurnTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: ActiveTurn | None = None
        self._in_flight = 0
        self._tainted: set[UUID] = set()

    def begin(self, session_id: UUID, turn_id: UUID) -> ActiveTurn:
        """Admit a turn. Raises ``TurnBusyError`` if one is active or a tool still runs.

        Interrupting Hermes does not cancel an MCP call: the handler keeps running here, and a
        new turn must not overlap it.
        """
        with self._lock:
            if self._active is not None or self._in_flight:
                raise TurnBusyError("another turn is active")
            self._active = ActiveTurn(session_id=session_id, turn_id=turn_id)
            return self._active

    def end(self, turn_id: UUID) -> None:
        """Close ``turn_id``. Idempotent; it never closes a different turn."""
        with self._lock:
            if self._active is not None and self._active.turn_id == turn_id:
                self._active = None

    @contextmanager
    def turn(self, session_id: UUID, turn_id: UUID) -> Iterator[ActiveTurn]:
        active = self.begin(session_id, turn_id)
        try:
            yield active
        finally:
            self.end(turn_id)

    @contextmanager
    def tool_call(self) -> Iterator[None]:
        with self._lock:
            self._in_flight += 1
        try:
            yield
        finally:
            with self._lock:
                self._in_flight -= 1

    def active(self) -> ActiveTurn | None:
        with self._lock:
            return self._active

    def is_active(self, session_id: UUID, turn_id: UUID) -> bool:
        with self._lock:
            active = self._active
            return (
                active is not None
                and active.session_id == session_id
                and active.turn_id == turn_id
            )

    def mark_tainted(self, session_id: UUID) -> None:
        with self._lock:
            self._tainted.add(session_id)

    def is_tainted(self, session_id: UUID) -> bool:
        with self._lock:
            return session_id in self._tainted
