"""Herramientas Hermes de relaciones. Solo aceptan UUID; el backend valida tipos y reglas."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, TypeVar

from drakter_contracts.tools import AuditPolicy
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError
from app.database.connection import connect
from app.schemas.relations import (
    Direction, EntityType, RelatedItems, RelationshipCreate, RelationshipOut, RelationshipPage,
    RelationshipSearch, RelationshipType, RelationshipUpdate,
)
from app.schemas.storage import Cursor, Uuid
from app.services import relations as svc
from app.services.storage_ports import Actor, tool_deps
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec

R = TypeVar("R")

# El resumen de una confirmación solo recibe los argumentos: la ruta de la base la fija el
# arranque con `configure_summary_source`. Sin ella, el resumen cita solo el identificador.
_summary_db: Path | None = None


def configure_summary_source(db_path: Path | None) -> None:
    global _summary_db
    _summary_db = db_path


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _run(ctx: ToolContext, fn: Callable[[sqlite3.Connection, Any, Actor], R]) -> R:
    conn = connect(ctx.state.settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return fn(conn, tool_deps(ctx.state), Actor("agent", "mcp", str(ctx.turn_id)))
    except AppError as exc:
        raise ToolError(exc.code, exc.message) from exc
    finally:
        conn.close()


class RelatedArgs(Strict):
    entity_id: Uuid
    direction: Direction = "both"
    relationship_type: RelationshipType | None = None


def _related(ctx: ToolContext, args: RelatedArgs) -> RelatedItems:
    return _run(ctx, lambda c, d, a: svc.get_related_items(
        c, d, a, args.entity_id, direction=args.direction, relationship_type=args.relationship_type))


class SearchArgs(Strict):
    source_id: Uuid | None = None
    target_id: Uuid | None = None
    entity_type: EntityType | None = None
    relationship_type: RelationshipType | None = None
    limit: Annotated[int, Field(ge=1, le=50)] = 20
    cursor: Cursor | None = None


def _search(ctx: ToolContext, args: SearchArgs) -> RelationshipPage:
    query = RelationshipSearch(**args.model_dump())
    return _run(ctx, lambda c, d, a: svc.search_relationships(c, d, a, query))


def _create(ctx: ToolContext, args: RelationshipCreate) -> RelationshipOut:
    return _run(ctx, lambda c, d, a: svc.create_relationship(c, d, a, args))


class UpdateArgs(RelationshipUpdate):
    relationship_id: Uuid


def _update(ctx: ToolContext, args: UpdateArgs) -> RelationshipOut:
    data = RelationshipUpdate(metadata=args.metadata)
    return _run(ctx, lambda c, d, a: svc.update_relationship(c, d, a, args.relationship_id, data))


class DeleteArgs(Strict):
    relationship_id: Uuid


class Deleted(BaseModel):
    deleted: bool
    relationship_id: str


def _delete(ctx: ToolContext, args: DeleteArgs) -> Deleted:
    _run(ctx, lambda c, d, a: svc.delete_relationship(c, d, a, args.relationship_id))
    return Deleted(deleted=True, relationship_id=args.relationship_id)


def _summarize_delete(args: BaseModel) -> str:
    rid = getattr(args, "relationship_id", "?")
    if _summary_db is not None:
        conn = connect(_summary_db)
        conn.row_factory = sqlite3.Row
        try:
            text = svc.describe(conn, rid)
        finally:
            conn.close()
        if text:
            return text
    return f"Delete relationship {rid}"


_LOG = {"entity_id": "log", "source_id": "log", "target_id": "log", "relationship_id": "log",
        "relationship_type": "log", "direction": "log", "entity_type": "log", "limit": "log",
        "cursor": "omit", "metadata": "hash"}


def _audit(args_model: type[BaseModel]) -> dict[str, AuditPolicy]:
    """The module-wide policy, restricted to this tool's arguments (the registry rejects unknown names)."""
    return {name: rule for name, rule in _LOG.items() if name in args_model.model_fields}

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_related_items",
        description="List the items related to an entity, in both directions, with their titles.",
        domain="relationships", args_model=RelatedArgs, result_model=RelatedItems,
        permission="relationships.read", risk=RiskClass.READ, handler=_related,
        errors=("not_found",), idempotent=True, returns_untrusted=True, audit=_audit(RelatedArgs),
    ),
    ToolSpec(
        name="search_relationships",
        description="Search stored relationships by source, target, entity type or relationship type.",
        domain="relationships", args_model=SearchArgs, result_model=RelationshipPage,
        permission="relationships.read", risk=RiskClass.READ, handler=_search,
        idempotent=True, audit=_audit(SearchArgs),
    ),
    ToolSpec(
        name="create_relationship",
        description="Relate two existing entities by id with a relationship type allowed for their kinds.",
        domain="relationships", args_model=RelationshipCreate, result_model=RelationshipOut,
        permission="relationships.write", risk=RiskClass.WRITE, handler=_create,
        errors=("not_found", "conflict", "relationship_not_allowed", "hierarchy_cycle"),
        audit=_audit(RelationshipCreate),
    ),
    ToolSpec(
        name="update_relationship",
        description="Replace the metadata of an existing relationship by id. The ends and type cannot change.",
        domain="relationships", args_model=UpdateArgs, result_model=RelationshipOut,
        permission="relationships.write", risk=RiskClass.WRITE, handler=_update,
        errors=("not_found", "validation_error"), audit=_audit(UpdateArgs),
    ),
    ToolSpec(
        name="delete_relationship",
        description="Delete a relationship between two entities. Needs user confirmation.",
        domain="relationships", args_model=DeleteArgs, result_model=Deleted,
        permission="relationships.delete", risk=RiskClass.CONFIRM, handler=_delete,
        errors=("not_found", "confirmation_unavailable"), audit=_audit(DeleteArgs), summarize=_summarize_delete,
    ),
)
