"""`act`: runs a plan the backend already validated, behind the helper's own barrier (CONTRACT §5).

The barrier does not trust the backend: Drakter windows, HANDS_OFF apps, RISKY steps without `confirmed`
and password fields are refused here too. Progress events carry positions only, never what is typed.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import tree
from inject import Injector, InputError
from lists import fold, hands_off_name, is_risky_combo, is_risky_text


class Refused(Exception):
    """A step the barrier will not run. `code` is one of HELPER_ERROR_CODES."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class StepFailed(Exception):
    def __init__(self, code: str = "step_failed") -> None:
        super().__init__(code)
        self.code = code


def center(r: dict[str, int]) -> tuple[float, float]:
    return r["x"] + r["w"] / 2, r["y"] + r["h"] / 2


class Hands:
    """Shared state the barrier needs: the companion, the injector and Drakter's pids."""

    def __init__(self, companion, injector: Injector | None, emit: Callable[[str, dict[str, Any]], None]) -> None:
        self.companion = companion
        self.injector = injector
        self.emit = emit
        self.drakter_pids: set[int] = set()
        self.stop_requested = False
        self.busy = False

    # ── barrier ──────────────────────────────────────────────────────────────
    def window_by_id(self, window_id: str) -> dict[str, Any] | None:
        for w in self.companion.list_windows():
            if w["window_id"] == str(window_id):
                return w
        return None

    def refusal_for(self, w: dict[str, Any]) -> str | None:
        if w.get("_floating") or int(w.get("pid", 0)) in self.drakter_pids:
            return "drakter_window"
        if hands_off_name(*(w.get("_ids") or [w.get("app_id"), w.get("wm_class")]), _exe(w.get("pid"))):
            return "hands_off_app"
        return None

    def top_window_at(self, x: float, y: float) -> dict[str, Any] | None:
        for w in self.companion.list_windows():  # top to bottom
            if w.get("_floating") or w.get("minimized"):
                continue  # the floating window lets clicks through (ForcePassthrough) during an act
            f = w["frame"]
            if f["x"] <= x < f["x"] + f["w"] and f["y"] <= y < f["y"] + f["h"]:
                return w
        return None

    def check_point(self, target: dict[str, Any], x: float, y: float) -> None:
        """Under the point there must be the target window, and nothing hands-off or Drakter's."""
        w = self.top_window_at(x, y)
        if w is None:
            raise Refused("window_changed")
        if (code := self.refusal_for(w)) is not None:
            raise Refused(code)
        if w["window_id"] != target["window_id"] and int(w["pid"]) != int(target["pid"]):
            raise Refused("window_changed")

    def activate(self, target: dict[str, Any]) -> None:
        """Before typing: activate the target and check ACTIVE by AT-SPI. Another app in front stops."""
        ok = self.companion.activate(target["window_id"])
        if ok is False:
            raise Refused("window_changed")
        tree.pump(0.15)
        front = self.companion.active_window()
        if front is None or (front["window_id"] != target["window_id"] and int(front["pid"]) != int(target["pid"])):
            raise Refused("window_changed")
        if (code := self.refusal_for(front)) is not None:
            raise Refused(code)
        try:
            if not tree.is_active(tree.frame_for(front)):
                raise Refused("window_changed")
        except tree.TreeError:
            pass  # no tree: the extension's focus is the only signal

    # ── plan ─────────────────────────────────────────────────────────────────
    def act(self, p: dict[str, Any]) -> dict[str, Any]:
        act_id = str(p["act_id"])
        confirmed = p.get("confirmed") is True
        steps = list(p.get("steps") or [])
        controls = {int(c["id"]): c for c in p.get("controls") or [] if "id" in c}
        target = self.window_by_id(p["window_id"])
        if target is None:
            raise Refused("window_not_found")
        if (code := self.refusal_for(target)) is not None:
            raise Refused(code)
        self.stop_requested = False
        results: list[dict[str, Any]] = []
        status = "done"
        self.companion.passthrough(True)
        layout = self._layout()
        try:
            if self.injector is not None:
                try:
                    self.injector.start()
                except InputError:
                    self.injector = None
            # Bring the target to the front first (v2 `ActivateWindow`; the v1 prototype has none).
            if self.companion.activate(target["window_id"]):
                tree.pump(0.2)
            self.emit("act.progress", {"act_id": act_id, "index": 0, "state": "start"})
            home = self.injector.where() if self.injector is not None else None
            for i, step in enumerate(steps):
                if self.stop_requested:
                    results.extend({"index": j, "status": "skipped"} for j in range(i, len(steps)))
                    status = "stopped"
                    break
                try:
                    fresh = self.window_by_id(target["window_id"])
                    if fresh is None:
                        raise Refused("window_changed")
                    target = fresh
                    bounds = self._step(act_id, i, step, target, controls, confirmed, layout)
                    results.append({"index": i, "status": "ok", "bounds": bounds})
                except Refused as e:
                    results.append({"index": i, "status": "refused", "code": e.code})
                    results.extend({"index": j, "status": "skipped"} for j in range(i + 1, len(steps)))
                    status = "stopped"
                    break
                except (StepFailed, InputError, tree.TreeError) as e:
                    code = "step_failed" if isinstance(e, InputError) else e.code
                    results.append({"index": i, "status": "failed", "code": code})
                    results.extend({"index": j, "status": "skipped"} for j in range(i + 1, len(steps)))
                    status = "failed"
                    self.emit("act.progress", {"act_id": act_id, "index": i, "state": "failed"})
                    break
            if home is not None and self.injector is not None and steps and steps[-1].get("do") != "hover":
                try:
                    self.injector.move_to(*home, layout=layout)
                except InputError:
                    pass
        finally:
            if self.injector is not None:
                self.injector.stop()
            self.companion.passthrough(False)
        self.emit("act.progress", {"act_id": act_id, "index": max(0, len(results) - 1),
                                   "state": "done" if status == "done" else "failed"})
        return {"status": status, "steps": results}

    def _layout(self) -> tuple[int, int] | None:
        try:
            mons = self.companion.monitors()
        except Exception:  # noqa: BLE001
            return None
        if not mons:
            return None
        return (max(m["geometry"]["x"] + m["geometry"]["w"] for m in mons),
                max(m["geometry"]["y"] + m["geometry"]["h"] for m in mons))

    def _progress(self, act_id: str, i: int, bounds: dict[str, int] | None, hover: bool = False) -> None:
        self.emit("act.progress", {"act_id": act_id, "index": i, "state": "step", "bounds": bounds, "hover": hover})

    def _need_input(self) -> Injector:
        if self.injector is None:
            raise StepFailed("input_unavailable")
        return self.injector

    def _click(self, target, x, y, button="left", double=False, layout=None) -> None:
        self.check_point(target, x, y)
        inj = self._need_input()
        inj.move_to(x, y, layout=layout)
        self.check_point(target, x, y)  # a window can pop up while the pointer travels
        inj.button(button, double)
        tree.pump(0.3)

    def _resolve_id(self, target, controls, cid: int):
        ctl = controls.get(int(cid))
        if ctl is None:
            raise StepFailed("step_failed")
        acc, live = tree.rematch(target, ctl)
        return acc, (live or ctl)

    def _step(self, act_id, i, s, target, controls, confirmed, layout) -> dict[str, int] | None:
        do = s.get("do")
        if do in ("click_text", "click", "click_at"):
            if do == "click_text":
                acc, ctl = tree.find_acc(target, s["text"])
                if ctl is None:
                    raise StepFailed()
                label = ctl.get("name") or s["text"]
                if not confirmed and (is_risky_text(s["text"]) or is_risky_text(label)):
                    raise Refused("risky_step")
                rect = ctl["rect"]
            elif do == "click":
                acc, ctl = self._resolve_id(target, controls, s["id"])
                if not confirmed and is_risky_text(ctl.get("name")):
                    raise Refused("risky_step")
                rect = ctl.get("rect")
            else:
                x, y = float(s["x"]), float(s["y"])
                under = tree.at_point(target, x, y)
                if not confirmed and under is not None and is_risky_text(tree.label_near(under)):
                    raise Refused("risky_step")
                rect = {"x": int(x) - 4, "y": int(y) - 4, "w": 8, "h": 8}
            if rect is None:
                raise StepFailed()
            self._progress(act_id, i, rect)
            x, y = center(rect)
            if self.injector is None and do != "click_at" and acc is not None and s.get("button", "left") == "left":
                if not tree.do_action(acc):
                    raise StepFailed()
                tree.pump(0.3)
            else:
                self._click(target, x, y, s.get("button", "left"), bool(s.get("double")), layout)
            return rect

        if do in ("fill", "choose", "set", "focus"):
            if s.get("id") is not None:
                acc, ctl = self._resolve_id(target, controls, s["id"])
            else:
                acc, ctl = tree.find_acc(target, s["field"], editable_only=(do == "fill"))
                if acc is None and do == "fill":
                    acc, ctl = self._field_by_label(target, s["field"])
            if acc is None or ctl is None:
                raise StepFailed()
            rect = ctl.get("rect")
            self._progress(act_id, i, rect)
            if do == "focus":
                if rect is None:
                    raise StepFailed()
                self._click(target, *center(rect), layout=layout)
                return rect
            if do == "choose":
                if not confirmed and is_risky_text(s["option"]):
                    raise Refused("risky_step")
                self._choose(target, acc, rect, s["option"], layout)
                return rect
            if do == "set" and not isinstance(s.get("value"), str):
                self._set_value(acc, s.get("value"))
                return rect
            text = str(s.get("text") if do == "fill" else s.get("value"))
            if ctl.get("secret") or tree.is_secret(acc):
                raise Refused("secret_field")
            self._write(target, acc, rect, text, layout)
            return rect

        if do == "type":
            self.activate(target)
            acc = tree.focused(target)
            if acc is None or not (tree.is_editable(acc) or tree.role_of(acc) in tree.EDITABLE_ROLES):
                raise StepFailed()
            if tree.is_secret(acc):
                raise Refused("secret_field")
            before = tree.window_text(target)
            self._need_input().type_text(str(s["text"]))
            self._verify(target, str(s["text"]), before)
            return tree.rect_of(acc, target["frame"])

        if do == "key":
            combo = str(s["combo"])
            if not confirmed and is_risky_combo(combo):
                raise Refused("risky_step")
            self.activate(target)
            self._progress(act_id, i, None)
            self._need_input().combo(combo, int(s.get("repeat", 1)))
            tree.pump(0.25)
            return None

        if do == "scroll":
            rect = None
            if s.get("id") is not None:
                _acc, ctl = self._resolve_id(target, controls, s["id"])
                rect = ctl.get("rect")
            point = center(rect) if rect else center(target["frame"])
            self.check_point(target, *point)
            inj = self._need_input()
            inj.move_to(*point, layout=layout)
            inj.scroll(s.get("direction", "down"), 60 if s.get("to_end") else int(s.get("amount", 3)))
            tree.pump(0.2)
            return rect

        if do == "hover":
            if s.get("id") is not None:
                _acc, ctl = self._resolve_id(target, controls, s["id"])
            else:
                _acc, ctl = tree.find_acc(target, s["text"])
            if ctl is None or ctl.get("rect") is None:
                raise StepFailed()
            rect = ctl["rect"]
            self._progress(act_id, i, rect, hover=True)
            self.check_point(target, *center(rect))
            self._need_input().move_to(*center(rect), layout=layout)
            tree.pump(0.3)
            return rect

        if do == "wait":
            ms = int(s.get("ms", 1000))
            until = s.get("until_text")
            end = time.monotonic() + ms / 1000
            while time.monotonic() < end:
                if self.stop_requested:
                    return None
                if until and tree.find_acc(target, until)[0] is not None:
                    return None
                tree.pump(0.2)
            if until:
                raise StepFailed()
            return None

        raise StepFailed("validation_error")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _field_by_label(self, target, label: str):
        """A label «Nombre» with the editable field next to it (right or below)."""
        lab_acc, lab = tree.find_acc(target, label)
        if lab is None or lab.get("rect") is None:
            return None, None
        lx, ly = center(lab["rect"])
        best = None
        frame = tree.frame_for(target)
        for acc in tree.walk(frame, 3000):
            if not tree.is_editable(acc):
                continue
            r = tree.rect_of(acc, target["frame"])
            if r is None:
                continue
            cx, cy = center(r)
            if cx < lx - 20 or cy < ly - 20:
                continue
            d = abs(cx - lx) + abs(cy - ly)
            if best is None or d < best[0]:
                best = (d, acc)
        if best is None:
            return None, None
        return best[1], tree.control(best[1], 1, target["frame"], target["frame"])

    def _write(self, target, acc, rect, text: str, layout) -> None:
        before = tree.window_text(target)
        if tree.set_text(acc, text):
            tree.pump(0.25)
            if fold(text) in fold(tree.text_of(acc, 5000) or ""):
                return
        # No EditableText (Chromium): focus by clicking, select all and type.
        if rect is None:
            raise StepFailed()
        self._click(target, *center(rect), layout=layout)
        if tree.is_secret(tree.focused(target) or acc):
            raise Refused("secret_field")
        self.activate(target)
        inj = self._need_input()
        inj.combo("ctrl+a")
        inj.type_text(text)
        self._verify(target, text, before)

    def _verify(self, target, text: str, before: str) -> None:
        """The typed text must show up (text-changed by effect). If not, stop before the next step."""
        want = fold(text)[:120]
        for _ in range(5):
            tree.pump(0.25)
            now = tree.window_text(target)
            if want and want in fold(now):
                return
        if now == before:
            raise StepFailed()

    def _choose(self, target, acc, rect, option: str, layout) -> None:
        # Selection interface first (browsers), then the option's own action, then two clicks.
        try:
            for holder in [acc, *[acc.get_child_at_index(k) for k in range(min(acc.get_child_count(), 4))]]:
                if holder is None:
                    continue
                n = holder.get_child_count()
                for k in range(min(n, 500)):
                    child = holder.get_child_at_index(k)
                    if child is not None and tree.match_score(tree.name_of(child), option) >= 2:
                        try:
                            if tree.Atspi.Selection.select_child(holder, k):
                                tree.pump(0.25)
                                return
                        except Exception:  # noqa: BLE001
                            pass
                        if tree.do_action(child):
                            tree.pump(0.25)
                            return
        except Exception:  # noqa: BLE001
            pass
        if rect is None:
            raise StepFailed()
        self._click(target, *center(rect), layout=layout)
        tree.pump(0.3)
        opt_acc, opt = tree.find_acc(target, option)
        if opt is None or opt.get("rect") is None:
            raise StepFailed()
        self._click(target, *center(opt["rect"]), layout=layout)

    def _set_value(self, acc, value) -> None:
        if isinstance(value, bool):
            st = tree._states(acc)
            on = st is not None and (st.contains(tree.S.CHECKED) or st.contains(tree.S.PRESSED))
            if on != value and not tree.do_action(acc, ("toggle", "click", "press", "activate")):
                raise StepFailed()
            tree.pump(0.2)
            return
        try:
            if not tree.Atspi.Value.set_current_value(acc, float(value)):
                raise StepFailed()
        except StepFailed:
            raise
        except Exception:  # noqa: BLE001
            raise StepFailed() from None


def _exe(pid: Any) -> str | None:
    try:
        import os

        return os.path.basename(os.readlink(f"/proc/{int(pid)}/exe"))
    except Exception:  # noqa: BLE001
        return None
