"""Append-only audit log. Fails closed: if it cannot write, the caller's transaction aborts."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final
from uuid import uuid4

from app.core.logging import redact
from app.permissions.canonical import canonical_json, format_instant, utc_now
from app.permissions.models import ACTOR_TYPES, AuditFieldPolicy, CallContext

MAX_LOGGED_VALUE: Final = 500
MAX_LISTED_EVENTS: Final = 200
_INSERT: Final = """
    INSERT INTO audit_events (
        id, actor_type, principal, action, entity_type, entity_id, result, params_json,
        params_hash, error_code, confirmation_id, correlation_id, turn_id, tainted, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def filter_params(
    params: Mapping[str, Any], policies: Mapping[str, AuditFieldPolicy]
) -> dict[str, Any]:
    """Keep only what the action allow-lists. Everything else is omitted."""
    kept: dict[str, Any] = {}
    for name, policy in policies.items():
        if name not in params:
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
class AuditEntry:
    action: str
    result: str
    entity_type: str | None = None
    entity_id: str | None = None
    params: dict[str, Any] | None = None
    params_hash: str | None = None
    error_code: str | None = None
    confirmation_id: str | None = None


def write_event(conn: sqlite3.Connection, ctx: CallContext, entry: AuditEntry) -> None:
    """Insert one event inside the caller's transaction, if any."""
    conn.execute(
        _INSERT,
        (
            str(uuid4()),
            ACTOR_TYPES[ctx.principal],
            ctx.principal.value,
            entry.action,
            entry.entity_type,
            entry.entity_id,
            entry.result,
            None if entry.params is None else canonical_json(entry.params),
            entry.params_hash,
            entry.error_code,
            entry.confirmation_id,
            ctx.correlation_id,
            ctx.turn_id,
            int(ctx.tainted),
            format_instant(utc_now()),
        ),
    )


def list_events(
    conn: sqlite3.Connection, *, limit: int = 50, confirmation_id: str | None = None
) -> list[dict[str, Any]]:
    """Newest first. The content is untrusted data: it can quote what the agent sent."""
    bounded = max(1, min(limit, MAX_LISTED_EVENTS))
    columns = (
        "id, actor_type, principal, action, entity_type, entity_id, result, params_json, "
        "params_hash, error_code, confirmation_id, correlation_id, turn_id, tainted, created_at"
    )
    if confirmation_id is None:
        cursor = conn.execute(
            f"SELECT {columns} FROM audit_events ORDER BY created_at DESC, id LIMIT ?",
            (bounded,),
        )
    else:
        cursor = conn.execute(
            f"SELECT {columns} FROM audit_events WHERE confirmation_id = ? "
            "ORDER BY created_at DESC, id LIMIT ?",
            (confirmation_id, bounded),
        )
    names = [description[0] for description in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
