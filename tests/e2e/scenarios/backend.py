"""Backend real: arranque, autenticación, guardia, errores, WebSocket y permisos."""
from __future__ import annotations

import stat

from harness.model import NotChecked, check


@check("backend.arranca", "El backend arranca y responde en /health", needs=())
def starts(ctx):
    if "backend" in ctx.stack.failed:
        raise AssertionError(ctx.stack.why_unavailable("backend"))
    if not ctx.stack.available("backend"):
        raise NotChecked(ctx.stack.why_unavailable("backend"))
    reply = ctx.api.request("GET", "/health", auth=False)
    assert reply.status == 200 and reply.body == {"status": "ok"}, f"/health → {reply.status} {reply.body}"
    return "GET /health → 200 sin token"


@check("backend.stub_arranca", "El stub LLM arranca y se identifica como stub", needs=())
def stub_starts(ctx):
    if "stub" in ctx.stack.failed:
        raise AssertionError(ctx.stack.why_unavailable("stub"))
    if not ctx.stack.available("stub"):
        raise NotChecked(ctx.stack.why_unavailable("stub"))
    return f"stub en 127.0.0.1:{ctx.stack.stub_port} con dev_stub=true"


@check("hermes.preflight", "Hermes es el commit fijado, con venv propio Python >= 3.14 y aiohttp", needs=())
def hermes_preflight(ctx):
    if "hermes" in ctx.stack.failed:
        raise AssertionError(ctx.stack.why_unavailable("hermes"))
    if not ctx.stack.available("hermes"):
        raise NotChecked(ctx.stack.why_unavailable("hermes"))
    commit = ctx.stack.layout.config["hermes"]["commit"]
    return f"commit {commit[:12]} verificado en el venv; Python y aiohttp correctos"


@check("backend.loopback", "El backend escucha solo en 127.0.0.1")
def loopback(ctx):
    target = f"{ctx.api.port:04X}"
    rows = open("/proc/net/tcp").read().splitlines()[1:]
    listeners = [r.split()[1] for r in rows if r.split()[3] == "0A" and r.split()[1].endswith(f":{target}")]
    assert listeners == [f"0100007F:{target}"], f"sockets a la escucha: {listeners}"
    v6 = open("/proc/net/tcp6").read()
    assert f":{target} 00000000000000000000000000000000:0000 0A" not in v6, "también escucha en IPv6"
    return "un único socket en 127.0.0.1"


@check("backend.autenticacion", "Las rutas exigen token y el token no vale en la URL")
def auth(ctx):
    path = "/api/v1/auth/check"
    denied = ctx.api.request("GET", path, auth=False)
    assert denied.status == 401 and denied.error_code == "unauthorized", f"sin token → {denied.status}"
    assert ctx.api.request("GET", path).body == {"authenticated": True}
    wrong = ctx.api.request("GET", path, auth=False, headers={"Authorization": "Bearer malo"})
    assert wrong.status == 401, f"token falso → {wrong.status}"
    query = ctx.api.request("GET", f"{path}?token={ctx.api.token}", auth=False)
    assert query.status == 401, f"token en la URL → {query.status}"
    ghost = ctx.api.request("GET", "/api/v1/no-existe", auth=False)
    assert ghost.status == 401, f"ruta inexistente sin token → {ghost.status}"
    return "401 sin token, con token falso y con token en la URL; 200 con token"


@check("backend.guardia", "Se rechazan Host y Origin ajenos")
def guard(ctx):
    host = ctx.api.request("GET", "/health", auth=False, headers={"Host": "evil.example"})
    assert host.status == 403 and host.error_code == "forbidden_host", f"Host → {host.status}"
    origin = ctx.api.request("GET", "/health", auth=False, headers={"Origin": "https://evil.example"})
    assert origin.status == 403 and origin.error_code == "forbidden_origin", f"Origin → {origin.status}"
    return "403 forbidden_host y 403 forbidden_origin"


@check("backend.errores", "Los errores usan el sobre estándar con request_id")
def errors(ctx):
    reply = ctx.api.request("GET", "/api/v1/no-existe")
    body = reply.body.get("error", {}) if isinstance(reply.body, dict) else {}
    assert reply.status == 404 and {"code", "message", "request_id", "details"} <= body.keys(), \
        f"{reply.status}: {reply.body}"
    return f"404 con código {body['code']}"


@check("backend.websocket", "El WebSocket autentica por subprotocolo y rechaza lo ajeno")
def websocket(ctx):
    # El contrato mueve /ws a /api/v1/events, que solo emite: el ping es exclusivo de /ws.
    configured = ctx.catalog.get("conversation", {}).get("ws_path", "/ws")
    accepted = None
    for path in dict.fromkeys((configured, "/ws")):
        try:
            socket = ctx.api.ws(path)
        except Exception:  # noqa: BLE001 - ruta sin WebSocket: se prueba la siguiente.
            continue
        accepted = path
        with socket:
            assert socket.subprotocol == "drakter.v1", f"subprotocolo {socket.subprotocol}"
            if path == "/ws":
                socket.send("ping")
                assert socket.recv(timeout=5) == "pong"
        break
    assert accepted, f"ningún WebSocket acepta el token: {configured}, /ws"
    for label, kwargs in (("sin token", {"auth": False}), ("Origin ajeno", {"origin": "https://evil.example"})):
        try:
            ctx.api.ws(accepted, **kwargs).close()
        except Exception:  # noqa: BLE001 - el rechazo del handshake llega como excepción.
            continue
        raise AssertionError(f"WebSocket {accepted} aceptado {label}")
    return f"{accepted} acepta con token; handshake rechazado sin token y con Origin ajeno"


@check("backend.permisos", "Sesión y base de datos son privadas")
def permissions(ctx):
    modes = {path: stat.S_IMODE(path.stat().st_mode) for path in (
        ctx.stack.session_file, ctx.stack.data_dir / "drakter.db")}
    modes[ctx.stack.runtime_dir] = stat.S_IMODE(ctx.stack.runtime_dir.stat().st_mode)
    wrong = {str(path): oct(mode) for path, mode in modes.items() if mode & 0o077}
    assert not wrong, f"permisos abiertos: {wrong}"
    return "session.json y drakter.db sin acceso de grupo ni otros"


@check("backend.migraciones", "El esquema queda al día tras arrancar")
def migrations(ctx):
    status = ctx.stack.backend_cli("status")
    assert status.returncode == 0, status.stderr
    assert "pendientes: 0" in status.stdout, status.stdout
    if "última versión: 0" in status.stdout:
        raise NotChecked("el árbol no tiene ninguna migración: no hay esquema que comprobar")
    return " · ".join(status.stdout.split("\n")[:2])
