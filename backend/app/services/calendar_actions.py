"""Borrados de calendario y asignaturas como acciones de `ActionService`.

Se registran antes de adaptar las herramientas: `delete_event`, `delete_time_block` y
`delete_class_session` son a la vez ruta REST y herramienta, y comparten esta acción.
El servicio audita el éxito en la misma transacción; el handler no audita ni confirma.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from typing import Any

from drakter_contracts.tools import RiskClass
from pydantic import BaseModel, ConfigDict

from app.core.errors import AppError
from app.permissions.models import ActionRegistry, ActionSpec
from app.services import calendar as calendar_service
from app.services import subjects as subjects_service


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeleteEventArgs(_Args):
    event_id: str


class DeleteTimeBlockArgs(_Args):
    time_block_id: str


class DeleteClassSessionArgs(_Args):
    session_id: str


class DeleteSubjectArgs(_Args):
    subject_id: str


def _targets(field: str) -> Callable[[sqlite3.Connection, BaseModel], list[dict[str, Any]]]:
    def resolve(conn: sqlite3.Connection, params: BaseModel) -> list[dict[str, Any]]:
        entity_id = getattr(params, field)
        row = conn.execute("SELECT revision FROM entities WHERE id=?", (entity_id,)).fetchone()
        if row is None:
            raise AppError("not_found", "No se encuentra ese elemento. Puede que se haya eliminado.", 404)
        return [{"id": entity_id, "revision": row[0]}]

    return resolve


def _spec(
    name: str,
    permission: str,
    args_model: type[BaseModel],
    field: str,
    entity_type: str,
    label: str,
    delete: Callable[[sqlite3.Connection, str], Mapping[str, Any]],
) -> ActionSpec:
    return ActionSpec(
        name=name,
        permission=permission,
        risk=RiskClass.CONFIRM,
        args_model=args_model,
        handler=lambda conn, params: delete(conn, getattr(params, field)),
        summarize=lambda _: f"Vas a eliminar 1 {label}. Esta acción no se puede deshacer.",
        audit={field: "log"},
        resolve_targets=_targets(field),
        entity_type=entity_type,
    )


ACTION_SPECS: tuple[ActionSpec, ...] = (
    _spec(
        "delete_event", "calendar.delete", DeleteEventArgs, "event_id", "calendar_event",
        "evento", calendar_service.execute_delete_event,
    ),
    _spec(
        "delete_time_block", "calendar.delete", DeleteTimeBlockArgs, "time_block_id", "time_block",
        "bloque de tiempo", calendar_service.execute_delete_time_block,
    ),
    _spec(
        "delete_class_session", "subjects.delete", DeleteClassSessionArgs, "session_id",
        "class_session", "sesión de clase", subjects_service.execute_delete_class_session,
    ),
    _spec(
        "delete_subject", "subjects.delete", DeleteSubjectArgs, "subject_id", "subject",
        "asignatura", subjects_service.execute_delete_subject,
    ),
)  # fmt: skip


def register_actions(registry: ActionRegistry) -> None:
    """Llamar tras `install_security`, antes de adaptar herramientas con `tool_action_spec`."""
    for spec in ACTION_SPECS:
        registry.register(spec)
