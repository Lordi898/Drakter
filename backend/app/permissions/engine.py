"""Decide allow, confirm or deny. Grants live in code: nothing at runtime can widen them."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from app.permissions.models import (
    PROTECTED_MODULES,
    ActionSpec,
    ConfirmationPolicy,
    Decision,
    Operation,
    Principal,
    Risk,
    Verdict,
)

DEFAULT_BULK_THRESHOLD: Final = 20

_WRITES: Final = frozenset(
    {Operation.CREATE, Operation.UPDATE, Operation.DELETE, Operation.EXECUTE}
)
_GRANTS: Final[Mapping[Principal, frozenset[Operation]]] = {
    Principal.GUI_RENDERER: _WRITES | {Operation.READ},
    Principal.GUI_APPROVER: frozenset({Operation.READ, Operation.ADMIN}),
    Principal.AGENT: _WRITES | {Operation.READ},
}
# Read-only and explicit. No principal holds a write grant on a protected module.
_PROTECTED_READS: Final[Mapping[Principal, frozenset[str]]] = {
    Principal.GUI_RENDERER: PROTECTED_MODULES,
    Principal.GUI_APPROVER: PROTECTED_MODULES,
    Principal.AGENT: frozenset({"audit"}),
}


class PermissionEngine:
    def __init__(self, bulk_threshold: int = DEFAULT_BULK_THRESHOLD) -> None:
        if bulk_threshold < 2:
            raise ValueError("bulk_threshold must be at least 2")
        self._bulk_threshold = bulk_threshold

    def evaluate(
        self,
        principal: Principal,
        spec: ActionSpec,
        *,
        affected_count: int = 1,
        tainted: bool = False,
    ) -> Decision:
        if spec.module in PROTECTED_MODULES:
            allowed = spec.operation is Operation.READ and spec.module in _PROTECTED_READS.get(
                principal, frozenset()
            )
            if not allowed:
                return Decision(Verdict.DENY, "protected_module")
        if spec.operation not in _GRANTS.get(principal, frozenset()):
            return Decision(Verdict.DENY, "operation_not_granted")
        if spec.operation is Operation.READ:
            return Decision(Verdict.ALLOW, "read")

        # Strict union of the rules: undo never replaces confirmation.
        if spec.operation is Operation.DELETE:
            return Decision(Verdict.CONFIRM, "destructive")
        if spec.risk is Risk.SENSITIVE or spec.confirmation is ConfirmationPolicy.ALWAYS:
            return Decision(Verdict.CONFIRM, "sensitive")
        if spec.operation is Operation.ADMIN:
            return Decision(Verdict.CONFIRM, "admin")
        if affected_count >= self._bulk_threshold:
            return Decision(Verdict.CONFIRM, "bulk")
        if principal is Principal.AGENT:
            if spec.operation is Operation.EXECUTE:
                return Decision(Verdict.CONFIRM, "agent_execute")
            if tainted:
                return Decision(Verdict.CONFIRM, "tainted_turn")
        return Decision(Verdict.ALLOW, "granted")
