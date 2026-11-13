"""Servicio de proyectos. Cada escritura va en su transacción, con revisión y auditoría."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from typing import Any, Final

import logging

from app.core.errors import AppError, ErrorDetail
from app.repositories import projects as repo
from app.repositories.tasks_shared import (
    audits_failure,
    history_for,
    insert_entity,
    set_archived,
    set_metadata,
    touch_entity,
    write_audit,
)
from app.schemas.projects import (
    ProjectCreate,
    ProjectListQuery,
    ProjectOut,
    ProjectProgress,
    ProjectUpdate,
)
from app.schemas.tasks import HistoryEntry, Page
from app.services.tasks_ports import (
    ConfirmationRequired,
    ConfirmationTarget,
    ServiceContext,
    check_revision,
    conflict,
    new_id,
    not_found,
    transaction,
    utc_now,
)

logger = logging.getLogger(__name__)

_ENTITY = "project"
_PLAIN_FIELDS: Final = (
    "name", "description", "status", "priority", "start_date", "target_date", "manual_progress",
)


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, date) else value


def _split_metadata(raw: Mapping[str, Any]) -> tuple[str | None, dict[str, Any]]:
    visible = dict(raw)
    objective = visible.pop("objective", None)
    return (objective if isinstance(objective, str) else None), visible


def _progress(project_id: str, counts: Mapping[str, int], manual: int | None) -> ProjectProgress:
    total = counts["total"]
    computed = (200 * counts["completed"] + total) // (2 * total) if total else 0
    return ProjectProgress.model_validate(
        {
            "project_id": project_id,
            "total": total,
            "completed": counts["completed"],
            "open": counts["open"],
            "cancelled": counts["cancelled"],
            "overdue": counts["overdue"],
            "percent": computed if manual is None else manual,
            "computed_percent": computed,
            "source": "tasks" if manual is None else "manual",
        }
    )


def _out(row: Mapping[str, Any], counts: Mapping[str, int]) -> ProjectOut:
    objective, visible = _split_metadata(row["metadata"])
    data = {k: row[k] for k in row if k != "metadata"}
    data["objective"] = objective
    data["metadata"] = visible
    data["progress"] = _progress(row["id"], counts, row["manual_progress"])
    return ProjectOut.model_validate(data)


def _load(conn: sqlite3.Connection, project_id: str) -> dict[str, Any]:
    row = repo.get_project(conn, project_id)
    if row is None:
        raise not_found("El proyecto")
    return row


def _out_one(conn: sqlite3.Connection, project_id: str) -> ProjectOut:
    row = _load(conn, project_id)
    counts = repo.progress_counts(conn, [project_id], utc_now())[project_id]
    return _out(row, counts)


def _publish(
    ctx: ServiceContext, kind: str, entities: Sequence[tuple[str, str, int]]
) -> None:
    """Ya hubo `COMMIT`: un fallo del canal de eventos no puede hacer creer que no se guardó."""
    for entity_type, entity_id, revision in entities:
        try:
            ctx.ports.events.publish(
                f"workspace.entity_{kind}",
                {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "revision": revision,
                    "actor_type": ctx.actor.actor_type,
                },
            )
        except Exception:
            logger.exception("event_publish_failed", extra={"entity_id": entity_id})


def _has_dependents(message: str, count: int) -> AppError:
    detail = ErrorDetail(code="has_dependents", message=f"{message} ({count})")
    return AppError("has_dependents", message, 409, [detail])


def _validate_dates(start: str | None, target: str | None) -> None:
    if start and target and start > target:
        raise AppError("validation_error", "La fecha de inicio es posterior a la objetivo.", 422)


def _translate(exc: sqlite3.IntegrityError) -> AppError:
    return conflict("La operación entra en conflicto con los datos existentes.")


@audits_failure("project.create", "project")
def create_project(ctx: ServiceContext, data: ProjectCreate) -> ProjectOut:
    project_id = new_id()
    now = utc_now()
    metadata = {k: v for k, v in data.metadata.items() if k != "objective"}
    if data.objective is not None:
        metadata["objective"] = data.objective
    values: dict[str, Any] = {
        "id": project_id,
        "name": data.name,
        "description": data.description,
        "status": data.status,
        "priority": data.priority,
        "start_date": _iso(data.start_date),
        "target_date": _iso(data.target_date),
        "completed_at": now if data.status == "completed" else None,
        "manual_progress": data.manual_progress,
    }
    changes = {
        key: {"from": None, "to": value}
        for key, value in {**values, "objective": data.objective}.items()
        if key != "id" and value is not None
    }
    try:
        with transaction(ctx.conn):
            insert_entity(ctx.conn, project_id, _ENTITY, now, metadata)
            repo.insert_project(ctx.conn, values)
            write_audit(
                ctx.conn, ctx.actor, action="project.create", entity_type=_ENTITY,
                entity_id=project_id, params={"fields": sorted(changes)}, changes=changes,
            )
    except sqlite3.IntegrityError as exc:
        raise _translate(exc) from exc
    out = _out_one(ctx.conn, project_id)
    _publish(ctx, "created", [(_ENTITY, project_id, out.revision)])
    return out


def get_project(ctx: ServiceContext, project_id: str) -> ProjectOut:
    return _out_one(ctx.conn, project_id)


def list_projects(ctx: ServiceContext, query: ProjectListQuery) -> Page[ProjectOut]:
    page, total = repo.list_projects(
        ctx.conn,
        statuses=query.status,
        priorities=query.priority,
        q=query.q,
        include_archived=query.include_archived,
        sort=query.sort,
        limit=query.limit,
        offset=query.offset,
    )
    counts = repo.progress_counts(ctx.conn, [row["id"] for row in page], utc_now())
    return Page[ProjectOut](
        items=[_out(row, counts[row["id"]]) for row in page],
        total=total,
    )


@audits_failure("project.update", "project")
def update_project(
    ctx: ServiceContext,
    project_id: str,
    data: ProjectUpdate,
    *,
    expected_revision: int | None = None,
) -> ProjectOut:
    sent = data.model_fields_set
    now = utc_now()
    revision: int | None = None
    try:
        with transaction(ctx.conn):
            row = _load(ctx.conn, project_id)
            check_revision(row["revision"], expected_revision)
            if row["archived_at"] is not None:
                raise conflict("El proyecto está archivado; desarchívalo primero.")
            fields: dict[str, Any] = {}
            changes: dict[str, Any] = {}
            for name in _PLAIN_FIELDS:
                if name in sent:
                    new = _iso(getattr(data, name))
                    if new != row[name]:
                        fields[name] = new
                        changes[name] = {"from": row[name], "to": new}
            status = fields.get("status", row["status"])
            if "status" in fields:
                completed_at = now if status == "completed" else None
                fields["completed_at"] = completed_at
                changes["completed_at"] = {"from": row["completed_at"], "to": completed_at}
            _validate_dates(
                fields.get("start_date", row["start_date"]),
                fields.get("target_date", row["target_date"]),
            )
            old_objective, old_visible = _split_metadata(row["metadata"])
            objective = _iso(data.objective) if "objective" in sent else old_objective
            visible = data.metadata if "metadata" in sent and data.metadata is not None else old_visible
            visible = {k: v for k, v in visible.items() if k != "objective"}
            if objective != old_objective:
                changes["objective"] = {"from": old_objective, "to": objective}
            if visible != old_visible:
                changes["metadata"] = {"from": old_visible, "to": visible}
            if not changes:
                return _out_one(ctx.conn, project_id)
            if fields:
                repo.update_project_fields(ctx.conn, project_id, fields)
            if "objective" in changes or "metadata" in changes:
                stored = dict(visible)
                if objective is not None:
                    stored["objective"] = objective
                set_metadata(ctx.conn, project_id, stored)
            touch_entity(ctx.conn, project_id, now)
            write_audit(
                ctx.conn, ctx.actor, action="project.update", entity_type=_ENTITY,
                entity_id=project_id, params={"fields": sorted(changes)}, changes=changes,
            )
            revision = row["revision"] + 1
    except sqlite3.IntegrityError as exc:
        raise _translate(exc) from exc
    if revision is not None:
        _publish(ctx, "updated", [(_ENTITY, project_id, revision)])
    return _out_one(ctx.conn, project_id)


def _set_archived(
    ctx: ServiceContext, project_id: str, archive: bool, expected_revision: int | None
) -> ProjectOut:
    now = utc_now()
    revision: int | None = None
    with transaction(ctx.conn):
        row = _load(ctx.conn, project_id)
        check_revision(row["revision"], expected_revision)
        if (row["archived_at"] is not None) == archive:
            return _out_one(ctx.conn, project_id)
        target = now if archive else None
        set_archived(ctx.conn, [project_id], target)
        touch_entity(ctx.conn, project_id, now)
        write_audit(
            ctx.conn, ctx.actor,
            action="project.archive" if archive else "project.unarchive",
            entity_type=_ENTITY, entity_id=project_id,
            changes={"archived_at": {"from": row["archived_at"], "to": target}},
        )
        revision = row["revision"] + 1
    _publish(ctx, "archived" if archive else "restored", [(_ENTITY, project_id, revision)])
    return _out_one(ctx.conn, project_id)


@audits_failure("project.archive", "project")
def archive_project(
    ctx: ServiceContext, project_id: str, *, expected_revision: int | None = None
) -> ProjectOut:
    return _set_archived(ctx, project_id, True, expected_revision)


@audits_failure("project.unarchive", "project")
def unarchive_project(
    ctx: ServiceContext, project_id: str, *, expected_revision: int | None = None
) -> ProjectOut:
    return _set_archived(ctx, project_id, False, expected_revision)


def _delete_summary(name: str, tasks: int) -> str:
    text = f"Vas a eliminar 1 proyecto: «{name}». Esta acción no se puede deshacer."
    return f"{text} Sus {tasks} tareas se conservan sin proyecto." if tasks else text


@audits_failure("project.delete", "project")
def delete_project(
    ctx: ServiceContext,
    project_id: str,
    *,
    expected_revision: int | None = None,
    pre_confirmed: bool = False,
) -> None:
    if pre_confirmed:
        _execute_delete(ctx, project_id, expected_revision, None)
        return
    row = _load(ctx.conn, project_id)
    check_revision(row["revision"], expected_revision)
    blocking = repo.count_blocking(ctx.conn, project_id)
    if blocking:
        raise _has_dependents("El proyecto sigue vinculado a otros elementos.", blocking)
    tasks = repo.task_revisions_of_project(ctx.conn, project_id)
    targets = [
        ConfirmationTarget(entity_id=project_id, revision=row["revision"]),
        *(ConfirmationTarget(entity_id=tid, revision=rev) for tid, rev in tasks),
    ]
    ticket = ctx.ports.confirmations.request(
        ctx.conn,
        actor=ctx.actor,
        tool_name="delete_project",
        args={"project_id": project_id},
        summary=_delete_summary(row["name"], len(tasks)),
        affected_count=1 + len(tasks),
        targets=targets,
    )
    with transaction(ctx.conn):
        write_audit(
            ctx.conn, ctx.actor, action="project.delete", entity_type=_ENTITY,
            entity_id=project_id, affected_count=1 + len(tasks),
            result="confirmation_required",
        )
    raise ConfirmationRequired(ticket)


def _execute_delete(
    ctx: ServiceContext,
    project_id: str,
    expected_revision: int | None,
    targets: Sequence[ConfirmationTarget] | None,
) -> None:
    now = utc_now()
    try:
        with transaction(ctx.conn):
            row = _load(ctx.conn, project_id)
            check_revision(row["revision"], expected_revision)
            blocking = repo.count_blocking(ctx.conn, project_id)
            if blocking:
                raise _has_dependents("El proyecto sigue vinculado a otros elementos.", blocking)
            if targets is not None:
                current = {(project_id, row["revision"])} | set(
                    repo.task_revisions_of_project(ctx.conn, project_id)
                )
                if current != {(t.entity_id, t.revision) for t in targets}:
                    raise conflict("El proyecto o sus tareas cambiaron desde que se pidió la confirmación.")
            released = repo.release_tasks(ctx.conn, ctx.actor, project_id, now)
            repo.delete_project(ctx.conn, project_id)
            write_audit(
                ctx.conn, ctx.actor, action="project.delete", entity_type=_ENTITY,
                entity_id=project_id, affected_count=1 + len(released),
                params={"project_id": project_id},
                changes={"name": {"from": row["name"], "to": None}},
            )
    except sqlite3.IntegrityError as exc:
        raise _has_dependents("El proyecto sigue vinculado a otros elementos.", 1) from exc
    _publish(ctx, "deleted", [(_ENTITY, project_id, row["revision"])])
    _publish(ctx, "updated", [("task", tid, rev) for tid, rev in released])


def get_project_progress(ctx: ServiceContext, project_id: str) -> ProjectProgress:
    row = _load(ctx.conn, project_id)
    counts = repo.progress_counts(ctx.conn, [project_id], utc_now())[project_id]
    return _progress(project_id, counts, row["manual_progress"])


def project_activity(
    ctx: ServiceContext, project_id: str, *, limit: int, offset: int
) -> Page[HistoryEntry]:
    _load(ctx.conn, project_id)
    ids = [project_id, *repo.task_ids_of_project(ctx.conn, project_id)]
    rows, total = history_for(ctx.conn, ids, limit, offset)
    return Page[HistoryEntry](
        items=[HistoryEntry.model_validate(row) for row in rows], total=total
    )


@audits_failure("project.delete", "project")
def _run_confirmed_delete(
    ctx: ServiceContext, project_id: str, targets: Sequence[ConfirmationTarget]
) -> None:
    _execute_delete(ctx, project_id, None, targets)


def _confirmed_delete(
    ctx: ServiceContext, args: Mapping[str, Any], targets: Sequence[ConfirmationTarget]
) -> None:
    project_id = args.get("project_id")
    if not isinstance(project_id, str) or not any(t.entity_id == project_id for t in targets):
        raise conflict("La confirmación no corresponde a este proyecto.")
    _run_confirmed_delete(ctx, project_id, targets)


PROJECT_CONFIRMABLE: Final[
    dict[str, Callable[[ServiceContext, Mapping[str, Any], Sequence[ConfirmationTarget]], Any]]
] = {"delete_project": _confirmed_delete}
