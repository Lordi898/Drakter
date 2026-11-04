"""Herramientas Hermes del calendario. Solo llaman a servicios; nunca a SQL."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.calendar import (
    AgendaResponse,
    AvailabilityResponse,
    EventCreate,
    EventOut,
    EventUpdate,
    EventWriteResult,
    RecurrenceExceptionCreate,
    RecurrenceExceptionOut,
    TimeBlockCreate,
    TimeBlockUpdate,
    TimeBlockWriteResult,
)
from app.services import calendar as service
from app.services.habits_calendar_support import RequestContext
from app.tools.habits_calendar_toolspec import RiskClass, ToolSpec, service_handler


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EventIdArgs(_Args):
    event_id: str = Field(description="UUID del evento")


class UpdateEventArgs(EventUpdate):
    event_id: str = Field(description="UUID del evento")


class CreateExceptionArgs(RecurrenceExceptionCreate):
    event_id: str = Field(description="UUID del evento recurrente")


class UpdateTimeBlockArgs(TimeBlockUpdate):
    block_id: str = Field(description="UUID del bloque de tiempo")


class MoveTimeBlockArgs(_Args):
    block_id: str = Field(description="UUID del bloque de tiempo")
    local_start: datetime = Field(description="Nuevo inicio, hora local sin desfase")
    local_end: datetime = Field(description="Nuevo fin, hora local sin desfase")


class DeleteTimeBlockArgs(_Args):
    block_id: str = Field(description="UUID del bloque de tiempo")


class GetScheduleArgs(_Args):
    from_date: date = Field(description="Primer día (AAAA-MM-DD)")
    to_date: date = Field(description="Día final, exclusivo. Ventana máxima de 370 días")
    timezone: str = Field(max_length=64, description="Zona IANA en la que se muestra la agenda")
    types: list[str] | None = Field(
        default=None, description="Filtro opcional: event, reminder, work_session, time_block, class"
    )


class CheckAvailabilityArgs(_Args):
    local_start: datetime = Field(description="Inicio, hora local sin desfase")
    local_end: datetime = Field(description="Fin, hora local sin desfase")
    timezone: str = Field(max_length=64)


def _create_event(conn: sqlite3.Connection, ctx: RequestContext, args: EventCreate) -> EventWriteResult:
    return service.create_event(conn, ctx, args)


def _get_event(conn: sqlite3.Connection, ctx: RequestContext, args: EventIdArgs) -> EventOut:
    return service.get_event(conn, ctx, args.event_id)


def _update_event(conn: sqlite3.Connection, ctx: RequestContext, args: UpdateEventArgs) -> EventWriteResult:
    data = EventUpdate(**args.model_dump(exclude={"event_id"}, exclude_unset=True))
    return service.update_event(conn, ctx, args.event_id, data)


def _delete_event(conn: sqlite3.Connection, ctx: RequestContext, args: EventIdArgs) -> service.DeleteResult:
    # ToolGate ya impuso la confirmación (RiskClass.CONFIRM): se ejecuta el ejecutor registrado.
    return service.DeleteResult(**service.execute_delete_event(conn, ctx, {"event_id": args.event_id}))


def _create_exception(
    conn: sqlite3.Connection, ctx: RequestContext, args: CreateExceptionArgs
) -> RecurrenceExceptionOut:
    data = RecurrenceExceptionCreate(**args.model_dump(exclude={"event_id"}, exclude_unset=True))
    return service.create_exception(conn, ctx, args.event_id, data)


def _create_block(
    conn: sqlite3.Connection, ctx: RequestContext, args: TimeBlockCreate
) -> TimeBlockWriteResult:
    return service.create_time_block(conn, ctx, args)


def _update_block(
    conn: sqlite3.Connection, ctx: RequestContext, args: UpdateTimeBlockArgs
) -> TimeBlockWriteResult:
    data = TimeBlockUpdate(**args.model_dump(exclude={"block_id"}, exclude_unset=True))
    return service.update_time_block(conn, ctx, args.block_id, data)


def _move_block(
    conn: sqlite3.Connection, ctx: RequestContext, args: MoveTimeBlockArgs
) -> TimeBlockWriteResult:
    return service.move_time_block(conn, ctx, args.block_id, args.local_start, args.local_end)


def _delete_block(
    conn: sqlite3.Connection, ctx: RequestContext, args: DeleteTimeBlockArgs
) -> service.DeleteResult:
    return service.DeleteResult(
        **service.execute_delete_time_block(conn, ctx, {"time_block_id": args.block_id})
    )


def _schedule(conn: sqlite3.Connection, ctx: RequestContext, args: GetScheduleArgs) -> AgendaResponse:
    return service.agenda(conn, args.from_date, args.to_date, args.timezone, args.types)


def _availability(
    conn: sqlite3.Connection, ctx: RequestContext, args: CheckAvailabilityArgs
) -> AvailabilityResponse:
    return service.availability(conn, args.local_start, args.local_end, args.timezone)


_NOT_FOUND = ("not_found",)
_TIME_ERRORS = ("validation_error", "invalid_rrule", "invalid_timezone", "nonexistent_local_time")

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="create_event",
        description=(
            "Crea un evento, recordatorio o sesión de trabajo en el calendario. Con hora usa "
            "local_start/local_end (hora local sin desfase) y timezone IANA; de día completo, all_day=true "
            "con start_date y end_date_exclusive. `rrule` crea una serie (p. ej. FREQ=WEEKLY;BYDAY=MO). "
            "Los solapes se devuelven como aviso en `conflicts`; no bloquean."
        ),
        domain="calendar",
        args_model=EventCreate,
        result_model=EventWriteResult,
        permission="calendar.write",
        risk=RiskClass.WRITE,
        handler=service_handler("create_event", _create_event),
        errors=_TIME_ERRORS,
        audit={"kind": "log", "status": "log", "timezone": "log", "all_day": "log", "local_start": "log",
               "local_end": "log", "start_date": "log", "end_date_exclusive": "log", "rrule": "log",
               "title": "omit", "description": "omit"},
    ),
    ToolSpec(
        name="get_event",
        description="Devuelve un evento del calendario por id.",
        domain="calendar",
        args_model=EventIdArgs,
        result_model=EventOut,
        permission="calendar.read",
        risk=RiskClass.READ,
        handler=service_handler("get_event", _get_event),
        errors=_NOT_FOUND,
        idempotent=True,
        audit={"event_id": "log"},
    ),
    ToolSpec(
        name="update_event",
        description=(
            "Edita un evento. Solo se cambia lo indicado. Una serie con excepciones no admite cambiar "
            "su rango temporal. Los solapes se devuelven como aviso."
        ),
        domain="calendar",
        args_model=UpdateEventArgs,
        result_model=EventWriteResult,
        permission="calendar.write",
        risk=RiskClass.WRITE,
        handler=service_handler("update_event", _update_event),
        errors=(*_TIME_ERRORS, "not_found", "conflict"),
        audit={"event_id": "log", "kind": "log", "status": "log", "timezone": "log", "all_day": "log",
               "local_start": "log", "local_end": "log", "start_date": "log",
               "end_date_exclusive": "log", "rrule": "log", "title": "omit", "description": "omit"},
    ),
    ToolSpec(
        name="delete_event",
        description=(
            "Elimina un evento (y sus excepciones). Requiere confirmación del usuario. Para quitar una "
            "sola ocurrencia de una serie usa create_event_exception con kind=cancelled."
        ),
        domain="calendar",
        args_model=EventIdArgs,
        result_model=service.DeleteResult,
        permission="calendar.write",
        risk=RiskClass.CONFIRM,
        handler=service_handler("delete_event", _delete_event),
        errors=_NOT_FOUND,
        audit={"event_id": "log"},
        summarize=lambda args: f"Eliminar el evento {args.event_id} y sus excepciones",  # type: ignore[attr-defined]
    ),
    ToolSpec(
        name="create_event_exception",
        description=(
            "Cancela o modifica una sola ocurrencia de un evento recurrente. `occurrence_local_start` es "
            "la hora local original de la ocurrencia (AAAA-MM-DDTHH:MM:SS) o la fecha si es de día "
            "completo. kind=modified exige `override`."
        ),
        domain="calendar",
        args_model=CreateExceptionArgs,
        result_model=RecurrenceExceptionOut,
        permission="calendar.write",
        risk=RiskClass.WRITE,
        handler=service_handler("create_event_exception", _create_exception),
        errors=(*_TIME_ERRORS, "not_found", "conflict"),
        audit={"event_id": "log", "occurrence_local_start": "log", "kind": "log", "override": "omit"},
    ),
    ToolSpec(
        name="create_time_block",
        description=(
            "Reserva un bloque de tiempo (hora local + timezone IANA), opcionalmente asociado a una "
            "tarea con task_id. Los solapes se devuelven como aviso."
        ),
        domain="calendar",
        args_model=TimeBlockCreate,
        result_model=TimeBlockWriteResult,
        permission="calendar.write",
        risk=RiskClass.WRITE,
        handler=service_handler("create_time_block", _create_block),
        errors=(*_TIME_ERRORS, "not_found"),
        audit={"timezone": "log", "local_start": "log", "local_end": "log", "status": "log",
               "task_id": "log", "title": "omit", "description": "omit"},
    ),
    ToolSpec(
        name="update_time_block",
        description="Edita un bloque de tiempo (estado, tarea, título, horas). Solo se cambia lo indicado.",
        domain="calendar",
        args_model=UpdateTimeBlockArgs,
        result_model=TimeBlockWriteResult,
        permission="calendar.write",
        risk=RiskClass.WRITE,
        handler=service_handler("update_time_block", _update_block),
        errors=(*_TIME_ERRORS, "not_found"),
        audit={"block_id": "log", "timezone": "log", "local_start": "log", "local_end": "log",
               "status": "log", "task_id": "log", "title": "omit", "description": "omit"},
    ),
    ToolSpec(
        name="move_time_block",
        description="Mueve un bloque de tiempo a un nuevo local_start/local_end; conserva todo lo demás.",
        domain="calendar",
        args_model=MoveTimeBlockArgs,
        result_model=TimeBlockWriteResult,
        permission="calendar.write",
        risk=RiskClass.WRITE,
        handler=service_handler("move_time_block", _move_block),
        errors=(*_TIME_ERRORS, "not_found"),
        audit={"block_id": "log", "local_start": "log", "local_end": "log"},
    ),
    ToolSpec(
        name="delete_time_block",
        description="Elimina un bloque de tiempo. Requiere confirmación del usuario.",
        domain="calendar",
        args_model=DeleteTimeBlockArgs,
        result_model=service.DeleteResult,
        permission="calendar.write",
        risk=RiskClass.CONFIRM,
        handler=service_handler("delete_time_block", _delete_block),
        errors=_NOT_FOUND,
        audit={"block_id": "log"},
        summarize=lambda args: f"Eliminar el bloque de tiempo {args.block_id}",  # type: ignore[attr-defined]
    ),
    ToolSpec(
        name="get_schedule",
        description=(
            "Agenda combinada (eventos con sus series expandidas y excepciones, bloques de tiempo y "
            "clases) entre from_date (incluido) y to_date (excluido), mostrada en `timezone`."
        ),
        domain="calendar",
        args_model=GetScheduleArgs,
        result_model=AgendaResponse,
        permission="calendar.read",
        risk=RiskClass.READ,
        handler=service_handler("get_schedule", _schedule),
        errors=("window_too_large", "invalid_timezone", "validation_error"),
        idempotent=True,
        returns_untrusted=False,
        audit={"from_date": "log", "to_date": "log", "timezone": "log", "types": "log"},
    ),
    ToolSpec(
        name="check_availability",
        description=(
            "Comprueba si un intervalo (hora local + timezone) está libre y devuelve lo que lo pisa."
        ),
        domain="calendar",
        args_model=CheckAvailabilityArgs,
        result_model=AvailabilityResponse,
        permission="calendar.read",
        risk=RiskClass.READ,
        handler=service_handler("check_availability", _availability),
        errors=("validation_error", "invalid_timezone", "nonexistent_local_time", "window_too_large"),
        idempotent=True,
        audit={"local_start": "log", "local_end": "log", "timezone": "log"},
    ),
)
