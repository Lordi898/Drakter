"""Herramientas del modo flotante para dibujar y guiar (dominio `overlay`, docs/floating/CONTRACT.md §8.2).

`draw` y `guide_wait` son READ: dibujar es responder, no actuar (§14.2). Las marcas que actúan (`type`, `copy`,
`open`, `handoff`) están prohibidas y los botones solo ejecutan lo que el backend guardó y el usuario pulsa.
La validación (tidy → esquema → checkDraw → reglas de Drakter) está en `app/floating/validate.py`; la
reproducción, en `app/floating/runner.py`.
"""

from __future__ import annotations

from typing import Any, Final

from drakter_contracts.floating import DrawToolArgs, DrawToolResult, GuideWaitArgs, GuideWaitResult
from pydantic import model_validator

from app.floating.runner import RUNNER
from app.floating.validate import lean_schema, tidy_strict, validate_draw
from app.tools.spec import RiskClass, ToolContext, ToolSpec


class DrawArgs(DrawToolArgs):
    """`DrawToolArgs` con el tidy de Roamies antes de pydantic y el esquema lean para el modelo."""

    @model_validator(mode="before")
    @classmethod
    def _tidy(cls, data: Any) -> Any:
        return tidy_strict(data) if isinstance(data, dict) else data

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        return lean_schema()


async def _draw(ctx: ToolContext, args: DrawArgs) -> DrawToolResult:
    RUNNER.bind(ctx.state)
    valid = validate_draw(args.model_dump(exclude_none=True))
    return await RUNNER.draw(turn_id=ctx.turn_id, session_id=ctx.session_id, call_id=ctx.call_id, args=valid)


async def _guide_wait(ctx: ToolContext, args: GuideWaitArgs) -> GuideWaitResult:
    RUNNER.bind(ctx.state)
    return await RUNNER.guide_wait(args.guide_id)


_DRAW_DESCRIPTION: Final = (
    "Dibuja sobre la pantalla del usuario mientras habla: señala, rodea, subraya o numera cosas reales (beats con "
    "say y marks), o pinta tarjetas y diagramas en una zona libre. Un beat con wait espera a que el usuario haga "
    "clic o pase el ratón: entonces devuelve status=waiting y sigues con guide_wait. Solo funciona con el modo "
    "flotante activo. Lo que pone en say ya se dice en voz alta: no lo repitas.\n"
    "beats [{say, marks, wait?}]: say es una frase de menos de 20 palabras; 1 a 4 marcas por beat, en el orden en "
    "que las nombras; hasta 12 beats y 40 marcas.\n"
    "Lugares (at, to, tie), mejor primero: {text}: las palabras exactas en pantalla (every: true marca cada sitio, "
    "within {x, y, w, h} se limita a una zona); {id} de read_window; {x, y, w, h}: centro y tamaño en px de tu "
    "última captura (look_screen).\n"
    "Pantalla: target (un control que pulsar), ring, point, frame, underline, strike, check, cross, num, label, "
    "connect (at → to), trace/line/curve/arrow (points [x, y] de la captura), scroll (dir up|down), spotlight, "
    "hover (con wait 'hover'), write (text), highlight, circle, rect.\n"
    "Guías («¿cómo hago…?»): un beat por paso, cada uno un target con label y wait 'click'; el paso siguiente se "
    "busca tras el clic.\n"
    "Tarjetas (junto a la ventana; title, tie, card_size small|normal|large|full): card (heading, text, items, "
    "sources), note (text), clip (title, text), sources ([{name, url}]), legend (keys [{tone, text}]), list (title, "
    "items), mindmap (title, branches [{text, items, tone}], 2 a 8), bars (bars [{label, value, tone}], unit), graph "
    "(x_range, y_range, plots [{points, tone, label}], dots), timeline (events [{when, text}]), table (columns, rows), "
    "flow (nodes [{id, text, shape, tone}], links [{from, to, label, flow}], dir down|right), map (region, shade "
    "[{name, tone}], pins [{name, lat, lon}], routes), math (steps [{tex, note}], una línea LaTeX por paso), "
    "geometry (vertices, lines, angles, circles), molecule (smiles), model (parts 3D), quiz (questions [{text, "
    "options, answer, explain}]), ticket, medal, photo (sin imagen en Drakter: solo marco y pie).\n"
    "button (text, action {do: ask|open|copy, value}): un siguiente paso que pulsa el usuario. emote (name: "
    "hype|wave|upset|remind|motivate), sfx (name). type, copy, open y handoff no existen aquí: para actuar usa "
    "act_in_app u open_target. tone: accent, teal, amber, coral, lilac, sky, lime, red, white.\n"
    "deep: true para explicar a fondo (una tarjeta grande cada vez). keep: true conserva las tarjetas. Cada pieza "
    "recibe un id (p1, p2…); para cambiarla: edit [{do: recolor|move|erase|clear, part, tone, dx, dy}] sin beats."
)

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="draw",
        description=_DRAW_DESCRIPTION,
        domain="overlay",
        args_model=DrawArgs,
        result_model=DrawToolResult,
        permission="overlay.read",
        risk=RiskClass.READ,
        handler=_draw,
        errors=(
            "validation_error", "draw_invalid", "draw_action_forbidden", "floating_inactive", "overlay_unavailable",
            "companion_unavailable", "stale_screenshot", "stale_read", "part_not_found", "guide_busy", "interrupted",
        ),
        idempotent=False,
        timeout_s=90.0,
        audit={"target": "log", "deep": "log", "keep": "log"},
    ),
    ToolSpec(
        name="guide_wait",
        description=(
            "Espera a que el usuario haga el clic o el hover que pide el beat en curso de una guía (hasta unos "
            "110 s) y sigue dibujando los beats siguientes hasta la próxima espera o el final. Llámala tras draw "
            "o guide_wait con status=waiting."
        ),
        domain="overlay",
        args_model=GuideWaitArgs,
        result_model=GuideWaitResult,
        permission="overlay.read",
        risk=RiskClass.READ,
        handler=_guide_wait,
        errors=("guide_not_found", "floating_inactive", "overlay_unavailable", "interrupted"),
        idempotent=False,
        timeout_s=115.0,
        audit={"guide_id": "log"},
    ),
)
