"""REST del modo flotante (docs/floating/CONTRACT.md §7). Solo Electron main, con el token `ui`.

No hay ruta para aprobar nada desde el overlay. `ink_action` se audita como acción del usuario (origen REST).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated
from uuid import uuid4

from drakter_contracts.common import Origin
from drakter_contracts.floating import FloatingPresence, OverlayClientEvent
from fastapi import APIRouter, Body, Depends, Request, Response, status

from app.audit.writer import AuditEvent, write
from app.core.errors import AppError
from app.database.connection import connect
from app.floating.presence import update_presence
from app.floating.runner import RUNNER
from app.permissions.models import ActorContext, Principal

logger = logging.getLogger("drakter.api.overlay")


def _is_desktop(principal: object) -> bool:
    return principal == "desktop" or (
        getattr(principal, "kind", None) == "user" and getattr(principal, "id", None) == "desktop"
    )


async def require_desktop(request: Request) -> None:
    """Solo el escritorio. Sin principal no hay valor por defecto: se rechaza (revisión PR #76, M5).

    Vale el que fije el guardia para la petición; si no lo fija, el que el cableado declara para el
    token `ui` (`app.state.gui_principal`, `permissions/wiring.py`). Sin ninguno de los dos, 403.
    """
    state = request.scope.get("state") or {}
    principal = state.get("principal")
    if principal is None:
        principal = getattr(request.app.state, "gui_principal", None)
    if principal is None or not _is_desktop(principal):
        raise AppError("forbidden", "Desktop session required", 403)


router = APIRouter(prefix="/api/v1/overlay", dependencies=[Depends(require_desktop)])


@router.post("/presence", status_code=status.HTTP_204_NO_CONTENT)
async def post_presence(body: FloatingPresence, request: Request) -> Response:
    RUNNER.bind(request.app.state)
    update_presence(body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _audit_action(request: Request, part: str, found: bool) -> None:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        return
    conn = connect(settings.db_path)
    try:
        write(
            conn,
            ActorContext(principal=Principal.UI, origin=Origin.REST, correlation_id=str(uuid4())),
            AuditEvent(
                action="overlay.ink_action", result="success" if found else "failed",
                entity_type="overlay_part", entity_id=part, error_code=None if found else "not_found",
            ),
        )
        conn.commit()
    finally:
        conn.close()


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
async def post_event(event: Annotated[OverlayClientEvent, Body()], request: Request) -> Response:
    found = await RUNNER.client_event(event, state=request.app.state)
    if event.type == "ink_action":
        try:
            await asyncio.to_thread(_audit_action, request, event.part, found)
        except Exception:  # noqa: BLE001 - la auditoría no se salta en silencio
            logger.exception("ink_action audit failed", extra={"event": "overlay_audit_failed"})
            raise AppError("service_unavailable", "The action could not be audited.", 503) from None
    if not found:
        raise AppError("not_found", "That guide or part is gone.", 404)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
