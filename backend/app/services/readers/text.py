"""Lector de texto: lectura acotada con pread, UTF-8 con fallback latin-1."""

from __future__ import annotations

import io
import os
import re
from typing import TYPE_CHECKING

from . import Extracted, ReadFailed, ReadOptions, UnsupportedFormat

if TYPE_CHECKING:
    from app.services.storage_ports import StorageLimits


class PreadFile(io.RawIOBase):
    """Archivo de solo lectura sobre un fd con os.pread: no toca el offset compartido."""

    def __init__(self, fd: int) -> None:
        self._fd = fd
        self._pos = 0
        self._size = os.fstat(fd).st_size

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            pos = offset
        elif whence == 1:
            pos = self._pos + offset
        else:
            pos = self._size + offset
        self._pos = max(0, pos)
        return self._pos

    def readinto(self, b: bytearray | memoryview) -> int:  # type: ignore[override]
        data = os.pread(self._fd, len(b), self._pos)
        b[: len(data)] = data
        self._pos += len(data)
        return len(data)


def paginate(text: str, offset: int, max_chars: int, limit: int) -> tuple[str, bool, int | None]:
    offset = max(0, offset)
    max_chars = max(1, min(max_chars, limit))
    end = offset + max_chars
    chunk = text[offset:end]
    truncated = end < len(text)
    return chunk, truncated, (end if truncated else None)


def pread_all(fd: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    got = 0
    while got < limit:
        data = os.pread(fd, min(1 << 20, limit - got), got)
        if not data:
            break
        chunks.append(data)
        got += len(data)
    return b"".join(chunks)


def decode_bytes(raw: bytes, cut: bool) -> tuple[str, str]:
    if raw.startswith(b"\xef\xbb\xbf"):
        enc, body = "utf-8", raw[3:]
    elif raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            return raw.decode("utf-16"), "utf-16"
        except UnicodeDecodeError:
            return raw[2:].decode("latin-1"), "latin-1"
    else:
        enc, body = "utf-8", raw
    for trim in range(0, 4 if cut else 1):
        try:
            return (body[: len(body) - trim] if trim else body).decode("utf-8"), enc
        except UnicodeDecodeError:
            continue
    return body.decode("latin-1"), "latin-1"


def read_text_raw(fd: int, limits: StorageLimits) -> str:
    return _load(fd, limits)[0]


def _load(fd: int, limits: StorageLimits) -> tuple[str, str, bool]:
    raw = pread_all(fd, limits.max_text_bytes + 1)
    cut = len(raw) > limits.max_text_bytes
    raw = raw[: limits.max_text_bytes]
    head = raw[:8192]
    if b"\x00" in head and raw[:2] not in (b"\xff\xfe", b"\xfe\xff"):
        raise UnsupportedFormat("archivo binario")
    text, enc = decode_bytes(raw, cut)
    return text, enc, cut


_LINES = re.compile(r"^lines:(\d+)-(\d+)$")


def read_text(fd: int, options: ReadOptions, limits: StorageLimits) -> Extracted:
    text, enc, cut = _load(fd, limits)
    meta: dict[str, str | int | float | bool | None] = {
        "encoding": enc,
        "file_truncated": cut,
    }
    if options.selector:
        m = _LINES.match(options.selector.strip())
        if not m or int(m.group(1)) < 1 or int(m.group(2)) < int(m.group(1)):
            raise ReadFailed("selector invalido, se espera lines:A-B")
        a, b = int(m.group(1)), int(m.group(2))
        lines = text.splitlines(keepends=True)
        meta["total_lines"] = len(lines)
        text = "".join(lines[a - 1 : b])
        meta["selector"] = f"lines:{a}-{b}"
    chunk, truncated, nxt = paginate(text, options.offset, options.max_chars, limits.max_read_chars)
    meta["total_chars"] = len(text)
    return Extracted(chunk, truncated or cut, nxt, meta)
