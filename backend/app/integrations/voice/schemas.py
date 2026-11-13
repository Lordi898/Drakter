"""HTTP models of /api/v1/voice: frozen in `drakter_contracts.voice_ipc` (plan §4.3)."""

from __future__ import annotations

from drakter_contracts.events import VoiceState
from drakter_contracts.voice_ipc import (
    VoiceActivateIn,
    VoiceModeIn,
    VoiceOfferIn,
    VoiceOfferOut,
    VoiceStatusOut,
)

__all__ = [
    "VoiceActivateIn",
    "VoiceModeIn",
    "VoiceOfferIn",
    "VoiceOfferOut",
    "VoiceState",
    "VoiceStatusOut",
]
