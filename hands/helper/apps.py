"""List installed apps and open a URL, an app or a file with a clean launch environment (spike 03 §4)."""

from __future__ import annotations

import os

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from lists import hands_off_name  # noqa: E402

# Variables that a snap (VS Code) leaks and that crash or mislocalise GTK apps (spike 03 §1.4.1).
BAD_ENV = ("GTK_PATH", "GTK_EXE_PREFIX", "LOCPATH", "GIO_MODULE_DIR", "GSETTINGS_SCHEMA_DIR",
           "GDK_PIXBUF_MODULE_FILE", "GDK_PIXBUF_MODULEDIR", "GTK_IM_MODULE_FILE", "LD_LIBRARY_PATH",
           "LD_PRELOAD", "PYTHONPATH", "PYTHONHOME", "SNAP", "SNAP_NAME", "SNAP_INSTANCE_NAME", "SNAP_REVISION",
           "SNAP_LIBRARY_PATH", "SNAP_DATA", "SNAP_USER_DATA", "SNAP_COMMON", "SNAP_USER_COMMON",
           "VIRTUAL_ENV", "ELECTRON_RUN_AS_NODE", "DRAKTER_HANDS_ENV")
XDG_DATA_DIRS = "/usr/share/ubuntu:/usr/share/gnome:/usr/local/share/:/usr/share/:/var/lib/snapd/desktop"


class OpenError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def launch_context() -> Gio.AppLaunchContext:
    ctx = Gio.AppLaunchContext()
    for k in BAD_ENV:
        ctx.unsetenv(k)
    for k in list(os.environ):
        if k.startswith("SNAP_") or k.startswith("DRAKTER_"):
            ctx.unsetenv(k)
    ctx.setenv("XDG_DATA_DIRS", XDG_DATA_DIRS)
    ctx.setenv("GNOME_ACCESSIBILITY", "1")
    ctx.setenv("ACCESSIBILITY_ENABLED", "1")
    return ctx


def _app_id(info) -> str:
    i = info.get_id() or ""
    return i[: -len(".desktop")] if i.endswith(".desktop") else i


def list_apps() -> list[dict[str, str]]:
    out = []
    for a in Gio.AppInfo.get_all():
        try:
            if not a.should_show():
                continue
            aid = _app_id(a)
            if aid and not hands_off_name(aid):
                out.append({"app_id": aid, "name": (a.get_display_name() or aid)[:120]})
        except Exception:  # noqa: BLE001
            continue
    out.sort(key=lambda d: d["name"].lower())
    return out


def open_target(url: str | None, app_id: str | None, path: str | None) -> None:
    ctx = launch_context()
    try:
        if url is not None:
            if not url.lower().startswith(("http://", "https://", "mailto:")):
                raise OpenError("target_not_allowed")
            Gio.AppInfo.launch_default_for_uri(url, ctx)
        elif app_id is not None:
            if hands_off_name(app_id):
                raise OpenError("target_not_allowed")
            try:
                info = Gio.DesktopAppInfo.new(app_id if app_id.endswith(".desktop") else app_id + ".desktop")
            except TypeError:
                info = None
            if info is None:
                raise OpenError("app_not_found")
            if not info.launch([], ctx):
                raise OpenError("internal_error")
        elif path is not None:
            if not os.path.isabs(path) or not os.path.exists(path):
                raise OpenError("not_found")
            Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(path).get_uri(), ctx)
        else:
            raise OpenError("validation_error")
    except GLib.Error:
        raise OpenError("internal_error") from None
