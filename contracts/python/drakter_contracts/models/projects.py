from enum import StrEnum
from typing import Annotated

from pydantic import Field

from ..common import ContractModel, Id, Instant, LocalDate, Priority
from ._base import EntityOut, LongText, Metadata, Name, OutModel


class ProjectStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProgressSource(StrEnum):
    MANUAL = "manual"
    COMPUTED = "computed"


ManualProgress = Annotated[int, Field(ge=0, le=100)]


class ProjectCreate(ContractModel):
    name: Name
    description: LongText | None = None
    status: ProjectStatus = ProjectStatus.PLANNED
    priority: Priority = Priority.MEDIUM
    start_date: LocalDate | None = None
    target_date: LocalDate | None = None
    manual_progress: ManualProgress | None = None
    objective: Annotated[str, Field(max_length=2000)] | None = Field(default=None, description="Se guarda en `entities.metadata_json`")
    metadata: Metadata = {}


class ProjectUpdate(ContractModel):
    name: Name | None = None
    description: LongText | None = None
    status: ProjectStatus | None = None
    priority: Priority | None = None
    start_date: LocalDate | None = None
    target_date: LocalDate | None = None
    manual_progress: ManualProgress | None = None
    objective: Annotated[str, Field(max_length=2000)] | None = None
    metadata: Metadata | None = None


class ProjectProgress(OutModel):
    project_id: Id
    total: int
    completed: int
    open: int
    cancelled: int
    overdue: int
    percent: int
    computed_percent: int
    source: ProgressSource


class ProjectOut(EntityOut):
    name: str
    description: str | None = None
    status: ProjectStatus
    priority: Priority
    start_date: LocalDate | None = None
    target_date: LocalDate | None = None
    completed_at: Instant | None = None
    manual_progress: int | None = None
    objective: str | None = None
    progress: ProjectProgress | None = None
