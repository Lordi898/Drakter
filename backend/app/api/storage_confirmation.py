"""Serializa `ConfirmationRequired` con `confirmation` junto a `error` (contracts §5).

Vive aquí porque `install_error_handlers` no conoce esa extensión del sobre. Cuando
`core/errors.py` la incluya, esta ruta sobra.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any
from uuid import uuid4

from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response

from app.services.storage_ports import ConfirmationRequired


class ConfirmationRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                return await handler(request)
            except ConfirmationRequired as exc:
                request_id = request.scope.get("state", {}).get("request_id") or str(uuid4())
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": {
                            "code": exc.code,
                            "message": exc.message,
                            "request_id": request_id,
                            "details": [],
                        },
                        "confirmation": exc.ticket,
                    },
                )

        return handle
