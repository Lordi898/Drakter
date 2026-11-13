"""Formato de herramienta y resultado visible para el agente.

`ToolSpec`, `ToolRegistry` y el orden de `dispatch` viven en backend/app/tools/ y se rigen por
backend/app/integrations/hermes/CONTRACT.md §1. Aquí queda lo que comparten módulos, GUI y catálogo.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Final, Literal

from pydantic import BaseModel, Field

from .common import Id, Instant


class RiskClass(StrEnum):
    READ = "read"
    WRITE = "write"
    CONFIRM = "confirm"


AuditPolicy = Literal["log", "hash", "omit"]

# `permission` es `<dominio>.<accion>`: búsqueda transversal = dominio `search`, permiso `search.read`.
TOOL_DOMAINS: Final = (
    "tasks", "projects", "habits", "calendar", "subjects", "storage", "relationships",
    "tags", "search", "memory", "system", "config", "improvement", "voice",
)


class ToolErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: list[dict[str, Any]] = []


class ToolOk(BaseModel):
    status: Literal["ok"] = "ok"
    data: dict[str, Any]


class ToolFailed(BaseModel):
    status: Literal["error"] = "error"
    error: ToolErrorBody


class ToolConfirmationRequired(BaseModel):
    """`summary` lo calcula el backend desde los argumentos, nunca el modelo."""

    status: Literal["confirmation_required"] = "confirmation_required"
    action_id: Id
    summary: str
    expires_at: Instant


ToolOutcome = Annotated[ToolOk | ToolFailed | ToolConfirmationRequired, Field(discriminator="status")]


class UntrustedEnvelope(BaseModel):
    """Sobre obligatorio de todo contenido de documentos o memoria."""

    trust: Literal["untrusted"] = "untrusted"
    source_type: str
    source_id: str
    retrieved_at: Instant
    content_hash: str
    truncated: bool = False
    content: str


class ToolManifest(BaseModel):
    """Una entrada de contracts/tools/catalog.json."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,47}$")
    domain: str
    description: str
    permission: str
    risk: RiskClass
    idempotent: bool = False
    returns_untrusted: bool = False
    timeout_s: float = 15.0
    errors: list[str] = []
    args_model: str
    result_model: str
    phase: str
