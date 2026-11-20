"""SQL de relaciones. Toca `relationships`, `relationship_*` y lee `entities` y `v_entity_labels`."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from typing import Any

_CHUNK = 400


def _marks(n: int) -> str:
    return ",".join("?" * n)


def entities_by_ids(conn: sqlite3.Connection, ids: Sequence[str]) -> dict[str, sqlite3.Row]:
    """Tipo, archivado y etiqueta de varias entidades, una consulta por lote."""
    out: dict[str, sqlite3.Row] = {}
    unique = list(dict.fromkeys(ids))
    for i in range(0, len(unique), _CHUNK):
        chunk = unique[i : i + _CHUNK]
        rows = conn.execute(
            # Subconsulta correlacionada: SQLite empuja `l.id = e.id` a cada rama del UNION ALL
            # y busca por clave primaria. Con LEFT JOIN materializaba la vista entera (todas las
            # tablas) en cada llamada: 15,7 ms frente a 0,3 ms con ~9.000 entidades.
            "SELECT e.id, e.entity_type, e.archived_at,"
            " (SELECT l.label FROM v_entity_labels l WHERE l.id = e.id) AS label FROM entities e"
            f" WHERE e.id IN ({_marks(len(chunk))})",
            chunk,
        ).fetchall()
        out.update({r["id"]: r for r in rows})
    return out


def rule_exists(conn: sqlite3.Connection, rtype: str, source_type: str, target_type: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM relationship_rules WHERE relationship_type=? AND source_type=? AND target_type=?",
        (rtype, source_type, target_type),
    ).fetchone() is not None


def insert(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO relationships (id, source_id, source_type, target_id, target_type,"
        " relationship_type, metadata_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (row["id"], row["source_id"], row["source_type"], row["target_id"], row["target_type"],
         row["relationship_type"], json.dumps(row["metadata"], ensure_ascii=False), row["created_at"]),
    )


def get(conn: sqlite3.Connection, relationship_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM relationships WHERE id = ?", (relationship_id,)).fetchone()


def update_metadata(conn: sqlite3.Connection, relationship_id: str, metadata: dict[str, Any]) -> None:
    conn.execute(
        "UPDATE relationships SET metadata_json = ? WHERE id = ?",
        (json.dumps(metadata, ensure_ascii=False), relationship_id),
    )


def delete(conn: sqlite3.Connection, relationship_id: str) -> None:
    conn.execute("DELETE FROM relationships WHERE id = ?", (relationship_id,))


def search(
    conn: sqlite3.Connection, *, source_id: str | None, target_id: str | None,
    entity_type: str | None, relationship_type: str | None, limit: int, offset: int,
) -> list[sqlite3.Row]:
    where, params = ["1=1"], []
    if source_id:
        where.append("source_id = ?"); params.append(source_id)
    if target_id:
        where.append("target_id = ?"); params.append(target_id)
    if entity_type:
        where.append("(source_type = ? OR target_type = ?)"); params += [entity_type, entity_type]
    if relationship_type:
        where.append("relationship_type = ?"); params.append(relationship_type)
    return conn.execute(
        f"SELECT * FROM relationships WHERE {' AND '.join(where)} ORDER BY created_at, id LIMIT ? OFFSET ?",
        (*params, limit, offset),
    ).fetchall()


def for_entity(conn: sqlite3.Connection, entity_id: str, relationship_type: str | None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM relationships WHERE (source_id = ? OR target_id = ?)"
    params: list[Any] = [entity_id, entity_id]
    if relationship_type:
        sql += " AND relationship_type = ?"; params.append(relationship_type)
    return conn.execute(sql + " ORDER BY created_at, id", params).fetchall()


def virtual_pairs(conn: sqlite3.Connection, table: str, src_col: str, tgt_col: str, anchor: str,
                  anchor_is_source: bool) -> list[str]:
    """Ids del otro extremo de una arista de columna. Los identificadores vienen de `VIRTUAL_EDGES`."""
    own, other = (src_col, tgt_col) if anchor_is_source else (tgt_col, src_col)
    return [r[0] for r in conn.execute(
        f"SELECT {other} FROM {table} WHERE {own} = ? AND {other} IS NOT NULL ORDER BY {other}", (anchor,)
    )]


def types_with_rules(conn: sqlite3.Connection) -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    types = conn.execute("SELECT * FROM relationship_types ORDER BY relationship_type").fetchall()
    rules = conn.execute(
        "SELECT relationship_type, source_type, target_type FROM relationship_rules"
        " ORDER BY relationship_type, source_type, target_type"
    ).fetchall()
    return types, rules


def count_for_entity(conn: sqlite3.Connection, entity_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE source_id = ? OR target_id = ?", (entity_id, entity_id)
    ).fetchone()[0]


def delete_for_entity(conn: sqlite3.Connection, entity_id: str) -> int:
    return conn.execute(
        "DELETE FROM relationships WHERE source_id = ? OR target_id = ?", (entity_id, entity_id)
    ).rowcount
