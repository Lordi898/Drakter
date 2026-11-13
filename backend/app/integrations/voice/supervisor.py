"""Owns the `python -m voice` process: whitelisted environment, restarts and shutdown."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Final

logger = logging.getLogger("drakter.voice.supervisor")

# Exact names, never prefixes: a prefix would let anything through under that name.
_INHERITED: Final = ("PATH", "HOME", "XDG_RUNTIME_DIR", "LANG")
# PULSE_COOKIE stays out: it is not needed for the default per-user server.
_AUDIO: Final = (
    "PIPEWIRE_RUNTIME_DIR",
    "PIPEWIRE_REMOTE",
    "PULSE_SERVER",
    "PULSE_RUNTIME_PATH",
    "PULSE_SINK",
    "PULSE_SOURCE",
)
# Exact names of the voice v2 configuration (`VoiceConfig`, env or ~/.config/drakter/voice.toml).
# ⚠️ Align with voice/config.py (WP1) at integration time: names not listed here do not pass.
VOICE_CONFIG_VARS: Final = (
    "DRAKTER_VOICE_MODELS_DIR",
    "DRAKTER_VOICE_CONFIG",
    "DRAKTER_STT_MODEL",
    "DRAKTER_WAKE_THRESHOLD",
    "DRAKTER_FOLLOWUP_S",
    "DRAKTER_IDLE_NUDGE_S",
    "DRAKTER_TURN_STOP_SECS",
    "DRAKTER_FILLER_AFTER_MS",
    "DRAKTER_BARGEIN_MIN_WORDS",
    "DRAKTER_BARGEIN_DECIDE_MS",
    "DRAKTER_DUCK_GAIN",
    "DRAKTER_TOOL_PHRASE_GAP_S",
    "DRAKTER_FISH_FREE_UNTIL",
    "DRAKTER_ALLOW_PAID",
)
# Secrets the voice process needs. Taken only by exact name; never logged.
VOICE_SECRETS: Final = ("FISH_API_KEY",)
# Where voice.toml / voces.toml and the models live; the child resolves them itself.
_XDG: Final = ("XDG_CONFIG_HOME", "XDG_DATA_HOME")

_BACKOFF_BASE_S: Final = 1.0
_BACKOFF_CAP_S: Final = 60.0
_STABLE_AFTER_S: Final = 60.0  # a run this long clears the failure count
_MAX_FAILURES: Final = 8
_SHUTDOWN_WAIT_S: Final = 5.0
_TERMINATE_WAIT_S: Final = 3.0
_KILL_WAIT_S: Final = 2.0


def build_env(
    *,
    data_dir: Path,
    runtime_dir: Path,
    environ: Mapping[str, str] | None = None,
    file_values: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the child's environment from scratch.

    ``file_values`` only contributes voice configuration and ``VOICE_SECRETS``: the
    per-user ``.env`` also holds other API keys (Anthropic), which must not reach voice.
    """
    source = os.environ if environ is None else environ
    env = {name: source[name] for name in (*_INHERITED, *_AUDIO, *_XDG) if name in source}
    for name in (*VOICE_CONFIG_VARS, *VOICE_SECRETS):
        if name in source:
            env[name] = source[name]
        elif file_values and name in file_values:
            env[name] = file_values[name]
    env["DRAKTER_RUNTIME_DIR"] = str(runtime_dir)
    env["DRAKTER_DATA_DIR"] = str(data_dir)
    return env


class VoiceSupervisor:
    def __init__(
        self,
        *,
        python: Path,
        project_root: Path,
        env: Mapping[str, str],
        on_spawn: Callable[[], Awaitable[None]],
        on_exit: Callable[[int | None], Awaitable[None]],
        on_give_up: Callable[[], Awaitable[None]],
    ) -> None:
        self._python = python
        self._root = project_root
        self._env = dict(env)
        self._on_spawn = on_spawn
        self._on_exit = on_exit
        self._on_give_up = on_give_up
        self._proc: asyncio.subprocess.Process | None = None
        self._stopping = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="voice-supervisor")

    async def stop(self, request_shutdown: Callable[[], Awaitable[object]]) -> None:
        """`shutdown` over IPC, then terminate, then kill, each with its own limit."""
        self._stopping.set()
        proc = self._proc
        if proc is not None and proc.returncode is None:
            try:
                await asyncio.wait_for(request_shutdown(), _KILL_WAIT_S)
            except Exception as exc:  # noqa: BLE001 - the signals below still apply
                logger.info(
                    "Voice shutdown not acknowledged",
                    extra={"event": "voice_shutdown_unacked", "error": type(exc).__name__},
                )
            if not await self._exited(proc, _SHUTDOWN_WAIT_S):
                self._signal(proc, signal.SIGTERM)
                if not await self._exited(proc, _TERMINATE_WAIT_S):
                    self.kill()
                    await self._exited(proc, _KILL_WAIT_S)
        task, self._task = self._task, None
        if task is not None:
            try:
                await asyncio.wait_for(task, _KILL_WAIT_S)
            except TimeoutError:
                pass  # wait_for already cancelled it

    def kill(self) -> None:
        """Kill the whole group, so that a Piper child goes too. The run loop restarts it."""
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    @staticmethod
    def _signal(proc: asyncio.subprocess.Process, signum: signal.Signals) -> None:
        try:
            proc.send_signal(signum)
        except ProcessLookupError:
            pass

    @staticmethod
    async def _exited(proc: asyncio.subprocess.Process, timeout: float) -> bool:
        try:
            await asyncio.wait_for(proc.wait(), timeout)
        except TimeoutError:
            return False
        return True

    async def _run_once(self) -> int | None:
        await self._on_spawn()
        try:
            self._proc = await asyncio.create_subprocess_exec(
                str(self._python),
                "-m",
                "voice",
                "run",
                cwd=self._root,
                env=self._env,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            logger.error(
                "Voice process did not start",
                extra={"event": "voice_spawn_failed", "error": type(exc).__name__},
            )
            return None
        proc = self._proc
        logger.info("Voice process started", extra={"event": "voice_started", "pid": proc.pid})
        if self._stopping.is_set():  # stop() ran while this was spawning
            self.kill()
        code = await proc.wait()
        logger.info("Voice process exited", extra={"event": "voice_exited", "code": code})
        return code

    async def _run(self) -> None:
        failures = 0
        while not self._stopping.is_set():
            started = time.monotonic()
            code = await self._run_once()
            if self._stopping.is_set():
                return
            await self._on_exit(code)
            failures = 0 if time.monotonic() - started >= _STABLE_AFTER_S else failures + 1
            if failures >= _MAX_FAILURES:
                logger.error("Voice process gave up", extra={"event": "voice_gave_up"})
                await self._on_give_up()
                return
            delay = min(_BACKOFF_BASE_S * 2 ** max(failures - 1, 0), _BACKOFF_CAP_S)
            try:
                await asyncio.wait_for(self._stopping.wait(), delay)
            except TimeoutError:
                pass
