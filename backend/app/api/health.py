"""Liveness endpoint for Electron main."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.errors import AppError
from app.database.connection import connect

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    try:
        conn = connect(request.app.state.settings.db_path)
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
    except Exception:
        raise AppError("service_unavailable", "Service unavailable", 503) from None
    return {"status": "ok"}
