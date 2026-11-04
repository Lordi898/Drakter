"""Índice FTS5 del almacén: documentos de metadatos, extracción por chunks, búsqueda y refresco."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from app.core.errors import AppError
from app.repositories import storage as repo
from app.schemas.storage import RefreshResult, ResourceOut, SearchHit, SearchPage
from app.services import readers
from app.services import storage_safefs as safefs
from app.services.readers import link as readers_link
from app.services.storage_ports import Actor, StorageDeps, StorageLimits, utc_now, write_tx

INDEXABLE_FILE_TYPES = frozenset({"text", "code", "pdf", "document"})
NOTE_TYPES = frozenset({"note", "study_note"})
_BATCH = 200


# ---------------------------------------------------------------- helpers compartidos


def translate_error(exc: BaseException) -> AppError:
    """Excepciones de SafeFS y lectores a `AppError` con mensaje fijo."""
    if isinstance(exc, AppError):
        return exc
    if isinstance(exc, safefs.PathNotAllowed):
        return AppError("path_not_allowed", "Path is not allowed", 403)
    if isinstance(exc, safefs.MissingFile):
        return AppError("resource_unavailable", "Resource is not available", 424)
    if isinstance(exc, (readers.TooLarge, safefs.FileTooLarge)):
        return AppError("file_too_large", "File is too large", 413)
    if isinstance(exc, readers.ArchiveLimit):
        return AppError("archive_limit_exceeded", "Archive limit exceeded", 413)
    if isinstance(exc, readers.UnsupportedFormat):
        return AppError("unsupported_media_type", "Unsupported format", 415)
    if isinstance(exc, readers_link.UrlNotAllowed):
        return AppError("url_not_allowed", "URL is not allowed", 403)
    if isinstance(exc, readers_link.LinkFetchFailed):
        return AppError("link_fetch_failed", "Could not fetch the link", 502)
    return AppError("read_failed", "Could not read the resource", 422)


def location_root(loc: sqlite3.Row) -> tuple[Any, Any]:
    from pathlib import Path

    identity = None
    if loc["root_dev"] is not None and loc["root_ino"] is not None:
        identity = safefs.RootIdentity(loc["root_dev"], loc["root_ino"])
    return Path(loc["path"]), identity


def iso_from_ns(mtime_ns: int) -> str:
    stamp = datetime.fromtimestamp(mtime_ns / 1e9, UTC)
    return stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def hash_fd(fd: int, size: int) -> str:
    digest, offset = hashlib.sha256(), 0
    while offset < size:
        block = os.pread(fd, 1024 * 1024, offset)
        if not block:
            break
        digest.update(block)
        offset += len(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class FileInfo:
    relative_path: str
    size: int
    mtime_ns: int
    dev: int
    ino: int
    resource_type: str
    mime_type: str | None
    content_hash: str | None

    @property
    def source_modified_at(self) -> str:
        return iso_from_ns(self.mtime_ns)


def inspect_file(deps: StorageDeps, loc: sqlite3.Row, relative: str) -> FileInfo:
    """Abre por SafeFS, mide, detecta tipo y calcula SHA-256 si cabe. Lanza excepciones de SafeFS."""
    root, identity = location_root(loc)
    with safefs.open_file(root, identity, relative, denied=deps.denied_roots) as opened:
        head = os.pread(opened.fd, 8192, 0)
        rtype, mime = readers.detect_type(PurePosixPath(relative).name, head)
        digest = hash_fd(opened.fd, opened.size) if opened.size <= deps.limits.max_hash_bytes else None
        return FileInfo(relative, opened.size, opened.mtime_ns, opened.dev, opened.ino, rtype, mime, digest)


def chunks_of(text: str, limits: StorageLimits) -> list[str]:
    text = text[: limits.max_index_chars]
    size = limits.index_chunk_chars
    return [text[i : i + size] for i in range(0, len(text), size)]


def _get_row(conn: sqlite3.Connection, resource_id: str) -> sqlite3.Row:
    found = repo.get_resource_row(conn, resource_id)
    if found is None:
        raise AppError("not_found", "Resource not found", 404)
    return found


def _deny(conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, action: str, rid: str | None) -> AppError:
    deps.audit.record(conn, actor, action=action, result="denied", entity_type="resource", entity_id=rid,
                      error_code="permission_denied")
    return AppError("permission_denied", "Not allowed", 403)


# ---------------------------------------------------------------- documento de metadatos


def sync_document(conn: sqlite3.Connection, resource_row: Any, *, limits: StorageLimits | None = None) -> None:
    """Chunk 0 con metadatos; notas con `index_content` en chunks 1..n. Misma transacción del llamador."""
    limits = limits or StorageLimits()
    rid = resource_row["id"]
    r = _get_row(conn, rid)
    tags = repo.tags_for(conn, [rid])[rid]
    index_content = bool(repo.metadata_of(r).get("index_content"))
    parts = [r["resource_type"], r["relative_path"], r["mime_type"], r["description"], r["url"]]
    repo.upsert_chunk(conn, rid, 0, r["title"], "\n".join(p for p in parts if p), " ".join(tags))
    is_note = r["resource_type"] in NOTE_TYPES and r["location_id"] is None
    if not index_content:
        repo.delete_chunks_from(conn, rid, 1)
        if r["index_status"] != "none":
            repo.set_index_state(conn, rid, "none", None, None)
    elif is_note:
        repo.delete_chunks_from(conn, rid, 1)
        for n, piece in enumerate(chunks_of(r["note_body"] or "", limits), 1):
            repo.upsert_chunk(conn, rid, n, "", piece, "")
        repo.set_index_state(conn, rid, "indexed", utc_now(), None)
    elif r["location_id"] is None:
        repo.delete_chunks_from(conn, rid, 1)
        repo.set_index_state(conn, rid, "skipped", None, None)
    elif r["index_status"] in ("none", "skipped"):
        repo.set_index_state(conn, rid, "pending", None, None)


def _mark_unavailable(conn: sqlite3.Connection, rid: str, status: str) -> None:
    with write_tx(conn):
        repo.update_resource_fields(conn, rid, {"availability_status": status})
        repo.bump_entity(conn, rid, utc_now())


def _index_file(conn: sqlite3.Connection, deps: StorageDeps, r: sqlite3.Row) -> None:
    """Extrae fuera de la transacción y escribe después. Un fallo del lector queda en `failed`."""
    rid, loc = r["id"], repo.get_location(conn, r["location_id"])
    text, error, availability = "", None, None
    if r["resource_type"] not in INDEXABLE_FILE_TYPES:
        status = "skipped"
    elif loc is None or not loc["enabled"]:
        status, error = "failed", "resource_unavailable"
    else:
        status = "indexed"
        try:
            root, identity = location_root(loc)
            with safefs.open_file(root, identity, r["relative_path"], denied=deps.denied_roots,
                                  max_bytes=deps.limits.max_read_file_bytes) as opened:
                text = readers.extract_for_index(opened.fd, r["resource_type"], r["mime_type"], deps.limits)
        except Exception as exc:  # el lector nunca rompe la operación
            status, error = "failed", translate_error(exc).code
            if isinstance(exc, safefs.MissingFile):
                availability = "missing"
            elif isinstance(exc, safefs.PathNotAllowed):
                availability = "forbidden"
    now = utc_now()
    with write_tx(conn):
        repo.delete_chunks_from(conn, rid, 1)
        if status == "indexed":
            for n, piece in enumerate(chunks_of(text, deps.limits), 1):
                repo.upsert_chunk(conn, rid, n, "", piece, "")
        repo.set_index_state(conn, rid, status, now if status == "indexed" else None, error)
        if availability:
            repo.update_resource_fields(conn, rid, {"availability_status": availability})
        repo.bump_entity(conn, rid, now)


def index_resource(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, resource_id: str, include_content: bool | None = None
) -> ResourceOut:
    r = _get_row(conn, resource_id)
    loc = repo.get_location(conn, r["location_id"]) if r["location_id"] else None
    if actor.is_agent and loc is not None and not loc["agent_read"]:
        raise _deny(conn, deps, actor, "storage.resource.index", resource_id)
    meta = repo.metadata_of(r)
    if include_content is not None and include_content != bool(meta.get("index_content")):
        meta["index_content"] = include_content
        with write_tx(conn):
            repo.bump_entity(conn, resource_id, utc_now(), metadata=meta)
            sync_document(conn, r, limits=deps.limits)
        r = _get_row(conn, resource_id)
    if meta.get("index_content") and r["location_id"] is not None:
        _index_file(conn, deps, r)
    out = repo.resource_out(conn, resource_id)
    deps.audit.record(conn, actor, action="storage.resource.index", result="success", entity_type="resource",
                      entity_id=resource_id, params={"index_status": out.index_status})
    return out


# ---------------------------------------------------------------- búsqueda


def search_resources(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, *, q: str, types: list[str] | None = None,
    limit: int = 20, cursor: str | None = None,
) -> SearchPage:
    limit, offset = repo.clamp_limit(limit, 20), repo.decode_cursor(cursor)
    match = repo.fts_match(q)
    if match is None:
        return SearchPage(items=[], next_cursor=None)
    found = repo.search_rows(conn, match, types or None, actor.is_agent, limit + 1, offset)
    page = found[:limit]
    by_id = {r["id"]: r for r in repo.rows(
        conn, repo.RESOURCE_SELECT + f" WHERE r.id IN ({','.join('?' * len(page))})", [p["id"] for p in page]
    )} if page else {}
    ordered = [by_id[p["id"]] for p in page if p["id"] in by_id]
    summaries = dict(zip((r["id"] for r in ordered), repo.summaries(conn, ordered), strict=True))
    items = [SearchHit(resource=summaries[p["id"]], snippet=p["snip"] or "") for p in page if p["id"] in summaries]
    return SearchPage(items=items, next_cursor=repo.encode_cursor(offset + limit) if len(found) > limit else None)


# ---------------------------------------------------------------- refresco


def refresh_index(
    conn: sqlite3.Connection, deps: StorageDeps, actor: Actor, confirmation_id: str | None
) -> RefreshResult:
    targets = repo.list_resource_rows(conn, files_only=True, limit=10**9)
    if actor.is_agent:
        deps.gate.require(
            conn, actor, tool="refresh_resource_index", args={},
            summary=f"Comprobar {len(targets)} archivos del almacén y reindexar los modificados",
            affected_count=len(targets), confirmation_id=confirmation_id,
        )
    locs = {l["id"]: l for l in repo.list_locations(conn)}
    counts = dict(checked=0, available=0, missing=0, moved=0, forbidden=0, reindexed=0, failed=0)
    pending: list[tuple[str, dict[str, Any]]] = []
    reindex: list[sqlite3.Row] = []

    def flush() -> None:
        if not pending:
            return
        now = utc_now()
        with write_tx(conn):
            for rid, fields in pending:
                repo.update_resource_fields(conn, rid, fields)
                repo.bump_entity(conn, rid, now)
        pending.clear()

    for r in targets:
        loc = locs.get(r["location_id"])
        if loc is None or not loc["enabled"]:
            continue
        counts["checked"] += 1
        root, identity = location_root(loc)
        status, fields = "available", {}
        try:
            entry = safefs.stat_file(root, identity, r["relative_path"], denied=deps.denied_roots)
            changed = entry.size != r["size_bytes"] or iso_from_ns(entry.mtime_ns) != r["source_modified_at"]
            if changed:
                info = inspect_file(deps, loc, r["relative_path"])
                fields = {"size_bytes": info.size, "source_modified_at": info.source_modified_at,
                          "content_hash": info.content_hash}
                if repo.metadata_of(r).get("index_content"):
                    reindex.append(r)
        except safefs.MissingFile:
            status = "missing"
        except safefs.PathNotAllowed:
            status = "forbidden"
        except Exception:
            counts["failed"] += 1
            status = "unreachable"
        if status != "unreachable":
            counts["available" if status == "available" else status] += 1
        if status != r["availability_status"] or fields:
            pending.append((r["id"], {"availability_status": status, **fields}))
        if len(pending) >= _BATCH:
            flush()
    flush()
    for r in reindex:
        _index_file(conn, deps, repo.get_resource_row(conn, r["id"]))
        after = repo.get_resource_row(conn, r["id"])
        counts["reindexed" if after["index_status"] == "indexed" else "failed"] += 1
    deps.audit.record(conn, actor, action="storage.index.refresh", result="success", affected_count=counts["checked"],
                      params=counts)
    return RefreshResult(**counts)
