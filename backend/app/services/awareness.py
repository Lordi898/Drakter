"""Live context for each turn: the machine, a hardware change, and where the conversation is.

`AwarenessService.prefix` is an `AgentRuntime.add_turn_prefix` hook, so its lines reach only
the turn prompt: never the system prompt (byte-stable, V-21), never the database, never the
chat. It must be quick, because it runs on the event loop when a message is submitted: a
read-only SQLite query and a few reads of /proc and /sys. The hardware probe itself runs in
a thread (`HardwareTracker.refresh_if_stale`).

Chat titles are the user's words: they go in «», clipped and without invisible characters,
and the agent reads the messages themselves only through `chat_history` tools, which return
them as untrusted data.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.text import strip_invisible
from app.repositories.notifications_due import default_timezone
from app.services.hardware import HardwareTracker, change_line, live, summary_line

logger = logging.getLogger("drakter.awareness")

FALLBACK_TIMEZONE: Final = "Europe/Madrid"
CHANGE_NOTICE_S: Final = 72 * 3600  # a change is announced to the sessions of the next 3 days
TITLE_MAX: Final = 60
_MONTHS: Final = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip

STARTED_AT: Final = datetime.now(UTC)
STARTED_MONOTONIC: Final = time.monotonic()


def parse_instant(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def clip_title(raw: str | None) -> str | None:
    if not raw:
        return None
    text = " ".join(strip_invisible(raw).replace("«", "").replace("»", "").split())
    if not text:
        return None
    return text if len(text) <= TITLE_MAX else text[: TITLE_MAX - 1] + "…"


def ago(delta: timedelta) -> str:
    seconds = max(0, int(delta.total_seconds()))
    if seconds < 90:
        return "hace un momento"
    minutes = seconds // 60
    if minutes < 60:
        return f"hace {minutes} min"
    hours, rest = divmod(minutes, 60)
    if hours < 24:
        return f"hace {hours} h" + (f" {rest} min" if rest and hours < 3 else "")
    days = hours // 24
    return "hace 1 día" if days == 1 else f"hace {days} días"


def local_day(moment: datetime, now: datetime) -> str:
    """«hoy a las 09:12», «ayer a las 22:40», «el 25 de noviembre» (same zone for both)."""
    if moment.date() == now.date():
        return f"hoy a las {moment:%H:%M}"
    if moment.date() == (now - timedelta(days=1)).date():
        return f"ayer a las {moment:%H:%M}"
    text = f"el {moment.day} de {_MONTHS[moment.month - 1]}"
    return text if moment.year == now.year else f"{text} de {moment.year}"


class AwarenessService:
    def __init__(self, db_path: Path, tracker: HardwareTracker, *, clock: Callable[[], datetime] | None = None) -> None:
        self._db_path = db_path
        self.tracker = tracker
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()
        self._announced: set[tuple[UUID, str]] = set()  # (session, change detected_at)

    # The hook ------------------------------------------------------------------

    def prefix(self, session_id: UUID, source: str) -> str | None:
        lines: list[str] = []
        for part in (self._machine_lines, self._conversation_line):
            try:
                lines.extend(part(session_id))
            except Exception as exc:  # noqa: BLE001 - one missing line beats a broken turn
                logger.warning("awareness line failed", extra={"event": "awareness_failed", "kind": type(exc).__name__})
        return "\n".join(lines) if lines else None

    # Machine ---------------------------------------------------------------------

    def _machine_lines(self, session_id: UUID) -> list[str]:
        self.tracker.refresh_if_stale()
        profile = self.tracker.profile
        if profile is None:
            return []
        lines = [summary_line(profile, live(self.tracker.data_dir))]
        change = self.tracker.change
        detected = parse_instant(change.detected_at) if change else None
        if change and detected and (self._clock() - detected).total_seconds() < CHANGE_NOTICE_S:
            key = (session_id, change.detected_at)
            with self._lock:
                fresh = key not in self._announced
                self._announced.add(key)
            if fresh:
                lines.append(change_line(change))
        return lines

    # Conversation ----------------------------------------------------------------

    def zone(self, conn: sqlite3.Connection) -> ZoneInfo:
        try:
            return ZoneInfo(default_timezone(conn) or FALLBACK_TIMEZONE)
        except (ZoneInfoNotFoundError, ValueError, sqlite3.Error):
            return ZoneInfo(FALLBACK_TIMEZONE)

    def _conversation_line(self, session_id: UUID) -> list[str]:
        sid = str(session_id)
        with sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True, timeout=1) as conn:
            zone = self.zone(conn)
            row = conn.execute("SELECT created_at FROM conversations WHERE id = ?", (sid,)).fetchone()
            if row is None:
                return []
            users = conn.execute(
                "SELECT count(*) FROM messages WHERE conversation_id = ? AND role = 'user'", (sid,)
            ).fetchone()[0]
            previous = conn.execute(
                "SELECT created_at FROM messages WHERE conversation_id = ? "
                "ORDER BY created_at DESC, rowid DESC LIMIT 1 OFFSET 1",
                (sid,),
            ).fetchone()
            others = conn.execute("SELECT count(*) FROM conversations WHERE id != ?", (sid,)).fetchone()[0]
            latest = conn.execute(
                "SELECT title, updated_at FROM conversations WHERE id != ? ORDER BY updated_at DESC LIMIT 1",
                (sid,),
            ).fetchone()
        now = self._clock().astimezone(zone)
        started = parse_instant(row[0])
        parts: list[str] = []
        if users <= 1:
            parts.append("primer mensaje de una conversación nueva")
        else:
            text = f"mensaje {users} de esta conversación"
            if started:
                text += f", empezada {local_day(started.astimezone(zone), now)}"
            parts.append(text)
            last = parse_instant(previous[0]) if previous else None
            if last:
                parts.append(f"el mensaje anterior fue {ago(now - last)}")
        if others:
            text = f"{others} conversación anterior" if others == 1 else f"{others} conversaciones anteriores"
            when = parse_instant(latest[1]) if latest else None
            title = clip_title(latest[0]) if latest else None
            if when:
                text += f"; la más reciente, {'«' + title + '», ' if title else ''}{local_day(when.astimezone(zone), now)}"
            parts.append(text + " (consúltalas con list_chat_sessions o search_chat_history si hacen falta)")
        else:
            parts.append("no hay conversaciones anteriores")
        return ["[conversación: " + "; ".join(parts) + "]"]
