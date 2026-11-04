"""Catálogo de errores común a REST, herramientas y WebSocket.

El sobre HTTP es el de backend/CONTRACT.md: {"error":{code,message,request_id,details}}.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    code: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[ErrorDetail] = []


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class ConfirmationTicket(BaseModel):
    """`summary` y `affected_count` los calcula el backend. `params_hash` es `args_hash` de la fila."""

    id: str
    summary: str
    affected_count: int | None = None
    expires_at: str
    params_hash: str


class ConfirmationRequiredEnvelope(ErrorEnvelope):
    """HTTP 409 con `error.code == "confirmation_required"`. Nunca 2xx."""

    confirmation: ConfirmationTicket


class ErrorCode(StrEnum):
    # Ya emitidos por la base del backend
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN_CLIENT = "forbidden_client"
    FORBIDDEN_HOST = "forbidden_host"
    FORBIDDEN_ORIGIN = "forbidden_origin"
    SERVICE_UNAVAILABLE = "service_unavailable"
    # Dominio
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INVALID_QUERY = "invalid_query"
    PERMISSION_DENIED = "permission_denied"
    REVISION_MISMATCH = "revision_mismatch"
    HIERARCHY_CYCLE = "hierarchy_cycle"
    RELATIONSHIP_NOT_ALLOWED = "relationship_not_allowed"
    HAS_DEPENDENTS = "has_dependents"
    NONEXISTENT_LOCAL_TIME = "nonexistent_local_time"
    # Confirmaciones
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMATION_EXPIRED = "confirmation_expired"
    CONFIRMATION_UNAVAILABLE = "confirmation_unavailable"
    CONFIRMATION_ALREADY_RESOLVED = "confirmation_already_resolved"
    # Almacén
    PATH_NOT_ALLOWED = "path_not_allowed"
    FILE_TOO_LARGE = "file_too_large"
    ARCHIVE_LIMIT_EXCEEDED = "archive_limit_exceeded"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    # Agente
    AGENT_UNAVAILABLE = "agent_unavailable"
    AGENT_BUSY = "agent_busy"
    AGENT_TIMEOUT = "agent_timeout"
    AGENT_DISCONNECTED = "agent_disconnected"
    PROVIDER_AUTH = "provider_auth"
    PROVIDER_ERROR = "provider_error"
    NO_ACTIVE_TURN = "no_active_turn"
    TOOL_TIMEOUT = "tool_timeout"
    # Componentes externos
    MEMORY_UNAVAILABLE = "memory_unavailable"
    VOICE_UNAVAILABLE = "voice_unavailable"
    RATE_LIMITED = "rate_limited"


HTTP_STATUS: Final[dict[ErrorCode, int]] = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN_CLIENT: 403,
    ErrorCode.FORBIDDEN_HOST: 403,
    ErrorCode.FORBIDDEN_ORIGIN: 403,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.INVALID_QUERY: 400,
    ErrorCode.PERMISSION_DENIED: 403,
    ErrorCode.REVISION_MISMATCH: 412,
    ErrorCode.HIERARCHY_CYCLE: 409,
    ErrorCode.RELATIONSHIP_NOT_ALLOWED: 422,
    ErrorCode.HAS_DEPENDENTS: 409,
    ErrorCode.NONEXISTENT_LOCAL_TIME: 422,
    ErrorCode.CONFIRMATION_REQUIRED: 409,
    ErrorCode.CONFIRMATION_EXPIRED: 410,
    ErrorCode.CONFIRMATION_UNAVAILABLE: 503,
    ErrorCode.CONFIRMATION_ALREADY_RESOLVED: 409,
    ErrorCode.PATH_NOT_ALLOWED: 403,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.ARCHIVE_LIMIT_EXCEEDED: 413,
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: 415,
    ErrorCode.RESOURCE_UNAVAILABLE: 424,
    ErrorCode.AGENT_UNAVAILABLE: 503,
    ErrorCode.AGENT_BUSY: 409,
    ErrorCode.AGENT_TIMEOUT: 504,
    ErrorCode.AGENT_DISCONNECTED: 503,
    ErrorCode.PROVIDER_AUTH: 503,
    ErrorCode.PROVIDER_ERROR: 502,
    ErrorCode.NO_ACTIVE_TURN: 403,
    ErrorCode.TOOL_TIMEOUT: 504,
    ErrorCode.MEMORY_UNAVAILABLE: 503,
    ErrorCode.VOICE_UNAVAILABLE: 503,
    ErrorCode.RATE_LIMITED: 429,
}
