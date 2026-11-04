"""Esquema mínimo para las comprobaciones de almacén y relaciones.

`entities`, `tags` y `entity_tags` son de contracts; aquí hay una copia solo para
comprobar el frente sin depender de la migración común. Las tablas de otros
módulos se crean con lo justo para probar aristas virtuales.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMAS = Path(__file__).resolve().parents[1] / "app" / "schemas"

_COMMON = """
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE (id, entity_type)
);
CREATE TABLE tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL UNIQUE,
    color TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE entity_tags (
    entity_id TEXT NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL REFERENCES tags (id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (entity_id, tag_id)
) WITHOUT ROWID;
CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE subjects (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    parent_task_id TEXT,
    project_id TEXT,
    subject_id TEXT
);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_COMMON)
    conn.executescript((SCHEMAS / "ddl_storage.sql").read_text(encoding="utf-8"))
    conn.executescript((SCHEMAS / "ddl_relations.sql").read_text(encoding="utf-8"))
