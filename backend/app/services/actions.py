"""Single path for every confirmable write, whatever its origin.

An operation with effective risk `confirm` only stores a row and answers
`confirmation_required`. Execution happens in `approve`, from the stored arguments,
exactly once. Hermes and the model take no part in that decision.

Lifecycle: pending -> approved -> executing -> executed | failed, or pending ->
rejected | expired. Success is audited in the transaction of the action; refusals and
failures in their own one, after the rollback. If the audit cannot be written, nothing
runs.
"""

from __future__ import annotations

import hmac
import json
import logging
import sqlite3
import threading
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Protocol
from uuid import UUID, uuid4

from drakter_contracts.common import Origin, format_instant
from drakter_contracts.errors import HTTP_STATUS, ConfirmationTicket, ErrorCode
from drakter_contracts.events import ConfirmationRequested, ConfirmationResolved
from drakter_contracts.tools import (
    RiskClass,
    ToolConfirmationRequired,
    ToolErrorBody,
    ToolFailed,
    ToolOk,
)
from pydantic import BaseModel, ValidationError

from app.audit.writer import AuditEvent, filter_params, write
from app.core.errors import AppError
from app.database.connection import connect
from app.permissions.canonical import after, args_hash, canonical_json, utc_now
from app.permissions.credentials import ApprovalSigner
from app.permissions.engine import DEFAULT_BULK_THRESHOLD, PermissionEngine
from app.permissions.models import (
    ACTOR_TYPES,
    ActionRegistry,
    ActionSpec,
    ActorContext,
    Decision,
    Principal,
    Verdict,
)

CONFIRMATION_TTL_SECONDS: Final = 300
MAX_SUMMARY_LENGTH: Final = 500
MAX_LISTED: Final = 100
_DECIDED_VIA: Final = "desktop"
_SYSTEM_CORRELATION: Final = "system"
_COLUMNS: Final = (
    "id, tool_name, actor_type, origin, turn_id, correlation_id, args_json, args_hash, "
    "targets_json, summary, affected_count, risk, status, created_at, expires_at, "
    "decided_at, decided_via, executed_at, result_json, error_code"
)

logger = logging.getLogger("drakter.actions")

ToolResult = ToolOk | ToolFailed | ToolConfirmationRequired


class EventSink(Protocol):
    def publish(self, event_type: str, payload: Mapping[str, Any], correlation_id: str) -> None: ...


class ConfirmationRequiredError(Exception):
    """REST form of a pending confirmation: 409 with the `confirmation` object."""

    def __init__(self, ticket: ConfirmationTicket) -> None:
        super().__init__("confirmation_required")
        self.ticket = ticket


@dataclass(frozen=True)
class ActionResult:
    action_id: str
    status: str
    data: Mapping[str, Any] | None


@dataclass(frozen=True)
class ReconcileReport:
    expired: int
    failed: int


def _error(code: ErrorCode, message: str) -> AppError:
    return AppError(code.value, message, HTTP_STATUS[code])


def _failed(code: str, message: str) -> ToolFailed:
    return ToolFailed(error=ToolErrorBody(code=code, message=message))


def _displayable(text: str) -> str:
    """Drop control and bidi characters: a summary must read as what it stores."""
    cleaned = "".join(
        " " if unicodedata.category(char) in ("Cc", "Cf", "Zl", "Zp") else char for char in text
    )
    return cleaned[:MAX_SUMMARY_LENGTH]


class ActionService:
    def __init__(
        self,
        *,
        db_path: Path,
        registry: ActionRegistry,
        engine: PermissionEngine,
        signer: ApprovalSigner,
        events: EventSink | None = None,
        ttl_seconds: float = CONFIRMATION_TTL_SECONDS,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.registry = registry
        self._db_path = db_path
        self._engine = engine
        self._signer = signer
        self._events = events
        self._ttl = ttl_seconds
        self._clock = clock
        self._turn_lock = threading.Lock()
        self._turn_total: tuple[str | None, int] = (None, 0)

    def open(self) -> sqlite3.Connection:
        conn = connect(self._db_path)
        conn.execute("PRAGMA recursive_triggers=ON")
        if conn.execute("PRAGMA recursive_triggers").fetchone() != (1,):
            conn.close()
            raise sqlite3.OperationalError("recursive_triggers is not active")
        return conn

    # ---------------------------------------------------------------- request

    def execute_or_request(
        self, ctx: ActorContext, spec: ActionSpec, params: BaseModel
    ) -> ToolResult:
        """Run the action or leave it pending. Refusals are results, not exceptions."""
        conn = self.open()
        try:
            args = params.model_dump(mode="json")
            try:
                canonical = canonical_json(args)
            except ValueError:
                return self._refuse(
                    conn, ctx, spec, ErrorCode.VALIDATION_ERROR.value, "Invalid arguments"
                )
            digest = args_hash(spec.name, canonical)
            conn.execute("BEGIN IMMEDIATE")
            try:
                decision, affected = self._decide(conn, ctx, spec, params)
                if decision.verdict is Verdict.DENY:
                    conn.execute("ROLLBACK")
                    return self._refuse(
                        conn,
                        ctx,
                        spec,
                        ErrorCode.PERMISSION_DENIED.value,
                        "Action not permitted",
                        args=args,
                        digest=digest,
                        reason=decision.reason,
                    )
                if decision.verdict is Verdict.CONFIRM:
                    return self._request(conn, ctx, spec, params, canonical, digest, affected)
                event = self._event(spec, "success", args, digest, affected)
                if spec.external:
                    # Its own connections would block on this transaction. The audit
                    # goes first: if it cannot be written, nothing runs.
                    conn.execute("ROLLBACK")
                    self._write_alone(
                        conn, ctx, replace(event, action=f"{spec.name}.started")
                    )
                    outcome = spec.handler(conn, params)
                    self._write_alone(conn, ctx, event)
                else:
                    outcome = spec.handler(conn, params)
                    self._require_transaction(conn)
                    write(conn, ctx, event)
                    conn.execute("COMMIT")
            except Exception as exc:  # noqa: BLE001 - every failure becomes a structured result
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                code, message = self._describe(exc)
                return self._refuse(
                    conn, ctx, spec, code, message, args=args, digest=digest, result="failed"
                )
            self._count_for_turn(ctx, spec, affected)
            return ToolOk(data=dict(outcome))
        finally:
            conn.close()

    def authorize(
        self, ctx: ActorContext, spec: ActionSpec, params: BaseModel
    ) -> tuple[Verdict, ToolResult | None]:
        """Decide for a caller that runs the handler itself (`ToolGate`).

        `CONFIRM` stores the row: the caller must not run anything.
        """
        conn = self.open()
        try:
            args = params.model_dump(mode="json")
            canonical = canonical_json(args)
            digest = args_hash(spec.name, canonical)
            conn.execute("BEGIN IMMEDIATE")
            try:
                decision, affected = self._decide(conn, ctx, spec, params)
                if decision.verdict is Verdict.CONFIRM:
                    return Verdict.CONFIRM, self._request(
                        conn, ctx, spec, params, canonical, digest, affected
                    )
                conn.execute("ROLLBACK")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            if decision.verdict is Verdict.DENY:
                refused = self._refuse(
                    conn,
                    ctx,
                    spec,
                    ErrorCode.PERMISSION_DENIED.value,
                    "Action not permitted",
                    args=args,
                    digest=digest,
                    reason=decision.reason,
                )
                return Verdict.DENY, refused
            self._count_for_turn(ctx, spec, affected)
            return Verdict.ALLOW, None
        finally:
            conn.close()

    def _decide(
        self, conn: sqlite3.Connection, ctx: ActorContext, spec: ActionSpec, params: BaseModel
    ) -> tuple[Decision, int]:
        affected = spec.count_affected(conn, params) if spec.count_affected else 1
        decision = self._engine.evaluate(
            ctx.principal,
            spec,
            affected_count=affected,
            turn_total=self._turn_so_far(ctx),
            tainted=ctx.tainted,
            bulk_threshold=self._bulk_threshold(conn),
        )
        return decision, affected

    @staticmethod
    def _bulk_threshold(conn: sqlite3.Connection) -> int:
        row = conn.execute("SELECT value_json FROM settings WHERE key = 'bulk_threshold'").fetchone()
        value = json.loads(row[0]) if row else None
        return value if isinstance(value, int) and not isinstance(value, bool) else (
            DEFAULT_BULK_THRESHOLD
        )

    def _turn_so_far(self, ctx: ActorContext) -> int:
        with self._turn_lock:
            turn, total = self._turn_total
        return total if ctx.turn_id is not None and turn == ctx.turn_id else 0

    def _count_for_turn(self, ctx: ActorContext, spec: ActionSpec, affected: int) -> None:
        if ctx.turn_id is None or spec.risk is RiskClass.READ:
            return
        with self._turn_lock:
            turn, total = self._turn_total
            self._turn_total = (ctx.turn_id, affected + (total if turn == ctx.turn_id else 0))

    def _request(
        self,
        conn: sqlite3.Connection,
        ctx: ActorContext,
        spec: ActionSpec,
        params: BaseModel,
        canonical: str,
        digest: str,
        affected: int,
    ) -> ToolConfirmationRequired:
        """Store the row and close the transaction opened by the caller."""
        now = self._clock()
        action_id = str(uuid4())
        expires_at = format_instant(after(now, self._ttl))
        targets = spec.resolve_targets(conn, params) if spec.resolve_targets else []
        summary = _displayable(spec.summarize(params) if spec.summarize else spec.name)
        turn_id = self._existing_turn(conn, ctx.turn_id)
        conn.execute(
            f"INSERT INTO pending_confirmations ({_COLUMNS}) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, "
            "NULL, NULL, NULL, NULL, NULL)",
            (
                action_id,
                spec.name,
                ACTOR_TYPES[ctx.principal].value,
                ctx.origin.value,
                turn_id,
                ctx.correlation_id,
                canonical,
                digest,
                canonical_json(targets),
                summary,
                affected,
                "confirm" if spec.risk is RiskClass.CONFIRM else "write",
                format_instant(now),
                expires_at,
            ),
        )
        write(
            conn,
            ctx,
            self._event(
                spec,
                "confirmation_required",
                params.model_dump(mode="json"),
                digest,
                affected,
                confirmation_id=action_id,
            ),
        )
        conn.execute("COMMIT")
        self._publish(
            "confirmation.requested",
            ConfirmationRequested(
                action_id=UUID(action_id),
                session_id=UUID(ctx.session_id) if ctx.session_id else None,
                turn_id=UUID(turn_id) if turn_id else None,
                tool=spec.name,
                summary=summary,
                affected_count=affected,
                expires_at=after(now, self._ttl),
            ),
            ctx.correlation_id,
        )
        return ToolConfirmationRequired(
            action_id=UUID(action_id), summary=summary, expires_at=after(now, self._ttl)
        )

    # ---------------------------------------------------------------- decide

    def approval_token(
        self, conn: sqlite3.Connection, action_id: UUID, principal: Principal
    ) -> str:
        if principal is not Principal.APPROVER:
            raise _error(ErrorCode.PERMISSION_DENIED, "Approver required")
        row = self._row(conn, action_id)
        if row is None:
            raise _error(ErrorCode.NOT_FOUND, "Confirmation not found")
        if row["status"] != "pending":
            raise _error(ErrorCode.CONFIRMATION_ALREADY_RESOLVED, "Confirmation already resolved")
        return self._signer.issue(
            row["id"], row["tool_name"], row["args_hash"], row["expires_at"]
        )

    def approve(
        self,
        conn: sqlite3.Connection,
        action_id: UUID,
        params_hash: str,
        principal: Principal,
        *,
        approval_token: str,
        correlation_id: str,
    ) -> ActionResult:
        ctx = ActorContext(principal, Origin.REST, correlation_id)
        if principal is not Principal.APPROVER:
            self._audit_alone(conn, ctx, "confirmation.approve", "denied", "permission_denied",
                              str(action_id))
            raise _error(ErrorCode.PERMISSION_DENIED, "Approver required")

        row: dict[str, Any] | None = None
        claimed = False
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._row(conn, action_id)
            refusal = self._refusal_for(row, str(action_id), params_hash, approval_token)
            if refusal is not None:
                code, expired = refusal
                if expired and row is not None:
                    self._expire_rows(conn, [row])
                    conn.execute("COMMIT")
                    self._publish_resolved(row["id"], "expired", code.value, correlation_id)
                else:
                    conn.execute("ROLLBACK")
                self._audit_alone(conn, ctx, "confirmation.approve", "denied", code.value,
                                  str(action_id), row)
                raise _error(code, "Confirmation cannot be approved")
            assert row is not None

            moment = format_instant(self._clock())
            won = conn.execute(
                "UPDATE pending_confirmations SET status = 'approved', decided_at = ?, "
                "decided_via = ? WHERE id = ? AND status = 'pending' AND args_hash = ? "
                "AND expires_at > ? RETURNING id",
                (moment, _DECIDED_VIA, row["id"], params_hash, moment),
            ).fetchone()
            if won is None:
                conn.execute("ROLLBACK")
                raise _error(
                    ErrorCode.CONFIRMATION_ALREADY_RESOLVED, "Confirmation already resolved"
                )
            claimed = True
            conn.execute(
                "UPDATE pending_confirmations SET status = 'executing' WHERE id = ? "
                "AND status = 'approved'",
                (row["id"],),
            )

            spec, params = self._prepare(conn, row)
            if spec.external:
                write(conn, ctx, self._row_event(row, "confirmation.approved", "success"))
                conn.execute("COMMIT")
                outcome = spec.handler(conn, params)
                conn.execute("BEGIN IMMEDIATE")
            else:
                outcome = spec.handler(conn, params)
                self._require_transaction(conn)
            data = dict(outcome)
            conn.execute(
                "UPDATE pending_confirmations SET status = 'executed', executed_at = ?, "
                "result_json = ? WHERE id = ? AND status = 'executing'",
                (format_instant(self._clock()), canonical_json(data), row["id"]),
            )
            write(conn, ctx, self._row_event(row, spec.name, "success"))
            conn.execute("COMMIT")
        except AppError as exc:
            # Only the call that won the row may close it: a loser must not touch it.
            if claimed:
                self._fail(conn, ctx, row, exc.code)
            elif conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        except Exception as exc:  # noqa: BLE001 - a claimed row must never stay open
            if not claimed:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            code, _ = self._describe(exc)
            self._fail(conn, ctx, row, code)
            raise _error(ErrorCode.INTERNAL_ERROR, "Action failed") from None
        self._publish_resolved(row["id"], "executed", None, correlation_id)
        return ActionResult(row["id"], "executed", data)

    def reject(
        self,
        conn: sqlite3.Connection,
        action_id: UUID,
        principal: Principal,
        *,
        correlation_id: str,
    ) -> None:
        ctx = ActorContext(principal, Origin.REST, correlation_id)
        if principal is not Principal.APPROVER:
            self._audit_alone(conn, ctx, "confirmation.reject", "denied", "permission_denied",
                              str(action_id))
            raise _error(ErrorCode.PERMISSION_DENIED, "Approver required")
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._row(conn, action_id)
            if row is None:
                raise _error(ErrorCode.NOT_FOUND, "Confirmation not found")
            changed = conn.execute(
                "UPDATE pending_confirmations SET status = 'rejected', decided_at = ?, "
                "decided_via = ? WHERE id = ? AND status = 'pending' RETURNING id",
                (format_instant(self._clock()), _DECIDED_VIA, row["id"]),
            ).fetchone()
            if changed is None:
                raise _error(
                    ErrorCode.CONFIRMATION_ALREADY_RESOLVED, "Confirmation already resolved"
                )
            write(conn, ctx, self._row_event(row, "confirmation.rejected", "denied",
                                             "confirmation_rejected"))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        self._publish_resolved(row["id"], "rejected", None, correlation_id)

    def expire_due(self, conn: sqlite3.Connection) -> int:
        now = format_instant(self._clock())
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = self._select(
                conn, "status = 'pending' AND expires_at <= ?", (now,)
            )
            self._expire_rows(conn, rows)
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        for row in rows:
            self._publish_resolved(row["id"], "expired", None, row["correlation_id"])
        return len(rows)

    def reconcile_on_boot(self, conn: sqlite3.Connection) -> ReconcileReport:
        """Close what a previous process left open. Never re-runs anything.

        Every pending row expires: the signing key died with that process. A row
        left mid-way has an unknown outcome and must not be retried.
        """
        ctx = self._system_ctx(_SYSTEM_CORRELATION)
        conn.execute("BEGIN IMMEDIATE")
        try:
            pending = self._select(conn, "status = 'pending'", ())
            self._expire_rows(conn, pending)
            unfinished = self._select(conn, "status IN ('approved', 'executing')", ())
            for row in unfinished:
                conn.execute(
                    "UPDATE pending_confirmations SET status = 'failed', "
                    "error_code = 'outcome_uncertain' WHERE id = ?",
                    (row["id"],),
                )
                write(conn, ctx, self._row_event(row, "confirmation.reconciled", "failed",
                                                 "outcome_uncertain"))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return ReconcileReport(expired=len(pending), failed=len(unfinished))

    # ---------------------------------------------------------------- read

    def list_confirmations(
        self, conn: sqlite3.Connection, status: str | None = "pending"
    ) -> list[dict[str, Any]]:
        where = "1 = 1" if status is None else "status = ?"
        rows = self._select(
            conn,
            f"{where} ORDER BY created_at DESC LIMIT {MAX_LISTED}",
            () if status is None else (status,),
        )
        return [self._view(row) for row in rows]

    def detail(self, conn: sqlite3.Connection, action_id: UUID) -> dict[str, Any]:
        row = self._row(conn, action_id)
        if row is None:
            raise _error(ErrorCode.NOT_FOUND, "Confirmation not found")
        return self._view(row)

    def ticket(self, conn: sqlite3.Connection, action_id: UUID) -> ConfirmationTicket:
        row = self._row(conn, action_id)
        if row is None:
            raise _error(ErrorCode.NOT_FOUND, "Confirmation not found")
        return ConfirmationTicket(
            id=row["id"],
            summary=row["summary"],
            affected_count=row["affected_count"],
            expires_at=row["expires_at"],
            params_hash=row["args_hash"],
        )

    def unwrap(self, outcome: ToolResult) -> Mapping[str, Any]:
        """REST form of a result: data, or the exception of the common envelope."""
        if isinstance(outcome, ToolOk):
            return outcome.data
        if isinstance(outcome, ToolConfirmationRequired):
            conn = self.open()
            try:
                raise ConfirmationRequiredError(self.ticket(conn, outcome.action_id))
            finally:
                conn.close()
        code = outcome.error.code
        known = ErrorCode._value2member_map_.get(code)
        status = HTTP_STATUS[known] if isinstance(known, ErrorCode) else 400
        raise AppError(code, outcome.error.message, status)

    def action_result(
        self, conn: sqlite3.Connection, action_id: UUID, ctx: ActorContext
    ) -> ToolResult:
        """Outcome for whoever asked. Never carries arguments or anything to approve with."""
        row = self._row(conn, action_id)
        if row is None or row["actor_type"] != ACTOR_TYPES[ctx.principal].value:
            return _failed(ErrorCode.NOT_FOUND.value, "Confirmation not found")
        result = json.loads(row["result_json"]) if row["result_json"] else None
        return ToolOk(
            data={"status": row["status"], "result": result, "error_code": row["error_code"]}
        )

    # ---------------------------------------------------------------- internals

    def _refusal_for(
        self,
        row: Mapping[str, Any] | None,
        action_id: str,
        params_hash: str,
        approval_token: str,
    ) -> tuple[ErrorCode, bool] | None:
        if row is None:
            return ErrorCode.NOT_FOUND, False
        if not self._signer.verify(
            approval_token, row["id"], row["tool_name"], row["args_hash"], row["expires_at"]
        ):
            return ErrorCode.PERMISSION_DENIED, False
        if row["status"] != "pending":
            return ErrorCode.CONFIRMATION_ALREADY_RESOLVED, False
        if row["expires_at"] <= format_instant(self._clock()):
            return ErrorCode.CONFIRMATION_EXPIRED, True
        if not hmac.compare_digest(row["args_hash"].encode("utf-8"), params_hash.encode("utf-8")):
            return ErrorCode.CONFLICT, False
        return None

    def _prepare(
        self, conn: sqlite3.Connection, row: Mapping[str, Any]
    ) -> tuple[ActionSpec, BaseModel]:
        """Rebuild the action from the stored row and check nothing moved underneath."""
        spec = self.registry.get(row["tool_name"])
        if spec is None:
            raise _error(ErrorCode.CONFIRMATION_UNAVAILABLE, "Action no longer exists")
        if args_hash(row["tool_name"], row["args_json"]) != row["args_hash"]:
            raise _error(ErrorCode.CONFLICT, "Stored arguments do not match")
        params = spec.args_model.model_validate(json.loads(row["args_json"]))
        targets = spec.resolve_targets(conn, params) if spec.resolve_targets else []
        if canonical_json(targets) != row["targets_json"]:
            raise _error(ErrorCode.CONFLICT, "Targets changed since the request")
        affected = spec.count_affected(conn, params) if spec.count_affected else 1
        if affected != row["affected_count"]:
            raise _error(ErrorCode.CONFLICT, "Targets changed since the request")
        return spec, params

    def _fail(
        self,
        conn: sqlite3.Connection,
        ctx: ActorContext,
        row: Mapping[str, Any] | None,
        code: str,
    ) -> None:
        """Roll back, then close the row in its own transaction: no retry stays open."""
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        if row is None:
            return
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "UPDATE pending_confirmations SET status = 'approved', decided_at = ?, "
                "decided_via = ? WHERE id = ? AND status = 'pending'",
                (format_instant(self._clock()), _DECIDED_VIA, row["id"]),
            )
            conn.execute(
                "UPDATE pending_confirmations SET status = 'failed', error_code = ? "
                "WHERE id = ? AND status IN ('approved', 'executing')",
                (code, row["id"]),
            )
            write(conn, ctx, self._row_event(row, "confirmation.failed", "failed", code))
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        self._publish_resolved(row["id"], "failed", code, ctx.correlation_id)

    def _expire_rows(self, conn: sqlite3.Connection, rows: list[Mapping[str, Any]]) -> None:
        ctx = self._system_ctx(_SYSTEM_CORRELATION)
        for row in rows:
            conn.execute(
                "UPDATE pending_confirmations SET status = 'expired' WHERE id = ? "
                "AND status = 'pending'",
                (row["id"],),
            )
            write(conn, ctx, self._row_event(row, "confirmation.expired", "denied",
                                             ErrorCode.CONFIRMATION_EXPIRED.value))

    def _refuse(
        self,
        conn: sqlite3.Connection,
        ctx: ActorContext,
        spec: ActionSpec,
        code: str,
        message: str,
        *,
        args: Mapping[str, Any] | None = None,
        digest: str | None = None,
        result: str = "denied",
        reason: str | None = None,
    ) -> ToolFailed:
        event = self._event(spec, result, args or {}, digest, None, error_code=reason or code)
        self._write_alone(conn, ctx, event)
        return _failed(code, message)

    def _audit_alone(
        self,
        conn: sqlite3.Connection,
        ctx: ActorContext,
        action: str,
        result: str,
        code: str,
        confirmation_id: str,
        row: Mapping[str, Any] | None = None,
    ) -> None:
        self._write_alone(
            conn,
            ctx,
            AuditEvent(
                action=action,
                result=result,
                tool_name=row["tool_name"] if row else None,
                params_hash=row["args_hash"] if row else None,
                error_code=code,
                confirmation_id=confirmation_id,
            ),
        )

    @staticmethod
    def _write_alone(conn: sqlite3.Connection, ctx: ActorContext, event: AuditEvent) -> None:
        conn.execute("BEGIN IMMEDIATE")
        try:
            write(conn, ctx, event)
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise

    @staticmethod
    def _event(
        spec: ActionSpec,
        result: str,
        args: Mapping[str, Any],
        digest: str | None,
        affected: int | None,
        *,
        error_code: str | None = None,
        confirmation_id: str | None = None,
    ) -> AuditEvent:
        return AuditEvent(
            action=spec.name,
            result=result,
            tool_name=spec.name,
            entity_type=spec.entity_type,
            affected_count=affected,
            params=filter_params(args, spec.audit),
            params_hash=digest,
            error_code=error_code,
            confirmation_id=confirmation_id,
        )

    def _row_event(
        self, row: Mapping[str, Any], action: str, result: str, code: str | None = None
    ) -> AuditEvent:
        spec = self.registry.get(row["tool_name"])
        args = json.loads(row["args_json"])
        return AuditEvent(
            action=action,
            result=result,
            tool_name=row["tool_name"],
            entity_type=spec.entity_type if spec else None,
            affected_count=row["affected_count"],
            params=filter_params(args, spec.audit) if spec else None,
            params_hash=row["args_hash"],
            error_code=code,
            confirmation_id=row["id"],
        )

    @staticmethod
    def _require_transaction(conn: sqlite3.Connection) -> None:
        if not conn.in_transaction:
            raise RuntimeError("A handler closed the transaction of the gate")

    @staticmethod
    def _describe(exc: Exception) -> tuple[str, str]:
        if isinstance(exc, AppError):
            return exc.code, "Action failed"
        if isinstance(exc, ValidationError):
            return ErrorCode.VALIDATION_ERROR.value, "Invalid arguments"
        logger.exception("Action failed", extra={"event": "action_failed"})
        return ErrorCode.INTERNAL_ERROR.value, "Action failed"

    @staticmethod
    def _existing_turn(conn: sqlite3.Connection, turn_id: str | None) -> str | None:
        if turn_id is None:
            return None
        row = conn.execute("SELECT 1 FROM agent_turns WHERE id = ?", (turn_id,)).fetchone()
        return turn_id if row else None

    @staticmethod
    def _system_ctx(correlation_id: str) -> ActorContext:
        return ActorContext(Principal.SYSTEM, Origin.INTERNAL, correlation_id)

    def _row(self, conn: sqlite3.Connection, action_id: UUID) -> dict[str, Any] | None:
        rows = self._select(conn, "id = ?", (str(action_id),))
        return rows[0] if rows else None

    @staticmethod
    def _select(
        conn: sqlite3.Connection, where: str, arguments: tuple[Any, ...]
    ) -> list[dict[str, Any]]:
        cursor = conn.execute(
            f"SELECT {_COLUMNS} FROM pending_confirmations WHERE {where}", arguments
        )
        names = [description[0] for description in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]

    @staticmethod
    def _view(row: Mapping[str, Any]) -> dict[str, Any]:
        """What the GUI shows. The arguments are data, never instructions."""
        return {
            "id": row["id"],
            "tool": row["tool_name"],
            "actor_type": row["actor_type"],
            "origin": row["origin"],
            "risk": row["risk"],
            "status": row["status"],
            "summary": row["summary"],
            "affected_count": row["affected_count"],
            "args": json.loads(row["args_json"]),
            "targets": json.loads(row["targets_json"]),
            "params_hash": row["args_hash"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "decided_at": row["decided_at"],
            "executed_at": row["executed_at"],
            "error_code": row["error_code"],
        }

    def _publish_resolved(
        self, action_id: str, status: str, code: str | None, correlation_id: str
    ) -> None:
        self._publish(
            "confirmation.resolved",
            ConfirmationResolved(action_id=UUID(action_id), status=status, error_code=code),
            correlation_id,
        )

    def _publish(self, event_type: str, payload: BaseModel, correlation_id: str) -> None:
        """Runs after COMMIT. A lost event must not undo a committed action."""
        if self._events is None:
            return
        try:
            self._events.publish(event_type, payload.model_dump(mode="json"), correlation_id)
        except Exception:  # noqa: BLE001
            logger.exception("Event not published", extra={"event": "event_not_published"})
