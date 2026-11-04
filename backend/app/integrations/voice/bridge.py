"""Voice <-> agent bridge.

A transcript is one conversation turn from the user, and that is all it can be:
this module never reads what the text says. Spoken approval does not exist.
Logs and audit carry lengths and times, never text.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections import deque
from collections.abc import AsyncIterator, Coroutine, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from app.integrations.voice.client import VoiceClient, VoiceIPCError, VoiceUnavailableError

if TYPE_CHECKING:
    from app.integrations.voice.service import AgentTurnPort, AuditPort, EventSink

logger = logging.getLogger("drakter.voice.bridge")

VOICE_EVENTS: Final = frozenset(
    {
        "voice.state_changed",
        "voice.mic_changed",
        "voice.wakeword_detected",
        "voice.listening_started",
        "voice.speech_started",
        "voice.speech_ended",
        "voice.listening_stopped",
        "voice.transcription_partial",
        "voice.transcription_completed",
        "voice.playback_started",
        "voice.playback_level",
        "voice.playback_stopped",
        "voice.playback_interrupted",
        "voice.metrics",
        "voice.error",
    }
)
_INTERRUPT_REASONS: Final = frozenset({"user", "barge_in", "new_turn"})
_MAX_ID_CHARS: Final = 128
_MAX_LANGUAGE_CHARS: Final = 16
# 4 bytes per character at most, so a chunk always fits the 256 KiB IPC line.
_MAX_SPEAK_CHARS: Final = 32_000
_CLOSED_TURNS: Final = 256


def _turn_id(payload: Mapping[str, object]) -> str | None:
    value = payload.get("turn_id")
    return value if isinstance(value, str) and 0 < len(value) <= _MAX_ID_CHARS else None


@dataclass
class _ActiveTurn:
    turn_id: str
    task: asyncio.Task[None]
    started: float
    spoken_chars: int = 0


class VoiceBridge:
    def __init__(
        self,
        client: VoiceClient,
        *,
        events: EventSink,
        agent: AgentTurnPort,
        audit: AuditPort,
    ) -> None:
        self._client = client
        self._events = events
        self._agent = agent
        self._audit = audit
        self._active: _ActiveTurn | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        # Turns that already started or were interrupted: a late or repeated
        # transcript must not open them again.
        self._closed: deque[str] = deque(maxlen=_CLOSED_TURNS)

    async def handle_event(self, name: str, payload: Mapping[str, object]) -> None:
        """Called in order by the client. Must not wait on IPC: that is what the tasks are for."""
        if name not in VOICE_EVENTS:
            return
        # Cutting the agent goes before anything that can be slow.
        if name == "voice.playback_interrupted":
            elapsed_ms, spoken = self._on_interrupted(payload)
            await self.publish(name, payload)
            await self._record(
                "voice.interrupted",
                {
                    "turn_id": _turn_id(payload),
                    "reason": reason
                    if (reason := payload.get("reason")) in _INTERRUPT_REASONS
                    else "unknown",
                    "turn_elapsed_ms": elapsed_ms,
                    "spoken_chars": spoken,
                },
            )
            return
        await self.publish(name, payload)
        if name == "voice.playback_level":
            return
        if name == "voice.listening_started":
            turn_id = _turn_id(payload)
            if self._active is not None and self._active.turn_id != turn_id:
                self.cancel_active()
        elif name == "voice.transcription_completed":
            self._on_transcription(payload)
        elif name == "voice.wakeword_detected":
            await self._record(
                "voice.wakeword_detected",
                {"turn_id": _turn_id(payload), "score": payload.get("score")},
            )
        elif name == "voice.mic_changed":
            await self._record(
                "voice.mic_changed",
                {
                    "enabled": payload.get("enabled") is True,
                    "capture_open": payload.get("capture_open") is True,
                },
            )

    def cancel_active(self) -> None:
        """Stop the agent task of the current turn, if there is one."""
        active, self._active = self._active, None
        if active is not None:
            active.task.cancel()

    async def aclose(self) -> None:
        self.cancel_active()
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def publish(self, name: str, payload: Mapping[str, object]) -> None:
        """A subscriber failing must not affect the turn."""
        try:
            await self._events.publish(name, payload, version=1, experimental=True)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Voice event not published",
                extra={"event": "voice_publish_failed", "error": type(exc).__name__},
            )

    async def _record(self, action: str, meta: Mapping[str, object]) -> None:
        try:
            await self._audit.record(action, meta)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Voice audit failed",
                extra={"event": "voice_audit_failed", "error": type(exc).__name__},
            )

    def _on_interrupted(self, payload: Mapping[str, object]) -> tuple[int | None, int | None]:
        turn_id = _turn_id(payload)
        if turn_id is not None:
            self._closed.append(turn_id)
        active = self._active
        if active is None or (turn_id is not None and active.turn_id != turn_id):
            return None, None
        self.cancel_active()
        return int((time.monotonic() - active.started) * 1000), active.spoken_chars

    def _on_transcription(self, payload: Mapping[str, object]) -> None:
        turn_id = _turn_id(payload)
        text = payload.get("text")
        if turn_id is None or not isinstance(text, str):
            logger.warning("Voice transcript invalid", extra={"event": "voice_transcript_invalid"})
            return
        if turn_id in self._closed:
            return
        self._closed.append(turn_id)
        self.cancel_active()
        if not text.strip():
            self._spawn(self._close_turn(turn_id))  # the manager is waiting for this turn
            return
        task = self._spawn(self._run_turn(turn_id, text, payload))
        self._active = _ActiveTurn(turn_id, task, time.monotonic())

    def _spawn(self, coroutine: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
        task = asyncio.create_task(coroutine, name="voice-turn")
        self._tasks.add(task)
        task.add_done_callback(self._forget)
        return task

    def _forget(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if self._active is not None and self._active.task is task:
            self._active = None

    async def _run_turn(self, turn_id: str, text: str, payload: Mapping[str, object]) -> None:
        language = payload.get("language")
        try:
            # Fails closed: a turn the audit log cannot record does not reach the agent.
            await self._audit.record(
                "voice.turn_started",
                {
                    "turn_id": turn_id,
                    "text_chars": len(text),
                    "audio_ms": payload.get("audio_ms"),
                    "language": language[:_MAX_LANGUAGE_CHARS]
                    if isinstance(language, str)
                    else None,
                },
            )
            stream = self._agent.submit_user_turn(text, turn_id=turn_id, source="voice")
            if inspect.isawaitable(stream):  # coroutine or async generator: both are valid ports
                stream = await stream
            await self._forward(turn_id, stream)
        except Exception as exc:  # noqa: BLE001 - nothing an agent raises may reach the voice loop
            logger.error(
                "Voice turn failed",
                extra={"event": "voice_turn_failed", "error": type(exc).__name__},
            )
            await self.publish(
                "voice.error",
                {
                    "code": "agent_failed",
                    "stage": "agent",
                    "message": "The agent could not complete this turn",
                    "recoverable": True,
                    "turn_id": turn_id,
                },
            )
            await self._close_turn(turn_id)

    async def _forward(self, turn_id: str, stream: AsyncIterator[str]) -> None:
        try:
            async for delta in stream:
                if not isinstance(delta, str) or not delta:
                    continue
                for start in range(0, len(delta), _MAX_SPEAK_CHARS):
                    chunk = delta[start : start + _MAX_SPEAK_CHARS]
                    result = await self._speak(turn_id, chunk, final=False)
                    if result.get("ignored") is True:  # interrupted on the voice side
                        return
                    if self._active is not None and self._active.turn_id == turn_id:
                        self._active.spoken_chars += len(chunk)
            await self._speak(turn_id, "", final=True)
        finally:
            aclose = getattr(stream, "aclose", None)
            if aclose is not None:
                await aclose()

    async def _speak(self, turn_id: str, text: str, *, final: bool) -> dict[str, Any]:
        return await self._client.request(
            "speak", {"turn_id": turn_id, "text": text, "final": final}
        )

    async def _close_turn(self, turn_id: str) -> None:
        """An empty final `speak` takes the manager from `waiting` back to `idle`."""
        try:
            await self._speak(turn_id, "", final=True)
        except (VoiceIPCError, VoiceUnavailableError) as exc:
            logger.warning(
                "Voice turn not closed",
                extra={"event": "voice_turn_not_closed", "error": type(exc).__name__},
            )
