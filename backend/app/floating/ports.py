"""Puertos del DrawRunner hacia B3 (pantalla y manos) y V1 (voz), detrás de sus firmas congeladas
(docs/floating/CONTRACT.md §8.1 bis, §9.2 y §10).

B3: `app.integrations.hands.resolve.resolve_marks`, `records.invalidate_turn_views` y el `HandsClient` del
proceso (`client.current_client()` para escuchar eventos, `client.ensure_client()` para mandar `open`).
V1: `VoiceOrchestrator.reserve_speech_id` y `speak_beat`, que llegan como `state.voice`.
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from drakter_contracts.floating import FLOATING_TOOL_ERRORS, MissingTarget

from app.integrations.hands import client as hands
from app.integrations.hands import records
from app.integrations.hands import resolve as hands_resolve
from app.tools.spec import ToolError

logger = logging.getLogger("drakter.floating.ports")

# Códigos del helper que `draw` declara; el resto se informa como `companion_unavailable`.
_DRAW_HANDS_ERRORS = ("companion_unavailable", "stale_screenshot", "stale_read")


@dataclass
class Seg:
    """`ResolvedSeg` de §9.2, normalizado."""

    beats: list[dict[str, Any]]
    missing: list[MissingTarget] = field(default_factory=list)
    win: list[float] | None = None
    busy: list[list[float]] = field(default_factory=list)


async def resolve_marks(beats: list[dict[str, Any]], *, target: str, turn_id: UUID, after_wait: bool) -> Seg:
    try:
        res = await hands_resolve.resolve_marks(beats, target=target, turn_id=turn_id, after_wait=after_wait)
    except hands.HandsError as exc:
        code = exc.code if exc.code in _DRAW_HANDS_ERRORS else "companion_unavailable"
        raise ToolError(code, FLOATING_TOOL_ERRORS[code]) from None
    return Seg(beats=list(res.beats), missing=list(res.missing), win=res.win, busy=list(res.busy))


def invalidate_turn_views(turn_id: UUID) -> None:
    records.invalidate_turn_views(turn_id)


def hands_client() -> hands.HandsClient | None:
    """El `HandsClient` del proceso si ya arrancó (lo arranca `ensure_client()` en el primer uso)."""
    return hands.current_client()


def on_hands_event(type: str, cb: Callable[[Any], None]) -> Callable[[], None] | None:
    client = hands_client()
    if client is None:
        return None
    return client.on_event(type, cb)


async def open_url(url: str) -> bool:
    """`open` del helper para un botón `open` pulsado por el usuario. La URL ya pasó `check_url`."""
    from drakter_contracts.hands_ipc import HOpen

    try:
        client = await hands.ensure_client()
        await client.call("open", HOpen(url=url))
    except hands.HandsError as exc:
        logger.info("hands helper unavailable: url not opened",
                    extra={"event": "floating_open_unavailable", "code": exc.code})
        return False
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
