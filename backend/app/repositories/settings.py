"""SQLite access for the settings module. Only parameterised SQL."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime

from app.services.settings_models import SettingItem


def now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def read_all(conn: sqlite3.Connection) -> dict[str, SettingItem]:
    rows = conn.execute("SELECT key, value, updated_at FROM settings").fetchall()
    return {r[0]: SettingItem(key=r[0], value=r[1], updated_at=r[2]) for r in rows}


def upsert(conn: sqlite3.Connection, key: str, value: str, updated_at: str) -> SettingItem:
    conn.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value, updated_at),
    )
    return SettingItem(key=key, value=value, updated_at=updated_at)


def schema_version(conn: sqlite3.Connection) -> int | None:
    if not table_exists(conn, "schema_version"):
        return None
    row = conn.execute("SELECT max(version) FROM schema_version").fetchone()
    return None if row is None or row[0] is None else int(row[0])


def record_settings_audit(
    conn: sqlite3.Connection,
    *,
    correlation_id: str,
    action: str,
    entity_type: str | None,
    entity_id: str | None,
    params: dict[str, str],
    affected_count: int,
) -> None:
    """Single place that knows the audit_events layout (the common schema may still change)."""
    conn.execute(
        "INSERT INTO audit_events (id, occurred_at, correlation_id, actor_type, origin, action, "
        "tool_name, entity_type, entity_id, affected_count, params_redacted_json, changes_json, "
        "result, error_code, confirmation_id, duration_ms) "
        "VALUES (?, ?, ?, 'user', 'rest', ?, NULL, ?, ?, ?, ?, NULL, 'success', NULL, NULL, NULL)",
        (
            str(uuid.uuid4()),
            now_utc(),
            correlation_id,
            action,
            entity_type,
            entity_id,
            affected_count,
            json.dumps(params, separators=(",", ":")),
        ),
    )
