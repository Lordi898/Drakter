"""Chat history over the `conversations`, `agent_turns` and `messages` tables."""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypeVar
from uuid import UUID, uuid4

from drakter_contracts.common import format_instant
from pydantic import BaseModel

from app.database.connection import connect

MessageStatus = Literal["streaming", "complete", "cancelled", "failed"]
TurnStatus = Literal["completed", "failed", "cancelled", "interrupted"]
T = TypeVar("T")


class ChatSession(BaseModel):
    id: UUID
    title: str | None = None
    status: Literal["open", "closed"]
    created_at: str
    updated_at: str
    ended_at: str | None = None


class ChatMessage(BaseModel):
    id: UUID
    session_id: UUID
    turn_id: UUID | None
    role: Literal["user", "assistant", "system"]
    text: str
    status: MessageStatus
    created_at: str


class ActiveTurnExists(RuntimeError):
    """`ux_agent_turns_active` refused a second running turn."""


def now_instant() -> str:
    return format_instant(datetime.now(UTC))


_MESSAGE_COLUMNS = "id, conversation_id, turn_id, role, content, status, created_at"
_SESSION_COLUMNS = "id, title, created_at, updated_at, ended_at"


def _to_session(row: tuple) -> ChatSession:
    return ChatSession(
        id=row[0],
        title=row[1],
        status="closed" if row[4] else "open",
        created_at=row[2],
        updated_at=row[3],
        ended_at=row[4],
    )


def _to_message(row: tuple) -> ChatMessage:
    return ChatMessage(
        id=row[0],
        session_id=row[1],
        turn_id=row[2],
        role=row[3],
        text=row[4],
        status=row[5],
        created_at=row[6],
    )


class SqliteChatStore:
    """Synchronous sqlite3 in worker threads, with one connection per operation."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def _run(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        def call() -> T:
            conn = connect(self._db_path)
            try:
                return operation(conn)
            finally:
                conn.close()

        return await asyncio.to_thread(call)

    async def _transaction(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        def wrapped(conn: sqlite3.Connection) -> T:
            conn.execute("BEGIN IMMEDIATE")
            try:
                result = operation(conn)
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
            return result

        return await self._run(wrapped)

    async def recover_interrupted(self) -> int:
        """At boot nothing is running: whatever says so was cut short."""
        now = now_instant()

        def operation(conn: sqlite3.Connection) -> int:
            cursor = conn.execute(
                "UPDATE agent_turns SET status = 'interrupted', ended_at = ?, "
                "error_code = 'agent_disconnected' WHERE status = 'running'",
                (now,),
            )
            conn.execute("UPDATE messages SET status = 'failed' WHERE status = 'streaming'")
            return cursor.rowcount

        return await self._transaction(operation)

    async def create_session(self, session_id: UUID) -> ChatSession:
        now = now_instant()

        def operation(conn: sqlite3.Connection) -> ChatSession:
            conn.execute(
                "INSERT INTO conversations (id, hermes_session_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (str(session_id), str(session_id), now, now),
            )
            return ChatSession(id=session_id, status="open", created_at=now, updated_at=now)

        return await self._transaction(operation)

    async def get_session(self, session_id: UUID) -> ChatSession | None:
        def operation(conn: sqlite3.Connection) -> ChatSession | None:
            return self._select_session(conn, session_id)

        return await self._run(operation)

    @staticmethod
    def _select_session(conn: sqlite3.Connection, session_id: UUID) -> ChatSession | None:
        row = conn.execute(
            f"SELECT {_SESSION_COLUMNS} FROM conversations WHERE id = ?", (str(session_id),)
        ).fetchone()
        return _to_session(row) if row else None

    async def list_sessions(self, limit: int, offset: int) -> tuple[list[ChatSession], int]:
        def operation(conn: sqlite3.Connection) -> tuple[list[ChatSession], int]:
            total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            rows = conn.execute(
                f"SELECT {_SESSION_COLUMNS} FROM conversations "
                "ORDER BY updated_at DESC, rowid DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [_to_session(row) for row in rows], total

        return await self._run(operation)

    async def close_session(self, session_id: UUID) -> ChatSession | None:
        now = now_instant()

        def operation(conn: sqlite3.Connection) -> ChatSession | None:
            conn.execute(
                "UPDATE conversations SET ended_at = ?, updated_at = ? "
                "WHERE id = ? AND ended_at IS NULL",
                (now, now, str(session_id)),
            )
            return self._select_session(conn, session_id)

        return await self._transaction(operation)

    async def list_messages(
        self, session_id: UUID, limit: int, offset: int
    ) -> tuple[list[ChatMessage], int]:
        def operation(conn: sqlite3.Connection) -> tuple[list[ChatMessage], int]:
            total = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (str(session_id),)
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT {_MESSAGE_COLUMNS} FROM messages WHERE conversation_id = ? "
                "ORDER BY created_at, rowid LIMIT ? OFFSET ?",
                (str(session_id), limit, offset),
            ).fetchall()
            return [_to_message(row) for row in rows], total

        return await self._run(operation)

    @staticmethod
    def _select_client_message(
        conn: sqlite3.Connection, session_id: UUID, client_message_id: UUID
    ) -> ChatMessage | None:
        row = conn.execute(
            f"SELECT {_MESSAGE_COLUMNS} FROM messages "
            "WHERE conversation_id = ? AND client_message_id = ?",
            (str(session_id), str(client_message_id)),
        ).fetchone()
        return _to_message(row) if row else None

    async def find_client_message(
        self, session_id: UUID, client_message_id: UUID
    ) -> ChatMessage | None:
        def operation(conn: sqlite3.Connection) -> ChatMessage | None:
            return self._select_client_message(conn, session_id, client_message_id)

        return await self._run(operation)

    async def begin_turn(
        self,
        session_id: UUID,
        turn_id: UUID,
        text: str,
        client_message_id: UUID | None,
        *,
        store_message: bool = True,
    ) -> tuple[ChatMessage, bool]:
        """Open the turn with its user message. False: duplicate of an earlier message.

        `store_message=False`: the text is already stored (a steer reopened as a turn).

        The caller already holds the process-wide turn slot, so a row still `running`
        is a leftover from a turn whose closing write failed, and it must not block.
        """
        now = now_instant()
        message = ChatMessage(
            id=uuid4(),
            session_id=session_id,
            turn_id=turn_id,
            role="user",
            text=text,
            status="complete",
            created_at=now,
        )

        def operation(conn: sqlite3.Connection) -> tuple[ChatMessage, bool]:
            if client_message_id is not None:
                existing = self._select_client_message(conn, session_id, client_message_id)
                if existing is not None:
                    return existing, False
            conn.execute(
                "UPDATE agent_turns SET status = 'interrupted', ended_at = ?, "
                "error_code = 'agent_disconnected' WHERE status = 'running'",
                (now,),
            )
            try:
                conn.execute(
                    "INSERT INTO agent_turns "
                    "(id, conversation_id, correlation_id, status, created_at, started_at) "
                    "VALUES (?, ?, ?, 'running', ?, ?)",
                    (str(turn_id), str(session_id), str(turn_id), now, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ActiveTurnExists from exc
            if store_message:
                self._insert_message(conn, message, client_message_id)
            return message, True

        return await self._transaction(operation)

    async def add_user_message(self, session_id: UUID, turn_id: UUID, text: str) -> ChatMessage:
        """A user message inside a running turn: an accepted voice correction (steer)."""
        message = ChatMessage(
            id=uuid4(),
            session_id=session_id,
            turn_id=turn_id,
            role="user",
            text=text,
            status="complete",
            created_at=now_instant(),
        )

        def operation(conn: sqlite3.Connection) -> None:
            self._insert_message(conn, message, None)

        await self._transaction(operation)
        return message

    async def start_assistant_message(self, session_id: UUID, turn_id: UUID) -> UUID:
        message = ChatMessage(
            id=uuid4(),
            session_id=session_id,
            turn_id=turn_id,
            role="assistant",
            text="",
            status="streaming",
            created_at=now_instant(),
        )

        def operation(conn: sqlite3.Connection) -> UUID:
            self._insert_message(conn, message, None)
            return message.id

        return await self._transaction(operation)

    async def finish_turn(
        self,
        turn_id: UUID,
        status: TurnStatus,
        error_code: str | None,
        message_id: UUID | None,
        text: str,
        message_status: MessageStatus,
    ) -> None:
        now = now_instant()

        def operation(conn: sqlite3.Connection) -> None:
            conn.execute(
                "UPDATE agent_turns SET status = ?, error_code = ?, ended_at = ? WHERE id = ?",
                (status, error_code, now, str(turn_id)),
            )
            if message_id is not None:
                conn.execute(
                    "UPDATE messages SET content = ?, status = ? WHERE id = ?",
                    (text, message_status, str(message_id)),
                )

        await self._transaction(operation)

    @staticmethod
    def _insert_message(
        conn: sqlite3.Connection, message: ChatMessage, client_message_id: UUID | None
    ) -> None:
        conn.execute(
            "INSERT INTO messages "
            "(id, conversation_id, turn_id, role, content, client_message_id, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(message.id),
                str(message.session_id),
                str(message.turn_id) if message.turn_id else None,
                message.role,
                message.text,
                str(client_message_id) if client_message_id else None,
                message.status,
                message.created_at,
            ),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (message.created_at, str(message.session_id)),
        )
