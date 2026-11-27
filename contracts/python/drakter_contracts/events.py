"""Eventos WebSocket v1: un único flujo servidor→cliente en `WS /api/v1/events`.

`version` es la versión del payload de ese `type`; la del protocolo va en el subprotocolo `drakter.v1`.
`voice.*` es experimental hasta que el frente de voz mida latencia. Voz v2 (Pipecat) usa `voice.state`,
`voice.playback`, `voice.error` y `voice.profile_changed`. `ui.mode` pide al escritorio cambiar de modo
de interfaz (Drakter o Jarvis) y `ui.appearance`, de avatar o de interfaz Jarvis: son solo estética y el
backend no guarda nada. `ui.floating` y `overlay.*` son del modo flotante (docs/floating/CONTRACT.md §6):
los consume Electron main, no el renderer principal.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Final, Literal

from pydantic import BaseModel, Field, model_validator

from .common import ActorType, EntityType, Id, Instant
from .floating import (
    OverlayClipboard,
    OverlayDraw,
    OverlayHands,
    OverlayInkClear,
    OverlayInkStale,
    OverlayTrail,
    UiFloatingRequested,
)


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
    job_id: Id | None = None  # confirmación pedida desde un trabajo en segundo plano


class ConfirmationResolved(BaseModel):
    action_id: Id
    status: Literal["approved", "rejected", "expired", "executed", "failed"]
    error_code: str | None = None


# chat.*
class ChatUserMessage(BaseModel):
    """Mensaje del usuario ya guardado, escrito o dictado. El renderer adopta `session_id`."""

    message_id: Id
    session_id: Id
    turn_id: Id
    text: str
    input_source: Literal["text", "voice"] = "text"
    created_at: Instant


# job.* (trabajos en segundo plano; no alimentan el personaje)
class JobStarted(BaseModel):
    job_id: Id
    title: str
    lane: str
    created_at: Instant


class JobProgress(BaseModel):
    job_id: Id
    state: Literal["running"] = "running"
    elapsed_s: int
    tool_calls: int
    last_tool: str | None = None


class JobFinished(BaseModel):
    job_id: Id
    state: Literal["completed", "failed", "cancelled"]
    reason: str | None = None
    pending_actions: int = 0
    finished_at: Instant


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


# voice.* (sin audio por este canal)
class VoiceProfileChanged(BaseModel):
    """Perfil de voz activo. Lleva el nombre del perfil, nunca su ID de Fish."""

    profile: str
    previous: str | None = None


# voice.* v2 (Pipecat). Snapshot: se reemite en cada cambio y tras un resync. Sin `mic` (lo calcula el renderer).
class VoiceState(BaseModel):
    connected: bool
    mode: Literal["standby", "conversation"]
    tts: Literal["fish", "local"]
    profile: str
    wake_enabled: bool


class VoicePlayback(BaseModel):
    """Progreso de reproducción. Sin texto: lo oído viaja solo por IPC al backend."""

    turn_id: Id
    speech_id: int
    state: Literal["started", "sentence_done", "finished", "interrupted"]
    sentence_index: int


class VoiceError(BaseModel):
    code: str
    stage: Literal["transport", "stt", "turn", "tts", "ipc", "wake"]
    recoverable: bool
    turn_id: Id | None = None
    message: Annotated[str, Field(max_length=160)] | None = None
    """Texto corto en español para la interfaz (opcional; nunca lleva datos del usuario ni del error)."""


# ui.* (aspecto del escritorio; sin datos del usuario)
class UiModeRequested(BaseModel):
    """Petición de cambiar el modo de la interfaz. El renderer decide si la aplica; no hay estado en el backend.

    `source`: `voice` (capa 0 de la voz, frase cerrada) o `agent` (herramienta `ui_set_mode`).
    `utt_id`: el del enunciado, solo si viene de la voz.
    """

    mode: Literal["jarvis", "drakter"]
    source: Literal["voice", "agent"]
    utt_id: Annotated[str, Field(max_length=64)] | None = None


# Listas cerradas de la apariencia (plan jarvis-seleccion.md). `none` = el personaje de siempre (.riv o SVG).
AvatarChoice = Literal[
    "holo-contorno", "holo-hilo", "holo-busto", "holo-orbe", "holo-filamento", "ascuario", "relojero",
    "filamento", "none",
]
JarvisLayoutChoice = Literal["nucleo", "holomesa", "visor"]


class UiAppearanceRequested(BaseModel):
    """Petición de cambiar el avatar y/o la interfaz del modo Jarvis. Solo estética: el renderer guarda la
    preferencia; el backend no guarda estado. Al menos uno de `avatar` o `layout`.

    `source`: `voice` (capa 0, frase cerrada) o `agent` (herramienta de apariencia).
    """

    avatar: AvatarChoice | None = None
    layout: JarvisLayoutChoice | None = None
    source: Literal["voice", "agent"]
    utt_id: Annotated[str, Field(max_length=64)] | None = None

    @model_validator(mode="after")
    def _something(self) -> UiAppearanceRequested:
        if self.avatar is None and self.layout is None:
            raise ValueError("ui.appearance needs avatar or layout")
        return self


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
    "chat.user_message": ChatUserMessage,
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
    "job.started": JobStarted,
    "job.progress": JobProgress,
    "job.finished": JobFinished,
    "voice.state": VoiceState,
    "voice.playback": VoicePlayback,
    "voice.error": VoiceError,
    "voice.profile_changed": VoiceProfileChanged,
    "ui.mode": UiModeRequested,
    "ui.appearance": UiAppearanceRequested,
    "ui.floating": UiFloatingRequested,
    "overlay.draw": OverlayDraw,
    "overlay.ink_clear": OverlayInkClear,
    "overlay.ink_stale": OverlayInkStale,
    "overlay.hands": OverlayHands,
    "overlay.trail": OverlayTrail,
    "overlay.clipboard": OverlayClipboard,
}
EXPERIMENTAL_PREFIXES: Final = ("voice.",)
