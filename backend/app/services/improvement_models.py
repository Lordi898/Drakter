"""Domain vocabulary and strict request models of the improvement cycle.

Every model forbids extra fields: `confirmed`, `principal`, `approved` and the
like are rejected rather than ignored. Identity never comes from a body.
"""

from __future__ import annotations

from typing import Annotated, Final, Literal, get_args

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field

MAX_FEEDBACK_CHARS: Final = 8192
MAX_TITLE_CHARS: Final = 200
MAX_RATIONALE_CHARS: Final = 8192
MAX_REASON_CHARS: Final = 2000
MAX_PATCH_BYTES: Final = 1024 * 1024
MAX_PAGE_SIZE: Final = 200
MAX_OFFSET: Final = 2**31

Category = Literal[
    "communication_preference",
    "context_adjustment",
    "skill_fix",
    "procedure_improvement",
    "memory_retrieval",
    "performance",
    "interface",
    "bug_fix",
]
Severity = Literal["low", "medium", "high", "critical"]
ClassifiedBy = Literal["rules", "default", "user"]
FeedbackOrigin = Literal["user", "agent", "system"]
ProposalStatus = Literal[
    "draft",
    "evaluating",
    "evaluated_passed",
    "evaluated_failed",
    "evaluation_blocked",
    "approved",
    "applied",
    "reverted",
    "rejected",
]
EvaluationStatus = Literal["passed", "failed", "blocked"]
EventType = Literal[
    "feedback_recorded",
    "feedback_reclassified",
    "proposal_created",
    "evaluation_started",
    "evaluation_finished",
    "approval_requested",
    "approved",
    "apply_failed",
    "applied",
    "revert_requested",
    "revert_failed",
    "reverted",
    "rejected",
    "invalidated_by_restore",
]

CATEGORIES: Final[tuple[str, ...]] = get_args(Category)
SEVERITIES: Final[tuple[str, ...]] = get_args(Severity)
STATUSES: Final[tuple[str, ...]] = get_args(ProposalStatus)


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


def _no_nul(value: str) -> str:
    # SQLite's length() stops at NUL, so it would dodge the size checks in the DDL.
    if "\x00" in value:
        raise ValueError("NUL is not allowed")
    return value


def _single_line(value: str) -> str:
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("control characters are not allowed")
    return value


def _patch_size(value: str) -> str:
    if len(value.encode("utf-8")) > MAX_PATCH_BYTES:
        raise ValueError("patch too large")
    return value


FeedbackText = Annotated[
    str,
    Field(min_length=1, max_length=MAX_FEEDBACK_CHARS),
    AfterValidator(_no_nul),
    AfterValidator(_not_blank),
]
Title = Annotated[
    str,
    Field(min_length=1, max_length=MAX_TITLE_CHARS),
    AfterValidator(_not_blank),
    AfterValidator(_single_line),
]
Rationale = Annotated[str, Field(max_length=MAX_RATIONALE_CHARS), AfterValidator(_no_nul)]
# A char is at least one byte, so `max_length` bounds the work before encoding.
PatchText = Annotated[
    str, Field(min_length=1, max_length=MAX_PATCH_BYTES), AfterValidator(_patch_size)
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FeedbackCreate(StrictModel):
    text: FeedbackText


class FeedbackReclassify(StrictModel):
    category: Category
    severity: Severity


class ProposalCreate(StrictModel):
    title: Title
    rationale: Rationale = ""
    category: Category | None = None
    feedback_id: Annotated[str, Field(min_length=36, max_length=36)] | None = None
    patch: PatchText | None = None


class ConfirmationBody(StrictModel):
    confirmation_id: Annotated[str, Field(min_length=1, max_length=128)]


class RejectBody(StrictModel):
    reason: Annotated[
        str,
        Field(min_length=1, max_length=MAX_REASON_CHARS),
        AfterValidator(_no_nul),
        AfterValidator(_not_blank),
    ]


class ReportExportBody(StrictModel):
    from_: AwareDatetime | None = Field(default=None, alias="from")
    to: AwareDatetime | None = None
