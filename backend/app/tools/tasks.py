"""Herramientas del agente para tareas. Finas: validan, llaman al servicio y traducen errores."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Annotated, Final, TypeVar
from uuid import UUID

from pydantic import Field

from app.api.tasks_http import PORTS_STATE_KEY
from app.core.errors import AppError
from app.database.connection import connect
from app.schemas.tasks import (
    MAX_TAGS,
    Out,
    Page,
    Strict,
    SubtaskCreate,
    TagName,
    TaskCompleteRequest,
    TaskCreate,
    TaskDetail,
    TaskListQuery,
    TaskOut,
    TaskUpdate,
)
from app.services import tasks as svc
from app.services.tasks_ports import (
    Actor,
    ConfirmationRequired,
    Ports,
    ServiceContext,
)
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec

R = TypeVar("R")

_DOMAIN: Final = "tasks"
_ERR_READ: Final = ("not_found", "validation_error")
_ERR_WRITE: Final = ("not_found", "conflict", "revision_mismatch", "validation_error")
_ERR_CYCLE: Final = (*_ERR_WRITE, "hierarchy_cycle")
_ERR_CONFIRM: Final = (*_ERR_WRITE, "confirmation_required", "confirmation_unavailable")


def run_service(ctx: ToolContext, tool_name: str, call: Callable[[ServiceContext], R]) -> R:
    """Abre la conexión, ejecuta `call` con un actor de agente y traduce los errores."""
    conn = connect(ctx.state.settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        ports = getattr(ctx.state, PORTS_STATE_KEY, None) or Ports()
        actor = Actor(
            actor_type="agent",
            origin="mcp",
            correlation_id=str(ctx.turn_id),
            tool_name=tool_name,
        )
        return call(ServiceContext(conn=conn, actor=actor, ports=ports))
    except ConfirmationRequired as exc:
        raise ToolError(
            "confirmation_required",
            exc.ticket.summary,
            details=[exc.ticket.model_dump(mode="json")],
        ) from None
    except AppError as exc:
        raise ToolError(
            exc.code,
            exc.message,
            details=[d.model_dump(mode="json") for d in exc.details] or None,
        ) from None
    finally:
        conn.close()


# --- Argumentos y resultados ---------------------------------------------------------------


class Deleted(Out):
    deleted: bool
    id: UUID


class TaskIdArgs(Strict):
    task_id: UUID


class TaskRevisionArgs(Strict):
    task_id: UUID
    expected_revision: int | None = None


class UpdateTaskArgs(Strict):
    task_id: UUID
    expected_revision: int | None = None
    patch: TaskUpdate


class CompleteTaskArgs(Strict):
    task_id: UUID
    expected_revision: int | None = None


class CreateSubtaskArgs(Strict):
    parent_task_id: UUID
    subtask: SubtaskCreate


class SearchTasksArgs(Strict):
    query: Annotated[str, Field(min_length=1, max_length=200)]
    limit: Annotated[int, Field(ge=1, le=50)] = 20


class SetTaskTagsArgs(Strict):
    task_id: UUID
    names: Annotated[list[TagName], Field(max_length=MAX_TAGS)]


class TaskDependencyArgs(Strict):
    task_id: UUID
    depends_on_task_id: UUID


class DeleteTaskArgs(Strict):
    task_id: UUID
    expected_revision: int | None = None


# --- Handlers ------------------------------------------------------------------------------


def _create_task(ctx: ToolContext, args: TaskCreate) -> TaskOut:
    return run_service(ctx, "create_task", lambda s: svc.create_task(s, args))


def _get_task(ctx: ToolContext, args: TaskIdArgs) -> TaskDetail:
    return run_service(ctx, "get_task", lambda s: svc.get_task(s, str(args.task_id)))


def _update_task(ctx: ToolContext, args: UpdateTaskArgs) -> TaskOut:
    return run_service(
        ctx,
        "update_task",
        lambda s: svc.update_task(
            s, str(args.task_id), args.patch, expected_revision=args.expected_revision
        ),
    )


def _complete_task(ctx: ToolContext, args: CompleteTaskArgs) -> TaskOut:
    return run_service(
        ctx,
        "complete_task",
        lambda s: svc.complete_task(
            s,
            str(args.task_id),
            TaskCompleteRequest(),
            expected_revision=args.expected_revision,
        ),
    )


def _reopen_task(ctx: ToolContext, args: TaskRevisionArgs) -> TaskOut:
    return run_service(
        ctx,
        "reopen_task",
        lambda s: svc.reopen_task(
            s, str(args.task_id), expected_revision=args.expected_revision
        ),
    )


def _archive_task(ctx: ToolContext, args: TaskRevisionArgs) -> TaskOut:
    return run_service(
        ctx,
        "archive_task",
        lambda s: svc.archive_task(
            s, str(args.task_id), expected_revision=args.expected_revision
        ),
    )


def _unarchive_task(ctx: ToolContext, args: TaskRevisionArgs) -> TaskOut:
    return run_service(
        ctx,
        "unarchive_task",
        lambda s: svc.unarchive_task(
            s, str(args.task_id), expected_revision=args.expected_revision
        ),
    )


def _create_subtask(ctx: ToolContext, args: CreateSubtaskArgs) -> TaskOut:
    return run_service(
        ctx,
        "create_subtask",
        lambda s: svc.create_subtask(s, str(args.parent_task_id), args.subtask),
    )


def _list_tasks(ctx: ToolContext, args: TaskListQuery) -> Page[TaskOut]:
    return run_service(ctx, "list_tasks", lambda s: svc.list_tasks(s, args))


def _search_tasks(ctx: ToolContext, args: SearchTasksArgs) -> Page[TaskOut]:
    query = TaskListQuery(q=args.query, limit=args.limit)
    return run_service(ctx, "search_tasks", lambda s: svc.list_tasks(s, query))


def _set_task_tags(ctx: ToolContext, args: SetTaskTagsArgs) -> TaskOut:
    return run_service(
        ctx,
        "set_task_tags",
        lambda s: svc.replace_task_tags(s, str(args.task_id), list(args.names)),
    )


def _add_task_dependency(ctx: ToolContext, args: TaskDependencyArgs) -> TaskDetail:
    return run_service(
        ctx,
        "add_task_dependency",
        lambda s: svc.add_task_dependency(s, str(args.task_id), str(args.depends_on_task_id)),
    )


def _remove_task_dependency(ctx: ToolContext, args: TaskDependencyArgs) -> TaskDetail:
    return run_service(
        ctx,
        "remove_task_dependency",
        lambda s: svc.remove_task_dependency(
            s, str(args.task_id), str(args.depends_on_task_id)
        ),
    )


def _delete_task(ctx: ToolContext, args: DeleteTaskArgs) -> Deleted:
    # Solo se llega aquí tras el ToolGate (riesgo CONFIRM), de ahí pre_confirmed=True.
    run_service(
        ctx,
        "delete_task",
        lambda s: svc.delete_task(
            s,
            str(args.task_id),
            expected_revision=args.expected_revision,
            pre_confirmed=True,
        ),
    )
    return Deleted(deleted=True, id=args.task_id)


def _summarize_delete(args: DeleteTaskArgs) -> str:
    return f"Eliminar la tarea {args.task_id} y todas sus subtareas"


# --- Catálogo ------------------------------------------------------------------------------

_ID_AUDIT = {"task_id": "log", "expected_revision": "log"}
_TASK_FIELDS_AUDIT = {
    "title": "hash",
    "description": "hash",
    "status": "log",
    "priority": "log",
    "start_at": "log",
    "due_at": "log",
    "due_date": "log",
    "estimated_minutes": "log",
    "parent_task_id": "log",
    "project_id": "log",
    "subject_id": "log",
    "position": "log",
    "tags": "hash",
    "metadata": "omit",
}


def _spec(
    name: str,
    description: str,
    args_model: type[Strict],
    result_model: type[Out],
    handler: Callable[..., Out],
    permission: str,
    risk: RiskClass,
    errors: tuple[str, ...],
    audit: dict[str, str],
    *,
    idempotent: bool = False,
    summarize: Callable[..., str] | None = None,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=description,
        domain=_DOMAIN,
        args_model=args_model,
        result_model=result_model,
        permission=permission,
        risk=risk,
        handler=handler,
        errors=errors,
        idempotent=idempotent,
        audit=audit,
        summarize=summarize,
    )


R_, W_, C_ = RiskClass.READ, RiskClass.WRITE, RiskClass.CONFIRM

TOOLS: tuple[ToolSpec, ...] = (
    _spec(
        "create_task", "Crea una tarea.", TaskCreate, TaskOut, _create_task,
        "tasks.write", W_, _ERR_WRITE, dict(_TASK_FIELDS_AUDIT),
    ),
    _spec(
        "get_task", "Devuelve una tarea con subtareas y dependencias.", TaskIdArgs, TaskDetail,
        _get_task, "tasks.read", R_, _ERR_READ, dict(_ID_AUDIT), idempotent=True,
    ),
    _spec(
        "update_task", "Modifica campos de una tarea.", UpdateTaskArgs, TaskOut, _update_task,
        "tasks.write", W_, _ERR_CYCLE, {**_ID_AUDIT, "patch": "hash"},
    ),
    _spec(
        "complete_task", "Marca una tarea como completada.", CompleteTaskArgs, TaskOut,
        _complete_task, "tasks.write", W_, _ERR_WRITE, dict(_ID_AUDIT), idempotent=True,
    ),
    _spec(
        "reopen_task", "Reabre una tarea completada o cancelada.", TaskRevisionArgs, TaskOut,
        _reopen_task, "tasks.write", W_, _ERR_WRITE, dict(_ID_AUDIT),
    ),
    _spec(
        "archive_task", "Archiva una tarea.", TaskRevisionArgs, TaskOut, _archive_task,
        "tasks.write", W_, _ERR_WRITE, dict(_ID_AUDIT), idempotent=True,
    ),
    _spec(
        "unarchive_task", "Restaura una tarea archivada.", TaskRevisionArgs, TaskOut,
        _unarchive_task, "tasks.write", W_, _ERR_WRITE, dict(_ID_AUDIT), idempotent=True,
    ),
    _spec(
        "create_subtask", "Crea una subtarea dentro de otra tarea.", CreateSubtaskArgs, TaskOut,
        _create_subtask, "tasks.write", W_, _ERR_CYCLE,
        {"parent_task_id": "log", "subtask": "hash"},
    ),
    _spec(
        "list_tasks", "Lista tareas con filtros.", TaskListQuery, Page[TaskOut], _list_tasks,
        "tasks.read", R_, _ERR_READ,
        {
            "status": "log", "priority": "log", "project_id": "log", "no_project": "log",
            "subject_id": "log", "parent_task_id": "log", "root_only": "log", "tag": "hash",
            "due_before": "log", "due_after": "log", "q": "hash", "include_archived": "log",
            "sort": "log", "limit": "log", "offset": "log",
        },
        idempotent=True,
    ),
    _spec(
        "search_tasks", "Busca tareas por texto.", SearchTasksArgs, Page[TaskOut],
        _search_tasks, "tasks.read", R_, _ERR_READ, {"query": "hash", "limit": "log"},
        idempotent=True,
    ),
    _spec(
        "set_task_tags", "Sustituye las etiquetas de una tarea.", SetTaskTagsArgs, TaskOut,
        _set_task_tags, "tasks.write", W_, _ERR_WRITE, {"task_id": "log", "names": "hash"},
        idempotent=True,
    ),
    _spec(
        "add_task_dependency", "Hace que una tarea dependa de otra.", TaskDependencyArgs,
        TaskDetail, _add_task_dependency, "tasks.write", W_, _ERR_CYCLE,
        {"task_id": "log", "depends_on_task_id": "log"},
    ),
    _spec(
        "remove_task_dependency", "Quita una dependencia entre tareas.", TaskDependencyArgs,
        TaskDetail, _remove_task_dependency, "tasks.write", W_, _ERR_WRITE,
        {"task_id": "log", "depends_on_task_id": "log"},
    ),
    _spec(
        "delete_task", "Elimina una tarea y sus subtareas.", DeleteTaskArgs, Deleted,
        _delete_task, "tasks.delete", C_, _ERR_CONFIRM, dict(_ID_AUDIT),
        summarize=_summarize_delete,
    ),
)
