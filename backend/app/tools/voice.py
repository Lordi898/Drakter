"""Voice profile tools: list the profiles and switch the active one.

The IDs live only in the user's ``voces.toml``; no result here carries a whole ID. The switch
is low risk (a name saved in the settings), so it needs no confirmation. The registry audits it.
"""

from __future__ import annotations

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


class SetProfileResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: str
    previous: str
    description: str
    changed: bool


def _raise(exc: VoiceProfileError) -> ToolError:
    return ToolError(exc.code, exc.message)


def _list_profiles(ctx: ToolContext, args: NoArgs) -> ProfileList:
    try:
        return service.list_profiles(ctx.state.settings.db_path)
    except VoiceProfileError as exc:
        raise _raise(exc) from None


async def _set_profile(ctx: ToolContext, args: SetProfileArgs) -> SetProfileResult:
    db_path = ctx.state.settings.db_path
    try:
        name = service.resolve_configured(args.profile)
        config = service.load_config()
        previous = service.active_profile(db_path, config)
        changed = previous != name
        service.save_active(db_path, name)
    except VoiceProfileError as exc:
        raise _raise(exc) from None
    if changed:
        await _announce(ctx, name, previous)
    return SetProfileResult(
        active=name, previous=previous, description=config.perfiles[name].descripcion, changed=changed
    )


async def _announce(ctx: ToolContext, name: str, previous: str) -> None:
    """Event for the interface and message for the voice process. Neither can fail the tool."""
    hub: Any = getattr(getattr(ctx.state, "agent_runtime", None), "hub", None)
    if hub is not None:
        try:
            hub.publish(
                "voice.profile_changed",
                VoiceProfileChanged(profile=name, previous=previous),
                correlation_id=str(ctx.turn_id),
            )
        except Exception:  # noqa: BLE001
            logger.exception("event failed", extra={"event": "voice_profile_event_failed"})
    voice: Any = getattr(ctx.state, "voice_service", None)
    if voice is not None:
        try:
            await voice.set_voice_profile(name)
        except Exception:  # noqa: BLE001 - an old voice process ignores it
            logger.warning("voice process ignored the profile", extra={"event": "voice_ipc_skip"})


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
            "Cambia el perfil de voz activo por nombre o alias (\"la neutral\", \"la otra\"). "
            "Falla si no existe o aún no tiene ID de voz."
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
