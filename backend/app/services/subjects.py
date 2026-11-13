"""Reglas de asignaturas, sesiones de clase semanales, excepciones y proyección a la agenda.

Las clases nunca se copian a `calendar_events`: `project_class_sessions` las calcula en lectura
desde `class_sessions` + `recurrence_exceptions`. La auditoría solo lleva ids, fechas y estados.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from typing import Any

from pydantic import BaseModel

from app.core.errors import AppError, ErrorDetail
from app.repositories import subjects as repo
from app.schemas.calendar import AgendaItem, OccurrenceOverride, RecurrenceExceptionOut
from app.schemas.subjects import (
    ClassSessionCreate,
    ClassSessionOut,
    ClassSessionUpdate,
    ScheduleExceptionCreate,
    SubjectCreate,
    SubjectOut,
    SubjectUpdate,
    Timetable,
    TimetableEntry,
)
from app.services.calendar_recurrence import to_display, to_utc, utc_iso
from app.services.habits_calendar_support import (
    RequestContext,
    bounded_limit,
    deletion_summary,
    decode_cursor,
    ensure_timezone,
    insert_entity,
    new_id,
    now_utc,
    record_audit,
    require_entity,
    set_archived,
    split_page,
    touch_entity,
    transaction,
)

_DT_FMT = "%Y-%m-%dT%H:%M"


class SubjectList(BaseModel):
    items: list[SubjectOut]
    next_cursor: str | None


class ClassSessionWriteResult(BaseModel):
    """Sesión escrita más las clases que se le pisan: avisa, no bloquea."""

    session: ClassSessionOut
    conflicts: list[ClassSessionOut]


class SessionList(BaseModel):
    items: list[ClassSessionOut]
    next_cursor: str | None


class SubjectResources(BaseModel):
    items: list[dict[str, Any]]


@contextmanager
def _atomic(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Una transacción propia, o la ya abierta por el pipeline de confirmaciones."""
    if conn.in_transaction:
        yield conn
    else:
        with transaction(conn):
            yield conn


# --- asignaturas ---------------------------------------------------------------------------


def _subject_out(conn: sqlite3.Connection, subject_id: str) -> SubjectOut:
    row = repo.get_subject(conn, subject_id)
    if row is None:
        raise AppError("not_found", "No existe esa asignatura", 404)
    return SubjectOut(**row)


def create_subject(conn: sqlite3.Connection, ctx: RequestContext, data: SubjectCreate) -> SubjectOut:
    subject_id = new_id()
    with _atomic(conn):
        insert_entity(conn, subject_id, "subject")
        repo.insert_subject(conn, {"id": subject_id, **data.model_dump()})
        record_audit(
            conn, ctx, "create_subject", entity_type="subject", entity_id=subject_id,
            params={"subject_id": subject_id},
        )  # fmt: skip
    return _subject_out(conn, subject_id)


def get_subject(conn: sqlite3.Connection, ctx: RequestContext, subject_id: str) -> SubjectOut:
    return _subject_out(conn, subject_id)


def list_subjects(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    *,
    include_archived: bool = False,
    limit: int | None = None,
    cursor: str | None = None,
) -> SubjectList:
    size = bounded_limit(limit)
    rows = repo.list_subjects(
        conn, include_archived=include_archived, after=decode_cursor(cursor), limit=size + 1
    )
    page, next_cursor = split_page(rows, size, ("created_at", "id"))
    return SubjectList(items=[SubjectOut(**row) for row in page], next_cursor=next_cursor)


def update_subject(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    subject_id: str,
    data: SubjectUpdate,
    if_match: int | None = None,
) -> SubjectOut:
    columns = {name: getattr(data, name) for name in data.model_fields_set}
    if "name" in columns and columns["name"] is None:
        raise AppError("validation_error", "El nombre no puede quedar vacío", 422)
    with _atomic(conn):
        require_entity(conn, subject_id, "subject")
        touch_entity(conn, subject_id, if_match)
        repo.update_subject(conn, subject_id, columns)
        record_audit(
            conn, ctx, "update_subject", entity_type="subject", entity_id=subject_id,
            params={"subject_id": subject_id}, changes={"fields": sorted(columns)},
        )  # fmt: skip
    return _subject_out(conn, subject_id)


def archive_subject(
    conn: sqlite3.Connection, ctx: RequestContext, subject_id: str, archived: bool
) -> SubjectOut:
    action = "archive_subject" if archived else "unarchive_subject"
    with _atomic(conn):
        require_entity(conn, subject_id, "subject")
        set_archived(conn, subject_id, archived)
        record_audit(
            conn, ctx, action, entity_type="subject", entity_id=subject_id,
            params={"subject_id": subject_id},
        )  # fmt: skip
    return _subject_out(conn, subject_id)


def _dependents(conn: sqlite3.Connection, subject_id: str) -> dict[str, int]:
    return {
        "sessions": repo.count_sessions(conn, subject_id),
        "tasks": repo.count_tasks(conn, subject_id),
        "relationships": repo.count_relationships(conn, subject_id),
    }


def _check_subject_deletable(conn: sqlite3.Connection, subject_id: str) -> None:
    counts = _dependents(conn, subject_id)
    if any(counts.values()):
        raise AppError(
            "has_dependents",
            "La asignatura tiene sesiones, tareas o relaciones vinculadas. "
            "Elimínalas o desvincúlalas antes de borrarla.",
            409,
            [
                ErrorDetail(field=name, code="has_dependents", message=str(count))
                for name, count in counts.items()
                if count
            ],
        )


def deletion_prompt_subject(conn: sqlite3.Connection, subject_id: str) -> str:
    subject = repo.get_subject(conn, subject_id)
    if subject is None:
        raise AppError("not_found", "No existe esa asignatura", 404)
    _check_subject_deletable(conn, subject_id)
    return deletion_summary("asignatura", subject["name"])


def execute_delete_subject(conn: sqlite3.Connection, subject_id: str) -> dict[str, Any]:
    """Corre dentro de la transacción de ActionService, que audita."""
    require_entity(conn, subject_id, "subject")
    _check_subject_deletable(conn, subject_id)
    repo.delete_subject(conn, subject_id)
    return {"deleted": True, "subject_id": subject_id}


def get_subject_resources(
    conn: sqlite3.Connection, ctx: RequestContext, subject_id: str
) -> SubjectResources:
    """Recursos enlazados a la asignatura en `relationships`, en cualquier sentido.

    Solo ids y valores de enumeración: títulos y descripciones son datos no confiables
    y se leen con `get_resource`, que los marca como tales.
    """
    require_entity(conn, subject_id, "subject")
    rows = conn.execute(
        """
        SELECT r.id, r.resource_type, r.availability_status, rel.relationship_type,
               CASE WHEN rel.source_id = :s THEN 'outgoing' ELSE 'incoming' END AS direction
        FROM relationships rel
        JOIN resources r
          ON r.id = CASE WHEN rel.source_id = :s THEN rel.target_id ELSE rel.source_id END
        JOIN entities e ON e.id = r.id
        WHERE (rel.source_id = :s AND rel.target_type = 'resource')
           OR (rel.target_id = :s AND rel.source_type = 'resource')
        ORDER BY rel.created_at, r.id
        LIMIT 200
        """,
        {"s": subject_id},
    ).fetchall()
    keys = ("resource_id", "resource_type", "availability_status", "relationship_type", "direction")
    return SubjectResources(items=[dict(zip(keys, tuple(row), strict=True)) for row in rows])


# --- sesiones de clase ---------------------------------------------------------------------


def _session_out(conn: sqlite3.Connection, session_id: str) -> ClassSessionOut:
    row = repo.get_session(conn, session_id)
    if row is None:
        raise AppError("not_found", "No existe esa sesión de clase", 404)
    return ClassSessionOut(**row)


def _overlaps(candidate: dict[str, Any], other: dict[str, Any]) -> bool:
    if candidate["timezone"] != other["timezone"]:
        return False  # horas locales de zonas distintas no son comparables sin fecha concreta
    if not (
        candidate["starts_local_time"] < other["ends_local_time"]
        and other["starts_local_time"] < candidate["ends_local_time"]
    ):
        return False
    a_until = candidate["valid_until"] or "9999-12-31"
    b_until = other["valid_until"] or "9999-12-31"
    return candidate["valid_from"] <= b_until and other["valid_from"] <= a_until


def _conflicts(
    conn: sqlite3.Connection, candidate: dict[str, Any], exclude_id: str | None
) -> list[ClassSessionOut]:
    others = repo.sessions_same_weekday(conn, candidate["weekday"], exclude_id)
    return [ClassSessionOut(**row) for row in others if _overlaps(candidate, row)]


def _session_params(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": row["id"], "interval_weeks": row["interval_weeks"], "subject_id": row["subject_id"], "weekday": row["weekday"],
        "starts_local_time": row["starts_local_time"], "ends_local_time": row["ends_local_time"],
        "valid_from": row["valid_from"], "valid_until": row["valid_until"],
    }  # fmt: skip


def list_class_sessions(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    subject_id: str,
    include_archived: bool = False,
    limit: int | None = None,
    cursor: str | None = None,
) -> SessionList:
    require_entity(conn, subject_id, "subject")
    size = bounded_limit(limit)
    rows = repo.list_sessions(
        conn, subject_id, include_archived=include_archived,
        after=decode_cursor(cursor, size=3), limit=size + 1,
    )  # fmt: skip
    page, next_cursor = split_page(rows, size, ("weekday", "starts_local_time", "id"))
    return SessionList(items=[ClassSessionOut(**row) for row in page], next_cursor=next_cursor)


def get_class_session(
    conn: sqlite3.Connection, ctx: RequestContext, session_id: str
) -> ClassSessionOut:
    return _session_out(conn, session_id)


def create_class_session(
    conn: sqlite3.Connection, ctx: RequestContext, subject_id: str, data: ClassSessionCreate
) -> ClassSessionWriteResult:
    ensure_timezone(data.timezone)
    session_id = new_id()
    values = {
        "id": session_id,
        "subject_id": subject_id,
        "weekday": data.weekday,
        "starts_local_time": data.starts_local_time,
        "ends_local_time": data.ends_local_time,
        "timezone": data.timezone,
        "valid_from": data.valid_from.isoformat(),
        "valid_until": data.valid_until.isoformat() if data.valid_until else None,
        "interval_weeks": data.interval_weeks,
        "room": data.room,
    }
    with _atomic(conn):
        require_entity(conn, subject_id, "subject")
        conflicts = _conflicts(conn, values, None)
        insert_entity(conn, session_id, "class_session")
        repo.insert_session(conn, values)
        record_audit(
            conn, ctx, "create_class_session", entity_type="class_session", entity_id=session_id,
            params=_session_params(values),
        )  # fmt: skip
    return ClassSessionWriteResult(session=_session_out(conn, session_id), conflicts=conflicts)


def update_class_session(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    session_id: str,
    data: ClassSessionUpdate,
    if_match: int | None = None,
) -> ClassSessionWriteResult:
    columns: dict[str, Any] = {}
    for name in data.model_fields_set:
        value = getattr(data, name)
        if value is None and name not in ("valid_until", "room"):
            raise AppError("validation_error", f"{name} no puede ser nulo", 422)
        if isinstance(value, date):
            value = value.isoformat()
        columns[name] = value
    if "timezone" in columns:
        ensure_timezone(columns["timezone"])
    with _atomic(conn):
        current = repo.get_session(conn, session_id)
        if current is None:
            raise AppError("not_found", "No existe esa sesión de clase", 404)
        merged = {**current, **columns}
        if merged["ends_local_time"] <= merged["starts_local_time"]:
            raise AppError("validation_error", "ends_local_time debe ser posterior a starts_local_time", 422)
        if merged["valid_until"] is not None and merged["valid_until"] < merged["valid_from"]:
            raise AppError("validation_error", "valid_until no puede ser anterior a valid_from", 422)
        touch_entity(conn, session_id, if_match)
        repo.update_session(conn, session_id, columns)
        conflicts = _conflicts(conn, merged, session_id)
        record_audit(
            conn, ctx, "update_class_session", entity_type="class_session", entity_id=session_id,
            params=_session_params(merged), changes={"fields": sorted(columns)},
        )  # fmt: skip
    return ClassSessionWriteResult(session=_session_out(conn, session_id), conflicts=conflicts)


def deletion_prompt_class_session(conn: sqlite3.Connection, session_id: str) -> str:
    row = repo.get_session(conn, session_id)
    if row is None:
        raise AppError("not_found", "No existe esa sesión de clase", 404)
    subject = repo.get_subject(conn, row["subject_id"])
    return deletion_summary("sesión de clase", subject["name"] if subject else "clase")


def execute_delete_class_session(conn: sqlite3.Connection, session_id: str) -> dict[str, Any]:
    """Corre dentro de la transacción de ActionService, que audita."""
    require_entity(conn, session_id, "class_session")
    repo.delete_session(conn, session_id)
    return {"deleted": True, "session_id": session_id}


def create_schedule_exception(
    conn: sqlite3.Connection, ctx: RequestContext, session_id: str, data: ScheduleExceptionCreate
) -> RecurrenceExceptionOut:
    with _atomic(conn):
        row = repo.get_session(conn, session_id)
        if row is None:
            raise AppError("not_found", "No existe esa sesión de clase", 404)
        day = data.occurrence_date
        until = row["valid_until"] or "9999-12-31"
        if (
            day.isoweekday() != row["weekday"]
            or not (row["valid_from"] <= day.isoformat() <= until)
            or not _in_cycle(row, day)
        ):
            raise AppError(
                "validation_error",
                "Esa fecha no es una clase de esta sesión. Elige un día que se imparta.",
                422,
                [
                    ErrorDetail(
                        field="occurrence_date", code="invalid_occurrence",
                        message="No coincide con el día, la vigencia o la frecuencia",
                    )
                ],
            )
        occurrence = f"{day.isoformat()}T{row['starts_local_time']}"
        override = (
            data.override.model_dump_json(exclude_none=True) if data.override is not None else None
        )
        values = {
            "id": new_id(), "class_session_id": session_id, "occurrence_local_start": occurrence,
            "kind": data.kind, "override_json": override, "created_at": now_utc(),
        }  # fmt: skip
        values["id"], values["created_at"] = repo.replace_exception(conn, values)
        record_audit(
            conn, ctx, "create_schedule_exception", entity_type="class_session",
            entity_id=session_id,
            params={"session_id": session_id, "occurrence_date": day.isoformat(), "kind": data.kind},
        )  # fmt: skip
    return RecurrenceExceptionOut(
        id=values["id"], source_type="class_session", source_id=session_id,
        occurrence_local_start=occurrence, kind=data.kind, override=data.override,
        created_at=values["created_at"],
    )  # fmt: skip


# --- horario y proyección ------------------------------------------------------------------


def get_timetable(
    conn: sqlite3.Connection, ctx: RequestContext, on_date: date | None = None
) -> Timetable:
    if on_date is None:
        raise AppError(
            "invalid_query", "Indica la fecha (on) para consultar el horario.", 422,
            [ErrorDetail(field="on", code="required", message="Falta la fecha")],
        )  # fmt: skip
    day = on_date
    rows = repo.timetable_rows(conn, day.isoformat())
    return Timetable(on_date=day, entries=[TimetableEntry(**row) for row in rows])


def _local(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _monday(day: date) -> date:
    return day - timedelta(days=day.isoweekday() - 1)


def _in_cycle(row: dict[str, Any], day: date) -> bool:
    """La semana ISO de `day` dista de la de `valid_from` un múltiplo de interval_weeks."""
    weeks = (_monday(day) - _monday(date.fromisoformat(row["valid_from"]))).days // 7
    return weeks % row["interval_weeks"] == 0


def project_class_sessions(
    conn: sqlite3.Connection, from_date: date, to_date: date, tz: str
) -> list[AgendaItem]:
    """Ocurrencias de clase con inicio (en `tz`) en [from_date, to_date). No escribe nada."""
    one_day = timedelta(days=1)
    first, last = from_date - one_day, to_date + one_day  # las zonas desplazan el día local
    sessions = repo.projectable_sessions(conn, first.isoformat(), last.isoformat())
    exceptions = {
        (row["class_session_id"], row["occurrence_local_start"]): row
        for row in repo.session_exceptions(conn, [row["id"] for row in sessions])
    }
    items: list[AgendaItem] = []
    for row in sessions:
        start_t = time.fromisoformat(row["starts_local_time"])
        end_t = time.fromisoformat(row["ends_local_time"])
        day = max(first, date.fromisoformat(row["valid_from"]))
        stop = min(last, date.fromisoformat(row["valid_until"])) if row["valid_until"] else last
        day += timedelta(days=(row["weekday"] - day.isoweekday()) % 7)
        while day <= stop:
            current = day
            day += timedelta(days=7)
            if not _in_cycle(row, current):
                continue
            original = datetime.combine(current, start_t)
            occurrence = original.strftime(_DT_FMT)
            exc = exceptions.get((row["id"], occurrence))
            if exc is not None and exc["kind"] == "cancelled":
                continue
            local_start, local_end = original, datetime.combine(current, end_t)
            override = OccurrenceOverride()
            if exc is not None and exc["override_json"]:
                override = OccurrenceOverride.model_validate_json(exc["override_json"])
                duration = local_end - local_start
                if override.local_start is not None:
                    local_start = _local(override.local_start)
                    local_end = local_start + duration
                if override.local_end is not None and _local(override.local_end) > local_start:
                    local_end = _local(override.local_end)
            starts = to_utc(local_start, row["timezone"], strict=False)
            ends = to_utc(local_end, row["timezone"], strict=False)
            display_start = to_display(starts, tz)
            if not (from_date <= date.fromisoformat(display_start[:10]) < to_date):
                continue
            items.append(
                AgendaItem(
                    occurrence_id=f"{row['id']}:{occurrence}",
                    source_type="class_session",
                    source_id=row["id"],
                    title=override.title or row["subject_name"],
                    description=override.description or row["subject_description"],
                    kind="class",
                    status="confirmed",
                    all_day=False,
                    timezone=row["timezone"],
                    occurrence_local_start=occurrence,
                    starts_at_utc=utc_iso(starts),
                    ends_at_utc=utc_iso(ends),
                    start_date=None,
                    end_date_exclusive=None,
                    display_start=display_start,
                    display_end=to_display(ends, tz),
                    recurring=True,
                    modified=exc is not None,
                    room=override.room or row["room"],
                    subject_id=row["subject_id"],
                    color=row["color"],
                )
            )
    items.sort(key=lambda item: (item.starts_at_utc or "", item.source_id))
    return items


