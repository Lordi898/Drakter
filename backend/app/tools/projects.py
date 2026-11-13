"""Herramientas del agente para proyectos. El borrado de proyectos queda solo en la GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final
from uuid import UUID

from app.schemas.projects import (
    ProjectCreate,
    ProjectListQuery,
    ProjectOut,
    ProjectProgress,
    ProjectUpdate,
)
from app.schemas.tasks import Out, Page, Strict
from app.services import projects as svc
from app.tools.spec import RiskClass, ToolContext, ToolSpec
from app.tools.tasks import run_service

_DOMAIN: Final = "projects"
_ERR_READ: Final = ("not_found", "validation_error")
_ERR_WRITE: Final = ("not_found", "conflict", "revision_mismatch", "validation_error")


class ProjectIdArgs(Strict):
    project_id: UUID


class ProjectRevisionArgs(Strict):
    project_id: UUID
    expected_revision: int | None = None


class UpdateProjectArgs(Strict):
    project_id: UUID
    expected_revision: int | None = None
    patch: ProjectUpdate


def _create_project(ctx: ToolContext, args: ProjectCreate) -> ProjectOut:
    return run_service(ctx, "create_project", lambda s: svc.create_project(s, args))


def _get_project(ctx: ToolContext, args: ProjectIdArgs) -> ProjectOut:
    return run_service(ctx, "get_project", lambda s: svc.get_project(s, str(args.project_id)))


def _update_project(ctx: ToolContext, args: UpdateProjectArgs) -> ProjectOut:
    return run_service(
        ctx,
        "update_project",
        lambda s: svc.update_project(
            s, str(args.project_id), args.patch, expected_revision=args.expected_revision
        ),
    )


def _archive_project(ctx: ToolContext, args: ProjectRevisionArgs) -> ProjectOut:
    return run_service(
        ctx,
        "archive_project",
        lambda s: svc.archive_project(
            s, str(args.project_id), expected_revision=args.expected_revision
        ),
    )


def _unarchive_project(ctx: ToolContext, args: ProjectRevisionArgs) -> ProjectOut:
    return run_service(
        ctx,
        "unarchive_project",
        lambda s: svc.unarchive_project(
            s, str(args.project_id), expected_revision=args.expected_revision
        ),
    )


def _list_projects(ctx: ToolContext, args: ProjectListQuery) -> Page[ProjectOut]:
    return run_service(ctx, "list_projects", lambda s: svc.list_projects(s, args))


def _get_project_progress(ctx: ToolContext, args: ProjectIdArgs) -> ProjectProgress:
    return run_service(
        ctx,
        "get_project_progress",
        lambda s: svc.get_project_progress(s, str(args.project_id)),
    )


def _spec(
    name: str,
    description: str,
    args_model: type[Strict],
    result_model: type[Out],
    handler: Callable[..., Out],
    risk: RiskClass,
    audit: dict[str, str],
    *,
    idempotent: bool = False,
) -> ToolSpec:
    read = risk is RiskClass.READ
    return ToolSpec(
        name=name,
        description=description,
        domain=_DOMAIN,
        args_model=args_model,
        result_model=result_model,
        permission="projects.read" if read else "projects.write",
        risk=risk,
        handler=handler,
        errors=_ERR_READ if read else _ERR_WRITE,
        idempotent=idempotent,
        audit=audit,
    )


_ID_AUDIT = {"project_id": "log", "expected_revision": "log"}
R_, W_ = RiskClass.READ, RiskClass.WRITE

TOOLS: tuple[ToolSpec, ...] = (
    _spec(
        "create_project", "Crea un proyecto.", ProjectCreate, ProjectOut, _create_project, W_,
        {
            "name": "hash", "description": "hash", "objective": "hash", "status": "log",
            "priority": "log", "start_date": "log", "target_date": "log",
            "manual_progress": "log", "metadata": "omit",
        },
    ),
    _spec(
        "get_project", "Devuelve un proyecto con su progreso.", ProjectIdArgs, ProjectOut,
        _get_project, R_, {"project_id": "log"}, idempotent=True,
    ),
    _spec(
        "update_project", "Modifica campos de un proyecto.", UpdateProjectArgs, ProjectOut,
        _update_project, W_, {**_ID_AUDIT, "patch": "hash"},
    ),
    _spec(
        "archive_project", "Archiva un proyecto.", ProjectRevisionArgs, ProjectOut,
        _archive_project, W_, dict(_ID_AUDIT), idempotent=True,
    ),
    _spec(
        "unarchive_project", "Restaura un proyecto archivado.", ProjectRevisionArgs, ProjectOut,
        _unarchive_project, W_, dict(_ID_AUDIT), idempotent=True,
    ),
    _spec(
        "list_projects", "Lista proyectos con filtros.", ProjectListQuery, Page[ProjectOut],
        _list_projects, R_,
        {
            "status": "log", "priority": "log", "q": "hash", "include_archived": "log",
            "sort": "log", "limit": "log", "offset": "log",
        },
        idempotent=True,
    ),
    _spec(
        "get_project_progress", "Devuelve el progreso de un proyecto.", ProjectIdArgs,
        ProjectProgress, _get_project_progress, R_, {"project_id": "log"}, idempotent=True,
    ),
)
