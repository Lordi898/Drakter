"""Tokens de arranque y guardia ASGI del puerto de la GUI (D-14)."""

from __future__ import annotations

import hmac
import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final, NamedTuple
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import BIND_HOST
from app.core.errors import error_body_bytes
from app.core.logging import register_secret

if TYPE_CHECKING:
    from app.core.bootstrap import Credentials

WS_SUBPROTOCOL: Final = "drakter.v1"
MAX_BODY_BYTES: Final = 1_048_576

logger = logging.getLogger("drakter.security")

_WS_POLICY_VIOLATION: Final = 1008
_MAX_LOGGED_PATH: Final = 256
_APPROVAL_PATH: Final = re.compile(r"/api/v1/confirmations(?:/[^/]+)?/(?:approve|reject)/?")
_REPEATED_SLASHES: Final = re.compile(r"/{2,}")
_APPROVER_WRITE_PATHS: Final = ("/api/v1/storage-locations", "/api/v1/permissions")
_SAFE_METHODS: Final = frozenset({"GET", "HEAD"})


class SessionToken:
    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value.encode("ascii")
        register_secret(value)

    def matches(self, candidate: bytes) -> bool:
        if not isinstance(candidate, bytes):
            return False
        return hmac.compare_digest(self._value, candidate)

    def reveal(self) -> str:
        """Only to hand the token to a child process we start (the Hermes MCP client)."""
        return self._value.decode("ascii")

    def __repr__(self) -> str:
        return "SessionToken(<redacted>)"

    __str__ = __repr__


class Role(StrEnum):
    UI = "ui"
    APPROVER = "approver"


def required_role(method: str | None, path: str) -> Role:
    # Las variantes de una ruta protegida también exigen `approver`, aunque no enruten.
    normalized = _REPEATED_SLASHES.sub("/", path)
    if _APPROVAL_PATH.fullmatch(normalized):
        return Role.APPROVER
    if method not in _SAFE_METHODS and method is not None:
        for protected in _APPROVER_WRITE_PATHS:
            if normalized == protected or normalized.startswith(f"{protected}/"):
                return Role.APPROVER
    return Role.UI


class _Rejection(NamedTuple):
    status: int
    code: str
    message: str


_FORBIDDEN_CLIENT: Final = _Rejection(403, "forbidden_client", "Client not allowed")
_FORBIDDEN_HOST: Final = _Rejection(403, "forbidden_host", "Host not allowed")
_FORBIDDEN_ORIGIN: Final = _Rejection(403, "forbidden_origin", "Origin not allowed")
_UNAUTHORIZED: Final = _Rejection(401, "unauthorized", "Authentication required")
_PERMISSION_DENIED: Final = _Rejection(403, "permission_denied", "Permission denied")
_BODY_TOO_LARGE: Final = _Rejection(413, "file_too_large", "Request body too large")


def _headers_by_name(scope: Scope) -> dict[bytes, list[bytes]]:
    # Uvicorn entrega los nombres sin normalizar en websocket (`raw_items`).
    headers: dict[bytes, list[bytes]] = {}
    for name, value in scope.get("headers", ()):
        headers.setdefault(bytes(name).lower(), []).append(bytes(value))
    return headers


def _declares_oversized_body(headers: dict[bytes, list[bytes]]) -> bool:
    return any(
        value.isdigit() and int(value) > MAX_BODY_BYTES
        for value in headers.get(b"content-length", ())
    )


@dataclass(slots=True)
class _BodyLimit:
    seen: int = 0
    response_started: bool = False
    blocked: bool = False


class SecurityGuardMiddleware:
    def __init__(self, app: ASGIApp, *, credentials: Credentials, port: int) -> None:
        self.app = app
        self._credentials = credentials
        self._host = f"{BIND_HOST}:{port}".encode("ascii")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        scope.setdefault("state", {})["request_id"] = str(uuid4())
        headers = _headers_by_name(scope)
        rejection = self._evaluate(scope, headers)
        if rejection is not None:
            await self._reject(scope, receive, send, rejection)
        elif scope["type"] == "http":
            await self._forward_with_body_limit(scope, receive, send)
        else:
            await self.app(scope, receive, send)

    def _evaluate(self, scope: Scope, headers: dict[bytes, list[bytes]]) -> _Rejection | None:
        client = scope.get("client")
        if not client or client[0] != BIND_HOST:
            return _FORBIDDEN_CLIENT
        if headers.get(b"host") != [self._host]:
            return _FORBIDDEN_HOST
        if b"origin" in headers:
            return _FORBIDDEN_ORIGIN

        caller = self._identify(headers)
        if caller is None:
            return _UNAUTHORIZED
        if caller is not required_role(scope.get("method"), scope["path"]):
            return _PERMISSION_DENIED
        if scope["type"] == "http" and _declares_oversized_body(headers):
            return _BODY_TOO_LARGE
        return None

    def _identify(self, headers: dict[bytes, list[bytes]]) -> Role | None:
        authorization = headers.get(b"authorization", [])
        if len(authorization) != 1:
            return None
        scheme, _, credential = authorization[0].partition(b" ")
        if scheme.lower() != b"bearer":
            return None
        # Ambas comparaciones siempre: el tiempo no debe revelar cuál estuvo cerca.
        is_ui = self._credentials.ui.matches(credential)
        is_approver = self._credentials.approver.matches(credential)
        if is_ui:
            return Role.UI
        return Role.APPROVER if is_approver else None

    async def _forward_with_body_limit(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit = _BodyLimit()

        async def limited_receive() -> Message:
            message = await receive()
            if message["type"] != "http.request":
                return message
            limit.seen += len(message.get("body", b""))
            if limit.seen <= MAX_BODY_BYTES:
                return message
            if not limit.response_started and not limit.blocked:
                await self._send_rejection(scope, send, _BODY_TOO_LARGE)
            limit.blocked = True
            return {"type": "http.disconnect"}

        async def guarded_send(message: Message) -> None:
            if limit.blocked:
                return
            if message["type"] == "http.response.start":
                limit.response_started = True
            await send(message)

        await self.app(scope, limited_receive, guarded_send)

    async def _reject(
        self, scope: Scope, receive: Receive, send: Send, rejection: _Rejection
    ) -> None:
        if scope["type"] == "websocket":
            self._log_rejection(scope, rejection)
            message = await receive()
            if message["type"] == "websocket.connect":
                await send({"type": "websocket.close", "code": _WS_POLICY_VIOLATION})
            return
        await self._send_rejection(scope, send, rejection)

    async def _send_rejection(self, scope: Scope, send: Send, rejection: _Rejection) -> None:
        self._log_rejection(scope, rejection)
        body = error_body_bytes(rejection.code, rejection.message, scope["state"]["request_id"])
        response_headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]
        if rejection is _UNAUTHORIZED:
            response_headers.append((b"www-authenticate", b"Bearer"))
        if rejection is _BODY_TOO_LARGE:
            # El resto del cuerpo queda sin leer: la conexión no se puede reutilizar.
            response_headers.append((b"connection", b"close"))
        await send(
            {"type": "http.response.start", "status": rejection.status, "headers": response_headers}
        )
        await send({"type": "http.response.body", "body": body})

    def _log_rejection(self, scope: Scope, rejection: _Rejection) -> None:
        logger.warning(
            "Request rejected",
            extra={
                "event": rejection.code,
                "method": "WEBSOCKET" if scope["type"] == "websocket" else scope.get("method"),
                "path": str(scope.get("path"))[:_MAX_LOGGED_PATH],
                "status": rejection.status,
                "request_id": scope["state"]["request_id"],
            },
        )
