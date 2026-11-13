"""Duplicate detection: normalized content or token Jaccard (es/en stopwords ignored)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.core.text import strip_invisible
from app.integrations.memory.models import MemoryDraft, MemoryRecord, MemoryStatus
from app.integrations.memory.store_sqlite import content_hash

_TOKEN = re.compile(r"\w+")

# Negations are deliberately NOT stopwords: "no me gusta X" must differ from "me gusta X".
STOPWORDS: frozenset[str] = frozenset(
    """el la los las un una unos unas de del al y o u e a en con por para que se su sus lo le les me te mi mis tu tus
    es son soy eres era ser fue ha han he hay muy más mas pero como
    the a an and or of to in on at for with by is are am was were be been it its my your i me this that these those
    as from""".split()
)
INACTIVE = (MemoryStatus.REJECTED, MemoryStatus.SUPERSEDED)


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(strip_invisible(text).casefold())


def content_tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in tokens(text) if t not in STOPWORDS)


def normalized(text: str) -> str:
    return " ".join(tokens(text))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_duplicate_text(a: str, b: str, threshold: float = 0.85) -> bool:
    if normalized(a) == normalized(b):
        return True
    return jaccard(content_tokens(a), content_tokens(b)) >= threshold


def find_duplicate(
    draft: MemoryDraft, existing: Sequence[MemoryRecord], threshold: float = 0.85
) -> MemoryRecord | None:
    """First active (not REJECTED/SUPERSEDED) record equal or near-equal to the draft."""
    h = content_hash(draft.content)
    dt = content_tokens(draft.content)
    dn = normalized(draft.content)
    for rec in existing:
        if rec.status in INACTIVE:
            continue
        if rec.content_hash == h or normalized(rec.content) == dn:
            return rec
        if jaccard(dt, content_tokens(rec.content)) >= threshold:
            return rec
    return None
