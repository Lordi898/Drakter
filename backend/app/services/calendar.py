"""Reglas del calendario: eventos, series con excepciones, bloques de tiempo y agenda.

La serie nunca se materializa: se expande en lectura sobre hora local, siempre dentro de una ventana.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.errors import AppError, ErrorDetail
from app.repositories import calendar as repo
from app.schemas.calendar import (
    AgendaItem,
    AgendaResponse,
    AvailabilityResponse,
    EventCreate,
    EventOut,
    EventUpdate,
    EventWriteResult,
    FreeSlot,
    OccurrenceOverride,
    OverlapGroup,
    RecurrenceExceptionCreate,
    RecurrenceExceptionOut,
    TimeBlockCreate,
    TimeBlockOut,
    TimeBlockUpdate,
    TimeBlockWriteResult,
)
from app.services.calendar_recurrence import (
    expand_dates,
    normalize_rrule,
    parse_rrule,
    rule_matches,
    to_display,
    to_utc,
    utc_iso,
)
from app.services.habits_calendar_support import (
    ConfirmationRef,
    RequestContext,
    bounded_limit,
    confirmed_action,
    bounded_offset,
    deletion_summary,
    ensure_timezone,
    insert_entity,
    new_id,
    now_utc,
    record_audit,
    request_confirmation,
    touch_entity,
    transaction,
)

MAX_WINDOW_DAYS = 370
CONFLICT_SERIES_OCCURRENCES = 50
CONFLICT_SERIES_DAYS = 180
MAX_CONFLICTS = 50
MAX_FREE_SLOTS = 500
_NOT_BUSY = frozenset({"cancelled", "skipped", "done"})
_EVENT_KINDS = ("event", "reminder", "work_session")
_TEMPORAL = ("timezone", "all_day", "local_start", "local_end", "start_date", "end_date_exclusive", "rrule")


class EventPage(BaseModel):
    items: list[EventOut]
    total: int


class TimeBlockPage(BaseModel):
    items: list[TimeBlockOut]
    total: int


class ExceptionList(BaseModel):
    items: list[RecurrenceExceptionOut]
    total: int


class OverlapsResponse(BaseModel):
    timezone: str
    items: list[OverlapGroup]


class FreeSlotsResponse(BaseModel):
    timezone: str
    items: list[FreeSlot]
    truncated: bool


class DeleteResult(BaseModel):
    status: str
    id: str


# ------------------------------------------------------------------ utilidades


@contextmanager
def _atomic(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Una transacción propia, o la ya abierta por el pipeline de confirmaciones."""
    if conn.in_transaction:
        yield conn
    else:
        with transaction(conn):
            yield conn


def _query(message: str) -> AppError:
    return AppError("invalid_query", message, 400)


def _invalid(message: str) -> AppError:
    return AppError("validation_error", message, 422)


def _not_found() -> AppError:
    return AppError("not_found", "No se encuentra el elemento. Puede que se haya eliminado.", 404)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _local_iso(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M")


def _day_start_utc(day: date, tz: str) -> datetime:
    return to_utc(datetime.combine(day, time.min), tz, strict=False)


def _event_row(conn: sqlite3.Connection, event_id: str) -> dict[str, Any]:
    row = repo.get_event(conn, event_id)
    if row is None:
        raise _not_found()
    return row


def _block_row(conn: sqlite3.Connection, block_id: str) -> dict[str, Any]:
    row = repo.get_time_block(conn, block_id)
    if row is None:
        raise _not_found()
    return row


# ------------------------------------------------------------------- derivados


def _derive_event(data: EventCreate) -> dict[str, Any]:
    """Guarda local + zona y calcula los derivados UTC (estricto en la primera ocurrencia)."""
    ensure_timezone(data.timezone)
    rrule = normalize_rrule(data.rrule) if data.rrule else None
    values: dict[str, Any] = {
        "title": data.title, "description": data.description, "location": data.location,
        "reminder_minutes_before": data.reminder_minutes_before, "kind": data.kind,
        "status": data.status, "timezone": data.timezone, "all_day": int(data.all_day),
        "local_start": None, "local_end": None, "start_date": None, "end_date_exclusive": None,
        "starts_at_utc": None, "ends_at_utc": None, "rrule": rrule, "recurrence_until_utc": None,
    }  # fmt: skip
    if data.all_day:
        values["start_date"] = data.start_date.isoformat()  # type: ignore[union-attr]
        values["end_date_exclusive"] = data.end_date_exclusive.isoformat()  # type: ignore[union-attr]
    else:
        assert data.local_start is not None and data.local_end is not None
        local_start, local_end = _dt(data.local_start), _dt(data.local_end)
        starts = to_utc(local_start, data.timezone, strict=True)
        ends = to_utc(local_end, data.timezone, strict=True)
        if ends <= starts:
            raise _invalid("El evento debe terminar después de empezar.")
        values.update(
            local_start=_local_iso(local_start), local_end=_local_iso(local_end),
            starts_at_utc=utc_iso(starts), ends_at_utc=utc_iso(ends),
        )  # fmt: skip
    if rrule:
        until = parse_rrule(rrule).until
        if until is not None:
            values["recurrence_until_utc"] = utc_iso(
                to_utc(datetime.combine(until, time(23, 59, 59)), data.timezone, strict=False)
            )
    return values


def _derive_block(data: TimeBlockCreate) -> dict[str, Any]:
    ensure_timezone(data.timezone)
    local_start, local_end = _dt(data.local_start), _dt(data.local_end)
    starts = to_utc(local_start, data.timezone, strict=True)
    ends = to_utc(local_end, data.timezone, strict=True)
    if ends <= starts:
        raise _invalid("El bloque debe terminar después de empezar.")
    return {
        "title": data.title, "description": data.description, "timezone": data.timezone,
        "local_start": _local_iso(local_start), "local_end": _local_iso(local_end),
        "starts_at_utc": utc_iso(starts), "ends_at_utc": utc_iso(ends), "status": data.status,
        "task_id": data.task_id,
    }  # fmt: skip


def _validated(model: type[BaseModel], payload: dict[str, Any]) -> Any:
    try:
        return model(**payload)
    except ValidationError:
        raise _invalid("Revisa los datos del calendario: alguno no es válido.") from None


# --------------------------------------------------------------- agenda: items


def _item(
    *, source_type: str, source_id: str, title: str, description: str | None, kind: str, status: str,
    all_day: bool, tz: str, occurrence: str, starts: datetime | None, ends: datetime | None,
    start_date: date | None, end_date: date | None, display_tz: str, recurring: bool,
    modified: bool, room: str | None = None, task_id: str | None = None,
    location: str | None = None,
) -> AgendaItem:  # fmt: skip
    return AgendaItem(
        occurrence_id=f"{source_id}:{occurrence}", source_type=source_type,  # type: ignore[arg-type]
        source_id=source_id, title=title, description=description, kind=kind, status=status,
        all_day=all_day, timezone=tz, occurrence_local_start=occurrence,
        starts_at_utc=utc_iso(starts) if starts else None, ends_at_utc=utc_iso(ends) if ends else None,
        start_date=start_date, end_date_exclusive=end_date,
        display_start=to_display(starts, display_tz) if starts else None,
        display_end=to_display(ends, display_tz) if ends else None,
        recurring=recurring, modified=modified, room=room, task_id=task_id, location=location,
    )  # fmt: skip


def _parse_override(raw: str | None) -> OccurrenceOverride | None:
    return OccurrenceOverride(**json.loads(raw)) if raw else None


def _expand_event(
    row: dict[str, Any],
    exceptions: dict[str, tuple[str, str | None]],
    ws: date,
    we: date,
    display_tz: str,
) -> list[AgendaItem]:
    """Ocurrencias de un evento cuya parte visible cae en [ws, we) (fechas en `display_tz`)."""
    tz = row["timezone"]
    all_day = bool(row["all_day"])
    recurring = row["rrule"] is not None
    win_start = _day_start_utc(ws, display_tz)
    win_end = _day_start_utc(we, display_tz)
    if all_day:
        dtstart = date.fromisoformat(row["start_date"])
        span = date.fromisoformat(row["end_date_exclusive"]) - dtstart
        local_time, duration = time.min, span
    else:
        first = _dt(row["local_start"])
        dtstart = first.date()
        local_time, duration = first.time(), _dt(row["local_end"]) - first
    if recurring:
        pad = timedelta(days=duration.days + 2)
        days = expand_dates(parse_rrule(row["rrule"]), dtstart, max(ws - pad, dtstart), we)
    else:
        days = [dtstart]
    out: list[AgendaItem] = []
    for day in days:
        key = day.isoformat() if all_day else _local_iso(datetime.combine(day, local_time))
        exc = exceptions.get(key) if recurring else None
        if exc and exc[0] == "cancelled":
            continue
        override = _parse_override(exc[1]) if exc else None
        title, description, room = row["title"], row["description"], None
        location = row["location"]
        if override:
            title = override.title or title
            description = override.description if override.description is not None else description
            room = override.room
        if all_day:
            end_day = day + span
            if not (day < we and end_day > ws):
                continue
            out.append(_item(
                source_type="calendar_event", source_id=row["id"], title=title,
                description=description, kind=row["kind"], status=row["status"], all_day=True,
                tz=tz, occurrence=key, starts=None, ends=None, start_date=day, end_date=end_day,
                display_tz=display_tz, recurring=recurring, modified=exc is not None, room=room,
                location=location,
            ))  # fmt: skip
            continue
        local_start = datetime.combine(day, local_time)
        local_end = local_start + duration
        if override and override.local_start is not None:
            local_start = _dt(override.local_start)
            local_end = local_start + duration
        if override and override.local_end is not None:
            local_end = _dt(override.local_end)
        starts = to_utc(local_start, tz, strict=False)
        ends = to_utc(local_end, tz, strict=False)
        if not (starts < win_end and ends > win_start):
            continue
        out.append(_item(
            source_type="calendar_event", source_id=row["id"], title=title, description=description,
            kind=row["kind"], status=row["status"], all_day=False, tz=tz, occurrence=key,
            starts=starts, ends=ends, start_date=None, end_date=None, display_tz=display_tz,
            recurring=recurring, modified=exc is not None, room=room, location=location,
        ))  # fmt: skip
    return out


def _block_item(row: dict[str, Any], display_tz: str) -> AgendaItem:
    starts, ends = _parse_utc(row["starts_at_utc"]), _parse_utc(row["ends_at_utc"])
    return _item(
        source_type="time_block", source_id=row["id"], title=row["title"],
        description=row["description"], kind="time_block", status=row["status"], all_day=False,
        tz=row["timezone"], occurrence=_local_iso(_dt(row["local_start"])), starts=starts, ends=ends,
        start_date=None, end_date=None, display_tz=display_tz, recurring=False, modified=False,
        task_id=row["task_id"],
    )  # fmt: skip


def _collect(
    conn: sqlite3.Connection,
    ws: date,
    we: date,
    tz: str,
    types: list[str] | None = None,
    status: str | None = None,
) -> list[AgendaItem]:
    """Items sin ordenar ni limitar. No recurrente: filtro en SQL. Recurrente: expansión en Python."""
    ws_utc, we_utc = utc_iso(_day_start_utc(ws, tz)), utc_iso(_day_start_utc(we, tz))
    items: list[AgendaItem] = []
    kinds = list(_EVENT_KINDS) if types is None else [k for k in types if k in _EVENT_KINDS]
    if kinds:
        rows = repo.events_in_window(
            conn, start_utc=ws_utc, end_utc=we_utc, start_date=ws.isoformat(), end_date=we.isoformat(),
            kinds=None if types is None else kinds,
        )  # fmt: skip
        recurring_ids = [r["id"] for r in rows if r["rrule"] is not None]
        exceptions = repo.exceptions_for_events(conn, recurring_ids) if recurring_ids else {}
        for row in rows:
            items.extend(_expand_event(row, exceptions.get(row["id"], {}), ws, we, tz))
    if types is None or "time_block" in types:
        items.extend(_block_item(r, tz) for r in repo.blocks_in_window(conn, ws_utc, we_utc))
    if types is None or "class" in types:
        from app.services import subjects as subjects_service  # import tardío: evita ciclos

        items.extend(subjects_service.project_class_sessions(conn, ws, we, tz))
    if status is not None:
        return [i for i in items if i.status == status]
    return [i for i in items if i.status != "cancelled"]


def _sort_key(item: AgendaItem) -> tuple[str, str]:
    return (item.display_start or f"{item.start_date}T00:00:00", item.occurrence_id)


def _check_window(from_date: date, to_date: date) -> None:
    if to_date <= from_date:
        raise _query("La fecha final debe ser posterior a la inicial.")
    if (to_date - from_date).days > MAX_WINDOW_DAYS:
        raise _query(f"El rango máximo es de {MAX_WINDOW_DAYS} días.")


def agenda(
    conn: sqlite3.Connection,
    from_date: date,
    to_date: date,
    tz: str,
    types: list[str] | None = None,
    limit: int = 2000,
    status: str | None = None,
) -> AgendaResponse:
    """Eventos (expandidos, con excepciones), bloques y clases. `to` es exclusivo."""
    ensure_timezone(tz)
    _check_window(from_date, to_date)
    items = sorted(_collect(conn, from_date, to_date, tz, types, status), key=_sort_key)
    return AgendaResponse(
        timezone=tz, from_date=from_date, to_date=to_date, items=items[:limit],
        truncated=len(items) > limit,
    )  # fmt: skip


# ------------------------------------------------------------- solapes y huecos


def _busy(item: AgendaItem) -> bool:
    return (
        not item.all_day
        and item.kind != "reminder"
        and item.status not in _NOT_BUSY
        and item.starts_at_utc is not None
        and item.ends_at_utc is not None
    )


def _overlaps(a: AgendaItem, b: AgendaItem) -> bool:
    return a.starts_at_utc < b.ends_at_utc and b.starts_at_utc < a.ends_at_utc  # type: ignore[operator]


def _conflicts(
    conn: sqlite3.Connection, candidates: list[AgendaItem], tz: str, exclude_source: str | None
) -> list[AgendaItem]:
    mine = [c for c in candidates if _busy(c)]
    if not mine:
        return []
    low = date.fromisoformat(min(c.starts_at_utc for c in mine)[:10]) - timedelta(days=1)  # type: ignore[arg-type,type-var]
    high = date.fromisoformat(max(c.ends_at_utc for c in mine)[:10]) + timedelta(days=2)  # type: ignore[arg-type,type-var]
    found: list[AgendaItem] = []
    for other in sorted(_collect(conn, low, high, tz), key=_sort_key):
        if other.source_id == exclude_source or not _busy(other):
            continue
        if any(_overlaps(other, c) for c in mine):
            found.append(other)
            if len(found) >= MAX_CONFLICTS:
                break
    return found


def _event_candidates(row: dict[str, Any], exceptions: dict[str, tuple[str, str | None]]) -> list[AgendaItem]:
    if row["all_day"]:
        return []
    start = _dt(row["local_start"]).date()
    items = _expand_event(row, exceptions, start, start + timedelta(days=CONFLICT_SERIES_DAYS), row["timezone"])
    return sorted(items, key=_sort_key)[:CONFLICT_SERIES_OCCURRENCES]


def overlaps(conn: sqlite3.Connection, from_date: date, to_date: date, tz: str) -> OverlapsResponse:
    ensure_timezone(tz)
    _check_window(from_date, to_date)
    busy = sorted((i for i in _collect(conn, from_date, to_date, tz) if _busy(i)),
                  key=lambda i: (i.starts_at_utc, i.occurrence_id))  # type: ignore[arg-type,return-value]
    groups: list[OverlapGroup] = []
    current: list[AgendaItem] = []
    group_end = ""
    for item in busy:
        if current and item.starts_at_utc < group_end:  # type: ignore[operator]
            current.append(item)
            group_end = max(group_end, item.ends_at_utc)  # type: ignore[type-var]
            continue
        if len(current) > 1:
            groups.append(_group(current, group_end))
        current, group_end = [item], item.ends_at_utc  # type: ignore[assignment]
    if len(current) > 1:
        groups.append(_group(current, group_end))
    return OverlapsResponse(timezone=tz, items=groups)


def _group(items: list[AgendaItem], end: str) -> OverlapGroup:
    return OverlapGroup(
        items=[i.occurrence_id for i in items], starts_at_utc=items[0].starts_at_utc,  # type: ignore[arg-type]
        ends_at_utc=end,
    )  # fmt: skip


def availability(
    conn: sqlite3.Connection, local_start: str, local_end: str, tz: str
) -> AvailabilityResponse:
    ensure_timezone(tz)
    try:
        start_local, end_local = _dt(local_start), _dt(local_end)
    except ValueError:
        raise _query("Las horas deben tener el formato AAAA-MM-DDTHH:MM.") from None
    if start_local.tzinfo or end_local.tzinfo:
        raise _query("Las horas son locales: sin desfase horario.")
    if end_local <= start_local:
        raise _query("El intervalo debe terminar después de empezar.")
    if end_local - start_local > timedelta(days=MAX_WINDOW_DAYS):
        raise _query(f"El rango máximo es de {MAX_WINDOW_DAYS} días.")
    starts = to_utc(start_local, tz, strict=True)
    ends = to_utc(end_local, tz, strict=True)
    probe = _item(
        source_type="time_block", source_id="probe", title="", description=None, kind="time_block",
        status="planned", all_day=False, tz=tz, occurrence=_local_iso(start_local), starts=starts,
        ends=ends, start_date=None, end_date=None, display_tz=tz, recurring=False, modified=False,
    )  # fmt: skip
    conflicts = _conflicts(conn, [probe], tz, None)
    return AvailabilityResponse(
        available=not conflicts, starts_at_utc=utc_iso(starts), ends_at_utc=utc_iso(ends),
        conflicts=conflicts,
    )  # fmt: skip


def free_slots(
    conn: sqlite3.Connection, from_date: date, to_date: date, tz: str, min_minutes: int = 30
) -> FreeSlotsResponse:
    """Huecos libres dentro de [from, to) (días completos en `tz`), sin horario laboral."""
    ensure_timezone(tz)
    _check_window(from_date, to_date)
    start = _day_start_utc(from_date, tz)
    end = _day_start_utc(to_date, tz)
    busy = sorted(
        ((i.starts_at_utc, i.ends_at_utc) for i in _collect(conn, from_date, to_date, tz) if _busy(i)),
        key=lambda p: p[0],  # type: ignore[arg-type,return-value]
    )
    cursor = utc_iso(start)
    limit = utc_iso(end)
    minimum = timedelta(minutes=min_minutes)
    gaps: list[tuple[str, str]] = []

    def add(a: str, b: str) -> None:
        if a < b and _parse_utc(b) - _parse_utc(a) >= minimum:
            gaps.append((a, b))

    for b_start, b_end in busy:
        add(cursor, min(b_start, limit))  # type: ignore[type-var]
        cursor = max(cursor, b_end)  # type: ignore[type-var]
    add(cursor, limit)
    slots = [
        FreeSlot(
            starts_at_utc=a, ends_at_utc=b, display_start=to_display(_parse_utc(a), tz),
            display_end=to_display(_parse_utc(b), tz),
        )
        for a, b in gaps[:MAX_FREE_SLOTS]
    ]  # fmt: skip
    return FreeSlotsResponse(timezone=tz, items=slots, truncated=len(gaps) > MAX_FREE_SLOTS)


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ---------------------------------------------------------------------- eventos


def _no_dependents(conn: sqlite3.Connection, entity_id: str) -> None:
    count = repo.count_relationships(conn, entity_id)
    if count:
        raise AppError(
            "has_dependents",
            "No se puede eliminar porque tiene elementos relacionados. Quita antes las relaciones.",
            409,
            [ErrorDetail(code="has_dependents", message=f"{count} relaciones")],
        )


def _event_params(event_id: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event_id, "kind": row["kind"], "status": row["status"],
        "all_day": bool(row["all_day"]), "recurring": row["rrule"] is not None,
    }  # fmt: skip


def _event_result(conn: sqlite3.Connection, event_id: str) -> EventWriteResult:
    row = _event_row(conn, event_id)
    exceptions = repo.exceptions_for_events(conn, [event_id]).get(event_id, {})
    conflicts = _conflicts(conn, _event_candidates(row, exceptions), row["timezone"], event_id)
    return EventWriteResult(event=EventOut(**row), conflicts=conflicts)


def create_event(conn: sqlite3.Connection, ctx: RequestContext, data: EventCreate) -> EventWriteResult:
    values = _derive_event(data)
    event_id = new_id()
    with transaction(conn):
        insert_entity(conn, event_id, "calendar_event")
        repo.insert_event(conn, {"id": event_id, **values})
        record_audit(
            conn, ctx, "event.create", entity_type="calendar_event", entity_id=event_id,
            params=_event_params(event_id, values),
        )  # fmt: skip
    return _event_result(conn, event_id)


def get_event(conn: sqlite3.Connection, ctx: RequestContext, event_id: str) -> EventOut:
    return EventOut(**_event_row(conn, event_id))


def list_events(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    *,
    include_archived: bool = False,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> EventPage:
    rows, total = repo.list_events(
        conn, include_archived=include_archived, status=status, limit=bounded_limit(limit),
        offset=bounded_offset(offset),
    )  # fmt: skip
    return EventPage(items=[EventOut(**r) for r in rows], total=total)


def update_event(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    event_id: str,
    data: EventUpdate,
    if_match: int | None = None,
) -> EventWriteResult:
    current = _event_row(conn, event_id)
    changes = data.model_dump(exclude_unset=True)
    merged = {
        k: current[k]
        for k in ("title", "description", "location", "reminder_minutes_before", "kind", "status",
                  "timezone", "all_day", "local_start", "local_end", "start_date",
                  "end_date_exclusive", "rrule")
    }  # fmt: skip
    merged["all_day"] = bool(merged["all_day"])
    merged.update(changes)
    if changes.get("all_day") is True:  # cambiar de forma: lo que no se envía de la otra forma se anula
        merged["local_start"] = changes.get("local_start")
        merged["local_end"] = changes.get("local_end")
    elif changes.get("all_day") is False:
        merged["start_date"] = changes.get("start_date")
        merged["end_date_exclusive"] = changes.get("end_date_exclusive")
    validated: EventCreate = _validated(EventCreate, merged)
    values = _derive_event(validated)
    changed_fields = [k for k, v in values.items() if k in repo.EVENT_COLUMNS and v != current.get(k)]
    temporal_changed = any(
        k in changed_fields for k in ("timezone", "all_day", "local_start", "local_end", "start_date",
                                      "end_date_exclusive", "rrule")
    )  # fmt: skip
    if temporal_changed and repo.count_exceptions(conn, event_id):
        raise AppError("conflict", "Esta serie tiene ocurrencias modificadas o canceladas: no se puede cambiar su horario.", 409)
    with transaction(conn):
        touch_entity(conn, event_id, if_match)
        repo.update_event(conn, event_id, {k: values[k] for k in changed_fields})
        record_audit(
            conn, ctx, "event.update", entity_type="calendar_event", entity_id=event_id,
            params=_event_params(event_id, values), changes={"fields": changed_fields},
        )  # fmt: skip
    return _event_result(conn, event_id)


def request_delete_event(conn: sqlite3.Connection, ctx: RequestContext, event_id: str) -> ConfirmationRef:
    row = _event_row(conn, event_id)
    _no_dependents(conn, event_id)
    with transaction(conn):
        return request_confirmation(
            conn, ctx, "delete_event", {"event_id": event_id},
            deletion_summary("evento", row["title"], repo.count_exceptions(conn, event_id)),
            entity_type="calendar_event", entity_id=event_id,
        )  # fmt: skip


@confirmed_action("delete_event")
def execute_delete_event(
    conn: sqlite3.Connection, ctx: RequestContext, args: dict[str, Any]
) -> dict[str, Any]:
    event_id = str(args["event_id"])
    _event_row(conn, event_id)
    _no_dependents(conn, event_id)
    with _atomic(conn):
        repo.delete_event(conn, event_id)
        record_audit(
            conn, ctx, "delete_event", result="success", entity_type="calendar_event",
            entity_id=event_id, params={"event_id": event_id},
        )  # fmt: skip
    return {"status": "deleted", "id": event_id}


# ------------------------------------------------------------------ excepciones


def _exception_out(row: dict[str, Any]) -> RecurrenceExceptionOut:
    return RecurrenceExceptionOut(
        id=row["id"], source_type="calendar_event", source_id=row["event_id"],
        occurrence_local_start=row["occurrence_local_start"], kind=row["kind"],
        override=_parse_override(row["override_json"]), created_at=row["created_at"],
    )  # fmt: skip


def list_exceptions(conn: sqlite3.Connection, ctx: RequestContext, event_id: str) -> ExceptionList:
    _event_row(conn, event_id)
    items = [_exception_out(r) for r in repo.list_exceptions(conn, event_id)]
    return ExceptionList(items=items, total=len(items))


def create_exception(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    event_id: str,
    data: RecurrenceExceptionCreate,
    if_match: int | None = None,
) -> RecurrenceExceptionOut:
    row = _event_row(conn, event_id)
    if row["rrule"] is None:
        raise AppError("conflict", "Este evento no se repite, así que no tiene ocurrencias sueltas.", 409)
    all_day = bool(row["all_day"])
    key = data.occurrence_local_start
    try:
        if all_day:
            day = date.fromisoformat(key)
            matches_time = len(key) == 10
            dtstart = date.fromisoformat(row["start_date"])
        else:
            parsed = datetime.fromisoformat(key)
            day, dtstart = parsed.date(), _dt(row["local_start"]).date()
            matches_time = len(key) == 16 and parsed.time() == _dt(row["local_start"]).time()
    except ValueError:
        raise _invalid("La fecha de la ocurrencia no es válida.") from None
    if not matches_time or day < dtstart or not rule_matches(parse_rrule(row["rrule"]), dtstart, day):
        raise _invalid("Esa fecha no corresponde a ninguna ocurrencia de la serie.")
    if data.override is not None:
        ov = data.override
        if all_day and (ov.local_start or ov.local_end):
            raise _invalid("Un evento de día completo no admite cambiar la hora.")
        if not all_day and (ov.local_start or ov.local_end):
            start = _dt(ov.local_start) if ov.local_start else datetime.combine(day, _dt(row["local_start"]).time())
            end = _dt(ov.local_end) if ov.local_end else start + (_dt(row["local_end"]) - _dt(row["local_start"]))
            if end <= start:
                raise _invalid("La ocurrencia debe terminar después de empezar.")
            to_utc(start, row["timezone"], strict=True)
            to_utc(end, row["timezone"], strict=True)
    if repo.get_exception(conn, event_id, key):
        raise AppError("conflict", "Esa ocurrencia ya estaba modificada o cancelada.", 409)
    override_json = (
        None
        if data.override is None
        else json.dumps(data.override.model_dump(mode="json", exclude_none=True), ensure_ascii=False)
    )
    exception_id = new_id()
    with transaction(conn):
        touch_entity(conn, event_id, if_match)
        repo.insert_exception(
            conn,
            {
                "id": exception_id, "event_id": event_id, "occurrence_local_start": key,
                "kind": data.kind, "override_json": override_json, "created_at": now_utc(),
            },
        )  # fmt: skip
        record_audit(
            conn, ctx, "event.exception.create", entity_type="calendar_event", entity_id=event_id,
            params={"event_id": event_id, "occurrence_local_start": key, "kind": data.kind},
        )  # fmt: skip
    created = repo.get_exception(conn, event_id, key)
    assert created is not None
    return _exception_out(created)


# ---------------------------------------------------------------------- bloques


def _check_task(conn: sqlite3.Connection, task_id: str | None) -> None:
    if task_id is not None and not repo.task_exists(conn, task_id):
        raise AppError("not_found", "No se encuentra la tarea indicada. Puede que se haya eliminado.", 404)


def _block_result(conn: sqlite3.Connection, block_id: str) -> TimeBlockWriteResult:
    row = _block_row(conn, block_id)
    conflicts = _conflicts(conn, [_block_item(row, row["timezone"])], row["timezone"], block_id)
    return TimeBlockWriteResult(time_block=TimeBlockOut(**row), conflicts=conflicts)


def _block_params(block_id: str, row: dict[str, Any]) -> dict[str, Any]:
    return {"time_block_id": block_id, "status": row["status"], "task_id": row["task_id"]}


def create_time_block(
    conn: sqlite3.Connection, ctx: RequestContext, data: TimeBlockCreate
) -> TimeBlockWriteResult:
    values = _derive_block(data)
    _check_task(conn, data.task_id)
    block_id = new_id()
    with transaction(conn):
        insert_entity(conn, block_id, "time_block")
        repo.insert_time_block(conn, {"id": block_id, **values})
        record_audit(
            conn, ctx, "time_block.create", entity_type="time_block", entity_id=block_id,
            params=_block_params(block_id, values),
        )  # fmt: skip
    return _block_result(conn, block_id)


def get_time_block(conn: sqlite3.Connection, ctx: RequestContext, block_id: str) -> TimeBlockOut:
    return TimeBlockOut(**_block_row(conn, block_id))


def list_time_blocks(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    *,
    include_archived: bool = False,
    task_id: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> TimeBlockPage:
    rows, total = repo.list_time_blocks(
        conn, include_archived=include_archived, task_id=task_id, status=status,
        limit=bounded_limit(limit), offset=bounded_offset(offset),
    )  # fmt: skip
    return TimeBlockPage(items=[TimeBlockOut(**r) for r in rows], total=total)


def update_time_block(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    block_id: str,
    data: TimeBlockUpdate,
    if_match: int | None = None,
) -> TimeBlockWriteResult:
    current = _block_row(conn, block_id)
    changes = data.model_dump(exclude_unset=True)
    merged = {k: current[k] for k in ("title", "description", "timezone", "local_start", "local_end",
                                      "status", "task_id")}  # fmt: skip
    merged.update({k: v for k, v in changes.items() if not (v is None and k not in ("task_id", "description"))})
    validated: TimeBlockCreate = _validated(TimeBlockCreate, merged)
    if "task_id" in changes:
        _check_task(conn, validated.task_id)
    values = _derive_block(validated)
    changed_fields = [k for k, v in values.items() if v != current.get(k)]
    with transaction(conn):
        touch_entity(conn, block_id, if_match)
        repo.update_time_block(conn, block_id, {k: values[k] for k in changed_fields})
        record_audit(
            conn, ctx, "time_block.update", entity_type="time_block", entity_id=block_id,
            params=_block_params(block_id, values), changes={"fields": changed_fields},
        )  # fmt: skip
    return _block_result(conn, block_id)


def move_time_block(
    conn: sqlite3.Connection,
    ctx: RequestContext,
    block_id: str,
    local_start: str,
    local_end: str,
    if_match: int | None = None,
) -> TimeBlockWriteResult:
    """Nuevo local_start/local_end; todo lo demás se conserva."""
    return update_time_block(
        conn, ctx, block_id, TimeBlockUpdate(local_start=local_start, local_end=local_end), if_match
    )


def request_delete_time_block(
    conn: sqlite3.Connection, ctx: RequestContext, block_id: str
) -> ConfirmationRef:
    row = _block_row(conn, block_id)
    _no_dependents(conn, block_id)
    with transaction(conn):
        return request_confirmation(
            conn, ctx, "delete_time_block", {"time_block_id": block_id},
            deletion_summary("bloque de tiempo", row["title"]),
            entity_type="time_block", entity_id=block_id,
        )  # fmt: skip


@confirmed_action("delete_time_block")
def execute_delete_time_block(
    conn: sqlite3.Connection, ctx: RequestContext, args: dict[str, Any]
) -> dict[str, Any]:
    block_id = str(args["time_block_id"])
    _block_row(conn, block_id)
    _no_dependents(conn, block_id)
    with _atomic(conn):
        repo.delete_time_block(conn, block_id)
        record_audit(
            conn, ctx, "delete_time_block", result="success", entity_type="time_block",
            entity_id=block_id, params={"time_block_id": block_id},
        )  # fmt: skip
    return {"status": "deleted", "id": block_id}
