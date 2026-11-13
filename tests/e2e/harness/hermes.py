"""Preflight de Hermes: runner propio, commit instalado y herramientas que ve el modelo.

Hermes y el modelo no son confiables: la lista blanca se comprueba desde fuera, sobre los
`tools[]` que llegan al modelo, no sobre lo que el runner dice de sí mismo.
"""
from __future__ import annotations

import http.client
import json
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MIN_PYTHON = (3, 14)
RUNNER = Path("app/integrations/hermes/runner/drakter_runner.py")


def installed_commit(venv: Path) -> str | None:
    """Commit según PEP 610 (`direct_url.json`) o, si es editable, el del clon local."""
    for record in venv.glob("lib/python*/site-packages/hermes*.dist-info/direct_url.json"):
        data = json.loads(record.read_text())
        if commit := data.get("vcs_info", {}).get("commit_id"):
            return commit
        url = data.get("url", "")
        if url.startswith("file://"):
            probe = subprocess.run(["git", "-C", url.removeprefix("file://"), "rev-parse", "HEAD"],
                                   capture_output=True, text=True, check=False)
            return probe.stdout.strip() or None
    return None


def problems(venv: Path, commit: str, env: dict[str, str]) -> list[str]:
    """Lista vacía si el venv cumple. Solo inspecciona: no arranca Hermes."""
    python = venv / "bin" / "python"
    if not python.is_file():
        return [f"el venv no tiene {python}"]
    probe = subprocess.run([str(python), "-I", "-c", "import sys; print(*sys.version_info[:2])"],
                           capture_output=True, text=True, env=env, timeout=30, check=False)
    if probe.returncode != 0:
        return [f"{python} no se pudo ejecutar"]
    found = []
    version = tuple(int(part) for part in probe.stdout.split())
    if version < MIN_PYTHON:
        found.append(f"Python {version[0]}.{version[1]}; se exige >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")
    installed = installed_commit(venv)
    if installed is None:
        found.append("commit no verificable: sin direct_url.json con commit")
    elif installed != commit:
        found.append(f"commit {installed[:12]}; se exige {commit[:12]}")
    return found


def outside_allowlist(requests: list[dict], pattern: str) -> list[str]:
    allowed = re.compile(pattern)
    names = {tool.get("name", "") for request in requests for tool in request.get("tools") or []}
    return sorted(name for name in names if not allowed.fullmatch(name))


class ToolRecorder(ThreadingHTTPServer):
    """Proxy en loopback delante del stub: registra lo que se ofrece al modelo."""

    daemon_threads = True

    def __init__(self, upstream_port: int) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.upstream_port = upstream_port
        self.requests: list[dict] = []
        self.lock = threading.Lock()
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def port(self) -> int:
        return self.server_address[1]


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: ToolRecorder

    def log_message(self, format: str, *args) -> None:
        return

    def _forward(self, body: bytes | None) -> None:
        upstream = http.client.HTTPConnection("127.0.0.1", self.server.upstream_port, timeout=120)
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() in ("content-type", "accept", "anthropic-version")}
        headers["Host"] = f"127.0.0.1:{self.server.upstream_port}"
        upstream.request(self.command, self.path, body, headers)
        reply = upstream.getresponse()
        self.send_response(reply.status)
        for key, value in reply.getheaders():
            if key.lower() not in ("connection", "transfer-encoding", "server", "date"):
                self.send_header(key, value)
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        while chunk := reply.read1(65536):
            self.wfile.write(chunk)
            self.wfile.flush()
        upstream.close()

    def do_GET(self) -> None:
        self._forward(None)

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            with self.server.lock:
                self.server.requests.append(json.loads(body))
        except ValueError:
            pass  # el stub responderá al cuerpo inválido
        self._forward(body)
