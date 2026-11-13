"""`AuditPort` of the voice orchestrator over the backend's `audit_events` (the same writer the
gate uses). Voice only passes ids, categories, counts and timings; this adapter keeps scalars
and bounds them, so a transcript can never land in the audit log by accident."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Final
from uuid import uuid4

from drakter_contracts.common import Origin

from app.audit.writer import AuditEvent, write
from app.database.connection import connect
from app.permissions.models import ActorContext, Principal

_MAX_STR: Final = 64
_MAX_KEYS: Final = 16


def _bounded(meta: Mapping[str, object]) -> dict[str, object]:
    kept: dict[str, object] = {}
    for key, value in list(meta.items())[:_MAX_KEYS]:
        if isinstance(value, bool | int | float) or value is None:
            kept[str(key)[:_MAX_STR]] = value
        elif isinstance(value, str):
            kept[str(key)[:_MAX_STR]] = value[:_MAX_STR]
    return kept


class VoiceAudit:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def record(self, action: str, meta: Mapping[str, object]) -> None:
        await asyncio.to_thread(self._write, action, _bounded(meta))

    def _write(self, action: str, params: dict[str, object]) -> None:
        conn = connect(self._db_path)
        try:
            write(
                conn,
                ActorContext(
                    principal=Principal.SYSTEM, origin=Origin.INTERNAL, correlation_id=str(uuid4())
                ),
                AuditEvent(action=action[:_MAX_STR], result="success", params=params or None),
            )
        finally:
            conn.close()
