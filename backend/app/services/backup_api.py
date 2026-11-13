"""User-only HTTP API for backups. The agent has no tool that reaches this."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable, Mapping
from typing import Annotated, Any, Final, TypeVar

from drakter_contracts.common import Origin as OriginEnum
from fastapi import APIRouter, Body, Request

from app.core.config import Settings
from app.core.errors import AppError
from app.permissions.models import ActorContext
from app.permissions.models import Principal as PermissionPrincipal
from app.services.backup_actions import DELETE_BACKUP, DeleteBackupArgs
from app.services.backup_export import export_workspace
from app.services.backup_models import (
    BundleInfo,
    CreateBundleRequest,
    ExportResponse,
    VerifyResponse,
)
from app.services.backup_service import (
    create_bundle,
    is_bundle_name,
    list_bundles,
    resolve_bundle,
    verify_bundle,
)
from app.services.improvement_ports import (
    AuditEvent,
    Principal,
    get_audit,
    get_principal,
    require_user,
)

logger = logging.getLogger("drakter.backup")

router = APIRouter(prefix="/api/v1/backups")

T = TypeVar("T")
Detail = dict[str, str | int | bool | None]

_ENTITY_TYPE: Final = "backup"
_COLLECTION: Final = "bundles"


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def _audit(
    request: Request,
    principal: Principal,
    action: str,
    target: str,
    result: str,
    detail: Detail | None = None,
) -> bool:
    """Record without masking the outcome: the act already happened or was already refused."""
    state = request.scope.get("state", {})
    event = AuditEvent(
        actor_type=principal.kind,
        action=action,
        entity_type=_ENTITY_TYPE,
        # A client-supplied string only reaches the trail once it is a valid name.
        entity_id=target if target == _COLLECTION or is_bundle_name(target) else "invalid",
        result=result,  # type: ignore[arg-type]
        correlation_id=state.get("request_id"),
        detail=detail or {},
    )
    try:
        get_audit(request).record(event)
    except Exception as exc:
        logger.error("audit record failed for %s", action, exc_info=exc)
        return False
    return True


def _authorize(request: Request, action: str, target: str) -> Principal:
    principal = get_principal(request)
    try:
        require_user(principal)
    except AppError as exc:
        _audit(request, principal, action, target, "denied", {"code": exc.code})
        raise
    return principal


def _audited(
    request: Request, principal: Principal, action: str, target: str, work: Callable[[], T]
) -> T:
    """Run an act and record how it ended."""
    try:
        outcome = work()
    except AppError as exc:
        _audit(request, principal, action, target, "failed", {"code": exc.code})
        raise
    except Exception:
        _audit(request, principal, action, target, "failed", {"code": "internal_error"})
        raise
    _audit(request, principal, action, target, "ok")
    return outcome


@router.get("", response_model=list[BundleInfo])
def get_bundles(request: Request) -> list[BundleInfo]:
    action = "backup.list"
    principal = _authorize(request, action, _COLLECTION)
    return _audited(
        request, principal, action, _COLLECTION, lambda: list_bundles(_settings(request))
    )


@router.post("", response_model=BundleInfo)
def post_bundle(
    request: Request,
    body: Annotated[CreateBundleRequest, Body(default_factory=CreateBundleRequest)],
) -> BundleInfo:
    action = "backup.create"
    principal = _authorize(request, action, _COLLECTION)
    return _audited(
        request,
        principal,
        action,
        _COLLECTION,
        lambda: create_bundle(_settings(request), body.label, body.include_storage),
    )


@router.post("/export", response_model=ExportResponse)
def post_export(request: Request) -> ExportResponse:
    action = "backup.export"
    principal = _authorize(request, action, _COLLECTION)

    def export() -> ExportResponse:
        try:
            path = export_workspace(_settings(request))
        except (OSError, ValueError, sqlite3.Error) as exc:
            logger.error("export failed", exc_info=exc, extra={"event": "backup_export_failed"})
            raise AppError("backup_export_failed", "No se pudo exportar el Workspace", 500) from exc
        return ExportResponse(name=path.name, size_bytes=path.stat().st_size)

    return _audited(request, principal, action, _COLLECTION, export)


@router.post("/{name}/verify", response_model=VerifyResponse)
def post_verify(request: Request, name: str) -> VerifyResponse:
    action = "backup.verify"
    principal = _authorize(request, action, name)

    def verify() -> VerifyResponse:
        manifest = verify_bundle(resolve_bundle(_settings(request), name))
        return VerifyResponse(
            name=name,
            valid=True,
            schema_version=manifest.schema_version,
            file_count=len(manifest.files),
        )

    return _audited(request, principal, action, name, verify)


@router.delete("/{name}")
def delete_one(request: Request, name: str) -> Mapping[str, Any]:
    """Sin cuerpo: 409 `confirmation_required`; se borra en `/confirmations/{id}/approve`.

    `ActionService` audita la petición y la ejecución. Sin el pipeline montado no se borra.
    """
    resolve_bundle(_settings(request), name)  # 400 nombre no válido, 404 inexistente
    actions = getattr(request.app.state, "actions", None)
    spec = actions.registry.get(DELETE_BACKUP) if actions is not None else None
    if spec is None:
        raise AppError(
            "confirmation_unavailable", "No se puede confirmar ahora mismo. No se ha borrado nada.", 503
        )
    actor = ActorContext(
        principal=PermissionPrincipal.UI,
        origin=OriginEnum.REST,
        correlation_id=request.scope.get("state", {}).get("request_id") or "",
    )
    return actions.unwrap(actions.execute_or_request(actor, spec, DeleteBackupArgs(name=name)))
