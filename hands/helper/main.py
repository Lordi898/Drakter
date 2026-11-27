"""Drakter desktop helper (`/usr/bin/python3 -I hands/helper/main.py`), docs/floating/CONTRACT.md §5.

JSONL over stdin/stdout with the `IpcMessage` envelope of `drakter_contracts.voice_ipc`
(`{kind, id, type, payload}`); protocol and models in `drakter_contracts.hands_ipc`. stderr is a log
without screen content. One thread: `GLib.MainLoop` serves stdin, D-Bus signals and AT-SPI.

It is the only process of the backend that talks to AT-SPI, Mutter RemoteDesktop and the companion
extension. It does not decide permissions: it runs what the backend validated, behind its own barrier.
"""

from __future__ import annotations

import json
import os
import signal
import stat
import sys
import traceback
from collections import deque
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script's directory

import gi  # noqa: E402

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

import apps  # noqa: E402
import lists  # noqa: E402
import tree  # noqa: E402
from act import Hands, Refused, StepFailed  # noqa: E402
from companion import Companion, CompanionError, public_window  # noqa: E402
from inject import Injector  # noqa: E402

PROTOCOL = 1
MAX_LINE = 1024 * 1024


def log(msg: str) -> None:
    print(f"hands: {msg}", file=sys.stderr, flush=True)


def write(obj: dict[str, Any]) -> None:
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    if len(line.encode("utf-8")) > MAX_LINE:
        obj = {"kind": "err", "id": obj.get("id", ""), "type": obj.get("type", ""),
               "payload": {"code": "internal_error", "message": "result too large"}}
        line = json.dumps(obj)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def emit(evt: str, payload: dict[str, Any]) -> None:
    write({"kind": "evt", "id": "", "type": evt, "payload": payload})


class HelperError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.message = message or code


def shots_dir() -> str:
    """`$XDG_RUNTIME_DIR/drakter/shots`, 0700 all the way, no symlinks (the extension checks it too)."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        raise HelperError("capture_failed", "no XDG_RUNTIME_DIR")
    path = runtime
    for part in ("drakter", "shots"):
        path = os.path.join(path, part)
        try:
            os.mkdir(path, 0o700)
        except FileExistsError:
            pass
        st = os.lstat(path)
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
            raise HelperError("capture_failed", "unsafe shots directory")
        if st.st_mode & 0o077:
            os.chmod(path, 0o700)
    return path


class Helper:
    def __init__(self) -> None:
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.companion = Companion(self.bus)
        self.mutter_rd = Injector.available(self.bus)
        injector = Injector(self.bus, self._pointer) if self.mutter_rd else None
        self.hands = Hands(self.companion, injector, emit)
        self.loop = GLib.MainLoop()
        self.queue: deque[dict[str, Any]] = deque()
        self.buf = b""
        self.helloed = False
        self.last_status = None
        self.watch_id = Gio.bus_watch_name_on_connection(
            self.bus, "org.drakter.Companion", Gio.BusNameWatcherFlags.NONE, self._appeared, self._vanished)

    def _pointer(self) -> tuple[int, int]:
        return self.companion.pointer()

    # ── companion lifecycle ──────────────────────────────────────────────────
    def _appeared(self, *_a) -> None:
        if self.helloed:
            self.companion.hello()
            self.companion.subscribe(self._on_change)
            self._report()

    def _vanished(self, *_a) -> None:
        self.companion.status = "missing"
        if self.helloed:
            self._report()

    def _report(self) -> None:
        if self.companion.status != self.last_status:
            self.last_status = self.companion.status
            emit("companion", {"status": self.companion.status})

    def _on_change(self, kind: str, data: Any) -> None:
        if kind == "focus":
            w = data if data and not data.get("_floating") else None
            emit("focus.changed", {"window": public_window(w) if w else None})
        elif kind == "windows" and data in ("created", "closed", "restacked", "geometry", "workspace", "monitors"):
            emit("windows.changed", {"reason": data})

    # ── stdin ────────────────────────────────────────────────────────────────
    def on_stdin(self, fd: int, cond: GLib.IOCondition) -> bool:
        if cond & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
            chunk = b""
        else:
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                return True
        if not chunk:
            self.loop.quit()
            return False
        self.buf += chunk
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            if len(line) > MAX_LINE:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if not isinstance(msg, dict) or msg.get("kind") != "cmd":
                continue
            if msg.get("type") == "act.stop":  # served at once, also in the middle of an act
                self.hands.stop_requested = True
                write({"kind": "ok", "id": msg.get("id", ""), "type": "act.stop", "payload": {}})
                continue
            self.queue.append(msg)
        if len(self.buf) > MAX_LINE:
            self.buf = b""
        if not self.hands.busy:
            GLib.idle_add(self.drain)
        return True

    def drain(self) -> bool:
        while self.queue and not self.hands.busy:
            msg = self.queue.popleft()
            self.hands.busy = True
            try:
                self.handle(msg)
            finally:
                self.hands.busy = False
        return False

    def handle(self, msg: dict[str, Any]) -> None:
        mid, typ = str(msg.get("id", "")), str(msg.get("type", ""))
        payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
        try:
            if typ != "hello" and not self.helloed:
                raise HelperError("validation_error", "hello first")
            fn = getattr(self, "cmd_" + typ.replace(".", "_"), None)
            if fn is None:
                raise HelperError("validation_error", "unknown command")
            result = fn(payload)
            write({"kind": "ok", "id": mid, "type": typ, "payload": result or {}})
        except (HelperError, CompanionError, Refused, StepFailed, tree.TreeError, apps.OpenError) as e:
            write({"kind": "err", "id": mid, "type": typ,
                   "payload": {"code": e.code, "message": getattr(e, "message", e.code)}})
        except (KeyError, TypeError, ValueError) as e:
            write({"kind": "err", "id": mid, "type": typ,
                   "payload": {"code": "validation_error", "message": type(e).__name__}})
        except Exception as e:  # noqa: BLE001 - one bad command must not kill the helper
            # Only where it failed, never a traceback: a repr of an AT-SPI name is screen content (review M2).
            frames = traceback.extract_tb(e.__traceback__)
            where = f" at {os.path.basename(frames[-1].filename)}:{frames[-1].lineno}" if frames else ""
            log(f"{typ} failed: {type(e).__name__}{where}")
            write({"kind": "err", "id": mid, "type": typ,
                   "payload": {"code": "internal_error", "message": type(e).__name__}})
        if self.companion.status in ("missing", "denied") and self.helloed:
            self._report()
        if typ == "shutdown":
            self.loop.quit()

    # ── commands ─────────────────────────────────────────────────────────────
    def cmd_hello(self, p: dict[str, Any]) -> dict[str, Any]:
        self.hands.drakter_pids = {int(x) for x in p.get("drakter_pids", [])[:16]}
        self.companion.hello()
        if self.companion.usable:
            self.companion.subscribe(self._on_change)
        self.helloed = True
        self.last_status = self.companion.status
        session = os.environ.get("XDG_SESSION_TYPE", "")
        return {
            "protocol": PROTOCOL,
            "atspi": tree.available(),
            "mutter_rd": self.mutter_rd,
            "companion": self.companion.status,
            "companion_version": self.companion.version,
            "session": session if session in ("wayland", "x11") else "unknown",
        }

    def _visible(self) -> list[dict[str, Any]]:
        return [w for w in self.companion.list_windows() if not w.get("_floating")]

    def cmd_windows_list(self, _p: dict[str, Any]) -> dict[str, Any]:
        wins = self._visible()
        front = None
        for w in wins:
            if w["focused"] and int(w["pid"]) not in self.hands.drakter_pids:
                front = w["window_id"]
                break
        if front is None:
            for w in wins:
                if int(w["pid"]) not in self.hands.drakter_pids and not w.get("minimized"):
                    front = w["window_id"]
                    break
        return {"windows": [public_window(w) for w in wins][:64], "monitors": self.companion.monitors(),
                "front_window_id": front}

    def _window(self, window_id: str) -> dict[str, Any]:
        w = self.hands.window_by_id(str(window_id))
        if w is None or w.get("_floating"):
            raise HelperError("window_not_found")
        return w

    def cmd_windows_activate(self, p: dict[str, Any]) -> dict[str, Any]:
        w = self._window(p["window_id"])
        if (code := self.hands.refusal_for(w)) is not None:
            raise HelperError(code)
        if self.companion.activate(w["window_id"]) is False:
            raise HelperError("window_not_found")
        return {}

    def _secret_app(self, w: dict[str, Any]) -> bool:
        return lists.secret_app_name(*self.hands.ids_of(w)) is not None

    def _refuse_secret_in(self, area: dict[str, int] | None) -> None:
        """Password managers, the keyring, polkit and gnome-shell are never captured (review I3)."""
        for w in self._visible():
            if w.get("minimized") or not self._secret_app(w):
                continue
            f = w["frame"]
            if area is None or (f["x"] < area["x"] + area["w"] and area["x"] < f["x"] + f["w"]
                                and f["y"] < area["y"] + area["h"] and area["y"] < f["y"] + f["h"]):
                raise HelperError("secret_window")

    def _monitor_area(self, index: int) -> dict[str, int] | None:
        for m in self.companion.monitors():
            if int(m.get("index", -1)) == index:
                return m["geometry"]
        return None

    def cmd_screenshot(self, p: dict[str, Any]) -> dict[str, Any]:
        opts: dict[str, Any] = {"dir": shots_dir(), "cursor": bool(p.get("cursor", False)),
                                "hide_floating": bool(p.get("hide_floating", True))}
        if p.get("window_id") is not None:
            w = self._window(p["window_id"])
            if self._secret_app(w):
                raise HelperError("secret_window")
            if "window" in self.companion.capabilities or (self.companion.version or 0) >= 2:
                opts["window_id"] = w["window_id"]
            else:
                opts["area"] = w["frame"]  # v1 prototype: the window's frame as an area
        elif p.get("area") is not None:
            a = p["area"]
            opts["area"] = {k: int(a[k]) for k in ("x", "y", "w", "h")}
            self._refuse_secret_in(opts["area"])
        elif p.get("monitor") is not None:
            opts["monitor"] = int(p["monitor"])
            self._refuse_secret_in(self._monitor_area(opts["monitor"]))
        else:
            self._refuse_secret_in(None)
        try:
            path, geo, scale = self.companion.screenshot(opts)
        except CompanionError as e:
            if e.code in ("rate_limited", "window_not_found", "companion_unavailable"):
                raise
            raise HelperError("capture_failed") from None
        return {"path": path, "geometry": geo, "scale": scale}

    def cmd_passthrough(self, p: dict[str, Any]) -> dict[str, Any]:
        self.companion.passthrough(bool(p.get("on")))
        return {}

    def cmd_atspi_read(self, p: dict[str, Any]) -> dict[str, Any]:
        w = self._window(p["window_id"])
        ids = self.hands.ids_of(w)
        if lists.secret_app_name(*ids) is not None or lists.terminal_name(*ids) is not None:
            raise HelperError("secret_window")  # review I3: never read secrets or terminals
        return tree.read(w, min(int(p.get("max_controls", 260)), 260), bool(p.get("include_text", True)),
                         min(int(p.get("max_text", 5000)), 5000))

    def cmd_atspi_find(self, p: dict[str, Any]) -> dict[str, Any]:
        w = self._window(p["window_id"])
        within = p.get("within")
        return {"matches": tree.find(w, str(p["text"])[:80], p.get("role"), bool(p.get("every")), within)}

    def cmd_act(self, p: dict[str, Any]) -> dict[str, Any]:
        # Without Mutter RD, semantic AT-SPI actions still run; steps that need real input fail.
        return self.hands.act(p)

    def cmd_apps_list(self, _p: dict[str, Any]) -> dict[str, Any]:
        return {"apps": apps.list_apps()}

    def cmd_open(self, p: dict[str, Any]) -> dict[str, Any]:
        apps.open_target(p.get("url"), p.get("app_id"), p.get("path"))
        return {}

    def cmd_shutdown(self, _p: dict[str, Any]) -> dict[str, Any]:
        return {}

    def run(self) -> None:
        os.set_blocking(0, False)
        GLib.io_add_watch(0, GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN | GLib.IOCondition.HUP | GLib.IOCondition.ERR,
                          self.on_stdin)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda *_: (self.loop.quit(), False)[1])
        self.loop.run()
        self.companion.passthrough(False)


def main() -> int:
    try:
        Helper().run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
