"""Herramientas Hermes de hábitos. Solo llaman a servicios; nunca a SQL."""

from __future__ import annotations

import sqlite3
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.habits import (
    HabitCreate,
    HabitHistory,
    HabitOut,
    HabitRecordOut,
    HabitRecordUpsert,
    HabitStatistics,
    HabitStatus,
    HabitUpdate,
    RecordStatus,
)
from app.services import habits as service
from app.services.habits_calendar_support import RequestContext
from app.tools.habits_calendar_toolspec import RiskClass, ToolSpec, service_handler


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HabitIdArgs(_Args):
    habit_id: str = Field(description="UUID del hábito")


class UpdateHabitArgs(HabitUpdate):
    habit_id: str = Field(description="UUID del hábito")


class ArchiveHabitArgs(_Args):
    habit_id: str = Field(description="UUID del hábito")
    archived: bool = Field(default=True, description="true archiva; false lo restaura")


class ListHabitsArgs(_Args):
    include_archived: bool = False
    status: HabitStatus | None = None
    limit: int | None = Field(default=None, ge=1, le=200)
    cursor: str | None = None


class RegisterCompletionArgs(_Args):
    habit_id: str = Field(description="UUID del hábito")
    occurrence_date: date | None = Field(
        default=None, description="Día a registrar (AAAA-MM-DD); por defecto, hoy en la zona del hábito"
    )
    status: RecordStatus = "done"
    note: str | None = Field(default=None, max_length=2000)


class RangeArgs(_Args):
    habit_id: str = Field(description="UUID del hábito")
    from_date: date | None = Field(default=None, description="Inicio (AAAA-MM-DD); por defecto, 30 días atrás")
    to_date: date | None = Field(default=None, description="Fin (AAAA-MM-DD); por defecto, hoy")


def _create(conn: sqlite3.Connection, ctx: RequestContext, args: HabitCreate) -> HabitOut:
    return service.create_habit(conn, ctx, args)


def _get(conn: sqlite3.Connection, ctx: RequestContext, args: HabitIdArgs) -> HabitOut:
    return service.get_habit(conn, ctx, args.habit_id)


def _update(conn: sqlite3.Connection, ctx: RequestContext, args: UpdateHabitArgs) -> HabitOut:
    data = HabitUpdate(**args.model_dump(exclude={"habit_id"}, exclude_unset=True))
    return service.update_habit(conn, ctx, args.habit_id, data)


def _archive(conn: sqlite3.Connection, ctx: RequestContext, args: ArchiveHabitArgs) -> HabitOut:
    return service.set_habit_archived(conn, ctx, args.habit_id, args.archived)


def _list(conn: sqlite3.Connection, ctx: RequestContext, args: ListHabitsArgs) -> service.HabitPage:
    return service.list_habits(
        conn, ctx, include_archived=args.include_archived, status=args.status,
        limit=args.limit, cursor=args.cursor,
    )  # fmt: skip


def _register(
    conn: sqlite3.Connection, ctx: RequestContext, args: RegisterCompletionArgs
) -> HabitRecordOut:
    day = args.occurrence_date
    if day is None:
        day = service.habit_today(conn, args.habit_id)
    return service.upsert_record(
        conn, ctx, args.habit_id, day, HabitRecordUpsert(status=args.status, note=args.note)
    )


def _history(conn: sqlite3.Connection, ctx: RequestContext, args: RangeArgs) -> HabitHistory:
    return service.history(conn, ctx, args.habit_id, args.from_date, args.to_date)


def _stats(conn: sqlite3.Connection, ctx: RequestContext, args: RangeArgs) -> HabitStatistics:
    return service.statistics(conn, ctx, args.habit_id, args.from_date, args.to_date)


_NOT_FOUND = ("not_found", "validation_error")

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="create_habit",
        description=(
            "Crea un hábito del usuario con su frecuencia (RRULE, p. ej. FREQ=DAILY o "
            "FREQ=WEEKLY;BYDAY=MO,WE,FR), zona horaria IANA y fecha de inicio."
        ),
        domain="habits",
        args_model=HabitCreate,
        result_model=HabitOut,
        permission="habits.write",
        risk=RiskClass.WRITE,
        handler=service_handler("create_habit", _create),
        errors=("validation_error", "invalid_rrule", "invalid_timezone", "not_found"),
        audit={"start_date": "log", "end_date": "log", "goal_project_id": "log", "name": "omit",
               "description": "omit", "goal_note": "omit"},
    ),
    ToolSpec(
        name="get_habit",
        description="Devuelve un hábito con su frecuencia vigente, versiones y estado de hoy.",
        domain="habits",
        args_model=HabitIdArgs,
        result_model=HabitOut,
        permission="habits.read",
        risk=RiskClass.READ,
        handler=service_handler("get_habit", _get),
        errors=_NOT_FOUND,
        idempotent=True,
        audit={"habit_id": "log"},
    ),
    ToolSpec(
        name="update_habit",
        description=(
            "Edita un hábito. Solo se cambia lo indicado. Cambiar `rrule` abre una versión nueva de "
            "la frecuencia desde `schedule_effective_from` (por defecto hoy) sin tocar los registros."
        ),
        domain="habits",
        args_model=UpdateHabitArgs,
        result_model=HabitOut,
        permission="habits.write",
        risk=RiskClass.WRITE,
        handler=service_handler("update_habit", _update),
        errors=("validation_error", "not_found", "conflict", "invalid_rrule", "invalid_timezone"),
        audit={"habit_id": "log", "status": "log", "end_date": "log",
               "schedule_effective_from": "log", "name": "omit", "description": "omit",
               "goal_note": "omit"},
    ),
    ToolSpec(
        name="archive_habit",
        description=(
            "Archiva un hábito (reversible; no borra nada ni sus registros). "
            "Con archived=false lo restaura."
        ),
        domain="habits",
        args_model=ArchiveHabitArgs,
        result_model=HabitOut,
        permission="habits.write",
        risk=RiskClass.WRITE,
        handler=service_handler("archive_habit", _archive),
        errors=_NOT_FOUND,
        idempotent=True,
        audit={"habit_id": "log", "archived": "log"},
    ),
    ToolSpec(
        name="list_habits",
        description="Lista los hábitos del usuario (sin archivados salvo include_archived=true), paginados.",
        domain="habits",
        args_model=ListHabitsArgs,
        result_model=service.HabitPage,
        permission="habits.read",
        risk=RiskClass.READ,
        handler=service_handler("list_habits", _list),
        errors=("validation_error", "invalid_cursor"),
        idempotent=True,
        audit={"include_archived": "log", "status": "log", "limit": "log", "cursor": "omit"},
    ),
    ToolSpec(
        name="register_habit_completion",
        description=(
            "Registra el resultado de un hábito en un día (done, skipped o missed). Si ya hay registro "
            "ese día lo actualiza. No admite días futuros."
        ),
        domain="habits",
        args_model=RegisterCompletionArgs,
        result_model=HabitRecordOut,
        permission="habits.write",
        risk=RiskClass.WRITE,
        handler=service_handler("register_habit_completion", _register),
        errors=("validation_error", "not_found", "conflict"),
        idempotent=True,
        audit={"habit_id": "log", "occurrence_date": "log", "status": "log", "note": "omit"},
    ),
    ToolSpec(
        name="get_habit_history",
        description=(
            "Historial día a día de un hábito: si estaba programado y su estado. "
            "Máximo 400 días; por defecto, los últimos 30."
        ),
        domain="habits",
        args_model=RangeArgs,
        result_model=HabitHistory,
        permission="habits.read",
        risk=RiskClass.READ,
        handler=service_handler("get_habit_history", _history),
        errors=("validation_error", "not_found", "window_too_large"),
        idempotent=True,
        audit={"habit_id": "log", "from_date": "log", "to_date": "log"},
    ),
    ToolSpec(
        name="get_habit_statistics",
        description=(
            "Estadísticas de un hábito en un rango: programados, hechos, saltados, sin registrar, "
            "tasa de cumplimiento y rachas. Máximo 400 días; por defecto, los últimos 30."
        ),
        domain="habits",
        args_model=RangeArgs,
        result_model=HabitStatistics,
        permission="habits.read",
        risk=RiskClass.READ,
        handler=service_handler("get_habit_statistics", _stats),
        errors=("validation_error", "not_found", "window_too_large"),
        idempotent=True,
        audit={"habit_id": "log", "from_date": "log", "to_date": "log"},
    ),
)
