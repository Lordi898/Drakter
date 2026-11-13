"""Assembles the agent side of the backend and runs each conversation turn.

Nothing here can take the backend down: without Hermes or tools, the API stays up and
the agent reports `offline`.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Final
from uuid import UUID, uuid4

from drakter_contracts.errors import HTTP_STATUS, ErrorCode
from drakter_contracts.events import (
    AgentError,
    AgentMessageCompleted,
    AgentMessageDelta,
    AgentMessageStarted,
    AgentState,
    AgentStatusChanged,
    AgentToolCompleted,
    AgentToolStarted,
    AgentTurnFinished,
    AgentTurnStarted,
    ConfirmationRequested,
    SystemHealthChanged,
)
from pydantic import BaseModel

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import SessionToken
from app.events import EventHub
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

if TYPE_CHECKING:
    from app.integrations.hermes.settings import AgentSettings

logger = logging.getLogger("drakter.agent.runtime")

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
STOP_TURN_GRACE_S: Final = 12.0
# success/error/interrupted are moments for the character, not resting states.
SETTLE_DELAY_S: Final = 1.5


def _agent_error(code: ErrorCode) -> AppError:
    return AppError(code.value, SAFE_MESSAGES[code], HTTP_STATUS[code])


def _not_found(message: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND.value, message, HTTP_STATUS[ErrorCode.NOT_FOUND])


@dataclass(slots=True)
class _ActiveTurn:
    session_id: UUID
    turn_id: UUID
    text: list[str] = field(default_factory=list)
    message_id: UUID | None = None
    task: asyncio.Task[None] | None = None

    @property
    def correlation_id(self) -> str:
        return str(self.turn_id)


class AgentRuntime:
    def __init__(self, settings: Settings, agent_settings: AgentSettings | None = None) -> None:
        from app.integrations.hermes.settings import AgentSettings as LoadedSettings

        self.settings = settings
        self.agent_settings = agent_settings or LoadedSettings()
        self.hub = EventHub()
        self.store = SqliteChatStore(settings.db_path)
        self.registry: Any | None = None
        self.turns: Any | None = None
        self.provider: AgentProvider | None = None
        # What ToolContext.state exposes; tools only read `agent_runtime` and `settings`.
        self.tool_state = SimpleNamespace(agent_runtime=self, settings=settings)
        self._tools_server: Any | None = None
        self._supervisor: Any | None = None
        self._boot_task: asyncio.Task[None] | None = None
        self._active: _ActiveTurn | None = None
        self._state = AgentState.OFFLINE
        self._health: tuple[str, str | None] | None = None
        self._settle: asyncio.TimerHandle | None = None

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
        try:
            from app.tools.registry import ToolRegistry, load_builtin_tools
            from app.tools.turns import TurnTracker

            turns = TurnTracker()
            registry = ToolRegistry(turns)
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
        if self._settle is not None:
            self._settle.cancel()
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
        provider = self.provider
        status = provider.status() if provider is not None else None
        state = self._state
        if status is not None and status.state != "ready":
            state = AgentState.OFFLINE
        return {
            "state": state.value,
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

    async def submit_message(
        self, session_id: UUID, text: str, client_message_id: UUID | None
    ) -> tuple[UUID, UUID]:
        """Accept a user message and start its turn. Returns (turn_id, message_id)."""
        session = await self._require_session(session_id)
        if session.status != "open":
            raise AppError(ErrorCode.CONFLICT.value, "La sesión está cerrada.", 409)
        if client_message_id is not None:
            existing = await self.store.find_client_message(session_id, client_message_id)
            if existing is not None:
                return existing.turn_id, existing.id
        provider = self._require_provider()
        turn_id = uuid4()
        active = self._reserve_turn(session_id, turn_id)
        try:
            message, created = await self.store.begin_turn(
                session_id, turn_id, text, client_message_id
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
        if self._settle is not None:
            self._settle.cancel()
        self._publish(
            active,
            "agent.turn_started",
            AgentTurnStarted(session_id=session_id, turn_id=turn_id),
        )
        self._publish_state(AgentState.THINKING, turn_id=turn_id)
        request = TurnRequest(session_id=session_id, turn_id=turn_id, text=text)
        active.task = asyncio.create_task(self._run_turn(provider, request, active))
        return turn_id, message.id

    def _publish(self, active: _ActiveTurn, event_type: str, payload: BaseModel) -> None:
        self.hub.publish(event_type, payload, correlation_id=active.correlation_id)

    def _reserve_turn(self, session_id: UUID, turn_id: UUID) -> _ActiveTurn:
        """Admission: synchronous, so two requests cannot both get through."""
        if self._active is not None:
            raise _agent_error(ErrorCode.AGENT_BUSY)
        if self.turns is not None:
            from app.tools.turns import TurnBusyError

            try:
                self.turns.begin(session_id, turn_id)
            except TurnBusyError:
                raise _agent_error(ErrorCode.AGENT_BUSY) from None
        self._active = _ActiveTurn(session_id=session_id, turn_id=turn_id)
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

    async def _handle_event(self, active: _ActiveTurn, event: Any) -> None:
        ids = {"session_id": active.session_id, "turn_id": active.turn_id}
        if isinstance(event, Thinking):
            self._publish_state(AgentState.THINKING, turn_id=active.turn_id)
        elif isinstance(event, MessageDelta):
            await self._ensure_message(active)
            active.text.append(event.text)
            self._publish_state(AgentState.SPEAKING, turn_id=active.turn_id)
            self._publish(
                active, "agent.message_delta", AgentMessageDelta(**ids, delta=event.text)
            )
        elif isinstance(event, ToolStarted):
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
            self._publish_state(AgentState.THINKING, turn_id=active.turn_id)

    async def _close_turn(
        self, active: _ActiveTurn, terminal: TurnCompleted | TurnCancelled | TurnFailed
    ) -> None:
        """Commit, free the slot, and only then tell the GUI it may send again."""
        outcome, error_code, message_status, state = self._outcome_of(terminal)
        text = terminal.text if isinstance(terminal, TurnCompleted) else "".join(active.text)
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
            extra={"event": "turn_finished", "turn_id": str(active.turn_id), "outcome": outcome},
        )
        ids = {"session_id": active.session_id, "turn_id": active.turn_id}
        if isinstance(terminal, TurnCompleted) and active.message_id is not None:
            self._publish(
                active,
                "agent.message_completed",
                AgentMessageCompleted(**ids, message_id=active.message_id, text=terminal.text),
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
        self._publish_state(state, reason=outcome, turn_id=active.turn_id)
        self._settle = asyncio.get_running_loop().call_later(
            SETTLE_DELAY_S, self._sync_provider_state
        )

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
        """Publishes changes, and always the end of a turn: the GUI needs that signal."""
        if state == self._state and reason is None:
            return
        previous, self._state = self._state, state
        self.hub.publish(
            "agent.status_changed",
            AgentStatusChanged(state=state, previous=previous, turn_id=turn_id, reason=reason),
            correlation_id=str(turn_id) if turn_id else None,
        )
