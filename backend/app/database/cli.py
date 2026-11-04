"""Database maintenance: `python -m app.database.cli status|migrate|backup|restore <archivo>`."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

from app.core.config import Settings, ensure_private_dir, load_settings
from app.database.backup import BackupError, create_backup, restore_backup
from app.database.connection import connect
from app.database.migrator import (
    MIGRATIONS_DIR,
    MigrationError,
    current_version,
    load_migrations,
    migrate,
)


def _status(settings: Settings) -> None:
    latest = len(load_migrations(MIGRATIONS_DIR))
    version = 0
    if settings.db_path.exists():
        conn = connect(settings.db_path)
        try:
            version = current_version(conn)
        finally:
            conn.close()
    print(f"versión actual: {version}")
    print(f"última versión: {latest}")
    print(f"pendientes: {max(latest - version, 0)}")


def _migrate(settings: Settings) -> None:
    result = migrate(settings.db_path, settings.backups_dir)
    print(f"versión: {result.from_version} -> {result.to_version}")
    for name in result.applied:
        print(f"aplicada: {name}")
    if result.backup is not None:
        print(f"copia: {result.backup}")


def _backup(settings: Settings) -> None:
    print(f"copia: {create_backup(settings.db_path, settings.backups_dir, 'manual')}")


def _restore(settings: Settings, file: str) -> None:
    path = Path(file)
    # A bare name refers to a copy listed in the backups directory.
    backup = settings.backups_dir / path if path.parent == Path() else path
    previous = restore_backup(settings.db_path, settings.backups_dir, backup)
    print("restaurada")
    print(f"copia previa: {previous}")


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m app.database.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="muestra la versión del esquema")
    commands.add_parser("migrate", help="aplica las migraciones pendientes")
    commands.add_parser("backup", help="crea una copia verificada")
    restore = commands.add_parser("restore", help="restaura una copia de seguridad")
    restore.add_argument("archivo")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    os.umask(0o077)
    try:
        settings = load_settings()
    except Exception:  # noqa: BLE001 - its text may echo configured values.
        print("error: configuración no válida", file=sys.stderr)
        return 1
    try:
        ensure_private_dir(settings.data_dir)
        ensure_private_dir(settings.backups_dir)
        if args.command == "status":
            _status(settings)
        elif args.command == "migrate":
            _migrate(settings)
        elif args.command == "backup":
            _backup(settings)
        else:
            _restore(settings, args.archivo)
    except (MigrationError, BackupError, OSError, ValueError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
