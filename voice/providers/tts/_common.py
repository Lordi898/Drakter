"""Piezas comunes de los proveedores TTS: lectura tolerante de `VoiceConfig` y transforms de texto."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, Final

from drakter_contracts.speech_markup import keep_allowed, strip_tags

FISH_MODEL: Final = "s2.1-pro-free"
"""Único modelo de Fish permitido (V-11): el de pago (`s2.1-pro`) es el valor por defecto de Pipecat."""
FISH_FREE_UNTIL: Final = date(2026, 11, 30)
SAMPLE_RATE: Final = 24000
DEFAULT_MODELS_DIR: Final = Path.home() / ".local" / "share" / "drakter" / "models"


def cfg_get(cfg: Any, name: str, default: Any) -> Any:
    """Campo de `VoiceConfig` con valor por defecto (WP1 define la clase; aquí no se asume)."""
    value = getattr(cfg, name, None)
    return default if value is None else value


def models_dir(cfg: Any, shared: Any = None) -> Path:
    for source in (shared, cfg):
        value = getattr(source, "models_dir", None)
        if value:
            return Path(value)
    return DEFAULT_MODELS_DIR


def fish_free_until(cfg: Any) -> date:
    value = cfg_get(cfg, "fish_free_until", FISH_FREE_UNTIL)
    return value if isinstance(value, date) else date.fromisoformat(str(value))


async def t_keep_allowed(text: str, _t: object = None) -> str:
    return keep_allowed(text)


async def t_strip_tags(text: str, _t: object = None) -> str:
    return strip_tags(text)


def t_expression(enabled: Callable[[], bool]):
    """Para Fish: deja las etiquetas permitidas, o las quita todas si la expresión está apagada."""

    async def transform(text: str, _t: object = None) -> str:
        return keep_allowed(text) if enabled() else strip_tags(text)

    return transform
