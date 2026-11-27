"""Supervisor and client of the desktop helper (`/usr/bin/python3 -I hands/helper/main.py`), CONTRACT §5.

One per backend process (`ensure_client(state)`). JSONL over the child's stdin/stdout with the `IpcMessage`
envelope; results are validated with `HELPER_RESULTS` and events with `HELPER_EVTS`. Restarts with
exponential backoff, like the voice. Never logs line contents: results carry screen text.

`call` works from any event loop: the confirmation pipeline runs approved handlers in a worker thread
with its own loop (`permissions/tool_gate.py`), and the pipes belong to the loop that started the child.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

from drakter_contracts.hands_ipc import (
    HELPER_CMDS,
    HELPER_EVTS,
    HELPER_RESULTS,
    HELPER_TIMEOUTS_S,
    MAX_HELPER_LINE_BYTES,
    HHello,
    HHelloResult,
)
from pydantic import BaseModel, ValidationError

from app.integrations.hands.lists import HELPER_DIR

logger = logging.getLogger("drakter.hands")

SYSTEM_PYTHON: Final = Path("/usr/bin/python3")
HELPER_SCRIPT: Final = HELPER_DIR / "main.py"
# Exact names only. GTK_PATH, GTK_EXE_PREFIX, LOCPATH, GSETTINGS_SCHEMA_DIR, GIO_MODULE_DIR and the snap
# variables never pass (spike 03 §1.4.1): the environment is built from scratch.
_INHERITED: Final = (
    "HOME", "USER", "LOGNAME", "LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LC_CTYPE", "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS", "WAYLAND_DISPLAY", "DISPLAY", "XAUTHORITY", "XDG_SESSION_TYPE",
    "XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "DESKTOP_SESSION", "XDG_DATA_HOME", "XDG_CONFIG_HOME",
    "AT_SPI_BUS_ADDRESS",
)
_XDG_DATA_DIRS: Final = "/usr/share/ubuntu:/usr/share/gnome:/usr/local/share/:/usr/share/:/var/lib/snapd/desktop"
_BACKOFF_BASE_S: Final = 1.0
_BACKOFF_CAP_S: Final = 60.0
_STABLE_AFTER_S: Final = 60.0
_MAX_FAILURES: Final = 8
_READY_WAIT_S: Final = 6.0


class HandsError(Exception):
    """The helper answered `err{code, message}`, or is not there (`companion_unavailable`)."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.message = message or code


def build_env(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if environ is None else environ
    env = {k: source[k] for k in _INHERITED if k in source}
    env["PATH"] = "/usr/bin:/bin"
    env["XDG_DATA_DIRS"] = _XDG_DATA_DIRS
    env["GNOME_ACCESSIBILITY"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def drakter_pids() -> list[int]:
    """Backend and Electron (the backend's parent: Electron spawns it directly)."""
    pids = {os.getpid()}
    ppid = os.getppid()
    if ppid > 1:
        pids.add(ppid)
    extra = os.environ.get("DRAKTER_ELECTRON_PID", "")
    if extra.isdigit():
        pids.add(int(extra))
    return sorted(pids)[:16]


class HandsClient:
    def __init__(self, *, python: Path = SYSTEM_PYTHON, script: Path = HELPER_SCRIPT,
                 env: Mapping[str, str] | None = None) -> None:
        self._python = python
        self._script = script
        self._env = dict(env) if env is not None else build_env()
        self._proc: asyncio.subprocess.Process | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._listeners: dict[str, list[Callable[[BaseModel], None]]] = {}
        self._status: HHelloResult | None = None
        self._ready = asyncio.Event()
        self._stopping = False
        self._write_lock = asyncio.Lock()

    # ── public API (CONTRACT §8.1 bis) ───────────────────────────────────────
    @property
    def status(self) -> HHelloResult | None:
        return self._status

    async def call(self, type: str, payload: BaseModel) -> BaseModel:
        loop = asyncio.get_running_loop()
        if self._loop is not None and loop is not self._loop:
            fut = asyncio.run_coroutine_threadsafe(self._call(type, payload), self._loop)
            return await asyncio.wrap_future(fut)
        return await self._call(type, payload)

    def on_event(self, type: str, cb: Callable[[BaseModel], None]) -> Callable[[], None]:
        self._listeners.setdefault(type, []).append(cb)

        def off() -> None:
            try:
                self._listeners.get(type, []).remove(cb)
            except ValueError:
                pass

        return off

    # ── lifecycle ────────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._task is None:
            self._loop = asyncio.get_running_loop()
            self._task = asyncio.create_task(self._run(), name="hands-supervisor")

    async def wait_ready(self, timeout: float = _READY_WAIT_S) -> bool:
        if self._loop is not None and asyncio.get_running_loop() is not self._loop:
            return self._ready.is_set()  # another loop (approval worker): the event belongs to the main one
        try:
            await asyncio.wait_for(self._ready.wait(), timeout)
        except TimeoutError:
            return False
        return True

    async def stop(self) -> None:
        self._stopping = True
        proc = self._proc
        if proc is not None and proc.returncode is None:
            try:
                await asyncio.wait_for(self._call("shutdown", HELPER_CMDS["shutdown"]()), 2)
            except Exception:  # noqa: BLE001 - the signals below still apply
                pass
            try:
                await asyncio.wait_for(proc.wait(), 2)
            except TimeoutError:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

    # ── internals ────────────────────────────────────────────────────────────
    async def _call(self, type: str, payload: BaseModel) -> BaseModel:
        if type not in HELPER_CMDS:
            raise HandsError("validation_error", "unknown helper command")
        proc = self._proc
        if proc is None or proc.returncode is not None or proc.stdin is None:
            raise HandsError("companion_unavailable", "helper not running")
        if type != "hello" and not self._ready.is_set():
            raise HandsError("companion_unavailable", "helper not ready")
        rid = uuid4().hex
        line = json.dumps({"kind": "cmd", "id": rid, "type": type, "payload": payload.model_dump(mode="json")},
                          ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(line) > MAX_HELPER_LINE_BYTES:
            raise HandsError("validation_error", "command too large")
        fut: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        try:
            async with self._write_lock:
                proc.stdin.write(line + b"\n")
                await proc.stdin.drain()
            msg = await asyncio.wait_for(fut, HELPER_TIMEOUTS_S.get(type, 5))
        except TimeoutError:
            if type == "act":
                try:
                    await self._call("act.stop", HELPER_CMDS["act.stop"]())
                except HandsError:
                    pass
            raise HandsError("step_failed" if type == "act" else "companion_unavailable", "helper timeout") from None
        except (BrokenPipeError, ConnectionResetError):
            raise HandsError("companion_unavailable", "helper pipe closed") from None
        finally:
            self._pending.pop(rid, None)
        if msg.get("kind") == "err":
            body = msg.get("payload") or {}
            raise HandsError(str(body.get("code", "internal_error"))[:40], str(body.get("message", ""))[:200])
        model = HELPER_RESULTS.get(type)
        data = msg.get("payload") or {}
        if model is None:
            return HELPER_CMDS["shutdown"]()  # HEmpty: commands without a result
        try:
            return model.model_validate(data)
        except ValidationError:
            logger.warning("Helper result rejected", extra={"event": "hands_bad_result", "cmd": type})
            raise HandsError("internal_error", "invalid helper result") from None

    async def _run(self) -> None:
        failures = 0
        while not self._stopping:
            started = asyncio.get_running_loop().time()
            await self._run_once()
            if self._stopping:
                return
            failures = 0 if asyncio.get_running_loop().time() - started > _STABLE_AFTER_S else failures + 1
            if failures >= _MAX_FAILURES:
                logger.error("Hands helper gave up", extra={"event": "hands_gave_up"})
                return
            await asyncio.sleep(min(_BACKOFF_CAP_S, _BACKOFF_BASE_S * 2 ** max(0, failures - 1)))

    async def _run_once(self) -> None:
        self._ready.clear()
        self._status = None
        try:
            self._proc = await asyncio.create_subprocess_exec(
                str(self._python), "-I", str(self._script),
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env=self._env, cwd=str(self._script.parent), start_new_session=True,
                limit=MAX_HELPER_LINE_BYTES + 1024,
            )
        except OSError as exc:
            logger.error("Hands helper did not start", extra={"event": "hands_spawn_failed", "error": type(exc).__name__})
            return
        proc = self._proc
        logger.info("Hands helper started", extra={"event": "hands_started", "pid": proc.pid})
        reader = asyncio.create_task(self._read(proc))
        errlog = asyncio.create_task(self._drain_stderr(proc))
        try:
            hello = await self._call("hello", HHello(drakter_pids=drakter_pids()))
            assert isinstance(hello, HHelloResult)
            self._status = hello
            self._ready.set()
            logger.info("Hands helper ready", extra={"event": "hands_ready", "companion": hello.companion,
                                                      "atspi": hello.atspi, "mutter_rd": hello.mutter_rd})
        except HandsError as exc:
            logger.error("Hands helper hello failed", extra={"event": "hands_hello_failed", "code": exc.code})
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        code = await proc.wait()
        self._ready.clear()
        reader.cancel()
        errlog.cancel()
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(HandsError("companion_unavailable", "helper exited"))
        self._pending.clear()
        logger.info("Hands helper exited", extra={"event": "hands_exited", "code": code})

    async def _read(self, proc: asyncio.subprocess.Process) -> None:
        assert proc.stdout is not None
        while True:
            try:
                raw = await proc.stdout.readline()
            except (ValueError, asyncio.LimitOverrunError):
                continue  # an over-long line is dropped
            if not raw:
                return
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue
            kind = msg.get("kind")
            if kind in ("ok", "err"):
                fut = self._pending.get(str(msg.get("id")))
                if fut is not None and not fut.done():
                    fut.set_result(msg)
            elif kind == "evt":
                self._dispatch(str(msg.get("type")), msg.get("payload") or {})

    def _dispatch(self, type: str, payload: dict[str, Any]) -> None:
        model = HELPER_EVTS.get(type)
        if model is None:
            return
        try:
            evt = model.model_validate(payload)
        except ValidationError:
            return
        if type == "companion" and self._status is not None:
            self._status = self._status.model_copy(update={"companion": evt.status})  # type: ignore[attr-defined]
        for cb in tuple(self._listeners.get(type, ())):
            try:
                cb(evt)
            except Exception:  # noqa: BLE001 - one listener must not stop the others
                logger.exception("Hands event listener failed", extra={"event": "hands_listener_failed"})

    @staticmethod
    async def _drain_stderr(proc: asyncio.subprocess.Process) -> None:
        assert proc.stderr is not None
        while True:
            line = await proc.stderr.readline()
            if not line:
                return
            logger.info("hands helper: %s", line.decode("utf-8", "replace").rstrip()[:300],
                        extra={"event": "hands_stderr"})


# ── one client per process ───────────────────────────────────────────────────
_client: HandsClient | None = None


def current_client() -> HandsClient | None:
    return _client


async def ensure_client() -> HandsClient:
    """The process's helper, started on first use. Raises `companion_unavailable` if it is not ready."""
    global _client
    if _client is None:
        _client = HandsClient()
        from app.integrations.hands import records

        records.attach(_client)
        _client.start()
    if not await _client.wait_ready():
        raise HandsError("companion_unavailable", "helper not ready")
    status = _client.status
    if status is None or status.companion not in ("ok", "outdated"):
        raise HandsError("companion_unavailable", f"companion {status.companion if status else 'unknown'}")
    return _client


async def shutdown_client() -> None:
    global _client
    client, _client = _client, None
    if client is not None:
        await client.stop()
