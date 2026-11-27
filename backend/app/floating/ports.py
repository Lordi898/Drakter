"""Puertos del DrawRunner hacia B3 (pantalla y manos) y V1 (voz), detrás de sus firmas congeladas
(docs/floating/CONTRACT.md §8.1 bis, §9.2 y §10).

Mientras B3 o V1 no estén fusionados, se usan dobles: la resolución pone las marcas donde dicen sus `x/y`
(o en una rejilla fija si solo traen `text`/`id`), y la voz responde `voiced=False` (el overlay usa su reloj
local). En cuanto existan `app.integrations.hands.resolve` y `VoiceOrchestrator.speak_beat`, se usan ellos.
"""

from __future__ import annotations

import importlib
import itertools
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from drakter_contracts.floating import MissingTarget

logger = logging.getLogger("drakter.floating.ports")

_PLACES = ("at", "to", "tie")


@dataclass
class Seg:
    """`ResolvedSeg` de §9.2, normalizado."""

    beats: list[dict[str, Any]]
    missing: list[MissingTarget] = field(default_factory=list)
    win: list[float] | None = None
    busy: list[list[float]] = field(default_factory=list)


def _module(name: str) -> Any | None:
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name and f"{name}.".startswith(f"{exc.name}."):
            return None
        raise


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_missing(item: Any) -> MissingTarget:
    return item if isinstance(item, MissingTarget) else MissingTarget.model_validate(
        item if isinstance(item, dict) else item.model_dump()
    )


def _simulated(beats: list[dict[str, Any]]) -> Seg:
    """Doble de B3: px de captura = px lógicos (escala 1, origen 0)."""
    out = []
    for b in beats:
        marks = []
        for j, m in enumerate(b.get("marks") or []):
            o = dict(m)
            for k in _PLACES:
                t = m.get(k)
                if not isinstance(t, dict):
                    continue
                if t.get("x") is not None and t.get("y") is not None:
                    w, h = t.get("w") or 28, t.get("h") or 28
                    rect = [t["x"] - w / 2, t["y"] - h / 2, w, h]
                else:
                    rect = [120 + 90 * j, 120, 80, 28]
                o[k] = {"rect": [round(v) for v in rect], "src": t}
            if isinstance(m.get("points"), list):
                o["points"] = [list(p) for p in m["points"]]
            marks.append(o)
        out.append({**b, "marks": marks})
    return Seg(beats=out)


async def resolve_marks(beats: list[dict[str, Any]], *, target: str, turn_id: UUID, after_wait: bool) -> Seg:
    mod = _module("app.integrations.hands.resolve")
    fn = getattr(mod, "resolve_marks", None) if mod else None
    if fn is None:
        return _simulated(beats)
    res = await fn(beats, target=target, turn_id=turn_id, after_wait=after_wait)
    return Seg(
        beats=list(_get(res, "beats") or []),
        missing=[_as_missing(x) for x in (_get(res, "missing") or [])],
        win=_get(res, "win"),
        busy=list(_get(res, "busy") or []),
    )


def invalidate_turn_views(turn_id: UUID) -> None:
    mod = _module("app.integrations.hands.records")
    fn = getattr(mod, "invalidate_turn_views", None) if mod else None
    if fn is not None:
        fn(turn_id)


def hands_client() -> Any | None:
    """El `HandsClient` del proceso (B3). Su acceso no está congelado: se prueban los nombres razonables."""
    mod = _module("app.integrations.hands.client")
    if mod is None:
        return None
    for name in ("get_hands_client", "get_client", "hands_client", "client", "CLIENT"):
        value = getattr(mod, name, None)
        if value is None:
            continue
        if callable(value) and not hasattr(value, "on_event"):
            try:
                value = value()
            except Exception:  # noqa: BLE001
                continue
        if value is not None and hasattr(value, "on_event"):
            return value
    return None


def on_hands_event(type: str, cb: Callable[[Any], None]) -> Callable[[], None] | None:
    client = hands_client()
    if client is None:
        return None
    return client.on_event(type, cb)


async def open_url(url: str) -> bool:
    """`open` del helper para un botón `open` pulsado por el usuario. La URL ya pasó `check_url`."""
    client = hands_client()
    if client is None:
        logger.info("hands helper unavailable: url not opened", extra={"event": "floating_open_unavailable"})
        return False
    from drakter_contracts.hands_ipc import HOpen

    await client.call("open", HOpen(url=url))
    return True


# ── voz (V1) ───────────────────────────────────────────────────────────────
_local_ids = itertools.count(1_000_000)


def reserve_speech_id(voice: Any) -> int:
    fn = getattr(voice, "reserve_speech_id", None)
    return int(fn()) if fn is not None else next(_local_ids)


async def speak_beat(voice: Any, turn_id: str, speech_id: int, guide_id: str, beat: int, text: str) -> bool:
    fn = getattr(voice, "speak_beat", None)
    if fn is None or not text:
        return False
    try:
        return bool(await fn(turn_id, speech_id, guide_id, beat, text))
    except Exception:  # noqa: BLE001 - sin voz, el overlay usa su reloj local
        logger.exception("speak_beat failed", extra={"event": "floating_speak_beat_failed"})
        return False
