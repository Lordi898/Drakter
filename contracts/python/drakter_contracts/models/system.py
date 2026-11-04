from typing import Literal

from ..common import EntityType, Id, Instant
from ._base import OutModel


class ComponentHealth(OutModel):
    component: Literal["backend", "hermes", "memory", "voice", "database"]
    status: Literal["ok", "degraded", "down"]
    detail: str | None = None


class HealthOut(OutModel):
    status: Literal["ok", "degraded", "down"]
    components: list[ComponentHealth] = []


class SystemInfoOut(OutModel):
    contract_version: str
    schema_version: int
    boot_id: Id
    started_at: Instant
    default_timezone: str


class SearchHitOut(OutModel):
    """Búsqueda global (`search_documents`): metadatos y fragmento; sin contenido completo."""

    entity_type: EntityType
    entity_id: Id
    title: str
    snippet: str = ""
    archived: bool = False
    content_trust: Literal["untrusted"] = "untrusted"
