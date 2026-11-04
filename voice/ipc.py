"""Unix socket server of the voice process: one client, JSON lines, strict validation.

Nothing received is ever executed: a command is a name out of a fixed table plus typed arguments.
"""

from __future__ import annotations

import asyncio
import errno
import json
import logging
import os
import re
import socket
import stat
import struct
from collections import deque
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from voice.contracts import EVENTS, VoiceError
from voice.metrics import ensure_private_dir

log = logging.getLogger("voice.ipc")

MAX_LINE_BYTES: Final = 256 * 1024
MAX_PENDING_MESSAGES: Final = 4096  # a client this far behind is stuck: it is dropped, not its events
MAX_PENDING_LEVELS: Final = 8  # mouth levels are the only thing ever discarded
MAX_INFLIGHT_COMMANDS: Final = 16
FLUSH_TIMEOUT_S: Final = 1.0
_LEVEL_EVENT: Final = "voice.playback_level"
_ID_RE: Final = re.compile(r"[A-Za-z0-9._-]{1,128}")
_INTERRUPT_REASONS: Final = frozenset({"user", "barge_in", "new_turn"})


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and _ID_RE.fullmatch(value) is not None


def _is_bool(value: object) -> bool:
    return isinstance(value, bool)


def _is_str(value: object) -> bool:
    return isinstance(value, str)


def _is_context(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items())


def _is_reason(value: object) -> bool:
    return isinstance(value, str) and value in _INTERRUPT_REASONS


Check = Callable[[object], bool]
# name -> (required args, optional args)
COMMANDS: Final[Mapping[str, tuple[Mapping[str, Check], Mapping[str, Check]]]] = {
    "status": ({}, {}),
    "mic.set": ({"enabled": _is_bool}, {}),
    "wakeword.set": ({"enabled": _is_bool}, {}),
    "listen.start": ({}, {}),
    "listen.stop": ({}, {}),
    "listen.cancel": ({}, {}),
    "speak": ({"turn_id": _valid_id, "text": _is_str, "final": _is_bool}, {"context": _is_context}),
    "interrupt": ({}, {"reason": _is_reason}),
    "shutdown": ({}, {}),
}


@dataclass(frozen=True, slots=True)
class Command:
    id: str
    name: str
    args: dict[str, Any]


class BadCommand(Exception):
    """`request_id` is echoed when it was valid, so the client can match the refusal."""

    def __init__(self, message: str, request_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.request_id = request_id


def _reject_constant(name: str) -> None:
    raise ValueError(name)


def parse_command(line: bytes) -> Command:
    """Validates one line. Unknown fields, names, arguments or types are all refused."""
    try:
        raw = json.loads(line.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise BadCommand("malformed message") from None
    if not isinstance(raw, dict):
        raise BadCommand("message must be an object")
    request_id = raw.get("id")
    if not _valid_id(request_id):
        raise BadCommand("invalid id")
    if set(raw) != {"kind", "id", "name", "args"} or raw["kind"] != "cmd":
        raise BadCommand("invalid message", request_id)
    name, args = raw["name"], raw["args"]
    if not isinstance(name, str) or name not in COMMANDS:
        raise BadCommand("unknown command", request_id)
    if not isinstance(args, dict):
        raise BadCommand("args must be an object", request_id)
    required, optional = COMMANDS[name]
    if set(args) - set(required) - set(optional) or set(required) - set(args):
        raise BadCommand("invalid arguments", request_id)
    for key, value in args.items():
        check = required.get(key) or optional[key]
        if not check(value):
            raise BadCommand(f"invalid argument: {key}", request_id)
    return Command(id=request_id, name=name, args=args)


def _remove_stale_socket(path: Path) -> None:
    """Removes a leftover socket: only a socket, ours, with nobody listening."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return
    if not stat.S_ISSOCK(st.st_mode):
        raise ValueError(f"refusing to replace something that is not a socket: {path}")
    if st.st_uid != os.getuid():
        raise ValueError(f"socket not owned by the current user: {path}")
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    probe.settimeout(0.5)
    try:
        probe.connect(str(path))
    except OSError as exc:
        if exc.errno != errno.ECONNREFUSED:
            raise ValueError(f"cannot tell whether the socket is alive: {path}") from exc
    else:
        raise ValueError(f"another voice process is listening on {path}")
    finally:
        probe.close()
    path.unlink(missing_ok=True)


def _peer_uid(writer: asyncio.StreamWriter) -> int | None:
    sock = writer.get_extra_info("socket")
    if sock is None:
        return None
    raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", raw)
    return uid


def _encode(message: Mapping[str, Any]) -> bytes:
    return json.dumps(message, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


class _Client:
    """Bounded outgoing queue. Writing is one task, so a slow client delays nobody else."""

    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self.writer = writer
        self._messages: deque[bytes] = deque()
        self._levels: deque[bytes] = deque(maxlen=MAX_PENDING_LEVELS)
        self._ready = asyncio.Event()
        self._idle = asyncio.Event()
        self._idle.set()
        self.closed = False
        self.overflowed = False

    def send(self, data: bytes) -> None:
        if self.closed:
            return
        if len(self._messages) >= MAX_PENDING_MESSAGES:
            self.overflowed = True
            self.close()
            return
        self._messages.append(data)
        self._idle.clear()
        self._ready.set()

    def send_level(self, data: bytes) -> None:
        if not self.closed:
            self._levels.append(data)  # maxlen: the oldest level falls off
            self._idle.clear()
            self._ready.set()

    def close(self) -> None:
        self.closed = True
        self._ready.set()
        self.writer.close()

    async def pump(self) -> None:
        try:
            while not self.closed:
                await self._ready.wait()
                self._ready.clear()
                while (self._messages or self._levels) and not self.closed:
                    # Levels only wait behind what is already due: they go stale fast.
                    data = self._messages.popleft() if self._messages else self._levels.popleft()
                    self.writer.write(data)
                    await self.writer.drain()
                self._idle.set()
        except (ConnectionError, OSError):
            self.close()

    async def flush(self) -> None:
        try:
            await asyncio.wait_for(self._idle.wait(), FLUSH_TIMEOUT_S)
        except TimeoutError:
            pass


CommandHandler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class IpcServer:
    def __init__(
        self,
        path: Path,
        on_command: CommandHandler,
        on_disconnect: Callable[[], Awaitable[None]],
    ) -> None:
        self._path = Path(path)
        self._on_command = on_command
        self._on_disconnect = on_disconnect
        self._server: asyncio.Server | None = None
        self._client: _Client | None = None
        self._inode: int | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        ensure_private_dir(self._path.parent)
        _remove_stale_socket(self._path)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            previous = os.umask(0o177)
            try:
                sock.bind(str(self._path))
            finally:
                os.umask(previous)
            os.chmod(self._path, 0o600)
            self._inode = os.lstat(self._path).st_ino
            self._server = await asyncio.start_unix_server(self._serve, sock=sock, limit=MAX_LINE_BYTES)
        except BaseException:
            sock.close()
            raise
        log.info("listening", extra={"data": {"socket": self._path.name}})

    async def stop(self) -> None:
        """Lets the last replies out, then removes the socket."""
        client = self._client
        if client is not None:
            await client.flush()
        if self._server is not None:
            self._server.close()
            self._server = None
        if client is not None:
            client.close()
        for task in tuple(self._tasks):
            task.cancel()
        self._unlink_socket()

    def _unlink_socket(self) -> None:
        try:
            if os.lstat(self._path).st_ino == self._inode:
                self._path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass

    def publish(self, name: str, payload: Mapping[str, Any]) -> None:
        """Called on the loop by the manager. Only mouth levels may be dropped on the way."""
        if name not in EVENTS:
            raise ValueError(f"event outside the contract: {name}")
        client = self._client
        if client is None:
            return
        data = _encode({"kind": "evt", "name": name, "ts": datetime.now(UTC).isoformat(), "payload": payload})
        if name == _LEVEL_EVENT:
            client.send_level(data)
        else:
            client.send(data)

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            uid = _peer_uid(writer)
        except OSError:
            uid = None
        if uid != os.getuid():
            log.warning("peer_rejected", extra={"data": {"reason": "uid"}})
            writer.close()
            return
        if self._client is not None:
            log.warning("peer_rejected", extra={"data": {"reason": "busy"}})
            writer.close()
            return

        client = _Client(writer)
        self._client = client
        pump = asyncio.create_task(client.pump())
        self._tasks.add(pump)
        pump.add_done_callback(self._tasks.discard)
        try:
            await self._read_lines(reader, client)
        finally:
            self._client = None
            client.close()
            pump.cancel()
            log.info("client_gone", extra={"data": {"overflowed": client.overflowed}})
            try:
                await self._on_disconnect()
            except Exception as exc:  # noqa: BLE001 - the failure was already reported as voice.error
                log.error("disconnect_cleanup_failed", extra={"data": {"error": type(exc).__name__}})

    async def _read_lines(self, reader: asyncio.StreamReader, client: _Client) -> None:
        slots = asyncio.Semaphore(MAX_INFLIGHT_COMMANDS)
        while not client.closed:
            try:
                line = await reader.readline()
            except ValueError:  # the line outgrew the buffer limit
                log.warning("line_too_long", extra={"data": {}})
                return
            except ConnectionError:
                return
            if not line or not line.endswith(b"\n"):
                return
            if len(line) > MAX_LINE_BYTES:
                log.warning("line_too_long", extra={"data": {}})
                return
            try:
                command = parse_command(line)
            except BadCommand as exc:
                self._reply_error(client, exc.request_id, "invalid_request", exc.message)
                continue
            # One task per command, started in arrival order: a slow one (opening the mic) must
            # not hold back an interrupt. Handlers change state before their first await, so
            # speak deltas keep their order.
            await slots.acquire()
            task = asyncio.create_task(self._run(client, command))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            task.add_done_callback(lambda _t: slots.release())

    async def _run(self, client: _Client, command: Command) -> None:
        try:
            result = await self._on_command(command.name, command.args)
        except VoiceError as exc:
            self._reply_error(client, command.id, exc.code, exc.message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - one failed command must not end the service
            log.error("command_failed", extra={"data": {"command": command.name, "error": type(exc).__name__}})
            self._reply_error(client, command.id, "engine_failed", "internal error")
        else:
            client.send(_encode({"kind": "res", "id": command.id, "ok": True, "result": result}))

    @staticmethod
    def _reply_error(client: _Client, request_id: str | None, code: str, message: str) -> None:
        client.send(
            _encode({"kind": "res", "id": request_id, "ok": False, "error": {"code": code, "message": message}})
        )
