"""User-only HTTP API for backups. The agent has no tool that reaches this."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from typing import Annotated, Final, TypeVar

from fastapi import APIRouter, Body, Request

from app.core.config import Settings
from app.core.errors import AppError
from app.services.backup_export import export_workspace
from app.services.backup_models import (
    BundleInfo,
    ConfirmationResponse,
    ConfirmRequest,
    CreateBundleRequest,
    DeleteResponse,
    ExportResponse,
    RestoreReport,
    VerifyResponse,
)
from app.services.backup_service import (
    bundle_digest,
    create_bundle,
    delete_bundle,
    is_bundle_name,
    list_bundles,
    resolve_bundle,
    restore_bundle,
    verify_bundle,
)
from app.services.improvement_ports import (
    ApprovalRequest,
    AuditEvent,
    Principal,
    get_audit,
    get_gate,
    get_principal,
    require_user,
)

logger = logging.getLogger("drakter.backup")

router = APIRouter(prefix="/api/v1/backups")

T = TypeVar("T")
Detail = dict[str, str | int | bool | None]

_ENTITY_TYPE: Final = "backup"
_COLLECTION: Final = "bundles"
_RESTORE: Final = "backup.restore"
_DELETE: Final = "backup.delete"


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


def _approval(request: Request, action: str, name: str, verb: str) -> ApprovalRequest:
    return ApprovalRequest(
        action=action,
        target_id=name,
        digest=bundle_digest(_settings(request), name),
        summary=f"{verb} la copia {name}",
    )


def _request_confirmation(
    request: Request, name: str, action: str, verb: str
) -> ConfirmationResponse:
    principal = _authorize(request, action, name)

    audited_action = f"{action}.request"
    try:
        approval = _approval(request, action, name, verb)
        confirmation_id = get_gate(request).request(approval, principal)
    except AppError as exc:
        _audit(request, principal, audited_action, name, "denied", {"code": exc.code})
        raise
    _audit(request, principal, audited_action, name, "ok")
    return ConfirmationResponse(confirmation_id=confirmation_id)


def _consume(
    request: Request, principal: Principal, action: str, name: str, verb: str, confirmation_id: str
) -> None:
    """Spend the approval against the file as it is now, before acting."""
    try:
        approval = _approval(request, action, name, verb)
        get_gate(request).consume(confirmation_id, approval, principal)
    except AppError as exc:
        _audit(request, principal, action, name, "denied", {"code": exc.code})
        raise




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


@router.post("/{name}/restore-request", response_model=ConfirmationResponse)
def post_restore_request(request: Request, name: str) -> ConfirmationResponse:
    return _request_confirmation(request, name, _RESTORE, "Restaurar")


@router.post("/{name}/delete-request", response_model=ConfirmationResponse)
def post_delete_request(request: Request, name: str) -> ConfirmationResponse:
    return _request_confirmation(request, name, _DELETE, "Borrar")


@router.post("/{name}/restore", response_model=RestoreReport)
def post_restore(request: Request, name: str, body: ConfirmRequest) -> RestoreReport:
    principal = _authorize(request, _RESTORE, name)
    _consume(request, principal, _RESTORE, name, "Restaurar", body.confirmation_id)
    state = request.app.state
    try:
        report = restore_bundle(
            _settings(request),
            name,
            getattr(state, "post_restore_hooks", ()),
            getattr(state, "restore_quiesce", None),
        )
    except AppError as exc:
        _audit(request, principal, _RESTORE, name, "failed", {"code": exc.code})
        raise
    except Exception:
        _audit(request, principal, _RESTORE, name, "failed", {"code": "internal_error"})
        raise
    # Written now on purpose: the restore rolled `audit_events` back, and this
    # entry is the record that it did. The previous history is in `pre_restore`.
    recorded = _audit(
        request,
        principal,
        _RESTORE,
        name,
        "ok" if report.status == "ok" else "failed",
        {
            "status": report.status,
            "pre_restore": report.pre_restore,
            "schema_version": report.schema_version,
            "hook_failures": len(report.hook_failures),
        },
    )
    return report.model_copy(update={"audit_recorded": recorded})


@router.delete("/{name}", response_model=DeleteResponse)
def delete_one(request: Request, name: str, body: ConfirmRequest) -> DeleteResponse:
    principal = _authorize(request, _DELETE, name)
    _consume(request, principal, _DELETE, name, "Borrar", body.confirmation_id)

    def delete() -> DeleteResponse:
        delete_bundle(_settings(request), name)
        return DeleteResponse(name=name, deleted=True)

    return _audited(request, principal, _DELETE, name, delete)
