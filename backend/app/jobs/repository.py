"""SQL de `jobs`. Único sitio que escribe la tabla. Funciones síncronas: se llaman con `to_thread`."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Final
from uuid import UUID

from drakter_contracts.jobs import JobState

from app.database.connection import connect
from app.jobs.models import Job, iso

_COLUMNS: Final = (
    "id, parent_session_id, session_id, lane, title, brief, state, reason, summary, tainted, "
    "tool_calls, last_tool, pending_actions, created_at, started_at, finished_at"
)


def _uuid(value: str | None) -> UUID | None:
    return UUID(value) if value else None


def _instant(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=UUID(row["id"]),
        parent_session_id=_uuid(row["parent_session_id"]),
        session_id=UUID(row["session_id"]),
        lane=row["lane"],
        title=row["title"],
        brief=row["brief"],
        state=JobState(row["state"]),
        reason=row["reason"],
        summary=row["summary"],
        tainted=bool(row["tainted"]),
        tool_calls=row["tool_calls"],
        last_tool=row["last_tool"],
        pending_actions=row["pending_actions"],
        created_at=_instant(row["created_at"]),  # type: ignore[arg-type]
        started_at=_instant(row["started_at"]),
        finished_at=_instant(row["finished_at"]),
    )


def _open(db_path: Path) -> sqlite3.Connection:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def insert(db_path: Path, job: Job) -> None:
    conn = _open(db_path)
    try:
        with conn:
            conn.execute(
                f"INSERT INTO jobs ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(job.id), str(job.parent_session_id) if job.parent_session_id else None,
                    str(job.session_id), job.lane, job.title, job.brief, job.state.value,
                    job.reason, job.summary, int(job.tainted), job.tool_calls, job.last_tool,
                    job.pending_actions, iso(job.created_at), iso(job.started_at),
                    iso(job.finished_at),
                ),
            )  # fmt: skip
    finally:
        conn.close()


def update(db_path: Path, job: Job) -> None:
    """Persiste lo que cambia durante la vida del trabajo."""
    conn = _open(db_path)
    try:
        with conn:
            conn.execute(
                "UPDATE jobs SET state = ?, reason = ?, summary = ?, tainted = ?, tool_calls = ?, "
                "last_tool = ?, pending_actions = ?, started_at = ?, finished_at = ? WHERE id = ?",
                (
                    job.state.value, job.reason, job.summary, int(job.tainted), job.tool_calls,
                    job.last_tool, job.pending_actions, iso(job.started_at), iso(job.finished_at),
                    str(job.id),
                ),
            )  # fmt: skip
    finally:
        conn.close()


def get(db_path: Path, job_id: UUID) -> Job | None:
    conn = _open(db_path)
    try:
        row = conn.execute(f"SELECT {_COLUMNS} FROM jobs WHERE id = ?", (str(job_id),)).fetchone()
    finally:
        conn.close()
    return _row_to_job(row) if row is not None else None


def recent(db_path: Path, limit: int = 50) -> list[Job]:
    conn = _open(db_path)
    try:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_job(row) for row in rows]


def fail_orphans(db_path: Path, finished_at: datetime, reason: str) -> int:
    """Al arrancar: un trabajo `running` de un proceso anterior ya no tiene runner."""
    conn = _open(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE jobs SET state = 'failed', reason = ?, finished_at = ? WHERE state = 'running'",
                (reason, iso(finished_at)),
            )
        return cursor.rowcount
    finally:
        conn.close()
