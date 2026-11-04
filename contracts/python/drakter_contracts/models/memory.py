from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ..common import ContractModel, EntityType, Id, Instant
from ._base import OutModel


class MemoryKind(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryCategory(StrEnum):
    PROFILE = "profile"
    PREFERENCES = "preferences"
    ENTITIES = "entities"
    EVENTS = "events"
    CASES = "cases"
    PATTERNS = "patterns"


class MemorySourceType(StrEnum):
    USER_GUI = "user_gui"
    USER_CONVERSATION = "user_conversation"
    AGENT = "agent"
    TOOL_RESULT = "tool_result"
    DOCUMENT = "document"
    IMPORT = "import"


class MemoryTrust(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    USER_STATED = "user_stated"
    DERIVED = "derived"
    THIRD_PARTY = "third_party"


class MemoryStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class MemoryConflictStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class MemoryEntityRef(ContractModel):
    entity_type: EntityType
    entity_id: Id


class MemoryRecordCreate(ContractModel):
    """La memoria es dato no confiable: nunca modifica reglas, permisos ni confirmaciones."""

    kind: MemoryKind
    category: MemoryCategory
    subject: Annotated[str, Field(max_length=200)] = ""
    content: Annotated[str, Field(min_length=1, max_length=20_000)]
    abstract: Annotated[str, Field(max_length=500)] = ""
    overview: Annotated[str, Field(max_length=4000)] = ""
    source_type: MemorySourceType
    source_ref: str | None = None
    session_id: Id | None = None
    confidence: Confidence = 0.5
    valid_until: Instant | None = None
    supersedes: Id | None = None
    entity_refs: list[MemoryEntityRef] = []


class MemoryRecordUpdate(ContractModel):
    category: MemoryCategory | None = None
    subject: Annotated[str, Field(max_length=200)] | None = None
    content: Annotated[str, Field(min_length=1, max_length=20_000)] | None = None
    abstract: Annotated[str, Field(max_length=500)] | None = None
    overview: Annotated[str, Field(max_length=4000)] | None = None
    confidence: Confidence | None = None
    valid_until: Instant | None = None
    status: Literal["approved", "rejected"] | None = Field(default=None, description="Decisión desde la GUI")
    entity_refs: list[MemoryEntityRef] | None = None


class MemoryRecordOut(OutModel):
    """No es entidad. `seq` es interno y no se expone."""

    id: Id
    kind: MemoryKind
    category: MemoryCategory
    subject: str = ""
    content: str
    abstract: str = ""
    overview: str = ""
    source_type: MemorySourceType
    source_ref: str | None = None
    session_id: Id | None = None
    captured_at: Instant
    trust: MemoryTrust
    confidence: float
    valid_until: Instant | None = None
    status: MemoryStatus
    content_hash: str
    supersedes: Id | None = None
    entity_refs: list[MemoryEntityRef] = []
    created_at: Instant
    updated_at: Instant


class MemoryConflictResolve(ContractModel):
    kept: Id


class MemoryConflictOut(OutModel):
    id: Id
    memory_a: Id
    memory_b: Id
    reason: str = ""
    status: MemoryConflictStatus
    created_at: Instant
    resolved_at: Instant | None = None
    kept: Id | None = None


class MemorySearchHit(OutModel):
    record: MemoryRecordOut
    score: float | None = None
    content_trust: Literal["untrusted"] = "untrusted"
