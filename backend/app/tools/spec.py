"""Declarative description of an agent tool. Holds no behaviour beyond plain data."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from drakter_contracts.tools import AuditPolicy, RiskClass
from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Identity of a call. It comes from the backend, never from model arguments (F19)."""

    turn_id: UUID
    session_id: UUID
    call_id: str
    principal: Literal["agent"]
    state: Any  # app.state
    # Set by the job lane (`integrations/hermes/lanes.py`), never by the model: a call made
    # from a background job. It travels to `confirmation.requested.job_id`.
    job_id: UUID | None = None


ToolHandler = Callable[[ToolContext, Any], "BaseModel | Awaitable[BaseModel]"]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str  # ^[a-z][a-z0-9_]{2,47}$, unique
    description: str  # for the model, no business rules
    domain: str
    args_model: type[BaseModel]  # extra="forbid"
    result_model: type[BaseModel]
    permission: str  # "<domain>.<action>"
    risk: RiskClass  # always declared, never inferred from the name
    handler: ToolHandler  # sync handlers run in a worker thread
    errors: tuple[str, ...] = ()
    idempotent: bool = False
    timeout_s: float = 15.0  # 1..120
    returns_untrusted: bool = False  # documents, memory: taints the session
    audit: Mapping[str, AuditPolicy] = field(default_factory=dict)  # unlisted means "hash"
    summarize: Callable[[BaseModel], str] | None = None  # required for CONFIRM


class ToolError(Exception):
    """Expected tool failure. ``message`` reaches the agent, so it must be safe to show."""

    def __init__(
        self,
        code: str,
        message: str,
        retryable: bool = False,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details
