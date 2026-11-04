"""Contrato Pydantic del calendario.

Regla de tiempo (C-12): la verdad de lo no recurrente y lo recurrente es la hora
local más la zona IANA. `*_utc` son derivados para consultar rangos.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

EventKind = Literal["event", "reminder", "work_session"]
EventStatus = Literal["tentative", "confirmed", "cancelled"]
TimeBlockStatus = Literal["planned", "in_progress", "done", "skipped", "cancelled"]
SourceType = Literal["calendar_event", "time_block", "class_session"]
ExceptionKind = Literal["cancelled", "modified"]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _naive(value: datetime | None, field: str) -> None:
    if value is not None and value.tzinfo is not None:
        raise ValueError(f"{field} es hora local: sin desfase")


class EventCreate(_Input):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    kind: EventKind = "event"
    status: EventStatus = "confirmed"
    timezone: str = Field(max_length=64)
    all_day: bool = False
    local_start: datetime | None = None
    local_end: datetime | None = None
    start_date: date | None = None
    end_date_exclusive: date | None = None
    rrule: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _shape(self) -> Self:
        _naive(self.local_start, "local_start")
        _naive(self.local_end, "local_end")
        if self.all_day:
            if self.start_date is None or self.end_date_exclusive is None:
                raise ValueError("Un evento de día completo exige start_date y end_date_exclusive")
            if self.local_start or self.local_end:
                raise ValueError("Un evento de día completo no lleva horas")
            if self.end_date_exclusive <= self.start_date:
                raise ValueError("end_date_exclusive debe ser posterior a start_date")
        else:
            if self.local_start is None or self.local_end is None:
                raise ValueError("Un evento con hora exige local_start y local_end")
            if self.start_date or self.end_date_exclusive:
                raise ValueError("Un evento con hora no lleva fechas de día completo")
            if self.local_end <= self.local_start:
                raise ValueError("local_end debe ser posterior a local_start")
        return self


class EventUpdate(_Input):
    """PATCH. Si cambia cualquier campo temporal, el servicio revalida la forma completa."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    kind: EventKind | None = None
    status: EventStatus | None = None
    timezone: str | None = Field(default=None, max_length=64)
    all_day: bool | None = None
    local_start: datetime | None = None
    local_end: datetime | None = None
    start_date: date | None = None
    end_date_exclusive: date | None = None
    rrule: str | None = Field(default=None, max_length=200)


class EventOut(BaseModel):
    id: str
    title: str
    description: str | None
    kind: EventKind
    status: EventStatus
    timezone: str
    all_day: bool
    local_start: datetime | None
    local_end: datetime | None
    start_date: date | None
    end_date_exclusive: date | None
    starts_at_utc: str | None
    ends_at_utc: str | None
    rrule: str | None
    archived_at: str | None
    revision: int
    created_at: str
    updated_at: str


class TimeBlockCreate(_Input):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    timezone: str = Field(max_length=64)
    local_start: datetime
    local_end: datetime
    status: TimeBlockStatus = "planned"
    task_id: str | None = None

    @model_validator(mode="after")
    def _shape(self) -> Self:
        _naive(self.local_start, "local_start")
        _naive(self.local_end, "local_end")
        if self.local_end <= self.local_start:
            raise ValueError("local_end debe ser posterior a local_start")
        return self


class TimeBlockUpdate(_Input):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    timezone: str | None = Field(default=None, max_length=64)
    local_start: datetime | None = None
    local_end: datetime | None = None
    status: TimeBlockStatus | None = None
    task_id: str | None = None


class TimeBlockOut(BaseModel):
    id: str
    title: str
    description: str | None
    timezone: str
    local_start: datetime
    local_end: datetime
    starts_at_utc: str
    ends_at_utc: str
    status: TimeBlockStatus
    task_id: str | None
    archived_at: str | None
    revision: int
    created_at: str
    updated_at: str


class OccurrenceOverride(_Input):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    local_start: datetime | None = None
    local_end: datetime | None = None
    room: str | None = Field(default=None, max_length=200)


class RecurrenceExceptionCreate(_Input):
    occurrence_local_start: str = Field(
        max_length=19, description="Hora local original de la ocurrencia, o fecha si es de día completo"
    )
    kind: ExceptionKind
    override: OccurrenceOverride | None = None

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.kind == "modified" and self.override is None:
            raise ValueError("Una excepción modificada exige override")
        if self.kind == "cancelled" and self.override is not None:
            raise ValueError("Una excepción cancelada no lleva override")
        return self


class RecurrenceExceptionOut(BaseModel):
    id: str
    source_type: Literal["calendar_event", "class_session"]
    source_id: str
    occurrence_local_start: str
    kind: ExceptionKind
    override: OccurrenceOverride | None
    created_at: str


class AgendaItem(BaseModel):
    """Una ocurrencia. `occurrence_id` = `<source_id>:<occurrence_local_start>`, estable."""

    occurrence_id: str
    source_type: SourceType
    source_id: str
    title: str
    description: str | None
    kind: str = Field(description="event|reminder|work_session|time_block|class")
    status: str
    all_day: bool
    timezone: str
    occurrence_local_start: str
    starts_at_utc: str | None
    ends_at_utc: str | None
    start_date: date | None
    end_date_exclusive: date | None
    display_start: str | None = Field(description="Inicio en la zona pedida, sin desfase; null si es de día completo")
    display_end: str | None
    recurring: bool
    modified: bool
    room: str | None = None
    subject_id: str | None = None
    task_id: str | None = None
    color: str | None = None


class AgendaResponse(BaseModel):
    timezone: str
    from_date: date
    to_date: date
    items: list[AgendaItem]
    truncated: bool


class OverlapGroup(BaseModel):
    items: list[str] = Field(description="occurrence_id de las ocurrencias que se pisan")
    starts_at_utc: str
    ends_at_utc: str


class EventWriteResult(BaseModel):
    event: EventOut
    conflicts: list[AgendaItem]


class TimeBlockWriteResult(BaseModel):
    time_block: TimeBlockOut
    conflicts: list[AgendaItem]


class AvailabilityResponse(BaseModel):
    available: bool
    starts_at_utc: str
    ends_at_utc: str
    conflicts: list[AgendaItem]


class FreeSlot(BaseModel):
    starts_at_utc: str
    ends_at_utc: str
    display_start: str
    display_end: str
