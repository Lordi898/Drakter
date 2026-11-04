"""JSONL audit for memory operations. Never writes memory content, plain queries or secrets."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.logging import redact

OPERATIONS_LOG = "memory_operations.log"
RETRIEVAL_LOG = "retrieval.log"


class JsonlAudit:
    """Implements AuditSink. Files are created 0600; the directory is not created here."""

    def __init__(self, logs_dir: Path) -> None:
        self._dir = Path(logs_dir)
        self._lock = threading.Lock()

    def _append(self, name: str, entry: dict[str, Any]) -> None:
        line = json.dumps(redact(entry), ensure_ascii=False, default=str, separators=(",", ":")) + "\n"
        path = self._dir / name
        with self._lock:
            self._dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
            try:
                os.fchmod(fd, 0o600)
                os.write(fd, line.encode("utf-8"))
            finally:
                os.close(fd)

    def record(
        self,
        *,
        action: str,
        actor: str,
        target: str,
        outcome: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._append(
            OPERATIONS_LOG,
            {
                "ts": datetime.now(UTC).isoformat(),
                "action": action,
                "actor": actor,
                "target": target,
                "outcome": outcome,
                "detail": detail or {},
            },
        )

    def record_retrieval(self, query_hash: str, ids: Sequence[UUID | str], tainted: bool) -> None:
        self._append(
            RETRIEVAL_LOG,
            {
                "ts": datetime.now(UTC).isoformat(),
                "query_hash": query_hash,
                "ids": [str(i) for i in ids],
                "tainted": tainted,
            },
        )
