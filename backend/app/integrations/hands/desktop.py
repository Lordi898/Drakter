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
from typing import Final

from drakter_contracts.floating import LogicalRect, WindowRef
from drakter_contracts.hands_ipc import HEmpty, HScreenshot, HScreenshotResult, HelperWindow, HWindowsResult

from app.integrations.hands.client import HandsClient, HandsError, drakter_pids
from app.integrations.hands.lists import hands_off_name, secret_title

MAX_SIDE: Final = 1568
MAX_PNG_BYTES: Final = 256 * 1024
JPEG_QUALITY: Final = 85


def is_drakter(w: HelperWindow) -> bool:
    return w.pid in drakter_pids() or hands_off_name(w.app_id) == "Drakter"


def is_hands_off(w: HelperWindow) -> bool:
    return hands_off_name(w.app_id, w.wm_class) is not None


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

    @property
    def b64(self) -> str:
        return base64.b64encode(self.data).decode("ascii")


def encode(path: Path, crop: tuple[int, int, int, int] | None = None) -> Encoded:
    """Long side down to 1568 px; PNG, or JPEG q85 when the PNG passes 256 KB (Pillow)."""
    from PIL import Image

    with Image.open(path) as im:
        im.load()
        img = im.convert("RGB")
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
    return Encoded(data, mime, img.width, img.height, hashlib.sha256(data).hexdigest())


def iter_lines(values: Iterator[str], limit: int) -> tuple[str, bool]:
    out, used, cut = [], 0, False
    for v in values:
        if used + len(v) + 1 > limit:
            cut = True
            break
        out.append(v)
        used += len(v) + 1
    return "\n".join(out), cut
