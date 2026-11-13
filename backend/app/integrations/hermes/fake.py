"""Deterministic provider with no network: lets the GUI work without a key.

Triggers inside the message text: `fake:tool` runs get_system_status through the real
registry, `fake:slow` slows the reply down, `fake:fail` ends the turn with an error,
`fake:tags` answers with expression tags cut across deltas (and in the terminal text).
A steer is accepted between deltas; its text decides: `fake:reject` refuses it and
`fake:pending` accepts it but leaves it unconsumed (`pending_steer`).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any, Final
from uuid import UUID, uuid4

from drakter_contracts.errors import ErrorCode

from app.integrations.hermes.events import (
    AgentEvent,
    MessageDelta,
    Steered,
    Thinking,
    ToolCompleted,
    ToolStarted,
    TurnCancelled,
    TurnCompleted,
    turn_failed,
)
from app.integrations.hermes.provider import ProviderStatus, TurnRequest

logger = logging.getLogger("drakter.agent.fake")

FAKE_TOOL: Final = "get_system_status"
FAST_DELAY_S: Final = 0.01
SLOW_DELAY_S: Final = 0.25


class FakeProvider:
    name = "fake"

    def __init__(
        self,
        registry: Any | None,
        state: Any,
        observer: Callable[[str, Any, Any], None] | None = None,
    ) -> None:
        self._registry = registry
        self._state = state
        self._observer = observer
        self._cancels: dict[UUID, asyncio.Event] = {}
        self._steers: dict[UUID, list[str]] = {}

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        for cancel in self._cancels.values():
            cancel.set()

    def status(self) -> ProviderStatus:
        return ProviderStatus("ready", None, "fake")

    async def create_session(self) -> UUID:
        return uuid4()

    async def close_session(self, session_id: UUID) -> None:
        return None

    async def cancel(self, turn_id: UUID) -> None:
        cancel = self._cancels.get(turn_id)
        if cancel is not None:
            cancel.set()

    async def steer_turn(self, turn_id: UUID, text: str) -> None:
        steers = self._steers.get(turn_id)
        if steers is not None:
            steers.append(text)

    async def stream_turn(self, request: TurnRequest) -> AsyncIterator[AgentEvent]:
        cancel = self._cancels[request.turn_id] = asyncio.Event()
        steers = self._steers[request.turn_id] = []
        pending: str | None = None
        command = request.text.lower()
        delay = SLOW_DELAY_S if "fake:slow" in command else FAST_DELAY_S
        try:
            yield Thinking()
            if "fake:tool" in command:
                call_id = f"call-{uuid4().hex[:12]}"
                yield ToolStarted(tool=FAKE_TOOL, call_id=call_id)
                failed = await self._call_tool(request, call_id)
                yield ToolCompleted(tool=FAKE_TOOL, call_id=call_id, error=failed)
            reply = f"Respuesta simulada a {len(request.text)} caracteres recibidos."
            words = reply.split(" ")
            chunks = [f"{word} " for word in words[:-1]] + [words[-1]]
            if "fake:tags" in command:
                reply = "[calm] Hola, señor. [happy]Todo en orden [break] y listo."
                chunks = ["[cal", "m] Hola, ", "señor. [hap", "py]", "Todo en orden [", "break] y listo."]
            if "fake:fail" in command:
                yield MessageDelta(text=chunks[0])
                yield turn_failed(ErrorCode.PROVIDER_ERROR, retryable=True)
                return
            queue = list(chunks)
            while queue:
                if await self._cancelled(cancel, delay):
                    yield TurnCancelled()
                    return
                if steers:
                    text = steers.pop(0)
                    accepted = "fake:reject" not in text.lower()
                    yield Steered(accepted=accepted)
                    if accepted and "fake:pending" in text.lower():
                        pending = text
                    elif accepted:
                        reply = f"Corrección recibida ({len(text)} caracteres)."
                        queue = [f"{word} " for word in reply.split(" ")]
                        queue[-1] = queue[-1].rstrip()
                    continue
                yield MessageDelta(text=queue.pop(0))
            while steers:  # too late for this turn
                steers.pop(0)
                yield Steered(accepted=False)
            yield TurnCompleted(
                text=reply, usage={"input_tokens": 0, "output_tokens": 0}, pending_steer=pending
            )
        finally:
            self._cancels.pop(request.turn_id, None)
            self._steers.pop(request.turn_id, None)

    @staticmethod
    async def _cancelled(cancel: asyncio.Event, delay: float) -> bool:
        try:
            await asyncio.wait_for(cancel.wait(), timeout=delay)
        except TimeoutError:
            return False
        return True

    async def _call_tool(self, request: TurnRequest, call_id: str) -> bool:
        """Go through the real dispatch. Returns True when the tool did not succeed."""
        if self._registry is None:
            return True
        from app.tools.spec import ToolContext

        context = ToolContext(
            turn_id=request.turn_id,
            session_id=request.session_id,
            call_id=call_id,
            principal="agent",
            state=self._state,
        )
        outcome = await self._registry.dispatch(FAKE_TOOL, {}, context, observer=self._observer)
        return outcome.model_dump().get("status") != "ok"
