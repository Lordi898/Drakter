"""AgentProvider over the Hermes runner, reached only through the supervisor.

The runner is not trusted: everything it sends is validated and reduced to `AgentEvent`,
and none of its free text reaches the logs or the GUI except the assistant reply.
Internal Hermes approvals are denied by the runner; real confirmation lives in the backend.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Protocol
from uuid import UUID, uuid4

from drakter_contracts.errors import ErrorCode

from app.integrations.hermes.events import (
    TERMINAL_EVENTS,
    AgentEvent,
    MessageDelta,
    Thinking,
    ToolCompleted,
    ToolSource,
    ToolStarted,
    TurnCancelled,
    TurnCompleted,
    TurnFailed,
    turn_failed,
)
from app.integrations.hermes.provider import ProviderStatus, TurnRequest

if TYPE_CHECKING:
    from app.integrations.hermes.settings import AgentSettings

logger = logging.getLogger("drakter.agent.hermes")

INSTRUCTIONS_RELATIVE_PATH: Final = Path("agent/configuration/safety_instructions.md")
MCP_TOOL_PREFIX: Final = "mcp__drakter__"
# stop_turn gives the runner its grace and then kills it, so a terminal event is due by then.
STOP_MARGIN_S: Final = 10.0
TICK_S: Final = 0.25
_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,96}$")
_RETRYABLE_CODES: Final = frozenset({ErrorCode.AGENT_BUSY, ErrorCode.AGENT_UNAVAILABLE})
_RUNNER_CODES: Final = frozenset(
    {
        ErrorCode.AGENT_BUSY,
        ErrorCode.AGENT_UNAVAILABLE,
        ErrorCode.AGENT_TIMEOUT,
        ErrorCode.AGENT_DISCONNECTED,
        ErrorCode.PROVIDER_AUTH,
        ErrorCode.PROVIDER_ERROR,
    }
)
_END_OF_STREAM: Final = object()


class _Supervisor(Protocol):
    state: str

    def run_turn(
        self, turn_id: UUID, session_id: UUID, text: str, instructions: str
    ) -> AsyncIterator[dict[str, Any]]: ...

    async def stop_turn(self, turn_id: UUID, grace_s: float = 5) -> None: ...


@dataclass(slots=True)
class _Turn:
    turn_id: UUID
    turn_deadline: float
    idle_deadline: float
    text: list[str] = field(default_factory=list)
    cancel_requested: bool = False
    cancel_deadline: float | None = None
    finished: bool = False


def _clean_tool_name(raw: Any) -> str:
    if not isinstance(raw, str) or not _NAME.match(raw):
        return "unknown"
    return raw.removeprefix(MCP_TOOL_PREFIX)


def _tool_source(raw: Any) -> ToolSource:
    return "drakter" if isinstance(raw, str) and raw.startswith(MCP_TOOL_PREFIX) else "hermes"


def _clean_call_id(raw: Any) -> str:
    return raw if isinstance(raw, str) and _NAME.match(raw) else f"call-{uuid4().hex[:12]}"


def _clean_usage(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    return {
        key: value
        for key, value in raw.items()
        if isinstance(key, str) and type(value) is int
    }


def _failure_from(data: dict[str, Any]) -> TurnFailed:
    """The runner's code is honoured if known; its message is discarded."""
    try:
        code = ErrorCode(data.get("code"))
    except ValueError:
        code = ErrorCode.PROVIDER_ERROR
    if code not in _RUNNER_CODES:
        code = ErrorCode.PROVIDER_ERROR
    return turn_failed(code, retryable=code in _RETRYABLE_CODES)


class HermesProvider:
    name = "hermes"

    def __init__(
        self, settings: AgentSettings, supervisor: _Supervisor | None, repo_root: Path
    ) -> None:
        self._settings = settings
        self._supervisor = supervisor
        self._instructions_path = repo_root / INSTRUCTIONS_RELATIVE_PATH
        self._instructions: str | None = None
        self._turns: dict[UUID, _Turn] = {}
        self._background: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        # Read once: the text is part of the prompt prefix and must stay byte-stable (H-21).
        self._instructions = await asyncio.to_thread(self._load_instructions)

    def _load_instructions(self) -> str | None:
        try:
            text = self._instructions_path.read_text(encoding="utf-8")
        except OSError:
            logger.error("safety instructions missing", extra={"event": "instructions_missing"})
            return None
        if not text.strip():
            logger.error("safety instructions empty", extra={"event": "instructions_empty"})
            return None
        return text

    async def stop(self) -> None:
        if self._background:
            await asyncio.wait(self._background, timeout=STOP_MARGIN_S)

    def status(self) -> ProviderStatus:
        model = self._settings.model_name
        if self._supervisor is None:
            return ProviderStatus("offline", "El agente no se ha podido arrancar.", model)
        if self._instructions is None:
            return ProviderStatus("failed", "Faltan las instrucciones de seguridad.", model)
        state = self._supervisor.state
        if state == "ready":
            return ProviderStatus("ready", None, model)
        if state in ("starting", "restarting"):
            return ProviderStatus("starting", "El agente se está iniciando.", model)
        if state == "failed":
            return ProviderStatus("failed", "El agente no se ha podido arrancar.", model)
        return ProviderStatus("offline", "El agente está detenido.", model)

    async def create_session(self) -> UUID:
        return uuid4()

    async def close_session(self, session_id: UUID) -> None:
        return None

    async def cancel(self, turn_id: UUID) -> None:
        turn = self._turns.get(turn_id)
        if turn is None or turn.finished or turn.cancel_requested:
            return
        turn.cancel_requested = True
        turn.cancel_deadline = time.monotonic() + STOP_MARGIN_S
        # In the background: stop_turn may take its whole grace and the API must not wait.
        self._spawn(self._stop_quietly(turn_id))

    async def stream_turn(self, request: TurnRequest) -> AsyncIterator[AgentEvent]:
        now = time.monotonic()
        turn = _Turn(
            turn_id=request.turn_id,
            turn_deadline=now + self._settings.turn_timeout_s,
            idle_deadline=now + self._settings.idle_timeout_s,
        )
        self._turns[request.turn_id] = turn
        started = False
        try:
            if self.status().state != "ready" or self._instructions is None:
                turn.finished = True
                yield turn_failed(ErrorCode.AGENT_UNAVAILABLE, retryable=True)
                return
            yield Thinking()
            started = True
            async for event in self._consume(request, turn):
                yield event
        except Exception as exc:  # noqa: BLE001 - the terminal event is the contract
            logger.warning(
                "hermes turn aborted",
                extra={
                    "event": "turn_aborted",
                    "turn_id": str(turn.turn_id),
                    "kind": type(exc).__name__,
                },
            )
            turn.finished = True
            yield turn_failed(ErrorCode.PROVIDER_ERROR)
        finally:
            self._turns.pop(request.turn_id, None)
            if started and not turn.finished:
                # The consumer left mid-turn (shutdown): the runner must not keep working.
                self._spawn(self._stop_quietly(request.turn_id))

    async def _consume(self, request: TurnRequest, turn: _Turn) -> AsyncIterator[AgentEvent]:
        queue: asyncio.Queue[object] = asyncio.Queue(maxsize=256)
        pump = asyncio.create_task(self._pump(request, queue))
        try:
            while True:
                expired = self._expired_deadline(turn)
                if expired is not None:
                    turn.finished = True
                    yield await self._finish_by_deadline(turn, queue, expired)
                    return
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=self._wait_time(turn))
                except TimeoutError:
                    continue
                if item is _END_OF_STREAM:
                    # Never resent: the outcome is unknown.
                    turn.finished = True
                    yield self._lost(turn)
                    return
                event = self._normalize(turn, item)
                if event is None:
                    continue
                if isinstance(event, TERMINAL_EVENTS):
                    turn.finished = True
                yield event
                if turn.finished:
                    return
        finally:
            pump.cancel()
            await asyncio.gather(pump, return_exceptions=True)

    async def _pump(self, request: TurnRequest, queue: asyncio.Queue[object]) -> None:
        assert self._supervisor is not None and self._instructions is not None
        try:
            stream = self._supervisor.run_turn(
                request.turn_id, request.session_id, request.text, self._instructions
            )
            async for raw in stream:
                await queue.put(raw)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - reported as a lost stream
            logger.warning(
                "hermes stream interrupted",
                extra={
                    "event": "stream_interrupted",
                    "turn_id": str(request.turn_id),
                    "kind": type(exc).__name__,
                },
            )
        await queue.put(_END_OF_STREAM)

    @staticmethod
    def _lost(turn: _Turn) -> AgentEvent:
        return TurnCancelled() if turn.cancel_requested else turn_failed(ErrorCode.AGENT_DISCONNECTED)

    @staticmethod
    def _expired_deadline(turn: _Turn) -> str | None:
        now = time.monotonic()
        if turn.cancel_deadline is not None:
            # A cancelled turn lives by its own clock: it is already on the way out.
            return "cancel" if now >= turn.cancel_deadline else None
        return "timeout" if now >= min(turn.turn_deadline, turn.idle_deadline) else None

    @staticmethod
    def _wait_time(turn: _Turn) -> float:
        deadline = turn.cancel_deadline or min(turn.turn_deadline, turn.idle_deadline)
        # Bounded so a cancel arriving during the wait is seen promptly.
        return max(0.0, min(deadline - time.monotonic(), TICK_S))

    async def _finish_by_deadline(
        self, turn: _Turn, queue: asyncio.Queue[object], expired: str
    ) -> AgentEvent:
        logger.warning(
            "hermes turn deadline",
            extra={"event": "turn_deadline", "turn_id": str(turn.turn_id), "reason": expired},
        )
        await self._stop_quietly(turn.turn_id)
        # stop_turn has returned, so the terminal event is either queued or never coming.
        deadline = time.monotonic() + TICK_S
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=remaining)
            except TimeoutError:
                break
            if item is _END_OF_STREAM:
                break
            event = self._normalize(turn, item)
            if isinstance(event, TurnCompleted):
                return event  # it finished after all: the reply is real
            if isinstance(event, TERMINAL_EVENTS):
                break
        return TurnCancelled() if expired == "cancel" else turn_failed(ErrorCode.AGENT_TIMEOUT)

    def _normalize(self, turn: _Turn, data: object) -> AgentEvent | None:
        if not isinstance(data, dict):
            logger.warning("runner event is not an object", extra={"event": "runner_bad_event"})
            return None
        if data.get("turn_id") not in (None, str(turn.turn_id)):
            logger.warning("runner event for another turn", extra={"event": "runner_wrong_turn"})
            return None
        name = data.get("ev")
        turn.idle_deadline = time.monotonic() + self._settings.idle_timeout_s
        if name == "thinking":
            return Thinking()
        if name == "delta":
            text = data.get("text")
            if not isinstance(text, str) or not text:
                return None
            turn.text.append(text)
            return MessageDelta(text=text)
        if name == "tool_started":
            return ToolStarted(
                tool=_clean_tool_name(data.get("tool")),
                call_id=_clean_call_id(data.get("call_id")),
                source=_tool_source(data.get("tool")),
            )
        if name == "tool_completed":
            return ToolCompleted(
                tool=_clean_tool_name(data.get("tool")),
                call_id=_clean_call_id(data.get("call_id")),
                # An interrupted tool may still be running: it is never reported as a success.
                error=bool(data.get("error")) or bool(data.get("interrupted")),
                source=_tool_source(data.get("tool")),
            )
        if name == "completed":
            output = data.get("output")
            text = output if isinstance(output, str) and output else "".join(turn.text)
            return TurnCompleted(text=text, usage=_clean_usage(data.get("usage")))
        if name == "cancelled":
            return TurnCancelled()
        if name == "failed":
            return _failure_from(data)
        label = name if isinstance(name, str) and _NAME.match(name) else "invalid"
        logger.info("runner event ignored", extra={"event": "runner_unknown", "runner_ev": label})
        return None

    async def _stop_quietly(self, turn_id: UUID) -> None:
        if self._supervisor is None:
            return
        try:
            await self._supervisor.stop_turn(turn_id)
        except Exception as exc:  # noqa: BLE001 - the deadline path decides the outcome
            logger.warning(
                "hermes stop failed", extra={"event": "stop_failed", "kind": type(exc).__name__}
            )

    def _spawn(self, coroutine: Coroutine[Any, Any, None]) -> None:
        task = asyncio.ensure_future(coroutine)
        self._background.add(task)
        task.add_done_callback(self._background.discard)
