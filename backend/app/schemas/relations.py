"""Modelos de API y herramientas de relaciones."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.storage import Cursor, Uuid

EntityType = Literal[
    "task", "project", "habit", "calendar_event", "time_block",
    "subject", "class_session", "resource", "folder",
]
RelationshipType = Literal[
    "belongs_to", "related_to", "scheduled_for", "uses_resource", "depends_on",
    "supports", "studies", "parent_of", "references", "derived_from",
]
Direction = Literal["in", "out", "both"]

MAX_METADATA_BYTES = 4096


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _check_metadata(value: dict[str, Any]) -> dict[str, Any]:
    import json

    if len(json.dumps(value, ensure_ascii=False).encode()) > MAX_METADATA_BYTES:
        raise ValueError("Metadata too large")
    return value


class RelationshipCreate(StrictModel):
    source_id: Uuid
    target_id: Uuid
    relationship_type: RelationshipType
    metadata: dict[str, Any] = {}

    _metadata = field_validator("metadata")(_check_metadata)


class RelationshipUpdate(StrictModel):
    metadata: dict[str, Any]

    _metadata = field_validator("metadata")(_check_metadata)


class RelationshipOut(BaseModel):
    id: str
    source_id: str
    source_type: EntityType
    target_id: str
    target_type: EntityType
    relationship_type: RelationshipType
    metadata: dict[str, Any]
    created_at: str


class RelationshipPage(BaseModel):
    items: list[RelationshipOut]
    next_cursor: str | None


class RelationshipTypeOut(BaseModel):
    relationship_type: RelationshipType
    label: str
    inverse_label: str
    description: str
    symmetric: bool
    allowed_pairs: list[tuple[EntityType, EntityType]]


class RelatedItem(BaseModel):
    """Una arista vista desde una entidad. `virtual` significa que viene de una columna."""

    relationship_id: str | None
    relationship_type: RelationshipType
    direction: Literal["in", "out"]
    label: str
    entity_id: str
    entity_type: EntityType
    entity_title: str
    archived: bool
    virtual: bool
    metadata: dict[str, Any]


class RelatedItems(BaseModel):
    entity_id: str
    entity_type: EntityType
    entity_title: str
    items: list[RelatedItem]


class RelationshipSearch(StrictModel):
    source_id: Uuid | None = None
    target_id: Uuid | None = None
    entity_type: EntityType | None = None
    relationship_type: RelationshipType | None = None
    limit: Annotated[int, Field(ge=1, le=200)] = 50
    cursor: Cursor | None = None
