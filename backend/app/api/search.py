"""REST de la búsqueda global. Se incluye en `create_app` con `search.router`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.database.connection import connect
from app.services.search import search_global
from app.services.search_schemas import (
    MAX_LIMIT,
    MAX_OFFSET,
    MAX_QUERY_CHARS,
    SearchEntityType,
    SearchPage,
)

router = APIRouter(prefix="/api/v1")


@router.get("/search", response_model=SearchPage)
def search(
    request: Request,
    q: Annotated[str, Query(min_length=1, max_length=MAX_QUERY_CHARS)],
    types: Annotated[list[SearchEntityType] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 20,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> SearchPage:
    conn = connect(request.app.state.settings.db_path)
    try:
        return search_global(conn, q=q, types=types, limit=limit, offset=offset)
    finally:
        conn.close()
