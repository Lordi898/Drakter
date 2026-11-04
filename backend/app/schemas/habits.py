"""Contrato Pydantic de hábitos. `extra='forbid'` en toda entrada."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.calendar import LocalTime

HabitStatus = Literal["active", "paused", "ended"]
RecordStatus = Literal["done", "skipped", "missed"]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HabitCreate(_Input):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    timezone: str = Field(max_length=64)
    rrule: str = Field(max_length=200, description="Subconjunto RRULE, p. ej. FREQ=WEEKLY;BYDAY=MO,WE")
    start_date: date
    end_date: date | None = None
    goal_note: str | None = Field(default=None, max_length=1000)
    goal_project_id: str | None = None
    preferred_local_time: LocalTime | None = None
    reminder_enabled: bool = False


class HabitUpdate(_Input):
    """PATCH: lo ausente no cambia; `model_fields_set` distingue ausente de null."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    timezone: str | None = Field(default=None, max_length=64)
    rrule: str | None = Field(default=None, max_length=200)
    schedule_effective_from: date | None = Field(
        default=None, description="Inicio de la nueva frecuencia; por defecto, hoy en la zona del hábito."
    )
    end_date: date | None = None
    status: HabitStatus | None = None
    goal_note: str | None = Field(default=None, max_length=1000)
    goal_project_id: str | None = None
    preferred_local_time: LocalTime | None = None
    reminder_enabled: bool | None = None


class HabitScheduleVersion(BaseModel):
    id: str
    rrule: str
    valid_from: date
    valid_until: date | None


class HabitOut(BaseModel):
    id: str
    name: str
    description: str | None
    timezone: str
    rrule: str
    schedule_versions: list[HabitScheduleVersion]
    status: HabitStatus
    start_date: date
    end_date: date | None
    goal_note: str | None
    goal_project_id: str | None
    preferred_local_time: LocalTime | None
    reminder_enabled: bool
    today_scheduled: bool
    today_status: RecordStatus | None
    archived_at: str | None
    revision: int
    created_at: str
    updated_at: str


class HabitRecordUpsert(_Input):
    status: RecordStatus
    note: str | None = Field(default=None, max_length=2000)


class HabitRecordOut(BaseModel):
    id: str
    habit_id: str
    occurrence_date: date
    status: RecordStatus
    note: str | None
    created_at: str
    updated_at: str


class HabitHistoryDay(BaseModel):
    date: date
    scheduled: bool
    status: RecordStatus | None
    note: str | None


class HabitHistory(BaseModel):
    habit_id: str
    from_date: date
    to_date: date
    days: list[HabitHistoryDay]


class WeekdayStat(BaseModel):
    weekday: int = Field(ge=1, le=7)
    scheduled: int
    done: int


class HabitStatistics(BaseModel):
    habit_id: str
    from_date: date
    to_date: date
    scheduled: int
    done: int
    skipped: int
    missed: int
    unrecorded: int
    completion_rate: float | None = Field(description="done / (scheduled - skipped); null si el divisor es 0")
    current_streak: int
    best_streak: int
    by_weekday: list[WeekdayStat]
