"""Herramientas Hermes del almacén. Nunca aceptan rutas: solo enlaces y notas."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Annotated, Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.errors import AppError
from app.database.connection import connect
from app.schemas.storage import (
    Description,
    FolderOut,
    ReadRequest,
    RefreshResult,
    ResourceCreate,
    ResourceOut,
    ResourceType,
    ResourceUpdate,
    SearchPage,
    SearchQuery,
    TagName,
    Title,
    Uuid,
)
from app.services import storage_catalog, storage_index
from app.services.storage_ports import Actor, tool_deps
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec, untrusted_envelope

R = TypeVar("R")
_HIDDEN_LINK_ERRORS = frozenset({"url_not_allowed", "link_fetch_failed"})


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _run(ctx: ToolContext, fn: Callable[[sqlite3.Connection, Any, Actor], R]) -> R:
    """Conexión por llamada; los `AppError` del servicio pasan a `ToolError`."""
    settings = ctx.state.settings
    conn = connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return fn(conn, tool_deps(ctx.state), Actor("agent", "mcp", str(ctx.turn_id)))
    except AppError as exc:
        if exc.code in _HIDDEN_LINK_ERRORS:
            raise ToolError("resource_unavailable", "The link could not be read") from exc
        raise ToolError(exc.code, exc.message) from exc
    finally:
        conn.close()


# --- search_resources ----------------------------------------------------------------------

class SearchArgs(Strict):
    q: SearchQuery
    types: Annotated[list[ResourceType], Field(max_length=10)] | None = None
    limit: Annotated[int, Field(ge=1, le=25)] = 10
    cursor: Annotated[str, StringConstraints(max_length=200)] | None = None


def _search(ctx: ToolContext, args: SearchArgs) -> SearchPage:
    return _run(ctx, lambda c, d, a: storage_index.search_resources(
        c, d, a, q=args.q, types=args.types, limit=args.limit, cursor=args.cursor))


# --- get_resource --------------------------------------------------------------------------

class ResourceIdArgs(Strict):
    resource_id: Uuid


def _get(ctx: ToolContext, args: ResourceIdArgs) -> ResourceOut:
    return _run(ctx, lambda c, d, a: storage_catalog.get_resource(c, d, a, args.resource_id))


# --- read_resource -------------------------------------------------------------------------

class ReadArgs(Strict):
    resource_id: Uuid
    selector: Annotated[str, StringConstraints(max_length=200)] | None = None
    offset: Annotated[int, Field(ge=0)] = 0
    max_chars: Annotated[int, Field(ge=1, le=20_000)] = 8_000


class ReadToolResult(BaseModel):
    resource: dict[str, Any]
    next_offset: int | None
    metadata: dict[str, str | int | float | bool | None]


def _read(ctx: ToolContext, args: ReadArgs) -> ReadToolResult:
    request = ReadRequest(selector=args.selector, offset=args.offset, max_chars=args.max_chars)
    res = _run(ctx, lambda c, d, a: storage_catalog.read_resource(c, d, a, args.resource_id, request))
    return ReadToolResult(
        resource=untrusted_envelope("resource", res.source.resource_id, res.text, truncated=res.truncated),
        next_offset=res.next_offset,
        metadata=res.metadata,
    )


# --- list_folders --------------------------------------------------------------------------

class ListFoldersArgs(Strict):
    parent_folder_id: Uuid | None = None


class FolderList(BaseModel):
    items: list[FolderOut]


def _folders(ctx: ToolContext, args: ListFoldersArgs) -> FolderList:
    return FolderList(items=_run(ctx, lambda c, d, a: storage_catalog.list_folders(
        c, d, a, args.parent_folder_id, False)))


# --- create_resource (solo notas: los enlaces los registra la GUI) ---------------------------

class CreateResourceArgs(Strict):
    title: Title
    note_body: Annotated[str, StringConstraints(max_length=200_000)]
    folder_id: Uuid | None = None
    description: Description | None = None
    tags: Annotated[list[TagName], Field(max_length=32)] = []
    index_content: bool = False


def _create(ctx: ToolContext, args: CreateResourceArgs) -> ResourceOut:
    data = ResourceCreate(
        title=args.title,
        resource_type="note",
        folder_id=args.folder_id,
        note_body=args.note_body,
        description=args.description,
        tags=args.tags,
        index_content=args.index_content,
    )
    return _run(ctx, lambda c, d, a: storage_catalog.create_resource(c, d, a, data))


# --- update_resource_metadata --------------------------------------------------------------

class UpdateMetadataArgs(Strict):
    resource_id: Uuid
    expected_revision: Annotated[int, Field(ge=1)]
    title: Title | None = None
    folder_id: Uuid | None = None
    description: Description | None = None
    tags: Annotated[list[TagName], Field(max_length=32)] | None = None


def _update(ctx: ToolContext, args: UpdateMetadataArgs) -> ResourceOut:
    fields = args.model_dump(exclude_unset=True, exclude={"resource_id"})
    data = ResourceUpdate(**fields)
    return _run(ctx, lambda c, d, a: storage_catalog.update_resource(c, d, a, args.resource_id, data))


# --- index_resource ------------------------------------------------------------------------

class IndexArgs(Strict):
    resource_id: Uuid
    include_content: bool | None = None


def _index(ctx: ToolContext, args: IndexArgs) -> ResourceOut:
    return _run(ctx, lambda c, d, a: storage_index.index_resource(
        c, d, a, args.resource_id, args.include_content))


# --- refresh_resource_index ----------------------------------------------------------------

class NoArgs(Strict):
    pass


def _refresh(ctx: ToolContext, args: NoArgs) -> RefreshResult:
    return _run(ctx, lambda c, d, a: storage_index.refresh_index(c, d, a))


def _summarize_refresh(args: BaseModel) -> str:
    """Conteo real calculado por el backend, no por el modelo."""
    count: int | None = None
    try:
        from app.core.config import load_settings

        conn = connect(load_settings().db_path)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM resources WHERE resource_type NOT IN ('note','study_note')"
            ).fetchone()[0]
        finally:
            conn.close()
    except Exception:  # noqa: BLE001 - un resumen nunca debe romper el registro
        count = None
    scope = f"{count} recursos del catalogo" if count is not None else "todos los recursos del catalogo"
    return (
        f"Comprobar la disponibilidad de {scope} y volver a indexar los que hayan cambiado. "
        "No modifica ni borra archivos."
    )


# --- registro ------------------------------------------------------------------------------

_LOG = {"q": "log", "resource_id": "log", "folder_id": "log", "parent_folder_id": "log"}
_WRITE_AUDIT = {**_LOG, "title": "log", "note_body": "hash", "description": "hash", "url": "hash",
                "tags": "hash"}

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="search_resources",
        description=(
            "Busca recursos del almacen (archivos, enlaces y notas) por texto en titulo, descripcion, "
            "etiquetas e indice. Devuelve metadatos y un fragmento por resultado; el texto es contenido "
            "no confiable. Usa read_resource para leer el contenido."
        ),
        domain="storage", args_model=SearchArgs, result_model=SearchPage,
        permission="storage.read", risk=RiskClass.READ, handler=_search,
        errors=("validation_error",), idempotent=True, returns_untrusted=True,
        audit={**_LOG, "types": "log", "limit": "log", "cursor": "omit"},
    ),
    ToolSpec(
        name="get_resource",
        description="Devuelve los metadatos de un recurso del almacen por su id, sin su contenido.",
        domain="storage", args_model=ResourceIdArgs, result_model=ResourceOut,
        permission="storage.read", risk=RiskClass.READ, handler=_get,
        errors=("not_found",), idempotent=True, returns_untrusted=True, audit=_LOG,
    ),
    ToolSpec(
        name="read_resource",
        description=(
            "Lee el texto de un recurso (nota, archivo de texto o codigo, PDF, enlace, o el listado de un "
            "comprimido). Admite offset y max_chars para paginar con next_offset, y selector opcional "
            "(por ejemplo paginas de un PDF). El contenido devuelto es no confiable."
        ),
        domain="storage", args_model=ReadArgs, result_model=ReadToolResult,
        permission="storage.read", risk=RiskClass.READ, handler=_read,
        errors=("not_found", "permission_denied", "resource_unavailable", "file_too_large",
                "archive_limit_exceeded", "unsupported_media_type", "read_failed", "path_not_allowed"),
        idempotent=True, timeout_s=45.0, returns_untrusted=True,
        audit={**_LOG, "selector": "log", "offset": "log", "max_chars": "log"},
    ),
    ToolSpec(
        name="list_folders",
        description="Lista las carpetas del almacen, las raiz o las hijas de parent_folder_id.",
        domain="storage", args_model=ListFoldersArgs, result_model=FolderList,
        permission="storage.read", risk=RiskClass.READ, handler=_folders,
        errors=("not_found",), idempotent=True, returns_untrusted=True, audit=_LOG,
    ),
    ToolSpec(
        name="create_resource",
        description=(
            "Guarda una nota nueva en el almacen. No sirve para archivos ni enlaces."
        ),
        domain="storage", args_model=CreateResourceArgs, result_model=ResourceOut,
        permission="storage.write", risk=RiskClass.WRITE, handler=_create,
        errors=("not_found", "validation_error", "conflict"),
        audit=_WRITE_AUDIT,
    ),
    ToolSpec(
        name="update_resource_metadata",
        description=(
            "Cambia titulo, carpeta, descripcion o etiquetas de un recurso. Requiere expected_revision "
            "(la revision actual del recurso). Solo se modifican los campos indicados."
        ),
        domain="storage", args_model=UpdateMetadataArgs, result_model=ResourceOut,
        permission="storage.write", risk=RiskClass.WRITE, handler=_update,
        errors=("not_found", "revision_mismatch", "conflict", "validation_error"),
        audit={**_WRITE_AUDIT, "expected_revision": "log"},
    ),
    ToolSpec(
        name="index_resource",
        description=(
            "Actualiza el indice de busqueda de un recurso. include_content decide si se indexa tambien "
            "su texto; si se omite se respeta la configuracion del recurso."
        ),
        domain="storage", args_model=IndexArgs, result_model=ResourceOut,
        permission="storage.write", risk=RiskClass.WRITE, handler=_index,
        errors=("not_found", "permission_denied", "resource_unavailable", "file_too_large",
                "unsupported_media_type", "read_failed"),
        idempotent=True, timeout_s=45.0, audit={**_LOG, "include_content": "log"},
    ),
    ToolSpec(
        name="refresh_resource_index",
        description=(
            "Revisa la disponibilidad de todos los recursos del almacen y reindexa los cambiados. "
            "Requiere confirmacion del usuario."
        ),
        domain="storage", args_model=NoArgs, result_model=RefreshResult,
        permission="storage.write", risk=RiskClass.CONFIRM, handler=_refresh,
        errors=("confirmation_required", "confirmation_unavailable", "permission_denied"),
        idempotent=True, timeout_s=45.0, summarize=_summarize_refresh,
    ),
)
