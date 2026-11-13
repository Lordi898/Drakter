"""Formatos serializados y enumerados comunes (contracts/README.md §2)."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Generic, TypeVar
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer

T = TypeVar("T")

_LOCAL_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")
_LOCAL_TIME = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


class ContractModel(BaseModel):
    """Base de entradas: rechaza campos desconocidos."""

    model_config = ConfigDict(extra="forbid")


def format_instant(value: datetime) -> str:
    """UTC con milisegundos de ancho fijo: `YYYY-MM-DDTHH:MM:SS.sssZ`."""
    if value.tzinfo is None:
        raise ValueError("instante sin zona horaria")
    utc = value.astimezone(UTC)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond // 1000:03d}Z"


def _parse_instant(value: object) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(parsed, datetime) or parsed.tzinfo is None:
        raise ValueError("se esperaba un instante ISO 8601 con zona")
    return parsed.astimezone(UTC)


def _check_timezone(value: str) -> str:
    if value not in available_timezones():
        raise ValueError("zona horaria IANA desconocida")
    return value


def _check_local_datetime(value: str) -> str:
    if not _LOCAL_DATETIME.fullmatch(value):
        raise ValueError("se esperaba YYYY-MM-DDTHH:MM")
    datetime.fromisoformat(value)
    return value


def _check_local_time(value: str) -> str:
    if not _LOCAL_TIME.fullmatch(value):
        raise ValueError("se esperaba HH:MM")
    return value


Id = UUID
Instant = Annotated[datetime, BeforeValidator(_parse_instant), PlainSerializer(format_instant, return_type=str)]
LocalDate = date
LocalDateTime = Annotated[str, AfterValidator(_check_local_datetime)]
LocalTime = Annotated[str, AfterValidator(_check_local_time)]
IanaTimezone = Annotated[str, AfterValidator(_check_timezone)]
HexColor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


class EntityType(StrEnum):
    TASK = "task"
    PROJECT = "project"
    HABIT = "habit"
    CALENDAR_EVENT = "calendar_event"
    TIME_BLOCK = "time_block"
    SUBJECT = "subject"
    CLASS_SESSION = "class_session"
    RESOURCE = "resource"
    FOLDER = "folder"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ActorType(StrEnum):
    USER = "user"
    AGENT = "agent"
    AUTOMATION = "automation"
    SYSTEM = "system"


class Origin(StrEnum):
    REST = "rest"
    MCP = "mcp"
    SCHEDULER = "scheduler"
    INTERNAL = "internal"


class Page(BaseModel, Generic[T]):
    """Forma única de todo listado. Cursor opaco; `limit` lo acota el servidor."""

    items: list[T]
    next_cursor: str | None = None
    total: int | None = None
