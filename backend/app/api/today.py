"""`GET /api/v1/today`: read-only daily summary in an explicit timezone."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Query, Request
from zoneinfo import available_timezones

from app.core.errors import AppError
from app.database.connection import connect
from app.services.today import build_today
from app.services.today_models import TodayResponse

router = APIRouter(prefix="/api/v1", tags=["today"])
log = logging.getLogger("drakter.today")


@lru_cache(maxsize=1)
def _valid_timezones() -> frozenset[str]:
    return frozenset(available_timezones())


@router.get("/today", response_model=TodayResponse)
def get_today(request: Request, tz: str = Query(alias="timezone", min_length=1, max_length=64)) -> TodayResponse:
    if tz not in _valid_timezones():
        raise AppError("invalid_timezone", "Invalid timezone", 422)
    try:
        conn = connect(request.app.state.settings.db_path)
    except (sqlite3.Error, OSError, ValueError):
        log.exception("today: database could not be opened")
        raise AppError("service_unavailable", "Service unavailable", 503) from None
    with closing(conn):
        conn.execute("PRAGMA query_only=ON")
        return build_today(conn, tz, datetime.now(timezone.utc))
