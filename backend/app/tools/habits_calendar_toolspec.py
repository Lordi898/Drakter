"""Adaptador al contrato de herramientas de drakter-16 (`app/tools/spec.py`).

Usa el `ToolSpec` real en cuanto esté en la rama; hasta entonces define uno con los
mismos campos, para que `app/tools/{habits,calendar,subjects}.py` no cambien.

`service_handler` convierte un servicio `(conn, ctx, args)` en el handler
`(tool_ctx, args)` que espera el registro. El agente solo llega a la base por aquí.
La confirmación de RiskClass.CONFIRM la impone `ToolGate` y la ejecución es de
`ActionService`: el handler de `delete_*` se niega a borrar y no hay herramienta de aprobar.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.core.errors import AppError
from app.database.connection import connect
from app.services.habits_calendar_support import RequestContext

try:
    from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec
except ImportError:
    from drakter_contracts.tools import RiskClass

    AuditPolicy = Literal["log", "hash", "omit"]

    @dataclass(frozen=True, slots=True)
    class ToolContext:  # type: ignore[no-redef]
        turn_id: UUID
        session_id: UUID
        call_id: str
        principal: Literal["agent"]
        state: Any

    class ToolError(Exception):  # type: ignore[no-redef]
        def __init__(
            self, code: str, message: str, retryable: bool = False, details: Any = None
        ) -> None:
            super().__init__(code)
            self.code = code
            self.message = message
            self.retryable = retryable
            self.details = details

    @dataclass(frozen=True, slots=True)
    class ToolSpec:  # type: ignore[no-redef]
        name: str
        description: str
        domain: str
        args_model: type[BaseModel]
        result_model: type[BaseModel]
        permission: str
        risk: RiskClass
        handler: Callable[[Any, Any], Any]
        errors: tuple[str, ...] = ()
        idempotent: bool = False
        timeout_s: float = 15.0
        returns_untrusted: bool = False
        audit: Mapping[str, AuditPolicy] = field(default_factory=dict)
        summarize: Callable[[BaseModel], str] | None = None


__all__ = ["RiskClass", "ToolContext", "ToolError", "ToolSpec", "deny_direct", "service_handler"]

A = TypeVar("A", bound=BaseModel)
R = TypeVar("R", bound=BaseModel)


def service_handler(
    tool_name: str, service: Callable[[sqlite3.Connection, RequestContext, A], R]
) -> Callable[[ToolContext, A], R]:
    """Abre la conexión, fija el actor `agent` y traduce `AppError` a `ToolError`."""

    def handler(tool_ctx: ToolContext, args: A) -> R:
        ctx = RequestContext(
            "agent", "mcp", str(tool_ctx.turn_id), tool_name=tool_name, turn_id=str(tool_ctx.turn_id)
        )
        conn = connect(tool_ctx.state.settings.db_path)
        try:
            return service(conn, ctx, args)
        except AppError as exc:
            raise ToolError(exc.code, exc.message) from None
        finally:
            conn.close()

    return handler


def deny_direct(tool_ctx: ToolContext, args: BaseModel) -> Any:
    """Un borrado nunca corre por `handler`: si se llega aquí, falla cerrado."""
    raise ToolError("confirmation_unavailable", "Esta acción solo se ejecuta al aprobarla en la GUI.")
