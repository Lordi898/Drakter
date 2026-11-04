from enum import StrEnum
from typing import Annotated

from pydantic import Field

from ..common import ContractModel, Id, Instant
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


class MessageCreate(ContractModel):
    """Mensaje del usuario; arranca un turno. `client_message_id` evita duplicados al reintentar."""

    content: Annotated[str, Field(min_length=1, max_length=20_000)]
    client_message_id: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    input_source: InputSource = InputSource.TEXT


class MessageUpdate(ContractModel):
    """Solo cancelación de un mensaje en streaming."""

    status: MessageStatus | None = None


class MessageOut(OutModel):
    id: Id
    conversation_id: Id
    turn_id: Id | None = None
    role: MessageRole
    content: str
    client_message_id: str | None = None
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
