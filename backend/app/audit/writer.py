"""Append-only audit log. `write` fails closed: an error aborts the caller's transaction."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final
from uuid import uuid4

from drakter_contracts.common import format_instant
from drakter_contracts.tools import AuditPolicy

from app.core.logging import redact
from app.permissions.canonical import canonical_json, utc_now
from app.permissions.models import ACTOR_TYPES, ActorContext

MAX_LOGGED_VALUE: Final = 500
MAX_LISTED_EVENTS: Final = 200
_COLUMNS: Final = (
    "id, occurred_at, correlation_id, actor_type, origin, action, tool_name, entity_type, "
    "entity_id, affected_count, params_redacted_json, changes_json, result, error_code, "
    "confirmation_id, duration_ms"
)
_INSERT: Final = (
    f"INSERT INTO audit_events ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def filter_params(
    params: Mapping[str, Any], policies: Mapping[str, AuditPolicy]
) -> dict[str, Any]:
    """Keep only what the action allow-lists. Everything else is omitted."""
    kept: dict[str, Any] = {}
    for name, policy in policies.items():
        if policy == "omit" or name not in params:
            continue
        value = params[name]
        if policy == "hash":
            digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
            kept[name] = f"sha256:{digest}"
            continue
        cleaned = redact(value)
        if isinstance(cleaned, str):
            cleaned = cleaned[:MAX_LOGGED_VALUE]
        elif len(canonical_json(cleaned)) > MAX_LOGGED_VALUE:
            cleaned = "[TRUNCATED]"
        kept[name] = cleaned
    return kept


@dataclass(frozen=True)
class AuditEvent:
    """`result` is one of success, denied, failed or confirmation_required.

    `args_hash`, `turn_id` and `tainted` travel in `changes_json` until `audit_events`
    has its own columns for them.
    """

    action: str
    result: str
    tool_name: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    affected_count: int | None = None
    params: Mapping[str, Any] | None = None
    args_hash: str | None = None
    error_code: str | None = None
    confirmation_id: str | None = None
    duration_ms: int | None = None


def write(conn: sqlite3.Connection, ctx: ActorContext, event: AuditEvent) -> None:
    """Insert one event, inside the caller's transaction if there is one."""
    binding = {"args_hash": event.args_hash, "turn_id": ctx.turn_id, "tainted": ctx.tainted}
    conn.execute(
        _INSERT,
        (
            str(uuid4()),
            format_instant(utc_now()),
            ctx.correlation_id,
            ACTOR_TYPES[ctx.principal].value,
            ctx.origin.value,
            event.action,
            event.tool_name,
            event.entity_type,
            event.entity_id,
            event.affected_count,
            None if event.params is None else canonical_json(event.params),
            canonical_json(binding),
            event.result,
            event.error_code,
            event.confirmation_id,
            event.duration_ms,
        ),
    )


def list_events(
    conn: sqlite3.Connection, *, limit: int = 50, confirmation_id: str | None = None
) -> list[dict[str, Any]]:
    """Newest first. Content is untrusted data: it can quote what the agent sent."""
    bounded = max(1, min(limit, MAX_LISTED_EVENTS))
    query = f"SELECT seq, {_COLUMNS} FROM audit_events"
    arguments: tuple[Any, ...] = (bounded,)
    if confirmation_id is not None:
        query += " WHERE confirmation_id = ?"
        arguments = (confirmation_id, bounded)
    cursor = conn.execute(f"{query} ORDER BY seq DESC LIMIT ?", arguments)
    names = [description[0] for description in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
