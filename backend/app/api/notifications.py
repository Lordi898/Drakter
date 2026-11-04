"""API de notificaciones para la GUI. No hay herramienta de agente ni borrado.

Montaje en `app/main.py`: `app.include_router(notifications.router)`. El guardia de
seguridad exige el token de sesión en todas estas rutas.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from drakter_contracts.common import format_instant
from drakter_contracts.models.notifications import NotificationOut
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.database.connection import connect
from app.repositories import notifications as repo
from app.services.reminders import CATCH_UP, TICK_SECONDS, ReminderTicker

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

MAX_LIMIT = 200


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int


class MarkReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[UUID] = Field(min_length=1, max_length=MAX_LIMIT)


class MarkReadResult(BaseModel):
    updated: int


class ReminderStatus(BaseModel):
    """La GUI lo enseña tal cual: los recordatorios solo funcionan con la app abierta."""

    requires_app_open: Literal[True] = True
    running: bool
    tick_seconds: int
    catch_up_hours: int
    last_tick_at: str | None
    last_error: str | None


@contextmanager
def _db(request: Request) -> Iterator[sqlite3.Connection]:
    # Dentro del endpoint y no como dependencia: FastAPI puede ejecutar una dependencia
    # generadora en otro hilo y sqlite3 no admite compartir la conexión entre hilos.
    conn = connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


@router.get("", response_model=NotificationPage)
def list_notifications(
    request: Request,
    unread: bool = False,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationPage:
    with _db(request) as conn:
        rows, total = repo.list_notifications(conn, unread_only=unread, limit=limit, offset=offset)
    return NotificationPage(
        items=[NotificationOut.model_validate(asdict(row)) for row in rows], total=total
    )


@router.post("/read", response_model=MarkReadResult)
def mark_read(request: Request, body: MarkReadRequest) -> MarkReadResult:
    ids = [str(item) for item in body.ids]
    with _db(request) as conn:
        updated = repo.mark_read(conn, ids, format_instant(datetime.now(UTC)))
    return MarkReadResult(updated=updated)


@router.get("/status", response_model=ReminderStatus)
def reminder_status(request: Request) -> ReminderStatus:
    ticker: ReminderTicker | None = getattr(request.app.state, "reminders", None)
    return ReminderStatus(
        running=ticker is not None and ticker.running,
        tick_seconds=TICK_SECONDS,
        catch_up_hours=int(CATCH_UP.total_seconds() // 3600),
        last_tick_at=None if ticker is None else ticker.last_tick_at,
        last_error=None if ticker is None else ticker.last_error,
    )
