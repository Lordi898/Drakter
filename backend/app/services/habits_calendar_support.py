"""Interfaz fina con la infraestructura común que aún no existe.

Hábitos, calendario y asignaturas solo tocan lo común a través de este archivo.
Cuando `contracts/` fije entidades, auditoría y confirmaciones, se adapta aquí y
el resto no cambia. Usa las tablas `entities`, `audit_events` y
`pending_confirmations` de schema_v1.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Request
from pydantic import BaseModel

from app.core.errors import AppError
from app.database.connection import connect

ActorType = Literal["user", "agent", "automation", "system"]
Origin = Literal["rest", "mcp", "scheduler", "internal"]
AuditResult = Literal["success", "denied", "failed", "confirmation_required"]

CONFIRMATION_TTL: Final = timedelta(minutes=15)
MAX_LIMIT: Final = 200


@dataclass(frozen=True)
class RequestContext:
    actor_type: ActorType
    origin: Origin
    correlation_id: str
    tool_name: str | None = None
    turn_id: str | None = None


class ConfirmationRef(BaseModel):
    """Lo destructivo no se ejecuta: devuelve esto (HTTP 202 o `confirmation_required`)."""

    status: Literal["confirmation_required"] = "confirmation_required"
    confirmation_id: str
    summary: str
    expires_at: str
    affected_count: int | None = None


def now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def new_id() -> str:
    return str(uuid4())


def ensure_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError, OSError):
        raise AppError("invalid_timezone", "La zona horaria no es una zona IANA válida", 422) from None


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """Dependencia FastAPI: una conexión por petición."""
    conn = connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def rest_context(request: Request) -> RequestContext:
    """Toda ruta REST viene hoy del token de escritorio: actor `user`."""
    state = request.scope.get("state") or {}
    return RequestContext("user", "rest", str(state.get("request_id") or new_id()))


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def insert_entity(
    conn: sqlite3.Connection, entity_id: str, entity_type: str, metadata: dict[str, Any] | None = None
) -> None:
    timestamp = now_utc()
    conn.execute(
        "INSERT INTO entities(id,entity_type,created_at,updated_at,metadata_json) VALUES(?,?,?,?,?)",
        (entity_id, entity_type, timestamp, timestamp, json.dumps(metadata or {}, ensure_ascii=False)),
    )


def touch_entity(
    conn: sqlite3.Connection, entity_id: str, expected_revision: int | None = None
) -> None:
    """Sube la revisión. Con `If-Match` distinto: 412 `revision_mismatch`."""
    row = conn.execute("SELECT revision FROM entities WHERE id=?", (entity_id,)).fetchone()
    if row is None:
        raise AppError("not_found", "No existe ese elemento", 404)
    if expected_revision is not None and row[0] != expected_revision:
        raise AppError("revision_mismatch", "El elemento cambió desde que se leyó", 412)
    conn.execute(
        "UPDATE entities SET revision=revision+1, updated_at=? WHERE id=?", (now_utc(), entity_id)
    )


def set_archived(conn: sqlite3.Connection, entity_id: str, archived: bool) -> None:
    touch_entity(conn, entity_id)
    conn.execute(
        "UPDATE entities SET archived_at=? WHERE id=?", (now_utc() if archived else None, entity_id)
    )


def require_entity(conn: sqlite3.Connection, entity_id: str, entity_type: str) -> None:
    row = conn.execute(
        "SELECT 1 FROM entities WHERE id=? AND entity_type=?", (entity_id, entity_type)
    ).fetchone()
    if row is None:
        raise AppError("not_found", "No existe ese elemento", 404)


def record_audit(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    action: str,
    *,
    result: AuditResult = "success",
    entity_type: str | None = None,
    entity_id: str | None = None,
    params: dict[str, Any] | None = None,
    changes: dict[str, Any] | None = None,
    error_code: str | None = None,
    affected_count: int | None = None,
    confirmation_id: str | None = None,
) -> None:
    """Mutación y auditoría van en la misma transacción. `params` es lista blanca: sin contenido libre."""
    conn.execute(
        "INSERT INTO audit_events(id,occurred_at,correlation_id,actor_type,origin,action,tool_name,"
        "entity_type,entity_id,affected_count,params_redacted_json,changes_json,result,error_code,"
        "confirmation_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            new_id(), now_utc(), ctx.correlation_id, ctx.actor_type, ctx.origin, action, ctx.tool_name,
            entity_type, entity_id, affected_count,
            None if params is None else json.dumps(params, ensure_ascii=False, default=str),
            None if changes is None else json.dumps(changes, ensure_ascii=False, default=str),
            result, error_code, confirmation_id,
        ),
    )  # fmt: skip


def request_confirmation(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    tool_name: str,
    args: dict[str, Any],
    summary: str,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    affected_count: int | None = None,
) -> ConfirmationRef:
    """Crea la confirmación pendiente; nada se ejecuta hasta la aprobación desde la GUI.

    La aprobación es del pipeline común (`POST /api/v1/confirmations/{id}/approve`),
    no del agente. Ese pipeline llama a `execute_confirmed` con los `args` guardados.
    """
    if tool_name not in CONFIRMED_ACTIONS:
        raise AppError("internal_error", "Acción sin ejecutor registrado", 500)
    created = datetime.now(UTC)
    expires_at = (created + CONFIRMATION_TTL).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    encoded = json.dumps(args, ensure_ascii=False, sort_keys=True, default=str)
    confirmation_id = new_id()
    conn.execute(
        "INSERT INTO pending_confirmations(id,tool_name,actor_type,turn_id,correlation_id,args_json,"
        "args_hash,summary,affected_count,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            confirmation_id, tool_name, ctx.actor_type, ctx.turn_id, ctx.correlation_id, encoded,
            hashlib.sha256(encoded.encode()).hexdigest(), summary, affected_count,
            created.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), expires_at,
        ),
    )  # fmt: skip
    record_audit(
        conn, ctx, tool_name, result="confirmation_required", entity_type=entity_type,
        entity_id=entity_id, affected_count=affected_count, confirmation_id=confirmation_id,
    )  # fmt: skip
    return ConfirmationRef(
        confirmation_id=confirmation_id, summary=summary, expires_at=expires_at,
        affected_count=affected_count,
    )  # fmt: skip


ConfirmedAction = Callable[[sqlite3.Connection, RequestContext, dict[str, Any]], dict[str, Any]]
CONFIRMED_ACTIONS: dict[str, ConfirmedAction] = {}


def confirmed_action(name: str) -> Callable[[ConfirmedAction], ConfirmedAction]:
    """Registra quién ejecuta `name` una vez aprobada. Lo usa el pipeline común."""

    def register(action: ConfirmedAction) -> ConfirmedAction:
        CONFIRMED_ACTIONS[name] = action
        return action

    return register


def bounded_limit(limit: int | None, default: int = 50) -> int:
    return max(1, min(limit if limit is not None else default, MAX_LIMIT))


def encode_cursor(value: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except ValueError:
        raise AppError("invalid_cursor", "Cursor no válido", 422) from None
    if not isinstance(value, dict):
        raise AppError("invalid_cursor", "Cursor no válido", 422)
    return value
