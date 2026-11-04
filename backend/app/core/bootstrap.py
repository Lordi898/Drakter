"""Handshake con Electron main por stdin y stdout (D-14)."""

import base64
import binascii
import json
import os
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from app.core.security import SessionToken

_MAX_LINE_BYTES: Final = 4096
_TOKEN_RE: Final = re.compile(rb"[A-Za-z0-9_-]{43}")


class HandshakeError(Exception):
    """Handshake inválido. El mensaje nunca incluye lo recibido."""


@dataclass(frozen=True, slots=True)
class Credentials:
    ui: SessionToken
    approver: SessionToken


def take_standard_streams() -> tuple[int, int]:
    """Reserva stdin y stdout para el canal con main, fuera del alcance de cualquier hijo."""
    control_in = os.dup(0)
    control_out = os.dup(1)
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, 0)
    os.close(devnull)
    os.dup2(2, 1)
    return control_in, control_out


def _read_line(fd: int) -> bytes:
    line = bytearray()
    while b"\n" not in line:
        chunk = os.read(fd, _MAX_LINE_BYTES + 1 - len(line))
        if not chunk:
            raise HandshakeError("stdin closed before the handshake")
        line += chunk
        if len(line) > _MAX_LINE_BYTES:
            raise HandshakeError("handshake line too long")
    end = line.index(b"\n")
    if end + 1 != len(line):
        raise HandshakeError("unexpected data after the handshake line")
    return bytes(line[:end])


def _parse_token(value: object) -> str:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value.encode("utf-8")) is None:
        raise HandshakeError("invalid token")
    try:
        decoded = base64.urlsafe_b64decode(value + "=")
    except (binascii.Error, ValueError) as exc:
        raise HandshakeError("invalid token") from exc
    if len(decoded) != 32 or base64.urlsafe_b64encode(decoded).rstrip(b"=").decode() != value:
        raise HandshakeError("invalid token")
    return value


def read_credentials(fd: int) -> Credentials:
    try:
        message = json.loads(_read_line(fd))
    except ValueError:
        raise HandshakeError("handshake is not valid JSON") from None
    if not isinstance(message, dict) or set(message) != {"v", "ui", "approver"}:
        raise HandshakeError("unexpected handshake fields")
    if message["v"] != 1 or isinstance(message["v"], bool):
        raise HandshakeError("unsupported handshake version")
    ui = _parse_token(message["ui"])
    approver = _parse_token(message["approver"])
    if ui == approver:
        raise HandshakeError("tokens must differ")
    return Credentials(ui=SessionToken(ui), approver=SessionToken(approver))


def announce_port(fd: int, port: int) -> None:
    with os.fdopen(fd, "wb") as stream:
        stream.write(json.dumps({"v": 1, "port": port}, separators=(",", ":")).encode() + b"\n")


def watch_eof(fd: int, on_eof: Callable[[], None]) -> threading.Thread:
    def wait() -> None:
        try:
            while os.read(fd, 4096):
                pass
        except OSError:
            pass
        on_eof()

    thread = threading.Thread(target=wait, name="stdin-eof", daemon=True)
    thread.start()
    return thread
