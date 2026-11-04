from typing import Annotated

from pydantic import Field

from ..common import ContractModel, HexColor, IanaTimezone, Id, LocalDate, LocalTime
from ._base import EntityOut, LongText, Metadata, Name, OutModel

Weekday = Annotated[int, Field(ge=1, le=7, description="1=lunes .. 7=domingo")]


class SubjectCreate(ContractModel):
    name: Name
    description: LongText | None = None
    teacher: Name | None = None
    color: HexColor | None = None
    metadata: Metadata = {}


class SubjectUpdate(ContractModel):
    name: Name | None = None
    description: LongText | None = None
    teacher: Name | None = None
    color: HexColor | None = None
    metadata: Metadata | None = None


class SubjectOut(EntityOut):
    name: str
    description: str | None = None
    teacher: str | None = None
    color: HexColor | None = None
    session_count: int = 0


class ClassSessionCreate(ContractModel):
    weekday: Weekday
    starts_local_time: LocalTime
    ends_local_time: LocalTime
    timezone: IanaTimezone
    valid_from: LocalDate
    valid_until: LocalDate | None = None
    interval_weeks: Annotated[int, Field(ge=1)] = 1
    room: Name | None = None
    metadata: Metadata = {}


class ClassSessionUpdate(ContractModel):
    weekday: Weekday | None = None
    starts_local_time: LocalTime | None = None
    ends_local_time: LocalTime | None = None
    timezone: IanaTimezone | None = None
    valid_from: LocalDate | None = None
    valid_until: LocalDate | None = None
    interval_weeks: Annotated[int, Field(ge=1)] | None = None
    room: Name | None = None
    metadata: Metadata | None = None


class ClassSessionOut(EntityOut):
    subject_id: Id
    weekday: int
    starts_local_time: LocalTime
    ends_local_time: LocalTime
    timezone: IanaTimezone
    valid_from: LocalDate
    valid_until: LocalDate | None = None
    interval_weeks: int = 1
    room: str | None = None


class TimetableEntry(OutModel):
    session_id: Id
    subject_id: Id
    subject_name: str
    color: HexColor | None = None
    teacher: str | None = None
    weekday: int
    starts_local_time: LocalTime
    ends_local_time: LocalTime
    timezone: IanaTimezone
    room: str | None = None
    valid_from: LocalDate
    valid_until: LocalDate | None = None


class Timetable(OutModel):
    on_date: LocalDate
    entries: list[TimetableEntry]
