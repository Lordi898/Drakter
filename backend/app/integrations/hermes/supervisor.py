"""Runs the Hermes runner (runner/drakter_runner.py) as a watched subprocess, Linux.

Hermes is not trusted: it gets an allowlisted environment, a dedicated HOME and a
guard nonce that changes on every launch, and turns only start after its `ready`
matches what this side expects. Nothing here raises towards the caller: a failure
ends in state="failed" with a safe `detail`, and every turn ends in a terminal event.
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
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal
from urllib.parse import urlsplit
from uuid import UUID

from app.core.config import BIND_HOST, ensure_private_dir
from app.core.logging import redact, register_secret
from app.integrations.hermes.home import (
    DEFAULT_HOME_NAME,
    DEFAULT_REASONING_EFFORT,
    GUARD_NONCE_ENV,
    GUARD_PROOF,
    MCP_TOKEN_ENV,
    MCP_URL_ENV,
    HomeError,
    HomeManifest,
    HomePaths,
    captured_tool_name,
    materialize_home,
    verify_home,
)
from app.integrations.hermes.settings import HERMES_COMMIT, AgentSettings

logger = logging.getLogger(__name__)

SupervisorState = Literal["stopped", "starting", "ready", "restarting", "failed"]

RUNNER_PATH: Final = Path(__file__).resolve().parent / "runner" / "drakter_runner.py"
READY_TIMEOUT_S: Final = 120.0  # imports are slow when the machine is swapping
EOF_GRACE_S: Final = 3.0  # the runner exits by itself once stdin closes
STOP_GRACE_S: Final = 5.0
MAX_RESTARTS: Final = 5
BACKOFF_BASE_S: Final = 1.0
BACKOFF_MAX_S: Final = 30.0
STABLE_AFTER_S: Final = 300.0
LOG_MAX_BYTES: Final = 5 * 1024 * 1024
STREAM_LIMIT: Final = 16 * 1024 * 1024  # a `completed` line holds the whole answer
LOG_LINE_MAX: Final = 8192
EXIT_FOREIGN_TOOLS: Final = 3
TERMINAL_EVENTS: Final = frozenset({"completed", "cancelled", "failed"})
_PASSTHROUGH_ENV: Final = ("LANG", "LC_ALL", "LC_CTYPE", "TZ")


class _Fatal(Exception):
    """Retrying cannot help. str() is the safe detail."""


class _Transient(Exception):
    """Worth a restart with backoff. str() is the safe detail."""


class _RedactedLog:
    """Runner stderr, line by line, after redaction, 0600, one rotated copy."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd = self._open()

    def _open(self) -> int:
        return os.open(
            self._path,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )

    def write(self, raw: bytes) -> None:
        text = raw.decode("utf-8", "replace").rstrip("\r\n")[:LOG_LINE_MAX]
        line = f"{redact(text)}\n".encode()
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


@dataclass(slots=True)
class _Turn:
    turn_id: str
    events: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    finished: asyncio.Event = field(default_factory=asyncio.Event)
    stopping: bool = False


def _token_text(token: Any) -> str:
    reveal = getattr(token, "reveal", None)
    return reveal() if callable(reveal) else str(token)


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
        home_name: str = DEFAULT_HOME_NAME,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    ) -> None:
        self._settings = settings
        self._data_dir = Path(data_dir)
        self._tool_names = tuple(tool_names)
        self._agent_tool_token = agent_tool_token
        self._agent_tools_url = agent_tools_url
        self._repo_root = Path(repo_root)
        self._on_state = on_state
        self._ready_timeout_s = ready_timeout_s
        self._home_name = home_name
        self._reasoning_effort = reasoning_effort
        self._paths = HomePaths.under(self._data_dir, home_name)
        self._state: SupervisorState = "stopped"
        self._detail = ""
        self._nonce = ""
        self._manifest: HomeManifest | None = None
        self._proc: asyncio.subprocess.Process | None = None
        self._log: _RedactedLog | None = None
        self._tasks: list[asyncio.Task[None]] = []
        self._ready: asyncio.Future[dict[str, Any]] | None = None
        self._turn: _Turn | None = None
        self._task: asyncio.Task[None] | None = None
        self._settled = asyncio.Event()
        self._restarts = 0
        self._kill_requested = False

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
    def child_pid(self) -> int | None:
        proc = self._proc
        return proc.pid if proc is not None and proc.returncode is None else None

    async def start(self) -> None:
        """Returns at once: the launch goes on in the background and on_state reports it."""
        if self._task is not None and not self._task.done():
            return
        self._settled = asyncio.Event()
        self._restarts = 0
        self._state, self._detail = "stopped", ""
        self._set_state("starting", "")
        self._task = asyncio.create_task(self._run(), name="hermes-supervisor")

    async def wait_settled(self) -> None:
        """Until the first launch has ended in ready, restarting or failed."""
        await self._settled.wait()

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._terminate()
        self._set_state("stopped", "")

    async def run_turn(
        self,
        turn_id: UUID | str,
        session_id: UUID | str,
        text: str,
        instructions: str,
        reasoning_effort: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Raw runner events; the last one is always terminal. A dead runner never repeats a turn."""
        tid = str(turn_id)
        if self._turn is not None:
            yield {"ev": "failed", "turn_id": tid, "code": "agent_busy", "message": "Ya hay un turno en curso."}
            return
        if self._state != "ready":
            yield {"ev": "failed", "turn_id": tid, "code": "agent_unavailable", "message": "El agente no está listo."}
            return
        turn = _Turn(tid)
        self._turn = turn
        message = {"op": "turn", "turn_id": tid, "session_id": str(session_id), "input": text}
        if reasoning_effort is not None:  # this turn only; else the home's agent.reasoning_effort
            message["reasoning_effort"] = reasoning_effort
        if not await self._send({**message, "instructions": instructions}):
            self._finish_turn(turn, self._lost_event(turn))
        terminal = False
        try:
            while not terminal:
                event = await turn.events.get()
                terminal = event.get("ev") in TERMINAL_EVENTS
                yield event
        finally:
            if not terminal:  # abandoned by the consumer: Hermes must not keep working unseen
                task = asyncio.ensure_future(self.stop_turn(tid))
                task.add_done_callback(lambda done: done.exception())

    async def stop_turn(self, turn_id: UUID | str, grace_s: float = STOP_GRACE_S) -> None:
        """`stop` to the runner; with no terminal in `grace_s`, kill the group and restart."""
        turn = self._turn
        if turn is None or turn.turn_id != str(turn_id):
            return
        turn.stopping = True
        await self._send({"op": "stop", "turn_id": turn.turn_id})
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(turn.finished.wait(), grace_s)
            return
        logger.warning("hermes_turn_kill")
        proc = self._proc
        if proc is not None and proc.returncode is None:
            self._kill_requested = True
            _signal_group(proc.pid, signal.SIGKILL)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(turn.finished.wait(), EOF_GRACE_S)

    async def steer_turn(self, turn_id: UUID | str, text: str) -> bool:
        """`steer` to the runner for the active turn; it answers `steered` in the turn stream."""
        turn = self._turn
        if turn is None or turn.turn_id != str(turn_id) or turn.stopping:
            return False
        return await self._send({"op": "steer", "turn_id": turn.turn_id, "text": text})

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

    async def _send(self, message: dict[str, Any]) -> bool:
        proc = self._proc
        if proc is None or proc.stdin is None or proc.returncode is not None:
            return False
        try:
            proc.stdin.write(json.dumps(message, ensure_ascii=False).encode() + b"\n")
            await proc.stdin.drain()
        except (OSError, RuntimeError):
            return False
        return True

    def _finish_turn(self, turn: _Turn, event: dict[str, Any]) -> None:
        turn.events.put_nowait(event)
        turn.finished.set()
        if self._turn is turn:
            self._turn = None

    @staticmethod
    def _lost_event(turn: _Turn) -> dict[str, Any]:
        if turn.stopping:
            return {"ev": "cancelled", "turn_id": turn.turn_id}
        return {
            "ev": "failed",
            "turn_id": turn.turn_id,
            "code": "agent_disconnected",
            "message": "El agente se ha detenido a mitad del turno.",
        }

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            while True:
                launched_at = loop.time()
                try:
                    proc = await self._launch()
                    await self._await_ready(proc)
                    self._set_state("ready", "")
                    self._settled.set()
                    code = await proc.wait()
                    detail = f"runner exited with code {code}"
                except _Transient as exc:
                    detail = str(exc)
                await self._terminate()
                if self._kill_requested:  # a stop that needed force is not a crash
                    self._kill_requested = False
                    self._set_state("restarting", "restarting after a forced stop")
                    continue
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

    def _python(self) -> str:
        found = shutil.which(str(self._settings.hermes_python))
        if found is None:
            raise _Fatal("python of the Hermes venv not found")
        # Not resolved: a venv python is a symlink and needs its own path to find the venv.
        return os.path.abspath(found)

    def _child_env(self, python: str) -> dict[str, str]:
        s, paths = self._settings, self._paths
        env = {name: os.environ[name] for name in _PASSTHROUGH_ENV if name in os.environ}
        env.setdefault("LANG", "C.UTF-8")
        env.update(
            PATH=os.pathsep.join((os.path.dirname(python), "/usr/local/bin", "/usr/bin", "/bin")),
            HOME=str(paths.user_home),
            XDG_CONFIG_HOME=str(paths.user_home / ".config"),
            XDG_CACHE_HOME=str(paths.user_home / ".cache"),
            XDG_DATA_HOME=str(paths.user_home / ".local" / "share"),
            TMPDIR=str(paths.tmp),
            HERMES_HOME=str(paths.root),
            PYTHONDONTWRITEBYTECODE="1",  # no __pycache__ inside plugins/
            PYTHONUNBUFFERED="1",
            DRAKTER_PARENT_PID=str(os.getpid()),
        )
        env[MCP_URL_ENV] = self._agent_tools_url
        env[MCP_TOKEN_ENV] = _token_text(self._agent_tool_token)
        env[GUARD_NONCE_ENV] = self._nonce
        if s.model_provider == "anthropic" and s.anthropic_api_key is not None:
            env["ANTHROPIC_API_KEY"] = s.anthropic_api_key.get_secret_value()
        return env

    async def _launch(self) -> asyncio.subprocess.Process:
        s = self._settings
        python = self._python()
        if not _is_loopback_http(self._agent_tools_url):
            raise _Fatal("the agent tools URL must be plain http on loopback")
        if s.model_provider == "anthropic" and (
            s.anthropic_api_key is None or not s.anthropic_api_key.get_secret_value()
        ):
            raise _Fatal("ANTHROPIC_API_KEY is not configured")
        try:
            self._manifest = materialize_home(
                s,
                self._data_dir,
                self._tool_names,
                self._repo_root,
                home_name=self._home_name,
                reasoning_effort=self._reasoning_effort,
            )
        except HomeError as exc:
            raise _Fatal(str(exc)) from exc

        self._nonce = secrets.token_hex(32)
        register_secret(self._nonce)
        register_secret(_token_text(self._agent_tool_token))
        if s.anthropic_api_key is not None:
            register_secret(s.anthropic_api_key.get_secret_value())
        (self._paths.run / GUARD_PROOF).unlink(missing_ok=True)
        logs_dir = self._data_dir / "logs"
        try:
            ensure_private_dir(logs_dir)
            verify_home(self._manifest)
            self._log = _RedactedLog(logs_dir / "hermes.log")
            proc = await asyncio.create_subprocess_exec(
                python,
                "-I",
                "-B",  # -I ignores PYTHONDONTWRITEBYTECODE: no __pycache__ inside plugins/
                str(RUNNER_PATH),
                cwd=self._paths.cwd,
                env=self._child_env(python),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,  # own group: stop reaches every descendant
                limit=STREAM_LIMIT,
            )
        except HomeError as exc:
            raise _Fatal(str(exc)) from exc
        except (OSError, ValueError) as exc:
            raise _Fatal(f"the runner could not be started: {type(exc).__name__}") from exc
        self._proc = proc
        self._ready = asyncio.get_running_loop().create_future()
        self._tasks = [
            asyncio.create_task(self._read_protocol(proc)),
            asyncio.create_task(self._read_stderr(proc)),
        ]
        return proc

    async def _read_stderr(self, proc: asyncio.subprocess.Process) -> None:
        assert proc.stderr is not None
        while True:
            try:
                raw = await proc.stderr.readline()
            except ValueError:  # one line above STREAM_LIMIT, already discarded by asyncio
                continue
            if not raw:
                return
            if self._log is not None:
                self._log.write(raw)

    async def _read_protocol(self, proc: asyncio.subprocess.Process) -> None:
        assert proc.stdout is not None
        while True:
            try:
                raw = await proc.stdout.readline()
            except ValueError:
                logger.warning("hermes_protocol_line_too_long")
                continue
            if not raw:
                break
            try:
                event = json.loads(raw)
            except ValueError:
                event = None
            if isinstance(event, dict):
                self._dispatch(event)
        if self._ready is not None and not self._ready.done():
            self._ready.set_result({})
        turn = self._turn
        if turn is not None:
            self._finish_turn(turn, self._lost_event(turn))

    def _dispatch(self, event: dict[str, Any]) -> None:
        kind = event.get("ev")
        if kind == "ready":
            if self._ready is not None and not self._ready.done():
                self._ready.set_result(event)
            return
        turn = self._turn
        if turn is None or event.get("turn_id") != turn.turn_id:
            return  # a late event of a finished turn, or something this side never asked for
        if kind in TERMINAL_EVENTS:
            self._finish_turn(turn, event)
        else:
            turn.events.put_nowait(event)

    async def _await_ready(self, proc: asyncio.subprocess.Process) -> None:
        assert self._ready is not None
        try:
            ready = await asyncio.wait_for(asyncio.shield(self._ready), self._ready_timeout_s)
        except TimeoutError as exc:
            raise _Transient("the runner did not become ready in time") from exc
        if not ready:
            code = await proc.wait()
            if code == EXIT_FOREIGN_TOOLS:
                raise _Fatal("Hermes offered tools outside the Drakter catalog")
            raise _Transient(f"the runner exited during startup with code {code}")
        nonce = ready.get("nonce")
        if not isinstance(nonce, str) or not secrets.compare_digest(nonce.encode(), self._nonce.encode()):
            raise _Fatal("drakter_guard did not load: turns are refused")
        if ready.get("commit") != HERMES_COMMIT:
            raise _Fatal("this Hermes is not the verified commit")
        tools = ready.get("tools")
        expected = {captured_tool_name(name) for name in self._tool_names}
        if not isinstance(tools, list) or set(tools) != expected:
            raise _Fatal("Hermes does not offer exactly the Drakter catalog")

    async def _terminate(self) -> None:
        """Close stdin (the runner exits on EOF), then SIGTERM, then SIGKILL, then sweep the group."""
        proc, self._proc = self._proc, None
        if proc is not None:
            pgid = proc.pid
            if proc.stdin is not None:
                proc.stdin.close()
            if not await self._exited(proc, EOF_GRACE_S):
                _signal_group(pgid, signal.SIGTERM)
                if not await self._exited(proc, EOF_GRACE_S):
                    logger.warning("hermes_stop_timeout")
            _signal_group(pgid, signal.SIGKILL)
            await proc.wait()
            tasks, self._tasks = self._tasks, []
            if tasks:
                await asyncio.wait(tasks, timeout=2.0)
                for task in tasks:
                    task.cancel()
        turn = self._turn
        if turn is not None:
            self._finish_turn(turn, self._lost_event(turn))
        if self._log is not None:
            self._log.close()
            self._log = None

    @staticmethod
    async def _exited(proc: asyncio.subprocess.Process, timeout_s: float) -> bool:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(proc.wait(), timeout_s)
            return True
        return False
