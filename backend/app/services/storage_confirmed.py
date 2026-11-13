"""Ejecución de lo aprobado en la GUI: lo llama `POST /confirmations/{id}/approve`.

El pipeline común reclama la fila (`approved -> executing`) y llama aquí con los
`args_json` guardados, tal cual. Aquí no se decide nada sobre la aprobación.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from typing import Any, Final

from app.core.config import Settings
from app.services import relations, storage_catalog, storage_index, storage_scan
from app.services.storage_ports import ApprovedByDispatcher, Actor, StorageDeps

Executor = Callable[[sqlite3.Connection, StorageDeps, Actor, Mapping[str, Any]], Any]

CONFIRMED_ACTIONS: Final[Mapping[str, Executor]] = {
    "delete_resource": lambda c, d, a, x: storage_catalog.delete_resource(
        c, d, a, x["resource_id"], bool(x["detach"])
    ),
    "delete_folder": lambda c, d, a, x: storage_catalog.delete_folder(c, d, a, x["folder_id"]),
    "delete_storage_location": lambda c, d, a, x: storage_catalog.delete_location(c, d, a, x["location_id"]),
    "refresh_resource_index": lambda c, d, a, x: storage_index.refresh_index(c, d, a),
    "scan_location": lambda c, d, a, x: storage_scan.scan_location(c, d, a, x["location_id"]),
    "delete_relationship": lambda c, d, a, x: relations.delete_relationship(c, d, a, x["relationship_id"]),
}


def execute_confirmed(
    conn: sqlite3.Connection, settings: Settings, actor: Actor, tool: str, args: Mapping[str, Any]
) -> Any:
    executor = CONFIRMED_ACTIONS[tool]
    # The pipeline's connection returns tuples; storage code reads columns by name.
    previous = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        return executor(conn, StorageDeps(settings=settings, gate=ApprovedByDispatcher()), actor, args)
    finally:
        conn.row_factory = previous
