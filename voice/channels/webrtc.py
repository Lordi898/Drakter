"""Canal WebRTC por loopback (transporte B): `SmallWebRTCTransport` sin servidores ICE.

El renderer captura con `getUserMedia` y negocia por señalización propia (renderer → main →
backend → IPC `rtc.offer` → aquí). Una sola conexión a la vez (`ConnectionMode.SINGLE`): una
oferta nueva sin el `pc_id` vigente es una reconexión (recarga del renderer) y sustituye a la
anterior. Por cada conexión nueva se llama a `on_connection(transport)`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.request_handler import (
    ConnectionMode,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

if TYPE_CHECKING:
    from pipecat.transports.base_transport import BaseTransport

    from voice.config import VoiceConfig

log = logging.getLogger("voice.webrtc")

LOOPBACK = "127.0.0.1"
_loopback_enabled = False


def enable_loopback_candidates() -> None:
    """Hace que aioice ofrezca 127.0.0.1 como candidato ICE de host.

    `aioice.ice.get_host_addresses` descarta el loopback a propósito (aioice 0.13, `ice.py`), y
    sin él la sesión depende de la IP de la red: cambiar de wifi a ethernet la tiraría, y sin
    red no habría voz. Se envuelve esa función (la busca por nombre global al reunir candidatos)
    y se pone el loopback el primero. Es el único parche a una librería de este proceso; el
    renderer necesita además `--allow-loopback-in-peer-connection` (WP8a).
    """
    global _loopback_enabled
    if _loopback_enabled:
        return
    import aioice.ice

    original = aioice.ice.get_host_addresses

    def with_loopback(use_ipv4: bool = True, use_ipv6: bool = True) -> list[str]:
        # aioice la llama por nombre (`use_ipv4=..., use_ipv6=...`): se reenvían igual.
        addresses = original(use_ipv4=use_ipv4, use_ipv6=use_ipv6)
        if use_ipv4 and LOOPBACK not in addresses:
            addresses.insert(0, LOOPBACK)
        return addresses

    aioice.ice.get_host_addresses = with_loopback
    _loopback_enabled = True


async def _no_connection_handler(_transport: BaseTransport) -> None:
    raise RuntimeError("WebRTCChannel.on_connection is not set")


class WebRTCChannel:
    """Implementa `ports.Channel`."""

    def __init__(self, cfg: VoiceConfig) -> None:
        if cfg.rtc_loopback:
            enable_loopback_candidates()
        self._ping_timeout = cfg.rtc_ping_timeout_s
        self._handler = SmallWebRTCRequestHandler(ice_servers=[], connection_mode=ConnectionMode.SINGLE)
        self._current: SmallWebRTCConnection | None = None
        self._lock = asyncio.Lock()
        self._watchdog: asyncio.Task[None] | None = None
        # Los fija el núcleo tras crear el canal.
        self.on_connection: Callable[[BaseTransport], Awaitable[None]] = _no_connection_handler
        self.make_mixer: Callable[[], Any] = lambda: None  # mixer de salida de cada conexión

    async def accept_offer(
        self, sdp: str, type: str, pc_id: str | None, restart_pc: bool | None
    ) -> dict[str, Any]:
        async with self._lock:
            current = self._current
            if current is None or pc_id != current.pc_id:
                # Conexión nueva. Si quedaba otra viva, el cliente se recargó: se cierra,
                # porque en modo SINGLE el manejador rechazaría la oferta.
                if current is not None:
                    log.info("replacing_connection", extra={"data": {}})
                    await self._drop_current()
                pc_id = None
            request = SmallWebRTCRequest(sdp=sdp, type=type, pc_id=pc_id, restart_pc=restart_pc)
            answer = await self._handler.handle_web_request(request, self._on_webrtc_connection)
            if answer is None:
                raise RuntimeError("no SDP answer")
            return dict(answer)

    async def _on_webrtc_connection(self, connection: SmallWebRTCConnection) -> None:
        self._current = connection

        @connection.event_handler("closed")
        async def on_closed(closed: SmallWebRTCConnection) -> None:
            if self._current is closed:
                self._current = None

        transport = SmallWebRTCTransport(
            webrtc_connection=connection,
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                audio_out_mixer=self.make_mixer(),
            ),
        )
        self._stop_watchdog()
        self._watchdog = asyncio.create_task(self._watch(connection))
        await self.on_connection(transport)

    async def _watch(self, connection: SmallWebRTCConnection) -> None:
        """Detecta la desconexión por el data channel.

        aiortc no avisa cuando el par desaparece sin cerrar (pestaña recargada, proceso muerto).
        El cliente manda `ping` por el data channel y Pipecat anota cuándo llegó el último
        (`is_connected()`); si deja de llegar, se cierra la conexión, y ese cierre es el que
        ve el transporte (`on_client_disconnected`).
        """
        seen, last_ok = False, time.monotonic()
        while self._current is connection:
            await asyncio.sleep(1.0)
            if connection.is_connected():
                seen, last_ok = True, time.monotonic()
            elif seen and time.monotonic() - last_ok > self._ping_timeout:
                log.warning("peer_lost", extra={"data": {"reason": "ping_timeout"}})
                await connection.disconnect()
                return

    def _stop_watchdog(self) -> None:
        if self._watchdog is not None and self._watchdog is not asyncio.current_task():
            self._watchdog.cancel()
        self._watchdog = None

    async def _drop_current(self) -> None:
        self._stop_watchdog()
        self._current = None
        await self._handler.close()  # desconecta el par y vacía el mapa de conexiones

    async def close(self) -> None:
        async with self._lock:
            await self._drop_current()


def create(cfg: VoiceConfig) -> WebRTCChannel:
    return WebRTCChannel(cfg)
