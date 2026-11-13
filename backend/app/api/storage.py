"""Rutas REST del almacén (ubicaciones, carpetas, recursos). Contrato: storage_relations_contract.md."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from pydantic import BaseModel

from app.api._storage_confirmation import ConfirmationRoute
from app.database.connection import connect
from app.schemas.storage import (
    Cursor,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    ReadRequest,
    ReadEnvelope,
    RefreshResult,
    ResourceCreate,
    ResourceOut,
    ResourcePage,
    ResourceType,
    ResourceUpdate,
    ScanRequest,
    ScanResult,
    SearchPage,
    SearchQuery,
    StorageLocationCreate,
    StorageLocationOut,
    StorageLocationUpdate,
    AvailabilityStatus,
    TagName,
    Uuid,
)
from app.services import storage_catalog, storage_index, storage_scan
from app.services.storage_ports import Actor, StorageDeps, utc_now

router = APIRouter(prefix="/api/v1", route_class=ConfirmationRoute)

ResourceId = Annotated[Uuid, Path()]


def get_deps(request: Request) -> StorageDeps:
    deps = getattr(request.app.state, "storage_deps", None)
    if deps is None:
        deps = StorageDeps(settings=request.app.state.settings)
        request.app.state.storage_deps = deps
    return deps


def actor(request: Request) -> Actor:
    return Actor("user", "rest", request.scope["state"]["request_id"])


def db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(db)]
Deps = Annotated[StorageDeps, Depends(get_deps)]
Who = Annotated[Actor, Depends(actor)]
IfMatch = Annotated[int | None, Header(ge=1)]


class StorageLocationList(BaseModel):
    items: list[StorageLocationOut]
    next_cursor: str | None = None


class FolderList(BaseModel):
    items: list[FolderOut]
    next_cursor: str | None = None


def _with_revision[T: (FolderUpdate, ResourceUpdate)](data: T, if_match: int | None) -> T:
    """`If-Match` manda; el campo del cuerpo sigue valiendo para las herramientas."""
    return data if if_match is None else data.model_copy(update={"expected_revision": if_match})


# --- ubicaciones ---------------------------------------------------------------------------

@router.get("/storage-locations")
def list_locations(conn: Conn, deps: Deps, who: Who) -> StorageLocationList:
    return StorageLocationList(items=storage_catalog.list_locations(conn, deps, who))


@router.post("/storage-locations", status_code=201)
def create_location(data: StorageLocationCreate, conn: Conn, deps: Deps, who: Who) -> StorageLocationOut:
    return storage_catalog.create_location(conn, deps, who, data)


@router.patch("/storage-locations/{location_id}")
def update_location(
    location_id: ResourceId, data: StorageLocationUpdate, conn: Conn, deps: Deps, who: Who
) -> StorageLocationOut:
    return storage_catalog.update_location(conn, deps, who, location_id, data)


@router.delete("/storage-locations/{location_id}", status_code=204)
def delete_location(
    location_id: ResourceId, conn: Conn, deps: Deps, who: Who
) -> Response:
    storage_catalog.delete_location(conn, deps, who, location_id)
    return Response(status_code=204)


# --- carpetas ------------------------------------------------------------------------------

@router.get("/folders")
def list_folders(
    conn: Conn,
    deps: Deps,
    who: Who,
    parent_id: Annotated[Uuid | None, Query()] = None,
    include_archived: bool = False,
) -> FolderList:
    return FolderList(items=storage_catalog.list_folders(conn, deps, who, parent_id, include_archived))


@router.post("/folders", status_code=201)
def create_folder(data: FolderCreate, conn: Conn, deps: Deps, who: Who) -> FolderOut:
    return storage_catalog.create_folder(conn, deps, who, data)


@router.patch("/folders/{folder_id}")
def update_folder(
    folder_id: ResourceId, data: FolderUpdate, conn: Conn, deps: Deps, who: Who, if_match: IfMatch = None
) -> FolderOut:
    return storage_catalog.update_folder(conn, deps, who, folder_id, _with_revision(data, if_match))


@router.delete("/folders/{folder_id}", status_code=204)
def delete_folder(
    folder_id: ResourceId, conn: Conn, deps: Deps, who: Who
) -> Response:
    storage_catalog.delete_folder(conn, deps, who, folder_id)
    return Response(status_code=204)


# --- recursos: rutas fijas antes de /{id} --------------------------------------------------

@router.get("/resources/search")
def search_resources(
    conn: Conn,
    deps: Deps,
    who: Who,
    q: Annotated[SearchQuery, Query()],
    type: Annotated[list[ResourceType] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[Cursor | None, Query()] = None,
) -> SearchPage:
    return storage_index.search_resources(conn, deps, who, q=q, types=type, limit=limit, cursor=cursor)


@router.post("/resources/refresh-index")
def refresh_index(conn: Conn, deps: Deps, who: Who) -> RefreshResult:
    return storage_index.refresh_index(conn, deps, who)


@router.post("/resources/scan")
def scan_location(
    data: ScanRequest, conn: Conn, deps: Deps, who: Who
) -> ScanResult:
    return storage_scan.scan_location(conn, deps, who, data.location_id)


@router.get("/resources")
def list_resources(
    conn: Conn,
    deps: Deps,
    who: Who,
    folder_id: Annotated[Uuid | None, Query()] = None,
    type: Annotated[ResourceType | None, Query()] = None,
    availability: Annotated[AvailabilityStatus | None, Query()] = None,
    tag: Annotated[TagName | None, Query()] = None,
    include_archived: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[Cursor | None, Query()] = None,
) -> ResourcePage:
    return storage_catalog.list_resources(
        conn, deps, who,
        folder_id=folder_id, resource_type=type, availability=availability, tag=tag,
        include_archived=include_archived, limit=limit, cursor=cursor,
    )


@router.post("/resources", status_code=201)
def create_resource(data: ResourceCreate, conn: Conn, deps: Deps, who: Who) -> ResourceOut:
    return storage_catalog.create_resource(conn, deps, who, data)


@router.get("/resources/{resource_id}")
def get_resource(resource_id: ResourceId, conn: Conn, deps: Deps, who: Who) -> ResourceOut:
    return storage_catalog.get_resource(conn, deps, who, resource_id)


@router.patch("/resources/{resource_id}")
def update_resource(
    resource_id: ResourceId, data: ResourceUpdate, conn: Conn, deps: Deps, who: Who, if_match: IfMatch = None
) -> ResourceOut:
    return storage_catalog.update_resource(conn, deps, who, resource_id, _with_revision(data, if_match))


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(
    resource_id: ResourceId,
    conn: Conn,
    deps: Deps,
    who: Who,
    detach: bool = False,
) -> Response:
    storage_catalog.delete_resource(conn, deps, who, resource_id, detach)
    return Response(status_code=204)


@router.post("/resources/{resource_id}/archive")
def archive_resource(resource_id: ResourceId, conn: Conn, deps: Deps, who: Who) -> ResourceOut:
    return storage_catalog.archive_resource(conn, deps, who, resource_id)


@router.post("/resources/{resource_id}/unarchive")
def unarchive_resource(resource_id: ResourceId, conn: Conn, deps: Deps, who: Who) -> ResourceOut:
    return storage_catalog.unarchive_resource(conn, deps, who, resource_id)


@router.post("/resources/{resource_id}/read")
def read_resource(
    resource_id: ResourceId, conn: Conn, deps: Deps, who: Who, data: ReadRequest | None = None
) -> ReadEnvelope:
    result = storage_catalog.read_resource(conn, deps, who, resource_id, data or ReadRequest())
    return ReadEnvelope(
        source_type="resource",
        source_id=result.source.resource_id,
        retrieved_at=utc_now(),
        content_hash=hashlib.sha256(result.text.encode("utf-8")).hexdigest(),
        truncated=result.truncated,
        content=result.text,
        title=result.source.title,
        next_offset=result.next_offset,
        metadata=result.metadata,
    )


@router.post("/resources/{resource_id}/index")
def index_resource(
    resource_id: ResourceId,
    conn: Conn,
    deps: Deps,
    who: Who,
    include_content: Annotated[bool | None, Query()] = None,
) -> ResourceOut:
    return storage_index.index_resource(conn, deps, who, resource_id, include_content)



