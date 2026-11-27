"""IPC voz ↔ backend (plan de voz v2 §4.2) y modelos REST de `/api/v1/voice` (§4.3).

Transporte: UDS JSONL (`voice/ipc.py`), la voz es servidor y el backend cliente; máximo 256 KiB por
línea. Sobre común `IpcMessage`: `evt` (voz → backend), `cmd` (backend → voz) y su respuesta `ok`
(payload según `CMD_RESULTS`, `{}` si no figura) o `err` (`IpcErr`).
La voz solo emite texto de usuario: no aprueba confirmaciones ni toca BD ni hub.
"""

from __future__ import annotations

from typing import Annotated, Any, Final, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import ContractModel
from .events import AvatarChoice, JarvisLayoutChoice, VoiceState

MAX_LINE_BYTES: Final = 256 * 1024

Trigger = Literal["wake", "hotkey", "ui", "followup"]
Mode = Literal["standby", "conversation"]
TtsName = Literal["fish", "local"]
ErrorStage = Literal["transport", "stt", "turn", "tts", "ipc", "wake"]
SpeechOutcome = Literal["completed", "cancelled", "failed"]
PlaybackState = Literal["started", "sentence_done", "finished", "interrupted"]

# Lista cerrada. Textos en agent/identity/voice_phrases.es.toml (`clave = ["variante", …]`).
PhraseKey = Literal[
    "ack_1", "ack_2", "ack_3", "wait_1", "wait_2", "wait_3", "tool_generic", "confirm_on_screen",
    "rest_on_screen", "busy", "job_started", "job_done", "job_failed", "tts_fallback", "offline",
    "idle_nudge", "goodbye", "ui_jarvis", "ui_drakter", "ui_avatar", "ui_layout",
    "ui_floating_on", "ui_floating_off", "floating_unavailable",
]
PHRASE_KEYS: Final[tuple[str, ...]] = get_args(PhraseKey)


class IpcMessage(BaseModel):
    kind: Literal["evt", "cmd", "ok", "err"]
    id: str
    type: str
    payload: dict[str, Any] = {}


class IpcErr(BaseModel):
    code: str
    message: str


# ── voz → backend (evt) ─────────────────────────────────────────────────────
class EvtReady(BaseModel):
    pipecat: str = "1.16.0"
    stt: str
    tts: str
    wake: bool


class EvtState(BaseModel):
    connected: bool
    mode: Mode
    tts: TtsName
    profile: str


class EvtUserSpeech(BaseModel):
    utt_id: str
    phase: Literal["started", "stopped"]


class EvtUserTurn(BaseModel):
    utt_id: str
    text: str
    lang: Literal["es"] = "es"
    trigger: Trigger
    overlap: Literal["none", "bot_speaking", "agent_busy"] = "none"
    audio_ms: int
    stt_ms: int
    eot_ms: int


class EvtPlayback(BaseModel):
    """`heard_tail`/`pending_head` solo con `state="interrupted"`: texto hablado, no el del chat."""

    turn_id: str
    speech_id: int
    state: PlaybackState
    sentence_index: int
    heard_tail: Annotated[str, Field(max_length=80)] | None = None
    pending_head: Annotated[str, Field(max_length=200)] | None = None


class EvtLocalCommand(BaseModel):
    """Orden de la capa 0, ya aplicada por la voz. `ui_jarvis`/`ui_drakter`: cambiar el modo de la interfaz
    (el backend publica `ui.mode`). `ui_floating_on`/`ui_floating_off`: «modo flotante» / «quita el modo
    flotante» (el backend publica `ui.floating`, docs/floating/CONTRACT.md §10). `ui_appearance`: cambiar el avatar o la interfaz Jarvis, con
    exactamente uno de `avatar` o `layout` (el backend publica `ui.appearance`)."""

    command: Literal[
        "stop_speech", "rest", "close", "ui_jarvis", "ui_drakter", "ui_appearance",
        "ui_floating_on", "ui_floating_off",
    ]
    utt_id: str
    avatar: AvatarChoice | None = None
    layout: JarvisLayoutChoice | None = None

    @model_validator(mode="after")
    def _target(self) -> EvtLocalCommand:
        targets = (self.avatar is not None) + (self.layout is not None)
        if self.command == "ui_appearance" and targets != 1:
            raise ValueError("ui_appearance needs exactly one of avatar or layout")
        if self.command != "ui_appearance" and targets:
            raise ValueError("avatar/layout only go with ui_appearance")
        return self


class EvtTtsFallback(BaseModel):
    """Una vez por arranque. `from` es palabra reservada en Python: el atributo es `from_`."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    from_: Literal["fish"] = Field("fish", alias="from")
    to: Literal["local"] = "local"
    reason: Literal["auth", "quota", "rate_limit", "network", "expired", "unknown"]


class EvtMetrics(BaseModel):
    """Sin texto. `agent_ttft_ms` lo mide el backend."""

    turn_id: str | None = None
    endpointing_ms: int | None = None
    stt_ms: int | None = None
    tts_ttfa_ms: int | None = None
    total_ms: int | None = None
    false_ducks: int | None = None


class EvtError(BaseModel):
    code: str
    stage: ErrorStage
    recoverable: bool
    turn_id: str | None = None
    message: Annotated[str, Field(max_length=160)] | None = None
    """Texto corto en español para la interfaz (opcional; nunca lleva datos del usuario ni del error)."""


EVTS: Final[dict[str, type[BaseModel]]] = {
    "voice.ready": EvtReady,
    "voice.state": EvtState,
    "voice.user_speech": EvtUserSpeech,
    "voice.user_turn": EvtUserTurn,
    "voice.playback": EvtPlayback,
    "voice.local_command": EvtLocalCommand,
    "voice.tts_fallback": EvtTtsFallback,
    "voice.metrics": EvtMetrics,
    "voice.error": EvtError,
}


# ── backend → voz (cmd) ─────────────────────────────────────────────────────
class CmdRtcOffer(ContractModel):
    sdp: str
    type: Literal["offer"] = "offer"
    pc_id: str | None = None
    restart_pc: bool | None = None


class RtcAnswer(BaseModel):
    sdp: str
    type: Literal["answer"] = "answer"
    pc_id: str


class CmdSpeakOpen(ContractModel):
    """Abre un tramo de habla. `speech_id` es monótono por proceso de backend."""

    turn_id: str
    speech_id: int


class CmdSpeakDelta(ContractModel):
    """Texto crudo con etiquetas. Duplicado o speech cortado → `ok{ignored: true}`."""

    speech_id: int
    seq: int
    text: str


class CmdSpeakFlush(ContractModel):
    speech_id: int


class CmdSpeakClose(ContractModel):
    speech_id: int
    outcome: SpeechOutcome


class CmdSpeakStop(ContractModel):
    speech_id: int | None = None
    reason: Literal["barge_in", "user", "mute", "new_turn", "steered"]


class CmdSpeakBeat(ContractModel):
    """Modo flotante (docs/floating/CONTRACT.md §10): dice `text` como una locución propia con `speech_id`.

    Equivale a `speak.open` + `speak.delta` + `speak.close(completed)` en un solo comando. Se encola detrás de lo
    que ya suene en ese `turn_id` (FIFO, sin cortar ni ser cortada por otro tramo del mismo turno); la cortan
    `speak.stop` y el barge-in, como a cualquier tramo. Emite los `voice.playback` habituales con este
    `speech_id`. `ok{ignored: true}` si la voz está silenciada (`tts_enabled=false`) o sin conexión: el
    backend usa entonces el reloj local del overlay.
    """

    turn_id: str
    speech_id: int
    guide_id: str
    beat: Annotated[int, Field(ge=1, le=12)]
    text: Annotated[str, Field(min_length=1, max_length=240)]


class CmdSpeakPhrase(ContractModel):
    key: PhraseKey
    when: Literal["now", "when_silent"] = "now"


class CmdTurnPhase(ContractModel):
    turn_id: str
    phase: Literal["thinking", "executing", "done"]
    tool: str | None = None


class CmdVoiceConfig(ContractModel):
    tts_enabled: bool
    profile: str
    wake_enabled: bool
    expression: Literal["off", "llm"]


class CmdModeSet(ContractModel):
    mode: Mode
    trigger: Trigger


class CmdEmpty(ContractModel):
    """`status` y `shutdown` no llevan payload."""


class SpeakAck(BaseModel):
    ignored: bool = False


class StatusResult(BaseModel):
    state: dict[str, Any]
    metrics_last: dict[str, Any] | None = None


CMDS: Final[dict[str, type[BaseModel]]] = {
    "rtc.offer": CmdRtcOffer,
    "speak.open": CmdSpeakOpen,
    "speak.delta": CmdSpeakDelta,
    "speak.flush": CmdSpeakFlush,
    "speak.close": CmdSpeakClose,
    "speak.stop": CmdSpeakStop,
    "speak.beat": CmdSpeakBeat,
    "speak.phrase": CmdSpeakPhrase,
    "turn.phase": CmdTurnPhase,
    "voice.config": CmdVoiceConfig,
    "mode.set": CmdModeSet,
    "status": CmdEmpty,
    "shutdown": CmdEmpty,
}
CMD_RESULTS: Final[dict[str, type[BaseModel]]] = {
    "rtc.offer": RtcAnswer,
    "speak.delta": SpeakAck,
    "speak.beat": SpeakAck,
    "status": StatusResult,
}


# ── REST /api/v1/voice (§4.3) ───────────────────────────────────────────────
class VoiceOfferIn(ContractModel):
    sdp: Annotated[str, Field(min_length=1, max_length=65536)]
    type: Literal["offer"] = "offer"
    pc_id: str | None = None
    restart_pc: bool | None = None


class VoiceOfferOut(BaseModel):
    sdp: str
    type: Literal["answer"] = "answer"
    pc_id: str


class VoiceActivateIn(ContractModel):
    trigger: Literal["hotkey", "ui"]


class VoiceModeIn(ContractModel):
    mode: Mode


class VoiceStatusOut(VoiceState):
    """`VoiceState` (el payload de `voice.state`) más las últimas métricas, sin texto."""

    metrics_last: dict[str, Any] | None = None
