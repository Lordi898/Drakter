"""Real pointer and keyboard input through `org.gnome.Mutter.RemoteDesktop` (spike 03 §2.1).

No root and no dialog. Every call goes through the connection that created the session. Absolute motion
needs a consumed ScreenCast stream, so the pointer moves in relative steps, checked against the extension's
`GetPointer`, and goes back to where the user had it.
"""

from __future__ import annotations

import time
from typing import Callable

from gi.repository import Gio, GLib

RD = "org.gnome.Mutter.RemoteDesktop"
RD_PATH = "/org/gnome/Mutter/RemoteDesktop"
SESSION = RD + ".Session"
BTN = {"left": 0x110, "right": 0x111, "middle": 0x112}

# X keysyms (keysymdef.h) for the named keys a `key` step may use.
NAMED = {
    "return": 0xFF0D, "enter": 0xFF0D, "kp_enter": 0xFF8D, "tab": 0xFF09, "escape": 0xFF1B, "esc": 0xFF1B,
    "backspace": 0xFF08, "delete": 0xFFFF, "kp_delete": 0xFF9F, "insert": 0xFF63, "home": 0xFF50,
    "end": 0xFF57, "left": 0xFF51, "up": 0xFF52, "right": 0xFF53, "down": 0xFF54, "page_up": 0xFF55,
    "pageup": 0xFF55, "prior": 0xFF55, "page_down": 0xFF56, "pagedown": 0xFF56, "next": 0xFF56,
    "space": 0x20, "menu": 0xFF67, "print": 0xFF61,
    **{f"f{i}": 0xFFBE + i - 1 for i in range(1, 13)},
}
MODS = {"ctrl": 0xFFE3, "shift": 0xFFE1, "alt": 0xFFE9, "super": 0xFFEB}


def char_keysym(ch: str) -> int:
    o = ord(ch)
    if ch == "\n":
        return 0xFF0D
    if ch == "\t":
        return 0xFF09
    if 0x20 <= o <= 0x7E or 0xA0 <= o <= 0xFF:
        return o
    return 0x01000000 + o


def key_keysym(key: str) -> int | None:
    k = key.lower()
    if k in NAMED:
        return NAMED[k]
    if len(key) == 1:
        return char_keysym(key.lower() if key.isalpha() else key)
    return None


class InputError(Exception):
    pass


class Injector:
    def __init__(self, bus: Gio.DBusConnection, pointer: Callable[[], tuple[int, int]] | None) -> None:
        self.bus = bus
        self._pointer = pointer
        self._path: str | None = None

    def _call(self, path: str, iface: str, method: str, args: GLib.Variant | None = None):
        try:
            return self.bus.call_sync(RD, path, iface, method, args, None, Gio.DBusCallFlags.NONE, 3000, None)
        except GLib.Error as e:
            raise InputError(Gio.DBusError.get_remote_error(e) or "remote desktop error") from None

    @staticmethod
    def available(bus: Gio.DBusConnection) -> bool:
        try:
            bus.call_sync(RD, RD_PATH, "org.freedesktop.DBus.Properties", "Get",
                          GLib.Variant("(ss)", (RD, "SupportedDeviceTypes")), None, Gio.DBusCallFlags.NONE, 2000, None)
            return True
        except GLib.Error:
            return False

    # ── session ──────────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._path is not None:
            return
        self._path = self._call(RD_PATH, RD, "CreateSession").unpack()[0]
        self._call(self._path, SESSION, "Start")

    def stop(self) -> None:
        path, self._path = self._path, None
        if path is not None:
            try:
                self._call(path, SESSION, "Stop")
            except InputError:
                pass

    def _s(self, method: str, args: GLib.Variant | None = None) -> None:
        if self._path is None:
            self.start()
        self._call(self._path, SESSION, method, args)

    # ── pointer ──────────────────────────────────────────────────────────────
    def where(self) -> tuple[int, int] | None:
        if self._pointer is None:
            return None
        try:
            return self._pointer()
        except Exception:  # noqa: BLE001
            return None

    def move_to(self, x: float, y: float, layout: tuple[int, int] | None = None) -> None:
        """Relative motion until `GetPointer` says we are there (±1 px). Falls back to the corner anchor."""
        cur = self.where()
        if cur is None:
            if layout is None:
                raise InputError("no pointer position")
            self._s("NotifyPointerMotionRelative", GLib.Variant("(dd)", (10000.0, 10000.0)))
            time.sleep(0.03)
            cur = (layout[0] - 1, layout[1] - 1)
        for _ in range(4):
            dx, dy = x - cur[0], y - cur[1]
            if abs(dx) <= 1 and abs(dy) <= 1:
                return
            self._s("NotifyPointerMotionRelative", GLib.Variant("(dd)", (float(dx), float(dy))))
            time.sleep(0.03)
            now = self.where()
            if now is None:
                return
            cur = now
        if abs(x - cur[0]) > 2 or abs(y - cur[1]) > 2:
            raise InputError("pointer did not reach the target")

    def button(self, button: str = "left", double: bool = False) -> None:
        code = BTN.get(button, BTN["left"])
        for i in range(2 if double else 1):
            self._s("NotifyPointerButton", GLib.Variant("(ib)", (code, True)))
            time.sleep(0.04)
            self._s("NotifyPointerButton", GLib.Variant("(ib)", (code, False)))
            if double and i == 0:
                time.sleep(0.08)

    def scroll(self, direction: str, steps: int) -> None:
        axis = 1 if direction in ("left", "right") else 0
        sign = -1 if direction in ("up", "left") else 1
        for _ in range(max(1, steps)):
            self._s("NotifyPointerAxisDiscrete", GLib.Variant("(ui)", (axis, sign)))
            time.sleep(0.03)

    # ── keyboard ─────────────────────────────────────────────────────────────
    def keysym(self, ks: int, pressed: bool) -> None:
        self._s("NotifyKeyboardKeysym", GLib.Variant("(ub)", (ks, pressed)))

    def combo(self, combo: str, repeat: int = 1) -> None:
        *mods, key = [p for p in combo.split("+") if p]
        ks = key_keysym(key)
        if ks is None or any(m.lower() not in MODS for m in mods):
            raise InputError("unknown key")
        for _ in range(max(1, repeat)):
            for m in mods:
                self.keysym(MODS[m.lower()], True)
            self.keysym(ks, True)
            self.keysym(ks, False)
            for m in reversed(mods):
                self.keysym(MODS[m.lower()], False)
            time.sleep(0.03)

    def type_text(self, text: str) -> None:
        for ch in text:
            ks = char_keysym(ch)
            self.keysym(ks, True)
            self.keysym(ks, False)
            time.sleep(0.012)
