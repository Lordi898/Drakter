"""Confirmations. Listing is for the GUI; deciding is for Electron main only.

`SecurityGuardMiddleware` admits `approve` and `reject` only with the `approver` token,
which lives in Electron main and arrives by stdin. Chat, voice and the agent have no
way into this router: the agent token is not valid on this port.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from drakter_contracts.common import ContractModel
from fastapi import APIRouter, Query, Request
from pydantic import Field

from app.core.errors import AppError
from app.permissions.models import Principal
from app.services.actions import DEFAULT_LISTED, MAX_LISTED, ActionService

router = APIRouter(prefix="/api/v1/confirmations")


class ApproveBody(ContractModel):
    params_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


def _actions(request: Request) -> ActionService:
    actions = getattr(request.app.state, "actions", None)
    if actions is None:
        raise AppError("confirmation_unavailable", "Confirmations unavailable", 503)
    return actions


def _request_id(request: Request) -> str:
    return request.scope["state"]["request_id"]


def _require_exact_path(request: Request, verb: str) -> None:
    """Second barrier: the guard's role check holds only for the exact path it recognizes.

    The router also matches a final newline (`approve%0A`), which the guard does not
    treat as this route. Without this, the `ui` token would decide.
    """
    if request.scope["path"].rsplit("/", 1)[-1] != verb:
        raise AppError("permission_denied", "Approver required", 403)


@router.get("")
def list_confirmations(
    request: Request,
    status: Annotated[
        str,
        Query(pattern="^(pending|approved|rejected|expired|executing|executed|failed)$"),
    ] = "pending",
    limit: Annotated[int, Query(ge=1, le=MAX_LISTED)] = DEFAULT_LISTED,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> dict[str, Any]:
    actions = _actions(request)
    conn = actions.open()
    try:
        actions.expire_due(conn)
        try:
            return actions.list_confirmations(conn, status, limit=limit, cursor=cursor)
        except ValueError:
            raise AppError("invalid_query", "Invalid cursor", 400) from None
    finally:
        conn.close()


@router.get("/{action_id}")
def get_confirmation(request: Request, action_id: UUID) -> dict[str, Any]:
    actions = _actions(request)
    conn = actions.open()
    try:
        return actions.detail(conn, action_id)
    finally:
        conn.close()


@router.post("/{action_id}/approve")
def approve_confirmation(
    request: Request, action_id: UUID, body: ApproveBody
) -> dict[str, Any]:
    _require_exact_path(request, "approve")
    actions = _actions(request)
    conn = actions.open()
    try:
        result = actions.approve(
            conn,
            action_id,
            body.params_hash,
            Principal.APPROVER,  # Only that token passes the guard on this path.
            correlation_id=_request_id(request),
        )
    finally:
        conn.close()
    return {"id": result.action_id, "status": result.status, "data": result.data}


@router.post("/{action_id}/reject")
def reject_confirmation(request: Request, action_id: UUID) -> dict[str, str]:
    _require_exact_path(request, "reject")
    actions = _actions(request)
    conn = actions.open()
    try:
        actions.reject(
            conn, action_id, Principal.APPROVER, correlation_id=_request_id(request)
        )
    finally:
        conn.close()
    return {"id": str(action_id), "status": "rejected"}
