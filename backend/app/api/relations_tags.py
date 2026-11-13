"""Rutas REST de etiquetas (`/api/v1`).

La búsqueda global es `app/api/search.py` (reconcile_structured, DECISIONS 2026-11-04).
"""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from app.api.storage import db, get_deps
from app.api._storage_confirmation import ConfirmationRoute
from app.schemas.storage import Cursor, TagName, Uuid
from app.services import relations_tags as svc
from app.services.storage_ports import Actor, StorageDeps

router = APIRouter(prefix="/api/v1", tags=["tags"], route_class=ConfirmationRoute)

Conn = Annotated[sqlite3.Connection, Depends(db)]
Deps = Annotated[StorageDeps, Depends(get_deps)]


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
