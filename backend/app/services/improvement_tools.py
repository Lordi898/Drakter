"""Plain functions behind the agent's improvement tools, free of FastAPI.

The author is always the agent. There is deliberately no way here to evaluate,
approve, apply or revert: those stay on the user's side of the API.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Final

from pydantic import Field, ValidationError

from app.core.errors import AppError
from app.services import improvement_feedback, improvement_proposals
from app.services.improvement_models import (
    MAX_PAGE_SIZE,
    FeedbackCreate,
    ProposalCreate,
    ProposalStatus,
    StrictModel,
)
from app.services.improvement_ports import AuditSink, LogAuditSink, Principal

AGENT_PRINCIPAL: Final = Principal(kind="agent", id="hermes")

ToolResult = dict[str, Any]


class RecordFeedbackParams(FeedbackCreate):
    pass


class CreateProposalParams(ProposalCreate):
    pass


class ListProposalsParams(StrictModel):
    limit: Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE)] = 50
    offset: Annotated[int, Field(ge=0, le=2**31)] = 0
    status: ProposalStatus | None = None


class GetProposalParams(StrictModel):
    proposal_id: Annotated[str, Field(min_length=36, max_length=36)]


@dataclass(frozen=True)
class ImprovementToolContext:
    db_path: Path
    audit: AuditSink = field(default_factory=LogAuditSink)
    correlation_id: str | None = None


def _error(code: str, message: str) -> ToolResult:
    return {"ok": False, "error": {"code": code, "message": message}}


def _guarded(run: Callable[[], dict[str, Any]]) -> ToolResult:
    """Turn every failure into a structured result that never echoes the input."""
    try:
        return {"ok": True, "data": run()}
    except ValidationError:
        return _error("validation_error", "Parámetros no válidos")
    except AppError as exc:
        return _error(exc.code, exc.message)
    except Exception:
        return _error("internal_error", "Error interno")


def record_feedback(ctx: ImprovementToolContext, params: Mapping[str, Any]) -> ToolResult:
    def run() -> dict[str, Any]:
        body = RecordFeedbackParams.model_validate(dict(params))
        return improvement_feedback.record_feedback(
            ctx.db_path, AGENT_PRINCIPAL, body.text, ctx.audit, ctx.correlation_id
        )

    return _guarded(run)


def create_proposal(ctx: ImprovementToolContext, params: Mapping[str, Any]) -> ToolResult:
    def run() -> dict[str, Any]:
        body = CreateProposalParams.model_validate(dict(params))
        return improvement_proposals.create_proposal(
            ctx.db_path, AGENT_PRINCIPAL, body, ctx.audit, ctx.correlation_id
        )

    return _guarded(run)


def list_proposals(ctx: ImprovementToolContext, params: Mapping[str, Any]) -> ToolResult:
    def run() -> dict[str, Any]:
        body = ListProposalsParams.model_validate(dict(params))
        return improvement_proposals.list_proposals(
            ctx.db_path, limit=body.limit, offset=body.offset, status=body.status
        )

    return _guarded(run)


def get_proposal(ctx: ImprovementToolContext, params: Mapping[str, Any]) -> ToolResult:
    def run() -> dict[str, Any]:
        body = GetProposalParams.model_validate(dict(params))
        return improvement_proposals.get_proposal(
            ctx.db_path, body.proposal_id, include_patch=False
        )

    return _guarded(run)
