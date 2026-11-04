"""Confirmations. Listing is for the GUI; deciding is for Electron main only.

These dependencies check the credential themselves, on top of the guard: a route
reachable with another token would still refuse to decide. Agent credentials never
match, and chat or voice have no way into this router.
"""

from __future__ import annotations

from typing import Annotated, Any, Final
from uuid import UUID

from drakter_contracts.common import ContractModel, Origin
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from app.audit.writer import AuditEvent
from app.core.errors import AppError
from app.permissions.models import ActorContext, Principal
from app.services.actions import ActionService

APPROVER_HEADER: Final = "x-drakter-approver"
_NO_STORE: Final = {"Cache-Control": "no-store"}

router = APIRouter(prefix="/api/v1/confirmations")


class ApproveBody(ContractModel):
    params_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval_token: str = Field(min_length=1, max_length=128)


def _actions(request: Request) -> ActionService:
    return request.app.state.actions


def _request_id(request: Request) -> str:
    return request.scope["state"]["request_id"]


def _bearer(request: Request) -> bytes:
    values = request.headers.getlist("authorization")
    if len(values) != 1:
        return b""
    scheme, _, credential = values[0].partition(" ")
    return credential.encode("utf-8") if scheme.lower() == "bearer" else b""


def _deny(request: Request, code: str) -> AppError:
    """Attempts to decide without the credential are audited."""
    actions = _actions(request)
    ctx = ActorContext(Principal.UI, Origin.REST, _request_id(request))
    conn = actions.open()
    try:
        actions._write_alone(  # noqa: SLF001 - same audit path as the service
            conn,
            ctx,
            AuditEvent(
                action="confirmation.decide",
                result="denied",
                error_code=code,
                confirmation_id=request.path_params.get("action_id")
                and str(request.path_params["action_id"]),
            ),
        )
    finally:
        conn.close()
    return AppError("permission_denied", "Approver required", 403)


def require_ui(request: Request) -> Principal:
    if not request.app.state.token.matches(_bearer(request)):
        raise AppError("permission_denied", "GUI credential required", 403)
    return Principal.UI


def require_approver(request: Request) -> Principal:
    """Session bearer, approver header, and no browser context."""
    if not request.app.state.token.matches(_bearer(request)):
        raise _deny(request, "not_gui")
    if "origin" in request.headers:
        raise _deny(request, "origin_present")
    values = request.headers.getlist(APPROVER_HEADER)
    approver = getattr(request.app.state, "approver_token", None)
    if approver is None or len(values) != 1 or not approver.matches(values[0].encode("utf-8")):
        raise _deny(request, "approver_required")
    return Principal.APPROVER


Ui = Annotated[Principal, Depends(require_ui)]
Approver = Annotated[Principal, Depends(require_approver)]


@router.get("")
def list_confirmations(
    request: Request,
    _: Ui,
    status: Annotated[
        str,
        Query(pattern="^(pending|approved|rejected|expired|executing|executed|failed)$"),
    ] = "pending",
) -> dict[str, Any]:
    actions = _actions(request)
    conn = actions.open()
    try:
        actions.expire_due(conn)
        items = actions.list_confirmations(conn, status)
    finally:
        conn.close()
    return {"items": items, "total": len(items)}


@router.get("/{action_id}")
def get_confirmation(request: Request, action_id: UUID, _: Ui) -> dict[str, Any]:
    actions = _actions(request)
    conn = actions.open()
    try:
        return actions.detail(conn, action_id)
    finally:
        conn.close()


@router.post("/{action_id}/approval-token")
def issue_approval_token(
    request: Request, action_id: UUID, principal: Approver
) -> JSONResponse:
    """What main reads before its native dialog: the detail plus the one-use token."""
    actions = _actions(request)
    conn = actions.open()
    try:
        body = actions.detail(conn, action_id)
        body["approval_token"] = actions.approval_token(conn, action_id, principal)
    finally:
        conn.close()
    return JSONResponse(body, headers=_NO_STORE)


@router.post("/{action_id}/approve")
def approve_confirmation(
    request: Request, action_id: UUID, body: ApproveBody, principal: Approver
) -> dict[str, Any]:
    actions = _actions(request)
    conn = actions.open()
    try:
        result = actions.approve(
            conn,
            action_id,
            body.params_hash,
            principal,
            approval_token=body.approval_token,
            correlation_id=_request_id(request),
        )
    finally:
        conn.close()
    return {"id": result.action_id, "status": result.status, "data": result.data}


@router.post("/{action_id}/reject")
def reject_confirmation(
    request: Request, action_id: UUID, principal: Approver
) -> dict[str, str]:
    actions = _actions(request)
    conn = actions.open()
    try:
        actions.reject(conn, action_id, principal, correlation_id=_request_id(request))
    finally:
        conn.close()
    return {"id": str(action_id), "status": "rejected"}
