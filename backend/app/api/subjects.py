"""Rutas finas de asignaturas, sesiones de clase y horario. Las reglas viven en services/subjects.py."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.schemas.calendar import RecurrenceExceptionOut
from app.schemas.subjects import (
    ClassSessionCreate,
    ClassSessionOut,
    ClassSessionUpdate,
    ScheduleExceptionCreate,
    SubjectCreate,
    SubjectOut,
    SubjectUpdate,
    Timetable,
)
from app.services import subjects as service
from app.services.habits_calendar_support import (
    RequestContext,
    confirmation_response,
    get_db,
    rest_context,
)
from app.services.subjects import (
    ClassSessionWriteResult,
    SessionList,
    SubjectList,
    SubjectResources,
)

__all__ = ["ClassSessionWriteResult", "router"]

router = APIRouter(prefix="/api/v1", tags=["subjects"])

Db = Annotated[sqlite3.Connection, Depends(get_db)]
Ctx = Annotated[RequestContext, Depends(rest_context)]
IfMatch = Annotated[str | None, Header(alias="If-Match")]


def _revision(if_match: str | None) -> int | None:
    if if_match is None:
        return None
    text = if_match.removeprefix("W/").strip().strip('"')
    if not text.isdigit():
        raise AppError("invalid_if_match", "If-Match debe ser la revisión numérica", 400)
    return int(text)


@router.get("/subjects", response_model=SubjectList)
def list_subjects(
    conn: Db,
    ctx: Ctx,
    include_archived: bool = False,
    limit: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int | None, Query(ge=0)] = None,
) -> SubjectList:
    return service.list_subjects(
        conn, ctx, include_archived=include_archived, limit=limit, offset=offset
    )


@router.post("/subjects", response_model=SubjectOut, status_code=201)
def create_subject(body: SubjectCreate, conn: Db, ctx: Ctx) -> SubjectOut:
    return service.create_subject(conn, ctx, body)


@router.get("/subjects/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: str, conn: Db, ctx: Ctx) -> SubjectOut:
    return service.get_subject(conn, ctx, subject_id)


@router.patch("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: str, body: SubjectUpdate, conn: Db, ctx: Ctx, if_match: IfMatch = None
) -> SubjectOut:
    return service.update_subject(conn, ctx, subject_id, body, _revision(if_match))


@router.delete("/subjects/{subject_id}", status_code=409, response_model=None)
def delete_subject(subject_id: str, conn: Db, ctx: Ctx) -> JSONResponse:
    return confirmation_response(ctx, service.request_delete_subject(conn, ctx, subject_id))


@router.post("/subjects/{subject_id}/archive", response_model=SubjectOut)
def archive_subject(subject_id: str, conn: Db, ctx: Ctx) -> SubjectOut:
    return service.archive_subject(conn, ctx, subject_id, True)


@router.post("/subjects/{subject_id}/unarchive", response_model=SubjectOut)
def unarchive_subject(subject_id: str, conn: Db, ctx: Ctx) -> SubjectOut:
    return service.archive_subject(conn, ctx, subject_id, False)


@router.get("/subjects/{subject_id}/sessions", response_model=SessionList)
def list_sessions(
    subject_id: str,
    conn: Db,
    ctx: Ctx,
    include_archived: bool = False,
    limit: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int | None, Query(ge=0)] = None,
) -> SessionList:
    return service.list_class_sessions(conn, ctx, subject_id, include_archived, limit, offset)


@router.post(
    "/subjects/{subject_id}/sessions", response_model=ClassSessionWriteResult, status_code=201
)
def create_session(
    subject_id: str, body: ClassSessionCreate, conn: Db, ctx: Ctx
) -> ClassSessionWriteResult:
    return service.create_class_session(conn, ctx, subject_id, body)


@router.get("/subjects/{subject_id}/resources", response_model=SubjectResources)
def subject_resources(subject_id: str, conn: Db, ctx: Ctx) -> SubjectResources:
    return service.get_subject_resources(conn, ctx, subject_id)


@router.get("/class-sessions/{session_id}", response_model=ClassSessionOut)
def get_session(session_id: str, conn: Db, ctx: Ctx) -> ClassSessionOut:
    return service.get_class_session(conn, ctx, session_id)


@router.patch("/class-sessions/{session_id}", response_model=ClassSessionWriteResult)
def update_session(
    session_id: str, body: ClassSessionUpdate, conn: Db, ctx: Ctx, if_match: IfMatch = None
) -> ClassSessionWriteResult:
    return service.update_class_session(conn, ctx, session_id, body, _revision(if_match))


@router.delete("/class-sessions/{session_id}", status_code=409, response_model=None)
def delete_session(session_id: str, conn: Db, ctx: Ctx) -> JSONResponse:
    return confirmation_response(ctx, service.request_delete_class_session(conn, ctx, session_id))


@router.post(
    "/class-sessions/{session_id}/exceptions",
    response_model=RecurrenceExceptionOut,
    status_code=201,
)
def create_exception(
    session_id: str, body: ScheduleExceptionCreate, conn: Db, ctx: Ctx
) -> RecurrenceExceptionOut:
    return service.create_schedule_exception(conn, ctx, session_id, body)


@router.get("/timetable", response_model=Timetable)
def timetable(conn: Db, ctx: Ctx, on: date | None = None) -> Timetable:
    return service.get_timetable(conn, ctx, on)
