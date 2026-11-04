"""Agent tools of the improvement cycle: thin wrappers over ``improvement_tools``.

There are no tools to evaluate, approve, apply or revert, and the author is fixed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Final

from app.services import improvement_tools
from app.services.improvement_models import (
    Category,
    EvaluationStatus,
    ProposalStatus,
    Severity,
    StrictModel,
)
from app.services.improvement_ports import AuditSink, LogAuditSink
from app.services.improvement_tools import (
    CreateProposalParams,
    GetProposalParams,
    ImprovementToolContext,
    ListProposalsParams,
    RecordFeedbackParams,
)
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec

_ERRORS: Final = (
    "validation_error",
    "feedback_not_found",
    "proposal_not_found",
    "internal_error",
)


class FeedbackResult(StrictModel):
    id: str
    category: Category
    severity: Severity
    untrusted: bool


class ProposalSummary(StrictModel):
    id: str
    title: str
    rationale: str
    category: Category | None
    author_kind: str
    status: ProposalStatus
    has_patch: bool
    patch_sha256: str | None
    created_at: str
    untrusted: bool


class ProposalCreated(ProposalSummary):
    pass


class ProposalPage(StrictModel):
    items: list[ProposalSummary]
    total: int
    limit: int
    offset: int


class EvaluationSummary(StrictModel):
    id: str
    status: EvaluationStatus
    changed_paths: list[str]
    protected_paths: list[str]
    untrusted: bool


class ProposalDetail(ProposalSummary):
    evaluation: EvaluationSummary | None


def _project(model: type[StrictModel], data: dict[str, Any]) -> dict[str, Any]:
    """Keep the fields this tool publishes; the models themselves forbid extras."""
    return {name: data[name] for name in model.model_fields}


def _call(
    function: Callable[[ImprovementToolContext, Mapping[str, Any]], dict[str, Any]],
    ctx: ToolContext,
    args: StrictModel,
) -> dict[str, Any]:
    sink: AuditSink | None = getattr(ctx.state, "audit_sink", None)
    outcome = function(
        ImprovementToolContext(
            db_path=ctx.state.settings.db_path,
            audit=sink if sink is not None else LogAuditSink(),
            correlation_id=str(ctx.turn_id),
        ),
        args.model_dump(exclude_none=True),
    )
    if not outcome["ok"]:
        raise ToolError(outcome["error"]["code"], outcome["error"]["message"])
    data: dict[str, Any] = outcome["data"]
    return data


def _record_feedback(ctx: ToolContext, args: RecordFeedbackParams) -> FeedbackResult:
    data = _call(improvement_tools.record_feedback, ctx, args)
    return FeedbackResult.model_validate(_project(FeedbackResult, data))


def _create_proposal(ctx: ToolContext, args: CreateProposalParams) -> ProposalCreated:
    data = _call(improvement_tools.create_proposal, ctx, args)
    return ProposalCreated.model_validate(_project(ProposalCreated, data))


def _list_proposals(ctx: ToolContext, args: ListProposalsParams) -> ProposalPage:
    data = _call(improvement_tools.list_proposals, ctx, args)
    items = [_project(ProposalSummary, item) for item in data["items"]]
    return ProposalPage.model_validate({**data, "items": items})


def _get_proposal(ctx: ToolContext, args: GetProposalParams) -> ProposalDetail:
    data = _call(improvement_tools.get_proposal, ctx, args)
    evaluation = data["evaluation"]
    return ProposalDetail.model_validate(
        {
            **_project(ProposalSummary, data),
            "evaluation": _project(EvaluationSummary, evaluation) if evaluation else None,
        }
    )


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="record_improvement_feedback",
        description="Registra una observación de mejora sobre Drakter.",
        domain="system",
        args_model=RecordFeedbackParams,
        result_model=FeedbackResult,
        permission="improvement.write",
        risk=RiskClass.WRITE,
        handler=_record_feedback,
        errors=_ERRORS,
        audit={"text": "hash"},
        # Fixed text: a tainted turn turns this into a confirmation for the user.
        summarize=lambda _: "Registrar una observación de mejora",
    ),
    ToolSpec(
        name="create_improvement_proposal",
        description="Crea un borrador de propuesta de mejora, con parche opcional.",
        domain="system",
        args_model=CreateProposalParams,
        result_model=ProposalCreated,
        permission="improvement.write",
        risk=RiskClass.WRITE,
        handler=_create_proposal,
        errors=_ERRORS,
        audit={
            "title": "hash",
            "rationale": "hash",
            "patch": "hash",
            "category": "log",
            "feedback_id": "log",
        },
        summarize=lambda _: "Crear un borrador de propuesta de mejora",
    ),
    ToolSpec(
        name="list_improvement_proposals",
        description="Lista propuestas de mejora y su estado.",
        domain="system",
        args_model=ListProposalsParams,
        result_model=ProposalPage,
        permission="improvement.read",
        risk=RiskClass.READ,
        handler=_list_proposals,
        errors=_ERRORS,
        idempotent=True,
        returns_untrusted=True,
        audit={"limit": "log", "offset": "log", "status": "log"},
    ),
    ToolSpec(
        name="get_improvement_proposal",
        description="Consulta una propuesta de mejora y su última evaluación, sin el parche.",
        domain="system",
        args_model=GetProposalParams,
        result_model=ProposalDetail,
        permission="improvement.read",
        risk=RiskClass.READ,
        handler=_get_proposal,
        errors=_ERRORS,
        idempotent=True,
        returns_untrusted=True,
        audit={"proposal_id": "log"},
    ),
)
