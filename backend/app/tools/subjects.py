"""Herramientas Hermes de asignaturas. Solo llaman a servicios; Hermes nunca toca la base."""

from __future__ import annotations

import sqlite3
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.calendar import RecurrenceExceptionOut
from app.schemas.subjects import (
    ClassSessionCreate,
    ClassSessionUpdate,
    ScheduleExceptionCreate,
    SubjectCreate,
    SubjectOut,
    SubjectUpdate,
    Timetable,
)
from app.services import subjects as service
from app.services.habits_calendar_support import RequestContext
from app.tools.habits_calendar_toolspec import RiskClass, ToolSpec, deny_direct, service_handler

_ERRORS = ("not_found", "has_dependents", "revision_mismatch", "invalid_timezone", "validation_error")


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GetSubjectArgs(_Args):
    subject_id: str


class UpdateSubjectArgs(SubjectUpdate):
    subject_id: str


class ListSubjectsArgs(_Args):
    include_archived: bool = False
    limit: int | None = Field(default=None, ge=1, le=200)
    cursor: str | None = None


class CreateClassSessionArgs(ClassSessionCreate):
    subject_id: str


class UpdateClassSessionArgs(ClassSessionUpdate):
    session_id: str


class DeleteClassSessionArgs(_Args):
    session_id: str


class DeleteResult(BaseModel):
    deleted: bool
    session_id: str


class CreateScheduleExceptionArgs(ScheduleExceptionCreate):
    session_id: str


class GetTimetableArgs(_Args):
    on: date = Field(description="Fecha (AAAA-MM-DD) en la que se consulta el horario vigente")


def _create_subject(conn: sqlite3.Connection, ctx: RequestContext, args: SubjectCreate) -> SubjectOut:
    return service.create_subject(conn, ctx, SubjectCreate(**args.model_dump()))


def _get_subject(conn: sqlite3.Connection, ctx: RequestContext, args: GetSubjectArgs) -> SubjectOut:
    return service.get_subject(conn, ctx, args.subject_id)


def _update_subject(
    conn: sqlite3.Connection, ctx: RequestContext, args: UpdateSubjectArgs
) -> SubjectOut:
    fields = args.model_fields_set - {"subject_id"}
    data = SubjectUpdate(**{name: getattr(args, name) for name in fields})
    return service.update_subject(conn, ctx, args.subject_id, data)


def _list_subjects(
    conn: sqlite3.Connection, ctx: RequestContext, args: ListSubjectsArgs
) -> service.SubjectList:
    return service.list_subjects(
        conn, ctx, include_archived=args.include_archived, limit=args.limit, cursor=args.cursor
    )


def _create_class_session(
    conn: sqlite3.Connection, ctx: RequestContext, args: CreateClassSessionArgs
) -> service.ClassSessionWriteResult:
    data = ClassSessionCreate(**args.model_dump(exclude={"subject_id"}))
    return service.create_class_session(conn, ctx, args.subject_id, data)


def _update_class_session(
    conn: sqlite3.Connection, ctx: RequestContext, args: UpdateClassSessionArgs
) -> service.ClassSessionWriteResult:
    fields = args.model_fields_set - {"session_id"}
    data = ClassSessionUpdate(**{name: getattr(args, name) for name in fields})
    return service.update_class_session(conn, ctx, args.session_id, data)


def _create_schedule_exception(
    conn: sqlite3.Connection, ctx: RequestContext, args: CreateScheduleExceptionArgs
) -> RecurrenceExceptionOut:
    data = ScheduleExceptionCreate(**args.model_dump(exclude={"session_id"}))
    return service.create_schedule_exception(conn, ctx, args.session_id, data)


def _get_timetable(
    conn: sqlite3.Connection, ctx: RequestContext, args: GetTimetableArgs
) -> Timetable:
    return service.get_timetable(conn, ctx, args.on)


def _get_subject_resources(
    conn: sqlite3.Connection, ctx: RequestContext, args: GetSubjectArgs
) -> service.SubjectResources:
    return service.get_subject_resources(conn, ctx, args.subject_id)


_SESSION_AUDIT = {
    "weekday": "log", "starts_local_time": "log", "ends_local_time": "log", "timezone": "log",
    "valid_from": "log", "valid_until": "log", "room": "omit",
}  # fmt: skip
# El registro rechaza claves de auditoría que no son argumentos de la herramienta.
_CREATE_SESSION_AUDIT = {"subject_id": "log", **_SESSION_AUDIT}
_UPDATE_SESSION_AUDIT = {"session_id": "log", **_SESSION_AUDIT}

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="create_subject",
        description="Crea una asignatura (nombre, profesor, color hexadecimal #RRGGBB, descripción).",
        domain="subjects",
        args_model=SubjectCreate,
        result_model=SubjectOut,
        permission="subjects.write",
        risk=RiskClass.WRITE,
        handler=service_handler("create_subject", _create_subject),
        errors=_ERRORS,
        audit={"name": "omit", "description": "omit", "teacher": "omit", "color": "log"},
    ),
    ToolSpec(
        name="get_subject",
        description="Devuelve una asignatura por id, con su número de sesiones de clase activas.",
        domain="subjects",
        args_model=GetSubjectArgs,
        result_model=SubjectOut,
        permission="subjects.read",
        risk=RiskClass.READ,
        handler=service_handler("get_subject", _get_subject),
        errors=("not_found",),
        idempotent=True,
        audit={"subject_id": "log"},
    ),
    ToolSpec(
        name="update_subject",
        description="Modifica solo los campos indicados de una asignatura.",
        domain="subjects",
        args_model=UpdateSubjectArgs,
        result_model=SubjectOut,
        permission="subjects.write",
        risk=RiskClass.WRITE,
        handler=service_handler("update_subject", _update_subject),
        errors=_ERRORS,
        audit={
            "subject_id": "log", "name": "omit", "description": "omit", "teacher": "omit",
            "color": "log",
        },
    ),
    ToolSpec(
        name="list_subjects",
        description="Lista asignaturas con paginación por cursor; excluye archivadas salvo que se pida.",
        domain="subjects",
        args_model=ListSubjectsArgs,
        result_model=service.SubjectList,
        permission="subjects.read",
        risk=RiskClass.READ,
        handler=service_handler("list_subjects", _list_subjects),
        errors=(),
        idempotent=True,
        audit={"include_archived": "log", "limit": "log", "cursor": "omit"},
    ),
    ToolSpec(
        name="create_class_session",
        description=(
            "Crea una sesión de clase semanal (weekday 1=lunes..7=domingo, horas locales, zona IANA, "
            "vigencia). Avisa en `conflicts` de solapes con otras clases sin bloquear."
        ),
        domain="subjects",
        args_model=CreateClassSessionArgs,
        result_model=service.ClassSessionWriteResult,
        permission="subjects.write",
        risk=RiskClass.WRITE,
        handler=service_handler("create_class_session", _create_class_session),
        errors=_ERRORS,
        audit=_CREATE_SESSION_AUDIT,
    ),
    ToolSpec(
        name="update_class_session",
        description="Modifica solo los campos indicados de una sesión de clase; avisa de solapes.",
        domain="subjects",
        args_model=UpdateClassSessionArgs,
        result_model=service.ClassSessionWriteResult,
        permission="subjects.write",
        risk=RiskClass.WRITE,
        handler=service_handler("update_class_session", _update_class_session),
        errors=_ERRORS,
        audit=_UPDATE_SESSION_AUDIT,
    ),
    ToolSpec(
        name="delete_class_session",
        description="Elimina una sesión de clase semanal y sus excepciones. Requiere confirmación del usuario.",
        domain="subjects",
        args_model=DeleteClassSessionArgs,
        result_model=DeleteResult,
        permission="subjects.delete",
        risk=RiskClass.CONFIRM,
        handler=deny_direct,
        errors=("not_found",),
        audit={"session_id": "log"},
        summarize=lambda args: "Eliminar una sesión de clase semanal y sus excepciones",
    ),
    ToolSpec(
        name="create_schedule_exception",
        description=(
            "Cancela o modifica una sola ocurrencia de una clase (occurrence_date, kind "
            "cancelled|modified, override con nueva hora, aula o título)."
        ),
        domain="subjects",
        args_model=CreateScheduleExceptionArgs,
        result_model=RecurrenceExceptionOut,
        permission="subjects.write",
        risk=RiskClass.WRITE,
        handler=service_handler("create_schedule_exception", _create_schedule_exception),
        errors=("not_found", "validation_error"),
        audit={"session_id": "log", "occurrence_date": "log", "kind": "log", "override": "omit"},
    ),
    ToolSpec(
        name="get_timetable",
        description="Horario semanal vigente en una fecha, ordenado por día y hora.",
        domain="subjects",
        args_model=GetTimetableArgs,
        result_model=Timetable,
        permission="subjects.read",
        risk=RiskClass.READ,
        handler=service_handler("get_timetable", _get_timetable),
        errors=(),
        idempotent=True,
        audit={"on": "log"},
    ),
    ToolSpec(
        name="get_subject_resources",
        description=(
            "Recursos vinculados a una asignatura por relaciones: id, tipo, disponibilidad y "
            "tipo de relación. Para el título o el contenido usa get_resource."
        ),
        domain="subjects",
        args_model=GetSubjectArgs,
        result_model=service.SubjectResources,
        permission="subjects.read",
        risk=RiskClass.READ,
        handler=service_handler("get_subject_resources", _get_subject_resources),
        errors=("not_found",),
        idempotent=True,
        audit={"subject_id": "log"},
    ),
)
