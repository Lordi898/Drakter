"""Vocabulary of the gate.

`ActionSpec` is the thin interface a tool or route declares. The shared ToolSpec
of `contracts/` maps onto it one to one once it is frozen.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Final, Literal

from pydantic import BaseModel

PROTECTED_MODULES: Final = frozenset({"permissions", "audit", "confirmations"})
_ACTION_NAME: Final = re.compile(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*")
_SENSITIVE_FIELD: Final = re.compile(
    r"authorization|token|secret|password|api_?key|cookie|credential", re.IGNORECASE
)


class Operation(StrEnum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class Risk(StrEnum):
    READ = "read"
    WRITE = "write"
    SENSITIVE = "sensitive"
    FORBIDDEN = "forbidden"


class ConfirmationPolicy(StrEnum):
    NEVER = "never"
    BULK = "bulk"
    ALWAYS = "always"


class Principal(StrEnum):
    GUI_APPROVER = "gui_approver"
    GUI_RENDERER = "gui_renderer"
    AGENT = "agent"
    AUTOMATION = "automation"
    SYSTEM = "system"


ACTOR_TYPES: Final[Mapping[Principal, str]] = {
    Principal.GUI_APPROVER: "user",
    Principal.GUI_RENDERER: "user",
    Principal.AGENT: "agent",
    Principal.AUTOMATION: "automation",
    Principal.SYSTEM: "system",
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
class CallContext:
    """Identity of a call, built by the backend. Never from model-controlled arguments."""

    principal: Principal
    correlation_id: str
    turn_id: str | None = None
    tainted: bool = False


AuditFieldPolicy = Literal["log", "hash"]
Handler = Callable[[sqlite3.Connection, dict[str, Any]], dict[str, Any]]
TargetProbe = Callable[[sqlite3.Connection, dict[str, Any]], str]
AffectedCounter = Callable[[sqlite3.Connection, dict[str, Any]], int]


@dataclass(frozen=True)
class ActionSpec:
    """One operation of the backend.

    `handler` runs inside the transaction of the gate and must not commit. With
    `external=True` it runs outside any transaction: its effects cannot be rolled
    back, so a crash leaves the row `executing` and it ends as `outcome_uncertain`.

    `target_digest` summarizes the current state of the targets. Any change between
    request and approval invalidates the confirmation. Fields not named in
    `audit_fields` are never written to the audit log.
    """

    name: str
    module: str
    operation: Operation
    risk: Risk
    confirmation: ConfirmationPolicy
    params_model: type[BaseModel]
    handler: Handler
    audit_fields: Mapping[str, AuditFieldPolicy] = field(default_factory=dict)
    target_digest: TargetProbe | None = None
    count_affected: AffectedCounter | None = None
    entity_type: str | None = None
    external: bool = False

    def __post_init__(self) -> None:
        if not _ACTION_NAME.fullmatch(self.name) or self.name.split(".")[0] != self.module:
            raise ValueError(f"Invalid action name: {self.name}")
        if self.params_model.model_config.get("extra") != "forbid":
            raise ValueError(f"{self.name}: params_model must set extra='forbid'")
        if self.risk is Risk.FORBIDDEN:
            raise ValueError(f"{self.name}: forbidden actions have no implementation")
        if (self.operation is Operation.READ) != (self.risk is Risk.READ):
            raise ValueError(f"{self.name}: read risk and read operation go together")
        must_confirm = self.operation is Operation.DELETE or self.risk is Risk.SENSITIVE
        if must_confirm and self.confirmation is not ConfirmationPolicy.ALWAYS:
            raise ValueError(f"{self.name}: destructive or sensitive actions always confirm")
        if self.external and self.confirmation is not ConfirmationPolicy.ALWAYS:
            raise ValueError(f"{self.name}: external effects always confirm")
        for name in self.audit_fields:
            if name not in self.params_model.model_fields:
                raise ValueError(f"{self.name}: unknown audit field {name}")
            if _SENSITIVE_FIELD.search(name):
                raise ValueError(f"{self.name}: {name} cannot be audited")


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
