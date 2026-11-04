"""REST de proyectos. `pre_confirmed` nunca se acepta del cliente."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response

from app.api.tasks_http import confirmation_response, parse_if_match, service_context
from app.schemas.projects import (
    ProjectCreate,
    ProjectListQuery,
    ProjectOut,
    ProjectProgress,
    ProjectUpdate,
)
from app.schemas.tasks import DEFAULT_LIMIT, MAX_LIMIT, MAX_OFFSET, HistoryEntry, Page
from app.services import projects as service
from app.services.tasks_ports import ConfirmationRequired

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

IfMatch = Annotated[str | None, Header()]


@router.get("", response_model=Page[ProjectOut])
def list_projects(request: Request, query: Annotated[ProjectListQuery, Query()]) -> Page[ProjectOut]:
    with service_context(request) as ctx:
        return service.list_projects(ctx, query)


@router.post("", status_code=201, response_model=ProjectOut)
def create_project(request: Request, body: ProjectCreate) -> ProjectOut:
    with service_context(request) as ctx:
        return service.create_project(ctx, body)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(request: Request, project_id: UUID) -> ProjectOut:
    with service_context(request) as ctx:
        return service.get_project(ctx, str(project_id))


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    request: Request, project_id: UUID, body: ProjectUpdate, if_match: IfMatch = None
) -> ProjectOut:
    revision = parse_if_match(if_match)
    with service_context(request) as ctx:
        return service.update_project(ctx, str(project_id), body, expected_revision=revision)


@router.delete("/{project_id}", status_code=204, response_class=Response)
def delete_project(request: Request, project_id: UUID, if_match: IfMatch = None) -> Response:
    revision = parse_if_match(if_match)
    with service_context(request) as ctx:
        try:
            service.delete_project(ctx, str(project_id), expected_revision=revision)
        except ConfirmationRequired as exc:
            return confirmation_response(request, exc)
    return Response(status_code=204)


@router.post("/{project_id}/archive", response_model=ProjectOut)
def archive_project(request: Request, project_id: UUID, if_match: IfMatch = None) -> ProjectOut:
    revision = parse_if_match(if_match)
    with service_context(request) as ctx:
        return service.archive_project(ctx, str(project_id), expected_revision=revision)


@router.post("/{project_id}/unarchive", response_model=ProjectOut)
def unarchive_project(request: Request, project_id: UUID, if_match: IfMatch = None) -> ProjectOut:
    revision = parse_if_match(if_match)
    with service_context(request) as ctx:
        return service.unarchive_project(ctx, str(project_id), expected_revision=revision)


@router.get("/{project_id}/progress", response_model=ProjectProgress)
def project_progress(request: Request, project_id: UUID) -> ProjectProgress:
    with service_context(request) as ctx:
        return service.get_project_progress(ctx, str(project_id))


@router.get("/{project_id}/activity", response_model=Page[HistoryEntry])
def project_activity(
    request: Request,
    project_id: UUID,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> Page[HistoryEntry]:
    with service_context(request) as ctx:
        return service.project_activity(ctx, str(project_id), limit=limit, offset=offset)
