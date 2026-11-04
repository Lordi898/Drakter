"""Interfaz fina entre almacén/relaciones y lo que aún fija el contrato común.

Auditoría, confirmaciones y ToolSpec los define drakter-11 en `contracts/`. Hasta
entonces los módulos solo dependen de lo que hay aquí; al integrar se sustituyen
estas clases por adaptadores sin tocar los servicios. Sin adaptador real las
confirmaciones fallan cerradas: nada destructivo se ejecuta.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.core.errors import AppError, ErrorDetail

audit_logger = logging.getLogger("drakter.audit")

ActorKind = Literal["user", "agent", "automation", "system"]
Origin = Literal["rest", "mcp", "scheduler", "internal"]
AuditResult = Literal["success", "denied", "failed", "confirmation_required"]
Risk = Literal["low", "medium", "high"]
ToolConfirmation = Literal["never", "required"]

MAX_AUDIT_VALUE_CHARS: Final = 200


@dataclass(frozen=True)
class Actor:
    kind: ActorKind
    origin: Origin
    correlation_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def is_agent(self) -> bool:
        return self.kind == "agent"


class AuditSink(Protocol):
    def record(
        self,
        conn: sqlite3.Connection,
        actor: Actor,
        *,
        action: str,
        result: AuditResult,
        entity_type: str | None = None,
        entity_id: str | None = None,
        affected_count: int | None = None,
        params: Mapping[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None: ...


class ConfirmationGate(Protocol):
    def require(
        self,
        conn: sqlite3.Connection,
        actor: Actor,
        *,
        tool: str,
        args: Mapping[str, Any],
        summary: str,
        affected_count: int,
        confirmation_id: str | None,
    ) -> None:
        """Vuelve solo si hay una aprobación válida de la GUI para estos argumentos.

        Si no, lanza `AppError` con `confirmation_required` (409). `summary` y
        `affected_count` los calcula el backend, jamás el modelo.
        """
        ...


def _redact_param(value: Any) -> Any:
    if isinstance(value, str):
        return value[:MAX_AUDIT_VALUE_CHARS]
    if isinstance(value, bool | int | float) or value is None:
        return value
    return f"<{type(value).__name__}>"


class LoggingAudit:
    """Provisional: va al log JSON, que ya redacta secretos. Sustituir por `audit_events`."""

    def record(
        self,
        conn: sqlite3.Connection,
        actor: Actor,
        *,
        action: str,
        result: AuditResult,
        entity_type: str | None = None,
        entity_id: str | None = None,
        affected_count: int | None = None,
        params: Mapping[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        audit_logger.info(
            "audit",
            extra={
                "event": "audit",
                "actor_type": actor.kind,
                "origin": actor.origin,
                "correlation_id": actor.correlation_id,
                "action": action,
                "result": result,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "affected_count": affected_count,
                "params": {k: _redact_param(v) for k, v in (params or {}).items()},
                "error_code": error_code,
            },
        )


class DenyAllConfirmations:
    """Falla cerrada mientras no exista el flujo real de `pending_confirmations`."""

    def require(
        self,
        conn: sqlite3.Connection,
        actor: Actor,
        *,
        tool: str,
        args: Mapping[str, Any],
        summary: str,
        affected_count: int,
        confirmation_id: str | None,
    ) -> None:
        raise AppError("confirmation_required", "This action needs confirmation", 409)


@dataclass(frozen=True)
class StorageLimits:
    """Valores iniciales propuestos, sin medir (BL-15, C-18)."""

    max_read_file_bytes: int = 64 * 1024 * 1024
    max_text_bytes: int = 8 * 1024 * 1024
    max_read_chars: int = 20_000
    default_read_chars: int = 8_000
    max_index_chars: int = 200_000
    index_chunk_chars: int = 4_000
    max_hash_bytes: int = 512 * 1024 * 1024
    scan_max_entries: int = 50_000
    scan_max_depth: int = 32
    pdf_max_pages: int = 2_000
    worker_cpu_seconds: int = 20
    worker_address_space_bytes: int = 1024 * 1024 * 1024
    worker_timeout_seconds: float = 30.0
    worker_max_output_bytes: int = 4 * 1024 * 1024
    archive_max_bytes: int = 512 * 1024 * 1024
    archive_max_entries: int = 10_000
    archive_max_total_bytes: int = 2 * 1024 * 1024 * 1024
    archive_max_entry_bytes: int = 100 * 1024 * 1024
    archive_max_ratio: int = 100
    archive_max_depth: int = 16
    archive_max_path_bytes: int = 1024
    link_max_bytes: int = 4 * 1024 * 1024
    link_timeout_seconds: float = 10.0
    link_max_redirects: int = 3


@dataclass(frozen=True)
class StorageDeps:
    settings: Settings
    audit: AuditSink = field(default_factory=LoggingAudit)
    gate: ConfirmationGate = field(default_factory=DenyAllConfirmations)
    limits: StorageLimits = field(default_factory=StorageLimits)

    @property
    def denied_roots(self) -> tuple[Path, ...]:
        """Rutas que nunca se sirven, aunque queden dentro de una ubicación (BL-12)."""
        home = Path.home()
        return (
            home / ".ssh",
            home / ".gnupg",
            home / ".aws",
            home / ".config" / "drakter",
            home / ".hermes",
            home / ".mozilla",
            home / ".config" / "google-chrome",
            home / ".config" / "chromium",
            self.settings.data_dir,
            self.settings.runtime_dir,
        )


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def new_id() -> str:
    return str(uuid4())


@contextmanager
def write_tx(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """`connect` usa autocommit: las escrituras compuestas pasan por aquí."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


@dataclass(frozen=True)
class ToolContext:
    conn: sqlite3.Connection
    actor: Actor
    deps: StorageDeps


ToolHandler = Callable[[ToolContext, Any], BaseModel]


@dataclass(frozen=True)
class ToolSpec:
    """Forma local; se adapta al ToolSpec de `contracts/` al integrar."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    permission: str
    risk: Risk
    confirmation: ToolConfirmation
    handler: ToolHandler


def run_tool(spec: ToolSpec, ctx: ToolContext, raw_args: Mapping[str, Any]) -> dict[str, Any]:
    """Valida, ejecuta, audita y devuelve siempre un resultado estructurado."""
    audit_params = dict(raw_args)
    try:
        args = spec.input_model.model_validate(raw_args)
    except ValidationError as exc:
        ctx.deps.audit.record(
            ctx.conn, ctx.actor, action=spec.name, result="failed",
            params=audit_params, error_code="validation_error",
        )
        details = [
            {"field": ".".join(str(p) for p in e["loc"]), "code": e["type"], "message": "Invalid value"}
            for e in exc.errors()
        ]
        return {"ok": False, "error": {"code": "validation_error", "message": "Invalid arguments", "details": details}}
    try:
        output = spec.handler(ctx, args)
    except AppError as exc:
        result: AuditResult = "confirmation_required" if exc.code == "confirmation_required" else "failed"
        ctx.deps.audit.record(
            ctx.conn, ctx.actor, action=spec.name, result=result,
            params=audit_params, error_code=exc.code,
        )
        details = [_detail_dict(d) for d in exc.details]
        return {"ok": False, "error": {"code": exc.code, "message": exc.message, "details": details}}
    except Exception:
        audit_logger.exception("tool_failed", extra={"event": "tool_failed", "tool": spec.name})
        ctx.deps.audit.record(
            ctx.conn, ctx.actor, action=spec.name, result="failed",
            params=audit_params, error_code="internal_error",
        )
        return {"ok": False, "error": {"code": "internal_error", "message": "Internal error", "details": []}}
    ctx.deps.audit.record(ctx.conn, ctx.actor, action=spec.name, result="success", params=audit_params)
    return {"ok": True, "result": json.loads(output.model_dump_json())}


def _detail_dict(detail: ErrorDetail) -> dict[str, Any]:
    return detail.model_dump()
