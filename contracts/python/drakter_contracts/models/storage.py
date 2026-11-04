from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field

from ..common import ContractModel, Id, Instant
from ._base import EntityOut, LongText, Metadata, Name, OutModel, TagName, Title
from .tags import TagOut  # noqa: F401

RelativePath = Annotated[str, Field(min_length=1, max_length=4096, description="Relativo a la ubicación; sin '..' ni '/' inicial")]


class ResourceType(StrEnum):
    IMAGE = "image"
    DOCUMENT = "document"
    PDF = "pdf"
    TEXT = "text"
    CODE = "code"
    LINK = "link"
    NOTE = "note"
    STUDY_NOTE = "study_note"
    ARCHIVE = "archive"
    OTHER = "other"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    MOVED = "moved"
    UNREACHABLE = "unreachable"
    FORBIDDEN = "forbidden"


class IndexStatus(StrEnum):
    NONE = "none"
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"
    SKIPPED = "skipped"


# --- Ubicaciones: solo GUI. `path` absoluta solo aquí; nunca en recursos ni herramientas ---
class StorageLocationCreate(ContractModel):
    path: Annotated[str, Field(min_length=1, max_length=4096)]
    label: Title
    read_only: bool = True
    agent_read: bool = False


class StorageLocationUpdate(ContractModel):
    label: Title | None = None
    read_only: bool | None = None
    agent_read: bool | None = None
    enabled: bool | None = None


class StorageLocationOut(OutModel):
    """No es entidad. `root_dev` y `root_ino` no se exponen."""

    id: Id
    path: str
    label: str
    read_only: bool
    agent_read: bool
    enabled: bool
    created_at: Instant


# --- Carpetas ---
class FolderCreate(ContractModel):
    name: Name
    parent_folder_id: Id | None = None
    location_id: Id | None = None
    relative_path: RelativePath | None = None
    metadata: Metadata = {}


class FolderUpdate(ContractModel):
    name: Name | None = None
    parent_folder_id: Id | None = None
    metadata: Metadata | None = None


class FolderOut(EntityOut):
    name: str
    parent_folder_id: Id | None = None
    location_id: Id | None = None
    relative_path: str | None = None
    resource_count: int = 0


# --- Recursos: ninguna ruta absoluta ---
class ResourceCreate(ContractModel):
    title: Title
    resource_type: ResourceType | None = None
    folder_id: Id | None = None
    location_id: Id | None = None
    relative_path: RelativePath | None = None
    url: AnyHttpUrl | None = None
    note_body: Annotated[str, Field(max_length=1_000_000)] | None = None
    description: LongText | None = None
    tags: Annotated[list[TagName], Field(max_length=32)] = []
    index_content: bool = False
    metadata: Metadata = {}


class ResourceUpdate(ContractModel):
    title: Title | None = None
    folder_id: Id | None = None
    note_body: Annotated[str, Field(max_length=1_000_000)] | None = None
    description: LongText | None = None
    tags: Annotated[list[TagName], Field(max_length=32)] | None = None
    index_content: bool | None = None
    metadata: Metadata | None = None


class ResourceOut(EntityOut):
    title: str
    resource_type: ResourceType
    folder_id: Id | None = None
    location_id: Id | None = None
    relative_path: str | None = None
    url: str | None = None
    description: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    content_hash: str | None = None
    source_modified_at: Instant | None = None
    availability_status: AvailabilityStatus
    index_status: IndexStatus
    indexed_at: Instant | None = None
    index_error_code: str | None = None
    has_note_body: bool = False
    index_content: bool = False
    tags: list[str] = []


class ResourceSearchHit(OutModel):
    resource: ResourceOut
    snippet: str
    content_trust: Literal["untrusted"] = "untrusted"


class ResourceReadRequest(ContractModel):
    selector: Annotated[str, Field(max_length=200)] | None = None
    offset: Annotated[int, Field(ge=0)] = 0
    max_chars: Annotated[int, Field(ge=1, le=20_000)] = 8_000


class ResourceReadResult(OutModel):
    """El contenido va siempre como dato no confiable (ver `UntrustedEnvelope`)."""

    resource_id: Id
    title: str
    text: str
    truncated: bool
    next_offset: int | None = None
    metadata: dict[str, str | int | float | bool | None] = {}
    content_trust: Literal["untrusted"] = "untrusted"


class StorageScanRequest(ContractModel):
    location_id: Id


class StorageScanResult(OutModel):
    location_id: Id
    seen: int
    added: int
    updated: int
    missing: int
    moved: int
    skipped: int
    truncated: bool


class StorageRefreshResult(OutModel):
    checked: int
    available: int
    missing: int
    moved: int
    forbidden: int
    reindexed: int
    failed: int
