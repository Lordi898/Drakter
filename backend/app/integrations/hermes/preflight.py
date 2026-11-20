"""The check that decides: what tools does Hermes really offer the model?

`python -m app.integrations.hermes.preflight` builds a temporary home, starts the
runner against the DEV stub and a probe MCP server, runs real turns, records the
tools[] of every model request and exits 0 only if it is exactly mcp__drakter__<catalog>.
Never reads ~/.config/drakter and never uses a real key.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import http.client
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

import mcp_types as mt
import uvicorn
from mcp.server.lowlevel.server import Server
from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import BIND_HOST
from app.integrations.hermes.home import FIRST_SKILL, SKILLS_HEADER, captured_tool_name
from app.integrations.hermes.settings import HERMES_COMMIT, AgentSettings
from app.integrations.hermes.supervisor import HermesSupervisor

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
PROBE_TOOL: Final = "preflight_probe"
PROBE_RESULT: Final = "PREFLIGHT-OK-5e1c"
INSTRUCTIONS: Final = "Instrucciones estables de la sesión de preflight."
SOUL_MARKER: Final = "Reglas de seguridad de Drakter"
VOICE_MARKER: Final = "# VOICE"  # agent/identity/VOICE.md, with the speech markup block expanded
CANARY: Final = "PREFLIGHT-CANARY-CONTEXT-FILE"
SCENARIO: Final = "drakter-preflight"
TURN_TIMEOUT_S: Final = 180.0
HERMES_CHECK_TIMEOUT_S: Final = 60.0
SLOW_CHUNK_DELAY_S: Final = 0.5


class Report:
    def __init__(self) -> None:
        self.failures = 0

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        self.failures += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAIL'} {label}{f' ({detail})' if detail else ''}", flush=True)
        return ok


class Recorder(ThreadingHTTPServer):
    """Loopback proxy in front of the stub: the stub stays a black box."""

    daemon_threads = True

    def __init__(self, upstream_port: int) -> None:
        super().__init__((BIND_HOST, 0), _RecordingHandler)
        self.upstream_port = upstream_port
        self.requests: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        self.chunk_delay_s = 0.0

    def snapshot(self, start: int = 0) -> list[dict[str, Any]]:
        with self.lock:
            return self.requests[start:]


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
        try:
            while chunk := response.read1(256 if self.server.chunk_delay_s else 65536):
                self.wfile.write(chunk)
                self.wfile.flush()
                time.sleep(self.server.chunk_delay_s)
        except OSError:
            pass  # a stopped turn drops the connection
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


async def venv_commit(python: str, work: Path) -> str:
    """By hash, from the install itself: the version text of one commit varies."""
    code = "from hermes_cli.version_info import get_version_info; print(get_version_info().commit)"
    home = work / "version-home"
    home.mkdir(mode=0o700)
    process = await asyncio.create_subprocess_exec(
        python, "-I", "-c", code, cwd=work,
        env={"PATH": "/usr/bin:/bin", "HOME": str(home), "HERMES_HOME": str(home)},
        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), HERMES_CHECK_TIMEOUT_S)
    except TimeoutError:
        process.kill()
        await process.wait()
        return ""
    lines = stdout.decode("utf-8", "replace").split()
    return lines[-1] if lines else ""


async def run_probe_turn(supervisor: HermesSupervisor, session_id: str, text: str) -> list[dict[str, Any]]:
    events = []
    async with asyncio.timeout(TURN_TIMEOUT_S):
        async for event in supervisor.run_turn(str(uuid4()), session_id, text, INSTRUCTIONS):
            events.append(event)
    return events


def gateway_processes(pgid: int, marker: str) -> list[str]:
    """Hermes gateways of this run, by process group or by this run's home on the command line."""
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
            group = os.getpgid(int(entry.name))
        except OSError:
            continue
        if (group == pgid or marker in cmdline) and ("gateway" in cmdline or "scheduler" in cmdline):
            found.append(f"{entry.name}: {cmdline[:80]}")
    return found


def scheduler_threads(pid: int) -> list[str]:
    names = []
    for task in Path(f"/proc/{pid}/task").iterdir():
        try:
            names.append((task / "comm").read_text(encoding="utf-8").strip())
        except OSError:
            continue
    return [name for name in names if "cron" in name.lower() or "sched" in name.lower()]


async def check_stop(supervisor: HermesSupervisor, recorder: Recorder, report: Report) -> None:
    """Times the real cut of a turn while the model is streaming, without any kill."""
    recorder.chunk_delay_s = SLOW_CHUNK_DELAY_S
    turn_id = str(uuid4())
    events: list[dict[str, Any]] = []

    async def consume() -> None:
        async for event in supervisor.run_turn(turn_id, str(uuid4()), "[stub:conversacion] parada", INSTRUCTIONS):
            events.append(event)

    pid = supervisor.child_pid
    task = asyncio.create_task(consume())
    async with asyncio.timeout(TURN_TIMEOUT_S):
        while not any(event.get("ev") == "delta" for event in events):
            await asyncio.sleep(0.01)
    started = time.monotonic()
    await supervisor.stop_turn(turn_id)
    await task
    elapsed = time.monotonic() - started
    recorder.chunk_delay_s = 0.0
    kept = supervisor.child_pid == pid
    report.check(
        events[-1].get("ev") == "cancelled" and kept,
        "hard_interrupt corta un turno en curso",
        f"{elapsed:.2f} s, proceso {'conservado' if kept else 'matado'}",
    )


async def check_steer(supervisor: HermesSupervisor, recorder: Recorder, report: Report) -> None:
    """Voice v2 (V-22): `steer` while the model streams answers `steered` in the same turn."""
    recorder.chunk_delay_s = SLOW_CHUNK_DELAY_S
    turn_id = str(uuid4())
    events: list[dict[str, Any]] = []

    async def consume() -> None:
        async for event in supervisor.run_turn(turn_id, str(uuid4()), "[stub:conversacion] corrige", INSTRUCTIONS):
            events.append(event)

    task = asyncio.create_task(consume())
    async with asyncio.timeout(TURN_TIMEOUT_S):
        while not any(event.get("ev") == "delta" for event in events):
            await asyncio.sleep(0.01)
        sent = await supervisor.steer_turn(turn_id, "mejor responde en una frase")
        await task
    recorder.chunk_delay_s = 0.0
    steered = [event for event in events if event.get("ev") == "steered"]
    report.check(
        sent and len(steered) == 1 and events[-1].get("ev") in ("completed", "cancelled", "failed"),
        "steer responde steered en el mismo turno",
        f"accepted={steered[0].get('accepted') if steered else '?'}, terminal={events[-1].get('ev') if events else '?'}",
    )


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


async def exercise(
    supervisor: HermesSupervisor, recorder: Recorder, probe: ProbeState, names: list[str], data_dir: Path,
    token: str, report: Report,
) -> None:
    await supervisor.start()
    await supervisor.wait_settled()
    if not report.check(supervisor.state == "ready", "runner listo: nonce, commit y catálogo", supervisor.detail):
        print_log_tail(data_dir)
        return
    pid = supervisor.child_pid
    assert pid is not None
    print(f"home {supervisor.manifest.digest if supervisor.manifest else '?'}", flush=True)
    session_id = str(uuid4())
    events = await run_probe_turn(supervisor, session_id, f"[stub:{SCENARIO}] comprobación")
    print(f"eventos = {[event.get('ev') for event in events]}", flush=True)
    last = events[-1] if events else {}
    report.check(last.get("ev") == "completed", "turno completado", str(last.get("output", last))[:120])

    first = [request for request in recorder.snapshot() if request.get("tools")]
    if not report.check(bool(first), "el modelo recibió tools[]", f"{len(recorder.snapshot())} peticiones"):
        return
    tools = offered_tools(recorder.snapshot())
    print(f"tools[] = {sorted(tools)}", flush=True)
    expected = {captured_tool_name(name) for name in names}
    report.check(tools == expected, "tools[] es exactamente el catálogo", ", ".join(sorted(tools ^ expected)))
    report.check(probe.names[:1] == [PROBE_TOOL], "llamada MCP con ${DRAKTER_MCP_URL} y ${DRAKTER_MCP_TOKEN}")
    system = system_text(first[0])
    report.check(SOUL_MARKER in system, "SOUL.md en el prompt de sistema")
    report.check(
        VOICE_MARKER in system and "<!-- speech_markup" not in system,
        "VOICE.md en el prompt de sistema, con las etiquetas de expresión",
    )
    report.check(INSTRUCTIONS in system, "instructions en el prompt de sistema")
    skills = [name for name in sorted(tools) if "skill" in name.removeprefix(captured_tool_name(""))]
    report.check(not skills, "sin herramientas skill_* (skill_manage, skill_view, skills_list)", ", ".join(skills))
    report.check(
        SKILLS_HEADER in system and f"## Skill `{FIRST_SKILL}`" in system,
        "skills de agent/skills/ en el prompt de sistema, de solo lectura",
    )
    report.check(CANARY not in system, "sin archivos de contexto en el prompt")

    before = len(recorder.snapshot())
    await run_probe_turn(supervisor, session_id, "[stub:conversacion] segundo turno")
    second = [request for request in recorder.snapshot(before) if request.get("tools")]
    digest = hashlib.sha256(system.encode()).hexdigest()
    second_digest = hashlib.sha256(system_text(second[0]).encode()).hexdigest() if second else "-"
    print(f"hash de las instructions: {digest[:16]} / {second_digest[:16]}", flush=True)
    stable = bool(second) and second_digest == digest and second[0]["tools"] == first[0]["tools"]
    report.check(stable, "hash del system y tools idénticos entre turnos (H-21, V-21)")
    config = json.loads((data_dir / "hermes" / "config.yaml").read_text(encoding="utf-8"))
    report.check(config["agent"].get("reasoning_effort") == "low", "reasoning_effort low en el primer plano")
    grew = bool(second) and len(second[0]["messages"]) > len(first[0]["messages"])
    report.check(grew, "el segundo turno lleva el historial")

    alive = gateway_processes(pid, str(data_dir)) + scheduler_threads(pid)
    report.check(not alive, "ningún gateway ni scheduler vivo", "; ".join(alive))
    await check_steer(supervisor, recorder, report)
    await check_stop(supervisor, recorder, report)
    pid = supervisor.child_pid or pid
    await supervisor.stop()
    await asyncio.sleep(0.2)
    report.check(not _group_alive(pid), "sin procesos tras parar")
    report.check(supervisor.state == "stopped", "estado stopped")
    check_no_secret_on_disk(data_dir, [token], report)


# Private Hermes names the runner relies on (drakter_runner.DrakterAgent), each with the module
# that calls or reads it. A rename upstream would make the override dead code without any error.
RUNNER_HOOKS: Final[tuple[tuple[str, str, bool], ...]] = (
    # (name, module that uses it, must be a method of AIAgent)
    ("_repair_tool_call", "agent.turn_tool_validation", True),
    ("_invoke_api_request_error_hook", "agent.turn_api_error", True),
    ("_try_recover_primary_transport", "agent.turn_api_error", True),
    ("_api_max_retries", "agent.conversation_loop", False),
    ("_auto_recovery_cycles", "agent.turn_recovery_autorecover", False),
)


async def venv_missing_hooks(python: str, work: Path) -> list[str]:
    """Names of RUNNER_HOOKS that this Hermes no longer defines or no longer uses."""
    code = (
        "import importlib, inspect, json, sys\n"
        "from run_agent import AIAgent\n"
        "missing = []\n"
        "for name, module, method in json.loads(sys.argv[1]):\n"
        "    used = name in inspect.getsource(importlib.import_module(module))\n"
        "    defined = callable(getattr(AIAgent, name, None)) if method else True\n"
        "    if not (used and defined): missing.append(name)\n"
        "print(json.dumps(missing))\n"
    )
    home = work / "hooks-home"
    home.mkdir(mode=0o700)
    process = await asyncio.create_subprocess_exec(
        python, "-I", "-c", code, json.dumps(RUNNER_HOOKS), cwd=work,
        env={"PATH": "/usr/bin:/bin", "HOME": str(home), "HERMES_HOME": str(home)},
        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), HERMES_CHECK_TIMEOUT_S)
    except TimeoutError:
        process.kill()
        await process.wait()
        return ["(timeout)"]
    lines = stdout.decode("utf-8", "replace").strip().splitlines()
    try:
        return list(json.loads(lines[-1])) if lines else ["(sin salida)"]
    except ValueError:
        return ["(salida inválida)"]


async def preflight(args: argparse.Namespace, work: Path, report: Report) -> None:
    python = shutil.which(args.hermes_python)
    if not report.check(python is not None, "python del venv de Hermes", args.hermes_python):
        return
    assert python is not None
    commit = await venv_commit(python, work)
    if not report.check(commit == HERMES_COMMIT, "commit fijado, por hash", commit):
        return
    missing = await venv_missing_hooks(python, work)
    if not report.check(not missing, "ganchos privados del runner presentes en Hermes", ", ".join(missing)):
        return
    stub_script = Path(args.stub).resolve()
    if not report.check(stub_script.is_file(), "stub de desarrollo", str(stub_script)):
        return
    data_dir = work / "data"
    data_dir.mkdir(mode=0o700)
    scenarios = work / "scenarios"
    shutil.copytree(stub_script.parent / "scenarios", scenarios)
    write_scenario(scenarios)

    token = "preflight-" + os.urandom(16).hex()
    names = sorted({PROBE_TOOL, *args.tools})
    tools_port, stub_port = free_port(), free_port()
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
    mcp_server = uvicorn.Server(uvicorn.Config(
        build_probe_mcp(names, probe, token), host=BIND_HOST, port=tools_port, log_config=None,
        access_log=False, lifespan="on",
    ))
    mcp_task = asyncio.create_task(mcp_server.serve())
    settings = AgentSettings(
        _env_file=None,
        env="development",
        model_provider="dev_stub",
        model_name=args.model,
        dev_stub_url=f"http://{BIND_HOST}:{recorder.server_address[1]}",
        hermes_python=Path(python),
        anthropic_api_key=None,
    )
    tools_url = f"http://{BIND_HOST}:{tools_port}/mcp"
    supervisor = HermesSupervisor(settings, data_dir, names, token, tools_url, REPO_ROOT)
    # Where a wrong working directory would make Hermes look for context files (F21, H-15).
    canary_dir = data_dir / "hermes" / "user-home"
    canary_dir.mkdir(parents=True, mode=0o700)
    (data_dir / "hermes").chmod(0o700)
    (canary_dir / "AGENTS.md").write_text(CANARY, encoding="utf-8")
    try:
        await asyncio.sleep(0.5)
        await exercise(supervisor, recorder, probe, names, data_dir, token, report)
    finally:
        await supervisor.stop()
        mcp_server.should_exit = True
        await asyncio.gather(mcp_task, return_exceptions=True)
        recorder.shutdown()
        recorder.server_close()
        stub.terminate()
        await stub.wait()


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Comprueba la superficie real de herramientas de Hermes.")
    parser.add_argument("--stub", default=os.environ.get(
        "DRAKTER_DEV_STUB_SERVER", str(REPO_ROOT / "tools" / "dev-llm-stub" / "server.py")))
    parser.add_argument("--hermes-python", default=os.environ.get("DRAKTER_HERMES_PYTHON", "hermes-python"))
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
