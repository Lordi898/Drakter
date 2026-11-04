"""Wiring of the security front. `app/main.py` needs the three calls listed in README.md."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path
from typing import Final
from uuid import uuid4

from drakter_contracts.errors import ConfirmationRequiredEnvelope, ErrorBody
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import confirmations
from app.core.config import Settings
from app.core.security import SessionToken
from app.permissions.credentials import (
    APPROVER_FILE_NAME,
    ApprovalSigner,
    write_approver_file,
)
from app.permissions.engine import PermissionEngine, load_agent_grants
from app.permissions.models import ActionRegistry
from app.services.actions import ActionService, ConfirmationRequiredError, EventSink

SWEEP_SECONDS: Final = 30.0
logger = logging.getLogger("drakter.security")


def install_security(
    app: FastAPI,
    settings: Settings,
    *,
    agent_grants_path: Path,
    events: EventSink | None = None,
) -> ActionService:
    actions = ActionService(
        db_path=settings.db_path,
        registry=ActionRegistry(),
        engine=PermissionEngine(load_agent_grants(agent_grants_path)),
        signer=ApprovalSigner(),
        events=events,
    )
    app.state.actions = actions
    app.state.approver_token = SessionToken()
    app.add_exception_handler(ConfirmationRequiredError, _confirmation_required)
    app.include_router(confirmations.router)
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


async def start_security(app: FastAPI, settings: Settings) -> None:
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
    write_approver_file(settings.runtime_dir / APPROVER_FILE_NAME, app.state.approver_token)
    app.state.confirmation_sweeper = asyncio.create_task(_sweep(actions))


async def stop_security(app: FastAPI, settings: Settings) -> None:
    sweeper = getattr(app.state, "confirmation_sweeper", None)
    if sweeper is not None:
        sweeper.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweeper
    (settings.runtime_dir / APPROVER_FILE_NAME).unlink(missing_ok=True)


async def _sweep(actions: ActionService) -> None:
    def expire() -> None:
        conn = actions.open()
        try:
            actions.expire_due(conn)
        finally:
            conn.close()

    while True:
        await asyncio.sleep(SWEEP_SECONDS)
        try:
            await asyncio.to_thread(expire)
        except Exception:  # noqa: BLE001 - approval checks expiry itself; retry on next tick
            logger.exception("Sweep failed", extra={"event": "confirmation_sweep_failed"})
