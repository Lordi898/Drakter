"""AT-SPI: read a window as controls, find by text, hit-test a point (spike 03 §1).

Coordinates: `rect = frame of the extension + extents(WINDOW)`; SCREEN is (0,0) in GTK4 and relative in
browsers. Not thread-safe: called only from the helper's main loop thread.
"""

from __future__ import annotations

import time
from typing import Any

import gi

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi  # noqa: E402

from lists import match_score  # noqa: E402

S = Atspi.StateType
WIN = Atspi.CoordType.WINDOW
MAX_NODES = 4000
MAX_DEPTH = 60

INTERACTIVE = {
    "push button", "toggle button", "button", "entry", "password text", "link", "check box", "radio button",
    "combo box", "menu item", "check menu item", "radio menu item", "page tab", "list item", "tree item",
    "table cell", "spin button", "slider", "switch", "menu", "icon", "toggle switch", "spinbutton",
}
EDITABLE_ROLES = {"entry", "password text", "text", "spin button", "combo box", "terminal", "document text"}
TEXTUAL = {"label", "heading", "paragraph", "static", "caption", "text", "section", "status bar", "title bar"}
STATE_NAMES = {
    S.ENABLED: "enabled", S.SHOWING: "visible", S.FOCUSED: "focused", S.CHECKED: "checked",
    S.SELECTED: "selected", S.EXPANDED: "expanded", S.ACTIVE: "active", S.EDITABLE: "editable",
    S.PRESSED: "pressed", S.SENSITIVE: "sensitive", S.FOCUSABLE: "focusable", S.MULTI_LINE: "multi_line",
}
_BROWSER_TOOLKITS = ("gecko", "chromium", "chrome", "webkit")

try:
    Atspi.init()
except Exception:  # noqa: BLE001
    pass


class TreeError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def available() -> bool:
    try:
        return Atspi.get_desktop(0) is not None
    except Exception:  # noqa: BLE001
        return False


# ── window ↔ accessible ──────────────────────────────────────────────────────
def app_for_pid(pid: int):
    try:
        desk = Atspi.get_desktop(0)
        for i in range(desk.get_child_count()):
            a = desk.get_child_at_index(i)
            if a is not None and a.get_process_id() == pid:
                return a
    except Exception:  # noqa: BLE001
        pass
    return None


def _states(acc) -> Any:
    try:
        return acc.get_state_set()
    except Exception:  # noqa: BLE001
        return None


def frame_for(win: dict[str, Any]):
    """The AT-SPI frame of an extension window: same pid, then title, ACTIVE, and size."""
    app = app_for_pid(int(win["pid"]))
    if app is None:
        raise TreeError("accessibility_unavailable")
    frames = []
    try:
        for i in range(app.get_child_count()):
            f = app.get_child_at_index(i)
            if f is not None:
                frames.append(f)
    except Exception:  # noqa: BLE001
        pass
    if not frames:
        raise TreeError("accessibility_unavailable")
    title = (win.get("title") or "").strip()
    fw, fh = win["frame"]["w"], win["frame"]["h"]

    def score(f) -> tuple[int, int, int]:
        name = (f.get_name() or "").strip()
        st = _states(f)
        active = 1 if st is not None and st.contains(S.ACTIVE) else 0
        try:
            r = f.get_extents(WIN)
            size = -abs(r.width - fw) - abs(r.height - fh)
        except Exception:  # noqa: BLE001
            size = -99999
        return (1 if title and name == title else 0, active if win.get("focused") else 0, size)

    return max(frames, key=score)


def is_active(frame) -> bool:
    st = _states(frame)
    return st is not None and st.contains(S.ACTIVE)


def toolkit(frame) -> str:
    try:
        return (frame.get_application().get_toolkit_name() or "").lower()
    except Exception:  # noqa: BLE001
        return ""


# ── nodes ────────────────────────────────────────────────────────────────────
def walk(root, limit: int = MAX_NODES) -> list:
    out: list = []
    stack = [(root, 0)]
    while stack and len(out) < limit:
        acc, depth = stack.pop()
        if acc is None:
            continue
        out.append(acc)
        if depth >= MAX_DEPTH:
            continue
        st = _states(acc)
        # A hidden subtree (closed menu, other tab) is skipped, except for the root.
        if acc is not root and st is not None and not st.contains(S.SHOWING):
            continue
        try:
            n = min(acc.get_child_count(), 2000)
        except Exception:  # noqa: BLE001
            continue
        kids = []
        for i in range(n):
            try:
                kids.append(acc.get_child_at_index(i))
            except Exception:  # noqa: BLE001
                pass
        stack.extend((k, depth + 1) for k in reversed(kids))
    return out


def collection_nodes(frame) -> list | None:
    """Server-side match of showing nodes (browsers implement `Collection`, GTK4 does not)."""
    try:
        ss = Atspi.StateSet.new([S.SHOWING])
        rule = Atspi.MatchRule.new(ss, Atspi.CollectionMatchType.ALL, None, Atspi.CollectionMatchType.NONE,
                                   [], Atspi.CollectionMatchType.NONE, None, Atspi.CollectionMatchType.NONE, False)
        return list(Atspi.Collection.get_matches(frame, rule, Atspi.CollectionSortOrder.CANONICAL, MAX_NODES, True))
    except Exception:  # noqa: BLE001
        return None


def nodes_of(frame) -> list:
    if any(t in toolkit(frame) for t in _BROWSER_TOOLKITS):
        got = collection_nodes(frame)
        if got:
            return got
    return walk(frame)


def role_of(acc) -> str:
    try:
        return acc.get_role_name() or ""
    except Exception:  # noqa: BLE001
        return ""


def name_of(acc) -> str:
    try:
        return (acc.get_name() or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def text_of(acc, limit: int = 200) -> str | None:
    try:
        n = Atspi.Text.get_character_count(acc)
        return Atspi.Text.get_text(acc, 0, min(n, limit)) if n > 0 else ""
    except Exception:  # noqa: BLE001
        return None


def rect_of(acc, origin: dict[str, int]) -> dict[str, int] | None:
    try:
        r = acc.get_extents(WIN)
    except Exception:  # noqa: BLE001
        return None
    if r.width <= 0 or r.height <= 0:
        return None
    return {"x": origin["x"] + r.x, "y": origin["y"] + r.y, "w": r.width, "h": r.height}


def actions_of(acc) -> list[str]:
    try:
        return [Atspi.Action.get_action_name(acc, i) or "" for i in range(Atspi.Action.get_n_actions(acc))][:8]
    except Exception:  # noqa: BLE001
        return []


def is_secret(acc, role: str | None = None) -> bool:
    role = role if role is not None else role_of(acc)
    if role == "password text":
        return True
    try:
        attrs = acc.get_attributes() or {}
        if str(attrs.get("text-input-type", "")).lower() == "password":
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def is_editable(acc, st=None) -> bool:
    st = st if st is not None else _states(acc)
    if st is not None and st.contains(S.EDITABLE):
        return True
    try:
        return "EditableText" in (acc.get_interfaces() or [])
    except Exception:  # noqa: BLE001
        return False


def control(acc, cid: int, origin: dict[str, int], frame_rect: dict[str, int]) -> dict[str, Any]:
    role = role_of(acc)
    st = _states(acc)
    secret = is_secret(acc, role)
    editable = is_editable(acc, st)
    value = None
    if editable and not secret:
        value = text_of(acc)
    elif role in ("slider", "spin button", "progress bar"):
        try:
            value = str(Atspi.Value.get_current_value(acc))
        except Exception:  # noqa: BLE001
            value = None
    rect = rect_of(acc, origin)
    off = rect is None or not _intersects(rect, frame_rect) or (st is not None and not st.contains(S.SHOWING))
    return {
        "id": cid,
        "role": role[:40] or "unknown",
        "name": name_of(acc)[:200],
        "value": None if value is None else value[:200],
        "rect": rect,
        "states": [n for s, n in STATE_NAMES.items() if st is not None and st.contains(s)][:12],
        "actions": actions_of(acc),
        "editable": editable,
        "offscreen": off,
        "secret": secret,
    }


def _intersects(a: dict[str, int], b: dict[str, int]) -> bool:
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def _wanted(acc, role: str) -> bool:
    if role in INTERACTIVE:
        return True
    if role in ("text", "document text") and is_editable(acc):
        return True
    return False


# ── commands ─────────────────────────────────────────────────────────────────
def read(win: dict[str, Any], max_controls: int, include_text: bool, max_text: int) -> dict[str, Any]:
    frame = frame_for(win)
    origin = win["frame"]
    nodes = nodes_of(frame)
    controls: list[dict[str, Any]] = []
    texts: list[str] = []
    seen: set[str] = set()
    used = 0
    truncated = False
    for acc in nodes:
        role = role_of(acc)
        if _wanted(acc, role):
            if len(controls) >= max_controls:
                truncated = True
                continue
            controls.append(control(acc, len(controls) + 1, origin, origin))
        elif include_text and role in TEXTUAL:
            t = name_of(acc) or (text_of(acc, 500) or "").strip()
            if t and t not in seen and not is_secret(acc, role):
                seen.add(t)
                if used + len(t) + 1 > max_text:
                    truncated = True
                    continue
                texts.append(t)
                used += len(t) + 1
    return {"controls": controls, "text": "\n".join(texts)[:max_text], "truncated": truncated}


def find(win: dict[str, Any], text: str, role: str | None = None, every: bool = False,
         within: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """exact > whole word > start of word; never a word inside another. Up to 8 with `every`."""
    frame = frame_for(win)
    origin = win["frame"]
    hits = []
    for idx, acc in enumerate(nodes_of(frame)):
        r = role_of(acc)
        if role and r != role:
            continue
        name = name_of(acc)
        sc = match_score(name, text)
        if sc == 0 and is_editable(acc) and not is_secret(acc, r):
            sc = min(1, match_score(text_of(acc), text))
        if sc == 0:
            continue
        rect = rect_of(acc, origin)
        if rect is None:
            continue
        if within is not None:
            cx, cy = rect["x"] + rect["w"] / 2, rect["y"] + rect["h"] / 2
            if not (within["x"] <= cx <= within["x"] + within["w"] and within["y"] <= cy <= within["y"] + within["h"]):
                continue
        st = _states(acc)
        visible = st is not None and st.contains(S.SHOWING) and _intersects(rect, origin)
        interactive = r in INTERACTIVE
        hits.append(((-sc, 0 if visible else 1, 0 if interactive else 1, rect["y"], rect["x"], idx), acc))
    hits.sort(key=lambda h: h[0])
    out = []
    for n, (_k, acc) in enumerate(hits[: 8 if every else 1]):
        out.append(control(acc, n + 1, origin, origin))
    return out


def find_acc(win: dict[str, Any], text: str, *, editable_only: bool = False, role: str | None = None):
    """Best live accessible for a text (same ranking as `find`), plus its control dict."""
    frame = frame_for(win)
    origin = win["frame"]
    best = None
    for idx, acc in enumerate(nodes_of(frame)):
        r = role_of(acc)
        if role and r != role:
            continue
        if editable_only and not (is_editable(acc) or r in EDITABLE_ROLES):
            continue
        sc = match_score(name_of(acc), text)
        if sc == 0:
            continue
        rect = rect_of(acc, origin)
        if rect is None:
            continue
        st = _states(acc)
        visible = st is not None and st.contains(S.SHOWING) and _intersects(rect, origin)
        key = (-sc, 0 if visible else 1, 0 if r in INTERACTIVE else 1, idx)
        if best is None or key < best[0]:
            best = (key, acc)
    if best is None:
        return None, None
    return best[1], control(best[1], 1, origin, origin)


def rematch(win: dict[str, Any], ctl: dict[str, Any]):
    """The live accessible for a control of an earlier read: same role and name, nearest rect."""
    frame = frame_for(win)
    origin = win["frame"]
    want_role, want_name, want = ctl.get("role"), ctl.get("name") or "", ctl.get("rect")
    best = None
    for acc in nodes_of(frame):
        if role_of(acc) != want_role or name_of(acc)[:200] != want_name:
            continue
        r = rect_of(acc, origin)
        d = 0 if (r is None or want is None) else abs(r["x"] - want["x"]) + abs(r["y"] - want["y"])
        if best is None or d < best[0]:
            best = (d, acc)
    if best is None:
        return None, None
    return best[1], control(best[1], int(ctl.get("id", 1)), origin, origin)


def focused(win: dict[str, Any]):
    frame = frame_for(win)
    for acc in walk(frame, 3000):
        st = _states(acc)
        if st is not None and st.contains(S.FOCUSED):
            return acc
    return None


def at_point(win: dict[str, Any], x: float, y: float):
    """Deepest accessible under a global point, inside this window (GTK4 implements it in WINDOW coords)."""
    frame = frame_for(win)
    origin = win["frame"]
    try:
        acc = Atspi.Component.get_accessible_at_point(frame, int(x - origin["x"]), int(y - origin["y"]), WIN)
    except Exception:  # noqa: BLE001
        return None
    for _ in range(20):
        if acc is None:
            break
        try:
            child = Atspi.Component.get_accessible_at_point(acc, int(x - origin["x"]), int(y - origin["y"]), WIN)
        except Exception:  # noqa: BLE001
            child = None
        if child is None or child == acc:
            break
        acc = child
    return acc


def label_near(acc) -> str:
    """Name of a node or, if it has none, of its first named ancestor (for the RISKY check)."""
    for _ in range(6):
        if acc is None:
            return ""
        n = name_of(acc)
        if n:
            return n
        try:
            acc = acc.get_parent()
        except Exception:  # noqa: BLE001
            return ""
    return ""


def window_text(win: dict[str, Any], limit: int = 20000) -> str:
    """Folded text of the window (names and editable contents), to verify that typing landed."""
    frame = frame_for(win)
    parts = []
    for acc in walk(frame, 3000):
        r = role_of(acc)
        if is_secret(acc, r):
            continue
        parts.append(name_of(acc))
        if is_editable(acc) or r in ("text", "label", "paragraph"):
            parts.append(text_of(acc, 2000) or "")
        if sum(len(p) for p in parts) > limit:
            break
    return " ".join(" ".join(parts).split())


def do_action(acc, prefer: tuple[str, ...] = ("click", "press", "activate", "toggle", "jump")) -> bool:
    names = actions_of(acc)
    for want in prefer:
        for i, n in enumerate(names):
            if n.lower() == want:
                try:
                    return bool(Atspi.Action.do_action(acc, i))
                except Exception:  # noqa: BLE001
                    return False
    if names:
        try:
            return bool(Atspi.Action.do_action(acc, 0))
        except Exception:  # noqa: BLE001
            return False
    return False


def set_text(acc, text: str) -> bool:
    try:
        return bool(Atspi.EditableText.set_text_contents(acc, text))
    except Exception:  # noqa: BLE001
        return False


def pump(seconds: float) -> None:
    """Let GLib deliver D-Bus replies and AT-SPI events while we wait (single thread, spike 03 §1.4.5)."""
    from gi.repository import GLib

    ctx = GLib.MainContext.default()
    end = time.monotonic() + seconds
    while True:
        while ctx.pending():
            ctx.iteration(False)
        if time.monotonic() >= end:
            return
        time.sleep(0.01)
