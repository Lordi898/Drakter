"""Rutas finas del calendario."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse

from app.core.errors import AppError
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
    TimeBlockOut,
    TimeBlockUpdate,
    TimeBlockWriteResult,
)
from app.services import calendar as service
from app.services.habits_calendar_support import (
    RequestContext,
    confirmation_response,
    get_db,
    rest_context,
)

router = APIRouter(prefix="/api/v1", tags=["calendar"])

Conn = Annotated[sqlite3.Connection, Depends(get_db)]
Ctx = Annotated[RequestContext, Depends(rest_context)]
FromQ = Annotated[date, Query(alias="from")]
ToQ = Annotated[date, Query(alias="to")]
IfMatch = Annotated[str | None, Header(alias="If-Match")]


def _revision(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.strip().removeprefix("W/").strip('"'))
    except ValueError:
        raise AppError("validation_error", "La versión indicada no es válida.", 422) from None


# ---------------------------------------------------------------------- eventos


@router.get("/calendar/events", response_model=service.EventPage)
def list_events(
    conn: Conn, ctx: Ctx, include_archived: bool = False, status: str | None = None,
    limit: int | None = None, offset: int | None = None,
) -> service.EventPage:  # fmt: skip
    return service.list_events(
        conn, ctx, include_archived=include_archived, status=status, limit=limit, offset=offset
    )


@router.post("/calendar/events", response_model=EventWriteResult, status_code=201)
def create_event(body: EventCreate, conn: Conn, ctx: Ctx) -> EventWriteResult:
    return service.create_event(conn, ctx, body)


@router.get("/calendar/events/{event_id}", response_model=EventOut)
def get_event(event_id: str, conn: Conn, ctx: Ctx) -> EventOut:
    return service.get_event(conn, ctx, event_id)


@router.patch("/calendar/events/{event_id}", response_model=EventWriteResult)
def update_event(
    event_id: str, body: EventUpdate, conn: Conn, ctx: Ctx, if_match: IfMatch = None
) -> EventWriteResult:
    return service.update_event(conn, ctx, event_id, body, _revision(if_match))


@router.delete("/calendar/events/{event_id}", response_model=None, responses={409: {"description": "Pide confirmación"}})
def delete_event(event_id: str, conn: Conn, ctx: Ctx) -> JSONResponse:
    return confirmation_response(ctx, service.request_delete_event(conn, ctx, event_id))


@router.get("/calendar/events/{event_id}/exceptions", response_model=service.ExceptionList)
def list_exceptions(event_id: str, conn: Conn, ctx: Ctx) -> service.ExceptionList:
    return service.list_exceptions(conn, ctx, event_id)


@router.post(
    "/calendar/events/{event_id}/exceptions", response_model=RecurrenceExceptionOut, status_code=201
)
def create_exception(
    event_id: str, body: RecurrenceExceptionCreate, conn: Conn, ctx: Ctx, if_match: IfMatch = None
) -> RecurrenceExceptionOut:
    return service.create_exception(conn, ctx, event_id, body, _revision(if_match))


# ---------------------------------------------------------------------- bloques


@router.get("/calendar/time-blocks", response_model=service.TimeBlockPage)
def list_time_blocks(
    conn: Conn, ctx: Ctx, include_archived: bool = False, task_id: str | None = None,
    status: str | None = None, limit: int | None = None, offset: int | None = None,
) -> service.TimeBlockPage:  # fmt: skip
    return service.list_time_blocks(
        conn, ctx, include_archived=include_archived, task_id=task_id, status=status,
        limit=limit, offset=offset,
    )  # fmt: skip


@router.post("/calendar/time-blocks", response_model=TimeBlockWriteResult, status_code=201)
def create_time_block(body: TimeBlockCreate, conn: Conn, ctx: Ctx) -> TimeBlockWriteResult:
    return service.create_time_block(conn, ctx, body)


@router.get("/calendar/time-blocks/{block_id}", response_model=TimeBlockOut)
def get_time_block(block_id: str, conn: Conn, ctx: Ctx) -> TimeBlockOut:
    return service.get_time_block(conn, ctx, block_id)


@router.patch("/calendar/time-blocks/{block_id}", response_model=TimeBlockWriteResult)
def update_time_block(
    block_id: str, body: TimeBlockUpdate, conn: Conn, ctx: Ctx, if_match: IfMatch = None
) -> TimeBlockWriteResult:
    return service.update_time_block(conn, ctx, block_id, body, _revision(if_match))


@router.delete(
    "/calendar/time-blocks/{block_id}", response_model=None, responses={409: {"description": "Pide confirmación"}}
)
def delete_time_block(block_id: str, conn: Conn, ctx: Ctx) -> JSONResponse:
    return confirmation_response(ctx, service.request_delete_time_block(conn, ctx, block_id))


# ----------------------------------------------------------------------- agenda


@router.get("/calendar/agenda", response_model=AgendaResponse)
def get_agenda(
    conn: Conn, from_: FromQ, to: ToQ, timezone: str, types: str | None = None, status: str | None = None
) -> AgendaResponse:
    aliases = {"class_session": "class"}  # el origen y el `kind` de una clase se llaman distinto
    kinds = [aliases.get(t.strip(), t.strip()) for t in types.split(",") if t.strip()] if types else None
    return service.agenda(conn, from_, to, timezone, kinds, status=status)


@router.get("/calendar/availability", response_model=AvailabilityResponse)
def get_availability(
    conn: Conn, local_start: str, local_end: str, timezone: str
) -> AvailabilityResponse:
    return service.availability(conn, local_start, local_end, timezone)


@router.get("/calendar/free-slots", response_model=service.FreeSlotsResponse)
def get_free_slots(
    conn: Conn, from_: FromQ, to: ToQ, timezone: str, min_minutes: Annotated[int, Query(ge=1, le=1440)] = 30
) -> service.FreeSlotsResponse:
    return service.free_slots(conn, from_, to, timezone, min_minutes)


@router.get("/calendar/overlaps", response_model=service.OverlapsResponse)
def get_overlaps(conn: Conn, from_: FromQ, to: ToQ, timezone: str) -> service.OverlapsResponse:
    return service.overlaps(conn, from_, to, timezone)
