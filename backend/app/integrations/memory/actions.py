"""Forget and approve a memory from the GUI as `ActionService` actions: 409, then run on approve.

Single confirmation path (`contracts/README.md` §5, `contracts/api/routes.md` memoria). The
client sends no confirmation id: the row lives in `pending_confirmations` and is resolved in
`POST /confirmations/{id}/approve` with the approver token. The agent keeps its own
`forget_memory` tool action; these names are GUI only.

`external=True`: the memory adapter opens its own connections, which would block on the
gate's transaction. The target carries a hash of the record: if it changes before approval,
the confirmation fails with `conflict`.
"""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any, Final
from uuid import UUID

from drakter_contracts.tools import RiskClass
from pydantic import BaseModel, ConfigDict

from app.core.errors import AppError
from app.integrations.memory.service import USER, MemoryService
from app.permissions.models import ActionRegistry, ActionSpec

FORGET_MEMORY_GUI: Final = "forget_memory_gui"
APPROVE_MEMORY_GUI: Final = "approve_memory_gui"


class MemoryTargetArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID


def _targets(service: MemoryService) -> Any:
    def resolve(_conn: sqlite3.Connection, params: BaseModel) -> list[dict[str, Any]]:
        memory_id = getattr(params, "id")
        try:
            rec = service.get(memory_id)
        except AppError:
            return [{"id": str(memory_id), "content_hash": "missing"}]
        state = f"{rec.status.value}|{rec.updated_at.isoformat()}|{rec.content_hash}"
        return [{"id": str(memory_id), "content_hash": hashlib.sha256(state.encode()).hexdigest()}]

    return resolve


def forget_spec(service: MemoryService) -> ActionSpec:
    def handler(_conn: sqlite3.Connection, params: BaseModel) -> dict[str, Any]:
        report = service.forget_authorized(getattr(params, "id"), USER)
        return report.model_dump(mode="json")

    return ActionSpec(
        name=FORGET_MEMORY_GUI,
        permission="memory.forget",
        risk=RiskClass.CONFIRM,
        args_model=MemoryTargetArgs,
        handler=handler,
        summarize=lambda params: (
            f"Vas a olvidar de forma permanente el recuerdo {getattr(params, 'id')}. "
            "Esta acción no se puede deshacer."
        ),
        audit={"id": "log"},
        resolve_targets=_targets(service),
        entity_type="memory",
        external=True,
    )


def approve_spec(service: MemoryService) -> ActionSpec:
    def handler(_conn: sqlite3.Connection, params: BaseModel) -> dict[str, Any]:
        return service.approve(getattr(params, "id"), USER).model_dump(mode="json")

    return ActionSpec(
        name=APPROVE_MEMORY_GUI,
        permission="memory.approve",
        risk=RiskClass.CONFIRM,
        args_model=MemoryTargetArgs,
        handler=handler,
        summarize=lambda params: (
            f"Vas a aprobar el recuerdo {getattr(params, 'id')}: el agente podrá recuperarlo."
        ),
        audit={"id": "log"},
        resolve_targets=_targets(service),
        entity_type="memory",
        external=True,
    )


def register_actions(registry: ActionRegistry, service: MemoryService | None) -> None:
    """Call after `install_security` and before `start_security` (which freezes the registry)."""
    if service is None:
        return
    registry.register(forget_spec(service))
    registry.register(approve_spec(service))
