"""Mantiene al día el índice común con los datos estructurados del Workspace.

`search_documents` y `search_fts` son los de `drakter/almacen-relaciones`: aquí no
se define ninguna tabla. Los recursos los escribe `storage_index.sync_document`.
Para el resto de tipos este módulo es el único escritor: compara en SQL lo que
debería haber con lo que hay y escribe solo la diferencia antes de cada consulta,
así que ninguna búsqueda ve un dato desfasado aunque el módulo dueño no escriba
el índice en su transacción, como pide `contracts/README.md` §4.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Final

logger = logging.getLogger("drakter.search")


@dataclass(frozen=True, slots=True)
class StructuredSource:
    entity_type: str
    table: str
    title: str
    body: str


_NL: Final = "char(10)"

STRUCTURED_SOURCES: Final[tuple[StructuredSource, ...]] = (
    StructuredSource("task", "tasks", "s.title", "coalesce(s.description, '')"),
    StructuredSource("project", "projects", "s.name", "coalesce(s.description, '')"),
    StructuredSource(
        "habit",
        "habits",
        "s.name",
        f"trim(coalesce(s.description, '') || {_NL} || coalesce(s.target_note, ''), {_NL})",
    ),
    StructuredSource(
        "calendar_event",
        "calendar_events",
        "s.title",
        f"trim(coalesce(s.description, '') || {_NL} || coalesce(s.location, ''), {_NL})",
    ),
    StructuredSource(
        "subject",
        "subjects",
        "s.name",
        f"trim(coalesce(s.description, '') || {_NL} || coalesce(s.teacher, ''), {_NL})",
    ),
)


_TAGS_SQL: Final = (
    "(SELECT coalesce(group_concat(name, ' '), '') FROM ("
    "SELECT t.name AS name FROM entity_tags AS et JOIN tags AS t ON t.id = et.tag_id "
    "WHERE et.entity_id = s.id ORDER BY t.name))"
)
_WANTED_SQL: Final = " UNION ALL ".join(
    f"SELECT s.id AS entity_id, '{source.entity_type}' AS entity_type, "
    f"{source.title} AS title, {source.body} AS body, {_TAGS_SQL} AS tags "
    f"FROM {source.table} AS s"
    for source in STRUCTURED_SOURCES
)
_STALE_SQL: Final = (
    "SELECT w.entity_id, w.entity_type, w.title, w.body, w.tags "
    f"FROM ({_WANTED_SQL}) AS w "
    "LEFT JOIN search_documents AS d ON d.entity_id = w.entity_id AND d.chunk_no = 0 "
    "WHERE d.doc_id IS NULL OR d.title <> w.title OR d.body <> w.body OR d.tags <> w.tags"
)


def reconcile_structured(conn: sqlite3.Connection) -> int:
    """Lleva al índice lo que cambió y devuelve cuántas filas escribió.

    Los borrados no pasan por aquí: `ON DELETE CASCADE` desde `entities` y los
    disparadores del índice ya los resuelven. Si otra escritura retiene la base,
    la búsqueda continúa con el índice anterior: es un dato derivado.
    """
    if conn.execute(f"{_STALE_SQL} LIMIT 1").fetchone() is None:
        return 0

    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError:
        logger.warning("search index busy", extra={"event": "search_reconcile_skipped"})
        return 0
    try:
        stale = conn.execute(_STALE_SQL).fetchall()
        conn.executemany(
            "INSERT INTO search_documents (entity_id, chunk_no, entity_type, title, body, tags) "
            "VALUES (?, 0, ?, ?, ?, ?) "
            "ON CONFLICT (entity_id, chunk_no) DO UPDATE SET entity_type = excluded.entity_type, "
            "title = excluded.title, body = excluded.body, tags = excluded.tags",
            stale,
        )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return len(stale)
