"""Reglas de dominio de tareas. REST y las herramientas de Hermes pasan siempre por aquí.

La confirmación la decide este módulo: calcula alcance y resumen fuera de la transacción, pide
la confirmación y, al ejecutar, vuelve a calcular el alcance dentro de la transacción. Así un
alcance que crece entre medias no se ejecuta sin confirmar.
"""

from __future__ import annotations

import logging
import math
import sqlite3
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Final, NoReturn
from uuid import UUID

from app.core.errors import AppError, ErrorDetail
from app.repositories import tasks as repo
from app.repositories.tasks_shared import (
    add_dependency,
    audits_failure,
    dependencies_of,
    dependency_would_cycle,
    dependents_of,
    entity_exists,
    history_for,
    insert_entity,
    list_tags,
    normalize_tag,
    remove_all_dependencies,
    remove_dependency,
    replace_tags,
    set_archived,
    set_metadata,
    tags_for,
    touch_entity,
    write_audit,
)
from app.schemas.tasks import (
    MAX_LIMIT,
    MAX_OFFSET,
    HistoryEntry,
    Page,
    SubtaskCreate,
    TagOut,
    TaskCompleteRequest,
    TaskCreate,
    TaskDetail,
    TaskListQuery,
    TaskNode,
    TaskOut,
    TaskRef,
    TaskUpdate,
    format_timestamp,
)
from app.services.tasks_ports import (
    BULK_THRESHOLD,
    MAX_TASK_DEPTH,
    ConfirmationRequired,
    ConfirmationTarget,
    ServiceContext,
    check_revision,
    conflict,
    hierarchy_cycle,
    new_id,
    not_found,
    transaction,
    utc_now,
)

logger = logging.getLogger("drakter.tasks")

_TASK: Final = "La tarea"
_SCOPE_CHANGED: Final = (
    "El alcance de la operación cambió desde que se confirmó. Vuelve a intentarlo."
)
_OWN_DESCENDANT: Final = "Una tarea no puede colgar de sí misma ni de un descendiente."
_DEPENDENCY_CYCLE: Final = "Esa dependencia crearía un ciclo."
_COMPLETED_PARENT: Final = "La tarea padre está completada: no admite subtareas abiertas."
_MAX_LABEL: Final = 80

Row = dict[str, Any]
_Change = dict[str, dict[str, Any]]


# --- Piezas comunes ---------------------------------------------------------------------------


@contextmanager
def _write(ctx: ServiceContext) -> Iterator[None]:
    """Transacción que traduce las barreras de la base a `conflict` sin filtrar SQL."""
    try:
        with transaction(ctx.conn):
            yield
    except sqlite3.IntegrityError as exc:
        if "task_hierarchy_cycle" in str(exc):
            raise hierarchy_cycle(_OWN_DESCENDANT) from exc
        if "relationship_cycle" in str(exc):
            raise hierarchy_cycle(_DEPENDENCY_CYCLE) from exc
        raise conflict("La operación entra en conflicto con los datos existentes.") from exc


def _str(value: UUID | str | None) -> str | None:
    return None if value is None else str(value)


def _load(conn: sqlite3.Connection, task_id: str) -> Row:
    row = repo.get_row(conn, task_id)
    if row is None:
        raise not_found(_TASK)
    return row


def _task_out(conn: sqlite3.Connection, task_id: str) -> TaskOut:
    return TaskOut.model_validate(repo.with_computed(conn, [_load(conn, task_id)])[0])


def _is_open(row: Row) -> bool:
    return row["status"] not in repo.CLOSED_STATUSES and row["archived_at"] is None


def _label(title: str) -> str:
    """El título es texto libre: en un resumen de confirmación va entre comillas y acotado."""
    text = " ".join(title.split())
    return text if len(text) <= _MAX_LABEL else text[:_MAX_LABEL] + "…"


def _summary(verb: str, title: str, affected: int, *, undoable: bool) -> str:
    """Plantilla de `contracts/README.md` §5; `affected` incluye la propia tarea."""
    dependents = f" y {affected - 1} dependientes" if affected > 1 else ""
    closing = "se puede deshacer" if undoable else "no se puede deshacer"
    return f"Vas a {verb} 1 tarea: «{_label(title)}»{dependents}. Esta acción {closing}."


def _audit(
    ctx: ServiceContext,
    action: str,
    task_id: str,
    *,
    changes: Mapping[str, Any] | None = None,
    affected: int = 1,
) -> None:
    write_audit(
        ctx.conn,
        ctx.actor,
        action=action,
        entity_type="task",
        entity_id=task_id,
        changes=changes,
        affected_count=affected,
    )


def _touch_and_audit(
    ctx: ServiceContext,
    action: str,
    task_id: str,
    rows: Sequence[Row],
    now: str,
    changes_for: Callable[[Row], _Change],
) -> None:
    """Cada fila queda en su propio historial; la raíz lleva el recuento total."""
    for row in rows:
        touch_entity(ctx.conn, row["id"], now)
        _audit(
            ctx,
            action,
            row["id"],
            changes=changes_for(row),
            affected=len(rows) if row["id"] == task_id else 1,
        )


def _publish(ctx: ServiceContext, kind: str, entities: Iterable[tuple[str, int]]) -> None:
    """Ya hubo `COMMIT`: un fallo del canal de eventos no puede hacer creer que no se guardó."""
    for entity_id, revision in entities:
        try:
            ctx.ports.events.publish(
                f"workspace.entity_{kind}",
                {
                    "entity_type": "task",
                    "entity_id": entity_id,
                    "revision": revision,
                    "actor_type": ctx.actor.actor_type,
                },
            )
        except Exception:
            logger.exception("event_publish_failed", extra={"entity_id": entity_id})


def _next_revisions(rows: Iterable[Row]) -> list[tuple[str, int]]:
    return [(row["id"], row["revision"] + 1) for row in rows]


def _request_confirmation(
    ctx: ServiceContext,
    *,
    tool_name: str,
    action: str,
    task_id: str,
    args: Mapping[str, Any],
    audit_params: Mapping[str, Any],
    summary: str,
    rows: Sequence[Row],
) -> NoReturn:
    """`args` se guarda para ejecutar; a auditoría solo va `audit_params`: ids, booleanos y
    nombres de campos, nunca títulos, descripciones ni metadatos."""
    ticket = ctx.ports.confirmations.request(
        ctx.conn,
        actor=ctx.actor,
        tool_name=tool_name,
        args=args,
        summary=summary,
        affected_count=len(rows),
        targets=[ConfirmationTarget(row["id"], row["revision"]) for row in rows],
    )
    with _write(ctx):
        write_audit(
            ctx.conn,
            ctx.actor,
            action=action,
            entity_type="task",
            entity_id=task_id,
            params=audit_params,
            affected_count=len(rows),
            result="confirmation_required",
        )
    raise ConfirmationRequired(ticket)


def _guard_scope(
    rows: Sequence[Row],
    pre_confirmed: bool,
    targets: Sequence[ConfirmationTarget] | None,
) -> None:
    """Dentro de la transacción: nunca se ejecuta más de lo que se confirmó."""
    if pre_confirmed:
        _check_targets(rows, targets)
    elif len(rows) > BULK_THRESHOLD:
        raise conflict(_SCOPE_CHANGED)


def _check_targets(rows: Sequence[Row], targets: Sequence[ConfirmationTarget] | None) -> None:
    if targets is None:
        return
    confirmed = {(target.entity_id, target.revision) for target in targets}
    if confirmed != {(row["id"], row["revision"]) for row in rows}:
        raise conflict(_SCOPE_CHANGED)


def _check_project(conn: sqlite3.Connection, project_id: str) -> None:
    if not entity_exists(conn, project_id, "project"):
        raise not_found("El proyecto")
    if repo.is_archived(conn, project_id):
        raise conflict("No se puede asociar una tarea a un proyecto archivado.")


def _check_subject(conn: sqlite3.Connection, subject_id: str) -> None:
    if not entity_exists(conn, subject_id, "subject"):
        raise not_found("La asignatura")


def _check_parent(conn: sqlite3.Connection, parent_id: str) -> Row:
    parent = repo.get_row(conn, parent_id)
    if parent is None:
        raise not_found("La tarea padre")
    if parent["archived_at"] is not None:
        raise conflict("La tarea padre está archivada.")
    return parent


def _check_position(position: float | None) -> None:
    if position is not None and not math.isfinite(position):
        raise AppError("validation_error", "La posición debe ser un número finito.", 422)


def _stamp(value: Any) -> str | None:
    return None if value is None else format_timestamp(value)


def _day(value: Any) -> str | None:
    return None if value is None else value.isoformat()


# --- Crear y leer -----------------------------------------------------------------------------


def _create(ctx: ServiceContext, data: TaskCreate, parent_id: str | None) -> TaskOut:
    conn = ctx.conn
    _check_position(data.position)
    with _write(ctx):
        project_id = _str(data.project_id)
        if parent_id is not None:
            parent = _check_parent(conn, parent_id)
            if parent["status"] == "completed":
                raise conflict(_COMPLETED_PARENT)
            if repo.depth_of(conn, parent_id) + 1 > MAX_TASK_DEPTH:
                raise conflict(f"La profundidad máxima es {MAX_TASK_DEPTH}.")
            if project_id is not None and project_id != parent["project_id"]:
                raise conflict("Una subtarea pertenece al proyecto de su tarea padre.")
            project_id = parent["project_id"]
        if project_id is not None:
            _check_project(conn, project_id)
        subject_id = _str(data.subject_id)
        if subject_id is not None:
            _check_subject(conn, subject_id)

        task_id = new_id()
        now = utc_now()
        position = data.position
        if position is None:
            position = repo.next_position(conn, parent_id, project_id)
        values: dict[str, Any] = {
            "id": task_id,
            "title": data.title,
            "description": data.description,
            "status": data.status,
            "priority": data.priority,
            "start_at": _stamp(data.start_at),
            "due_at": _stamp(data.due_at),
            "due_date": _day(data.due_date),
            "estimated_minutes": data.estimated_minutes,
            "parent_task_id": parent_id,
            "project_id": project_id,
            "subject_id": subject_id,
            "position": position,
        }
        insert_entity(conn, task_id, "task", now, data.metadata)
        repo.insert_task(conn, values)
        changes: _Change = {
            name: {"from": None, "to": value}
            for name, value in values.items()
            if name != "id" and value is not None
        }
        if data.tags:
            replace_tags(conn, task_id, data.tags, now)
            changes["tags"] = {"from": [], "to": _tag_names(conn, task_id)}
        _audit(ctx, "task.create", task_id, changes=changes)
        out = _task_out(conn, task_id)
    _publish(ctx, "created", [(task_id, out.revision)])
    return out


@audits_failure("task.create", "task")
def create_task(ctx: ServiceContext, data: TaskCreate) -> TaskOut:
    return _create(ctx, data, _str(data.parent_task_id))


@audits_failure("task.create", "task")
def create_subtask(ctx: ServiceContext, parent_id: str, data: SubtaskCreate) -> TaskOut:
    return _create(ctx, data, str(parent_id))


def get_task(ctx: ServiceContext, task_id: str) -> TaskDetail:
    conn = ctx.conn
    tree = repo.subtree(conn, task_id)
    if not tree:
        raise not_found(_TASK)
    root, descendants = tree[0], tree[1:]
    # Archivar no propaga: una rama archivada solo se ve si sostiene algo activo.
    kept: set[str] = set()
    for row in reversed(descendants):
        if row["archived_at"] is None or row["id"] in kept:
            kept.update((row["id"], row["parent_task_id"]))
    visible = [row for row in descendants if row["id"] in kept]
    computed = repo.with_computed(conn, [root, *visible])

    nodes: dict[str, Row] = {}
    for row in computed:
        node = {key: value for key, value in row.items() if key != "level"}
        nodes[row["id"]] = {**node, "children": []}
    for row in computed[1:]:
        nodes[row["parent_task_id"]]["children"].append(nodes[row["id"]])

    root_node = nodes[root["id"]]
    dependency_ids = [target for _, target in dependencies_of(conn, [task_id])]
    dependent_ids = dependents_of(conn, task_id)
    return TaskDetail.model_validate(
        {
            **{key: value for key, value in root_node.items() if key != "children"},
            "subtasks": [TaskNode.model_validate(child) for child in root_node["children"]],
            "dependencies": [
                TaskRef.model_validate(ref) for ref in repo.task_refs(conn, dependency_ids)
            ],
            "dependents": [
                TaskRef.model_validate(ref) for ref in repo.task_refs(conn, dependent_ids)
            ],
        }
    )


def list_tasks(ctx: ServiceContext, query: TaskListQuery) -> Page[TaskOut]:
    rows, total = repo.list_rows(ctx.conn, query)
    items = [TaskOut.model_validate(row) for row in repo.with_computed(ctx.conn, rows)]
    return Page[TaskOut](items=items, total=total)


# --- Actualizar -------------------------------------------------------------------------------


@dataclass(frozen=True)
class _UpdatePlan:
    row: Row
    fields: dict[str, Any]  # Solo columnas que cambian.
    project_id: str | None
    cascade: list[Row]  # Filas cuyo proyecto cambia.


def _plain_fields(conn: sqlite3.Connection, data: TaskUpdate) -> dict[str, Any]:
    given = data.model_fields_set
    fields: dict[str, Any] = {
        name: getattr(data, name)
        for name in ("title", "description", "status", "priority", "estimated_minutes")
        if name in given
    }
    if "start_at" in given:
        fields["start_at"] = _stamp(data.start_at)
    if "due_at" in given:
        fields["due_at"] = _stamp(data.due_at)
    if "due_date" in given:
        fields["due_date"] = _day(data.due_date)
    if fields.get("due_at") is not None and fields.get("due_date") is not None:
        raise AppError("validation_error", "Indica due_at o due_date, no ambos.", 422)
    # Una tarea tiene una sola fecha límite: fijar una sustituye a la otra.
    if fields.get("due_at") is not None:
        fields["due_date"] = None
    elif fields.get("due_date") is not None:
        fields["due_at"] = None
    if "subject_id" in given:
        subject_id = _str(data.subject_id)
        if subject_id is not None:
            _check_subject(conn, subject_id)
        fields["subject_id"] = subject_id
    return fields


def _plan_update(
    conn: sqlite3.Connection,
    task_id: str,
    data: TaskUpdate,
    expected_revision: int | None,
) -> _UpdatePlan:
    row = _load(conn, task_id)
    check_revision(row["revision"], expected_revision)
    given = data.model_fields_set
    if "status" in given and row["status"] == "completed":
        raise conflict("La tarea está completada: reábrela primero.")
    _check_position(data.position)
    fields = _plain_fields(conn, data)

    parent_id = _str(data.parent_task_id) if "parent_task_id" in given else row["parent_task_id"]
    moved = parent_id != row["parent_task_id"]
    tree: list[Row] | None = None
    parent: Row | None = None
    if moved and parent_id is not None:
        tree = repo.subtree(conn, task_id)
        if parent_id in {item["id"] for item in tree}:
            raise hierarchy_cycle(_OWN_DESCENDANT)
        parent = _check_parent(conn, parent_id)
        height = max(item["level"] for item in tree)
        if repo.depth_of(conn, parent_id) + 1 + height > MAX_TASK_DEPTH:
            raise conflict(f"La profundidad máxima es {MAX_TASK_DEPTH}.")

    requested = _str(data.project_id)
    if parent_id is not None:
        project_id = parent["project_id"] if parent is not None else row["project_id"]
        if "project_id" in given and requested != project_id:
            raise conflict("Una subtarea pertenece al proyecto de su tarea padre.")
    else:
        project_id = requested if "project_id" in given else row["project_id"]

    status = fields.get("status", row["status"])
    reopened = row["status"] in repo.CLOSED_STATUSES and status not in repo.CLOSED_STATUSES
    if parent_id is not None and status not in repo.CLOSED_STATUSES and (moved or reopened):
        holder = parent if parent is not None else _load(conn, parent_id)
        if holder["status"] == "completed":
            raise conflict(_COMPLETED_PARENT)

    cascade: list[Row] = []
    project_changed = project_id != row["project_id"]
    if project_changed:
        if project_id is not None:
            _check_project(conn, project_id)
        tree = tree if tree is not None else repo.subtree(conn, task_id)
        cascade = [item for item in tree if item["project_id"] != project_id]

    if moved:
        fields["parent_task_id"] = parent_id
    if "position" in given:
        fields["position"] = data.position
    elif moved or (parent_id is None and project_changed):
        fields["position"] = repo.next_position(conn, parent_id, project_id)
    fields = {name: value for name, value in fields.items() if value != row[name]}
    return _UpdatePlan(row=row, fields=fields, project_id=project_id, cascade=cascade)


def _tag_names(conn: sqlite3.Connection, task_id: str) -> list[str]:
    return [tag["name"] for tag in tags_for(conn, [task_id])[task_id]]


def _tags_differ(names: Iterable[str], current: Iterable[str]) -> bool:
    wanted = {normalize_tag(name) for name in names} - {""}
    return wanted != {normalize_tag(name) for name in current}


def _update(
    ctx: ServiceContext,
    task_id: str,
    data: TaskUpdate,
    expected_revision: int | None,
    pre_confirmed: bool,
    targets: Sequence[ConfirmationTarget] | None,
) -> TaskOut:
    conn = ctx.conn
    if not pre_confirmed:
        plan = _plan_update(conn, task_id, data, expected_revision)
        if len(plan.cascade) > BULK_THRESHOLD:
            _request_confirmation(
                ctx,
                tool_name="update_task",
                action="task.update",
                task_id=task_id,
                args={
                    "task_id": task_id,
                    "data": data.model_dump(mode="json", exclude_unset=True),
                },
                audit_params={"task_id": task_id, "fields": sorted(data.model_fields_set)},
                summary=_summary(
                    "actualizar", plan.row["title"], len(plan.cascade), undoable=True
                ),
                rows=plan.cascade,
            )

    with _write(ctx):
        plan = _plan_update(conn, task_id, data, expected_revision)
        _guard_scope(plan.cascade, pre_confirmed, targets)
        row = plan.row
        changes: _Change = {
            name: {"from": row[name], "to": value} for name, value in plan.fields.items()
        }
        if plan.cascade:
            changes["project_id"] = {"from": row["project_id"], "to": plan.project_id}
        given = data.model_fields_set
        if "metadata" in given and data.metadata != row["metadata"]:
            changes["metadata"] = {"from": row["metadata"], "to": data.metadata}
        tags_before = _tag_names(conn, task_id)
        replace = data.tags is not None and _tags_differ(data.tags, tags_before)
        if not changes and not replace:
            return _task_out(conn, task_id)

        now = utc_now()
        repo.update_fields(conn, task_id, plan.fields)
        if plan.cascade:
            repo.set_project(conn, [item["id"] for item in plan.cascade], plan.project_id)
        if data.metadata is not None and "metadata" in changes:
            set_metadata(conn, task_id, data.metadata)
        if data.tags is not None and replace:
            replace_tags(conn, task_id, data.tags, now)
            changes["tags"] = {"from": tags_before, "to": _tag_names(conn, task_id)}

        descendants = [item for item in plan.cascade if item["id"] != task_id]
        touch_entity(conn, task_id, now)
        _audit(ctx, "task.update", task_id, changes=changes, affected=1 + len(descendants))
        _touch_and_audit(
            ctx,
            "task.update",
            task_id,
            descendants,
            now,
            lambda item: {"project_id": {"from": item["project_id"], "to": plan.project_id}},
        )
        out = _task_out(conn, task_id)
    _publish(ctx, "updated", _next_revisions([row, *descendants]))
    return out


@audits_failure("task.update", "task")
def update_task(
    ctx: ServiceContext,
    task_id: str,
    data: TaskUpdate,
    *,
    expected_revision: int | None = None,
    pre_confirmed: bool = False,
) -> TaskOut:
    return _update(ctx, task_id, data, expected_revision, pre_confirmed, None)


# --- Completar y reabrir ----------------------------------------------------------------------


def _plan_complete(
    conn: sqlite3.Connection,
    task_id: str,
    data: TaskCompleteRequest,
    expected_revision: int | None,
) -> tuple[Row, list[Row]]:
    """Devuelve la raíz y lo que se completaría; vacío si ya está completada."""
    root = _load(conn, task_id)
    if root["status"] == "completed":
        return root, []
    check_revision(root["revision"], expected_revision)
    tree = repo.subtree(conn, task_id)
    open_subtasks = [row for row in tree[1:] if _is_open(row)]
    if open_subtasks and not data.complete_subtasks:
        raise conflict("La tarea tiene subtareas abiertas.")
    scope = [tree[0], *open_subtasks]
    ignore = {row["id"] for row in tree} if data.complete_subtasks else set()
    if repo.unresolved_dependencies(conn, [row["id"] for row in scope], ignore):
        raise conflict("La tarea tiene dependencias sin resolver.")
    return root, scope


def _complete(
    ctx: ServiceContext,
    task_id: str,
    data: TaskCompleteRequest,
    expected_revision: int | None,
    pre_confirmed: bool,
    targets: Sequence[ConfirmationTarget] | None,
) -> TaskOut:
    conn = ctx.conn
    if not pre_confirmed:
        root, scope = _plan_complete(conn, task_id, data, expected_revision)
        if len(scope) > BULK_THRESHOLD:
            _request_confirmation(
                ctx,
                tool_name="complete_task",
                action="task.complete",
                task_id=task_id,
                args={"task_id": task_id, "complete_subtasks": data.complete_subtasks},
                audit_params={"task_id": task_id, "complete_subtasks": data.complete_subtasks},
                summary=_summary("completar", root["title"], len(scope), undoable=True),
                rows=scope,
            )

    with _write(ctx):
        _, scope = _plan_complete(conn, task_id, data, expected_revision)
        if not scope:
            return _task_out(conn, task_id)
        _guard_scope(scope, pre_confirmed, targets)
        now = utc_now()
        repo.mark_completed(conn, [row["id"] for row in scope], now)
        _touch_and_audit(
            ctx,
            "task.complete",
            task_id,
            scope,
            now,
            lambda row: {
                "status": {"from": row["status"], "to": "completed"},
                "completed_at": {"from": None, "to": now},
            },
        )
        out = _task_out(conn, task_id)
    _publish(ctx, "updated", _next_revisions(scope))
    return out


@audits_failure("task.complete", "task")
def complete_task(
    ctx: ServiceContext,
    task_id: str,
    data: TaskCompleteRequest,
    *,
    expected_revision: int | None = None,
    pre_confirmed: bool = False,
) -> TaskOut:
    return _complete(ctx, task_id, data, expected_revision, pre_confirmed, None)


@audits_failure("task.reopen", "task")
def reopen_task(
    ctx: ServiceContext, task_id: str, *, expected_revision: int | None = None
) -> TaskOut:
    conn = ctx.conn
    with _write(ctx):
        row = _load(conn, task_id)
        check_revision(row["revision"], expected_revision)
        if row["status"] not in repo.CLOSED_STATUSES:
            raise conflict("Solo se reabre una tarea completada o cancelada.")
        parent_id = row["parent_task_id"]
        if parent_id is not None and _load(conn, parent_id)["status"] == "completed":
            raise conflict("La tarea padre está completada: reábrela primero.")
        now = utc_now()
        repo.update_fields(conn, task_id, {"status": "pending", "completed_at": None})
        touch_entity(conn, task_id, now)
        changes: _Change = {"status": {"from": row["status"], "to": "pending"}}
        if row["completed_at"] is not None:
            changes["completed_at"] = {"from": row["completed_at"], "to": None}
        _audit(ctx, "task.reopen", task_id, changes=changes)
        out = _task_out(conn, task_id)
    _publish(ctx, "updated", _next_revisions([row]))
    return out


# --- Archivar ---------------------------------------------------------------------------------


def _set_archived(
    ctx: ServiceContext,
    task_id: str,
    expected_revision: int | None,
    *,
    archive: bool,
) -> TaskOut:
    """Solo esta tarea: archivar no propaga a hijos. Repetirlo no cambia nada."""
    conn = ctx.conn
    with _write(ctx):
        row = _load(conn, task_id)
        if (row["archived_at"] is not None) == archive:
            return _task_out(conn, task_id)
        check_revision(row["revision"], expected_revision)
        now = utc_now()
        archived_at = now if archive else None
        set_archived(conn, [task_id], archived_at)
        touch_entity(conn, task_id, now)
        changes = {"archived_at": {"from": row["archived_at"], "to": archived_at}}
        _audit(ctx, "task.archive" if archive else "task.unarchive", task_id, changes=changes)
        out = _task_out(conn, task_id)
    _publish(ctx, "archived" if archive else "restored", _next_revisions([row]))
    return out


@audits_failure("task.archive", "task")
def archive_task(
    ctx: ServiceContext, task_id: str, *, expected_revision: int | None = None
) -> TaskOut:
    return _set_archived(ctx, task_id, expected_revision, archive=True)


@audits_failure("task.unarchive", "task")
def unarchive_task(
    ctx: ServiceContext, task_id: str, *, expected_revision: int | None = None
) -> TaskOut:
    return _set_archived(ctx, task_id, expected_revision, archive=False)


# --- Borrar -----------------------------------------------------------------------------------


def _plan_delete(
    conn: sqlite3.Connection, task_id: str, expected_revision: int | None
) -> tuple[list[Row], list[Row]]:
    """Devuelve el subárbol, raíz primero, y las tareas de fuera que dependen de él."""
    root = _load(conn, task_id)
    check_revision(root["revision"], expected_revision)
    scope = repo.subtree(conn, task_id)
    ids = {row["id"] for row in scope}
    linked = repo.count_blocking_relationships(conn, sorted(ids))
    if linked:
        message = f"La tarea sigue vinculada a otros elementos ({linked})."
        detail = ErrorDetail(code="has_dependents", message=message)
        raise AppError("has_dependents", message, 409, [detail])
    outside: dict[str, Row] = {}
    for row in scope:
        for source_id in dependents_of(conn, row["id"]):
            if source_id not in ids and source_id not in outside:
                outside[source_id] = _load(conn, source_id)
    return scope, list(outside.values())


def _remove_rows(ctx: ServiceContext, scope: Sequence[Row], dependents: Sequence[Row]) -> None:
    """Dentro de la transacción. Quien dependía de lo borrado queda desbloqueado: es un cambio
    suyo, así que sube su `revision` y queda en su historial."""
    conn = ctx.conn
    ids = [row["id"] for row in scope]
    removed = [
        pair
        for pair in dependencies_of(conn, [row["id"] for row in dependents])
        if pair[1] in set(ids)
    ]
    remove_all_dependencies(conn, ids)
    repo.delete_rows(conn, list(reversed(ids)))
    now = utc_now()
    for row in dependents:
        touch_entity(conn, row["id"], now)
    for source_id, target_id in removed:
        changes = {"depends_on": {"from": target_id, "to": None}}
        _audit(ctx, "task.dependency_remove", source_id, changes=changes)
    affected = len(scope) + len(dependents)
    for index, row in enumerate(scope):
        _audit(
            ctx,
            "task.delete",
            row["id"],
            changes={"title": {"from": row["title"], "to": None}},
            affected=affected if index == 0 else 1,
        )


def _delete(
    ctx: ServiceContext,
    task_id: str,
    expected_revision: int | None,
    pre_confirmed: bool,
    targets: Sequence[ConfirmationTarget] | None,
) -> None:
    conn = ctx.conn
    if not pre_confirmed:
        scope, dependents = _plan_delete(conn, task_id, expected_revision)
        rows = [*scope, *dependents]
        _request_confirmation(
            ctx,
            tool_name="delete_task",
            action="task.delete",
            task_id=task_id,
            args={"task_id": task_id},
            audit_params={"task_id": task_id},
            summary=_summary("eliminar", scope[0]["title"], len(rows), undoable=False),
            rows=rows,
        )

    with _write(ctx):
        scope, dependents = _plan_delete(conn, task_id, expected_revision)
        _check_targets([*scope, *dependents], targets)
        _remove_rows(ctx, scope, dependents)
    _publish(ctx, "updated", _next_revisions(dependents))
    _publish(ctx, "deleted", [(row["id"], row["revision"]) for row in scope])


@audits_failure("task.delete", "task")
def delete_task(
    ctx: ServiceContext,
    task_id: str,
    *,
    expected_revision: int | None = None,
    pre_confirmed: bool = False,
) -> None:
    _delete(ctx, task_id, expected_revision, pre_confirmed, None)


@audits_failure("task.delete", "task")
def delete_leaf_task(ctx: ServiceContext, task_id: str, expected_revision: int) -> None:
    """Solo para el handler CONFIRM: lo aprobado es exactamente una tarea, sin puerta aquí."""
    conn = ctx.conn
    with _write(ctx):
        # Sin revisión no hay borrado: 0 nunca coincide, `revision` empieza en 1.
        scope, dependents = _plan_delete(conn, task_id, expected_revision or 0)
        if len(scope) > 1:
            raise conflict("La tarea tiene subtareas.")
        if dependents:
            raise conflict("Otras tareas dependen de esta.")
        _remove_rows(ctx, scope, [])
    _publish(ctx, "deleted", [(scope[0]["id"], scope[0]["revision"])])


# --- Etiquetas y dependencias -----------------------------------------------------------------


@audits_failure("task.tags", "task")
def replace_task_tags(ctx: ServiceContext, task_id: str, names: list[str]) -> TaskOut:
    conn = ctx.conn
    with _write(ctx):
        row = _load(conn, task_id)
        before = _tag_names(conn, task_id)
        if not _tags_differ(names, before):
            return _task_out(conn, task_id)
        now = utc_now()
        replace_tags(conn, task_id, names, now)
        touch_entity(conn, task_id, now)
        changes = {"tags": {"from": before, "to": _tag_names(conn, task_id)}}
        _audit(ctx, "task.tags", task_id, changes=changes)
        out = _task_out(conn, task_id)
    _publish(ctx, "updated", _next_revisions([row]))
    return out


def list_task_tags(ctx: ServiceContext) -> list[TagOut]:
    return [TagOut.model_validate(tag) for tag in list_tags(ctx.conn)]


@audits_failure("task.dependency_add", "task")
def add_task_dependency(ctx: ServiceContext, task_id: str, depends_on_id: str) -> TaskDetail:
    conn = ctx.conn
    added = False
    with _write(ctx):
        row = _load(conn, task_id)
        _load(conn, depends_on_id)
        if task_id == depends_on_id:
            raise hierarchy_cycle("Una tarea no puede depender de sí misma.")
        if dependency_would_cycle(conn, task_id, depends_on_id):
            raise hierarchy_cycle(_DEPENDENCY_CYCLE)
        now = utc_now()
        added = add_dependency(conn, task_id, depends_on_id, now)
        if added:
            touch_entity(conn, task_id, now)
            changes = {"depends_on": {"from": None, "to": depends_on_id}}
            _audit(ctx, "task.dependency_add", task_id, changes=changes)
    if added:
        _publish(ctx, "updated", _next_revisions([row]))
    return get_task(ctx, task_id)


@audits_failure("task.dependency_remove", "task")
def remove_task_dependency(ctx: ServiceContext, task_id: str, depends_on_id: str) -> TaskDetail:
    conn = ctx.conn
    with _write(ctx):
        row = _load(conn, task_id)
        if not remove_dependency(conn, task_id, depends_on_id):
            raise not_found("La dependencia")
        touch_entity(conn, task_id, utc_now())
        changes = {"depends_on": {"from": depends_on_id, "to": None}}
        _audit(ctx, "task.dependency_remove", task_id, changes=changes)
    _publish(ctx, "updated", _next_revisions([row]))
    return get_task(ctx, task_id)


def task_history(
    ctx: ServiceContext, task_id: str, *, limit: int, offset: int
) -> Page[HistoryEntry]:
    _load(ctx.conn, task_id)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, min(offset, MAX_OFFSET))
    rows, total = history_for(ctx.conn, [task_id], limit, offset)
    return Page[HistoryEntry](
        items=[HistoryEntry.model_validate(row) for row in rows], total=total
    )


# --- Ejecutores de confirmación ---------------------------------------------------------------
# Comparan alcance y revisiones dentro de la misma transacción que ejecuta. No son accesibles
# por REST: los llama la puerta de confirmaciones al aprobar.


@audits_failure("task.delete", "task")
def _confirmed_delete(
    ctx: ServiceContext, args: Mapping[str, Any], targets: Sequence[ConfirmationTarget]
) -> None:
    _delete(ctx, str(args["task_id"]), None, True, targets)


@audits_failure("task.complete", "task")
def _confirmed_complete(
    ctx: ServiceContext, args: Mapping[str, Any], targets: Sequence[ConfirmationTarget]
) -> TaskOut:
    data = TaskCompleteRequest(complete_subtasks=bool(args.get("complete_subtasks", False)))
    return _complete(ctx, str(args["task_id"]), data, None, True, targets)


@audits_failure("task.update", "task")
def _confirmed_update(
    ctx: ServiceContext, args: Mapping[str, Any], targets: Sequence[ConfirmationTarget]
) -> TaskOut:
    data = TaskUpdate.model_validate(args["data"])
    return _update(ctx, str(args["task_id"]), data, None, True, targets)


TASK_CONFIRMABLE: Final[
    dict[str, Callable[[ServiceContext, Mapping[str, Any], Sequence[ConfirmationTarget]], Any]]
] = {
    "delete_task": _confirmed_delete,
    "complete_task": _confirmed_complete,
    "update_task": _confirmed_update,
}
