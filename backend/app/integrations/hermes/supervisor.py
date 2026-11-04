"""Runs `hermes gateway run` as a watched subprocess (Linux).

Hermes is not trusted: it gets an allowlisted environment, a dedicated HOME, and
a key and guard nonce that change on every launch. Nothing here raises towards
the caller: a failure ends in state="failed" with a safe `detail`.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
import os
import secrets
import shutil
import signal
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Final, Literal
from urllib.parse import urlsplit

import httpx

from app.core.config import BIND_HOST, ensure_private_dir
from app.core.logging import redact, register_secret
from app.integrations.hermes.home import (
    GUARD_NONCE_ENV,
    GUARD_PROOF,
    MCP_TOKEN_ENV,
    MCP_URL_ENV,
    HomeError,
    HomeManifest,
    HomePaths,
    materialize_home,
    verify_home,
)
from app.integrations.hermes.settings import AgentSettings

logger = logging.getLogger(__name__)

SupervisorState = Literal["stopped", "starting", "ready", "restarting", "failed"]

READY_TIMEOUT_S: Final = 120.0  # imports are slow when the machine is swapping
POLL_INTERVAL_S: Final = 0.25
STOP_GRACE_S: Final = 15.0
HEALTH_INTERVAL_S: Final = 10.0
HEALTH_MAX_FAILURES: Final = 3
MAX_RESTARTS: Final = 5
BACKOFF_BASE_S: Final = 1.0
BACKOFF_MAX_S: Final = 30.0
STABLE_AFTER_S: Final = 300.0
LOG_MAX_BYTES: Final = 5 * 1024 * 1024
STREAM_LIMIT: Final = 1024 * 1024
LOG_LINE_MAX: Final = 8192
_PASSTHROUGH_ENV: Final = ("LANG", "LC_ALL", "LC_CTYPE", "TZ")
_REQUIRED_FEATURES: Final = ("run_submission", "run_events_sse", "run_stop")
_CHILD_RECORD: Final = "gateway-child.json"


class _Fatal(Exception):
    """Retrying cannot help. str() is the safe detail."""


class _Transient(Exception):
    """Worth a restart with backoff. str() is the safe detail."""


class _RedactedLog:
    """Hermes stdout and stderr, line by line, after redaction, 0600, one rotated copy."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd = self._open()

    def _open(self) -> int:
        return os.open(
            self._path,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )

    def write(self, stream: str, raw: bytes) -> None:
        text = raw.decode("utf-8", "replace").rstrip("\r\n")[:LOG_LINE_MAX]
        line = f"{stream}: {redact(text)}\n".encode()
        try:
            if os.fstat(self._fd).st_size + len(line) > LOG_MAX_BYTES:
                os.close(self._fd)
                self._fd = -1
                os.replace(self._path, self._path.with_name(self._path.name + ".1"))
                self._fd = self._open()
            os.write(self._fd, line)
        except OSError:
            logger.warning("hermes_log_write_failed")

    def close(self) -> None:
        if self._fd >= 0:
            with contextlib.suppress(OSError):
                os.close(self._fd)
            self._fd = -1


def _token_text(token: Any) -> str:
    reveal = getattr(token, "reveal", None)
    return reveal() if callable(reveal) else str(token)


def _process_start_ticks(pid: int) -> int | None:
    """Field 22 of /proc/<pid>/stat: tells a live process from a reused pid."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii", errors="replace")
        return int(stat.rsplit(")", 1)[1].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def _is_loopback_http(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "http" and parts.hostname == BIND_HOST and parts.username is None


def _signal_group(pgid: int, signum: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pgid, signum)


class HermesSupervisor:
    def __init__(
        self,
        settings: AgentSettings,
        data_dir: Path,
        tool_names: Sequence[str],
        agent_tool_token: Any,
        agent_tools_url: str,
        repo_root: Path,
        on_state: Callable[[str], Any] | None = None,
        *,
        ready_timeout_s: float = READY_TIMEOUT_S,
    ) -> None:
        self._settings = settings
        self._data_dir = Path(data_dir)
        self._tool_names = tuple(tool_names)
        self._agent_tool_token = agent_tool_token
        self._agent_tools_url = agent_tools_url
        self._repo_root = Path(repo_root)
        self._on_state = on_state
        self._ready_timeout_s = ready_timeout_s
        self._paths = HomePaths.under(self._data_dir)
        self._state: SupervisorState = "stopped"
        self._detail = ""
        self._api_key = ""
        self._nonce = ""
        self._manifest: HomeManifest | None = None
        self._proc: asyncio.subprocess.Process | None = None
        self._pumps: list[asyncio.Task[None]] = []
        self._log: _RedactedLog | None = None
        self._task: asyncio.Task[None] | None = None
        self._settled = asyncio.Event()
        self._restarts = 0

    @property
    def state(self) -> SupervisorState:
        return self._state

    @property
    def detail(self) -> str:
        return self._detail

    @property
    def manifest(self) -> HomeManifest | None:
        return self._manifest

    @property
    def api_base(self) -> str:
        return f"http://{BIND_HOST}:{self._settings.hermes_port}"

    @property
    def child_pid(self) -> int | None:
        proc = self._proc
        return proc.pid if proc is not None and proc.returncode is None else None

    def api_key(self) -> str:
        return self._api_key

    async def start(self) -> None:
        """Returns once the first launch has settled; restarts continue in the background."""
        if self._task is not None and not self._task.done():
            return
        self._settled = asyncio.Event()
        self._restarts = 0
        self._task = asyncio.create_task(self._run(), name="hermes-supervisor")
        await self._settled.wait()

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._terminate()
        self._set_state("stopped", "")

    def _set_state(self, state: SupervisorState, detail: str) -> None:
        changed = state != self._state
        self._state, self._detail = state, detail
        if not changed:
            return
        logger.info("hermes_state", extra={"state": state, "detail": detail})
        if self._on_state is None:
            return
        try:
            result = self._on_state(state)
            if inspect.isawaitable(result):
                asyncio.ensure_future(result)
        except Exception:
            logger.exception("hermes_on_state_failed")

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            self._set_state("starting", "")
            while True:
                launched_at = loop.time()
                try:
                    proc = await self._launch()
                    await self._await_ready(proc)
                    self._set_state("ready", "")
                    self._settled.set()
                    detail = await self._watch(proc)
                except _Transient as exc:
                    detail = str(exc)
                await self._terminate()
                if loop.time() - launched_at >= STABLE_AFTER_S:
                    self._restarts = 0
                self._restarts += 1
                if self._restarts > MAX_RESTARTS:
                    raise _Fatal(f"too many restarts: {detail}")
                self._set_state("restarting", detail)
                self._settled.set()
                backoff = BACKOFF_BASE_S * 2 ** (self._restarts - 1)
                await asyncio.sleep(min(backoff, BACKOFF_MAX_S))
        except _Fatal as exc:
            await self._terminate()
            self._set_state("failed", str(exc))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("hermes_supervisor_crashed")
            await self._terminate()
            self._set_state("failed", "internal supervisor error")
        finally:
            self._settled.set()

    def _binary(self) -> str:
        found = shutil.which(self._settings.hermes_command)
        if found is None:
            raise _Fatal("hermes executable not found")
        return os.path.abspath(found)

    def _child_env(self, binary: str, nonce: str) -> dict[str, str]:
        s, paths = self._settings, self._paths
        env = {name: os.environ[name] for name in _PASSTHROUGH_ENV if name in os.environ}
        env.setdefault("LANG", "C.UTF-8")
        env.update(
            PATH=os.pathsep.join((os.path.dirname(binary), "/usr/local/bin", "/usr/bin", "/bin")),
            HOME=str(paths.user_home),
            XDG_CONFIG_HOME=str(paths.user_home / ".config"),
            XDG_CACHE_HOME=str(paths.user_home / ".cache"),
            XDG_DATA_HOME=str(paths.user_home / ".local" / "share"),
            TMPDIR=str(paths.tmp),
            HERMES_HOME=str(paths.root),
            PYTHONDONTWRITEBYTECODE="1",  # no __pycache__ inside plugins/
            PYTHONUNBUFFERED="1",
            API_SERVER_ENABLED="true",
            API_SERVER_HOST=BIND_HOST,
            API_SERVER_PORT=str(s.hermes_port),
            API_SERVER_KEY=self._api_key,
        )
        env[MCP_URL_ENV] = self._agent_tools_url
        env[MCP_TOKEN_ENV] = _token_text(self._agent_tool_token)
        env[GUARD_NONCE_ENV] = nonce
        if s.model_provider == "anthropic" and s.anthropic_api_key is not None:
            env["ANTHROPIC_API_KEY"] = s.anthropic_api_key.get_secret_value()
        return env

    async def _launch(self) -> asyncio.subprocess.Process:
        s = self._settings
        binary = self._binary()
        if not _is_loopback_http(self._agent_tools_url):
            raise _Fatal("the agent tools URL must be plain http on loopback")
        if s.model_provider == "anthropic" and (
            s.anthropic_api_key is None or not s.anthropic_api_key.get_secret_value()
        ):
            raise _Fatal("ANTHROPIC_API_KEY is not configured")
        try:
            self._manifest = materialize_home(s, self._data_dir, self._tool_names, self._repo_root)
        except HomeError as exc:
            raise _Fatal(str(exc)) from exc

        await self._reap_stale_child()
        self._api_key = secrets.token_urlsafe(48)
        nonce = secrets.token_hex(32)
        for secret in (self._api_key, nonce, _token_text(self._agent_tool_token)):
            register_secret(secret)
        if s.anthropic_api_key is not None:
            register_secret(s.anthropic_api_key.get_secret_value())
        proof = self._paths.run / GUARD_PROOF
        proof.unlink(missing_ok=True)
        env = self._child_env(binary, nonce)
        logs_dir = self._data_dir / "logs"
        try:
            ensure_private_dir(logs_dir)
            verify_home(self._manifest)
            self._log = _RedactedLog(logs_dir / "hermes.log")
            proc = await asyncio.create_subprocess_exec(
                binary,
                "gateway",
                "run",
                "--external-supervisor",
                cwd=self._paths.cwd,
                env=env,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,  # own group: stop reaches every descendant
                limit=STREAM_LIMIT,
            )
        except HomeError as exc:
            raise _Fatal(str(exc)) from exc
        except (OSError, ValueError) as exc:
            raise _Fatal(f"hermes could not be started: {type(exc).__name__}") from exc
        self._proc = proc
        self._record_child(proc.pid)
        self._pumps = [
            asyncio.create_task(self._pump("stdout", proc.stdout)),
            asyncio.create_task(self._pump("stderr", proc.stderr)),
        ]
        self._nonce = nonce
        return proc

    def _record_child(self, pid: int) -> None:
        record = {"pid": pid, "start_ticks": _process_start_ticks(pid)}
        path = self._paths.run / _CHILD_RECORD
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(record, handle)

    async def _reap_stale_child(self) -> None:
        """A backend killed with SIGKILL leaves Hermes running: finish it here."""
        path = self._paths.run / _CHILD_RECORD
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            pid, ticks = int(record["pid"]), int(record["start_ticks"])
        except (OSError, ValueError, KeyError, TypeError):
            path.unlink(missing_ok=True)
            return
        if _process_start_ticks(pid) == ticks:
            logger.warning("hermes_stale_child_reaped", extra={"pid": pid})
            _signal_group(pid, signal.SIGTERM)
            deadline = asyncio.get_running_loop().time() + STOP_GRACE_S
            while _process_start_ticks(pid) == ticks and asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(POLL_INTERVAL_S)
            _signal_group(pid, signal.SIGKILL)
        path.unlink(missing_ok=True)

    async def _pump(self, name: str, stream: asyncio.StreamReader | None) -> None:
        if stream is None:
            return
        while True:
            try:
                raw = await stream.readline()
            except ValueError:  # one line above STREAM_LIMIT, already discarded by asyncio
                continue
            if not raw:
                return
            if self._log is not None:
                self._log.write(name, raw)

    async def _await_ready(self, proc: asyncio.subprocess.Process) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._ready_timeout_s
        async with httpx.AsyncClient(base_url=self.api_base, timeout=5.0, trust_env=False) as client:
            while True:
                if proc.returncode is not None:
                    raise _Transient("hermes exited during startup")
                if loop.time() >= deadline:
                    raise _Transient("hermes did not become healthy in time")
                try:
                    response = await client.get("/health")
                    if response.status_code == 200 and response.json().get("status") == "ok":
                        break
                except (httpx.HTTPError, ValueError, AttributeError):
                    pass
                await asyncio.sleep(POLL_INTERVAL_S)
            await self._check_key_required(client)
            await self._check_capabilities(client)
        await self._await_guard_proof(deadline)

    async def _check_key_required(self, client: httpx.AsyncClient) -> None:
        """Hermes ignores a weak API_SERVER_KEY: without this the API could be open."""
        try:
            response = await client.get("/v1/capabilities")
        except httpx.HTTPError as exc:
            raise _Transient("hermes capabilities could not be read") from exc
        if response.status_code != 401:
            raise _Fatal("the Hermes API answers without the launch key")

    async def _check_capabilities(self, client: httpx.AsyncClient) -> None:
        try:
            response = await client.get(
                "/v1/capabilities", headers={"Authorization": f"Bearer {self._api_key}"}
            )
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise _Transient("hermes capabilities could not be read") from exc
        if response.status_code != 200 or not isinstance(data, dict):
            # A 401 means another process answers on this port: our key is one launch old at most.
            raise _Fatal("the process on the Hermes port rejected the launch key")
        features = data.get("features") or {}
        auth = data.get("auth") or {}
        if (
            data.get("object") != "hermes.api_server.capabilities"
            or auth.get("required") is not True
            or not all(features.get(name) is True for name in _REQUIRED_FEATURES)
        ):
            raise _Fatal("hermes does not offer the required API")

    async def _await_guard_proof(self, deadline: float) -> None:
        loop = asyncio.get_running_loop()
        path = self._paths.run / GUARD_PROOF
        while True:
            with contextlib.suppress(OSError):
                if secrets.compare_digest(path.read_bytes(), self._nonce.encode()):
                    return
            if loop.time() >= deadline:
                raise _Fatal("drakter_guard did not load: runs are refused")
            await asyncio.sleep(POLL_INTERVAL_S)

    async def _watch(self, proc: asyncio.subprocess.Process) -> str:
        """Blocks while Hermes is healthy; returns the safe reason it stopped being so."""
        failures = 0
        exited = asyncio.create_task(proc.wait())
        try:
            async with httpx.AsyncClient(base_url=self.api_base, timeout=5.0, trust_env=False) as client:
                while True:
                    done, _ = await asyncio.wait({exited}, timeout=HEALTH_INTERVAL_S)
                    if done:
                        return f"hermes exited with code {exited.result()}"
                    try:
                        healthy = (await client.get("/health")).status_code == 200
                    except httpx.HTTPError:
                        healthy = False
                    failures = 0 if healthy else failures + 1
                    if failures >= HEALTH_MAX_FAILURES:
                        return "hermes stopped answering"
        finally:
            exited.cancel()

    async def _terminate(self) -> None:
        """SIGTERM to the group, SIGKILL after the grace period, then sweep what is left."""
        proc, self._proc = self._proc, None
        self._api_key = ""
        if proc is not None:
            pgid = proc.pid
            if proc.returncode is None:
                _signal_group(pgid, signal.SIGTERM)
                try:
                    await asyncio.wait_for(proc.wait(), STOP_GRACE_S)
                except TimeoutError:
                    logger.warning("hermes_stop_timeout")
            _signal_group(pgid, signal.SIGKILL)
            await proc.wait()
            pumps, self._pumps = self._pumps, []
            if pumps:
                await asyncio.wait(pumps, timeout=2.0)
                for pump in pumps:
                    pump.cancel()
            with contextlib.suppress(OSError):
                (self._paths.run / _CHILD_RECORD).unlink(missing_ok=True)
        if self._log is not None:
            self._log.close()
            self._log = None
