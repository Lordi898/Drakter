"""Data sources of `GET /api/v1/today`. Each section is isolated: one failing never drops the rest."""

from __future__ import annotations

import importlib
import logging
import sqlite3
from collections.abc import Callable, Iterable, Sequence
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from typing import Any, TypeVar
from zoneinfo import ZoneInfo, available_timezones

from app.services.today_models import (
    SECTION_LIMIT,
    Section,
    TodayAgendaEntry,
    TodayHabit,
    TodayProject,
    TodayTask,
)

log = logging.getLogger("drakter.today")

OPEN_STATUSES = ("pending", "in_progress", "on_hold")
# Prefiltro de «Hoy»: lo que no tenga forma ISO pasa a Python, que lo cuenta como ilegible.
_ISO_INSTANT = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*"
_ISO_DATE = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"


@lru_cache(maxsize=1)
def _valid_zones() -> frozenset[str]:
    """`available_timezones()` recorre tzdata en disco (~25 ms): una vez por proceso."""
    return frozenset(available_timezones())
_PRIORITY_RANK = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
T = TypeVar("T")


def _unavailable(reason: str) -> Section[Any]:
    return Section(status="unavailable", reason=reason)  # type: ignore[arg-type]


def _ready(items: Sequence[T]) -> Section[T]:
    return Section(
        status="ready",
        items=list(items[:SECTION_LIMIT]),
        total=len(items),
        truncated=len(items) > SECTION_LIMIT,
    )


def _missing_tables(conn: sqlite3.Connection, tables: Iterable[str]) -> bool:
    wanted = tuple(tables)
    marks = ",".join("?" * len(wanted))
    found = conn.execute(
        f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ({marks})",  # noqa: S608
        wanted,
    ).fetchone()[0]
    return found < len(wanted)


def _safe(
    name: str,
    conn: sqlite3.Connection,
    tables: Iterable[str],
    produce: Callable[[], Any],
    count: int = 1,
) -> Any:
    """Run `produce`; on any problem return `count` unavailable sections (tuple if > 1)."""

    def fallback(reason: str) -> Any:
        sections = tuple(_unavailable(reason) for _ in range(count))
        return sections if count > 1 else sections[0]

    try:
        if _missing_tables(conn, tables):
            return fallback("not_migrated")
        return produce()
    except ModuleNotFoundError as exc:
        if (exc.name or "").startswith("app."):
            log.warning("today section %s: module missing (%s)", name, exc.name)
            return fallback("module_missing")
        log.exception("today section %s failed", name)
        return fallback("failed")
    except Exception:  # noqa: BLE001 - isolation by design; logged without user data
        log.exception("today section %s failed", name)
        return fallback("failed")


# ----------------------------------------------------------------- time helpers


def parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def local_midnight(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz).astimezone(timezone.utc)


# ------------------------------------------------------------------ tasks/projects


def _task_due(
    due_at: str | None, due_date: str | None, today: date, now: datetime, tz: ZoneInfo, next_start: datetime
) -> tuple[str, int, datetime] | None:
    """Return (bucket, days_overdue, sort_instant) or None when the task is not for today."""
    if due_at is not None:
        instant = parse_instant(due_at)
        if instant < now:
            return "overdue", max((today - instant.astimezone(tz).date()).days, 0), instant
        if instant < next_start:
            return "today", 0, instant
        return None
    if due_date is not None:
        day = date.fromisoformat(due_date)
        if day < today:
            return "overdue", (today - day).days, local_midnight(day, tz)
        if day == today:
            return "today", 0, local_midnight(day, tz)
    return None


def _open_marks() -> str:
    return ",".join("?" * len(OPEN_STATUSES))


def tasks_sections(
    conn: sqlite3.Connection, tz_name: str, now: datetime
) -> tuple[Section[TodayTask], Section[TodayTask]]:
    def produce() -> tuple[Section[TodayTask], Section[TodayTask]]:
        tz = ZoneInfo(tz_name)
        today = now.astimezone(tz).date()
        next_start = local_midnight(today + timedelta(days=1), tz)
        rows = conn.execute(
            f"""SELECT t.id, t.title, t.status, t.priority, t.due_at, t.due_date,
                       t.project_id, p.name, t.parent_task_id
                FROM tasks t
                JOIN entities e ON e.id = t.id
                LEFT JOIN projects p ON p.id = t.project_id
                WHERE t.status IN ({_open_marks()}) AND e.archived_at IS NULL
                  AND ((t.due_at IS NOT NULL AND (t.due_at < ? OR t.due_at NOT GLOB ?))
                    OR (t.due_at IS NULL AND t.due_date IS NOT NULL
                        AND (t.due_date <= ? OR t.due_date NOT GLOB ?)))""",  # noqa: S608
            # Solo descarta lo que seguro no es de hoy: `_task_due` decide el resto. Un día de
            # margen en `due_at` cubre cualquier desfase horario escrito en el texto.
            (*OPEN_STATUSES, (next_start + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
             _ISO_INSTANT, today.isoformat(), _ISO_DATE),
        ).fetchall()
        overdue: list[tuple[tuple[Any, ...], TodayTask]] = []
        due_today: list[tuple[tuple[Any, ...], TodayTask]] = []
        skipped = 0
        for tid, title, status, priority, due_at, due_date, pid, pname, parent in rows:
            try:
                found = _task_due(due_at, due_date, today, now, tz, next_start)
            except ValueError:
                skipped += 1
                continue
            if found is None:
                continue
            bucket, days, instant = found
            task = TodayTask(
                id=tid, title=title, status=status, priority=priority, due_at=due_at,
                due_date=date.fromisoformat(due_date) if due_date else None,
                days_overdue=days, project_id=pid, project_name=pname, parent_task_id=parent,
            )  # fmt: skip
            rank = _PRIORITY_RANK[priority]
            if bucket == "overdue":
                overdue.append(((instant, rank, tid), task))
            else:
                due_today.append(((due_at is None, instant, rank, tid), task))
        if skipped:
            log.warning("today: %d tasks with unreadable due date skipped", skipped)
        overdue.sort(key=lambda pair: pair[0])
        due_today.sort(key=lambda pair: pair[0])
        return _ready([t for _, t in overdue]), _ready([t for _, t in due_today])

    return _safe("tasks", conn, ("tasks", "entities", "projects"), produce, count=2)


def projects_section(conn: sqlite3.Connection, tz_name: str, now: datetime) -> Section[TodayProject]:
    def produce() -> Section[TodayProject]:
        tz = ZoneInfo(tz_name)
        today = now.astimezone(tz).date()
        next_start = local_midnight(today + timedelta(days=1), tz)
        projects = conn.execute(
            """SELECT p.id, p.name, p.priority, p.target_date, p.manual_progress
               FROM projects p JOIN entities e ON e.id = p.id
               WHERE p.status = 'active' AND e.archived_at IS NULL"""
        ).fetchall()
        counts: dict[str, list[int]] = {}  # id -> [open, overdue, done, not_cancelled]
        task_rows = conn.execute(
            """SELECT t.project_id, t.status, t.due_at, t.due_date
               FROM tasks t
               JOIN entities te ON te.id = t.id
               JOIN projects p ON p.id = t.project_id
               JOIN entities pe ON pe.id = p.id
               WHERE p.status = 'active' AND pe.archived_at IS NULL AND te.archived_at IS NULL"""
        ).fetchall()
        for pid, status, due_at, due_date in task_rows:
            c = counts.setdefault(pid, [0, 0, 0, 0])
            if status != "cancelled":
                c[3] += 1
            if status == "completed":
                c[2] += 1
            if status in OPEN_STATUSES:
                c[0] += 1
                try:
                    found = _task_due(due_at, due_date, today, now, tz, next_start)
                except ValueError:
                    found = None
                if found is not None and found[0] == "overdue":
                    c[1] += 1
        items: list[TodayProject] = []
        for pid, name, priority, target, manual in projects:
            opened, overdue, done, active = counts.get(pid, [0, 0, 0, 0])
            if manual is not None:
                progress, source = manual, "manual"
            elif active > 0:
                progress, source = round(100 * done / active), "calculated"
            else:
                progress, source = None, None
            items.append(
                TodayProject(
                    id=pid, name=name, priority=priority,
                    target_date=date.fromisoformat(target) if target else None,
                    progress=progress, progress_source=source,
                    open_tasks=opened, overdue_tasks=overdue,
                )  # fmt: skip
            )
        items.sort(
            key=lambda p: (
                _PRIORITY_RANK[p.priority],
                p.target_date is None,
                p.target_date or date.min,
                p.name,
            )
        )
        return _ready(items)

    return _safe("projects", conn, ("tasks", "entities", "projects"), produce)


# ------------------------------------------------------------------------ agenda


def agenda_section(conn: sqlite3.Connection, tz_name: str, now: datetime) -> Section[TodayAgendaEntry]:
    def produce() -> Section[TodayAgendaEntry]:
        calendar = importlib.import_module("app.services.calendar")
        today = now.astimezone(ZoneInfo(tz_name)).date()
        response = calendar.agenda(conn, today, today + timedelta(days=1), tz_name)
        items = [
            TodayAgendaEntry(
                occurrence_id=i.occurrence_id, source_type=i.source_type, source_id=i.source_id,
                title=i.title, kind=i.kind, all_day=i.all_day,
                display_start=None if i.all_day else i.display_start,
                display_end=None if i.all_day else i.display_end,
                room=i.room, color=i.color,
            )
            for i in response.items
        ]  # fmt: skip
        section = _ready(items)
        if getattr(response, "truncated", False) and not section.truncated:
            section = section.model_copy(update={"truncated": True})
        return section

    return _safe(
        "agenda", conn, ("calendar_events", "time_blocks", "class_sessions", "entities"), produce
    )


# ------------------------------------------------------------------------ habits


def habits_section(conn: sqlite3.Connection, now: datetime) -> Section[TodayHabit]:
    def produce() -> Section[TodayHabit]:
        recurrence = importlib.import_module("app.services.calendar_recurrence")
        valid_zones = _valid_zones()
        habits = conn.execute(
            """SELECT h.id, h.name, h.timezone, h.preferred_local_time, h.start_date, h.end_date
               FROM habits h JOIN entities e ON e.id = h.id
               WHERE h.status = 'active' AND e.archived_at IS NULL"""
        ).fetchall()
        local_today: dict[str, date] = {}
        for hid, _n, zone, _t, _s, _e in habits:
            if zone in valid_zones:
                local_today[hid] = now.astimezone(ZoneInfo(zone)).date()
            else:
                log.warning("today: habit with invalid timezone skipped")
        versions: dict[str, list[tuple[str, str | None, str]]] = {}
        for hid, rrule, valid_from, valid_until in conn.execute(
            "SELECT habit_id, rrule, valid_from, valid_until FROM habit_schedule_versions"
        ):
            versions.setdefault(hid, []).append((valid_from, valid_until, rrule))
        days = sorted({d.isoformat() for d in local_today.values()})
        statuses: dict[tuple[str, str], str] = {}
        if days:
            marks = ",".join("?" * len(days))
            for hid, day, status in conn.execute(
                f"SELECT habit_id, occurrence_date, status FROM habit_records "  # noqa: S608
                f"WHERE occurrence_date IN ({marks})",
                days,
            ):
                statuses[(hid, day)] = status
        rules: dict[str, Any] = {}
        entries: list[tuple[tuple[Any, ...], TodayHabit]] = []
        for hid, name, _zone, preferred, start, end in habits:
            day = local_today.get(hid)
            if day is None or day < date.fromisoformat(start):
                continue
            if end is not None and day > date.fromisoformat(end):
                continue
            scheduled = False
            for valid_from, valid_until, rrule in versions.get(hid, []):
                try:
                    if valid_from > day.isoformat():
                        continue
                    if valid_until is not None and day.isoformat() >= valid_until:
                        continue
                    if rrule not in rules:
                        rules[rrule] = recurrence.parse_rrule(rrule)
                    if recurrence.rule_matches(rules[rrule], date.fromisoformat(valid_from), day):
                        scheduled = True
                        break
                except Exception:  # noqa: BLE001 - one corrupt version must not drop the section
                    log.warning("today: habit schedule version unreadable, skipped")
            if not scheduled:
                continue
            habit = TodayHabit(
                id=hid, name=name, preferred_local_time=preferred,
                today_status=statuses.get((hid, day.isoformat())),
            )  # fmt: skip
            entries.append(((preferred is None, preferred or "", name), habit))
        entries.sort(key=lambda pair: pair[0])
        return _ready([h for _, h in entries])

    return _safe(
        "habits", conn, ("habits", "habit_schedule_versions", "habit_records", "entities"), produce
    )
