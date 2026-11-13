"""Servidor UDS JSONL del proceso de voz: un cliente (el backend), validación estricta.

Sobre común `IpcMessage{kind, id, type, payload}` (`drakter_contracts.voice_ipc`): el backend
envía `cmd`, la voz responde `ok` o `err` con el mismo `id` y emite `evt`. Nada de lo recibido se
ejecuta: un comando es un nombre de la tabla `CMDS` más un payload validado por su modelo.
"""

from __future__ import annotations

import asyncio
import errno
import itertools
import json
import logging
import os
import socket
import stat
import struct
from collections import deque
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any, Final

from drakter_contracts.voice_ipc import CMD_RESULTS, CMDS, EVTS, MAX_LINE_BYTES, IpcMessage
from pydantic import BaseModel, ValidationError

from voice.metrics import ensure_private_dir

log = logging.getLogger("voice.ipc")

MAX_PENDING_MESSAGES: Final = 4096  # un cliente tan atrasado está colgado: se le corta
FLUSH_TIMEOUT_S: Final = 1.0
# Comandos lentos (negociación ICE) que no deben retener a los demás, p. ej. un speak.stop.
_CONCURRENT: Final = frozenset({"rtc.offer"})


class IpcError(Exception):
    """Fallo de un comando que se devuelve al backend como `err{code, message}`."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def parse_command(line: bytes) -> tuple[str, str, BaseModel]:
    """Valida una línea y devuelve `(id, type, payload)`. Lanza `IpcError` con el motivo."""
    try:
        message = IpcMessage.model_validate_json(line)
    except ValidationError:
        raise IpcError("invalid_request", "malformed message") from None
    model = CMDS.get(message.type)
    if message.kind != "cmd" or model is None:
        raise _BadCommand(message.id, "unknown command")
    try:
        return message.id, message.type, model.model_validate(message.payload)
    except ValidationError:
        raise _BadCommand(message.id, "invalid payload") from None


class _BadCommand(IpcError):
    """Petición rechazada cuyo `id` sí era válido: se devuelve para que el cliente la empareje."""

    def __init__(self, request_id: str, message: str) -> None:
        super().__init__("invalid_request", message)
        self.request_id = request_id


def _remove_stale_socket(path: Path) -> None:
    """Quita un socket huérfano: solo si es un socket, nuestro, y nadie escucha en él."""
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


def _encode(kind: str, message_id: str, type_: str, payload: Mapping[str, Any]) -> bytes:
    body = {"kind": kind, "id": message_id, "type": type_, "payload": payload}
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode() + b"\n"


class _Client:
    """Cola de salida acotada. Escribe una sola tarea: un cliente lento no frena al pipeline."""

    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self.writer = writer
        self._messages: deque[bytes] = deque()
        self._ready = asyncio.Event()
        self._idle = asyncio.Event()
        self._idle.set()
        self.closed = False

    def send(self, data: bytes) -> None:
        if self.closed:
            return
        if len(self._messages) >= MAX_PENDING_MESSAGES:
            log.warning("client_overflow", extra={"data": {}})
            self.close()
            return
        self._messages.append(data)
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
                while self._messages and not self.closed:
                    self.writer.write(self._messages.popleft())
                    await self.writer.drain()
                self._idle.set()
        except (ConnectionError, OSError):
            self.close()

    async def flush(self) -> None:
        try:
            await asyncio.wait_for(self._idle.wait(), FLUSH_TIMEOUT_S)
        except TimeoutError:
            pass


# (type, payload validado) -> resultado para `ok`
CommandHandler = Callable[[str, BaseModel], Awaitable[Mapping[str, Any] | None]]


class IpcServer:
    def __init__(
        self,
        path: Path,
        on_command: CommandHandler,
        on_connect: Callable[[], Awaitable[None]],
        on_disconnect: Callable[[], Awaitable[None]],
    ) -> None:
        self._path = Path(path)
        self._on_command = on_command
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._server: asyncio.Server | None = None
        self._client: _Client | None = None
        self._inode: int | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._evt_ids = itertools.count(1)

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
        """Deja salir las últimas respuestas y quita el socket."""
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
        try:
            if os.lstat(self._path).st_ino == self._inode:
                self._path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass

    def publish(self, type_: str, payload: Mapping[str, Any]) -> None:
        """Emite un `evt` validado contra su modelo. Sin cliente, se descarta."""
        model = EVTS.get(type_)
        if model is None:
            raise ValueError(f"event outside the contract: {type_}")
        body = model.model_validate(dict(payload)).model_dump(mode="json", exclude_none=True, by_alias=True)
        client = self._client
        if client is not None:
            client.send(_encode("evt", f"e{next(self._evt_ids)}", type_, body))

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            uid = _peer_uid(writer)
        except OSError:
            uid = None
        if uid != os.getuid() or self._client is not None:
            log.warning("peer_rejected", extra={"data": {"reason": "uid" if uid != os.getuid() else "busy"}})
            writer.close()
            return

        client = _Client(writer)
        self._client = client
        self._spawn(client.pump())
        try:
            await self._on_connect()
            await self._read_lines(reader, client)
        finally:
            self._client = None
            await client.flush()
            client.close()
            log.info("client_gone", extra={"data": {}})
            try:
                await self._on_disconnect()
            except Exception as exc:  # noqa: BLE001 - la limpieza no debe tumbar el servidor
                log.error("disconnect_cleanup_failed", extra={"data": {"error": type(exc).__name__}})

    def _spawn(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _read_lines(self, reader: asyncio.StreamReader, client: _Client) -> None:
        while not client.closed:
            try:
                line = await reader.readline()
            except ValueError:  # la línea superó el límite del búfer
                log.warning("line_too_long", extra={"data": {}})
                return
            except ConnectionError:
                return
            if not line or not line.endswith(b"\n"):
                return
            try:
                request_id, type_, payload = parse_command(line)
            except _BadCommand as exc:
                client.send(_encode("err", exc.request_id, "", {"code": exc.code, "message": exc.message}))
                continue
            except IpcError as exc:
                client.send(_encode("err", "", "", {"code": exc.code, "message": exc.message}))
                continue
            # En serie y en orden de llegada: así `speak.delta` conserva su orden.
            if type_ in _CONCURRENT:
                self._spawn(self._run(client, request_id, type_, payload))
            else:
                await self._run(client, request_id, type_, payload)

    async def _run(self, client: _Client, request_id: str, type_: str, payload: BaseModel) -> None:
        try:
            result = await self._on_command(type_, payload) or {}
            model = CMD_RESULTS.get(type_)
            body = model.model_validate(dict(result)).model_dump(mode="json") if model else dict(result)
        except IpcError as exc:
            client.send(_encode("err", request_id, type_, {"code": exc.code, "message": exc.message}))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - un comando fallido no acaba con el servicio
            log.error("command_failed", extra={"data": {"command": type_, "error": type(exc).__name__}})
            client.send(_encode("err", request_id, type_, {"code": "internal_error", "message": "internal error"}))
        else:
            client.send(_encode("ok", request_id, type_, body))
