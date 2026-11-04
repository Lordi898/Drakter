"""Rutas REST de relaciones (`/api/v1`)."""

from __future__ import annotations

import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.storage_confirmation import ConfirmationRoute

from app.api.storage import db, get_deps
from app.schemas.relations import (
    RelatedItems, RelationshipCreate, RelationshipOut, RelationshipPage, RelationshipSearch,
    RelationshipType, RelationshipTypeOut, RelationshipUpdate, EntityType,
)
from app.schemas.storage import Cursor, Uuid
from app.services import relations as svc
from app.services.storage_ports import Actor, StorageDeps

router = APIRouter(prefix="/api/v1", tags=["relationships"], route_class=ConfirmationRoute)

Conn = Annotated[sqlite3.Connection, Depends(db)]
Deps = Annotated[StorageDeps, Depends(get_deps)]


def _actor(request: Request) -> Actor:
    return Actor("user", "rest", request.scope["state"]["request_id"])


@router.get("/relationships/types", response_model=list[RelationshipTypeOut])
def list_types(request: Request, conn: Conn, deps: Deps) -> list[RelationshipTypeOut]:
    return svc.list_types(conn, deps, _actor(request))


@router.get("/relationships", response_model=RelationshipPage)
def search_relationships(
    request: Request, conn: Conn, deps: Deps,
    source_id: Uuid | None = None, target_id: Uuid | None = None,
    entity_type: EntityType | None = None, type: RelationshipType | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50, cursor: Cursor | None = None,
) -> RelationshipPage:
    query = RelationshipSearch(source_id=source_id, target_id=target_id, entity_type=entity_type,
                               relationship_type=type, limit=limit, cursor=cursor)
    return svc.search_relationships(conn, deps, _actor(request), query)


@router.post("/relationships", response_model=RelationshipOut, status_code=201)
def create_relationship(data: RelationshipCreate, request: Request, conn: Conn, deps: Deps) -> RelationshipOut:
    return svc.create_relationship(conn, deps, _actor(request), data)


@router.patch("/relationships/{relationship_id}", response_model=RelationshipOut)
def update_relationship(
    relationship_id: Uuid, data: RelationshipUpdate, request: Request, conn: Conn, deps: Deps
) -> RelationshipOut:
    return svc.update_relationship(conn, deps, _actor(request), relationship_id, data)


@router.delete("/relationships/{relationship_id}", status_code=204)
def delete_relationship(
    relationship_id: Uuid, request: Request, conn: Conn, deps: Deps, confirmation_id: str | None = None
) -> Response:
    svc.delete_relationship(conn, deps, _actor(request), relationship_id, confirmation_id)
    return Response(status_code=204)


@router.get("/entities/{entity_id}/related", response_model=RelatedItems)
def related_items(
    entity_id: Uuid, request: Request, conn: Conn, deps: Deps,
    direction: Literal["in", "out", "both"] = "both", type: RelationshipType | None = None,
) -> RelatedItems:
    return svc.get_related_items(conn, deps, _actor(request), entity_id,
                                 direction=direction, relationship_type=type)
