"""StatusArbiter: the only producer of `agent.status_changed` (voice v2, V-28).

Two sources feed it, `agent` (AgentRuntime) and `voice` (VoiceOrchestrator). Each source has a
resting state plus, optionally, a transient one (`error`, `interrupted`, `success`) that expires on
its own. The character shows the highest-priority state of all, and every state is held at least
`MIN_HOLD_S` so it can be seen. Jobs do not feed the character.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Final, Literal
from uuid import UUID

from drakter_contracts.events import AgentState, AgentStatusChanged

from app.events.hub import EventHub

logger = logging.getLogger("drakter.agent.status")

CharacterState = AgentState
StatusPayload = AgentStatusChanged
Source = Literal["agent", "voice"]

MIN_HOLD_S: Final = 0.35
TRANSIENT_S: Final[dict[AgentState, float]] = {
    AgentState.ERROR: 2.0,
    AgentState.INTERRUPTED: 0.8,
    AgentState.SUCCESS: 1.2,
}
# Highest first.
PRIORITY: Final[tuple[AgentState, ...]] = (
    AgentState.OFFLINE,
    AgentState.ERROR,
    AgentState.INTERRUPTED,
    AgentState.SPEAKING,
    AgentState.EXECUTING,
    AgentState.THINKING,
    AgentState.LISTENING,
    AgentState.SUCCESS,
    AgentState.IDLE,
)
_RANK: Final = {state: rank for rank, state in enumerate(PRIORITY)}
# A new activity of a source ends its own transient; idle/offline do not.
_ACTIVE: Final = frozenset(
    {AgentState.LISTENING, AgentState.THINKING, AgentState.SPEAKING, AgentState.EXECUTING}
)


@dataclass(slots=True)
class _Entry:
    state: AgentState
    turn_id: UUID | None
    reason: str | None
    until: float | None = None  # monotonic deadline of a transient


class StatusArbiter:
    def __init__(self, hub: EventHub) -> None:
        self._hub = hub
        self._base: dict[str, _Entry] = {}
        self._transient: dict[str, _Entry] = {}
        self.current: StatusPayload = AgentStatusChanged(state=AgentState.OFFLINE)
        self._shown_at = 0.0
        self._timer: asyncio.TimerHandle | None = None

    def signal(
        self,
        source: Source,
        state: CharacterState | None,
        *,
        turn_id: UUID | None = None,
        reason: str | None = None,
    ) -> None:
        """Never raises: a status hiccup must not break a turn."""
        try:
            self._signal(source, state, turn_id, reason)
        except Exception as exc:  # noqa: BLE001
            logger.warning("status signal failed", extra={"event": "status_failed", "kind": type(exc).__name__})

    def _signal(self, source: str, state: AgentState | None, turn_id: UUID | None, reason: str | None) -> None:
        if state is None:
            self._base.pop(source, None)
        elif state in TRANSIENT_S:
            self._base.pop(source, None)
            until = time.monotonic() + TRANSIENT_S[state]
            self._transient[source] = _Entry(state, turn_id, reason, until)
        else:
            if state in _ACTIVE:
                self._transient.pop(source, None)
            self._base[source] = _Entry(state, turn_id, reason)
        # A fresh end-of-turn (reason) is always worth publishing, even with the same state.
        self._evaluate(force=reason is not None)

    def _winner(self) -> _Entry:
        now = time.monotonic()
        for source, entry in list(self._transient.items()):
            if entry.until is not None and entry.until <= now:
                del self._transient[source]
        candidates = [*self._base.values(), *self._transient.values()]
        if not candidates:
            return _Entry(AgentState.IDLE, None, None)
        return min(candidates, key=lambda e: _RANK[e.state])

    def _evaluate(self, *, force: bool = False) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        winner = self._winner()
        now = time.monotonic()
        changed = winner.state != self.current.state
        if changed or (force and (winner.turn_id, winner.reason) != (self.current.turn_id, self.current.reason)):
            wait = self._shown_at + MIN_HOLD_S - now
            if wait > 0 and changed:
                self._schedule(wait)
                return
            self._publish(winner, now)
        self._schedule_expiry(now)

    def _publish(self, winner: _Entry, now: float) -> None:
        previous = self.current.state
        self.current = AgentStatusChanged(
            state=winner.state, previous=previous, turn_id=winner.turn_id, reason=winner.reason
        )
        self._shown_at = now
        self._hub.publish(
            "agent.status_changed",
            self.current,
            correlation_id=str(winner.turn_id) if winner.turn_id else None,
        )

    def _schedule_expiry(self, now: float) -> None:
        deadlines = [e.until for e in self._transient.values() if e.until is not None]
        if deadlines:
            self._schedule(max(0.0, min(deadlines) - now) + 0.001)

    def _schedule(self, delay: float) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no loop (scripts): the next signal re-evaluates
        self._timer = loop.call_later(delay, self._evaluate)
