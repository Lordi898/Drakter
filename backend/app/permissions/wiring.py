"""Connects the modules' confirmation ports to `pending_confirmations` and `ActionService`.

`app/main.py` calls `wire_security` in `_install_services` and `start_security` /
`stop_security` in `lifespan` (README.md). Without it every destructive operation fails
closed with `confirmation_unavailable`.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

from drakter_contracts.common import format_instant
from drakter_contracts.events import EVENTS
from fastapi import FastAPI

from app.core.config import Settings
from app.permissions.canonical import (
    after,
    canonical_json,
    compute_params_hash,
    utc_now,
)
from app.permissions.models import ACTOR_TYPES, ActorContext
from app.permissions.setup import install_security
from app.services.actions import (
    CONFIRMATION_TTL_SECONDS,
    ActionService,
    ConfirmedExecutor,
)

logger = logging.getLogger("drakter.security")

REPO_ROOT: Final = Path(__file__).resolve().parents[3]
AGENT_GRANTS: Final = REPO_ROOT / "agent/configuration/permissions.json"
PORTS_STATE_KEY: Final = "workspace_ports"  # app/api/tasks_http.py and app/tools/tasks.py
_MAX_SUMMARY: Final = 500
# Rows and executors of the task/project services. The prefix keeps them apart from the
# agent tools `delete_task`, `update_task` and `complete_task`: executors win over the
# registry in `approve`, so a shared name would run the service executor on a tool's row.
WORKSPACE_PREFIX: Final = "workspace_"


def _clean_summary(text: str) -> str:
    cleaned = "".join(" " if not char.isprintable() else char for char in text)
    return cleaned if len(cleaned) <= _MAX_SUMMARY else f"{cleaned[: _MAX_SUMMARY - 1]}…"


class PendingConfirmationGate:
    """`tasks_ports.ConfirmationGate`: stores the pending row; `approve` runs it later."""

    def __init__(self, ttl_seconds: float = CONFIRMATION_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds

    def request(
        self,
        conn: sqlite3.Connection,
        *,
        actor: Any,
        tool_name: str,
        args: Mapping[str, Any],
        summary: str,
        affected_count: int,
        targets: Sequence[Any],
    ) -> Any:
        from app.schemas.tasks import ConfirmationTicket

        tool_name = WORKSPACE_PREFIX + tool_name
        canonical = canonical_json(dict(args))
        digest = compute_params_hash(tool_name, canonical)
        stored_targets = canonical_json(
            [{"entity_id": t.entity_id, "revision": t.revision} for t in targets]
        )
        now = utc_now()
        action_id, expires_at = str(uuid4()), format_instant(after(now, self._ttl))
        text = _clean_summary(summary)
        if conn.in_transaction:
            raise RuntimeError("A confirmation is requested outside any open transaction")
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "INSERT INTO pending_confirmations (id, tool_name, actor_type, origin, "
                "correlation_id, args_json, args_hash, targets_json, summary, affected_count, "
                "risk, status, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirm', 'pending', ?, ?)",
                (
                    action_id, tool_name, actor.actor_type, actor.origin, actor.correlation_id,
                    canonical, digest, stored_targets, text, affected_count,
                    format_instant(now), expires_at,
                ),
            )  # fmt: skip
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        # `confirmation.requested` goes out on the next sweeper tick (announce_pending).
        return ConfirmationTicket(
            id=action_id,
            summary=text,
            affected_count=affected_count,
            expires_at=expires_at,
            params_hash=digest,
        )


class HubEventSink:
    """`tasks_ports.EventSink` on top of the event hub. Called after COMMIT: never raises."""

    def __init__(self, hub: Any) -> None:
        self._hub = hub

    def publish(self, event_type: str, payload: Mapping[str, Any]) -> None:
        try:
            self._hub.publish(event_type, EVENTS[event_type].model_validate(dict(payload)))
        except Exception:
            logger.exception("event not published", extra={"event": "event_publish_failed"})


def _stored_targets(conn: sqlite3.Connection, tool: str, args: Mapping[str, Any]) -> list[Any]:
    """Targets of the row this approval claimed (status `executing`, same tool and hash)."""
    from app.services.tasks_ports import ConfirmationTarget

    digest = compute_params_hash(tool, canonical_json(dict(args)))
    row = conn.execute(
        "SELECT targets_json FROM pending_confirmations WHERE status = 'executing' "
        "AND tool_name = ? AND args_hash = ? ORDER BY created_at DESC LIMIT 1",
        (tool, digest),
    ).fetchone()
    if row is None:
        raise RuntimeError("The approved confirmation is not executing")
    return [ConfirmationTarget(t["entity_id"], t["revision"]) for t in json.loads(row[0])]


def _workspace_executor(
    run: Callable[..., Any], tool: str, ports: Any
) -> ConfirmedExecutor:
    def execute(conn: sqlite3.Connection, ctx: ActorContext, args: Mapping[str, Any]) -> Any:
        from app.services.tasks_ports import Actor, ServiceContext

        conn.row_factory = sqlite3.Row
        actor = Actor(
            actor_type=ACTOR_TYPES[ctx.principal].value,
            origin=ctx.origin.value,
            correlation_id=ctx.correlation_id,
            tool_name=tool,
        )
        targets = _stored_targets(conn, WORKSPACE_PREFIX + tool, args)
        result = run(ServiceContext(conn=conn, actor=actor, ports=ports), args, targets)
        return result if isinstance(result, Mapping) else {}

    return execute


def workspace_executors(ports: Any) -> dict[str, ConfirmedExecutor]:
    """Approved tasks and projects. Absent fronts contribute nothing."""
    executors: dict[str, ConfirmedExecutor] = {}
    try:
        from app.services.projects import PROJECT_CONFIRMABLE
        from app.services.tasks import TASK_CONFIRMABLE
    except ModuleNotFoundError:
        return executors
    for table in (TASK_CONFIRMABLE, PROJECT_CONFIRMABLE):
        for tool, run in table.items():
            executors[WORKSPACE_PREFIX + tool] = _workspace_executor(run, tool, ports)
    return executors


def wire_security(app: FastAPI, settings: Settings) -> ActionService:
    """After `app.state.event_hub` exists and before the app starts serving."""
    actions = install_security(app, settings, agent_grants_path=AGENT_GRANTS)
    try:
        from app.services.calendar_actions import register_actions
    except ModuleNotFoundError:
        register_actions = None
    if register_actions is not None:
        register_actions(actions.registry)

    from app.services.tasks_ports import Ports

    hub = getattr(app.state, "event_hub", None)
    ports = Ports(
        confirmations=PendingConfirmationGate(),
        **({"events": HubEventSink(hub)} if hub is not None else {}),
    )
    setattr(app.state, PORTS_STATE_KEY, ports)
    for tool, executor in workspace_executors(ports).items():
        actions.add_executor(tool, executor)
    runtime = getattr(app.state, "agent_runtime", None)
    if runtime is not None:
        # Agent tools reach the same gate through `ToolContext.state`.
        setattr(runtime.tool_state, PORTS_STATE_KEY, ports)
    return actions
