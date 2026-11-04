"""Base WebSocket endpoint: ping/pong only."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import WS_SUBPROTOCOL

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    offered = websocket.scope.get("subprotocols") or []
    if WS_SUBPROTOCOL in offered:
        await websocket.accept(subprotocol=WS_SUBPROTOCOL)
    else:
        await websocket.accept()
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            if message.get("text") == "ping":
                await websocket.send_text("pong")
            else:
                await websocket.close(code=1003)
                return
    except WebSocketDisconnect:
        return
