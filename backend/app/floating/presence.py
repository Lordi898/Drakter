"""Presencia del modo flotante (docs/floating/CONTRACT.md §7 y §8.1 bis).

Electron main la manda por `POST /api/v1/overlay/presence` al arrancar, en cada cambio y cada 30 s.
Caduca a los 75 s sin renovar: se trata como `active:false` (`current_presence()` devuelve None).
Solo memoria del proceso; no se guarda en la BD.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Final

from drakter_contracts.floating import FloatingPresence

logger = logging.getLogger("drakter.floating.presence")

TTL_S: Final = 75.0

_lock = threading.Lock()
_last: tuple[FloatingPresence, float] | None = None
_listeners: list[Callable[[FloatingPresence | None], None]] = []


def update_presence(presence: FloatingPresence) -> None:
    """Guarda la presencia y avisa a los oyentes (el DrawRunner para las guías al desactivarse)."""
    global _last
    with _lock:
        _last = (presence, time.monotonic())
        listeners = tuple(_listeners)
    for listener in listeners:
        try:
            listener(presence)
        except Exception:  # noqa: BLE001 - un oyente roto no tumba la ruta
            logger.exception("presence listener failed", extra={"event": "floating_presence_listener_failed"})


def current_presence() -> FloatingPresence | None:
    """None = nunca llegó o caducó (75 s)."""
    with _lock:
        if _last is None:
            return None
        presence, at = _last
    if time.monotonic() - at > TTL_S:
        return None
    return presence


def is_active() -> bool:
    presence = current_presence()
    return bool(presence and presence.active and presence.companion == "ok")


def on_presence(listener: Callable[[FloatingPresence | None], None]) -> Callable[[], None]:
    with _lock:
        _listeners.append(listener)

    def off() -> None:
        with _lock:
            if listener in _listeners:
                _listeners.remove(listener)

    return off
