"""SQL del almacén: ubicaciones, carpetas, recursos, etiquetas e índice FTS5.

Solo este módulo (y `relations`) toca `entities`, `tags` y `entity_tags`. Nada aquí abre
transacciones: las abre el servicio con `write_tx`.
"""

from __future__ import annotations

import base64
import binascii
import json
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Final

from app.core.errors import AppError
from app.schemas.storage import ResourceOut, ResourceSummary

UNSET: Final = object()
MAX_PAGE: Final = 100

LOCATION_COLUMNS: Final = (
    "id, path, label, read_only, agent_read, enabled, created_at, root_dev, root_ino"
)
RESOURCE_SELECT: Final = (
    "SELECT r.*, e.created_at, e.updated_at, e.archived_at, e.revision, e.metadata_json"
    " FROM resources r JOIN entities e ON e.id = r.id"
)


def rows(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    try:
        return cur.execute(sql, params).fetchall()
    finally:
        cur.close()


def row(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
    found = rows(conn, sql, params)
    return found[0] if found else None


def scalar(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> Any:
    found = row(conn, sql, params)
    return found[0] if found else None


def _marks(count: int) -> str:
    return ",".join("?" * count)


# ---------------------------------------------------------------- cursor / paging


def clamp_limit(limit: int | None, default: int = 50) -> int:
    return max(1, min(limit or default, MAX_PAGE))


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        value = int(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode())
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise AppError("validation_error", "Invalid cursor", 422) from None
    if value < 0:
        raise AppError("validation_error", "Invalid cursor", 422)
    return value


# ---------------------------------------------------------------- locations


def get_location(conn: sqlite3.Connection, location_id: str) -> sqlite3.Row | None:
    return row(conn, f"SELECT {LOCATION_COLUMNS} FROM storage_locations WHERE id = ?", (location_id,))


def list_locations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return rows(conn, f"SELECT {LOCATION_COLUMNS} FROM storage_locations ORDER BY label, id")


def insert_location(
    conn: sqlite3.Connection, *, location_id: str, path: str, label: str, agent_read: bool,
    root_dev: int, root_ino: int, now: str,
) -> None:
    conn.execute(
        "INSERT INTO storage_locations (id, path, label, read_only, agent_read, enabled, created_at,"
        " root_dev, root_ino) VALUES (?, ?, ?, 1, ?, 1, ?, ?, ?)",
        (location_id, path, label, int(agent_read), now, root_dev, root_ino),
    )


def update_location(conn: sqlite3.Connection, location_id: str, fields: Mapping[str, Any]) -> None:
    if not fields:
        return
    allowed = {"label", "agent_read", "enabled"}
    keys = [k for k in fields if k in allowed]
    conn.execute(
        f"UPDATE storage_locations SET {', '.join(f'{k} = ?' for k in keys)} WHERE id = ?",
        [*(int(fields[k]) if isinstance(fields[k], bool) else fields[k] for k in keys), location_id],
    )


def count_location_resources(conn: sqlite3.Connection, location_id: str) -> int:
    return int(scalar(conn, "SELECT COUNT(*) FROM resources WHERE location_id = ?", (location_id,)))


def delete_location(conn: sqlite3.Connection, location_id: str) -> None:
    conn.execute("DELETE FROM storage_locations WHERE id = ?", (location_id,))


# ---------------------------------------------------------------- entities


def insert_entity(
    conn: sqlite3.Connection, entity_id: str, entity_type: str, now: str, metadata: Mapping[str, Any] | None = None
) -> None:
    conn.execute(
        "INSERT INTO entities (id, entity_type, created_at, updated_at, revision, metadata_json)"
        " VALUES (?, ?, ?, ?, 1, ?)",
        (entity_id, entity_type, now, now, json.dumps(dict(metadata or {}))),
    )


def get_entity(conn: sqlite3.Connection, entity_id: str) -> sqlite3.Row | None:
    return row(conn, "SELECT * FROM entities WHERE id = ?", (entity_id,))


def bump_entity(
    conn: sqlite3.Connection, entity_id: str, now: str, *, metadata: Mapping[str, Any] | None = None,
    archived_at: Any = UNSET,
) -> None:
    sets, params = ["updated_at = ?", "revision = revision + 1"], [now]
    if metadata is not None:
        sets.append("metadata_json = ?")
        params.append(json.dumps(dict(metadata)))
    if archived_at is not UNSET:
        sets.append("archived_at = ?")
        params.append(archived_at)
    conn.execute(f"UPDATE entities SET {', '.join(sets)} WHERE id = ?", [*params, entity_id])


def count_relationships(conn: sqlite3.Connection, entity_id: str) -> int:
    return int(
        scalar(conn, "SELECT COUNT(*) FROM relationships WHERE source_id = ? OR target_id = ?", (entity_id, entity_id))
    )


# ---------------------------------------------------------------- tags


def tags_for(conn: sqlite3.Connection, entity_ids: Iterable[str]) -> dict[str, list[str]]:
    ids = list(entity_ids)
    result: dict[str, list[str]] = {i: [] for i in ids}
    for start in range(0, len(ids), 500):
        part = ids[start : start + 500]
        for r in rows(
            conn,
            "SELECT et.entity_id, t.name FROM entity_tags et JOIN tags t ON t.id = et.tag_id"
            f" WHERE et.entity_id IN ({_marks(len(part))}) ORDER BY t.name_normalized",
            part,
        ):
            result[r["entity_id"]].append(r["name"])
    return result


def set_tags(conn: sqlite3.Connection, entity_id: str, names: Iterable[str], now: str, new_id: Any) -> None:
    """Sustitución completa; las etiquetas que faltan se crean."""
    wanted: dict[str, str] = {}
    for name in names:
        clean = name.strip()
        if clean:
            wanted.setdefault(clean.casefold(), clean)
    conn.execute("DELETE FROM entity_tags WHERE entity_id = ?", (entity_id,))
    for normalized, name in wanted.items():
        tag_id = scalar(conn, "SELECT id FROM tags WHERE name_normalized = ?", (normalized,))
        if tag_id is None:
            tag_id = new_id()
            conn.execute(
                "INSERT INTO tags (id, name, name_normalized, created_at) VALUES (?, ?, ?, ?)",
                (tag_id, name, normalized, now),
            )
        conn.execute(
            "INSERT INTO entity_tags (entity_id, tag_id, created_at) VALUES (?, ?, ?)", (entity_id, tag_id, now)
        )


# ---------------------------------------------------------------- folders


def _folder_select(where: str) -> str:
    return (
        "SELECT f.id, f.name, f.parent_folder_id, e.revision, e.created_at, e.updated_at, e.archived_at,"
        " (SELECT COUNT(*) FROM resources r JOIN entities re ON re.id = r.id"
        "   WHERE r.folder_id = f.id AND re.archived_at IS NULL) AS resource_count"
        f" FROM folders f JOIN entities e ON e.id = f.id WHERE {where}"
    )


def get_folder(conn: sqlite3.Connection, folder_id: str) -> sqlite3.Row | None:
    return row(conn, _folder_select("f.id = ?"), (folder_id,))


def list_folders(conn: sqlite3.Connection, parent_id: str | None, include_archived: bool) -> list[sqlite3.Row]:
    where = "f.parent_folder_id IS ?" if parent_id is None else "f.parent_folder_id = ?"
    if not include_archived:
        where += " AND e.archived_at IS NULL"
    return rows(conn, _folder_select(where) + " ORDER BY f.name COLLATE NOCASE, f.id", (parent_id,))


def insert_folder(conn: sqlite3.Connection, folder_id: str, name: str, parent_id: str | None, now: str) -> None:
    insert_entity(conn, folder_id, "folder", now)
    conn.execute("INSERT INTO folders (id, name, parent_folder_id) VALUES (?, ?, ?)", (folder_id, name, parent_id))


def update_folder(conn: sqlite3.Connection, folder_id: str, fields: Mapping[str, Any]) -> None:
    keys = [k for k in fields if k in ("name", "parent_folder_id")]
    if keys:
        conn.execute(
            f"UPDATE folders SET {', '.join(f'{k} = ?' for k in keys)} WHERE id = ?",
            [*(fields[k] for k in keys), folder_id],
        )


def count_folder_children(conn: sqlite3.Connection, folder_id: str) -> int:
    return int(scalar(conn, "SELECT COUNT(*) FROM folders WHERE parent_folder_id = ?", (folder_id,))) + int(
        scalar(conn, "SELECT COUNT(*) FROM resources WHERE folder_id = ?", (folder_id,))
    )


def delete_folder(conn: sqlite3.Connection, folder_id: str) -> None:
    conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))  # el trigger borra la entidad


# ---------------------------------------------------------------- resources


def get_resource_row(conn: sqlite3.Connection, resource_id: str) -> sqlite3.Row | None:
    return row(conn, RESOURCE_SELECT + " WHERE r.id = ?", (resource_id,))


def metadata_of(resource_row: Mapping[str, Any] | sqlite3.Row) -> dict[str, Any]:
    try:
        data = json.loads(resource_row["metadata_json"] or "{}")
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def insert_resource(conn: sqlite3.Connection, values: Mapping[str, Any], metadata: Mapping[str, Any], now: str) -> None:
    insert_entity(conn, values["id"], "resource", now, metadata)
    keys = list(values)
    conn.execute(
        f"INSERT INTO resources ({', '.join(keys)}) VALUES ({_marks(len(keys))})", [values[k] for k in keys]
    )


_RESOURCE_COLUMNS = frozenset(
    "title folder_id location_id relative_path url note_body description mime_type size_bytes content_hash"
    " source_modified_at availability_status index_status indexed_at index_error_code resource_type".split()
)


def update_resource_fields(conn: sqlite3.Connection, resource_id: str, fields: Mapping[str, Any]) -> None:
    keys = [k for k in fields if k in _RESOURCE_COLUMNS]
    if len(keys) != len(fields):
        raise ValueError("unknown resource column")
    if keys:
        conn.execute(
            f"UPDATE resources SET {', '.join(f'{k} = ?' for k in keys)} WHERE id = ?",
            [*(fields[k] for k in keys), resource_id],
        )


def list_resource_rows(
    conn: sqlite3.Connection, *, folder_id: str | None = None, resource_type: str | None = None,
    availability: str | None = None, tag: str | None = None, include_archived: bool = False,
    location_id: str | None = None, files_only: bool = False, limit: int = 50, offset: int = 0,
) -> list[sqlite3.Row]:
    where, params = ["1 = 1"], []
    if folder_id is not None:
        where.append("r.folder_id = ?")
        params.append(folder_id)
    if resource_type is not None:
        where.append("r.resource_type = ?")
        params.append(resource_type)
    if availability is not None:
        where.append("r.availability_status = ?")
        params.append(availability)
    if tag is not None:
        where.append(
            "EXISTS (SELECT 1 FROM entity_tags et JOIN tags t ON t.id = et.tag_id"
            " WHERE et.entity_id = r.id AND t.name_normalized = ?)"
        )
        params.append(tag.strip().casefold())
    if location_id is not None:
        where.append("r.location_id = ?")
        params.append(location_id)
    if files_only:
        where.append("r.location_id IS NOT NULL")
    if not include_archived:
        where.append("e.archived_at IS NULL")
    return rows(
        conn,
        f"{RESOURCE_SELECT} WHERE {' AND '.join(where)} ORDER BY e.updated_at DESC, r.id LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )


def summary_of(r: sqlite3.Row, tags: list[str]) -> ResourceSummary:
    return ResourceSummary(
        id=r["id"], title=r["title"], resource_type=r["resource_type"], folder_id=r["folder_id"],
        mime_type=r["mime_type"], size_bytes=r["size_bytes"], availability_status=r["availability_status"],
        index_status=r["index_status"], tags=tags, revision=r["revision"], created_at=r["created_at"],
        updated_at=r["updated_at"], archived_at=r["archived_at"],
    )


def summaries(conn: sqlite3.Connection, resource_rows: Sequence[sqlite3.Row]) -> list[ResourceSummary]:
    tag_map = tags_for(conn, [r["id"] for r in resource_rows])
    return [summary_of(r, tag_map[r["id"]]) for r in resource_rows]


def out_of(r: sqlite3.Row, tags: list[str]) -> ResourceOut:
    base = summary_of(r, tags).model_dump()
    return ResourceOut(
        **base, location_id=r["location_id"], relative_path=r["relative_path"], url=r["url"],
        description=r["description"], content_hash=r["content_hash"], source_modified_at=r["source_modified_at"],
        has_note_body=r["note_body"] is not None, index_content=bool(metadata_of(r).get("index_content")),
        index_error_code=r["index_error_code"], indexed_at=r["indexed_at"],
    )


def resource_out(conn: sqlite3.Connection, resource_id: str) -> ResourceOut:
    found = get_resource_row(conn, resource_id)
    if found is None:
        raise AppError("not_found", "Resource not found", 404)
    return out_of(found, tags_for(conn, [resource_id])[resource_id])


# ---------------------------------------------------------------- search_documents / FTS5


def upsert_chunk(
    conn: sqlite3.Connection, entity_id: str, chunk_no: int, title: str, body: str, tags: str
) -> None:
    conn.execute(
        "INSERT INTO search_documents (entity_id, chunk_no, entity_type, title, body, tags)"
        " VALUES (?, ?, 'resource', ?, ?, ?)"
        " ON CONFLICT (entity_id, chunk_no) DO UPDATE SET title = excluded.title, body = excluded.body,"
        " tags = excluded.tags",
        (entity_id, chunk_no, title, body, tags),
    )


def delete_chunks_from(conn: sqlite3.Connection, entity_id: str, first_chunk: int) -> None:
    conn.execute("DELETE FROM search_documents WHERE entity_id = ? AND chunk_no >= ?", (entity_id, first_chunk))


def set_index_state(
    conn: sqlite3.Connection, resource_id: str, status: str, indexed_at: str | None, error_code: str | None
) -> None:
    update_resource_fields(
        conn, resource_id, {"index_status": status, "indexed_at": indexed_at, "index_error_code": error_code}
    )


def fts_match(query: str) -> str | None:
    """Cada término es una frase FTS5 con `"` duplicada y `*` aparte; sin sintaxis expuesta."""
    terms = [t for t in query.split() if t][:16]
    if not terms:
        return None
    return " ".join('"' + t.replace('"', '""') + '"*' for t in terms)


def search_rows(
    conn: sqlite3.Connection, match: str, types: Sequence[str] | None, agent_visible_only: bool, limit: int, offset: int
) -> list[sqlite3.Row]:
    where, params = ["search_fts MATCH ?", "e.archived_at IS NULL"], []
    if types:
        where.append(f"r.resource_type IN ({_marks(len(types))})")
        params.extend(types)
    if agent_visible_only:
        where.append("(r.location_id IS NULL OR (l.agent_read = 1 AND l.enabled = 1))")
    where = [w for w in where if w != "search_fts MATCH ?"]
    sql = (
        "WITH hits AS MATERIALIZED (SELECT rowid AS doc_id, snippet(search_fts, -1, '[', ']', '...', 16) AS snip,"
        " bm25(search_fts, 5.0, 1.0, 2.0) AS score FROM search_fts WHERE search_fts MATCH ?)"
        " SELECT d.entity_id AS id, h.snip AS snip, MIN(h.score) AS score"
        " FROM hits h JOIN search_documents d ON d.doc_id = h.doc_id"
        " JOIN entities e ON e.id = d.entity_id JOIN resources r ON r.id = d.entity_id"
        " LEFT JOIN storage_locations l ON l.id = r.location_id"
        f" WHERE {' AND '.join(where)} GROUP BY d.entity_id ORDER BY score, d.entity_id LIMIT ? OFFSET ?"
    )
    try:
        return rows(conn, sql, [match, *params, limit, offset])
    except sqlite3.OperationalError:
        return []  # consulta sin términos indexables (p. ej. solo signos)
