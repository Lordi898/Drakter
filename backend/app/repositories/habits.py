"""SQL parametrizado de hábitos. Sin reglas de negocio ni transacciones."""

from __future__ import annotations

import sqlite3
from typing import Any

_HABIT_SELECT = (
    "SELECT h.id,h.name,h.description,h.timezone,h.target_note,h.preferred_local_time,"
    "h.goal_project_id,h.reminder_enabled,h.status,h.start_date,h.end_date,"
    "e.archived_at,e.revision,e.created_at,e.updated_at "
    "FROM habits h JOIN entities e ON e.id=h.id"
)
# Columnas que el servicio puede actualizar: lista blanca para armar el SET.
UPDATABLE_COLUMNS = frozenset(
    {
        "name", "description", "timezone", "target_note", "preferred_local_time",
        "goal_project_id", "reminder_enabled", "status", "end_date",
    }
)  # fmt: skip


def _rows(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    names = [col[0] for col in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def project_exists(conn: sqlite3.Connection, project_id: str) -> bool:
    return conn.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone() is not None


def insert_habit(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO habits(id,name,description,timezone,target_note,preferred_local_time,"
        "goal_project_id,reminder_enabled,status,start_date,end_date) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            values["id"], values["name"], values["description"], values["timezone"],
            values["target_note"], values["preferred_local_time"], values["goal_project_id"],
            values["reminder_enabled"], values["status"], values["start_date"], values["end_date"],
        ),
    )  # fmt: skip


def get_habit(conn: sqlite3.Connection, habit_id: str) -> dict[str, Any] | None:
    rows = _rows(conn.execute(_HABIT_SELECT + " WHERE h.id=?", (habit_id,)))
    return rows[0] if rows else None


def list_habits(
    conn: sqlite3.Connection,
    *,
    include_archived: bool,
    status: str | None,
    after: tuple[str, str] | None,
    limit: int,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if not include_archived:
        clauses.append("e.archived_at IS NULL")
    if status is not None:
        clauses.append("h.status=?")
        params.append(status)
    if after is not None:
        clauses.append("(e.created_at,h.id)>(?,?)")
        params.extend(after)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    sql = _HABIT_SELECT + where + " ORDER BY e.created_at,h.id LIMIT ?"
    return _rows(conn.execute(sql, params))


def update_habit(conn: sqlite3.Connection, habit_id: str, columns: dict[str, Any]) -> None:
    if not columns:
        return
    unknown = set(columns) - UPDATABLE_COLUMNS
    if unknown:
        raise ValueError(f"Columnas no actualizables: {sorted(unknown)}")
    assignments = ",".join(f"{name}=?" for name in columns)  # nombres de la lista blanca
    conn.execute(f"UPDATE habits SET {assignments} WHERE id=?", (*columns.values(), habit_id))


def insert_version(
    conn: sqlite3.Connection,
    version_id: str,
    habit_id: str,
    rrule: str,
    valid_from: str,
    created_at: str,
) -> None:
    conn.execute(
        "INSERT INTO habit_schedule_versions(id,habit_id,rrule,valid_from,valid_until,created_at) "
        "VALUES(?,?,?,?,NULL,?)",
        (version_id, habit_id, rrule, valid_from, created_at),
    )


def close_version(conn: sqlite3.Connection, version_id: str, valid_until: str) -> None:
    conn.execute(
        "UPDATE habit_schedule_versions SET valid_until=? WHERE id=?", (valid_until, version_id)
    )


def replace_version_rrule(conn: sqlite3.Connection, version_id: str, rrule: str) -> None:
    conn.execute("UPDATE habit_schedule_versions SET rrule=? WHERE id=?", (rrule, version_id))


def versions_for(conn: sqlite3.Connection, habit_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {habit_id: [] for habit_id in habit_ids}
    if not habit_ids:
        return result
    marks = ",".join("?" * len(habit_ids))
    cur = conn.execute(
        "SELECT id,habit_id,rrule,valid_from,valid_until FROM habit_schedule_versions "
        f"WHERE habit_id IN ({marks}) ORDER BY habit_id,valid_from",
        habit_ids,
    )
    for row in _rows(cur):
        result[row["habit_id"]].append(row)
    return result


def records_on(
    conn: sqlite3.Connection, habit_ids: list[str], day: str
) -> dict[str, str]:
    """Estado del registro de `day` por hábito."""
    if not habit_ids:
        return {}
    marks = ",".join("?" * len(habit_ids))
    cur = conn.execute(
        f"SELECT habit_id,status FROM habit_records WHERE occurrence_date=? AND habit_id IN ({marks})",
        (day, *habit_ids),
    )
    return {habit_id: status for habit_id, status in cur.fetchall()}


def upsert_record(
    conn: sqlite3.Connection,
    record_id: str,
    habit_id: str,
    day: str,
    status: str,
    note: str | None,
    timestamp: str,
) -> None:
    conn.execute(
        "INSERT INTO habit_records(id,habit_id,occurrence_date,status,note,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?) ON CONFLICT(habit_id,occurrence_date) DO UPDATE SET "
        "status=excluded.status, note=excluded.note, updated_at=excluded.updated_at",
        (record_id, habit_id, day, status, note, timestamp, timestamp),
    )


def get_record(conn: sqlite3.Connection, habit_id: str, day: str) -> dict[str, Any] | None:
    cur = conn.execute(
        "SELECT id,habit_id,occurrence_date,status,note,created_at,updated_at "
        "FROM habit_records WHERE habit_id=? AND occurrence_date=?",
        (habit_id, day),
    )
    rows = _rows(cur)
    return rows[0] if rows else None


def records_between(
    conn: sqlite3.Connection, habit_id: str, start: str, end: str
) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT id,habit_id,occurrence_date,status,note,created_at,updated_at "
        "FROM habit_records WHERE habit_id=? AND occurrence_date BETWEEN ? AND ? "
        "ORDER BY occurrence_date",
        (habit_id, start, end),
    )
    return _rows(cur)
