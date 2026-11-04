"""Verified SQLite backups through the online backup API."""

from __future__ import annotations

import os
import re
import sqlite3
import stat
import tempfile
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from app.database.connection import connect, secure_sidecars, sqlite_uri

_LABEL_PATTERN: Final = re.compile(r"[a-z0-9-]+")
_SQLITE_MAGIC: Final = b"SQLite format 3\x00"
_WAL_VERSION: Final = 2
_PRIVATE_FILE_MODE: Final = 0o600
_PRIVATE_DIR_MODE: Final = 0o700
_COPY_TIMEOUT_SECONDS: Final = 10.0
_COPY_RETRY_SECONDS: Final = 0.1
_FAILURES: Final = (OSError, ValueError, sqlite3.Error)


class BackupError(Exception):
    """A backup could not be created, verified or restored."""


def _ensure_backups_dir(backups_dir: Path) -> None:
    backups_dir.mkdir(mode=_PRIVATE_DIR_MODE, parents=True, exist_ok=True)
    info = os.lstat(backups_dir)
    if not stat.S_ISDIR(info.st_mode):
        raise BackupError("El directorio de copias no es un directorio real")
    if info.st_uid != os.geteuid():
        raise BackupError("El directorio de copias pertenece a otro usuario")
    if stat.S_IMODE(info.st_mode) != _PRIVATE_DIR_MODE:
        os.chmod(backups_dir, _PRIVATE_DIR_MODE)


def _copy(source: sqlite3.Connection, target: sqlite3.Connection) -> None:
    """Run the backup API, which otherwise retries forever on a held lock."""
    deadline = time.monotonic() + _COPY_TIMEOUT_SECONDS

    def abort_when_stuck(status: int, _remaining: int, _total: int) -> None:
        busy = status in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
        if busy and time.monotonic() >= deadline:
            raise BackupError("La base sigue bloqueada por otra conexión")

    source.backup(target, progress=abort_when_stuck, sleep=_COPY_RETRY_SECONDS)


def _check_integrity(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA integrity_check").fetchall()
    if rows != [("ok",)]:
        raise BackupError("integrity_check ha detectado daños")


def _fsync_path(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create_backup(db_path: Path, backups_dir: Path, label: str) -> Path:
    if _LABEL_PATTERN.fullmatch(label) is None:
        raise BackupError("La etiqueta de la copia solo admite [a-z0-9-]")
    if not os.path.lexists(db_path):
        raise BackupError("No existe la base que se quiere copiar")
    temporary: Path | None = None
    try:
        _ensure_backups_dir(backups_dir)
        descriptor, name = tempfile.mkstemp(dir=backups_dir, prefix=".tmp-", suffix=".db")
        os.close(descriptor)
        temporary = Path(name)
        with closing(connect(db_path)) as source:
            with closing(sqlite3.connect(temporary, isolation_level=None)) as target:
                _copy(source, target)
                # The copy inherits the WAL flag; read-only opens would then
                # leave -wal/-shm files next to it. A backup is a single file.
                target.execute("PRAGMA journal_mode=DELETE").fetchall()
                _check_integrity(target)
        os.chmod(temporary, _PRIVATE_FILE_MODE)
        _fsync_path(temporary)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        destination = backups_dir / f"drakter-{stamp}-{label}.db"
        os.replace(temporary, destination)
        temporary = None
        _fsync_path(backups_dir)
    except _FAILURES as exc:
        raise BackupError(f"No se pudo crear la copia: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def _open_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(sqlite_uri(path, read_only=True), uri=True, isolation_level=None)


def verify_backup(backup_path: Path) -> None:
    try:
        info = os.lstat(backup_path)
        if not stat.S_ISREG(info.st_mode):
            raise BackupError("La copia no es un archivo regular")
        with open(backup_path, "rb") as stream:
            header = stream.read(20)
        # An empty or foreign file would otherwise open as a valid empty database.
        if len(header) < 20 or not header.startswith(_SQLITE_MAGIC):
            raise BackupError("El archivo no es una base SQLite")
        if _WAL_VERSION in (header[18], header[19]):
            raise BackupError("La copia está en modo WAL: puede depender de archivos auxiliares")
        with closing(_open_read_only(backup_path)) as conn:
            _check_integrity(conn)
    except _FAILURES as exc:
        raise BackupError(f"La copia no es válida: {exc}") from exc


def _resolve_inside(backups_dir: Path, backup_path: Path) -> Path:
    try:
        _ensure_backups_dir(backups_dir)
        info = os.lstat(backup_path)
        root = Path(os.path.realpath(backups_dir))
        resolved = Path(os.path.realpath(backup_path))
    except OSError as exc:
        raise BackupError(f"No se puede acceder a la copia: {exc}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise BackupError("La copia no puede ser un enlace simbólico")
    if not stat.S_ISREG(info.st_mode):
        raise BackupError("La copia no es un archivo regular")
    if resolved == root or not resolved.is_relative_to(root):
        raise BackupError("La copia está fuera del directorio de copias")
    return resolved


def _check_restored(db_path: Path) -> None:
    """Reopen: a fresh connection proves WAL and permissions as a new process sees them."""
    with closing(connect(db_path)) as conn:
        _check_integrity(conn)
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchall()
    secure_sidecars(db_path)
    if stat.S_IMODE(os.lstat(db_path).st_mode) != _PRIVATE_FILE_MODE:
        raise BackupError("La base restaurada no tiene permisos 600")


def restore_backup(db_path: Path, backups_dir: Path, backup_path: Path) -> Path:
    source_path = _resolve_inside(backups_dir, backup_path)
    verify_backup(source_path)
    try:
        # Restoring is how a lost database comes back: create it if missing.
        connect(db_path).close()
    except _FAILURES as exc:
        raise BackupError(f"No se puede abrir la base: {exc}") from exc
    previous = create_backup(db_path, backups_dir, "pre-restore")
    verify_backup(previous)
    try:
        with closing(_open_read_only(source_path)) as source:
            with closing(connect(db_path)) as target:
                # One transaction on the WAL target: other connections see the
                # old or the new state, and a failure leaves the old one.
                _copy(source, target)
        _check_restored(db_path)
    except (*_FAILURES, BackupError) as exc:
        raise BackupError(f"Restauración fallida: {exc}. Copia previa: {previous}") from exc
    return previous
