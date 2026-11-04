"""Consultas de solo lectura de vencimientos para el tick de recordatorios.

Cubre lo que no necesita expansión: tareas y eventos sin `rrule`. Las ocurrencias
recurrentes y los hábitos dependen de las reglas DST de calendario (D-18) y llegan
por `register_reminder_source`.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Final

_ACTIVE_TASK: Final = "t.status IN ('pending', 'in_progress') AND e.archived_at IS NULL"
_EVENT_BASE: Final = (
    "FROM calendar_events c JOIN entities e ON e.id = c.id "
    "WHERE c.rrule IS NULL AND c.status <> 'cancelled' AND e.archived_at IS NULL "
    "AND c.reminder_minutes_before IS NOT NULL"
)
_FIRE_AT: Final = (
    "strftime('%Y-%m-%dT%H:%M:%fZ', c.starts_at_utc, printf('-%d minutes', c.reminder_minutes_before))"
)


@dataclass(frozen=True, slots=True)
class DueTask:
    id: str
    title: str
    due_at: str | None
    due_date: str | None


@dataclass(frozen=True, slots=True)
class DueEvent:
    id: str
    title: str
    timezone: str
    starts_at_utc: str | None
    start_date: str | None
    minutes_before: int


def tasks_due_at(conn: sqlite3.Connection, after: str, until: str) -> list[DueTask]:
    """Tareas con hora de vencimiento en (after, until]."""
    rows = conn.execute(
        "SELECT t.id, t.title, t.due_at, t.due_date FROM tasks t JOIN entities e ON e.id = t.id "
        f"WHERE {_ACTIVE_TASK} AND t.due_at > ? AND t.due_at <= ? ORDER BY t.due_at",
        (after, until),
    )
    return [DueTask(*row) for row in rows]


def tasks_due_on(conn: sqlite3.Connection, first_day: str, last_day: str) -> list[DueTask]:
    """Tareas con fecha sin hora en el rango; el servicio decide con la zona local."""
    rows = conn.execute(
        "SELECT t.id, t.title, t.due_at, t.due_date FROM tasks t JOIN entities e ON e.id = t.id "
        f"WHERE {_ACTIVE_TASK} AND t.due_date >= ? AND t.due_date <= ? ORDER BY t.due_date",
        (first_day, last_day),
    )
    return [DueTask(*row) for row in rows]


def timed_events_due(conn: sqlite3.Connection, started_after: str, until: str) -> list[DueEvent]:
    """Eventos cuyo aviso ya toca (`fire_at <= until`) y que no empezaron antes de `started_after`."""
    rows = conn.execute(
        "SELECT c.id, c.title, c.timezone, c.starts_at_utc, c.start_date, c.reminder_minutes_before "
        f"{_EVENT_BASE} AND c.all_day = 0 AND c.starts_at_utc > ? AND {_FIRE_AT} <= ? "
        "ORDER BY c.starts_at_utc",
        (started_after, until),
    )
    return [DueEvent(*row) for row in rows]


def all_day_events_near(conn: sqlite3.Connection, first_day: str, last_day: str) -> list[DueEvent]:
    """Eventos de día completo candidatos; el servicio calcula su aviso con la zona del evento."""
    rows = conn.execute(
        "SELECT c.id, c.title, c.timezone, c.starts_at_utc, c.start_date, c.reminder_minutes_before "
        f"{_EVENT_BASE} AND c.all_day = 1 AND c.start_date >= ? "
        "AND date(c.start_date, printf('-%d minutes', c.reminder_minutes_before)) <= ? "
        "ORDER BY c.start_date",
        (first_day, last_day),
    )
    return [DueEvent(*row) for row in rows]
