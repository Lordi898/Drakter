"""Wake word that never fires: default when there is no custom model."""

from __future__ import annotations

from voice.config import VoiceConfig
from voice.contracts import AudioFrame, WakeDetection


class NullWakeWord:
    name = "null"

    def __init__(self, config: VoiceConfig | None = None) -> None:
        pass

    def load(self) -> None:
        pass

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        return None

    def reset(self) -> None:
        pass

    def close(self) -> None:
        pass
