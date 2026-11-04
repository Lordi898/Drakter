"""Rule based extractor (es/en). Implements the `Extractor` Protocol; no model, no network."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.integrations.memory.models import (
    SUBJECT_MAX_CHARS,
    MemoryDraft,
    Provenance,
    SourceType,
    TrustLevel,
)
from app.integrations.memory.pipeline.classify import classify
from app.integrations.memory.ports import MemoryDraftSeed
from app.integrations.memory.store_sqlite import normalize_subject

MAX_INPUT_CHARS = 20_000
MAX_CANDIDATES = 10
MAX_SENTENCE_CHARS = 400

_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")
_SECRET = re.compile(
    r"sk-[A-Za-z0-9_\-]{8,}|\b(?:password|passwd|contraseña|secret|token|api[_\- ]?key)\b\s*[=:]|\bBearer\s+[A-Za-z0-9._\-]{16,}|\bAKIA[0-9A-Z]{12,}",
    re.IGNORECASE,
)
_HYPOTHETICAL = re.compile(
    r"^(?:si|if|suppose|imagine|imagina|supón|supon|what if|qué pasaría|que pasaria|ojalá|ojala|cuando|when|unless|a menos que)\b"
    r"|\b(?:would|could|might|podría|podria|pudiera|quisiera|sería|seria)\b",
    re.IGNORECASE,
)
_LEAD = re.compile(r"^(?:oye|hey|bueno|well|ok|vale|por cierto|btw)[,:]?\s+", re.IGNORECASE)
_ARTICLE = re.compile(r"^(?:el|la|los|las|un|una|unos|unas|the|a|an|some)\s+", re.IGNORECASE)
_OBJ_END = re.compile(r"\s+(?:a|al|antes que|sobre|más que|mas que|over|to|than|rather than|because|porque|y|and|but|pero)\s+", re.IGNORECASE)
_TRAIL = " \t.,;:!¡\"'()[]"

# (pattern, kind_key, confidence). Each pattern has ONE bounded `.{1,N}` quantifier per group, no nesting.
_REMEMBER = re.compile(r"^(?:recuerda|recuérdame|acuérdate de|ten en cuenta|remember|please remember|keep in mind)\s+(?:que|that)\s+(.{1,400})$", re.IGNORECASE)
_PREFER = re.compile(r"^(?:yo\s+)?(?:prefiero|i\s+(?:really\s+|usually\s+)?prefer)\s+(.{1,300})$", re.IGNORECASE)
_DISLIKE = re.compile(r"^(?:yo\s+)?(?:no\s+me\s+gust(?:a|an)|odio|i\s+(?:don'?t|do\s+not)\s+like|i\s+hate|i\s+dislike)\s+(.{1,300})$", re.IGNORECASE)
_LIKE = re.compile(r"^(?:a\s+mí\s+)?(?:me\s+(?:gust(?:a|an)|encant(?:a|an))|i\s+(?:really\s+)?(?:like|love|enjoy))\s+(.{1,300})$", re.IGNORECASE)
_LIVE = re.compile(r"^(?:yo\s+)?(?:vivo\s+en|i\s+live\s+in)\s+(.{1,200})$", re.IGNORECASE)
_NAME = re.compile(r"^(?:me\s+llamo|my\s+name\s+is|mi\s+nombre\s+es)\s+(.{1,100})$", re.IGNORECASE)
_AM = re.compile(r"^(?:yo\s+)?(?:soy|i\s+am\s+(?:a|an|the)|i'm\s+(?:a|an|the))\s+(.{1,200})$", re.IGNORECASE)
_MY = re.compile(r"^(?:mi|my)\s+(\w{2,30}(?:\s\w{2,30})?)\s+(?:es|son|is|are)\s+(.{1,300})$", re.IGNORECASE)


def _object(raw: str) -> str:
    obj = raw.strip(_TRAIL)
    obj = _OBJ_END.split(obj, maxsplit=1)[0]
    obj = _ARTICLE.sub("", obj.strip(_TRAIL))
    return " ".join(obj.split()[:4])


def _subject(prefix: str, name: str) -> str:
    name = name.strip(_TRAIL)
    if not name:
        return ""
    return normalize_subject(f"{prefix}:{name}")[:SUBJECT_MAX_CHARS]


def _analyze(sentence: str, depth: int = 0) -> tuple[str, str, float] | None:
    """Return (content, subject, confidence) or None."""
    m = _REMEMBER.match(sentence)
    if m and depth == 0:
        inner = m.group(1).strip()
        sub = _analyze(inner, 1)
        return (inner, sub[1] if sub else "", 0.8)
    for rx, prefix, conf in ((_PREFER, "preferencia", 0.75), (_DISLIKE, "preferencia", 0.7), (_LIKE, "preferencia", 0.7)):
        m = rx.match(sentence)
        if m:
            return (sentence, _subject(prefix, _object(m.group(1))), conf)
    m = _LIVE.match(sentence)
    if m:
        return (sentence, _subject("usuario", "ciudad"), 0.7)
    m = _NAME.match(sentence)
    if m:
        return (sentence, _subject("usuario", "nombre"), 0.75)
    m = _AM.match(sentence)
    if m:
        return (sentence, _subject("usuario", "identidad"), 0.6)
    m = _MY.match(sentence)
    if m:
        return (sentence, _subject("usuario", m.group(1)), 0.7)
    return None


class RuleExtractor:
    """Explicit statements only. Documents, tool results and imports never dictate memories."""

    def extract(self, text: str, source: MemoryDraftSeed) -> list[MemoryDraft]:
        try:
            src = SourceType(source.source_type)
        except ValueError:
            return []
        if src not in (SourceType.USER_CONVERSATION, SourceType.AGENT, SourceType.USER_GUI):
            return []
        trust = TrustLevel.DERIVED if src is SourceType.AGENT else TrustLevel.USER_STATED
        now = datetime.now(UTC)
        prov = Provenance(
            source_type=src, source_ref=source.source_ref, session_id=source.session_id, captured_at=now
        )
        drafts: list[MemoryDraft] = []
        for raw in _SPLIT.split(text[:MAX_INPUT_CHARS]):
            if len(drafts) >= MAX_CANDIDATES:
                break
            s = _LEAD.sub("", raw.strip())
            if not s or len(s) > MAX_SENTENCE_CHARS:
                continue
            if "?" in s or "¿" in s or _HYPOTHETICAL.search(s):
                continue
            found = _analyze(s.rstrip(_TRAIL))
            if not found:
                continue
            content, subject, conf = found
            content = content.strip()
            if not content or _SECRET.search(content):
                continue
            if src is SourceType.AGENT:
                conf = max(0.5, conf - 0.1)
            kind, category = classify(content)
            drafts.append(
                MemoryDraft(
                    kind=kind,
                    category=category,
                    subject=subject,
                    content=content,
                    abstract=content[:256],
                    provenance=prov,
                    trust=trust,
                    confidence=conf,
                )
            )
        return drafts
