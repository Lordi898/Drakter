"""SQL de `notifications`. Único sitio que escribe la tabla.

`read_at` significa «ya entregada a la GUI». No hay borrado: quitar una fila
perdería su `dedupe_key` y el recordatorio volvería a salir en el siguiente tick.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final
from uuid import uuid4

_COLUMNS: Final = "id, kind, title, body, severity, entity_id, created_at, read_at, dedupe_key"
_INSERT: Final = (
    "INSERT INTO notifications(id, kind, title, body, severity, entity_id, created_at, dedupe_key) "
    "VALUES(?, ?, ?, ?, ?, ?, ?, ?) "
    "ON CONFLICT(dedupe_key) WHERE dedupe_key IS NOT NULL DO NOTHING"
)


@dataclass(frozen=True, slots=True)
class NewNotification:
    dedupe_key: str
    kind: str
    title: str
    body: str | None = None
    severity: str = "info"
    entity_id: str | None = None


@dataclass(frozen=True, slots=True)
class NotificationRow:
    id: str
    kind: str
    title: str
    body: str | None
    severity: str
    entity_id: str | None
    created_at: str
    read_at: str | None
    dedupe_key: str | None


def insert_new(
    conn: sqlite3.Connection, items: Iterable[NewNotification], created_at: str
) -> list[NotificationRow]:
    """Inserta en una transacción y devuelve solo las filas nuevas (las repetidas se ignoran)."""
    created: list[NotificationRow] = []
    conn.execute("BEGIN IMMEDIATE")
    try:
        for item in items:
            notification_id = str(uuid4())
            cursor = conn.execute(
                _INSERT,
                (
                    notification_id,
                    item.kind,
                    item.title,
                    item.body,
                    item.severity,
                    item.entity_id,
                    created_at,
                    item.dedupe_key,
                ),
            )
            if cursor.rowcount == 1:
                created.append(
                    NotificationRow(
                        notification_id,
                        item.kind,
                        item.title,
                        item.body,
                        item.severity,
                        item.entity_id,
                        created_at,
                        None,
                        item.dedupe_key,
                    )
                )
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return created


def existing_keys(conn: sqlite3.Connection, keys: Sequence[str]) -> set[str]:
    """Claves ya emitidas, para no gastar el cupo de un tick en repetidos."""
    found: set[str] = set()
    for start in range(0, len(keys), 500):
        chunk = keys[start : start + 500]
        marks = ",".join("?" * len(chunk))
        rows = conn.execute(
            f"SELECT dedupe_key FROM notifications WHERE dedupe_key IN ({marks})", chunk
        )
        found.update(row[0] for row in rows)
    return found


def list_notifications(
    conn: sqlite3.Connection,
    *,
    unread_only: bool,
    limit: int,
    offset: int,
) -> tuple[list[NotificationRow], int]:
    """Una página, más recientes primero, y el total del filtro."""
    clause = "WHERE read_at IS NULL " if unread_only else ""
    total = conn.execute(f"SELECT count(*) FROM notifications {clause}").fetchone()[0]
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM notifications {clause}"
        "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return [NotificationRow(*row) for row in rows], total


def mark_read(conn: sqlite3.Connection, ids: Sequence[str], read_at: str) -> int:
    """Idempotente: lo ya leído conserva su `read_at` y no cuenta."""
    if not ids:
        return 0
    marks = ",".join("?" * len(ids))
    cursor = conn.execute(
        f"UPDATE notifications SET read_at = ? WHERE read_at IS NULL AND id IN ({marks})",
        (read_at, *ids),
    )
    return cursor.rowcount
