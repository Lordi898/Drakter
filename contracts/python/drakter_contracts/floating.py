"""Modo flotante: eventos, cuerpos REST y argumentos/resultados de herramientas (docs/floating/CONTRACT.md).

Coordenadas: **px lógicos globales del stage de GNOME** (los mismos que da la extensión drakter-companion),
origen arriba a la izquierda de la disposición de monitores. Un rectángulo en lista es `[x, y, w, h]`.
Las capturas tienen su propia escala (`scale_to_logical`); el modelo habla en px de la captura y el backend
convierte. Identificadores de ventana: el `id` uint64 de Mutter **como cadena decimal** (JS pierde precisión).

Todo texto que venga de la pantalla (títulos, árbol de accesibilidad, OCR, píxeles) es dato no confiable y
solo viaja dentro de `UntrustedEnvelope.content`; los campos estructurados no llevan texto de terceros.
"""

from __future__ import annotations

from typing import Annotated, Any, Final, Literal

from pydantic import BaseModel, Field, model_validator

from .common import ContractModel, Id, Instant
from .tools import ImageAttachment, UntrustedEnvelope

# ── tipos comunes ────────────────────────────────────────────────────────────
WindowId = Annotated[str, Field(pattern=r"^[0-9]{1,20}$")]
PartId = Annotated[str, Field(pattern=r"^p[0-9]{1,4}$")]
RectList = Annotated[list[float], Field(min_length=4, max_length=4)]
"""`[x, y, w, h]` en px lógicos globales."""

AvatarSize = Literal["default", "small", "cursor"]
AvatarPin = Literal["top-left", "top-right", "bottom-left", "bottom-right", "center", "release"]
BeatWait = Literal["click", "hover"]
WaitResult = Literal["clicked", "hovered", "timeout", "skipped"]
CompanionStatus = Literal["ok", "missing", "outdated", "denied", "unsupported_session"]


class LogicalRect(ContractModel):
    x: int
    y: int
    w: Annotated[int, Field(ge=0)]
    h: Annotated[int, Field(ge=0)]


class MonitorInfo(ContractModel):
    index: Annotated[int, Field(ge=0)]
    geometry: LogicalRect
    workarea: LogicalRect
    scale: Annotated[float, Field(gt=0, le=4)]
    primary: bool


class WindowRef(ContractModel):
    """Ventana sin texto de terceros: el título va, si acaso, en el sobre no confiable."""

    window_id: WindowId
    app_id: Annotated[str, Field(max_length=255)] | None = None
    pid: Annotated[int, Field(ge=0)]
    client: Literal["wayland", "x11"]
    frame: LogicalRect
    monitor: Annotated[int, Field(ge=0)]
    focused: bool
    fullscreen: bool = False
    hands_off: bool = False
    """La app está en HANDS_OFF: se puede señalar, nunca accionar."""
    drakter: bool = False
    """Es una ventana del propio Drakter (mismo pid que Electron o el backend)."""


# ── ui.floating (backend → Electron main) ────────────────────────────────────
class UiFloatingRequested(BaseModel):
    """Pide activar/desactivar el modo flotante o cambiar el avatar flotante. Solo estética; decide Electron main.

    `source`: `voice` (capa 0, frase cerrada) o `agent` (`ui_set_floating`). Al menos uno de `action`, `size`, `pin`.
    """

    action: Literal["on", "off", "toggle"] | None = None
    size: AvatarSize | None = None
    pin: AvatarPin | None = None
    source: Literal["voice", "agent"]
    utt_id: Annotated[str, Field(max_length=64)] | None = None

    @model_validator(mode="after")
    def _something(self) -> UiFloatingRequested:
        if self.action is None and self.size is None and self.pin is None:
            raise ValueError("ui.floating needs action, size or pin")
        return self


# ── overlay.* (backend → Electron main → renderer flotante) ─────────────────
class OverlayBeat(BaseModel):
    """Un beat ya resuelto, con la forma que espera `ink.js` (Roamies `SC/tools.mjs:739-743`).

    `marks` son marcas de `draw.mjs` con los objetivos ya resueltos (`at.rect`, `to.rect`, `tie.rect`, `points`
    en px lógicos globales) y `part` asignada. Electron main las vuelve a validar con `draw.mjs` + zod.
    """

    say: Annotated[str, Field(max_length=240)]
    marks: Annotated[list[dict[str, Any]], Field(max_length=40)]
    wait: BeatWait | None = None
    n: Annotated[int, Field(ge=1, le=12)]
    caption: Annotated[str, Field(max_length=240)]
    voiced: bool
    read: Annotated[float, Field(ge=0, le=30)] | None = None


class OverlayDraw(BaseModel):
    """`overlay.draw`: un segmento (= un beat) de un dibujo. El bridge lo entrega como
    `{kind:'agent', e:{type:'draw', id: guide_id, seg, last, beats, edits, win, busy, fade?, deep?}}`."""

    guide_id: Id
    turn_id: Id
    call_id: Annotated[str, Field(max_length=64)]
    seg: Annotated[int, Field(ge=0, le=11)]
    last: bool
    beats: Annotated[list[OverlayBeat], Field(min_length=1, max_length=1)]
    edits: Annotated[list[dict[str, Any]], Field(max_length=20)] = []
    win: RectList | None = None
    busy: Annotated[list[RectList], Field(max_length=300)] = []
    fade: Annotated[float, Field(gt=0, le=120)] | None = None
    deep: bool | None = None
    speech_id: int | None = None
    """Locución de este beat (`speak.beat`). Solo Drakter: el bridge la quita antes de `ink.js`."""


class OverlayInkClear(BaseModel):
    """`overlay.ink_clear` → `{kind:'agent', e:{type:'ink_clear', ...}}` (`ink.js:2380-2384`)."""

    screen: bool | None = None
    stop: bool | None = None
    parts: Annotated[list[PartId], Field(max_length=64)] | None = None
    all: bool | None = None
    guide_id: Id | None = None


class OverlayInkStale(BaseModel):
    """`overlay.ink_stale` → `{kind:'agent', e:{type:'ink_stale'}}`: lo no fijado se desvanece."""

    reason: Literal["focus_changed", "window_moved", "window_closed"]


class HandsStepBounds(BaseModel):
    bounds: RectList
    hover: bool = False


class OverlayHands(BaseModel):
    """`overlay.hands` → `{kind:'hands', on}` | `{kind:'hands', step:{bounds, hover}}`. Exactamente uno."""

    act_id: Id
    on: bool | None = None
    step: HandsStepBounds | None = None

    @model_validator(mode="after")
    def _one(self) -> OverlayHands:
        if (self.on is None) == (self.step is None):
            raise ValueError("overlay.hands needs exactly one of on or step")
        return self


class TrailStep(BaseModel):
    text: Annotated[str, Field(max_length=48)]
    state: Literal["", "now", "ok", "bad"]
    why: Annotated[str, Field(max_length=120)] | None = None


class OverlayTrail(BaseModel):
    """`overlay.trail` → `{kind:'agent', e:{type:'trail', steps, head, final}}` (tarjeta de pasos)."""

    act_id: Id
    steps: Annotated[list[TrailStep], Field(min_length=1, max_length=8)]
    head: Annotated[str, Field(max_length=40)]
    final: bool


class OverlayClipboard(BaseModel):
    """`overlay.clipboard`: Electron main copia `text` al portapapeles (botón `copy` de una tarjeta, pulsado por el usuario)."""

    part: PartId
    text: Annotated[str, Field(max_length=600)]


# ── REST de entrada (solo Electron main, token `ui`) ─────────────────────────
class FloatingPresence(ContractModel):
    """`POST /api/v1/overlay/presence`. Al arrancar, en cada cambio y cada 30 s; caduca a los 75 s."""

    active: bool
    ready: bool
    """La página respondió `ui_ready`."""
    companion: CompanionStatus
    monitor: MonitorInfo | None = None
    bridge_version: Annotated[int, Field(ge=1)] = 1


class _ClientEvent(ContractModel):
    pass


class DrawStartedIn(_ClientEvent):
    type: Literal["draw_started"]
    guide_id: Id
    seg: Annotated[int, Field(ge=0, le=11)]


class DrawDoneIn(_ClientEvent):
    type: Literal["draw_done"]
    guide_id: Id


class DrawWaitDoneIn(_ClientEvent):
    type: Literal["draw_wait_done"]
    guide_id: Id
    beat: Annotated[int, Field(ge=1, le=12)]
    result: WaitResult


class InkClosedIn(_ClientEvent):
    type: Literal["ink_closed"]
    part: PartId


class InkClearedIn(_ClientEvent):
    type: Literal["ink_cleared"]


class InkPinnedIn(_ClientEvent):
    type: Literal["ink_pinned"]
    part: PartId
    on: bool


class InkActionIn(_ClientEvent):
    type: Literal["ink_action"]
    part: PartId


OverlayClientEvent = Annotated[
    DrawStartedIn | DrawDoneIn | DrawWaitDoneIn | InkClosedIn | InkClearedIn | InkPinnedIn | InkActionIn,
    Field(discriminator="type"),
]
"""`POST /api/v1/overlay/events`. `id` de Roamies = `guide_id`. Lo demás que manda la página lo resuelve main."""


# ── herramientas: dibujo y guía (dominio `overlay`) ─────────────────────────
class DrawToolArgs(ContractModel):
    """Envoltura de `draw`. El esquema que ve el modelo es `contracts/floating/draw_args.schema.json` (generado del
    zod de `draw.mjs`, versión lean); la validación real es: tidyDraw → JSON Schema → checkDraw → reglas Drakter."""

    target: Annotated[str, Field(max_length=120)] | None = None
    beats: Annotated[list[dict[str, Any]], Field(max_length=12)] | None = None
    edit: Annotated[list[dict[str, Any]], Field(max_length=20)] | None = None
    deep: bool | None = None
    keep: bool | None = None


class DrawnPart(BaseModel):
    part: PartId
    kind: Annotated[str, Field(max_length=16)]
    label: Annotated[str, Field(max_length=40)] | None = None


class MissingTarget(BaseModel):
    beat: Annotated[int, Field(ge=1, le=12)]
    mark: Annotated[int, Field(ge=1, le=40)]
    reason: Literal["not_found", "off_screen", "stale_shot", "stale_read", "no_window", "hands_off"]


class DrawToolResult(BaseModel):
    guide_id: Id
    status: Literal["done", "waiting", "edited"]
    """`waiting`: un beat espera clic o hover; llama a `guide_wait(guide_id)`."""
    waiting_beat: Annotated[int, Field(ge=1, le=12)] | None = None
    wait: BeatWait | None = None
    drawn: list[DrawnPart] = []
    on_screen: list[DrawnPart] = []
    missing: list[MissingTarget] = []
    said: list[Annotated[str, Field(max_length=240)]] = []
    """Ya dicho en voz alta: el modelo no lo repite."""
    notes: list[Annotated[str, Field(max_length=300)]] = []


class GuideWaitArgs(ContractModel):
    guide_id: Id


class GuideWaitResult(BaseModel):
    guide_id: Id
    beat: Annotated[int, Field(ge=1, le=12)]
    """Beat cuya espera se resolvió."""
    result: WaitResult
    status: Literal["waiting", "done", "stopped"]
    waiting_beat: Annotated[int, Field(ge=1, le=12)] | None = None
    wait: BeatWait | None = None
    said: list[Annotated[str, Field(max_length=240)]] = []
    notes: list[Annotated[str, Field(max_length=300)]] = []


# ── herramientas: pantalla (dominio `screen`) ───────────────────────────────
class ZoomRegion(ContractModel):
    """Recorte de una captura anterior del mismo turno, en px de esa captura."""

    shot_id: Id
    x: Annotated[float, Field(ge=0)]
    y: Annotated[float, Field(ge=0)]
    w: Annotated[float, Field(gt=0)]
    h: Annotated[float, Field(gt=0)]


class LookScreenArgs(ContractModel):
    target: Literal["front", "screen", "window"] = "front"
    window_id: WindowId | None = None
    zoom: ZoomRegion | None = None
    cursor: bool = False

    @model_validator(mode="after")
    def _window(self) -> LookScreenArgs:
        if (self.target == "window") != (self.window_id is not None):
            raise ValueError("window_id goes with target=window, and only then")
        return self


class ShotImage(BaseModel):
    width: Annotated[int, Field(ge=1, le=1568)]
    height: Annotated[int, Field(ge=1, le=1568)]
    mime_type: Literal["image/png", "image/jpeg"]
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class LookScreenResult(BaseModel):
    """`logical = origin + px_captura * scale_to_logical`. La imagen viaja aparte (`attachments`, ImageContent MCP)."""

    shot_id: Id
    image: ShotImage
    origin: Annotated[list[int], Field(min_length=2, max_length=2)]
    scale_to_logical: Annotated[float, Field(gt=0)]
    window: WindowRef | None = None
    taken_at: Instant
    envelope: UntrustedEnvelope
    attachments: list[ImageAttachment] = Field(default_factory=list, exclude=True)


class ReadWindowArgs(ContractModel):
    window_id: WindowId | None = None
    """Por defecto, la ventana activa (que no sea de Drakter)."""
    max_controls: Annotated[int, Field(ge=1, le=260)] = 260
    include_text: bool = True


class ControlInfo(BaseModel):
    """Sin nombre ni valor: esos textos van en el sobre (`#id rol «nombre» = valor`)."""

    id: Annotated[int, Field(ge=1)]
    role: Annotated[str, Field(max_length=40)]
    rect: LogicalRect | None = None
    states: list[Annotated[str, Field(max_length=24)]] = []
    actions: list[Annotated[str, Field(max_length=32)]] = []
    editable: bool = False
    offscreen: bool = False
    secret: bool = False
    """Campo de contraseña: no se lee su valor y las manos no escriben en él."""


class ReadWindowResult(BaseModel):
    read_id: Id
    window: WindowRef
    controls: Annotated[list[ControlInfo], Field(max_length=260)]
    text_truncated: bool = False
    redacted: Annotated[int, Field(ge=0)] = 0
    envelope: UntrustedEnvelope


class ListWindowsArgs(ContractModel):
    pass


class ListWindowsResult(BaseModel):
    windows: Annotated[list[WindowRef], Field(max_length=64)]
    """De arriba abajo (`stack` 0 = la de encima). Los títulos van en el sobre: `[window_id] app_id — título`."""
    monitors: list[MonitorInfo]
    front_window_id: WindowId | None = None
    envelope: UntrustedEnvelope


# ── herramientas: manos (dominio `hands`) ───────────────────────────────────
Button = Literal["left", "right", "middle"]
_Text80 = Annotated[str, Field(min_length=1, max_length=80)]


class _Step(ContractModel):
    pass


class StepClickText(_Step):
    do: Literal["click_text"]
    text: _Text80
    near: _Text80 | None = None
    button: Button = "left"
    double: bool = False


class StepClick(_Step):
    do: Literal["click"]
    id: Annotated[int, Field(ge=1)]
    button: Button = "left"
    double: bool = False


class StepClickAt(_Step):
    """Último recurso: px de la captura `shot_id` del acto."""

    do: Literal["click_at"]
    x: Annotated[float, Field(ge=0)]
    y: Annotated[float, Field(ge=0)]
    button: Button = "left"
    double: bool = False


class StepFill(_Step):
    do: Literal["fill"]
    field: _Text80 | None = None
    id: Annotated[int, Field(ge=1)] | None = None
    text: Annotated[str, Field(max_length=2000)]

    @model_validator(mode="after")
    def _where(self) -> StepFill:
        if (self.field is None) == (self.id is None):
            raise ValueError("fill needs exactly one of field or id")
        return self


class StepChoose(_Step):
    do: Literal["choose"]
    field: _Text80 | None = None
    id: Annotated[int, Field(ge=1)] | None = None
    option: Annotated[str, Field(min_length=1, max_length=120)]

    @model_validator(mode="after")
    def _where(self) -> StepChoose:
        if (self.field is None) == (self.id is None):
            raise ValueError("choose needs exactly one of field or id")
        return self


class StepType(_Step):
    """Escribe en el campo con el foco; falla si el foco no está en un campo editable."""

    do: Literal["type"]
    text: Annotated[str, Field(min_length=1, max_length=2000)]


class StepKey(_Step):
    do: Literal["key"]
    combo: Annotated[str, Field(pattern=r"^([a-z]+\+){0,3}[A-Za-z0-9_]{1,16}$")]
    """`ctrl+s`, `Return`, `shift+Tab`… Modificadores: ctrl, shift, alt, super."""
    repeat: Annotated[int, Field(ge=1, le=20)] = 1


class StepScroll(_Step):
    do: Literal["scroll"]
    direction: Literal["up", "down", "left", "right"] = "down"
    amount: Annotated[int, Field(ge=1, le=20)] = 3
    to_end: bool = False
    id: Annotated[int, Field(ge=1)] | None = None


class StepHover(_Step):
    do: Literal["hover"]
    text: _Text80 | None = None
    id: Annotated[int, Field(ge=1)] | None = None

    @model_validator(mode="after")
    def _where(self) -> StepHover:
        if (self.text is None) == (self.id is None):
            raise ValueError("hover needs exactly one of text or id")
        return self


class StepFocus(_Step):
    do: Literal["focus"]
    id: Annotated[int, Field(ge=1)]


class StepSet(_Step):
    """Valor de un control (deslizador, interruptor, casilla) por AT-SPI."""

    do: Literal["set"]
    id: Annotated[int, Field(ge=1)]
    value: bool | float | Annotated[str, Field(max_length=120)]


class StepWait(_Step):
    do: Literal["wait"]
    ms: Annotated[int, Field(ge=100, le=5000)] = 1000
    until_text: _Text80 | None = None


HandsStep = Annotated[
    StepClickText | StepClick | StepClickAt | StepFill | StepChoose | StepType | StepKey | StepScroll
    | StepHover | StepFocus | StepSet | StepWait,
    Field(discriminator="do"),
]


class ActInAppArgs(ContractModel):
    window_id: Annotated[WindowId, Field(description=(
        "Ventana donde se actúa: su id sale de list_windows o de read_window. Obligatorio: la confirmación "
        "nombra esa app y su título, y la aprobación solo vale para ella."))]
    steps: Annotated[list[HandsStep], Field(min_length=1, max_length=40)]
    read_id: Id | None = None
    """Lectura (`read_window`) a la que se refieren los `id` de los pasos."""
    shot_id: Id | None = None
    """Captura (`look_screen`) a la que se refieren los `click_at`."""
    confirm: bool = False
    """Pide la confirmación del usuario para este plan (obligatorio si algún paso es arriesgado)."""


class StepOutcome(BaseModel):
    index: Annotated[int, Field(ge=0, le=39)]
    do: Annotated[str, Field(max_length=16)]
    status: Literal["ok", "failed", "refused", "skipped"]
    code: Annotated[str, Field(max_length=40)] | None = None
    message: Annotated[str, Field(max_length=200)] | None = None


class ActInAppResult(BaseModel):
    act_id: Id
    status: Literal["done", "stopped", "failed"]
    steps: list[StepOutcome]
    window: WindowRef | None = None
    read_id: Id | None = None
    """Lectura nueva de la ventana tras los pasos (no hace falta otro `read_window`)."""
    envelope: UntrustedEnvelope | None = None


class OpenTargetArgs(ContractModel):
    url: Annotated[str, Field(max_length=2000)] | None = None
    """`http`, `https` o `mailto`. Sin credenciales, sin red local."""
    app_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}(\.desktop)?$")] | None = None
    location_id: Id | None = None
    relative_path: Annotated[str, Field(min_length=1, max_length=1024)] | None = None
    confirm: bool = False

    @model_validator(mode="after")
    def _one(self) -> OpenTargetArgs:
        kinds = (self.url is not None) + (self.app_id is not None) + (self.location_id is not None)
        if kinds != 1 or (self.location_id is None) != (self.relative_path is None):
            raise ValueError("give exactly one of url, app_id or location_id+relative_path")
        return self


class OpenTargetResult(BaseModel):
    opened: bool
    kind: Literal["url", "app", "file"]
    display: Annotated[str, Field(max_length=120)]


# ── herramienta: activar el modo flotante (dominio `ui`) ────────────────────
class SetFloatingArgs(ContractModel):
    on: bool | None = None
    size: AvatarSize | None = None
    pin: AvatarPin | None = None

    @model_validator(mode="after")
    def _something(self) -> SetFloatingArgs:
        if self.on is None and self.size is None and self.pin is None:
            raise ValueError("indica on, size o pin")
        return self


class SetFloatingResult(BaseModel):
    delivered: bool
    available: bool
    """La extensión de GNOME está lista (según la última presencia de Electron)."""
    active: bool
    """Estado conocido antes de esta petición."""
    note: Annotated[str, Field(max_length=200)]


# ── catálogo de errores de herramienta (ToolError.code) ─────────────────────
FLOATING_TOOL_ERRORS: Final[dict[str, str]] = {
    "floating_inactive": "El modo flotante no está activo.",
    "floating_unavailable": "Falta la extensión de GNOME drakter-companion o no responde.",
    "overlay_unavailable": "La ventana flotante no confirmó el dibujo en 15 s.",
    "companion_unavailable": "La extensión de GNOME no responde.",
    "draw_invalid": "El dibujo no pasa checkDraw: el mensaje lista los problemas.",
    "draw_action_forbidden": "Marcas type, copy, open o handoff: en Drakter se hacen con act_in_app/open_target.",
    "part_not_found": "edit nombra una parte que ya no está en pantalla.",
    "guide_busy": "Ya hay una guía en curso en este turno.",
    "guide_not_found": "No existe esa guía o ya terminó.",
    "interrupted": "El usuario cortó (voz, Esc o borrar dibujo).",
    "stale_screenshot": "La captura ya no vale: la ventana cambió o es de otro turno.",
    "stale_read": "La lectura ya no vale: la ventana cambió o es de otro turno.",
    "shot_not_found": "No existe esa captura en este turno.",
    "capture_failed": "La extensión no pudo capturar.",
    "secret_window": "Hay una ventana con un archivo sensible a la vista (.env, claves…): no se captura.",
    "window_not_found": "Esa ventana ya no existe.",
    "accessibility_unavailable": "La app no expone árbol de accesibilidad.",
    "hands_disabled": "El usuario no ha activado las manos (ajuste floating_hands_enabled).",
    "hands_off_app": "App protegida (terminal, contraseñas, ajustes…): solo se puede señalar.",
    "drakter_window": "El objetivo es una ventana de Drakter.",
    "risky_step": "Paso arriesgado sin confirmación: repite con confirm=true.",
    "secret_field": "Campo de contraseña: las manos no escriben secretos.",
    "window_changed": "La ventana objetivo cambió o perdió el foco.",
    "step_failed": "Un paso falló; los siguientes no se ejecutaron.",
    "input_unavailable": "No hay inyector de entrada (Mutter RemoteDesktop).",
    "target_not_allowed": "URL, app o archivo no permitido.",
    "app_not_found": "No existe esa aplicación.",
    "ui_unavailable": "No se pudo avisar a la interfaz de escritorio.",
    "stale_window": "La ventana aprobada ya no existe o es de otra app: no se ejecuta.",
    "screen_disabled": "El usuario no ha activado la pantalla (ajuste floating_screen_enabled).",
    "job_lane_forbidden": "Una tarea en segundo plano no puede ver la pantalla ni usar las manos.",
}
