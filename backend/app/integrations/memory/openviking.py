"""OpenViking adapter: a closed gap until E2.

OpenViking is not configured (no key, no server). The real calls are written in E2
against the API verified at that moment; no routes or payloads are assumed here.
Until then `status()` reports unavailable and every other operation raises
`MemoryBackendUnavailable`.
"""

from __future__ import annotations

from typing import Never
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


class MemoryBackendUnavailable(RuntimeError):
    """The memory backend is not configured or not reachable."""


class OpenVikingAdapter:
    def _unavailable(self) -> Never:
        raise MemoryBackendUnavailable("OpenViking no esta configurado")

    def status(self) -> BackendStatus:
        return BackendStatus(backend="openviking", available=False, detail="OpenViking no esta configurado")

    def create(self, draft: MemoryDraft, status: MemoryStatus, supersedes: UUID | None = None) -> MemoryRecord:
        self._unavailable()

    def get(self, memory_id: UUID) -> MemoryRecord | None:
        self._unavailable()

    def list(self, flt: MemoryFilter) -> tuple[list[MemoryRecord], int]:
        self._unavailable()

    def search(self, query: MemoryQuery) -> list[MemoryHit]:
        self._unavailable()

    def read(self, memory_id: UUID, level: DetailLevel) -> str | None:
        self._unavailable()

    def find_by_hash(self, content_hash: str) -> MemoryRecord | None:
        self._unavailable()

    def related(self, draft: MemoryDraft, limit: int = 20) -> list[MemoryRecord]:
        self._unavailable()

    def update(self, memory_id: UUID, patch: MemoryPatch, trust: TrustLevel | None = None) -> MemoryRecord | None:
        self._unavailable()

    def set_status(self, memory_id: UUID, status: MemoryStatus) -> MemoryRecord | None:
        self._unavailable()

    def delete(self, memory_id: UUID) -> ForgetReport | None:
        self._unavailable()

    def add_conflict(self, memory_a: UUID, memory_b: UUID, reason: str) -> MemoryConflict:
        self._unavailable()

    def list_conflicts(self, open_only: bool = True) -> list[MemoryConflict]:
        self._unavailable()

    def resolve_conflict(self, conflict_id: UUID, kept: UUID | None) -> MemoryConflict | None:
        self._unavailable()
