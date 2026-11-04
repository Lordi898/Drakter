"""Auth check: reaching this handler means the guard accepted the token."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/auth")


@router.get("/check")
def check() -> dict[str, bool]:
    return {"authenticated": True}
