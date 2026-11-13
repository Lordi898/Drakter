"""Adaptador al contrato de herramientas de drakter-16 (`app/tools/spec.py`).

Reexporta el `ToolSpec` real para `app/tools/{habits,calendar,subjects}.py`.

`service_handler` convierte un servicio `(conn, ctx, args)` en el handler
`(tool_ctx, args)` que espera el registro. El agente solo llega a la base por aquí.
La confirmación de RiskClass.CONFIRM la impone `ToolGate` y la ejecución es de
`ActionService`: el handler de `delete_*` se niega a borrar y no hay herramienta de aprobar.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.errors import AppError
from app.database.connection import connect
from app.services.habits_calendar_support import RequestContext
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec


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
