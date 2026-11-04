"""Transactional SQL migrations, validated before anything is touched."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from app.database.backup import BackupError, create_backup, verify_copy
from app.database.connection import connect
from app.database.schema import (
    MIGRATIONS_DIR,
    SCHEMA_VERSION_TABLE,
    Migration,
    MigrationError,
    check_applied,
    current_version,
    load_migrations,
    read_state,
)

__all__ = [
    "MIGRATIONS_DIR",
    "SCHEMA_VERSION_TABLE",
    "MigrationError",
    "MigrationResult",
    "current_version",
    "load_migrations",
    "migrate",
]

_MIGRATION_LOCK_TIMEOUT_MS: Final = 60000
_MAX_ATTEMPTS: Final = 3
_CREATE_SCHEMA_VERSION: Final = f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        checksum TEXT NOT NULL,
        applied_at TEXT NOT NULL
    )
"""


@dataclass(frozen=True)
class MigrationResult:
    from_version: int
    to_version: int
    applied: tuple[str, ...]
    backup: Path | None


def _make_backup(db_path: Path, backups_dir: Path) -> Path:
    try:
        backup = create_backup(db_path, backups_dir, "pre-migrate")
        verify_copy(backup)
    except BackupError as exc:
        raise MigrationError(f"No se aplicó nada: {exc}") from exc
    return backup


def _apply(conn: sqlite3.Connection, migrations: tuple[Migration, ...]) -> None:
    if not migrations:
        return
    for migration in migrations:
        for statement in migration.statements:
            try:
                conn.execute(statement)
            except sqlite3.Error as exc:
                raise MigrationError(f"{migration.name}: {exc}") from exc
            if not conn.in_transaction:
                raise MigrationError(f"{migration.name}: terminó la transacción")
        conn.execute(
            f"INSERT INTO {SCHEMA_VERSION_TABLE} (version, name, checksum, applied_at) "
            "VALUES (?, ?, ?, ?)",
            (
                migration.version,
                migration.name,
                migration.checksum,
                datetime.now(UTC).isoformat(),
            ),
        )
    if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise MigrationError("foreign_key_check ha detectado referencias rotas")
    if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise MigrationError("integrity_check ha detectado daños")


def _rollback(conn: sqlite3.Connection) -> None:
    if conn.in_transaction:
        conn.execute("ROLLBACK")


@contextmanager
def _foreign_keys_disabled(conn: sqlite3.Connection) -> Iterator[None]:
    """Keep DROP TABLE from cascading: the pragma is a no-op inside a transaction."""
    conn.execute("PRAGMA foreign_keys=OFF")
    if conn.execute("PRAGMA foreign_keys").fetchone() != (0,):
        raise MigrationError("No se pudo desactivar foreign_keys para migrar")
    try:
        yield
    finally:
        _rollback(conn)
        conn.execute("PRAGMA foreign_keys=ON")


def _attempt(
    conn: sqlite3.Connection,
    db_path: Path,
    backups_dir: Path,
    migrations: tuple[Migration, ...],
) -> MigrationResult | None:
    """Run one pass; `None` means the database moved after the copy, so start over."""
    seen = read_state(conn)
    check_applied(seen, migrations)
    needs_work = seen.version < len(migrations)
    if not needs_work and seen.has_version_table:
        return MigrationResult(seen.version, seen.version, (), None)

    backup = _make_backup(db_path, backups_dir) if needs_work and seen.has_data else None
    citation = f"Copia de seguridad: {backup}" if backup else "Sin copia: la base no tenía datos"

    with _foreign_keys_disabled(conn):
        try:
            conn.execute("BEGIN IMMEDIATE")
            locked = read_state(conn)
            check_applied(locked, migrations)
            pending = migrations[locked.version :]
            stale = locked.version != seen.version or (locked.has_data and backup is None)
            if pending and stale:
                return None
            conn.execute(_CREATE_SCHEMA_VERSION)
            _apply(conn, pending)
            conn.execute("COMMIT")
        except BaseException as exc:
            _rollback(conn)
            if isinstance(exc, MigrationError | sqlite3.Error):
                raise MigrationError(f"{exc}. Base revertida. {citation}") from exc
            raise
    return MigrationResult(
        locked.version,
        len(migrations),
        tuple(migration.name for migration in pending),
        backup,
    )


def migrate(
    db_path: Path, backups_dir: Path, migrations_dir: Path = MIGRATIONS_DIR
) -> MigrationResult:
    migrations = load_migrations(migrations_dir)
    try:
        conn = connect(db_path, create=True)
    except (OSError, ValueError, sqlite3.Error) as exc:
        raise MigrationError(f"No se puede abrir la base: {exc}") from exc
    try:
        # Concurrent starts wait for the migrating process, however long it takes.
        conn.execute(f"PRAGMA busy_timeout={_MIGRATION_LOCK_TIMEOUT_MS}")
        for _ in range(_MAX_ATTEMPTS):
            result = _attempt(conn, db_path, backups_dir, migrations)
            if result is not None:
                return result
    except sqlite3.Error as exc:
        raise MigrationError(f"Fallo de SQLite durante la migración: {exc}") from exc
    finally:
        conn.close()
    raise MigrationError("La base cambia sin parar: no se aplicó nada")
