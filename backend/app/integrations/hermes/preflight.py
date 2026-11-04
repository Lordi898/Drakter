"""The check that decides: what tools does Hermes really offer the model?

`python -m app.integrations.hermes.preflight` builds a temporary home, starts
Hermes against the DEV stub and a probe MCP server, launches a run, records the
tools[] of every model request and exits 0 only if nothing outside
mcp__drakter__* appears. GET /v1/toolsets is not used: it misses tools (H-05, H-08).
Never touches ~/.config/drakter, nor real keys.
"""

from __future__ import annotations

import argparse
import asyncio
import http.client
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import threading
from collections.abc import Iterable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Final

import httpx
import mcp_types as mt
import uvicorn
from mcp.server.lowlevel.server import Server
from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import BIND_HOST
from app.integrations.hermes.home import captured_tool_name
from app.integrations.hermes.settings import HERMES_COMMIT, HERMES_VERSION, AgentSettings
from app.integrations.hermes.supervisor import HermesSupervisor

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
PROBE_TOOL: Final = "preflight_probe"
PROBE_RESULT: Final = "PREFLIGHT-OK-5e1c"
SOUL_MARKER: Final = "Reglas de seguridad de Drakter"
CANARY: Final = "PREFLIGHT-CANARY-CONTEXT-FILE"
SCENARIO: Final = "drakter-preflight"
RUN_TIMEOUT_S: Final = 180.0
HERMES_CHECK_TIMEOUT_S: Final = 60.0
_COMMIT_IN_VERSION_RE: Final = re.compile(r"(?:\blocal |\.g)([0-9a-f]{7,40})\b")


def commit_matches(version_output: str) -> bool:
    """By commit only: accepts `local b200f5bc60e3` and `+20302.gb200f5b` alike."""
    found = _COMMIT_IN_VERSION_RE.findall(version_output)
    return bool(found) and all(HERMES_COMMIT.startswith(commit) for commit in found)


async def _output(*command: str, env: dict[str, str], cwd: Path) -> tuple[int, str]:
    process = await asyncio.create_subprocess_exec(
        *command, env=env, cwd=cwd, stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), HERMES_CHECK_TIMEOUT_S)
    except TimeoutError:
        process.kill()
        await process.wait()
        return 124, ""
    return int(process.returncode or 0), stdout.decode("utf-8", "replace")


async def check_hermes_install(binary: str, work: Path, report: Report) -> bool:
    """Commit and aiohttp, before a launch that would only time out."""
    found = shutil.which(binary)
    if not report.check(found is not None, "ejecutable de Hermes encontrado", binary):
        return False
    assert found is not None
    home = work / "version-home"
    home.mkdir(mode=0o700)
    # updates.check off here too: `hermes --version` otherwise asks the network.
    (home / "config.yaml").write_text('{"updates": {"check": false}}\n', encoding="utf-8")
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "HERMES_HOME": str(home)}
    code, text = await _output(found, "--version", env=env, cwd=work)
    first_line = text.splitlines()[0] if text else ""
    matches = code == 0 and commit_matches(text)
    report.check(matches, f"commit fijado {HERMES_VERSION} {HERMES_COMMIT[:12]}", first_line)
    shebang = Path(found).read_bytes()[:256].split(b"\n", 1)[0]
    python = shebang[2:].decode("utf-8", "replace").strip() if shebang.startswith(b"#!") else ""
    code, _ = await _output(python, "-I", "-c", "import aiohttp", env=env, cwd=work) if python else (1, "")
    has_aiohttp = report.check(
        code == 0,
        "aiohttp importa en el venv de Hermes",
        "" if code == 0 else "sin aiohttp no arranca el API server: instala con `uv sync --frozen --extra sms`",
    )
    return matches and has_aiohttp


class Recorder(ThreadingHTTPServer):
    """Loopback proxy in front of the stub: the stub stays a black box."""

    daemon_threads = True

    def __init__(self, upstream_port: int) -> None:
        super().__init__((BIND_HOST, 0), _RecordingHandler)
        self.upstream_port = upstream_port
        self.requests: list[dict[str, Any]] = []
        self.lock = threading.Lock()


class _RecordingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: Recorder

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _forward(self, body: bytes | None) -> None:
        upstream = http.client.HTTPConnection(BIND_HOST, self.server.upstream_port, timeout=60)
        headers = {
            name: value for name, value in self.headers.items()
            if name.lower() in ("content-type", "accept", "anthropic-version")
        }
        headers["Host"] = f"{BIND_HOST}:{self.server.upstream_port}"
        upstream.request(self.command, self.path, body, headers)
        response = upstream.getresponse()
        self.send_response(response.status)
        for name, value in response.getheaders():
            if name.lower() not in ("connection", "transfer-encoding", "server", "date"):
                self.send_header(name, value)
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        while chunk := response.read1(65536):
            self.wfile.write(chunk)
            self.wfile.flush()
        upstream.close()

    def do_GET(self) -> None:
        self._forward(None)

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            parsed = json.loads(body)
            with self.server.lock:
                self.server.requests.append(parsed)
        except ValueError:
            pass
        self._forward(body)


class _BearerOnly:
    def __init__(self, app: ASGIApp, token: str) -> None:
        self._app = app
        self._expected = f"Bearer {token}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and dict(scope["headers"]).get(b"authorization") != self._expected:
            await send({"type": "http.response.start", "status": 401, "headers": []})
            await send({"type": "http.response.body", "body": b""})
            return
        await self._app(scope, receive, send)


@dataclass
class ProbeState:
    calls: int = 0
    names: list[str] = field(default_factory=list)


def build_probe_mcp(names: Iterable[str], state: ProbeState, token: str) -> ASGIApp:
    """Stand-in for the real bridge, so this module needs nothing from app.tools."""
    tools = [
        mt.Tool(name=name, description="Preflight probe", input_schema={"type": "object", "properties": {}})
        for name in names
    ]

    async def list_tools(_ctx: Any, _params: Any) -> mt.ListToolsResult:
        return mt.ListToolsResult(tools=tools)

    async def call_tool(_ctx: Any, params: mt.CallToolRequestParams) -> mt.CallToolResult:
        state.calls += 1
        state.names.append(params.name)
        return mt.CallToolResult(content=[mt.TextContent(type="text", text=PROBE_RESULT)])

    server = Server("drakter-preflight", on_list_tools=list_tools, on_call_tool=call_tool)
    app = server.streamable_http_app(
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    return _BearerOnly(app, token)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind((BIND_HOST, 0))
        return int(sock.getsockname()[1])


def write_scenario(directory: Path) -> None:
    steps = [
        {"tool_calls": [{"name": f"drakter__{PROBE_TOOL}", "input": {}}]},
        {"text": "Fin del preflight: {{tool_result}}"},
    ]
    (directory / f"{SCENARIO}.json").write_text(json.dumps({"steps": steps}), encoding="utf-8")


class Report:
    def __init__(self) -> None:
        self.failures = 0

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        self.failures += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAIL'} {label}{f' ({detail})' if detail else ''}", flush=True)
        return ok


def offered_tools(requests: list[dict[str, Any]]) -> set[str]:
    return {
        str(tool.get("name"))
        for request in requests
        for tool in request.get("tools") or []
        if isinstance(tool, dict)
    }


def system_text(request: dict[str, Any]) -> str:
    system = request.get("system")
    if isinstance(system, str):
        return system
    return "\n".join(str(block.get("text", "")) for block in system or [] if isinstance(block, dict))


async def wait_run(client: httpx.AsyncClient, key: str, run_id: str) -> str:
    deadline = asyncio.get_running_loop().time() + RUN_TIMEOUT_S
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get(f"/v1/runs/{run_id}", headers={"Authorization": f"Bearer {key}"})
        status = str(response.json().get("status"))
        if status in ("completed", "failed", "cancelled", "stopped", "error"):
            return status
        await asyncio.sleep(0.5)
    return "timeout"


async def check_cron(client: httpx.AsyncClient, key: str, recorder: Recorder, report: Report) -> None:
    """H-20: a job shares the API key but not the api_server list.

    NO COMPROBADO unless this prints its OK line: with no `cron` list drakter-5 saw a job run
    terminal, and [no_mcp] plus agent.disabled_toolsets stay unproven until a job reaches the
    model here. The backend never calls /api/jobs either way.
    """
    headers = {"Authorization": f"Bearer {key}"}
    before = len(recorder.requests)
    marker = f"[stub:{SCENARIO}] cron"
    created = await client.post(
        "/api/jobs",
        headers=headers,
        json={"name": "preflight", "schedule": "every 1h", "prompt": marker},
    )
    if created.status_code not in (200, 201):
        print(f"NO COMPROBADO cron: /api/jobs responde {created.status_code}", flush=True)
        return
    job_id = created.json()["job"]["id"]
    await client.post(f"/api/jobs/{job_id}/run", headers=headers)
    deadline = asyncio.get_running_loop().time() + 90.0
    cron_requests: list[dict[str, Any]] = []
    while asyncio.get_running_loop().time() < deadline and not cron_requests:
        await asyncio.sleep(0.5)
        with recorder.lock:  # only the job's own request: a late session title would prove nothing
            cron_requests = [r for r in recorder.requests[before:] if marker in json.dumps(r.get("messages"))]
    if not cron_requests:
        print("NO COMPROBADO cron: el job no llegó al modelo en 90 s", flush=True)
    else:
        tools = offered_tools(cron_requests)
        report.check(not tools, "cron sin herramientas", ", ".join(sorted(tools)[:10]))
    await client.delete(f"/api/jobs/{job_id}", headers=headers)


async def preflight(args: argparse.Namespace, work: Path, report: Report) -> None:
    stub_script = Path(args.stub).resolve()
    if not stub_script.is_file():
        raise SystemExit(f"stub no encontrado: {stub_script}")
    if not await check_hermes_install(args.hermes, work, report):
        return
    data_dir = work / "data"
    data_dir.mkdir(mode=0o700)
    scenarios = work / "scenarios"
    scenarios.mkdir()
    shutil.copytree(stub_script.parent / "scenarios", scenarios, dirs_exist_ok=True)
    write_scenario(scenarios)

    token = "preflight-" + os.urandom(16).hex()
    names = sorted({PROBE_TOOL, *args.tools})
    hermes_port, tools_port, stub_port = free_port(), free_port(), free_port()
    probe = ProbeState()
    stub = await asyncio.create_subprocess_exec(
        sys.executable, "-I", str(stub_script), "--port", str(stub_port), "--scenarios", str(scenarios),
        cwd=work,
        env={"PATH": "/usr/bin:/bin", "DRAKTER_ENV": "development"},
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    recorder = Recorder(stub_port)
    threading.Thread(target=recorder.serve_forever, daemon=True).start()
    mcp_config = uvicorn.Config(
        build_probe_mcp(names, probe, token), host=BIND_HOST, port=tools_port, log_config=None,
        access_log=False, lifespan="on",
    )
    mcp_server = uvicorn.Server(mcp_config)
    mcp_task = asyncio.create_task(mcp_server.serve())
    settings = AgentSettings(
        _env_file=None,
        env="development",
        model_provider="dev_stub",
        model_name=args.model,
        dev_stub_url=f"http://{BIND_HOST}:{recorder.server_address[1]}",
        hermes_command=args.hermes,
        hermes_port=hermes_port,
        anthropic_api_key=None,
    )
    tools_url = f"http://{BIND_HOST}:{tools_port}/mcp"
    supervisor = HermesSupervisor(settings, data_dir, names, token, tools_url, REPO_ROOT)
    # Where a wrong terminal.cwd would make Hermes look for context files (F21, H-15).
    home_canary = supervisor._paths.user_home
    home_canary.mkdir(parents=True, mode=0o700)
    (home_canary / "AGENTS.md").write_text(CANARY, encoding="utf-8")
    try:
        await asyncio.sleep(0.5)
        await supervisor.start()
        ready = report.check(supervisor.state == "ready", "gateway listo y guardián cargado", supervisor.detail)
        if not ready:
            print_log_tail(data_dir)
            return
        child = supervisor.child_pid
        print(f"home {supervisor.manifest.digest if supervisor.manifest else '?'}", flush=True)
        key = supervisor.api_key()
        async with httpx.AsyncClient(base_url=supervisor.api_base, timeout=30.0, trust_env=False) as client:
            created = await client.post(
                "/v1/runs",
                headers={"Authorization": f"Bearer {key}"},
                json={"input": f"[stub:{SCENARIO}] comprobación"},
            )
            if not report.check(created.status_code in (200, 202), "run aceptado", str(created.status_code)):
                return
            status = await wait_run(client, key, created.json()["run_id"])
            report.check(status == "completed", "run completado", status)
            await asyncio.sleep(1.0)
            with recorder.lock:
                run_requests = list(recorder.requests)
            with_tools = [request for request in run_requests if request.get("tools")]
            report.check(bool(with_tools), "el modelo recibió tools[]", f"{len(run_requests)} peticiones")
            tools = offered_tools(run_requests)
            print(f"tools[] = {sorted(tools)}", flush=True)
            foreign = sorted(name for name in tools if not name.startswith("mcp__drakter__"))
            report.check(not foreign, "ninguna herramienta fuera de mcp__drakter__*", ", ".join(foreign))
            missing = sorted(captured_tool_name(name) for name in names if captured_tool_name(name) not in tools)
            report.check(not missing, "catálogo completo en tools[]", ", ".join(missing))
            report.check(probe.names[:1] == [PROBE_TOOL], "llamada MCP con ${DRAKTER_MCP_URL} y ${DRAKTER_MCP_TOKEN}")
            system = system_text(with_tools[0]) if with_tools else ""
            report.check(SOUL_MARKER in system, "SOUL.md en el prompt de sistema")
            report.check(CANARY not in system, "sin archivos de contexto de HOME en el prompt")
            await check_cron(client, key, recorder, report)
        await supervisor.stop()
        gone = child is not None and not _group_alive(child)
        report.check(gone, "sin procesos tras parar")
        report.check(supervisor.state == "stopped", "estado stopped")
        check_no_secret_on_disk(data_dir, [key, token], report)
    finally:
        await supervisor.stop()
        mcp_server.should_exit = True
        await asyncio.gather(mcp_task, return_exceptions=True)
        recorder.shutdown()
        recorder.server_close()
        stub.terminate()
        await stub.wait()


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def check_no_secret_on_disk(data_dir: Path, secrets: list[str], report: Report) -> None:
    needles = [secret.encode() for secret in secrets if secret]
    leaks = []
    for path in data_dir.rglob("*"):
        if path.is_file() and not path.is_symlink() and path.stat().st_size < 64 * 1024 * 1024:
            content = path.read_bytes()
            if any(needle in content for needle in needles):
                leaks.append(str(path.relative_to(data_dir)))
    report.check(not leaks, "ningún secreto en disco", ", ".join(leaks))


def print_log_tail(data_dir: Path) -> None:
    log = data_dir / "logs" / "hermes.log"
    if log.is_file():
        print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]), flush=True)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Comprueba la superficie real de herramientas de Hermes.")
    parser.add_argument("--stub", default=os.environ.get(
        "DRAKTER_DEV_STUB_SERVER", str(REPO_ROOT / "tools" / "dev-llm-stub" / "server.py")))
    parser.add_argument("--hermes", default=os.environ.get("DRAKTER_HERMES_COMMAND", "hermes"))
    parser.add_argument("--model", default="claude-haiku-5-5")
    parser.add_argument("--tools", default="", help="nombres nativos del catálogo, separados por comas")
    parser.add_argument("--keep", action="store_true", help="conserva el directorio temporal")
    args = parser.parse_args(argv)
    args.tools = [name for name in args.tools.split(",") if name]
    return args


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("DRAKTER_ENV", "").strip().lower() == "production":
        print("el preflight usa el stub de desarrollo: no corre con DRAKTER_ENV=production", file=sys.stderr)
        return 2
    args = parse_args(argv)
    report = Report()
    work = Path(tempfile.mkdtemp(prefix="drakter-preflight-")).resolve()
    try:
        asyncio.run(preflight(args, work, report))
    finally:
        if args.keep:
            print(f"directorio conservado: {work}", flush=True)
        else:
            shutil.rmtree(work, ignore_errors=True)
    print("PREFLIGHT OK" if not report.failures else f"PREFLIGHT FALLIDO: {report.failures}", flush=True)
    return 0 if not report.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
