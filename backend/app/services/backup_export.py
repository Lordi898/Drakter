"""Workspace export: a portable ZIP with one JSONL file per table."""

from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
import zipfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from app.core.config import Settings, ensure_private_dir
from app.database.connection import sqlite_uri
from app.database.migrator import SCHEMA_VERSION_TABLE

_IDENTIFIER: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\Z")
_SECRET_COLUMN: Final = re.compile(
    r"secret|token|passw|passphrase|api_?key|private_?key|credential|cookie|authorization",
    re.IGNORECASE,
)
_CONFIRMATION_TABLE: Final = re.compile(r"confirm|approval|pending_", re.IGNORECASE)
_FTS_SHADOW_SUFFIXES: Final = ("data", "idx", "content", "docsize", "config")
_METADATA_MEMBER: Final = "_export.json"


def _quoted(identifier: str) -> str:
    if _IDENTIFIER.fullmatch(identifier) is None:
        raise ValueError("unsafe SQL identifier")
    return f'"{identifier}"'


def _exportable_tables(conn: sqlite3.Connection) -> tuple[list[str], list[str]]:
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    virtual = [
        name for name, sql in rows if (sql or "").lstrip().upper().startswith("CREATE VIRTUAL")
    ]
    internal = set(virtual) | {
        f"{name}_{suffix}" for name in virtual for suffix in _FTS_SHADOW_SUFFIXES
    }
    tables: list[str] = []
    skipped: list[str] = []
    for name, _ in rows:
        if name.startswith("sqlite_") or name == SCHEMA_VERSION_TABLE or name in internal:
            continue
        if _CONFIRMATION_TABLE.search(name) or _IDENTIFIER.fullmatch(name) is None:
            skipped.append(name)
        else:
            tables.append(name)
    return tables, skipped


def _exportable_columns(conn: sqlite3.Connection, table: str) -> tuple[list[str], list[str]]:
    names = [row[1] for row in conn.execute(f"PRAGMA table_info({_quoted(table)})")]
    keep = [
        name
        for name in names
        if _IDENTIFIER.fullmatch(name) is not None and _SECRET_COLUMN.search(name) is None
    ]
    return keep, [f"{table}.{name}" for name in names if name not in keep]


def _json_value(value: object) -> object:
    if isinstance(value, bytes):
        return {"$base64": base64.b64encode(value).decode("ascii")}
    return value


def _write_table(
    conn: sqlite3.Connection, archive: zipfile.ZipFile, table: str, columns: list[str]
) -> None:
    selection = ", ".join(_quoted(column) for column in columns)
    info = zipfile.ZipInfo(f"{table}.jsonl", date_time=datetime.now(UTC).timetuple()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    with archive.open(info, "w", force_zip64=True) as member:
        if not columns:
            return
        for row in conn.execute(f"SELECT {selection} FROM {_quoted(table)}"):
            record = {
                column: _json_value(value) for column, value in zip(columns, row, strict=True)
            }
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            member.write(line.encode("utf-8") + b"\n")


def _write_export(conn: sqlite3.Connection, target: Path, stamp: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    with os.fdopen(os.open(target, flags, 0o600), "wb") as raw:
        with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as archive:
            # One read transaction: every table comes from the same instant.
            conn.execute("BEGIN")
            tables, skipped_tables = _exportable_tables(conn)
            skipped_columns: list[str] = []
            for table in tables:
                columns, skipped = _exportable_columns(conn, table)
                skipped_columns.extend(skipped)
                _write_table(conn, archive, table, columns)
            conn.execute("COMMIT")
            metadata = {
                "exported_at": stamp,
                "tables": tables,
                "skipped_tables": skipped_tables,
                "skipped_columns": skipped_columns,
            }
            archive.writestr(_METADATA_MEMBER, json.dumps(metadata, ensure_ascii=False, indent=2))
        raw.flush()
        os.fsync(raw.fileno())


def export_workspace(settings: Settings) -> Path:
    exports = settings.data_dir / "exports"
    ensure_private_dir(exports)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    target = exports / f"drakter-export-{stamp}.zip"
    temporary = exports / f".tmp-{stamp}.zip"
    uri = sqlite_uri(settings.db_path, read_only=True)
    try:
        with closing(sqlite3.connect(uri, uri=True, isolation_level=None)) as conn:
            conn.text_factory = lambda raw: raw.decode("utf-8", "replace")
            conn.execute("PRAGMA query_only=ON")
            _write_export(conn, temporary, stamp)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
