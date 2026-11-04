"""Base real para las comprobaciones: las migraciones de drakter-11."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.database.connection import connect
from app.database.migrator import migrate


def open_database(directory: Path) -> sqlite3.Connection:
    """Migra una base nueva en `directory` y devuelve una conexión con `sqlite3.Row`."""
    database = directory / "drakter.db"
    migrate(database, directory / "backups")
    conn = connect(database)
    conn.row_factory = sqlite3.Row
    return conn
