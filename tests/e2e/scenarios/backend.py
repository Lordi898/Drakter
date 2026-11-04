"""Backend real: arranque, autenticación, guardia, errores, WebSocket y permisos."""
from __future__ import annotations

import stat
from pathlib import Path

from harness.model import NotChecked, check


@check("backend.arranca", "El backend arranca y responde en /health", needs=())
def starts(ctx):
    if "backend" in ctx.stack.failed:
        raise AssertionError(ctx.stack.why_unavailable("backend"))
    if not ctx.stack.available("backend"):
        raise NotChecked(ctx.stack.why_unavailable("backend"))
    reply = ctx.api.request("GET", "/health")
    assert reply.status == 200 and reply.body == {"status": "ok"}, f"/health → {reply.status} {reply.body}"
    return f"handshake por stdin, puerto {ctx.api.port} anunciado y GET /health → 200"


@check("backend.stub_arranca", "El stub LLM arranca y se identifica como stub", needs=())
def stub_starts(ctx):
    if "stub" in ctx.stack.failed:
        raise AssertionError(ctx.stack.why_unavailable("stub"))
    if not ctx.stack.available("stub"):
        raise NotChecked(ctx.stack.why_unavailable("stub"))
    return f"stub en 127.0.0.1:{ctx.stack.stub_port} con dev_stub=true"


@check("hermes.preflight", "Hermes es el commit fijado, con venv propio Python >= 3.14 y runner propio", needs=())
def hermes_preflight(ctx):
    if "hermes" in ctx.stack.failed:
        raise AssertionError(ctx.stack.why_unavailable("hermes"))
    if not ctx.stack.available("hermes"):
        raise NotChecked(ctx.stack.why_unavailable("hermes"))
    commit = ctx.stack.layout.config["hermes"]["commit"]
    return f"commit {commit[:12]} verificado en el venv; Python correcto; runner presente"


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
    query = ctx.api.request("GET", f"{path}?token={ctx.api.tokens['ui']}", auth=False)
    assert query.status == 401, f"token en la URL → {query.status}"
    ghost = ctx.api.request("GET", "/api/v1/no-existe", auth=False)
    assert ghost.status == 401, f"ruta inexistente sin token → {ghost.status}"
    return "401 sin token, con token falso y con token en la URL; 200 con token"


@check("backend.guardia", "Se rechazan Host y cualquier Origin, también en /health")
def guard(ctx):
    bare = ctx.api.request("GET", "/health", auth=False)
    assert bare.status == 401, f"/health sin token → {bare.status}"
    for label, headers in (("ajeno", "evil.example"), ("localhost", f"localhost:{ctx.api.port}")):
        host = ctx.api.request("GET", "/health", headers={"Host": headers})
        assert host.status == 403 and host.error_code == "forbidden_host", f"Host {label} → {host.status}"
    for value in ("https://evil.example", "app://drakter", "null"):
        origin = ctx.api.request("GET", "/health", headers={"Origin": value})
        assert origin.status == 403 and origin.error_code == "forbidden_origin", f"Origin {value} → {origin.status}"
    return "/health exige token; 403 con Host ajeno o localhost y con cualquier Origin"


@check("backend.roles", "Cada token solo vale para su rol")
def roles(ctx):
    approve = "/api/v1/confirmations/00000000-0000-0000-0000-000000000000/approve"
    ui = ctx.api.request("POST", approve)
    assert ui.status == 403 and ui.error_code == "permission_denied", f"ui aprobando → {ui.status}"
    locations = ctx.api.request("POST", "/api/v1/storage-locations", json_body={})
    assert locations.status == 403, f"ui en storage-locations → {locations.status}"
    approver = ctx.api.request("GET", "/health", role="approver")
    assert approver.status == 403 and approver.error_code == "permission_denied", f"approver en /health → {approver.status}"
    return "ui no aprueba ni toca ubicaciones; approver no accede al resto"


@check("backend.credenciales", "Los tokens no están en argv, entorno ni disco")
def credentials(ctx):
    proc = ctx.stack.procs["backend"]
    exposed = b"".join(Path(f"/proc/{proc.pid}/{name}").read_bytes() for name in ("cmdline", "environ"))
    files = [p for p in ctx.stack.layout.work.rglob("*") if p.is_file() and p.suffix not in (".db", ".log")]
    for token in ctx.stack.tokens:
        assert token.encode() not in exposed, "token en argv o entorno"
        assert not any(token.encode() in p.read_bytes() for p in files), "token en disco"
    assert not list(ctx.stack.layout.work.rglob("session.json")), "existe session.json"
    return f"argv y entorno limpios; {len(files)} archivos revisados; sin session.json"


@check("backend.errores", "Los errores usan el sobre estándar con request_id")
def errors(ctx):
    reply = ctx.api.request("GET", "/api/v1/no-existe")
    body = reply.body.get("error", {}) if isinstance(reply.body, dict) else {}
    assert reply.status == 404 and {"code", "message", "request_id", "details"} <= body.keys(), \
        f"{reply.status}: {reply.body}"
    return f"404 con código {body['code']}"


@check("backend.websocket", "El WebSocket exige token de ui en la cabecera y rechaza lo ajeno")
def websocket(ctx):
    path = ctx.catalog.get("conversation", {}).get("ws_path", "/api/v1/events")
    with ctx.api.ws(path) as socket:
        assert socket.subprotocol == "drakter.v1", f"subprotocolo {socket.subprotocol}"
    token = ctx.api.tokens["ui"]
    rejected = (("sin token", {"role": None}), ("Origin", {"origin": "app://drakter"}),
                ("rol approver", {"role": "approver"}),
                ("token en subprotocolo", {"role": None, "subprotocols": ("drakter.v1", f"drakter.auth.{token}")}))
    for label, kwargs in rejected:
        try:
            ctx.api.ws(path, **kwargs).close()
        except Exception:  # noqa: BLE001 - el rechazo del handshake llega como excepción.
            continue
        raise AssertionError(f"WebSocket {path} aceptado: {label}")
    return f"{path} acepta ui; rechaza sin token, con Origin, con approver y con token en subprotocolo"


@check("backend.permisos", "Datos y base de datos son privados")
def permissions(ctx):
    modes = {path: stat.S_IMODE(path.stat().st_mode) for path in (
        ctx.stack.data_dir, ctx.stack.data_dir / "drakter.db", ctx.stack.data_dir / "logs")}
    wrong = {str(path): oct(mode) for path, mode in modes.items() if mode & 0o077}
    assert not wrong, f"permisos abiertos: {wrong}"
    return "datos, drakter.db y logs sin acceso de grupo ni otros"


@check("backend.migraciones", "El esquema queda al día tras arrancar")
def migrations(ctx):
    status = ctx.stack.backend_cli("status")
    assert status.returncode == 0, status.stderr
    assert "pendientes: 0" in status.stdout, status.stdout
    if "última versión: 0" in status.stdout:
        raise NotChecked("el árbol no tiene ninguna migración: no hay esquema que comprobar")
    return " · ".join(status.stdout.split("\n")[:2])
