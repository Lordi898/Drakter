"""What the user actually heard before cutting Drakter off (V-32), and the turn prefix.

The voice process sends `heard_tail` (≤80) and `pending_head` (≤200) of the *spoken* text with
`voice.playback{interrupted}`. They are kept as-is, used once in the prefix of the next turn of
that session and then forgotten. Never stored in the DB, never in `chat.user_message`.
"""

from __future__ import annotations

import threading
from typing import Final
from uuid import UUID

VOICE_CHANNEL: Final = "[canal: voz]"
_MAX_TAIL: Final = 80
_MAX_HEAD: Final = 200


def _clean(text: str | None, limit: int) -> str:
    # Spoken text of Drakter's own answer; the quotes are ours, so take theirs out.
    return " ".join((text or "").replace("«", "").replace("»", "").split())[:limit]


class HeardNotes:
    def __init__(self) -> None:
        self._lock = threading.Lock()  # the prefix hook may run off the event loop
        self._notes: dict[UUID, str] = {}

    def record(self, session_id: UUID, heard_tail: str | None, pending_head: str | None) -> None:
        tail = _clean(heard_tail, _MAX_TAIL)
        head = _clean(pending_head, _MAX_HEAD)
        if not tail and not head:
            return
        note = f"[interrumpido tras: «{tail}»; pendiente sin decir: «{head}»]"
        with self._lock:
            self._notes[session_id] = note

    def prefix(self, session_id: UUID, source: str) -> str | None:
        """`AgentRuntime.add_turn_prefix` hook. The interruption note goes out once."""
        with self._lock:
            note = self._notes.pop(session_id, None)
        parts = [VOICE_CHANNEL] if source == "voice" else []
        if note:
            parts.append(note)
        return "\n".join(parts) if parts else None
