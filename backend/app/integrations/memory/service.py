"""Memory policy: initial status, approval, conflicts and forgetting. See CONTRACT.md."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.core.text import strip_invisible
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
    Provenance,
    SourceType,
    TrustLevel,
)
from app.integrations.memory.pipeline.conflicts import find_contradictions
from app.integrations.memory.pipeline.dedupe import find_duplicate
from app.integrations.memory.pipeline.extract import contains_secret
from app.integrations.memory.ports import (
    AuditSink,
    ConfirmationGate,
    Extractor,
    MemoryAdapter,
    MemoryDraftSeed,
)
from app.integrations.memory.store_sqlite import content_hash

USER = "user"
AGENT = "agent"
_THIRD_PARTY_SOURCES = frozenset({SourceType.DOCUMENT, SourceType.TOOL_RESULT, SourceType.IMPORT})


@dataclass(frozen=True)
class IngestResult:
    record: MemoryRecord | None
    duplicate_of: UUID | None = None
    conflicts: list[MemoryConflict] = field(default_factory=list)


def _trust_for(source: SourceType, requested: TrustLevel, tainted: bool = False) -> TrustLevel:
    """Rule 2 plus a ceiling by origin: nobody self-assigns more trust than the source deserves."""
    if source in _THIRD_PARTY_SOURCES:
        return TrustLevel.THIRD_PARTY
    if source is SourceType.USER_GUI:
        return TrustLevel.USER_CONFIRMED
    if source is SourceType.USER_CONVERSATION:
        return TrustLevel.USER_STATED if requested is TrustLevel.USER_CONFIRMED else requested
    if tainted:
        # The model may be relaying a document it read in this session: no laundering into DERIVED.
        return TrustLevel.THIRD_PARTY
    return TrustLevel.DERIVED if requested in (TrustLevel.USER_CONFIRMED, TrustLevel.USER_STATED) else requested


def _not_found() -> AppError:
    return AppError("memory_not_found", "Memory not found.", 404)


class MemoryService:
    def __init__(
        self,
        adapter: MemoryAdapter,
        gate: ConfirmationGate,
        audit: AuditSink,
        extractor: Extractor | None = None,
    ) -> None:
        self._adapter = adapter
        self._gate = gate
        self._audit = audit
        self._extractor = extractor

    # -- helpers -----------------------------------------------------------------

    def _log(self, action: str, actor: str, target: str, outcome: str, **detail: Any) -> None:
        self._audit.record(action=action, actor=actor, target=target, outcome=outcome, detail=detail or None)

    def _require_user(self, action: str, actor: str, target: str) -> None:
        if actor != USER:
            self._log(action, actor, target, "forbidden")
            raise AppError("forbidden_actor", "Only the user can perform this action.", 403)

    def _require(self, memory_id: UUID) -> MemoryRecord:
        rec = self._adapter.get(memory_id)
        if rec is None:
            raise _not_found()
        return rec

    def _open_conflicts_for(self, memory_id: UUID) -> list[MemoryConflict]:
        return [c for c in self._adapter.list_conflicts(open_only=True) if memory_id in (c.memory_a, c.memory_b)]

    # -- ingest ------------------------------------------------------------------

    def ingest(self, draft: MemoryDraft, actor: str, *, tainted: bool = False) -> IngestResult:
        """`tainted`: the agent's session already received untrusted content (set by the tool)."""
        source = SourceType.AGENT if actor == AGENT else draft.provenance.source_type
        if actor == AGENT and draft.provenance.source_type is not SourceType.AGENT:
            draft = draft.model_copy(
                update={"provenance": Provenance(
                    source_type=SourceType.AGENT,
                    source_ref=draft.provenance.source_ref,
                    session_id=draft.provenance.session_id,
                    captured_at=draft.provenance.captured_at,
                )}
            )
        draft = draft.model_copy(update={
            "trust": _trust_for(source, draft.trust, tainted and actor == AGENT),
            # Invisible characters would dodge dedupe, conflict detection and a user's rejection.
            "content": strip_invisible(draft.content),
            "subject": strip_invisible(draft.subject),
            "abstract": strip_invisible(draft.abstract),
            "overview": strip_invisible(draft.overview),
        })

        if contains_secret(draft.content):
            self._log("memory.ingest", actor, "-", "secret_rejected", source=source.value)
            raise AppError("memory_secret_rejected", "Memories cannot contain credentials.", 422)

        dup = self._adapter.find_by_hash(content_hash(draft.content))
        related = self._adapter.related(draft)
        if dup is None:
            dup = find_duplicate(draft, related)
        if dup is not None:
            self._log("memory.ingest", actor, str(dup.id), "duplicate", source=source.value)
            return IngestResult(record=None, duplicate_of=dup.id)

        contradictions = find_contradictions(draft, related)
        approved = actor == USER and source is SourceType.USER_GUI and not contradictions
        record = self._adapter.create(draft, MemoryStatus.APPROVED if approved else MemoryStatus.PENDING)
        conflicts = [self._adapter.add_conflict(old.id, record.id, reason[:256]) for old, reason in contradictions]
        self._log(
            "memory.ingest", actor, str(record.id), "created",
            source=source.value, status=record.status.value, conflicts=len(conflicts),
        )
        return IngestResult(record=record, conflicts=conflicts)

    def extract_from_turn(self, text: str, seed: MemoryDraftSeed, actor: str) -> list[IngestResult]:
        if self._extractor is None:
            return []
        return [self.ingest(d, actor) for d in self._extractor.extract(text, seed)]

    # -- transitions (user only) -------------------------------------------------

    def approve(self, memory_id: UUID, actor: str) -> MemoryRecord:
        self._require_user("memory.approve", actor, str(memory_id))
        self._require(memory_id)
        if self._open_conflicts_for(memory_id):
            self._log("memory.approve", actor, str(memory_id), "conflict_open")
            raise AppError("memory_conflict_open", "Resolve the open conflict first.", 409)
        rec = self._adapter.set_status(memory_id, MemoryStatus.APPROVED)
        if rec is None:
            raise _not_found()
        self._log("memory.approve", actor, str(memory_id), "ok")
        return rec

    def reject(self, memory_id: UUID, actor: str) -> MemoryRecord:
        self._require_user("memory.reject", actor, str(memory_id))
        rec = self._adapter.set_status(memory_id, MemoryStatus.REJECTED)
        if rec is None:
            raise _not_found()
        self._log("memory.reject", actor, str(memory_id), "ok")
        return rec

    def correct(self, memory_id: UUID, patch: MemoryPatch, actor: str) -> MemoryRecord:
        self._require_user("memory.correct", actor, str(memory_id))
        current = self._require(memory_id)
        third_party = current.provenance.source_type in _THIRD_PARTY_SOURCES  # rule 2 outlives a correction
        rec = self._adapter.update(memory_id, patch, None if third_party else TrustLevel.USER_CONFIRMED)
        if rec is None:
            raise _not_found()
        self._log("memory.correct", actor, str(memory_id), "ok", fields=sorted(patch.model_fields_set))
        return rec

    def resolve_conflict(self, conflict_id: UUID, kept: UUID | None, actor: str) -> MemoryConflict:
        self._require_user("memory.resolve_conflict", actor, str(conflict_id))
        conflict = next((c for c in self._adapter.list_conflicts(open_only=True) if c.id == conflict_id), None)
        if conflict is None:
            raise AppError("conflict_not_found", "Open conflict not found.", 404)
        if kept is not None and kept not in (conflict.memory_a, conflict.memory_b):
            raise AppError("invalid_kept", "kept must be one of the two conflicting memories.", 422)
        resolved = self._adapter.resolve_conflict(conflict_id, kept)
        if resolved is None:
            raise AppError("conflict_not_found", "Open conflict not found.", 404)
        if kept is not None:
            other = conflict.memory_b if kept == conflict.memory_a else conflict.memory_a
            self._adapter.set_status(other, MemoryStatus.SUPERSEDED)
            if not self._open_conflicts_for(kept):
                self._adapter.set_status(kept, MemoryStatus.APPROVED)
        self._log("memory.resolve_conflict", actor, str(conflict_id), "ok", kept=str(kept) if kept else None)
        return resolved

    def forget(self, memory_id: UUID, confirmation_id: str | None, actor: str) -> ForgetReport:
        self._require_user("memory.forget", actor, str(memory_id))
        self._require(memory_id)
        if not self._gate.verify("memory.forget", str(memory_id), confirmation_id):
            self._log("memory.forget", actor, str(memory_id), "confirmation_required")
            raise AppError("confirmation_required", "Forgetting requires confirmation from the GUI.", 409)
        report = self._adapter.delete(memory_id)
        if report is None:
            raise _not_found()
        self._log(
            "memory.forget", actor, str(memory_id), "ok",
            erased_from=list(report.erased_from), not_reached=list(report.not_reached),
        )
        return report

    def forget_authorized(self, memory_id: UUID, actor: str) -> ForgetReport:
        """Delete after the confirmation was enforced outside (ToolRegistry/ToolGate). Not exposed to the GUI router."""
        self._require(memory_id)
        report = self._adapter.delete(memory_id)
        if report is None:
            raise _not_found()
        self._log(
            "memory.forget", actor, str(memory_id), "ok_authorized",
            erased_from=list(report.erased_from), not_reached=list(report.not_reached),
        )
        return report

    # -- reads -------------------------------------------------------------------

    def get(self, memory_id: UUID) -> MemoryRecord:
        return self._require(memory_id)

    def list(self, flt: MemoryFilter) -> tuple[list[MemoryRecord], int]:
        return self._adapter.list(flt)

    def conflicts(self, open_only: bool = True) -> list[MemoryConflict]:
        return self._adapter.list_conflicts(open_only=open_only)

    def search(self, query: MemoryQuery, actor: str) -> list[MemoryHit]:
        hits = self._adapter.search(query)
        self._log_retrieval(query.text, [h.id for h in hits], actor, "search")
        return hits

    def read(self, memory_id: UUID, level: DetailLevel, actor: str) -> str:
        text = self._adapter.read(memory_id, level)
        if text is None:
            self._log("memory.read", actor, str(memory_id), "not_found")
            raise _not_found()
        self._log_retrieval("", [memory_id], actor, "read", level=level.value)
        return text

    def _log_retrieval(self, text: str, ids: list[UUID], actor: str, action: str, **detail: Any) -> None:
        qh = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._log(f"memory.{action}", actor, qh[:16], "ok", hits=len(ids), **detail)
        self._audit.record_retrieval(qh, ids, True)

    def memories_for_context(self, text: str, level: DetailLevel = DetailLevel.L1, budget_hits: int = 8) -> list[Any]:
        from app.integrations.memory.context.builder import MemoryForContext  # noqa: PLC0415

        if not text.strip():
            return []
        query = MemoryQuery(text=text[:2000] or " ", limit=budget_hits)
        with_text = getattr(self._adapter, "search_with_text", None)
        if with_text is not None:
            # One query and one connection per turn instead of 1 + one per hit (~2 ms each).
            pairs: list[tuple[MemoryHit, str]] = with_text(query, level)
            self._log_retrieval(query.text, [h.id for h, _ in pairs], AGENT, "search")
        else:
            hits = self.search(query, AGENT)
            pairs = [(hit, body) for hit in hits if (body := self._adapter.read(hit.id, level)) is not None]
        return [
            MemoryForContext(id=hit.id, text=body, provenance=hit.provenance, trust=hit.trust, updated_at=hit.updated_at)
            for hit, body in pairs
        ]

    def status(self) -> BackendStatus:
        return self._adapter.status()

