"""Thin ports shared by the improvement and backup services.

The real confirmation gate, audit trail and principal resolution belong to the
security front. Until they are wired, every default here fails closed: nothing
that needs a human approval can run. Integration replaces only the objects
stored on ``app.state``; no service changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Final, Literal, Protocol

from fastapi import Request

from app.core.errors import AppError

logger = logging.getLogger("drakter.improvement")

PrincipalKind = Literal["user", "agent", "system"]


@dataclass(frozen=True)
class Principal:
    """Who is acting. Derived from the credential, never from the request body."""

    kind: PrincipalKind
    id: str


UNKNOWN_AGENT: Final = Principal(kind="agent", id="unresolved")


@dataclass(frozen=True)
class ApprovalRequest:
    """What a human is asked to approve. ``digest`` binds approval to exact content."""

    action: str
    target_id: str
    digest: str
    summary: str


@dataclass(frozen=True)
class AuditEvent:
    """Matches ``audit_events`` (ROADMAP 8.1). ``detail`` must never carry secrets."""

    actor_type: PrincipalKind
    action: str
    entity_type: str
    entity_id: str
    result: Literal["ok", "denied", "failed"]
    correlation_id: str | None = None
    detail: dict[str, str | int | bool | None] = field(default_factory=dict)


class ConfirmationGate(Protocol):
    def request(self, approval: ApprovalRequest, principal: Principal) -> str:
        """Register a pending approval and return its confirmation id."""
        ...

    def consume(
        self, confirmation_id: str, approval: ApprovalRequest, principal: Principal
    ) -> None:
        """Atomically spend an approval granted from the GUI, or raise ``AppError``.

        Must reject a non-user principal, a wrong action, target or digest, an
        expired confirmation and any second use.
        """
        ...


class AuditSink(Protocol):
    def record(self, event: AuditEvent) -> None: ...


class DenyAllGate:
    """Default gate: without the real mechanism, nothing gets approved."""

    def request(self, approval: ApprovalRequest, principal: Principal) -> str:
        raise AppError(
            "confirmation_unavailable",
            "El mecanismo de confirmación no está disponible",
            503,
        )

    def consume(
        self, confirmation_id: str, approval: ApprovalRequest, principal: Principal
    ) -> None:
        raise AppError(
            "confirmation_unavailable",
            "El mecanismo de confirmación no está disponible",
            503,
        )


class LogAuditSink:
    """Interim sink: a structured log line, redacted by the JSON formatter."""

    def record(self, event: AuditEvent) -> None:
        logger.info(
            "audit",
            extra={
                "event": "audit",
                "actor_type": event.actor_type,
                "action": event.action,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "result": event.result,
                "correlation_id": event.correlation_id,
                "detail": event.detail,
            },
        )


def get_gate(request: Request) -> ConfirmationGate:
    gate: ConfirmationGate | None = getattr(request.app.state, "confirmation_gate", None)
    return gate if gate is not None else DenyAllGate()


def get_audit(request: Request) -> AuditSink:
    sink: AuditSink | None = getattr(request.app.state, "audit_sink", None)
    return sink if sink is not None else LogAuditSink()


def get_principal(request: Request) -> Principal:
    """Resolve the caller of a GUI route.

    Hermes reaches tools only through its own port and credential, so the GUI
    API serves the user. That fact is declared once, at wiring time, through
    ``app.state.gui_principal``; a per-request principal set by the guard wins.
    An unresolved caller counts as the agent, the least privileged kind.
    """
    scoped = request.scope.get("state", {}).get("principal")
    if isinstance(scoped, Principal):
        return scoped
    declared = getattr(request.app.state, "gui_principal", None)
    return declared if isinstance(declared, Principal) else UNKNOWN_AGENT


def require_user(principal: Principal) -> None:
    if principal.kind != "user":
        raise AppError(
            "user_required", "Esta operación solo puede hacerla el usuario", 403
        )
