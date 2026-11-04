"""Catálogo del almacén: ubicaciones, carpetas y recursos (archivo, enlace, nota)."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.core.errors import AppError, ErrorDetail
from app.repositories import storage as repo
from app.schemas.storage import (
    FolderCreate, FolderOut, FolderUpdate, ReadRequest, ReadResult, ReadSource, ResourceCreate, ResourceOut,
    ResourcePage, ResourceUpdate, StorageLocationCreate, StorageLocationOut, StorageLocationUpdate,
)
from app.services import readers
from app.services import storage_safefs as safefs
from app.services.readers import link as readers_link
from app.services.storage_index import (
    NOTE_TYPES, _index_file, inspect_file, location_root, sync_document, translate_error,
)
from app.services.storage_ports import Actor, StorageDeps, new_id, utc_now, write_tx

_FOLDER_ENTITY = "folder"


def _duplicate(message: str) -> AppError:
    return AppError("conflict", message, 409, [ErrorDetail(code="duplicate", message=message)])


def _denied(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, action: str, rtype: str, rid: str | None) -> AppError:
    deps.audit.record(conn, actor, action=action, result="denied", entity_type=rtype, entity_id=rid,
                      error_code="permission_denied")
    return AppError("permission_denied", "Not allowed", 403)


def _require_user(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, action: str, rid: str | None = None) -> None:
    if actor.kind != "user" or actor.origin != "rest":
        raise _denied(conn, deps, actor, action, "storage_location", rid)


def _revision_mismatch() -> AppError:
    return AppError("revision_mismatch", "The item was modified by someone else", 412)


# ---------------------------------------------------------------- ubicaciones


def _location_out(r: sqlite3.Row) -> StorageLocationOut:
    return StorageLocationOut(
        id=r["id"], path=r["path"], label=r["label"], read_only=bool(r["read_only"]),
        agent_read=bool(r["agent_read"]), enabled=bool(r["enabled"]), created_at=r["created_at"],
    )


def _location(conn: sqlite3.Connection, location_id: str) -> sqlite3.Row:
    found = repo.get_location(conn, location_id)
    if found is None:
        raise AppError("not_found", "Location not found", 404)
    return found


def list_locations(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor) -> list[StorageLocationOut]:
    if actor.is_agent:
        raise _denied(conn, deps, actor, "storage.location.list", "storage_location", None)
    return [_location_out(r) for r in repo.list_locations(conn)]


def create_location(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, data: StorageLocationCreate) -> StorageLocationOut:
    _require_user(conn, deps, actor, "storage.location.create")
    try:
        path, identity = safefs.validate_location_path(data.path, deps.denied_roots)
    except safefs.PathNotAllowed:
        raise AppError("path_not_allowed", "Path is not allowed", 403) from None
    location_id = new_id()
    try:
        with write_tx(conn):
            repo.insert_location(conn, location_id=location_id, path=str(path), label=data.label,
                                 agent_read=data.agent_read, root_dev=identity.dev, root_ino=identity.ino,
                                 now=utc_now())
            deps.audit.record(conn, actor, action="storage.location.create", result="success",
                              entity_type="storage_location", entity_id=location_id,
                              params={"agent_read": data.agent_read})
    except sqlite3.IntegrityError:
        raise _duplicate("Location already exists") from None
    return _location_out(_location(conn, location_id))


def update_location(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, location_id: str, data: StorageLocationUpdate) -> StorageLocationOut:
    _require_user(conn, deps, actor, "storage.location.update", location_id)
    _location(conn, location_id)
    fields = {k: getattr(data, k) for k in ("label", "agent_read", "enabled") if k in data.model_fields_set
              and getattr(data, k) is not None}
    with write_tx(conn):
        repo.update_location(conn, location_id, fields)
        deps.audit.record(conn, actor, action="storage.location.update", result="success",
                          entity_type="storage_location", entity_id=location_id,
                          params={k: v for k, v in fields.items() if k != "label"})
    return _location_out(_location(conn, location_id))


def repo_location_label(conn: sqlite3.Connection, location_id: str) -> str:
    row = conn.execute("SELECT label FROM storage_locations WHERE id = ?", (location_id,)).fetchone()
    return str(row["label"]) if row is not None else location_id


def delete_location(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, location_id: str, confirmation_id: str | None) -> None:
    _require_user(conn, deps, actor, "storage.location.delete", location_id)
    _location(conn, location_id)
    count = repo.count_location_resources(conn, location_id)
    if count:
        raise AppError("has_dependents", "Location still has resources", 409)
    label = repo_location_label(conn, location_id)
    deps.gate.require(conn, actor, tool="delete_storage_location", args={"location_id": location_id},
                      summary=f"Vas a eliminar 1 ubicación: «{label}». Esta acción no se puede deshacer. "
                              "Los archivos originales no se tocan.",
                      affected_count=1, confirmation_id=confirmation_id,
                      targets=[{"id": location_id}])
    with write_tx(conn):
        repo.delete_location(conn, location_id)
        deps.audit.record(conn, actor, action="storage.location.delete", result="success",
                          entity_type="storage_location", entity_id=location_id, affected_count=1)


# ---------------------------------------------------------------- carpetas


def _folder_out(r: sqlite3.Row) -> FolderOut:
    return FolderOut(**{k: r[k] for k in FolderOut.model_fields})


def _folder(conn: sqlite3.Connection, folder_id: str) -> sqlite3.Row:
    found = repo.get_folder(conn, folder_id)
    if found is None:
        raise AppError("not_found", "Folder not found", 404)
    return found


def list_folders(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, parent_id: str | None, include_archived: bool = False) -> list[FolderOut]:
    """`parent_id=None` lista las carpetas raíz."""
    return [_folder_out(r) for r in repo.list_folders(conn, parent_id, include_archived)]


def create_folder(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, data: FolderCreate) -> FolderOut:
    if data.parent_folder_id:
        _folder(conn, data.parent_folder_id)
    folder_id = new_id()
    try:
        with write_tx(conn):
            repo.insert_folder(conn, folder_id, data.name, data.parent_folder_id, utc_now())
            deps.audit.record(conn, actor, action="storage.folder.create", result="success",
                              entity_type=_FOLDER_ENTITY, entity_id=folder_id)
    except sqlite3.IntegrityError:
        raise _duplicate("Folder already exists") from None
    return _folder_out(_folder(conn, folder_id))


def update_folder(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, folder_id: str, data: FolderUpdate) -> FolderOut:
    try:
        with write_tx(conn):
            current = _folder(conn, folder_id)
            if current["revision"] != data.expected_revision:
                raise _revision_mismatch()
            fields: dict[str, Any] = {}
            if data.name is not None:
                fields["name"] = data.name
            if "parent_folder_id" in data.model_fields_set:
                if data.parent_folder_id:
                    _folder(conn, data.parent_folder_id)
                fields["parent_folder_id"] = data.parent_folder_id
            repo.update_folder(conn, folder_id, fields)
            repo.bump_entity(conn, folder_id, utc_now())
            deps.audit.record(conn, actor, action="storage.folder.update", result="success",
                              entity_type=_FOLDER_ENTITY, entity_id=folder_id)
    except sqlite3.IntegrityError as exc:
        if "folder_hierarchy_cycle" in str(exc):
            raise AppError("hierarchy_cycle", "Folder hierarchy would loop", 409) from None
        raise _duplicate("Folder already exists") from None
    except sqlite3.DatabaseError as exc:  # el trigger de ciclo usa RAISE(ABORT)
        if "folder_hierarchy_cycle" in str(exc):
            raise AppError("hierarchy_cycle", "Folder hierarchy would loop", 409) from None
        raise
    return _folder_out(_folder(conn, folder_id))


def delete_folder(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, folder_id: str, confirmation_id: str | None) -> None:
    row = _folder(conn, folder_id)
    if repo.count_folder_children(conn, folder_id):
        raise AppError("has_dependents", "Folder is not empty", 409)
    deps.gate.require(conn, actor, tool="delete_folder", args={"folder_id": folder_id},
                      summary=f"Vas a eliminar 1 carpeta: «{row['name']}». Esta acción no se puede deshacer.",
                      affected_count=1, confirmation_id=confirmation_id,
                      targets=[{"id": folder_id, "revision": row["revision"]}])
    with write_tx(conn):
        repo.delete_folder(conn, folder_id)
        deps.audit.record(conn, actor, action="storage.folder.delete", result="success",
                          entity_type=_FOLDER_ENTITY, entity_id=folder_id, affected_count=1)


# ---------------------------------------------------------------- recursos


def _resource_row(conn: sqlite3.Connection, resource_id: str) -> sqlite3.Row:
    found = repo.get_resource_row(conn, resource_id)
    if found is None:
        raise AppError("not_found", "Resource not found", 404)
    return found


def list_resources(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, *, folder_id: str | None = None,
    resource_type: str | None = None, availability: str | None = None, tag: str | None = None,
    include_archived: bool = False, limit: int = 50, cursor: str | None = None,
) -> ResourcePage:
    limit, offset = repo.clamp_limit(limit), repo.decode_cursor(cursor)
    found = repo.list_resource_rows(conn, folder_id=folder_id, resource_type=resource_type,
                                    availability=availability, tag=tag, include_archived=include_archived,
                                    limit=limit + 1, offset=offset)
    return ResourcePage(items=repo.summaries(conn, found[:limit]),
                        next_cursor=repo.encode_cursor(offset + limit) if len(found) > limit else None)


def get_resource(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, resource_id: str) -> ResourceOut:
    return repo.resource_out(conn, resource_id)


def _invalid(message: str) -> AppError:
    return AppError("validation_error", message, 422)


def create_resource(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, data: ResourceCreate) -> ResourceOut:
    is_file = data.location_id is not None or data.relative_path is not None
    shapes = [is_file, data.url is not None, data.note_body is not None]
    if sum(shapes) != 1 or (is_file and (data.location_id is None or data.relative_path is None)):
        raise _invalid("Provide exactly one of file, url or note_body")
    if is_file and actor.is_agent:
        raise _denied(conn, deps, actor, "storage.resource.create", "resource", None)
    if data.folder_id:
        _folder(conn, data.folder_id)
    values: dict[str, Any] = {
        "id": new_id(), "title": data.title, "folder_id": data.folder_id, "description": data.description,
    }
    meta: dict[str, Any] = {"index_content": data.index_content}
    if is_file:
        loc = _location(conn, data.location_id)  # type: ignore[arg-type]
        if not loc["enabled"]:
            raise AppError("resource_unavailable", "Location is disabled", 424)
        try:
            relative = safefs.validate_relative_path(data.relative_path)  # type: ignore[arg-type]
            info = inspect_file(deps, loc, relative)
        except Exception as exc:
            raise translate_error(exc) from None
        if repo.scalar(conn, "SELECT 1 FROM resources WHERE location_id = ? AND relative_path = ?",
                       (loc["id"], relative)):
            raise _duplicate("Resource already exists")
        values.update(
            resource_type=data.resource_type or info.resource_type, location_id=loc["id"], relative_path=relative,
            mime_type=info.mime_type, size_bytes=info.size, content_hash=info.content_hash,
            source_modified_at=info.source_modified_at,
        )
        meta.update(file_dev=info.dev, file_ino=info.ino)
    elif data.url is not None:
        if data.resource_type not in (None, "link"):
            raise _invalid("Links are always of type link")
        values.update(resource_type="link", url=str(data.url))
    else:
        if data.resource_type not in (None, *NOTE_TYPES):
            raise _invalid("Notes are of type note or study_note")
        values.update(resource_type=data.resource_type or "note", note_body=data.note_body)
    try:
        with write_tx(conn):
            now = utc_now()
            repo.insert_resource(conn, values, meta, now)
            repo.set_tags(conn, values["id"], data.tags, now, new_id)
            sync_document(conn, values, limits=deps.limits)
            deps.audit.record(conn, actor, action="storage.resource.create", result="success",
                              entity_type="resource", entity_id=values["id"],
                              params={"resource_type": values["resource_type"]})
    except sqlite3.IntegrityError:
        raise _duplicate("Resource already exists") from None
    if is_file and data.index_content:
        _index_file(conn, deps, _resource_row(conn, values["id"]))
    return repo.resource_out(conn, values["id"])


def update_resource(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, resource_id: str, data: ResourceUpdate) -> ResourceOut:
    given = data.model_fields_set
    reindex = False
    with write_tx(conn):
        r = _resource_row(conn, resource_id)
        if r["revision"] != data.expected_revision:
            raise _revision_mismatch()
        fields: dict[str, Any] = {}
        if data.title is not None:
            fields["title"] = data.title
        if "description" in given:
            fields["description"] = data.description
        if "folder_id" in given:
            if data.folder_id:
                _folder(conn, data.folder_id)
            fields["folder_id"] = data.folder_id
        if "note_body" in given:
            if r["resource_type"] not in NOTE_TYPES or r["location_id"] is not None or data.note_body is None:
                raise _invalid("note_body only applies to notes")
            fields["note_body"] = data.note_body
        meta = repo.metadata_of(r)
        if data.index_content is not None and data.index_content != bool(meta.get("index_content")):
            meta["index_content"] = data.index_content
            reindex = data.index_content and r["location_id"] is not None
        now = utc_now()
        repo.update_resource_fields(conn, resource_id, fields)
        repo.bump_entity(conn, resource_id, now, metadata=meta)
        if data.tags is not None:
            repo.set_tags(conn, resource_id, data.tags, now, new_id)
        sync_document(conn, r, limits=deps.limits)
        deps.audit.record(conn, actor, action="storage.resource.update", result="success",
                          entity_type="resource", entity_id=resource_id)
    if reindex:
        _index_file(conn, deps, _resource_row(conn, resource_id))
    return repo.resource_out(conn, resource_id)


def _set_archived(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, resource_id: str, archive: bool) -> ResourceOut:
    _resource_row(conn, resource_id)
    now = utc_now()
    with write_tx(conn):
        repo.bump_entity(conn, resource_id, now, archived_at=now if archive else None)
        deps.audit.record(conn, actor, action="storage.resource.archive" if archive else "storage.resource.unarchive",
                          result="success", entity_type="resource", entity_id=resource_id)
    return repo.resource_out(conn, resource_id)


def archive_resource(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, resource_id: str) -> ResourceOut:
    return _set_archived(conn, deps, actor, resource_id, True)


def unarchive_resource(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, resource_id: str) -> ResourceOut:
    return _set_archived(conn, deps, actor, resource_id, False)


def delete_resource(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, resource_id: str, confirmation_id: str | None,
    detach: bool = False,
) -> None:
    row = _resource_row(conn, resource_id)
    related = repo.count_relationships(conn, resource_id)
    if related and not detach:
        raise AppError("has_dependents", "Resource has relationships", 409)
    deps.gate.require(
        conn, actor, tool="delete_resource", args={"resource_id": resource_id, "detach": detach},
        summary=f"Vas a eliminar 1 recurso: «{row['title']}»"
        + (f" y {related} dependientes" if related else "")
        + ". Esta acción no se puede deshacer. El archivo original no se toca.",
        affected_count=1 + related, confirmation_id=confirmation_id,
        targets=[{"id": resource_id, "revision": row["revision"]}],
    )
    with write_tx(conn):
        if related:
            from app.services.relations import detach_entity  # import perezoso: otro frente

            detach_entity(conn, deps, actor, resource_id)
        conn.execute("DELETE FROM resources WHERE id = ?", (resource_id,))  # el trigger borra la entidad
        deps.audit.record(conn, actor, action="storage.resource.delete", result="success",
                          entity_type="resource", entity_id=resource_id, affected_count=1 + related)


# ---------------------------------------------------------------- lectura


def read_resource(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, resource_id: str, request: ReadRequest) -> ReadResult:
    r = _resource_row(conn, resource_id)  # 1. buscar
    loc = repo.get_location(conn, r["location_id"]) if r["location_id"] else None
    if loc is not None and not loc["enabled"]:  # 2. disponibilidad
        raise AppError("resource_unavailable", "Resource is not available", 424)
    if actor.is_agent and loc is not None and not loc["agent_read"]:  # 3. permisos
        raise _denied(conn, deps, actor, "storage.resource.read", "resource", resource_id)
    options = readers.ReadOptions(request.selector, request.offset, request.max_chars)
    try:  # 4. lector
        if r["location_id"] is None and r["url"] is not None:
            extracted = readers_link.read_link(r["url"], options, deps.limits)
        elif r["location_id"] is None:
            body = r["note_body"] or ""
            end = request.offset + request.max_chars
            extracted = readers.Extracted(
                text=body[request.offset : end], truncated=end < len(body),
                next_offset=end if end < len(body) else None,
                metadata={"resource_type": r["resource_type"], "total_chars": len(body)},
            )
        else:
            root, identity = location_root(loc)
            with safefs.open_file(root, identity, r["relative_path"], denied=deps.denied_roots,
                                  max_bytes=deps.limits.max_read_file_bytes) as opened:
                extracted = readers.read_file(opened.fd, r["resource_type"], r["mime_type"], options, deps.limits)
            if r["availability_status"] != "available":
                _set_availability(conn, resource_id, "available")
    except Exception as exc:
        err = translate_error(exc)
        if isinstance(exc, safefs.MissingFile):
            _set_availability(conn, resource_id, "missing")
        elif isinstance(exc, safefs.PathNotAllowed):
            _set_availability(conn, resource_id, "forbidden")
        deps.audit.record(conn, actor, action="storage.resource.read", result="failed", entity_type="resource",
                          entity_id=resource_id, error_code=err.code)
        raise err from None
    deps.audit.record(conn, actor, action="storage.resource.read", result="success", entity_type="resource",
                      entity_id=resource_id, params={"offset": request.offset, "max_chars": request.max_chars})
    return ReadResult(text=extracted.text, truncated=extracted.truncated, next_offset=extracted.next_offset,
                      metadata=dict(extracted.metadata), source=ReadSource(resource_id=resource_id, title=r["title"]))


def _set_availability(conn: sqlite3.Connection, resource_id: str, status: str) -> None:
    with write_tx(conn):
        repo.update_resource_fields(conn, resource_id, {"availability_status": status})
        repo.bump_entity(conn, resource_id, utc_now())
