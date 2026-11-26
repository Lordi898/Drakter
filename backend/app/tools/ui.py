"""Herramienta del modo de interfaz: pasar el escritorio a Jarvis o volver a Drakter.

Solo cambia el aspecto (reversible, sin datos), así que no pide confirmación; en una sesión
contaminada por documentos o memoria la puerta la sube a `confirm` como a cualquier WRITE. La
audita el registro. Publica `ui.mode` por `app.services.ui_mode`, con el límite común de 1/s.
"""

from __future__ import annotations

from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.ui_mode import request_ui_mode
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
)
