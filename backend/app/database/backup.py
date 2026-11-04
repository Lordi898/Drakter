"""Verified SQLite backups through the online backup API."""

from __future__ import annotations

import hashlib
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
from app.database.lock import DatabaseInUse, exclusive_instance
from app.database.schema import (
    MIGRATIONS_DIR,
    MigrationError,
    check_applied,
    has_version_table,
    load_migrations,
    read_state,
)

_LABEL_PATTERN: Final = re.compile(r"[a-z0-9-]+")
_SIDECAR_PATTERN: Final = re.compile(r"([0-9a-f]{64})  ([^\n]+)\n")
_SQLITE_MAGIC: Final = b"SQLite format 3\x00"
_WAL_VERSION: Final = 2
_PRIVATE_FILE_MODE: Final = 0o600
_PRIVATE_DIR_MODE: Final = 0o700
_MAX_SIDECAR_BYTES: Final = 512
_HASH_CHUNK_BYTES: Final = 1024 * 1024
_COPY_TIMEOUT_SECONDS: Final = 10.0
_COPY_RETRY_SECONDS: Final = 0.1
_FAILURES: Final = (OSError, ValueError, sqlite3.Error)
_LIVE_FILE_SUFFIXES: Final = ("", "-wal", "-shm")


class BackupError(Exception):
    """A backup could not be created, verified or restored."""


class _DamagedDatabase(BackupError):
    """SQLite itself reports damage, unlike a full disk or a held lock."""


def _is_damage(exc: Exception) -> bool:
    code = getattr(exc, "sqlite_errorcode", None)
    return code is not None and code & 0xFF in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


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
        raise _DamagedDatabase("integrity_check ha detectado daños")


def _fsync_path(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _sidecar_path(backup_path: Path) -> Path:
    return backup_path.with_name(f"{backup_path.name}.sha256")


def _publish_sidecar(sidecar: Path, digest: str, backup_name: str) -> None:
    descriptor, name = tempfile.mkstemp(dir=sidecar.parent, prefix=".tmp-", suffix=".sha256")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"{digest}  {backup_name}\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, sidecar)
    finally:
        temporary.unlink(missing_ok=True)


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
        destination = backups_dir / f"drakter-{_timestamp()}-{label}.db"
        sidecar = _sidecar_path(destination)
        # Sidecar first: a crash then leaves a stray hash, never an unverifiable copy.
        _publish_sidecar(sidecar, _sha256(temporary), destination.name)
        try:
            os.replace(temporary, destination)
        except OSError:
            sidecar.unlink(missing_ok=True)
            raise
        temporary = None
        _fsync_path(backups_dir)
    except _FAILURES as exc:
        if _is_damage(exc):
            raise _DamagedDatabase(f"La base está dañada: {exc}") from exc
        raise BackupError(f"No se pudo crear la copia: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def _open_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(sqlite_uri(path, read_only=True), uri=True, isolation_level=None)


def _check_digest(backup_path: Path) -> None:
    """Damage inside a row is invisible to integrity_check: only the hash catches it."""
    sidecar = _sidecar_path(backup_path)
    info = os.lstat(sidecar)
    if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_SIDECAR_BYTES:
        raise BackupError("El hash de la copia no es un archivo regular válido")
    match = _SIDECAR_PATTERN.fullmatch(sidecar.read_text(encoding="utf-8"))
    if match is None or match.group(2) != backup_path.name:
        raise BackupError("El hash de la copia tiene un formato no válido")
    if match.group(1) != _sha256(backup_path):
        raise BackupError("El contenido de la copia no coincide con su hash")


def _check_file_shape(backup_path: Path) -> None:
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


def verify_copy(backup_path: Path) -> None:
    """Check a copy is intact, whatever it holds.

    Own fresh copies stop here: the database they protect may legitimately have
    no `schema_version` yet, and that must not block the operation being protected.
    """
    try:
        _check_file_shape(backup_path)
        _check_digest(backup_path)
        with closing(_open_read_only(backup_path)) as conn:
            _check_integrity(conn)
    except _FAILURES as exc:
        raise BackupError(f"La copia no es válida: {exc}") from exc


def verify_backup(backup_path: Path) -> None:
    verify_copy(backup_path)
    try:
        with closing(_open_read_only(backup_path)) as conn:
            present = has_version_table(conn)
    except _FAILURES as exc:
        raise BackupError(f"La copia no es válida: {exc}") from exc
    if not present:
        raise BackupError("La copia no es de Drakter: no tiene schema_version")


def _check_compatible(backup_path: Path, migrations_dir: Path) -> None:
    try:
        migrations = load_migrations(migrations_dir)
        with closing(_open_read_only(backup_path)) as conn:
            check_applied(read_state(conn), migrations)
    except (MigrationError, *_FAILURES) as exc:
        raise BackupError(f"La copia es incompatible con este código: {exc}") from exc


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


def _quarantine(db_path: Path, backups_dir: Path) -> Path:
    """Move the live files aside. Nothing here deletes: they are the user's last data."""
    _ensure_backups_dir(backups_dir)
    directory = backups_dir / f"quarantine-{_timestamp()}"
    directory.mkdir(mode=_PRIVATE_DIR_MODE)
    for suffix in _LIVE_FILE_SUFFIXES:
        source = Path(f"{db_path}{suffix}")
        try:
            os.replace(source, directory / source.name)
        except FileNotFoundError:
            continue
    _fsync_path(directory)
    _fsync_path(db_path.parent)
    return directory


def _preserve_live_database(db_path: Path, backups_dir: Path) -> Path:
    """Leave the live state recoverable and a healthy database to restore over."""
    try:
        if not os.path.lexists(db_path):
            # A leftover WAL would be replayed into the new file.
            orphans = [s for s in ("-wal", "-shm") if os.path.lexists(f"{db_path}{s}")]
            if orphans:
                _quarantine(db_path, backups_dir)
            connect(db_path, create=True).close()
        try:
            previous = create_backup(db_path, backups_dir, "pre-restore")
            verify_copy(previous)
        except _DamagedDatabase:
            previous = _quarantine(db_path, backups_dir)
            connect(db_path, create=True).close()
    except _FAILURES as exc:
        raise BackupError(f"No se puede preparar la base: {exc}") from exc
    return previous


def _check_restored(db_path: Path) -> None:
    """Reopen: a fresh connection proves WAL and permissions as a new process sees them."""
    with closing(connect(db_path)) as conn:
        _check_integrity(conn)
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchall()
    secure_sidecars(db_path)
    if stat.S_IMODE(os.lstat(db_path).st_mode) != _PRIVATE_FILE_MODE:
        raise BackupError("La base restaurada no tiene permisos 600")


def _restore(db_path: Path, backups_dir: Path, backup_path: Path, migrations_dir: Path) -> Path:
    source_path = _resolve_inside(backups_dir, backup_path)
    verify_backup(source_path)
    _check_compatible(source_path, migrations_dir)
    previous = _preserve_live_database(db_path, backups_dir)
    try:
        with closing(_open_read_only(source_path)) as source:
            with closing(connect(db_path)) as target:
                # One transaction on the WAL target: other connections see the
                # old or the new state, and a failure leaves the old one.
                _copy(source, target)
        _check_restored(db_path)
    except (*_FAILURES, BackupError) as exc:
        raise BackupError(f"Restauración fallida: {exc}. Estado previo en: {previous}") from exc
    return previous


def restore_backup(
    db_path: Path,
    backups_dir: Path,
    backup_path: Path,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> Path:
    try:
        with exclusive_instance(db_path):
            return _restore(db_path, backups_dir, backup_path, migrations_dir)
    except DatabaseInUse as exc:
        raise BackupError(f"Restauración cancelada, no se tocó nada: {exc}") from exc
