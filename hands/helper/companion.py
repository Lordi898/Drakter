"""Client of the drakter-companion GNOME extension (docs/floating/CONTRACT.md §3), from the helper.

Everything runs on the helper's only thread. The connection is the session bus singleton, the same one
Mutter RemoteDesktop uses: both need one connection for the whole session.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from gi.repository import Gio, GLib

BUS_NAME = "org.drakter.Companion"
OBJ = "/org/drakter/Companion"
IFACE = "org.drakter.Companion1"
MIN_VERSION = 2
_TIMEOUT_MS = 4000


class CompanionError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.message = message or code


def _rect(v: Any) -> dict[str, int]:
    x, y, w, h = (int(n) for n in v)
    return {"x": x, "y": y, "w": max(0, w), "h": max(0, h)}


def norm_window(d: dict[str, Any]) -> dict[str, Any] | None:
    """Extension window dict → `HelperWindow` (+ private keys starting with `_`)."""
    if not d or "id" not in d:
        return None
    ids = [str(d.get(k) or "") for k in ("app_id", "gtk_app_id", "sandboxed_app_id", "wm_class", "wm_class_instance")]
    ids = [i[: -len(".desktop")] if i.endswith(".desktop") else i for i in ids if i]
    # The shell names apps without a .desktop file "window:N": the toolkit's own id says more.
    app_id = next((i for i in ids[:3] if not i.startswith("window:")), None)
    return {
        "window_id": str(int(d["id"])),
        "app_id": app_id or None,
        "wm_class": d.get("wm_class") or None,
        "title": str(d.get("title") or "")[:512],
        "pid": max(0, int(d.get("pid", 0))),
        "client": "x11" if d.get("client") == "x11" else "wayland",
        "frame": _rect(d.get("frame", (0, 0, 0, 0))),
        "buffer": _rect(d.get("buffer", (0, 0, 0, 0))),
        "monitor": max(0, int(d.get("monitor", 0))),
        "stack": int(d.get("stack", 0)),
        "focused": bool(d.get("focused", False)),
        "minimized": bool(d.get("minimized", False)),
        "fullscreen": bool(d.get("fullscreen", False)),
        "maximized": bool(d.get("maximized", False)),
        "_floating": bool(d.get("floating", False)),
        "_type": str(d.get("type") or ""),
        "_ids": ids,
    }


def public_window(w: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in w.items() if not k.startswith("_")}


def norm_monitor(d: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": max(0, int(d.get("index", 0))),
        "geometry": _rect(d.get("geometry", (0, 0, 0, 0))),
        "workarea": _rect(d.get("workarea", d.get("geometry", (0, 0, 0, 0)))),
        "scale": min(4.0, max(0.01, float(d.get("scale", 1.0)))),
        "primary": bool(d.get("primary", False)),
    }


class Companion:
    def __init__(self, bus: Gio.DBusConnection) -> None:
        self.bus = bus
        self.status = "missing"  # ok | missing | outdated | denied
        self.version: int | None = None
        self.capabilities: set[str] = set()
        self._subs: list[int] = []
        self._on_change: Callable[[str, Any], None] | None = None

    # ── low level ────────────────────────────────────────────────────────────
    def _call(self, method: str, args: GLib.Variant | None = None, rtype: str | None = None) -> Any:
        try:
            res = self.bus.call_sync(
                BUS_NAME, OBJ, IFACE, method, args,
                GLib.VariantType.new(rtype) if rtype else None,
                Gio.DBusCallFlags.NONE, _TIMEOUT_MS, None,
            )
        except GLib.Error as e:
            remote = Gio.DBusError.get_remote_error(e) or ""
            if remote.endswith(".AccessDenied"):
                self.status = "denied"
                raise CompanionError("companion_unavailable", "access denied") from None
            if remote.endswith(".RateLimited"):
                raise CompanionError("rate_limited") from None
            if remote.endswith(".NotFound"):
                raise CompanionError("window_not_found") from None
            if remote.endswith("UnknownMethod"):
                raise CompanionError("unknown_method", method) from None
            if remote.endswith(("ServiceUnknown", "NameHasNoOwner", "NoReply")) or "ServiceUnknown" in str(e):
                self.status = "missing"
                raise CompanionError("companion_unavailable", "extension missing") from None
            raise CompanionError("internal_error", remote or "dbus error") from None
        return res.unpack() if res is not None else ()

    def hello(self) -> str:
        """Authenticates this connection. Returns the status (`ok`, `missing`, `outdated`, `denied`)."""
        runtime = os.environ.get("XDG_RUNTIME_DIR", "")
        token_path = os.path.join(runtime, "drakter-companion", "token")
        try:
            ver = self.bus.call_sync(
                BUS_NAME, OBJ, "org.freedesktop.DBus.Properties", "Get",
                GLib.Variant("(ss)", (IFACE, "Version")), None, Gio.DBusCallFlags.NONE, _TIMEOUT_MS, None,
            ).unpack()[0]
            self.version = int(ver)
        except GLib.Error:
            self.status = "missing"
            return self.status
        try:
            st = os.stat(token_path)
            if st.st_uid != os.getuid() or st.st_mode & 0o077:
                self.status = "denied"
                return self.status
            with open(token_path, encoding="utf-8") as fh:
                token = fh.read().strip()
        except OSError:
            self.status = "missing"
            return self.status
        try:
            info = self._call("Hello", GLib.Variant("(s)", (token,)), "(a{sv})")[0]
        except CompanionError:
            if self.status != "denied":
                self.status = "missing"
            return self.status
        self.capabilities = set(info.get("capabilities", []))
        # v1 (the spike prototype) still works for the hands, with fallbacks; it is reported as outdated.
        self.status = "ok" if (self.version or 0) >= MIN_VERSION else "outdated"
        return self.status

    @property
    def usable(self) -> bool:
        return self.status in ("ok", "outdated")

    def require(self) -> None:
        if not self.usable:
            raise CompanionError("companion_unavailable", f"companion {self.status}")

    # ── API ──────────────────────────────────────────────────────────────────
    def list_windows(self) -> list[dict[str, Any]]:
        self.require()
        raw = self._call("ListWindows", None, "(aa{sv})")[0]
        out = []
        for i, d in enumerate(raw):
            w = norm_window(d)
            if w is not None:
                w["stack"] = i if w["stack"] < 0 else w["stack"]
                out.append(w)
        return out

    def active_window(self) -> dict[str, Any] | None:
        self.require()
        return norm_window(self._call("GetActiveWindow", None, "(a{sv})")[0])

    def monitors(self) -> list[dict[str, Any]]:
        self.require()
        return [norm_monitor(m) for m in self._call("GetMonitors", None, "(aa{sv})")[0]]

    def pointer(self) -> tuple[int, int]:
        self.require()
        x, y, _mods, _t = self._call("GetPointer", None, "(iiux)")
        return int(x), int(y)

    def screenshot(self, opts: dict[str, Any]) -> tuple[str, dict[str, int], float]:
        self.require()
        v: dict[str, GLib.Variant] = {"dir": GLib.Variant("s", opts["dir"])}
        if opts.get("window_id") is not None:
            v["window"] = GLib.Variant("t", int(opts["window_id"]))
        if opts.get("area") is not None:
            a = opts["area"]
            v["area"] = GLib.Variant("(iiii)", (a["x"], a["y"], a["w"], a["h"]))
        if opts.get("monitor") is not None:
            v["monitor"] = GLib.Variant("i", int(opts["monitor"]))
        v["cursor"] = GLib.Variant("b", bool(opts.get("cursor", False)))
        v["hide_floating"] = GLib.Variant("b", bool(opts.get("hide_floating", True)))
        path, geo, scale = self._call("Screenshot", GLib.Variant("(a{sv})", (v,)), "(s(iiii)d)")
        return str(path), _rect(geo), float(scale)

    def activate(self, window_id: str) -> bool | None:
        """`ActivateWindow` (v2). None when the extension is the v1 prototype (no such method)."""
        self.require()
        try:
            return bool(self._call("ActivateWindow", GLib.Variant("(t)", (int(window_id),)), "(b)")[0])
        except CompanionError as e:
            if e.code == "unknown_method":
                return None
            raise

    def passthrough(self, on: bool) -> bool:
        """`ForcePassthrough` (v2). False when the method does not exist (v1 prototype)."""
        if not self.usable:
            return False
        try:
            self._call("ForcePassthrough", GLib.Variant("(b)", (bool(on),)), None)
            return True
        except CompanionError:
            return False

    # ── signals ──────────────────────────────────────────────────────────────
    def subscribe(self, on_change: Callable[[str, Any], None]) -> None:
        """`windows b` subscription: FocusChanged / WindowsChanged → on_change(kind, data)."""
        self._on_change = on_change
        for name in ("FocusChanged", "WindowsChanged"):
            self._subs.append(self.bus.signal_subscribe(
                BUS_NAME, IFACE, name, OBJ, None, Gio.DBusSignalFlags.NONE, self._signal, None))
        if self.usable:
            try:
                self._call("Subscribe", GLib.Variant("(a{sv})", ({"windows": GLib.Variant("b", True)},)), None)
            except CompanionError:
                pass

    def _signal(self, _conn, _sender, _path, _iface, name, params, _data) -> None:
        if self._on_change is None:
            return
        try:
            if name == "FocusChanged":
                self._on_change("focus", norm_window(params.unpack()[0]))
            elif name == "WindowsChanged":
                self._on_change("windows", str(params.unpack()[0]))
        except Exception:  # noqa: BLE001 - a malformed signal must not stop the helper
            pass
