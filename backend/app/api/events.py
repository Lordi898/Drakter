"""`WS /api/v1/events`: the single server-to-client stream. Commands go through REST."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Final
from uuid import UUID

from drakter_contracts.events import EventEnvelope
from fastapi import APIRouter, Query, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.core.security import WS_SUBPROTOCOL
from app.events import CLOSE, EventHub, Subscription

logger = logging.getLogger("drakter.api.events")

WS_SEND_TIMEOUT_S: Final = 5.0
WS_UNSUPPORTED_DATA: Final = 1003
WS_TRY_AGAIN_LATER: Final = 1013

router = APIRouter(prefix="/api/v1")


async def _send(websocket: WebSocket, envelope: EventEnvelope) -> None:
    text = envelope.model_dump_json()
    await asyncio.wait_for(websocket.send_text(text), timeout=WS_SEND_TIMEOUT_S)


async def _write_events(websocket: WebSocket, subscription: Subscription) -> int:
    """Only writer on the socket. Returns the close code once the client falls behind."""
    try:
        for envelope in subscription.replay:
            await _send(websocket, envelope)
        while True:
            item = await subscription.queue.get()
            if item is CLOSE:
                break
            await _send(websocket, item)
    except TimeoutError:
        pass
    logger.info("slow event client disconnected", extra={"event": "ws_slow_client"})
    return WS_TRY_AGAIN_LATER


async def _watch_input(websocket: WebSocket) -> int | None:
    """Nothing is expected from the client: only its disconnection is meaningful."""
    message = await websocket.receive()
    return None if message["type"] == "websocket.disconnect" else WS_UNSUPPORTED_DATA


@router.websocket("/events")
async def events(
    websocket: WebSocket,
    after_seq: Annotated[int | None, Query(ge=0)] = None,
    boot_id: UUID | None = None,
) -> None:
    offered = websocket.scope.get("subprotocols") or []
    await websocket.accept(subprotocol=WS_SUBPROTOCOL if WS_SUBPROTOCOL in offered else None)
    hub: EventHub | None = getattr(websocket.app.state, "event_hub", None)
    if hub is None:
        await websocket.close(code=WS_TRY_AGAIN_LATER)
        return
    subscription = hub.subscribe(after_seq, boot_id)
    writer = asyncio.create_task(_write_events(websocket, subscription))
    reader = asyncio.create_task(_watch_input(websocket))
    close_code: int | None = None
    try:
        done, _ = await asyncio.wait({writer, reader}, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task.exception() is None:
                close_code = task.result() or close_code
    finally:
        subscription.close()
        for task in (writer, reader):
            task.cancel()
        await asyncio.gather(writer, reader, return_exceptions=True)
    if close_code is not None:
        try:
            await asyncio.wait_for(websocket.close(code=close_code), timeout=WS_SEND_TIMEOUT_S)
        except (TimeoutError, RuntimeError, WebSocketDisconnect):
            pass
