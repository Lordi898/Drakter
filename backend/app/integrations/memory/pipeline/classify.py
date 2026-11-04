"""Rule based classification (MASTER_PLAN §10.4). Pure, no model, no network."""

from __future__ import annotations

import re

from app.integrations.memory.models import MemoryCategory, MemoryKind

# Only single, non nested quantifiers: the input is untrusted (ReDoS).
_PROFILE = re.compile(
    r"\b(?:soy|me llamo|mi nombre|vivo en|nací|trabajo (?:en|como)|estudio|my name|i am|i'm|i live in|i was born|i work (?:at|as|in)|i study)\b"
)
_PREFERENCES = re.compile(
    r"\b(?:prefiero|me gust\w{0,3}|no me gust\w{0,3}|me encant\w{0,3}|odio|favorit[oa]s?|i prefer|i like|i don't like|i do not like|i love|i hate|i dislike|my favou?rite)\b"
)
_PATTERNS = re.compile(
    r"\b(?:siempre|suelo|normalmente|habitualmente|cada (?:día|dia|semana|mes|mañana|noche)|todos los \w{3,12}|always|usually|normally|typically|every (?:day|week|month|morning|night))\b"
)
_CASES = re.compile(
    r"\b(?:el problema|la solución|la solucion|se solucionó|se resolvió|fixed by|the problem|the solution|solved by|workaround)\b"
)
_EVENTS = re.compile(
    r"\b(?:ayer|anoche|hoy|mañana|el (?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)|yesterday|last night|today|tomorrow|on (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|\d{4}-\d{2}-\d{2})\b"
)


def classify(text: str) -> tuple[MemoryKind, MemoryCategory]:
    t = text[:5000].casefold()
    if _PROFILE.search(t):
        return MemoryKind.SEMANTIC, MemoryCategory.PROFILE
    if _PREFERENCES.search(t):
        return MemoryKind.SEMANTIC, MemoryCategory.PREFERENCES
    if _PATTERNS.search(t):
        return MemoryKind.PROCEDURAL, MemoryCategory.PATTERNS
    if _CASES.search(t):
        return MemoryKind.EPISODIC, MemoryCategory.CASES
    if _EVENTS.search(t):
        return MemoryKind.EPISODIC, MemoryCategory.EVENTS
    return MemoryKind.SEMANTIC, MemoryCategory.ENTITIES
