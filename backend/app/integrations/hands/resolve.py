"""Where each mark of a beat goes on the real screen (CONTRACT §9.2). Used by B2's DrawRunner.

For every `Target` (`at`, `to`, `tie`): `id` → the turn's read; `x/y/w/h` without text → the latest capture;
`text` → AT-SPI in the target window, then OCR of its crop, then its own `x/y`; else `missing`. `points` are
capture pixels. Marks on HANDS_OFF apps are drawn too: pointing is allowed, acting is not.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Final
from uuid import UUID

from drakter_contracts.floating import LogicalRect, MissingTarget
from drakter_contracts.hands_ipc import HAtspiFind, HAtspiFindResult, HScreenshot, HWindowsResult, HelperWindow

from app.integrations.hands import desktop, ocr, records
from app.integrations.hands.client import HandsClient, HandsError, ensure_client
from app.integrations.hands.lists import match_score

CARDS: Final = frozenset({
    "card", "note", "list", "mindmap", "clip", "sources", "photo", "graph", "legend", "timeline", "molecule",
    "model", "flow", "table", "bars", "map", "math", "geometry", "quiz", "ticket", "medal",
})
PATHS: Final = frozenset({"trace", "line", "curve", "arrow"})
TARGET_KEYS: Final = ("at", "to", "tie")
MAX_MARKS: Final = 40
MAX_EVERY: Final = 8
MAX_BUSY: Final = 300


@dataclass(slots=True)
class ResolvedSeg:
    """`beats` with `at/to/tie` → `{"rect":[x,y,w,h], "src": <original Target>}` and `points` in global logical
    px; the marks that could not be placed are left out and listed in `missing`."""

    beats: list[dict[str, Any]]
    missing: list[MissingTarget] = field(default_factory=list)
    win: list[float] | None = None
    busy: list[list[float]] = field(default_factory=list)


class _Missing(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _rect(r: LogicalRect) -> list[float]:
    return [float(r.x), float(r.y), float(r.w), float(r.h)]


def _has_place(t: Any) -> bool:
    return isinstance(t, dict) and (t.get("text") is not None or t.get("id") is not None
                                    or (t.get("x") is not None and t.get("y") is not None))


# Searches shared inside one segment, until a wait; after a click they run again.
_cache: dict[tuple[UUID, str, str], list[list[float]]] = {}
_cache_epoch: dict[UUID, int] = {}


class _Look:
    def __init__(self, client: HandsClient, turn_id: UUID, win: HelperWindow | None, wins: HWindowsResult) -> None:
        self.client = client
        self.turn_id = turn_id
        self.win = win
        self.wins = wins
        self.shot = records.latest_shot(turn_id)
        self.read = records.latest_read(turn_id)
        self._ocr: list[tuple[str, list[float]]] | None = None

    # px of the latest capture → global logical px
    def pixel(self, x: float, y: float) -> tuple[float, float]:
        if self.shot is None or self.shot.stale:
            raise _Missing("stale_shot")
        return self.shot.to_logical(x, y)

    def by_id(self, cid: int) -> list[float]:
        if self.read is None or self.read.stale:
            raise _Missing("stale_read")
        c = self.read.by_id().get(int(cid))
        if c is None or c.rect is None:
            raise _Missing("not_found")
        return _rect(c.rect)

    def within(self, w: dict[str, Any] | None) -> list[float] | None:
        if not isinstance(w, dict):
            return None
        a = self.pixel(float(w["x"]) - float(w["w"]) / 2, float(w["y"]) - float(w["h"]) / 2)
        b = self.pixel(float(w["x"]) + float(w["w"]) / 2, float(w["y"]) + float(w["h"]) / 2)
        return [a[0], a[1], b[0] - a[0], b[1] - a[1]]

    async def text(self, text: str, every: bool, within: list[float] | None) -> list[list[float]]:
        key = (self.turn_id, self.win.window_id if self.win else "screen", f"{text}\x00{every}\x00{within}")
        if key in _cache:
            return _cache[key]
        hits: list[list[float]] = []
        if self.win is not None:
            try:
                res = await self.client.call("atspi.find", HAtspiFind(
                    window_id=self.win.window_id, text=text[:80], every=every,
                    within=None if within is None else LogicalRect(x=int(within[0]), y=int(within[1]),
                                                                   w=int(within[2]), h=int(within[3]))))
                assert isinstance(res, HAtspiFindResult)
                hits = [_rect(m.rect) for m in res.matches if m.rect is not None]
            except HandsError:
                hits = []
        if not hits:
            hits = await self._ocr_find(text, every, within)
        _cache[key] = hits
        return hits

    async def _ocr_find(self, text: str, every: bool, within: list[float] | None) -> list[list[float]]:
        if self._ocr is None:
            self._ocr = []
            if not ocr.available():
                return []
            req = (HScreenshot(window_id=self.win.window_id) if self.win is not None
                   else HScreenshot(monitor=self._monitor()))
            try:
                async with desktop.captured(self.client, req) as cap:
                    result = await ocr.run_ocr(cap.path)
                    if result is not None:
                        g, s = cap.geometry, cap.scale
                        self._ocr = [(b.text, [g.x + b.rect[0] / s, g.y + b.rect[1] / s, b.rect[2] / s, b.rect[3] / s])
                                     for b in result.boxes]
            except HandsError:
                self._ocr = []
        scored = []
        for i, (t, r) in enumerate(self._ocr):
            sc = match_score(t, text)
            if sc == 0:
                continue
            if within is not None:
                cx, cy = r[0] + r[2] / 2, r[1] + r[3] / 2
                if not (within[0] <= cx <= within[0] + within[2] and within[1] <= cy <= within[1] + within[3]):
                    continue
            scored.append(((-sc, r[1], r[0], i), r))
        scored.sort(key=lambda s: s[0])
        return [r for _k, r in scored[: MAX_EVERY if every else 1]]

    def _monitor(self) -> int:
        for m in self.wins.monitors:
            if m.primary:
                return m.index
        return 0

    async def place(self, t: dict[str, Any]) -> list[list[float]]:
        """One or more rects (several only with `every`/`within`)."""
        if t.get("id") is not None:
            return [self.by_id(int(t["id"]))]
        if t.get("text") is not None:
            within = self.within(t.get("within")) if t.get("within") else None
            hits = await self.text(str(t["text"]), bool(t.get("every")), within)
            if hits:
                return hits if (t.get("every") or within) else hits[:1]
            if t.get("x") is None or t.get("y") is None:
                raise _Missing("not_found")
        x, y = float(t["x"]), float(t["y"])
        w, h = t.get("w"), t.get("h")
        if w is not None and h is not None and float(w) > 0 and float(h) > 0:
            a = self.pixel(x - float(w) / 2, y - float(h) / 2)
            b = self.pixel(x + float(w) / 2, y + float(h) / 2)
            return [[a[0], a[1], b[0] - a[0], b[1] - a[1]]]
        cx, cy = self.pixel(x, y)
        return [[cx - 14, cy - 14, 28.0, 28.0]]


def _round(r: list[float]) -> list[float]:
    return [float(round(v)) for v in r]


async def resolve_marks(beats: list[dict], *, target: str, turn_id: UUID, after_wait: bool) -> ResolvedSeg:
    """CONTRACT §9.2. Raises `HandsError('companion_unavailable')` without the helper."""
    client = await ensure_client()
    epoch = records.current_epoch()
    if after_wait or _cache_epoch.get(turn_id) != epoch:
        for k in [k for k in _cache if k[0] == turn_id]:
            _cache.pop(k, None)
        _cache_epoch[turn_id] = epoch
    wins = await desktop.list_windows(client)
    win = desktop.by_target(wins, target)
    look = _Look(client, turn_id, win, wins)
    # An app or `window:<id>` that is not open: its marks cannot be placed. `front` without a window
    # falls back to the whole screen, like `screen`.
    lost = win is None and (target or "front").strip() not in ("front", "screen")
    out_beats: list[dict[str, Any]] = []
    missing: list[MissingTarget] = []
    has_cards = False
    for bi, beat in enumerate(beats):
        b = copy.deepcopy(beat)
        marks_out: list[dict[str, Any]] = []
        for mi, mark in enumerate(beat.get("marks") or []):
            if not isinstance(mark, dict):
                continue
            has_cards = has_cards or mark.get("kind") in CARDS
            try:
                if lost and any(_has_place(mark.get(k)) for k in TARGET_KEYS):
                    raise _Missing("no_window")
                resolved = [copy.deepcopy(mark)]
                for k in TARGET_KEYS:
                    t = mark.get(k)
                    if not _has_place(t):
                        continue
                    rects = await look.place(t)
                    if k == "at" and len(rects) > 1:
                        resolved = [{**copy.deepcopy(mark), "at": {"rect": _round(r), "src": copy.deepcopy(t)}}
                                    for r in rects[:MAX_EVERY]]
                    else:
                        for m in resolved:
                            m[k] = {"rect": _round(rects[0]), "src": copy.deepcopy(t)}
                pts = mark.get("points")
                if mark.get("kind") in PATHS and isinstance(pts, list) and len(pts) >= 2:
                    mapped = [list(map(float, look.pixel(float(p[0]), float(p[1])))) for p in pts]
                    for m in resolved:
                        m["points"] = [[round(x, 1), round(y, 1)] for x, y in mapped]
                marks_out.extend(resolved)
            except _Missing as e:
                missing.append(MissingTarget(beat=min(bi + 1, 12), mark=min(mi + 1, 40), reason=e.reason))
            except (KeyError, TypeError, ValueError):
                missing.append(MissingTarget(beat=min(bi + 1, 12), mark=min(mi + 1, 40), reason="not_found"))
        b["marks"] = marks_out[:MAX_MARKS]
        out_beats.append(b)
    win_rect = _rect(win.frame) if (win is not None and has_cards) else None
    busy: list[list[float]] = []
    if look.read is not None and not look.read.stale:
        busy = [_rect(c.rect) for c in look.read.controls if c.rect is not None][:MAX_BUSY]
    return ResolvedSeg(beats=out_beats, missing=missing, win=win_rect, busy=busy)
