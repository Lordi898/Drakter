from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ..common import ContractModel, EntityType, Id, Instant
from ._base import Metadata, OutModel


class RelationshipType(StrEnum):
    BELONGS_TO = "belongs_to"
    RELATED_TO = "related_to"
    SCHEDULED_FOR = "scheduled_for"
    USES_RESOURCE = "uses_resource"
    DEPENDS_ON = "depends_on"
    SUPPORTS = "supports"
    STUDIES = "studies"
    PARENT_OF = "parent_of"
    REFERENCES = "references"
    DERIVED_FROM = "derived_from"


class RelationshipCreate(ContractModel):
    source_id: Id
    target_id: Id
    relationship_type: RelationshipType
    metadata: Metadata = {}


class RelationshipUpdate(ContractModel):
    metadata: Metadata | None = None


class RelationshipOut(OutModel):
    """No es entidad: sin revision ni archived_at (0006)."""

    id: Id
    source_id: Id
    source_type: EntityType
    target_id: Id
    target_type: EntityType
    relationship_type: RelationshipType
    metadata: Metadata = {}
    created_at: Instant


class RelationshipTypeOut(OutModel):
    relationship_type: RelationshipType
    label: str = ""
    inverse_label: str = ""
    description: str
    symmetric: bool
    allowed_pairs: list[tuple[EntityType, EntityType]] = []


class RelationshipSearch(ContractModel):
    source_id: Id | None = None
    target_id: Id | None = None
    entity_type: EntityType | None = None
    relationship_type: RelationshipType | None = None
    limit: int = Field(default=50, ge=1, le=200)
    cursor: Annotated[str, Field(max_length=200)] | None = None


class RelatedItem(OutModel):
    relationship_id: Id | None = None
    relationship_type: RelationshipType
    direction: Literal["in", "out"]
    label: str
    entity_id: Id
    entity_type: EntityType
    entity_title: str
    archived: bool
    virtual: bool = False
    metadata: Metadata = {}


class RelatedItems(OutModel):
    entity_id: Id
    entity_type: EntityType
    entity_title: str
    items: list[RelatedItem]
