from enum import StrEnum
from typing import Any

from ..common import ActorType, EntityType, Id, Instant, Origin
from ._base import OutModel


class AuditResult(StrEnum):
    SUCCESS = "success"
    DENIED = "denied"
    FAILED = "failed"
    CONFIRMATION_REQUIRED = "confirmation_required"


class AuditEventOut(OutModel):
    """Solo lectura: la auditoría es append-only (trigger `audit_immutable`); no hay Create/Update públicos.

    `params` sale de la lista blanca de `ToolSpec.audit`: nunca claves ni contenido de documentos.
    """

    seq: int
    id: Id
    occurred_at: Instant
    correlation_id: str
    actor_type: ActorType
    origin: Origin
    action: str
    tool_name: str | None = None
    entity_type: EntityType | None = None
    entity_id: Id | None = None
    affected_count: int | None = None
    params: dict[str, Any] | None = None
    params_hash: str | None = None
    changes: dict[str, Any] | None = None
    result: AuditResult
    error_code: str | None = None
    confirmation_id: Id | None = None
    duration_ms: int | None = None
    turn_id: Id | None = None
    tainted: bool = False
    agent_provider: str | None = None
