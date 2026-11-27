"""Application factory."""

from __future__ import annotations

import asyncio
import os
import pkgutil
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import APIRouter, FastAPI

from app import api
from app.core.bootstrap import Credentials
from app.core.config import Settings, ensure_private_dir
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.security import SecurityGuardMiddleware
from app.database.lock import exclusive_instance
from app.database.migrator import migrate
from app.events import EventHub
from app.permissions.setup import start_security, stop_security
from app.permissions.wiring import wire_security
from app.services.improvement_proposals import recover_interrupted


def _discover_routers() -> Iterator[APIRouter]:
    """Cada `app/api/<nombre>.py` con `router` se monta: nadie edita este archivo para añadir rutas.

    Un módulo sin `router` es un auxiliar de otros routers y no se monta.
    """
    for module in pkgutil.iter_modules(api.__path__):
        router = getattr(import_module(f"{api.__name__}.{module.name}"), "router", None)
        if router is not None:
            yield router


def _optional_module(name: str) -> ModuleType | None:
    """Módulos de otros frentes. Solo se tolera su ausencia, nunca un fallo al importarlos."""
    try:
        return import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name and f"{name}.".startswith(f"{exc.name}."):
            return None
        raise


def _install_services(app: FastAPI, settings: Settings) -> None:
    hermes = _optional_module("app.integrations.hermes.runtime")
    memory = _optional_module("app.integrations.memory.router")
    reminders = _optional_module("app.services.reminders")
    # Readable titles in the confirmation summaries of delete_relationship and delete_task.
    for tools_module in ("app.tools.relations", "app.tools.tasks"):
        module = _optional_module(tools_module)
        if module:
            module.configure_summary_source(settings.db_path)

    runtime = hermes.AgentRuntime(settings) if hermes else None
    hub = runtime.hub if runtime else EventHub()
    app.state.agent_runtime = runtime
    app.state.agent_settings = runtime.agent_settings if runtime else None
    app.state.event_hub = hub

    app.state.memory_service = memory.build_memory_service(settings) if memory else None
    if memory:
        app.include_router(memory.router)
        if runtime:
            runtime.tool_state.memory_service = app.state.memory_service

    app.state.reminders = (
        reminders.ReminderTicker(settings.db_path, publish=hub.publish) if reminders else None
    )
    wire_security(app, settings)
    _install_voice(app, settings, runtime)
    if runtime:
        # Read-only views for the agent's system tools (system_views.py): same objects as the GUI.
        runtime.tool_state.actions = app.state.actions
        runtime.tool_state.voice = app.state.voice
        _install_awareness(app, settings, runtime)


def runtime_dir() -> Path:
    """Same rule as voice/config.py: the voice socket is `<this>/voice.sock`."""
    raw = os.environ.get("XDG_RUNTIME_DIR")
    return (Path(raw) if raw else Path(f"/run/user/{os.getuid()}")) / "drakter"


def _install_voice(app: FastAPI, settings: Settings, runtime: Any) -> None:
    """Voice v2 (WP5): the orchestrator is the runtime's TurnTap. It starts in the lifespan."""
    app.state.voice = None
    if runtime is None:
        return
    from app.integrations.voice.audit import VoiceAudit
    from app.integrations.voice.router import router as voice_router
    from app.integrations.voice.service import VoiceOrchestrator
    from app.integrations.voice.settings import load_voice_settings

    app.include_router(voice_router)
    orchestrator = VoiceOrchestrator(
        load_voice_settings(),
        runtime=runtime,
        audit=VoiceAudit(settings.db_path),
        data_dir=settings.data_dir,
        runtime_dir=runtime_dir(),
        db_path=settings.db_path,
    )
    runtime.add_turn_prefix(orchestrator.heard.prefix)
    # Hermes retrying an unreachable model on a voice turn: the cached `offline` phrase, once.
    runtime.on_model_unreachable = lambda _source: orchestrator.say_phrase("offline")
    app.state.voice = orchestrator


def _install_awareness(app: FastAPI, settings: Settings, runtime: Any) -> None:
    """Self- and context awareness: the machine it runs on (re-read, never configured) and where
    the conversation is, as a turn prefix; `get_self_profile` reads the same objects."""
    from app.services.awareness import AwarenessService
    from app.services.hardware import HardwareTracker

    tracker = HardwareTracker(settings.data_dir)
    tracker.refresh_if_stale()  # first probe in a thread: the app does not wait for lspci
    awareness = AwarenessService(settings.db_path, tracker)
    runtime.add_turn_prefix(awareness.prefix)
    runtime.tool_state.awareness = awareness
    app.state.awareness = awareness


async def _start_jobs(app: FastAPI) -> Any:
    """Drakter Jobs (WP7). `install_jobs` registers its own turn prefix. A finished job is
    announced with a phrase once voice is silent (never as an assistant message)."""
    from app.jobs.manager import install_jobs

    manager = await install_jobs(app)
    voice = app.state.voice
    if voice is not None:
        manager.on_job_finished = lambda job: voice.say_phrase(
            "job_done" if job.state == "completed" else "job_failed", "when_silent"
        )
    return manager


def create_app(
    settings: Settings,
    *,
    credentials: Credentials,
    port: int,
    on_ready: Callable[[], None],
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        for directory in (settings.data_dir, settings.logs_dir, settings.backups_dir):
            ensure_private_dir(directory)
        configure_logging(settings.log_level, settings.logs_dir)
        with exclusive_instance(settings.db_path):
            await asyncio.to_thread(migrate, settings.db_path, settings.backups_dir)
            # Evaluations cut short by a stop go back to draft before anything can resume them.
            await asyncio.to_thread(recover_interrupted, settings)
            await start_security(app)
            runtime, reminders = app.state.agent_runtime, app.state.reminders
            voice = app.state.voice
            jobs = None
            if runtime:
                await runtime.start()
            try:
                if runtime:
                    jobs = await _start_jobs(app)
                if voice:
                    ensure_private_dir(runtime_dir())
                    await voice.start()  # sets the runtime's TurnTap
                if reminders:
                    await reminders.start()
                try:
                    on_ready()
                    yield
                finally:
                    if reminders:
                        await reminders.stop()
            finally:
                if voice:
                    await voice.stop()
                if jobs:
                    await jobs.stop()
                if runtime:
                    await runtime.stop()
                await stop_security(app)

    app = FastAPI(
        title="Drakter",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
        lifespan=lifespan,
    )
    app.state.settings = settings

    install_error_handlers(app)
    for router in _discover_routers():
        app.include_router(router)
    _install_services(app, settings)

    app.add_middleware(SecurityGuardMiddleware, credentials=credentials, port=port)
    return app
