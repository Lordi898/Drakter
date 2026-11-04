"""Hardened SQLite connections: one private file, WAL and enforced foreign keys."""

from __future__ import annotations

import os
import sqlite3
import stat
import time
from pathlib import Path
from typing import Final
from urllib.parse import quote

BUSY_TIMEOUT_MS: Final = 5000
_PRIVATE_MODE: Final = 0o600
_SIDECAR_SUFFIXES: Final = ("-wal", "-shm")
_RETRY_DELAY_SECONDS: Final = 0.05


def sqlite_uri(path: Path, *, read_only: bool = False) -> str:
    """Build a `file:` URI, quoting characters SQLite would treat as URI syntax."""
    target = quote(os.path.abspath(path))
    return f"file:{target}?mode=ro" if read_only else f"file:{target}?mode=rw"


def _check_owned_regular_file(path: Path, info: os.stat_result) -> None:
    if stat.S_ISLNK(info.st_mode):
        raise ValueError(f"La base no puede ser un enlace simbólico: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"La base no es un archivo regular: {path}")
    if info.st_uid != os.geteuid():
        raise ValueError(f"La base pertenece a otro usuario: {path}")


def _prepare_database_file(path: Path, *, create: bool) -> os.stat_result:
    """Create or validate the file and return its identity.

    An existing database is inspected only through its path. Opening and closing
    a descriptor to it would silently drop every POSIX lock SQLite holds on that
    file in this process, and `connect` runs while other connections are live.
    """
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        if not create:
            raise
        flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            descriptor = os.open(path, flags, _PRIVATE_MODE)
        except FileExistsError:
            # Lost the creation race: validate what the other opener created.
            info = os.lstat(path)
        else:
            try:
                os.fchmod(descriptor, _PRIVATE_MODE)
            finally:
                os.close(descriptor)
            info = os.lstat(path)
    _check_owned_regular_file(path, info)
    if stat.S_IMODE(info.st_mode) != _PRIVATE_MODE:
        os.chmod(path, _PRIVATE_MODE)
    return info


def secure_sidecars(path: Path) -> None:
    """Keep `-wal` and `-shm` private; SQLite copies the mode of the main file."""
    for suffix in _SIDECAR_SUFFIXES:
        sidecar = Path(f"{path}{suffix}")
        try:
            info = os.lstat(sidecar)
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise ValueError(f"Archivo auxiliar de la base no regular: {sidecar}")
            if info.st_uid != os.geteuid():
                raise ValueError(f"Archivo auxiliar de otro usuario: {sidecar}")
            if stat.S_IMODE(info.st_mode) != _PRIVATE_MODE:
                os.chmod(sidecar, _PRIVATE_MODE)
        except FileNotFoundError:
            continue  # Removed by the last connection closing elsewhere.


def _is_busy(exc: sqlite3.Error) -> bool:
    code = getattr(exc, "sqlite_errorcode", None)
    return code is not None and code & 0xFF in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)


def _enable_wal(conn: sqlite3.Connection) -> None:
    """Switch to WAL, retrying: the switch can skip the busy handler on a first start."""
    deadline = time.monotonic() + BUSY_TIMEOUT_MS / 1000
    while True:
        try:
            row = conn.execute("PRAGMA journal_mode=WAL").fetchone()
        except sqlite3.OperationalError as exc:
            if not _is_busy(exc) or time.monotonic() >= deadline:
                raise
        else:
            if row is not None and str(row[0]).lower() == "wal":
                return
            if time.monotonic() >= deadline:
                raise sqlite3.OperationalError("No se pudo activar WAL en la base")
        time.sleep(_RETRY_DELAY_SECONDS)


def _configure(conn: sqlite3.Connection) -> None:
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    _enable_wal(conn)
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    if conn.execute("PRAGMA foreign_keys").fetchone() != (1,):
        raise sqlite3.OperationalError("No se pudo activar foreign_keys en la base")


def connect(db_path: Path, *, create: bool = False) -> sqlite3.Connection:
    path = Path(db_path)
    identity = _prepare_database_file(path, create=create)
    secure_sidecars(path)
    conn = sqlite3.connect(
        sqlite_uri(path),
        uri=True,
        timeout=BUSY_TIMEOUT_MS / 1000,
        isolation_level=None,
    )
    try:
        current = os.lstat(path)
        if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise ValueError(f"La base cambió mientras se abría: {path}")
        _check_owned_regular_file(path, current)
        _configure(conn)
        secure_sidecars(path)
    except BaseException:
        conn.close()
        raise
    return conn
