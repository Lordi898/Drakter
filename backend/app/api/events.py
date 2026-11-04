"""Único WebSocket: flujo de eventos servidor→cliente."""

from __future__ import annotations

from typing import Annotated

from drakter_contracts.common import Id
from fastapi import APIRouter, Query, WebSocket

from app.core.security import WS_SUBPROTOCOL

router = APIRouter()


@router.websocket("/api/v1/events")
async def events(
    websocket: WebSocket,
    after_seq: Annotated[int | None, Query(ge=0)] = None,
    boot_id: Id | None = None,
) -> None:
    offered = websocket.scope.get("subprotocols") or []
    await websocket.accept(subprotocol=WS_SUBPROTOCOL if WS_SUBPROTOCOL in offered else None)
    message = await websocket.receive()
    if message["type"] != "websocket.disconnect":
        # Los comandos van por REST: este canal no acepta entradas.
        await websocket.close(code=1003)
