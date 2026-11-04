"""Contrato Pydantic de asignaturas y horario."""

from __future__ import annotations

from datetime import date, time
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.calendar import ExceptionKind, OccurrenceOverride


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


_COLOR = r"^#[0-9a-fA-F]{6}$"


class SubjectCreate(_Input):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    teacher: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, pattern=_COLOR)


class SubjectUpdate(_Input):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    teacher: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, pattern=_COLOR)


class SubjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    teacher: str | None
    color: str | None
    session_count: int
    archived_at: str | None
    revision: int
    created_at: str
    updated_at: str


class ClassSessionCreate(_Input):
    weekday: int = Field(ge=1, le=7, description="1=lunes .. 7=domingo")
    starts_local_time: time
    ends_local_time: time
    timezone: str = Field(max_length=64)
    valid_from: date
    valid_until: date | None = None
    room: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.ends_local_time <= self.starts_local_time:
            raise ValueError("ends_local_time debe ser posterior a starts_local_time")
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("valid_until no puede ser anterior a valid_from")
        return self


class ClassSessionUpdate(_Input):
    weekday: int | None = Field(default=None, ge=1, le=7)
    starts_local_time: time | None = None
    ends_local_time: time | None = None
    timezone: str | None = Field(default=None, max_length=64)
    valid_from: date | None = None
    valid_until: date | None = None
    room: str | None = Field(default=None, max_length=200)


class ClassSessionOut(BaseModel):
    id: str
    subject_id: str
    weekday: int
    starts_local_time: time
    ends_local_time: time
    timezone: str
    valid_from: date
    valid_until: date | None
    room: str | None
    archived_at: str | None
    revision: int
    created_at: str
    updated_at: str


class ScheduleExceptionCreate(_Input):
    occurrence_date: date
    kind: ExceptionKind
    override: OccurrenceOverride | None = None

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.kind == "modified" and self.override is None:
            raise ValueError("Una excepción modificada exige override")
        if self.kind == "cancelled" and self.override is not None:
            raise ValueError("Una excepción cancelada no lleva override")
        return self


class TimetableEntry(BaseModel):
    session_id: str
    subject_id: str
    subject_name: str
    color: str | None
    teacher: str | None
    weekday: int
    starts_local_time: time
    ends_local_time: time
    timezone: str
    room: str | None
    valid_from: date
    valid_until: date | None


class Timetable(BaseModel):
    on_date: date
    entries: list[TimetableEntry]
