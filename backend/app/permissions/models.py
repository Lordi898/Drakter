"""Vocabulary of the gate.

`ActionSpec` is what the gate executes. REST services declare it directly; a
`ToolSpec` of `app/tools/` is adapted by `app/permissions/tool_gate.py`.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Final

from drakter_contracts.common import ActorType, Origin
from drakter_contracts.tools import AuditPolicy, RiskClass
from pydantic import BaseModel

PROTECTED_DOMAINS: Final = frozenset({"permissions", "audit", "confirmations"})
_PERMISSION: Final = re.compile(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*")
_TOOL_NAME: Final = re.compile(r"[a-z][a-z0-9_]{2,47}")
_SENSITIVE_FIELD: Final = re.compile(
    r"authorization|token|secret|password|api_?key|cookie|credential", re.IGNORECASE
)


class Principal(StrEnum):
    """Who is calling, always derived from the credential."""

    UI = "ui"
    APPROVER = "approver"
    AGENT = "agent"
    SYSTEM = "system"


ACTOR_TYPES: Final[Mapping[Principal, ActorType]] = {
    Principal.UI: ActorType.USER,
    Principal.APPROVER: ActorType.USER,
    Principal.AGENT: ActorType.AGENT,
    Principal.SYSTEM: ActorType.SYSTEM,
}


class Verdict(StrEnum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str


@dataclass(frozen=True)
class ActorContext:
    """Identity of a call. Built by the backend, never from model-controlled arguments."""

    principal: Principal
    origin: Origin
    correlation_id: str
    turn_id: str | None = None
    session_id: str | None = None
    tainted: bool = False
    agent_provider: str | None = None


Handler = Callable[[sqlite3.Connection, BaseModel], Mapping[str, Any]]
TargetResolver = Callable[[sqlite3.Connection, BaseModel], list[dict[str, Any]]]
AffectedCounter = Callable[[sqlite3.Connection, BaseModel], int]
Summarizer = Callable[[BaseModel], str]


@dataclass(frozen=True)
class ActionSpec:
    """One operation of the backend.

    `handler` runs inside the transaction of the gate and must not commit. With
    `external=True` it runs outside any transaction, as anything with its own
    connections or with effects outside SQLite must: those cannot be rolled back, so
    a crash between start and end ends as `outcome_uncertain`.

    `resolve_targets` returns ids with their `revision`, or a `content_hash`. If the
    result differs at approval time the confirmation fails with `conflict`.
    `summarize` is computed by the backend from validated arguments. Fields not
    listed in `audit` are never written to the audit log.
    """

    name: str
    permission: str
    risk: RiskClass
    args_model: type[BaseModel]
    handler: Handler
    summarize: Summarizer | None = None
    audit: Mapping[str, AuditPolicy] = field(default_factory=dict)
    resolve_targets: TargetResolver | None = None
    count_affected: AffectedCounter | None = None
    entity_type: str | None = None
    external: bool = False

    def __post_init__(self) -> None:
        if not _TOOL_NAME.fullmatch(self.name):
            raise ValueError(f"Invalid action name: {self.name}")
        if not _PERMISSION.fullmatch(self.permission):
            raise ValueError(f"{self.name}: invalid permission {self.permission}")
        if self.args_model.model_config.get("extra") != "forbid":
            raise ValueError(f"{self.name}: args_model must set extra='forbid'")
        if self.permission.endswith(".read") and self.risk is not RiskClass.READ:
            raise ValueError(f"{self.name}: a read permission cannot write")
        # Anything that may reach a confirmation needs a backend-made summary.
        if self.risk is not RiskClass.READ and self.summarize is None:
            raise ValueError(f"{self.name}: a summary is required")
        for name in self.audit:
            if name not in self.args_model.model_fields:
                raise ValueError(f"{self.name}: unknown audit field {name}")
            if _SENSITIVE_FIELD.search(name) and self.audit[name] != "omit":
                raise ValueError(f"{self.name}: {name} cannot be audited")

    @property
    def domain(self) -> str:
        return self.permission.split(".", 1)[0]


class ActionRegistry:
    """Whatever is not registered does not exist. Closed at startup."""

    def __init__(self) -> None:
        self._specs: dict[str, ActionSpec] = {}
        self._frozen = False

    def register(self, spec: ActionSpec) -> None:
        if self._frozen:
            raise RuntimeError("ActionRegistry is frozen")
        if spec.name in self._specs:
            raise ValueError(f"Duplicate action: {spec.name}")
        self._specs[spec.name] = spec

    def freeze(self) -> None:
        self._frozen = True

    def get(self, name: str) -> ActionSpec | None:
        return self._specs.get(name)
