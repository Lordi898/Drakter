"""Cadena TTS con respaldo: `ServiceSwitcher` con la estrategia `DrakterFailover` (V-12).

La estrategia base de Pipecat solo conmuta cuando el servicio queda `is_usable=False` (autenticación,
autorización, petición inválida). Esta además conmuta con cuota agotada o tras
`MAX_CONSECUTIVE` errores seguidos (en una ventana de `ERROR_WINDOW_S`). Al conmutar:
`state.tts_active="local"`, `voice.tts_fallback` y la frase `tts_fallback`, una sola vez por proceso.

Los proveedores marcados como no disponibles (`service.unavailable`, ver `fish.py`) se descartan al
construir: sin `FISH_API_KEY` o con la fecha vencida la cadena arranca directamente en Kokoro.
Si la sesión ya conmutó (`state.tts_active == "local"`), las conexiones nuevas también arrancan en local.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Final

from loguru import logger
from pipecat.frames.frames import ErrorFrame
from pipecat.pipeline.service_switcher import ServiceSwitcher, ServiceSwitcherStrategyFailover
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.utils.errors import ErrorCategory

from voice.ports import Ctl, TTSProvider

MAX_CONSECUTIVE: Final = 3
ERROR_WINDOW_S: Final = 60.0
_SWITCH_CATEGORIES: Final = frozenset({
    ErrorCategory.AUTHENTICATION,
    ErrorCategory.AUTHORIZATION,
    ErrorCategory.QUOTA,
    ErrorCategory.INVALID_REQUEST,
})
_REASONS: Final = {
    ErrorCategory.AUTHENTICATION: "auth",
    ErrorCategory.AUTHORIZATION: "auth",
    ErrorCategory.QUOTA: "quota",
    ErrorCategory.RATE_LIMIT: "rate_limit",
    ErrorCategory.CONNECTIVITY: "network",
}

_announced = False  # voice.tts_fallback: una vez por arranque del proceso


async def announce_fallback(ctl: Ctl | None, reason: str) -> None:
    """Marca el TTS local como activo y avisa una sola vez por proceso."""
    global _announced
    if ctl is not None:
        ctl.state.tts_active = "local"
    if _announced or ctl is None:
        return
    _announced = True
    try:
        await ctl.emit("voice.tts_fallback", {"from": "fish", "to": "local", "reason": reason})
        await ctl.play_phrase("tts_fallback", "when_silent")
    except Exception as exc:  # el aviso nunca rompe la voz
        logger.warning(f"tts_fallback: no se pudo avisar: {exc}")


class DrakterFailover(ServiceSwitcherStrategyFailover):
    """Failover con categorías ampliadas y recuento de errores seguidos."""

    def __init__(self, services: list[FrameProcessor]) -> None:
        super().__init__(services)
        self.ctl: Ctl | None = None
        self._errors = 0
        self._last_error = 0.0

    def bind(self, ctl: Ctl) -> None:
        self.ctl = ctl

    async def handle_error(self, error: ErrorFrame) -> FrameProcessor | None:
        failed = error.processor or self._active_service
        if failed is not self._active_service:
            return None
        now = time.monotonic()
        self._errors = self._errors + 1 if now - self._last_error < ERROR_WINDOW_S else 1
        self._last_error = now
        category = error.category or ErrorCategory.UNKNOWN
        if failed.is_usable and category not in _SWITCH_CATEGORIES and self._errors < MAX_CONSECUTIVE:
            return None
        logger.warning(f"TTS {failed.name}: error {category.value} ({self._errors} seguidos); conmutando")
        target = self._next_service()
        if target is None:
            logger.error("TTS: no hay otro servicio al que conmutar")
            return None
        switched = await self._set_active_if_available(target)
        if switched is not None:
            self._errors = 0
            await announce_fallback(self.ctl, _REASONS.get(category, "unknown"))
        return switched

    def _next_service(self) -> FrameProcessor | None:
        idx = self._services.index(self._active_service)
        for offset in range(1, len(self._services)):
            candidate = self._services[(idx + offset) % len(self._services)]
            if candidate.is_usable:
                return candidate
        return None


def create(cfg: Any, ctl: Ctl, providers: list[TTSProvider]) -> ServiceSwitcher:
    usable: list[TTSProvider] = []
    skipped_reason: str | None = None
    for p in providers:
        reason = getattr(p.service, "unavailable", None)
        if reason:
            skipped_reason = skipped_reason or reason
            continue
        usable.append(p)
    if not usable:
        raise RuntimeError("no hay ningún TTS disponible (ni Fish ni Kokoro)")
    if ctl.state.tts_active == "local":  # ya conmutó en esta sesión: arranca en local
        usable.sort(key=lambda p: p.expressive)
    for p in usable:  # la expresión de Fish sigue el ajuste voice.config en caliente
        if hasattr(p.service, "expression_enabled"):
            p.service.expression_enabled = lambda: ctl.state.expression != "off"
    switcher = ServiceSwitcher(services=[p.service for p in usable], strategy_type=DrakterFailover)
    switcher.strategy.bind(ctl)
    switcher.tts_providers = usable  # para quien necesite el nombre del servicio activo
    if not usable[0].expressive and any(p.expressive for p in providers):
        ctl.state.tts_active = "local"
        if skipped_reason:
            _schedule(announce_fallback(ctl, skipped_reason))
    elif usable[0].expressive:
        ctl.state.tts_active = "fish"
    return switcher


def _schedule(coro) -> None:
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:  # sin bucle (CLI): se descarta el aviso
        coro.close()
