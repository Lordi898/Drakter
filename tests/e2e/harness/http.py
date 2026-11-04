"""Cliente HTTP y WebSocket del backend. Sin proxies: todo va por loopback."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@dataclass(frozen=True)
class Response:
    status: int
    body: Any  # JSON si lo era; si no, texto
    headers: dict[str, str]

    @property
    def error_code(self) -> str | None:
        if isinstance(self.body, dict) and isinstance(self.body.get("error"), dict):
            return self.body["error"].get("code")
        return None


class Api:
    def __init__(self, port: int, token: str) -> None:
        self.port = port
        self.token = token

    def request(self, method: str, path: str, *, json_body: Any = None, auth: bool = True,
                headers: dict[str, str] | None = None, timeout: float = 30) -> Response:
        data = None if json_body is None else json.dumps(json_body).encode()
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data,
                                         method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if auth:
            request.add_header("Authorization", f"Bearer {self.token}")
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with _OPENER.open(request, timeout=timeout) as reply:
                return _response(reply.status, reply.read(), reply.headers)
        except urllib.error.HTTPError as exc:
            return _response(exc.code, exc.read(), exc.headers)

    def ws(self, path: str = "/ws", *, origin: str | None = None, auth: bool = True,
           open_timeout: float = 5):
        """Abre un WebSocket con el contrato real: subprotocolo, nunca token en la URL."""
        from websockets.sync.client import connect

        protocols = ["drakter.v1"]
        if auth:
            protocols.append(f"drakter.auth.{self.token}")
        return connect(f"ws://127.0.0.1:{self.port}{path}", subprotocols=protocols, origin=origin,
                       proxy=None, open_timeout=open_timeout)


def _response(status: int, raw: bytes, headers: Any) -> Response:
    text = raw.decode("utf-8", "replace")
    try:
        body: Any = json.loads(text) if text else None
    except ValueError:
        body = text
    return Response(status, body, {k.lower(): v for k, v in headers.items()})
