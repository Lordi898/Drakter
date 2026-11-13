"""VoiceOrchestrator: the only entry point to voice for the rest of the backend (plan WP5).

- Supervises `python -m voice run` and its IPC link (`supervisor.py`, `client.py`).
- Is the `TurnTap` of the agent runtime through `VoiceBridge` (never blocks a turn).
- Turns `voice.user_turn` into agent turns through `VoicePolicy`.
- Publishes `voice.state`, `voice.playback` (no text), `voice.error` and, once, the
  `notification.created` of the TTS fallback. The voice process never touches the hub.
- Signals the `StatusArbiter` as source `"voice"`.

No transcript, spoken text or key is logged or audited: only ids, categories and timings.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, Literal, Protocol
from uuid import UUID, uuid4

from drakter_contracts.events import (
    NotificationCreated,
    VoiceError,
    VoicePlayback,
    VoiceState,
)
from drakter_contracts.voice_ipc import (
    CMD_RESULTS,
    CMDS,
    EVTS,
    EvtLocalCommand,
    EvtMetrics,
    EvtPlayback,
    EvtState,
    EvtTtsFallback,
    EvtUserSpeech,
    EvtUserTurn,
    VoiceOfferIn,
    VoiceOfferOut,
    VoiceStatusOut,
)
from pydantic import BaseModel, ValidationError

from app.integrations.voice.bridge import Source, VoiceBridge
from app.integrations.voice.client import VoiceClient, VoiceUnavailableError, shutdown_stale
from app.integrations.voice.heard import HeardNotes
from app.integrations.voice.policy import RuntimePort, VoicePolicy
from app.integrations.voice.settings import VoiceSettings, read_env_file
from app.integrations.voice.supervisor import VoiceSupervisor, build_env
from app.services import settings as settings_service
from app.services.settings_models import SETTING_DEFAULTS

logger = logging.getLogger("drakter.voice.service")

_STATUS_TIMEOUT_S: Final = 2.0
_OFFER_TIMEOUT_S: Final = 10.0
_TURN_END_WAIT_S: Final = 2.0
_VOICE_KEYS: Final = ("voice_tts_enabled", "voice_profile", "voice_wake_enabled", "voice_expression")


class AuditPort(Protocol):
    async def record(self, action: str, meta: Mapping[str, object]) -> None: ...


class NullAudit:
    async def record(self, action: str, meta: Mapping[str, object]) -> None:
        return None


class Hub(Protocol):
    def publish(self, type: str, payload: BaseModel, *, correlation_id: str | None = None) -> Any: ...
    def subscribe(self, after_seq: int | None, boot_id: UUID | None) -> Any: ...
    def unsubscribe(self, subscription: Any) -> None: ...


class OrchestratorRuntime(RuntimePort, Protocol):
    hub: Hub

    def set_turn_tap(self, tap: Any) -> None: ...


class VoiceOrchestrator:
    def __init__(
        self,
        settings: VoiceSettings,
        *,
        runtime: OrchestratorRuntime,
        audit: AuditPort | None = None,
        data_dir: Path,
        runtime_dir: Path,
        db_path: Path,
    ) -> None:
        self._settings = settings
        self._runtime = runtime
        self._audit = audit or NullAudit()
        self._data_dir = data_dir
        self._runtime_dir = runtime_dir
        self._db_path = db_path
        self._socket_path = runtime_dir / "voice.sock"
        self._cfg: dict[str, str] = dict(SETTING_DEFAULTS)
        self._client = VoiceClient(
            self._socket_path,
            on_event=self._on_event,
            on_connected=self._on_connected,
            on_disconnected=self._on_disconnected,
        )
        self._bridge = VoiceBridge(
            self._request,
            tts_enabled=lambda: self._cfg.get("voice_tts_enabled") == "true",
            max_chars_text=settings.speak_max_chars_text,
            observer=self,
        )
        self._policy = VoicePolicy(
            runtime,
            self._bridge,
            audit=self._record,
            on_error=lambda code: self._publish_error(code, "turn", True),
            bot_speaking=lambda: self._bot_speaking,
            min_words=settings.bargein_min_words,
        )
        self.heard = HeardNotes()
        # snapshot published as `voice.state`
        self._connected = False
        self._mode: Literal["standby", "conversation"] = "standby"
        self._tts: Literal["fish", "local"] = "fish"
        self._bot_speaking = False
        self._fallback_notified = False
        self._metrics_last: dict[str, Any] = {}
        self._ttft_t0: float | None = None  # end of the last voice turn
        self._ttft_turns: dict[UUID, float] = {}
        self._supervisor: VoiceSupervisor | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tasks: set[asyncio.Task[Any]] = set()
        self._hub_task: asyncio.Task[None] | None = None
        self._misconfigured = False
        self._stopping = False
        self._down_reported = False

    # ── lifecycle ──────────────────────────────────────────────────────────
    async def start(self) -> None:
        """Wire into the runtime and spawn voice. WP9 also registers `self.heard.prefix`
        with `runtime.add_turn_prefix`."""
        if self._loop is not None:
            return
        self._loop = asyncio.get_running_loop()
        self._stopping = False
        await asyncio.to_thread(self._load_settings)
        self._bridge.start()
        self._runtime.set_turn_tap(self._bridge)
        settings_service.add_setting_listener(self._on_setting_threadsafe)
        self._hub_task = asyncio.create_task(self._watch_hub(), name="voice-hub-watch")
        if not self._settings.voice_enabled:
            return
        python = self._settings.voice_python
        if python is None or not python.is_file():
            # Voice being broken is no reason for the backend not to start.
            self._misconfigured = True
            self._publish_error("dependency_missing", "ipc", False)
            return
        if await shutdown_stale(self._socket_path):
            logger.warning("Stale voice process stopped", extra={"event": "voice_stale_stopped"})
        self._supervisor = VoiceSupervisor(
            python=python,
            project_root=self._settings.voice_project_root,
            env=build_env(
                data_dir=self._data_dir, runtime_dir=self._runtime_dir, file_values=read_env_file()
            ),
            on_spawn=self._on_spawn,
            on_exit=self._on_process_exit,
            on_give_up=self._on_give_up,
        )
        self._client.start()
        self._supervisor.start()

    def attach_client_only(self) -> None:
        """Connect to an already running voice process (dev and the IPC simulator)."""
        self._client.start()

    async def stop(self) -> None:
        self._stopping = True
        settings_service.remove_setting_listener(self._on_setting_threadsafe)
        with contextlib.suppress(Exception):
            self._runtime.set_turn_tap(None)
        if self._hub_task is not None:
            self._hub_task.cancel()
        for task in (*self._tasks, *((self._hub_task,) if self._hub_task else ())):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._bridge.aclose()
        supervisor, self._supervisor = self._supervisor, None
        if supervisor is not None:
            await supervisor.stop(lambda: self._client.request("shutdown"))
        await self._client.close()
        self._loop = None

    # ── REST surface (router.py) ────────────────────────────────────────────
    def snapshot(self) -> VoiceState:
        return VoiceState(
            connected=self._connected,
            mode=self._mode,
            tts=self._tts,
            profile=self._cfg.get("voice_profile", "natural"),
            wake_enabled=self._cfg.get("voice_wake_enabled") == "true",
        )

    async def offer(self, body: VoiceOfferIn) -> VoiceOfferOut:
        result = await self._request(
            "rtc.offer", body.model_dump(exclude_none=True), timeout=_OFFER_TIMEOUT_S
        )
        await self._record("voice.offer", {"restart_pc": bool(body.restart_pc)})
        return VoiceOfferOut.model_validate(result)

    async def set_mode(
        self, mode: Literal["standby", "conversation"], trigger: str
    ) -> VoiceState:
        await self._request("mode.set", {"mode": mode, "trigger": trigger})
        await self._record("voice.mode", {"mode": mode, "trigger": trigger})
        self._mode = mode  # voice.state confirms it; the answer should not wait for that
        return self.snapshot()

    def say_phrase(self, key: str, when: Literal["now", "when_silent"] = "now") -> None:
        """`speak.phrase` from elsewhere in the backend (Jobs: `job_done`/`job_failed`).
        Fire-and-forget through the bridge queue; never raises."""
        if self._loop is None:
            return
        self._bridge.phrase(key, when)

    async def status(self) -> VoiceStatusOut:
        base = self.snapshot().model_dump()
        try:
            raw = await self._request("status", {}, timeout=_STATUS_TIMEOUT_S)
            metrics = raw.get("metrics_last")
            if isinstance(metrics, dict):
                self._metrics_last.update(metrics)
        except Exception:  # noqa: BLE001 - not reachable: the snapshot says connected=False
            pass
        return VoiceStatusOut(**base, metrics_last=dict(self._metrics_last) or None)

    # ── IPC ────────────────────────────────────────────────────────────────
    async def _request(
        self,
        type: str,
        payload: Mapping[str, Any],
        *,
        timeout: float | None = None,
        handshake: bool = False,
    ) -> dict[str, Any]:
        """Validate against the frozen contract, send, validate the answer."""
        body = CMDS[type].model_validate(dict(payload)).model_dump(
            mode="json", by_alias=True, exclude_none=True
        )
        result = await self._client.request(type, body, timeout=timeout, handshake=handshake)
        model = CMD_RESULTS.get(type)
        return model.model_validate(result).model_dump(mode="json") if model else result

    def _voice_config(self) -> dict[str, Any]:
        return {
            "tts_enabled": self._cfg.get("voice_tts_enabled") == "true",
            "profile": self._cfg.get("voice_profile", "natural"),
            "wake_enabled": self._cfg.get("voice_wake_enabled") == "true",
            "expression": self._cfg.get("voice_expression", "llm"),
        }

    async def _on_connected(self) -> None:
        # Before anyone else may send: voice starts with the user's current settings.
        await self._request("voice.config", self._voice_config(), handshake=True)
        self._down_reported = False

    async def _on_disconnected(self) -> None:
        await self._report_down("voice_link_lost")

    async def _on_spawn(self) -> None:
        self._down_reported = False

    async def _on_process_exit(self, code: int | None) -> None:
        await self._report_down("voice_process_exited")

    async def _on_give_up(self) -> None:
        self._publish_error("voice_process_failed", "ipc", False)

    async def _report_down(self, code: str) -> None:
        self._connected = False
        if self._bot_speaking:
            self._bot_speaking = False
            self._signal(None)
        if self._stopping or self._down_reported:
            return
        self._down_reported = True
        self._publish_error(code, "ipc", True)
        self._publish("voice.state", self.snapshot())

    # ── events from voice ──────────────────────────────────────────────────
    async def _on_event(self, name: str, payload: Mapping[str, object]) -> None:
        model = EVTS.get(name)
        if model is None:
            return
        try:
            evt = model.model_validate(dict(payload))
        except ValidationError:
            logger.warning("Voice event invalid", extra={"event": "voice_evt_invalid", "type": name})
            return
        handler = getattr(self, "_evt_" + name.removeprefix("voice."))
        await handler(evt)

    async def _evt_ready(self, evt: BaseModel) -> None:
        await self._record("voice.ready", evt.model_dump())

    async def _evt_state(self, evt: EvtState) -> None:
        self._connected, self._mode, self._tts = evt.connected, evt.mode, evt.tts
        self._publish("voice.state", self.snapshot())

    async def _evt_user_speech(self, evt: EvtUserSpeech) -> None:
        self._signal("listening" if evt.phase == "started" else None)

    async def _evt_user_turn(self, evt: EvtUserTurn) -> None:
        self._ttft_t0 = time.monotonic()
        self._metrics_last.update({"stt_ms": evt.stt_ms, "endpointing_ms": evt.eot_ms})
        await self._policy.user_turn(evt)

    async def _evt_playback(self, evt: EvtPlayback) -> None:
        turn_id = _uuid(evt.turn_id)
        if evt.state == "started":
            self._bot_speaking = True
            self._signal("speaking", turn_id)
        elif evt.state == "finished":
            self._bot_speaking = False
            self._signal(None, turn_id)
        elif evt.state == "interrupted":
            self._bot_speaking = False
            self._bridge.cut(evt.speech_id)
            session_id = self._bridge.session_of(turn_id) if turn_id else None
            if session_id is not None:
                self.heard.record(session_id, evt.heard_tail, evt.pending_head)
            logger.info("Voice playback interrupted", extra={
                "event": "voice_interrupted", "has_session": session_id is not None,
                "heard_chars": len(evt.heard_tail or ""), "pending_chars": len(evt.pending_head or "")})
            self._signal("interrupted", turn_id)
        if turn_id is not None:
            self._publish(
                "voice.playback",
                VoicePlayback(
                    turn_id=turn_id,
                    speech_id=evt.speech_id,
                    state=evt.state,
                    sentence_index=evt.sentence_index,
                ),
            )

    async def _evt_local_command(self, evt: EvtLocalCommand) -> None:
        await self._policy.local_command(evt)

    async def _evt_tts_fallback(self, evt: EvtTtsFallback) -> None:
        self._tts = "local"
        await self._record("voice.tts_fallback", {"reason": evt.reason})
        if not self._fallback_notified:
            self._fallback_notified = True
            self._publish(
                "notification.created",
                NotificationCreated(
                    notification_id=uuid4(),
                    kind="voice.tts_fallback",
                    title="Fish no está disponible: Drakter usa la voz local.",
                    severity="warning",
                ),
            )
        self._publish("voice.state", self.snapshot())

    async def _evt_metrics(self, evt: EvtMetrics) -> None:
        self._metrics_last.update(evt.model_dump(exclude_none=True))

    async def _evt_error(self, evt: BaseModel) -> None:
        self._publish("voice.error", VoiceError.model_validate(evt.model_dump()))

    # ── TapObserver (called by the bridge drain task) ───────────────────────
    def turn_started(self, turn_id: UUID, session_id: UUID, source: Source) -> None:
        if source == "voice" and self._ttft_t0 is not None:
            self._ttft_turns[turn_id] = self._ttft_t0
            self._ttft_t0 = None

    def first_delta(self, turn_id: UUID) -> None:
        t0 = self._ttft_turns.pop(turn_id, None)
        if t0 is not None:
            ttft = int((time.monotonic() - t0) * 1000)
            self._metrics_last.update({"turn_id": str(turn_id), "agent_ttft_ms": ttft})
            logger.info("Voice agent TTFT", extra={"event": "voice_agent_ttft", "ms": ttft})

    def turn_ended(self, turn_id: UUID, outcome: str) -> None:
        self._ttft_turns.pop(turn_id, None)
        self._spawn(self._after_turn())

    async def _after_turn(self) -> None:
        # The tap fires inside _close_turn: give the runtime a moment to free the turn.
        deadline = time.monotonic() + _TURN_END_WAIT_S
        while self._runtime.active_turn() is not None and time.monotonic() < deadline:
            await asyncio.sleep(0.05)
        await self._policy.turn_ended()

    # ── settings (V-31) ─────────────────────────────────────────────────────
    def _load_settings(self) -> None:
        try:
            listed = settings_service.list_settings(self._db_path)
        except Exception:  # noqa: BLE001 - defaults until the DB is there
            return
        for item in listed.items:
            if item.key in _VOICE_KEYS and item.value is not None:
                self._cfg[item.key] = item.value

    def _on_setting_threadsafe(self, key: str, value: str) -> None:
        loop = self._loop
        if key in _VOICE_KEYS and loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self._apply_setting, key, value)

    def _apply_setting(self, key: str, value: str) -> None:
        if self._cfg.get(key) == value:
            return
        self._cfg[key] = value
        if key == "voice_tts_enabled" and value == "false":
            self._bridge.mute()
        self._bridge.send("voice.config", self._voice_config())
        self._publish("voice.state", self.snapshot())

    # ── hub: confirmations (V-34) ───────────────────────────────────────────
    async def _watch_hub(self) -> None:
        hub = self._runtime.hub
        while True:
            sub = hub.subscribe(None, None)
            try:
                while True:
                    envelope = await sub.queue.get()
                    kind = getattr(envelope, "type", None)
                    if kind is None:  # CLOSE: we lagged; subscribe again
                        break
                    action_id = str((envelope.payload or {}).get("action_id", ""))
                    if kind == "confirmation.requested":
                        self._policy.confirmation_requested(action_id)
                    elif kind == "confirmation.resolved":
                        self._policy.confirmation_resolved(action_id)
            finally:
                hub.unsubscribe(sub)

    # ── helpers ─────────────────────────────────────────────────────────────
    def _publish(self, type: str, payload: BaseModel) -> None:
        try:
            self._runtime.hub.publish(type, payload)
        except Exception as exc:  # noqa: BLE001 - a subscriber failing must not affect voice
            logger.error(
                "Voice event not published",
                extra={"event": "voice_publish_failed", "type": type, "error": type_name(exc)},
            )

    def _publish_error(self, code: str, stage: str, recoverable: bool) -> None:
        self._publish(
            "voice.error",
            VoiceError.model_validate({"code": code, "stage": stage, "recoverable": recoverable}),
        )

    def _signal(self, state: str | None, turn_id: UUID | None = None) -> None:
        arbiter = getattr(self._runtime, "status_arbiter", None)
        if arbiter is None:
            return
        try:
            arbiter.signal("voice", state, turn_id=turn_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Voice arbiter signal failed",
                           extra={"event": "voice_signal_failed", "error": type_name(exc)})

    async def _record(self, action: str, meta: Mapping[str, object]) -> None:
        try:
            await self._audit.record(action, meta)
        except Exception as exc:  # noqa: BLE001
            logger.error("Voice audit failed",
                         extra={"event": "voice_audit_failed", "error": type_name(exc)})

    def _spawn(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


def _uuid(value: str | None) -> UUID | None:
    try:
        return UUID(value) if value else None
    except ValueError:
        return None


def type_name(exc: BaseException) -> str:
    return type(exc).__name__


__all__ = ["VoiceOrchestrator", "VoiceUnavailableError", "AuditPort", "NullAudit"]
