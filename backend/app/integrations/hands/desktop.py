"""Shared steps of the screen tools and the target resolver: windows, captures and their scale."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from drakter_contracts.floating import LogicalRect, WindowRef
from drakter_contracts.hands_ipc import HEmpty, HScreenshot, HScreenshotResult, HelperWindow, HWindowsResult

from app.integrations.hands.client import HandsClient, HandsError, drakter_pids
from app.integrations.hands.lists import hands_off_name, secret_app_name, secret_title, terminal_name

if TYPE_CHECKING:
    from PIL import Image

MAX_SIDE: Final = 1568
MAX_PNG_BYTES: Final = 256 * 1024
JPEG_QUALITY: Final = 85


def is_drakter(w: HelperWindow) -> bool:
    return w.pid in drakter_pids() or hands_off_name(w.app_id) == "Drakter"


def is_hands_off(w: HelperWindow) -> bool:
    return hands_off_name(w.app_id, w.wm_class) is not None


def is_secret_app(w: HelperWindow) -> bool:
    """Password manager, keyring, polkit or gnome-shell: never captured nor read (review I3)."""
    return secret_app_name(w.app_id, w.wm_class) is not None


def is_terminal(w: HelperWindow) -> bool:
    return terminal_name(w.app_id, w.wm_class) is not None


def _overlaps(a: LogicalRect, b: LogicalRect) -> bool:
    return a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h


def secret_app_in(wins: HWindowsResult, area: LogicalRect | None) -> bool:
    """A secret app among the visible windows inside `area` (None: anywhere on the screen)."""
    return any(is_secret_app(w) and (area is None or _overlaps(w.frame, area))
               for w in wins.windows if not w.minimized)


def monitor_rect(wins: HWindowsResult, index: int) -> LogicalRect | None:
    return next((m.geometry for m in wins.monitors if m.index == index), None)


# The last window list, so a confirmation summary (sync, no helper call) can name the window.
_known: dict[str, HelperWindow] = {}


def known_window(window_id: str | None) -> HelperWindow | None:
    return _known.get(str(window_id)) if window_id is not None else None


def window_ref(w: HelperWindow) -> WindowRef:
    return WindowRef(
        window_id=w.window_id, app_id=(w.app_id or w.wm_class or None) and (w.app_id or w.wm_class)[:255],
        pid=w.pid, client=w.client, frame=w.frame, monitor=w.monitor, focused=w.focused,
        fullscreen=w.fullscreen, hands_off=is_hands_off(w), drakter=is_drakter(w),
    )


def app_label(w: HelperWindow) -> str:
    return (w.app_id or w.wm_class or "la ventana")[:60]


async def list_windows(client: HandsClient) -> HWindowsResult:
    res = await client.call("windows.list", HEmpty())
    assert isinstance(res, HWindowsResult)
    _known.clear()
    _known.update({w.window_id: w for w in res.windows})
    return res


def front(wins: HWindowsResult) -> HelperWindow | None:
    """The active window that is not Drakter's (the helper already leaves the floating window out)."""
    by_id = {w.window_id: w for w in wins.windows}
    if wins.front_window_id and (w := by_id.get(wins.front_window_id)) and not is_drakter(w):
        return w
    for w in wins.windows:
        if not is_drakter(w) and not w.minimized:
            return w
    return None


def pick(wins: HWindowsResult, window_id: str | None) -> HelperWindow:
    if window_id is None:
        w = front(wins)
        if w is None:
            raise HandsError("window_not_found")
        return w
    for w in wins.windows:
        if w.window_id == window_id:
            return w
    raise HandsError("window_not_found")


def by_target(wins: HWindowsResult, target: str | None) -> HelperWindow | None:
    """`front` (default), `screen` (None), `window:<id>` or an app name (CONTRACT §9.2)."""
    t = (target or "front").strip()
    if t == "screen":
        return None
    if t == "front":
        return front(wins)
    if t.startswith("window:"):
        wid = t[7:]
        return next((w for w in wins.windows if w.window_id == wid), None)
    name = t.lower()
    for w in wins.windows:
        app = (w.app_id or w.wm_class or "").lower()
        if app == name or (name and name in app):
            return w
    for w in wins.windows:  # by title last: it is untrusted, but here it only picks where to point
        if name and name in (w.title or "").lower():
            return w
    return None


def secret_on_screen(wins: HWindowsResult) -> bool:
    return any(secret_title(w.title) for w in wins.windows if not w.minimized)


@dataclass(frozen=True, slots=True)
class Capture:
    path: Path
    geometry: LogicalRect
    scale: float  # image px per logical px


@contextlib.asynccontextmanager
async def captured(client: HandsClient, req: HScreenshot):  # type: ignore[no-untyped-def]
    """A PNG from the extension that is deleted on exit, whatever happens."""
    res = await client.call("screenshot", req)
    assert isinstance(res, HScreenshotResult)
    path = Path(res.path)
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    try:
        real = path.resolve(strict=True)
        if not runtime or not str(real).startswith(str(Path(runtime).resolve()) + "/"):
            raise HandsError("capture_failed", "capture outside the runtime directory")
        yield Capture(real, res.geometry, res.scale)
    finally:
        with contextlib.suppress(OSError):
            path.unlink()


@dataclass(frozen=True, slots=True)
class Encoded:
    data: bytes
    mime: str
    width: int
    height: int
    sha256: str
    covered: int = 0

    @property
    def b64(self) -> str:
        return base64.b64encode(self.data).decode("ascii")


def terminal_layers(wins: HWindowsResult, area: LogicalRect) -> list[tuple[LogicalRect, bool]]:
    """Visible windows over `area`, bottom to top (`stack` 0 is the top), each with "is a terminal"."""
    shown = [w for w in wins.windows if not w.minimized and _overlaps(w.frame, area)]
    return [(w.frame, is_terminal(w)) for w in sorted(shown, key=lambda w: w.stack, reverse=True)]


def cover_terminals(img: "Image.Image", geometry: LogicalRect, layers: list[tuple[LogicalRect, bool]]) -> int:
    """Paints opaque the visible part of every terminal in the capture (review N5). Returns how many.

    The layers are drawn bottom to top on a label mask, so a window above a terminal keeps its pixels.
    """
    from PIL import Image, ImageDraw

    if not any(term for _, term in layers):
        return 0
    sx, sy = img.width / geometry.w, img.height / geometry.h
    labels = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(labels)
    for i, (r, _) in enumerate(layers[-255:], start=1):
        box = (round((r.x - geometry.x) * sx), round((r.y - geometry.y) * sy),
               round((r.x + r.w - geometry.x) * sx) - 1, round((r.y + r.h - geometry.y) * sy) - 1)
        draw.rectangle(box, fill=i)
    terms = {i for i, (_, term) in enumerate(layers[-255:], start=1) if term}
    hist = labels.histogram()
    shown = {i for i in terms if hist[i]}
    if shown:
        img.paste((24, 24, 24), mask=labels.point([255 if v in shown else 0 for v in range(256)]))
    return len(shown)


def encode(path: Path, crop: tuple[int, int, int, int] | None = None,
           cover: tuple[LogicalRect, list[tuple[LogicalRect, bool]]] | None = None) -> Encoded:
    """Long side down to 1568 px; PNG, or JPEG q85 when the PNG passes 256 KB (Pillow).

    `cover` (capture geometry, `terminal_layers`): terminals painted opaque before anything else;
    how many goes in `Encoded.covered`.
    """
    from PIL import Image

    with Image.open(path) as im:
        im.load()
        img = im.convert("RGB")
    covered = cover_terminals(img, *cover) if cover is not None else 0
    if crop is not None:
        x, y, w, h = crop
        img = img.crop((max(0, x), max(0, y), min(img.width, x + w), min(img.height, y + h)))
    if max(img.size) > MAX_SIDE:
        k = MAX_SIDE / max(img.size)
        img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    mime = "image/png"
    if buf.tell() > MAX_PNG_BYTES:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True)
        mime = "image/jpeg"
    data = buf.getvalue()
    return Encoded(data, mime, img.width, img.height, hashlib.sha256(data).hexdigest(), covered)


def iter_lines(values: Iterator[str], limit: int) -> tuple[str, bool]:
    out, used, cut = [], 0, False
    for v in values:
        if used + len(v) + 1 > limit:
            cut = True
            break
        out.append(v)
        used += len(v) + 1
    return "\n".join(out), cut
