from enum import StrEnum
from typing import Annotated

from pydantic import Field

from ..common import ContractModel, IanaTimezone, Id, Instant, LocalDate, LocalTime
from ._base import EntityCoreOut, LongText, Name, OutModel

Rrule = Annotated[str, Field(max_length=200, description="Subconjunto RRULE, p. ej. FREQ=WEEKLY;BYDAY=MO,WE")]


class HabitStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class HabitRecordStatus(StrEnum):
    DONE = "done"
    SKIPPED = "skipped"
    MISSED = "missed"


class HabitCreate(ContractModel):
    name: Name
    description: LongText | None = None
    timezone: IanaTimezone
    rrule: Rrule
    start_date: LocalDate
    end_date: LocalDate | None = None
    goal_note: Annotated[str, Field(max_length=1000)] | None = None
    goal_project_id: Id | None = None
    preferred_local_time: LocalTime | None = None
    reminder_enabled: bool = False


class HabitUpdate(ContractModel):
    name: Name | None = None
    description: LongText | None = None
    timezone: IanaTimezone | None = None
    rrule: Rrule | None = None
    schedule_effective_from: LocalDate | None = Field(
        default=None, description="Con `rrule`: inicio de la nueva fila de habit_schedule_versions"
    )
    end_date: LocalDate | None = None
    status: HabitStatus | None = None
    goal_note: Annotated[str, Field(max_length=1000)] | None = None
    goal_project_id: Id | None = None
    preferred_local_time: LocalTime | None = None
    reminder_enabled: bool | None = None


class HabitScheduleVersionOut(OutModel):
    id: Id
    rrule: str
    valid_from: LocalDate
    valid_until: LocalDate | None = None


class HabitOut(EntityCoreOut):
    name: str
    description: str | None = None
    timezone: IanaTimezone
    rrule: str
    schedule_versions: list[HabitScheduleVersionOut] = []
    status: HabitStatus
    start_date: LocalDate
    end_date: LocalDate | None = None
    goal_note: str | None = Field(default=None, description="Columna `habits.target_note`")
    goal_project_id: Id | None = None
    preferred_local_time: LocalTime | None = None
    reminder_enabled: bool
    today_scheduled: bool = False
    today_status: HabitRecordStatus | None = None


class HabitRecordCreate(ContractModel):
    """PUT de un día (idempotente por habit_id + occurrence_date)."""

    status: HabitRecordStatus
    note: Annotated[str, Field(max_length=2000)] | None = None


class HabitRecordUpdate(ContractModel):
    status: HabitRecordStatus | None = None
    note: Annotated[str, Field(max_length=2000)] | None = None


class HabitRecordOut(OutModel):
    """Fila de `habit_records`: no es entidad (sin archived_at ni revision)."""

    id: Id
    habit_id: Id
    occurrence_date: LocalDate
    status: HabitRecordStatus
    note: str | None = None
    created_at: Instant
    updated_at: Instant


class HabitHistoryDay(OutModel):
    date: LocalDate
    scheduled: bool
    status: HabitRecordStatus | None = None
    note: str | None = None


class HabitHistory(OutModel):
    habit_id: Id
    from_date: LocalDate
    to_date: LocalDate
    days: list[HabitHistoryDay]


class WeekdayStat(OutModel):
    weekday: int = Field(ge=1, le=7)
    scheduled: int
    done: int


class HabitStatistics(OutModel):
    habit_id: Id
    from_date: LocalDate
    to_date: LocalDate
    scheduled: int
    done: int
    skipped: int
    missed: int
    unrecorded: int
    completion_rate: float | None = Field(default=None, description="done / (scheduled - skipped); null si el divisor es 0")
    current_streak: int
    best_streak: int
    by_weekday: list[WeekdayStat]
