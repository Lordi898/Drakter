"""REST API for the GUI. The actor is always the user; provenance is fixed by the server."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.integrations.memory.audit import JsonlAudit
from app.integrations.memory.models import (
    L0_MAX_CHARS,
    L1_MAX_CHARS,
    L2_MAX_CHARS,
    SUBJECT_MAX_CHARS,
    BackendStatus,
    EntityRef,
    ForgetReport,
    MemoryCategory,
    MemoryConflict,
    MemoryDraft,
    MemoryFilter,
    MemoryHit,
    MemoryKind,
    MemoryPatch,
    MemoryQuery,
    MemoryRecord,
    MemoryStatus,
    Provenance,
    SourceType,
    TrustLevel,
)
from app.integrations.memory.pipeline.extract import RuleExtractor
from app.integrations.memory.ports import DenyAllGate
from app.integrations.memory.service import USER, MemoryService
from app.integrations.memory.store_sqlite import SqliteMemoryAdapter

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


def build_memory_service(settings: Settings) -> MemoryService:
    return MemoryService(
        SqliteMemoryAdapter(settings.db_path),
        DenyAllGate(),
        JsonlAudit(settings.logs_dir),
        RuleExtractor(),
    )


def get_memory_service(request: Request) -> MemoryService:
    return request.app.state.memory_service


Service = Annotated[MemoryService, Depends(get_memory_service)]


class MemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: MemoryKind
    category: MemoryCategory
    subject: str = Field(default="", max_length=SUBJECT_MAX_CHARS)
    content: str = Field(min_length=1, max_length=L2_MAX_CHARS)
    abstract: str = Field(default="", max_length=L0_MAX_CHARS)
    overview: str = Field(default="", max_length=L1_MAX_CHARS)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    valid_until: datetime | None = None
    entity_refs: tuple[EntityRef, ...] = Field(default=(), max_length=32)


class MemoryCreated(BaseModel):
    record: MemoryRecord | None
    duplicate_of: UUID | None
    conflicts: list[MemoryConflict]


class MemoryPage(BaseModel):
    items: list[MemoryRecord]
    total: int
    limit: int
    offset: int


class SearchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)
    kinds: tuple[MemoryKind, ...] = ()
    categories: tuple[MemoryCategory, ...] = ()
    limit: int = Field(default=8, ge=1, le=50)


class ResolveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kept: UUID | None = None


class ForgetBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_id: str | None = Field(default=None, max_length=128)


@router.get("", response_model=MemoryPage)
def list_memories(
    service: Service,
    statuses: Annotated[list[MemoryStatus] | None, Query()] = None,
    kinds: Annotated[list[MemoryKind] | None, Query()] = None,
    categories: Annotated[list[MemoryCategory] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MemoryPage:
    flt = MemoryFilter(
        statuses=tuple(statuses or ()),
        kinds=tuple(kinds or ()),
        categories=tuple(categories or ()),
        limit=limit,
        offset=offset,
    )
    items, total = service.list(flt)
    return MemoryPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/status", response_model=BackendStatus)
def memory_status(service: Service) -> BackendStatus:
    return service.status()


@router.get("/conflicts", response_model=list[MemoryConflict])
def list_conflicts(service: Service, open_only: bool = True) -> list[MemoryConflict]:
    return service.conflicts(open_only)


@router.post("/conflicts/{conflict_id}/resolve", response_model=MemoryConflict)
def resolve_conflict(conflict_id: UUID, body: ResolveBody, service: Service) -> MemoryConflict:
    return service.resolve_conflict(conflict_id, body.kept, USER)


@router.post("", response_model=MemoryCreated, status_code=201)
def create_memory(body: MemoryCreate, service: Service) -> MemoryCreated:
    draft = MemoryDraft(
        kind=body.kind,
        category=body.category,
        subject=body.subject,
        content=body.content,
        abstract=body.abstract,
        overview=body.overview,
        provenance=Provenance(source_type=SourceType.USER_GUI, captured_at=datetime.now(UTC)),
        trust=TrustLevel.USER_CONFIRMED,
        confidence=body.confidence,
        valid_until=body.valid_until,
        entity_refs=body.entity_refs,
    )
    result = service.ingest(draft, USER)
    return MemoryCreated(record=result.record, duplicate_of=result.duplicate_of, conflicts=result.conflicts)


@router.post("/search", response_model=list[MemoryHit])
def search_memories(body: SearchBody, service: Service) -> list[MemoryHit]:
    return service.search(MemoryQuery(**body.model_dump()), USER)


@router.get("/{memory_id}", response_model=MemoryRecord)
def get_memory(memory_id: UUID, service: Service) -> MemoryRecord:
    return service.get(memory_id)


@router.patch("/{memory_id}", response_model=MemoryRecord)
def correct_memory(memory_id: UUID, patch: MemoryPatch, service: Service) -> MemoryRecord:
    return service.correct(memory_id, patch, USER)


@router.post("/{memory_id}/approve", response_model=MemoryRecord)
def approve_memory(memory_id: UUID, service: Service) -> MemoryRecord:
    return service.approve(memory_id, USER)


@router.post("/{memory_id}/reject", response_model=MemoryRecord)
def reject_memory(memory_id: UUID, service: Service) -> MemoryRecord:
    return service.reject(memory_id, USER)


@router.post("/{memory_id}/forget", response_model=ForgetReport)
def forget_memory(memory_id: UUID, body: ForgetBody, service: Service) -> ForgetReport:
    return service.forget(memory_id, body.confirmation_id, USER)
