"""IPC backend ↔ helper de escritorio (`hands/helper/`) y ↔ OCR (`hands/ocr/`). docs/floating/CONTRACT.md §5.

Helper: proceso aparte con `/usr/bin/python3 -I` del sistema (gi: Atspi 2.0, Gio), lanzado y supervisado por el
backend, JSONL por stdin/stdout (una línea ≤ 1 MiB), stderr = log sin contenido de pantalla. Sobre `IpcMessage`
de `voice_ipc` (`cmd` backend→helper, `ok`/`err` respuesta con el mismo `id`, `evt` helper→backend). Es el ÚNICO
proceso del backend que habla con AT-SPI, con Mutter RemoteDesktop y (por D-Bus) con la extensión
drakter-companion. No toca la BD, no conoce Hermes y no decide permisos: ejecuta lo que el backend ya validó,
con una segunda barrera propia (HANDS_OFF, RISKY, ventanas de Drakter, campos secretos).

OCR: `~/.local/share/drakter/venvs/ocr/bin/python -I -m drakter_ocr`, un proceso por petición (se cierra al acabar,
por la RAM), petición JSON por stdin y respuesta JSON por stdout.
"""

from __future__ import annotations

from typing import Annotated, Final, Literal

from pydantic import BaseModel, Field

from .common import ContractModel
from .floating import HandsStep, LogicalRect, MonitorInfo, WindowId

MAX_HELPER_LINE_BYTES: Final = 1024 * 1024
HELPER_PROTOCOL: Final = 1

# ── tipos ────────────────────────────────────────────────────────────────────
class HelperWindow(BaseModel):
    """`ListWindows`/`GetActiveWindow` de la extensión, normalizado. `title` es dato no confiable."""

    window_id: WindowId
    app_id: str | None = None
    wm_class: str | None = None
    title: Annotated[str, Field(max_length=512)] = ""
    pid: int
    client: Literal["wayland", "x11"]
    frame: LogicalRect
    buffer: LogicalRect
    monitor: int
    stack: int
    focused: bool
    minimized: bool = False
    fullscreen: bool = False
    maximized: bool = False


class AtspiControl(BaseModel):
    """`rect` ya en px lógicos globales (`frame` de la extensión + extents WINDOW). `name`/`value`: no confiables."""

    id: Annotated[int, Field(ge=1)]
    role: str
    name: Annotated[str, Field(max_length=200)] = ""
    value: Annotated[str, Field(max_length=200)] | None = None
    rect: LogicalRect | None = None
    states: list[str] = []
    actions: list[str] = []
    editable: bool = False
    offscreen: bool = False
    secret: bool = False


# ── comandos (cmd) ───────────────────────────────────────────────────────────
class HHello(ContractModel):
    protocol: Literal[1] = 1
    drakter_pids: Annotated[list[int], Field(max_length=16)]
    """pids de Electron y del backend: sus ventanas nunca se accionan."""


class HHelloResult(BaseModel):
    protocol: int
    atspi: bool
    mutter_rd: bool
    companion: Literal["ok", "missing", "outdated", "denied"]
    companion_version: int | None = None
    session: Literal["wayland", "x11", "unknown"]


class HEmpty(ContractModel):
    pass


class HWindowsResult(BaseModel):
    windows: list[HelperWindow]
    monitors: list[MonitorInfo]
    front_window_id: WindowId | None = None


class HWindowRef(ContractModel):
    window_id: WindowId


class HScreenshot(ContractModel):
    """El helper elige su carpeta (`$XDG_RUNTIME_DIR/drakter/shots`, 0700) y la extensión escribe el PNG 0600."""

    window_id: WindowId | None = None
    area: LogicalRect | None = None
    monitor: int | None = None
    cursor: bool = False
    hide_floating: bool = True


class HScreenshotResult(BaseModel):
    path: str
    geometry: LogicalRect
    scale: Annotated[float, Field(gt=0)]
    """px de imagen por px lógico."""


class HPassthrough(ContractModel):
    """`ForcePassthrough` de la extensión: la ventana flotante deja pasar todos los clics mientras dure."""

    on: bool


class HAtspiRead(ContractModel):
    window_id: WindowId
    max_controls: Annotated[int, Field(ge=1, le=260)] = 260
    include_text: bool = True
    max_text: Annotated[int, Field(ge=0, le=5000)] = 5000


class HAtspiReadResult(BaseModel):
    controls: list[AtspiControl]
    text: Annotated[str, Field(max_length=5000)] = ""
    truncated: bool = False


class HAtspiFind(ContractModel):
    window_id: WindowId
    text: Annotated[str, Field(min_length=1, max_length=80)]
    role: str | None = None
    every: bool = False
    within: LogicalRect | None = None


class HAtspiFindResult(BaseModel):
    matches: Annotated[list[AtspiControl], Field(max_length=8)]


class HAct(ContractModel):
    """Plan ya validado por el backend. `click_at` llega convertido a px lógicos (`x`, `y` globales).

    `confirmed`: el usuario aprobó este paso (pipeline de confirmación). Solo vale en planes de un paso: el
    backend manda cada paso aprobado solo. Sin él, el helper rechaza los pasos RISKY por su cuenta
    (`risky_step`). Siempre rechaza HANDS_OFF, ventanas de Drakter y campos secretos.
    """

    act_id: str
    window_id: WindowId
    steps: Annotated[list[HandsStep], Field(min_length=1, max_length=40)]
    confirmed: bool = False
    controls: Annotated[list[AtspiControl], Field(max_length=260)] = []
    """Controles de la lectura `read_id`, para reemparejar los `id` (`liveControls`/`rematch` de Roamies)."""


class HStepResult(BaseModel):
    index: int
    status: Literal["ok", "failed", "refused", "skipped"]
    code: str | None = None
    bounds: LogicalRect | None = None


class HActResult(BaseModel):
    status: Literal["done", "stopped", "failed"]
    steps: list[HStepResult]


class HApp(BaseModel):
    app_id: str
    name: str


class HAppsResult(BaseModel):
    apps: list[HApp]


class HOpen(ContractModel):
    """El backend ya validó el destino. `path` es absoluto y salió del servicio de almacén (realpath)."""

    url: str | None = None
    app_id: str | None = None
    path: str | None = None


HELPER_CMDS: Final[dict[str, type[BaseModel]]] = {
    "hello": HHello,
    "windows.list": HEmpty,
    "windows.activate": HWindowRef,
    "screenshot": HScreenshot,
    "passthrough": HPassthrough,
    "atspi.read": HAtspiRead,
    "atspi.find": HAtspiFind,
    "act": HAct,
    "act.stop": HEmpty,
    "apps.list": HEmpty,
    "open": HOpen,
    "shutdown": HEmpty,
}
HELPER_RESULTS: Final[dict[str, type[BaseModel]]] = {
    "hello": HHelloResult,
    "windows.list": HWindowsResult,
    "screenshot": HScreenshotResult,
    "atspi.read": HAtspiReadResult,
    "atspi.find": HAtspiFindResult,
    "act": HActResult,
    "apps.list": HAppsResult,
}
HELPER_TIMEOUTS_S: Final[dict[str, float]] = {
    "hello": 5, "windows.list": 2, "windows.activate": 2, "screenshot": 5, "passthrough": 1,
    "atspi.read": 8, "atspi.find": 4, "act": 85, "act.stop": 2, "apps.list": 3, "open": 5, "shutdown": 2,
}


# ── eventos (evt) ────────────────────────────────────────────────────────────
class HEvtWindowsChanged(BaseModel):
    reason: Literal["created", "closed", "restacked", "geometry", "workspace", "monitors"]


class HEvtFocusChanged(BaseModel):
    window: HelperWindow | None = None


class HEvtProgress(BaseModel):
    """Progreso de `act`: solo posición, nunca lo tecleado."""

    act_id: str
    index: int
    state: Literal["start", "step", "done", "failed"]
    bounds: LogicalRect | None = None
    hover: bool = False


class HEvtCompanion(BaseModel):
    status: Literal["ok", "missing", "outdated", "denied"]


HELPER_EVTS: Final[dict[str, type[BaseModel]]] = {
    "windows.changed": HEvtWindowsChanged,
    "focus.changed": HEvtFocusChanged,
    "act.progress": HEvtProgress,
    "companion": HEvtCompanion,
}

HELPER_ERROR_CODES: Final = (
    "companion_unavailable", "accessibility_unavailable", "input_unavailable", "window_not_found",
    "window_changed", "hands_off_app", "drakter_window", "risky_step", "secret_field", "step_failed",
    "capture_failed", "rate_limited", "validation_error", "internal_error", "secret_window",
)


# ── OCR ──────────────────────────────────────────────────────────────────────
class OcrRequest(ContractModel):
    image: str
    """Ruta absoluta de un PNG del backend (0600)."""
    region: Annotated[list[int], Field(min_length=4, max_length=4)] | None = None
    """`[x, y, w, h]` en px de la imagen."""
    lang: Literal["latin"] = "latin"
    threads: Annotated[int, Field(ge=1, le=8)] = 4


class OcrBox(BaseModel):
    text: Annotated[str, Field(max_length=500)]
    rect: Annotated[list[int], Field(min_length=4, max_length=4)]
    """px de la imagen completa."""
    score: Annotated[float, Field(ge=0, le=1)]


class OcrResult(BaseModel):
    boxes: Annotated[list[OcrBox], Field(max_length=2000)]
    ms: int
    model: str
    error: str | None = None
