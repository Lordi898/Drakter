"""Normalized provider events: what any AgentProvider yields during a turn."""

from __future__ import annotations

from typing import Annotated, Final, Literal

from drakter_contracts.errors import ErrorCode
from pydantic import BaseModel, ConfigDict, Field

# Provider text never reaches the GUI: every failure is shown with one of these.
SAFE_MESSAGES: Final[dict[ErrorCode, str]] = {
    ErrorCode.AGENT_UNAVAILABLE: "El agente no está disponible ahora mismo.",
    ErrorCode.AGENT_BUSY: "El agente ya está atendiendo otro turno.",
    ErrorCode.AGENT_TIMEOUT: "El agente ha tardado demasiado en responder.",
    ErrorCode.AGENT_DISCONNECTED: "Se perdió la conexión con el agente; el resultado del turno es incierto.",
    ErrorCode.PROVIDER_AUTH: "El proveedor del modelo ha rechazado las credenciales.",
    ErrorCode.PROVIDER_ERROR: "El proveedor del modelo ha fallado.",
}

ToolSource = Literal["drakter", "hermes"]


class _AgentEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Thinking(_AgentEvent):
    type: Literal["thinking"] = "thinking"


class MessageDelta(_AgentEvent):
    type: Literal["message_delta"] = "message_delta"
    text: str


class ToolStarted(_AgentEvent):
    type: Literal["tool_started"] = "tool_started"
    tool: str
    call_id: str
    source: ToolSource = "drakter"


class ToolCompleted(_AgentEvent):
    type: Literal["tool_completed"] = "tool_completed"
    tool: str
    call_id: str
    error: bool = False
    source: ToolSource = "drakter"


class Steered(_AgentEvent):
    """Answer to a `steer`: accepted means Hermes took the correction into the same turn."""

    type: Literal["steered"] = "steered"
    accepted: bool


class ModelRetrying(_AgentEvent):
    """Hermes could not reach the model (transport error) and is retrying on its own."""

    type: Literal["model_retrying"] = "model_retrying"
    reason: str = "unknown"


class TurnCompleted(_AgentEvent):
    type: Literal["turn_completed"] = "turn_completed"
    text: str
    usage: dict[str, int] = Field(default_factory=dict)
    # A correction Hermes accepted but never consumed: the runtime opens a new turn with it.
    pending_steer: str | None = None


class TurnCancelled(_AgentEvent):
    type: Literal["turn_cancelled"] = "turn_cancelled"


class TurnFailed(_AgentEvent):
    type: Literal["turn_failed"] = "turn_failed"
    code: ErrorCode
    message: str
    retryable: bool = False


AgentEvent = Annotated[
    Thinking | MessageDelta | ToolStarted | ToolCompleted | Steered | ModelRetrying | TurnCompleted
    | TurnCancelled | TurnFailed,
    Field(discriminator="type"),
]
TERMINAL_EVENTS: Final = (TurnCompleted, TurnCancelled, TurnFailed)


def turn_failed(code: ErrorCode, *, retryable: bool = False) -> TurnFailed:
    return TurnFailed(code=code, message=SAFE_MESSAGES[code], retryable=retryable)
