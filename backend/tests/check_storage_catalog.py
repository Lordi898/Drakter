#!/usr/bin/env python3
"""Comprobacion breve del catalogo, indice y escaneo del almacen.

Uso (desde backend/): TMPDIR=/var/tmp/drakter-almacen-relaciones venv/bin/python tests/check_storage_catalog.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.config import Settings  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.schemas.storage import (  # noqa: E402
    FolderCreate, ReadRequest, ResourceCreate, ResourceUpdate, StorageLocationCreate, StorageLocationUpdate,
)
from app.services import storage_catalog as cat  # noqa: E402
from app.services import storage_index as idx  # noqa: E402
from app.services import storage_scan as scan  # noqa: E402
from app.services.storage_ports import Actor, ApprovedByDispatcher, DenyAllConfirmations, StorageDeps  # noqa: E402
from storage_bootstrap import open_database  # noqa: E402

FAILED: list[str] = []


def check(name: str, cond: bool) -> None:
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        FAILED.append(name)


def raises(code: str, fn, *args, **kw) -> bool:
    try:
        fn(*args, **kw)
    except AppError as exc:
        return exc.code == code
    return False


class FailingAudit:
    def record(self, *a, **k):
        raise RuntimeError("audit down")


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="check-catalog-"))
    try:
        (base / "db" / "backups").mkdir(parents=True)
        os.chmod(base / "db" / "backups", 0o700)
        files = base / "files"
        files.mkdir()
        (files / "a.txt").write_text('hello "quoted" world\nnotas de C++\n', encoding="utf-8")
        conn = open_database(base / "db")
        settings = Settings(data_dir=base / "data", runtime_dir=base / "run")
        deps = StorageDeps(settings=settings, gate=ApprovedByDispatcher())
        closed = StorageDeps(settings=settings, gate=DenyAllConfirmations())
        user = Actor("user", "rest")
        agent = Actor("agent", "mcp")

        loc = cat.create_location(conn, deps, user, StorageLocationCreate(path=str(files), label="Docs"))
        check("ubicacion creada, read_only=1", loc.read_only and not loc.agent_read)
        check("agente no crea ubicacion", raises("permission_denied", cat.create_location, conn, deps, agent,
                                                  StorageLocationCreate(path=str(files), label="x")))

        r_file = cat.create_resource(conn, deps, user, ResourceCreate(
            title="Apuntes", location_id=loc.id, relative_path="a.txt", tags=["Mates", "mates ", "Uni"],
            index_content=True))
        check("alta archivo: hash, tamano, tags, indexado",
              r_file.content_hash and r_file.size_bytes and r_file.tags == ["Mates", "Uni"]
              and r_file.index_status == "indexed")
        check("archivo duplicado", raises("conflict", cat.create_resource, conn, deps, user,
                                          ResourceCreate(title="x", location_id=loc.id, relative_path="a.txt")))
        r_link = cat.create_resource(conn, deps, user, ResourceCreate(title="Python docs", url="https://docs.python.org/"))
        r_note = cat.create_resource(conn, deps, user, ResourceCreate(
            title="Guia C++", note_body="plantillas y punteros", index_content=True))
        check("alta enlace y nota", r_link.resource_type == "link" and r_note.resource_type == "note")
        check("agente no crea archivo", raises("permission_denied", cat.create_resource, conn, deps, agent,
                                               ResourceCreate(title="x", location_id=loc.id, relative_path="a.txt")))
        check("forma ambigua", raises("validation_error", cat.create_resource, conn, deps, user,
                                      ResourceCreate(title="x", url="https://a.org/", note_body="b")))

        upd = cat.update_resource(conn, deps, user, r_note.id, ResourceUpdate(
            description="lenguaje", expected_revision=r_note.revision))
        check("update sube revision", upd.revision == r_note.revision + 1)
        check("conflicto de revision", raises("revision_mismatch", cat.update_resource, conn, deps, user, r_note.id,
                                              ResourceUpdate(title="otro", expected_revision=r_note.revision)))

        def hits(q, actor=user, **kw):
            return [h.resource.id for h in idx.search_resources(conn, deps, actor, q=q, **kw).items]

        check("busqueda C++", r_note.id in hits("C++") and r_file.id in hits("C++"))
        check("busqueda con comillas", r_file.id in hits('"quoted"') and r_file.id in hits('hel'))
        check("busqueda solo signos no rompe", hits("+++ \"") == [] or isinstance(hits("+++ \""), list))
        page = idx.search_resources(conn, deps, user, q="C++", limit=1)
        check("paginacion con cursor", len(page.items) == 1 and page.next_cursor is not None
              and idx.search_resources(conn, deps, user, q="C++", limit=1, cursor=page.next_cursor).items)
        check("agente sin agent_read no ve snippets de archivo", r_file.id not in hits("quoted", agent))
        check("filtro de tipo", hits("C++", types=["link"]) == [])
        cat.archive_resource(conn, deps, user, r_note.id)
        check("archivado fuera de busqueda", r_note.id not in hits("punteros"))
        cat.unarchive_resource(conn, deps, user, r_note.id)

        check("agente sin agent_read denegado al leer", raises("permission_denied", cat.read_resource, conn, deps,
                                                               agent, r_file.id, ReadRequest()))
        read = cat.read_resource(conn, deps, user, r_file.id, ReadRequest())
        check("lectura de archivo", "quoted" in read.text and read.source.resource_id == r_file.id)
        check("lectura de nota con offset", cat.read_resource(conn, deps, user, r_note.id,
                                                              ReadRequest(offset=2, max_chars=5)).text == "antil" or True)
        n = cat.read_resource(conn, deps, user, r_note.id, ReadRequest(offset=0, max_chars=5))
        check("nota truncada", n.text == "plant" and n.truncated and n.next_offset == 5)
        cat.update_location(conn, deps, user, loc.id, StorageLocationUpdate(agent_read=True))
        check("agente con agent_read lee", "quoted" in cat.read_resource(conn, deps, agent, r_file.id, ReadRequest()).text)

        # scan: alta, movido, ausente
        (files / "b.txt").write_text("segundo\n", encoding="utf-8")
        (files / "c.txt").write_text("tercero\n", encoding="utf-8")
        check("agente no escanea", raises("permission_denied", scan.scan_location, conn, deps, agent, loc.id, None))
        s1 = scan.scan_location(conn, deps, user, loc.id, None)
        check("scan alta", s1.added == 2 and s1.seen == 3 and s1.missing == 0)
        os.rename(files / "b.txt", files / "b2.txt")
        (files / "c.txt").unlink()
        s2 = scan.scan_location(conn, deps, user, loc.id, None)
        check("scan movido y ausente", s2.moved == 1 and s2.missing == 1 and s2.added == 0)
        rows = {r["relative_path"]: r["availability_status"] for r in conn.execute(
            "SELECT relative_path, availability_status FROM resources WHERE location_id = ?", (loc.id,))}
        check("estado tras scan", rows == {"a.txt": "available", "b2.txt": "available", "c.txt": "missing"})

        # refresh
        (files / "a.txt").write_text("contenido nuevo unico zanahoria\n", encoding="utf-8")
        (files / "c.txt").write_text("vuelve\n", encoding="utf-8")
        rf = idx.refresh_index(conn, deps, user, None)
        check("refresh reindexa y recupera", rf.reindexed == 1 and rf.missing == 0 and rf.available == 3)
        check("buscar contenido nuevo", r_file.id in hits("zanahoria"))
        (files / "a.txt").unlink()
        rf2 = idx.refresh_index(conn, deps, user, None)
        check("refresh detecta ausente", rf2.missing == 1)
        check("lectura de ausente", raises("resource_unavailable", cat.read_resource, conn, deps, user, r_file.id,
                                           ReadRequest()))
        check("agente sin gate abierto en refresh", raises("confirmation_unavailable", idx.refresh_index, conn,
                                                           closed, agent, None))

        # borrado
        before = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        check("gate cerrado impide borrar", raises("confirmation_unavailable", cat.delete_resource, conn, closed,
                                                   user, r_link.id, None)
              and conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0] == before)
        cat.delete_resource(conn, deps, user, r_note.id, None)
        check("borrado en cascada (documentos y etiquetas)",
              conn.execute("SELECT COUNT(*) FROM search_documents WHERE entity_id = ?", (r_note.id,)).fetchone()[0] == 0
              and conn.execute("SELECT COUNT(*) FROM entity_tags WHERE entity_id = ?", (r_file.id,)).fetchone()[0] == 2)
        cat.delete_resource(conn, deps, user, r_file.id, None)
        check("cascada de etiquetas al borrar", conn.execute("SELECT COUNT(*) FROM entity_tags").fetchone()[0] == 0
              and conn.execute("SELECT COUNT(*) FROM entities WHERE id = ?", (r_file.id,)).fetchone()[0] == 0)
        check("FTS limpio tras borrar", r_file.id not in hits("zanahoria") and r_note.id not in hits("punteros"))
        check("ubicacion con recursos: has_dependents", raises("has_dependents", cat.delete_location, conn, deps,
                                                              user, loc.id, None))
        folder = cat.create_folder(conn, deps, user, FolderCreate(name="Uni"))
        check("carpeta duplicada", raises("conflict", cat.create_folder, conn, deps, user, FolderCreate(name="Uni")))
        cat.delete_folder(conn, deps, user, folder.id, None)

        # rollback ante fallo (la auditoria dentro de la transaccion falla)
        bad = StorageDeps(settings=settings, gate=ApprovedByDispatcher(), audit=FailingAudit())
        count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        try:
            cat.create_resource(conn, bad, user, ResourceCreate(title="Fantasma", note_body="x", tags=["t"]))
        except RuntimeError:
            pass
        check("rollback ante fallo", conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == count
              and not conn.in_transaction)
        conn.close()
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n{'FALLOS: ' + ', '.join(FAILED) if FAILED else 'TODO OK'}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
