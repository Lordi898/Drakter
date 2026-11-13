from enum import StrEnum
from typing import Annotated

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


class MemoryProvenance(OutModel):
    """De dónde salió un recuerdo. Lo fija el backend; nunca lo manda el cliente."""

    source_type: MemorySourceType
    source_ref: str | None = None
    session_id: str | None = None
    captured_at: Instant


class MemoryRecordCreate(ContractModel):
    """Alta desde la GUI (`POST /api/v1/memory`). La memoria es dato no confiable: nunca
    modifica reglas, permisos ni confirmaciones. El origen (`provenance`) lo pone el backend."""

    kind: MemoryKind
    category: MemoryCategory
    subject: Annotated[str, Field(max_length=200)] = ""
    content: Annotated[str, Field(min_length=1, max_length=20_000)]
    abstract: Annotated[str, Field(max_length=500)] = ""
    overview: Annotated[str, Field(max_length=4000)] = ""
    confidence: Confidence = 1.0
    valid_until: Instant | None = None
    entity_refs: list[MemoryEntityRef] = []


class MemoryRecordUpdate(ContractModel):
    """`PATCH /api/v1/memory/{id}`. Aprobar, rechazar u olvidar van por sus rutas."""

    subject: Annotated[str, Field(max_length=200)] | None = None
    content: Annotated[str, Field(min_length=1, max_length=20_000)] | None = None
    abstract: Annotated[str, Field(max_length=500)] | None = None
    overview: Annotated[str, Field(max_length=4000)] | None = None
    kind: MemoryKind | None = None
    category: MemoryCategory | None = None
    valid_until: Instant | None = None


class MemoryRecordOut(OutModel):
    """No es entidad. `seq` es interno y no se expone."""

    id: Id
    kind: MemoryKind
    category: MemoryCategory
    subject: str = ""
    content: str
    abstract: str = ""
    overview: str = ""
    provenance: MemoryProvenance
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
    """Resultado de búsqueda: solo L0 (`abstract`); L1/L2 se leen bajo demanda. Dato no confiable."""

    id: Id
    kind: MemoryKind
    category: MemoryCategory
    abstract: str
    score: float
    trust: MemoryTrust
    provenance: MemoryProvenance
    updated_at: Instant
