"""Contradiction detection. Only detects; never resolves (CONTRACT rule 3)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime

from app.integrations.memory.models import MemoryDraft, MemoryRecord
from app.integrations.memory.pipeline.dedupe import INACTIVE, content_tokens, is_duplicate_text, jaccard
from app.integrations.memory.store_sqlite import normalize_subject

REASON_MAX = 256
_NEGATIONS = frozenset({"no", "nunca", "jamás", "jamas", "tampoco", "ni", "not", "never", "neither", "nor", "cannot"})
_CONTRACTION = re.compile(r"\b(?:don|doesn|didn|isn|aren|wasn|weren|won|can|couldn|shouldn|wouldn|haven|hasn)['’]t\b")
_DONT = re.compile(r"\b(?:dont|doesnt|cant|wont)\b")
_TOKEN = re.compile(r"\w+")
SIMILARITY = 0.6  # on tokens with negations removed


def _polarity_tokens(text: str) -> tuple[bool, frozenset[str]]:
    t = text.casefold()
    negated = bool(_CONTRACTION.search(t) or _DONT.search(t))
    t = _CONTRACTION.sub(" ", t)
    t = _DONT.sub(" ", t)
    words = _TOKEN.findall(t)
    negated = negated or any(w in _NEGATIONS for w in words)
    return negated, content_tokens(" ".join(w for w in words if w not in _NEGATIONS))


def find_contradictions(draft: MemoryDraft, existing: Sequence[MemoryRecord]) -> list[tuple[MemoryRecord, str]]:
    out: list[tuple[MemoryRecord, str]] = []
    d_subject = normalize_subject(draft.subject) if draft.subject else ""
    d_neg, d_tok = _polarity_tokens(draft.content)
    for rec in existing:
        if rec.status in INACTIVE:
            continue
        if is_duplicate_text(draft.content, rec.content):
            continue
        r_neg, r_tok = _polarity_tokens(rec.content)
        if d_neg != r_neg and jaccard(d_tok, r_tok) >= SIMILARITY:
            out.append((rec, "Polaridad opuesta sobre un texto muy parecido (negación)."[:REASON_MAX]))
        elif d_subject and rec.subject and normalize_subject(rec.subject) == d_subject:
            out.append((rec, "Mismo sujeto con contenido distinto."[:REASON_MAX]))
    return out


def is_stale(record: MemoryRecord, now: datetime) -> bool:
    """True when valid_until has passed. Naive datetimes are taken as UTC."""
    vu = record.valid_until
    if vu is None:
        return False
    if vu.tzinfo is None:
        vu = vu.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return vu <= now
