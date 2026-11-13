"""Counts, changelog and Markdown export. Reports never carry patches or free text."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from app.core.config import Settings, ensure_private_dir
from app.core.errors import AppError
from app.services.improvement_models import CATEGORIES, SEVERITIES, STATUSES
from app.services.improvement_ports import AuditSink, Principal, require_user
from app.services.improvement_store import (
    audited,
    format_ts,
    new_id,
    open_db,
    page,
)

_UNCLASSIFIED: Final = "unclassified"
_MAX_EXPORT_EVENTS: Final = 500


def normalize_range(start: datetime | None, end: datetime | None) -> tuple[str | None, str | None]:
    if start is not None and end is not None and start > end:
        raise AppError("invalid_range", "El inicio del intervalo es posterior al final", 400)
    return (
        format_ts(start) if start is not None else None,
        format_ts(end) if end is not None else None,
    )


def _counts(
    conn: sqlite3.Connection,
    table: str,
    expression: str,
    keys: tuple[str, ...],
    start: str | None,
    end: str | None,
) -> dict[str, int]:
    """``table`` and ``expression`` are internal constants, never request input."""
    rows = conn.execute(
        f"SELECT {expression}, COUNT(*) FROM {table}"
        " WHERE (?1 IS NULL OR created_at >= ?1) AND (?2 IS NULL OR created_at <= ?2)"
        f" GROUP BY {expression}",
        (start, end),
    ).fetchall()
    return {**dict.fromkeys(keys, 0), **{row[0]: row[1] for row in rows}}


def _summary(conn: sqlite3.Connection, start: str | None, end: str | None) -> dict[str, Any]:
    feedback, proposals = "improvement_feedback", "improvement_proposals"
    by_category = _counts(conn, feedback, "category", CATEGORIES, start, end)
    by_status = _counts(conn, proposals, "status", STATUSES, start, end)
    return {
        "from": start,
        "to": end,
        "feedback": {
            "total": sum(by_category.values()),
            "by_type": by_category,
            "by_severity": _counts(conn, feedback, "severity", SEVERITIES, start, end),
        },
        "proposals": {
            "total": sum(by_status.values()),
            "by_status": by_status,
            "by_type": _counts(
                conn,
                proposals,
                f"COALESCE(category, '{_UNCLASSIFIED}')",
                (*CATEGORIES, _UNCLASSIFIED),
                start,
                end,
            ),
        },
    }


def summary(db_path: Path, start: datetime | None, end: datetime | None) -> dict[str, Any]:
    window = normalize_range(start, end)
    with open_db(db_path) as conn:
        return _summary(conn, *window)


def _public_event(row: sqlite3.Row) -> dict[str, Any]:
    return {**dict(row), "detail": json.loads(row["detail"])}


def changelog(
    db_path: Path, *, limit: int, offset: int, proposal_id: str | None = None
) -> dict[str, Any]:
    where = "proposal_id = ?" if proposal_id is not None else "1 = 1"
    values = (proposal_id,) if proposal_id is not None else ()
    with open_db(db_path) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM improvement_events WHERE {where}", values
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT seq, id, proposal_id, feedback_id, event_type, from_status, to_status,"
            f" actor_kind, actor_id, detail, created_at FROM improvement_events WHERE {where}"
            " ORDER BY seq DESC LIMIT ? OFFSET ?",
            (*values, limit, offset),
        ).fetchall()
    return page([_public_event(row) for row in rows], total, limit, offset)


def _section(title: str, counts: dict[str, int]) -> list[str]:
    return [f"### {title}", "", *(f"- {key}: {value}" for key, value in counts.items()), ""]


def _render(report: dict[str, Any], events: list[sqlite3.Row], generated_at: str) -> str:
    """Only enum values, UUIDs and timestamps from the database reach this text."""
    feedback, proposals = report["feedback"], report["proposals"]
    lines = [
        "# Informe de automejora de Drakter",
        "",
        f"- Generado: {generated_at}",
        f"- Desde: {report['from'] or 'inicio'}",
        f"- Hasta: {report['to'] or 'ahora'}",
        "",
        f"## Feedback ({feedback['total']})",
        "",
        *_section("Por tipo", feedback["by_type"]),
        *_section("Por severidad", feedback["by_severity"]),
        f"## Propuestas ({proposals['total']})",
        "",
        *_section("Por estado", proposals["by_status"]),
        *_section("Por tipo", proposals["by_type"]),
        f"## Historial (últimos {len(events)} eventos)",
        "",
        "| Fecha | Evento | Propuesta | De | A | Actor |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {row['created_at']} | {row['event_type']} | {row['proposal_id'] or '-'}"
        f" | {row['from_status'] or '-'} | {row['to_status'] or '-'} | {row['actor_kind']} |"
        for row in events
    ]
    return "\n".join(lines) + "\n"


def _write_private(path: Path, content: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(content)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def export_report(
    settings: Settings,
    principal: Principal,
    start: datetime | None,
    end: datetime | None,
    audit: AuditSink,
    correlation_id: str | None = None,
) -> dict[str, str]:
    report_id = new_id()
    with audited(
        audit, principal, "improvement.report_export", "improvement_report", report_id,
        correlation_id,
    ):
        require_user(principal)
        window = normalize_range(start, end)
        with open_db(settings.db_path) as conn:
            report = _summary(conn, *window)
            events = conn.execute(
                "SELECT created_at, event_type, proposal_id, from_status, to_status, actor_kind"
                " FROM improvement_events"
                " WHERE (?1 IS NULL OR created_at >= ?1) AND (?2 IS NULL OR created_at <= ?2)"
                " ORDER BY seq DESC LIMIT ?3",
                (*window, _MAX_EXPORT_EVENTS),
            ).fetchall()
        generated_at = datetime.now(UTC)
        stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
        root = settings.data_dir / "improvement"
        directory = root / "reports"
        path = directory / f"improvement-report-{stamp}-{report_id[:8]}.md"
        try:
            ensure_private_dir(root)
            ensure_private_dir(directory)
            _write_private(path, _render(report, events, format_ts(generated_at)))
        except (OSError, ValueError) as exc:
            raise AppError("report_write_failed", "No se pudo escribir el informe", 500) from exc
    return {"id": report_id, "file_name": path.name, "path": str(path)}
