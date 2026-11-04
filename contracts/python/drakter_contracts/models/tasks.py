from enum import StrEnum
from typing import Annotated

from pydantic import Field

from ..common import ContractModel, Id, Instant, LocalDate, Priority
from ._base import EntityOut, LongText, Metadata, OutModel, TagName, Title
from .tags import TagOut

Minutes = Annotated[int, Field(ge=0, le=1_000_000)]


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskCreate(ContractModel):
    title: Title
    description: LongText | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    start_at: Instant | None = None
    due_at: Instant | None = None
    due_date: LocalDate | None = None
    estimated_minutes: Minutes | None = None
    parent_task_id: Id | None = None
    project_id: Id | None = None
    subject_id: Id | None = None
    position: float | None = None
    tags: Annotated[list[TagName], Field(max_length=32)] = []
    metadata: Metadata = {}


class TaskUpdate(ContractModel):
    title: Title | None = None
    description: LongText | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    start_at: Instant | None = None
    due_at: Instant | None = None
    due_date: LocalDate | None = None
    estimated_minutes: Minutes | None = None
    parent_task_id: Id | None = None
    project_id: Id | None = None
    subject_id: Id | None = None
    position: float | None = None
    tags: Annotated[list[TagName], Field(max_length=32)] | None = None
    metadata: Metadata | None = None


class TaskCompleteRequest(ContractModel):
    complete_subtasks: bool = False


class TaskDependencyCreate(ContractModel):
    depends_on_task_id: Id


class TaskRef(OutModel):
    id: Id
    title: str
    status: TaskStatus


class TaskOut(EntityOut):
    title: str
    description: str | None = None
    status: TaskStatus
    priority: Priority
    start_at: Instant | None = None
    due_at: Instant | None = None
    due_date: LocalDate | None = None
    completed_at: Instant | None = None
    estimated_minutes: int | None = None
    parent_task_id: Id | None = None
    project_id: Id | None = None
    subject_id: Id | None = None
    position: float
    tags: list[TagOut] = []
    depth: int = 0
    subtask_count: int = 0
    completed_subtask_count: int = 0
    blocked: bool = False
