from enum import StrEnum
from typing import Any, Literal

from ..common import ActorType, ContractModel, Id, Instant, Origin
from ._base import OutModel


class ConfirmationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"


class ConfirmationRisk(StrEnum):
    WRITE = "write"
    CONFIRM = "confirm"


class ConfirmationTarget(OutModel):
    entity_type: str
    entity_id: Id
    revision: int | None = None


class ConfirmationCreate(ContractModel):
    """Uso interno del backend; ninguna ruta pública la acepta. Los textos los calcula el backend."""

    tool_name: str
    actor_type: ActorType
    origin: Origin
    turn_id: Id | None = None
    correlation_id: str
    args: dict[str, Any]
    targets: list[ConfirmationTarget] = []
    summary: str
    affected_count: int | None = None
    risk: ConfirmationRisk


class ConfirmationDecision(ContractModel):
    """Cuerpo (vacío salvo nota) de approve|reject; la decisión es la ruta."""

    reason: str | None = None


ConfirmationUpdate = ConfirmationDecision


class ConfirmationOut(OutModel):
    """`args` ya sin secretos (lista blanca de auditoría). `decided_via` solo vale `desktop`."""

    id: Id
    tool_name: str
    actor_type: ActorType
    origin: Origin
    turn_id: Id | None = None
    correlation_id: str
    args: dict[str, Any] = {}
    args_hash: str
    targets: list[ConfirmationTarget] = []
    summary: str
    affected_count: int | None = None
    risk: ConfirmationRisk
    status: ConfirmationStatus
    created_at: Instant
    expires_at: Instant
    decided_at: Instant | None = None
    decided_via: Literal["desktop"] | None = None
    executed_at: Instant | None = None
    result: dict[str, Any] | None = None
    error_code: str | None = None
