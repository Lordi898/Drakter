"""Job lanes (voz v2, V-24): a second Hermes, isolated from the foreground one.

A `Lane` groups its own `TurnTracker`, a `ToolRegistry` without `jobs_*`, an
`AgentToolsServer` with its own `SessionToken` on an ephemeral port, a `HermesSupervisor`
with its own home (`hermes-w1`) and a `HermesProvider`. Gate and audit are the foreground's
(`runtime.tool_wiring`), so every call is authorized and audited the same way.

The foreground `AgentRuntime` is not built on `Lane` (deferred in the plan). One turn at a
time per lane; the `JobManager` decides what runs on it.
"""

from __future__ import annotations

import inspect
import logging
import secrets
from collections.abc import AsyncIterator, Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, Final
from uuid import UUID

from app.core.config import ensure_private_dir
from app.core.security import SessionToken
from app.integrations.hermes.events import AgentEvent
from app.integrations.hermes.provider import AgentProvider, ProviderStatus, TurnRequest
from app.tools.registry import ToolObserver, ToolRegistry, load_builtin_tools
from app.tools.spec import ToolContext
from app.tools.turns import TurnBusyError, TurnTracker

logger = logging.getLogger("drakter.agent.lanes")

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
# A worker never starts or steers jobs, nor switches the desktop UI under the user.
EXCLUDED_DOMAINS: Final = frozenset({"jobs", "ui"})


class LaneBusy(RuntimeError):
    """The lane already runs a turn."""


class LaneRegistry(ToolRegistry):
    """Stamps `ctx.job_id` on every call: Hermes sends no identity over MCP (F19)."""

    def __init__(self, *args: Any, job_of: Callable[[], UUID | None], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._job_of = job_of

    async def dispatch(
        self,
        name: str,
        raw_args: dict[str, Any],
        ctx: ToolContext,
        *,
        observer: ToolObserver | None = None,
    ) -> Any:
        job_id = self._job_of()
        if job_id is not None and ctx.job_id is None:
            ctx = replace(ctx, job_id=job_id)
        return await super().dispatch(name, raw_args, ctx, observer=observer)


def _accepts(callable_: Any, *names: str) -> bool:
    try:
        params = inspect.signature(callable_).parameters
    except (TypeError, ValueError):
        return False
    return all(name in params for name in names)


class Lane:
    def __init__(self, name: str, home_name: str, effort: str, turn_timeout_s: float) -> None:
        self.name = name
        self.home_name = home_name
        self.effort = effort
        self.turn_timeout_s = turn_timeout_s
        self.turns = TurnTracker()
        self.registry: LaneRegistry | None = None
        self.provider: AgentProvider | None = None
        self.current_job_id: UUID | None = None
        self._server: Any | None = None
        self._supervisor: Any | None = None

    # Lifecycle

    async def start(self, runtime: Any, observer: ToolObserver) -> None:
        """Never raises: a lane that cannot start stays `offline` (`lane_unavailable`)."""
        try:
            await self._start(runtime, observer)
        except Exception as exc:  # noqa: BLE001 - a job lane must not take the backend down
            logger.error(
                "job lane not started",
                extra={"event": "lane_start_failed", "lane": self.name, "kind": type(exc).__name__},
            )

    async def _start(self, runtime: Any, observer: ToolObserver) -> None:
        wiring = dict(getattr(runtime, "tool_wiring", {}) or {})
        everything = ToolRegistry(self.turns, **wiring)
        load_builtin_tools(everything)
        registry = LaneRegistry(self.turns, **wiring, job_of=lambda: self.current_job_id)
        for spec in everything.catalog():
            if spec.domain not in EXCLUDED_DOMAINS:
                registry.register(spec)
        self.registry = registry
        settings = runtime.agent_settings.model_copy(update={"turn_timeout_s": self.turn_timeout_s})
        if settings.agent_provider == "fake":
            from app.integrations.hermes.fake import FakeProvider

            self.provider = FakeProvider(registry, runtime.tool_state, observer)
            await self.provider.start()
            return
        from app.integrations.hermes.hermes_provider import HermesProvider
        from app.integrations.hermes.supervisor import HermesSupervisor
        from app.tools.mcp_bridge import AgentToolsServer, build_agent_tools_app

        token = SessionToken(secrets.token_urlsafe(32))
        app = build_agent_tools_app(
            registry, self.turns, token, runtime.tool_state, observer=observer
        )
        self._server = AgentToolsServer(app)
        await self._server.start()
        self._supervisor = self._make_supervisor(
            HermesSupervisor, settings, runtime.settings.data_dir, registry, token
        )
        self.provider = HermesProvider(
            settings,
            self._supervisor,
            REPO_ROOT,
            memory=lambda: getattr(runtime.tool_state, "memory_service", None),
            turns=self.turns,
        )
        await self.provider.start()
        await self._supervisor.start()  # returns at once; the runner boots in the background

    def _make_supervisor(
        self, cls: Any, settings: Any, data_dir: Path, registry: ToolRegistry, token: Any
    ) -> Any:
        assert self._server is not None
        args = (settings, data_dir, [s.name for s in registry.catalog()], token, self._server.url, REPO_ROOT)
        if _accepts(cls, "home_name", "reasoning_effort"):
            return cls(*args, home_name=self.home_name, reasoning_effort=self.effort)
        # Without WP6's kwargs: an own data dir keeps the home and its log apart, but the
        # lane runs with the default effort.
        logger.warning(
            "supervisor without home_name; lane uses its own data dir",
            extra={"event": "lane_home_fallback", "lane": self.name},
        )
        lanes_dir = data_dir / "lanes"
        ensure_private_dir(lanes_dir)
        own = lanes_dir / self.name
        ensure_private_dir(own)
        return cls(settings, own, *args[2:])

    async def stop(self) -> None:
        for label, closer in (
            ("provider", self.provider.stop if self.provider else None),
            ("supervisor", self._supervisor.stop if self._supervisor else None),
            ("tools", self._server.stop if self._server else None),
        ):
            if closer is None:
                continue
            try:
                await closer()
            except Exception as exc:  # noqa: BLE001 - one piece must not block the others
                logger.warning(
                    "lane piece did not stop cleanly",
                    extra={"event": "lane_stop_failed", "lane": self.name, "piece": label,
                           "kind": type(exc).__name__},
                )  # fmt: skip

    # State

    def status(self) -> ProviderStatus:
        if self.provider is None:
            return ProviderStatus("offline", "El carril de trabajos no está disponible.")
        return self.provider.status()

    def ready(self) -> bool:
        return self.status().state == "ready"

    @property
    def busy(self) -> bool:
        return self.current_job_id is not None or self.turns.active() is not None

    @property
    def child_pid(self) -> int | None:
        return getattr(self._supervisor, "child_pid", None)

    # Turns

    async def create_session(self) -> UUID:
        assert self.provider is not None
        return await self.provider.create_session()

    def mark_tainted(self, session_id: UUID) -> None:
        self.turns.mark_tainted(session_id)

    def is_tainted(self, session_id: UUID) -> bool:
        return self.turns.is_tainted(session_id)

    async def stream_turn(self, request: TurnRequest) -> AsyncIterator[AgentEvent]:
        """Admit the turn in the lane's tracker (MCP calls are attributed to it) and stream it."""
        if self.provider is None:
            raise LaneBusy("lane not started")
        try:
            self.turns.begin(request.session_id, request.turn_id)
        except TurnBusyError:
            raise LaneBusy("lane busy") from None
        stream = self.provider.stream_turn(request)
        try:
            async for event in stream:
                yield event
        finally:
            await stream.aclose()  # type: ignore[attr-defined]
            self.turns.end(request.turn_id)

    async def cancel(self, turn_id: UUID) -> None:
        if self.provider is not None:
            await self.provider.cancel(turn_id)

    @property
    def can_steer(self) -> bool:
        return callable(getattr(self.provider, "steer_turn", None))

    async def steer(self, turn_id: UUID, text: str) -> bool | None:
        """`True`/`False` if the provider answered now; `None` if the answer comes later as a
        `steered` event in the turn stream (or the provider cannot steer: see `can_steer`)."""
        if not self.can_steer:
            return None
        result = self.provider.steer_turn(turn_id, text)  # type: ignore[union-attr]
        if inspect.isawaitable(result):
            result = await result
        return result if isinstance(result, bool) else None
