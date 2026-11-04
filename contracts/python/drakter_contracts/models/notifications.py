from enum import StrEnum
from typing import Annotated

from pydantic import Field

from ..common import ContractModel, Id, Instant
from ._base import OutModel


class NotificationSeverity(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationCreate(ContractModel):
    kind: Annotated[str, Field(min_length=1, max_length=64)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    body: Annotated[str, Field(max_length=2000)] | None = None
    severity: NotificationSeverity = NotificationSeverity.INFO
    entity_id: Id | None = None
    dedupe_key: Annotated[str, Field(max_length=200)] | None = None


class NotificationUpdate(ContractModel):
    """PATCH: marcar leída (`true`) o no leída (`false`)."""

    read: bool | None = None


class NotificationOut(OutModel):
    """No es entidad: sin revision ni archived_at."""

    id: Id
    kind: str
    title: str
    body: str | None = None
    severity: NotificationSeverity
    entity_id: Id | None = None
    created_at: Instant
    read_at: Instant | None = None
    dedupe_key: str | None = None
