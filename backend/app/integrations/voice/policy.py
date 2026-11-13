"""What a finished voice turn becomes (plan WP5): a new agent turn, a `steer`, nothing, or a
turn queued until the current one ends.

Voice only ever produces *user text*. Nothing said out loud approves anything: with a
confirmation pending Drakter says `confirm_on_screen` and the text is an ordinary turn (V-34).
Audit carries categories and counts, never the transcript.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Final, Literal, Protocol
from uuid import UUID

from drakter_contracts.voice_ipc import EvtLocalCommand, EvtUserTurn

logger = logging.getLogger("drakter.voice.policy")

Decision = Literal["submitted", "steered", "queued", "dropped", "failed"]

# Used only if voice/conversation/layer0.py (WP4) cannot be imported in the backend venv.
_FALLBACK_BACKCHANNELS: Final = frozenset(
    {"vale", "ok", "okay", "sí", "si", "ajá", "aja", "ya", "claro", "mhm", "mm", "eh", "ah",
     "entiendo", "genial", "perfecto", "bien", "vale vale", "sí sí", "ya ya"}
)


def _load_classify() -> Callable[[str, bool, bool], str | None] | None:
    try:
        from voice.conversation.layer0 import classify  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001 - backend venv may not see voice/; fall back
        return None
    return classify


_classify = _load_classify()


def is_backchannel(text: str) -> bool:
    if _classify is not None:
        try:
            return _classify(text, False, False) == "backchannel"
        except Exception:  # noqa: BLE001
            pass
    norm = " ".join(text.lower().strip(" .,!?¡¿…").split())
    return norm in _FALLBACK_BACKCHANNELS


class ActiveTurn(Protocol):
    turn_id: UUID
    session_id: UUID


class RuntimePort(Protocol):
    """Subset of `AgentRuntime` (plan §4.6) used by voice."""

    async def submit_message(
        self, session_id: UUID, text: str, client_message_id: UUID | None, *,
        source: Literal["text", "voice"] = "text",
    ) -> tuple[UUID, UUID]: ...
    async def current_session(self) -> UUID: ...
    async def steer(self, turn_id: UUID, text: str) -> bool: ...
    def active_turn(self) -> ActiveTurn | None: ...


class SpeechPort(Protocol):
    def phrase(self, key: str, when: str = "now") -> None: ...
    def stop(self, reason: str) -> None: ...


AuditFn = Callable[[str, Mapping[str, object]], Awaitable[None]]
ErrorFn = Callable[[str], None]


class VoicePolicy:
    def __init__(
        self,
        runtime: RuntimePort,
        speech: SpeechPort,
        *,
        audit: AuditFn,
        on_error: ErrorFn,
        bot_speaking: Callable[[], bool],
        min_words: int,
    ) -> None:
        self._runtime = runtime
        self._speech = speech
        self._audit = audit
        self._on_error = on_error
        self._bot_speaking = bot_speaking
        self._min_words = min_words
        self._queued: list[str] = []
        self._pending_confirmations: set[str] = set()
        self._lock = asyncio.Lock()  # one decision at a time: active_turn() must not race

    # ── confirmations (fed from the hub by the orchestrator) ────────────────
    def confirmation_requested(self, action_id: str) -> None:
        self._pending_confirmations.add(action_id)
        self._speech.phrase("confirm_on_screen")

    def confirmation_resolved(self, action_id: str) -> None:
        self._pending_confirmations.discard(action_id)

    # ── events from voice ───────────────────────────────────────────────────
    async def user_turn(self, evt: EvtUserTurn) -> Decision:
        text = evt.text.strip()
        decision: Decision = "dropped"
        if text:
            async with self._lock:
                decision = await self._decide(text, evt.overlap)
        await self._audit(
            "voice.user_turn",
            {
                "utt_id": evt.utt_id[:64],
                "trigger": evt.trigger,
                "overlap": evt.overlap,
                "text_chars": len(text),
                "words": len(text.split()),
                "decision": decision,
                "audio_ms": evt.audio_ms,
            },
        )
        return decision

    async def local_command(self, evt: EvtLocalCommand) -> None:
        # Voice already acted on it (layer 0); the backend only keeps the trace.
        await self._audit("voice.local_command", {"command": evt.command, "utt_id": evt.utt_id[:64]})

    async def turn_ended(self) -> None:
        """Called after a terminal: a turn that could not steer runs now."""
        async with self._lock:
            await self._flush_queue()

    # ── internals ───────────────────────────────────────────────────────────
    async def _decide(self, text: str, overlap: str) -> Decision:
        if self._pending_confirmations:
            self._speech.phrase("confirm_on_screen")
        active = self._runtime.active_turn()
        if active is None:
            if self._bot_speaking():
                self._speech.stop("new_turn")
            return await self._submit(text)
        if is_backchannel(text) or (
            overlap == "agent_busy" and len(text.split()) < self._min_words
        ):
            return "dropped"
        try:
            if await self._runtime.steer(active.turn_id, text):
                return "steered"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Voice steer failed", extra={"event": "voice_steer_failed",
                                                        "error": type(exc).__name__})
        self._queued.append(text)
        if self._runtime.active_turn() is None:  # it ended while we were steering
            await self._flush_queue()
            return "submitted"
        return "queued"

    async def _flush_queue(self) -> None:
        if not self._queued or self._runtime.active_turn() is not None:
            return
        text, self._queued = "\n".join(self._queued), []
        await self._submit(text)

    async def _submit(self, text: str) -> Decision:
        try:
            session_id = await self._runtime.current_session()
            await self._runtime.submit_message(session_id, text, None, source="voice")
            return "submitted"
        except Exception as exc:  # noqa: BLE001 - AppError (busy, offline) or anything else
            code = getattr(exc, "code", None)
            if code == "agent_busy":
                self._queued.append(text)
                return "queued"
            logger.warning("Voice turn not submitted", extra={"event": "voice_submit_failed",
                                                              "error": type(exc).__name__})
            self._speech.phrase("offline")
            self._on_error("agent_unavailable")
            return "failed"

