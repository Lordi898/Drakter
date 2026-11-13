"""Bajada de volumen del bot mientras se decide un barge-in (V-09).

`DuckMixer` va en `TransportParams.audio_out_mixer`: la salida lo aplica a cada `OutputAudioRawFrame`
del TTS justo al emitir (`transports/base_output.py`, `with_mixer`), así que el cambio se oye ya,
sin esperar a la cola. Con mixer la salida emite silencio continuo en reposo (se mide en WP9).

Quién lo mueve: `Ctl.set_duck(on)` (session.py, WP1) llama a `DuckMixer.set_duck(on)` del mixer de
la conexión activa. También acepta `MixerUpdateSettingsFrame(settings={"duck": bool})`.
Audio PCM s16 mono (la salida de la voz es mono).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from pipecat.audio.mixers.base_audio_mixer import BaseAudioMixer
from pipecat.frames.frames import MixerControlFrame, MixerEnableFrame, MixerUpdateSettingsFrame

if TYPE_CHECKING:
    from voice.config import VoiceConfig
    from voice.ports import Ctl

RAMP_S = 0.030


class DuckMixer(BaseAudioMixer):
    def __init__(self, duck_gain: float = 0.25) -> None:
        self._duck_gain = float(duck_gain)
        self._gain = 1.0  # ganancia aplicada al último sample
        self._target = 1.0
        self._step = 1.0  # cambio de ganancia por sample (se fija en start)
        self._enabled = True

    @property
    def ducked(self) -> bool:
        return self._target < 1.0

    def set_duck(self, on: bool) -> None:
        self._target = self._duck_gain if on else 1.0

    async def start(self, sample_rate: int) -> None:
        self._step = 1.0 / max(1.0, RAMP_S * sample_rate)

    async def stop(self) -> None:
        self._gain = self._target = 1.0

    async def process_frame(self, frame: MixerControlFrame) -> None:
        if isinstance(frame, MixerUpdateSettingsFrame) and "duck" in frame.settings:
            self.set_duck(bool(frame.settings["duck"]))
        elif isinstance(frame, MixerEnableFrame):
            self._enabled = frame.enable

    async def mix(self, audio: bytes) -> bytes:
        if not self._enabled or (self._gain == 1.0 and self._target == 1.0) or not audio:
            return audio
        samples = np.frombuffer(audio, dtype=np.int16)
        n = len(samples)
        if self._gain == self._target:
            gains = np.full(n, self._gain, dtype=np.float32)
        else:
            # Rampa lineal hacia el objetivo (30 ms de 1.0 a 0.0) y luego constante.
            direction = 1.0 if self._target > self._gain else -1.0
            ramp = self._gain + direction * self._step * np.arange(1, n + 1, dtype=np.float32)
            gains = np.minimum(ramp, self._target) if direction > 0 else np.maximum(ramp, self._target)
            self._gain = float(gains[-1])
        out = np.clip(samples.astype(np.float32) * gains, -32768, 32767).astype(np.int16)
        return out.tobytes()


def create(cfg: VoiceConfig, ctl: Ctl) -> DuckMixer:
    """Fábrica del registro: `("mixer", "duck")`. `ctl` no se usa: es Ctl quien llama a `set_duck`."""
    return DuckMixer(duck_gain=getattr(cfg, "duck_gain", 0.25))
