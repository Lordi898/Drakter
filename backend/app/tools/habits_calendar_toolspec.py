"""ToolSpec provisional (C-03, C-04) hasta que `contracts/` fije el común.

Cada `TOOLS` de `habits_tools`, `calendar_tools` y `subjects_tools` se adapta aquí
sin cambios. El agente no toca la base: `run_tool` valida, ejecuta el servicio y
audita. Ninguna herramienta aprueba confirmaciones.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from app.core.errors import AppError
from app.services.habits_calendar_support import ConfirmationRef, RequestContext, record_audit

Risk = Literal["read", "write", "sensitive"]
Confirmation = Literal["never", "always"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel] | None
    handler: Callable[[sqlite3.Connection, RequestContext, Any], Any]
    permission: str
    risk: Risk
    confirmation: Confirmation = "never"
    read_only: bool = False
    idempotent: bool = False
    timeout_s: int = 10
    errors: tuple[str, ...] = ("validation_error", "not_found", "conflict")
    audit_fields: tuple[str, ...] = field(default=())


def _dump(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump(item) for item in value]
    return value


def _rejected(code: str, message: str, fields: list[str] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "rejected",
        "error": {"code": code, "message": message, "retryable": False, "fields": fields or []},
    }


def run_tool(
    spec: ToolSpec, conn: sqlite3.Connection, ctx: RequestContext, raw_args: dict[str, Any]
) -> dict[str, Any]:
    """Rechazos previsibles con `ok:false`, sin excepción, para no disparar el breaker de Hermes."""
    params = {key: raw_args[key] for key in spec.audit_fields if key in raw_args}
    try:
        args = spec.input_model.model_validate(raw_args)
    except ValidationError as exc:
        fields = [".".join(str(part) for part in error["loc"]) for error in exc.errors()]
        record_audit(
            conn, ctx, spec.name, result="failed", params=params, error_code="validation_error"
        )
        return _rejected("validation_error", "Parámetros no válidos", fields)
    try:
        result = spec.handler(conn, ctx, args)
    except AppError as exc:
        record_audit(conn, ctx, spec.name, result="failed", params=params, error_code=exc.code)
        return _rejected(exc.code, exc.message, [d.field for d in exc.details if d.field])
    if isinstance(result, ConfirmationRef):
        return {
            "ok": False,
            "status": "confirmation_required",
            "confirmation": result.model_dump(mode="json", exclude={"status"}),
            "meta": {"correlation_id": ctx.correlation_id},
        }
    if spec.read_only:
        record_audit(conn, ctx, spec.name, params=params)
    return {
        "ok": True,
        "status": "completed",
        "data": _dump(result),
        "meta": {"correlation_id": ctx.correlation_id, "truncated": False},
    }
