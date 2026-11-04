"""Builds the `GET /api/v1/today` response. Pure with respect to the clock: `now` comes in."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.services import today_sources as sources
from app.services.today_models import TodayResponse


def build_today(conn: sqlite3.Connection, timezone_name: str, now: datetime) -> TodayResponse:
    """`timezone_name` must already be validated against `zoneinfo.available_timezones()`."""
    now = now.astimezone(timezone.utc)
    local_date = now.astimezone(ZoneInfo(timezone_name)).date()
    overdue, due_today = sources.tasks_sections(conn, timezone_name, now)
    return TodayResponse(
        date=local_date,
        timezone=timezone_name,
        generated_at=now.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        overdue=overdue,
        due_today=due_today,
        projects=sources.projects_section(conn, timezone_name, now),
        agenda=sources.agenda_section(conn, timezone_name, now),
        habits=sources.habits_section(conn, now),
    )
