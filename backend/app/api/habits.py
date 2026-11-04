"""Rutas finas de hábitos."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from app.schemas.habits import (
    HabitCreate,
    HabitHistory,
    HabitStatus,
    HabitOut,
    HabitRecordOut,
    HabitRecordUpsert,
    HabitStatistics,
    HabitUpdate,
)
from app.core.errors import AppError
from app.services import habits as service
from app.services.habits_calendar_support import RequestContext, get_db, rest_context

router = APIRouter(prefix="/api/v1", tags=["habits"])

Conn = Annotated[sqlite3.Connection, Depends(get_db)]
Ctx = Annotated[RequestContext, Depends(rest_context)]
FromQ = Annotated[date | None, Query(alias="from")]
ToQ = Annotated[date | None, Query(alias="to")]
IfMatch = Annotated[str | None, Header(alias="If-Match")]


def _revision(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.strip().strip('"'))
    except ValueError:
        raise AppError("validation_error", "La revisión indicada no es válida", 422) from None


@router.get("/habits", response_model=service.HabitPage)
def list_habits(
    conn: Conn,
    ctx: Ctx,
    include_archived: bool = False,
    status: HabitStatus | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> service.HabitPage:
    return service.list_habits(
        conn, ctx, include_archived=include_archived, status=status, limit=limit, offset=offset
    )


@router.post("/habits", response_model=HabitOut, status_code=201)
def create_habit(body: HabitCreate, conn: Conn, ctx: Ctx) -> HabitOut:
    return service.create_habit(conn, ctx, body)


@router.get("/habits/{habit_id}", response_model=HabitOut)
def get_habit(habit_id: str, conn: Conn, ctx: Ctx) -> HabitOut:
    return service.get_habit(conn, ctx, habit_id)


@router.patch("/habits/{habit_id}", response_model=HabitOut)
def update_habit(
    habit_id: str, body: HabitUpdate, conn: Conn, ctx: Ctx, if_match: IfMatch = None
) -> HabitOut:
    return service.update_habit(conn, ctx, habit_id, body, _revision(if_match))


@router.post("/habits/{habit_id}/archive", response_model=HabitOut)
def archive_habit(habit_id: str, conn: Conn, ctx: Ctx, if_match: IfMatch = None) -> HabitOut:
    return service.set_habit_archived(conn, ctx, habit_id, True, _revision(if_match))


@router.post("/habits/{habit_id}/unarchive", response_model=HabitOut)
def unarchive_habit(habit_id: str, conn: Conn, ctx: Ctx, if_match: IfMatch = None) -> HabitOut:
    return service.set_habit_archived(conn, ctx, habit_id, False, _revision(if_match))


@router.put("/habits/{habit_id}/records/{occurrence_date}", response_model=HabitRecordOut)
def upsert_record(
    habit_id: str, occurrence_date: date, body: HabitRecordUpsert, conn: Conn, ctx: Ctx
) -> HabitRecordOut:
    return service.upsert_record(conn, ctx, habit_id, occurrence_date, body)


@router.get("/habits/{habit_id}/records", response_model=service.RecordPage)
def list_records(
    habit_id: str, conn: Conn, ctx: Ctx, from_date: FromQ = None, to_date: ToQ = None
) -> service.RecordPage:
    return service.list_records(conn, ctx, habit_id, from_date, to_date)


@router.get("/habits/{habit_id}/history", response_model=HabitHistory)
def history(
    habit_id: str, conn: Conn, ctx: Ctx, from_date: FromQ = None, to_date: ToQ = None
) -> HabitHistory:
    return service.history(conn, ctx, habit_id, from_date, to_date)


@router.get("/habits/{habit_id}/statistics", response_model=HabitStatistics)
def statistics(
    habit_id: str, conn: Conn, ctx: Ctx, from_date: FromQ = None, to_date: ToQ = None
) -> HabitStatistics:
    return service.statistics(conn, ctx, habit_id, from_date, to_date)
