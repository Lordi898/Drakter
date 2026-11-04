"""Rutas REST de tareas. `pre_confirmed` no existe aquí: la confirmación la decide el servicio."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Header, Query, Request, Response
from fastapi.responses import JSONResponse

from app.api.tasks_http import confirmation_response, service_context
from app.api.tasks_http import expected_revision as resolve_revision
from app.schemas.tasks import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MAX_OFFSET,
    HistoryEntry,
    Page,
    SubtaskCreate,
    TagOut,
    TaskCompleteRequest,
    TaskCreate,
    TaskDependencyCreate,
    TaskDetail,
    TaskListQuery,
    TaskOut,
    TaskTagsReplace,
    TaskUpdate,
)
from app.services import tasks as service
from app.services.tasks_ports import ConfirmationRequired

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

IfMatch = Annotated[str | None, Header()]
# La GUI no puede enviar cabeceras: `?revision=N` equivale a `If-Match`.
Revision = Annotated[int | None, Query(ge=1)]
HistoryLimit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
HistoryOffset = Annotated[int, Query(ge=0, le=MAX_OFFSET)]


@router.get("", response_model=Page[TaskOut])
def list_tasks(request: Request, query: Annotated[TaskListQuery, Query()]) -> Page[TaskOut]:
    with service_context(request) as ctx:
        return service.list_tasks(ctx, query)


@router.post("", response_model=TaskOut, status_code=201)
def create_task(request: Request, data: TaskCreate) -> TaskOut:
    with service_context(request) as ctx:
        return service.create_task(ctx, data)


# Antes que `/{task_id}`.
@router.get("/tags", response_model=list[TagOut])
def list_task_tags(request: Request) -> list[TagOut]:
    with service_context(request) as ctx:
        return service.list_task_tags(ctx)


@router.get("/{task_id}", response_model=TaskDetail)
def get_task(request: Request, task_id: UUID) -> TaskDetail:
    with service_context(request) as ctx:
        return service.get_task(ctx, str(task_id))


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    request: Request,
    task_id: UUID,
    data: TaskUpdate,
    if_match: IfMatch = None,
    revision: Revision = None,
) -> TaskOut | JSONResponse:
    expected_revision = resolve_revision(if_match, revision)
    with service_context(request) as ctx:
        try:
            return service.update_task(
                ctx, str(task_id), data, expected_revision=expected_revision
            )
        except ConfirmationRequired as exc:
            return confirmation_response(request, exc)


@router.delete("/{task_id}", status_code=204, response_model=None)
def delete_task(
    request: Request, task_id: UUID, if_match: IfMatch = None, revision: Revision = None
) -> Response:
    expected_revision = resolve_revision(if_match, revision)
    with service_context(request) as ctx:
        try:
            service.delete_task(ctx, str(task_id), expected_revision=expected_revision)
        except ConfirmationRequired as exc:
            return confirmation_response(request, exc)
    return Response(status_code=204)


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(
    request: Request,
    task_id: UUID,
    data: TaskCompleteRequest | None = Body(default=None),
    if_match: IfMatch = None,
    revision: Revision = None,
) -> TaskOut | JSONResponse:
    expected_revision = resolve_revision(if_match, revision)
    with service_context(request) as ctx:
        try:
            return service.complete_task(
                ctx,
                str(task_id),
                data or TaskCompleteRequest(),
                expected_revision=expected_revision,
            )
        except ConfirmationRequired as exc:
            return confirmation_response(request, exc)


@router.post("/{task_id}/reopen", response_model=TaskOut)
def reopen_task(
    request: Request, task_id: UUID, if_match: IfMatch = None, revision: Revision = None
) -> TaskOut:
    expected_revision = resolve_revision(if_match, revision)
    with service_context(request) as ctx:
        return service.reopen_task(ctx, str(task_id), expected_revision=expected_revision)


@router.post("/{task_id}/archive", response_model=TaskOut)
def archive_task(
    request: Request, task_id: UUID, if_match: IfMatch = None, revision: Revision = None
) -> TaskOut:
    expected_revision = resolve_revision(if_match, revision)
    with service_context(request) as ctx:
        return service.archive_task(ctx, str(task_id), expected_revision=expected_revision)


@router.post("/{task_id}/unarchive", response_model=TaskOut)
def unarchive_task(
    request: Request, task_id: UUID, if_match: IfMatch = None, revision: Revision = None
) -> TaskOut:
    expected_revision = resolve_revision(if_match, revision)
    with service_context(request) as ctx:
        return service.unarchive_task(ctx, str(task_id), expected_revision=expected_revision)


@router.post("/{task_id}/subtasks", response_model=TaskOut, status_code=201)
def create_subtask(request: Request, task_id: UUID, data: SubtaskCreate) -> TaskOut:
    with service_context(request) as ctx:
        return service.create_subtask(ctx, str(task_id), data)


@router.put("/{task_id}/tags", response_model=TaskOut)
def replace_task_tags(request: Request, task_id: UUID, data: TaskTagsReplace) -> TaskOut:
    with service_context(request) as ctx:
        return service.replace_task_tags(ctx, str(task_id), data.names)


@router.post("/{task_id}/dependencies", response_model=TaskDetail)
def add_task_dependency(
    request: Request, task_id: UUID, data: TaskDependencyCreate
) -> TaskDetail:
    with service_context(request) as ctx:
        return service.add_task_dependency(ctx, str(task_id), str(data.depends_on_task_id))


@router.delete("/{task_id}/dependencies/{dep_id}", response_model=TaskDetail)
def remove_task_dependency(request: Request, task_id: UUID, dep_id: UUID) -> TaskDetail:
    with service_context(request) as ctx:
        return service.remove_task_dependency(ctx, str(task_id), str(dep_id))


@router.get("/{task_id}/history", response_model=Page[HistoryEntry])
def task_history(
    request: Request,
    task_id: UUID,
    limit: HistoryLimit = DEFAULT_LIMIT,
    offset: HistoryOffset = 0,
) -> Page[HistoryEntry]:
    with service_context(request) as ctx:
        return service.task_history(ctx, str(task_id), limit=limit, offset=offset)
