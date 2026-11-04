"""Transactional SQL migrations, validated before anything is touched."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from app.database.backup import BackupError, create_backup, verify_backup
from app.database.connection import connect

SCHEMA_VERSION_TABLE: Final = "schema_version"
MIGRATIONS_DIR: Final = Path(__file__).resolve().parents[2] / "migrations"

_FILE_PATTERN: Final = re.compile(r"(\d{4})_[A-Za-z0-9_-]+\.sql")
_ALLOWED_STATEMENTS: Final = frozenset(
    {
        "ALTER",
        "ANALYZE",
        "CREATE",
        "DELETE",
        "DROP",
        "INSERT",
        "REINDEX",
        "REPLACE",
        "UPDATE",
        "WITH",
    }
)
_KEYWORD_PATTERN: Final = re.compile(r"[A-Za-z]+")
_SQL_WHITESPACE: Final = " \t\n\r\f"
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


class MigrationError(Exception):
    """Migrations are invalid or could not be applied; the database was not changed."""


@dataclass(frozen=True)
class MigrationResult:
    from_version: int
    to_version: int
    applied: tuple[str, ...]
    backup: Path | None


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    checksum: str
    statements: tuple[str, ...]


@dataclass(frozen=True)
class _DatabaseState:
    has_version_table: bool
    has_data: bool
    applied: tuple[tuple[int, str], ...]

    @property
    def version(self) -> int:
        return len(self.applied)


def _skip_noise(sql: str) -> str:
    """Drop what SQLite ignores before a statement: blanks, comments and bare `;`."""
    position = 0
    while position < len(sql):
        if sql[position] in _SQL_WHITESPACE or sql[position] == ";":
            position += 1
        elif sql.startswith("--", position):
            end = sql.find("\n", position)
            position = len(sql) if end == -1 else end + 1
        elif sql.startswith("/*", position):
            end = sql.find("*/", position + 2)
            position = len(sql) if end == -1 else end + 2
        else:
            break
    return sql[position:]


def _split_statements(sql: str, file_name: str) -> tuple[str, ...]:
    statements: list[str] = []
    start = 0
    position = sql.find(";")
    while position != -1:
        candidate = sql[start : position + 1]
        # False while the `;` sits in a string, a comment or a trigger body.
        if sqlite3.complete_statement(candidate):
            if _skip_noise(candidate):
                statements.append(candidate)
            start = position + 1
        position = sql.find(";", position + 1)
    if _skip_noise(sql[start:]):
        raise MigrationError(f"{file_name}: sentencia incompleta o sin `;` final")
    if not statements:
        raise MigrationError(f"{file_name}: no contiene sentencias")
    return tuple(statements)


def _check_statement(statement: str, file_name: str) -> None:
    keyword = _KEYWORD_PATTERN.match(_skip_noise(statement))
    # Allowlist on purpose: a variant nobody listed is rejected, not executed.
    if keyword is None or keyword.group().upper() not in _ALLOWED_STATEMENTS:
        found = keyword.group().upper() if keyword is not None else "desconocida"
        raise MigrationError(f"{file_name}: sentencia no permitida ({found})")


def _read_migration(path: Path, version: int) -> Migration:
    if path.is_symlink() or not path.is_file():
        raise MigrationError(f"{path.name}: no es un archivo regular")
    try:
        content = path.read_bytes()
        sql = content.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise MigrationError(f"{path.name}: no se puede leer como UTF-8") from exc
    if "\x00" in sql:
        raise MigrationError(f"{path.name}: contiene un byte nulo")
    statements = _split_statements(sql, path.name)
    for statement in statements:
        _check_statement(statement, path.name)
    return Migration(version, path.name, hashlib.sha256(content).hexdigest(), statements)


def load_migrations(migrations_dir: Path) -> tuple[Migration, ...]:
    """Read and validate every file; never touches the database."""
    try:
        paths = sorted(path for path in migrations_dir.iterdir() if path.suffix == ".sql")
    except OSError as exc:
        raise MigrationError(f"No se puede leer el directorio de migraciones: {exc}") from exc
    numbered: dict[int, Path] = {}
    for path in paths:
        match = _FILE_PATTERN.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"{path.name}: el nombre debe ser NNNN_nombre.sql")
        version = int(match.group(1))
        if version in numbered:
            raise MigrationError(f"Migración duplicada: {version:04d}")
        numbered[version] = path
    expected = list(range(1, len(numbered) + 1))
    if sorted(numbered) != expected:
        raise MigrationError("Las migraciones deben ir numeradas de 1 en 1 sin huecos")
    return tuple(_read_migration(numbered[version], version) for version in expected)


def _has_version_table(conn: sqlite3.Connection) -> bool:
    query = "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?"
    return conn.execute(query, (SCHEMA_VERSION_TABLE,)).fetchone() is not None


def current_version(conn: sqlite3.Connection) -> int:
    if not _has_version_table(conn):
        return 0
    row = conn.execute(f"SELECT MAX(version) FROM {SCHEMA_VERSION_TABLE}").fetchone()
    return int(row[0]) if row[0] is not None else 0


def _read_state(conn: sqlite3.Connection) -> _DatabaseState:
    has_table = _has_version_table(conn)
    # Any schema object counts as data, including an empty schema_version.
    has_data = (
        conn.execute(
            r"SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite\_%' ESCAPE '\' LIMIT 1"
        ).fetchone()
        is not None
    )
    applied: tuple[tuple[int, str], ...] = ()
    if has_table:
        query = f"SELECT version, checksum FROM {SCHEMA_VERSION_TABLE} ORDER BY version"
        applied = tuple(conn.execute(query).fetchall())
    return _DatabaseState(has_table, has_data, applied)


def _check_applied(state: _DatabaseState, migrations: tuple[Migration, ...]) -> None:
    versions = [version for version, _ in state.applied]
    if versions != list(range(1, len(versions) + 1)):
        raise MigrationError(f"{SCHEMA_VERSION_TABLE} tiene huecos: falta una migración aplicada")
    if state.version > len(migrations):
        raise MigrationError(
            f"La base (v{state.version}) es más nueva que el código (v{len(migrations)}) "
            "o falta una migración aplicada"
        )
    for (version, checksum), migration in zip(state.applied, migrations, strict=False):
        if checksum != migration.checksum:
            raise MigrationError(f"La migración aplicada {version:04d} ha cambiado de checksum")


def _make_backup(db_path: Path, backups_dir: Path) -> Path:
    try:
        backup = create_backup(db_path, backups_dir, "pre-migrate")
        verify_backup(backup)
    except BackupError as exc:
        raise MigrationError(f"No se aplicó nada: {exc}") from exc
    return backup


def _apply(conn: sqlite3.Connection, migrations: tuple[Migration, ...]) -> None:
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


def _attempt(
    conn: sqlite3.Connection,
    db_path: Path,
    backups_dir: Path,
    migrations: tuple[Migration, ...],
) -> MigrationResult | None:
    """Run one pass; `None` means the database moved after the copy, so start over."""
    seen = _read_state(conn)
    _check_applied(seen, migrations)
    needs_work = seen.version < len(migrations)
    if not needs_work and seen.has_version_table:
        return MigrationResult(seen.version, seen.version, (), None)

    backup = _make_backup(db_path, backups_dir) if needs_work and seen.has_data else None
    citation = f"Copia de seguridad: {backup}" if backup else "Sin copia: la base no tenía datos"

    try:
        conn.execute("BEGIN IMMEDIATE")
        locked = _read_state(conn)
        _check_applied(locked, migrations)
        pending = migrations[locked.version :]
        if pending and (locked.version != seen.version or (locked.has_data and backup is None)):
            _rollback(conn)
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
        conn = connect(db_path)
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
