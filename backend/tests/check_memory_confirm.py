#!/usr/bin/env python3
"""Olvidar y aprobar un recuerdo desde la GUI pasan por el camino único (CLAUDE.md §4, excepción 2).

Uso (desde backend/): TMPDIR=/var/tmp/drakter-mem .venv/bin/python tests/check_memory_confirm.py
"""
from __future__ import annotations

import asyncio
import secrets
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent / "critical"))

from check_confirmations import PORT, asgi  # noqa: E402

from app.core.bootstrap import Credentials  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.core.security import SessionToken  # noqa: E402
from app.database.migrator import migrate  # noqa: E402
from app.main import create_app  # noqa: E402
from app.permissions.setup import start_security, stop_security  # noqa: E402

RESULTS: list[bool] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    RESULTS.append(bool(cond))
    print(f"{'OK  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  [{detail}]"))


async def main(root: Path) -> None:
    settings = Settings(data_dir=root / "data", _env_file=None)
    (root / "data" / "backups").mkdir(parents=True, mode=0o700)
    migrate(settings.db_path, settings.backups_dir)
    session, approver = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    app = create_app(settings, credentials=Credentials(ui=SessionToken(session), approver=SessionToken(approver)),
                     port=PORT, on_ready=lambda: None)
    await start_security(app)
    ui = {"authorization": f"Bearer {session}"}
    main_process = {"authorization": f"Bearer {approver}"}
    mem = "/api/v1/memory"
    try:
        code, body = await asgi(app, "POST", mem, ui, {"kind": "semantic", "category": "preferences",
                                                        "content": "Prefiero el té verde"})
        check("crear (control)", code == 201, (code, body))
        mid = body["record"]["id"]

        code, body = await asgi(app, "POST", f"{mem}/{mid}/forget", ui, {"confirmation_id": "x"})
        check("un confirmation_id en el cuerpo no salta la confirmación: 409", code == 409, (code, body))
        code, body = await asgi(app, "POST", f"{mem}/{mid}/forget", ui)
        check("forget: 409 confirmation_required", code == 409 and "confirmation_required" in str(body), (code, body))
        action, ph = (body["confirmation"]["id"], body["confirmation"]["params_hash"]) if code == 409 else ("", "")
        code, _ = await asgi(app, "GET", f"{mem}/{mid}", ui)
        check("sigue existiendo antes de aprobar", code == 200, code)
        code, _ = await asgi(app, "POST", f"/api/v1/confirmations/{action}/approve", ui, {})
        check("token ui no aprueba: 403", code == 403, code)
        code, _ = await asgi(app, "GET", f"{mem}/{mid}", ui)
        check("sigue existiendo tras el 403", code == 200, code)
        code, body = await asgi(app, "POST", f"/api/v1/confirmations/{action}/approve", main_process, {"params_hash": ph})
        check("approver aprueba: 200 executed", code == 200 and "executed" in str(body), (code, body))
        code, _ = await asgi(app, "GET", f"{mem}/{mid}", ui)
        check("borrado tras aprobar: 404", code == 404, code)
        code, _ = await asgi(app, "POST", f"/api/v1/confirmations/{action}/approve", main_process, {"params_hash": ph})
        check("segunda aprobación no repite", code != 200, code)

        code, body = await asgi(app, "POST", "/api/v1/memory/search", ui, {"text": "x"})
        code, body = await asgi(app, "POST", mem, ui, {"kind": "semantic", "category": "entities",
                                                        "content": "Drakter es mi agente"})
        rid = body["record"]["id"]
        await asgi(app, "POST", f"{mem}/{rid}/reject", ui)
        code, body = await asgi(app, "POST", f"{mem}/{rid}/approve", ui)
        check("approve: 409", code == 409, (code, body))
        action, ph = (body["confirmation"]["id"], body["confirmation"]["params_hash"]) if code == 409 else ("", "")
        code, rec = await asgi(app, "GET", f"{mem}/{rid}", ui)
        check("sigue rechazado antes de aprobar", rec["status"] == "rejected", rec)
        code, body = await asgi(app, "POST", f"/api/v1/confirmations/{action}/approve", main_process, {"params_hash": ph})
        code, rec = await asgi(app, "GET", f"{mem}/{rid}", ui)
        check("approver aprueba: queda approved", rec["status"] == "approved", (code, body, rec))
        await asgi(app, "POST", mem, ui, {"kind": "semantic", "category": "preferences", "subject": "bebida",
                                           "content": "Me gusta el café"})
        code, body = await asgi(app, "POST", mem, ui, {"kind": "semantic", "category": "preferences",
                                                        "subject": "bebida", "content": "No me gusta el café"})
        code, body = await asgi(app, "POST", f"{mem}/{body['record']['id']}/approve", ui)
        check("approve con conflicto abierto: 409 memory_conflict_open sin fila", code == 409
              and "memory_conflict_open" in str(body) and "confirmation" not in body, (code, body))
        code, _ = await asgi(app, "POST", f"{mem}/00000000-0000-4000-8000-000000000000/forget", ui)
        check("forget de un id inexistente: 404 sin fila", code == 404, code)
    finally:
        await stop_security(app)


if __name__ == "__main__":
    tmp = Path(tempfile.mkdtemp(prefix="drakter-memconf-"))
    try:
        asyncio.run(main(tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nResumen: {sum(RESULTS)}/{len(RESULTS)} OK")
    sys.exit(0 if all(RESULTS) else 1)
