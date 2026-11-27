"""MCP bridge: serves the tool registry to Hermes on its own loopback port.

The separation from the GUI API is one of network and credential: Hermes holds a token that
is valid here and nowhere else, and no GUI or confirmation route exists on this port. Every
check below runs before any byte reaches the MCP SDK.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import socket
from collections.abc import Generator
from typing import Any, Final, Protocol
from uuid import UUID, uuid4

import uvicorn
from drakter_contracts.errors import ErrorCode
from drakter_contracts.tools import ToolOk, ToolOutcome
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import BIND_HOST
from app.core.errors import error_body_bytes
from app.tools.registry import ToolObserver, ToolRegistry
from app.tools.spec import RiskClass, ToolContext, ToolSpec
from app.tools.turns import TurnTracker

AGENT_TOOLS_PATH: Final = "/mcp"
MCP_SERVER_NAME: Final = "drakter"

_NO_TURN: Final = UUID(int=0)
_MAX_BODY_BYTES: Final = 1024 * 1024
_START_TIMEOUT_S: Final = 10.0
_STOP_TIMEOUT_S: Final = 10.0
_BEARER: Final = b"bearer "
_WS_POLICY_VIOLATION: Final = 1008

logger = logging.getLogger("drakter.tools.mcp")


class _TokenLike(Protocol):
    def matches(self, candidate: bytes) -> bool: ...  # hmac.compare_digest in SessionToken


def _mcp_tool(spec: ToolSpec) -> types.Tool:
    # No output_schema: what the agent receives is ToolOutcome, not result_model.
    return types.Tool(
        name=spec.name,
        description=spec.description,
        input_schema=spec.args_model.model_json_schema(),
        annotations=types.ToolAnnotations(
            read_only_hint=True if spec.risk is RiskClass.READ else None,
            destructive_hint=spec.risk is RiskClass.CONFIRM,
            idempotent_hint=spec.idempotent,
        ),
    )


def _call_result(outcome: ToolOutcome) -> types.CallToolResult:
    """A business error travels as data, in the outcome.

    ``is_error`` stays False: Hermes counts every ``isError`` as a circuit breaker strike and
    after 3 in a row (``_CIRCUIT_BREAKER_THRESHOLD``) blocks the whole server for 60 s, so a
    model that insists on bad arguments would lose all its tools.

    Images (``ToolOk.attachments``, excluded from the JSON) go after the text, which comes
    first and carries the untrusted envelope. Hermes turns them into ``image`` blocks when
    ``agent.image_input_mode`` is ``native``.
    """
    payload = outcome.model_dump(mode="json")
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    content: list[types.TextContent | types.ImageContent] = [
        types.TextContent(type="text", text=text)
    ]
    if isinstance(outcome, ToolOk):
        content.extend(
            types.ImageContent(type="image", data=a.data_b64, mime_type=a.mime_type)
            for a in outcome.attachments
        )
    return types.CallToolResult(
        content=content,
        structured_content=payload,
        is_error=False,
    )


def _build_server(
    registry: ToolRegistry, turns: TurnTracker, state: Any, observer: ToolObserver | None
) -> Server[Any]:
    options = {"observer": observer} if observer is not None else {}

    async def list_tools(ctx: Any, params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=[_mcp_tool(spec) for spec in registry.catalog()])

    async def call_tool(ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        # Identity comes from the tracker. Nothing the model sends can select a session (F19);
        # without a turn the nil ids make dispatch reject the call and audit it.
        active = turns.active()
        tool_ctx = ToolContext(
            turn_id=active.turn_id if active else _NO_TURN,
            session_id=active.session_id if active else _NO_TURN,
            call_id=uuid4().hex,
            principal="agent",
            state=state,
        )
        outcome = await registry.dispatch(
            params.name, dict(params.arguments or {}), tool_ctx, **options
        )
        return _call_result(outcome)

    return Server(MCP_SERVER_NAME, on_list_tools=list_tools, on_call_tool=call_tool)


def _header_values(scope: Scope, name: bytes) -> list[bytes]:
    return [value for key, value in scope["headers"] if key.lower() == name]


def _host_allowed(scope: Scope) -> bool:
    """Exactly ``127.0.0.1:<real port>``. The port comes from the socket, not the request."""
    server = scope.get("server")
    if server is None:
        return False
    return _header_values(scope, b"host") == [f"{BIND_HOST}:{server[1]}".encode("ascii")]


def _bearer(scope: Scope) -> bytes | None:
    values = _header_values(scope, b"authorization")
    if len(values) != 1 or values[0][: len(_BEARER)].lower() != _BEARER:
        return None
    return values[0][len(_BEARER) :]


class _AgentToolsApp:
    """Pure ASGI. Rejects before the SDK and owns the session manager's lifetime."""

    def __init__(self, server: Server[Any], token: _TokenLike) -> None:
        self._server = server
        self._token = token
        self._manager: StreamableHTTPSessionManager | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
        elif scope["type"] == "websocket":
            await receive()
            await send({"type": "websocket.close", "code": _WS_POLICY_VIOLATION})
        elif scope["type"] == "http":
            await self._http(scope, receive, send)

    async def _lifespan(self, receive: Receive, send: Send) -> None:
        await receive()  # lifespan.startup
        # run() works once per instance, so a new app start needs a new manager.
        manager = StreamableHTTPSessionManager(
            app=self._server,
            json_response=True,
            stateless=True,
            max_request_body_size=_MAX_BODY_BYTES,
            security_settings=TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=[f"{BIND_HOST}:*"],
                allowed_origins=[],
            ),
        )
        async with manager.run():
            self._manager = manager
            await send({"type": "lifespan.startup.complete"})
            await receive()  # lifespan.shutdown
            self._manager = None
        await send({"type": "lifespan.shutdown.complete"})

    async def _http(self, scope: Scope, receive: Receive, send: Send) -> None:
        rejection = self._rejection(scope)
        if rejection is not None:
            status, code, message, headers = rejection
            logger.warning(
                "agent tools request rejected",
                extra={
                    "event": "agent_tools_rejected",
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status,
                },
            )
            await self._send_error(send, status, code, message, headers)
            return
        if self._manager is None:
            await self._send_error(
                send, 503, ErrorCode.SERVICE_UNAVAILABLE, "Tool bridge not ready.", []
            )
            return
        await self._manager.handle_request(scope, receive, send)

    def _rejection(
        self, scope: Scope
    ) -> tuple[int, str, str, list[tuple[bytes, bytes]]] | None:
        client = scope.get("client")
        if client is None or client[0] != BIND_HOST:
            return 403, ErrorCode.FORBIDDEN_CLIENT, "Client not allowed.", []
        if not _host_allowed(scope):
            return 403, ErrorCode.FORBIDDEN_HOST, "Host not allowed.", []
        if _header_values(scope, b"origin"):
            return 403, ErrorCode.FORBIDDEN_ORIGIN, "Origin not allowed.", []
        candidate = _bearer(scope)
        if candidate is None or not self._token.matches(candidate):
            challenge = [(b"www-authenticate", b"Bearer")]
            return 401, ErrorCode.UNAUTHORIZED, "Authentication required.", challenge
        if scope["path"] != AGENT_TOOLS_PATH:
            return 404, "http_404", "Not found.", []
        # Stateless: there is no stream to open with GET nor session to end with DELETE.
        if scope["method"] != "POST":
            return 405, "http_405", "Method not allowed.", [(b"allow", b"POST")]
        return None

    @staticmethod
    async def _send_error(
        send: Send,
        status: int,
        code: str,
        message: str,
        headers: list[tuple[bytes, bytes]],
    ) -> None:
        body = error_body_bytes(code, message, str(uuid4()))
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    *headers,
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def build_agent_tools_app(
    registry: ToolRegistry,
    turns: TurnTracker,
    token: _TokenLike,
    state: Any,
    *,
    observer: ToolObserver | None = None,
) -> ASGIApp:
    if registry.turns is not turns:
        raise ValueError("registry and bridge must share the same TurnTracker")
    return _AgentToolsApp(_build_server(registry, turns, state, observer), token)


class _EmbeddedServer(uvicorn.Server):
    """Runs inside the backend's event loop: signals belong to the main server."""

    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None, None, None]:
        yield


class AgentToolsServer:
    """Own Uvicorn on an ephemeral loopback port. Neither address nor port is configurable.

    ``port`` and ``url`` are valid after ``start()``; Hermes learns them from the backend.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app
        self.port = 0
        self._server: _EmbeddedServer | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def url(self) -> str:
        if not self.port:
            raise RuntimeError("agent tools server not started")
        return f"http://{BIND_HOST}:{self.port}{AGENT_TOOLS_PATH}"

    async def start(self) -> None:
        if self._task is not None:
            raise RuntimeError("agent tools server already started")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((BIND_HOST, 0))
            sock.listen(128)
        except OSError:
            sock.close()
            raise
        self.port = sock.getsockname()[1]

        config = uvicorn.Config(
            self._app,
            host=BIND_HOST,  # informational: the bound socket is passed to serve()
            port=self.port,
            log_config=None,
            access_log=False,
            server_header=False,
            proxy_headers=False,
            ws="none",
            lifespan="on",
            timeout_graceful_shutdown=int(_STOP_TIMEOUT_S / 2),
        )
        server = _EmbeddedServer(config)
        task = asyncio.create_task(server.serve(sockets=[sock]))
        self._server, self._task = server, task
        try:
            async with asyncio.timeout(_START_TIMEOUT_S):
                while not server.started:
                    if task.done():
                        raise RuntimeError("agent tools server stopped during startup")
                    await asyncio.sleep(0.01)
        except BaseException:
            with contextlib.suppress(Exception):
                await self.stop()
            sock.close()
            raise

    async def stop(self) -> None:
        server, task = self._server, self._task
        self._server, self._task = None, None
        if server is None or task is None:
            return
        server.should_exit = True
        try:
            await asyncio.wait_for(asyncio.shield(task), _STOP_TIMEOUT_S)
        except TimeoutError:
            server.force_exit = True
            await task
