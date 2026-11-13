"""REST surface of the improvement cycle. Identity always comes from the Principal."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Annotated, Any
from uuid import UUID, uuid4

from drakter_contracts.common import Origin
from fastapi import APIRouter, Query, Request
from pydantic import AwareDatetime

from app.core.config import Settings
from app.core.errors import AppError
from app.permissions.models import ActorContext
from app.permissions.models import Principal as SecurityPrincipal
from app.services import (
    improvement_actions,
    improvement_feedback,
    improvement_proposals,
    improvement_reports,
)
from app.services.improvement_models import (
    MAX_OFFSET,
    MAX_PAGE_SIZE,
    Category,
    FeedbackCreate,
    FeedbackOrigin,
    FeedbackReclassify,
    ProposalCreate,
    ProposalStatus,
    RejectBody,
    ReportExportBody,
    Severity,
)
from app.services.improvement_ports import ApprovalRequest, get_audit, get_principal
from app.services.improvement_proposals import FlowContext

router = APIRouter(prefix="/api/v1/improvement")

Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
Offset = Annotated[int, Query(ge=0, le=MAX_OFFSET)]


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def _correlation_id(request: Request) -> str | None:
    request_id = request.scope.get("state", {}).get("request_id")
    return request_id if isinstance(request_id, str) else None


def _flow(request: Request) -> FlowContext:
    return FlowContext(
        settings=_settings(request),
        principal=get_principal(request),
        audit=get_audit(request),
        correlation_id=_correlation_id(request),
    )


def _confirm(request: Request, action: str, approval: ApprovalRequest) -> Mapping[str, Any]:
    """Hand the decision to `ActionService`, the single confirmation path."""
    actions = getattr(request.app.state, "actions", None)
    spec = actions.registry.get(action) if actions is not None else None
    if spec is None:
        raise AppError(
            "confirmation_unavailable", "El mecanismo de confirmación no está disponible", 503
        )
    actor = ActorContext(
        principal=SecurityPrincipal.UI,
        origin=Origin.REST,
        correlation_id=_correlation_id(request) or str(uuid4()),
    )
    params = improvement_actions.ProposalDecisionArgs(
        proposal_id=approval.target_id, digest=approval.digest
    )
    summary = approval.summary
    return actions.unwrap(
        actions.execute_or_request(actor, replace(spec, summarize=lambda _: summary), params)
    )


@router.post("/feedback", status_code=201)
def create_feedback(body: FeedbackCreate, request: Request) -> dict[str, Any]:
    return improvement_feedback.record_feedback(
        _settings(request).db_path,
        get_principal(request),
        body.text,
        get_audit(request),
        _correlation_id(request),
    )


@router.get("/feedback")
def list_feedback(
    request: Request,
    limit: Limit = 50,
    offset: Offset = 0,
    category: Category | None = None,
    severity: Severity | None = None,
    origin: FeedbackOrigin | None = None,
) -> dict[str, Any]:
    return improvement_feedback.list_feedback(
        _settings(request).db_path,
        limit=limit,
        offset=offset,
        category=category,
        severity=severity,
        origin=origin,
    )


@router.get("/feedback/{feedback_id}")
def get_feedback(feedback_id: UUID, request: Request) -> dict[str, Any]:
    return improvement_feedback.get_feedback(_settings(request).db_path, str(feedback_id))


@router.patch("/feedback/{feedback_id}/classification")
def reclassify_feedback(
    feedback_id: UUID, body: FeedbackReclassify, request: Request
) -> dict[str, Any]:
    return improvement_feedback.reclassify_feedback(
        _settings(request).db_path,
        get_principal(request),
        str(feedback_id),
        body.category,
        body.severity,
        get_audit(request),
        _correlation_id(request),
    )


@router.post("/proposals", status_code=201)
def create_proposal(body: ProposalCreate, request: Request) -> dict[str, Any]:
    return improvement_proposals.create_proposal(
        _settings(request).db_path,
        get_principal(request),
        body,
        get_audit(request),
        _correlation_id(request),
    )


@router.get("/proposals")
def list_proposals(
    request: Request,
    limit: Limit = 50,
    offset: Offset = 0,
    status: ProposalStatus | None = None,
) -> dict[str, Any]:
    return improvement_proposals.list_proposals(
        _settings(request).db_path, limit=limit, offset=offset, status=status
    )


@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: UUID, request: Request) -> dict[str, Any]:
    return improvement_proposals.get_proposal(_settings(request).db_path, str(proposal_id))


@router.post("/proposals/{proposal_id}/evaluate")
def evaluate(proposal_id: UUID, request: Request) -> dict[str, Any]:
    return improvement_proposals.evaluate(_flow(request), str(proposal_id))


@router.post("/proposals/{proposal_id}/approval-request")
def approval_request(proposal_id: UUID, request: Request) -> Mapping[str, Any]:
    """409 `confirmation_required`: approve at `/api/v1/confirmations/{id}/approve`."""
    approval = improvement_proposals.prepare_approval(_flow(request), str(proposal_id))
    return _confirm(request, improvement_actions.APPROVE_ACTION, approval)


@router.post("/proposals/{proposal_id}/apply")
def apply(proposal_id: UUID, request: Request) -> dict[str, Any]:
    return improvement_proposals.apply(_flow(request), str(proposal_id))


@router.post("/proposals/{proposal_id}/revert-request")
def revert_request(proposal_id: UUID, request: Request) -> Mapping[str, Any]:
    """409 `confirmation_required`: confirm at `/api/v1/confirmations/{id}/approve`."""
    approval = improvement_proposals.prepare_revert(_flow(request), str(proposal_id))
    return _confirm(request, improvement_actions.REVERT_ACTION, approval)


@router.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: UUID, body: RejectBody, request: Request) -> dict[str, Any]:
    return improvement_proposals.reject(_flow(request), str(proposal_id), body.reason)


@router.get("/reports/summary")
def report_summary(
    request: Request,
    start: Annotated[AwareDatetime | None, Query(alias="from")] = None,
    end: Annotated[AwareDatetime | None, Query(alias="to")] = None,
) -> dict[str, Any]:
    return improvement_reports.summary(_settings(request).db_path, start, end)


@router.get("/changelog")
def changelog(
    request: Request,
    limit: Limit = 50,
    offset: Offset = 0,
    proposal_id: UUID | None = None,
) -> dict[str, Any]:
    return improvement_reports.changelog(
        _settings(request).db_path,
        limit=limit,
        offset=offset,
        proposal_id=str(proposal_id) if proposal_id is not None else None,
    )


@router.post("/reports/export", status_code=201)
def export_report(body: ReportExportBody, request: Request) -> dict[str, str]:
    return improvement_reports.export_report(
        _settings(request),
        get_principal(request),
        body.from_,
        body.to,
        get_audit(request),
        _correlation_id(request),
    )
