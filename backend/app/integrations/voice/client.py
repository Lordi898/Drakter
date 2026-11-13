"""asyncio client of the voice IPC socket (voice/CONTRACT.md, section IPC; envelope of
`drakter_contracts.voice_ipc.IpcMessage`: ``{kind: evt|cmd|ok|err, id, type, payload}``).

Never logs line contents: events carry transcripts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import struct
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

logger = logging.getLogger("drakter.voice.client")

MAX_LINE_BYTES: Final = 256 * 1024
DEFAULT_REQUEST_TIMEOUT: Final = 5.0
_CONNECT_TIMEOUT: Final = 2.0
_RETRY_MIN: Final = 0.1
_RETRY_MAX: Final = 2.0
_EVENT_QUEUE_SIZE: Final = 1024

EventHandler = Callable[[str, Mapping[str, object]], Awaitable[None]]
LinkHandler = Callable[[], Awaitable[None]]


class VoiceUnavailableError(Exception):
    """The voice process cannot be reached, or did not answer in time."""


class VoiceIPCError(Exception):
    """The voice process answered ``err{code, message}``."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


def _encode_command(request_id: str, name: str, args: Mapping[str, object]) -> bytes:
    line = json.dumps(
        {"kind": "cmd", "id": request_id, "type": name, "payload": dict(args)},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8", "replace")
    if len(line) > MAX_LINE_BYTES:
        raise ValueError("voice command exceeds the IPC line limit")
    return line + b"\n"


def _check_peer(writer: asyncio.StreamWriter) -> None:
    """The socket lives in a 0700 directory; this is the second barrier."""
    peercred = getattr(socket, "SO_PEERCRED", None)
    sock = writer.get_extra_info("socket")
    if peercred is None or sock is None:
        return
    raw = sock.getsockopt(socket.SOL_SOCKET, peercred, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", raw)
    if uid != os.getuid():
        raise PermissionError("voice socket owned by another user")


class VoiceClient:
    """One connection at a time, re-established on its own until ``close``.

    ``on_connected`` runs on every new connection before anyone else may send
    commands: that is where the current `voice.config` is pushed. If it raises, the
    connection is dropped and retried.
    """

    def __init__(
        self,
        socket_path: Path,
        *,
        on_event: EventHandler,
        on_connected: LinkHandler,
        on_disconnected: LinkHandler,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        self._path = socket_path
        self._on_event = on_event
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._timeout = request_timeout
        self._writer: asyncio.StreamWriter | None = None
        self._ready = False
        self._closing = False
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._events: asyncio.Queue[tuple[str, Mapping[str, object]]] = asyncio.Queue(
            _EVENT_QUEUE_SIZE
        )
        self._tasks: tuple[asyncio.Task[None], ...] = ()

    @property
    def ready(self) -> bool:
        return self._ready

    def start(self) -> None:
        if not self._tasks:
            self._closing = False
            self._tasks = (
                asyncio.create_task(self._run(), name="voice-ipc"),
                asyncio.create_task(self._dispatch(), name="voice-ipc-events"),
            )

    async def close(self) -> None:
        self._closing = True
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = ()

    async def request(
        self,
        name: str,
        args: Mapping[str, object] | None = None,
        *,
        timeout: float | None = None,
        handshake: bool = False,
    ) -> dict[str, Any]:
        writer = self._writer
        if writer is None or not (self._ready or handshake):
            raise VoiceUnavailableError("voice process not connected")
        request_id = str(uuid4())
        line = _encode_command(request_id, name, args or {})
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        try:
            async with asyncio.timeout(self._timeout if timeout is None else timeout):
                writer.write(line)
                await writer.drain()
                return await future
        except TimeoutError as exc:
            raise VoiceUnavailableError("voice process did not answer") from exc
        except OSError as exc:
            raise VoiceUnavailableError("voice connection lost") from exc
        finally:
            self._pending.pop(request_id, None)

    async def _run(self) -> None:
        delay = _RETRY_MIN
        while not self._closing:
            try:
                async with asyncio.timeout(_CONNECT_TIMEOUT):
                    reader, writer = await asyncio.open_unix_connection(
                        self._path, limit=MAX_LINE_BYTES
                    )
            except (OSError, TimeoutError):
                await asyncio.sleep(delay)
                delay = min(delay * 2, _RETRY_MAX)
                continue
            if await self._session(reader, writer):
                delay = _RETRY_MIN
            await asyncio.sleep(delay)
            delay = min(delay * 2, _RETRY_MAX)

    async def _session(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bool:
        """Serve one connection. Returns True if it got past the handshake."""
        self._writer = writer
        read_task = asyncio.create_task(self._read_loop(reader), name="voice-ipc-read")
        handshake = asyncio.create_task(self._handshake(writer), name="voice-ipc-handshake")
        established = False
        try:
            await asyncio.wait({read_task, handshake}, return_when=asyncio.FIRST_COMPLETED)
            if handshake.done() and handshake.exception() is None:
                established = self._ready = True
                await read_task
            elif handshake.done():
                error = handshake.exception()
                logger.warning(
                    "Voice handshake failed",
                    extra={"event": "voice_handshake_failed", "error": type(error).__name__},
                )
        finally:
            self._ready = False
            self._writer = None
            read_task.cancel()
            handshake.cancel()
            await asyncio.gather(read_task, handshake, return_exceptions=True)
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(VoiceUnavailableError("voice connection lost"))
            self._pending.clear()
            while not self._events.empty():
                self._events.get_nowait()
            writer.close()
            if not self._closing:
                await self._notify(self._on_disconnected)
        return established

    async def _handshake(self, writer: asyncio.StreamWriter) -> None:
        _check_peer(writer)
        await self._on_connected()

    async def _notify(self, handler: LinkHandler) -> None:
        try:
            await handler()
        except Exception as exc:  # noqa: BLE001 - a callback must not kill the link loop
            logger.error(
                "Voice link callback failed",
                extra={"event": "voice_callback_failed", "error": type(exc).__name__},
            )

    async def _read_loop(self, reader: asyncio.StreamReader) -> None:
        while True:
            try:
                line = await reader.readline()
            except ValueError:  # StreamReader's form of "over the limit"
                logger.warning("Voice line too long", extra={"event": "voice_line_too_long"})
                return
            except OSError:
                return
            if not line.endswith(b"\n"):  # EOF, possibly mid-line
                return
            try:
                message = json.loads(line)
            except (ValueError, RecursionError):
                message = None
            if not isinstance(message, dict):
                logger.warning("Voice line invalid", extra={"event": "voice_line_invalid"})
                return
            kind = message.get("kind")
            if kind in ("ok", "err"):
                self._resolve(message)
            elif kind == "evt":
                await self._enqueue(message)

    def _resolve(self, message: Mapping[str, Any]) -> None:
        future = self._pending.get(message.get("id"))  # type: ignore[arg-type]
        if future is None or future.done():
            return
        payload = message.get("payload")
        if message.get("kind") == "ok":
            future.set_result(payload if isinstance(payload, dict) else {})
            return
        error = payload
        error = error if isinstance(error, dict) else {}
        future.set_exception(
            VoiceIPCError(str(error.get("code", "unknown")), str(error.get("message", "")))
        )

    async def _enqueue(self, message: Mapping[str, Any]) -> None:
        name = message.get("type")
        payload = message.get("payload", {})
        if not isinstance(name, str) or not isinstance(payload, dict):
            return
        await self._events.put((name, payload))

    async def _dispatch(self) -> None:
        # Apart from the reader, so that a slow subscriber cannot delay responses.
        while True:
            name, payload = await self._events.get()
            try:
                await self._on_event(name, payload)
            except Exception as exc:  # noqa: BLE001 - one bad event must not stop the rest
                logger.error(
                    "Voice event handler failed",
                    extra={"event": "voice_event_failed", "error": type(exc).__name__},
                )


async def shutdown_stale(path: Path, *, timeout: float = 3.0) -> bool:
    """Stop a process left by a backend that died hard: it would hold the socket and models."""
    if not path.is_socket():
        return False
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_unix_connection(path, limit=MAX_LINE_BYTES)
            try:
                _check_peer(writer)
                writer.write(_encode_command(str(uuid4()), "shutdown", {}))
                await writer.drain()
                while await reader.read(MAX_LINE_BYTES):
                    pass
            finally:
                writer.close()
    except (OSError, TimeoutError):
        return False
    return True
