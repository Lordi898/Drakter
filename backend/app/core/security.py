"""Token de sesión, archivo de sesión y guardia ASGI de la API local."""

import hmac
import json
import logging
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, NamedTuple
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import BIND_HOST
from app.core.errors import CORS_ORIGIN_STATE_KEY, cors_headers, error_body_bytes
from app.core.logging import register_secret

PUBLIC_PATHS: Final = frozenset({"/health"})
WS_SUBPROTOCOL: Final = "drakter.v1"
WS_AUTH_PREFIX: Final = "drakter.auth."

logger = logging.getLogger("drakter.security")

_WS_AUTH_PREFIX_BYTES: Final = WS_AUTH_PREFIX.encode("ascii")
_WS_POLICY_VIOLATION: Final = 1008
# O_NOFOLLOW no existe en Windows.
_O_NOFOLLOW: Final = getattr(os, "O_NOFOLLOW", 0)


class SessionToken:
    __slots__ = ("_value",)

    def __init__(self) -> None:
        self._value = secrets.token_urlsafe(32)
        register_secret(self._value)

    def matches(self, candidate: bytes) -> bool:
        if not isinstance(candidate, bytes):
            return False
        return hmac.compare_digest(self._value.encode("ascii"), candidate)

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "SessionToken(<redacted>)"

    __str__ = __repr__


def write_session_file(path: Path, token: SessionToken, port: int) -> None:
    payload = json.dumps(
        {
            "token": token.reveal(),
            "port": port,
            "pid": os.getpid(),
            "started_at": datetime.now(UTC).isoformat(),
        }
    ).encode("utf-8")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def remove_session_file(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY | _O_NOFOLLOW)
    except FileNotFoundError:
        return
    except OSError:
        # Un symlink u otra cosa que no abrimos no es nuestro archivo.
        logger.warning("Session file not removed", extra={"event": "session_file_not_removed"})
        return
    try:
        with os.fdopen(descriptor, "rb") as stream:
            owner = json.loads(stream.read()).get("pid")
    except (OSError, ValueError, AttributeError):
        logger.warning("Session file not removed", extra={"event": "session_file_not_removed"})
        return
    if owner == os.getpid():
        path.unlink(missing_ok=True)


class _Rejection(NamedTuple):
    status: int
    code: str
    message: str


_FORBIDDEN_CLIENT: Final = _Rejection(403, "forbidden_client", "Client not allowed")
_FORBIDDEN_HOST: Final = _Rejection(403, "forbidden_host", "Host not allowed")
_FORBIDDEN_ORIGIN: Final = _Rejection(403, "forbidden_origin", "Origin not allowed")
_UNAUTHORIZED: Final = _Rejection(401, "unauthorized", "Authentication required")


def _headers_by_name(scope: Scope) -> dict[bytes, list[bytes]]:
    # Uvicorn entrega los nombres sin normalizar en websocket (`raw_items`).
    headers: dict[bytes, list[bytes]] = {}
    for name, value in scope.get("headers", ()):
        headers.setdefault(bytes(name).lower(), []).append(bytes(value))
    return headers


class SecurityGuardMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        token: SessionToken,
        port: int,
        allowed_origins: tuple[str, ...],
    ) -> None:
        self.app = app
        self._token = token
        self._hosts = frozenset({f"127.0.0.1:{port}".encode(), f"localhost:{port}".encode()})
        self._origins = frozenset(origin.encode("utf-8") for origin in allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        scope.setdefault("state", {})["request_id"] = str(uuid4())
        rejection = self._evaluate(scope, _headers_by_name(scope))
        if rejection is not None:
            await self._reject(scope, receive, send, rejection)
            return

        if "subprotocols" in scope:
            # El subprotocolo con el token ya cumplió: que no llegue a los handlers.
            scope["subprotocols"] = [
                protocol
                for protocol in scope["subprotocols"]
                if not protocol.startswith(WS_AUTH_PREFIX)
            ]
        await self.app(scope, receive, send)

    def _evaluate(self, scope: Scope, headers: dict[bytes, list[bytes]]) -> _Rejection | None:
        client = scope.get("client")
        if not client or client[0] != BIND_HOST:
            return _FORBIDDEN_CLIENT

        hosts = headers.get(b"host", [])
        if len(hosts) != 1 or hosts[0].lower() not in self._hosts:
            return _FORBIDDEN_HOST

        origins = headers.get(b"origin", [])
        if origins and (len(origins) != 1 or origins[0] not in self._origins):
            return _FORBIDDEN_ORIGIN
        if origins:
            # Los errores que nacen fuera de CORS deben seguir siendo legibles para este origen.
            scope["state"][CORS_ORIGIN_STATE_KEY] = origins[0].decode("ascii")

        if scope["type"] == "http":
            if scope["path"] in PUBLIC_PATHS:
                return None
            is_preflight = (
                scope["method"] == "OPTIONS"
                and origins
                and b"access-control-request-method" in headers
            )
            if is_preflight:
                return None

        return None if self._is_authenticated(scope, headers) else _UNAUTHORIZED

    def _is_authenticated(self, scope: Scope, headers: dict[bytes, list[bytes]]) -> bool:
        authorization = headers.get(b"authorization", [])
        if len(authorization) > 1:
            return False
        if authorization:
            scheme, _, credential = authorization[0].partition(b" ")
            if scheme.lower() == b"bearer" and self._token.matches(credential):
                return True

        if scope["type"] != "websocket":
            return False
        offered = [
            protocol.strip(b" \t")
            for value in headers.get(b"sec-websocket-protocol", [])
            for protocol in value.split(b",")
        ]
        credentials = [
            protocol.removeprefix(_WS_AUTH_PREFIX_BYTES)
            for protocol in offered
            if protocol.startswith(_WS_AUTH_PREFIX_BYTES)
        ]
        return len(credentials) == 1 and self._token.matches(credentials[0])

    async def _reject(
        self, scope: Scope, receive: Receive, send: Send, rejection: _Rejection
    ) -> None:
        request_id = scope["state"]["request_id"]
        is_websocket = scope["type"] == "websocket"
        logger.warning(
            "Request rejected",
            extra={
                "event": rejection.code,
                "method": "WEBSOCKET" if is_websocket else scope.get("method"),
                "path": scope.get("path"),
                "status": rejection.status,
                "request_id": request_id,
            },
        )

        if is_websocket:
            message = await receive()
            if message["type"] == "websocket.connect":
                await send({"type": "websocket.close", "code": _WS_POLICY_VIOLATION})
            return

        body = error_body_bytes(rejection.code, rejection.message, request_id)
        response_headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]
        if rejection is _UNAUTHORIZED:
            response_headers.append((b"www-authenticate", b"Bearer"))
        response_headers.extend(
            (name.encode("ascii"), value.encode("ascii"))
            for name, value in cors_headers(scope["state"].get(CORS_ORIGIN_STATE_KEY)).items()
        )
        await send(
            {"type": "http.response.start", "status": rejection.status, "headers": response_headers}
        )
        await send({"type": "http.response.body", "body": body})
