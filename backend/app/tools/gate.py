"""Authorization and audit interfaces, plus their provisional defaults.

``drakter/seguridad`` provides the real implementations behind these Protocols.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from drakter_contracts.errors import ErrorCode
from pydantic import BaseModel

from app.tools.spec import RiskClass, ToolContext, ToolSpec


def confirm_reason(spec: ToolSpec, args: BaseModel | None) -> str | None:
    """Reason from ``spec.confirm_if`` for a WRITE, or None. A failing hook demands confirmation."""
    if spec.risk is not RiskClass.WRITE or spec.confirm_if is None or args is None:
        return None
    try:
        reason = spec.confirm_if(args)
    except Exception:  # noqa: BLE001 - fail closed: an unknown answer means "ask the user"
        logging.getLogger("drakter.tools").exception(
            "confirm_if failed", extra={"event": "tool_confirm_if_failed", "tool": spec.name}
        )
        return "Hay que confirmar esta acción."
    return reason.strip() if isinstance(reason, str) and reason.strip() else None


def effective_risk(
    spec: ToolSpec, *, tainted: bool, args: BaseModel | None = None
) -> RiskClass:
    """A WRITE in a tainted session needs the same confirmation as a CONFIRM (F08).

    So does a WRITE whose ``confirm_if`` gives a reason for these arguments.
    This covers `jobs_start` and `jobs_cancel` too (V-26). A call from a job lane carries
    `ctx.job_id`; the lane's observer copies it to `confirmation.requested.job_id`.
    """
    if spec.risk is RiskClass.WRITE and (tainted or confirm_reason(spec, args) is not None):
        return RiskClass.CONFIRM
    return spec.risk


@dataclass(frozen=True, slots=True)
class GateDecision:
    kind: Literal["allow", "deny", "confirm"]
    code: str | None = None
    message: str | None = None
    action_id: str | UUID | None = None
    summary: str | None = None
    expires_at: datetime | str | None = None


class ToolGate(Protocol):
    async def authorize(
        self, spec: ToolSpec, args: BaseModel, ctx: ToolContext, *, tainted: bool
    ) -> GateDecision: ...


@dataclass(frozen=True, slots=True)
class ToolAuditEvent:
    """``args`` already has the per-argument policy applied: sinks never receive raw values."""

    phase: Literal["attempt", "result", "rejected"]
    tool: str
    turn_id: UUID
    session_id: UUID
    call_id: str
    principal: str
    tainted: bool
    outcome: Literal["pending", "ok", "error", "confirmation_required"]
    code: str | None = None
    permission: str | None = None
    risk: str | None = None
    effective_risk: str | None = None
    args: Mapping[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None
    # Images of the result: only sha256, width and height, never the pixels.
    attachments: tuple[Mapping[str, Any], ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuditSink(Protocol):
    async def record(self, event: ToolAuditEvent) -> None:
        """If this raises, the tool does not run (fail-closed)."""
        ...


def audit_args(spec: ToolSpec, args: BaseModel) -> dict[str, Any]:
    """Apply the policy of each argument. Anything not listed is hashed."""
    audited: dict[str, Any] = {}
    for key, value in args.model_dump(mode="json").items():
        policy = spec.audit.get(key, "hash")
        if policy == "log":
            audited[key] = value
        elif policy == "hash":
            canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
            audited[key] = {"sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}
    return audited


class DefaultToolGate:
    """Provisional until ``drakter/seguridad``: there is no confirmation flow behind it.

    READ and WRITE pass; anything that needs confirmation, or an unknown risk, is denied.
    """

    async def authorize(
        self, spec: ToolSpec, args: BaseModel, ctx: ToolContext, *, tainted: bool
    ) -> GateDecision:
        risk = effective_risk(spec, tainted=tainted, args=args)
        if risk is RiskClass.READ or risk is RiskClass.WRITE:
            return GateDecision(kind="allow")
        if risk is RiskClass.CONFIRM:
            return GateDecision(
                kind="deny",
                code=ErrorCode.CONFIRMATION_UNAVAILABLE,
                message="This action needs user confirmation, which is not available yet.",
            )
        return GateDecision(
            kind="deny", code=ErrorCode.PERMISSION_DENIED, message="Action not allowed."
        )


class LogAuditSink:
    """Provisional until ``drakter/seguridad``: one JSON event per call on ``drakter.audit``.

    Only a log, not the ``audit_events`` table. ``logging`` swallows handler errors, so a
    full disk does not stop execution here; the real sink must fail closed.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("drakter.audit")

    async def record(self, event: ToolAuditEvent) -> None:
        payload = {
            "event": "tool_audit",
            "phase": event.phase,
            "tool": event.tool,
            "permission": event.permission,
            "risk": event.risk,
            "effective_risk": event.effective_risk,
            "outcome": event.outcome,
            "code": event.code,
            "tainted": event.tainted,
            "principal": event.principal,
            "turn_id": str(event.turn_id),
            "session_id": str(event.session_id),
            "call_id": event.call_id,
            "tool_args": dict(event.args),  # logging reserves the key "args"
            "duration_ms": event.duration_ms,
            "attachments": [dict(a) for a in event.attachments],
            "at": event.timestamp.isoformat(),
        }
        json.dumps(payload)  # a value that cannot be serialized fails here, not in the handler
        self._logger.info("tool_audit", extra=payload)
