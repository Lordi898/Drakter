"""Base real para las comprobaciones: migraciones de drakter-11 más el delta del almacén."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.database.connection import connect
from app.database.migrator import migrate

DELTA = Path(__file__).resolve().parents[1] / "app" / "schemas" / "ddl_storage.sql"


def open_database(directory: Path) -> sqlite3.Connection:
    """Migra una base nueva en `directory` y devuelve una conexión con `sqlite3.Row`."""
    database = directory / "drakter.db"
    migrate(database, directory / "backups")
    conn = connect(database)
    conn.row_factory = sqlite3.Row
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(storage_locations)")}
    if "agent_read" not in columns:
        lines = DELTA.read_text(encoding="utf-8").splitlines()
        sql = "\n".join(line for line in lines if not line.startswith("--"))
        for statement in filter(str.strip, sql.split(";")):
            conn.execute(statement)
    return conn
