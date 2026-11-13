"""Puertos de la voz v2 (plan de voz v2 §4.7). CONGELADO por WP0: nadie más lo edita.

Pipecat es la abstracción: cada proveedor expone una fábrica `create(...)` que devuelve objetos de
Pipecat, registrada en `voice/registry.py`. Este módulo solo declara las firmas, el estado de sesión
y el control (`Ctl`), y se importa sin Pipecat instalado.

Firmas de las fábricas `create` por clase (`registry.create(kind, name, *args)`):

    stt(cfg, shared) -> STTService
    vad(cfg) -> VADAnalyzer
    turn_stop(cfg, shared) -> BaseUserTurnStopStrategy
    turn_start(cfg, ctl) -> list[BaseUserTurnStartStrategy]
    wake(cfg, shared, ctl) -> FrameProcessor                      # WakeGate (solo audio)
    tts(cfg, shared, profile: ResolvedProfile) -> TTSProvider
    tts_chain(cfg, ctl, providers: list[TTSProvider]) -> FrameProcessor   # ServiceSwitcher
    mixer(cfg, ctl) -> BaseAudioMixer                             # DuckMixer
    channel(cfg) -> Channel

`cfg` es `voice.config.VoiceConfig`. Las fábricas no descargan nada: si falta un modelo, fallan.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeVar

if TYPE_CHECKING:
    from pipecat.audio.mixers.base_audio_mixer import BaseAudioMixer
    from pipecat.audio.vad.vad_analyzer import VADAnalyzer
    from pipecat.processors.frame_processor import FrameProcessor
    from pipecat.services.stt_service import STTService
    from pipecat.services.tts_service import TTSService
    from pipecat.transports.base_transport import BaseTransport
    from pipecat.turns.user_start import BaseUserTurnStartStrategy
    from pipecat.turns.user_stop import BaseUserTurnStopStrategy

    from voice.config import VoiceConfig

T = TypeVar("T")

Trigger = Literal["wake", "hotkey", "ui", "followup"]  # = drakter_contracts.voice_ipc.Trigger
Mode = Literal["standby", "conversation"]


class Shared(Protocol):
    """Caché por proceso: los modelos (Moonshine, Kokoro, openWakeWord, Smart Turn) se cargan una vez."""

    models_dir: Path

    def get(self, key: str, loader: Callable[[], T]) -> T: ...


@dataclass(frozen=True)
class ResolvedProfile:
    """`voice` es el reference_id resuelto en ejecución desde voces.toml. Nunca se loguea."""

    name: str
    voice: str | None = None

    def __repr__(self) -> str:  # el ID de voz no sale ni en trazas
        return f"ResolvedProfile(name={self.name!r}, voice={'***' if self.voice else None})"


@dataclass(frozen=True)
class TTSProvider:
    service: TTSService
    name: str
    expressive: bool  # admite etiquetas [tag] (Fish); si no, se le quitan con strip_tags


class Channel(Protocol):
    """Canal de transporte (WebRTC). El núcleo monta un `PipelineTask` por conexión."""

    on_connection: Callable[[BaseTransport], Awaitable[None]]

    async def accept_offer(
        self, sdp: str, type: str, pc_id: str | None, restart_pc: bool | None
    ) -> dict[str, Any]: ...  # {sdp, type: "answer", pc_id}

    async def close(self) -> None: ...


@dataclass
class SessionState:
    """Estado de la sesión de voz, fuera del pipeline. Cada campo lo escribe solo su dueño."""

    mode: Mode = "standby"  # session.py (Ctl.set_mode)
    trigger: Trigger | None = None  # session.py / WakeGate vía ctl.set_mode
    connected: bool = False  # session.py
    bot_speaking: bool = False  # PlaybackTracker
    spoken_tail: str = ""  # PlaybackTracker (últimos 200 caracteres dichos)
    awaiting_answer: bool = False  # PlaybackTracker (la última frase dicha acaba en «?»)
    turn_id: str | None = None  # el puente
    speech_id: int | None = None  # el puente
    turn_phase: str = "done"  # el puente
    tts_enabled: bool = True  # voice.config
    profile: str = "natural"  # voice.config
    wake_enabled: bool = True  # voice.config
    expression: str = "llm"  # voice.config
    tts_active: Literal["fish", "local"] = "fish"  # el failover


class Ctl(Protocol):
    """Control de la sesión. Lo implementa `voice/session.py` (WP1)."""

    state: SessionState

    async def emit(self, type: str, payload: dict[str, Any]) -> None: ...

    async def interrupt(self, reason: str) -> None: ...  # InterruptionFrame; el puente marca el speech cortado

    async def play_phrase(self, key: str, when: str = "now") -> None: ...  # no suena si tts_enabled es falso

    def set_duck(self, on: bool) -> None: ...

    async def set_mode(self, mode: str, trigger: str) -> None: ...  # único dueño del modo; emite voice.state


# Firmas de las fábricas, para anotar los módulos de proveedores.
SttFactory = Callable[["VoiceConfig", Shared], "STTService"]
VadFactory = Callable[["VoiceConfig"], "VADAnalyzer"]
TurnStopFactory = Callable[["VoiceConfig", Shared], "BaseUserTurnStopStrategy"]
TurnStartFactory = Callable[["VoiceConfig", Ctl], "list[BaseUserTurnStartStrategy]"]
WakeFactory = Callable[["VoiceConfig", Shared, Ctl], "FrameProcessor"]
TtsFactory = Callable[["VoiceConfig", Shared, ResolvedProfile], TTSProvider]
TtsChainFactory = Callable[["VoiceConfig", Ctl, "list[TTSProvider]"], "FrameProcessor"]
MixerFactory = Callable[["VoiceConfig", Ctl], "BaseAudioMixer"]
ChannelFactory = Callable[["VoiceConfig"], Channel]
