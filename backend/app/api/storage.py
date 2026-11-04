"""Rutas REST del almacén (ubicaciones, carpetas, recursos). Contrato: storage_relations_contract.md."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from app.api.storage_confirmation import ConfirmationRoute
from app.database.connection import connect
from app.schemas.storage import (
    Cursor,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    ReadRequest,
    ReadResult,
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
from app.services.storage_ports import Actor, StorageDeps

router = APIRouter(prefix="/api/v1", route_class=ConfirmationRoute)

ResourceId = Annotated[Uuid, Path()]
ConfirmationId = Annotated[str | None, Query(max_length=100)]


def get_deps(request: Request) -> StorageDeps:
    deps = getattr(request.app.state, "storage_deps", None)
    if deps is None:
        deps = StorageDeps(settings=request.app.state.settings)
        request.app.state.storage_deps = deps
    return deps


def actor(request: Request) -> Actor:
    return Actor("user", "rest", request.scope["state"]["request_id"])


def db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = connect(request.app.state.settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(db)]
Deps = Annotated[StorageDeps, Depends(get_deps)]
Who = Annotated[Actor, Depends(actor)]


# --- ubicaciones ---------------------------------------------------------------------------

@router.get("/storage-locations")
def list_locations(conn: Conn, deps: Deps, who: Who) -> list[StorageLocationOut]:
    return storage_catalog.list_locations(conn, deps, who)


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
    location_id: ResourceId, conn: Conn, deps: Deps, who: Who, confirmation_id: ConfirmationId = None
) -> Response:
    storage_catalog.delete_location(conn, deps, who, location_id, confirmation_id)
    return Response(status_code=204)


# --- carpetas ------------------------------------------------------------------------------

@router.get("/folders")
def list_folders(
    conn: Conn,
    deps: Deps,
    who: Who,
    parent_id: Annotated[Uuid | None, Query()] = None,
    include_archived: bool = False,
) -> list[FolderOut]:
    return storage_catalog.list_folders(conn, deps, who, parent_id, include_archived)


@router.post("/folders", status_code=201)
def create_folder(data: FolderCreate, conn: Conn, deps: Deps, who: Who) -> FolderOut:
    return storage_catalog.create_folder(conn, deps, who, data)


@router.patch("/folders/{folder_id}")
def update_folder(folder_id: ResourceId, data: FolderUpdate, conn: Conn, deps: Deps, who: Who) -> FolderOut:
    return storage_catalog.update_folder(conn, deps, who, folder_id, data)


@router.delete("/folders/{folder_id}", status_code=204)
def delete_folder(
    folder_id: ResourceId, conn: Conn, deps: Deps, who: Who, confirmation_id: ConfirmationId = None
) -> Response:
    storage_catalog.delete_folder(conn, deps, who, folder_id, confirmation_id)
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
def refresh_index(conn: Conn, deps: Deps, who: Who, confirmation_id: ConfirmationId = None) -> RefreshResult:
    return storage_index.refresh_index(conn, deps, who, confirmation_id)


@router.post("/resources/scan")
def scan_location(
    data: ScanRequest, conn: Conn, deps: Deps, who: Who, confirmation_id: ConfirmationId = None
) -> ScanResult:
    return storage_scan.scan_location(conn, deps, who, data.location_id, confirmation_id)


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
    resource_id: ResourceId, data: ResourceUpdate, conn: Conn, deps: Deps, who: Who
) -> ResourceOut:
    return storage_catalog.update_resource(conn, deps, who, resource_id, data)


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(
    resource_id: ResourceId,
    conn: Conn,
    deps: Deps,
    who: Who,
    confirmation_id: ConfirmationId = None,
    detach: bool = False,
) -> Response:
    storage_catalog.delete_resource(conn, deps, who, resource_id, confirmation_id, detach)
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
) -> ReadResult:
    return storage_catalog.read_resource(conn, deps, who, resource_id, data or ReadRequest())


@router.post("/resources/{resource_id}/index")
def index_resource(
    resource_id: ResourceId,
    conn: Conn,
    deps: Deps,
    who: Who,
    include_content: Annotated[bool | None, Query()] = None,
) -> ResourceOut:
    return storage_index.index_resource(conn, deps, who, resource_id, include_content)



