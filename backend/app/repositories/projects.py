"""SQL de proyectos. Sin transacciones: las abre el servicio.

También contiene la lectura de `tasks` que necesita el progreso y el borrado de proyectos,
para que el servicio de proyectos no dependa del de tareas.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any, Final

from app.repositories.tasks_shared import touch_entity

_SELECT: Final = (
    "SELECT p.id, p.name, p.description, p.status, p.priority, p.start_date, p.target_date,"
    " p.completed_at, p.manual_progress, e.created_at, e.updated_at, e.archived_at,"
    " e.revision, e.metadata_json"
    " FROM projects p JOIN entities e ON e.id = p.id"
)

_UPDATABLE: Final = frozenset(
    {
        "name", "description", "status", "priority", "start_date", "target_date",
        "completed_at", "manual_progress",
    }
)

# Solo valores de esta tabla llegan a ORDER BY.
_SORT_SQL: Final = {
    "name": "p.name COLLATE NOCASE",
    "created_at": "e.created_at",
    "updated_at": "e.updated_at",
    "target_date": "p.target_date",
    "priority": "CASE p.priority WHEN 'low' THEN 0 WHEN 'medium' THEN 1"
    " WHEN 'high' THEN 2 ELSE 3 END",
    "status": "p.status",
}


def _placeholders(values: Sequence[Any]) -> str:
    return ",".join("?" * len(values))


def _row(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    keys = (
        "id", "name", "description", "status", "priority", "start_date", "target_date",
        "completed_at", "manual_progress", "created_at", "updated_at", "archived_at",
        "revision",
    )
    data = dict(zip(keys, tuple(row)[:13], strict=True))
    data["metadata"] = json.loads(row[13]) if row[13] else {}
    return data


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def insert_project(conn: sqlite3.Connection, values: Mapping[str, Any]) -> None:
    conn.execute(
        "INSERT INTO projects (id, name, description, status, priority, start_date, target_date,"
        " completed_at, manual_progress) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            values["id"], values["name"], values["description"], values["status"],
            values["priority"], values["start_date"], values["target_date"],
            values["completed_at"], values["manual_progress"],
        ),
    )


def get_project(conn: sqlite3.Connection, project_id: str) -> dict[str, Any] | None:
    row = conn.execute(f"{_SELECT} WHERE p.id = ?", (project_id,)).fetchone()
    return None if row is None else _row(row)


def update_project_fields(
    conn: sqlite3.Connection, project_id: str, fields: Mapping[str, Any]
) -> None:
    if not fields:
        return
    unknown = set(fields) - _UPDATABLE
    if unknown:
        raise ValueError(f"unknown project columns: {sorted(unknown)}")
    assignments = ", ".join(f"{name} = ?" for name in fields)
    conn.execute(
        f"UPDATE projects SET {assignments} WHERE id = ?", (*fields.values(), project_id)
    )


def list_projects(
    conn: sqlite3.Connection,
    *,
    statuses: Sequence[str],
    priorities: Sequence[str],
    q: str | None,
    include_archived: bool,
    sort: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Devuelve la página y el total que cumple el filtro."""
    where: list[str] = []
    params: list[Any] = []
    if statuses:
        where.append(f"p.status IN ({_placeholders(statuses)})")
        params.extend(statuses)
    if priorities:
        where.append(f"p.priority IN ({_placeholders(priorities)})")
        params.extend(priorities)
    if q:
        pattern = f"%{escape_like(q)}%"
        where.append(
            "(p.name LIKE ? ESCAPE '\\' OR COALESCE(p.description, '') LIKE ? ESCAPE '\\')"
        )
        params.extend((pattern, pattern))
    if not include_archived:
        where.append("e.archived_at IS NULL")
    order: list[str] = []
    for part in sort.split(","):
        descending = part.startswith("-")
        order.append(f"{_SORT_SQL[part.removeprefix('-')]} {'DESC' if descending else 'ASC'}")
    order.append("p.id ASC")
    clause = f" WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(
        "SELECT count(*) FROM projects p JOIN entities e ON e.id = p.id" + clause, tuple(params)
    ).fetchone()[0]
    sql = _SELECT + clause + f" ORDER BY {', '.join(order)} LIMIT ? OFFSET ?"
    rows = conn.execute(sql, (*params, limit, offset)).fetchall()
    return [_row(row) for row in rows], total


def progress_counts(
    conn: sqlite3.Connection, project_ids: Sequence[str], now: str
) -> dict[str, dict[str, int]]:
    """Una consulta para todos los proyectos. Hoja = tarea sin hijos no archivados.

    Solo cuentan hojas no archivadas. `total` excluye las canceladas; `overdue` son hojas
    abiertas con `due_at` o `due_date` anterior a `now`.
    """
    found = {
        pid: {"total": 0, "completed": 0, "open": 0, "cancelled": 0, "overdue": 0}
        for pid in project_ids
    }
    if not project_ids:
        return found
    rows = conn.execute(
        "SELECT t.project_id,"
        " SUM(t.status = 'completed'),"
        " SUM(t.status NOT IN ('completed', 'cancelled')),"
        " SUM(t.status = 'cancelled'),"
        " SUM(t.status NOT IN ('completed', 'cancelled')"
        "     AND ((t.due_at IS NOT NULL AND t.due_at < ?)"
        "          OR (t.due_date IS NOT NULL AND t.due_date < substr(?, 1, 10))))"
        " FROM tasks t JOIN entities te ON te.id = t.id"
        f" WHERE t.project_id IN ({_placeholders(project_ids)}) AND te.archived_at IS NULL"
        " AND NOT EXISTS (SELECT 1 FROM tasks c JOIN entities ce ON ce.id = c.id"
        "                 WHERE c.parent_task_id = t.id AND ce.archived_at IS NULL)"
        " GROUP BY t.project_id",
        (now, now, *project_ids),
    ).fetchall()
    for project_id, completed, open_, cancelled, overdue in rows:
        counts = found[project_id]
        counts["completed"] = completed or 0
        counts["open"] = open_ or 0
        counts["cancelled"] = cancelled or 0
        counts["overdue"] = overdue or 0
        counts["total"] = counts["completed"] + counts["open"]
    return found


def task_ids_of_project(conn: sqlite3.Connection, project_id: str) -> list[str]:
    rows = conn.execute("SELECT id FROM tasks WHERE project_id = ?", (project_id,)).fetchall()
    return [row[0] for row in rows]


def release_tasks(conn: sqlite3.Connection, project_id: str, now: str) -> list[tuple[str, int]]:
    """Deja las tareas del proyecto sin proyecto y sube su revisión. Devuelve (id, revisión)."""
    task_ids = task_ids_of_project(conn, project_id)
    if not task_ids:
        return []
    conn.execute("UPDATE tasks SET project_id = NULL WHERE project_id = ?", (project_id,))
    released: list[tuple[str, int]] = []
    for task_id in task_ids:
        touch_entity(conn, task_id, now)
        row = conn.execute("SELECT revision FROM entities WHERE id = ?", (task_id,)).fetchone()
        released.append((task_id, row[0]))
    return released


def delete_project(conn: sqlite3.Connection, project_id: str) -> None:
    """Borra la fila de dominio; `trg_projects_delete_entity` borra su entidad (y sus etiquetas, en cascada)."""
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
