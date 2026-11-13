"""Voice profile tools: list the profiles and switch the active one.

The IDs live only in the user's ``voces.toml``; no result here carries a whole ID. The switch
is low risk (a name saved in the settings), so it needs no confirmation. The registry audits it.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Final

from drakter_contracts.events import VoiceProfileChanged
from pydantic import BaseModel, ConfigDict, Field

from app.services import voice_profile as service
from app.services.voice_profile import ProfileList, VoiceProfileError
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec

logger = logging.getLogger("drakter.tools")

_ERRORS: Final = (
    "voice_config_invalid",
    "profile_not_found",
    "profile_unconfigured",
    "settings_unavailable",
)


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SetProfileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str = Field(
        min_length=1,
        max_length=64,
        description="Nombre del perfil o uno de sus alias, tal como lo dijo el usuario.",
    )


# Ningún TTS usa todavía el perfil (Pipecat + Fish no están): el cambio solo queda guardado.
# Pasará a True cuando el proceso de voz lo aplique de verdad.
VOICE_APPLIES_PROFILE: Final = False


class SetProfileResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: str
    previous: str
    description: str
    changed: bool
    applied_to_voice: bool  # False: preferencia guardada, la voz que suena no cambia aún
    note: str


def _list_profiles(ctx: ToolContext, args: NoArgs) -> ProfileList:
    try:
        return service.list_profiles(ctx.state.settings.db_path)
    except VoiceProfileError as exc:
        raise ToolError(exc.code, exc.message) from None


async def _set_profile(ctx: ToolContext, args: SetProfileArgs) -> SetProfileResult:
    try:
        # SQLite y el archivo son E/S bloqueante: fuera del event loop.
        done = await asyncio.to_thread(service.switch_profile, ctx.state.settings.db_path, args.profile)
    except VoiceProfileError as exc:
        raise ToolError(exc.code, exc.message) from None
    if done.changed:
        _announce(ctx, done.active, done.previous)
    note = (
        "El perfil está activo en la voz."
        if VOICE_APPLIES_PROFILE
        else "Preferencia guardada: la voz con Fish aún no está conectada, así que no suena "
        "distinto todavía; se usará cuando lo esté."
    )
    return SetProfileResult(**done.model_dump(), applied_to_voice=VOICE_APPLIES_PROFILE, note=note)


def _announce(ctx: ToolContext, name: str, previous: str) -> None:
    """Evento para la interfaz. No puede hacer fallar la herramienta."""
    hub: Any = getattr(getattr(ctx.state, "agent_runtime", None), "hub", None)
    if hub is None:
        return
    try:
        hub.publish(
            "voice.profile_changed",
            VoiceProfileChanged(profile=name, previous=previous),
            correlation_id=str(ctx.turn_id),
        )
    except Exception:  # noqa: BLE001
        logger.exception("event failed", extra={"event": "voice_profile_event_failed"})


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="voice_list_profiles",
        description=(
            "Lista los perfiles de voz: nombre, alias, descripción, cuál está activo y si "
            "están configurados. Úsala si el usuario pregunta qué voces tienes."
        ),
        domain="voice",
        args_model=NoArgs,
        result_model=ProfileList,
        permission="voice.read",
        risk=RiskClass.READ,
        handler=_list_profiles,
        errors=_ERRORS,
        idempotent=True,
        timeout_s=5.0,
    ),
    ToolSpec(
        name="voice_set_profile",
        description=(
            "Cambia el perfil de voz activo por nombre o alias (\"neutral\", \"la otra\"; vale "
            "tal como lo diga el usuario). Falla si no existe o aún no tiene ID de voz. "
            "Guarda la preferencia: mira `applied_to_voice` antes de decir que ya suena."
        ),
        domain="voice",
        args_model=SetProfileArgs,
        result_model=SetProfileResult,
        permission="voice.write",
        risk=RiskClass.WRITE,
        handler=_set_profile,
        errors=_ERRORS,
        idempotent=True,
        timeout_s=10.0,
        audit={"profile": "log"},
    ),
)
