"""Eventos WebSocket v1: un único flujo servidor→cliente en `WS /api/v1/events`.

`version` es la versión del payload de ese `type`; la del protocolo va en el subprotocolo `drakter.v1`.
`voice.*` es experimental hasta que el frente de voz mida latencia.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Final, Literal

from pydantic import BaseModel

from .common import ActorType, EntityType, Id, Instant


class AgentState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    EXECUTING = "executing"
    SUCCESS = "success"
    ERROR = "error"
    INTERRUPTED = "interrupted"
    OFFLINE = "offline"


class EventEnvelope(BaseModel):
    event_id: Id
    seq: int
    boot_id: Id
    timestamp: Instant
    type: str
    version: int = 1
    correlation_id: str | None = None
    payload: dict[str, Any]


# agent.*
class AgentStatusChanged(BaseModel):
    state: AgentState
    previous: AgentState | None = None
    turn_id: Id | None = None
    reason: str | None = None


class AgentExpressionChanged(BaseModel):
    expression: str
    intensity: float | None = None
    turn_id: Id | None = None


class TurnRef(BaseModel):
    session_id: Id
    turn_id: Id


class AgentTurnStarted(TurnRef):
    input_source: Literal["text", "voice"] = "text"


class AgentTurnFinished(TurnRef):
    outcome: Literal["completed", "failed", "cancelled", "interrupted"]


class AgentMessageStarted(TurnRef):
    message_id: Id


class AgentMessageDelta(TurnRef):
    delta: str


class AgentMessageCompleted(TurnRef):
    """Lleva el texto completo: perder deltas se corrige solo."""

    message_id: Id
    text: str


class AgentToolStarted(TurnRef):
    tool: str
    call_id: str
    source: Literal["drakter", "hermes"] = "drakter"


class AgentToolCompleted(AgentToolStarted):
    error: bool = False


class AgentError(BaseModel):
    session_id: Id | None = None
    turn_id: Id | None = None
    code: str
    message: str
    retryable: bool = False


# confirmation.*
class ConfirmationRequested(BaseModel):
    action_id: Id
    session_id: Id | None = None
    turn_id: Id | None = None
    tool: str
    summary: str
    affected_count: int | None = None
    expires_at: Instant


class ConfirmationResolved(BaseModel):
    action_id: Id
    status: Literal["approved", "rejected", "expired", "executed", "failed"]
    error_code: str | None = None


# workspace.* (sin contenido; se emiten solo tras COMMIT)
class WorkspaceEntityChange(BaseModel):
    entity_type: EntityType
    entity_id: Id
    revision: int
    changed_fields: list[str] = []
    actor_type: ActorType


class WorkspaceRelationshipChange(BaseModel):
    relationship_id: Id
    relationship_type: str
    source_type: EntityType
    source_id: Id
    target_type: EntityType
    target_id: Id
    actor_type: ActorType


# storage.*, notification.*, system.*
class StorageIndexProgress(BaseModel):
    job_id: Id
    done: int
    total: int | None = None
    state: Literal["running", "completed", "failed"]


class NotificationCreated(BaseModel):
    notification_id: Id
    kind: str
    title: str
    severity: Literal["info", "success", "warning", "error"] = "info"


class SystemHealthChanged(BaseModel):
    component: Literal["backend", "hermes", "memory", "voice", "database"]
    status: Literal["ok", "degraded", "down"]
    detail: str | None = None


class SystemResyncRequired(BaseModel):
    reason: Literal["buffer_overflow", "boot_changed", "client_lagging"]


# voice.* (experimental, sin audio por este canal)
class VoiceUtterance(BaseModel):
    utterance_id: Id


class VoiceListeningStarted(BaseModel):
    trigger: Literal["wakeword", "push_to_talk"]


class VoiceWakewordDetected(BaseModel):
    score: float | None = None


class VoiceTranscription(VoiceUtterance):
    text: str


class VoicePlaybackLevel(VoiceUtterance):
    level: float


class VoiceProfileChanged(BaseModel):
    """Perfil de voz activo. Lleva el nombre del perfil, nunca su ID de Fish."""

    profile: str
    previous: str | None = None


EVENTS: Final[dict[str, type[BaseModel]]] = {
    "agent.status_changed": AgentStatusChanged,
    "agent.expression_changed": AgentExpressionChanged,
    "agent.turn_started": AgentTurnStarted,
    "agent.turn_finished": AgentTurnFinished,
    "agent.message_started": AgentMessageStarted,
    "agent.message_delta": AgentMessageDelta,
    "agent.message_completed": AgentMessageCompleted,
    "agent.tool_started": AgentToolStarted,
    "agent.tool_completed": AgentToolCompleted,
    "agent.error": AgentError,
    "confirmation.requested": ConfirmationRequested,
    "confirmation.resolved": ConfirmationResolved,
    "workspace.entity_created": WorkspaceEntityChange,
    "workspace.entity_updated": WorkspaceEntityChange,
    "workspace.entity_archived": WorkspaceEntityChange,
    "workspace.entity_restored": WorkspaceEntityChange,
    "workspace.entity_deleted": WorkspaceEntityChange,
    "workspace.relationship_created": WorkspaceRelationshipChange,
    "workspace.relationship_deleted": WorkspaceRelationshipChange,
    "storage.index_progress": StorageIndexProgress,
    "notification.created": NotificationCreated,
    "system.health_changed": SystemHealthChanged,
    "system.resync_required": SystemResyncRequired,
    "voice.wakeword_detected": VoiceWakewordDetected,
    "voice.listening_started": VoiceListeningStarted,
    "voice.speech_ended": VoiceUtterance,
    "voice.transcription_partial": VoiceTranscription,
    "voice.transcription_completed": VoiceTranscription,
    "voice.playback_started": VoiceUtterance,
    "voice.playback_level": VoicePlaybackLevel,
    "voice.playback_stopped": VoiceUtterance,
    "voice.playback_interrupted": VoiceUtterance,
    "voice.profile_changed": VoiceProfileChanged,
}
EXPERIMENTAL_PREFIXES: Final = ("voice.",)
