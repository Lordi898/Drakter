#!/usr/bin/env python3
"""Comprobacion rapida de las rutas REST y las herramientas del almacen.

Uso (desde backend/): TMPDIR=/var/tmp/drakter-almacen-relaciones venv/bin/python tests/check_storage_api.py
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

import storage_tool_stub  # noqa: E402

storage_tool_stub.install()

from fastapi.testclient import TestClient  # noqa: E402

from app.api import storage as storage_api  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.tools import storage as storage_tools  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    print(f"{'OK  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  [{detail}]"), flush=True)
    if not cond:
        FAILS.append(name)


def check_tools() -> None:
    names = [t.name for t in storage_tools.TOOLS]
    check("tools: nombres validos", all(re.fullmatch(r"[a-z][a-z0-9_]{2,47}", n) for n in names), names)
    check("tools: sin duplicados", len(set(names)) == len(names))
    check("tools: extra=forbid", all(t.args_model.model_config.get("extra") == "forbid" for t in storage_tools.TOOLS))
    check("tools: esquema JSON", all(t.args_model.model_json_schema() and t.result_model.model_json_schema()
                                     for t in storage_tools.TOOLS))
    check("tools: ninguna acepta rutas", not any(
        f in t.args_model.model_fields for t in storage_tools.TOOLS for f in ("path", "relative_path", "location_id")))
    refresh = next(t for t in storage_tools.TOOLS if t.name == "refresh_resource_index")
    check("tools: refresh es CONFIRM con summarize", refresh.risk.value == "confirm" and refresh.summarize is not None)
    check("tools: summarize devuelve texto", isinstance(refresh.summarize(refresh.args_model()), str))


def main() -> int:
    check_tools()
    root = Path(tempfile.mkdtemp(prefix="drakter-storage-api-"))
    settings = Settings(data_dir=root / "data", runtime_dir=root / "run")
    app = create_app(settings)
    app.include_router(storage_api.router)
    with TestClient(app, base_url=f"http://127.0.0.1:{settings.port}", client=("127.0.0.1", 50000)) as c:
        c.headers["Authorization"] = f"Bearer {app.state.token.reveal()}"

        r = c.post("/api/v1/resources", json={"title": "Apuntes de redes", "resource_type": "note",
                                               "note_body": "El protocolo zanahoria usa puertos altos.",
                                               "tags": ["redes"], "index_content": True})
        check("crear nota 201", r.status_code == 201, r.text)
        note_id = r.json().get("id")
        r = c.post("/api/v1/resources", json={"title": "Documentacion", "resource_type": "link",
                                               "url": "https://example.com/docs"})
        check("crear enlace 201", r.status_code == 201, r.text)

        r = c.get("/api/v1/resources", params={"limit": 10})
        check("listar 2 recursos", r.status_code == 200 and len(r.json()["items"]) == 2, r.text)
        r = c.get("/api/v1/resources", params={"type": "note", "tag": "redes"})
        check("listar filtrado", r.status_code == 200 and len(r.json()["items"]) == 1, r.text)
        r = c.get("/api/v1/resources", params={"limit": 500})
        check("limit > 100 es 422", r.status_code == 422, r.status_code)

        r = c.post(f"/api/v1/resources/{note_id}/index")
        check("indexar nota", r.status_code == 200, r.text)
        r = c.get("/api/v1/resources/search", params={"q": "redes"})
        check("buscar encuentra la nota", r.status_code == 200 and any(
            h["resource"]["id"] == note_id for h in r.json()["items"]), r.text)
        r = c.get("/api/v1/resources/not-a-uuid")
        check("id no UUID es 422", r.status_code == 422, r.status_code)
        r = c.get(f"/api/v1/resources/{note_id}")
        check("obtener recurso", r.status_code == 200 and r.json()["id"] == note_id, r.text)

        r = c.post(f"/api/v1/resources/{note_id}/read", json={"max_chars": 100})
        check("leer nota", r.status_code == 200 and "zanahoria" in r.json()["text"]
              and r.json()["content_trust"] == "untrusted", r.text)

        r = c.delete(f"/api/v1/resources/{note_id}")
        check("DELETE sin gate real: 503 confirmation_unavailable (o 409 confirmation_required)",
              (r.status_code, r.json()["error"]["code"]) in {(503, "confirmation_unavailable"),
                                                             (409, "confirmation_required")}, r.text)
        r = c.get(f"/api/v1/resources/{note_id}")
        check("la nota sigue ahi", r.status_code == 200, r.text)
    print("FALLOS: " + ", ".join(FAILS) if FAILS else "TODO OK")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
