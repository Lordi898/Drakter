"""Listado seguro de comprimidos (zip, tar, tar.gz/bz2/xz). Solo lista: nunca extrae.

`list_archive` corre en el proceso hijo. Para tar comprimido se descomprime en flujo
contando bytes reales por trozos (sin fiarse de cabeceras) y se aborta por
`archive_max_total_bytes` o por proporcion. Sin recursion: un comprimido dentro de otro
solo se marca.
"""

from __future__ import annotations

import bz2
import gzip
import io
import lzma
import os
import stat
import tarfile
import zipfile
from typing import TYPE_CHECKING, Any

from app.services.readers import ArchiveLimit, Extracted, ReadFailed, ReadOptions

if TYPE_CHECKING:
    from app.services.storage_ports import StorageLimits

RATIO_MIN_BYTES = 1 << 20  # la proporcion solo se exige por encima de 1 MiB
_NESTED_EXT = (".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz", ".tbz2", ".txz", ".7z", ".rar", ".jar")
_MAX_NAME_SHOWN = 300


def _safe_display(name: str) -> str:
    s = "".join(c if c.isprintable() else "?" for c in name)
    return s if len(s) <= _MAX_NAME_SHOWN else s[:_MAX_NAME_SHOWN] + "..."


def validate_name(name: str, limits: Any) -> str | None:
    """Devuelve el motivo si el nombre es invalido, None si es aceptable."""
    if "\x00" in name:
        return "nul"
    try:
        if len(name.encode("utf-8", "surrogateescape")) > limits.archive_max_path_bytes:
            return "too_long"
    except UnicodeError:
        return "bad_encoding"
    norm = name.replace("\\", "/")
    if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":" and norm[0].isalpha()):
        return "absolute"
    parts = [p for p in norm.split("/") if p not in ("", ".")]
    if ".." in parts:
        return "traversal"
    if len(parts) > limits.archive_max_depth:
        return "too_deep"
    return None


def _entry(name: str, size: int, kind: str, limits: Any, extra: list[str] | None = None) -> dict[str, Any]:
    flags = list(extra or [])
    bad = validate_name(name, limits)
    if bad:
        flags.append(f"invalid_name:{bad}")
    if kind == "file" and name.lower().endswith(_NESTED_EXT):
        flags.append("nested_archive")
    return {"name": _safe_display(name), "size": size, "kind": kind, "flags": flags}


class _Counting:
    """Lector que cuenta bytes reales descomprimidos y aborta por total o proporcion."""

    def __init__(self, inner: Any, raw: Any, limits: Any) -> None:
        self._inner, self._raw, self._limits = inner, raw, limits
        self.total = 0

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0 or n > 65536:
            n = 65536
        data = self._inner.read(n)
        self.total += len(data)
        lim = self._limits
        if self.total > lim.archive_max_total_bytes:
            raise ArchiveLimit("el contenido descomprimido supera el maximo permitido")
        if self.total > RATIO_MIN_BYTES and self.total > lim.archive_max_ratio * max(self._raw.tell(), 1):
            raise ArchiveLimit("proporcion de compresion sospechosa (posible bomba)")
        return data


def _zip_entries(f: Any, archive_size: int, limits: Any) -> tuple[list[dict[str, Any]], int]:
    try:
        zf = zipfile.ZipFile(f)
        infos = zf.infolist()
    except (zipfile.BadZipFile, OSError, ValueError, NotImplementedError) as exc:
        raise ReadFailed("zip invalido") from exc
    if len(infos) > limits.archive_max_entries:
        raise ArchiveLimit("demasiadas entradas en el comprimido")
    out: list[dict[str, Any]] = []
    total = 0
    for zi in infos:
        mode = zi.external_attr >> 16
        extra: list[str] = []
        if zi.flag_bits & 0x1:
            extra.append("encrypted")
        if zi.is_dir():
            kind = "dir"
        elif stat.S_ISLNK(mode):
            kind = "symlink"
        elif stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode):
            kind = "device"
        else:
            kind = "file"
        size = zi.file_size
        if size > limits.archive_max_entry_bytes:
            raise ArchiveLimit("una entrada supera el tamano maximo")
        if size > RATIO_MIN_BYTES and size > limits.archive_max_ratio * max(zi.compress_size, 1):
            raise ArchiveLimit("proporcion de compresion sospechosa (posible bomba)")
        total += size
        if total > limits.archive_max_total_bytes:
            raise ArchiveLimit("el contenido descomprimido declarado supera el maximo permitido")
        out.append(_entry(zi.filename, size, kind, limits, extra))
    if total > RATIO_MIN_BYTES and total > limits.archive_max_ratio * max(archive_size, 1):
        raise ArchiveLimit("proporcion de compresion sospechosa (posible bomba)")
    return out, total


def _tar_entries(raw: Any, magic: bytes, limits: Any) -> tuple[list[dict[str, Any]], int]:
    if magic[:2] == b"\x1f\x8b":
        inner: Any = gzip.GzipFile(fileobj=raw, mode="rb")
    elif magic[:3] == b"BZh":
        inner = bz2.BZ2File(raw, "rb")
    elif magic[:6] == b"\xfd7zXZ\x00":
        inner = lzma.LZMAFile(raw, "rb")
    else:
        inner = raw
    counter = _Counting(inner, raw, limits)
    out: list[dict[str, Any]] = []
    declared = 0
    try:
        with tarfile.open(fileobj=counter, mode="r|") as tf:  # type: ignore[call-overload]
            for ti in tf:
                if len(out) >= limits.archive_max_entries:
                    raise ArchiveLimit("demasiadas entradas en el comprimido")
                if ti.isdir():
                    kind = "dir"
                elif ti.issym():
                    kind = "symlink"
                elif ti.islnk():
                    kind = "hardlink"
                elif ti.isfile():
                    kind = "file"
                elif ti.ischr() or ti.isblk() or ti.isfifo():
                    kind = "device"
                else:
                    kind = "other"
                size = ti.size if kind == "file" else 0
                if size > limits.archive_max_entry_bytes:
                    raise ArchiveLimit("una entrada supera el tamano maximo")
                declared += size
                if declared > limits.archive_max_total_bytes:
                    raise ArchiveLimit("el contenido descomprimido declarado supera el maximo")
                out.append(_entry(ti.name, size, kind, limits))
                tf.members = []  # no acumular referencias
    except (tarfile.TarError, OSError, EOFError, lzma.LZMAError, ValueError, zlib_error()) as exc:
        raise ReadFailed(f"tar invalido o corrupto: {type(exc).__name__}") from exc
    if not out:
        raise ReadFailed("el comprimido esta vacio o no es un tar")
    return out, max(declared, 0)


def zlib_error() -> type[Exception]:
    import zlib

    return zlib.error


def list_archive(fd: int, limits: Any) -> dict[str, Any]:
    """Lista un comprimido desde un fd. Pensado para el proceso hijo."""
    from app.services.readers.text import PreadFile

    size = os.fstat(fd).st_size
    if size > limits.archive_max_bytes:
        raise ArchiveLimit("comprimido demasiado grande")
    raw = io.BufferedReader(PreadFile(fd))
    magic = raw.peek(512)[:512]
    if magic[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        fmt = "zip"
        entries, total = _zip_entries(raw, size, limits)
    elif magic[:2] == b"\x1f\x8b":
        fmt = "tar.gz"
        entries, total = _tar_entries(raw, magic, limits)
    elif magic[:3] == b"BZh":
        fmt = "tar.bz2"
        entries, total = _tar_entries(raw, magic, limits)
    elif magic[:6] == b"\xfd7zXZ\x00":
        fmt = "tar.xz"
        entries, total = _tar_entries(raw, magic, limits)
    elif magic[257:262] == b"ustar":
        fmt = "tar"
        entries, total = _tar_entries(raw, magic, limits)
    else:
        raise ReadFailed("formato de comprimido no soportado (v1: zip, tar, tar.gz/bz2/xz)")
    flags = sorted({f.split(":")[0] for e in entries for f in e["flags"]})
    result: dict[str, Any] = {
        "format": fmt,
        "entries": entries,
        "total_uncompressed_bytes": total,
        "flags": flags,
        "listing_truncated": False,
    }
    budget = int(limits.worker_max_output_bytes) - 4096
    while len(entries) > 1 and sum(len(e["name"]) + 60 for e in entries) > budget:
        del entries[len(entries) // 2 :]
        result["listing_truncated"] = True
    return result


def read_archive(fd: int, options: ReadOptions, limits: StorageLimits) -> Extracted:
    """Lado padre: lanza el analisis aislado y da formato al listado."""
    from app.services.readers.sandbox import run_in_sandbox
    from app.services.readers.text import paginate

    res = run_in_sandbox("archive", fd, {}, limits)
    lines = []
    for e in res["entries"]:
        mark = f"  [{', '.join(e['flags'])}]" if e["flags"] else ""
        lines.append(f"{e['kind']:<8} {e['size']:>12}  {e['name']}{mark}")
    if res.get("listing_truncated"):
        lines.append("... listado recortado por tamano")
    text = "\n".join(lines)
    chunk, truncated, nxt = paginate(text, options.offset, options.max_chars, limits.max_read_chars)
    meta = {
        "format": res["format"],
        "entries": len(res["entries"]),
        "total_uncompressed_bytes": res["total_uncompressed_bytes"],
        "flags": ",".join(res["flags"]),
        "listing_truncated": bool(res.get("listing_truncated")),
    }
    return Extracted(chunk, truncated, nxt, meta)
