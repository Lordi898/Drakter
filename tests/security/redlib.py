"""Núcleo del banco de ataques de Drakter. Solo biblioteca estándar.

Cada ataque intenta romper una garantía y termina en un veredicto:

- BLOCKED: el sistema resistió.
- BREACH: la garantía se rompió de verdad en esta ejecución.
- NOT_APPLICABLE: la pieza atacada todavía no existe; no prueba nada.
- ERROR: el propio ataque falló; tampoco prueba nada y hace fallar el banco.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_ORIGIN = "app://drakter"
START_TIMEOUT_SECONDS = 30.0


class Breach(Exception):
    """La garantía atacada no se ha sostenido."""


class NotApplicable(Exception):
    """La pieza atacada no existe en este objetivo."""


def expect(condition: object, message: str) -> None:
    if not condition:
        raise Breach(message)


@dataclass(frozen=True)
class Attack:
    id: str
    title: str
    guarantee: str
    run: Callable[["Context"], None]
    finding: str | None = None


ATTACKS: list[Attack] = []


def attack(
    attack_id: str, title: str, *, guarantee: str, finding: str | None = None
) -> Callable[[Callable[["Context"], None]], Callable[["Context"], None]]:
    def register(function: Callable[["Context"], None]) -> Callable[["Context"], None]:
        if any(item.id == attack_id for item in ATTACKS):
            raise ValueError(f"id de ataque repetido: {attack_id}")
        ATTACKS.append(Attack(attack_id, title, guarantee, function, finding))
        return function

    return register


@dataclass
class Response:
    status: int
    headers: list[tuple[str, str]]
    body: bytes

    def header(self, name: str) -> list[str]:
        return [value for key, value in self.headers if key.lower() == name.lower()]

    def json(self) -> Any:
        try:
            return json.loads(self.body)
        except ValueError:
            return None

    @property
    def error_code(self) -> str | None:
        payload = self.json()
        if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            code = payload["error"].get("code")
            return code if isinstance(code, str) else None
        return None


def _read_response(sock: socket.socket) -> Response:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(65536)
        if not chunk:
            break
        data += chunk
    head, _, body = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    if not lines or len(lines[0].split(" ")) < 2:
        return Response(0, [], data)
    status = int(lines[0].split(" ")[1])
    headers = [
        (name.strip(), value.strip())
        for name, _, value in (line.partition(":") for line in lines[1:])
    ]
    length = next((value for key, value in headers if key.lower() == "content-length"), None)
    if length is not None:
        while len(body) < int(length):
            chunk = sock.recv(65536)
            if not chunk:
                break
            body += chunk
    else:
        try:
            while chunk := sock.recv(65536):
                body += chunk
        except OSError:
            pass
    return Response(status, headers, body)


@dataclass
class Context:
    """Objetivo en marcha y utilidades que comparten todos los ataques."""

    backend_dir: Path
    root: Path
    data_dir: Path
    runtime_dir: Path
    port: int
    token: str
    approver_token: str
    session: dict[str, Any]
    stderr_path: Path
    contract: dict[str, Any]
    process: subprocess.Popen[bytes] | None = None
    scratch_count: int = field(default=0)

    @property
    def host(self) -> str:
        return f"127.0.0.1:{self.port}"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "drakter.db"

    def scratch(self) -> Path:
        """Directorio nuevo y vacío para el ataque, dentro de la raíz aislada."""
        self.scratch_count += 1
        path = self.root / f"scratch-{self.scratch_count}"
        path.mkdir(mode=0o700)
        return path

    def raw(self, payload: bytes, timeout: float = 5.0) -> Response:
        """Envía bytes tal cual, para probar lo que un cliente normal no permite."""
        with socket.create_connection(("127.0.0.1", self.port), timeout=timeout) as sock:
            sock.sendall(payload)
            return _read_response(sock)

    def http(
        self,
        method: str,
        path: str,
        *,
        headers: Iterable[tuple[str, str]] | None = None,
        body: bytes | None = None,
        json_body: object = None,
        token: str | None | bool = True,
        host: str | None = None,
        timeout: float = 5.0,
    ) -> Response:
        """`token=True` usa el de la sesión, `False` ninguno, y un texto ese valor."""
        lines = [f"{method} {path} HTTP/1.1", f"Host: {host or self.host}", "Connection: close"]
        if token is True:
            lines.append(f"Authorization: Bearer {self.token}")
        elif isinstance(token, str):
            lines.append(f"Authorization: Bearer {token}")
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            lines.append("Content-Type: application/json")
        if body is not None:
            lines.append(f"Content-Length: {len(body)}")
        lines.extend(f"{name}: {value}" for name, value in headers or ())
        payload = ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + (body or b"")
        return self.raw(payload, timeout)

    def ws_handshake(
        self,
        path: str = "/api/v1/events",
        *,
        headers: Iterable[tuple[str, str]] | None = None,
        host: str | None = None,
        timeout: float = 5.0,
    ) -> Response:
        """Handshake crudo: 101 es que el servidor aceptó la conexión."""
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        lines = [
            f"GET {path} HTTP/1.1",
            f"Host: {host or self.host}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            "Sec-WebSocket-Version: 13",
        ]
        lines.extend(f"{name}: {value}" for name, value in headers or ())
        payload = ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")
        with socket.create_connection(("127.0.0.1", self.port), timeout=timeout) as sock:
            sock.sendall(payload)
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
        head = data.partition(b"\r\n\r\n")[0].decode("latin-1").split("\r\n")
        parts = head[0].split(" ") if head else []
        status = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 0
        found = [
            (name.strip(), value.strip())
            for name, _, value in (line.partition(":") for line in head[1:])
        ]
        return Response(status, found, data)

    def route(self, name: str) -> str:
        """Ruta declarada en contract.py; sin declarar o sin servir, no es aplicable."""
        path = self.contract["routes"].get(name)
        if path is None:
            raise NotApplicable(f"ruta sin declarar en el contrato: {name}")
        probe = path.format(id="00000000-0000-4000-8000-000000000000")
        if self.http("OPTIONS", probe, token=True).status == 404:
            if self.http("GET", probe, token=True).error_code == "http_404":
                raise NotApplicable(f"ruta no servida por este objetivo: {path}")
        return path

    def logs_text(self) -> str:
        """Todo lo que el backend ha escrito hasta ahora: stderr y archivos de log."""
        chunks = [self.stderr_path.read_text("utf-8", "replace")]
        logs_dir = self.data_dir / "logs"
        if logs_dir.is_dir():
            chunks.extend(
                path.read_text("utf-8", "replace") for path in sorted(logs_dir.iterdir())
            )
        return "\n".join(chunks)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _isolated_root() -> Path:
    parent = os.environ.get("TMPDIR")
    if not parent or Path(parent).resolve() == Path("/tmp"):
        raise SystemExit("Define TMPDIR fuera de /tmp, por ejemplo /var/tmp/drakter-red")
    Path(parent).mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="redteam-", dir=parent))


def _read_announcement(process: subprocess.Popen[bytes], timeout: float) -> int:
    """Espera la línea `{"v":1,"port":N}` con la que el backend anuncia que está listo."""
    assert process.stdout is not None
    deadline = time.monotonic() + timeout
    line = b""
    while b"\n" not in line:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("el backend no anunció su puerto a tiempo")
        if select.select([process.stdout], [], [], remaining)[0]:
            chunk = os.read(process.stdout.fileno(), 4096)
            if not chunk:
                raise RuntimeError(f"el backend salió sin anunciar puerto: {process.wait(5)}")
            line += chunk
    return int(json.loads(line)["port"])


def start_target(backend_dir: Path, python: str, contract: dict[str, Any]) -> Context:
    """Arranca `python -m app` como lo hace Electron main (D-14), en una raíz nueva.

    Los tokens se entregan por stdin y el puerto llega por stdout; stdin queda
    abierto porque su cierre apaga el backend. HOME y XDG_CONFIG_HOME apuntan a
    esa raíz: el banco no puede leer la configuración ni los secretos reales.
    """
    root = _isolated_root()
    data_dir, runtime_dir = root / "data", root / "runtime"
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "HOME": str(root / "home"),
        "XDG_CONFIG_HOME": str(root / "config"),
        "XDG_DATA_HOME": str(root / "xdg-data"),
        "XDG_RUNTIME_DIR": str(root / "xdg-runtime"),
        "TMPDIR": str(root),
        "DRAKTER_DATA_DIR": str(data_dir),
        "DRAKTER_RUNTIME_DIR": str(runtime_dir),
        "DRAKTER_LOG_LEVEL": "DEBUG",
        **contract.get("env", {}),
    }
    (root / "home").mkdir(mode=0o700)
    ui_token, approver_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    stderr_path = root / "stderr.log"
    with open(stderr_path, "wb") as stderr:
        process = subprocess.Popen(
            [python, "-m", "app"],
            cwd=backend_dir,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            start_new_session=True,
        )
    assert process.stdin is not None
    try:
        handshake = {"v": 1, "ui": ui_token, "approver": approver_token}
        process.stdin.write(json.dumps(handshake).encode("ascii") + b"\n")
        process.stdin.flush()
        port = _read_announcement(process, START_TIMEOUT_SECONDS)
    except BaseException:
        stop_target(process)
        raise
    return Context(
        backend_dir=backend_dir,
        root=root,
        data_dir=data_dir,
        runtime_dir=runtime_dir,
        port=port,
        token=ui_token,
        approver_token=approver_token,
        session={"token": ui_token, "approver_token": approver_token, "port": port},
        stderr_path=stderr_path,
        contract=contract,
        process=process,
    )


def stop_target(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(5)


def cleanup(context: Context) -> None:
    if context.process is not None:
        stop_target(context.process)
    shutil.rmtree(context.root, ignore_errors=True)


def run_attacks(context: Context, attacks: Iterable[Attack]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in attacks:
        try:
            item.run(context)
            verdict, detail = "BLOCKED", ""
        except Breach as exc:
            verdict, detail = "BREACH", str(exc)
        except NotApplicable as exc:
            verdict, detail = "NOT_APPLICABLE", str(exc)
        except Exception:  # noqa: BLE001 - un ataque roto no debe parar el banco
            verdict, detail = "ERROR", traceback.format_exc(limit=4)
        # El token real nunca sale del banco, ni siquiera en el informe.
        detail = detail.replace(context.token, "[TOKEN]")
        detail = detail.replace(context.approver_token, "[APPROVER_TOKEN]")
        results.append(
            {
                "id": item.id,
                "title": item.title,
                "guarantee": item.guarantee,
                "finding": item.finding,
                "verdict": verdict,
                "detail": detail,
            }
        )
        print(f"{verdict:<14} {item.id:<10} {item.title}" + (f"\n    {detail}" if detail else ""))
        sys.stdout.flush()
    return results
