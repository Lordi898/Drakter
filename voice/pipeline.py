"""Montaje del pipeline de Pipecat: uno por conexión WebRTC.

    input → WakeGate → VADProcessor → STT → UserTurnProcessor (único) → BackendBridgeProcessor
          → SpeechGuard → cadena TTS → PhrasePlayer → output [mixer] → PlaybackTracker

Todo se crea con `registry.create`: cambiar un proveedor es cambiar un nombre en `VoiceConfig`.
Los modelos pesados salen de `shared` (una carga por proceso); los procesadores son de usar y
tirar, porque un `FrameProcessor` no sobrevive a su pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.turns.user_turn_processor import UserTurnProcessor
from pipecat.turns.user_turn_strategies import UserTurnStrategies

from voice.bridge import BackendBridgeProcessor
from voice.config import NULL
from voice.metrics import MetricsSink, create_observer
from voice.ports import ResolvedProfile
from voice.registry import create
from voice.session import Parts, Session, resolve_profile

if TYPE_CHECKING:
    from pipecat.transports.base_transport import BaseTransport

    from voice.config import VoiceConfig
    from voice.ports import Shared


def build(transport: BaseTransport, ctl: Session, shared: Shared, cfg: VoiceConfig) -> PipelineWorker:
    """Devuelve la tarea del pipeline (`PipelineWorker`; `PipelineTask` es su alias deprecado)."""
    state = ctl.state
    # El ID de voz solo se resuelve si hay Fish; nunca se registra.
    profile = resolve_profile(state.profile) if ctl.uses_fish() else ResolvedProfile(state.profile)

    wake = create("wake", cfg.wake, cfg, shared, ctl)
    vad = VADProcessor(vad_analyzer=create("vad", cfg.vad, cfg))
    stt = create("stt", cfg.stt, cfg, shared)
    start = create("turn_start", cfg.turn_start, cfg, ctl)
    turns = UserTurnProcessor(
        user_turn_strategies=UserTurnStrategies(
            start=start, stop=[create("turn_stop", cfg.turn_stop, cfg, shared)]
        ),
        user_idle_timeout=cfg.idle_nudge_s,
    )
    create("idle", cfg.idle, turns, ctl, cfg)  # engancha on_user_turn_idle
    bridge = BackendBridgeProcessor(ctl, cfg, start_strategies=start)
    guard = _speech("guard", cfg.guard)
    providers = [create("tts", name, cfg, shared, profile) for name in cfg.tts]
    tts = create("tts_chain", cfg.tts_chain, cfg, ctl, providers)
    providers = getattr(tts, "tts_providers", providers)  # los que el failover dejó en uso
    phrases = _speech("phrases", cfg.phrases, cfg, ctl, profile)
    # DESPUÉS de la salida: cuenta lo oído. El texto del speech lo acumula el guard.
    playback = _speech("playback", cfg.playback, ctl, text_source=getattr(guard, "speech_text", None))

    pipeline = Pipeline(
        [transport.input(), wake, vad, stt, turns, bridge, guard, tts, phrases, transport.output(), playback]
    )
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, audio_in_sample_rate=16000, audio_out_sample_rate=24000),
        observers=[create_observer(ctl, MetricsSink(cfg.metrics_path))],
        idle_timeout_secs=None,  # en reposo el pipeline calla durante horas: no es inactividad
        enable_rtvi=False,  # cliente WebRTC propio, sin RTVI
    )
    ctl.bind(Parts(worker=worker, bridge=bridge, phrases=phrases, tts=list(providers)))
    return worker


def _speech(kind: str, name: str, *args: Any, **kwargs: Any) -> Any:
    """Piezas de `voice/speech/` (sin entrada en la tabla del registro), o su versión vacía."""
    if name == NULL:
        return create(kind, NULL, *args, **kwargs)
    if kind == "guard":
        from voice.speech.guard import SpeechGuard

        return SpeechGuard()
    if kind == "phrases":
        from voice.speech.phrases import PhrasePlayer

        return PhrasePlayer(*args)
    from voice.speech.playback import PlaybackTracker

    return PlaybackTracker(*args, **kwargs)
