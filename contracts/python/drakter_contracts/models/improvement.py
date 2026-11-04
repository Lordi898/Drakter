from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ..common import ContractModel, Id, Instant
from ._base import OutModel


class ImprovementCategory(StrEnum):
    COMMUNICATION = "communication"
    CONTEXT = "context"
    SKILL = "skill"
    PROCEDURE = "procedure"
    MEMORY = "memory"
    PERFORMANCE = "performance"
    INTERFACE = "interface"
    BUG = "bug"


class ImprovementSource(StrEnum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class ProposalStatus(StrEnum):
    DRAFT = "draft"
    EVALUATING = "evaluating"
    READY = "ready"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"


class EvaluationOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class ImprovementFeedbackCreate(ContractModel):
    source: ImprovementSource
    category: ImprovementCategory
    summary: Annotated[str, Field(min_length=1, max_length=2000)]
    correlation_id: str | None = None


class ImprovementFeedbackOut(OutModel):
    id: Id
    source: ImprovementSource
    category: ImprovementCategory
    summary: str
    correlation_id: str | None = None
    created_at: Instant


class ImprovementProposalCreate(ContractModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    category: ImprovementCategory
    summary: Annotated[str, Field(min_length=1, max_length=4000)]
    feedback_id: Id | None = None
    created_by: ImprovementSource = ImprovementSource.USER


class ImprovementProposalUpdate(ContractModel):
    """Aprobar, rechazar o aplicar solo lo decide la GUI; la automejora nunca toca producción sin ello."""

    title: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    summary: Annotated[str, Field(min_length=1, max_length=4000)] | None = None
    status: Literal["approved", "rejected"] | None = None


class ImprovementProposalOut(OutModel):
    id: Id
    title: str
    category: ImprovementCategory
    summary: str
    status: ProposalStatus
    feedback_id: Id | None = None
    document_path: str | None = Field(default=None, description="Relativa al directorio de propuestas")
    git_ref: str | None = None
    created_by: ImprovementSource
    created_at: Instant
    updated_at: Instant
    decided_at: Instant | None = None
    decided_via: Literal["desktop"] | None = None
    applied_at: Instant | None = None


class ImprovementEvaluationCreate(ContractModel):
    proposal_id: Id
    environment: Annotated[str, Field(min_length=1, max_length=200)]
    outcome: EvaluationOutcome
    report_path: str | None = None


class ImprovementEvaluationOut(OutModel):
    id: Id
    proposal_id: Id
    environment: str
    outcome: EvaluationOutcome
    report_path: str | None = None
    created_at: Instant
