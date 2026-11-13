"""Perfil de voz activo: el backend es la fuente de verdad (ajuste ``voice_profile``).

Los IDs de Fish viven solo en ``voces.toml`` del usuario (``drakter_contracts.voice_profiles``).
Aquí se resuelve el perfil, se guarda cuál está activo y se enmascaran los IDs; el valor
guardado es el nombre del perfil, nunca el ID.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Final

from drakter_contracts.voice_profiles import (
    VoiceConfig,
    VoiceConfigError,
    VoiceProfileStore,
    mask_id,
)
from pydantic import BaseModel, ConfigDict

from app.core.errors import AppError
from app.database.connection import connect
from app.repositories import settings as repo

logger = logging.getLogger(__name__)

SETTING_KEY: Final = "voice_profile"
_STORE: Final = VoiceProfileStore()


class VoiceProfileError(Exception):
    """Fallo esperado. ``code`` es estable; ``message`` se puede enseñar al agente."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ProfileInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    aliases: list[str]
    active: bool
    configured: bool
    id_masked: str | None


class ProfileList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: str
    default: str
    model: str
    provider: str
    config_path: str
    profiles: list[ProfileInfo]
    hint: str | None = None


def get_store() -> VoiceProfileStore:
    return _STORE


def load_config(store: VoiceProfileStore | None = None) -> VoiceConfig:
    store = store or _STORE
    try:
        return store.get()
    except VoiceConfigError as exc:
        raise VoiceProfileError("voice_config_invalid", str(exc)) from None


def stored_profile(db_path: Path) -> str | None:
    try:
        with closing(connect(db_path)) as conn:
            if not repo.table_exists(conn, "settings"):
                return None
            item = repo.read_all(conn).get(SETTING_KEY)
    except Exception:  # noqa: BLE001 - leer el perfil activo nunca rompe la lista
        return None
    return item.value if item else None


def active_profile(db_path: Path, config: VoiceConfig) -> str:
    """El guardado si todavía existe en el archivo; si no, el de por defecto."""
    saved = stored_profile(db_path)
    return saved if saved in config.perfiles else config.default


def list_profiles(db_path: Path, store: VoiceProfileStore | None = None) -> ProfileList:
    config = load_config(store)
    active = active_profile(db_path, config)
    profiles = [
        ProfileInfo(
            name=name,
            description=p.descripcion,
            aliases=list(p.alias),
            active=name == active,
            configured=p.configured,
            id_masked=mask_id(p.reference_id),
        )
        for name, p in config.perfiles.items()
    ]
    path = (store or _STORE).path
    pending = [p.name for p in profiles if not p.configured]
    return ProfileList(
        active=active,
        default=config.default,
        model=config.tts.modelo,
        provider=config.tts.proveedor,
        config_path=str(path),
        profiles=profiles,
        hint=f"Sin configurar: {', '.join(pending)}. Pon los IDs en {path}" if pending else None,
    )


def resolve_configured(
    query: str, store: VoiceProfileStore | None = None, config: VoiceConfig | None = None
) -> str:
    """Nombre canónico de un perfil existente y con ID. Si no, ``VoiceProfileError``.

    Con ``config`` se usa esa misma lectura del archivo (una sola por operación).
    """
    config = config or load_config(store)
    name = config.resolve(query)
    if name is None:
        known = ", ".join(config.perfiles)
        raise VoiceProfileError("profile_not_found", f"No existe ese perfil de voz. Hay: {known}.")
    if not config.perfiles[name].configured:
        raise VoiceProfileError(
            "profile_unconfigured",
            f"Perfil sin configurar: el perfil {name!r} no tiene ID de voz. "
            f"El usuario debe poner el ID en {(store or _STORE).path}.",
        )
    return name


class SwitchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: str
    previous: str
    description: str
    changed: bool


def switch_profile(db_path: Path, query: str) -> SwitchResult:
    """Resuelve, guarda y devuelve el cambio. Bloqueante: llamar con ``asyncio.to_thread``."""
    config = load_config()
    name = resolve_configured(query, config=config)
    previous = active_profile(db_path, config)
    save_active(db_path, name)
    return SwitchResult(
        active=name,
        previous=previous,
        description=config.perfiles[name].descripcion,
        changed=previous != name,
    )


def save_active(db_path: Path, name: str) -> str | None:
    """Guarda el perfil activo. Devuelve el anterior (``None`` si no había)."""
    try:
        with closing(connect(db_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                if not repo.table_exists(conn, "settings"):
                    raise VoiceProfileError("settings_unavailable", "Ajustes no disponibles.")
                previous = repo.read_all(conn).get(SETTING_KEY)
                repo.upsert(conn, SETTING_KEY, name, repo.now_utc())
                conn.execute("COMMIT")
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
    except VoiceProfileError:
        raise
    except Exception:  # noqa: BLE001
        logger.error("voice profile save failed", extra={"event": "voice_profile_save_failed"})
        raise VoiceProfileError("settings_unavailable", "Ajustes no disponibles.") from None
    return previous.value if previous else None


def validate_setting_value(value: str, store: VoiceProfileStore | None = None) -> str:
    """Para ``POST /settings/voice_profile``: nombre canónico, existente y configurado."""
    try:
        return resolve_configured(value, store)
    except VoiceProfileError as exc:
        status = 422
        raise AppError("invalid_voice_profile", exc.message, status) from None
