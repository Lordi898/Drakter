"""Rutas REST de etiquetas y búsqueda global (`/api/v1`)."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from app.api.storage import db, get_deps
from app.api._storage_confirmation import ConfirmationRoute
from app.schemas.storage import Cursor, SearchQuery, TagName, Uuid
from app.services import relations_tags as svc
from app.services import storage_search_all as search
from app.services.storage_ports import Actor, StorageDeps

router = APIRouter(prefix="/api/v1", tags=["tags"], route_class=ConfirmationRoute)

Conn = Annotated[sqlite3.Connection, Depends(db)]
Deps = Annotated[StorageDeps, Depends(get_deps)]
ENTITY_TYPES = ("task", "project", "habit", "calendar_event", "time_block", "subject", "class_session",
                "resource", "folder")


class TagsReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    names: list[TagName]


def _actor(request: Request) -> Actor:
    return Actor("user", "rest", request.scope["state"]["request_id"])


@router.get("/tags", response_model=svc.TagPage)
def list_tags(conn: Conn, q: Annotated[str | None, Query(max_length=60)] = None,
              limit: Annotated[int, Query(ge=1, le=100)] = 50, cursor: Cursor | None = None) -> svc.TagPage:
    return svc.list_tags(conn, q=q, limit=limit, cursor=cursor)


@router.get("/entities/{entity_id}/tags", response_model=svc.TagPage)
def get_entity_tags(entity_id: Uuid, conn: Conn) -> svc.TagPage:
    return svc.entity_tags(conn, entity_id)


@router.put("/entities/{entity_id}/tags", response_model=svc.TagPage)
def put_entity_tags(entity_id: Uuid, data: TagsReplace, request: Request, conn: Conn, deps: Deps) -> svc.TagPage:
    return svc.set_entity_tags(conn, deps, _actor(request), entity_id, data.names)


@router.get("/search", response_model=search.SearchAllPage)
def search_all(
    conn: Conn, q: SearchQuery, types: Annotated[list[str] | None, Query(max_length=9)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20, cursor: Cursor | None = None,
) -> search.SearchAllPage:
    kinds = [t for part in (types or []) for t in part.split(",") if t]
    bad = [t for t in kinds if t not in ENTITY_TYPES]
    if bad:
        from app.core.errors import AppError
        raise AppError("validation_error", f"Unknown entity type: {bad[0]}", 422)
    return search.search_all(conn, q=q, types=kinds or None, limit=limit, cursor=cursor)
