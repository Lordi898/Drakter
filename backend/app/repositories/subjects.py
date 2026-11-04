"""SQL parametrizado de asignaturas, sesiones de clase y excepciones. Sin reglas de negocio."""

from __future__ import annotations

import sqlite3
from typing import Any

_SUBJECT_SELECT = (
    "SELECT s.id,s.name,s.description,s.teacher,s.color,"
    "(SELECT count(*) FROM class_sessions c JOIN entities ce ON ce.id=c.id "
    "WHERE c.subject_id=s.id AND ce.archived_at IS NULL) AS session_count,"
    "e.archived_at,e.revision,e.created_at,e.updated_at "
    "FROM subjects s JOIN entities e ON e.id=s.id"
)
_SESSION_SELECT = (
    "SELECT c.id,c.subject_id,c.weekday,c.starts_local_time,c.ends_local_time,c.timezone,"
    "c.valid_from,c.valid_until,c.room,e.archived_at,e.revision,e.created_at,e.updated_at "
    "FROM class_sessions c JOIN entities e ON e.id=c.id"
)
SUBJECT_COLUMNS = frozenset({"name", "description", "teacher", "color"})
SESSION_COLUMNS = frozenset(
    {"weekday", "starts_local_time", "ends_local_time", "timezone", "valid_from", "valid_until", "room"}
)


def _rows(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    names = [col[0] for col in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def _update(
    conn: sqlite3.Connection, table: str, allowed: frozenset[str], row_id: str, columns: dict[str, Any]
) -> None:
    if not columns:
        return
    unknown = set(columns) - allowed
    if unknown:
        raise ValueError(f"Columnas no actualizables: {sorted(unknown)}")
    assignments = ",".join(f"{name}=?" for name in columns)  # nombres de la lista blanca
    conn.execute(f"UPDATE {table} SET {assignments} WHERE id=?", (*columns.values(), row_id))  # noqa: S608


# --- asignaturas ---------------------------------------------------------------------------


def insert_subject(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO subjects(id,name,description,teacher,color) VALUES(?,?,?,?,?)",
        (values["id"], values["name"], values["description"], values["teacher"], values["color"]),
    )


def get_subject(conn: sqlite3.Connection, subject_id: str) -> dict[str, Any] | None:
    rows = _rows(conn.execute(_SUBJECT_SELECT + " WHERE s.id=?", (subject_id,)))
    return rows[0] if rows else None


def list_subjects(
    conn: sqlite3.Connection, *, include_archived: bool, after: tuple[str, str] | None, limit: int
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if not include_archived:
        clauses.append("e.archived_at IS NULL")
    if after is not None:
        clauses.append("(e.created_at,s.id)>(?,?)")
        params.extend(after)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    return _rows(conn.execute(_SUBJECT_SELECT + where + " ORDER BY e.created_at,s.id LIMIT ?", params))


def update_subject(conn: sqlite3.Connection, subject_id: str, columns: dict[str, Any]) -> None:
    _update(conn, "subjects", SUBJECT_COLUMNS, subject_id, columns)


def delete_subject(conn: sqlite3.Connection, subject_id: str) -> None:
    conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
    conn.execute("DELETE FROM entities WHERE id=?", (subject_id,))


def count_sessions(conn: sqlite3.Connection, subject_id: str) -> int:
    return conn.execute(
        "SELECT count(*) FROM class_sessions WHERE subject_id=?", (subject_id,)
    ).fetchone()[0]


def count_tasks(conn: sqlite3.Connection, subject_id: str) -> int:
    """`tasks` la crea otro módulo: si aún no existe (o no tiene subject_id), no hay tareas."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "subject_id" not in columns:
        return 0
    return conn.execute("SELECT count(*) FROM tasks WHERE subject_id=?", (subject_id,)).fetchone()[0]


# --- sesiones de clase ---------------------------------------------------------------------


def insert_session(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO class_sessions(id,subject_id,weekday,starts_local_time,ends_local_time,"
        "timezone,valid_from,valid_until,room) VALUES(?,?,?,?,?,?,?,?,?)",
        (
            values["id"], values["subject_id"], values["weekday"], values["starts_local_time"],
            values["ends_local_time"], values["timezone"], values["valid_from"],
            values["valid_until"], values["room"],
        ),
    )  # fmt: skip


def get_session(conn: sqlite3.Connection, session_id: str) -> dict[str, Any] | None:
    rows = _rows(conn.execute(_SESSION_SELECT + " WHERE c.id=?", (session_id,)))
    return rows[0] if rows else None


def list_sessions(
    conn: sqlite3.Connection, subject_id: str, *, include_archived: bool
) -> list[dict[str, Any]]:
    where = " WHERE c.subject_id=?" + ("" if include_archived else " AND e.archived_at IS NULL")
    return _rows(
        conn.execute(
            _SESSION_SELECT + where + " ORDER BY c.weekday,c.starts_local_time,c.id", (subject_id,)
        )
    )


def update_session(conn: sqlite3.Connection, session_id: str, columns: dict[str, Any]) -> None:
    _update(conn, "class_sessions", SESSION_COLUMNS, session_id, columns)


def delete_session(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute("DELETE FROM recurrence_exceptions WHERE class_session_id=?", (session_id,))
    conn.execute("DELETE FROM class_sessions WHERE id=?", (session_id,))
    conn.execute("DELETE FROM entities WHERE id=?", (session_id,))


def sessions_same_weekday(
    conn: sqlite3.Connection, weekday: int, exclude_id: str | None
) -> list[dict[str, Any]]:
    """Sesiones activas (no archivadas, de asignaturas no archivadas) de un día de la semana."""
    sql = (
        _SESSION_SELECT
        + " JOIN entities se ON se.id=c.subject_id"
        " WHERE c.weekday=? AND e.archived_at IS NULL AND se.archived_at IS NULL"
    )
    params: list[Any] = [weekday]
    if exclude_id is not None:
        sql += " AND c.id<>?"
        params.append(exclude_id)
    return _rows(conn.execute(sql + " ORDER BY c.starts_local_time,c.id", params))


def timetable_rows(conn: sqlite3.Connection, on_date: str) -> list[dict[str, Any]]:
    sql = (
        "SELECT c.id AS session_id,c.subject_id,s.name AS subject_name,s.color,s.teacher,c.weekday,"
        "c.starts_local_time,c.ends_local_time,c.timezone,c.room,c.valid_from,c.valid_until "
        "FROM class_sessions c JOIN subjects s ON s.id=c.subject_id "
        "JOIN entities e ON e.id=c.id JOIN entities se ON se.id=s.id "
        "WHERE e.archived_at IS NULL AND se.archived_at IS NULL "
        "AND c.valid_from<=? AND (c.valid_until IS NULL OR c.valid_until>=?) "
        "ORDER BY c.weekday,c.starts_local_time,c.id"
    )
    return _rows(conn.execute(sql, (on_date, on_date)))


def projectable_sessions(conn: sqlite3.Connection, first: str, last: str) -> list[dict[str, Any]]:
    """Sesiones activas cuya vigencia toca [first, last] (ambos inclusive), con datos de la asignatura."""
    sql = (
        "SELECT c.id,c.subject_id,s.name AS subject_name,s.description AS subject_description,"
        "s.color,c.weekday,c.starts_local_time,c.ends_local_time,c.timezone,c.room,"
        "c.valid_from,c.valid_until "
        "FROM class_sessions c JOIN subjects s ON s.id=c.subject_id "
        "JOIN entities e ON e.id=c.id JOIN entities se ON se.id=s.id "
        "WHERE e.archived_at IS NULL AND se.archived_at IS NULL "
        "AND c.valid_from<=? AND (c.valid_until IS NULL OR c.valid_until>=?) "
        "ORDER BY c.id"
    )
    return _rows(conn.execute(sql, (last, first)))


# --- excepciones ---------------------------------------------------------------------------


def session_exceptions(conn: sqlite3.Connection, session_ids: list[str]) -> list[dict[str, Any]]:
    if not session_ids:
        return []
    marks = ",".join("?" * len(session_ids))
    return _rows(
        conn.execute(
            "SELECT id,class_session_id,occurrence_local_start,kind,override_json,created_at "
            f"FROM recurrence_exceptions WHERE class_session_id IN ({marks})",  # noqa: S608
            session_ids,
        )
    )


def replace_exception(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    conn.execute(
        "DELETE FROM recurrence_exceptions WHERE class_session_id=? AND occurrence_local_start=?",
        (values["class_session_id"], values["occurrence_local_start"]),
    )
    conn.execute(
        "INSERT INTO recurrence_exceptions(id,event_id,class_session_id,occurrence_local_start,"
        "kind,override_json,created_at) VALUES(?,NULL,?,?,?,?,?)",
        (
            values["id"], values["class_session_id"], values["occurrence_local_start"],
            values["kind"], values["override_json"], values["created_at"],
        ),
    )  # fmt: skip
