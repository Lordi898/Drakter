"""Decide allow, confirm or deny.

Grants are code plus a read-only file for the agent: nothing at runtime widens them,
and no grant, wildcard included, reaches a write on a protected domain.
"""

from __future__ import annotations

import fnmatch
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from drakter_contracts.tools import RiskClass

from app.permissions.models import (
    PROTECTED_DOMAINS,
    ActionSpec,
    Decision,
    Principal,
    Verdict,
)

DEFAULT_BULK_THRESHOLD: Final = 10
_GRANT: Final = re.compile(r"[a-z][a-z0-9_]*\.([a-z][a-z0-9_]*|\*)")


def load_agent_grants(path: Path) -> tuple[str, ...]:
    """Read `{"granted": [...]}`. A missing file grants nothing; a malformed one fails."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ()
    granted = data.get("granted") if isinstance(data, dict) else None
    if not isinstance(granted, list) or not all(
        isinstance(item, str) and _GRANT.fullmatch(item) for item in granted
    ):
        raise ValueError(f"Malformed agent permissions: {path}")
    return tuple(granted)


class PermissionEngine:
    def __init__(self, agent_grants: Iterable[str] = ()) -> None:
        self._agent_grants = tuple(agent_grants)

    def _is_granted(self, principal: Principal, spec: ActionSpec) -> bool:
        permission = spec.permission
        if permission.endswith(".admin"):
            return principal is Principal.APPROVER
        if principal is Principal.UI:
            return True
        if principal is Principal.AGENT:
            return any(fnmatch.fnmatchcase(permission, grant) for grant in self._agent_grants)
        return False

    def evaluate(
        self,
        principal: Principal,
        spec: ActionSpec,
        *,
        affected_count: int = 1,
        turn_total: int = 0,
        tainted: bool = False,
        bulk_threshold: int = DEFAULT_BULK_THRESHOLD,
    ) -> Decision:
        if spec.domain in PROTECTED_DOMAINS and not spec.permission.endswith(".read"):
            return Decision(Verdict.DENY, "protected_domain")
        if not self._is_granted(principal, spec):
            return Decision(Verdict.DENY, "permission_denied")
        if spec.risk is RiskClass.READ:
            return Decision(Verdict.ALLOW, "read")

        # Strict union of the rules: the most demanding one wins, undo never exempts.
        # A setting can only lower it: a raised one must not switch confirmation off.
        threshold = max(2, min(bulk_threshold, DEFAULT_BULK_THRESHOLD))
        if spec.risk is RiskClass.CONFIRM:
            return Decision(Verdict.CONFIRM, "declared")
        if spec.permission.endswith((".delete", ".execute", ".admin")):
            return Decision(Verdict.CONFIRM, "destructive")
        if affected_count >= threshold or affected_count + turn_total >= threshold:
            return Decision(Verdict.CONFIRM, "bulk")
        if tainted:
            return Decision(Verdict.CONFIRM, "tainted_turn")
        return Decision(Verdict.ALLOW, "granted")
