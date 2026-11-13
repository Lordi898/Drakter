"""VoiceService: the only entry point to voice for the rest of the backend."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Mapping
from pathlib import Path
from typing import Final, Literal, Protocol

from drakter_contracts.voice_profiles import VOICE_IPC_SET_PROFILE
from pydantic import ValidationError

from app.integrations.voice.bridge import VoiceBridge
from app.integrations.voice.client import (
    VoiceClient,
    VoiceIPCError,
    VoiceUnavailableError,
    shutdown_stale,
)
from app.integrations.voice.schemas import VoiceStatus
from app.integrations.voice.settings import VoiceSettings, read_env_file
from app.integrations.voice.supervisor import VoiceSupervisor, build_env

logger = logging.getLogger("drakter.voice.service")

_STATUS_TIMEOUT_S: Final = 2.0


class EventSink(Protocol):
    async def publish(
        self,
        type: str,
        payload: Mapping[str, object],
        *,
        version: int = 1,
        experimental: bool = True,
    ) -> None: ...


class AgentTurnPort(Protocol):
    async def submit_user_turn(
        self, text: str, *, turn_id: str, source: Literal["voice"]
    ) -> AsyncIterator[str]: ...


class AuditPort(Protocol):
    async def record(self, action: str, meta: Mapping[str, object]) -> None: ...


class NullEventSink:
    async def publish(
        self,
        type: str,
        payload: Mapping[str, object],
        *,
        version: int = 1,
        experimental: bool = True,
    ) -> None:
        return None


class NullAudit:
    async def record(self, action: str, meta: Mapping[str, object]) -> None:
        return None


class NullAgentTurn:
    """Until the agent is wired: the turn ends in `voice.error` and voice returns to idle."""

    async def submit_user_turn(
        self, text: str, *, turn_id: str, source: Literal["voice"]
    ) -> AsyncIterator[str]:
        raise RuntimeError("agent not connected")


class VoiceService:
    def __init__(
        self,
        settings: VoiceSettings,
        *,
        events: EventSink,
        agent: AgentTurnPort,
        audit: AuditPort,
        data_dir: Path,
        runtime_dir: Path,
    ) -> None:
        self._settings = settings
        self._audit = audit
        self._data_dir = data_dir
        self._socket_path = runtime_dir / "voice.sock"
        self._runtime_dir = runtime_dir
        self._client = VoiceClient(
            self._socket_path,
            on_event=self._on_event,
            on_connected=self._on_connected,
            on_disconnected=self._on_disconnected,
        )
        self._bridge = VoiceBridge(self._client, events=events, agent=agent, audit=audit)
        self._supervisor: VoiceSupervisor | None = None
        self._misconfigured = False
        self._stopping = False
        self._down_reported = False

    async def start(self) -> None:
        if not self._settings.voice_enabled or self._supervisor is not None:
            return
        python = self._settings.voice_python
        if python is None or not python.is_file():
            # Voice being broken is no reason for the backend not to start.
            self._misconfigured = True
            await self._publish_error(
                "dependency_missing", "DRAKTER_VOICE_PYTHON is not set or does not exist", False
            )
            return
        if await shutdown_stale(self._socket_path):
            logger.warning("Stale voice process stopped", extra={"event": "voice_stale_stopped"})
        self._stopping = False
        self._supervisor = VoiceSupervisor(
            python=python,
            project_root=self._settings.voice_project_root,
            env=build_env(
                data_dir=self._data_dir,
                runtime_dir=self._runtime_dir,
                file_values=read_env_file(),
            ),
            on_spawn=self._on_spawn,
            on_exit=self._on_process_exit,
            on_give_up=self._on_give_up,
        )
        self._client.start()
        self._supervisor.start()

    async def stop(self) -> None:
        self._stopping = True
        await self._bridge.aclose()
        supervisor, self._supervisor = self._supervisor, None
        if supervisor is not None:
            await supervisor.stop(lambda: self._client.request("shutdown"))
        await self._client.close()

    async def status(self) -> VoiceStatus:
        if not self._settings.voice_enabled:
            return VoiceStatus(available=False, unavailable_reason="disabled")
        if self._misconfigured:
            return VoiceStatus(available=False, unavailable_reason="misconfigured")
        try:
            raw = await self._client.request("status", timeout=_STATUS_TIMEOUT_S)
            return VoiceStatus(available=True, **raw)
        except (VoiceUnavailableError, VoiceIPCError, ValidationError, TypeError):
            return VoiceStatus(available=False, unavailable_reason="not_responding")

    async def set_mic(self, enabled: bool) -> None:
        if enabled:
            # Fails closed: a microphone that cannot be audited stays off.
            await self._record_or_refuse("voice.mic_requested", {"enabled": True})
            await self._client.request("mic.set", {"enabled": True})
            return
        await self._mic_off()
        await self._record("voice.mic_requested", {"enabled": False})

    async def set_wakeword(self, enabled: bool) -> None:
        if enabled:
            await self._record_or_refuse("voice.wakeword_requested", {"enabled": True})
            await self._client.request("wakeword.set", {"enabled": True})
            return
        await self._client.request("wakeword.set", {"enabled": False})
        await self._record("voice.wakeword_requested", {"enabled": False})

    async def set_voice_profile(self, profile: str) -> None:
        """Avisa del perfil activo. Si el proceso de voz no lo entiende o no está, se ignora."""
        try:
            await self._client.request(VOICE_IPC_SET_PROFILE, {"profile": profile})
        except (VoiceUnavailableError, VoiceIPCError):
            return

    async def listen_start(self) -> str:
        result = await self._client.request("listen.start")
        turn_id = result.get("turn_id")
        if not isinstance(turn_id, str) or not turn_id:
            raise VoiceUnavailableError("voice process returned no turn_id")
        return turn_id

    async def listen_stop(self) -> None:
        await self._client.request("listen.stop")

    async def listen_cancel(self) -> None:
        await self._client.request("listen.cancel")

    async def interrupt(self) -> None:
        # The agent may still be thinking, with nothing playing: voice would have
        # no interruption to report, so it is cut here as well.
        self._bridge.cancel_active()
        try:
            await self._client.request("interrupt", {"reason": "user"})
        finally:
            await self._record("voice.interrupt_requested", {"reason": "user"})

    async def _mic_off(self) -> None:
        was_ready = self._client.ready
        try:
            await self._client.request("mic.set", {"enabled": False})
        except (VoiceUnavailableError, VoiceIPCError):
            # An "off" that may not have happened: the capture dies with the process.
            if was_ready and self._supervisor is not None:
                logger.error("Voice mic off failed", extra={"event": "voice_mic_off_failed"})
                self._supervisor.kill()
            raise

    async def _record(self, action: str, meta: Mapping[str, object]) -> None:
        try:
            await self._audit.record(action, meta)
        except Exception as exc:  # noqa: BLE001 - already done; must not undo a privacy action
            logger.error(
                "Voice audit failed",
                extra={"event": "voice_audit_failed", "error": type(exc).__name__},
            )

    async def _record_or_refuse(self, action: str, meta: Mapping[str, object]) -> None:
        try:
            await self._audit.record(action, meta)
        except Exception as exc:  # noqa: BLE001
            raise VoiceUnavailableError("audit log unavailable") from exc

    async def _publish_error(self, code: str, message: str, recoverable: bool) -> None:
        await self._bridge.publish(
            "voice.error",
            {"code": code, "stage": "process", "message": message, "recoverable": recoverable},
        )

    async def _on_event(self, name: str, payload: Mapping[str, object]) -> None:
        await self._bridge.handle_event(name, payload)

    async def _on_connected(self) -> None:
        # Before the client lets anyone else in: after a crash or a dropped link,
        # the microphone is off until the user turns it on again.
        await self._client.request("mic.set", {"enabled": False}, handshake=True)
        self._down_reported = False

    async def _on_disconnected(self) -> None:
        await self._report_down("voice_link_lost")

    async def _on_spawn(self) -> None:
        self._down_reported = False

    async def _on_process_exit(self, code: int | None) -> None:
        await self._report_down("voice_process_exited")

    async def _on_give_up(self) -> None:
        await self._publish_error("voice_process_failed", "Voice process keeps failing", False)

    async def _report_down(self, code: str) -> None:
        self._bridge.cancel_active()
        if self._stopping or self._down_reported:
            return
        self._down_reported = True
        await self._publish_error(code, "Voice process is not available", True)
        await self._bridge.publish("voice.mic_changed", {"enabled": False, "capture_open": False})
