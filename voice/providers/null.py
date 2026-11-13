"""Proveedores vacíos: el proceso arranca sin modelos, sin red y sin los demás paquetes.

`registry.create(kind, "null", *args)` llama a `create(kind, *args)`. Sirven para arrancar y para
las comprobaciones (`voice/tests/check_pipeline.py`); no reconocen ni sintetizan voz de verdad.
"""

from __future__ import annotations

import math
import struct
from collections.abc import AsyncGenerator
from typing import Any

from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    InterruptionFrame,
    TTSAudioRawFrame,
    TTSTextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.settings import STTSettings, TTSSettings
from pipecat.services.stt_service import STTService
from pipecat.services.tts_service import TTSService
from pipecat.turns.user_start import VADUserTurnStartStrategy
from pipecat.turns.user_stop import SpeechTimeoutUserTurnStopStrategy

from voice.ports import TTSProvider

TONE_RATE = 24000


class Passthrough(FrameProcessor):
    """No hace nada: deja pasar todos los frames."""

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)

    async def play(self, key: str, when: str = "now") -> None:  # como PhrasePlayer
        return None


class NullSTT(STTService):
    """No transcribe: consume el audio y no emite texto."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(settings=STTSettings(model=None, language=None), **kwargs)

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:
        return
        yield  # pragma: no cover - lo convierte en generador asíncrono


class EnergyVAD(VADAnalyzer):
    """VAD por energía, sin modelo. Suficiente para un wav limpio; no para un micrófono real."""

    def __init__(self) -> None:
        super().__init__(sample_rate=16000, params=VADParams(stop_secs=0.2))

    def num_frames_required(self) -> int:
        return 320  # 20 ms a 16 kHz

    def voice_confidence(self, buffer: bytes) -> float:
        count = len(buffer) // 2
        if not count:
            return 0.0
        samples = struct.unpack(f"<{count}h", buffer[: count * 2])
        rms = math.sqrt(sum(s * s for s in samples) / count) / 32768.0
        return 1.0 if rms > 0.02 else 0.0


class ToneTTS(TTSService):
    """TTS simulado: un tono de 60 ms por carácter (máximo 3 s). Da audio real que medir."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            push_start_frame=True,
            push_stop_frames=True,
            sample_rate=TONE_RATE,
            settings=TTSSettings(model=None, voice=None, language=None),
            **kwargs,
        )

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame | None, None]:
        seconds = min(3.0, 0.06 * max(1, len(text)))
        chunk = TONE_RATE // 50  # 20 ms
        for start in range(0, int(seconds * TONE_RATE), chunk):
            samples = (int(6000 * math.sin(2 * math.pi * 440 * (start + i) / TONE_RATE)) for i in range(chunk))
            yield TTSAudioRawFrame(
                audio=struct.pack(f"<{chunk}h", *samples),
                sample_rate=TONE_RATE,
                num_channels=1,
                context_id=context_id,
            )


class NullPlayback(FrameProcessor):
    """Sustituto mínimo del PlaybackTracker de WP3: mantiene `bot_speaking` y emite `voice.playback`."""

    def __init__(self, ctl: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ctl = ctl
        self._sentences = 0

    async def _emit(self, state: str, **extra: Any) -> None:
        s = self._ctl.state
        if s.turn_id is None or s.speech_id is None:
            return  # una frase fija sin speech: no hay a quién atribuirla
        payload = {"turn_id": s.turn_id, "speech_id": s.speech_id, "state": state, "sentence_index": self._sentences}
        await self._ctl.emit("voice.playback", {**payload, **extra})

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        s = self._ctl.state
        if isinstance(frame, BotStartedSpeakingFrame) and not s.bot_speaking:
            s.bot_speaking, self._sentences = True, 0
            await self._emit("started")
        elif isinstance(frame, TTSTextFrame):
            s.spoken_tail = (s.spoken_tail + " " + frame.text)[-200:]
            s.awaiting_answer = frame.text.rstrip().endswith("?")
        elif isinstance(frame, InterruptionFrame) and s.bot_speaking:
            s.bot_speaking = False
            pending = getattr(self._ctl, "speech_text", "")
            await self._emit("interrupted", heard_tail=s.spoken_tail[-80:], pending_head=pending[:200])
        elif isinstance(frame, BotStoppedSpeakingFrame) and s.bot_speaking:
            s.bot_speaking = False
            await self._emit("finished")
        await self.push_frame(frame, direction)


def create(kind: str, *args: Any, **kwargs: Any) -> Any:
    match kind:
        case "stt":
            return NullSTT()
        case "vad":
            return EnergyVAD()
        case "turn_start":
            return [VADUserTurnStartStrategy()]
        case "turn_stop":
            return SpeechTimeoutUserTurnStopStrategy(user_speech_timeout=0.6)
        case "tts":
            return TTSProvider(service=ToneTTS(), name="null", expressive=False)
        case "tts_chain":
            providers: list[TTSProvider] = args[2]
            return providers[0].service  # sin conmutación
        case "playback":
            return NullPlayback(args[1])
        case "wake" | "guard" | "phrases":
            return Passthrough()
        case "mixer" | "idle":
            return None  # sin mixer la salida no genera silencio continuo; idle no engancha nada
    raise KeyError(f"no hay proveedor vacío para: {kind}")
