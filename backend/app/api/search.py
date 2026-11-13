"""REST de la búsqueda global. Se incluye en `create_app` con `search.router`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.database.connection import connect
from app.services.search import SearchPage, search_global
from app.services.search_schemas import (
    DEFAULT_LIMIT,
    MAX_CURSOR_CHARS,
    MAX_LIMIT,
    MAX_QUERY_CHARS,
    SearchEntityType,
)

router = APIRouter(prefix="/api/v1")


@router.get("/search", response_model=SearchPage)
def search(
    request: Request,
    q: Annotated[str, Query(min_length=1, max_length=MAX_QUERY_CHARS)],
    types: Annotated[list[SearchEntityType] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=MAX_CURSOR_CHARS)] = None,
) -> SearchPage:
    conn = connect(request.app.state.settings.db_path)
    try:
        return search_global(conn, q=q, types=types, limit=limit, cursor=cursor)
    finally:
        conn.close()
