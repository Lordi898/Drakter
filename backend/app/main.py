"""Application factory."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health, ws
from app.core.config import Settings, ensure_private_dir
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.security import (
    SecurityGuardMiddleware,
    SessionToken,
    remove_session_file,
    write_session_file,
)
from app.database.migrator import migrate


def create_app(settings: Settings) -> FastAPI:
    token = SessionToken()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        for directory in (
            settings.data_dir,
            settings.runtime_dir,
            settings.logs_dir,
            settings.backups_dir,
        ):
            ensure_private_dir(directory)
        configure_logging(settings.log_level, settings.logs_dir)
        await asyncio.to_thread(migrate, settings.db_path, settings.backups_dir)
        write_session_file(settings.session_file, token, settings.port)
        try:
            yield
        finally:
            remove_session_file(settings.session_file)

    app = FastAPI(
        title="Drakter",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.token = token

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(ws.router)

    # The last middleware added is the outermost: guard wraps CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(
        SecurityGuardMiddleware,
        token=token,
        port=settings.port,
        allowed_origins=settings.allowed_origins,
    )
    return app
