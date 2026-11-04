"""HTTP models of /api/v1/voice."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

VoiceStateName = Literal[
    "off", "idle", "armed", "listening", "transcribing", "waiting", "speaking", "error"
]
ListenMode = Literal["push_to_talk", "wakeword"]
UnavailableReason = Literal["disabled", "misconfigured", "not_responding"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VoiceProviders(_Strict):
    stt: str | None = None
    tts: str | None = None
    tts_active: str | None = None
    vad: str | None = None
    wakeword: str | None = None
    audio: str | None = None


class VoiceReady(_Strict):
    stt: bool = False
    tts: bool = False
    vad: bool = False


class VoiceStatus(_Strict):
    """`status` of the IPC contract, plus whether the backend can reach the process."""

    available: bool
    unavailable_reason: UnavailableReason | None = None
    state: VoiceStateName = "off"
    mic_enabled: bool = False
    listen_mode: ListenMode = "push_to_talk"
    wakeword_available: bool = False
    barge_in: bool = False
    providers: VoiceProviders = VoiceProviders()
    ready: VoiceReady = VoiceReady()
    turn_id: str | None = None
    utterance_id: str | None = None


class MicRequest(_Strict):
    enabled: bool


class MicResponse(_Strict):
    enabled: bool


class WakewordRequest(_Strict):
    enabled: bool


class WakewordResponse(_Strict):
    enabled: bool


class ListenStartResponse(_Strict):
    turn_id: str


class VoiceAck(_Strict):
    ok: Literal[True] = True
