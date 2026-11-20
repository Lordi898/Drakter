"""Assembles the agent side of the backend and runs each conversation turn.

Nothing here can take the backend down: without Hermes or tools, the API stays up and
the agent reports `offline`.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import sqlite3
import time
from collections.abc import Callable
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Final, Literal, Protocol
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from drakter_contracts.errors import HTTP_STATUS, ErrorCode
from drakter_contracts.events import (
    AgentError,
    AgentMessageCompleted,
    AgentMessageDelta,
    AgentMessageStarted,
    AgentState,
    AgentToolCompleted,
    AgentToolStarted,
    AgentTurnFinished,
    AgentTurnStarted,
    ChatUserMessage,
    ConfirmationRequested,
    SystemHealthChanged,
)
from drakter_contracts.speech_markup import IncrementalStripper, strip_tags
from pydantic import BaseModel

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import SessionToken
from app.events import EventHub
from app.events.status import StatusArbiter
from app.integrations.hermes.chat_store import (
    ActiveTurnExists,
    ChatMessage,
    ChatSession,
    MessageStatus,
    SqliteChatStore,
    TurnStatus,
)
from app.integrations.hermes.events import (
    SAFE_MESSAGES,
    TERMINAL_EVENTS,
    MessageDelta,
    Steered,
    Thinking,
    ToolCompleted,
    ToolStarted,
    TurnCancelled,
    TurnCompleted,
    TurnFailed,
    turn_failed,
)
from app.integrations.hermes.fake import FakeProvider
from app.integrations.hermes.hermes_provider import HermesProvider
from app.integrations.hermes.provider import AgentProvider, ProviderStatus, TurnRequest
from app.repositories.notifications_due import default_timezone

if TYPE_CHECKING:
    from app.integrations.hermes.settings import AgentSettings

logger = logging.getLogger("drakter.agent.runtime")

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
FALLBACK_TIMEZONE: Final = "Europe/Madrid"  # contracts/README.md §4
_WEEKDAYS: Final = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MONTHS: Final = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
STOP_TURN_GRACE_S: Final = 12.0
# The runner answers a steer at once; past this the correction is treated as not accepted.
STEER_TIMEOUT_S: Final = 5.0
STEER_SEPARATOR: Final = "\n\n"
SESSION_SCAN: Final = 50

Source = Literal["text", "voice"]
Outcome = Literal["completed", "cancelled", "failed"]


class TurnTap(Protocol):
    """Implemented by VoiceOrchestrator. SYNCHRONOUS and NON-blocking (put_nowait); the runtime
    still wraps every call, so a broken tap never breaks a turn. Raw text, tags included."""

    def on_turn_started(self, turn_id: UUID, session_id: UUID, source: Source) -> None: ...

    def on_raw_delta(self, turn_id: UUID, text: str) -> None: ...

    def on_tool_started(self, turn_id: UUID, tool: str) -> None: ...

    def on_steered(self, turn_id: UUID, accepted: bool) -> None: ...

    def on_terminal(self, turn_id: UUID, outcome: Outcome) -> None: ...


TurnPrefix = Callable[[UUID, str], "str | None"]


@dataclass(frozen=True, slots=True)
class ActiveTurnInfo:
    turn_id: UUID
    session_id: UUID
    phase: Literal["generating", "executing"]


def _agent_error(code: ErrorCode) -> AppError:
    return AppError(code.value, SAFE_MESSAGES[code], HTTP_STATUS[code])


def _not_found(message: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND.value, message, HTTP_STATUS[ErrorCode.NOT_FOUND])


@dataclass(slots=True)
class _ActiveTurn:
    session_id: UUID
    turn_id: UUID
    source: Source = "text"
    text: list[str] = field(default_factory=list)  # already stripped of expression tags
    message_id: UUID | None = None
    task: asyncio.Task[None] | None = None
    phase: Literal["generating", "executing"] = "generating"
    stripper: IncrementalStripper = field(default_factory=IncrementalStripper)
    steer_waiters: list[asyncio.Future[bool]] = field(default_factory=list)
    # corrections accepted while `steer()` waited: that caller stores and shows them
    echoed_steers: int = 0
    started: float = field(default_factory=time.monotonic)
    first_delta_ms: int | None = None

    @property
    def correlation_id(self) -> str:
        return str(self.turn_id)


class AgentRuntime:
    def __init__(self, settings: Settings, agent_settings: AgentSettings | None = None) -> None:
        from app.integrations.hermes.settings import AgentSettings as LoadedSettings

        self.settings = settings
        self.agent_settings = agent_settings or LoadedSettings()
        self.hub = EventHub()
        # The only producer of agent.status_changed (V-28); the voice signals it too.
        self.status_arbiter = StatusArbiter(self.hub)
        self.store = SqliteChatStore(settings.db_path)
        self.registry: Any | None = None
        self.turns: Any | None = None
        # `gate` and `audit` for ToolRegistry; `permissions/wiring.py` sets the real ones.
        self.tool_wiring: dict[str, Any] = {}
        self.provider: AgentProvider | None = None
        # What ToolContext.state exposes; tools only read `agent_runtime` and `settings`.
        self.tool_state = SimpleNamespace(agent_runtime=self, settings=settings)
        self._tools_server: Any | None = None
        self._supervisor: Any | None = None
        self._boot_task: asyncio.Task[None] | None = None
        self._active: _ActiveTurn | None = None
        self._health: tuple[str, str | None] | None = None
        self._tap: TurnTap | None = None
        self._prefixes: list[TurnPrefix] = []
        self._session_lock = asyncio.Lock()
        self._follow_ups: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        try:
            await self._start()
        except Exception as exc:  # noqa: BLE001 - never takes the backend down
            logger.error(
                "agent runtime failed to start",
                extra={"event": "agent_start_failed", "kind": type(exc).__name__},
            )
            self._publish_health("down", "El agente no se ha podido arrancar.")

    async def _start(self) -> None:
        interrupted = await self.store.recover_interrupted()
        if interrupted:
            logger.warning(
                "turns interrupted by the previous shutdown",
                extra={"event": "turns_interrupted", "count": interrupted},
            )
        self._load_tools()
        if self.agent_settings.agent_provider == "fake":
            self.provider = FakeProvider(self.registry, self.tool_state, self.observe_tool_outcome)
            await self.provider.start()
            self._sync_provider_state()
            return
        supervisor = await self._prepare_hermes()
        if supervisor is not None:
            # Hermes takes seconds to boot and the backend's port has a deadline.
            self._boot_task = asyncio.create_task(self._boot_supervisor(supervisor))

    def _load_tools(self) -> None:
        """Idempotent: the security wiring loads them early to register their actions."""
        if self.registry is not None:
            return
        try:
            from app.tools.registry import ToolRegistry, load_builtin_tools
            from app.tools.turns import TurnTracker

            turns = TurnTracker()
            registry = ToolRegistry(turns, **self.tool_wiring)
            load_builtin_tools(registry)
        except Exception as exc:  # noqa: BLE001 - a bad tool module leaves the agent offline
            logger.error(
                "agent tools not loaded",
                extra={"event": "agent_tools_failed", "kind": type(exc).__name__},
            )
            return
        self.turns, self.registry = turns, registry

    async def _prepare_hermes(self) -> Any | None:
        supervisor = None
        try:
            supervisor = await self._prepare_supervisor()
        except Exception as exc:  # noqa: BLE001 - no tools or no bridge means offline
            logger.error(
                "hermes not prepared",
                extra={"event": "hermes_prepare_failed", "kind": type(exc).__name__},
            )
        provider = HermesProvider(
            self.agent_settings,
            supervisor,
            REPO_ROOT,
            memory=lambda: getattr(self.tool_state, "memory_service", None),
            turns=self.turns,
        )
        await provider.start()
        self.provider = provider
        self._sync_provider_state()
        return supervisor

    async def _boot_supervisor(self, supervisor: Any) -> None:
        try:
            await supervisor.start()
        except Exception as exc:  # noqa: BLE001 - Hermes missing or broken means offline
            logger.error(
                "hermes not started",
                extra={"event": "hermes_start_failed", "kind": type(exc).__name__},
            )
        self._sync_provider_state()

    async def _prepare_supervisor(self) -> Any:
        if self.registry is None or self.turns is None:
            raise RuntimeError("tools not loaded")
        from app.integrations.hermes.supervisor import HermesSupervisor
        from app.tools.mcp_bridge import AgentToolsServer, build_agent_tools_app

        token = SessionToken(secrets.token_urlsafe(32))
        app = build_agent_tools_app(
            self.registry, self.turns, token, self.tool_state, observer=self.observe_tool_outcome
        )
        self._tools_server = AgentToolsServer(app)
        await self._tools_server.start()
        self._supervisor = HermesSupervisor(
            self.agent_settings,
            self.settings.data_dir,
            [spec.name for spec in self.registry.catalog()],
            token,
            self._tools_server.url,
            REPO_ROOT,
            self._on_supervisor_state,
        )
        return self._supervisor

    def _on_supervisor_state(self, *_: Any) -> None:
        self._sync_provider_state()

    def _sync_provider_state(self) -> None:
        """Provider availability decides, except that a running turn keeps its own state."""
        status = self.provider.status() if self.provider else ProviderStatus("offline")
        health = {"ready": "ok", "starting": "degraded"}.get(status.state, "down")
        self._publish_health(health, status.detail)
        if self._active is None:
            self._publish_state(AgentState.IDLE if health == "ok" else AgentState.OFFLINE)

    def _publish_health(self, status: str, detail: str | None) -> None:
        if self._health == (status, detail):
            return
        self._health = (status, detail)
        self.hub.publish(
            "system.health_changed",
            SystemHealthChanged(component="hermes", status=status, detail=detail),
        )

    async def stop(self) -> None:
        active = self._active
        if active is not None and active.task is not None:
            await self._stop_active_turn(active)
        if self._boot_task is not None:
            self._boot_task.cancel()
            await asyncio.gather(self._boot_task, return_exceptions=True)
        for label, closer in (
            ("provider", self.provider.stop if self.provider else None),
            ("supervisor", self._supervisor.stop if self._supervisor else None),
            ("tools", self._tools_server.stop if self._tools_server else None),
        ):
            if closer is None:
                continue
            try:
                await closer()
            except Exception as exc:  # noqa: BLE001 - one piece must not block the others
                logger.warning(
                    "agent piece did not stop cleanly",
                    extra={"event": "agent_stop_failed", "piece": label, "kind": type(exc).__name__},
                )
        self._publish_state(AgentState.OFFLINE, reason="shutdown")

    async def _stop_active_turn(self, active: _ActiveTurn) -> None:
        assert active.task is not None
        try:
            if self.provider is not None:
                await self.provider.cancel(active.turn_id)
        except Exception as exc:  # noqa: BLE001 - shutting down regardless
            logger.warning(
                "turn cancel failed on shutdown",
                extra={"event": "turn_cancel_failed", "kind": type(exc).__name__},
            )
        done, _ = await asyncio.wait({active.task}, timeout=STOP_TURN_GRACE_S)
        if not done:
            active.task.cancel()
            await asyncio.gather(active.task, return_exceptions=True)

    def status(self) -> dict[str, str | None]:
        """`state` is the arbiter's: the same as the last agent.status_changed."""
        provider = self.provider
        status = provider.status() if provider is not None else None
        return {
            "state": self.status_arbiter.current.state.value,
            "provider": provider.name if provider else self.agent_settings.agent_provider,
            "model": status.model if status else None,
            "detail": status.detail if status else None,
        }

    # Sessions

    async def create_session(self) -> ChatSession:
        provider = self._require_provider()
        return await self.store.create_session(await provider.create_session())

    async def close_session(self, session_id: UUID) -> ChatSession:
        session = await self._require_session(session_id)
        if self._active is not None and self._active.session_id == session_id:
            raise _agent_error(ErrorCode.AGENT_BUSY)
        if self.provider is not None:
            await self.provider.close_session(session_id)
        closed = await self.store.close_session(session_id)
        return closed or session

    async def current_session(self) -> UUID:
        """The latest open session, shared by voice and chat; a new one if there is none."""
        async with self._session_lock:
            sessions, _ = await self.store.list_sessions(SESSION_SCAN, 0)
            for session in sessions:
                if session.status == "open":
                    return session.id
            return (await self.create_session()).id

    async def list_messages(
        self, session_id: UUID, limit: int, offset: int
    ) -> tuple[list[ChatMessage], int]:
        await self._require_session(session_id)
        return await self.store.list_messages(session_id, limit, offset)

    async def _require_session(self, session_id: UUID) -> ChatSession:
        session = await self.store.get_session(session_id)
        if session is None:
            raise _not_found("La sesión no existe.")
        return session

    def _require_provider(self) -> AgentProvider:
        provider = self.provider
        if provider is None or provider.status().state != "ready":
            raise _agent_error(ErrorCode.AGENT_UNAVAILABLE)
        return provider

    # Turns

    # Voice v2 ports (CONTRACT.md 5bis)

    def set_turn_tap(self, tap: TurnTap | None) -> None:
        self._tap = tap

    def add_turn_prefix(self, fn: TurnPrefix) -> None:
        """`fn(session_id, source)` -> text or None. Only for the prompt sent to the model:
        never stored, never in chat.user_message, never in the system prompt."""
        self._prefixes.append(fn)

    def active_turn(self) -> ActiveTurnInfo | None:
        active = self._active
        if active is None:
            return None
        return ActiveTurnInfo(turn_id=active.turn_id, session_id=active.session_id, phase=active.phase)

    async def steer(self, turn_id: UUID, text: str, *, source: Source = "voice") -> bool:
        """Correct the running turn (same turn_id). False if it is not running or Hermes refuses.

        An accepted correction is what the user said: like any user message it is stored and
        published as `chat.user_message` (voice and chat share the conversation). A refused
        one is not: the caller decides whether it becomes a turn of its own.
        """
        active, provider = self._active, self.provider
        if active is None or active.turn_id != turn_id or provider is None or not text.strip():
            return False
        waiter: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        active.steer_waiters.append(waiter)
        try:
            await provider.steer_turn(turn_id, text)
            accepted = await asyncio.wait_for(asyncio.shield(waiter), STEER_TIMEOUT_S)
        except Exception as exc:  # noqa: BLE001 - TimeoutError included: not accepted
            logger.info("steer not accepted", extra={"event": "steer_failed", "kind": type(exc).__name__})
            return False
        finally:
            if waiter in active.steer_waiters:
                active.steer_waiters.remove(waiter)
        if accepted:
            await self._echo_steer(active, text, source)
        return accepted

    async def _echo_steer(self, active: _ActiveTurn, text: str, source: Source) -> None:
        try:
            message = await self.store.add_user_message(active.session_id, active.turn_id, text)
        except Exception as exc:  # noqa: BLE001 - the correction already reached the agent
            logger.warning("steer not persisted", extra={"event": "steer_persist_failed", "kind": type(exc).__name__})
            return
        self._publish(
            active,
            "chat.user_message",
            ChatUserMessage(
                message_id=message.id,
                session_id=active.session_id,
                turn_id=active.turn_id,
                text=text,
                input_source=source,
                created_at=message.created_at,
            ),
        )

    def _call_tap(self, method: str, *args: Any) -> None:
        tap = self._tap
        if tap is None:
            return
        try:
            getattr(tap, method)(*args)
        except Exception as exc:  # noqa: BLE001 - the voice never breaks a turn
            logger.warning("turn tap failed", extra={"event": "turn_tap_failed", "kind": type(exc).__name__})

    def _user_zone(self) -> ZoneInfo:
        try:
            with sqlite3.connect(f"file:{self.settings.db_path}?mode=ro", uri=True, timeout=1) as conn:
                name = default_timezone(conn) or FALLBACK_TIMEZONE
            return ZoneInfo(name)
        except (sqlite3.Error, ValueError, ZoneInfoNotFoundError):
            return ZoneInfo(FALLBACK_TIMEZONE)

    def _clock_line(self) -> str:
        """Local date and time for this turn: without it the model asks `get_system_status` (UTC)
        or, without thinking, guesses the hour (LAT-1). Turn prompt only: the prefix cache holds."""
        zone = self._user_zone()
        now = datetime.now(zone)
        return (
            f"[ahora: {_WEEKDAYS[now.weekday()]} {now.day} de {_MONTHS[now.month - 1]} de {now.year}, "
            f"{now:%H:%M} ({zone.key})]"
        )

    def _turn_prefix(self, session_id: UUID, source: Source) -> str:
        parts: list[str] = []
        for fn in self._prefixes:
            try:
                part = fn(session_id, source)
            except Exception as exc:  # noqa: BLE001 - a turn without its prefix beats no turn
                logger.warning("turn prefix failed", extra={"event": "turn_prefix_failed", "kind": type(exc).__name__})
                continue
            if part:
                parts.append(part)
        parts.append(self._clock_line())
        return "\n".join(parts)

    # Turns

    async def submit_message(
        self,
        session_id: UUID,
        text: str,
        client_message_id: UUID | None,
        *,
        source: Source = "text",
        echoed: bool = False,
    ) -> tuple[UUID, UUID]:
        """Accept a user message and start its turn. Returns (turn_id, message_id).

        `echoed`: the text is already stored and shown (an accepted steer that Hermes never
        consumed); the new turn neither stores it again nor publishes `chat.user_message`.
        """
        session = await self._require_session(session_id)
        if session.status != "open":
            raise AppError(ErrorCode.CONFLICT.value, "La sesión está cerrada.", 409)
        if client_message_id is not None:
            existing = await self.store.find_client_message(session_id, client_message_id)
            if existing is not None:
                return existing.turn_id, existing.id
        provider = self._require_provider()
        turn_id = uuid4()
        active = self._reserve_turn(session_id, turn_id, source)
        try:
            message, created = await self.store.begin_turn(
                session_id, turn_id, text, client_message_id, store_message=not echoed
            )
        except ActiveTurnExists:
            self._end_turn(active)
            raise _agent_error(ErrorCode.AGENT_BUSY) from None
        except BaseException:
            self._end_turn(active)
            raise
        if not created:
            self._end_turn(active)
            return message.turn_id or turn_id, message.id
        if not echoed:
            self._publish(
                active,
                "chat.user_message",
                ChatUserMessage(
                    message_id=message.id,
                    session_id=session_id,
                    turn_id=turn_id,
                    text=text,
                    input_source=source,
                    created_at=message.created_at,
                ),
            )
        self._publish(
            active,
            "agent.turn_started",
            AgentTurnStarted(session_id=session_id, turn_id=turn_id, input_source=source),
        )
        self._call_tap("on_turn_started", turn_id, session_id, source)
        self._publish_state(AgentState.THINKING, turn_id=turn_id)
        request = TurnRequest(
            session_id=session_id,
            turn_id=turn_id,
            text=text,
            prefix=self._turn_prefix(session_id, source),
            source=source,
        )
        active.task = asyncio.create_task(self._run_turn(provider, request, active))
        return turn_id, message.id

    def _publish(self, active: _ActiveTurn, event_type: str, payload: BaseModel) -> None:
        self.hub.publish(event_type, payload, correlation_id=active.correlation_id)

    def _reserve_turn(self, session_id: UUID, turn_id: UUID, source: Source = "text") -> _ActiveTurn:
        """Admission: synchronous, so two requests cannot both get through."""
        if self._active is not None:
            raise _agent_error(ErrorCode.AGENT_BUSY)
        if self.turns is not None:
            from app.tools.turns import TurnBusyError

            try:
                self.turns.begin(session_id, turn_id)
            except TurnBusyError:
                raise _agent_error(ErrorCode.AGENT_BUSY) from None
        self._active = _ActiveTurn(session_id=session_id, turn_id=turn_id, source=source)
        return self._active

    def _end_turn(self, active: _ActiveTurn) -> None:
        if self.turns is not None:
            self.turns.end(active.turn_id)
        if self._active is active:
            self._active = None

    async def cancel_turn(self, turn_id: UUID) -> None:
        active = self._active
        if active is None or active.turn_id != turn_id or self.provider is None:
            raise _not_found("El turno no está activo.")
        await self.provider.cancel(turn_id)

    async def _run_turn(
        self, provider: AgentProvider, request: TurnRequest, active: _ActiveTurn
    ) -> None:
        terminal: TurnCompleted | TurnCancelled | TurnFailed | None = None
        try:
            terminal = await self._consume_turn(provider, request, active)
        except asyncio.CancelledError:
            terminal = turn_failed(ErrorCode.AGENT_DISCONNECTED)
            await asyncio.shield(self._close_turn(active, terminal))
            raise
        except Exception as exc:  # noqa: BLE001 - a broken provider must not hold the slot
            logger.warning(
                "turn crashed",
                extra={
                    "event": "turn_crashed",
                    "turn_id": str(request.turn_id),
                    "kind": type(exc).__name__,
                },
            )
            terminal = turn_failed(ErrorCode.PROVIDER_ERROR)
        await self._close_turn(active, terminal)

    async def _consume_turn(
        self, provider: AgentProvider, request: TurnRequest, active: _ActiveTurn
    ) -> TurnCompleted | TurnCancelled | TurnFailed:
        stream = provider.stream_turn(request)
        try:
            async for event in stream:
                if isinstance(event, TERMINAL_EVENTS):
                    return event
                await self._handle_event(active, event)
        finally:
            await stream.aclose()  # type: ignore[attr-defined]
        logger.warning(
            "provider stream ended without a terminal event",
            extra={"event": "turn_no_terminal", "turn_id": str(request.turn_id)},
        )
        return turn_failed(ErrorCode.PROVIDER_ERROR)

    async def _ensure_message(self, active: _ActiveTurn) -> UUID:
        if active.message_id is None:
            active.message_id = await self.store.start_assistant_message(
                active.session_id, active.turn_id
            )
            self._publish(
                active,
                "agent.message_started",
                AgentMessageStarted(
                    session_id=active.session_id,
                    turn_id=active.turn_id,
                    message_id=active.message_id,
                ),
            )
        return active.message_id

    async def _emit_text(self, active: _ActiveTurn, clean: str) -> None:
        """Tag-free text only: this is what the chat, the hub and the DB see."""
        if not clean:
            return
        await self._ensure_message(active)
        active.text.append(clean)
        self._publish(
            active,
            "agent.message_delta",
            AgentMessageDelta(session_id=active.session_id, turn_id=active.turn_id, delta=clean),
        )

    async def _handle_event(self, active: _ActiveTurn, event: Any) -> None:
        ids = {"session_id": active.session_id, "turn_id": active.turn_id}
        if isinstance(event, Thinking):
            active.phase = "generating"
            self._publish_state(AgentState.THINKING, turn_id=active.turn_id)
        elif isinstance(event, MessageDelta):
            active.phase = "generating"
            if active.first_delta_ms is None:
                active.first_delta_ms = round((time.monotonic() - active.started) * 1000)
            self._call_tap("on_raw_delta", active.turn_id, event.text)  # before the stripper
            self._publish_state(AgentState.SPEAKING, turn_id=active.turn_id)
            await self._emit_text(active, active.stripper.feed(event.text))
        elif isinstance(event, Steered):
            for waiter in active.steer_waiters:
                if not waiter.done():
                    waiter.set_result(event.accepted)
                    if event.accepted:
                        active.echoed_steers += 1  # before any terminal: see _close_turn
                    break
            if event.accepted:
                if active.message_id is not None:
                    await self._emit_text(active, active.stripper.flush() + STEER_SEPARATOR)
            self._call_tap("on_steered", active.turn_id, event.accepted)
        elif isinstance(event, ToolStarted):
            active.phase = "executing"
            self._call_tap("on_tool_started", active.turn_id, event.tool)
            self._publish_state(AgentState.EXECUTING, turn_id=active.turn_id)
            self._publish(
                active,
                "agent.tool_started",
                AgentToolStarted(**ids, tool=event.tool, call_id=event.call_id, source=event.source),
            )
        elif isinstance(event, ToolCompleted):
            self._publish(
                active,
                "agent.tool_completed",
                AgentToolCompleted(
                    **ids,
                    tool=event.tool,
                    call_id=event.call_id,
                    source=event.source,
                    error=event.error,
                ),
            )
            active.phase = "generating"
            self._publish_state(AgentState.THINKING, turn_id=active.turn_id)

    async def _close_turn(
        self, active: _ActiveTurn, terminal: TurnCompleted | TurnCancelled | TurnFailed
    ) -> None:
        """Commit, free the slot, and only then tell the GUI it may send again."""
        outcome, error_code, message_status, state = self._outcome_of(terminal)
        tail = active.stripper.flush()
        if tail:
            try:
                await self._emit_text(active, tail)
            except Exception:  # noqa: BLE001 - the terminal text below carries it anyway
                active.text.append(tail)
        for waiter in active.steer_waiters:
            if not waiter.done():
                waiter.set_result(False)
        # Expression tags are spoken, never stored nor shown (V-15): the terminal text too.
        completed_text = strip_tags(terminal.text) if isinstance(terminal, TurnCompleted) else None
        text = completed_text if completed_text is not None else "".join(active.text)
        try:
            if isinstance(terminal, TurnCompleted):
                await self._ensure_message(active)
            await self.store.finish_turn(
                active.turn_id, outcome, error_code, active.message_id, text, message_status
            )
        except Exception as exc:  # noqa: BLE001 - the reply still reaches the GUI
            logger.error(
                "turn not persisted",
                extra={"event": "chat_persist_failed", "kind": type(exc).__name__},
            )
        finally:
            self._end_turn(active)
        logger.info(
            "turn finished",
            extra={
                "event": "turn_finished",
                "turn_id": str(active.turn_id),
                "outcome": outcome,
                "source": active.source,
                # Accepted → first text delta in the backend, and the whole turn (latency).
                "first_delta_ms": active.first_delta_ms,
                "total_ms": round((time.monotonic() - active.started) * 1000),
                # "token" is a redacted key word: input_tokens → usage_input.
                **{
                    f"usage_{key.removesuffix('_tokens')}": value
                    for key, value in (terminal.usage if isinstance(terminal, TurnCompleted) else {}).items()
                },
            },
        )
        ids = {"session_id": active.session_id, "turn_id": active.turn_id}
        if isinstance(terminal, TurnCompleted) and active.message_id is not None:
            self._publish(
                active,
                "agent.message_completed",
                AgentMessageCompleted(**ids, message_id=active.message_id, text=text),
            )
        if isinstance(terminal, TurnFailed):
            self._publish(
                active,
                "agent.error",
                AgentError(
                    **ids,
                    code=terminal.code,
                    message=terminal.message,
                    retryable=terminal.retryable,
                ),
            )
        self._publish(active, "agent.turn_finished", AgentTurnFinished(**ids, outcome=outcome))
        tap_outcome: Outcome = outcome if outcome in ("completed", "cancelled") else "failed"
        self._call_tap("on_terminal", active.turn_id, tap_outcome)
        # success/error/interrupted are transients in the arbiter; then back to idle or offline.
        self._publish_state(state, reason=outcome, turn_id=active.turn_id)
        self._sync_provider_state()
        if isinstance(terminal, TurnCompleted) and terminal.pending_steer:
            if active.echoed_steers:
                self._follow_up(active.session_id, terminal.pending_steer, active.source)
            else:
                # Accepted only after `steer()` gave up (timeout): its caller already queued
                # the text as a turn of its own, so reopening it here would run it twice.
                logger.info("pending steer left to its caller", extra={"event": "steer_follow_up_skipped"})

    def _follow_up(self, session_id: UUID, text: str, source: Source) -> None:
        """A correction Hermes accepted but never consumed becomes the next turn. It is
        already in the chat (`_echo_steer`), so the new turn does not repeat it."""

        async def run() -> None:
            try:
                await self.submit_message(session_id, text, None, source=source, echoed=True)
            except Exception as exc:  # noqa: BLE001 - lost, like a message sent while busy
                logger.warning(
                    "pending steer not resubmitted",
                    extra={"event": "steer_follow_up_failed", "kind": type(exc).__name__},
                )

        task = asyncio.create_task(run())
        self._follow_ups.add(task)
        task.add_done_callback(self._follow_ups.discard)

    @staticmethod
    def _outcome_of(
        terminal: TurnCompleted | TurnCancelled | TurnFailed,
    ) -> tuple[TurnStatus, str | None, MessageStatus, AgentState]:
        if isinstance(terminal, TurnCompleted):
            return "completed", None, "complete", AgentState.SUCCESS
        if isinstance(terminal, TurnCancelled):
            return "cancelled", None, "cancelled", AgentState.INTERRUPTED
        # A lost agent leaves the outcome unknown: that is not the same as a failure.
        status: TurnStatus = "interrupted" if terminal.code == ErrorCode.AGENT_DISCONNECTED else "failed"
        return status, terminal.code.value, "failed", AgentState.ERROR

    def observe_tool_outcome(self, name: str, ctx: Any, outcome: Any) -> None:
        """Hook on every agent tool result: announces pending confirmations to the GUI."""
        data = outcome.model_dump()
        if data.get("status") != "confirmation_required":
            return
        self.hub.publish(
            "confirmation.requested",
            ConfirmationRequested(
                action_id=data["action_id"],
                session_id=ctx.session_id,
                turn_id=ctx.turn_id,
                tool=name,
                summary=data["summary"],
                affected_count=data.get("affected_count"),
                expires_at=data["expires_at"],
            ),
            correlation_id=str(ctx.turn_id),
        )

    def _publish_state(
        self,
        state: AgentState,
        *,
        reason: str | None = None,
        turn_id: UUID | None = None,
    ) -> None:
        """The agent's signal to the arbiter, the only one that publishes agent.status_changed."""
        self.status_arbiter.signal("agent", state, turn_id=turn_id, reason=reason)
