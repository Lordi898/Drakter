"""Recordatorios locales (D-29): tick de 60 s dentro del backend.

Solo existen con la app abierta: si el backend no corre, nadie avisa. Al arrancar se
recupera lo vencido en las últimas `CATCH_UP` y lo que aún esté por empezar; lo anterior
no se avisa. La API lo expone en `/api/v1/notifications/status` y la GUI lo muestra.

Emisión exactamente una vez: `dedupe_key` con índice único (`ddl_notifications.sql`).
La clave incluye el momento vencido, así que reprogramar genera un aviso nuevo y
reiniciar no repite. Sin ese índice el tick falla y no emite.

Títulos y descripciones son datos del usuario: no van a logs ni al agente, que no
tiene herramientas sobre notificaciones.

Montaje en `app/main.py`, dentro del `lifespan` y tras `migrate`:

    app.state.reminders = ReminderTicker(settings.db_path, publish=<publicador de eventos>)
    await app.state.reminders.start()
    try:
        yield
    finally:
        await app.state.reminders.stop()

`publish(type, payload)` puede ser síncrono o asíncrono. Sin él, la GUI se entera por
su sondeo de `GET /api/v1/notifications?unread=true`.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import sqlite3
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Final, Protocol
from zoneinfo import ZoneInfo

from app.database.connection import connect
from app.repositories import notifications as repo
from app.repositories import notifications_due as due
from app.repositories.notifications import NewNotification, NotificationRow

logger = logging.getLogger("drakter.reminders")

TICK_SECONDS: Final = 60  # D-29
CATCH_UP: Final = timedelta(hours=6)  # Elección: al abrir, lo vencido hace menos de esto.
MAX_PER_TICK: Final = 20  # Lo que no cabe sale en el siguiente tick, más antiguo primero.
MORNING: Final = time(9, 0)  # Hora del aviso de lo que solo tiene fecha.
NOTIFICATION_CREATED: Final = "notification.created"
_MAX_TITLE: Final = 120

Publish = Callable[[str, dict[str, Any]], Awaitable[None] | None]


@dataclass(frozen=True, slots=True)
class ReminderDue:
    """Un aviso que ya toca. `key` identifica el vencimiento concreto, no el elemento."""

    key: str
    kind: str
    title: str
    fire_at: datetime  # Con zona. Ordena la emisión.
    body: str | None = None
    severity: str = "info"
    entity_id: str | None = None


class ReminderSource(Protocol):
    def __call__(
        self, conn: sqlite3.Connection, now: datetime, catch_up: timedelta
    ) -> Iterable[ReminderDue]: ...


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _clip(title: str) -> str:
    return title if len(title) <= _MAX_TITLE else f"{title[: _MAX_TITLE - 1]}…"


def _clock(moment: datetime) -> str:
    return moment.strftime("%H:%M")


def _local_morning(day: date) -> datetime:
    # `astimezone` sobre hora ingenua aplica la zona del sistema con su DST de ese día.
    return datetime.combine(day, MORNING).astimezone()


def _task_sources(conn: sqlite3.Connection, now: datetime, catch_up: timedelta) -> Iterable[ReminderDue]:
    for task in due.tasks_due_at(conn, repo.format_utc(now - catch_up), repo.format_utc(now)):
        assert task.due_at is not None
        moment = _parse_utc(task.due_at)
        yield ReminderDue(
            key=f"task:{task.id}:{task.due_at}",
            kind="reminder.task",
            title=_clip(task.title),
            body=f"Vence a las {_clock(moment.astimezone())}",
            severity="warning",
            entity_id=task.id,
            fire_at=moment,
        )
    # Con solo fecha, el aviso vale todo el día: la tarea sigue a tiempo hasta medianoche.
    today = now.astimezone().date()
    for task in due.tasks_due_on(conn, today.isoformat(), today.isoformat()):
        assert task.due_date is not None
        fire_at = _local_morning(today)
        if fire_at <= now:
            yield ReminderDue(
                key=f"task:{task.id}:{task.due_date}",
                kind="reminder.task",
                title=_clip(task.title),
                body="Vence hoy",
                severity="warning",
                entity_id=task.id,
                fire_at=fire_at,
            )


def _event_sources(conn: sqlite3.Connection, now: datetime, catch_up: timedelta) -> Iterable[ReminderDue]:
    for event in due.timed_events_due(conn, repo.format_utc(now - catch_up), repo.format_utc(now)):
        assert event.starts_at_utc is not None
        start = _parse_utc(event.starts_at_utc)
        yield ReminderDue(
            key=f"event:{event.id}:{event.starts_at_utc}:{event.minutes_before}",
            kind="reminder.event",
            title=_clip(event.title),
            body=f"Empieza a las {_clock(start.astimezone(ZoneInfo(event.timezone)))}",
            entity_id=event.id,
            fire_at=start - timedelta(minutes=event.minutes_before),
        )
    # Margen de un día a cada lado: la fecha UTC y la de la zona del evento pueden diferir.
    today = now.astimezone(UTC).date()
    first = (today - timedelta(days=1)).isoformat()
    last = (today + timedelta(days=1)).isoformat()
    for event in due.all_day_events_near(conn, first, last):
        assert event.start_date is not None
        zone = ZoneInfo(event.timezone)
        day = date.fromisoformat(event.start_date)
        fire_at = datetime.combine(day, MORNING, zone) - timedelta(minutes=event.minutes_before)
        if fire_at <= now and now.astimezone(zone).date() <= day:
            yield ReminderDue(
                key=f"event:{event.id}:{event.start_date}:{event.minutes_before}",
                kind="reminder.event",
                title=_clip(event.title),
                body=f"El {day.strftime('%d/%m')}, todo el día",
                entity_id=event.id,
                fire_at=fire_at,
            )


_sources: dict[str, ReminderSource] = {"tasks": _task_sources, "events": _event_sources}


def register_reminder_source(name: str, source: ReminderSource) -> None:
    """Añade una fuente: ocurrencias recurrentes y hábitos, con la expansión DST de calendario.

    Una fuente lee y entrega avisos con `fire_at <= now`; la emisión y la deduplicación
    son de aquí. Su `key` debe incluir la ocurrencia, p. ej. `occurrence_id`.
    """
    if name in _sources:
        raise ValueError(f"Fuente de recordatorios repetida: {name}")
    _sources[name] = source


def collect_due(conn: sqlite3.Connection, now: datetime) -> tuple[list[ReminderDue], bool]:
    """Junta las fuentes. Una que falle no apaga las demás; devuelve si alguna falló."""
    found: dict[str, ReminderDue] = {}
    failed = False
    for name, source in list(_sources.items()):
        try:
            for item in source(conn, now, CATCH_UP):
                found.setdefault(item.key, item)
        except Exception:
            failed = True
            # Sin texto de la excepción: un error de SQLite puede citar datos.
            logger.error("Fuente de recordatorios fallida", extra={"event": "reminder_source_failed", "source": name})
    return sorted(found.values(), key=lambda item: item.fire_at), failed


def run_tick(db_path: Path, now: datetime) -> tuple[list[NotificationRow], bool]:
    """Un ciclo completo en un hilo: lee vencimientos y escribe lo nuevo."""
    conn = connect(db_path)
    try:
        pending, failed = collect_due(conn, now)
        seen = repo.existing_keys(conn, [item.key for item in pending])
        fresh = [item for item in pending if item.key not in seen][:MAX_PER_TICK]
        created = repo.insert_new(
            conn,
            (
                NewNotification(
                    dedupe_key=item.key,
                    kind=item.kind,
                    title=item.title,
                    body=item.body,
                    severity=item.severity,
                    entity_id=item.entity_id,
                )
                for item in fresh
            ),
            repo.format_utc(now),
        )
    finally:
        conn.close()
    return created, failed


class ReminderTicker:
    """Bucle del tick. Un ciclo fallido se registra y el siguiente lo reintenta."""

    def __init__(self, db_path: Path, *, publish: Publish | None = None) -> None:
        self._db_path = db_path
        self._publish = publish
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self.last_tick_at: str | None = None
        self.last_error: str | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="drakter-reminders")

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is None:
            return
        self._stop.set()
        await task

    async def _loop(self) -> None:
        while not self._stop.is_set():
            await self._tick_once()
            try:
                await asyncio.wait_for(self._stop.wait(), TICK_SECONDS)
            except TimeoutError:
                continue

    async def _tick_once(self) -> None:
        now = datetime.now(UTC)
        try:
            created, failed = await asyncio.to_thread(run_tick, self._db_path, now)
        except Exception as exc:
            self.last_error = "tick_failed"
            logger.error(
                "Tick de recordatorios fallido",
                extra={"event": "reminder_tick_failed", "error_type": type(exc).__name__},
            )
            return
        self.last_tick_at = repo.format_utc(now)
        self.last_error = "source_failed" if failed else None
        for row in created:
            await self._emit(row)

    async def _emit(self, row: NotificationRow) -> None:
        if self._publish is None:
            return
        try:
            result = self._publish(NOTIFICATION_CREATED, {"notification": asdict(row)})
            if inspect.isawaitable(result):
                await result
        except Exception:
            # La fila ya está guardada: la GUI la recoge en su sondeo.
            logger.warning("No se pudo publicar una notificación", extra={"event": "reminder_publish_failed"})
