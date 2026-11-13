"""Frozen interfaces of the voice pipeline. Every engine implements one Protocol here.

Engines are synchronous and blocking. VoiceManager runs them on worker threads and
never imports a concrete engine: it receives them from voice/registry.py. Heavy
libraries are imported lazily inside load(), so `import voice.contracts` needs numpy only.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, Literal, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

SAMPLE_RATE: Final = 16_000  # mic and STT/VAD input
FRAME_SAMPLES: Final = 512  # 32 ms; the frame size Silero expects at 16 kHz
FRAME_MS: Final = 32

Pcm = NDArray[np.float32]  # mono, range [-1, 1]


class VoiceError(Exception):
    """Recoverable engine failure. `code` is one of ERROR_CODES; message has no user text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ERROR_CODES: Final = frozenset(
    {
        "model_missing",  # the model is not on disk; nothing is ever downloaded on its own
        "dependency_missing",  # library or binary not installed
        "engine_failed",  # engine raised while running
        "audio_device",  # capture or playback device failed or vanished
        "cancelled",  # internal: stopped through CancelToken, never shown as an error
        "invalid_request",
    }
)


class CancelToken:
    """Cooperative cancellation. Engines check it between chunks or segments."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


class VoiceState(StrEnum):
    OFF = "off"  # microphone disabled; capture device closed
    IDLE = "idle"  # microphone allowed, nothing in progress
    ARMED = "armed"  # wakeword only: capture open, audio dropped after detection check
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    WAITING = "waiting"  # transcript delivered, waiting for text to speak
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AudioFrame:
    pcm: Pcm  # exactly FRAME_SAMPLES at SAMPLE_RATE
    captured_ns: int  # time.perf_counter_ns() when read


@dataclass(frozen=True, slots=True)
class PcmChunk:
    pcm: Pcm
    sample_rate: int


@dataclass(frozen=True, slots=True)
class WakeDetection:
    keyword: str
    score: float


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    text: str
    start_s: float
    end_s: float
    no_speech_prob: float | None = None


@dataclass(frozen=True, slots=True)
class VoiceInfo:
    id: str
    language: str  # BCP-47 style, for example "es-ES"
    gender: str | None = None


@dataclass(frozen=True, slots=True)
class TTSCapabilities:
    """What the engine really does. The personality engine must not exceed this."""

    speed: bool
    voices: bool
    streaming: bool  # yields audio before the whole text is synthesised
    intonation: bool = False
    emotion: bool = False
    extra_params: frozenset[str] = frozenset()  # engine-specific names accepted in VoiceParams.extra


@dataclass(frozen=True, slots=True)
class VoiceParams:
    """Applied params. Volume and pauses are applied by the player, so they work on any engine."""

    voice: str | None = None
    speed: float = 1.0
    gain: float = 1.0
    pause_after_ms: int = 0
    extra: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VoiceContext:
    """Input of the Voice Personality Engine (MASTER_PLAN §21.3)."""

    intent: str = "inform"
    agent_state: str = "speaking"
    expression: str = "neutral"
    priority: Literal["low", "normal", "high"] = "normal"


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    text: str
    params: VoiceParams
    ignored: tuple[str, ...] = ()  # requested controls the engine cannot apply


@runtime_checkable
class WakeWordProvider(Protocol):
    name: str

    def load(self) -> None: ...
    def process(self, frame: AudioFrame) -> WakeDetection | None: ...
    def reset(self) -> None: ...
    def close(self) -> None: ...


@runtime_checkable
class VADProvider(Protocol):
    name: str

    def load(self) -> None: ...
    def process(self, frame: AudioFrame) -> float:
        """Speech probability in [0, 1]. Keeps streaming state between calls."""
        ...

    def reset(self) -> None: ...
    def close(self) -> None: ...


@runtime_checkable
class STTProvider(Protocol):
    name: str

    def load(self) -> None: ...
    def transcribe(
        self, audio: Pcm, *, language: str | None, cancel: CancelToken
    ) -> Iterator[TranscriptSegment]:
        """Lazily yields segments as they are decoded. Stops early if `cancel` fires."""
        ...

    def close(self) -> None: ...


@runtime_checkable
class TTSProvider(Protocol):
    name: str
    capabilities: TTSCapabilities

    def load(self) -> None: ...
    def voices(self) -> list[VoiceInfo]: ...
    def synthesize(self, text: str, params: VoiceParams, cancel: CancelToken) -> Iterator[PcmChunk]: ...
    def close(self) -> None: ...


@runtime_checkable
class AudioCapture(Protocol):
    """Microphone. stop() must release the device for real: privacy depends on it."""

    name: str

    def start(self, on_frame: Callable[[AudioFrame], None], on_error: Callable[[VoiceError], None]) -> None: ...
    def stop(self) -> None: ...
    @property
    def active(self) -> bool: ...


@runtime_checkable
class AudioSink(Protocol):
    """Speaker. write() blocks; abort() may be called from another thread and cuts sound now."""

    name: str

    def open(self, sample_rate: int) -> None: ...
    def write(self, pcm: Pcm) -> None: ...
    def drain(self) -> None: ...
    def abort(self) -> None: ...
    def close(self) -> None: ...


StopReason = Literal["completed", "interrupted", "error"]


class PlayerListener(Protocol):
    """Called from the player thread; the manager hops back to its event loop."""

    def on_playback_started(self, utterance_id: str, started_ns: int) -> None: ...
    def on_level(self, utterance_id: str, level: float, position_ms: int) -> None: ...
    def on_playback_stopped(self, utterance_id: str, reason: StopReason, played_ms: int) -> None: ...


# Event names crossing the IPC socket and then the WebSocket (`experimental` until measured).
EVENT_VERSION: Final = 1
EVENTS: Final = frozenset(
    {
        "voice.state_changed",
        "voice.mic_changed",
        "voice.wakeword_detected",
        "voice.listening_started",
        "voice.speech_started",
        "voice.speech_ended",
        "voice.listening_stopped",
        "voice.transcription_partial",
        "voice.transcription_completed",
        "voice.playback_started",
        "voice.playback_level",
        "voice.playback_stopped",
        "voice.playback_interrupted",
        "voice.metrics",
        "voice.error",
    }
)
