"""Acceso a las tablas comunes (entities, tags, depends_on, audit_events).

Único archivo de este módulo que conoce esos nombres. Sigue el borrador `schema_v1`; si
`contracts/` los cambia, se adapta aquí. Sin `INSERT OR REPLACE` (C-16). Nada de esto
abre transacción: lo hace el servicio.
"""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Literal

from app.services.tasks_ports import Actor, new_id, utc_now

_SENSITIVE_KEYS = ("token", "secret", "password", "api_key", "apikey", "authorization", "credential")
_MAX_AUDIT_VALUE = 500


def _placeholders(values: Sequence[Any]) -> str:
    return ",".join("?" * len(values))


def insert_entity(
    conn: sqlite3.Connection,
    entity_id: str,
    entity_type: str,
    now: str,
    metadata: Mapping[str, Any],
) -> None:
    conn.execute(
        "INSERT INTO entities (id, entity_type, created_at, updated_at, metadata_json)"
        " VALUES (?, ?, ?, ?, ?)",
        (entity_id, entity_type, now, now, json.dumps(metadata, ensure_ascii=False)),
    )


def touch_entity(conn: sqlite3.Connection, entity_id: str, now: str) -> None:
    conn.execute(
        "UPDATE entities SET updated_at = ?, revision = revision + 1 WHERE id = ?",
        (now, entity_id),
    )


def set_metadata(conn: sqlite3.Connection, entity_id: str, metadata: Mapping[str, Any]) -> None:
    conn.execute(
        "UPDATE entities SET metadata_json = ? WHERE id = ?",
        (json.dumps(metadata, ensure_ascii=False), entity_id),
    )


def set_archived(conn: sqlite3.Connection, entity_ids: Sequence[str], archived_at: str | None) -> None:
    if entity_ids:
        conn.execute(
            f"UPDATE entities SET archived_at = ? WHERE id IN ({_placeholders(entity_ids)})",
            (archived_at, *entity_ids),
        )


def entity_exists(conn: sqlite3.Connection, entity_id: str, entity_type: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM entities WHERE id = ? AND entity_type = ?", (entity_id, entity_type)
    ).fetchone()
    return row is not None


def normalize_tag(name: str) -> str:
    return unicodedata.normalize("NFKC", name).strip().casefold()


def replace_tags(conn: sqlite3.Connection, entity_id: str, names: Iterable[str], now: str) -> None:
    """Crea las etiquetas que falten y deja exactamente estas en la entidad."""
    conn.execute("DELETE FROM entity_tags WHERE entity_id = ?", (entity_id,))
    seen: set[str] = set()
    for name in names:
        normalized = normalize_tag(name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        row = conn.execute(
            "SELECT id FROM tags WHERE name_normalized = ?", (normalized,)
        ).fetchone()
        if row is None:
            tag_id = new_id()
            conn.execute(
                "INSERT INTO tags (id, name, name_normalized, created_at) VALUES (?, ?, ?, ?)",
                (tag_id, name.strip(), normalized, now),
            )
        else:
            tag_id = row[0]
        conn.execute(
            "INSERT INTO entity_tags (entity_id, tag_id, created_at) VALUES (?, ?, ?)",
            (entity_id, tag_id, now),
        )


def tags_for(conn: sqlite3.Connection, entity_ids: Sequence[str]) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {entity_id: [] for entity_id in entity_ids}
    if not entity_ids:
        return found
    rows = conn.execute(
        "SELECT et.entity_id, t.id, t.name, t.color FROM entity_tags et"
        " JOIN tags t ON t.id = et.tag_id"
        f" WHERE et.entity_id IN ({_placeholders(entity_ids)}) ORDER BY t.name_normalized",
        tuple(entity_ids),
    ).fetchall()
    for entity_id, tag_id, name, color in rows:
        found[entity_id].append({"id": tag_id, "name": name, "color": color})
    return found


def list_tags(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT id, name, color FROM tags ORDER BY name_normalized").fetchall()
    return [{"id": row[0], "name": row[1], "color": row[2]} for row in rows]


def add_dependency(conn: sqlite3.Connection, task_id: str, depends_on_id: str, now: str) -> bool:
    """Devuelve False si ya existía."""
    cursor = conn.execute(
        "INSERT INTO relationships (id, source_id, source_type, target_id, target_type,"
        " relationship_type, created_at) VALUES (?, ?, 'task', ?, 'task', 'depends_on', ?)"
        " ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING",
        (new_id(), task_id, depends_on_id, now),
    )
    return cursor.rowcount > 0


def remove_dependency(conn: sqlite3.Connection, task_id: str, depends_on_id: str) -> bool:
    cursor = conn.execute(
        "DELETE FROM relationships WHERE source_id = ? AND target_id = ?"
        " AND relationship_type = 'depends_on'",
        (task_id, depends_on_id),
    )
    return cursor.rowcount > 0


def remove_all_dependencies(conn: sqlite3.Connection, task_ids: Sequence[str]) -> None:
    if task_ids:
        marks = _placeholders(task_ids)
        conn.execute(
            f"DELETE FROM relationships WHERE relationship_type = 'depends_on'"
            f" AND (source_id IN ({marks}) OR target_id IN ({marks}))",
            (*task_ids, *task_ids),
        )


def dependency_would_cycle(conn: sqlite3.Connection, task_id: str, depends_on_id: str) -> bool:
    """Llamar dentro de `BEGIN IMMEDIATE` (C-11): ¿`depends_on_id` llega ya a `task_id`?"""
    row = conn.execute(
        "WITH RECURSIVE reach(id) AS ("
        " SELECT ? UNION"
        " SELECT r.target_id FROM relationships r JOIN reach ON r.source_id = reach.id"
        " WHERE r.relationship_type = 'depends_on')"
        " SELECT 1 FROM reach WHERE id = ? LIMIT 1",
        (depends_on_id, task_id),
    ).fetchone()
    return row is not None


def dependencies_of(conn: sqlite3.Connection, task_ids: Sequence[str]) -> list[tuple[str, str]]:
    """Pares (tarea, tarea de la que depende)."""
    if not task_ids:
        return []
    rows = conn.execute(
        "SELECT source_id, target_id FROM relationships WHERE relationship_type = 'depends_on'"
        f" AND source_id IN ({_placeholders(task_ids)})",
        tuple(task_ids),
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


def dependents_of(conn: sqlite3.Connection, task_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT source_id FROM relationships WHERE relationship_type = 'depends_on'"
        " AND target_id = ?",
        (task_id,),
    ).fetchall()
    return [row[0] for row in rows]


def _redact(value: Any, key: str = "") -> Any:
    if any(mark in key.lower() for mark in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_redact(item) for item in value]
    if isinstance(value, str) and len(value) > _MAX_AUDIT_VALUE:
        return value[:_MAX_AUDIT_VALUE] + "…"
    return value


def write_audit(
    conn: sqlite3.Connection,
    actor: Actor,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    params: Mapping[str, Any] | None = None,
    changes: Mapping[str, Any] | None = None,
    affected_count: int | None = None,
    result: Literal["success", "denied", "failed", "confirmation_required"] = "success",
    error_code: str | None = None,
    duration_ms: int | None = None,
) -> None:
    conn.execute(
        "INSERT INTO audit_events (id, occurred_at, correlation_id, actor_type, origin, action,"
        " tool_name, entity_type, entity_id, affected_count, params_redacted_json, changes_json,"
        " result, error_code, confirmation_id, duration_ms)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            new_id(),
            utc_now(),
            actor.correlation_id,
            actor.actor_type,
            actor.origin,
            action,
            actor.tool_name,
            entity_type,
            entity_id,
            affected_count,
            None if params is None else json.dumps(_redact(params), ensure_ascii=False),
            None if changes is None else json.dumps(_redact(changes), ensure_ascii=False),
            result,
            error_code,
            actor.confirmation_id,
            duration_ms,
        ),
    )


def history_for(
    conn: sqlite3.Connection, entity_ids: Sequence[str], limit: int, offset: int
) -> list[dict[str, Any]]:
    """Más reciente primero. Devuelve hasta `limit + 1` para saber si hay otra página."""
    if not entity_ids:
        return []
    rows = conn.execute(
        "SELECT id, occurred_at, actor_type, origin, action, tool_name, entity_type, entity_id,"
        f" result, error_code, changes_json FROM audit_events"
        f" WHERE entity_id IN ({_placeholders(entity_ids)})"
        " ORDER BY seq DESC LIMIT ? OFFSET ?",
        (*entity_ids, limit + 1, offset),
    ).fetchall()
    keys = (
        "id", "occurred_at", "actor_type", "origin", "action", "tool_name",
        "entity_type", "entity_id", "result", "error_code",
    )
    return [
        {**dict(zip(keys, row[:10], strict=True)), "changes": json.loads(row[10]) if row[10] else None}
        for row in rows
    ]
