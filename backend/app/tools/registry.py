"""Tool catalog and the single execution path for agent calls."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
import pkgutil
import re
import time
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any, Final, get_args

import drakter_contracts
from drakter_contracts.errors import ErrorCode
from drakter_contracts.tools import ImageAttachment, ToolManifest, ToolOk, ToolOutcome
from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_core.core_schema import ErrorType

from app.tools.envelope import outcome_code, tool_confirmation, tool_failure
from app.tools.gate import (
    AuditSink,
    DefaultToolGate,
    GateDecision,
    LogAuditSink,
    ToolAuditEvent,
    ToolGate,
    audit_args,
    effective_risk,
)
from app.tools.permissions import PermissionPolicy
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec
from app.tools.turns import TurnTracker

TOOL_NAME_RE: Final = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
_DOMAIN_RE: Final = re.compile(r"^[a-z][a-z0-9_]*$")
_PERMISSION_RE: Final = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_MIN_TIMEOUT_S: Final = 1.0
_MAX_TIMEOUT_S: Final = 120.0
_MAX_ERROR_DETAILS: Final = 20

_KNOWN_ERROR_TYPES: Final = frozenset(get_args(ErrorType))
# Their text comes from a validator or quotes part of the input, so it is not safe to echo.
_OPAQUE_ERROR_TYPES: Final = frozenset({"value_error", "assertion_error"})

logger = logging.getLogger("drakter.tools")

ToolObserver = Callable[[str, ToolContext, ToolOutcome], "None | Awaitable[None]"]


class ToolRegistrationError(ValueError):
    """A tool declaration is incomplete or duplicated."""


class ToolLoadError(RuntimeError):
    """A tool module could not be loaded. The backend must not start without its tools."""


def _schema_nodes(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _schema_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _schema_nodes(value)


def _spec_problem(spec: ToolSpec) -> str | None:
    if not isinstance(spec.name, str) or TOOL_NAME_RE.fullmatch(spec.name) is None:
        return "name must match ^[a-z][a-z0-9_]{2,47}$"
    if not isinstance(spec.description, str) or not spec.description.strip():
        return "description is required"
    if not isinstance(spec.domain, str) or _DOMAIN_RE.fullmatch(spec.domain) is None:
        return "domain is required"
    for label, model in (("args_model", spec.args_model), ("result_model", spec.result_model)):
        if not (inspect.isclass(model) and issubclass(model, BaseModel)):
            return f"{label} must be a pydantic model"
    if spec.args_model.model_config.get("extra") != "forbid":
        return 'args_model must set extra="forbid"'
    for node in _schema_nodes(spec.args_model.model_json_schema()):
        if "properties" in node and node.get("additionalProperties") is not False:
            return 'nested models in args_model must set extra="forbid"'
    if not isinstance(spec.permission, str) or _PERMISSION_RE.fullmatch(spec.permission) is None:
        return 'permission must look like "<domain>.<action>"'
    if spec.permission.split(".", 1)[0] != spec.domain:
        return "permission must belong to the tool's domain"
    if not isinstance(spec.risk, RiskClass):
        return "risk must be a RiskClass"
    if not callable(spec.handler):
        return "handler must be callable"
    if not isinstance(spec.errors, tuple):
        return "errors must be a tuple"
    if not _MIN_TIMEOUT_S <= spec.timeout_s <= _MAX_TIMEOUT_S:
        return "timeout_s must be between 1 and 120"
    for key, policy in spec.audit.items():
        if key not in spec.args_model.model_fields:
            return f"audit names an unknown argument: {key}"
        if policy not in ("log", "hash", "omit"):
            return f"audit policy for {key} must be log, hash or omit"
    if spec.risk is RiskClass.CONFIRM and spec.summarize is None:
        return "a CONFIRM tool needs summarize"
    if spec.confirm_if is not None:
        if spec.risk is not RiskClass.WRITE:
            return "confirm_if only applies to a WRITE tool"
        if not callable(spec.confirm_if):
            return "confirm_if must be callable"
    attachments = spec.result_model.model_fields.get("attachments")
    if attachments is not None and attachments.exclude is not True:
        return "result_model.attachments must be excluded from the dump (exclude=True)"
    return None


_ATTACHMENTS: Final = TypeAdapter(list[ImageAttachment])
_MAX_ATTACHMENTS: Final = 1


def _attachments(spec: ToolSpec, result: Any) -> list[ImageAttachment]:
    """Images of the result: only from an excluded ``attachments`` field of ``result_model``."""
    if "attachments" not in spec.result_model.model_fields:
        return []
    raw = getattr(result, "attachments", None)
    if raw is None and isinstance(result, dict):
        raw = result.get("attachments")
    if not raw:
        return []
    items = [a.model_dump() if isinstance(a, BaseModel) else a for a in raw]
    attachments = _ATTACHMENTS.validate_python(items)
    if len(attachments) > _MAX_ATTACHMENTS:
        raise ValueError("too many attachments")
    return attachments


def _validation_details(exc: ValidationError) -> list[dict[str, Any]]:
    """Field, code and a safe message. Never ``input`` or ``ctx``."""
    details: list[dict[str, Any]] = []
    errors = exc.errors(include_url=False, include_context=False, include_input=False)
    for error in errors[:_MAX_ERROR_DETAILS]:
        kind = str(error["type"])
        safe = (
            kind in _KNOWN_ERROR_TYPES
            and kind not in _OPAQUE_ERROR_TYPES
            and "parsing" not in kind
        )
        loc = error["loc"]
        if kind == "extra_forbidden":
            # The key itself is model-chosen input: name its parent, never the key.
            loc = (*loc[:-1], "<extra>")
        field = ".".join(str(part) for part in loc)
        details.append(
            {
                # An extra key is text chosen by the model.
                "field": re.sub(r"[^\w.\-]", "?", field)[:100],
                "code": kind,
                "message": str(error["msg"]) if safe else "Invalid value.",
            }
        )
    return details


def _confirmation_outcome(decision: GateDecision) -> ToolOutcome | None:
    """None if the decision is incomplete or does not fit the contract."""
    if decision.action_id is None or not decision.summary or decision.expires_at is None:
        return None
    try:
        return tool_confirmation(decision.action_id, decision.summary, decision.expires_at)
    except ValidationError:
        return None


async def _invoke(spec: ToolSpec, ctx: ToolContext, args: BaseModel) -> Any:
    if inspect.iscoroutinefunction(spec.handler):
        return await spec.handler(ctx, args)
    result = await asyncio.to_thread(spec.handler, ctx, args)
    return await result if inspect.isawaitable(result) else result


def _discard_late_result(task: asyncio.Task[Any]) -> None:
    if not task.cancelled():
        task.exception()


async def _run_with_timeout(spec: ToolSpec, ctx: ToolContext, args: BaseModel) -> Any:
    """Run the handler. On timeout, return at once even if the handler ignores cancellation."""
    task = asyncio.ensure_future(_invoke(spec, ctx, args))
    try:
        done, _ = await asyncio.wait({task}, timeout=spec.timeout_s)
    except asyncio.CancelledError:
        task.cancel()
        raise
    if done:
        return task.result()
    task.cancel()
    task.add_done_callback(_discard_late_result)
    # A worker thread cannot be stopped and the handler may have finished its work.
    raise ToolError(
        ErrorCode.TOOL_TIMEOUT,
        "The tool timed out and its outcome is unknown. Check the state before repeating it.",
        retryable=False,
    )


class ToolRegistry:
    """Everything an agent call needs goes through ``dispatch``, in the contract's order."""

    def __init__(
        self,
        turns: TurnTracker | None = None,
        *,
        gate: ToolGate | None = None,
        audit: AuditSink | None = None,
        permissions: PermissionPolicy | None = None,
    ) -> None:
        self.turns = turns if turns is not None else TurnTracker()
        self.gate: ToolGate = gate if gate is not None else DefaultToolGate()
        self.audit: AuditSink = audit if audit is not None else LogAuditSink()
        self.permissions = permissions if permissions is not None else PermissionPolicy.load()
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if not isinstance(spec, ToolSpec):
            raise ToolRegistrationError(f"not a ToolSpec: {spec!r}")
        problem = _spec_problem(spec)
        if problem is not None:
            raise ToolRegistrationError(f"tool {spec.name!r}: {problem}")
        if spec.name in self._tools:
            raise ToolRegistrationError(f"tool {spec.name!r}: duplicated name")
        self._tools[spec.name] = spec

    def catalog(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools.values())

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    async def dispatch(
        self,
        name: str,
        raw_args: dict[str, Any],
        ctx: ToolContext,
        *,
        observer: ToolObserver | None = None,
    ) -> ToolOutcome:
        """Never raises. Cancellation of the caller is the only thing that propagates.

        ``observer`` receives the tool name, the context and the final outcome, for instance
        to publish ``confirmation.requested``. It cannot change the outcome.
        """
        try:
            outcome = await self._dispatch(name, raw_args, ctx)
        except Exception:
            logger.exception("tool dispatch failed", extra={"event": "tool_dispatch_failed"})
            outcome = tool_failure(ErrorCode.INTERNAL_ERROR, "The tool failed unexpectedly.")
        if observer is not None:
            try:
                result = observer(name, ctx, outcome)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("tool observer failed", extra={"event": "tool_observer_failed"})
        return outcome

    async def _dispatch(
        self, name: str, raw_args: dict[str, Any], ctx: ToolContext
    ) -> ToolOutcome:
        spec = self._tools.get(name)
        if spec is None:
            # The name comes from the model: it only reaches the audit trail if well formed.
            shown = name if TOOL_NAME_RE.fullmatch(str(name)) else "<invalid>"
            return await self._reject(
                tool_failure(ErrorCode.NOT_FOUND, "That tool does not exist."), shown, ctx
            )

        if not self.turns.is_active(ctx.session_id, ctx.turn_id):
            return await self._reject(
                tool_failure(ErrorCode.NO_ACTIVE_TURN, "There is no active turn."),
                spec.name,
                ctx,
                spec,
            )
        if not ctx.call_id:
            return await self._reject(
                tool_failure(ErrorCode.VALIDATION_ERROR, "The call has no identifier."),
                spec.name,
                ctx,
                spec,
            )

        try:
            args = spec.args_model.model_validate(raw_args)
        except ValidationError as exc:
            outcome = tool_failure(
                ErrorCode.VALIDATION_ERROR, "Invalid arguments.", details=_validation_details(exc)
            )
            return await self._reject(outcome, spec.name, ctx, spec)
        except Exception:  # a validator that raises something pydantic does not wrap
            logger.exception("tool validator failed", extra={"event": "tool_validator_failed"})
            outcome = tool_failure(ErrorCode.VALIDATION_ERROR, "Invalid arguments.")
            return await self._reject(outcome, spec.name, ctx, spec)

        tainted = self.turns.is_tainted(ctx.session_id)
        event_args = audit_args(spec, args)

        risk = effective_risk(spec, tainted=tainted, args=args)

        def reject(outcome: ToolOutcome) -> Any:
            return self._reject(outcome, spec.name, ctx, spec, tainted, event_args, risk)

        if not self.permissions.allows(spec.permission):
            return await reject(tool_failure(ErrorCode.PERMISSION_DENIED, "Permission denied."))

        unauthorized = tool_failure(
            ErrorCode.SERVICE_UNAVAILABLE, "The action could not be authorized."
        )
        try:
            decision = await self.gate.authorize(spec, args, ctx, tainted=tainted)
        except Exception:
            logger.exception("tool gate failed", extra={"event": "tool_gate_failed"})
            return await reject(unauthorized)

        kind = getattr(decision, "kind", None)
        if kind == "deny":
            return await reject(
                tool_failure(
                    decision.code or ErrorCode.PERMISSION_DENIED,
                    decision.message or "The action was denied.",
                )
            )
        if kind == "confirm":
            confirmation = _confirmation_outcome(decision)
            if confirmation is not None:
                return await reject(confirmation)
        # What needs confirmation is executed on the user's approval, never by an agent call.
        elif kind == "allow" and risk is not RiskClass.CONFIRM:
            return await self._execute(spec, args, ctx, tainted, event_args, risk)
        logger.error("invalid gate decision", extra={"event": "tool_gate_invalid"})
        return await reject(unauthorized)

    async def _execute(
        self,
        spec: ToolSpec,
        args: BaseModel,
        ctx: ToolContext,
        tainted: bool,
        event_args: dict[str, Any],
        risk: RiskClass,
    ) -> ToolOutcome:
        try:
            await self.audit.record(
                self._event(
                    "attempt", spec.name, ctx, spec, tainted, event_args, "pending", risk=risk
                )
            )
        except Exception:
            logger.exception("audit failed", extra={"event": "tool_audit_failed"})
            return tool_failure(ErrorCode.SERVICE_UNAVAILABLE, "The action could not be audited.")

        started = time.monotonic()
        outcome = await self._run_handler(spec, args, ctx)
        duration_ms = round((time.monotonic() - started) * 1000, 1)
        if outcome.status == "ok" and spec.returns_untrusted:
            self.turns.mark_tainted(ctx.session_id)

        event = self._event(
            "result",
            spec.name,
            ctx,
            spec,
            tainted,
            event_args,
            outcome.status,
            outcome_code(outcome),
            duration_ms,
            risk=risk,
            attachments=tuple(
                {"sha256": a.sha256, "width": a.width, "height": a.height}
                for a in (outcome.attachments if isinstance(outcome, ToolOk) else ())
            ),
        )
        try:
            await self.audit.record(event)
        except Exception:
            logger.exception("audit failed", extra={"event": "tool_audit_failed"})
            return tool_failure(
                ErrorCode.SERVICE_UNAVAILABLE, "The action ran but could not be audited."
            )
        return outcome

    async def _run_handler(
        self, spec: ToolSpec, args: BaseModel, ctx: ToolContext
    ) -> ToolOutcome:
        try:
            with self.turns.tool_call():
                result = await _run_with_timeout(spec, ctx, args)
        except ToolError as exc:
            return tool_failure(
                exc.code, exc.message, retryable=exc.retryable, details=exc.details
            )
        except Exception:
            logger.exception(
                "tool handler failed", extra={"event": "tool_failed", "tool": spec.name}
            )
            return tool_failure(ErrorCode.INTERNAL_ERROR, "The tool failed unexpectedly.")

        try:
            # Dumping first forces validation of instances built without it.
            dumped = result.model_dump() if isinstance(result, BaseModel) else result
            data = spec.result_model.model_validate(dumped).model_dump(mode="json")
            attachments = _attachments(spec, result)
        except Exception:  # noqa: BLE001 - includes serializers; the detail stays in the log
            logger.exception(
                "tool returned an invalid result",
                extra={"event": "tool_invalid_result", "tool": spec.name},
            )
            return tool_failure(ErrorCode.INTERNAL_ERROR, "The tool returned an invalid result.")
        return ToolOk(data=data, attachments=attachments)

    async def _reject(
        self,
        outcome: ToolOutcome,
        tool: str,
        ctx: ToolContext,
        spec: ToolSpec | None = None,
        tainted: bool | None = None,
        event_args: dict[str, Any] | None = None,
        risk: RiskClass | None = None,
    ) -> ToolOutcome:
        if tainted is None:
            tainted = self.turns.is_tainted(ctx.session_id)
        event = self._event(
            "rejected",
            tool,
            ctx,
            spec,
            tainted,
            event_args or {},
            outcome.status,
            outcome_code(outcome),
            risk=risk,
        )
        try:
            await self.audit.record(event)
        except Exception:
            logger.exception("audit failed", extra={"event": "tool_audit_failed"})
        return outcome

    @staticmethod
    def _event(
        phase: Any,
        tool: str,
        ctx: ToolContext,
        spec: ToolSpec | None,
        tainted: bool,
        event_args: dict[str, Any],
        outcome: Any,
        code: str | None = None,
        duration_ms: float | None = None,
        *,
        risk: RiskClass | None = None,
        attachments: tuple[dict[str, Any], ...] = (),
    ) -> ToolAuditEvent:
        if spec is not None and risk is None:
            risk = effective_risk(spec, tainted=tainted)
        return ToolAuditEvent(
            phase=phase,
            tool=tool,
            turn_id=ctx.turn_id,
            session_id=ctx.session_id,
            call_id=ctx.call_id,
            principal=ctx.principal,
            tainted=tainted,
            outcome=outcome,
            code=code,
            permission=spec.permission if spec else None,
            risk=spec.risk.value if spec else None,
            effective_risk=risk.value if spec and risk else None,
            args=event_args,
            duration_ms=duration_ms,
            attachments=attachments,
        )


def _tool_modules(package: ModuleType) -> Iterator[ModuleType]:
    names = sorted(info.name for info in pkgutil.iter_modules(package.__path__))
    for name in names:
        if name == "__main__":
            continue
        qualified = f"{package.__name__}.{name}"
        try:
            yield importlib.import_module(qualified)
        except Exception as exc:
            raise ToolLoadError(f"cannot import tool module {qualified}: {exc!r}") from exc


def _warn_catalog_drift(registry: ToolRegistry) -> None:
    """Log what differs from the canonical catalog. A warning: it never stops the startup."""
    path = Path(drakter_contracts.__file__).resolve().parents[2] / "tools" / "catalog.json"
    try:
        manifests = TypeAdapter(list[ToolManifest]).validate_json(path.read_bytes())
    except (OSError, ValueError):
        logger.warning("tool catalog unavailable", extra={"event": "tool_catalog_unavailable"})
        return
    catalog = {manifest.name: manifest for manifest in manifests}
    for spec in registry.catalog():
        manifest = catalog.get(spec.name)
        differs = manifest is None or (
            manifest.domain,
            manifest.permission,
            manifest.risk,
            manifest.returns_untrusted,
        ) != (spec.domain, spec.permission, spec.risk, spec.returns_untrusted)
        if differs:
            logger.warning(
                "tool differs from the catalog",
                extra={"event": "tool_catalog_drift", "tool": spec.name},
            )


def load_builtin_tools(registry: ToolRegistry) -> None:
    """Register ``TOOLS`` from every ``app.tools`` module. Any failure stops the startup."""
    import app.tools as package

    for module in _tool_modules(package):
        tools = getattr(module, "TOOLS", None)
        if tools is None:
            continue
        if not isinstance(tools, tuple):
            raise ToolLoadError(f"{module.__name__}.TOOLS must be a tuple of ToolSpec")
        for spec in tools:
            registry.register(spec)
    _warn_catalog_drift(registry)
