"""Herramientas de la interfaz: modo (Jarvis o Drakter) y apariencia (avatar e interfaz Jarvis).

Solo cambia el aspecto (reversible, sin datos), así que no pide confirmación; en una sesión
contaminada por documentos o memoria la puerta la sube a `confirm` como a cualquier WRITE. La
audita el registro. Publican `ui.mode` y `ui.appearance` por `app.services.ui_mode`, con el límite
de 1/s por tipo.
"""

from __future__ import annotations

from typing import Any, Final, Literal

from drakter_contracts.events import AvatarChoice, JarvisLayoutChoice
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.ui_mode import request_ui_appearance, request_ui_mode
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec

_ERRORS: Final = ("ui_unavailable",)


class SetUiModeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["jarvis", "drakter"] = Field(
        description="'jarvis' = interfaz holográfica (modo Jarvis); 'drakter' = la interfaz normal."
    )


class SetUiModeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested: Literal["jarvis", "drakter"]
    delivered: bool  # se publicó la petición; la ventana puede estar cerrada
    note: str


async def _set_mode(ctx: ToolContext, args: SetUiModeArgs) -> SetUiModeResult:
    hub: Any = getattr(getattr(ctx.state, "agent_runtime", None), "hub", None)
    outcome = request_ui_mode(hub, args.mode, "agent", correlation_id=str(ctx.turn_id))
    if outcome == "unavailable":
        raise ToolError("ui_unavailable", "No se pudo avisar a la interfaz de escritorio.", retryable=True)
    if outcome == "rate_limited":
        return SetUiModeResult(
            requested=args.mode,
            delivered=False,
            note="La interfaz acaba de cambiar de modo; no se ha vuelto a pedir.",
        )
    return SetUiModeResult(
        requested=args.mode,
        delivered=True,
        note="Petición enviada: si la app está abierta, cambia de modo en un instante.",
    )


class SetAppearanceArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    avatar: AvatarChoice | None = Field(
        default=None,
        description=(
            "Avatar 3D: holo-contorno (Holo-Contorno, holograma), holo-hilo (hilos), holo-busto (busto), "
            "holo-orbe (orbe), holo-filamento (filamento azul), ascuario (el dragón), relojero (El Relojero), "
            "filamento (filamento dorado) o none (sin avatar 3D: el personaje clásico)."
        ),
    )
    layout: JarvisLayoutChoice | None = Field(
        default=None,
        description="Interfaz del modo Jarvis: nucleo (Núcleo), holomesa (Holomesa, la mesa) o visor (Visor).",
    )

    @model_validator(mode="after")
    def _something(self) -> SetAppearanceArgs:
        if self.avatar is None and self.layout is None:
            raise ValueError("indica avatar, layout o ambos")
        return self


class SetAppearanceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    avatar: AvatarChoice | None
    layout: JarvisLayoutChoice | None
    delivered: bool  # se publicó la petición; la ventana puede estar cerrada
    note: str


async def _set_appearance(ctx: ToolContext, args: SetAppearanceArgs) -> SetAppearanceResult:
    hub: Any = getattr(getattr(ctx.state, "agent_runtime", None), "hub", None)
    outcome = request_ui_appearance(
        hub, "agent", avatar=args.avatar, layout=args.layout, correlation_id=str(ctx.turn_id)
    )
    if outcome == "unavailable":
        raise ToolError("ui_unavailable", "No se pudo avisar a la interfaz de escritorio.", retryable=True)
    if outcome == "rate_limited":
        return SetAppearanceResult(
            avatar=args.avatar, layout=args.layout, delivered=False,
            note="La apariencia acaba de cambiar; no se ha vuelto a pedir.",
        )
    note = "Petición enviada: si la app está abierta, cambia en un instante."
    if args.layout:
        note += " Elegir una interfaz también abre el modo Jarvis."
    if args.avatar and args.avatar != "none":
        note += " Si ese avatar aún no está instalado en la app, se verá el personaje clásico."
    return SetAppearanceResult(avatar=args.avatar, layout=args.layout, delivered=True, note=note)


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="ui_set_mode",
        description=(
            "Cambia el aspecto de la app de escritorio entre el modo Jarvis (interfaz holográfica) "
            "y Drakter (la normal). Solo cambia la interfaz: no toca datos ni tu forma de ser. "
            "Úsala cuando el usuario lo pida."
        ),
        domain="ui",
        args_model=SetUiModeArgs,
        result_model=SetUiModeResult,
        permission="ui.write",
        risk=RiskClass.WRITE,
        handler=_set_mode,
        errors=_ERRORS,
        idempotent=True,
        timeout_s=3.0,
        audit={"mode": "log"},
    ),
    ToolSpec(
        name="ui_set_appearance",
        description=(
            "Cambia el avatar 3D del personaje (en los dos modos) y/o la interfaz del modo Jarvis. Solo "
            "cambia el aspecto: no toca datos ni tu forma de ser. Úsala cuando el usuario lo pida; elegir "
            "una interfaz también abre el modo Jarvis."
        ),
        domain="ui",
        args_model=SetAppearanceArgs,
        result_model=SetAppearanceResult,
        permission="ui.write",
        risk=RiskClass.WRITE,
        handler=_set_appearance,
        errors=_ERRORS,
        idempotent=True,
        timeout_s=3.0,
        audit={"avatar": "log", "layout": "log"},
    ),
)
