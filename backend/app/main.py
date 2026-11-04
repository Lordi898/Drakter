"""Application factory."""

from __future__ import annotations

import asyncio
import pkgutil
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from importlib import import_module
from types import ModuleType

from fastapi import APIRouter, FastAPI

from app import api
from app.core.bootstrap import Credentials
from app.core.config import Settings, ensure_private_dir
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.security import SecurityGuardMiddleware
from app.database.lock import exclusive_instance
from app.database.migrator import migrate


def _discover_routers() -> Iterator[APIRouter]:
    """Cada `app/api/<nombre>.py` exporta `router`: nadie edita este archivo para añadir rutas."""
    for module in pkgutil.iter_modules(api.__path__):
        if not module.name.startswith("_"):
            yield import_module(f"{api.__name__}.{module.name}").router


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

    runtime = hermes.AgentRuntime(settings) if hermes else None
    hub = runtime.hub if runtime else None
    app.state.agent_runtime = runtime
    app.state.agent_settings = runtime.agent_settings if runtime else None
    app.state.event_hub = hub

    app.state.memory_service = memory.build_memory_service(settings) if memory else None
    if memory:
        app.include_router(memory.router)
        if runtime:
            runtime.tool_state.memory_service = app.state.memory_service

    app.state.reminders = (
        reminders.ReminderTicker(settings.db_path, publish=hub.publish if hub else None)
        if reminders
        else None
    )


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
            runtime, reminders = app.state.agent_runtime, app.state.reminders
            if runtime:
                await runtime.start()
            try:
                if reminders:
                    await reminders.start()
                try:
                    on_ready()
                    yield
                finally:
                    if reminders:
                        await reminders.stop()
            finally:
                if runtime:
                    await runtime.stop()

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
