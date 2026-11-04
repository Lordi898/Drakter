"""Reglas de hábitos: versiones de frecuencia, registros, historial y estadísticas."""

from __future__ import annotations

import sqlite3
from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel

from app.core.errors import AppError, ErrorDetail
from app.repositories import habits as repo
from app.schemas.habits import (
    HabitCreate,
    HabitHistory,
    HabitHistoryDay,
    HabitOut,
    HabitRecordOut,
    HabitRecordUpsert,
    HabitScheduleVersion,
    HabitStatistics,
    HabitUpdate,
    WeekdayStat,
)
from app.services.calendar_recurrence import (
    Rule,
    normalize_rrule,
    parse_rrule,
    rule_matches,
    today_in,
)
from app.services.habits_calendar_support import (
    RequestContext,
    bounded_limit,
    bounded_offset,
    ensure_timezone,
    insert_entity,
    new_id,
    now_utc,
    record_audit,
    require_entity,
    set_archived,
    touch_entity,
    transaction,
)

ENTITY = "habit"
MAX_RANGE_DAYS = 400
DEFAULT_RANGE_DAYS = 30
_NOT_NULL_FIELDS = ("name", "timezone", "rrule", "status", "reminder_enabled")


class HabitPage(BaseModel):
    items: list[HabitOut]
    total: int


class RecordPage(BaseModel):
    items: list[HabitRecordOut]
    total: int


def _invalid(message: str, field: str | None = None) -> AppError:
    detail = ErrorDetail(field=field, code="invalid", message=message)
    return AppError("validation_error", message, 422, [detail])


# --- programación -----------------------------------------------------------------------


_WEEKDAY_CODES = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")


def _selected_by_rule(rule: Rule, day: date) -> bool:
    """Comprueba BYDAY y BYMONTHDAY en `day`; `rule_matches` da DTSTART por válido siempre."""
    month_days = monthrange(day.year, day.month)[1]
    if rule.bymonthday and not any(
        day.day == (value if value > 0 else month_days + value + 1) for value in rule.bymonthday
    ):
        return False
    if not rule.byday:
        return True
    code = _WEEKDAY_CODES[day.weekday()]
    for entry in rule.byday:
        if entry[-2:] != code:
            continue
        ordinal = int(entry[:-2]) if len(entry) > 2 else 0
        if ordinal == 0:
            return True
        position = (day.day - 1) // 7 + 1 if ordinal > 0 else (month_days - day.day) // 7 + 1
        if position == abs(ordinal):
            return True
    return False


class _Schedule:
    """Versiones de frecuencia ya interpretadas, para decidir si un día está programado."""

    def __init__(self, habit: dict[str, Any], versions: list[dict[str, Any]]) -> None:
        self.start = date.fromisoformat(habit["start_date"])
        self.end = date.fromisoformat(habit["end_date"]) if habit["end_date"] else None
        self.items: list[tuple[Rule, date, date | None]] = [
            (
                parse_rrule(v["rrule"]),
                date.fromisoformat(v["valid_from"]),
                date.fromisoformat(v["valid_until"]) if v["valid_until"] else None,
            )
            for v in versions
        ]

    def scheduled(self, day: date) -> bool:
        if day < self.start or (self.end is not None and day > self.end):
            return False
        for rule, valid_from, valid_until in self.items:
            if valid_from <= day and (valid_until is None or day < valid_until):
                # `valid_from` es solo el ancla: a diferencia de un evento, no es una ocurrencia.
                return _selected_by_rule(rule, day) and rule_matches(rule, valid_from, day)
        return False


def _present(
    conn: sqlite3.Connection, rows: list[dict[str, Any]]
) -> list[HabitOut]:
    ids = [row["id"] for row in rows]
    versions = repo.versions_for(conn, ids)
    outputs: list[HabitOut] = []
    by_day: dict[str, dict[str, str]] = {}
    for row in rows:
        today = today_in(row["timezone"])
        key = today.isoformat()
        if key not in by_day:
            by_day[key] = repo.records_on(conn, ids, key)
        habit_versions = versions[row["id"]]
        schedule = _Schedule(row, habit_versions)
        outputs.append(
            HabitOut(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                timezone=row["timezone"],
                rrule=habit_versions[-1]["rrule"] if habit_versions else "",
                schedule_versions=[
                    HabitScheduleVersion(
                        id=v["id"],
                        rrule=v["rrule"],
                        valid_from=v["valid_from"],
                        valid_until=v["valid_until"],
                    )
                    for v in habit_versions
                ],
                status=row["status"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                goal_note=row["target_note"],
                goal_project_id=row["goal_project_id"],
                preferred_local_time=row["preferred_local_time"],
                reminder_enabled=bool(row["reminder_enabled"]),
                today_scheduled=schedule.scheduled(today),
                today_status=by_day[key].get(row["id"]),
                archived_at=row["archived_at"],
                revision=row["revision"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return outputs


def habit_today(conn: sqlite3.Connection, habit_id: str) -> date:
    return today_in(_load(conn, habit_id)["timezone"])


def _load(conn: sqlite3.Connection, habit_id: str) -> dict[str, Any]:
    row = repo.get_habit(conn, habit_id)
    if row is None:
        raise AppError("not_found", "No existe ese hábito", 404)
    return row


def _check_project(conn: sqlite3.Connection, project_id: str | None) -> None:
    if project_id is not None and not repo.project_exists(conn, project_id):
        raise AppError("not_found", "No existe el proyecto indicado", 404)


# --- CRUD -------------------------------------------------------------------------------


def create_habit(conn: sqlite3.Connection, ctx: RequestContext, data: HabitCreate) -> HabitOut:
    ensure_timezone(data.timezone)
    rrule = normalize_rrule(data.rrule)
    if data.end_date is not None and data.end_date < data.start_date:
        raise _invalid("La fecha de fin no puede ser anterior a la de inicio", "end_date")
    habit_id = new_id()
    with transaction(conn):
        _check_project(conn, data.goal_project_id)
        insert_entity(conn, habit_id, ENTITY)
        repo.insert_habit(
            conn,
            {
                "id": habit_id,
                "name": data.name,
                "description": data.description,
                "timezone": data.timezone,
                "target_note": data.goal_note,
                "preferred_local_time": data.preferred_local_time,
                "goal_project_id": data.goal_project_id,
                "reminder_enabled": int(data.reminder_enabled),
                "status": "active",
                "start_date": data.start_date.isoformat(),
                "end_date": data.end_date.isoformat() if data.end_date else None,
            },
        )
        repo.insert_version(conn, new_id(), habit_id, rrule, data.start_date.isoformat(), now_utc())
        record_audit(
            conn,
            ctx,
            "create_habit",
            entity_type=ENTITY,
            entity_id=habit_id,
            params={
                "habit_id": habit_id,
                "start_date": data.start_date.isoformat(),
                "end_date": data.end_date.isoformat() if data.end_date else None,
                "goal_project_id": data.goal_project_id,
            },
        )
    return _present(conn, [_load(conn, habit_id)])[0]


def get_habit(conn: sqlite3.Connection, ctx: RequestContext, habit_id: str) -> HabitOut:
    return _present(conn, [_load(conn, habit_id)])[0]


def list_habits(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    *,
    include_archived: bool = False,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> HabitPage:
    rows, total = repo.list_habits(
        conn,
        include_archived=include_archived,
        status=status,
        limit=bounded_limit(limit),
        offset=bounded_offset(offset),
    )
    return HabitPage(items=_present(conn, rows), total=total)


def update_habit(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    habit_id: str,
    data: HabitUpdate,
    expected_revision: int | None = None,
) -> HabitOut:
    sent = data.model_fields_set
    for name in _NOT_NULL_FIELDS:
        if name in sent and getattr(data, name) is None:
            raise _invalid("Este dato no puede quedar vacío", name)
    if "timezone" in sent and data.timezone is not None:
        ensure_timezone(data.timezone)
    new_rrule = normalize_rrule(data.rrule) if "rrule" in sent and data.rrule else None
    with transaction(conn):
        habit = _load(conn, habit_id)
        columns: dict[str, Any] = {}
        mapping = {"name": "name", "description": "description", "timezone": "timezone",
                   "status": "status", "goal_note": "target_note"}  # fmt: skip
        for field, column in mapping.items():
            if field in sent:
                columns[column] = getattr(data, field)
        if "end_date" in sent:
            columns["end_date"] = data.end_date.isoformat() if data.end_date else None
            if data.end_date and data.end_date.isoformat() < habit["start_date"]:
                raise _invalid("La fecha de fin no puede ser anterior a la de inicio", "end_date")
        if "goal_project_id" in sent:
            _check_project(conn, data.goal_project_id)
            columns["goal_project_id"] = data.goal_project_id
        if "preferred_local_time" in sent:
            columns["preferred_local_time"] = data.preferred_local_time
        if "reminder_enabled" in sent:
            columns["reminder_enabled"] = int(bool(data.reminder_enabled))

        touch_entity(conn, habit_id, expected_revision)
        repo.update_habit(conn, habit_id, columns)

        effective: date | None = None
        if new_rrule is not None:
            tz = columns.get("timezone", habit["timezone"])
            effective = data.schedule_effective_from or today_in(tz)
            _change_schedule(conn, habit_id, new_rrule, effective)
        record_audit(
            conn,
            ctx,
            "update_habit",
            entity_type=ENTITY,
            entity_id=habit_id,
            params={
                "habit_id": habit_id,
                "status": columns.get("status"),
                "end_date": columns.get("end_date"),
                "schedule_effective_from": effective.isoformat() if effective else None,
            },
            changes={"fields": sorted(sent)},
        )
    return _present(conn, [_load(conn, habit_id)])[0]


def _change_schedule(
    conn: sqlite3.Connection, habit_id: str, rrule: str, effective: date
) -> None:
    current = repo.versions_for(conn, [habit_id])[habit_id][-1]
    valid_from = date.fromisoformat(current["valid_from"])
    if effective < valid_from:
        raise AppError(
            "conflict", "La nueva frecuencia no puede empezar antes de la versión vigente", 409
        )
    if current["rrule"] == rrule:
        return
    if effective == valid_from:
        repo.replace_version_rrule(conn, current["id"], rrule)
        return
    repo.close_version(conn, current["id"], effective.isoformat())
    repo.insert_version(conn, new_id(), habit_id, rrule, effective.isoformat(), now_utc())


def set_habit_archived(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    habit_id: str,
    archived: bool,
    expected_revision: int | None = None,
) -> HabitOut:
    action = "archive_habit" if archived else "unarchive_habit"
    with transaction(conn):
        habit = _load(conn, habit_id)
        if (habit["archived_at"] is not None) != archived:
            if expected_revision is not None and habit["revision"] != expected_revision:
                raise AppError("revision_mismatch", "El elemento cambió desde que se leyó", 412)
            set_archived(conn, habit_id, archived)
        record_audit(
            conn, ctx, action, entity_type=ENTITY, entity_id=habit_id,
            params={"habit_id": habit_id},
        )  # fmt: skip
    return _present(conn, [_load(conn, habit_id)])[0]


# --- registros ----------------------------------------------------------------------------


def upsert_record(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    habit_id: str,
    day: date,
    data: HabitRecordUpsert,
) -> HabitRecordOut:
    with transaction(conn):
        require_entity(conn, habit_id, ENTITY)
        habit = _load(conn, habit_id)
        if day > today_in(habit["timezone"]):
            raise AppError("conflict", "No se puede registrar un día futuro", 409)
        repo.upsert_record(
            conn, new_id(), habit_id, day.isoformat(), data.status, data.note, now_utc()
        )
        record_audit(
            conn,
            ctx,
            "register_habit_completion",
            entity_type=ENTITY,
            entity_id=habit_id,
            params={"habit_id": habit_id, "occurrence_date": day.isoformat(), "status": data.status},
        )
    row = repo.get_record(conn, habit_id, day.isoformat())
    assert row is not None
    return HabitRecordOut(**row)


def _range(
    tz: str, from_date: date | None, to_date: date | None
) -> tuple[date, date]:
    end = to_date or today_in(tz)
    start = from_date or end - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if start > end:
        raise AppError("invalid_query", "El rango de fechas es incorrecto: el inicio es posterior al fin", 400)
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise AppError(
            "invalid_query", f"El rango máximo es de {MAX_RANGE_DAYS} días", 400
        )
    return start, end


def list_records(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    habit_id: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> RecordPage:
    habit = _load(conn, habit_id)
    start, end = _range(habit["timezone"], from_date, to_date)
    rows = repo.records_between(conn, habit_id, start.isoformat(), end.isoformat())
    return RecordPage(items=[HabitRecordOut(**row) for row in rows], total=len(rows))


def history(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    habit_id: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> HabitHistory:
    habit = _load(conn, habit_id)
    start, end = _range(habit["timezone"], from_date, to_date)
    schedule = _Schedule(habit, repo.versions_for(conn, [habit_id])[habit_id])
    records = {
        r["occurrence_date"]: r
        for r in repo.records_between(conn, habit_id, start.isoformat(), end.isoformat())
    }
    days: list[HabitHistoryDay] = []
    day = start
    while day <= end:
        record = records.get(day.isoformat())
        days.append(
            HabitHistoryDay(
                date=day,
                scheduled=schedule.scheduled(day),
                status=record["status"] if record else None,
                note=record["note"] if record else None,
            )
        )
        day += timedelta(days=1)
    return HabitHistory(habit_id=habit_id, from_date=start, to_date=end, days=days)


def statistics(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    habit_id: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> HabitStatistics:
    """Cuenta programados hasta hoy (los días futuros aún no cuentan)."""
    habit = _load(conn, habit_id)
    start, end = _range(habit["timezone"], from_date, to_date)
    today = today_in(habit["timezone"])
    last = min(end, today)
    schedule = _Schedule(habit, repo.versions_for(conn, [habit_id])[habit_id])
    records = {
        r["occurrence_date"]: r["status"]
        for r in repo.records_between(conn, habit_id, start.isoformat(), end.isoformat())
    }
    scheduled = done = skipped = missed = unrecorded = 0
    run = best = 0
    weekday = {n: [0, 0] for n in range(1, 8)}
    day = start
    while day <= last:
        if schedule.scheduled(day):
            status = records.get(day.isoformat())
            scheduled += 1
            weekday[day.isoweekday()][0] += 1
            if status == "done":
                done += 1
                weekday[day.isoweekday()][1] += 1
                run += 1
                best = max(best, run)
            elif status == "skipped":
                skipped += 1
            elif status == "missed":
                missed += 1
                run = 0
            elif day < today:
                unrecorded += 1
                run = 0
            # hoy sin registro: no suma ni rompe la racha
        day += timedelta(days=1)
    divisor = scheduled - skipped
    return HabitStatistics(
        habit_id=habit_id,
        from_date=start,
        to_date=end,
        scheduled=scheduled,
        done=done,
        skipped=skipped,
        missed=missed,
        unrecorded=unrecorded,
        completion_rate=(done / divisor) if divisor > 0 else None,
        current_streak=run,
        best_streak=best,
        by_weekday=[
            WeekdayStat(weekday=n, scheduled=v[0], done=v[1]) for n, v in sorted(weekday.items())
        ],
    )
