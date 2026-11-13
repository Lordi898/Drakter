"""Common entry for MCP, REST and DevProvider. Never raises; the result is the outcome."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from drakter_contracts.common import Origin
from drakter_contracts.errors import ErrorCode
from drakter_contracts.tools import ToolErrorBody, ToolFailed
from pydantic import ValidationError

from app.audit.writer import AuditEvent
from app.permissions.models import ActorContext, Principal
from app.services.actions import ActionService


def _failed(code: ErrorCode, message: str, details: list[dict[str, Any]] | None = None) -> ToolFailed:
    return ToolFailed(
        error=ToolErrorBody(code=code.value, message=message, details=details or [])
    )


def _refuse(
    actions: ActionService, ctx: ActorContext, tool: str, code: ErrorCode, message: str, **extra: Any
) -> dict[str, Any]:
    conn = actions.open()
    try:
        actions._write_alone(  # noqa: SLF001 - same pipeline, unknown tools have no spec
            conn, ctx, AuditEvent(action=tool, result="denied", error_code=code.value)
        )
    finally:
        conn.close()
    return _failed(code, message, **extra).model_dump(mode="json")


def dispatch(
    tool: str, raw_args: Mapping[str, Any], ctx: ActorContext, *, actions: ActionService
) -> dict[str, Any]:
    """Registered -> active turn -> valid arguments -> the gate. The order is fixed."""
    try:
        spec = actions.registry.get(tool)
        if spec is None:
            return _refuse(actions, ctx, tool[:64], ErrorCode.PERMISSION_DENIED, "Unknown tool")
        is_agent = ctx.principal is Principal.AGENT
        if (is_agent and not ctx.turn_id) or (ctx.origin is Origin.MCP and not is_agent):
            return _refuse(actions, ctx, tool, ErrorCode.NO_ACTIVE_TURN, "No active turn")
        try:
            params = spec.args_model.model_validate(dict(raw_args))
        except ValidationError as exc:
            details = [
                {
                    "field": ".".join(str(part) for part in error["loc"]),
                    "code": error["type"],
                    "message": error["msg"],
                }
                for error in exc.errors(include_url=False, include_input=False, include_context=False)
            ]
            return _refuse(
                actions, ctx, tool, ErrorCode.VALIDATION_ERROR, "Invalid arguments", details=details
            )
        return actions.execute_or_request(ctx, spec, params).model_dump(mode="json")
    except Exception:  # noqa: BLE001 - if it cannot be audited it does not run
        return _failed(ErrorCode.INTERNAL_ERROR, "Tool failed").model_dump(mode="json")
