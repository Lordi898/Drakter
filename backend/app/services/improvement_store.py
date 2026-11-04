"""SQLite access shared by the improvement services.

No statement here or in its callers may use `INSERT OR REPLACE`: it would slip
past the immutability triggers.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable, Iterator, Mapping
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

from app.core.errors import AppError
from app.database.connection import connect
from app.services.improvement_ports import AuditEvent, AuditSink, Principal

logger = logging.getLogger("drakter.improvement")

_TS_FORMAT: Final = "%Y-%m-%dT%H:%M:%S.%fZ"


def format_ts(value: datetime) -> str:
    """Fixed-width UTC text, so comparing strings compares instants."""
    return value.astimezone(UTC).strftime(_TS_FORMAT)


def utc_now() -> str:
    return format_ts(datetime.now(UTC))


def new_id() -> str:
    return str(uuid4())


@contextmanager
def open_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        yield conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def insert_event(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    actor: Principal,
    proposal_id: str | None = None,
    feedback_id: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    detail: Mapping[str, str | int | bool | None] | None = None,
) -> None:
    """Append to the changelog. ``detail`` carries only ids, hashes and states."""
    conn.execute(
        "INSERT INTO improvement_events (id, proposal_id, feedback_id, event_type,"
        " from_status, to_status, actor_kind, actor_id, detail, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            new_id(),
            proposal_id,
            feedback_id,
            event_type,
            from_status,
            to_status,
            actor.kind,
            actor.id,
            json.dumps(dict(detail or {}), sort_keys=True),
            utc_now(),
        ),
    )


def page(items: list[dict[str, Any]], total: int, limit: int, offset: int) -> dict[str, Any]:
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@dataclass
class AuditScope:
    """Filled in by the audited block. ``failed`` marks a 4xx that was no denial."""

    detail: dict[str, str | int | bool | None] = field(default_factory=dict)
    failed: bool = False
    attempted: bool = False
    record_attempt: Callable[[], None] = lambda: None

    def attempt(self) -> None:
        """Audit the intent before an effect. If this raises, the effect must not run."""
        self.record_attempt()
        self.attempted = True


@contextmanager
def audited(
    audit: AuditSink,
    actor: Principal,
    action: str,
    entity_type: str,
    entity_id: str,
    correlation_id: str | None,
) -> Iterator[AuditScope]:
    """Record one audit event per act, including denials and failures."""
    scope = AuditScope()

    def write(result: Any, **extra: str) -> None:
        audit.record(
            AuditEvent(
                actor_type=actor.kind,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                result=result,
                correlation_id=correlation_id,
                detail={**scope.detail, **extra},
            )
        )

    def record(result: Any, **extra: str) -> None:
        """After an attempted effect the outcome stands: a sink failure is only logged."""
        try:
            write(result, **extra)
        except Exception as exc:
            if not scope.attempted:
                raise
            logger.error(
                "audit_outcome_lost",
                extra={
                    "event": "audit_outcome_lost",
                    "action": action,
                    "entity_id": entity_id,
                    "result": result,
                    "error_type": type(exc).__name__,
                },
            )

    scope.record_attempt = lambda: write("attempted")
    try:
        yield scope
    except AppError as exc:
        failed = scope.failed or exc.status_code >= 500
        record("failed" if failed else "denied", code=exc.code)
        raise
    except Exception:
        record("failed", code="internal_error")
        raise
    record("ok")
