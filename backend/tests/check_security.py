#!/usr/bin/env python3
"""Comprobacion de seguridad del backend contra un servidor real (`python -m app`).

Escrita a partir de backend/CONTRACT.md. Uso (desde backend/):
    TMPDIR=/var/tmp/drakter-8 .venv/bin/python tests/check_security.py [--port 18830]
Sin --port prueba 18830-18839 y usa el primero libre. Sale != 0 si algo falla.
Todo el estado (config, datos, runtime, HOME) va a un directorio temporal nuevo.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ALLOWED_ORIGIN = "app://drakter"
RESULTS: list[tuple[bool, str]] = []


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

    def envelope(self, code: str | None = None) -> bool:
        j = self.json()
        if not (isinstance(j, dict) and set(j) == {"error"} and isinstance(j["error"], dict)):
            return False
        e = j["error"]
        ok = set(e) == {"code", "message", "request_id", "details"} and isinstance(e["details"], list)
        ok = ok and all(isinstance(e[k], str) and e[k] for k in ("code", "message", "request_id"))
        ok = ok and any("application/json" in v for v in self.h("content-type"))
        return ok and (code is None or e["code"] == code)


def raw_request(port: int, method: str, path: str, *, host: str | list[str] | None = "default",
                headers: list[tuple[str, str]] | None = None, token: str | None = None,
                timeout: float = 5.0) -> Resp:
    lines = [f"{method} {path} HTTP/1.1"]
    hosts = [f"127.0.0.1:{port}"] if host == "default" else ([] if host is None else ([host] if isinstance(host, str) else host))
    lines += [f"Host: {h}" for h in hosts]
    if token is not None:
        lines.append(f"Authorization: Bearer {token}")
    lines += [f"{k}: {v}" for k, v in (headers or [])]
    if not any(k.lower() == "upgrade" for k, _ in (headers or [])):
        lines.append("Connection: close")
    data = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    try:
        s.sendall(data)
        buf = b""
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
    head, _, body = buf.partition(b"\r\n\r\n")
    hl = head.decode("latin-1").split("\r\n")
    if len(hl) < 1 or not hl[0].startswith("HTTP/"):
        return Resp(0, [], buf)
    hdrs = [tuple(x.split(":", 1)[0:1] + [x.split(":", 1)[1].strip()]) for x in hl[1:] if ":" in x]
    return Resp(int(hl[0].split()[1]), hdrs, body)  # type: ignore[arg-type]


def ws_handshake_raw(port: int, *, host="default", token: str | None = None,
                     headers: list[tuple[str, str]] | None = None) -> Resp:
    key = base64.b64encode(os.urandom(16)).decode()
    h = [("Upgrade", "websocket"), ("Connection", "Upgrade"), ("Sec-WebSocket-Version", "13"),
         ("Sec-WebSocket-Key", key)] + (headers or [])
    return raw_request(port, "GET", "/ws", host=host, headers=h, token=token)


# ---------------------------------------------------------------- proceso
class Server:
    def __init__(self, root: Path, port: int):
        self.root, self.port = root, port
        self.config, self.data, self.run = root / "config", root / "data", root / "run"
        for d in (self.config, self.data, self.run):
            d.mkdir(mode=0o700, exist_ok=True)
        (root / "home").mkdir(exist_ok=True)
        self.session = self.run / "drakter" / "session.json"
        self.logfile = self.data / "drakter" / "logs" / "backend.log"
        self.proc: subprocess.Popen | None = None
        self.n = 0

    def env(self) -> dict[str, str]:
        e = {k: v for k, v in os.environ.items() if not k.startswith("DRAKTER_")
             and k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}
        e.update(XDG_CONFIG_HOME=str(self.config), XDG_DATA_HOME=str(self.data),
                 XDG_RUNTIME_DIR=str(self.run), HOME=str(self.root / "home"),
                 DRAKTER_PORT=str(self.port), PYTHONUNBUFFERED="1")
        return e

    def start(self) -> None:
        self.n += 1
        self.out = (self.root / f"stdout{self.n}.txt").open("wb")
        self.err = (self.root / f"stderr{self.n}.txt").open("wb")
        self.proc = subprocess.Popen([sys.executable, "-m", "app"], cwd=BACKEND, env=self.env(),
                                     stdout=self.out, stderr=self.err, stdin=subprocess.DEVNULL)
        deadline = time.time() + 30
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"el servidor termino al arrancar (codigo {self.proc.returncode}):\n"
                                   + self.output()[-2000:])
            if self.session.exists():
                try:
                    if raw_request(self.port, "GET", "/health", timeout=2).status == 200:
                        return
                except OSError:
                    pass
            time.sleep(0.2)
        raise RuntimeError("el servidor no quedo listo en 30 s:\n" + self.output()[-2000:])

    def output(self) -> str:
        self.out.flush(), self.err.flush()
        return ((self.root / f"stdout{self.n}.txt").read_bytes() + b"\n--stderr--\n"
                + (self.root / f"stderr{self.n}.txt").read_bytes()).decode("utf-8", "replace")

    def token(self) -> str:
        return json.loads(self.session.read_text())["token"]

    def stop(self, timeout: float = 15.0) -> int | None:
        if not self.proc or self.proc.poll() is not None:
            return self.proc.returncode if self.proc else None
        self.proc.send_signal(signal.SIGTERM)
        try:
            return self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
            return None

    def kill(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()


def mode(p: Path) -> int:
    return stat.S_IMODE(p.stat().st_mode)


def pick_port(arg: int | None) -> int:
    cands = [arg] if arg else list(range(18830, 18840))
    for p in cands:
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise SystemExit(f"ningun puerto libre en {cands}")


# ---------------------------------------------------------------- casos HTTP
def http_cases(srv: Server, token: str) -> None:
    port = srv.port
    R = lambda *a, **k: raw_request(port, *a, **k)  # noqa: E731
    bad_token = "TOKEN-CANARIO-INVALIDO-12345"

    # /health
    r = R("GET", "/health")
    check("/health 200 sin token con {status: ok}", r.status == 200 and r.json() == {"status": "ok"}, f"{r.status} {r.body[:100]!r}")
    check("/health no contiene token ni cabecera Server",
          token.encode() not in r.body and not r.h("server") and all(token not in v for _, v in r.headers), repr(r.headers))

    # autenticacion
    r = R("GET", "/api/v1/auth/check")
    check("sin token: 401 con envelope, code unauthorized y WWW-Authenticate: Bearer",
          r.status == 401 and r.envelope("unauthorized") and r.h("www-authenticate") == ["Bearer"], f"{r.status} {r.body[:120]!r} {r.headers}")
    r = R("GET", "/api/v1/auth/check", token=bad_token)
    check("token malo: 401 con envelope", r.status == 401 and r.envelope("unauthorized"), f"{r.status}")
    r = R("GET", "/api/v1/auth/check", headers=[("Authorization", "Bearer t\u00f3k\u00e9n-\u4e2d\u6587")])
    check("token no ASCII: 401 (no 500)", r.status == 401 and r.envelope("unauthorized"), f"{r.status} {r.body[:100]!r}")
    r = R("GET", "/api/v1/auth/check", headers=[("Authorization", f"Basic {token}")])
    check("esquema distinto de Bearer con el token correcto: 401", r.status == 401, f"{r.status}")
    r = R("GET", "/api/v1/auth/check", token=token)
    check("token correcto: 200 {authenticated: true}", r.status == 200 and r.json() == {"authenticated": True}, f"{r.status} {r.body[:100]!r}")
    r = R("GET", f"/api/v1/auth/check?token={token}")
    check("?token= en query NO autentica", r.status == 401, f"{r.status}")
    r = R("GET", "/api/v1/auth/check", headers=[("Cookie", f"token={token}")])
    check("cookie con el token NO autentica", r.status == 401, f"{r.status}")

    # rutas inexistentes
    r = R("GET", "/no/existe")
    check("ruta inexistente sin token: 401 (no revela 404)", r.status == 401 and r.envelope("unauthorized"), f"{r.status}")
    r = R("GET", "/no/existe", token=token)
    check("ruta inexistente con token: 404 con envelope", r.status == 404 and r.envelope(), f"{r.status} {r.body[:100]!r}")
    r = R("POST", "/health", token=token)
    check("metodo no permitido (POST /health): 405 con envelope", r.status == 405 and r.envelope(), f"{r.status}")

    # docs
    for p in ("/docs", "/redoc", "/openapi.json"):
        a, b = R("GET", p), R("GET", p, token=token)
        check(f"{p} no accesible (401 sin token, 404 con token)", a.status == 401 and b.status == 404, f"{a.status}/{b.status}")

    # Host
    for label, host in (("evil.com:puerto", f"evil.com:{port}"), ("127.0.0.1:otro puerto", f"127.0.0.1:{port + 1}"),
                        ("127.0.0.1 sin puerto", "127.0.0.1"), ("evil.com", "evil.com")):
        r = R("GET", "/api/v1/auth/check", host=host, token=token)
        check(f"Host falso ({label}) con token valido: 403 forbidden_host",
              r.status == 403 and r.envelope("forbidden_host"), f"{r.status} {r.body[:100]!r}")
    r = R("GET", "/health", host=f"evil.com:{port}")
    check("Host falso tambien en ruta publica (/health): 403", r.status == 403, f"{r.status}")
    r = R("GET", "/api/v1/auth/check", host=f"evil.com:{port}")
    check("Host falso sin token: 403 (el Host se valida antes que el token)", r.status == 403, f"{r.status}")
    r = R("GET", "/api/v1/auth/check", host=None, token=token)
    check("sin cabecera Host: rechazado (400/403, nunca 200)", r.status in (400, 403), f"{r.status}")
    r = R("GET", "/api/v1/auth/check", host=[f"127.0.0.1:{port}", f"evil.com:{port}"], token=token)
    check("dos cabeceras Host (valida + falsa): rechazado", r.status in (400, 403), f"{r.status}")
    r = R("GET", "/api/v1/auth/check", host=[f"127.0.0.1:{port}", f"127.0.0.1:{port}"], token=token)
    check("dos cabeceras Host identicas: rechazado", r.status in (400, 403), f"{r.status}")
    for h in (f"localhost:{port}", f"LOCALHOST:{port}", f"127.0.0.1:{port}"):
        r = R("GET", "/api/v1/auth/check", host=h, token=token)
        check(f"Host legitimo {h}: 200 (control)", r.status == 200, f"{r.status}")

    # Origin
    r = R("GET", "/api/v1/auth/check", token=token, headers=[("Origin", "http://evil.com")])
    check("Origin falso con token valido: 403 forbidden_origin", r.status == 403 and r.envelope("forbidden_origin"), f"{r.status}")
    r = R("GET", "/api/v1/auth/check", token=token, headers=[("Origin", "null")])
    check("Origin: null con token valido: 403", r.status == 403 and r.envelope("forbidden_origin"), f"{r.status}")
    r = R("GET", "/health", headers=[("Origin", "http://evil.com")])
    check("Origin falso tambien en /health: 403", r.status == 403, f"{r.status}")
    r = R("GET", "/api/v1/auth/check", token=token, headers=[("Origin", ALLOWED_ORIGIN), ("Origin", "http://evil.com")])
    check("dos cabeceras Origin: 403", r.status == 403, f"{r.status}")
    r = R("GET", "/api/v1/auth/check", token=token, headers=[("Origin", ALLOWED_ORIGIN)])
    check("Origin permitido: 200 con Access-Control-Allow-Origin y sin credenciales",
          r.status == 200 and r.h("access-control-allow-origin") == [ALLOWED_ORIGIN]
          and not r.h("access-control-allow-credentials"), f"{r.status} {r.headers}")
    r = R("GET", "/api/v1/auth/check", headers=[("Origin", ALLOWED_ORIGIN)])
    check("401 de origen permitido legible: incluye Access-Control-Allow-Origin",
          r.status == 401 and r.h("access-control-allow-origin") == [ALLOWED_ORIGIN], f"{r.status} {r.headers}")
    r = R("GET", "/api/v1/auth/check", headers=[("Origin", "http://evil.com")])
    check("403 de origen falso sin Access-Control-Allow-Origin",
          r.status == 403 and not r.h("access-control-allow-origin"), f"{r.status} {r.headers}")
    pre = [("Origin", ALLOWED_ORIGIN), ("Access-Control-Request-Method", "GET"),
           ("Access-Control-Request-Headers", "authorization")]
    r = R("OPTIONS", "/api/v1/auth/check", headers=pre)
    check("preflight de origen permitido sin token: 200 con CORS",
          r.status == 200 and r.h("access-control-allow-origin") == [ALLOWED_ORIGIN]
          and "GET" in ",".join(r.h("access-control-allow-methods")), f"{r.status} {r.headers}")
    r = R("OPTIONS", "/api/v1/auth/check", headers=[("Origin", "http://evil.com")] + pre[1:])
    check("preflight con Origin falso: 403", r.status == 403, f"{r.status}")
    r = R("OPTIONS", "/api/v1/auth/check", host=f"evil.com:{port}", headers=pre)
    check("preflight con Host falso: 403", r.status == 403, f"{r.status}")
    r = R("OPTIONS", "/api/v1/auth/check")
    check("OPTIONS sin Origin ni cabeceras CORS requiere token: 401", r.status == 401, f"{r.status}")


# ---------------------------------------------------------------- casos WS
def ws_cases(srv: Server, token: str) -> None:
    import websockets
    from websockets.asyncio.client import connect
    from websockets.exceptions import ConnectionClosed, InvalidStatus

    port = srv.port
    uri = f"ws://127.0.0.1:{port}/ws"
    auth = {"Authorization": f"Bearer {token}"}

    async def dial(**kw):
        return await connect(uri if "uri" not in kw else kw.pop("uri"), proxy=None, open_timeout=5, **kw)

    async def outcome(**kw) -> str:
        """'OPEN' si conecta, 'HTTP <n>' si el handshake es rechazado, otro texto si es otro error."""
        try:
            ws = await dial(**kw)
        except InvalidStatus as e:
            return f"HTTP {e.response.status_code}"
        except Exception as e:  # noqa: BLE001
            return f"ERR {type(e).__name__}: {e}"
        await ws.close()
        return "OPEN"

    async def main() -> None:
        # Control: el mismo cliente conecta con credenciales validas
        ctl = await outcome(additional_headers=auth)
        ctl_ok = check("WS control: el cliente conecta con Authorization valido", ctl == "OPEN", ctl)

        def rej(name: str, res: str) -> None:
            check(name, ctl_ok and res in ("HTTP 401", "HTTP 403"), res if ctl_ok else f"{res} (control fallido: no valido)")

        rej("WS sin token rechazado en el handshake", await outcome())
        rej("WS con token en query rechazado", await outcome(uri=f"{uri}?token={token}"))
        rej("WS con token malo en Authorization rechazado", await outcome(additional_headers={"Authorization": "Bearer nope"}))
        rej("WS con subprotocolo de auth malo rechazado", await outcome(subprotocols=["drakter.v1", "drakter.auth.nope"]))
        rej("WS con Origin falso (token valido) rechazado", await outcome(additional_headers=auth, origin="http://evil.com"))
        res = await outcome(additional_headers=auth, origin=ALLOWED_ORIGIN)
        check("WS con Origin permitido y token valido conecta (control)", res == "OPEN", res)

        # Host falso: handshake crudo para controlar el Host exacto
        good = ws_handshake_raw(port, token=token)
        check("WS crudo con Host correcto: 101 (control)", good.status == 101, f"{good.status}")
        for label, host in (("evil.com:puerto", f"evil.com:{port}"), ("127.0.0.1:otro puerto", f"127.0.0.1:{port + 1}")):
            r = ws_handshake_raw(port, host=host, token=token)
            check(f"WS con Host falso ({label}) y token valido rechazado",
                  good.status == 101 and r.status == 403, f"{r.status}")
        r = ws_handshake_raw(port, token=token, headers=[("Origin", "null")])
        check("WS con Origin: null y token valido rechazado", good.status == 101 and r.status == 403, f"{r.status}")

        r = ws_handshake_raw(port, headers=[("Authorization", "Bearer t\u00f6ken")])
        check("WS con cabecera no ASCII rechazado sin 500", good.status == 101 and r.status in (400, 401, 403), f"{r.status}")
        try:
            async with await dial(additional_headers=auth, max_size=None) as ws:
                await ws.send("x" * (1048576 + 1))
                await asyncio.wait_for(ws.recv(), 5)
            check("WS con trama mayor de 1 MiB cerrado", False, "no cerro")
        except Exception as e:  # noqa: BLE001
            close = getattr(getattr(e, "rcvd", None), "code", None)
            check("WS con trama mayor de 1 MiB cerrado (1009)", close == 1009, repr(e))

        # Subprotocolo de autenticacion
        try:
            async with await dial(subprotocols=["drakter.v1", f"drakter.auth.{token}"]) as ws:
                sp = ws.subprotocol
                await ws.send("ping")
                pong = await asyncio.wait_for(ws.recv(), 5)
            check("WS con subprotocolo: acepta con drakter.v1 y ping -> pong", sp == "drakter.v1" and pong == "pong", f"{sp!r} {pong!r}")
        except Exception as e:  # noqa: BLE001
            check("WS con subprotocolo: acepta con drakter.v1 y ping -> pong", False, repr(e))
        r = ws_handshake_raw(port, headers=[("Sec-WebSocket-Protocol", f"drakter.v1, drakter.auth.{token}")])
        sp = r.h("sec-websocket-protocol")
        check("WS: la respuesta nunca devuelve el subprotocolo de autenticacion",
              r.status == 101 and sp == ["drakter.v1"] and token not in str(r.headers), f"{r.status} {r.headers}")
        r = ws_handshake_raw(port, headers=[("Sec-WebSocket-Protocol", f"drakter.auth.{token}, drakter.v1")])
        check("WS: igual con el orden de subprotocolos invertido",
              r.status == 101 and r.h("sec-websocket-protocol") == ["drakter.v1"], f"{r.status} {r.headers}")

        # Authorization
        try:
            async with await dial(additional_headers=auth, subprotocols=["drakter.v1"]) as ws:
                await ws.send("ping")
                pong = await asyncio.wait_for(ws.recv(), 5)
                sp = ws.subprotocol
            check("WS con Authorization: ping -> pong y subprotocolo drakter.v1", pong == "pong" and sp == "drakter.v1", f"{pong!r} {sp!r}")
        except Exception as e:  # noqa: BLE001
            check("WS con Authorization: ping -> pong y subprotocolo drakter.v1", False, repr(e))

        # Entrada invalida -> 1003
        for label, payload in (("texto", "hola"), ("binario", b"\x00\x01")):
            try:
                async with await dial(additional_headers=auth) as ws:
                    await ws.send(payload)
                    try:
                        await asyncio.wait_for(ws.recv(), 5)
                        code = "respuesta inesperada"
                    except ConnectionClosed as e:
                        code = e.rcvd.code if e.rcvd else None
                check(f"WS entrada invalida ({label}) cierra con 1003", code == 1003, repr(code))
            except Exception as e:  # noqa: BLE001
                check(f"WS entrada invalida ({label}) cierra con 1003", False, repr(e))

    _ = websockets
    asyncio.run(main())


# ---------------------------------------------------------------- sistema
def system_cases(srv: Server, token: str) -> None:
    port = srv.port
    marker = "query-marker-7f3a"
    r = raw_request(port, "GET", f"/api/v1/auth/check?{marker}=1", token=token)
    time.sleep(0.2)
    check("la consulta de una peticion no llega a backend.log",
          r.status == 200 and srv.logfile.exists() and marker not in srv.logfile.read_text(), f"{r.status}")
    ss = subprocess.run(["ss", "-ltnH"], capture_output=True, text=True).stdout.splitlines()
    mine = [l.split()[3] for l in ss if len(l.split()) > 3 and l.split()[3].rsplit(":", 1)[-1] == str(port)]
    check("ss -ltn: el puerto solo escucha en 127.0.0.1", bool(mine) and all(a == f"127.0.0.1:{port}" for a in mine), repr(mine))

    sd = srv.session.parent
    check("session.json con permisos 600", srv.session.exists() and mode(srv.session) == 0o600, oct(mode(srv.session)) if srv.session.exists() else "no existe")
    check("directorio de sesion con permisos 700", mode(sd) == 0o700, oct(mode(sd)))
    sj = json.loads(srv.session.read_text())
    check("session.json con token/port/pid/started_at correctos",
          set(sj) == {"token", "port", "pid", "started_at"} and sj["port"] == port and sj["pid"] == srv.proc.pid
          and len(sj["token"]) >= 32, repr({k: v for k, v in sj.items() if k != "token"}))
    datadir = srv.data / "drakter"
    check("directorio de datos 700", datadir.is_dir() and mode(datadir) == 0o700, oct(mode(datadir)) if datadir.exists() else "no existe")
    for name in ("drakter.db", "drakter.db-wal", "drakter.db-shm"):
        p = datadir / name
        if name == "drakter.db":
            check("drakter.db existe con permisos 600", p.exists() and mode(p) == 0o600, oct(mode(p)) if p.exists() else "no existe")
        elif p.exists():
            check(f"{name} con permisos 600", mode(p) == 0o600, oct(mode(p)))
        else:
            print(f"----  {name} no existe ahora (el contrato solo lo exige cuando existe)")
    check("backend.log existe, no esta vacio y tiene permisos 600",
          srv.logfile.exists() and srv.logfile.stat().st_size > 0 and mode(srv.logfile) == 0o600,
          oct(mode(srv.logfile)) if srv.logfile.exists() else "no existe")
    check("directorio de logs 700", srv.logfile.parent.is_dir() and mode(srv.logfile.parent) == 0o700, oct(mode(srv.logfile.parent)))

    # el token no debe aparecer en logs, salida ni proceso
    logtxt = srv.logfile.read_bytes() if srv.logfile.exists() else b""
    out = srv.output().encode()
    check("el token no aparece en backend.log", token.encode() not in logtxt)
    check("el token no aparece en stdout/stderr", token.encode() not in out)
    check("tokens de prueba (malo y no ASCII) no se registran en backend.log",
          b"TOKEN-CANARIO-INVALIDO-12345" not in logtxt and "t\u00f3k\u00e9n".encode() not in logtxt)
    pid = srv.proc.pid
    check("el token no esta en cmdline ni en environ del proceso",
          token.encode() not in Path(f"/proc/{pid}/cmdline").read_bytes()
          and token.encode() not in Path(f"/proc/{pid}/environ").read_bytes())


# ---------------------------------------------------------------- principal
def run(root: Path, port: int) -> None:
    srv = Server(root, port)
    try:
        srv.start()
    except RuntimeError as e:
        check("el servidor arranca (sin esto ningun rechazo es valido)", False, str(e))
        return
    try:
        token = srv.token()
        check("el servidor arranca y publica session.json", True)
        http_cases(srv, token)
        ws_cases(srv, token)
        system_cases(srv, token)

        rc = srv.stop()
        check("SIGTERM: el servidor termina (0 o -15, uvicorn re-emite la senal) y borra session.json",
              rc in (0, -15) and not srv.session.exists(), f"rc={rc} session_existe={srv.session.exists()}")

        # segundo arranque
        srv.start()
        token2 = srv.token()
        check("segundo arranque: token distinto", token2 != token)
        r_old = raw_request(port, "GET", "/api/v1/auth/check", token=token)
        r_new = raw_request(port, "GET", "/api/v1/auth/check", token=token2)
        check("segundo arranque: token viejo 401 y nuevo 200",
              r_old.status == 401 and r_new.status == 200, f"{r_old.status}/{r_new.status}")
        logtxt = srv.logfile.read_bytes()
        check("segundo arranque: ningun token en backend.log ni en salida",
              token.encode() not in logtxt and token2.encode() not in logtxt
              and token2.encode() not in srv.output().encode())
        rc = srv.stop()
        check("segundo SIGTERM borra session.json", rc in (0, -15) and not srv.session.exists(), f"rc={rc}")
    finally:
        srv.kill()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int)
    ns = ap.parse_args()
    for k in ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        os.environ.pop(k, None)
    port = pick_port(ns.port)
    base = os.environ.get("TMPDIR") or "/var/tmp/drakter-8"
    Path(base).mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="drakter-sec-", dir=base))
    try:
        run(root, port)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    bad = [n for ok, n in RESULTS if not ok]
    print(f"\nResumen: {len(RESULTS) - len(bad)}/{len(RESULTS)} OK, {len(bad)} FAIL (puerto {port})")
    for n in bad:
        print(f"  FAIL: {n}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
