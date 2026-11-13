"""Feedback intake and deterministic classification.

The text is untrusted data: it is matched against fixed patterns and stored, and
nothing in it is ever interpreted or followed.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from app.core.errors import AppError
from app.services.improvement_models import (
    Category,
    ClassifiedBy,
    FeedbackOrigin,
    Severity,
)
from app.services.improvement_ports import AuditSink, Principal, require_user
from app.services.improvement_store import (
    audited,
    insert_event,
    new_id,
    open_db,
    page,
    transaction,
    utc_now,
)

DEFAULT_CATEGORY: Final[Category] = "procedure_improvement"
DEFAULT_SEVERITY: Final[Severity] = "medium"


def _pattern(*terms: str) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(terms) + r")")


# Patterns run over casefolded text without accents. Ties go to the earlier rule.
_CATEGORY_RULES: Final[tuple[tuple[Category, re.Pattern[str]], ...]] = (
    (
        "bug_fix",
        _pattern(
            r"error", r"fallo", r"falla", r"bug", r"crash", r"excepcion", r"exception",
            r"traceback", r"roto", r"rompe", r"no funciona", r"se cierra", r"se cuelga",
            r"broken", r"fails?\b",
        ),
    ),
    (
        "performance",
        _pattern(
            r"lent[oa]", r"tarda", r"latencia", r"rendimiento", r"consume", r"cpu\b",
            r"ram\b", r"slow", r"lag\b", r"performance", r"freez",
        ),
    ),
    (
        "memory_retrieval",
        _pattern(
            r"olvid", r"recuerd", r"recordar", r"recuper", r"memoria", r"forgot",
            r"remember", r"recall", r"memory",
        ),
    ),
    (
        "skill_fix",
        _pattern(r"skills?\b", r"habilidad", r"herramienta", r"tools?\b"),
    ),
    (
        "interface",
        _pattern(
            r"interfaz", r"pantalla", r"boton", r"ventana", r"panel", r"menu\b", r"tema\b",
            r"animacion", r"personaje", r"ui\b", r"button", r"screen", r"layout",
        ),
    ),
    (
        "communication_preference",
        _pattern(
            r"tono", r"formal", r"breve", r"respuestas? (?:larga|corta)", r"idioma",
            r"emoji", r"tutea", r"hablame", r"tone", r"concise", r"verbose", r"language",
        ),
    ),
    (
        "context_adjustment",
        _pattern(
            r"contexto", r"zona horaria", r"proyecto actual", r"asignatura", r"prioridad",
            r"context", r"timezone", r"priority",
        ),
    ),
    (
        "procedure_improvement",
        _pattern(
            r"proceso", r"procedimiento", r"pasos", r"flujo", r"rutina", r"workflow",
            r"procedure", r"steps\b",
        ),
    ),
)

_SEVERITY_RULES: Final[tuple[tuple[Severity, re.Pattern[str]], ...]] = (
    (
        "critical",
        _pattern(
            r"perdida de datos", r"perdi datos", r"corrup", r"seguridad", r"vulnerab",
            r"no arranca", r"data loss", r"security", r"secret", r"contrasena", r"password",
        ),
    ),
    (
        "high",
        _pattern(
            r"crash", r"se cierra", r"se cuelga", r"bloquea", r"no funciona", r"no puedo",
            r"grave", r"urgente", r"broken", r"blocked", r"urgent",
        ),
    ),
    (
        "low",
        _pattern(
            r"sugerencia", r"sugiero", r"preferiria", r"estaria bien", r"seria mejor",
            r"detalle", r"menor\b", r"minor", r"suggest", r"nice to have", r"would prefer",
        ),
    ),
)


@dataclass(frozen=True)
class Classification:
    category: Category
    severity: Severity
    classified_by: ClassifiedBy


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def classify(text: str) -> Classification:
    """Rules only: the same text always yields the same result."""
    normalized = _normalize(text)
    best: Category | None = None
    best_hits = 0
    for category, pattern in _CATEGORY_RULES:
        hits = sum(1 for _ in pattern.finditer(normalized))
        if hits > best_hits:
            best, best_hits = category, hits
    severity = next(
        (level for level, pattern in _SEVERITY_RULES if pattern.search(normalized)),
        DEFAULT_SEVERITY,
    )
    if best is None:
        return Classification(DEFAULT_CATEGORY, severity, "default")
    return Classification(best, severity, "rules")


def _public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "origin": row["origin"],
        "author_id": row["author_id"],
        "text": row["body"],
        "category": row["category"],
        "severity": row["severity"],
        "classified_by": row["classified_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "untrusted": True,
    }


def _not_found() -> AppError:
    return AppError("feedback_not_found", "El feedback no existe", 404)


def record_feedback(
    db_path: Path,
    principal: Principal,
    text: str,
    audit: AuditSink,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Store feedback; its origin is the caller's identity, never a parameter."""
    feedback_id = new_id()
    with audited(
        audit, principal, "improvement.feedback_record", "improvement_feedback",
        feedback_id, correlation_id,
    ) as scope:
        result = classify(text)
        scope.detail.update(category=result.category, severity=result.severity)
        now = utc_now()
        with open_db(db_path) as conn, transaction(conn):
            conn.execute(
                "INSERT INTO improvement_feedback (id, origin, author_id, body, category,"
                " severity, classified_by, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    feedback_id, principal.kind, principal.id, text, result.category,
                    result.severity, result.classified_by, now, now,
                ),
            )
            insert_event(
                conn,
                event_type="feedback_recorded",
                actor=principal,
                feedback_id=feedback_id,
                detail={"category": result.category, "severity": result.severity},
            )
            row = conn.execute(
                "SELECT * FROM improvement_feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
            return _public(row)


def get_feedback(db_path: Path, feedback_id: str) -> dict[str, Any]:
    with open_db(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM improvement_feedback WHERE id = ?", (feedback_id,)
        ).fetchone()
    if row is None:
        raise _not_found()
    return _public(row)


def list_feedback(
    db_path: Path,
    *,
    limit: int,
    offset: int,
    category: Category | None = None,
    severity: Severity | None = None,
    origin: FeedbackOrigin | None = None,
) -> dict[str, Any]:
    filters = {"category": category, "severity": severity, "origin": origin}
    active = {column: value for column, value in filters.items() if value is not None}
    where = " AND ".join(f"{column} = ?" for column in active) or "1 = 1"
    values = tuple(active.values())
    with open_db(db_path) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM improvement_feedback WHERE {where}", values
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM improvement_feedback WHERE {where}"
            " ORDER BY created_at DESC, id LIMIT ? OFFSET ?",
            (*values, limit, offset),
        ).fetchall()
    return page([_public(row) for row in rows], total, limit, offset)


def reclassify_feedback(
    db_path: Path,
    principal: Principal,
    feedback_id: str,
    category: Category,
    severity: Severity,
    audit: AuditSink,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    with audited(
        audit, principal, "improvement.feedback_reclassify", "improvement_feedback",
        feedback_id, correlation_id,
    ) as scope:
        require_user(principal)
        scope.detail.update(category=category, severity=severity)
        with open_db(db_path) as conn, transaction(conn):
            current = conn.execute(
                "SELECT category, severity FROM improvement_feedback WHERE id = ?",
                (feedback_id,),
            ).fetchone()
            if current is None:
                raise _not_found()
            conn.execute(
                "UPDATE improvement_feedback SET category = ?, severity = ?,"
                " classified_by = 'user', updated_at = ? WHERE id = ?",
                (category, severity, utc_now(), feedback_id),
            )
            insert_event(
                conn,
                event_type="feedback_reclassified",
                actor=principal,
                feedback_id=feedback_id,
                detail={
                    "from_category": current["category"],
                    "to_category": category,
                    "from_severity": current["severity"],
                    "to_severity": severity,
                },
            )
            row = conn.execute(
                "SELECT * FROM improvement_feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
            return _public(row)
