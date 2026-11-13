"""Voice process configuration, read from the environment only (no secrets here)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ListenMode = Literal["push_to_talk", "wakeword"]


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return default if raw is None or not raw.strip() else int(raw)


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return default if raw is None or not raw.strip() else float(raw)


def _str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    return default if raw is None or not raw.strip() else raw.strip()


def _path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser() if raw and raw.strip() else default


def _xdg(var: str, fallback: str) -> Path:
    raw = os.environ.get(var)
    return Path(raw) if raw else Path.home() / fallback


def _default_runtime_dir() -> Path:
    raw = os.environ.get("XDG_RUNTIME_DIR")
    return (Path(raw) if raw else Path(f"/run/user/{os.getuid()}")) / "drakter"


@dataclass(frozen=True)
class VoiceConfig:
    # Rutas. runtime_dir debe coincidir con Settings.runtime_dir del backend.
    runtime_dir: Path = field(default_factory=_default_runtime_dir)
    data_dir: Path = field(default_factory=lambda: _xdg("XDG_DATA_HOME", ".local/share") / "drakter")
    models_dir: Path | None = None  # por defecto data_dir/"voice"/"models"

    # STT
    stt_provider: str = "faster_whisper"
    stt_model: str = "small"  # "base" es la reserva si no cabe en RAM
    stt_device: str = "cpu"  # solo CPU: no hay GPU dedicada
    stt_compute_type: str = "int8"
    stt_language: str = "es"
    stt_beam_size: int = 1
    stt_threads: int = 4

    # TTS
    tts_provider: str = "kokoro"
    tts_fallback: str = "piper"  # "" desactiva el respaldo
    tts_voice: str = "ef_dora"
    tts_threads: int = 4  # 4 fue el mejor valor medido por drakter-5 con 8 hilos lógicos
    piper_python: Path | None = None  # intérprete del entorno donde vive piper-tts
    piper_voice: str = "es_ES-davefx-medium"

    # Escucha
    vad_provider: str = "silero"
    vad_threshold: float = 0.5
    vad_silence_ms: int = 800  # silencio que cierra la intervención
    vad_preroll_ms: int = 320
    max_utterance_s: int = 30
    wakeword_enabled: bool = False
    wakeword_provider: str = "null"  # "openwakeword" al tener modelo propio
    wakeword_model: Path | None = None
    wakeword_threshold: float = 0.5
    barge_in_enabled: bool = False  # interrupción por voz: requiere prueba real de eco
    barge_in_threshold: float = 0.8
    barge_in_min_ms: int = 320

    # Audio
    audio_backend: str = "auto"  # auto | pipewire | alsa | null
    input_device: str = ""
    output_device: str = ""
    level_hz: int = 15  # frecuencia de voice.playback_level
    output_latency_ms: int = 0  # desfase medible del altavoz, para la boca

    def __post_init__(self) -> None:
        if self.stt_device != "cpu":
            raise ValueError("stt_device must be 'cpu' in this version")

    @property
    def socket_path(self) -> Path:
        return self.runtime_dir / "voice.sock"

    @property
    def resolved_models_dir(self) -> Path:
        return self.models_dir or self.data_dir / "voice" / "models"

    @property
    def metrics_path(self) -> Path:
        return self.data_dir / "voice" / "metrics.jsonl"


def load_config() -> VoiceConfig:
    d = VoiceConfig()
    piper_python = os.environ.get("DRAKTER_PIPER_PYTHON")
    wake_model = os.environ.get("DRAKTER_WAKEWORD_MODEL")
    models = os.environ.get("DRAKTER_VOICE_MODELS_DIR")
    return VoiceConfig(
        runtime_dir=_path("DRAKTER_RUNTIME_DIR", d.runtime_dir),
        data_dir=_path("DRAKTER_DATA_DIR", d.data_dir),
        models_dir=Path(models).expanduser() if models else None,
        stt_provider=_str("DRAKTER_STT_PROVIDER", d.stt_provider),
        stt_model=_str("DRAKTER_STT_MODEL", d.stt_model),
        stt_device=_str("DRAKTER_STT_DEVICE", d.stt_device),
        stt_compute_type=_str("DRAKTER_STT_COMPUTE_TYPE", d.stt_compute_type),
        stt_language=_str("DRAKTER_STT_LANGUAGE", d.stt_language),
        stt_beam_size=_int("DRAKTER_STT_BEAM_SIZE", d.stt_beam_size),
        stt_threads=_int("DRAKTER_STT_THREADS", d.stt_threads),
        tts_provider=_str("DRAKTER_TTS_PROVIDER", d.tts_provider),
        tts_fallback=os.environ.get("DRAKTER_TTS_FALLBACK", d.tts_fallback).strip(),
        tts_voice=_str("DRAKTER_TTS_VOICE", d.tts_voice),
        tts_threads=_int("DRAKTER_TTS_THREADS", d.tts_threads),
        piper_python=Path(piper_python).expanduser() if piper_python else None,
        piper_voice=_str("DRAKTER_PIPER_VOICE", d.piper_voice),
        vad_provider=_str("DRAKTER_VAD_PROVIDER", d.vad_provider),
        vad_threshold=_float("DRAKTER_VAD_THRESHOLD", d.vad_threshold),
        vad_silence_ms=_int("DRAKTER_VAD_SILENCE_MS", d.vad_silence_ms),
        vad_preroll_ms=_int("DRAKTER_VAD_PREROLL_MS", d.vad_preroll_ms),
        max_utterance_s=_int("DRAKTER_VOICE_MAX_UTTERANCE_S", d.max_utterance_s),
        wakeword_enabled=_bool("DRAKTER_WAKEWORD_ENABLED", d.wakeword_enabled),
        wakeword_provider=_str("DRAKTER_WAKEWORD_PROVIDER", d.wakeword_provider),
        wakeword_model=Path(wake_model).expanduser() if wake_model else None,
        wakeword_threshold=_float("DRAKTER_WAKEWORD_THRESHOLD", d.wakeword_threshold),
        barge_in_enabled=_bool("DRAKTER_VOICE_BARGE_IN", d.barge_in_enabled),
        barge_in_threshold=_float("DRAKTER_VOICE_BARGE_IN_THRESHOLD", d.barge_in_threshold),
        barge_in_min_ms=_int("DRAKTER_VOICE_BARGE_IN_MIN_MS", d.barge_in_min_ms),
        audio_backend=_str("DRAKTER_AUDIO_BACKEND", d.audio_backend),
        input_device=os.environ.get("DRAKTER_AUDIO_INPUT", d.input_device).strip(),
        output_device=os.environ.get("DRAKTER_AUDIO_OUTPUT", d.output_device).strip(),
        level_hz=_int("DRAKTER_VOICE_LEVEL_HZ", d.level_hz),
        output_latency_ms=_int("DRAKTER_VOICE_OUTPUT_LATENCY_MS", d.output_latency_ms),
    )
