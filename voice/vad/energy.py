"""Model-free VAD: RMS level mapped to a pseudo-probability. Fallback when Silero is missing."""

from __future__ import annotations

import numpy as np

from voice.config import VoiceConfig
from voice.contracts import AudioFrame

# RMS (full scale 1.0) at which the output crosses 0.5 for the default vad_threshold.
_MID_RMS = 0.01


class EnergyVAD:
    name = "energy"

    def __init__(self, config: VoiceConfig) -> None:
        # p = r^2 / (r^2 + mid^2): 0.5 at RMS 0.01, ~0.99 at 0.1, ~0 for silence.
        self._mid = _MID_RMS

    def load(self) -> None:
        pass

    def process(self, frame: AudioFrame) -> float:
        pcm = frame.pcm
        if pcm.size == 0:
            return 0.0
        rms2 = float(np.mean(np.square(pcm, dtype=np.float32)))
        return rms2 / (rms2 + self._mid * self._mid)

    def reset(self) -> None:
        pass

    def close(self) -> None:
        pass
