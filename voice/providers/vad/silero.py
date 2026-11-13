"""VAD Silero (V-07): `SileroVADAnalyzer` con el modelo del wheel de Pipecat, sin ruta ni descarga.

`stop_secs=0.2` es fijo: Smart Turn v3 asume ese silencio corto y decide él el fin de turno.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

if TYPE_CHECKING:
    from voice.config import VoiceConfig

STOP_SECS = 0.2  # no cambiar: Smart Turn asume 0,2 s


def create(cfg: VoiceConfig) -> SileroVADAnalyzer:
    """Fábrica `vad(cfg)` (plan §4.7)."""
    params = VADParams(
        confidence=float(getattr(cfg, "vad_confidence", 0.7)),
        start_secs=float(getattr(cfg, "vad_start_secs", 0.2)),
        stop_secs=STOP_SECS,
        min_volume=float(getattr(cfg, "vad_min_volume", 0.6)),
    )
    return SileroVADAnalyzer(sample_rate=16000, params=params)
