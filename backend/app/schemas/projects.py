"""Contrato de proyectos. El progreso se deriva: nunca se copia nada de las tareas."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Final, Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.schemas.tasks import (
    DEFAULT_LIMIT,
    MAX_DESCRIPTION,
    MAX_LIMIT,
    MAX_OFFSET,
    Metadata,
    Out,
    Priority,
    Strict,
    check_sort,
)

ProjectStatus = Literal["planned", "active", "paused", "completed", "cancelled"]
ProgressSource = Literal["tasks", "manual"]

MAX_NAME: Final = 200
MAX_OBJECTIVE: Final = 2_000
PROJECT_SORT_FIELDS: Final = frozenset(
    {"name", "created_at", "updated_at", "target_date", "priority", "status"}
)

Name = Annotated[str, Field(min_length=1, max_length=MAX_NAME)]
ProjectDescription = Annotated[str, Field(max_length=MAX_DESCRIPTION)]
Objective = Annotated[str, Field(max_length=MAX_OBJECTIVE)]
ManualProgress = Annotated[int, Field(ge=0, le=100)]


class ProjectCreate(Strict):
    name: Name
    description: ProjectDescription | None = None
    objective: Objective | None = None
    status: ProjectStatus = "planned"
    priority: Priority = "medium"
    start_date: date | None = None
    target_date: date | None = None
    manual_progress: ManualProgress | None = None
    metadata: Metadata = {}

    @model_validator(mode="after")
    def _ordered_dates(self) -> Self:
        if self.start_date and self.target_date and self.start_date > self.target_date:
            raise PydanticCustomError(
                "start_after_target",
                "La fecha de inicio no puede ser posterior a la fecha objetivo.",
            )
        return self


class ProjectUpdate(Strict):
    """PATCH con la misma semántica que TaskUpdate. `status=completed` fija `completed_at`."""

    name: Name | None = None
    description: ProjectDescription | None = None
    objective: Objective | None = None
    status: ProjectStatus | None = None
    priority: Priority | None = None
    start_date: date | None = None
    target_date: date | None = None
    manual_progress: ManualProgress | None = None
    metadata: Metadata | None = None

    @model_validator(mode="after")
    def _no_null_required(self) -> Self:
        for name in ("name", "status", "priority", "metadata"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise PydanticCustomError(
                    "required_field_null", "Este campo no se puede dejar vacío."
                )
        if not self.model_fields_set:
            raise PydanticCustomError("empty_update", "No hay ningún cambio que guardar.")
        return self


class ProjectProgress(Out):
    """Regla explícita: `percent = round(100 * completed / total)` sobre tareas hoja no
    archivadas y no canceladas. Con `manual_progress` manda ese valor (`source='manual'`) y
    `computed_percent` conserva el calculado. Sin tareas, 0."""

    project_id: UUID
    total: int
    completed: int
    open: int
    cancelled: int
    overdue: int
    percent: int
    computed_percent: int
    source: ProgressSource


class ProjectOut(Out):
    id: UUID
    name: str
    description: str | None
    objective: str | None
    status: ProjectStatus
    priority: Priority
    start_date: str | None
    target_date: str | None
    completed_at: str | None
    manual_progress: int | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    archived_at: str | None
    revision: int
    progress: ProjectProgress


class ProjectListQuery(Strict):
    status: list[ProjectStatus] = []
    priority: list[Priority] = []
    q: Annotated[str, Field(max_length=200)] | None = None
    include_archived: bool = False
    sort: Annotated[str, Field(max_length=100)] = "-updated_at"
    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT
    offset: Annotated[int, Field(ge=0, le=MAX_OFFSET)] = 0

    @field_validator("sort")
    @classmethod
    def _known_sort(cls, value: str) -> str:
        return check_sort(value, PROJECT_SORT_FIELDS)
