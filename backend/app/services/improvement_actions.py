"""Approving and reverting an improvement proposal as `ActionService` confirmations.

The GUI asks with `approval-request` or `revert-request`: the backend answers 409
`confirmation_required` and the approver decides through
`/api/v1/confirmations/{id}/approve`. That is the only path, with the common expiry.
The arguments carry the digest, and the target fingerprint (status plus digest)
must not move between request and approval, or the confirmation ends in `conflict`.
Neither action is granted to the agent: its permissions never include them.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from typing import Any, Final

from drakter_contracts.tools import RiskClass
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.permissions.models import ActionRegistry, ActionSpec
from app.services import improvement_proposals

APPROVE_ACTION: Final = "approve_improvement_proposal"
REVERT_ACTION: Final = "revert_improvement_proposal"


class ProposalDecisionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=36, max_length=36)
    digest: str = Field(min_length=64, max_length=64)


def _targets(revert: bool) -> Callable[[sqlite3.Connection, BaseModel], list[dict[str, Any]]]:
    def resolve(conn: sqlite3.Connection, params: BaseModel) -> list[dict[str, Any]]:
        assert isinstance(params, ProposalDecisionArgs)
        fingerprint = improvement_proposals.approval_fingerprint(conn, params.proposal_id, revert)
        return [{"id": params.proposal_id, "content_hash": fingerprint}]

    return resolve


def _spec(
    name: str,
    permission: str,
    revert: bool,
    run: Callable[[Settings, str, str], Mapping[str, Any]],
    settings: Settings,
    verb: str,
) -> ActionSpec:
    return ActionSpec(
        name=name,
        permission=permission,
        risk=RiskClass.CONFIRM,
        args_model=ProposalDecisionArgs,
        # Own connections and, for revert, git: outside the gate's transaction.
        handler=lambda _conn, params: run(settings, params.proposal_id, params.digest),  # type: ignore[attr-defined]
        # Fixed text built from validated arguments; the title is untrusted.
        summarize=lambda params: (
            f"{verb} la propuesta de mejora {params.proposal_id}"  # type: ignore[attr-defined]
            f" (huella {params.digest[:12]})"  # type: ignore[attr-defined]
        ),
        audit={"proposal_id": "log", "digest": "log"},
        resolve_targets=_targets(revert),
        entity_type="improvement_proposal",
        external=True,
    )


def register_actions(registry: ActionRegistry, settings: Settings) -> None:
    """Call after `install_security`, before the registry is frozen."""
    registry.register(
        _spec(APPROVE_ACTION, "improvement.approve", False,
              improvement_proposals.execute_approval, settings, "Aprobar")
    )  # fmt: skip
    registry.register(
        _spec(REVERT_ACTION, "improvement.revert", True,
              improvement_proposals.execute_revert, settings, "Revertir")
    )  # fmt: skip
