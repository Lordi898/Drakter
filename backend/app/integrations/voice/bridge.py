"""Agent → voice: the `TurnTap` (plan §4.6) and the single outbound command queue.

Every tap method is synchronous, never blocks and never raises: it only does `put_nowait`.
One task drains the queue in order and talks IPC, so `speech_id`/`seq` bookkeeping lives in a
single place and voice can never break a turn (V-19). With `voice_tts_enabled=false` no
`speak.*` leaves this module except `speak.stop{mute}`: it is the only silence point (V-29).

Logs carry ids and counts, never text.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final, Literal, Protocol
from uuid import UUID

logger = logging.getLogger("drakter.voice.bridge")

Source = Literal["text", "voice"]
Outcome = Literal["completed", "cancelled", "failed"]
Request = Callable[[str, Mapping[str, Any]], Awaitable[dict[str, Any]]]

_QUEUE_SIZE: Final = 4096
_SENTENCE_END: Final = re.compile(r"[.!?…](?=\s|$)|\n")
# monotonic per backend process (plan §4.2)
_speech_ids: Final = itertools.count(1)
# Herramientas del modo flotante que hablan con `speak.beat` (docs/floating/CONTRACT.md §10): al empezar,
# el tramo del turno se cierra en vez de partirse con `speak.flush`, y lo que diga el modelo después va
# en un tramo nuevo, detrás de los beats (FIFO por turno en la voz).
_BEAT_TOOLS: Final = frozenset({"draw", "guide_wait"})
_BEAT_TIMEOUT_S: Final = 5.0


def reserve_speech_id() -> int:
    """Un `speech_id` del mismo contador monótono que los tramos de respuesta."""
    return next(_speech_ids)


class TapObserver(Protocol):
    """Hooks for the orchestrator; run inside the drain task, in order."""

    def turn_started(self, turn_id: UUID, session_id: UUID, source: Source) -> None: ...
    def first_delta(self, turn_id: UUID) -> None: ...
    def turn_ended(self, turn_id: UUID, outcome: Outcome) -> None: ...


@dataclass
class _Speech:
    speech_id: int
    seq: int = 0
    chars: int = 0
    open: bool = True


@dataclass
class _Turn:
    session_id: UUID
    source: Source
    speech: _Speech | None = None
    got_delta: bool = False
    reopen: bool = False  # tras un `draw`/`guide_wait`: el siguiente delta abre un tramo nuevo


class VoiceBridge:
    def __init__(
        self,
        request: Request,
        *,
        tts_enabled: Callable[[], bool],
        max_chars_text: int,
        observer: TapObserver,
    ) -> None:
        self._request = request
        self._tts_enabled = tts_enabled
        self._max_chars_text = max_chars_text
        self._observer = observer
        self._queue: asyncio.Queue[tuple[str, tuple[Any, ...]]] = asyncio.Queue(_QUEUE_SIZE)
        self._turns: dict[UUID, _Turn] = {}
        # Sesión de los últimos turnos ya terminados: su audio sigue sonando tras el final del
        # turno y un corte (`voice.playback{interrupted}`) llega después.
        self._ended: dict[UUID, UUID] = {}
        self._task: asyncio.Task[None] | None = None

    # ── lifecycle ──────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._drain(), name="voice-bridge")

    async def aclose(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    # ── TurnTap (sync, non-blocking, never raises) ───────────────────────────
    def on_turn_started(self, turn_id: UUID, session_id: UUID, source: Source) -> None:
        self._put("started", turn_id, session_id, source)

    def on_raw_delta(self, turn_id: UUID, text: str) -> None:
        self._put("delta", turn_id, text)

    def on_tool_started(self, turn_id: UUID, tool: str) -> None:
        self._put("tool", turn_id, tool)

    def on_steered(self, turn_id: UUID, accepted: bool) -> None:
        self._put("steered", turn_id, accepted)

    def on_terminal(self, turn_id: UUID, outcome: Outcome) -> None:
        self._put("terminal", turn_id, outcome)

    # ── orchestrator side (same queue, so order holds) ──────────────────────
    def phrase(self, key: str, when: str = "now") -> None:
        self._put("phrase", key, when)

    def stop(self, reason: str) -> None:
        """`speak.stop` of whatever is sounding (`new_turn`, `user`, `barge_in`)."""
        self._put("stop", reason)

    def mute(self) -> None:
        """`voice_tts_enabled` went false: close every speech and stop the sound."""
        self._put("mute")

    def cut(self, speech_id: int) -> None:
        """Voice reported `playback{interrupted}`: stop feeding that speech."""
        self._put("cut", speech_id)

    def send(self, type: str, payload: Mapping[str, Any]) -> None:
        """Any other fire-and-forget command (`voice.config`)."""
        self._put("raw", type, dict(payload))

    async def beat(self, turn_id: str, speech_id: int, guide_id: str, beat: int, text: str) -> bool:
        """`speak.beat` por la misma cola (respeta el orden con el resto de `speak.*`).

        `True` si la voz lo aceptó (`ignored:false`). Nunca lanza: sin voz, `False`.
        """
        if not self._tts_enabled():
            return False
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        payload = {"turn_id": turn_id, "speech_id": speech_id, "guide_id": guide_id, "beat": beat, "text": text}
        self._put("beat", payload, future)
        try:
            return await asyncio.wait_for(asyncio.shield(future), _BEAT_TIMEOUT_S)
        except (TimeoutError, asyncio.CancelledError):
            if not future.done():
                future.cancel()
            return False

    def session_of(self, turn_id: UUID) -> UUID | None:
        turn = self._turns.get(turn_id)
        return turn.session_id if turn else self._ended.get(turn_id)

    def speech_turn(self, speech_id: int) -> UUID | None:
        for turn_id, turn in self._turns.items():
            if turn.speech is not None and turn.speech.speech_id == speech_id:
                return turn_id
        return None

    # ── internals ───────────────────────────────────────────────────────────
    def _put(self, op: str, *args: Any) -> None:
        try:
            self._queue.put_nowait((op, args))
        except Exception:  # noqa: BLE001 - QueueFull or anything else: drop, never raise
            logger.warning("Voice command dropped", extra={"event": "voice_cmd_dropped", "op": op})

    async def _drain(self) -> None:
        while True:
            op, args = await self._queue.get()
            try:
                await getattr(self, f"_do_{op}")(*args)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - voice never breaks a turn
                logger.warning(
                    "Voice command failed",
                    extra={"event": "voice_cmd_failed", "op": op, "error": type(exc).__name__},
                )

    async def _send(self, type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        try:
            return await self._request(type, payload)
        except Exception as exc:  # noqa: BLE001 - voice down or err{}: the turn goes on
            logger.info(
                "Voice command not delivered",
                extra={"event": "voice_cmd_undelivered", "type": type, "error": type_name(exc)},
            )
            return {}

    async def _open(self, turn_id: UUID, turn: _Turn) -> None:
        turn.speech = None
        if not self._tts_enabled():
            return
        speech = _Speech(next(_speech_ids))
        turn.speech = speech
        await self._send("speak.open", {"turn_id": str(turn_id), "speech_id": speech.speech_id})

    async def _close(self, turn: _Turn, outcome: Outcome) -> None:
        speech = turn.speech
        if speech is not None and speech.open:
            speech.open = False
            await self._send("speak.close", {"speech_id": speech.speech_id, "outcome": outcome})

    async def _do_started(self, turn_id: UUID, session_id: UUID, source: Source) -> None:
        turn = _Turn(session_id, source)
        self._turns[turn_id] = turn
        self._observer.turn_started(turn_id, session_id, source)
        await self._open(turn_id, turn)
        await self._send("turn.phase", {"turn_id": str(turn_id), "phase": "thinking"})

    async def _do_delta(self, turn_id: UUID, text: str) -> None:
        turn = self._turns.get(turn_id)
        if turn is None or not text:
            return
        if not turn.got_delta:
            turn.got_delta = True
            self._observer.first_delta(turn_id)
        if turn.reopen:
            turn.reopen = False
            await self._open(turn_id, turn)
        speech = turn.speech
        if speech is None or not speech.open:
            return
        capped = False
        if turn.source == "text":
            text, capped = self._cap(speech.chars, text)
        if text:
            speech.chars += len(text)
            result = await self._send(
                "speak.delta", {"speech_id": speech.speech_id, "seq": speech.seq, "text": text}
            )
            speech.seq += 1
            if result.get("ignored") is True:  # already cut on the voice side
                speech.open = False
                return
        if capped:  # V-30: the rest stays on screen
            await self._close(turn, "completed")
            await self._do_phrase("rest_on_screen", "now")

    def _cap(self, said: int, text: str) -> tuple[str, bool]:
        """Cut a written turn at the first sentence end past `max_chars_text` (hard stop at 2×)."""
        limit = self._max_chars_text
        if said + len(text) <= limit:
            return text, False
        match = _SENTENCE_END.search(text, max(0, limit - said))
        if match is not None:
            return text[: match.end()], True
        if said + len(text) > 2 * limit:
            return text[: max(0, 2 * limit - said)], True
        return text, False

    async def _do_tool(self, turn_id: UUID, tool: str) -> None:
        turn = self._turns.get(turn_id)
        if turn is None:
            return
        if tool in _BEAT_TOOLS:
            # Sin flush: el tramo de antes se cierra y lo que venga después suena tras los beats.
            if turn.speech is not None and turn.speech.open:
                await self._close(turn, "completed")
                turn.reopen = True
        elif turn.speech is not None and turn.speech.open:
            await self._send("speak.flush", {"speech_id": turn.speech.speech_id})
        await self._send(
            "turn.phase", {"turn_id": str(turn_id), "phase": "executing", "tool": tool[:64]}
        )

    async def _do_steered(self, turn_id: UUID, accepted: bool) -> None:
        turn = self._turns.get(turn_id)
        if turn is None or not accepted:
            return
        speech = turn.speech
        if speech is not None:
            speech.open = False
            await self._send("speak.stop", {"speech_id": speech.speech_id, "reason": "steered"})
        await self._open(turn_id, turn)  # same turn_id, new speech_id

    async def _do_terminal(self, turn_id: UUID, outcome: Outcome) -> None:
        turn = self._turns.pop(turn_id, None)
        if turn is not None:
            self._ended[turn_id] = turn.session_id
            while len(self._ended) > 8:
                self._ended.pop(next(iter(self._ended)))
        if turn is None:
            return
        await self._close(turn, outcome)
        await self._send("turn.phase", {"turn_id": str(turn_id), "phase": "done"})
        self._observer.turn_ended(turn_id, outcome)

    async def _do_phrase(self, key: str, when: str) -> None:
        if self._tts_enabled():
            await self._send("speak.phrase", {"key": key, "when": when})

    async def _do_stop(self, reason: str) -> None:
        if self._tts_enabled():
            await self._send("speak.stop", {"reason": reason})

    async def _do_mute(self) -> None:
        for turn in self._turns.values():
            if turn.speech is not None:
                turn.speech.open = False
        await self._send("speak.stop", {"reason": "mute"})

    async def _do_cut(self, speech_id: int) -> None:
        for turn in self._turns.values():
            if turn.speech is not None and turn.speech.speech_id == speech_id:
                turn.speech.open = False

    async def _do_beat(self, payload: dict[str, Any], future: asyncio.Future[bool]) -> None:
        accepted = False
        try:
            if self._tts_enabled():
                result = await self._send("speak.beat", payload)
                accepted = result.get("ignored") is False
        finally:
            if not future.done():
                future.set_result(accepted)

    async def _do_raw(self, type: str, payload: dict[str, Any]) -> None:
        await self._send(type, payload)


def type_name(exc: BaseException) -> str:
    return type(exc).__name__
