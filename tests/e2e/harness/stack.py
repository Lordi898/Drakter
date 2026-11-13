"""Levanta y para backend, stub y Electron en un entorno aislado del usuario real."""
from __future__ import annotations

import json
import os
import secrets
import select
import shutil
import signal
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import hermes
from .http import Api, _OPENER

# Lista blanca: ni claves del entorno ni ELECTRON_RENDERER_URL llegan a los procesos.
INHERITED = ("PATH", "LANG", "LC_ALL", "TZ", "DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "TMPDIR")
BACKEND_TIMEOUT = 40
STUB_TIMEOUT = 15
STOP_TIMEOUT = 8


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@dataclass
class Layout:
    """Rutas de los componentes y del espacio de trabajo aislado de esta pasada."""
    root: Path
    work: Path
    backend_dir: Path
    desktop_dir: Path
    stub_dir: Path
    python: Path
    config: dict[str, Any]
    hermes_venv: Path | None = None


@dataclass
class Stack:
    layout: Layout
    procs: dict[str, subprocess.Popen] = field(default_factory=dict)
    logs: dict[str, Path] = field(default_factory=dict)
    state: dict[str, str] = field(default_factory=dict)  # componente -> "ok" o motivo
    failed: set[str] = field(default_factory=set)  # arrancó mal: FALLA, no NO COMPROBADO
    api: Api | None = None
    tokens: list[str] = field(default_factory=list)  # uno por arranque del backend
    stub_port: int = 0
    cdp_port: int = 0
    recorder: hermes.ToolRecorder | None = None
    headless: bool = False

    def __post_init__(self) -> None:
        work = self.layout.work
        self.home = work / "home"
        self.config_home = work / "xdg-config"
        self.data_dir = work / "data"
        self.sandbox = work / "sandbox"
        self.logs_dir = work / "logs"
        for path in (work, self.home, self.config_home, self.config_home / "drakter", self.data_dir,
                     work / "xdg-data", work / "xdg-cache", self.sandbox, self.logs_dir):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.chmod(0o700)

    # --- estado -----------------------------------------------------------------

    def available(self, name: str) -> bool:
        return self.state.get(name) == "ok"

    def why_unavailable(self, name: str) -> str:
        return self.state.get(name, "no se intentó arrancar")

    def _absent(self, name: str, reason: str) -> bool:
        self.state[name] = reason
        return False

    def _failed(self, name: str, reason: str) -> bool:
        self.failed.add(name)
        self.state[name] = reason
        return False

    # --- entorno ----------------------------------------------------------------

    def base_env(self) -> dict[str, str]:
        env = {key: os.environ[key] for key in INHERITED if key in os.environ}
        xauthority = Path(env.get("XAUTHORITY", Path.home() / ".Xauthority"))
        if "DISPLAY" in env and xauthority.is_file():
            env["XAUTHORITY"] = str(xauthority)  # HOME cambia: X no la encontraría
        work = self.layout.work
        env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.config_home),
                   XDG_DATA_HOME=str(work / "xdg-data"), XDG_CACHE_HOME=str(work / "xdg-cache"),
                   PYTHONDONTWRITEBYTECODE="1",
                   NO_PROXY="127.0.0.1,localhost")
        return env

    def write_env_file(self) -> None:
        """`.env` aislado de la pasada: es lo único que llega también al backend de Electron,
        cuyo host solo hereda una lista blanca de variables."""
        lines = {"DRAKTER_ENV": "development", "DRAKTER_DATA_DIR": str(self.data_dir),
                 "DRAKTER_LOG_LEVEL": "INFO"}
        if self.available("stub") and self.available("hermes"):
            values = {"stub_url": f"http://127.0.0.1:{self.recorder.port}",
                      "hermes_python": str(self.layout.hermes_venv / "bin" / "python")}
            for key, value in self.layout.config["backend_env_with_stub"].items():
                lines[key] = value.format(**values)
        path = self.config_home / "drakter" / ".env"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.writelines(f"{key}={value}\n" for key, value in lines.items())

    def backend_env(self) -> dict[str, str]:
        return self.base_env() | {"DRAKTER_DATA_DIR": str(self.data_dir)}

    # --- procesos ---------------------------------------------------------------

    def _spawn(self, name: str, argv: list[str], cwd: Path, env: dict[str, str],
               control: bool = False) -> subprocess.Popen:
        log_path = self.logs_dir / f"{name}.log"
        self.logs[name] = log_path
        with log_path.open("ab") as log:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, bufsize=0, start_new_session=True,
                                    stdin=subprocess.PIPE if control else subprocess.DEVNULL,
                                    stdout=subprocess.PIPE if control else log,
                                    stderr=log if control else subprocess.STDOUT)
        self.procs[name] = proc
        return proc

    def check_hermes(self) -> bool:
        """Preflight previo al backend: un Hermes incorrecto no llega a arrancarse."""
        venv = self.layout.hermes_venv
        if venv is None:
            return self._absent("hermes", "sin venv: usa --hermes-venv o DRAKTER_E2E_HERMES_VENV")
        if not venv.is_dir():
            return self._absent("hermes", f"no existe {venv}")
        found = hermes.problems(venv, self.layout.config["hermes"]["commit"], self.base_env())
        if found:
            return self._failed("hermes", "; ".join(found))
        if not (self.layout.backend_dir / hermes.RUNNER).is_file():
            return self._absent("hermes", f"el backend no incluye el runner {hermes.RUNNER}")
        self.state["hermes"] = "ok"
        return True

    def start_stub(self) -> bool:
        server = self.layout.stub_dir / "server.py"
        if not server.is_file():
            return self._absent("stub", f"no existe {server}")
        self.stub_port = free_port()
        env = self.base_env() | {"DRAKTER_ENV": "development"}
        proc = self._spawn("stub", ["python3", "-I", str(server), "--port", str(self.stub_port),
                                    "--var", f"sandbox={self.sandbox}"], self.layout.stub_dir, env)
        url = f"http://127.0.0.1:{self.stub_port}/health"
        deadline = time.monotonic() + STUB_TIMEOUT
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                return self._failed("stub", f"salió con código {proc.returncode}")
            try:
                with _OPENER.open(url, timeout=1) as reply:
                    if json.load(reply).get("dev_stub") is True:
                        self.recorder = hermes.ToolRecorder(self.stub_port)
                        self.state["stub"] = "ok"
                        return True
            except OSError:
                time.sleep(0.1)
        return self._failed("stub", f"sin /health tras {STUB_TIMEOUT} s")

    def start_backend(self) -> bool:
        if not (self.layout.backend_dir / "app" / "__main__.py").is_file():
            return self._absent("backend", f"no existe backend en {self.layout.backend_dir}")
        if not self.layout.python.is_file():
            return self._absent("backend", f"no existe {self.layout.python}")
        ui, approver = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.tokens += [ui, approver]
        proc = self._spawn("backend", [str(self.layout.python), "-m", "app"], self.layout.backend_dir,
                           self.backend_env(), control=True)
        # D-14: credenciales por stdin, que sigue abierto; su EOF apaga el backend.
        proc.stdin.write(json.dumps({"v": 1, "ui": ui, "approver": approver}).encode() + b"\n")
        try:
            port = self._announced_port(proc)
        except (TimeoutError, ValueError, KeyError) as exc:
            return self._failed("backend", f"sin anuncio de puerto: {exc}; ver backend.log")
        self.api = Api(port, ui, approver)
        if self.api.request("GET", "/health").status != 200:
            return self._failed("backend", "/health no responde 200")
        self.state["backend"] = "ok"
        return True

    @staticmethod
    def _announced_port(proc: subprocess.Popen) -> int:
        deadline = time.monotonic() + BACKEND_TIMEOUT
        line = b""
        while b"\n" not in line:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"{BACKEND_TIMEOUT} s")
            if select.select([proc.stdout], [], [], min(remaining, 0.5))[0]:
                chunk = proc.stdout.read(256)
                if not chunk:
                    raise ValueError(f"salió con código {proc.wait(5)}")
                line += chunk
        announced = json.loads(line)
        if announced["v"] != 1:
            raise ValueError(f"versión {announced['v']}")
        return int(announced["port"])

    def start_desktop(self) -> bool:
        desktop = self.layout.desktop_dir
        binary = desktop / "node_modules" / "electron" / "dist" / "electron"
        if not (desktop / "package.json").is_file():
            return self._absent("desktop", f"no existe escritorio en {desktop}")
        if not binary.is_file():
            return self._absent("desktop", "falta node_modules: cd desktop && npm ci")
        if not (desktop / "out" / "main" / "index.js").is_file():
            return self._absent("desktop", "falta desktop/out: npm run build o quita --no-build")
        if not (self.headless or os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return self._absent("desktop", "no hay sesión gráfica")
        self.cdp_port = free_port()
        # --no-sandbox SOLO en este arnés: chrome-sandbox no es SUID aquí y no hay sudo.
        # Nunca va en artefactos: el sandbox real queda sin probar y el informe lo avisa.
        argv = [str(binary), "--no-sandbox", f"--remote-debugging-port={self.cdp_port}",
                "--remote-debugging-address=127.0.0.1",
                f"--user-data-dir={self.layout.work / 'electron-profile'}", "--disable-gpu"]
        if self.headless:
            argv += ["--ozone-platform=headless", "--ozone-override-screen-size=1280,820"]
        argv.append(str(desktop))
        proc = self._spawn("desktop", argv, desktop, self.base_env() | {
            "DRAKTER_DATA_DIR": str(self.data_dir)})
        time.sleep(1)
        if proc.poll() is not None:
            return self._failed("desktop", f"salió con código {proc.returncode}; ver desktop.log")
        self.state["desktop"] = "ok"
        return True

    def stop(self, name: str) -> int | None:
        proc = self.procs.get(name)
        if proc is None:
            return None
        if proc.stdin is not None and not proc.stdin.closed:
            proc.stdin.close()  # EOF: apagado ordenado del backend (D-14)
            try:
                proc.wait(STOP_TIMEOUT)
            except subprocess.TimeoutExpired:
                pass
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(STOP_TIMEOUT)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(STOP_TIMEOUT)
            except ProcessLookupError:
                pass
        return proc.returncode

    def stop_all(self) -> dict[str, int | None]:
        # Electron primero: el backend debe sobrevivir a su cliente, no al revés.
        codes = {name: self.stop(name) for name in ("desktop", "backend", "stub")}
        if self.recorder is not None:
            self.recorder.shutdown()
            self.recorder.server_close()
            self.recorder = None
        return codes

    def backend_cli(self, *args: str) -> subprocess.CompletedProcess:
        """`python -m app.database.cli` contra la base aislada de esta pasada."""
        return subprocess.run([str(self.layout.python), "-m", "app.database.cli", *args],
                              cwd=self.layout.backend_dir, env=self.backend_env(), text=True,
                              capture_output=True, timeout=60, check=False)

    def stub_log(self) -> str:
        path = self.logs.get("stub")
        return path.read_text(errors="replace") if path and path.exists() else ""

    def remove_work(self) -> None:
        shutil.rmtree(self.layout.work, ignore_errors=True)
