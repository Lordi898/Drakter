"""Frozen data models for Drakter memory. See CONTRACT.md."""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Final
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

L0_MAX_CHARS: Final = 256
L1_MAX_CHARS: Final = 4000
L2_MAX_CHARS: Final = 100_000
SUBJECT_MAX_CHARS: Final = 200


class MemoryKind(StrEnum):
    """What type of memory (MASTER_PLAN §9)."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryCategory(StrEnum):
    """OpenViking categories (MASTER_PLAN §10.4), so records map 1:1 when it is plugged in."""

    PROFILE = "profile"
    PREFERENCES = "preferences"
    ENTITIES = "entities"
    EVENTS = "events"
    CASES = "cases"
    PATTERNS = "patterns"


class DetailLevel(StrEnum):
    L0 = "l0"
    L1 = "l1"
    L2 = "l2"


class MemoryStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SourceType(StrEnum):
    USER_GUI = "user_gui"  # typed or approved by the user in the GUI
    USER_CONVERSATION = "user_conversation"  # said by the user in a conversation
    AGENT = "agent"  # proposed by the model
    TOOL_RESULT = "tool_result"
    DOCUMENT = "document"  # store documents, web pages
    IMPORT = "import"


class TrustLevel(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    USER_STATED = "user_stated"
    DERIVED = "derived"
    THIRD_PARTY = "third_party"


class ConflictStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class EntityRef(BaseModel):
    """Reference to a Workspace entity. Memory stores the reference, never a copy of its state."""

    model_config = ConfigDict(frozen=True)

    entity_type: str = Field(min_length=1, max_length=64)
    entity_id: UUID


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_type: SourceType
    source_ref: str | None = Field(default=None, max_length=512)
    session_id: str | None = Field(default=None, max_length=128)
    captured_at: datetime  # timezone-aware UTC


class MemoryDraft(BaseModel):
    """A candidate memory before it is stored."""

    model_config = ConfigDict(frozen=True)

    kind: MemoryKind
    category: MemoryCategory
    subject: str = Field(default="", max_length=SUBJECT_MAX_CHARS)  # conflict key, see normalize_subject
    content: str = Field(min_length=1, max_length=L2_MAX_CHARS)  # L2
    abstract: str = Field(default="", max_length=L0_MAX_CHARS)  # L0
    overview: str = Field(default="", max_length=L1_MAX_CHARS)  # L1
    provenance: Provenance
    trust: TrustLevel
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    valid_until: datetime | None = None
    entity_refs: tuple[EntityRef, ...] = ()


class MemoryRecord(MemoryDraft):
    id: UUID
    status: MemoryStatus
    content_hash: str
    supersedes: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MemoryPatch(BaseModel):
    """User correction. Only set fields change. Content changes recompute content_hash."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str | None = Field(default=None, max_length=SUBJECT_MAX_CHARS)
    content: str | None = Field(default=None, min_length=1, max_length=L2_MAX_CHARS)
    abstract: str | None = Field(default=None, max_length=L0_MAX_CHARS)
    overview: str | None = Field(default=None, max_length=L1_MAX_CHARS)
    kind: MemoryKind | None = None
    category: MemoryCategory | None = None
    valid_until: datetime | None = None


class MemoryFilter(BaseModel):
    model_config = ConfigDict(frozen=True)

    statuses: tuple[MemoryStatus, ...] = ()
    kinds: tuple[MemoryKind, ...] = ()
    categories: tuple[MemoryCategory, ...] = ()
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class MemoryQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1, max_length=2000)
    kinds: tuple[MemoryKind, ...] = ()
    categories: tuple[MemoryCategory, ...] = ()
    limit: int = Field(default=8, ge=1, le=50)


class MemoryHit(BaseModel):
    """Search result. Exposes L0 only; L1/L2 are read on demand (MASTER_PLAN §10.5)."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    kind: MemoryKind
    category: MemoryCategory
    abstract: str
    score: float
    trust: TrustLevel
    provenance: Provenance
    updated_at: datetime


class MemoryConflict(BaseModel):
    """Two memories that disagree. Never resolved automatically."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    memory_a: UUID  # the older record
    memory_b: UUID  # the newer record
    reason: str = Field(max_length=256)
    status: ConflictStatus
    created_at: datetime
    resolved_at: datetime | None = None
    kept: UUID | None = None


class BackendStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend: str
    available: bool
    detail: str = ""


class ForgetReport(BaseModel):
    """What a forget really reached. Copies out of reach are stated, never hidden (dossier N3)."""

    model_config = ConfigDict(frozen=True)

    memory_id: UUID
    erased_from: tuple[str, ...]
    not_reached: tuple[str, ...]


class PriorityLevel(IntEnum):
    """Instruction priority (CLAUDE.md §8, MASTER_PLAN §8.3). 1 is the highest."""

    SECURITY = 1
    SYSTEM_RULES = 2
    IDENTITY = 3
    USER_CONTEXT = 4
    CONVERSATION = 5
    MEMORY = 6
    CURRENT_INSTRUCTION = 7


class ConversationTurn(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str = Field(pattern="^(user|assistant)$")
    text: str


class ContextSection(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: PriorityLevel
    name: str
    text: str
    trusted: bool  # False: delimited data with no authority
    truncated: bool = False
    chars: int = 0


class ContextBundle(BaseModel):
    """Assembled context. Hermes wiring uses `system_prompt` and `turn_prompt`."""

    model_config = ConfigDict(frozen=True)

    sections: tuple[ContextSection, ...]  # always sorted by level
    system_prompt: str  # levels 1-4
    turn_prompt: str  # levels 5-7, data blocks delimited
    memory_ids: tuple[UUID, ...]  # memories actually included, for retrieval.log and taint
    dropped_memory_ids: tuple[UUID, ...]  # left out by the budget
    tainted: bool  # True when any untrusted data was included
