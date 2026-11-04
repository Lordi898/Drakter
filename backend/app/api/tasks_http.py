"""Piezas HTTP compartidas por `api/tasks.py` y `api/projects.py`."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.errors import AppError, ErrorBody, ErrorEnvelope
from app.database.connection import connect
from app.services.tasks_ports import (
    Actor,
    ConfirmationRequired,
    Ports,
    ServiceContext,
)

PORTS_STATE_KEY: Final = "workspace_ports"


def _request_id(request: Request) -> str:
    return str(request.scope["state"]["request_id"])


@contextmanager
def service_context(request: Request) -> Iterator[ServiceContext]:
    """Conexión por petición, abierta y cerrada en el mismo hilo que la usa."""
    conn = connect(request.app.state.settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        ports = getattr(request.app.state, PORTS_STATE_KEY, None) or Ports()
        actor = Actor(actor_type="user", origin="rest", correlation_id=_request_id(request))
        yield ServiceContext(conn=conn, actor=actor, ports=ports)
    finally:
        conn.close()


def parse_if_match(value: str | None) -> int | None:
    """`If-Match: "<revision>"`, entity-tag entre comillas (C-19)."""
    if value is None:
        return None
    text = value.strip()
    if len(text) < 3 or text[0] != '"' or text[-1] != '"' or not text[1:-1].isdecimal():
        raise AppError("invalid_query", "La cabecera If-Match no es válida.", 400)
    return int(text[1:-1])


def confirmation_response(request: Request, required: ConfirmationRequired) -> JSONResponse:
    """409 con el envelope común y la extensión `confirmation` (C-20)."""
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code="confirmation_required",
            message="Esta operación necesita tu confirmación.",
            request_id=_request_id(request),
            details=[],
        )
    )
    return JSONResponse(
        status_code=409,
        content={
            **envelope.model_dump(mode="json"),
            "confirmation": required.ticket.model_dump(mode="json"),
        },
    )
