"""TTS principal: Fish Audio por WebSocket (plan de voz v2 V-11, V-13).

Guardas:
- Modelo: solo `s2.1-pro-free`. Cualquier otro aborta el arranque (el de pago es el defecto de Pipecat).
- Fecha: después de `cfg.fish_free_until` (2026-11-30) Fish no se usa (`expired`), salvo `cfg.allow_paid`.
- Sin `FISH_API_KEY`: no se usa (`auth`).
En los dos últimos casos la fábrica devuelve el proveedor marcado como no disponible
(`service.unavailable = motivo`) y sin conectar; la cadena de failover lo descarta y arranca en Kokoro.

`voice` es el reference_id resuelto en ejecución; nunca se loguea. No se usan `reference_id=`,
`model_id=` ni `params=` (deprecados).
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date
from typing import Any

from pipecat.services.fish.tts import FishAudioTTSService
from pipecat.utils.text.transforms.strip_markdown import StripMarkdown

from voice.ports import ResolvedProfile, TTSProvider
from voice.providers.tts._common import (
    FISH_MODEL,
    SAMPLE_RATE,
    cfg_get,
    fish_free_until,
    t_expression,
)
from voice.speech.lexicon import lexicon
from voice.speech.normalize import normalize_es


class FishModelNotAllowed(RuntimeError):
    """El modelo configurado no es el gratuito: no se arranca para no facturar."""


def fish_unavailable(cfg: Any, today: date | None = None) -> str | None:
    """Motivo por el que Fish no debe usarse (`"expired"`, `"auth"`) o `None` si puede."""
    today = today or date.today()
    if today > fish_free_until(cfg) and not cfg_get(cfg, "allow_paid", False):
        return "expired"
    if not os.environ.get("FISH_API_KEY"):
        return "auth"
    return None


class DrakterFishTTSService(FishAudioTTSService):
    """Fish con dos añadidos: `unavailable` (no conecta) y la expresión conmutable en caliente."""

    def __init__(self, *, unavailable: str | None = None, **kwargs: Any) -> None:
        self.unavailable = unavailable
        self.expression_enabled: Callable[[], bool] = lambda: True
        super().__init__(**kwargs)

    async def _connect(self) -> None:
        if self.unavailable:
            return
        await super()._connect()


def create(cfg: Any, shared: Any, profile: ResolvedProfile, *, today: date | None = None) -> TTSProvider:
    model = cfg_get(cfg, "tts_model", FISH_MODEL)
    if model != FISH_MODEL:
        raise FishModelNotAllowed(f"modelo de Fish no permitido: {model!r} (solo {FISH_MODEL!r})")
    unavailable = fish_unavailable(cfg, today)
    service_ref: list[DrakterFishTTSService] = []
    expression = t_expression(lambda: service_ref[0].expression_enabled() if service_ref else True)
    service = DrakterFishTTSService(
        unavailable=unavailable,
        api_key=os.environ.get("FISH_API_KEY", ""),
        sample_rate=SAMPLE_RATE,
        settings=FishAudioTTSService.Settings(
            model=FISH_MODEL,
            voice=profile.voice,
            latency="balanced",
            normalize=False,
        ),
        text_transforms=[
            ("*", expression),
            ("*", StripMarkdown(strip_urls=True)),
            ("*", lexicon),
            ("*", normalize_es),
        ],
    )
    service_ref.append(service)
    return TTSProvider(service=service, name="fish", expressive=True)
