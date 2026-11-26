"""What a finished voice turn becomes (plan WP5): a new agent turn, a `steer`, nothing, or a
turn queued until the current one ends.

Voice only ever produces *user text*. Nothing said out loud approves anything: with a
confirmation pending Drakter says `confirm_on_screen` and the text is an ordinary turn (V-34).
Audit carries categories and counts, never the transcript.
"""

from __future__ import annotations

import asyncio
import logging
import re
import tomllib
import unicodedata
from collections.abc import Awaitable, Callable, Mapping
from functools import lru_cache
from typing import Final, Literal, Protocol
from uuid import UUID

from drakter_contracts.voice_ipc import EvtLocalCommand, EvtUserTurn

from app.integrations.voice.settings import REPO_ROOT

logger = logging.getLogger("drakter.voice.policy")

Decision = Literal["submitted", "steered", "queued", "dropped", "failed"]

# Single source: the closed lists of voice/conversation/layer0.es.toml (WP4). The backend reads
# the data, not the voice code: its venv does not see `voice/`, and it only needs `backchannel`.
_LAYER0_TOML: Final = REPO_ROOT / "voice" / "conversation" / "layer0.es.toml"
_WORD: Final = re.compile(r"[a-z0-9ñ]+")


def _normalize(text: str) -> list[str]:
    """Same rule as voice.conversation.layer0.normalize: lowercase, no accents nor signs."""
    t = unicodedata.normalize("NFKD", text.lower())
    return _WORD.findall("".join(c for c in t if not unicodedata.combining(c)))


@lru_cache(maxsize=1)
def _backchannel_words() -> frozenset[str]:
    try:
        raw = tomllib.loads(_LAYER0_TOML.read_text(encoding="utf-8"))
        return frozenset(w for x in raw["backchannel"]["words"] for w in _normalize(str(x)))
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        # Without the list nothing is dropped: every short turn reaches the agent.
        logger.error("Layer 0 lists not loaded",
                     extra={"event": "voice_layer0_missing", "error": type(exc).__name__})
        return frozenset()


def is_backchannel(text: str) -> bool:
    """`classify(text, …) == "backchannel"` with nobody awaiting an answer: every word is one."""
    tokens = _normalize(text)
    words = _backchannel_words()
    return bool(tokens) and bool(words) and all(t in words for t in tokens)


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
# (modo, utt_id) → resultado de publicar `ui.mode` (`app.services.ui_mode.request_ui_mode`).
UiModeFn = Callable[[Literal["jarvis", "drakter"], str], str]
# (avatar, layout, utt_id) → resultado de publicar `ui.appearance` (`request_ui_appearance`).
UiAppearanceFn = Callable[[str | None, str | None, str], str]


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
        ui_mode: UiModeFn | None = None,
        ui_appearance: UiAppearanceFn | None = None,
    ) -> None:
        self._runtime = runtime
        self._speech = speech
        self._audit = audit
        self._on_error = on_error
        self._bot_speaking = bot_speaking
        self._min_words = min_words
        self._ui_mode = ui_mode
        self._ui_appearance = ui_appearance
        self._queued: list[str] = []
        self._pending_confirmations: set[str] = set()
        self._reminded: set[str] = set()  # recordado ya en un turno de voz: una vez por acción
        self._lock = asyncio.Lock()  # one decision at a time: active_turn() must not race

    # ── confirmations (fed from the hub by the orchestrator) ────────────────
    def confirmation_requested(self, action_id: str) -> None:
        if action_id in self._pending_confirmations:
            return  # reanuncio del mismo action_id (Jobs, resync): ya se dijo
        self._pending_confirmations.add(action_id)
        self._reminded.add(action_id)
        self._speech.phrase("confirm_on_screen")

    def confirmation_resolved(self, action_id: str) -> None:
        self._pending_confirmations.discard(action_id)
        self._reminded.discard(action_id)

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
        # Voice already acted on it (layer 0); the backend keeps the trace and, for the UI mode
        # commands, asks the desktop to switch (`ui.mode`). Nothing here reaches the agent.
        meta: dict[str, object] = {"command": evt.command, "utt_id": evt.utt_id[:64]}
        if evt.command in ("ui_jarvis", "ui_drakter"):
            mode: Literal["jarvis", "drakter"] = "jarvis" if evt.command == "ui_jarvis" else "drakter"
            meta["ui"] = self._ui_mode(mode, evt.utt_id) if self._ui_mode else "unavailable"
        elif evt.command == "ui_appearance":
            meta.update({k: v for k, v in (("avatar", evt.avatar), ("layout", evt.layout)) if v})
            meta["ui"] = (
                self._ui_appearance(evt.avatar, evt.layout, evt.utt_id) if self._ui_appearance else "unavailable"
            )
        await self._audit("voice.local_command", meta)

    async def turn_ended(self) -> None:
        """Called after a terminal: a turn that could not steer runs now."""
        async with self._lock:
            await self._flush_queue()

    # ── internals ───────────────────────────────────────────────────────────
    async def _decide(self, text: str, overlap: str) -> Decision:
        if self._pending_confirmations - self._reminded:
            self._reminded |= self._pending_confirmations
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

