from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ..common import (
    ContractModel, HexColor, IanaTimezone, Id, Instant, LocalDate, LocalDateTime,
)
from ._base import EntityOut, LongText, Metadata, OutModel, Title

Rrule = Annotated[str, Field(max_length=200)]
ReminderMinutes = Annotated[int, Field(ge=0)]


class EventKind(StrEnum):
    EVENT = "event"
    REMINDER = "reminder"
    WORK_SESSION = "work_session"


class EventStatus(StrEnum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class TimeBlockStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ExceptionKind(StrEnum):
    CANCELLED = "cancelled"
    MODIFIED = "modified"


class CalendarSourceType(StrEnum):
    CALENDAR_EVENT = "calendar_event"
    TIME_BLOCK = "time_block"
    CLASS_SESSION = "class_session"


class CalendarEventCreate(ContractModel):
    """Día completo: `start_date` + `end_date_exclusive`; si no, `local_start` + `local_end`."""

    title: Title
    description: LongText | None = None
    location: Annotated[str, Field(max_length=300)] | None = None
    kind: EventKind = EventKind.EVENT
    status: EventStatus = EventStatus.CONFIRMED
    timezone: IanaTimezone
    all_day: bool = False
    local_start: LocalDateTime | None = None
    local_end: LocalDateTime | None = None
    start_date: LocalDate | None = None
    end_date_exclusive: LocalDate | None = None
    rrule: Rrule | None = None
    reminder_minutes_before: ReminderMinutes | None = None
    metadata: Metadata = {}


class CalendarEventUpdate(ContractModel):
    title: Title | None = None
    description: LongText | None = None
    location: Annotated[str, Field(max_length=300)] | None = None
    kind: EventKind | None = None
    status: EventStatus | None = None
    timezone: IanaTimezone | None = None
    all_day: bool | None = None
    local_start: LocalDateTime | None = None
    local_end: LocalDateTime | None = None
    start_date: LocalDate | None = None
    end_date_exclusive: LocalDate | None = None
    rrule: Rrule | None = None
    reminder_minutes_before: ReminderMinutes | None = None
    metadata: Metadata | None = None


class CalendarEventOut(EntityOut):
    title: str
    description: str | None = None
    location: str | None = None
    kind: EventKind
    status: EventStatus
    timezone: IanaTimezone
    all_day: bool
    local_start: LocalDateTime | None = None
    local_end: LocalDateTime | None = None
    start_date: LocalDate | None = None
    end_date_exclusive: LocalDate | None = None
    starts_at_utc: Instant | None = None
    ends_at_utc: Instant | None = None
    rrule: str | None = None
    recurrence_until_utc: Instant | None = None
    reminder_minutes_before: int | None = None


class TimeBlockCreate(ContractModel):
    title: Title
    description: LongText | None = None
    timezone: IanaTimezone
    local_start: LocalDateTime
    local_end: LocalDateTime
    status: TimeBlockStatus = TimeBlockStatus.PLANNED
    task_id: Id | None = None
    metadata: Metadata = {}


class TimeBlockUpdate(ContractModel):
    title: Title | None = None
    description: LongText | None = None
    timezone: IanaTimezone | None = None
    local_start: LocalDateTime | None = None
    local_end: LocalDateTime | None = None
    status: TimeBlockStatus | None = None
    task_id: Id | None = None
    metadata: Metadata | None = None


class TimeBlockOut(EntityOut):
    title: str
    description: str | None = None
    timezone: IanaTimezone
    local_start: LocalDateTime
    local_end: LocalDateTime
    starts_at_utc: Instant
    ends_at_utc: Instant
    status: TimeBlockStatus
    task_id: Id | None = None


class OccurrenceOverride(ContractModel):
    title: Title | None = None
    description: LongText | None = None
    local_start: LocalDateTime | None = None
    local_end: LocalDateTime | None = None
    room: Annotated[str, Field(max_length=200)] | None = None


class RecurrenceExceptionCreate(ContractModel):
    occurrence_local_start: LocalDateTime
    kind: ExceptionKind
    override: OccurrenceOverride | None = None


class RecurrenceExceptionUpdate(ContractModel):
    kind: ExceptionKind | None = None
    override: OccurrenceOverride | None = None


class RecurrenceExceptionOut(OutModel):
    id: Id
    source_type: Literal["calendar_event", "class_session"]
    source_id: Id
    occurrence_local_start: LocalDateTime
    kind: ExceptionKind
    override: OccurrenceOverride | None = None
    created_at: Instant


class AgendaItem(OutModel):
    occurrence_id: str = Field(description="<source_id>:<local_start>")
    source_type: CalendarSourceType
    source_id: Id
    title: str
    description: str | None = None
    kind: str = Field(description="event|reminder|work_session|time_block|class")
    status: str
    all_day: bool
    timezone: IanaTimezone
    occurrence_local_start: str
    starts_at_utc: Instant | None = None
    ends_at_utc: Instant | None = None
    start_date: LocalDate | None = None
    end_date_exclusive: LocalDate | None = None
    display_start: str | None = None
    display_end: str | None = None
    recurring: bool
    modified: bool
    room: str | None = None
    subject_id: Id | None = None
    task_id: Id | None = None
    color: HexColor | None = None


class AgendaResponse(OutModel):
    timezone: IanaTimezone
    from_date: LocalDate
    to_date: LocalDate
    items: list[AgendaItem]
    truncated: bool


class OverlapGroup(OutModel):
    items: list[str]
    starts_at_utc: Instant
    ends_at_utc: Instant


class CalendarEventWriteResult(OutModel):
    event: CalendarEventOut
    conflicts: list[AgendaItem]


class TimeBlockWriteResult(OutModel):
    time_block: TimeBlockOut
    conflicts: list[AgendaItem]


class FreeSlot(OutModel):
    starts_at_utc: Instant
    ends_at_utc: Instant
    display_start: str
    display_end: str


class AvailabilityResponse(OutModel):
    available: bool
    starts_at_utc: Instant
    ends_at_utc: Instant
    conflicts: list[AgendaItem]
