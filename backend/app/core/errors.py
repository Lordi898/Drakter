"""Envelope de error uniforme. Nada que venga del cliente sale de aquí sin filtrar."""

import logging
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import Any, get_args
from uuid import uuid4

from drakter_contracts.errors import ErrorBody, ErrorDetail, ErrorEnvelope
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError
from fastapi.utils import is_body_allowed_for_status_code
from pydantic_core.core_schema import ErrorType
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import HTTPConnection, Request
from starlette.responses import Response
from starlette.websockets import WebSocket, WebSocketState

logger = logging.getLogger("drakter.errors")

_WS_INTERNAL_ERROR = 1011
_WS_POLICY_VIOLATION = 1008

# `msg` de estos tipos sale de plantillas de Pydantic. Se excluyen los que
# incrustan texto de un validador propio, que podría contener la entrada.
_BUILTIN_VALIDATION_TYPES = frozenset(get_args(ErrorType))
_TRUSTED_VALIDATION_TYPES = _BUILTIN_VALIDATION_TYPES - {"value_error", "assertion_error"}


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


def error_body_bytes(
    code: str,
    message: str,
    request_id: str,
    details: list[ErrorDetail] | None = None,
) -> bytes:
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id,
            details=details or [],
        )
    )
    return envelope.model_dump_json().encode("utf-8")


def _request_id(conn: HTTPConnection) -> str:
    state = conn.scope.get("state")
    request_id = state.get("request_id") if isinstance(state, Mapping) else None
    return request_id if isinstance(request_id, str) and request_id else str(uuid4())


def _json_error(
    conn: HTTPConnection,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: Mapping[str, str] | None = None,
) -> Response:
    return Response(
        content=error_body_bytes(code, message, _request_id(conn), details),
        status_code=status_code,
        headers=headers,
        media_type="application/json",
    )


async def _close_websocket(websocket: WebSocket, code: int) -> None:
    # Una Response no sirve en un websocket ya aceptado.
    if (
        websocket.application_state is not WebSocketState.DISCONNECTED
        and websocket.client_state is not WebSocketState.DISCONNECTED
    ):
        await websocket.close(code=code)


def _field_name(location: Sequence[Any]) -> str | None:
    if not location:
        return None
    # `loc` puede traer claves del cliente con sustitutos sueltos, que Pydantic
    # no acepta en un str: sin esto, un 422 acabaría en 500.
    return ".".join(str(part) for part in location).encode("utf-8", "backslashreplace").decode()


def _validation_detail(error: Mapping[str, Any]) -> ErrorDetail:
    error_type = error.get("type")
    # Un tipo ajeno a Pydantic es un PydanticCustomError nuestro. Con `ctx` su texto
    # puede interpolar lo recibido, así que solo se confía en el que no lo lleva.
    trusted = error_type in _TRUSTED_VALIDATION_TYPES or (
        error_type not in _BUILTIN_VALIDATION_TYPES and not error.get("ctx")
    )
    return ErrorDetail(
        field=_field_name(error.get("loc", ())),
        code=str(error_type) if trusted else "invalid_value",
        message=str(error.get("msg")) if trusted else "Invalid value",
    )


async def _handle_app_error(conn: HTTPConnection, exc: Exception) -> Response | None:
    assert isinstance(exc, AppError)
    if isinstance(conn, WebSocket):
        await _close_websocket(conn, _WS_INTERNAL_ERROR)
        return None
    return _json_error(
        conn,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def _handle_validation_error(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, RequestValidationError)
    return _json_error(
        request,
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details=[_validation_detail(error) for error in exc.errors()],
    )


async def _handle_websocket_validation_error(websocket: WebSocket, exc: Exception) -> None:
    # Sustituye al handler de FastAPI, que manda `errors()` en el motivo de cierre.
    await _close_websocket(websocket, _WS_POLICY_VIOLATION)


async def _handle_http_exception(conn: HTTPConnection, exc: Exception) -> Response | None:
    assert isinstance(exc, StarletteHTTPException)
    if isinstance(conn, WebSocket):
        await _close_websocket(conn, _WS_INTERNAL_ERROR)
        return None
    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=exc.headers)
    try:
        message = HTTPStatus(exc.status_code).phrase
    except ValueError:
        message = "HTTP error"
    return _json_error(
        conn,
        status_code=exc.status_code,
        code=f"http_{exc.status_code}",
        message=message,
        headers=exc.headers,
    )


async def _handle_unexpected(request: Request, exc: Exception) -> Response:
    # Starlette ejecuta esto en ServerErrorMiddleware, fuera del guardia, pero
    # comparte el mismo scope y por eso conserva el request_id.
    request_id = _request_id(request)
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        extra={"event": "internal_error", "path": request.url.path, "request_id": request_id},
    )
    return Response(
        content=error_body_bytes("internal_error", "Internal server error", request_id),
        status_code=500,
        media_type="application/json",
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(
        WebSocketRequestValidationError,
        _handle_websocket_validation_error,  # type: ignore[arg-type]
    )
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected)
