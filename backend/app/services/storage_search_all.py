"""Búsqueda global sobre `search_documents` (todas las entidades indexadas), sin archivados."""

from __future__ import annotations

import sqlite3
from typing import Literal

from pydantic import BaseModel

from app.repositories import storage as repo


class SearchAllHit(BaseModel):
    entity_id: str
    entity_type: str
    title: str
    snippet: str
    content_trust: Literal["untrusted"] = "untrusted"


class SearchAllPage(BaseModel):
    items: list[SearchAllHit]
    next_cursor: str | None = None


def search_all(
    conn: sqlite3.Connection, *, q: str, types: list[str] | None = None, limit: int = 20, cursor: str | None = None
) -> SearchAllPage:
    limit, offset = repo.clamp_limit(limit, 20), repo.decode_cursor(cursor)
    match = repo.fts_match(q)
    if match is None:
        return SearchAllPage(items=[])
    where, params = ["e.archived_at IS NULL"], []
    if types:
        where.append(f"d.entity_type IN ({','.join('?' * len(types))})")
        params.extend(types)
    sql = (
        "WITH hits AS MATERIALIZED (SELECT rowid AS doc_id, snippet(search_fts, -1, '[', ']', '...', 16) AS snip,"
        " bm25(search_fts, 5.0, 1.0, 2.0) AS score FROM search_fts WHERE search_fts MATCH ?)"
        " SELECT d.entity_id AS id, d.entity_type AS kind,"
        " (SELECT t.title FROM search_documents t WHERE t.entity_id = d.entity_id AND t.chunk_no = 0) AS title,"
        " h.snip AS snip, MIN(h.score) AS score"
        " FROM hits h JOIN search_documents d ON d.doc_id = h.doc_id JOIN entities e ON e.id = d.entity_id"
        f" WHERE {' AND '.join(where)} GROUP BY d.entity_id ORDER BY score, d.entity_id LIMIT ? OFFSET ?"
    )
    try:
        found = repo.rows(conn, sql, [match, *params, limit + 1, offset])
    except sqlite3.OperationalError:
        return SearchAllPage(items=[])
    page = found[:limit]
    return SearchAllPage(
        items=[SearchAllHit(entity_id=r["id"], entity_type=r["kind"], title=r["title"] or "", snippet=r["snip"] or "")
               for r in page],
        next_cursor=repo.encode_cursor(offset + limit) if len(found) > limit else None,
    )
