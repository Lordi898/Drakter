"""Contrato Pydantic del calendario.

Regla de tiempo (C-12): la verdad de lo no recurrente y lo recurrente es la hora
local más la zona IANA. `*_utc` son derivados para consultar rangos.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

_LOCAL_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:00)?")
_LOCAL_TIME = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def _check_local_datetime(value: str) -> str:
    """Se guarda `AAAA-MM-DDTHH:MM`. Se acepta `:00` final, que es el formato de
    `drakter_contracts.common`, y se recorta: el calendario no usa segundos."""
    if not _LOCAL_DATETIME.fullmatch(value):
        raise ValueError("se esperaba YYYY-MM-DDTHH:MM")
    datetime.fromisoformat(value)
    return value[:16]


def _check_local_time(value: str) -> str:
    if not _LOCAL_TIME.fullmatch(value):
        raise ValueError("se esperaba HH:MM")
    return value


# Mismos formatos que drakter_contracts.common; se ordenan bien como texto.
LocalDateTime = Annotated[str, AfterValidator(_check_local_datetime)]
LocalTime = Annotated[str, AfterValidator(_check_local_time)]

EventKind = Literal["event", "reminder", "work_session"]
EventStatus = Literal["tentative", "confirmed", "cancelled"]
TimeBlockStatus = Literal["planned", "in_progress", "done", "skipped", "cancelled"]
SourceType = Literal["calendar_event", "time_block", "class_session"]
ExceptionKind = Literal["cancelled", "modified"]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EventCreate(_Input):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    location: str | None = Field(default=None, max_length=300)
    reminder_minutes_before: int | None = Field(default=None, ge=0, le=40320)
    kind: EventKind = "event"
    status: EventStatus = "confirmed"
    timezone: str = Field(max_length=64)
    all_day: bool = False
    local_start: LocalDateTime | None = None
    local_end: LocalDateTime | None = None
    start_date: date | None = None
    end_date_exclusive: date | None = None
    rrule: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _shape(self) -> Self:
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
    location: str | None = Field(default=None, max_length=300)
    reminder_minutes_before: int | None = Field(default=None, ge=0, le=40320)
    kind: EventKind | None = None
    status: EventStatus | None = None
    timezone: str | None = Field(default=None, max_length=64)
    all_day: bool | None = None
    local_start: LocalDateTime | None = None
    local_end: LocalDateTime | None = None
    start_date: date | None = None
    end_date_exclusive: date | None = None
    rrule: str | None = Field(default=None, max_length=200)


class EventOut(BaseModel):
    id: str
    title: str
    description: str | None
    location: str | None
    reminder_minutes_before: int | None
    kind: EventKind
    status: EventStatus
    timezone: str
    all_day: bool
    local_start: LocalDateTime | None
    local_end: LocalDateTime | None
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
    local_start: LocalDateTime
    local_end: LocalDateTime
    status: TimeBlockStatus = "planned"
    task_id: str | None = None

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.local_end <= self.local_start:
            raise ValueError("local_end debe ser posterior a local_start")
        return self


class TimeBlockUpdate(_Input):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=8000)
    timezone: str | None = Field(default=None, max_length=64)
    local_start: LocalDateTime | None = None
    local_end: LocalDateTime | None = None
    status: TimeBlockStatus | None = None
    task_id: str | None = None


class TimeBlockOut(BaseModel):
    id: str
    title: str
    description: str | None
    timezone: str
    local_start: LocalDateTime
    local_end: LocalDateTime
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
    local_start: LocalDateTime | None = None
    local_end: LocalDateTime | None = None
    room: str | None = Field(default=None, max_length=200)


class RecurrenceExceptionCreate(_Input):
    occurrence_local_start: str = Field(
        max_length=16, description="Hora local original de la ocurrencia, o fecha si es de día completo"
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
    location: str | None = None
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
