"""Contrato de `/api/v1/settings`. Congelado: backend y escritorio construyen sobre esto.

- La tabla `settings` solo guarda valores no sensibles, y solo las claves de `SETTING_KEYS`.
  Cualquier otra clave es 404 `unknown_setting`: por aquí no entran secretos, permisos ni
  confirmaciones.
- El estado de la clave de API es solo presencia. El valor no se lee, no se transporta y no se
  registra. `.env` no se abre: de ese archivo solo se mira si existe.
- `unknown` significa "no se puede afirmar sin leer lo que no debemos leer". Nunca se convierte
  en `missing` ni en `inactive` por comodidad.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

SETTING_KEYS: Final = frozenset({"default_timezone", "voice_profile"})

KeyState = Literal["configured", "missing", "unknown"]
DevModeState = Literal["active", "inactive", "unknown"]


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True)


class SettingItem(_Out):
    key: str
    value: str | None  # null = sin valor guardado; la interfaz usa la zona del sistema
    updated_at: str | None


class SettingsList(_Out):
    persisted: bool  # False si la tabla aún no está migrada: se puede leer, no guardar
    items: list[SettingItem]


class SettingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: str = Field(min_length=1, max_length=64)


class AgentConfigStatus(_Out):
    key: KeyState
    dev_mode: DevModeState
    provider: str | None  # nombre público del proveedor, nunca una credencial
    model: str | None


class StorageStatus(_Out):
    data_dir: str
    schema_version: int | None


class BackupItem(_Out):
    name: str  # solo el nombre del archivo, nunca una ruta
    created_at: str  # UTC, sacado del nombre del archivo
    label: str
    size_bytes: int


class BackupList(_Out):
    items: list[BackupItem]


class SettingsStatus(_Out):
    agent: AgentConfigStatus
    storage: StorageStatus
    last_backup: BackupItem | None
