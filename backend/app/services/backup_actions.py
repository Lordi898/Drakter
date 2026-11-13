"""Borrar una copia (bundle) como acción de `ActionService`: 409 y ejecución en approve.

Único camino de confirmación (`contracts/README.md` §5). Solo la GUI: el agente no tiene
permiso `backups.*` ni herramienta. Riesgo `confirm`, efecto fuera de SQLite (`external`).
El objetivo guarda el hash del archivo: si la copia cambia antes de aprobar, `conflict`.

Restaurar no está aquí: con el backend en marcha, `database.backup.restore_backup` no puede
tomar el bloqueo de instancia y la restauración en caliente necesita un diseño propio.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Final

from drakter_contracts.tools import RiskClass
from pydantic import BaseModel, ConfigDict, field_validator

from app.core.config import Settings
from app.permissions.models import ActionRegistry, ActionSpec
from app.services.backup_service import bundle_digest, delete_bundle, is_bundle_name

DELETE_BACKUP: Final = "delete_backup"


class DeleteBackupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str

    @field_validator("name")
    @classmethod
    def _bundle_name(cls, value: str) -> str:
        if not is_bundle_name(value):
            raise ValueError("identificador de copia no válido")
        return value


def delete_backup_spec(settings: Settings) -> ActionSpec:
    def targets(_conn: sqlite3.Connection, params: BaseModel) -> list[dict[str, Any]]:
        name = getattr(params, "name")
        return [{"id": name, "content_hash": bundle_digest(settings, name)}]

    def handler(_conn: sqlite3.Connection, params: BaseModel) -> dict[str, Any]:
        name = getattr(params, "name")
        delete_bundle(settings, name)
        return {"name": name, "deleted": True}

    return ActionSpec(
        name=DELETE_BACKUP,
        permission="backups.delete",
        risk=RiskClass.CONFIRM,
        args_model=DeleteBackupArgs,
        handler=handler,
        summarize=lambda params: (
            f"Vas a eliminar 1 copia de seguridad: «{getattr(params, 'name')}». "
            "Esta acción no se puede deshacer."
        ),
        audit={"name": "log"},
        resolve_targets=targets,
        entity_type="backup",
        external=True,
    )


def register_actions(registry: ActionRegistry, settings: Settings) -> None:
    """Llamar tras `install_security` y antes de `start_security` (que congela el registro)."""
    registry.register(delete_backup_spec(settings))
