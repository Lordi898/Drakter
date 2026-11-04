"""Metadatos de imagen por cabecera. Nunca decodifica pixeles."""

from __future__ import annotations

import os
import struct
from typing import TYPE_CHECKING

from . import Extracted, ReadFailed

if TYPE_CHECKING:
    from app.services.storage_ports import StorageLimits

_HEAD = 1 << 20


def _jpeg(d: bytes) -> tuple[int, int]:
    i, n = 2, len(d)
    while i + 4 <= n:
        if d[i] != 0xFF:
            raise ReadFailed("JPEG invalido")
        while i < n and d[i] == 0xFF:
            i += 1
        if i >= n:
            break
        m = d[i]
        i += 1
        if m in (0x01, 0xD8) or 0xD0 <= m <= 0xD7:
            continue
        if m in (0xD9, 0xDA):
            break
        if i + 2 > n:
            break
        seg = struct.unpack(">H", d[i : i + 2])[0]
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            if i + 7 > n:
                break
            h, w = struct.unpack(">HH", d[i + 3 : i + 7])
            return w, h
        i += seg
    raise ReadFailed("JPEG sin cabecera SOF")


def _webp(d: bytes) -> tuple[int, int]:
    kind = d[12:16]
    if kind == b"VP8X" and len(d) >= 30:
        return (int.from_bytes(d[24:27], "little") + 1, int.from_bytes(d[27:30], "little") + 1)
    if kind == b"VP8L" and len(d) >= 25 and d[20] == 0x2F:
        b = int.from_bytes(d[21:25], "little")
        return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if kind == b"VP8 " and len(d) >= 30 and d[23:26] == b"\x9d\x01\x2a":
        w, h = struct.unpack("<HH", d[26:30])
        return w & 0x3FFF, h & 0x3FFF
    raise ReadFailed("WebP invalido")


def parse_image_header(d: bytes) -> tuple[str, int, int]:
    try:
        if d.startswith(b"\x89PNG\r\n\x1a\n"):
            if d[12:16] != b"IHDR" or len(d) < 24:
                raise ReadFailed("PNG truncado")
            w, h = struct.unpack(">II", d[16:24])
            fmt = "PNG"
        elif d.startswith(b"\xff\xd8"):
            (w, h), fmt = _jpeg(d), "JPEG"
        elif d[:6] in (b"GIF87a", b"GIF89a"):
            if len(d) < 10:
                raise ReadFailed("GIF truncado")
            w, h = struct.unpack("<HH", d[6:10])
            fmt = "GIF"
        elif d[:4] == b"RIFF" and d[8:12] == b"WEBP":
            (w, h), fmt = _webp(d), "WebP"
        elif d[:2] == b"BM":
            if len(d) < 26:
                raise ReadFailed("BMP truncado")
            dib = struct.unpack("<I", d[14:18])[0]
            if dib == 12:
                w, h = struct.unpack("<HH", d[18:22])
            elif dib >= 40:
                w, h = struct.unpack("<ii", d[18:26])
                w, h = abs(w), abs(h)
            else:
                raise ReadFailed("BMP invalido")
            fmt = "BMP"
        else:
            raise ReadFailed("no es una imagen reconocida")
    except struct.error as exc:
        raise ReadFailed("cabecera de imagen truncada") from exc
    if w <= 0 or h <= 0 or w > 1_000_000 or h > 1_000_000:
        raise ReadFailed("dimensiones de imagen invalidas")
    return fmt, w, h


def read_image(fd: int, limits: StorageLimits) -> Extracted:
    head = os.pread(fd, _HEAD, 0)
    fmt, w, h = parse_image_header(head)
    size = os.fstat(fd).st_size
    return Extracted(
        f"Imagen {fmt} de {w}×{h}",
        False,
        None,
        {"format": fmt, "width": w, "height": h, "size_bytes": size},
    )
