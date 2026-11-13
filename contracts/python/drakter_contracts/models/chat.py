from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ..common import ContractModel, Id, Instant
from ..events import AgentState
from ._base import OutModel


class TurnStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class InputSource(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageStatus(StrEnum):
    STREAMING = "streaming"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ConversationCreate(ContractModel):
    title: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class ConversationUpdate(ContractModel):
    title: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class ConversationOut(OutModel):
    """No es entidad (0007): sin revision ni archived_at; `ended_at` cierra la conversación."""

    id: Id
    title: str | None = None
    created_at: Instant
    updated_at: Instant
    ended_at: Instant | None = None


class ChatSession(ConversationOut):
    """Sesión de chat en la API. `session_id` en rutas y eventos es `conversations.id`."""

    status: Literal["open", "closed"]


class MessageCreate(ContractModel):
    """Mensaje del usuario; arranca un turno. `client_message_id` evita duplicados al reintentar."""

    text: Annotated[str, Field(min_length=1, max_length=20_000)]
    client_message_id: Annotated[str, Field(min_length=1, max_length=64)]
    input_source: InputSource = InputSource.TEXT


class MessageUpdate(ContractModel):
    """Solo cancelación de un mensaje en streaming."""

    status: MessageStatus | None = None


class MessageAccepted(OutModel):
    """Respuesta 202 de POST /chat/sessions/{id}/messages."""

    turn_id: Id
    message_id: Id


class AgentStatusOut(OutModel):
    """GET /agent/status. `detail` es texto seguro, sin secretos."""

    state: AgentState
    provider: str | None = None
    model: str | None = None
    detail: str | None = None


class MessageOut(OutModel):
    """En la API se llaman `session_id` y `text`; en la BD, `conversation_id` y `content`."""

    id: Id
    session_id: Id
    turn_id: Id | None = None
    role: MessageRole
    text: str
    status: MessageStatus
    created_at: Instant


class AgentTurnCreate(ContractModel):
    conversation_id: Id
    input_source: InputSource = InputSource.TEXT


class AgentTurnUpdate(ContractModel):
    status: TurnStatus | None = None


class AgentTurnOut(OutModel):
    id: Id
    conversation_id: Id
    correlation_id: str
    status: TurnStatus
    input_source: InputSource
    error_code: str | None = None
    created_at: Instant
    started_at: Instant | None = None
    ended_at: Instant | None = None
