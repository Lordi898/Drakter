"""Contrato de tareas: entrada, salida y consultas. Nada aquí toca la base."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Annotated, Any, Final, Generic, Literal, Self, TypeVar
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

TaskStatus = Literal["pending", "in_progress", "on_hold", "completed", "cancelled"]
# `completed` solo se alcanza con complete_task: así hay un único camino que comprueba
# subtareas y dependencias. Reabrir es reopen_task.
EditableTaskStatus = Literal["pending", "in_progress", "on_hold", "cancelled"]
Priority = Literal["low", "medium", "high", "urgent"]

MAX_TITLE: Final = 300
MAX_DESCRIPTION: Final = 20_000
MAX_TAGS: Final = 20
MAX_TAG_NAME: Final = 64
MAX_METADATA_BYTES: Final = 16_384
DEFAULT_LIMIT: Final = 50
MAX_LIMIT: Final = 200
MAX_OFFSET: Final = 1_000_000
TASK_SORT_FIELDS: Final = frozenset(
    {"position", "created_at", "updated_at", "due", "priority", "title"}
)


def to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def format_timestamp(value: datetime) -> str:
    """Formato único de C-13: `YYYY-MM-DDTHH:MM:SS.sssZ`."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


def check_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if len(json.dumps(value, ensure_ascii=False).encode()) > MAX_METADATA_BYTES:
        raise PydanticCustomError("metadata_too_large", "Los metadatos son demasiado grandes.")
    return value


UtcTimestamp = Annotated[
    AwareDatetime,
    AfterValidator(to_utc),
    PlainSerializer(format_timestamp, return_type=str, when_used="json"),
]
Title = Annotated[str, Field(min_length=1, max_length=MAX_TITLE)]
Description = Annotated[str, Field(max_length=MAX_DESCRIPTION)]
TagName = Annotated[str, Field(min_length=1, max_length=MAX_TAG_NAME)]
Metadata = Annotated[dict[str, Any], AfterValidator(check_metadata)]

T = TypeVar("T")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Page(Out, Generic[T]):
    """Listado de `contracts/README.md` §2: `total` cuenta todo lo que cumple el filtro."""

    items: list[T]
    total: int


class TagOut(Out):
    id: UUID
    name: str
    color: str | None = None


class TaskRef(Out):
    id: UUID
    title: str
    status: TaskStatus


class TaskCreate(Strict):
    title: Title
    description: Description | None = None
    status: EditableTaskStatus = "pending"
    priority: Priority = "medium"
    start_at: UtcTimestamp | None = None
    due_at: UtcTimestamp | None = None
    due_date: date | None = None
    estimated_minutes: Annotated[int, Field(ge=0, le=1_000_000)] | None = None
    parent_task_id: UUID | None = None
    project_id: UUID | None = None
    subject_id: UUID | None = None
    position: float | None = None
    tags: Annotated[list[TagName], Field(max_length=MAX_TAGS)] = []
    metadata: Metadata = {}

    @model_validator(mode="after")
    def _single_due(self) -> Self:
        if self.due_at is not None and self.due_date is not None:
            raise PydanticCustomError(
                "due_at_and_due_date", "Indica fecha límite con hora o sin hora, no las dos."
            )
        return self


class SubtaskCreate(TaskCreate):
    """El padre viene de la ruta o del argumento de la herramienta."""

    parent_task_id: None = None


class TaskUpdate(Strict):
    """PATCH: lo ausente no cambia; `null` borra si el campo lo admite (`model_fields_set`)."""

    title: Title | None = None
    description: Description | None = None
    status: EditableTaskStatus | None = None
    priority: Priority | None = None
    start_at: UtcTimestamp | None = None
    due_at: UtcTimestamp | None = None
    due_date: date | None = None
    estimated_minutes: Annotated[int, Field(ge=0, le=1_000_000)] | None = None
    parent_task_id: UUID | None = None
    project_id: UUID | None = None
    subject_id: UUID | None = None
    position: float | None = None
    tags: Annotated[list[TagName], Field(max_length=MAX_TAGS)] | None = None
    metadata: Metadata | None = None

    @model_validator(mode="after")
    def _no_null_required(self) -> Self:
        for name in ("title", "status", "priority", "position", "tags", "metadata"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise PydanticCustomError(
                    "required_field_null", "Este campo no se puede dejar vacío."
                )
        if not self.model_fields_set:
            raise PydanticCustomError("empty_update", "No hay ningún cambio que guardar.")
        return self


class TaskCompleteRequest(Strict):
    complete_subtasks: bool = False


class TaskDependencyCreate(Strict):
    depends_on_task_id: UUID


class TaskTagsReplace(Strict):
    names: Annotated[list[TagName], Field(max_length=MAX_TAGS)]


class TaskOut(Out):
    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    start_at: str | None
    due_at: str | None
    due_date: str | None
    completed_at: str | None
    estimated_minutes: int | None
    parent_task_id: UUID | None
    project_id: UUID | None
    subject_id: UUID | None
    position: float
    tags: list[TagOut]
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    archived_at: str | None
    revision: int
    depth: int
    subtask_count: int
    completed_subtask_count: int
    blocked: bool


class TaskNode(TaskOut):
    children: list[TaskNode] = []


class TaskDetail(TaskOut):
    subtasks: list[TaskNode]
    dependencies: list[TaskRef]
    dependents: list[TaskRef]


class TaskListQuery(Strict):
    status: list[TaskStatus] = []
    priority: list[Priority] = []
    project_id: UUID | None = None
    no_project: bool = False
    subject_id: UUID | None = None
    parent_task_id: UUID | None = None
    root_only: bool = False
    tag: Annotated[str, Field(max_length=MAX_TAG_NAME)] | None = None
    due_before: UtcTimestamp | None = None
    due_after: UtcTimestamp | None = None
    q: Annotated[str, Field(max_length=200)] | None = None
    include_archived: bool = False
    sort: Annotated[str, Field(max_length=100)] = "position,-created_at"
    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT
    offset: Annotated[int, Field(ge=0, le=MAX_OFFSET)] = 0

    @field_validator("sort")
    @classmethod
    def _known_sort(cls, value: str) -> str:
        return check_sort(value, TASK_SORT_FIELDS)


def check_sort(value: str, allowed: frozenset[str]) -> str:
    parts = [part.removeprefix("-") for part in value.split(",")]
    if not all(part in allowed for part in parts) or len(set(parts)) != len(parts):
        raise PydanticCustomError("invalid_sort", "Ese orden no está disponible.")
    return value


class HistoryEntry(Out):
    id: UUID
    occurred_at: str
    actor_type: Literal["user", "agent", "automation", "system"]
    origin: Literal["rest", "mcp", "scheduler", "internal"]
    action: str
    tool_name: str | None
    entity_type: str | None
    entity_id: UUID | None
    result: Literal["success", "denied", "failed", "confirmation_required"]
    error_code: str | None
    changes: dict[str, Any] | None


class ConfirmationTicket(Out):
    """Objeto `confirmation` del 409 (`contracts/README.md` §5). `params_hash` es `args_hash`."""

    id: UUID
    summary: str
    affected_count: int
    expires_at: str
    params_hash: str
