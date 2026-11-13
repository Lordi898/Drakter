"""SQL de tareas. Nada de esto abre transacción: lo hace el servicio.

Las filas salen como dicts con las claves de `TaskOut`. Los campos calculados se añaden por
lotes con `with_computed`, así una página o un subárbol no cuesta una consulta por tarea.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Collection, Mapping, Sequence
from typing import Any, Final

from app.repositories.tasks_shared import dependencies_of, normalize_tag, tags_for
from app.schemas.tasks import TaskListQuery, format_timestamp

CLOSED_STATUSES: Final = ("completed", "cancelled")

_COLUMNS: Final = (
    "t.id, t.title, t.description, t.status, t.priority, t.start_at, t.due_at, t.due_date,"
    " t.completed_at, t.estimated_minutes, t.parent_task_id, t.project_id, t.subject_id,"
    " t.position, e.created_at, e.updated_at, e.archived_at, e.revision, e.metadata_json"
)
_FROM: Final = "FROM tasks t JOIN entities e ON e.id = t.id"
_UPDATABLE: Final = frozenset(
    {
        "title", "description", "status", "priority", "start_at", "due_at", "due_date",
        "completed_at", "estimated_minutes", "parent_task_id", "subject_id", "position",
    }
)
# Una fecha sin hora cuenta como el inicio de su día en UTC.
_DUE: Final = "COALESCE(t.due_at, t.due_date || 'T00:00:00.000Z')"
_PRIORITY_RANK: Final = (
    "CASE t.priority WHEN 'low' THEN 0 WHEN 'medium' THEN 1 WHEN 'high' THEN 2 ELSE 3 END"
)
_SORT_EXPRESSIONS: Final[Mapping[str, str]] = {
    "position": "t.position",
    "created_at": "e.created_at",
    "updated_at": "e.updated_at",
    "due": _DUE,
    "priority": _PRIORITY_RANK,
    "title": "t.title COLLATE NOCASE",
}


def _marks(values: Sequence[Any]) -> str:
    return ",".join("?" * len(values))


def _row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["metadata"] = json.loads(data.pop("metadata_json") or "{}")
    return data


def _escape_like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _order_by(sort: str) -> str:
    terms: list[str] = []
    for part in sort.split(","):
        key = part.removeprefix("-")
        expression = _SORT_EXPRESSIONS[key]
        if key == "due":
            terms.append(f"{expression} IS NULL")  # Sin fecha, siempre al final.
        terms.append(f"{expression} {'DESC' if part.startswith('-') else 'ASC'}")
    terms.append("t.id ASC")  # Orden total: la paginación por offset no repite filas.
    return ", ".join(terms)


def get_row(conn: sqlite3.Connection, task_id: str) -> dict[str, Any] | None:
    row = conn.execute(f"SELECT {_COLUMNS} {_FROM} WHERE t.id = ?", (task_id,)).fetchone()
    return None if row is None else _row(row)


def is_archived(conn: sqlite3.Connection, entity_id: str) -> bool:
    row = conn.execute(
        "SELECT archived_at IS NOT NULL FROM entities WHERE id = ?", (entity_id,)
    ).fetchone()
    return row is not None and bool(row[0])


def list_rows(conn: sqlite3.Connection, query: TaskListQuery) -> tuple[list[dict[str, Any]], int]:
    """Devuelve la página y el total de filas que cumplen el filtro."""
    where: list[str] = []
    params: list[Any] = []
    if query.status:
        where.append(f"t.status IN ({_marks(query.status)})")
        params.extend(query.status)
    if query.priority:
        where.append(f"t.priority IN ({_marks(query.priority)})")
        params.extend(query.priority)
    if query.project_id is not None:
        where.append("t.project_id = ?")
        params.append(str(query.project_id))
    if query.no_project:
        where.append("t.project_id IS NULL")
    if query.subject_id is not None:
        where.append("t.subject_id = ?")
        params.append(str(query.subject_id))
    if query.parent_task_id is not None:
        where.append("t.parent_task_id = ?")
        params.append(str(query.parent_task_id))
    if query.root_only:
        where.append("t.parent_task_id IS NULL")
    if query.tag:
        where.append(
            "EXISTS (SELECT 1 FROM entity_tags et JOIN tags g ON g.id = et.tag_id"
            " WHERE et.entity_id = t.id AND g.name_normalized = ?)"
        )
        params.append(normalize_tag(query.tag))
    if query.due_before is not None:
        where.append(f"{_DUE} <= ?")
        params.append(format_timestamp(query.due_before))
    if query.due_after is not None:
        where.append(f"{_DUE} >= ?")
        params.append(format_timestamp(query.due_after))
    if query.q:
        where.append("(t.title LIKE ? ESCAPE '\\' OR t.description LIKE ? ESCAPE '\\')")
        pattern = _escape_like(query.q)
        params.extend((pattern, pattern))
    if not query.include_archived:
        where.append("e.archived_at IS NULL")
    clause = f" WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT count(*) {_FROM}{clause}", tuple(params)).fetchone()[0]
    rows = conn.execute(
        f"SELECT {_COLUMNS} {_FROM}{clause} ORDER BY {_order_by(query.sort)} LIMIT ? OFFSET ?",
        (*params, query.limit, query.offset),
    ).fetchall()
    return [_row(row) for row in rows], total


def subtree(conn: sqlite3.Connection, root_id: str) -> list[dict[str, Any]]:
    """La raíz primero y después por niveles; `level` es relativo a la raíz."""
    rows = conn.execute(
        "WITH RECURSIVE sub(id, level) AS ("
        " SELECT ?, 0"
        " UNION ALL"
        " SELECT c.id, sub.level + 1 FROM tasks c JOIN sub ON c.parent_task_id = sub.id)"
        f" SELECT {_COLUMNS}, sub.level AS level FROM sub"
        " JOIN tasks t ON t.id = sub.id JOIN entities e ON e.id = t.id"
        " ORDER BY sub.level, t.position, t.id",
        (root_id,),
    ).fetchall()
    return [_row(row) for row in rows]


def depth_of(conn: sqlite3.Connection, task_id: str) -> int:
    return _depths(conn, [task_id]).get(task_id, 0)


def _depths(conn: sqlite3.Connection, task_ids: Sequence[str]) -> dict[str, int]:
    rows = conn.execute(
        "WITH RECURSIVE up(task_id, parent_id, depth) AS ("
        f" SELECT id, parent_task_id, 0 FROM tasks WHERE id IN ({_marks(task_ids)})"
        " UNION ALL"
        " SELECT up.task_id, p.parent_task_id, up.depth + 1 FROM up"
        " JOIN tasks p ON p.id = up.parent_id)"
        " SELECT task_id, MAX(depth) FROM up GROUP BY task_id",
        tuple(task_ids),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _subtask_counts(
    conn: sqlite3.Connection, task_ids: Sequence[str]
) -> dict[str, tuple[int, int]]:
    """Hijos directos no archivados."""
    rows = conn.execute(
        "SELECT c.parent_task_id, COUNT(*), SUM(c.status = 'completed') FROM tasks c"
        " JOIN entities ce ON ce.id = c.id"
        f" WHERE c.parent_task_id IN ({_marks(task_ids)}) AND ce.archived_at IS NULL"
        " GROUP BY c.parent_task_id",
        tuple(task_ids),
    ).fetchall()
    return {row[0]: (row[1], row[2]) for row in rows}


def _statuses(conn: sqlite3.Connection, task_ids: Sequence[str]) -> dict[str, str]:
    if not task_ids:
        return {}
    rows = conn.execute(
        f"SELECT id, status FROM tasks WHERE id IN ({_marks(task_ids)})", tuple(task_ids)
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _unresolved_pairs(
    conn: sqlite3.Connection, task_ids: Sequence[str], ignore: Collection[str] = ()
) -> list[tuple[str, str]]:
    pairs = [pair for pair in dependencies_of(conn, task_ids) if pair[1] not in ignore]
    statuses = _statuses(conn, sorted({target for _, target in pairs}))
    return [
        (task_id, target)
        for task_id, target in pairs
        if target in statuses and statuses[target] not in CLOSED_STATUSES
    ]


def unresolved_dependencies(
    conn: sqlite3.Connection, task_ids: Sequence[str], ignore: Collection[str] = ()
) -> set[str]:
    return {target for _, target in _unresolved_pairs(conn, task_ids, ignore)}


def with_computed(
    conn: sqlite3.Connection, rows: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Añade `tags`, `depth`, `subtask_count`, `completed_subtask_count` y `blocked`."""
    if not rows:
        return []
    ids = [row["id"] for row in rows]
    depths = _depths(conn, ids)
    counts = _subtask_counts(conn, ids)
    tags = tags_for(conn, ids)
    blocked = {task_id for task_id, _ in _unresolved_pairs(conn, ids)}
    return [
        {
            **row,
            "tags": tags[row["id"]],
            "depth": depths.get(row["id"], 0),
            "subtask_count": counts.get(row["id"], (0, 0))[0],
            "completed_subtask_count": counts.get(row["id"], (0, 0))[1],
            "blocked": row["id"] in blocked,
        }
        for row in rows
    ]


def task_refs(conn: sqlite3.Connection, task_ids: Sequence[str]) -> list[dict[str, Any]]:
    if not task_ids:
        return []
    rows = conn.execute(
        f"SELECT id, title, status FROM tasks WHERE id IN ({_marks(task_ids)})"
        " ORDER BY position, id",
        tuple(task_ids),
    ).fetchall()
    return [dict(row) for row in rows]


def next_position(conn: sqlite3.Connection, parent_id: str | None, project_id: str | None) -> float:
    """Último del grupo de hermanos + 1. Las raíces se agrupan por proyecto."""
    if parent_id is not None:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM tasks WHERE parent_task_id = ?",
            (parent_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM tasks"
            " WHERE parent_task_id IS NULL AND project_id IS ?",
            (project_id,),
        ).fetchone()
    return float(row[0])


def insert_task(conn: sqlite3.Connection, values: Mapping[str, Any]) -> None:
    conn.execute(
        "INSERT INTO tasks (id, title, description, status, priority, start_at, due_at, due_date,"
        " estimated_minutes, parent_task_id, project_id, subject_id, position)"
        " VALUES (:id, :title, :description, :status, :priority, :start_at, :due_at, :due_date,"
        " :estimated_minutes, :parent_task_id, :project_id, :subject_id, :position)",
        values,
    )


def update_fields(conn: sqlite3.Connection, task_id: str, fields: Mapping[str, Any]) -> None:
    """Las columnas salen de `_UPDATABLE`; una clave desconocida es un error de programación."""
    if not fields:
        return
    unknown = set(fields) - _UPDATABLE
    if unknown:
        raise ValueError(f"unknown_task_columns: {sorted(unknown)}")
    assignments = ", ".join(f"{name} = ?" for name in fields)
    conn.execute(
        f"UPDATE tasks SET {assignments} WHERE id = ?", (*fields.values(), task_id)
    )


def set_project(
    conn: sqlite3.Connection, task_ids: Sequence[str], project_id: str | None
) -> None:
    if task_ids:
        conn.execute(
            f"UPDATE tasks SET project_id = ? WHERE id IN ({_marks(task_ids)})",
            (project_id, *task_ids),
        )


def mark_completed(conn: sqlite3.Connection, task_ids: Sequence[str], now: str) -> None:
    if task_ids:
        conn.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ?"
            f" WHERE id IN ({_marks(task_ids)})",
            (now, *task_ids),
        )


def count_blocking_relationships(conn: sqlite3.Connection, task_ids: Sequence[str]) -> int:
    """Relaciones que no son `depends_on`: su FK RESTRICT impide borrar la entidad."""
    if not task_ids:
        return 0
    marks = _marks(task_ids)
    return conn.execute(
        "SELECT count(*) FROM relationships WHERE relationship_type <> 'depends_on'"
        f" AND (source_id IN ({marks}) OR target_id IN ({marks}))",
        (*task_ids, *task_ids),
    ).fetchone()[0]


def delete_rows(conn: sqlite3.Connection, task_ids_bottom_up: Sequence[str]) -> None:
    """El orden importa: `fk_tasks_parent` es RESTRICT. El trigger borra cada entidad."""
    for task_id in task_ids_bottom_up:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
