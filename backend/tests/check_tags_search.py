#!/usr/bin/env python3
"""Comprobacion rapida de etiquetas y busqueda global.

Uso (desde backend/): TMPDIR=/var/tmp/drakter-almacen-relaciones venv/bin/python tests/check_tags_search.py
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

import storage_tool_stub  # noqa: E402

storage_tool_stub.install()

from fastapi.testclient import TestClient  # noqa: E402

from app.api import relations_tags as tags_api  # noqa: E402
from app.api import storage as storage_api  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.tools import tags as tag_tools  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    print(f"{'OK  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  [{detail}]"), flush=True)
    if not cond:
        FAILS.append(name)


def main() -> int:
    check("tools: extra=forbid", all(t.args_model.model_config.get("extra") == "forbid" for t in tag_tools.TOOLS))
    check("tools: esquemas", all(t.args_model.model_json_schema() and t.result_model.model_json_schema()
                                 for t in tag_tools.TOOLS))
    root = Path(tempfile.mkdtemp(prefix="drakter-tags-"))
    settings = Settings(data_dir=root / "data", runtime_dir=root / "run")
    app = create_app(settings)
    app.include_router(storage_api.router)
    app.include_router(tags_api.router)
    with TestClient(app, base_url=f"http://127.0.0.1:{settings.port}", client=("127.0.0.1", 50000)) as c:
        c.headers["Authorization"] = f"Bearer {app.state.token.reveal()}"
        r = c.post("/api/v1/resources", json={"title": "Apuntes de redes", "resource_type": "note",
                                               "note_body": "Texto", "tags": ["redes"]})
        nid = r.json()["id"]
        r = c.post("/api/v1/resources", json={"title": "Otro de redes", "resource_type": "link",
                                               "url": "https://example.com/x"})
        old = r.json()["id"]

        r = c.get("/api/v1/search", params={"q": "redes"})
        check("buscar 'redes' encuentra 2", r.status_code == 200 and len(r.json()["items"]) == 2, r.text)
        hit = r.json()["items"][0] if r.status_code == 200 and r.json()["items"] else {}
        check("hit con forma del contrato", hit.get("content_trust") == "untrusted"
              and hit.get("entity_type") == "resource" and "snippet" in hit and hit.get("title"), hit)
        r = c.get("/api/v1/search", params={"q": '"redes AND (x'})
        check("comillas/sintaxis FTS no rompen", r.status_code == 200, r.text)
        r = c.get("/api/v1/search", params={"q": "redes", "types": "task"})
        check("filtro types", r.status_code == 200 and r.json()["items"] == [], r.text)
        r = c.get("/api/v1/search", params={"q": "redes", "limit": 1})
        check("paginacion", r.status_code == 200 and r.json()["next_cursor"], r.text)
        r = c.get("/api/v1/search", params={"q": "redes", "limit": 500})
        check("limit > 100 es 422", r.status_code == 422, r.status_code)

        r = c.put(f"/api/v1/entities/{nid}/tags", json={"names": ["Fisica", "fisica", " Examen "]})
        check("PUT sustituye", r.status_code == 200 and sorted(t["name"] for t in r.json()["items"]) == ["Examen", "Fisica"], r.text)
        r = c.get(f"/api/v1/entities/{nid}/tags")
        check("GET entidad", r.status_code == 200 and len(r.json()["items"]) == 2, r.text)
        r = c.get("/api/v1/search", params={"q": "fisica"})
        check("el indice refleja la etiqueta nueva", [h["entity_id"] for h in r.json()["items"]] == [nid], r.text)
        r = c.get("/api/v1/tags", params={"q": "fis"})
        check("listar tags con q", r.status_code == 200 and [t["name"] for t in r.json()["items"]] == ["Fisica"]
              and r.json()["items"][0]["usage_count"] == 1, r.text)
        r = c.put(f"/api/v1/entities/{'0' * 8}-0000-0000-0000-{'0' * 12}/tags", json={"names": ["x"]})
        check("entidad inexistente 404", r.status_code == 404, r.text)
        r = c.put(f"/api/v1/entities/{nid}/tags", json={"names": ["a"], "extra": 1})
        check("extra prohibido 422", r.status_code == 422, r.status_code)

        with sqlite3.connect(settings.db_path) as raw:
            raw.execute("UPDATE entities SET archived_at='2026-01-01T00:00:00.000Z' WHERE id=?", (nid,))
        r = c.get("/api/v1/search", params={"q": "fisica"})
        check("archivado fuera de la busqueda", r.status_code == 200 and r.json()["items"] == [], r.text)
    print("FALLOS: " + ", ".join(FAILS) if FAILS else "TODO OK")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
