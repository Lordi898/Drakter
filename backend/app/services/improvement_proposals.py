"""Proposal lifecycle: drafting, isolated evaluation, approval, apply and revert.

Drakter proposes; only a user with a gate-issued confirmation can approve or
revert. Approval is bound by a digest to the exact patch and evaluation, and each
state change is one conditional UPDATE plus its event in a single transaction.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import sqlite3
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from app.core.config import Settings
from app.core.errors import AppError
from app.services import improvement_lab, improvement_policy
from app.services.improvement_lab import (
    AppliedChange,
    EvaluationOutcome,
    apply_patch,
    evaluate_patch,
    load_lab_config,
    revert_change,
)
from app.services.improvement_models import ProposalCreate, ProposalStatus
from app.services.improvement_policy import is_protected
from app.services.improvement_ports import (
    ApprovalRequest,
    AuditSink,
    ConfirmationGate,
    Principal,
    require_user,
)
from app.services.improvement_store import (
    AuditScope,
    audited,
    insert_event,
    new_id,
    open_db,
    page,
    transaction,
    utc_now,
)

logger = logging.getLogger("drakter.improvement")

ACTION_APPROVE: Final = "improvement.approve"
ACTION_APPROVE_PROTECTED: Final = "improvement.approve_protected"
ACTION_REVERT: Final = "improvement.revert"

_ENTITY: Final = "improvement_proposal"
_RESTORE_ACTOR: Final = Principal(kind="system", id="restore")
_RECOVERY_ACTOR: Final = Principal(kind="system", id="startup")
_MAX_OUTPUT_CHARS: Final = 16384
_REEVALUABLE: Final = frozenset(
    {"draft", "evaluated_passed", "evaluated_failed", "evaluation_blocked"}
)
# `applied` is left out on purpose: a live change is undone by reverting it, and
# rejecting would hide that it is still on its branch.
_REJECTABLE: Final = frozenset(
    {"draft", "evaluating", "evaluated_passed", "evaluated_failed",
     "evaluation_blocked", "approved"}
)
# Serializes every step that touches git or decides around it, so a second apply
# or a concurrent reject sees the settled state. Single-process backend.
_GIT_LOCK: Final = threading.Lock()

_SUMMARY_COLUMNS: Final = (
    "id, title, rationale, category, feedback_id, author_kind, author_id, patch_sha256,"
    " length(patch) AS patch_size, status, current_evaluation_id, pending_evaluation_id,"
    " approved_digest, approved_at, applied_branch, applied_commit, applied_at, reverted_at,"
    " rejected_at, rejection_reason, created_at, updated_at"
)


@dataclass(frozen=True)
class FlowContext:
    settings: Settings
    principal: Principal
    gate: ConfirmationGate
    audit: AuditSink
    correlation_id: str | None = None


@dataclass(frozen=True)
class Proposal:
    id: str
    status: ProposalStatus
    author_kind: str
    patch: bytes | None
    current_evaluation_id: str | None
    approved_digest: str | None
    applied_branch: str | None
    applied_commit: str | None


@dataclass(frozen=True)
class Evaluation:
    id: str
    status: str
    base_commit: str | None
    changed_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]


def _invalid_transition() -> AppError:
    return AppError(
        "invalid_transition", "La propuesta no admite esta acción en su estado actual", 409
    )


def _no_patch() -> AppError:
    return AppError("proposal_has_no_patch", "La propuesta no tiene parche", 409)


def _not_found() -> AppError:
    return AppError("proposal_not_found", "La propuesta no existe", 404)


def _protected_final() -> AppError:
    return AppError(
        "protected_path_forbidden",
        "Un parche que no es del usuario no puede tocar rutas protegidas",
        409,
    )


def patch_hash(patch: bytes | None) -> str:
    return hashlib.sha256(patch).hexdigest() if patch is not None else ""


def compute_digest(
    proposal_id: str, patch_sha256: str, evaluation_id: str | None, base_commit: str | None
) -> str:
    material = f"{proposal_id}|{patch_sha256}|{evaluation_id or ''}|{base_commit or ''}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _digest_of(proposal: Proposal, evaluation: Evaluation | None) -> str:
    return compute_digest(
        proposal.id,
        patch_hash(proposal.patch),
        evaluation.id if evaluation is not None else None,
        evaluation.base_commit if evaluation is not None else None,
    )


def _fetch_proposal(conn: sqlite3.Connection, proposal_id: str) -> Proposal:
    row = conn.execute(
        "SELECT id, status, author_kind, patch, current_evaluation_id, approved_digest,"
        " applied_branch, applied_commit FROM improvement_proposals WHERE id = ?",
        (proposal_id,),
    ).fetchone()
    if row is None:
        raise _not_found()
    return Proposal(**dict(row))


def _fetch_evaluation(conn: sqlite3.Connection, evaluation_id: str | None) -> Evaluation | None:
    if evaluation_id is None:
        return None
    row = conn.execute(
        "SELECT id, status, base_commit, changed_paths, protected_paths"
        " FROM improvement_evaluations WHERE id = ?",
        (evaluation_id,),
    ).fetchone()
    if row is None:
        return None
    return Evaluation(
        id=row["id"],
        status=row["status"],
        base_commit=row["base_commit"],
        changed_paths=tuple(json.loads(row["changed_paths"])),
        protected_paths=tuple(json.loads(row["protected_paths"])),
    )


def _protected_paths(changed: tuple[str, ...], reported: tuple[str, ...]) -> tuple[str, ...]:
    """The lab's report plus the live policy: a tighter policy applies at once."""
    return tuple(sorted({*reported, *(path for path in changed if is_protected(path))}))


def _transition(
    conn: sqlite3.Connection,
    proposal_id: str,
    *,
    expected: str,
    target: str,
    event: str,
    actor: Principal,
    fields: Mapping[str, str | None] | None = None,
    guards: Mapping[str, str | None] | None = None,
    detail: Mapping[str, str | int | bool | None] | None = None,
) -> None:
    """Atomic compare-and-set of the status. Column names are internal constants."""
    assignments = {"status": target, "updated_at": utc_now(), **(fields or {})}
    columns = ", ".join(f"{column} = ?" for column in assignments)
    conditions = "".join(f" AND {column} IS ?" for column in (guards or {}))
    cursor = conn.execute(
        f"UPDATE improvement_proposals SET {columns} WHERE id = ? AND status = ?{conditions}",
        (*assignments.values(), proposal_id, expected, *(guards or {}).values()),
    )
    if cursor.rowcount != 1:
        raise _invalid_transition()
    insert_event(
        conn,
        event_type=event,
        actor=actor,
        proposal_id=proposal_id,
        from_status=expected,
        to_status=target,
        detail=detail,
    )


def create_proposal(
    db_path: Path,
    principal: Principal,
    body: ProposalCreate,
    audit: AuditSink,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    proposal_id = new_id()
    patch = body.patch.encode("utf-8") if body.patch is not None else None
    sha = patch_hash(patch) if patch is not None else None
    with audited(
        audit, principal, "improvement.proposal_create", _ENTITY, proposal_id, correlation_id
    ) as scope:
        scope.detail.update(has_patch=patch is not None, patch_sha256=sha)
        if principal.kind not in ("user", "agent"):
            raise AppError("forbidden_author", "Este autor no puede crear propuestas", 403)
        now = utc_now()
        with open_db(db_path) as conn, transaction(conn):
            category = body.category
            if body.feedback_id is not None:
                row = conn.execute(
                    "SELECT category FROM improvement_feedback WHERE id = ?",
                    (body.feedback_id,),
                ).fetchone()
                if row is None:
                    raise AppError("feedback_not_found", "El feedback no existe", 404)
                category = category or row["category"]
            conn.execute(
                "INSERT INTO improvement_proposals (id, title, rationale, category,"
                " feedback_id, author_kind, author_id, patch, patch_sha256, status,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)",
                (
                    proposal_id, body.title, body.rationale, category, body.feedback_id,
                    principal.kind, principal.id, patch, sha, now, now,
                ),
            )
            insert_event(
                conn,
                event_type="proposal_created",
                actor=principal,
                proposal_id=proposal_id,
                feedback_id=body.feedback_id,
                to_status="draft",
                detail={"patch_sha256": sha},
            )
            return _load_public(conn, proposal_id)


def _public(row: sqlite3.Row) -> dict[str, Any]:
    fields = dict(row)
    fields.pop("approved_digest")
    fields.pop("pending_evaluation_id")
    fields["has_patch"] = row["patch_sha256"] is not None
    fields["untrusted"] = True
    return fields


def _load_public(conn: sqlite3.Connection, proposal_id: str) -> dict[str, Any]:
    row = conn.execute(
        f"SELECT {_SUMMARY_COLUMNS} FROM improvement_proposals WHERE id = ?", (proposal_id,)
    ).fetchone()
    if row is None:
        raise _not_found()
    return _public(row)


def _public_evaluation(conn: sqlite3.Connection, evaluation_id: str | None) -> dict[str, Any] | None:
    if evaluation_id is None:
        return None
    row = conn.execute(
        "SELECT id, status, base_commit, patch_sha256, changed_paths, protected_paths, checks,"
        " reason, created_at FROM improvement_evaluations WHERE id = ?",
        (evaluation_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        **dict(row),
        "changed_paths": json.loads(row["changed_paths"]),
        "protected_paths": json.loads(row["protected_paths"]),
        "checks": json.loads(row["checks"]),
        "untrusted": True,
    }


def get_proposal(
    db_path: Path, proposal_id: str, *, include_patch: bool = True
) -> dict[str, Any]:
    with open_db(db_path) as conn:
        result = _load_public(conn, proposal_id)
        result["evaluation"] = _public_evaluation(conn, result["current_evaluation_id"])
        if include_patch:
            row = conn.execute(
                "SELECT patch FROM improvement_proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
            patch: bytes | None = row["patch"]
            result["patch"] = patch.decode("utf-8") if patch is not None else None
    return result


def list_proposals(
    db_path: Path, *, limit: int, offset: int, status: ProposalStatus | None = None
) -> dict[str, Any]:
    where = "status = ?" if status is not None else "1 = 1"
    values = (status,) if status is not None else ()
    with open_db(db_path) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM improvement_proposals WHERE {where}", values
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT {_SUMMARY_COLUMNS} FROM improvement_proposals WHERE {where}"
            " ORDER BY created_at DESC, id LIMIT ? OFFSET ?",
            (*values, limit, offset),
        ).fetchall()
    return page([_public(row) for row in rows], total, limit, offset)


def _settled_outcome(
    proposal: Proposal, outcome: EvaluationOutcome
) -> tuple[str, str | None, tuple[str, ...]]:
    """Fail closed on what this module can verify itself, whatever the lab reports."""
    protected = _protected_paths(outcome.changed_paths, outcome.protected_paths)
    if outcome.patch_sha256 != patch_hash(proposal.patch):
        return "blocked", "patch_hash_mismatch", protected
    if outcome.status == "passed" and not outcome.base_commit:
        return "blocked", "missing_base_commit", protected
    if outcome.status == "passed" and proposal.author_kind != "user" and protected:
        return "failed", "protected_path", protected
    return outcome.status, outcome.reason, protected


def _finish_evaluation(
    ctx: FlowContext, proposal: Proposal, evaluation_id: str, outcome: EvaluationOutcome
) -> str:
    status, reason, protected = _settled_outcome(proposal, outcome)
    checks = [
        {
            "name": check.name,
            "passed": check.passed,
            "exit_code": check.exit_code,
            "output_tail": check.output_tail[-_MAX_OUTPUT_CHARS:],
        }
        for check in outcome.checks
    ]
    target = {
        "passed": "evaluated_passed",
        "failed": "evaluated_failed",
        "blocked": "evaluation_blocked",
    }[status]
    with open_db(ctx.settings.db_path) as conn, transaction(conn):
        conn.execute(
            "INSERT INTO improvement_evaluations (id, proposal_id, status, base_commit,"
            " patch_sha256, changed_paths, protected_paths, checks, reason, requested_by,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                evaluation_id, proposal.id, status, outcome.base_commit,
                patch_hash(proposal.patch), json.dumps(list(outcome.changed_paths)),
                json.dumps(list(protected)), json.dumps(checks), reason, ctx.principal.id,
                utc_now(),
            ),
        )
        _transition(
            conn,
            proposal.id,
            expected="evaluating",
            target=target,
            event="evaluation_finished",
            actor=ctx.principal,
            fields={"current_evaluation_id": evaluation_id, "pending_evaluation_id": None},
            guards={"pending_evaluation_id": evaluation_id},
            detail={"evaluation_id": evaluation_id, "evaluation_status": status},
        )
    return status


def evaluate(ctx: FlowContext, proposal_id: str) -> dict[str, Any]:
    with audited(
        ctx.audit, ctx.principal, "improvement.evaluate", _ENTITY, proposal_id,
        ctx.correlation_id,
    ) as scope:
        require_user(ctx.principal)
        evaluation_id = new_id()
        scope.detail["evaluation_id"] = evaluation_id
        with open_db(ctx.settings.db_path) as conn:
            proposal = _fetch_proposal(conn, proposal_id)
            if proposal.patch is None:
                raise _no_patch()
            if proposal.status not in _REEVALUABLE:
                raise _invalid_transition()
            previous = _fetch_evaluation(conn, proposal.current_evaluation_id)
            if proposal.author_kind != "user" and previous is not None and _protected_paths(
                previous.changed_paths, previous.protected_paths
            ):
                raise _protected_final()
            with transaction(conn):
                _transition(
                    conn,
                    proposal.id,
                    expected=proposal.status,
                    target="evaluating",
                    event="evaluation_started",
                    actor=ctx.principal,
                    fields={"pending_evaluation_id": evaluation_id},
                    detail={"evaluation_id": evaluation_id},
                )
        try:
            # The author is the proposal's, not the caller's: a user evaluating an
            # agent patch must not lift the protected-path rule.
            outcome = evaluate_patch(
                load_lab_config(ctx.settings),
                proposal.id,
                proposal.patch,
                proposal.author_kind,  # type: ignore[arg-type]
            )
        except Exception as exc:
            scope.failed = True
            code = exc.code if isinstance(exc, AppError) else "internal_error"
            _finish_evaluation(
                ctx,
                proposal,
                evaluation_id,
                EvaluationOutcome(
                    status="blocked",
                    base_commit=None,
                    patch_sha256=patch_hash(proposal.patch),
                    changed_paths=(),
                    protected_paths=(),
                    checks=(),
                    reason=code,
                ),
            )
            raise
        scope.detail["evaluation_status"] = _finish_evaluation(
            ctx, proposal, evaluation_id, outcome
        )
    return get_proposal(ctx.settings.db_path, proposal_id, include_patch=False)


def _approval_for(proposal: Proposal, evaluation: Evaluation | None) -> ApprovalRequest:
    """Check the proposal can be approved and rebuild the exact approval object."""
    if proposal.patch is None:
        if proposal.status not in ("draft", "evaluated_passed"):
            raise _invalid_transition()
    elif (
        proposal.status != "evaluated_passed"
        or evaluation is None
        or evaluation.status != "passed"
        or not evaluation.base_commit
    ):
        raise _invalid_transition()
    protected = (
        _protected_paths(evaluation.changed_paths, evaluation.protected_paths)
        if evaluation is not None
        else ()
    )
    if protected and proposal.author_kind != "user":
        raise _protected_final()
    digest = _digest_of(proposal, evaluation)
    # Fixed text: the title is untrusted and must not speak inside a human approval.
    target = f"propuesta {proposal.id} (huella {digest[:12]})"
    if protected:
        return ApprovalRequest(
            ACTION_APPROVE_PROTECTED,
            proposal.id,
            digest,
            f"Aprobar {target}, que toca {len(protected)} rutas protegidas",
        )
    return ApprovalRequest(ACTION_APPROVE, proposal.id, digest, f"Aprobar {target}")


def request_approval(ctx: FlowContext, proposal_id: str) -> dict[str, str]:
    with audited(
        ctx.audit, ctx.principal, "improvement.approval_request", _ENTITY, proposal_id,
        ctx.correlation_id,
    ) as scope:
        require_user(ctx.principal)
        with open_db(ctx.settings.db_path) as conn:
            proposal = _fetch_proposal(conn, proposal_id)
            evaluation = _fetch_evaluation(conn, proposal.current_evaluation_id)
            approval = _approval_for(proposal, evaluation)
            scope.detail.update(requested_action=approval.action, digest=approval.digest)
            confirmation_id = ctx.gate.request(approval, ctx.principal)
            with transaction(conn):
                insert_event(
                    conn,
                    event_type="approval_requested",
                    actor=ctx.principal,
                    proposal_id=proposal.id,
                    from_status=proposal.status,
                    to_status=proposal.status,
                    detail={"digest": approval.digest, "requested_action": approval.action},
                )
    return {
        "confirmation_id": confirmation_id,
        "action": approval.action,
        "digest": approval.digest,
    }


def approve(ctx: FlowContext, proposal_id: str, confirmation_id: str) -> dict[str, Any]:
    with audited(
        ctx.audit, ctx.principal, "improvement.approve", _ENTITY, proposal_id,
        ctx.correlation_id,
    ) as scope:
        require_user(ctx.principal)
        with open_db(ctx.settings.db_path) as conn:
            proposal = _fetch_proposal(conn, proposal_id)
            evaluation = _fetch_evaluation(conn, proposal.current_evaluation_id)
            approval = _approval_for(proposal, evaluation)
            scope.detail.update(requested_action=approval.action, digest=approval.digest)
            ctx.gate.consume(confirmation_id, approval, ctx.principal)
            with transaction(conn):
                _transition(
                    conn,
                    proposal.id,
                    expected=proposal.status,
                    target="approved",
                    event="approved",
                    actor=ctx.principal,
                    fields={"approved_digest": approval.digest, "approved_at": utc_now()},
                    guards={"current_evaluation_id": proposal.current_evaluation_id},
                    detail={
                        "digest": approval.digest,
                        "evaluation_id": proposal.current_evaluation_id,
                        "approved_action": approval.action,
                    },
                )
            return _load_public(conn, proposal.id)


def _record_git_failure(
    ctx: FlowContext, scope: AuditScope, proposal: Proposal, event: str, code: str
) -> None:
    scope.failed = True
    with open_db(ctx.settings.db_path) as conn, transaction(conn):
        insert_event(
            conn,
            event_type=event,
            actor=ctx.principal,
            proposal_id=proposal.id,
            from_status=proposal.status,
            to_status=proposal.status,
            detail={"code": code},
        )


def _verified_digest(proposal: Proposal, evaluation: Evaluation | None) -> str:
    digest = _digest_of(proposal, evaluation)
    stored = proposal.approved_digest
    if evaluation is None or stored is None or not hmac.compare_digest(stored, digest):
        raise AppError(
            "approval_digest_mismatch",
            "La aprobación no corresponde al contenido actual de la propuesta",
            409,
        )
    return digest


def _require_no_pending_restore(settings: Settings) -> None:
    # Deferred: keeps this module importable without loading the backup service.
    from app.services import backup_service

    # The backup front does not track unfinished restore hooks yet: without that
    # marker there is nothing pending to detect. Apply still needs the approval
    # bound to the exact patch digest.
    restore_hooks_pending = getattr(backup_service, "restore_hooks_pending", None)
    if restore_hooks_pending is not None and restore_hooks_pending(settings):
        raise AppError(
            "restore_hooks_pending",
            "Hay una restauración pendiente de completar; no se puede aplicar",
            409,
        )


def apply(ctx: FlowContext, proposal_id: str) -> dict[str, Any]:
    with audited(
        ctx.audit, ctx.principal, "improvement.apply", _ENTITY, proposal_id, ctx.correlation_id
    ) as scope:
        require_user(ctx.principal)
        with _GIT_LOCK:
            with open_db(ctx.settings.db_path) as conn:
                proposal = _fetch_proposal(conn, proposal_id)
                evaluation = _fetch_evaluation(conn, proposal.current_evaluation_id)
            if proposal.patch is None:
                raise _no_patch()
            if proposal.status != "approved":
                raise _invalid_transition()
            digest = _verified_digest(proposal, evaluation)
            assert evaluation is not None and evaluation.base_commit is not None
            scope.detail["digest"] = digest
            _require_no_pending_restore(ctx.settings)
            if improvement_policy.check_paths(
                evaluation.changed_paths,
                proposal.author_kind,  # type: ignore[arg-type]
            ):
                raise _protected_final()
            # Fixed message: the title is untrusted and must not reach git history.
            message = f"improvement: apply proposal {proposal.id}"
            scope.attempt()
            try:
                config = load_lab_config(ctx.settings)
                change = apply_patch(
                    config, proposal.id, proposal.patch, evaluation.base_commit, message
                )
            except Exception as exc:
                code = exc.code if isinstance(exc, AppError) else "internal_error"
                _record_git_failure(ctx, scope, proposal, "apply_failed", code)
                raise
            scope.detail.update(branch=change.branch, commit=change.commit)
            try:
                with open_db(ctx.settings.db_path) as conn, transaction(conn):
                    _transition(
                        conn,
                        proposal.id,
                        expected="approved",
                        target="applied",
                        event="applied",
                        actor=ctx.principal,
                        fields={
                            "applied_branch": change.branch,
                            "applied_commit": change.commit,
                            "applied_at": utc_now(),
                        },
                        guards={"approved_digest": digest},
                        detail={"branch": change.branch, "commit": change.commit},
                    )
            except AppError:
                # A restore invalidated the approval meanwhile: do not leave its branch.
                code = "state_changed"
                try:
                    revert_change(config, change)
                except Exception:
                    code = "state_changed_revert_failed"
                _record_git_failure(ctx, scope, proposal, "apply_failed", code)
                raise
    return get_proposal(ctx.settings.db_path, proposal_id, include_patch=False)


def _revert_approval(proposal: Proposal, evaluation: Evaluation | None) -> ApprovalRequest:
    if proposal.status != "applied" or proposal.applied_commit is None:
        raise _invalid_transition()
    return ApprovalRequest(
        ACTION_REVERT,
        proposal.id,
        _verified_digest(proposal, evaluation),
        f"Revertir propuesta {proposal.id} (commit {proposal.applied_commit[:12]})",
    )


def request_revert(ctx: FlowContext, proposal_id: str) -> dict[str, str]:
    with audited(
        ctx.audit, ctx.principal, "improvement.revert_request", _ENTITY, proposal_id,
        ctx.correlation_id,
    ) as scope:
        require_user(ctx.principal)
        with open_db(ctx.settings.db_path) as conn:
            proposal = _fetch_proposal(conn, proposal_id)
            evaluation = _fetch_evaluation(conn, proposal.current_evaluation_id)
            approval = _revert_approval(proposal, evaluation)
            scope.detail["digest"] = approval.digest
            confirmation_id = ctx.gate.request(approval, ctx.principal)
            with transaction(conn):
                insert_event(
                    conn,
                    event_type="revert_requested",
                    actor=ctx.principal,
                    proposal_id=proposal.id,
                    from_status=proposal.status,
                    to_status=proposal.status,
                    detail={"digest": approval.digest},
                )
    return {
        "confirmation_id": confirmation_id,
        "action": approval.action,
        "digest": approval.digest,
    }


def revert(ctx: FlowContext, proposal_id: str, confirmation_id: str) -> dict[str, Any]:
    with audited(
        ctx.audit, ctx.principal, "improvement.revert", _ENTITY, proposal_id, ctx.correlation_id
    ) as scope:
        require_user(ctx.principal)
        with _GIT_LOCK:
            with open_db(ctx.settings.db_path) as conn:
                proposal = _fetch_proposal(conn, proposal_id)
                evaluation = _fetch_evaluation(conn, proposal.current_evaluation_id)
            approval = _revert_approval(proposal, evaluation)
            assert proposal.applied_branch is not None and proposal.applied_commit is not None
            scope.detail["digest"] = approval.digest
            ctx.gate.consume(confirmation_id, approval, ctx.principal)
            change = AppliedChange(proposal.applied_branch, proposal.applied_commit)
            scope.attempt()
            try:
                revert_change(load_lab_config(ctx.settings), change)
            except Exception as exc:
                code = exc.code if isinstance(exc, AppError) else "internal_error"
                _record_git_failure(ctx, scope, proposal, "revert_failed", code)
                raise
            with open_db(ctx.settings.db_path) as conn, transaction(conn):
                _transition(
                    conn,
                    proposal.id,
                    expected="applied",
                    target="reverted",
                    event="reverted",
                    actor=ctx.principal,
                    fields={"reverted_at": utc_now()},
                    detail={"commit": change.commit},
                )
    return get_proposal(ctx.settings.db_path, proposal_id, include_patch=False)


def reject(ctx: FlowContext, proposal_id: str, reason: str) -> dict[str, Any]:
    with audited(
        ctx.audit, ctx.principal, "improvement.reject", _ENTITY, proposal_id, ctx.correlation_id
    ):
        require_user(ctx.principal)
        with _GIT_LOCK, open_db(ctx.settings.db_path) as conn:
            proposal = _fetch_proposal(conn, proposal_id)
            if proposal.status not in _REJECTABLE:
                raise _invalid_transition()
            with transaction(conn):
                _transition(
                    conn,
                    proposal.id,
                    expected=proposal.status,
                    target="rejected",
                    event="rejected",
                    actor=ctx.principal,
                    fields={
                        "rejected_at": utc_now(),
                        "rejection_reason": reason,
                        "pending_evaluation_id": None,
                    },
                )
            return _load_public(conn, proposal.id)


def _has_schema(conn: sqlite3.Connection) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'improvement_proposals'"
        ).fetchone()
        is not None
    )


def _reset_stale(
    conn: sqlite3.Connection, statuses: tuple[str, ...], event: str, actor: Principal
) -> int:
    """Roll back stale states in one transaction, joining the caller's if there is one."""
    if not _has_schema(conn):  # A copy older than this schema has nothing to reset.
        return 0
    own_transaction = not conn.in_transaction
    if own_transaction:
        conn.execute("BEGIN IMMEDIATE")
    try:
        marks = ", ".join("?" for _ in statuses)
        rows = conn.execute(
            f"SELECT id, status FROM improvement_proposals WHERE status IN ({marks})", statuses
        ).fetchall()
        for proposal_id, status in rows:
            _transition(
                conn,
                proposal_id,
                expected=status,
                target="evaluated_passed" if status == "approved" else "draft",
                event=event,
                actor=actor,
                fields={
                    "approved_digest": None,
                    "approved_at": None,
                    "pending_evaluation_id": None,
                },
            )
    except BaseException:
        if own_transaction:
            conn.execute("ROLLBACK")
        raise
    if own_transaction:
        conn.execute("COMMIT")
    return len(rows)


def invalidate_after_restore(conn: sqlite3.Connection) -> int:
    """Drop approvals and in-flight evaluations a restored database cannot vouch for.

    ``approved`` returns to ``evaluated_passed`` without its digest and
    ``evaluating`` to ``draft``, each with an ``invalidated_by_restore`` event.
    Joins the caller's transaction if there is one. Returns the rows changed.
    """
    return _reset_stale(
        conn, ("approved", "evaluating"), "invalidated_by_restore", _RESTORE_ACTOR
    )


def recover_interrupted(settings: Settings) -> int:
    """Startup step: evaluations cut short by a stop go back to ``draft``.

    Also sweeps their leftover experiments. Returns the proposals recovered.
    """
    with open_db(settings.db_path) as conn:
        recovered = _reset_stale(
            conn, ("evaluating",), "recovered_after_interrupt", _RECOVERY_ACTOR
        )
    improvement_lab.sweep_experiments(load_lab_config(settings))
    return recovered
