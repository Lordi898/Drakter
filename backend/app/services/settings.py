"""Settings service: validation, audited writes, status and backups."""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Final
from zoneinfo import available_timezones

from app.core.errors import AppError
from app.database.backup import BackupError, create_backup
from app.database.connection import connect
from app.repositories import settings as repo
from app.services import voice_profile
from app.services.settings_models import (
    SETTING_KEYS,
    BackupItem,
    BackupList,
    SettingItem,
    SettingsList,
    SettingsStatus,
    StorageStatus,
)
from app.services.settings_status import agent_config_status

logger = logging.getLogger(__name__)

_BACKUP_NAME: Final = re.compile(r"^drakter-(\d{8}T\d{12}Z)-([a-z0-9-]+)\.db$")
_BOOL_KEYS: Final = frozenset({
    "voice_tts_enabled", "voice_wake_enabled", "floating_hands_enabled", "floating_screen_enabled",
    "floating_sound",
})
_ENUM_KEYS: Final[dict[str, frozenset[str]]] = {
    "voice_expression": frozenset({"off", "llm"}),
    "floating_avatar_size": frozenset({"default", "small", "cursor"}),
}

SettingListener = Callable[[str, str], None]
# Called after COMMIT, from whatever thread wrote the setting (REST runs sync routes in a
# thread pool). Listeners must be thread-safe and must not block (V-31).
_listeners: list[SettingListener] = []


def add_setting_listener(fn: SettingListener) -> None:
    if fn not in _listeners:
        _listeners.append(fn)


def remove_setting_listener(fn: SettingListener) -> None:
    if fn in _listeners:
        _listeners.remove(fn)


def notify_setting_changed(key: str, value: str) -> None:
    """For writers that do not go through `update_setting` (``voice_profile.save_active``)."""
    for fn in tuple(_listeners):
        try:
            fn(key, value)
        except Exception:  # noqa: BLE001 - a listener must never undo a committed write
            logger.error("setting listener failed", extra={"event": "setting_listener_failed"})


@lru_cache(maxsize=1)
def _timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def _unavailable() -> AppError:
    return AppError("settings_unavailable", "Settings storage unavailable", 503)


def _open(db_path: Path) -> sqlite3.Connection:
    try:
        if not db_path.exists():
            raise FileNotFoundError
        return connect(db_path)
    except Exception:
        raise _unavailable() from None


def list_settings(db_path: Path) -> SettingsList:
    empty = [SettingItem(key=k, value=None, updated_at=None) for k in sorted(SETTING_KEYS)]
    try:
        conn = _open(db_path)
    except AppError:
        return SettingsList(persisted=False, items=empty)
    with closing(conn):
        if not repo.table_exists(conn, "settings"):
            return SettingsList(persisted=False, items=empty)
        stored = repo.read_all(conn)
    items = [
        stored.get(k, SettingItem(key=k, value=None, updated_at=None)) for k in sorted(SETTING_KEYS)
    ]
    return SettingsList(persisted=True, items=items)


def update_setting(db_path: Path, key: str, value: str, correlation_id: str) -> SettingItem:
    if key not in SETTING_KEYS:
        raise AppError("unknown_setting", "Unknown setting", 404)
    if key == "default_timezone" and value not in _timezones():
        raise AppError("invalid_timezone", "Invalid timezone", 422)
    if key == "voice_profile":
        value = voice_profile.validate_setting_value(value)
    if key in _BOOL_KEYS:
        value = value.strip().lower()
        if value not in ("true", "false"):
            raise AppError("invalid_setting_value", "Expected true or false", 422)
    if key in _ENUM_KEYS and value not in _ENUM_KEYS[key]:
        raise AppError("invalid_setting_value", "Invalid value", 422)
    conn = _open(db_path)
    with closing(conn):
        try:
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.Error:
            raise _unavailable() from None
        try:
            if not (repo.table_exists(conn, "settings") and repo.table_exists(conn, "audit_events")):
                raise _unavailable()
            item = repo.upsert(conn, key, value, repo.now_utc())
            repo.record_settings_audit(
                conn,
                correlation_id=correlation_id,
                action="settings.update",
                entity_type="setting",
                entity_id=key,
                params={"key": key},
                affected_count=1,
            )
            conn.execute("COMMIT")
        except AppError:
            _rollback(conn)
            raise
        except sqlite3.Error:
            _rollback(conn)
            logger.error("settings update failed", extra={"event": "settings_update_failed"})
            raise _unavailable() from None
    notify_setting_changed(key, value)
    return item


def _rollback(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ROLLBACK")
    except sqlite3.Error:
        pass


def _parse_backup(entry: os.DirEntry[str]) -> BackupItem | None:
    match = _BACKUP_NAME.match(entry.name)
    if match is None:
        return None
    try:
        if not entry.is_file(follow_symlinks=False):
            return None
        size = entry.stat(follow_symlinks=False).st_size
        moment = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S%fZ")
    except (OSError, ValueError):
        return None
    created = moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"
    return BackupItem(name=entry.name, created_at=created, label=match.group(2), size_bytes=size)


def list_backups(backups_dir: Path) -> BackupList:
    items: list[BackupItem] = []
    try:
        with os.scandir(backups_dir) as it:
            for entry in it:
                item = _parse_backup(entry)
                if item is not None:
                    items.append(item)
    except OSError:
        return BackupList(items=[])
    items.sort(key=lambda b: (b.created_at, b.name), reverse=True)
    return BackupList(items=items)


def create_manual_backup(db_path: Path, backups_dir: Path, correlation_id: str) -> BackupItem:
    conn = _open(db_path)
    with closing(conn):
        if not repo.table_exists(conn, "audit_events"):
            raise _unavailable()
    try:
        path = create_backup(db_path, backups_dir, "manual")
    except BackupError:
        logger.error("manual backup failed", extra={"event": "backup_failed"})
        raise AppError("backup_failed", "Backup failed", 500) from None
    with closing(_open(db_path)) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            repo.record_settings_audit(
                conn,
                correlation_id=correlation_id,
                action="backup.create",
                entity_type=None,
                entity_id=None,
                params={"label": "manual"},
                affected_count=1,
            )
            conn.execute("COMMIT")
        except sqlite3.Error:
            _rollback(conn)
            logger.error("backup audit failed", extra={"event": "backup_audit_failed"})
            raise _unavailable() from None
    for item in list_backups(backups_dir).items:
        if item.name == path.name:
            return item
    raise AppError("backup_failed", "Backup failed", 500)


def settings_status(state: Any, data_dir: Path, db_path: Path, backups_dir: Path) -> SettingsStatus:
    version: int | None = None
    try:
        with closing(_open(db_path)) as conn:
            version = repo.schema_version(conn)
    except Exception:
        version = None
    backups = list_backups(backups_dir).items
    return SettingsStatus(
        agent=agent_config_status(state),
        storage=StorageStatus(data_dir=str(data_dir), schema_version=version),
        last_backup=backups[0] if backups else None,
    )
