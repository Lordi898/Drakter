#!/usr/bin/env python3
"""Comprobación breve de que la puerta de confirmación no se puede saltar (CLAUDE.md §4).

Uso, desde backend/, con el contrato en la ruta:
    PYTHONPATH=.:../contracts/python .venv/bin/python tests/critical/check_confirmations.py
Sale != 0 si algo falla. Todo el estado va a un directorio temporal nuevo.
Ejerce la pila real de middlewares por ASGI, sin puerto ni Electron.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sqlite3
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

from drakter_contracts.common import ContractModel, Origin
from drakter_contracts.tools import RiskClass

from app.api.confirmations import APPROVER_HEADER
from app.audit.writer import list_events
from app.core.config import Settings
from app.core.errors import AppError
from app.database.migrator import migrate
from app.main import create_app
from app.permissions.credentials import APPROVER_FILE_NAME, ApprovalSigner
from app.permissions.engine import PermissionEngine
from app.permissions.models import ActionSpec, ActorContext, Principal
from app.permissions.setup import install_security, start_security, stop_security
from app.services.actions import ActionService, ConfirmationRequiredError
from app.tools.dispatcher import dispatch

PORT = 18765
FAILURES: list[str] = []


def check(name: str, ok: object, detail: object = "") -> None:
    print(f"{'OK  ' if ok else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILURES.append(name)


class Args(ContractModel):
    key: str
    password: str = "s3cret-value"


class Bulk(ContractModel):
    count: int


calls = {"demo_delete": 0, "demo_external": 0, "demo_write": 0}
revision = {"value": 1}
lock = threading.Lock()


def effect(name: str):
    def handler(conn: sqlite3.Connection, params: Args) -> dict[str, str]:
        with lock:
            calls[name] += 1
        return {"done": params.key}

    return handler


def write_setting(conn: sqlite3.Connection, params: Args) -> dict[str, str]:
    calls["demo_write"] += 1
    conn.execute(
        "INSERT INTO settings (key, value_json, updated_at, updated_by) "
        "VALUES (?, '1', '2026-01-01T00:00:00.000Z', 'system')",
        (params.key,),
    )
    return {"done": params.key}


def targets(conn: sqlite3.Connection, params: Args) -> list[dict[str, object]]:
    return [{"id": params.key, "revision": revision["value"]}]


def summary(params: Args) -> str:
    return f"Borrar {params.key}‮\x07"


SPECS = [
    ActionSpec("demo_delete", "demo.delete", RiskClass.CONFIRM, Args, effect("demo_delete"),
               summarize=summary, audit={"key": "log"}, resolve_targets=targets),
    ActionSpec("demo_external", "demo.delete", RiskClass.CONFIRM, Args, effect("demo_external"),
               summarize=summary, audit={"key": "log"}, external=True),
    ActionSpec("demo_write", "demo.write", RiskClass.WRITE, Args, write_setting, summarize=summary,
               audit={"key": "log"}),
    ActionSpec("demo_bulk", "demo.write", RiskClass.WRITE, Bulk, lambda c, p: {"ok": True},
               summarize=lambda p: "lote", count_affected=lambda c, p: p.count),
    ActionSpec("demo_read", "demo.read", RiskClass.READ, Args, lambda c, p: {"ok": True}),
    ActionSpec("audit_wipe", "audit.write", RiskClass.WRITE, Args, effect("demo_write"),
               summarize=summary),
    ActionSpec("grant_self", "permissions.admin", RiskClass.CONFIRM, Args, effect("demo_write"),
               summarize=summary),
]


def agent(turn: str | None = None, tainted: bool = False) -> ActorContext:
    return ActorContext(Principal.AGENT, Origin.MCP, "corr", turn or str(uuid4()), None, tainted)


async def asgi(app, method: str, path: str, headers: dict[str, str], body: object = None):
    raw = b"" if body is None else json.dumps(body).encode()
    pairs = [(b"host", f"127.0.0.1:{PORT}".encode()), (b"content-type", b"application/json")]
    pairs += [(k.encode(), v.encode()) for k, v in headers.items()]
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
        "path": path, "raw_path": path.encode(), "query_string": b"", "headers": pairs,
        "client": ("127.0.0.1", 50000), "server": ("127.0.0.1", PORT), "scheme": "http",
    }
    sent = False
    async def receive():
        nonlocal sent
        if sent:
            await asyncio.sleep(3600)
        sent = True
        return {"type": "http.request", "body": raw, "more_body": False}
    messages: list[dict] = []
    async def send(message):
        messages.append(message)
    await app(scope, receive, send)
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    data = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, json.loads(data) if data else None


def must_abort(conn: sqlite3.Connection, name: str, sql: str, args: tuple = ()) -> None:
    try:
        conn.execute(sql, args)
    except sqlite3.DatabaseError:
        check(name, True)
    else:
        check(name, False, "la sentencia no falló")


def status_of(conn: sqlite3.Connection, action_id: str) -> str:
    return conn.execute(
        "SELECT status FROM pending_confirmations WHERE id = ?", (action_id,)
    ).fetchone()[0]


async def main(root: Path) -> None:
    settings = Settings(data_dir=root / "data", runtime_dir=root / "run", port=PORT,
                        _env_file=None)
    (root / "data" / "backups").mkdir(parents=True, mode=0o700)
    (root / "run").mkdir(mode=0o700)
    grants = root / "permissions.json"
    grants.write_text(json.dumps({"granted": ["demo.*", "audit.*", "permissions.*"]}))
    migrate(settings.db_path, settings.backups_dir)

    app = create_app(settings)
    actions = install_security(app, settings, agent_grants_path=grants)
    for spec in SPECS:
        actions.registry.register(spec)
    await start_security(app, settings)

    session = app.state.token.reveal()
    approver = app.state.approver_token.reveal()
    agent_token = "agent-" + uuid4().hex
    ui = {"authorization": f"Bearer {session}"}
    main_process = {**ui, APPROVER_HEADER: approver}
    conn = actions.open()

    print("-- entrega del token de approver")
    handoff = settings.runtime_dir / APPROVER_FILE_NAME
    check("archivo de approver 0600", handoff.stat().st_mode & 0o777 == 0o600)
    check("archivo de approver contiene el token", json.loads(handoff.read_text())["approver_token"] == approver)

    print("-- el agente no ejecuta ni recibe nada con que aprobar")
    args = {"key": "a"}
    outcome = dispatch("demo_delete", args, agent(), actions=actions)
    check("borrar queda pendiente", outcome["status"] == "confirmation_required", outcome)
    check("no se ejecutó", calls["demo_delete"] == 0)
    check("el agente solo recibe action_id, summary y expires_at",
          set(outcome) == {"status", "action_id", "summary", "expires_at"}, outcome)
    check("resumen sin bidi ni control", "‮" not in outcome["summary"] and "\x07" not in outcome["summary"])
    action = outcome["action_id"]
    base = f"/api/v1/confirmations/{action}"
    detail = actions.detail(conn, UUID(action))
    hash_ = detail["params_hash"]

    print("-- solo Electron main decide")
    code, _ = await asgi(app, "POST", f"{base}/approve", {"authorization": f"Bearer {agent_token}"},
                         {"params_hash": hash_, "approval_token": "x"})
    check("token de agente: 401", code == 401, code)
    code, _ = await asgi(app, "POST", f"{base}/approval-token", {"authorization": f"Bearer {agent_token}"})
    check("token de agente no obtiene token de aprobación", code == 401, code)
    code, body = await asgi(app, "POST", f"{base}/approval-token", ui)
    check("GUI sin approver no obtiene token", code == 403, (code, body))
    code, _ = await asgi(app, "POST", f"{base}/approve", ui, {"params_hash": hash_, "approval_token": "x"})
    check("GUI sin approver: 403", code == 403, code)
    code, _ = await asgi(app, "POST", f"{base}/approve", {**ui, APPROVER_HEADER: "falso"},
                         {"params_hash": hash_, "approval_token": "x"})
    check("approver falso: 403", code == 403, code)
    code, _ = await asgi(app, "POST", f"{base}/reject", ui)
    check("rechazar también exige approver", code == 403, code)
    code, _ = await asgi(app, "POST", f"{base}/approve", {**main_process, "origin": "app://drakter"},
                         {"params_hash": hash_, "approval_token": "x"})
    check("con Origin (renderer): 403 aunque tenga approver", code == 403, code)
    code, body = await asgi(app, "GET", base, ui)
    check("la GUI ve la pendiente", code == 200 and "approval_token" not in body, (code, body))
    try:
        actions.approve(conn, UUID(action), hash_, Principal.AGENT, approval_token="x", correlation_id="c")
        check("el servicio rechaza a agente", False)
    except AppError as exc:
        check("el servicio rechaza a agente", exc.status_code == 403)
    try:
        actions.approve(conn, UUID(action), hash_, Principal.UI, approval_token="x", correlation_id="c")
        check("el servicio rechaza a ui", False)
    except AppError as exc:
        check("el servicio rechaza a ui", exc.status_code == 403)
    check("sigue pendiente y sin ejecutar", status_of(conn, action) == "pending" and calls["demo_delete"] == 0)
    denied = [e for e in list_events(conn, confirmation_id=action) if e["result"] == "denied"]
    check("los intentos quedan auditados", len(denied) >= 5, len(denied))

    print("-- token ligado a acción, parámetros y hash; un solo uso")
    code, ticket = await asgi(app, "POST", f"{base}/approval-token", main_process)
    check("main obtiene el token", code == 200 and ticket.get("approval_token"), (code, ticket))
    token = ticket["approval_token"]
    other = dispatch("demo_delete", {"key": "b"}, agent(), actions=actions)["action_id"]
    code, _ = await asgi(app, "POST", f"/api/v1/confirmations/{other}/approve", main_process,
                         {"params_hash": actions.detail(conn, UUID(other))["params_hash"], "approval_token": token})
    check("token de otra acción: 403", code == 403, code)
    code, _ = await asgi(app, "POST", f"{base}/approve", main_process,
                         {"params_hash": "0" * 64, "approval_token": token})
    check("hash distinto: 409", code == 409, code)
    check("hash distinto no consume la fila", status_of(conn, action) == "pending" and calls["demo_delete"] == 0)
    code, body = await asgi(app, "POST", f"{base}/approve", main_process,
                            {"params_hash": hash_, "approval_token": token})
    check("aprobar ejecuta", code == 200 and body["status"] == "executed", (code, body))
    code, _ = await asgi(app, "POST", f"{base}/approve", main_process,
                         {"params_hash": hash_, "approval_token": token})
    check("reutilizar el token: 409", code == 409, code)
    check("ejecutó exactamente una vez", calls["demo_delete"] == 1, calls)

    print("-- concurrencia")
    race = dispatch("demo_delete", {"key": "c"}, agent(), actions=actions)["action_id"]
    hash_race = actions.detail(conn, UUID(race))["params_hash"]
    token_race = actions.approval_token(conn, UUID(race), Principal.APPROVER)
    before = calls["demo_delete"]

    def attempt(_: int) -> str:
        local = actions.open()
        try:
            actions.approve(local, UUID(race), hash_race, Principal.APPROVER,
                            approval_token=token_race, correlation_id="race")
            return "ok"
        except AppError as exc:
            return exc.code
        finally:
            local.close()

    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(attempt, range(8)))
    check("8 aprobaciones simultáneas ejecutan una vez",
          calls["demo_delete"] == before + 1 and results.count("ok") == 1, results)
    check("la fila acaba executed", status_of(conn, race) == "executed", status_of(conn, race))

    print("-- objetivos cambiados y caducidad")
    stale = dispatch("demo_delete", {"key": "d"}, agent(), actions=actions)["action_id"]
    hash_stale = actions.detail(conn, UUID(stale))["params_hash"]
    token_stale = actions.approval_token(conn, UUID(stale), Principal.APPROVER)
    revision["value"] = 2
    before = calls["demo_delete"]
    try:
        actions.approve(conn, UUID(stale), hash_stale, Principal.APPROVER, approval_token=token_stale, correlation_id="c")
        check("revisión cambiada da conflict", False)
    except AppError as exc:
        check("revisión cambiada da conflict", exc.code == "conflict", exc.code)
    check("sin ejecutar y sin reintento", calls["demo_delete"] == before and status_of(conn, stale) == "failed", status_of(conn, stale))
    revision["value"] = 1

    late = ActionService(db_path=settings.db_path, registry=actions.registry,
                         engine=PermissionEngine(("demo.*",)), signer=ApprovalSigner(), ttl_seconds=-1)
    gone = dispatch("demo_delete", {"key": "e"}, agent(), actions=late)["action_id"]
    hash_gone = late.detail(conn, UUID(gone))["params_hash"]
    token_gone = late.approval_token(conn, UUID(gone), Principal.APPROVER)
    before = calls["demo_delete"]
    try:
        late.approve(conn, UUID(gone), hash_gone, Principal.APPROVER, approval_token=token_gone, correlation_id="c")
        check("caducada no se aprueba", False)
    except AppError as exc:
        check("caducada: 410", exc.status_code == 410, exc.status_code)
    check("caducar no ejecuta", calls["demo_delete"] == before and status_of(conn, gone) == "expired")

    print("-- reglas del motor")
    check("no registrada: denegada", dispatch("rm_rf", {}, agent(), actions=actions)["status"] == "error")
    check("sin turno por MCP: denegada",
          dispatch("demo_read", {"key": "x"}, ActorContext(Principal.AGENT, Origin.MCP, "c"), actions=actions)["error"]["code"] == "no_active_turn")
    result = dispatch("audit_wipe", {"key": "x"}, agent(), actions=actions)
    check("audit.write denegado aunque el agente tenga audit.*", result["status"] == "error", result)
    result = dispatch("grant_self", {"key": "x"}, agent(), actions=actions)
    check("permissions.admin denegado aunque tenga permissions.*", result["status"] == "error", result)
    result = dispatch("demo_write", {"key": "t1"}, agent(tainted=True), actions=actions)
    check("turno contaminado: WRITE pasa a confirmar", result["status"] == "confirmation_required", result)
    result = dispatch("demo_bulk", {"count": 10}, agent(), actions=actions)
    check("10 entidades: confirmar", result["status"] == "confirmation_required", result)
    turn = str(uuid4())
    statuses = [dispatch("demo_bulk", {"count": 4}, agent(turn), actions=actions)["status"] for _ in range(3)]
    check("el troceo acumula en el turno", statuses == ["ok", "ok", "confirmation_required"], statuses)
    result = dispatch("demo_delete", {"key": "x", "extra": "CENTINELA"}, agent(), actions=actions)
    check("argumento extra rechazado sin eco", result["error"]["code"] == "validation_error" and "CENTINELA" not in json.dumps(result), result)
    for label, kwargs in {
        "sin extra=forbid": {"args_model": type("Loose", (ContractModel,), {"model_config": {"extra": "ignore"}})},
        "sin resumen": {"risk": RiskClass.CONFIRM, "summarize": None},
        "lectura que escribe": {"permission": "demo.read", "risk": RiskClass.WRITE},
        "auditar un secreto": {"audit": {"password": "log"}},
    }.items():
        try:
            base_args = {"name": "bad_spec", "permission": "demo.write", "risk": RiskClass.WRITE,
                         "args_model": Args, "handler": effect("demo_write"), "summarize": summary}
            ActionSpec(**{**base_args, **kwargs})
            check(f"spec inválida: {label}", False)
        except ValueError:
            check(f"spec inválida: {label}", True)
    try:
        actions.registry.register(SPECS[0])
        check("registro cerrado tras arrancar", False)
    except RuntimeError:
        check("registro cerrado tras arrancar", True)

    print("-- 409 de REST")
    pending = actions.execute_or_request(agent(), SPECS[0], Args(key="rest"))
    try:
        actions.unwrap(pending)
        check("unwrap lanza", False)
    except ConfirmationRequiredError as exc:
        ticket_model = exc.ticket
        check("ticket con hash", len(ticket_model.params_hash) == 64)
        import app.permissions.setup as setup_module
        from starlette.requests import Request
        response = await setup_module._confirmation_required(Request({"type": "http", "state": {"request_id": "r"}}), exc)
        payload = json.loads(response.body)
        check("409 con error y confirmation", response.status_code == 409 and payload["error"]["code"] == "confirmation_required" and payload["confirmation"]["id"] == ticket_model.id, payload)

    print("-- inmutabilidad")
    must_abort(conn, "args_json inmutable", "UPDATE pending_confirmations SET args_json='{}' WHERE id=?", (action,))
    must_abort(conn, "fila no borrable", "DELETE FROM pending_confirmations WHERE id=?", (action,))
    must_abort(conn, "INSERT OR REPLACE sobre confirmación",
               "INSERT OR REPLACE INTO pending_confirmations (id, tool_name, actor_type, origin, correlation_id, args_json, args_hash, summary, risk, status, created_at, expires_at) "
               "VALUES (?, 't', 'user', 'rest', 'c', '{}', 'h', 's', 'confirm', 'pending', 'x', 'x')", (action,))
    must_abort(conn, "executed no vuelve a pending", "UPDATE pending_confirmations SET status='pending', decided_at=NULL, decided_via=NULL WHERE id=?", (action,))
    any_event = conn.execute("SELECT id, seq FROM audit_events LIMIT 1").fetchone()
    must_abort(conn, "auditoría sin UPDATE", "UPDATE audit_events SET result='success' WHERE id=?", (any_event[0],))
    must_abort(conn, "auditoría sin DELETE", "DELETE FROM audit_events")
    must_abort(conn, "auditoría sin REPLACE",
               "INSERT OR REPLACE INTO audit_events (seq, id, occurred_at, correlation_id, actor_type, origin, action, result) "
               "VALUES (?, ?, '2026-01-01T00:00:00.000Z', 'c', 'user', 'rest', 'x', 'success')", (any_event[1], any_event[0]))

    print("-- fallo cerrado")
    other_conn = actions.open()
    other_conn.execute("CREATE TRIGGER block_audit BEFORE INSERT ON audit_events WHEN new.action = 'demo_write' AND new.result = 'success' BEGIN SELECT raise(ABORT, 'audit down'); END")
    result = dispatch("demo_write", {"key": "no_audit"}, ActorContext(Principal.UI, Origin.REST, "c"), actions=actions)
    check("sin auditoría no se escribe", result["status"] == "error" and conn.execute("SELECT count(*) FROM settings WHERE key='no_audit'").fetchone()[0] == 0, result)
    other_conn.execute("DROP TRIGGER block_audit")
    other_conn.close()
    result = dispatch("demo_write", {"key": "with_audit"}, ActorContext(Principal.UI, Origin.REST, "c"), actions=actions)
    check("con auditoría sí", result["status"] == "ok" and conn.execute("SELECT count(*) FROM settings WHERE key='with_audit'").fetchone()[0] == 1, result)

    print("-- corte a mitad y reconciliación")
    crash = dispatch("demo_external", {"key": "f"}, agent(), actions=actions)["action_id"]
    left = dispatch("demo_delete", {"key": "g"}, agent(), actions=actions)["action_id"]
    moment = "2026-01-01T00:00:00.000Z"
    conn.execute("UPDATE pending_confirmations SET status='approved', decided_at=?, decided_via='desktop' WHERE id=?", (moment, crash))
    conn.execute("UPDATE pending_confirmations SET status='executing' WHERE id=?", (crash,))
    before = calls["demo_external"]
    report = actions.reconcile_on_boot(conn)
    check("executing pasa a failed sin repetir", status_of(conn, crash) == "failed" and calls["demo_external"] == before and report.failed == 1, report)
    check("pending caduca al arrancar", status_of(conn, left) == "expired")
    code = conn.execute("SELECT error_code FROM pending_confirmations WHERE id=?", (crash,)).fetchone()[0]
    check("marcado outcome_uncertain", code == "outcome_uncertain", code)

    print("-- secretos fuera de auditoría y de la tabla de eventos")
    dump = json.dumps(conn.execute("SELECT * FROM audit_events").fetchall())
    check("sin contraseña", "s3cret-value" not in dump)
    check("sin token de aprobación", token not in dump)
    check("sin tokens de sesión", session not in dump and approver not in dump)
    check("params_hash, turno y taint registrados",
          conn.execute("SELECT count(*) FROM audit_events WHERE params_hash IS NOT NULL AND turn_id IS NOT NULL").fetchone()[0] > 0)

    conn.close()
    await stop_security(app, settings)
    check("el archivo de approver desaparece al parar", not handoff.exists())


if __name__ == "__main__":
    root = Path(tempfile.mkdtemp(prefix="drakter-confirmations-"))
    try:
        asyncio.run(main(root))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print(f"\n{len(FAILURES)} fallos" + (": " + ", ".join(FAILURES) if FAILURES else ""))
    sys.exit(1 if FAILURES else 0)
