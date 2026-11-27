"""Sesión de voz: `SessionState`, `Ctl` y la caché de modelos. Vive FUERA del pipeline.

Hay un pipeline por conexión WebRTC, pero una sola `Session` por proceso: recargar el renderer
monta un pipeline nuevo sin perder el modo ni recargar modelos. `Session` es el único dueño del
modo (`set_mode`) y de `connected`, y despacha los comandos IPC de `voice_ipc` (plan §4.2).
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from drakter_contracts import voice_ipc as ipc
from pydantic import BaseModel, ValidationError

from voice.config import NULL, VoiceConfig
from voice.ports import ResolvedProfile, SessionState, Trigger, TTSProvider
from voice.registry import create

if TYPE_CHECKING:
    from pipecat.pipeline.worker import PipelineWorker

    from voice.bridge import BackendBridgeProcessor

log = logging.getLogger("voice.session")
T = TypeVar("T")


class SharedModels:
    """`ports.Shared`: cada modelo se carga una vez por proceso y sobrevive a las reconexiones."""

    def __init__(self, models_dir: Path) -> None:
        self.models_dir = Path(models_dir)
        self._items: dict[str, Any] = {}
        self._lock = threading.Lock()
        self.loads = 0  # cuántas cargas reales ha habido (para comprobar que no se recarga)

    def get(self, key: str, loader: Callable[[], T]) -> T:
        with self._lock:  # un cargador a la vez: dos modelos a la vez no caben holgados en RAM
            if key not in self._items:
                self._items[key] = loader()
                self.loads += 1
            return self._items[key]


@dataclass
class Parts:
    """Piezas del pipeline activo a las que la sesión necesita llegar."""

    worker: PipelineWorker
    bridge: BackendBridgeProcessor
    phrases: Any = None  # PhrasePlayer: expone `async play(key, when)`
    tts: list[TTSProvider] = field(default_factory=list)


def resolve_profile(name: str) -> ResolvedProfile:
    """Resuelve el perfil con `VoiceProfileStore` en ejecución. El ID nunca se registra."""
    from drakter_contracts.voice_profiles import VoiceConfigError, VoiceProfileStore

    try:
        voices = VoiceProfileStore().get()
        canonical = voices.resolve(name) or voices.default
        return ResolvedProfile(canonical, voices.perfiles[canonical].reference_id or None)
    except (VoiceConfigError, KeyError, OSError) as exc:
        log.warning("profile_unresolved", extra={"data": {"error": type(exc).__name__}})
        return ResolvedProfile(name, None)


class Session:
    """Implementa `ports.Ctl`. Un atributo de más por costura con WP3/WP4:

    - `speech_text`: texto sin etiquetas del speech activo (lo escribe el puente; lo lee el
      PlaybackTracker para `pending_head`).
    - `duck`: objetivo del ducking; además se llama a `mixer.set_duck(on)` si existe.
    - `false_ducks`: contador que incrementa la estrategia de inicio; sale en `voice.metrics`.
    """

    def __init__(self, cfg: VoiceConfig, publish: Callable[[str, Mapping[str, Any]], None]) -> None:
        self.cfg = cfg
        self.state = SessionState()
        self.speech_text = ""
        # Hay un tramo de habla del bot abierto o por sonar (lo mantiene el puente): el VAD no
        # abre turno al instante, igual que con el bot hablando.
        self.speech_open = False
        # Hay un tramo de respuesta sonando según el PlaybackTracker (de `started` a
        # `finished`/`interrupted`), aunque haya huecos sin audio entre frases.
        self.speech_playing = False
        self.duck = False
        self.false_ducks = 0
        self.metrics_last: dict[str, Any] | None = None
        self._publish = publish
        self._parts: Parts | None = None
        self._mixer: Any = None
        self._voice_pending = False
        self._errors_sent: dict[str, float] = {}  # código → último aviso (report_error)
        self._tasks: set[asyncio.Task[None]] = set()

    # ── pipeline activo ─────────────────────────────────────────────────────
    def new_mixer(self) -> Any:
        """Mixer de la conexión que se está montando (`None` con el proveedor vacío)."""
        self.duck = False
        self._mixer = create("mixer", self.cfg.mixer, self.cfg, self)
        return self._mixer

    def bind(self, parts: Parts) -> None:
        self._parts = parts

    def unbind(self, worker: PipelineWorker) -> None:
        if self._parts is not None and self._parts.worker is worker:
            self._parts = None

    def uses_fish(self) -> bool:
        return "fish" in self.cfg.tts

    # ── Ctl ─────────────────────────────────────────────────────────────────
    async def emit(self, type: str, payload: dict[str, Any]) -> None:
        if type == "voice.error" and "message" not in payload:
            from voice.errors import message_for

            payload = {**payload, "message": message_for(str(payload.get("code", "")))}
        try:
            self._publish(type, payload)
        except (ValueError, ValidationError) as exc:
            log.error("event_rejected", extra={"data": {"type": type, "error": type_name(exc)}})
        if type == "voice.playback" and payload.get("state") == "finished" and self._parts is not None:
            # FIFO de beats: el siguiente tramo arranca cuando el tracker termine de cerrar este.
            task = asyncio.get_running_loop().create_task(
                self._parts.bridge.on_playback_done(int(payload.get("speech_id", -1)))
            )
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def report_error(self, code: str, stage: str, recoverable: bool) -> None:
        """`voice.error` con su texto corto, una vez por código cada `REPEAT_S`. Nunca lanza."""
        from voice.errors import REPEAT_S

        now = time.monotonic()
        if now - self._errors_sent.get(code, -REPEAT_S) < REPEAT_S:
            return
        self._errors_sent[code] = now
        log.warning("voice_error", extra={"data": {"code": code, "stage": stage}})
        try:
            await self.emit("voice.error", {"code": code, "stage": stage, "recoverable": recoverable})
        except Exception as exc:  # noqa: BLE001 - el aviso nunca rompe la voz
            log.error("voice_error_not_sent", extra={"data": {"error": type_name(exc)}})

    async def interrupt(self, reason: str) -> None:
        if self._parts is not None:
            await self._parts.bridge.interrupt(reason)

    async def play_phrase(self, key: str, when: str = "now") -> None:
        player = getattr(self._parts, "phrases", None)
        play = getattr(player, "play", None)
        if play is None:
            return
        try:
            await play(key, when)
        except Exception as exc:  # noqa: BLE001 - una frase fija nunca tumba el turno
            log.warning("phrase_failed", extra={"data": {"key": key, "error": type_name(exc)}})

    def arm_filler(self) -> None:
        """Fin de turno de usuario: acuse si el primer audio tarda (PhrasePlayer de WP3)."""
        arm = getattr(getattr(self._parts, "phrases", None), "arm_filler", None)
        if arm is not None and self.state.tts_enabled:
            arm()

    def keep_filler(self) -> None:
        """La próxima interrupción (turno nuevo) no cancela el acuse ya armado."""
        keep = getattr(getattr(self._parts, "phrases", None), "keep_filler", None)
        if keep is not None:
            keep()

    async def on_tool(self, turn_id: str | None) -> None:
        hook = getattr(getattr(self._parts, "phrases", None), "on_tool", None)
        if hook is None:
            return
        try:
            await hook(turn_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("phrase_failed", extra={"data": {"key": "tool_generic", "error": type_name(exc)}})

    def set_duck(self, on: bool) -> None:
        self.duck = bool(on)
        setter = getattr(self._mixer, "set_duck", None)
        if setter is not None:
            setter(self.duck)

    async def set_mode(self, mode: str, trigger: str) -> None:
        if mode not in ("standby", "conversation") or trigger not in ("wake", "hotkey", "ui", "followup"):
            raise ValueError(f"invalid mode or trigger: {mode}/{trigger}")
        if mode == self.state.mode:
            return
        self.state.mode = mode  # type: ignore[assignment]
        self.state.trigger = trigger if mode == "conversation" else None  # type: ignore[assignment]
        if mode == "standby":
            self.set_duck(False)
        log.info("mode", extra={"data": {"mode": mode, "trigger": trigger}})
        await self.emit_state()

    # ── estado ──────────────────────────────────────────────────────────────
    async def emit_state(self) -> None:
        s = self.state
        await self.emit(
            "voice.state",
            {"connected": s.connected, "mode": s.mode, "tts": s.tts_active, "profile": s.profile},
        )

    async def set_connected(self, connected: bool) -> None:
        """Sin renderer no hay micrófono: la sesión vuelve a reposo.

        Una conexión nueva reemite siempre el snapshot, aunque sustituya a otra viva (recarga
        del renderer): el modo se conserva y el backend puede resincronizar.
        """
        s = self.state
        changed = connected or s.connected or s.mode != "standby"
        s.connected = connected
        if not connected:
            s.mode, s.trigger = "standby", None
            s.bot_speaking = False  # el pipeline que lo mantenía ya no existe
            self.speech_open = False
            self.speech_playing = False
            self.set_duck(False)
        if changed:
            await self.emit_state()

    def consume_trigger(self) -> Trigger:
        """Disparador del turno que se va a emitir; los siguientes de la conversación son `followup`."""
        trigger: Trigger = self.state.trigger or "followup"
        if self.state.mode == "conversation":
            self.state.trigger = "followup"
        return trigger

    def take_false_ducks(self) -> int:
        count, self.false_ducks = self.false_ducks, 0
        return count

    def snapshot(self) -> dict[str, Any]:
        state = dataclasses.asdict(self.state)
        state.pop("spoken_tail", None)  # es texto: no sale del proceso por `status`
        return state

    # ── voice.config ────────────────────────────────────────────────────────
    async def apply_config(self, config: ipc.CmdVoiceConfig) -> None:
        s = self.state
        profile_changed = config.profile != s.profile
        s.tts_enabled, s.wake_enabled, s.expression = config.tts_enabled, config.wake_enabled, config.expression
        s.profile = config.profile
        if profile_changed:
            self._voice_pending = True
            await self.apply_pending_voice()
            await self.emit_state()

    async def apply_pending_voice(self) -> None:
        """Cambia la voz de Fish. Si el bot está hablando, se aplica cuando termine."""
        if not self._voice_pending or self.state.bot_speaking or self._parts is None:
            return
        self._voice_pending = False
        fish = next((p for p in self._parts.tts if p.name == "fish"), None)
        if fish is None:
            return
        profile = resolve_profile(self.state.profile)
        set_profile = getattr(self._parts.phrases, "set_profile", None)
        if set_profile is not None:
            set_profile(profile)  # la caché de frases va por perfil
        if profile.voice is None:
            return
        from pipecat.frames.frames import TTSUpdateSettingsFrame
        from pipecat.services.settings import TTSSettings

        await self._parts.worker.queue_frame(
            TTSUpdateSettingsFrame(delta=TTSSettings(voice=profile.voice), service=fish.service)
        )

    # ── comandos IPC (plan §4.2) ────────────────────────────────────────────
    async def handle_command(self, type: str, payload: BaseModel) -> dict[str, Any]:
        bridge = self._parts.bridge if self._parts is not None else None
        match payload:
            case ipc.CmdSpeakOpen() if bridge:
                await bridge.speak_open(payload.turn_id, payload.speech_id)
            case ipc.CmdSpeakDelta():
                # Sin conexión no hay quien lo diga: se ignora, igual que un speech cortado.
                ignored = bridge is None or await bridge.speak_delta(payload.speech_id, payload.seq, payload.text)
                return {"ignored": ignored}
            case ipc.CmdSpeakFlush() if bridge:
                await bridge.speak_flush(payload.speech_id)
            case ipc.CmdSpeakClose() if bridge:
                await bridge.speak_close(payload.speech_id)
            case ipc.CmdSpeakBeat():
                # Sin conexión no hay quien lo diga: el overlay usa su reloj local.
                ignored = bridge is None or await bridge.speak_beat(payload.turn_id, payload.speech_id, payload.text)
                return {"ignored": ignored}
            case ipc.CmdSpeakStop() if bridge:
                await bridge.speak_stop(payload.speech_id, payload.reason)
            case ipc.CmdSpeakPhrase():
                await self.play_phrase(payload.key, payload.when)
            case ipc.CmdTurnPhase():
                self.state.turn_id, self.state.turn_phase = payload.turn_id, payload.phase
                if bridge:
                    await bridge.turn_phase(payload.phase)
                # `draw` y `guide_wait` hablan con sus beats: sin «un momento» entre medias.
                if payload.phase == "executing" and payload.tool not in ("draw", "guide_wait"):
                    await self.on_tool(payload.turn_id)
            case ipc.CmdVoiceConfig():
                await self.apply_config(payload)
            case ipc.CmdModeSet():
                await self.set_mode(payload.mode, payload.trigger)
            case ipc.CmdEmpty() if type == "status":
                return {"state": self.snapshot(), "metrics_last": self.metrics_last}
        return {}

    def ready_payload(self) -> dict[str, Any]:
        from importlib.metadata import version

        cfg = self.cfg
        return {
            "pipecat": version("pipecat-ai"),
            "stt": cfg.stt,
            "tts": cfg.tts[0] if cfg.tts else NULL,
            "wake": cfg.wake != NULL and self.state.wake_enabled,
        }


def type_name(exc: BaseException) -> str:
    return exc.__class__.__name__
