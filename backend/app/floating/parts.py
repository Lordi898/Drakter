"""Lo que hay dibujado ahora: partes `p1, p2…`, botones, fijadas y sueltas (docs/floating/CONTRACT.md §9.3-§9.4).

Port del estado de tinta de Roamies (`showcase/tauri/sidecar/tools.mjs:466-497`, KenKaiii/Roamies@8f0adaa,
AGPL-3.0) sobre `drawjs.Parts` (`createParts`, draw.mjs:493). Sin listas ni quizzes interactivos: en v1
`list_card` y `quiz_done` se ignoran (§11.3). Publica `overlay.ink_clear` por el callback `publish`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from drakter_contracts.floating import DrawnPart, OverlayInkClear

from app.floating import drawjs

Publish = Callable[[str, Any], None]

_QUOTED = re.compile(r"“(.*)”")


def part_label(desc: str) -> str | None:
    """`ring “Exportar”` → `Exportar` (lo que `partDesc` pone entre comillas), recortado a 40."""
    m = _QUOTED.search(desc or "")
    return m.group(1)[:40] if m and m.group(1) else None


class InkState:
    def __init__(self, publish: Publish) -> None:
        self._publish = publish
        self.parts = drawjs.create_parts()  # tools.mjs:469 (parts)
        self.buttons: dict[str, dict[str, Any]] = {}  # part → action {do, value} (tools.mjs:737)
        self.loose: set[str] = set()  # tools.mjs:473
        self.pinned: set[str] = set()  # tools.mjs:475
        self.fresh: set[str] = set()  # tools.mjs:479 (ink.fresh)
        self.turn: UUID | None = None  # tools.mjs:479 (ink.turn)

    # tools.mjs:476
    def _keep_pinned(self, part_id: str) -> bool:
        return part_id in self.pinned

    # tools.mjs:477 (forgetInk)
    def forget_ink(self) -> None:
        self.parts.clear(self._keep_pinned)
        for part_id in list(self.buttons):
            if part_id not in self.pinned:
                del self.buttons[part_id]
        self.loose = {p for p in self.loose if p in self.pinned}

    # tools.mjs:478 (windowBound)
    def window_bound(self) -> bool:
        return any(p not in self.loose for p in self.parts.ids)

    # tools.mjs:488 (clearScreenInk)
    def clear_screen_ink(self, stop: bool = False, guide_id: UUID | None = None) -> None:
        self.parts.clear_screen()
        for part_id in list(self.buttons):
            if not self.parts.has(part_id):
                del self.buttons[part_id]
        self._publish("overlay.ink_clear", OverlayInkClear(screen=True, stop=stop, guide_id=guide_id))

    # tools.mjs:489 (clearAllInk)
    def clear_all_ink(self) -> None:
        self.forget_ink()
        self._publish("overlay.ink_clear", OverlayInkClear())

    # tools.mjs:491-497 (cancelInk)
    def cancel_ink(self, guide_id: UUID | None = None) -> None:
        if not any(p not in self.fresh and p not in self.pinned for p in self.parts.ids):
            self.clear_all_ink()
            return
        ids = [p for p in self.fresh if self.parts.has(p) and p not in self.pinned]
        for p in ids:
            self.parts.remove(p)
            self.buttons.pop(p, None)
            self.loose.discard(p)
        self.parts.clear_screen()
        for p in list(self.buttons):
            if not self.parts.has(p):
                del self.buttons[p]
        self._publish(
            "overlay.ink_clear", OverlayInkClear(screen=True, stop=True, parts=ids[:64] or None, guide_id=guide_id)
        )

    # tools.mjs:776 (inkEvents.closed)
    def closed(self, part_id: str) -> None:
        self.parts.remove(part_id)
        self.buttons.pop(part_id, None)
        self.loose.discard(part_id)
        self.pinned.discard(part_id)

    # tools.mjs:777 (inkEvents.pinned)
    def pin(self, part_id: str, on: bool) -> None:
        if not on:
            self.pinned.discard(part_id)
        elif self.parts.has(part_id):
            self.pinned.add(part_id)

    def drawn_part(self, part_id: str) -> DrawnPart | None:
        p = self.parts.get(part_id)
        if not p:
            return None
        return DrawnPart(part=part_id, kind=str(p["kind"])[:16], label=part_label(p["desc"]))

    def on_screen(self) -> list[DrawnPart]:
        return [d for d in (self.drawn_part(p) for p in self.parts.ids) if d is not None]
