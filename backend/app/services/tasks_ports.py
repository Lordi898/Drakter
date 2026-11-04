"""Interfaz fina hacia lo común: actor, confirmaciones, eventos y transacción.

Tareas y proyectos dependen solo de esto. Cuando `contracts/` y `drakter/seguridad` fijen
las piezas reales, se cambia la implementación aquí sin tocar los servicios.
"""

from __future__ import annotations

import base64
import binascii
import json
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, Literal, Protocol
from uuid import uuid4

from app.core.errors import AppError
from app.schemas.tasks import ConfirmationTicket, format_timestamp

BULK_THRESHOLD: Final = 10  # Más de este número de filas afectadas es "masivo" (C-06).
MAX_TASK_DEPTH: Final = 8  # Una tarea raíz tiene profundidad 0.
MAX_CURSOR_OFFSET: Final = 1_000_000

ActorType = Literal["user", "agent", "automation", "system"]
Origin = Literal["rest", "mcp", "scheduler", "internal"]


@dataclass(frozen=True)
class Actor:
    actor_type: ActorType
    origin: Origin
    correlation_id: str
    tool_name: str | None = None
    confirmation_id: str | None = None


@dataclass(frozen=True)
class ConfirmationTarget:
    """Lo que el backend resolvió al pedir la confirmación. Si `revision` cambia, no se ejecuta."""

    entity_id: str
    revision: int


class ConfirmationRequired(Exception):
    """Resultado de flujo, no un fallo: REST lo da como 409 y MCP como `confirmation_required`."""

    def __init__(self, ticket: ConfirmationTicket) -> None:
        super().__init__("confirmation_required")
        self.ticket = ticket


class ConfirmationGate(Protocol):
    def request(
        self,
        conn: sqlite3.Connection,
        *,
        actor: Actor,
        tool_name: str,
        args: Mapping[str, Any],
        summary: str,
        affected_count: int,
        targets: Sequence[ConfirmationTarget],
    ) -> ConfirmationTicket:
        """Crea la fila pendiente fuera de cualquier transacción abierta y emite el evento."""
        ...


class EventSink(Protocol):
    def publish(self, event_type: str, payload: Mapping[str, Any]) -> None: ...


class FailClosedGate:
    """Sin puerta real no se ejecuta nada destructivo: el fallo es rechazar, nunca seguir."""

    def request(self, conn: sqlite3.Connection, **_: Any) -> ConfirmationTicket:
        raise AppError(
            "confirmation_unavailable",
            "Las confirmaciones no están disponibles; la operación no se ha ejecutado.",
            503,
        )


class NullEventSink:
    def publish(self, event_type: str, payload: Mapping[str, Any]) -> None:
        return None


@dataclass(frozen=True)
class Ports:
    confirmations: ConfirmationGate = field(default_factory=FailClosedGate)
    events: EventSink = field(default_factory=NullEventSink)


@dataclass(frozen=True)
class ServiceContext:
    conn: sqlite3.Connection
    actor: Actor
    ports: Ports


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    """`BEGIN IMMEDIATE` explícito: `connect` usa `isolation_level=None`."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def new_id() -> str:
    return str(uuid4())


def utc_now() -> str:
    return format_timestamp(datetime.now(UTC))


def not_found(what: str) -> AppError:
    return AppError("not_found", f"{what} no existe.", 404)


def conflict(message: str) -> AppError:
    return AppError("conflict", message, 409)


def check_revision(current: int, expected: int | None) -> None:
    if expected is not None and current != expected:
        raise AppError(
            "revision_mismatch",
            "El elemento cambió desde que se leyó. Vuelve a cargarlo.",
            412,
        )


def encode_cursor(offset: int) -> str:
    raw = json.dumps({"o": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        offset = json.loads(base64.urlsafe_b64decode(padded.encode()))["o"]
    except (binascii.Error, ValueError, KeyError, TypeError, UnicodeError):
        raise AppError("invalid_query", "El cursor no es válido.", 400) from None
    if not isinstance(offset, int) or isinstance(offset, bool):
        raise AppError("invalid_query", "El cursor no es válido.", 400)
    if not 0 <= offset <= MAX_CURSOR_OFFSET:
        raise AppError("invalid_query", "El cursor no es válido.", 400)
    return offset
