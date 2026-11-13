"""REST surface of the improvement cycle. Identity always comes from the Principal."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import AwareDatetime

from app.core.config import Settings
from app.services import improvement_feedback, improvement_proposals, improvement_reports
from app.services.improvement_models import (
    MAX_OFFSET,
    MAX_PAGE_SIZE,
    Category,
    ConfirmationBody,
    FeedbackCreate,
    FeedbackOrigin,
    FeedbackReclassify,
    ProposalCreate,
    ProposalStatus,
    RejectBody,
    ReportExportBody,
    Severity,
)
from app.services.improvement_ports import get_audit, get_gate, get_principal
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
        gate=get_gate(request),
        audit=get_audit(request),
        correlation_id=_correlation_id(request),
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
def approval_request(proposal_id: UUID, request: Request) -> dict[str, str]:
    return improvement_proposals.request_approval(_flow(request), str(proposal_id))


@router.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: UUID, body: ConfirmationBody, request: Request) -> dict[str, Any]:
    return improvement_proposals.approve(_flow(request), str(proposal_id), body.confirmation_id)


@router.post("/proposals/{proposal_id}/apply")
def apply(proposal_id: UUID, request: Request) -> dict[str, Any]:
    return improvement_proposals.apply(_flow(request), str(proposal_id))


@router.post("/proposals/{proposal_id}/revert-request")
def revert_request(proposal_id: UUID, request: Request) -> dict[str, str]:
    return improvement_proposals.request_revert(_flow(request), str(proposal_id))


@router.post("/proposals/{proposal_id}/revert")
def revert(proposal_id: UUID, body: ConfirmationBody, request: Request) -> dict[str, Any]:
    return improvement_proposals.revert(_flow(request), str(proposal_id), body.confirmation_id)


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
