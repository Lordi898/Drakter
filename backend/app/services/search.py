"""Búsqueda global sobre el índice común (`search_documents` + `search_fts`)."""

from __future__ import annotations

import base64
import binascii
import json
import math
import re
import sqlite3
from collections.abc import Sequence
from typing import Final

from drakter_contracts.common import Page
from drakter_contracts.models.system import SearchHitOut

from app.core.errors import AppError
from app.services.search_index import reconcile_structured
from app.services.search_schemas import (
    ALL_ENTITY_TYPES,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MAX_QUERY_CHARS,
    SearchEntityType,
)

SearchPage = Page[SearchHitOut]

MAX_TERMS: Final = 12
MAX_TITLE_CHARS: Final = 300
SNIPPET_TOKENS: Final = 16
# bm25 por columna: título, cuerpo, etiquetas.
_COLUMN_WEIGHTS: Final = "8.0, 1.0, 4.0"
# Controles y overrides bidi: el contenido no confiable no decide cómo se ve la fila.
_UNSAFE_TEXT: Final = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f‪-‮⁦-⁩]")
_WHITESPACE: Final = re.compile(r"\s+")
# El agente no ve ni los metadatos de lo que tampoco podría leer.
_AGENT_VISIBILITY: Final = (
    "AND (d.entity_type <> 'resource' OR EXISTS ("
    "SELECT 1 FROM resources AS r LEFT JOIN storage_locations AS l ON l.id = r.location_id "
    "WHERE r.id = d.entity_id AND (r.location_id IS NULL OR (l.agent_read = 1 AND l.enabled = 1))"
    "))"
)


def build_match_query(q: str) -> str | None:
    """Entrada del usuario como literales FTS5; nunca se expone su sintaxis.

    Cada término es una frase entrecomillada con prefijo, unidas por AND implícito.
    Un término sin letras ni cifras no produce tokens y se descarta.
    """
    clean = q.encode("utf-8", "ignore").decode("utf-8").replace("\x00", " ")
    terms = [term for term in clean[:MAX_QUERY_CHARS].split() if any(c.isalnum() for c in term)]
    if not terms:
        return None
    return " ".join('"' + term.replace('"', '""') + '"*' for term in terms[:MAX_TERMS])


def _plain(value: str) -> str:
    return _WHITESPACE.sub(" ", _UNSAFE_TEXT.sub(" ", value)).strip()


def _encode_cursor(score: float, entity_id: str) -> str:
    raw = json.dumps([score, entity_id], separators=(",", ":")).encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[float, str]:
    """Clave de orden (relevancia, id). Se comprueba porque llega del cliente."""
    try:
        raw = base64.b64decode(cursor.encode("ascii"), altchars=b"-_", validate=True)
        score, entity_id = json.loads(raw)
    except (ValueError, TypeError, binascii.Error):
        raise AppError("invalid_query", "Invalid cursor", 400) from None
    if (
        type(score) is not float
        or not math.isfinite(score)
        or not isinstance(entity_id, str)
        or len(entity_id) > 36
    ):
        raise AppError("invalid_query", "Invalid cursor", 400)
    return score, entity_id


def _matches_sql(type_count: int, visibility: str) -> str:
    placeholders = ", ".join("?" for _ in range(type_count))
    return f"""
        FROM search_fts
        JOIN search_documents AS d ON d.doc_id = search_fts.rowid
        JOIN entities AS e ON e.id = d.entity_id
        WHERE search_fts MATCH ?
          AND e.archived_at IS NULL
          AND d.entity_type IN ({placeholders})
          {visibility}
    """


def _select_sql(matches: str, *, after_cursor: bool) -> str:
    keyset = "AND (r.score, r.entity_id) > (?, ?)" if after_cursor else ""
    # snippet() y bm25() solo existen dentro de la consulta que recorre el FTS.
    return f"""
        WITH matches AS (
            SELECT d.entity_id, d.entity_type, d.chunk_no, d.title,
                   bm25(search_fts, {_COLUMN_WEIGHTS}) AS score,
                   snippet(search_fts, -1, '', '', '…', {SNIPPET_TOKENS}) AS excerpt
            {matches}
        ),
        ranked AS (
            SELECT *, row_number() OVER (
                PARTITION BY entity_id ORDER BY score, chunk_no
            ) AS position
            FROM matches
        )
        SELECT r.entity_id, r.entity_type, coalesce(h.title, r.title) AS title, r.excerpt, r.score
        FROM ranked AS r
        LEFT JOIN search_documents AS h ON h.entity_id = r.entity_id AND h.chunk_no = 0
        WHERE r.position = 1 {keyset}
        ORDER BY r.score, r.entity_id
        LIMIT ?
    """


def search_global(
    conn: sqlite3.Connection,
    *,
    q: str,
    types: Sequence[SearchEntityType] | None = None,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    agent: bool = False,
) -> SearchPage:
    """Devuelve la mejor coincidencia de cada entidad no archivada.

    Con `agent=True` se ocultan los recursos de ubicaciones sin `agent_read` o
    desactivadas. Todo resultado sale marcado como contenido no confiable.
    """
    limit = max(1, min(limit, MAX_LIMIT))
    after = _decode_cursor(cursor) if cursor is not None else None
    match = build_match_query(q)
    if match is None:
        return SearchPage(items=[], next_cursor=None, total=0)

    wanted = list(dict.fromkeys(types or ALL_ENTITY_TYPES))
    reconcile_structured(conn)
    matches = _matches_sql(len(wanted), _AGENT_VISIBILITY if agent else "")
    filters = (match, *wanted)
    total = conn.execute(f"SELECT count(DISTINCT d.entity_id) {matches}", filters).fetchone()[0]
    rows = conn.execute(
        _select_sql(matches, after_cursor=after is not None),
        (*filters, *(after or ()), limit + 1),
    ).fetchall()

    items: list[SearchHitOut] = []
    for entity_id, entity_type, raw_title, excerpt, _score in rows[:limit]:
        title = _plain(str(raw_title))[:MAX_TITLE_CHARS]
        snippet = _plain(str(excerpt or ""))
        items.append(
            SearchHitOut(
                entity_type=entity_type,
                entity_id=str(entity_id),
                title=title,
                # Un extracto que solo repite el título no aporta nada a la fila.
                snippet="" if snippet == title else snippet,
            )
        )
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = _encode_cursor(float(last[4]), str(last[0]))
    return SearchPage(items=items, next_cursor=next_cursor, total=int(total))
