#!/usr/bin/env python3
"""Comprobacion de seguridad del backend (D-14) contra un servidor real (`python -m app`).

Escrita a partir de backend/CONTRACT.md. Uso (desde backend/):
    TMPDIR=/var/tmp/drakter-8 .venv/bin/python tests/check_security.py
El puerto lo elige el servidor (127.0.0.1:0). Sale != 0 si algo falla.
Todo el estado (config, datos, runtime, HOME) va a un directorio temporal nuevo.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
RESULTS: list[tuple[bool, str]] = []
ALL_RESPONSE_HEADERS: list[tuple[str, str]] = []
STATE_FLAGS: dict[str, bool] = {}


def check(name: str, cond: bool, detail: str = "") -> bool:
    RESULTS.append((bool(cond), name))
    print(f"{'OK  ' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not cond else ""), flush=True)
    return bool(cond)


# ---------------------------------------------------------------- HTTP crudo
class Resp:
    def __init__(self, status: int, headers: list[tuple[str, str]], body: bytes):
        self.status, self.headers, self.body = status, headers, body

    def h(self, name: str) -> list[str]:
        return [v for k, v in self.headers if k.lower() == name.lower()]

    def json(self):
        try:
            return json.loads(self.body)
        except Exception:  # noqa: BLE001
            return None

    def error_code(self) -> str | None:
        j = self.json()
        return j["error"].get("code") if isinstance(j, dict) and isinstance(j.get("error"), dict) else None

    def envelope(self, code: str | None = None) -> bool:
        j = self.json()
        if not (isinstance(j, dict) and set(j) == {"error"} and isinstance(j["error"], dict)):
            return False
        e = j["error"]
        ok = set(e) == {"code", "message", "request_id", "details"} and isinstance(e["details"], list)
        ok = ok and all(isinstance(e[k], str) and e[k] for k in ("code", "message", "request_id"))
        ok = ok and any("application/json" in v for v in self.h("content-type"))
        return ok and (code is None or e["code"] == code)


def raw_request(port: int, method: str, path: str, *, host="default", headers=None, token: str | None = None,
                body: bytes = b"", declared_len: int | None = None, chunks=None, timeout: float = 5.0) -> Resp:
    lines = [f"{method} {path} HTTP/1.1"]
    hosts = [f"127.0.0.1:{port}"] if host == "default" else ([] if host is None else ([host] if isinstance(host, str) else host))
    lines += [f"Host: {h}" for h in hosts]
    if token is not None:
        lines.append(f"Authorization: Bearer {token}")
    hdrs = list(headers or [])
    lines += [f"{k}: {v}" for k, v in hdrs]
    if chunks is not None:
        lines.append("Transfer-Encoding: chunked")
    elif body or declared_len is not None:
        lines.append(f"Content-Length: {declared_len if declared_len is not None else len(body)}")
    if not any(k.lower() == "upgrade" for k, _ in hdrs):
        lines.append("Connection: close")
    data = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8") + (body if chunks is None else b"")
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    buf = b""
    try:
        try:
            s.sendall(data)
            if chunks is not None:
                for c in chunks:
                    s.sendall(f"{len(c):x}\r\n".encode() + c + b"\r\n")
                s.sendall(b"0\r\n\r\n")
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass
        while True:
            if b"\r\n\r\n" in buf:
                head, _, rest = buf.partition(b"\r\n\r\n")
                if head.split(b" ", 2)[1] == b"101":
                    break
                cl = [int(l.split(b":", 1)[1]) for l in head.split(b"\r\n")[1:] if l.lower().startswith(b"content-length:")]
                if cl and len(rest) >= cl[0]:
                    break
            try:
                chunk = s.recv(65536)
            except (socket.timeout, ConnectionResetError):
                break
            if not chunk:
                break
            buf += chunk
    finally:
        s.close()
    head, _, rbody = buf.partition(b"\r\n\r\n")
    hl = head.decode("latin-1").split("\r\n")
    if not hl or not hl[0].startswith("HTTP/"):
        return Resp(0, [], buf)
    parsed = []
    for x in hl[1:]:
        if ":" in x:
            k, v = x.split(":", 1)
            parsed.append((k.strip(), v.strip()))
    ALL_RESPONSE_HEADERS.extend(parsed)
    return Resp(int(hl[0].split()[1]), parsed, rbody)


def ws_handshake_raw(port: int, path: str = "/api/v1/events", *, host="default", token: str | None = None,
                     headers=None) -> Resp:
    key = base64.b64encode(os.urandom(16)).decode()
    h = [("Upgrade", "websocket"), ("Connection", "Upgrade"), ("Sec-WebSocket-Version", "13"),
         ("Sec-WebSocket-Key", key)] + list(headers or [])
    return raw_request(port, "GET", path, host=host, headers=h, token=token)


# ---------------------------------------------------------------- proceso
class Backend:
    """Un `python -m app` real con stdin/stdout/stderr en pipes."""

    def __init__(self, root: Path, name: str, creds: dict[str, str], data_dir: Path | None = None):
        self.root, self.name, self.creds = root, name, creds
        root.mkdir(parents=True, exist_ok=True)
        self.config, self.run = root / "config", root / "run"
        self.xdg_data = root / "xdg-data"
        for d in (self.config, self.run, self.xdg_data):
            d.mkdir(mode=0o700, exist_ok=True)
        (root / "home").mkdir(exist_ok=True)
        self.data_dir = data_dir or (self.xdg_data / "drakter")
        self.proc: subprocess.Popen | None = None
        self.port: int | None = None
        self.out, self.err = bytearray(), bytearray()
        self.stdout_ino = self.stderr_ino = 0

    def env(self) -> dict[str, str]:
        e = {k: v for k, v in os.environ.items() if not k.startswith("DRAKTER_")
             and k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}
        e.update(XDG_CONFIG_HOME=str(self.config), XDG_DATA_HOME=str(self.xdg_data),
                 XDG_RUNTIME_DIR=str(self.run), HOME=str(self.root / "home"), PYTHONUNBUFFERED="1")
        if self.data_dir != self.xdg_data / "drakter":
            e["DRAKTER_DATA_DIR"] = str(self.data_dir)
        return e

    def launch(self, line: bytes | None, *, close_stdin: bool = False) -> "Backend":
        self.proc = subprocess.Popen([sys.executable, "-m", "app"], cwd=BACKEND, env=self.env(),
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.stdout_ino = os.fstat(self.proc.stdout.fileno()).st_ino
        self.stderr_ino = os.fstat(self.proc.stderr.fileno()).st_ino
        for stream, buf in ((self.proc.stdout, self.out), (self.proc.stderr, self.err)):
            threading.Thread(target=self._drain, args=(stream, buf), daemon=True).start()
        try:
            if line is not None:
                self.proc.stdin.write(line)
                self.proc.stdin.flush()
            if close_stdin:
                self.proc.stdin.close()
        except BrokenPipeError:
            pass
        return self

    @staticmethod
    def _drain(stream, buf: bytearray) -> None:
        try:
            while True:
                c = os.read(stream.fileno(), 65536)
                if not c:
                    return
                buf.extend(c)
        except OSError:
            return

    def handshake_line(self, **over) -> bytes:
        d = {"v": 1, "ui": self.creds["ui"], "approver": self.creds["approver"]}
        d.update(over)
        return (json.dumps(d, separators=(",", ":")) + "\n").encode()

    def wait_port(self, timeout: float = 30.0) -> int:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if b"\n" in self.out:
                msg = json.loads(bytes(self.out).split(b"\n", 1)[0])
                self.port = int(msg["port"])
                return self.port
            if self.proc.poll() is not None:
                time.sleep(0.3)
                if b"\n" in self.out:
                    continue
                raise RuntimeError(f"{self.name}: termino sin anunciar puerto (codigo {self.proc.returncode}); "
                                   f"stderr={bytes(self.err)[-1500:]!r}")
            time.sleep(0.1)
        raise RuntimeError(f"{self.name}: no anuncio puerto en {timeout:.0f} s; stderr={bytes(self.err)[-1500:]!r}")

    def start_ok(self) -> "Backend":
        self.launch(self.handshake_line())
        self.wait_port()
        return self

    def stop_stdin(self, timeout: float = 15.0) -> int | None:
        try:
            self.proc.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        return self._wait(timeout)

    def sigterm(self, timeout: float = 15.0) -> int | None:
        self.proc.send_signal(signal.SIGTERM)
        return self._wait(timeout)

    def _wait(self, timeout: float) -> int | None:
        try:
            return self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            return None

    def kill(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()

    @property
    def logfile(self) -> Path:
        return self.data_dir / "logs" / "backend.log"

    def alive_and_healthy(self) -> bool:
        try:
            return self.proc.poll() is None and raw_request(self.port, "GET", "/health", token=self.creds["ui"], timeout=3).status == 200
        except OSError:
            return False


def mode(p: Path) -> int:
    return stat.S_IMODE(p.stat().st_mode)


def tree_contains(root: Path, needles: list[bytes]) -> list[str]:
    hits = []
    for p in root.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                data = p.read_bytes()
                if any(n in data for n in needles):
                    hits.append(str(p.relative_to(root)))
        except OSError:
            continue
    return hits


# ---------------------------------------------------------------- handshake
def handshake_cases(root: Path, creds: dict[str, str]) -> None:
    canary = "CANARYECHO" + secrets.token_hex(4)
    good = {"ui": creds["ui"], "approver": creds["approver"]}
    t1, t2 = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    cases = {
        "JSON roto": (f'{{"v":1,"ui":"{canary}\n'.encode(), [canary]),
        "v incorrecto": ((json.dumps({"v": 2, "ui": t1, "approver": t2}) + "\n").encode(), [t1, t2]),
        "token corto": ((json.dumps({"v": 1, "ui": canary, "approver": t2}) + "\n").encode(), [canary, t2]),
        "tokens iguales": ((json.dumps({"v": 1, "ui": t1, "approver": t1}) + "\n").encode(), [t1]),
        "linea de mas de 4 KiB": ((f'{{"v":1,"ui":"{canary}' + "A" * 5000 + '"}\n').encode(), [canary]),
        "EOF inmediato": (None, []),
    }
    _ = good
    for label, (line, secrets_) in cases.items():
        b = Backend(root / f"hs-{abs(hash(label))}", label, creds)
        try:
            b.launch(line, close_stdin=(line is None))
            rc = b._wait(20)
            time.sleep(0.2)
            leaked = [s for s in secrets_ if s.encode() in bytes(b.err) or s.encode() in bytes(b.out)]
            check(f"handshake invalido ({label}): codigo 2, sin puerto ni eco",
                  rc == 2 and b"\n" not in b.out and not b.out and not leaked,
                  f"rc={rc} out={bytes(b.out)[:100]!r} eco={leaked} err={bytes(b.err)[:200]!r}")
        finally:
            b.kill()


# ---------------------------------------------------------------- HTTP
def http_cases(be: Backend, agent: str) -> None:
    port, ui, ap = be.port, be.creds["ui"], be.creds["approver"]
    R = lambda *a, **k: raw_request(port, *a, **k)  # noqa: E731

    # Matriz basica: /health y auth/check
    for path in ("/health", "/api/v1/auth/check"):
        r = R("GET", path)
        check(f"{path} sin token: 401 unauthorized con envelope y WWW-Authenticate",
              r.status == 401 and r.envelope("unauthorized") and r.h("www-authenticate") == ["Bearer"], f"{r.status} {r.body[:100]!r}")
        r = R("GET", path, token=ui)
        want = {"/health": {"status": "ok"}, "/api/v1/auth/check": {"authenticated": True}}[path]
        check(f"{path} con ui: 200 {want}", r.status == 200 and r.json() == want, f"{r.status} {r.body[:100]!r}")
        r = R("GET", path, token=ap)
        check(f"{path} con approver: 403 permission_denied", r.status == 403 and r.envelope("permission_denied"), f"{r.status} {r.body[:100]!r}")
        r = R("GET", path, token=agent)
        check(f"{path} con tercer token (agent): 401", r.status == 401 and r.envelope("unauthorized"), f"{r.status}")
    r = R("GET", "/health", token=ui)
    check("/health: sin cabecera Server ni token en la respuesta",
          not r.h("server") and ui.encode() not in r.body and all(ui not in v for _, v in r.headers), repr(r.headers))
    r = R("GET", f"/health?token={ui}")
    check("?token= no autentica", r.status == 401, f"{r.status}")
    r = R("GET", "/health", headers=[("Authorization", f"Basic {ui}")])
    check("esquema Basic con el token correcto: 401", r.status == 401, f"{r.status}")
    r = R("GET", "/health", headers=[("Authorization", "Bearer tókén-中文")])
    check("token no ASCII: 401 (no 500)", r.status == 401 and r.envelope("unauthorized"), f"{r.status}")
    r = R("GET", "/health", headers=[("Authorization", f"Bearer {ui}"), ("Authorization", f"Bearer {ui}")])
    check("dos cabeceras Authorization (ambas validas): 401", r.status == 401, f"{r.status}")
    r = R("GET", "/health", headers=[("Cookie", f"token={ui}")])
    check("cookie con el token no autentica", r.status == 401, f"{r.status}")

    # Rutas inexistentes / docs
    r = R("GET", "/no/existe")
    check("ruta inexistente sin token: 401", r.status == 401, f"{r.status}")
    r = R("GET", "/no/existe", token=ui)
    check("ruta inexistente con ui: 404 http_404 con envelope", r.status == 404 and r.envelope("http_404"), f"{r.status} {r.body[:100]!r}")
    for p in ("/docs", "/redoc", "/openapi.json"):
        r = R("GET", p, token=ui)
        check(f"{p} con ui: 404 http_404", r.status == 404 and r.envelope("http_404"), f"{r.status}")
        check(f"{p} sin token: 401", R("GET", p).status == 401)
    r = R("GET", "/health/", token=ui)
    check("barra final en /health (redirect_slashes=False): 404 sin redireccion", r.status == 404 and not r.h("location"), f"{r.status}")

    # Matriz de roles protegidos
    protected = []
    for p in ("/api/v1/confirmations/x/approve", "/api/v1/confirmations/x/reject"):
        protected.append(("POST", p))
    for base in ("/api/v1/storage-locations", "/api/v1/storage-locations/x", "/api/v1/permissions", "/api/v1/permissions/x"):
        for m in ("POST", "PATCH", "DELETE"):
            protected.append((m, base))
    for m, p in protected:
        a, b, c = R(m, p), R(m, p, token=ui), R(m, p, token=ap)
        d = R(m, p, token=agent)
        # Con las rutas ya montadas, "pasa el guardia" es cualquier respuesta que no sea suya.
        check(f"{m} {p}: sin token 401, ui 403 permission_denied, approver pasa el guardia, agent 401",
              a.status == 401 and b.status == 403 and b.envelope("permission_denied")
              and c.status not in (401, 403) and d.status == 401,
              f"none={a.status} ui={b.status} approver={c.status}/{c.error_code()} agent={d.status}")
    r = R("GET", "/api/v1/storage-locations", token=ui)
    check("GET /api/v1/storage-locations con ui pasa el guardia", r.status not in (401, 403), f"{r.status}")
    r = R("GET", "/api/v1/storage-locations", token=ap)
    check("GET /api/v1/storage-locations con approver: 403 permission_denied", r.status == 403 and r.envelope("permission_denied"), f"{r.status}")
    r = R("GET", "/api/v1/confirmations/x/approve", token=ui)
    check("GET /api/v1/confirmations/x/approve con ui (cualquier metodo): 403", r.status == 403, f"{r.status}")

    # Variantes de ruta que no deben rodear el rol
    variants = [
        ("POST", "/api/v1/confirmations/x/approve/"), ("POST", "/api/v1/confirmations/x/reject/"),
        ("POST", "/api/v1/confirmations//approve"), ("POST", "/api/v1/confirmations/x//approve"),
        ("POST", "/api/v1/confirmations/x%2fapprove"), ("POST", "/api/v1/confirmations/x/%61pprove"),
        ("POST", "/api/v1/confirmations%2fx/approve"),
        ("POST", "/api/v1/storage-locations/"), ("POST", "/api/v1/storage-locations//x"),
        ("POST", "/api/v1/storage-locations%2fx"), ("POST", "/api/v1/%73torage-locations"),
        ("DELETE", "/api/v1/storage-locations/x/"), ("PATCH", "/api/v1/permissions/"),
        ("PATCH", "/api/v1/permissions%2fx"), ("DELETE", "/api/v1/permissions//x"),
        ("POST", "/api/v1//permissions"), ("POST", "//api/v1/permissions"),
    ]
    for m, p in variants:
        b = R(m, p, token=ui)
        c = R(m, p, token=ap)
        check(f"variante {m} {p}: ui 403 (no rodea el rol) y approver no recibe 2xx",
              b.status == 403 and c.status not in range(200, 300), f"ui={b.status} approver={c.status}")

    # Host y Origin con token ui valido
    for label, host in (("localhost", f"localhost:{port}"), ("evil.com", f"evil.com:{port}"),
                        ("otro puerto", f"127.0.0.1:{port + 1}"), ("sin puerto", "127.0.0.1")):
        r = R("GET", "/health", host=host, token=ui)
        check(f"Host {label} con ui: 403 forbidden_host", r.status == 403 and r.envelope("forbidden_host"), f"{r.status} {r.body[:100]!r}")
    r = R("GET", "/health", host=None, token=ui)
    check("sin Host: rechazado (400/403)", r.status in (400, 403), f"{r.status}")
    r = R("GET", "/health", host=[f"127.0.0.1:{port}", f"127.0.0.1:{port}"], token=ui)
    check("dos Host identicos: rechazado (400/403)", r.status in (400, 403), f"{r.status}")
    r = R("GET", "/health", host=[f"127.0.0.1:{port}", f"evil.com:{port}"], token=ui)
    check("dos Host (valido + falso): rechazado (400/403)", r.status in (400, 403), f"{r.status}")
    for ov in ("app://drakter", "null", "http://evil.com", f"http://127.0.0.1:{port}", ""):
        r = R("GET", "/health", token=ui, headers=[("Origin", ov)])
        check(f"Origin {ov!r} con ui: 403 forbidden_origin", r.status == 403 and r.envelope("forbidden_origin"), f"{r.status} {r.body[:100]!r}")
    r = R("GET", "/health", token=ui, headers=[("Origin", "app://drakter"), ("Origin", "app://drakter")])
    check("dos Origin: 403", r.status == 403, f"{r.status}")
    for ov in ("app://drakter", "http://evil.com", "null"):
        for tok in (None, ui):
            r = R("OPTIONS", "/health", token=tok, headers=[("Origin", ov), ("Access-Control-Request-Method", "GET"),
                                                          ("Access-Control-Request-Headers", "authorization")])
            check(f"preflight OPTIONS Origin {ov!r} ({'con ui' if tok else 'sin token'}): 403 forbidden_origin",
                  r.status == 403 and r.envelope("forbidden_origin"), f"{r.status}")
    r = R("OPTIONS", "/health", headers=[("Access-Control-Request-Method", "GET")])
    check("OPTIONS sin Origin ni token: 401 (sin excepcion de preflight)", r.status == 401, f"{r.status}")

    # Cuerpo
    r = R("POST", "/api/v1/auth/check", token=ui, declared_len=1048577)
    check("Content-Length 1 MiB + 1: 413 file_too_large", r.status == 413 and r.envelope("file_too_large"), f"{r.status} {r.body[:100]!r}")
    chunk = b"a" * 65536
    r = R("POST", "/api/v1/auth/check", token=ui, chunks=[chunk] * 17, timeout=10)
    # Ninguna ruta de esta base lee cuerpos: el 405 sale antes de leerlo. El 413 en streaming
    # de una ruta que lee el cuerpo se comprueba en la integracion con rutas reales.
    check("chunked > 1 MiB sobre ruta sin cuerpo no llega a 200", r.status in (405, 413), f"{r.status} {r.body[:100]!r}")
    r = R("GET", "/health", token=ui)
    check("servidor sigue respondiendo tras el chunked excedido", r.status == 200, f"{r.status}")
    r = R("POST", "/api/v1/auth/check", token=ui, body=b"a" * 1048576, timeout=10)
    check("cuerpo de exactamente 1 MiB: no da 413", r.status != 413 and r.status != 0, f"{r.status}")
    r = R("POST", "/api/v1/auth/check", token=ui, chunks=[chunk] * 16, timeout=10)
    check("chunked de exactamente 1 MiB: no da 413", r.status != 413 and r.status != 0, f"{r.status}")
    r = R("POST", "/api/v1/storage-locations", token=ui, declared_len=1048577)
    check("cuerpo enorme con ui en ruta protegida: no pasa (403 o 413)", r.status in (403, 413), f"{r.status}")
    r = R("GET", "/health", token=ui)
    check("servidor sigue respondiendo tras los cuerpos de prueba", r.status == 200, f"{r.status}")


# ---------------------------------------------------------------- WS
def ws_cases(be: Backend, agent: str) -> None:
    from websockets.asyncio.client import connect
    from websockets.exceptions import ConnectionClosed, InvalidStatus

    port, ui, ap = be.port, be.creds["ui"], be.creds["approver"]
    base = f"ws://127.0.0.1:{port}/api/v1/events"
    auth = {"Authorization": f"Bearer {ui}"}

    async def dial(uri=base, **kw):
        return await connect(uri, proxy=None, open_timeout=5, **kw)

    async def outcome(uri=base, **kw) -> str:
        try:
            ws = await dial(uri, **kw)
        except InvalidStatus as e:
            return f"HTTP {e.response.status_code}"
        except Exception as e:  # noqa: BLE001
            return f"ERR {type(e).__name__}: {e}"
        await ws.close()
        return "OPEN"

    async def main() -> None:
        try:
            async with await dial(additional_headers=auth) as ws:
                sp = ws.subprotocol
            ctl = check("WS control: ui conecta sin subprotocolo (subprotocolo None)", sp is None, repr(sp))
        except Exception as e:  # noqa: BLE001
            ctl = check("WS control: ui conecta sin subprotocolo (subprotocolo None)", False, repr(e))
        try:
            async with await dial(additional_headers=auth, subprotocols=["drakter.v1"]) as ws:
                sp = ws.subprotocol
            check("WS ofreciendo drakter.v1 lo devuelve", sp == "drakter.v1", repr(sp))
        except Exception as e:  # noqa: BLE001
            check("WS ofreciendo drakter.v1 lo devuelve", False, repr(e))
        res = await outcome(f"{base}?after_seq=0&boot_id={uuid.uuid4()}", additional_headers=auth)
        check("WS con ?after_seq=0&boot_id=<uuid> conecta", res == "OPEN", res)

        # after_seq=-1: no queda abierto
        try:
            ws = await dial(f"{base}?after_seq=-1", additional_headers=auth)
            try:
                await asyncio.wait_for(ws.recv(), 3)
                state = "recibio datos"
            except ConnectionClosed:
                state = "closed"
            except asyncio.TimeoutError:
                state = "ABIERTO"
            await ws.close()
        except InvalidStatus as e:
            state = f"closed (HTTP {e.response.status_code})"
        except Exception as e:  # noqa: BLE001
            state = f"ERR {e!r}"
        check("WS con after_seq=-1 no queda abierto", state.startswith("closed"), state)

        def rej(name: str, res: str) -> None:
            check(name, ctl and res in ("HTTP 401", "HTTP 403"), res if ctl else f"{res} (control fallido: no valido)")

        rej("WS sin token rechazado en handshake", await outcome())
        rej("WS con token ui en query rechazado", await outcome(f"{base}?token={ui}"))
        rej("WS con drakter.auth.<ui> como subprotocolo, sin Authorization, rechazado",
            await outcome(subprotocols=["drakter.v1", f"drakter.auth.{ui}"]))
        rej("WS con token approver rechazado", await outcome(additional_headers={"Authorization": f"Bearer {ap}"}))
        rej("WS con tercer token rechazado", await outcome(additional_headers={"Authorization": f"Bearer {agent}"}))
        rej("WS con Origin falso (token ui) rechazado", await outcome(additional_headers=auth, origin="http://evil.com"))
        rej("WS con Origin app://drakter (token ui) rechazado", await outcome(additional_headers=auth, origin="app://drakter"))

        good = ws_handshake_raw(port, token=ui)
        check("WS crudo con Host correcto y ui: 101 (control)", good.status == 101, f"{good.status}")
        for label, host in (("evil.com", f"evil.com:{port}"), ("otro puerto", f"127.0.0.1:{port + 1}"), ("localhost", f"localhost:{port}")):
            r = ws_handshake_raw(port, host=host, token=ui)
            check(f"WS con Host falso ({label}) y ui rechazado", good.status == 101 and r.status == 403, f"{r.status}")
        r = ws_handshake_raw(port, token=ui, headers=[("Origin", "null")])
        check("WS con Origin: null y ui rechazado", good.status == 101 and r.status == 403, f"{r.status}")

        # /ws antiguo
        res = await outcome(f"ws://127.0.0.1:{port}/ws", additional_headers=auth)
        check("/ws ya no acepta conexion (control: /api/v1/events si)", ctl and res != "OPEN" and res.startswith("HTTP "), res)

        # mensaje entrante -> 1003
        for label, payload in (("texto", "hola"), ("binario", b"\x00\x01")):
            try:
                async with await dial(additional_headers=auth) as ws:
                    await ws.send(payload)
                    try:
                        await asyncio.wait_for(ws.recv(), 5)
                        code = "respuesta inesperada"
                    except ConnectionClosed as e:
                        code = e.rcvd.code if e.rcvd else None
                check(f"WS mensaje entrante ({label}) cierra con 1003", code == 1003, repr(code))
            except Exception as e:  # noqa: BLE001
                check(f"WS mensaje entrante ({label}) cierra con 1003", False, repr(e))
        # trama > 1 MiB -> 1009
        try:
            async with await dial(additional_headers=auth) as ws:
                code = None
                try:
                    await ws.send(b"a" * (1048576 + 1))
                    await asyncio.wait_for(ws.recv(), 10)
                    code = "respuesta inesperada"
                except ConnectionClosed as e:
                    code = e.rcvd.code if e.rcvd else None
                except asyncio.TimeoutError:
                    code = "timeout (conexion abierta)"
            check("WS trama de mas de 1 MiB cierra con 1009", code == 1009, repr(code))
        except Exception as e:  # noqa: BLE001
            check("WS trama de mas de 1 MiB cierra con 1009", False, repr(e))

    asyncio.run(main())


# ---------------------------------------------------------------- sistema
def system_cases(be: Backend, tokens: list[str], root: Path) -> None:
    port, pid = be.port, be.proc.pid
    nb = [t.encode() for t in tokens]
    ss = subprocess.run(["ss", "-ltnpH"], capture_output=True, text=True).stdout.splitlines()
    mine = [l.split()[3] for l in ss if len(l.split()) > 3 and l.split()[3].rsplit(":", 1)[-1] == str(port)]
    check("ss -ltn: el puerto solo escucha en 127.0.0.1", bool(mine) and all(a == f"127.0.0.1:{port}" for a in mine), repr(mine))
    own = [l.split()[3] for l in ss if f"pid={pid}," in l or f"pid={pid})" in l]
    # El servidor de herramientas del agente abre un segundo puerto efímero, también en loopback.
    check("ss -ltnp: todos los listeners del proceso están en 127.0.0.1", bool(own) and all(a.startswith("127.0.0.1:") for a in own), repr(own))
    check("puerto anunciado dentro de 1024..65535", 1024 <= port <= 65535, str(port))

    fd0 = os.readlink(f"/proc/{pid}/fd/0")
    fd1 = os.readlink(f"/proc/{pid}/fd/1")
    check("fd 0 del proceso apunta a /dev/null", fd0 == "/dev/null", fd0)
    check("fd 1 del proceso no es el pipe de stdout", fd1 != f"pipe:[{be.stdout_ino}]", fd1)
    check("fd 1 del proceso apunta a stderr (pipe de stderr)", fd1 == f"pipe:[{be.stderr_ino}]", fd1)
    check("stdout contiene exactamente la linea {\"v\":1,\"port\":N} y nada mas",
          bytes(be.out) == (json.dumps({"v": 1, "port": port}, separators=(",", ":")) + "\n").encode()
          or (json.loads(bytes(be.out).split(b"\n", 1)[0]) == {"v": 1, "port": port}
              and bytes(be.out).count(b"\n") == 1 and bytes(be.out).endswith(b"\n")), repr(bytes(be.out)[:200]))
    check("el token no esta en /proc/<pid>/cmdline ni /proc/<pid>/environ",
          not any(t in Path(f"/proc/{pid}/cmdline").read_bytes() or t in Path(f"/proc/{pid}/environ").read_bytes() for t in nb))
    check("los hijos no heredan nada: ningun otro proceso hijo con el token",
          not any(t in _children_cmd(pid) for t in nb))
    check("no existe session.json en ningun sitio", not list(root.rglob("session.json")))
    log = be.logfile.read_bytes() if be.logfile.exists() else b""
    check("backend.log existe con permisos 600 y no esta vacio", be.logfile.exists() and mode(be.logfile) == 0o600 and len(log) > 0,
          oct(mode(be.logfile)) if be.logfile.exists() else "no existe")
    check("directorio de datos 700", mode(be.data_dir) == 0o700, oct(mode(be.data_dir)))
    db = be.data_dir / "drakter.db"
    check("drakter.db con permisos 600", db.exists() and mode(db) == 0o600, oct(mode(db)) if db.exists() else "no existe")
    for n in ("drakter.db-wal", "drakter.db-shm"):
        p = be.data_dir / n
        if p.exists():
            check(f"{n} con permisos 600", mode(p) == 0o600, oct(mode(p)))
    check("los tokens no aparecen en backend.log", not any(t in log for t in nb))
    check("los tokens no aparecen en stderr", not any(t in bytes(be.err) for t in nb))
    check("los tokens no aparecen en stdout", not any(t in bytes(be.out) for t in nb))
    hits = tree_contains(root, nb)
    check("los tokens no aparecen en ningun archivo bajo el directorio temporal", not hits, repr(hits))


def _safe_readlink(p: str):
    try:
        return os.readlink(p)
    except OSError:
        return None


def _children_cmd(pid: int) -> bytes:
    out = b""
    try:
        r = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout.split()
        for c in r:
            out += Path(f"/proc/{c}/cmdline").read_bytes() + Path(f"/proc/{c}/environ").read_bytes()
    except OSError:
        pass
    return out


def log_cases(be: Backend, tokens: list[str]) -> None:
    port, ui = be.port, be.creds["ui"]
    marker = "query-marker-" + secrets.token_hex(6)
    marker2 = "query-marker-" + secrets.token_hex(6)
    badtok = "BADTOKEN-CANARY-" + secrets.token_hex(6)
    r = raw_request(port, "GET", f"/health?{marker}", token=ui)
    check("control de logs: /health?marker con ui responde 200", r.status == 200, f"{r.status}")
    raw_request(port, "GET", f"/health?{marker2}")  # sin token
    r = raw_request(port, "GET", "/health", token=badtok)
    check("control de logs: token malo da 401", r.status == 401, f"{r.status}")
    raw_request(port, "GET", "/api/v1/auth/check", token=be.creds["approver"])
    time.sleep(0.5)
    log = be.logfile.read_bytes()
    check("?query-marker no aparece en backend.log (ni con ni sin token)", marker.encode() not in log and marker2.encode() not in log)
    check("un rechazo no registra el token recibido", badtok.encode() not in log and not any(t.encode() in log for t in tokens))
    check("backend.log registra la ruta de las peticiones (control no vacuo)", b"/health" in log)


# ---------------------------------------------------------------- principal
def run(root: Path) -> None:
    creds = {"ui": secrets.token_urlsafe(32), "approver": secrets.token_urlsafe(32)}
    agent = secrets.token_urlsafe(32)
    tokens = [creds["ui"], creds["approver"], agent]
    started: list[Backend] = []
    try:
        handshake_cases(root, creds)

        A = Backend(root / "A", "A", creds)
        started.append(A)
        try:
            A.start_ok()
        except RuntimeError as e:
            check("el servidor arranca y anuncia el puerto (sin esto ningun caso es valido)", False, str(e))
            return
        out = bytes(A.out)
        j = json.loads(out.split(b"\n", 1)[0])
        check("el servidor arranca y anuncia exactamente {v:1, port:N}", set(j) == {"v", "port"} and j["v"] == 1 and isinstance(j["port"], int))

        # Segundo arranque con el mismo data_dir: falla y A sigue vivo
        B = Backend(A.root, "B-mismo-data-dir", creds, data_dir=A.data_dir)
        started.append(B)
        B.launch(B.handshake_line())
        rc = B._wait(30)
        check("segundo arranque con el mismo data_dir: sale != 0 y no anuncia puerto",
              rc not in (None, 0) and b"\n" not in B.out and not B.out, f"rc={rc} out={bytes(B.out)[:100]!r}")
        check("el primer servidor sigue vivo y sano tras el segundo intento", A.alive_and_healthy())
        check("el segundo intento no deja tokens en stderr", not any(t.encode() in bytes(B.err) for t in tokens))

        http_cases(A, agent)
        ws_cases(A, agent)
        log_cases(A, tokens)
        system_cases(A, tokens, root)

        # Tercer arranque con otro data_dir: puerto distinto
        C = Backend(root / "C", "C", creds)
        started.append(C)
        try:
            C.start_ok()
            check("dos arranques con data_dir distinto: puertos distintos y ambos sanos",
                  C.port != A.port and C.alive_and_healthy() and A.alive_and_healthy(), f"{A.port} {C.port}")
            rc = C.sigterm()
            check("SIGTERM apaga el servidor (codigo 0 o -15)", rc in (0, -15), f"rc={rc}")
            check("tras SIGTERM el puerto deja de escuchar", _refused(C.port))
            check("no existe session.json tras apagar", not list(root.rglob("session.json")))
        except RuntimeError as e:
            check("dos arranques con data_dir distinto: puertos distintos", False, str(e))

        rc = A.stop_stdin()
        check("cerrar stdin apaga el servidor con codigo 0", rc == 0, f"rc={rc}")
        check("tras cerrar stdin el puerto deja de escuchar", _refused(A.port))
        hits = tree_contains(root, [t.encode() for t in tokens])
        check("tras apagar, los tokens siguen sin aparecer en ningun archivo", not hits, repr(hits))
        check("ninguna respuesta llevo Access-Control-Allow-Origin",
              not any(k.lower() == "access-control-allow-origin" for k, _ in ALL_RESPONSE_HEADERS))
        check("tokens ausentes en stderr final de A", not any(t.encode() in bytes(A.err) for t in tokens))
    finally:
        for b in started:
            b.kill()


def _refused(port: int) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=2).close()
        return False
    except OSError:
        return True


def main() -> int:
    for k in ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        os.environ.pop(k, None)
    base = os.environ.get("TMPDIR") or "/var/tmp/drakter-8"
    Path(base).mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="drakter-sec-", dir=base))
    try:
        run(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    bad = [n for ok, n in RESULTS if not ok]
    print(f"\nResumen: {len(RESULTS) - len(bad)}/{len(RESULTS)} OK, {len(bad)} FAIL")
    for n in bad:
        print(f"  FAIL: {n}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
