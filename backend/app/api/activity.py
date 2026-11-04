"""Activity log, read-only: `AuditEventOut` with cursor. Its content is untrusted data."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from drakter_contracts.models.activity import AuditResult
from fastapi import APIRouter, Query, Request

from app.audit.writer import MAX_LISTED_EVENTS, list_activity
from app.core.errors import AppError
from app.database.connection import connect

router = APIRouter(prefix="/api/v1")


@router.get("/activity")
def get_activity(
    request: Request,
    actor: Annotated[str | None, Query(pattern="^(user|agent|automation|system)$")] = None,
    entity_id: UUID | None = None,
    result: AuditResult | None = None,
    from_: Annotated[str | None, Query(alias="from", max_length=24)] = None,
    to: Annotated[str | None, Query(max_length=24)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LISTED_EVENTS)] = 50,
    cursor: Annotated[str | None, Query(max_length=128)] = None,
) -> dict[str, Any]:
    conn = connect(request.app.state.settings.db_path)
    try:
        return list_activity(
            conn,
            actor=actor,
            entity_id=str(entity_id) if entity_id else None,
            result=result.value if result else None,
            occurred_from=from_,
            occurred_to=to,
            limit=limit,
            cursor=cursor,
        )
    except ValueError:
        raise AppError("invalid_query", "Invalid cursor", 400) from None
    finally:
        conn.close()
