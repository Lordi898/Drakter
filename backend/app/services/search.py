"""Búsqueda global sobre el índice común (`search_documents` + `search_fts`)."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from typing import Final

from app.services.search_index import reconcile_structured
from app.services.search_schemas import (
    ALL_ENTITY_TYPES,
    MAX_LIMIT,
    MAX_OFFSET,
    MAX_QUERY_CHARS,
    SearchEntityType,
    SearchItem,
    SearchPage,
    SnippetPart,
)

MAX_TERMS: Final = 12
MAX_TITLE_CHARS: Final = 300
SNIPPET_TOKENS: Final = 16
# bm25 por columna: título, cuerpo, etiquetas.
_COLUMN_WEIGHTS: Final = "8.0, 1.0, 4.0"
# Uso privado de Unicode: ningún documento puede imitar un marcador de HTML o texto.
_MATCH_OPEN: Final = ""
_MATCH_CLOSE: Final = ""
_MARKER_SPLIT: Final = re.compile(f"([{_MATCH_OPEN}{_MATCH_CLOSE}])")
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


def _snippet_parts(raw: str, title: str) -> list[SnippetPart]:
    parts: list[SnippetPart] = []
    inside = False
    for piece in _MARKER_SPLIT.split(raw):
        if piece == _MATCH_OPEN:
            inside = True
        elif piece == _MATCH_CLOSE:
            inside = False
        else:
            text = _UNSAFE_TEXT.sub(" ", piece).replace("\n", " ").replace("\t", " ")
            if text:
                parts.append(SnippetPart(text=text, match=inside))
    # Un extracto que solo repite el título no aporta nada a la fila.
    return [] if _plain("".join(part.text for part in parts)) == title else parts


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


def _select_sql(matches: str) -> str:
    # snippet() y bm25() solo existen dentro de la consulta que recorre el FTS.
    return f"""
        WITH matches AS (
            SELECT d.entity_id, d.entity_type, d.chunk_no, d.title,
                   bm25(search_fts, {_COLUMN_WEIGHTS}) AS score,
                   snippet(search_fts, -1, ?, ?, '…', {SNIPPET_TOKENS}) AS excerpt
            {matches}
        ),
        ranked AS (
            SELECT *, row_number() OVER (
                PARTITION BY entity_id ORDER BY score, chunk_no
            ) AS position
            FROM matches
        )
        SELECT r.entity_id, r.entity_type, coalesce(h.title, r.title) AS title, r.excerpt
        FROM ranked AS r
        LEFT JOIN search_documents AS h ON h.entity_id = r.entity_id AND h.chunk_no = 0
        WHERE r.position = 1
        ORDER BY r.score, r.entity_id
        LIMIT ? OFFSET ?
    """


def search_global(
    conn: sqlite3.Connection,
    *,
    q: str,
    types: Sequence[SearchEntityType] | None = None,
    limit: int = 20,
    offset: int = 0,
    agent: bool = False,
) -> SearchPage:
    """Devuelve la mejor coincidencia de cada entidad no archivada.

    Con `agent=True` se ocultan los recursos de ubicaciones sin `agent_read` o
    desactivadas. Todo lo que sale de un recurso va con `trust="untrusted"`.
    """
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, min(offset, MAX_OFFSET))
    match = build_match_query(q)
    if match is None:
        return SearchPage(items=[], total=0)

    wanted = list(dict.fromkeys(types or ALL_ENTITY_TYPES))
    reconcile_structured(conn)
    matches = _matches_sql(len(wanted), _AGENT_VISIBILITY if agent else "")
    filters = (match, *wanted)
    total = conn.execute(f"SELECT count(DISTINCT d.entity_id) {matches}", filters).fetchone()[0]
    rows = conn.execute(
        _select_sql(matches),
        (_MATCH_OPEN, _MATCH_CLOSE, *filters, limit, offset),
    ).fetchall()

    items: list[SearchItem] = []
    for entity_id, entity_type, raw_title, excerpt in rows:
        title = _plain(str(raw_title))[:MAX_TITLE_CHARS]
        items.append(
            SearchItem(
                entity_type=entity_type,
                entity_id=str(entity_id),
                title=title,
                snippet=_snippet_parts(str(excerpt or ""), title),
                trust="untrusted" if entity_type == "resource" else "workspace",
            )
        )
    return SearchPage(items=items, total=int(total))
