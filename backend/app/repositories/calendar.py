"""SQL parametrizado del calendario. Sin reglas de negocio ni transacciones."""

from __future__ import annotations

import sqlite3
from typing import Any

_EVENT_SELECT = (
    "SELECT c.id,c.title,c.description,c.location,c.reminder_minutes_before,c.kind,c.status,c.timezone,c.all_day,c.local_start,c.local_end,"
    "c.start_date,c.end_date_exclusive,c.starts_at_utc,c.ends_at_utc,c.rrule,"
    "e.archived_at,e.revision,e.created_at,e.updated_at "
    "FROM calendar_events c JOIN entities e ON e.id=c.id"
)
_BLOCK_SELECT = (
    "SELECT b.id,b.title,b.description,b.timezone,b.local_start,b.local_end,b.starts_at_utc,"
    "b.ends_at_utc,b.status,b.task_id,e.archived_at,e.revision,e.created_at,e.updated_at "
    "FROM time_blocks b JOIN entities e ON e.id=b.id"
)
EVENT_COLUMNS = frozenset(
    {
        "title", "description", "location", "reminder_minutes_before", "kind", "status", "timezone",
        "all_day", "local_start", "local_end", "start_date", "end_date_exclusive", "starts_at_utc", "ends_at_utc", "rrule",
        "recurrence_until_utc",
    }
)  # fmt: skip
BLOCK_COLUMNS = frozenset(
    {
        "title", "description", "timezone", "local_start", "local_end", "starts_at_utc",
        "ends_at_utc", "status", "task_id",
    }
)  # fmt: skip


def _rows(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    names = [col[0] for col in cur.description]
    return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def _update(conn: sqlite3.Connection, table: str, allowed: frozenset[str], row_id: str,
            columns: dict[str, Any]) -> None:
    if not columns:
        return
    unknown = set(columns) - allowed
    if unknown:
        raise ValueError(f"Columnas no actualizables: {sorted(unknown)}")
    assignments = ",".join(f"{name}=?" for name in columns)  # nombres de la lista blanca
    conn.execute(f"UPDATE {table} SET {assignments} WHERE id=?", (*columns.values(), row_id))


def task_exists(conn: sqlite3.Connection, task_id: str) -> bool:
    return conn.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone() is not None


# ---------------------------------------------------------------- eventos


def insert_event(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO calendar_events(id,title,description,location,reminder_minutes_before,kind,status,timezone,all_day,local_start,"
        "local_end,start_date,end_date_exclusive,starts_at_utc,ends_at_utc,rrule,recurrence_until_utc)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            values["id"], values["title"], values["description"], values["location"],
            values["reminder_minutes_before"], values["kind"], values["status"],
            values["timezone"], values["all_day"], values["local_start"], values["local_end"],
            values["start_date"], values["end_date_exclusive"], values["starts_at_utc"],
            values["ends_at_utc"], values["rrule"], values["recurrence_until_utc"],
        ),
    )  # fmt: skip


def get_event(conn: sqlite3.Connection, event_id: str) -> dict[str, Any] | None:
    rows = _rows(conn.execute(_EVENT_SELECT + " WHERE c.id=?", (event_id,)))
    return rows[0] if rows else None


def list_events(
    conn: sqlite3.Connection,
    *,
    include_archived: bool,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    clauses: list[str] = []
    params: list[Any] = []
    if not include_archived:
        clauses.append("e.archived_at IS NULL")
    if status is not None:
        clauses.append("c.status=?")
        params.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    total = conn.execute(
        "SELECT count(*) FROM calendar_events c JOIN entities e ON e.id=c.id" + where, params
    ).fetchone()[0]
    rows = _rows(
        conn.execute(
            _EVENT_SELECT + where + " ORDER BY e.created_at,c.id LIMIT ? OFFSET ?", (*params, limit, offset)
        )
    )
    return rows, int(total)


def update_event(conn: sqlite3.Connection, event_id: str, columns: dict[str, Any]) -> None:
    _update(conn, "calendar_events", EVENT_COLUMNS, event_id, columns)


def events_in_window(
    conn: sqlite3.Connection,
    *,
    start_utc: str,
    end_utc: str,
    start_date: str,
    end_date: str,
    kinds: list[str] | None,
) -> list[dict[str, Any]]:
    """No recurrentes filtrados por rango en SQL; recurrentes que empiezan antes del fin y no han acabado."""
    params: list[Any] = [
        end_utc, start_utc, end_date, start_date,  # no recurrentes
        end_utc, end_date, start_utc,  # recurrentes
    ]  # fmt: skip
    kind_clause = ""
    if kinds is not None:
        kind_clause = f" AND c.kind IN ({','.join('?' * len(kinds))})"
        params.extend(kinds)
    sql = (
        _EVENT_SELECT
        + " WHERE e.archived_at IS NULL AND ("
        "(c.rrule IS NULL AND ((c.all_day=0 AND c.starts_at_utc<? AND c.ends_at_utc>?)"
        " OR (c.all_day=1 AND c.start_date<? AND c.end_date_exclusive>?)))"
        " OR (c.rrule IS NOT NULL AND ((c.all_day=0 AND c.starts_at_utc<?) OR (c.all_day=1 AND c.start_date<?))"
        " AND (c.recurrence_until_utc IS NULL OR c.recurrence_until_utc>=?)))"
        + kind_clause
        + " ORDER BY c.id"
    )
    return _rows(conn.execute(sql, params))


def count_relationships(conn: sqlite3.Connection, entity_id: str) -> int:
    row = conn.execute(
        "SELECT count(*) FROM relationships WHERE source_id=? OR target_id=?", (entity_id, entity_id)
    ).fetchone()
    return int(row[0])


def delete_event(conn: sqlite3.Connection, event_id: str) -> None:
    conn.execute("DELETE FROM recurrence_exceptions WHERE event_id=?", (event_id,))
    conn.execute("DELETE FROM calendar_events WHERE id=?", (event_id,))


# ------------------------------------------------------------ excepciones


def get_exception(conn: sqlite3.Connection, event_id: str, occurrence: str) -> dict[str, Any] | None:
    rows = _rows(
        conn.execute(
            "SELECT id,event_id,occurrence_local_start,kind,override_json,created_at "
            "FROM recurrence_exceptions WHERE event_id=? AND occurrence_local_start=?",
            (event_id, occurrence),
        )
    )
    return rows[0] if rows else None


def insert_exception(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO recurrence_exceptions(id,event_id,occurrence_local_start,kind,override_json,"
        "created_at) VALUES(?,?,?,?,?,?)",
        (
            values["id"], values["event_id"], values["occurrence_local_start"], values["kind"],
            values["override_json"], values["created_at"],
        ),
    )  # fmt: skip


def list_exceptions(conn: sqlite3.Connection, event_id: str) -> list[dict[str, Any]]:
    return _rows(
        conn.execute(
            "SELECT id,event_id,occurrence_local_start,kind,override_json,created_at "
            "FROM recurrence_exceptions WHERE event_id=? ORDER BY occurrence_local_start",
            (event_id,),
        )
    )


def count_exceptions(conn: sqlite3.Connection, event_id: str) -> int:
    row = conn.execute(
        "SELECT count(*) FROM recurrence_exceptions WHERE event_id=?", (event_id,)
    ).fetchone()
    return int(row[0])


def exceptions_for_events(
    conn: sqlite3.Connection, event_ids: list[str]
) -> dict[str, dict[str, tuple[str, str | None]]]:
    """event_id -> occurrence_local_start -> (kind, override_json)."""
    result: dict[str, dict[str, tuple[str, str | None]]] = {}
    for i in range(0, len(event_ids), 500):
        chunk = event_ids[i : i + 500]
        cur = conn.execute(
            "SELECT event_id,occurrence_local_start,kind,override_json FROM recurrence_exceptions "
            f"WHERE event_id IN ({','.join('?' * len(chunk))})",
            chunk,
        )
        for event_id, occurrence, kind, override in cur.fetchall():
            result.setdefault(event_id, {})[occurrence] = (kind, override)
    return result


# ---------------------------------------------------------------- bloques


def insert_time_block(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO time_blocks(id,title,description,timezone,local_start,local_end,starts_at_utc,"
        "ends_at_utc,status,task_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            values["id"], values["title"], values["description"], values["timezone"],
            values["local_start"], values["local_end"], values["starts_at_utc"],
            values["ends_at_utc"], values["status"], values["task_id"],
        ),
    )  # fmt: skip


def get_time_block(conn: sqlite3.Connection, block_id: str) -> dict[str, Any] | None:
    rows = _rows(conn.execute(_BLOCK_SELECT + " WHERE b.id=?", (block_id,)))
    return rows[0] if rows else None


def list_time_blocks(
    conn: sqlite3.Connection,
    *,
    include_archived: bool,
    task_id: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    clauses: list[str] = []
    params: list[Any] = []
    if not include_archived:
        clauses.append("e.archived_at IS NULL")
    if task_id is not None:
        clauses.append("b.task_id=?")
        params.append(task_id)
    if status is not None:
        clauses.append("b.status=?")
        params.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    total = conn.execute(
        "SELECT count(*) FROM time_blocks b JOIN entities e ON e.id=b.id" + where, params
    ).fetchone()[0]
    rows = _rows(
        conn.execute(
            _BLOCK_SELECT + where + " ORDER BY b.starts_at_utc,b.id LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
    )
    return rows, int(total)


def update_time_block(conn: sqlite3.Connection, block_id: str, columns: dict[str, Any]) -> None:
    _update(conn, "time_blocks", BLOCK_COLUMNS, block_id, columns)


def blocks_in_window(conn: sqlite3.Connection, start_utc: str, end_utc: str) -> list[dict[str, Any]]:
    return _rows(
        conn.execute(
            _BLOCK_SELECT + " WHERE e.archived_at IS NULL AND b.starts_at_utc<? AND b.ends_at_utc>?"
            " ORDER BY b.starts_at_utc,b.id",
            (end_utc, start_utc),
        )
    )


def delete_time_block(conn: sqlite3.Connection, block_id: str) -> None:
    conn.execute("DELETE FROM time_blocks WHERE id=?", (block_id,))
