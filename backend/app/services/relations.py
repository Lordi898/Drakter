"""Servicio de relaciones: validación por tipos, consulta inversa y elementos relacionados."""

from __future__ import annotations

import base64
import binascii
import json
import sqlite3
from typing import Any, Final, NamedTuple

from app.core.errors import AppError, ErrorDetail
from app.repositories import relations as repo
from app.schemas.relations import (
    RelatedItem, RelatedItems, RelationshipCreate, RelationshipOut, RelationshipPage,
    RelationshipSearch, RelationshipTypeOut, RelationshipUpdate,
)
from app.services.storage_ports import Actor, StorageDeps, new_id, utc_now, write_tx

# Etiqueta desde el origen y desde el destino, en español.
LABELS: Final[dict[str, tuple[str, str]]] = {
    "belongs_to": ("pertenece a", "contiene"),
    "related_to": ("relacionado con", "relacionado con"),
    "scheduled_for": ("programado para", "programa"),
    "uses_resource": ("usa el recurso", "es usado por"),
    "depends_on": ("depende de", "bloquea a"),
    "supports": ("apoya a", "recibe apoyo de"),
    "studies": ("estudia", "es estudiado por"),
    "parent_of": ("es padre de", "es hijo de"),
    "references": ("cita a", "es citado por"),
    "derived_from": ("deriva de", "da origen a"),
}


class VirtualEdge(NamedTuple):
    table: str
    column: str
    relationship_type: str
    row_type: str      # tipo de la fila de `table`
    column_type: str   # tipo de la entidad que apunta `column`
    inverted: bool     # True: la entidad de `column` es el origen de la arista


VIRTUAL_EDGES: Final[tuple[VirtualEdge, ...]] = (
    VirtualEdge("tasks", "project_id", "belongs_to", "task", "project", False),
    VirtualEdge("tasks", "subject_id", "belongs_to", "task", "subject", False),
    VirtualEdge("tasks", "parent_task_id", "parent_of", "task", "task", True),
    VirtualEdge("resources", "folder_id", "belongs_to", "resource", "folder", False),
    VirtualEdge("folders", "parent_folder_id", "parent_of", "folder", "folder", True),
    VirtualEdge("class_sessions", "subject_id", "belongs_to", "class_session", "subject", False),
)


def _out(row: sqlite3.Row) -> RelationshipOut:
    return RelationshipOut(
        id=row["id"], source_id=row["source_id"], source_type=row["source_type"],
        target_id=row["target_id"], target_type=row["target_type"],
        relationship_type=row["relationship_type"],
        metadata=json.loads(row["metadata_json"]), created_at=row["created_at"],
    )


def _not_found() -> AppError:
    return AppError("not_found", "Relationship not found", 404)


def list_types(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor) -> list[RelationshipTypeOut]:
    types, rules = repo.types_with_rules(conn)
    pairs: dict[str, list[tuple[Any, Any]]] = {}
    for r in rules:
        pairs.setdefault(r["relationship_type"], []).append((r["source_type"], r["target_type"]))
    return [
        RelationshipTypeOut(
            relationship_type=t["relationship_type"], label=LABELS[t["relationship_type"]][0],
            inverse_label=LABELS[t["relationship_type"]][1], description=t["description"],
            symmetric=bool(t["symmetric"]), allowed_pairs=pairs.get(t["relationship_type"], []),
        )
        for t in types
    ]


def create_relationship(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, data: RelationshipCreate
) -> RelationshipOut:
    if data.source_id == data.target_id:
        raise AppError("relationship_not_allowed", "An entity cannot relate to itself", 422)
    found = repo.entities_by_ids(conn, [data.source_id, data.target_id])
    src, tgt = found.get(data.source_id), found.get(data.target_id)
    if src is None or tgt is None:
        raise AppError("not_found", "Entity not found", 404)
    if src["archived_at"] is not None or tgt["archived_at"] is not None:
        raise AppError(
            "conflict", "Archived entities cannot be related", 409,
            [ErrorDetail(code="entity_archived", message="Entity is archived")])
    source_id, source_type = data.source_id, src["entity_type"]
    target_id, target_type = data.target_id, tgt["entity_type"]
    if data.relationship_type == "related_to" and source_id > target_id:
        source_id, target_id = target_id, source_id
        source_type, target_type = target_type, source_type
    if not repo.rule_exists(conn, data.relationship_type, source_type, target_type):
        raise AppError(
            "relationship_not_allowed",
            f"Relationship {data.relationship_type} is not allowed from {source_type} to {target_type}",
            422,
        )
    row = {
        "id": new_id(), "source_id": source_id, "source_type": source_type, "target_id": target_id,
        "target_type": target_type, "relationship_type": data.relationship_type,
        "metadata": data.metadata, "created_at": utc_now(),
    }
    try:
        with write_tx(conn):
            repo.insert(conn, row)
            deps.audit.record(
                conn, actor, action="relations.create", result="success", entity_type="relationship",
                entity_id=row["id"], affected_count=1,
                params={"relationship_type": data.relationship_type, "source_id": source_id,
                        "target_id": target_id},
            )
    except sqlite3.IntegrityError as exc:
        text = str(exc)
        if "relationship_cycle" in text:
            raise AppError("hierarchy_cycle", "The relationship would create a cycle", 409) from None
        if "UNIQUE" in text:
            raise AppError(
                "conflict", "The relationship already exists", 409,
                [ErrorDetail(code="duplicate", message="Duplicate relationship")]) from None
        raise AppError("relationship_not_allowed", "The relationship is not valid", 422) from None
    return RelationshipOut(**{k: row[k] for k in (
        "id", "source_id", "source_type", "target_id", "target_type", "relationship_type",
        "metadata", "created_at")})


def update_relationship(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, relationship_id: str,
    data: RelationshipUpdate,
) -> RelationshipOut:
    with write_tx(conn):
        if repo.get(conn, relationship_id) is None:
            raise _not_found()
        repo.update_metadata(conn, relationship_id, data.metadata)
        deps.audit.record(conn, actor, action="relations.update", result="success",
                          entity_type="relationship", entity_id=relationship_id, affected_count=1)
    return _out(repo.get(conn, relationship_id))  # type: ignore[arg-type]


def describe(conn: sqlite3.Connection, relationship_id: str) -> str | None:
    """Resumen legible (tipo y títulos) para confirmaciones. None si no existe."""
    row = repo.get(conn, relationship_id)
    if row is None:
        return None
    ents = repo.entities_by_ids(conn, [row["source_id"], row["target_id"]])
    title = lambda i: (ents[i]["label"] if i in ents and ents[i]["label"] else "?")  # noqa: E731
    return (f"Delete relationship '{LABELS[row['relationship_type']][0]}' between "
            f"{row['source_type']} \"{title(row['source_id'])}\" and "
            f"{row['target_type']} \"{title(row['target_id'])}\"")


def delete_relationship(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, relationship_id: str,
    confirmation_id: str | None,
) -> None:
    summary = describe(conn, relationship_id)
    if summary is None:
        raise _not_found()
    if actor.kind != "user":
        deps.gate.require(conn, actor, tool="delete_relationship",
                          args={"relationship_id": relationship_id}, summary=summary,
                          affected_count=1, confirmation_id=confirmation_id)
    with write_tx(conn):
        if repo.get(conn, relationship_id) is None:
            raise _not_found()
        repo.delete(conn, relationship_id)
        deps.audit.record(conn, actor, action="relations.delete", result="success",
                          entity_type="relationship", entity_id=relationship_id, affected_count=1)


def _encode(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def _decode(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        value = int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise AppError("validation_error", "Invalid cursor", 422) from None
    if value < 0:
        raise AppError("validation_error", "Invalid cursor", 422)
    return value


def search_relationships(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, query: RelationshipSearch
) -> RelationshipPage:
    offset = _decode(query.cursor)
    rows = repo.search(conn, source_id=query.source_id, target_id=query.target_id,
                       entity_type=query.entity_type, relationship_type=query.relationship_type,
                       limit=query.limit + 1, offset=offset)
    more = len(rows) > query.limit
    return RelationshipPage(items=[_out(r) for r in rows[: query.limit]],
                            next_cursor=_encode(offset + query.limit) if more else None)


def get_related_items(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, entity_id: str, *,
    direction: str = "both", relationship_type: str | None = None,
) -> RelatedItems:
    me = repo.entities_by_ids(conn, [entity_id]).get(entity_id)
    if me is None:
        raise AppError("not_found", "Entity not found", 404)
    my_type = me["entity_type"]
    # (relationship_id, type, direction, other_id, metadata)
    raw: list[tuple[str | None, str, str, str, dict[str, Any]]] = []
    for r in repo.for_entity(conn, entity_id, relationship_type):
        symmetric = r["relationship_type"] == "related_to"
        outgoing = r["source_id"] == entity_id
        if not symmetric and direction != "both" and direction != ("out" if outgoing else "in"):
            continue
        raw.append((r["id"], r["relationship_type"], "out" if (outgoing or symmetric) else "in",
                    r["target_id"] if outgoing else r["source_id"], json.loads(r["metadata_json"])))
    for e in VIRTUAL_EDGES:
        if relationship_type and e.relationship_type != relationship_type:
            continue
        src_col, tgt_col = (e.column, "id") if e.inverted else ("id", e.column)
        src_type, tgt_type = (e.column_type, e.row_type) if e.inverted else (e.row_type, e.column_type)
        for as_source, dirn, own_type in ((True, "out", src_type), (False, "in", tgt_type)):
            if own_type == my_type and direction in ("both", dirn):
                raw += [(None, e.relationship_type, dirn, other, {}) for other in
                        repo.virtual_pairs(conn, e.table, src_col, tgt_col, entity_id, as_source)]
    info = repo.entities_by_ids(conn, [r[3] for r in raw])
    items: list[RelatedItem] = []
    for rid, rtype, dirn, other, meta in raw:
        o = info.get(other)
        if o is None:
            continue
        items.append(RelatedItem(
            relationship_id=rid, relationship_type=rtype, direction=dirn,  # type: ignore[arg-type]
            label=LABELS[rtype][0 if dirn == "out" else 1], entity_id=other,
            entity_type=o["entity_type"], entity_title=o["label"] or "", archived=o["archived_at"] is not None,
            virtual=rid is None, metadata=meta,
        ))
    return RelatedItems(entity_id=entity_id, entity_type=my_type, entity_title=me["label"] or "", items=items)


def count_for_entity(conn: sqlite3.Connection, entity_id: str) -> int:
    return repo.count_for_entity(conn, entity_id)


def detach_entity(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, entity_id: str) -> int:
    """Borra las relaciones de la entidad dentro de la transacción de quien llama."""
    return repo.delete_for_entity(conn, entity_id)
