"""Frozen interfaces for Drakter memory. See CONTRACT.md."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from app.integrations.memory.models import (
    BackendStatus,
    DetailLevel,
    ForgetReport,
    MemoryConflict,
    MemoryDraft,
    MemoryFilter,
    MemoryHit,
    MemoryPatch,
    MemoryQuery,
    MemoryRecord,
    MemoryStatus,
    TrustLevel,
)


@runtime_checkable
class MemoryAdapter(Protocol):
    """Storage behind the service. Implementations do not decide status or policy."""

    def status(self) -> BackendStatus: ...

    def create(self, draft: MemoryDraft, status: MemoryStatus, supersedes: UUID | None = None) -> MemoryRecord: ...

    def get(self, memory_id: UUID) -> MemoryRecord | None: ...

    def list(self, flt: MemoryFilter) -> tuple[list[MemoryRecord], int]: ...  # (page, total)

    def search(self, query: MemoryQuery) -> list[MemoryHit]:
        """Only APPROVED records whose valid_until has not passed."""
        ...

    def read(self, memory_id: UUID, level: DetailLevel) -> str | None:
        """Text at that level, only for APPROVED unexpired records; None otherwise."""
        ...

    def find_by_hash(self, content_hash: str) -> MemoryRecord | None: ...

    def related(self, draft: MemoryDraft, limit: int = 20) -> list[MemoryRecord]:
        """PENDING or APPROVED records with the same subject or near text, for dedup and conflicts."""
        ...

    def update(self, memory_id: UUID, patch: MemoryPatch, trust: TrustLevel | None = None) -> MemoryRecord | None:
        """`trust` is set by the service only; it is not part of the client-facing patch."""
        ...

    def set_status(self, memory_id: UUID, status: MemoryStatus) -> MemoryRecord | None: ...

    def delete(self, memory_id: UUID) -> ForgetReport | None:
        """Hard delete of the record and its index entries; conflicts that cite it go too."""
        ...

    def add_conflict(self, memory_a: UUID, memory_b: UUID, reason: str) -> MemoryConflict: ...

    def list_conflicts(self, open_only: bool = True) -> list[MemoryConflict]: ...

    def resolve_conflict(self, conflict_id: UUID, kept: UUID | None) -> MemoryConflict | None: ...


class Extractor(Protocol):
    """Finds candidate memories in a text. Rule based now, model based later."""

    def extract(self, text: str, source: MemoryDraftSeed) -> list[MemoryDraft]: ...


@dataclass(frozen=True)
class MemoryDraftSeed:
    """Provenance data the extractor copies into every draft."""

    source_type: str  # SourceType value
    source_ref: str | None = None
    session_id: str | None = None


class ConfirmationGate(Protocol):
    """Backend-enforced confirmation. drakter/seguridad supplies the real one."""

    def verify(self, action: str, target: str, confirmation_id: str | None) -> bool:
        """True only if the GUI approved exactly this action on this target."""
        ...


class DenyAllGate:
    """Fail closed until the real gate is wired."""

    def verify(self, action: str, target: str, confirmation_id: str | None) -> bool:
        return False


class AuditSink(Protocol):
    """Audit of agent and memory actions. Never receives memory content or secrets."""

    def record(self, *, action: str, actor: str, target: str, outcome: str,
               detail: dict[str, Any] | None = None) -> None: ...

    def record_retrieval(self, query_hash: str, ids: Sequence[UUID], tainted: bool) -> None: ...
