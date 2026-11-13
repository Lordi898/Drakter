"""Wiring of the security front. `app/main.py` needs the three calls listed in README.md."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Mapping
from functools import partial
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, Final
from uuid import uuid4

from drakter_contracts.errors import ConfirmationRequiredEnvelope, ErrorBody
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.permissions.engine import PermissionEngine, load_agent_grants
from app.permissions.models import ActionRegistry
from app.permissions.models import ACTOR_TYPES, ActorContext
from app.services.actions import ActionService, ConfirmationRequiredError, ConfirmedExecutor

TICK_SECONDS: Final = 1.0
EXPIRE_EVERY_TICKS: Final = 30
# `confirmed_action` registers on import: these define the actions of hábitos y calendario.
_HABITS_CALENDAR_MODULES: Final = (
    "app.services.calendar",
    "app.services.subjects",
    "app.services.habits",
)
logger = logging.getLogger("drakter.security")


def _optional(name: str) -> ModuleType | None:
    """Modules of other fronts. Only their absence is tolerated, never a failed import."""
    try:
        return import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name and f"{name}.".startswith(f"{exc.name}."):
            return None
        raise


def _run_storage(
    module: ModuleType,
    settings: Settings,
    tool: str,
    conn: Any,
    ctx: ActorContext,
    args: Mapping[str, Any],
) -> Any:
    from app.services.storage_ports import Actor  # noqa: PLC0415 - optional front

    actor = Actor(
        kind=ACTOR_TYPES[ctx.principal].value,
        origin=ctx.origin.value,
        correlation_id=ctx.correlation_id,
    )
    return module.execute_confirmed(conn, settings, actor, tool, args)


def _run_habits_calendar(
    module: ModuleType, tool: str, conn: Any, ctx: ActorContext, args: Mapping[str, Any]
) -> Any:
    context = module.RequestContext(
        actor_type=ACTOR_TYPES[ctx.principal].value,
        origin=ctx.origin.value,
        correlation_id=ctx.correlation_id,
        tool_name=tool,
    )
    return module.CONFIRMED_ACTIONS[tool](conn, context, dict(args))


def load_confirmed_executors(settings: Settings) -> dict[str, ConfirmedExecutor]:
    """Who runs each approved tool. Two owners for one tool stop the boot."""
    executors: dict[str, ConfirmedExecutor] = {}

    def add(tool: str, executor: ConfirmedExecutor) -> None:
        if tool in executors:
            raise ValueError(f"Two executors for {tool}")
        executors[tool] = executor

    storage = _optional("app.services.storage_confirmed")
    if storage is not None:
        for tool in storage.CONFIRMED_ACTIONS:
            add(tool, partial(_run_storage, storage, settings, tool))
    support = _optional("app.services.habits_calendar_support")
    if support is not None:
        for name in _HABITS_CALENDAR_MODULES:
            _optional(name)
        for tool in support.CONFIRMED_ACTIONS:
            add(tool, partial(_run_habits_calendar, support, tool))
    return executors


def install_security(
    app: FastAPI, settings: Settings, *, agent_grants_path: Path
) -> ActionService:
    """After `app.state.event_hub` exists."""
    actions = ActionService(
        db_path=settings.db_path,
        registry=ActionRegistry(),
        engine=PermissionEngine(load_agent_grants(agent_grants_path)),
        events=getattr(app.state, "event_hub", None),
        executors=load_confirmed_executors(settings),
    )
    app.state.actions = actions
    app.add_exception_handler(ConfirmationRequiredError, _confirmation_required)
    return actions


async def _confirmation_required(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ConfirmationRequiredError)
    request_id = request.scope.get("state", {}).get("request_id") or str(uuid4())
    envelope = ConfirmationRequiredEnvelope(
        error=ErrorBody(
            code="confirmation_required",
            message="Esta operación necesita tu confirmación.",
            request_id=request_id,
        ),
        confirmation=exc.ticket,
    )
    return JSONResponse(envelope.model_dump(mode="json"), status_code=409)


async def start_security(app: FastAPI) -> None:
    """After `migrate` and once every action is registered. A failure stops the boot."""
    actions: ActionService = app.state.actions
    actions.registry.freeze()

    def reconcile() -> None:
        conn = actions.open()
        try:
            report = actions.reconcile_on_boot(conn)
        finally:
            conn.close()
        logger.info(
            "Confirmations reconciled",
            extra={"event": "confirmations_reconciled", "expired": report.expired,
                   "failed": report.failed},
        )

    await asyncio.to_thread(reconcile)
    app.state.confirmation_sweeper = asyncio.create_task(_sweep(actions))


async def stop_security(app: FastAPI) -> None:
    sweeper = getattr(app.state, "confirmation_sweeper", None)
    if sweeper is not None:
        sweeper.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweeper


async def _sweep(actions: ActionService) -> None:
    def work(tick: int) -> None:
        conn = actions.open()
        try:
            if tick % EXPIRE_EVERY_TICKS == 0:
                actions.expire_due(conn)
            actions.announce_pending(conn)
        finally:
            conn.close()

    tick = 0
    while True:
        await asyncio.sleep(TICK_SECONDS)
        tick += 1
        try:
            await asyncio.to_thread(work, tick)
        except Exception:  # noqa: BLE001 - approval checks expiry itself; retry on next tick
            logger.exception("Sweep failed", extra={"event": "confirmation_sweep_failed"})
