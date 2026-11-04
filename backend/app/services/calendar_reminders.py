"""Fuentes de recordatorios de hábitos y eventos recurrentes.

`app/services/reminders.py` cubre lo que no necesita expansión; lo recurrente llega aquí
porque depende de las reglas de cambio de hora. Cada fuente solo lee y entrega avisos
vencidos: emitirlos y deduplicarlos por `key` es del ticker. Se registran al importar
este módulo, que importa `app/api/calendar.py`; sin el módulo común no se hace nada.

Nombres y títulos son datos del usuario: no se registran en logs.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Final

from app.repositories import calendar as calendar_repo
from app.repositories import habits as habits_repo
from app.services import calendar as calendar_service
from app.services.calendar_recurrence import to_utc
from app.services.habits import _Schedule

_MAX_TITLE: Final = 120
_MORNING: Final = time(9, 0)  # Igual que `reminders.MORNING`: aviso de lo que solo tiene fecha.

try:
    from app.services.reminders import ReminderDue, register_reminder_source
except ImportError:  # Sin el módulo común, o sin `drakter_contracts`, no hay ticker.
    ReminderDue = None  # type: ignore[assignment,misc]
    register_reminder_source = None  # type: ignore[assignment]


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_TITLE else f"{text[: _MAX_TITLE - 1]}…"


def habit_reminders(conn: sqlite3.Connection, now: datetime, catch_up: timedelta) -> Iterable[Any]:
    """Un aviso por día programado, a `preferred_local_time`, si aún no hay registro."""
    habits = habits_repo.reminder_candidates(conn)
    versions = habits_repo.versions_for(conn, [row["id"] for row in habits])
    since = now - catch_up
    for habit in habits:
        schedule = _Schedule(habit, versions.get(habit["id"], []))
        moment = time.fromisoformat(habit["preferred_local_time"])
        day: date = since.astimezone(UTC).date() - timedelta(days=1)
        while day <= now.astimezone(UTC).date() + timedelta(days=1):
            fire_at = to_utc(datetime.combine(day, moment), habit["timezone"], strict=False)
            if (
                since < fire_at <= now
                and schedule.scheduled(day)
                and habits_repo.get_record(conn, habit["id"], day.isoformat()) is None
            ):
                yield ReminderDue(
                    key=f"habit:{habit['id']}:{day.isoformat()}",
                    kind="reminder.habit",
                    title=_clip(habit["name"]),
                    body=f"Hoy a las {habit['preferred_local_time']}",
                    entity_id=habit["id"],
                    fire_at=fire_at,
                )
            day += timedelta(days=1)


def recurring_event_reminders(
    conn: sqlite3.Connection, now: datetime, catch_up: timedelta
) -> Iterable[Any]:
    """Ocurrencias con aviso ya vencido que no empezaron antes del margen de recuperación."""
    events = calendar_repo.recurring_with_reminder(conn)
    if not events:
        return
    exceptions = calendar_repo.exceptions_for_events(conn, [row["id"] for row in events])
    since = now - catch_up
    for event in events:
        minutes = int(event["reminder_minutes_before"])
        lead = timedelta(minutes=minutes)
        first = since.astimezone(UTC).date() - timedelta(days=2)
        last = (now + lead).astimezone(UTC).date() + timedelta(days=2)
        items = calendar_service._expand_event(
            event, exceptions.get(event["id"], {}), first, last, event["timezone"]
        )
        for item in items:
            if item.all_day:
                assert item.start_date is not None
                start = to_utc(datetime.combine(item.start_date, _MORNING), event["timezone"], strict=False)
                body = f"El {item.start_date:%d/%m}, todo el día"
            else:
                assert item.starts_at_utc is not None
                start = datetime.fromisoformat(item.starts_at_utc.replace("Z", "+00:00"))
                body = f"Empieza a las {item.occurrence_local_start[11:16]}"
            fire_at = start - lead
            if fire_at <= now and start > since:
                yield ReminderDue(
                    key=f"event:{item.occurrence_id}:{minutes}",
                    kind="reminder.event",
                    title=_clip(item.title),
                    body=body,
                    entity_id=event["id"],
                    fire_at=fire_at,
                )


if register_reminder_source is not None:
    register_reminder_source("habits", habit_reminders)
    register_reminder_source("recurring_events", recurring_event_reminders)
