"""Modelos de API y herramientas del almacén."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints, field_validator

ResourceType = Literal[
    "image", "document", "pdf", "text", "code", "link", "note", "study_note", "archive", "other"
]
AvailabilityStatus = Literal["available", "missing", "moved", "unreachable", "forbidden"]
IndexStatus = Literal["none", "pending", "indexed", "failed", "skipped"]

Uuid = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Description = Annotated[str, StringConstraints(max_length=4000)]
TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Cursor = Annotated[str, StringConstraints(max_length=200)]
SearchQuery = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StorageLocationCreate(StrictModel):
    path: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    label: Title
    read_only: bool = True
    agent_read: bool = False


class StorageLocationUpdate(StrictModel):
    label: Title | None = None
    read_only: bool | None = None
    agent_read: bool | None = None
    enabled: bool | None = None


class StorageLocationOut(BaseModel):
    id: str
    path: str
    label: str
    read_only: bool
    agent_read: bool
    enabled: bool
    created_at: str
    updated_at: str


class FolderCreate(StrictModel):
    name: Title
    parent_folder_id: Uuid | None = None


class FolderUpdate(StrictModel):
    name: Title | None = None
    parent_folder_id: Uuid | None = None
    expected_revision: Annotated[int, Field(ge=1)]


class FolderOut(BaseModel):
    id: str
    name: str
    parent_folder_id: str | None
    resource_count: int
    revision: int
    created_at: str
    updated_at: str
    archived_at: str | None


class ResourceCreate(StrictModel):
    """Una de tres formas: archivo en una ubicación, enlace o nota."""

    title: Title
    resource_type: ResourceType | None = None
    folder_id: Uuid | None = None
    location_id: Uuid | None = None
    relative_path: Annotated[str, StringConstraints(min_length=1, max_length=4096)] | None = None
    url: AnyHttpUrl | None = None
    note_body: Annotated[str, StringConstraints(max_length=1_000_000)] | None = None
    description: Description | None = None
    tags: Annotated[list[TagName], Field(max_length=32)] = []
    index_content: bool = False

    @field_validator("url")
    @classmethod
    def only_web_urls(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and value.scheme not in ("http", "https"):
            raise ValueError("Only http and https")
        return value


class ResourceUpdate(StrictModel):
    title: Title | None = None
    folder_id: Uuid | None = None
    note_body: Annotated[str, StringConstraints(max_length=1_000_000)] | None = None
    description: Description | None = None
    tags: Annotated[list[TagName], Field(max_length=32)] | None = None
    index_content: bool | None = None
    expected_revision: Annotated[int, Field(ge=1)]


class ResourceSummary(BaseModel):
    """Lo que devuelven listados y búsqueda: metadatos, nunca contenido."""

    id: str
    title: str
    resource_type: ResourceType
    folder_id: str | None
    mime_type: str | None
    size_bytes: int | None
    availability_status: AvailabilityStatus
    index_status: IndexStatus
    tags: list[str]
    revision: int
    created_at: str
    updated_at: str
    archived_at: str | None


class ResourceOut(ResourceSummary):
    location_id: str | None
    relative_path: str | None
    url: str | None
    description: str | None
    content_hash: str | None
    source_modified_at: str | None
    has_note_body: bool
    index_content: bool
    index_error_code: str | None
    indexed_at: str | None


class ResourcePage(BaseModel):
    items: list[ResourceSummary]
    next_cursor: str | None


class SearchHit(BaseModel):
    resource: ResourceSummary
    snippet: str
    content_trust: Literal["untrusted"] = "untrusted"


class SearchPage(BaseModel):
    items: list[SearchHit]
    next_cursor: str | None


class ReadRequest(StrictModel):
    selector: Annotated[str, StringConstraints(max_length=200)] | None = None
    offset: Annotated[int, Field(ge=0)] = 0
    max_chars: Annotated[int, Field(ge=1, le=20_000)] = 8_000


class ReadSource(BaseModel):
    resource_id: str
    title: str


class ReadResult(BaseModel):
    text: str
    truncated: bool
    next_offset: int | None
    metadata: dict[str, str | int | float | bool | None]
    source: ReadSource
    content_trust: Literal["untrusted"] = "untrusted"


class ScanRequest(StrictModel):
    location_id: Uuid


class ScanResult(BaseModel):
    location_id: str
    seen: int
    added: int
    updated: int
    missing: int
    moved: int
    skipped: int
    truncated: bool


class RefreshResult(BaseModel):
    checked: int
    available: int
    missing: int
    moved: int
    forbidden: int
    reindexed: int
    failed: int
