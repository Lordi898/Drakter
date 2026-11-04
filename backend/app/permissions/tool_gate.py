"""Adapter from `app/tools/` (`ToolGate`, `AuditSink`) to the action service.

The `Protocol`s and dataclasses live in `app/tools/gate.py`. `decision` receives its
`GateDecision` so that this module does not depend on a branch not yet merged.
"""

from __future__ import annotations

import asyncio
import inspect
import sqlite3
from collections.abc import Callable, Mapping
from typing import Any

from drakter_contracts.common import Origin, format_instant
from drakter_contracts.tools import ToolConfirmationRequired, ToolFailed
from pydantic import BaseModel

from app.audit.writer import AuditEvent, filter_params, write
from app.permissions.models import ActionSpec, ActorContext, Principal, Verdict
from app.services.actions import ActionService


def tool_action_spec(tool: Any, make_context: Callable[[], Any]) -> ActionSpec:
    """Adapt a `ToolSpec`. Its handler opens its own connections, so it is `external`."""

    def handler(_conn: sqlite3.Connection, params: BaseModel) -> Mapping[str, Any]:
        result = tool.handler(make_context(), params)
        if inspect.isawaitable(result):
            # Approval runs in a worker thread, which has no running event loop.
            async def waited() -> Any:
                return await result

            result = asyncio.run(waited())
        return result.model_dump(mode="json")

    return ActionSpec(
        name=tool.name,
        permission=tool.permission,
        risk=tool.risk,
        args_model=tool.args_model,
        handler=handler,
        summarize=tool.summarize,
        audit=tool.audit,
        resolve_targets=getattr(tool, "resolve_targets", None),
        count_affected=getattr(tool, "count_affected", None),
        external=True,
    )


def _actor(ctx: Any, tainted: bool) -> ActorContext:
    return ActorContext(
        principal=Principal.AGENT,
        origin=Origin.MCP,
        correlation_id=str(ctx.turn_id),
        turn_id=str(ctx.turn_id),
        session_id=str(ctx.session_id),
        tainted=tainted,
    )


class BackendToolGate:
    """Implements `ToolGate`. A tool not adapted into the registry is denied."""

    def __init__(self, actions: ActionService, decision: Callable[..., Any]) -> None:
        self._actions = actions
        self._decision = decision

    async def authorize(self, spec: Any, args: BaseModel, ctx: Any, *, tainted: bool) -> Any:
        action = self._actions.registry.get(spec.name)
        if action is None:
            return self._decision(kind="deny", code="permission_denied", message="Unknown tool")
        verdict, outcome = await asyncio.to_thread(
            self._actions.authorize, _actor(ctx, tainted), action, args
        )
        if verdict is Verdict.ALLOW:
            return self._decision(kind="allow")
        if isinstance(outcome, ToolConfirmationRequired):
            return self._decision(
                kind="confirm",
                action_id=str(outcome.action_id),
                summary=outcome.summary,
                expires_at=format_instant(outcome.expires_at),
            )
        assert isinstance(outcome, ToolFailed)
        return self._decision(kind="deny", code=outcome.error.code, message=outcome.error.message)


class BackendAuditSink:
    """Implements `AuditSink`. Raises on failure, so the registry does not run the tool."""

    def __init__(self, actions: ActionService) -> None:
        self._actions = actions

    async def record(self, event: Any) -> None:
        await asyncio.to_thread(self._write, event)

    def _write(self, event: Any) -> None:
        ctx = ActorContext(
            principal=Principal.AGENT,
            origin=Origin.MCP,
            correlation_id=str(getattr(event, "turn_id", None) or "unknown"),
            turn_id=str(getattr(event, "turn_id", None) or "") or None,
            tainted=bool(getattr(event, "tainted", False)),
        )
        tool = getattr(event, "tool", None) or "unknown"
        spec = self._actions.registry.get(tool)
        args = getattr(event, "args", None) or {}
        conn = self._actions.open()
        try:
            write(
                conn,
                ctx,
                AuditEvent(
                    action=tool,
                    result=getattr(event, "result", None) or "success",
                    tool_name=tool,
                    params=filter_params(args, spec.audit) if spec else None,
                    error_code=getattr(event, "error_code", None),
                ),
            )
        finally:
            conn.close()
