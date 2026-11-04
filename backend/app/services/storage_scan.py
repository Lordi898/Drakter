"""Escaneo manual de una ubicación: altas, cambios, movidos y ausentes."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.core.errors import AppError
from app.repositories import storage as repo
from app.schemas.storage import ScanResult
from app.services import storage_safefs as safefs
from app.services.storage_index import (
    FileInfo, inspect_file, iso_from_ns, location_root, sync_document, translate_error,
)
from app.services.storage_ports import Actor, StorageDeps, new_id, utc_now, write_tx

_BATCH = 200


def scan_location(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, location_id: str
) -> ScanResult:
    if actor.kind != "user":
        deps.audit.record(conn, actor, action="storage.location.scan", result="denied",
                          entity_type="storage_location", entity_id=location_id, error_code="permission_denied")
        raise AppError("permission_denied", "Not allowed", 403)
    loc = repo.get_location(conn, location_id)
    if loc is None:
        raise AppError("not_found", "Location not found", 404)
    if not loc["enabled"]:
        raise AppError("resource_unavailable", "Location is disabled", 424)

    known = repo.count_location_resources(conn, location_id)
    deps.gate.require(
        conn, actor, tool="scan_location", args={"location_id": location_id},
        summary=f"Vas a escanear la ubicación «{loc['label']}», que tiene {known} recursos catalogados. "
                "Los archivos no se modifican.",
        affected_count=known, targets=[{"id": location_id}],
    )

    # 1. E/S fuera de transacción: recorrido y lectura de los archivos nuevos o cambiados.
    root, identity = location_root(loc)
    limits = deps.limits
    try:
        entries = list(safefs.scan(root, identity, denied=deps.denied_roots,
                                   max_entries=limits.scan_max_entries, max_depth=limits.scan_max_depth))
    except Exception as exc:
        raise translate_error(exc) from None
    truncated = len(entries) >= limits.scan_max_entries
    existing = {r["relative_path"]: r for r in repo.list_resource_rows(conn, location_id=location_id, include_archived=True, limit=10**9)}
    by_inode = {}
    for r in existing.values():
        meta = repo.metadata_of(r)
        if meta.get("file_dev") is not None:
            by_inode[(meta["file_dev"], meta["file_ino"])] = r
    seen_paths = {e.relative_path for e in entries}

    counts = dict(added=0, updated=0, missing=0, moved=0, skipped=0)
    adds: list[FileInfo] = []
    changes: list[tuple[sqlite3.Row, FileInfo | None]] = []  # None = solo disponibilidad
    moves: list[tuple[sqlite3.Row, str, Any]] = []
    for e in entries:
        if e.nlink != 1:
            counts["skipped"] += 1
            continue
        known = existing.get(e.relative_path)
        if known is not None:
            changed = e.size != known["size_bytes"] or iso_from_ns(e.mtime_ns) != known["source_modified_at"]
            meta = repo.metadata_of(known)
            replaced = (meta.get("file_dev"), meta.get("file_ino")) != (e.dev, e.ino)
            if changed or replaced:
                info = _inspect(deps, loc, e.relative_path, counts)
                if info is not None:
                    changes.append((known, info))
            elif known["availability_status"] != "available":
                changes.append((known, None))
            continue
        source = by_inode.get((e.dev, e.ino))
        if source is not None and source["relative_path"] not in seen_paths:
            moves.append((source, e.relative_path, e))
            continue
        info = _inspect(deps, loc, e.relative_path, counts)
        if info is not None:
            adds.append(info)
    moved_ids = {m[0]["id"] for m in moves}
    # `scan` calla lo que salta (EACCES, profundidad): no verlo no prueba que falte.
    gone = [] if truncated else [
        r for p, r in existing.items()
        if p not in seen_paths and r["id"] not in moved_ids and r["availability_status"] != "missing"
        and _really_missing(deps, root, identity, p)
    ]

    # 2. Escritura en lotes, cada uno en su transacción corta.
    def batches(items: list[Any]) -> Any:
        for i in range(0, len(items), _BATCH):
            yield items[i : i + _BATCH]

    for batch in batches(adds):
        with write_tx(conn):
            now = utc_now()
            for info in batch:
                values = {
                    "id": new_id(), "title": info.relative_path.rsplit("/", 1)[-1],
                    "resource_type": info.resource_type, "location_id": location_id,
                    "relative_path": info.relative_path, "mime_type": info.mime_type, "size_bytes": info.size,
                    "content_hash": info.content_hash, "source_modified_at": info.source_modified_at,
                }
                repo.insert_resource(conn, values, {"index_content": False, "file_dev": info.dev,
                                                    "file_ino": info.ino}, now)
                sync_document(conn, values, limits=limits)
        counts["added"] += len(batch)
    for batch in batches(changes):
        with write_tx(conn):
            now = utc_now()
            for known, info in batch:
                fields: dict[str, Any] = {"availability_status": "available"}
                meta = repo.metadata_of(known)
                if info is not None:
                    fields.update(size_bytes=info.size, source_modified_at=info.source_modified_at,
                                  content_hash=info.content_hash, mime_type=info.mime_type)
                    meta.update(file_dev=info.dev, file_ino=info.ino)
                    if meta.get("index_content"):
                        fields["index_status"] = "pending"
                repo.update_resource_fields(conn, known["id"], fields)
                repo.bump_entity(conn, known["id"], now, metadata=meta)
        counts["updated"] += len(batch)
    for batch in batches(moves):
        with write_tx(conn):
            now = utc_now()
            for source, new_path, e in batch:
                repo.update_resource_fields(conn, source["id"], {"relative_path": new_path,
                                                                 "availability_status": "available"})
                repo.bump_entity(conn, source["id"], now)
                sync_document(conn, source, limits=limits)
        counts["moved"] += len(batch)
    for batch in batches(gone):
        with write_tx(conn):
            now = utc_now()
            for r in batch:
                repo.update_resource_fields(conn, r["id"], {"availability_status": "missing"})
                repo.bump_entity(conn, r["id"], now)
        counts["missing"] += len(batch)

    result = ScanResult(location_id=location_id, seen=len(entries), truncated=truncated, **counts)
    deps.audit.record(conn, actor, action="storage.location.scan", result="success", entity_type="storage_location",
                      entity_id=location_id, affected_count=sum(counts.values()) - counts["skipped"],
                      params={**counts, "truncated": truncated})
    return result


def _really_missing(deps: StorageDeps, root: Any, identity: Any, relative: str) -> bool:
    try:
        safefs.stat_file(root, identity, relative, denied=deps.denied_roots)
    except safefs.MissingFile:
        return True
    except Exception:
        return False
    return False


def _inspect(deps: StorageDeps, loc: sqlite3.Row, relative: str, counts: dict[str, int]) -> FileInfo | None:
    try:
        return inspect_file(deps, loc, relative)
    except Exception:  # archivo ilegible, desaparecido o denegado entre el recorrido y la lectura
        counts["skipped"] += 1
        return None
