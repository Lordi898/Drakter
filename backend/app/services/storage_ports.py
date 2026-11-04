"""Interfaz fina entre almacén/relaciones y lo que aún fija el contrato común.

Auditoría y confirmaciones las cierra drakter/seguridad. Hasta entonces los servicios
solo dependen de lo que hay aquí; al integrar se sustituyen estas clases sin tocarlos.
Sin adaptador real las confirmaciones fallan cerradas: nada destructivo se ejecuta.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, Protocol
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import AppError

ActorKind = Literal["user", "agent", "automation", "system"]
Origin = Literal["rest", "mcp", "scheduler", "internal"]
AuditResult = Literal["success", "denied", "failed", "confirmation_required"]

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

        Si no, lanza `confirmation_required` (409) con un objeto `confirmation`
        {id, summary, affected_count, expires_at, params_hash} en el sobre, o
        `confirmation_unavailable` (503). `summary` y `affected_count` los calcula
        el backend, jamás el modelo.
        """
        ...


def _redact_param(value: Any) -> Any:
    if isinstance(value, str):
        return value[:MAX_AUDIT_VALUE_CHARS]
    if isinstance(value, bool | int | float) or value is None:
        return value
    return f"<{type(value).__name__}>"


class SqlAudit:
    """Escribe en `audit_events`. Dentro de `write_tx` se confirma con la operación."""

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
        redacted = {k: _redact_param(v) for k, v in (params or {}).items()}
        conn.execute(
            "INSERT INTO audit_events (id, occurred_at, correlation_id, actor_type, origin, action,"
            " entity_type, entity_id, affected_count, params_redacted_json, result, error_code)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()), utc_now(), actor.correlation_id, actor.kind, actor.origin, action,
                entity_type, entity_id, affected_count, json.dumps(redacted, ensure_ascii=False),
                result, error_code,
            ),
        )


class ApprovedByDispatcher:
    """Solo para herramientas: `ToolRegistry.dispatch` ya aplicó `ToolGate` antes del handler."""

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
        return None


class DenyAllConfirmations:
    """Falla cerrada mientras drakter/seguridad no conecte `pending_confirmations`."""

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
        # Nunca `confirmation_required`: ese código exige un objeto `confirmation` con
        # ticket, y aquí no existe ninguno que la GUI pueda aprobar.
        raise AppError("confirmation_unavailable", "Confirmation service unavailable", 503)


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
    audit: AuditSink = field(default_factory=SqlAudit)
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
    """Formato del esquema: YYYY-MM-DDTHH:MM:SS.sssZ."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


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


def tool_deps(state: Any) -> StorageDeps:
    """Dependencias para un handler de herramienta. `state` es `ToolContext.state`."""
    return StorageDeps(settings=state.settings, gate=ApprovedByDispatcher())
