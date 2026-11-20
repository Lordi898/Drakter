"""Registro de proveedores de la voz v2 (plan de voz v2 §4.7). CONGELADO por WP0.

Tabla estática perezosa: nada se importa hasta `create`. Añadir un proveedor es una línea en
`TABLE`, o un nombre `"paquete.modulo:fabrica"` en la configuración, sin tocar el núcleo.
Las firmas de cada clase están en `voice/ports.py`.
"""

from __future__ import annotations

import importlib
from typing import Any, Final

TABLE: Final[dict[tuple[str, str], str]] = {
    ("stt", "moonshine"): "voice.providers.stt.moonshine_streaming:create",
    ("stt", "auto"): "voice.providers.stt.cloud:create",
    ("stt", "deepgram"): "voice.providers.stt.cloud:create",
    ("stt", "groq"): "voice.providers.stt.cloud:create",
    ("vad", "silero"): "voice.providers.vad.silero:create",
    ("turn_stop", "smart_turn"): "voice.providers.turn.smart_turn:create",
    ("turn_start", "drakter"): "voice.conversation.start_strategy:create",
    ("wake", "openwakeword"): "voice.providers.wake.openwakeword_gate:create",
    ("tts", "fish"): "voice.providers.tts.fish:create",
    ("tts", "kokoro"): "voice.providers.tts.kokoro:create",
    ("tts_chain", "failover"): "voice.providers.tts.failover:create",
    ("mixer", "duck"): "voice.conversation.duck:create",
    ("channel", "webrtc"): "voice.channels.webrtc:create",
    ("*", "null"): "voice.providers.null:create",
}


def resolve(kind: str, name: str) -> str:
    """Ruta `"modulo:fabrica"` de un proveedor. Un nombre con `:` se usa tal cual."""
    if ":" in name:
        return name
    target = TABLE.get((kind, name)) or TABLE.get(("*", name))
    if target is None:
        raise KeyError(f"proveedor desconocido: {kind}/{name}")
    return target


def create(kind: str, name: str, *args: Any, **kw: Any) -> Any:
    """Importa (perezoso) y llama a la fábrica. `null` recibe además `kind` como primer argumento."""
    target = resolve(kind, name)
    module, _, attr = target.partition(":")
    factory = getattr(importlib.import_module(module), attr)
    if target == TABLE[("*", "null")]:
        return factory(kind, *args, **kw)
    return factory(*args, **kw)
