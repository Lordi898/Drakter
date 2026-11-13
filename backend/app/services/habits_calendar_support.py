"""Interfaz fina con lo común para hábitos, calendario y asignaturas.

Lo destructivo no pasa por aquí salvo `run_confirmable`, que entrega la operación a
`ActionService`: es el único camino de escritura confirmable.
"""

from __future__ import annotations

import base64
import json
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Final, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from drakter_contracts.common import Origin as OriginEnum
from fastapi import Request
from pydantic import BaseModel

from app.core.errors import AppError, ErrorDetail
from app.database.connection import connect
from app.permissions.models import ActorContext, Principal

ActorType = Literal["user", "agent", "automation", "system"]
Origin = Literal["rest", "mcp", "scheduler", "internal"]
AuditResult = Literal["success", "denied", "failed", "confirmation_required"]

MAX_LIMIT: Final = 200


@dataclass(frozen=True)
class RequestContext:
    actor_type: ActorType
    origin: Origin
    correlation_id: str
    tool_name: str | None = None
    turn_id: str | None = None


def format_instant(value: datetime) -> str:
    """Igual que `drakter_contracts.common.format_instant`: 24 caracteres con milisegundos."""
    utc = value.astimezone(UTC)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond // 1000:03d}Z"


def now_utc() -> str:
    return format_instant(datetime.now(UTC))


def new_id() -> str:
    return str(uuid4())


def ensure_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError, OSError):
        raise AppError(
            "validation_error",
            "La zona horaria no es válida. Elige una de la lista.",
            422,
            [ErrorDetail(field="timezone", code="invalid_timezone", message="Zona desconocida")],
        ) from None


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """Dependencia FastAPI: una conexión por petición."""
    conn = connect(request.app.state.settings.db_path, check_same_thread=False)
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
        raise AppError("not_found", "No se encuentra ese elemento. Puede que se haya eliminado.", 404)
    if expected_revision is not None and row[0] != expected_revision:
        raise AppError("revision_mismatch", "Este elemento ha cambiado desde que lo abriste. Recarga y vuelve a intentarlo.", 412)
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
        raise AppError("not_found", "No se encuentra ese elemento. Puede que se haya eliminado.", 404)


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


def deletion_summary(kind: str, name: str, dependents: int = 0) -> str:
    """Plantilla de contracts/README.md §5. `name` es dato del usuario: la GUI lo pinta como texto."""
    extra = f" y {dependents} {'dependiente' if dependents == 1 else 'dependientes'}" if dependents else ""
    return f"Vas a eliminar 1 {kind}: «{name}»{extra}. Esta acción no se puede deshacer."


def run_confirmable(
    request: Request, ctx: RequestContext, action: str, params: BaseModel, summary: str
) -> Mapping[str, Any]:
    """Entrega un borrado a `ActionService`. Riesgo `confirm`: sale 409 `confirmation_required`.

    `summary` lo calcula el servicio con datos de la base, porque `ActionSpec.summarize`
    solo ve los argumentos; nunca viene del cliente. Sin el pipeline montado no se borra.
    """
    actions = getattr(request.app.state, "actions", None)
    spec = actions.registry.get(action) if actions is not None else None
    if spec is None:
        raise AppError(
            "confirmation_unavailable", "No se puede confirmar ahora mismo. No se ha borrado nada.", 503
        )
    actor = ActorContext(
        principal=Principal.UI, origin=OriginEnum.REST, correlation_id=ctx.correlation_id
    )
    return actions.unwrap(
        actions.execute_or_request(actor, replace(spec, summarize=lambda _: summary), params)
    )


def bounded_limit(limit: int | None, default: int = 50) -> int:
    return max(1, min(limit if limit is not None else default, MAX_LIMIT))


def encode_cursor(key: Sequence[Any]) -> str:
    """Cursor opaco sobre (campo de orden, id)."""
    return base64.urlsafe_b64encode(json.dumps(list(key)).encode()).decode()


def decode_cursor(cursor: str | None, size: int = 2) -> list[Any] | None:
    if cursor is None:
        return None
    try:
        key = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except ValueError:
        raise AppError("invalid_query", "La paginación no es válida. Vuelve a cargar la lista.", 400) from None
    if not isinstance(key, list) or len(key) != size:
        raise AppError("invalid_query", "La paginación no es válida. Vuelve a cargar la lista.", 400)
    return key


def split_page(
    rows: list[dict[str, Any]], limit: int, key_fields: Sequence[str]
) -> tuple[list[dict[str, Any]], str | None]:
    """`rows` trae hasta `limit + 1` filas: la de más solo dice si hay otra página."""
    if len(rows) <= limit:
        return rows, None
    page = rows[:limit]
    return page, encode_cursor([page[-1][field] for field in key_fields])
