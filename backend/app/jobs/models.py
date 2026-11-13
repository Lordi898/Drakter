"""Fila de `jobs` en memoria y su conversión a los modelos del contrato."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final
from uuid import UUID

from drakter_contracts.common import format_instant
from drakter_contracts.jobs import JobOut, JobState, JobStatusItem

SUMMARY_MAX: Final = 8000
REASON_MAX: Final = 200


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(moment: datetime | None) -> str | None:
    return format_instant(moment) if moment is not None else None


@dataclass(slots=True)
class Job:
    id: UUID
    session_id: UUID
    lane: str
    title: str
    brief: str
    parent_session_id: UUID | None = None
    state: JobState = JobState.RUNNING
    reason: str | None = None
    summary: str | None = None
    tainted: bool = False
    tool_calls: int = 0
    last_tool: str | None = None
    pending_actions: int = 0
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def running(self) -> bool:
        return self.state is JobState.RUNNING

    def elapsed_s(self, now: datetime | None = None) -> int:
        start = self.started_at or self.created_at
        end = self.finished_at or now or utc_now()
        return max(0, int((end - start).total_seconds()))

    def out(self) -> JobOut:
        return JobOut(
            job_id=self.id,
            title=self.title,
            state=self.state,
            reason=self.reason,
            pending_actions=self.pending_actions,
            created_at=self.created_at,
            finished_at=self.finished_at,
            elapsed_s=self.elapsed_s(),
            tool_calls=self.tool_calls,
            last_tool=self.last_tool,
        )

    def status_item(self) -> JobStatusItem:
        return JobStatusItem(
            job_id=self.id,
            title=self.title,
            state=self.state,
            elapsed_s=self.elapsed_s(),
            tool_calls=self.tool_calls,
            last_tool=self.last_tool,
            pending_actions=self.pending_actions,
        )
