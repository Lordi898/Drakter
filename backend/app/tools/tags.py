"""Herramientas Hermes de etiquetas. Solo aceptan UUID; el backend valida la entidad."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Annotated, Any, TypeVar

from drakter_contracts.tools import AuditPolicy
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError
from app.database.connection import connect
from app.schemas.storage import Cursor, TagName, Uuid
from app.services import relations_tags as svc
from app.services.storage_ports import Actor, tool_deps
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec

R = TypeVar("R")


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


class ListTagsArgs(Strict):
    q: Annotated[str, Field(max_length=60)] | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    cursor: Cursor | None = None


class TagAssignmentArgs(Strict):
    entity_id: Uuid
    tag: TagName


class TagAssignmentResult(BaseModel):
    entity_id: str
    tags: list[str]


def _list(ctx: ToolContext, args: ListTagsArgs) -> svc.TagPage:
    return _run(ctx, lambda c, d, a: svc.list_tags(c, q=args.q, limit=args.limit, cursor=args.cursor))


def _change(ctx: ToolContext, args: TagAssignmentArgs, add: bool) -> TagAssignmentResult:
    page = _run(ctx, lambda c, d, a: svc.change_entity_tag(c, d, a, args.entity_id, args.tag, add=add))
    return TagAssignmentResult(entity_id=args.entity_id, tags=[t.name for t in page.items])


def _add(ctx: ToolContext, args: TagAssignmentArgs) -> TagAssignmentResult:
    return _change(ctx, args, True)


def _remove(ctx: ToolContext, args: TagAssignmentArgs) -> TagAssignmentResult:
    return _change(ctx, args, False)


_LOG = {"entity_id": "log", "tag": "hash", "q": "hash", "limit": "log", "cursor": "omit"}


def _audit(args_model: type[BaseModel]) -> dict[str, AuditPolicy]:
    """The module-wide policy, restricted to this tool's arguments (the registry rejects unknown names)."""
    return {name: rule for name, rule in _LOG.items() if name in args_model.model_fields}

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="list_tags", description="List the existing tags with their usage count.",
        domain="tags", args_model=ListTagsArgs, result_model=svc.TagPage,
        permission="tags.read", risk=RiskClass.READ, handler=_list,
        errors=("validation_error", "invalid_cursor"), idempotent=True, audit=_audit(ListTagsArgs),
    ),
    ToolSpec(
        name="add_tag",
        description="Attach a tag (created if missing) to a task, project, habit, event, subject or resource.",
        domain="tags", args_model=TagAssignmentArgs, result_model=TagAssignmentResult,
        permission="tags.write", risk=RiskClass.WRITE, handler=_add,
        errors=("not_found", "validation_error", "conflict"), idempotent=True, audit=_audit(TagAssignmentArgs),
    ),
    ToolSpec(
        name="remove_tag", description="Remove a tag from an item. Neither the tag nor the item is deleted.",
        domain="tags", args_model=TagAssignmentArgs, result_model=TagAssignmentResult,
        permission="tags.write", risk=RiskClass.WRITE, handler=_remove,
        errors=("not_found", "validation_error"), idempotent=True, audit=_audit(TagAssignmentArgs),
    ),
)
