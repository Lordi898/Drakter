"""Configuración del proceso de voz. Sin secretos: las claves llegan por el entorno.

Orden de precedencia: valores por defecto → `~/.config/drakter/voice.toml` (claves planas con
el nombre del campo) → variables `DRAKTER_VOICE_<CAMPO>` → `DRAKTER_RUNTIME_DIR` y
`DRAKTER_DATA_DIR`, que fija el supervisor del backend.

Los umbrales son PROVISIONALES y están sin calibrar (se miden en WP9). No son ajustes de usuario:
esos (`voice_tts_enabled`, `voice_profile`, …) llegan por el comando IPC `voice.config`.
"""

from __future__ import annotations

import dataclasses
import os
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, get_type_hints

REPO_ROOT = Path(__file__).resolve().parents[1]
NULL = "null"


def _xdg(var: str, fallback: str) -> Path:
    raw = os.environ.get(var, "")
    return Path(raw) if raw and Path(raw).is_absolute() else Path.home() / fallback


def _default_runtime_dir() -> Path:
    raw = os.environ.get("XDG_RUNTIME_DIR")
    return (Path(raw) if raw else Path(f"/run/user/{os.getuid()}")) / "drakter"


@dataclass(frozen=True)
class VoiceConfig:
    # ── Rutas. runtime_dir debe coincidir con Settings.runtime_dir del backend.
    runtime_dir: Path = field(default_factory=_default_runtime_dir)
    data_dir: Path = field(default_factory=lambda: _xdg("XDG_DATA_HOME", ".local/share") / "drakter")
    config_dir: Path = field(default_factory=lambda: _xdg("XDG_CONFIG_HOME", ".config") / "drakter")

    # ── Proveedores: nombre de `voice/registry.py` o "paquete.modulo:fabrica". "null" = vacío.
    stt: str = "moonshine"
    vad: str = "silero"
    turn_start: str = "drakter"
    turn_stop: str = "smart_turn"
    wake: str = "openwakeword"
    tts: tuple[str, ...] = ("fish", "kokoro")  # orden de preferencia del failover
    tts_chain: str = "failover"
    mixer: str = "duck"
    channel: str = "webrtc"
    # Piezas fuera de la tabla del registro; fábricas `create(cfg, ctl) -> FrameProcessor`.
    guard: str = "voice.speech.guard:create"
    phrases: str = "voice.speech.phrases:create"  # el procesador expone `async play(key, when)`
    playback: str = "voice.speech.playback:create"
    idle: str = "voice.conversation.idle:attach"  # attach(utp, ctl, cfg)

    # ── STT, activación y turnos (provisionales, sin calibrar)
    stt_model: str = "small"  # small | tiny (respaldo)
    threads: int = 2  # hilos por modelo local (CPU sin GPU dedicada)
    wake_models: tuple[str, ...] = ("hey_jarvis_v0.1.onnx",)  # en models/openwakeword/
    wake_threshold: float = 0.3
    turn_stop_secs: float = 3.0  # tope de silencio de Smart Turn
    turn_final_timeout_s: float = 1.0  # espera a la transcripción final tras el fin de turno
    followup_s: float = 20.0  # sin voz tras responder → reposo
    idle_nudge_s: float = 10.0  # user_idle_timeout del UserTurnProcessor
    bargein_min_words: int = 3
    bargein_decide_ms: int = 700
    duck_gain: float = 0.25

    # ── TTS
    tts_model: str = "s2.1-pro-free"  # lista blanca: el único gratuito
    fish_free_until: date = date(2026, 11, 30)  # después, Kokoro salvo allow_paid
    allow_paid: bool = False
    kokoro_voice: str = "ef_dora"
    filler_after_ms: int = 1200
    tool_phrase_gap_s: float = 8.0

    # ── WebRTC
    rtc_loopback: bool = True  # añade 127.0.0.1 a los candidatos ICE (aioice lo excluye)
    rtc_ping_timeout_s: float = 6.0  # sin ping del data channel → conexión perdida

    @property
    def socket_path(self) -> Path:
        return self.runtime_dir / "voice.sock"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def voice_dir(self) -> Path:
        """Datos de ejecución de la voz: métricas y caché de frases."""
        return self.data_dir / "voice"

    @property
    def metrics_path(self) -> Path:
        return self.voice_dir / "metrics.jsonl"

    @property
    def phrase_cache_dir(self) -> Path:
        return self.voice_dir / "cache"

    @property
    def phrases_path(self) -> Path:
        return REPO_ROOT / "agent" / "identity" / "voice_phrases.es.toml"

    def with_null_providers(self) -> VoiceConfig:
        """Todo vacío: el proceso arranca sin modelos, sin red y sin los demás paquetes."""
        names = ("stt", "vad", "turn_start", "turn_stop", "wake", "tts_chain", "mixer",
                 "guard", "phrases", "playback", "idle")
        return dataclasses.replace(self, tts=(NULL,), **dict.fromkeys(names, NULL))


def _coerce(kind: Any, raw: Any) -> Any:
    """Convierte un valor de TOML o de entorno al tipo del campo."""
    if kind is bool:
        return raw if isinstance(raw, bool) else str(raw).strip().lower() in {"1", "true", "yes", "on"}
    if kind is date:
        return raw if isinstance(raw, date) else date.fromisoformat(str(raw).strip())
    if kind is Path:
        return Path(str(raw)).expanduser()
    if kind in (int, float, str):
        return kind(raw.strip() if isinstance(raw, str) else raw)
    # tuple[str, ...]: lista TOML o texto separado por comas
    items = raw if isinstance(raw, (list, tuple)) else str(raw).split(",")
    return tuple(str(item).strip() for item in items if str(item).strip())


def load_config(environ: dict[str, str] | None = None) -> VoiceConfig:
    env = os.environ if environ is None else environ
    hints = get_type_hints(VoiceConfig)
    values: dict[str, Any] = {}

    for key in ("runtime_dir", "data_dir"):  # nombres que ya usa el supervisor del backend
        raw = env.get(f"DRAKTER_{key.upper()}", "").strip()
        if raw:
            values[key] = Path(raw).expanduser()

    toml_path = VoiceConfig().config_dir / "voice.toml"
    if toml_path.is_file():
        with toml_path.open("rb") as fh:
            for key, raw in tomllib.load(fh).items():
                if key not in hints:
                    raise ValueError(f"clave desconocida en {toml_path}: {key}")
                values.setdefault(key, _coerce(hints[key], raw))

    cfg = VoiceConfig(**values)
    # DRAKTER_VOICE_NULL=1 vacía todos los proveedores; una variable explícita puede
    # después sustituir uno (p. ej. un STT simulado en una comprobación).
    if _coerce(bool, env.get("DRAKTER_VOICE_NULL", "")):
        cfg = cfg.with_null_providers()
    overrides = {
        key: _coerce(kind, raw)
        for key, kind in hints.items()
        if (raw := env.get(f"DRAKTER_VOICE_{key.upper()}", "").strip())
    }
    cfg = dataclasses.replace(cfg, **overrides)
    if cfg.stt_model not in {"small", "tiny"}:
        raise ValueError("stt_model debe ser 'small' o 'tiny'")
    return cfg
