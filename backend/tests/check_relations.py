"""Comprobación breve de integridad de relaciones (CLAUDE.md §4). Uso: python -m tests.check_relations"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import storage_tool_stub  # noqa: E402

storage_tool_stub.install()

from app.core.errors import AppError  # noqa: E402
from app.schemas.relations import RelationshipCreate, RelationshipSearch, RelationshipUpdate  # noqa: E402
from app.services import relations as svc  # noqa: E402
from app.services.storage_ports import (  # noqa: E402
    Actor, ApprovedByDispatcher, DenyAllConfirmations, StorageDeps, utc_now,
)
from tests.storage_bootstrap import open_database  # noqa: E402

os.environ.setdefault("TMPDIR", "/var/tmp/drakter-almacen-relaciones")
NOW = utc_now()
FAILS: list[str] = []


def check(name: str, ok: bool) -> None:
    print(("OK   " if ok else "FAIL ") + name)
    if not ok:
        FAILS.append(name)


def raises(code: str, fn, detail: str | None = None) -> bool:  # noqa: ANN001
    try:
        fn()
    except AppError as exc:
        return exc.code == code and (detail is None or any(d.code == detail for d in exc.details))
    return False


def main() -> int:
    tmp = Path(tempfile.mkdtemp(dir=os.environ["TMPDIR"]))
    conn = open_database(tmp)
    settings = SimpleNamespace(db_path=tmp / "drakter.db", data_dir=tmp, runtime_dir=tmp)
    deps = StorageDeps(settings=settings, gate=DenyAllConfirmations())  # type: ignore[arg-type]
    user, agent = Actor("user", "rest"), Actor("agent", "mcp")

    def entity(kind: str, sql: str, *params: object) -> str:
        eid = str(uuid4())
        conn.execute("INSERT INTO entities (id, entity_type, created_at, updated_at) VALUES (?,?,?,?)",
                     (eid, kind, NOW, NOW))
        conn.execute(sql, (eid, *params))
        return eid

    project = entity("project", "INSERT INTO projects (id, name) VALUES (?,?)", "Proyecto A")
    project2 = entity("project", "INSERT INTO projects (id, name) VALUES (?,?)", "Proyecto B")
    subject = entity("subject", "INSERT INTO subjects (id, name) VALUES (?,?)", "Asignatura A")
    task = entity("task", "INSERT INTO tasks (id, title, project_id, subject_id) VALUES (?,?,?,?)",
                  "Tarea A", project, subject)
    task2 = entity("task", "INSERT INTO tasks (id, title) VALUES (?,?)", "Tarea B")
    event = entity("calendar_event",
                   "INSERT INTO calendar_events (id, title, timezone, local_start, local_end, starts_at_utc,"
                   " ends_at_utc) VALUES (?,?,?,?,?,?,?)", "Evento", "Europe/Madrid",
                   "2026-01-01T10:00", "2026-01-01T11:00", "2026-01-01T09:00:00.000Z", "2026-01-01T10:00:00.000Z")
    res = entity("resource", "INSERT INTO resources (id, title, resource_type, url) VALUES (?,?,?,?)",
                 "Enlace", "link", "https://example.com")
    old = entity("resource", "INSERT INTO resources (id, title, resource_type, url) VALUES (?,?,?,?)",
                 "Viejo", "link", "https://example.org")

    def rel(s: str, t: str, kind: str, actor: Actor = user):  # noqa: ANN202
        return svc.create_relationship(conn, deps, actor,
                                       RelationshipCreate(source_id=s, target_id=t, relationship_type=kind))

    # Seis combinaciones de la checklist
    items = svc.get_related_items(conn, deps, user, task).items
    check("tarea-proyecto virtual", any(i.virtual and i.entity_id == project and i.direction == "out"
                                        and i.relationship_id is None for i in items))
    check("tarea-asignatura virtual", any(i.virtual and i.entity_id == subject for i in items))
    r1 = rel(task, res, "uses_resource")
    check("tarea-recurso", r1.source_type == "task" and r1.target_type == "resource")
    r2 = rel(task, event, "scheduled_for")
    check("tarea-calendario", r2.target_type == "calendar_event")
    check("proyecto-recurso", rel(project, res, "uses_resource").source_type == "project")
    check("asignatura-recurso", rel(subject, res, "uses_resource").source_type == "subject")

    # Consulta inversa, etiquetas, títulos, filtros
    inv = svc.get_related_items(conn, deps, user, res).items
    ins = [i for i in inv if i.direction == "in" and i.relationship_type == "uses_resource"]
    check("consulta inversa (3 entrantes, etiqueta inversa)",
          len(ins) == 3 and all(i.label == "es usado por" for i in ins)
          and {i.entity_title for i in ins} == {"Tarea A", "Proyecto A", "Asignatura A"})
    pin = svc.get_related_items(conn, deps, user, project)
    check("virtual entrante proyecto<-tarea",
          any(i.virtual and i.direction == "in" and i.entity_id == task and i.label == "contiene"
              for i in pin.items))
    check("filtro direction/tipo", all(
        i.direction == "out" for i in svc.get_related_items(conn, deps, user, task, direction="out").items)
          and {i.relationship_type for i in svc.get_related_items(
              conn, deps, user, task, relationship_type="scheduled_for").items} == {"scheduled_for"})

    # Regla inválida (sin datos en el mensaje)
    try:
        rel(res, task, "depends_on")
        check("regla inválida", False)
    except AppError as exc:
        check("regla inválida", exc.code == "relationship_not_allowed" and "Enlace" not in exc.message
              and "resource" in exc.message)
    check("autorrelación", raises("relationship_not_allowed", lambda: rel(task, task, "related_to")))
    check("entidad ausente", raises("not_found", lambda: rel(task, str(uuid4()), "related_to")))

    # Ciclo depends_on
    rel(task, task2, "depends_on")
    check("ciclo depends_on", raises("hierarchy_cycle", lambda: rel(task2, task, "depends_on")))
    check("duplicado", raises("conflict", lambda: rel(task, task2, "depends_on"), "duplicate"))

    # Simétrica sin duplicado en ambos sentidos
    a, b = sorted((project, project2))
    first = rel(b, a, "related_to")
    check("simétrica normalizada", first.source_id == a and first.target_id == b
          and first.source_type == "project")
    check("simétrica sin duplicado", raises("conflict", lambda: rel(a, b, "related_to"), "duplicate")
          and raises("conflict", lambda: rel(b, a, "related_to"), "duplicate"))
    check("simétrica visible como salida en ambos lados", all(
        any(i.relationship_type == "related_to" and i.direction == "out" for i in
            svc.get_related_items(conn, deps, user, x).items) for x in (a, b)))

    # Entidad archivada
    conn.execute("UPDATE entities SET archived_at = ? WHERE id = ?", (NOW, old))
    check("entidad archivada", raises("conflict", lambda: rel(task, old, "uses_resource"), "entity_archived"))

    # Borrar entidad con relación: RESTRICT; luego detach_entity
    rel(task2, res, "uses_resource")  # una relación más sobre res
    try:
        conn.execute("DELETE FROM resources WHERE id = ?", (res,))
        restrict = False
    except sqlite3.IntegrityError:
        restrict = True
    check("borrar entidad con relación queda RESTRICT", restrict)
    check("count_for_entity", svc.count_for_entity(conn, res) == 4)
    conn.execute("BEGIN IMMEDIATE")
    removed = svc.detach_entity(conn, deps, user, res)
    conn.execute("COMMIT")
    check("detach_entity devuelve 4", removed == 4 and svc.count_for_entity(conn, res) == 0)
    conn.execute("DELETE FROM resources WHERE id = ?", (res,))
    check("borrado tras detach y sin huérfanos",
          conn.execute("SELECT COUNT(*) FROM v_orphan_entities").fetchone()[0] == 0
          and conn.execute("SELECT COUNT(*) FROM entities WHERE id = ?", (res,)).fetchone()[0] == 0)

    # search, types, update
    page = svc.search_relationships(conn, deps, user, RelationshipSearch(limit=1))
    page2 = svc.search_relationships(conn, deps, user, RelationshipSearch(limit=1, cursor=page.next_cursor))
    check("búsqueda con cursor", len(page.items) == 1 and page.next_cursor and page2.items
          and page.items[0].id != page2.items[0].id)
    types = svc.list_types(conn, deps, user)
    check("list_types", len(types) == 10 and next(
        t for t in types if t.relationship_type == "related_to").symmetric)
    upd = svc.update_relationship(conn, deps, user, first.id, RelationshipUpdate(metadata={"nota": 1}))
    check("update metadatos", upd.metadata == {"nota": 1})

    # Borrado: usuario sin gate, agente con gate cerrado y abierto
    check("agente con gate cerrado no borra", raises(
        "confirmation_unavailable", lambda: svc.delete_relationship(conn, deps, agent, first.id))
          and svc.search_relationships(conn, deps, user, RelationshipSearch(source_id=a)).items != [])
    open_deps = StorageDeps(settings=settings, gate=ApprovedByDispatcher())  # type: ignore[arg-type]
    svc.delete_relationship(conn, open_deps, agent, first.id)
    svc.delete_relationship(conn, open_deps, user, r2.id)
    check("borrado agente aprobado y usuario sin gate", raises(
        "not_found", lambda: svc.delete_relationship(conn, open_deps, user, r2.id)))
    n = conn.execute("SELECT COUNT(*) FROM audit_events WHERE action LIKE 'relations.%'").fetchone()[0]
    check("auditoría", n >= 10)

    # Herramientas (con sustituto de spec) y REST
    from app.tools import relations as tools  # noqa: PLC0415
    names = {t.name for t in tools.TOOLS}
    check("4 herramientas, delete CONFIRM", len(names) == 4 and next(
        t for t in tools.TOOLS if t.name == "delete_relationship").risk.value == "confirm")
    tools.configure_summary_source(tmp / "drakter.db")
    keep = rel(task, project2, "scheduled_for") if False else rel(task, res_alt(conn, entity), "uses_resource")
    summary = next(t for t in tools.TOOLS if t.name == "delete_relationship").summarize(
        tools.DeleteArgs(relationship_id=keep.id))
    check("summarize con tipo y títulos", "Tarea A" in summary and "uses_resource" not in summary
          and "usa el recurso" in summary)
    ctx = SimpleNamespace(turn_id=uuid4(), state=SimpleNamespace(settings=settings))
    spec = next(t for t in tools.TOOLS if t.name == "get_related_items")
    out = spec.handler(ctx, tools.RelatedArgs(entity_id=task))
    check("herramienta get_related_items", out.entity_id == task and len(out.items) >= 2)
    try:
        spec.handler(ctx, tools.RelatedArgs(entity_id=str(uuid4())))
        check("ToolError", False)
    except Exception as exc:  # noqa: BLE001
        check("ToolError not_found", getattr(exc, "code", "") == "not_found")

    try:
        from fastapi import FastAPI  # noqa: PLC0415
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from app.api import relations as api  # noqa: PLC0415
        app = FastAPI()
        app.state.settings = settings
        app.state.storage_deps = deps

        @app.middleware("http")
        async def rid(request, call_next):  # noqa: ANN001, ANN202
            request.scope.setdefault("state", {})["request_id"] = "t"
            return await call_next(request)
        app.include_router(api.router)
        from app.core.errors import install_error_handlers  # noqa: PLC0415
        install_error_handlers(app)
        client = TestClient(app)
        t = client.get("/api/v1/relationships/types")
        r = client.get(f"/api/v1/entities/{task}/related?direction=out")
        d = client.delete(f"/api/v1/relationships/{keep.id}")
        check("REST types/related/delete", t.status_code == 200 and len(t.json()) == 10
              and r.status_code == 200 and d.status_code == 503)
    except ImportError as exc:
        print(f"NO COMPROBADO REST: {exc}")
    conn.close()
    print("RESULTADO:", "FALLOS " + ", ".join(FAILS) if FAILS else "todo correcto")
    return 1 if FAILS else 0


def res_alt(conn: sqlite3.Connection, entity) -> str:  # noqa: ANN001
    return entity("resource", "INSERT INTO resources (id, title, resource_type, url) VALUES (?,?,?,?)",
                  "Otro", "link", "https://example.net")


if __name__ == "__main__":
    raise SystemExit(main())
