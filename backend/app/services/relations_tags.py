"""Etiquetas: listado, lectura y sustitución por entidad. El índice de recursos se refresca en la misma transacción."""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel

from app.core.errors import AppError
from app.repositories import storage as repo
from app.services import storage_index
from app.services.storage_ports import Actor, StorageDeps, new_id, utc_now, write_tx

MAX_TAGS_PER_ENTITY = 50


class TagOut(BaseModel):
    id: str
    name: str
    color: str | None = None
    usage_count: int = 0


class TagPage(BaseModel):
    items: list[TagOut]
    next_cursor: str | None = None


def _out(r: sqlite3.Row) -> TagOut:
    return TagOut(id=r["id"], name=r["name"], color=r["color"], usage_count=r["uses"])


def _normalize(name: str) -> str:
    return name.strip().casefold()


def list_tags(conn: sqlite3.Connection, *, q: str | None = None, limit: int = 50, cursor: str | None = None) -> TagPage:
    limit, offset = repo.clamp_limit(limit), repo.decode_cursor(cursor)
    where, params = "", []
    if q and q.strip():
        escaped = _normalize(q).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where, params = " WHERE t.name_normalized LIKE ? ESCAPE '\\'", [f"%{escaped}%"]
    found = repo.rows(
        conn,
        "SELECT t.id, t.name, t.color, (SELECT COUNT(*) FROM entity_tags et WHERE et.tag_id = t.id) AS uses"
        f" FROM tags t{where} ORDER BY t.name_normalized LIMIT ? OFFSET ?",
        [*params, limit + 1, offset],
    )
    return TagPage(items=[_out(r) for r in found[:limit]],
                   next_cursor=repo.encode_cursor(offset + limit) if len(found) > limit else None)


def _require_entity(conn: sqlite3.Connection, entity_id: str) -> str:
    kind = repo.scalar(conn, "SELECT entity_type FROM entities WHERE id = ?", (entity_id,))
    if kind is None:
        raise AppError("not_found", "Entity not found", 404)
    return kind


def entity_tags(conn: sqlite3.Connection, entity_id: str) -> TagPage:
    _require_entity(conn, entity_id)
    return TagPage(items=_for_entity(conn, entity_id))


def _for_entity(conn: sqlite3.Connection, entity_id: str) -> list[TagOut]:
    return [_out(r) for r in repo.rows(
        conn,
        "SELECT t.id, t.name, t.color, (SELECT COUNT(*) FROM entity_tags x WHERE x.tag_id = t.id) AS uses"
        " FROM entity_tags et JOIN tags t ON t.id = et.tag_id WHERE et.entity_id = ? ORDER BY t.name_normalized",
        (entity_id,))]


def _apply(conn: sqlite3.Connection, entity_id: str, kind: str, names: list[str]) -> None:
    repo.set_tags(conn, entity_id, names, utc_now(), new_id)
    if kind == "resource":
        r = repo.get_resource_row(conn, entity_id)
        if r is not None:
            storage_index.sync_document(conn, r)


def _clean(names: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for n in names:
        if n.strip():
            seen.setdefault(_normalize(n), n.strip())
    if len(seen) > MAX_TAGS_PER_ENTITY:
        raise AppError("validation_error", f"At most {MAX_TAGS_PER_ENTITY} tags per item", 422)
    return list(seen.values())


def set_entity_tags(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, entity_id: str, names: list[str]
) -> TagPage:
    wanted = _clean(names)
    with write_tx(conn):
        kind = _require_entity(conn, entity_id)
        _apply(conn, entity_id, kind, wanted)
        deps.audit.record(conn, actor, action="tags.set", result="success", entity_type=kind,
                          entity_id=entity_id, affected_count=len(wanted), params={"count": len(wanted)})
    return TagPage(items=_for_entity(conn, entity_id))


def change_entity_tag(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, entity_id: str, name: str, *, add: bool
) -> TagPage:
    """add_tag / remove_tag: cambia una sola etiqueta (idempotente) y devuelve las resultantes."""
    if not name.strip():
        raise AppError("validation_error", "Tag name is empty", 422)
    key = _normalize(name)
    with write_tx(conn):
        kind = _require_entity(conn, entity_id)
        current = [t.name for t in _for_entity(conn, entity_id)]
        if add:
            names = current if any(_normalize(c) == key for c in current) else [*current, name.strip()]
        else:
            names = [c for c in current if _normalize(c) != key]
        names = _clean(names)
        if names != current:
            _apply(conn, entity_id, kind, names)
        deps.audit.record(conn, actor, action="tags.add" if add else "tags.remove", result="success",
                          entity_type=kind, entity_id=entity_id, affected_count=int(names != current),
                          params={"tag": name.strip()})
    return TagPage(items=_for_entity(conn, entity_id))
