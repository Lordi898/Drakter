"""Peticiones estéticas al escritorio: modo (Drakter/Jarvis, `ui.mode`) y apariencia (avatar o
interfaz Jarvis, `ui.appearance`).

Única salida para las dos vías (capa 0 de la voz y las herramientas `ui_set_mode`/`ui_set_appearance`),
con un límite de un cambio por segundo por tipo de petición. No guarda el modo: es una preferencia de la interfaz y el renderer
decide si la aplica. El evento no lleva datos del usuario.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Final, Literal

from drakter_contracts.events import AvatarChoice, JarvisLayoutChoice, UiAppearanceRequested, UiModeRequested

logger = logging.getLogger("drakter.ui_mode")

UiMode = Literal["jarvis", "drakter"]
UiSource = Literal["voice", "agent"]
Outcome = Literal["published", "rate_limited", "unavailable"]

MIN_INTERVAL_S: Final = 1.0

_lock = threading.Lock()
_last_at = float("-inf")
_last_appearance_at = float("-inf")


def request_ui_mode(
    hub: Any,
    mode: UiMode,
    source: UiSource,
    *,
    utt_id: str | None = None,
    correlation_id: str | None = None,
) -> Outcome:
    """Publica la petición. Nunca lanza: el resultado dice qué pasó."""
    global _last_at
    if hub is None:
        return "unavailable"
    payload = UiModeRequested(mode=mode, source=source, utt_id=utt_id[:64] if utt_id else None)
    with _lock:
        now = time.monotonic()
        if now - _last_at < MIN_INTERVAL_S:
            return "rate_limited"
        _last_at = now
    try:
        hub.publish("ui.mode", payload, correlation_id=correlation_id)
    except Exception:  # noqa: BLE001 - un fallo del hub no tumba ni la voz ni la herramienta
        logger.exception("ui.mode publish failed", extra={"event": "ui_mode_publish_failed"})
        return "unavailable"
    return "published"


def request_ui_appearance(
    hub: Any,
    source: UiSource,
    *,
    avatar: AvatarChoice | None = None,
    layout: JarvisLayoutChoice | None = None,
    utt_id: str | None = None,
    correlation_id: str | None = None,
) -> Outcome:
    """Publica `ui.appearance` (al menos uno de `avatar` o `layout`). Nunca lanza."""
    global _last_appearance_at
    if hub is None or (avatar is None and layout is None):
        return "unavailable"
    payload = UiAppearanceRequested(
        avatar=avatar, layout=layout, source=source, utt_id=utt_id[:64] if utt_id else None
    )
    with _lock:
        now = time.monotonic()
        if now - _last_appearance_at < MIN_INTERVAL_S:
            return "rate_limited"
        _last_appearance_at = now
    try:
        hub.publish("ui.appearance", payload, correlation_id=correlation_id)
    except Exception:  # noqa: BLE001 - un fallo del hub no tumba ni la voz ni la herramienta
        logger.exception("ui.appearance publish failed", extra={"event": "ui_appearance_publish_failed"})
        return "unavailable"
    return "published"
