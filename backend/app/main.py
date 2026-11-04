"""Application factory."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, events, health
from app.core.bootstrap import Credentials
from app.core.config import Settings, ensure_private_dir
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.security import SecurityGuardMiddleware
from app.database.lock import exclusive_instance
from app.database.migrator import migrate


def create_app(
    settings: Settings,
    *,
    credentials: Credentials,
    port: int,
    on_ready: Callable[[], None],
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        for directory in (
            settings.data_dir,
            settings.logs_dir,
            settings.backups_dir,
        ):
            ensure_private_dir(directory)
        configure_logging(settings.log_level, settings.logs_dir)
        with exclusive_instance(settings.db_path):
            await asyncio.to_thread(migrate, settings.db_path, settings.backups_dir)
            on_ready()
            yield

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
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(events.router)

    app.add_middleware(SecurityGuardMiddleware, credentials=credentials, port=port)
    return app
