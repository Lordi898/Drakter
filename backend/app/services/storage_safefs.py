"""Acceso de solo lectura a archivos del almacén, confinado a una raíz.

Toda ruta se resuelve en el kernel con `openat2`: sin symlinks, sin salir de la raíz y
sin carreras entre comprobar y abrir. Si el kernel no lo ofrece, se falla cerrado. Los
mensajes de excepción son fijos: nunca incluyen rutas ni contenido.
"""

from __future__ import annotations

import ctypes
import errno
import os
import stat
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

_SYS_OPENAT2: Final = 437
_AT_FDCWD: Final = -100
_RESOLVE_NO_MAGICLINKS: Final = 0x02
_RESOLVE_NO_SYMLINKS: Final = 0x04
_RESOLVE_BENEATH: Final = 0x08
_RESOLVE_ABSOLUTE: Final = _RESOLVE_NO_SYMLINKS | _RESOLVE_NO_MAGICLINKS
_RESOLVE_CONFINED: Final = _RESOLVE_ABSOLUTE | _RESOLVE_BENEATH
_MAX_RETRIES: Final = 8

# `getattr`: el módulo debe importarse en plataformas sin estas constantes; allí
# `_openat2` falla cerrado.
_O_PATH: Final[int] = getattr(os, "O_PATH", 0)
_O_DIRECTORY: Final[int] = getattr(os, "O_DIRECTORY", 0)
_O_CLOEXEC: Final[int] = getattr(os, "O_CLOEXEC", 0)
_O_NONBLOCK: Final[int] = getattr(os, "O_NONBLOCK", 0)
_O_NOCTTY: Final[int] = getattr(os, "O_NOCTTY", 0)

# Sin O_NOFOLLOW: con O_PATH abriría el propio symlink y O_DIRECTORY daría ENOTDIR, que
# parece un archivo ausente. RESOLVE_NO_SYMLINKS ya da ELOOP en cualquier componente.
_ROOT_FLAGS: Final = _O_PATH | _O_DIRECTORY | _O_CLOEXEC
_FILE_FLAGS: Final = os.O_RDONLY | _O_CLOEXEC | _O_NONBLOCK | _O_NOCTTY
_DIR_FLAGS: Final = _FILE_FLAGS | _O_DIRECTORY
_STAT_FLAGS: Final = _O_PATH | _O_CLOEXEC  # con O_PATH, openat2 no admite otros flags

_DENIED_NAMES: Final = frozenset({".ssh", ".gnupg", ".env"})


class PathNotAllowed(Exception):
    """Traducir a `AppError` `path_not_allowed`."""

    def __init__(self) -> None:
        super().__init__("Path not allowed")


class MissingFile(Exception):
    """El archivo no está: disponibilidad `missing`."""

    def __init__(self) -> None:
        super().__init__("File is missing")


class FileTooLarge(Exception):
    """Supera `max_bytes`. Traducir a `AppError` `file_too_large`."""

    def __init__(self) -> None:
        super().__init__("File is too large")


@dataclass(frozen=True)
class RootIdentity:
    dev: int
    ino: int


@dataclass(frozen=True)
class ScanEntry:
    relative_path: str
    size: int
    mtime_ns: int
    dev: int
    ino: int
    nlink: int


@dataclass(frozen=True)
class OpenedFile:
    fd: int
    size: int
    mtime_ns: int
    dev: int
    ino: int
    _closed: bool = field(default=False, init=False, repr=False, compare=False)

    def close(self) -> None:
        # Idempotente: un segundo cierre podría alcanzar un fd ya reutilizado.
        if not self._closed:
            object.__setattr__(self, "_closed", True)
            os.close(self.fd)

    def __enter__(self) -> OpenedFile:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class _OpenHow(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint64),
        ("mode", ctypes.c_uint64),
        ("resolve", ctypes.c_uint64),
    ]


@lru_cache(maxsize=1)
def _syscall() -> Any:
    if not sys.platform.startswith("linux"):
        raise PathNotAllowed
    try:
        fn = ctypes.CDLL(None, use_errno=True).syscall
    except (OSError, AttributeError):
        raise PathNotAllowed from None
    fn.restype = ctypes.c_long
    fn.argtypes = [
        ctypes.c_long, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t,
    ]
    return fn


def _encode(path: str) -> bytes:
    try:
        raw = path.encode("utf-8")
    except UnicodeEncodeError:
        raise PathNotAllowed from None
    if b"\0" in raw:  # c_char_p cortaría ahí la ruta sin avisar
        raise PathNotAllowed
    return raw


def _openat2(dirfd: int, path: str, flags: int, resolve: int) -> int:
    fn = _syscall()
    raw = _encode(path)
    how = _OpenHow(flags, 0, resolve)
    for _ in range(_MAX_RETRIES):
        ctypes.set_errno(0)
        fd = fn(_SYS_OPENAT2, dirfd, raw, ctypes.byref(how), ctypes.sizeof(how))
        if fd >= 0:
            return int(fd)
        err = ctypes.get_errno()
        if err in (errno.EINTR, errno.EAGAIN):
            continue
        if err in (errno.ENOENT, errno.ENOTDIR):
            raise MissingFile
        break  # ENOSYS, EPERM de seccomp, ELOOP, EXDEV y cualquier otro: cerrado
    raise PathNotAllowed


def _has_control(text: str) -> bool:
    return any(ord(ch) < 32 or 127 <= ord(ch) < 160 for ch in text)


def _denied_name(name: str) -> bool:
    # `casefold`: `.ENV` es `.env` en sistemas de archivos sin mayúsculas (vfat, exfat).
    lowered = name.casefold()
    return lowered in _DENIED_NAMES or lowered.startswith(".env.")


def _safe_parts(path: Path | str) -> tuple[str, ...]:
    """Partes de una ruta absoluta sin `..`: sin symlinks, es ya la canónica."""
    text = os.fspath(path)
    if not text or _has_control(text):
        raise PathNotAllowed
    _encode(text)
    candidate = Path(text)
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise PathNotAllowed
    return candidate.parts


def _denied_set(denied: Sequence[Path]) -> frozenset[tuple[str, ...]]:
    """Cada denegada en forma literal y resuelta: pueden colgar de un symlink."""
    result: set[tuple[str, ...]] = set()
    for item in denied:
        text = os.fspath(item)
        result.add(Path(os.path.abspath(text)).parts)
        result.add(Path(os.path.realpath(text)).parts)
    return frozenset(result)


def _is_denied(parts: tuple[str, ...], denied: frozenset[tuple[str, ...]]) -> bool:
    if any(_denied_name(part) for part in parts):
        return True
    return any(parts[:depth] in denied for depth in range(1, len(parts) + 1))


def _home_paths() -> set[tuple[str, ...]]:
    homes = {os.path.realpath(Path.home())}
    if sys.platform != "win32":  # `$HOME` puede estar mal: también el de la cuenta
        import pwd

        homes.add(os.path.realpath(pwd.getpwuid(os.getuid()).pw_dir))
    return {Path(home).parts for home in homes}


def _same_inode(st: os.stat_result, path: Path | str) -> bool:
    try:
        other = os.stat(path)
    except OSError:
        return False
    return (st.st_dev, st.st_ino) == (other.st_dev, other.st_ino)


def _contains(outer: tuple[str, ...], inner: tuple[str, ...]) -> bool:
    return inner[: len(outer)] == outer


def _open_root(root: Path, identity: RootIdentity | None) -> int:
    fd = _openat2(_AT_FDCWD, str(Path(*_safe_parts(root))), _ROOT_FLAGS, _RESOLVE_ABSOLUTE)
    if identity is not None:
        st = os.fstat(fd)
        if (st.st_dev, st.st_ino) != (identity.dev, identity.ino):
            os.close(fd)
            raise PathNotAllowed
    return fd


def validate_location_path(path: str, denied: Sequence[Path]) -> tuple[Path, RootIdentity]:
    """Comprueba una ruta candidata a ubicación. Inexistente también es `PathNotAllowed`."""
    if not isinstance(path, str):
        raise PathNotAllowed
    parts = _safe_parts(path)
    if len(parts) < 2 or any(_denied_name(part) for part in parts):
        raise PathNotAllowed
    denied_paths = _denied_set(denied)
    if any(_contains(parts, item) or _contains(item, parts) for item in denied_paths):
        raise PathNotAllowed
    homes = _home_paths()
    if any(_contains(parts, home) for home in homes):  # el home o algo que lo contiene
        raise PathNotAllowed

    canonical = Path(*parts)
    try:
        fd = _openat2(_AT_FDCWD, str(canonical), _ROOT_FLAGS, _RESOLVE_ABSOLUTE)
    except MissingFile:
        raise PathNotAllowed from None
    try:
        st = os.fstat(fd)
    finally:
        os.close(fd)
    # Por inodo: un bind mount puede dar otro nombre a `/` o al home.
    if any(_same_inode(st, Path(*home)) for home in homes) or _same_inode(st, "/"):
        raise PathNotAllowed
    return canonical, RootIdentity(st.st_dev, st.st_ino)


def validate_relative_path(relative: str) -> str:
    """Normaliza una ruta relativa. Rechaza vacío, absoluto, `..`, NUL y control."""
    if not isinstance(relative, str) or not relative or relative.startswith("/"):
        raise PathNotAllowed
    if _has_control(relative):
        raise PathNotAllowed
    _encode(relative)
    parts = [part for part in relative.split("/") if part not in ("", ".")]
    if not parts or ".." in parts:
        raise PathNotAllowed
    return "/".join(parts)


def _checked_relative(root: Path, relative: str, denied: Sequence[Path]) -> str:
    normalized = validate_relative_path(relative)
    parts = (*_safe_parts(root), *normalized.split("/"))
    if _is_denied(parts, _denied_set(denied)):
        raise PathNotAllowed
    return normalized


def open_file(
    root: Path,
    identity: RootIdentity | None,
    relative: str,
    *,
    denied: Sequence[Path],
    max_bytes: int | None = None,
) -> OpenedFile:
    normalized = _checked_relative(root, relative, denied)
    root_fd = _open_root(root, identity)
    try:
        fd = _openat2(root_fd, normalized, _FILE_FLAGS, _RESOLVE_CONFINED)
    finally:
        os.close(root_fd)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise PathNotAllowed
        if max_bytes is not None and st.st_size > max_bytes:
            raise FileTooLarge
    except BaseException:
        os.close(fd)
        raise
    return OpenedFile(fd, st.st_size, st.st_mtime_ns, st.st_dev, st.st_ino)


def stat_file(
    root: Path, identity: RootIdentity | None, relative: str, *, denied: Sequence[Path]
) -> ScanEntry:
    normalized = _checked_relative(root, relative, denied)
    root_fd = _open_root(root, identity)
    try:
        fd = _openat2(root_fd, normalized, _STAT_FLAGS, _RESOLVE_CONFINED)
    finally:
        os.close(root_fd)
    try:
        st = os.fstat(fd)
    finally:
        os.close(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        raise PathNotAllowed
    return _entry(normalized, st)


def _entry(relative: str, st: os.stat_result) -> ScanEntry:
    return ScanEntry(relative, st.st_size, st.st_mtime_ns, st.st_dev, st.st_ino, st.st_nlink)


def _child(prefix: str, name: str) -> str | None:
    """Ruta del hijo, o None si `open_file` nunca podría servirla."""
    relative = f"{prefix}/{name}" if prefix else name
    try:
        validate_relative_path(relative)
    except PathNotAllowed:
        return None
    return relative


def scan(
    root: Path,
    identity: RootIdentity | None,
    *,
    denied: Sequence[Path],
    max_entries: int,
    max_depth: int,
) -> Iterator[ScanEntry]:
    """Recorre archivos regulares sin seguir symlinks, en orden no definido.

    Devuelve como mucho `max_entries`: alcanzar esa cifra significa recorrido incompleto,
    y quien llama no debe concluir que falta lo no visto. La raíz en `depth` 0: sus hijos
    directos se listan siempre y `max_depth` limita los descensos. Una raíz ilegible lanza
    `PathNotAllowed`; un subdirectorio ilegible se salta.
    """
    root_parts = _safe_parts(root)
    denied_paths = _denied_set(denied)
    if _is_denied(root_parts, denied_paths):
        raise PathNotAllowed
    if max_entries <= 0:
        return

    root_fd = _open_root(root, identity)
    try:
        yielded = 0
        pending: list[tuple[str, int]] = [("", 0)]
        while pending:
            prefix, depth = pending.pop()
            try:
                dir_fd = _openat2(root_fd, prefix or ".", _DIR_FLAGS, _RESOLVE_CONFINED)
            except (PathNotAllowed, MissingFile):
                if not prefix:
                    raise
                continue
            try:
                with os.scandir(dir_fd) as entries:
                    for item in _iter_quietly(entries):
                        relative = _child(prefix, item.name)
                        if relative is None:
                            continue
                        if _is_denied((*root_parts, *relative.split("/")), denied_paths):
                            continue
                        try:
                            st = item.stat(follow_symlinks=False)
                        except OSError:
                            continue
                        if stat.S_ISDIR(st.st_mode):
                            if depth < max_depth and len(pending) < max_entries:
                                pending.append((relative, depth + 1))
                        elif stat.S_ISREG(st.st_mode) and st.st_nlink == 1:
                            yield _entry(relative, st)
                            yielded += 1
                            if yielded >= max_entries:
                                return
            finally:
                os.close(dir_fd)
    finally:
        os.close(root_fd)


def _iter_quietly(entries: Iterator[os.DirEntry[str]]) -> Iterator[os.DirEntry[str]]:
    """Un error de lectura a medio directorio acaba ese directorio, no el recorrido."""
    while True:
        try:
            item = next(entries)
        except (StopIteration, OSError):
            return
        yield item
