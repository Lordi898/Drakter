#!/usr/bin/env python3
"""Comprobacion breve del esquema v1 (excepcion 3 y 2 de CLAUDE.md §4).

Uso, desde backend/: TMPDIR=/var/tmp/drakter-contratos python3 migrations/check_migrations.py
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.backup import create_backup, restore_backup  # noqa: E402
from app.database.connection import connect  # noqa: E402
from app.database.migrator import migrate  # noqa: E402

NOW = "2026-11-04T10:00:00.000Z"
FAILS: list[str] = []
REQUIRED_TRIGGERS = {
    *(f"trg_{t}_delete_entity" for t in ("tasks", "projects", "subjects", "habits", "calendar_events", "time_blocks", "class_sessions", "resources", "folders")),
    "trg_tasks_no_cycle", "trg_folders_no_cycle", "trg_relationships_no_cycle",
    "trg_audit_no_update", "trg_audit_no_delete", "trg_audit_no_replace",
    "trg_pc_transition", "trg_pc_immutable", "trg_pc_no_delete", "trg_pc_no_replace",
    "trg_pc_identity", "trg_pc_born_pending", "trg_pc_closed", "trg_pc_decided_once",
    "trg_search_ai", "trg_search_ad", "trg_search_au",
    "trg_memory_records_ai", "trg_memory_records_au", "trg_memory_records_ad",
}


def ok(name: str, cond: bool) -> None:
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        FAILS.append(name)


def rejected(conn: sqlite3.Connection, name: str, sql: str, args: tuple = ()) -> None:
    try:
        conn.execute(sql, args)
    except sqlite3.Error:
        ok(name, True)
    else:
        ok(name, False)


def new_id() -> str:
    return str(uuid.uuid4())


def entity(conn: sqlite3.Connection, kind: str) -> str:
    eid = new_id()
    conn.execute("INSERT INTO entities (id, entity_type, created_at, updated_at) VALUES (?,?,?,?)", (eid, kind, NOW, NOW))
    return eid


def task(conn: sqlite3.Connection, title: str = "t") -> str:
    tid = entity(conn, "task")
    conn.execute("INSERT INTO tasks (id, title) VALUES (?,?)", (tid, title))
    return tid


def relate(conn: sqlite3.Connection, kind: str, source: str, target: str, a: str = "task", b: str = "task") -> None:
    conn.execute(
        "INSERT INTO relationships (id, source_id, source_type, target_id, target_type, relationship_type, created_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (new_id(), source, a, target, b, kind, NOW),
    )


def audit(conn: sqlite3.Connection, aid: str, verb: str = "INSERT") -> None:
    conn.execute(
        f"{verb} INTO audit_events (id, occurred_at, correlation_id, actor_type, origin, action, result)"
        " VALUES (?,?,?,?,?,?,?)",
        (aid, NOW, "c", "agent", "mcp", "x", "success"),
    )


def confirmation(conn: sqlite3.Connection, verb: str = "INSERT", cid: str | None = None) -> str:
    cid = cid or new_id()
    conn.execute(
        f"{verb} INTO pending_confirmations (id, tool_name, actor_type, origin, correlation_id, args_json, args_hash,"
        " summary, risk, created_at, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (cid, "delete_task", "agent", "mcp", "c", "{}", "h", "s", "confirm", NOW, NOW),
    )
    return cid


def run(root: Path) -> None:
    db, backups = root / "d.db", root / "backups"
    old_dir = root / "v10"
    old_dir.mkdir()
    for sql in sorted(Path(__file__).parent.glob("00*.sql"))[:10]:
        shutil.copy(sql, old_dir)
    migrate(db, backups, old_dir)
    conn = connect(db)
    try:
        for key, raw in (("default_timezone", '"Europe/Madrid"'), ("bulk_threshold", "20")):
            conn.execute("INSERT INTO settings (key, value_json, updated_at, updated_by) VALUES (?,?,?,'user')", (key, raw, NOW))
    finally:
        conn.close()
    first = migrate(db, backups)
    ok("0011 con datos crea copia", first.backup is not None and first.applied[:1] == ("0011_settings_value.sql",))
    first_version = first.to_version
    ok("aplica todas las migraciones", first_version == len(list(Path(__file__).parent.glob("0*.sql"))))
    ok("segunda pasada idempotente", migrate(db, backups).applied == ())

    conn = connect(db)
    try:
        rows = dict(conn.execute("SELECT key, value FROM settings").fetchall())
        ok("0011 conserva valores", rows == {"default_timezone": "Europe/Madrid", "bulk_threshold": "20"})
        lectura = dict(conn.execute("SELECT key, value_json FROM settings").fetchall())
        ok("value_json sigue siendo JSON", json.loads(lectura["default_timezone"]) == "Europe/Madrid" and json.loads(lectura["bulk_threshold"]) == 20)
        conn.execute("INSERT INTO settings (key, value, updated_at) VALUES ('tema', 'oscuro', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (NOW,))
        rejected(conn, "value_json no se escribe", "UPDATE settings SET value_json = '1' WHERE key = 'tema'")
        rejected(conn, "valor demasiado largo", "UPDATE settings SET value = ? WHERE key = 'tema'", ("x" * 65,))
        conn.execute("DELETE FROM settings WHERE key = 'tema'")
        found = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
        ok("triggers obligatorios", REQUIRED_TRIGGERS <= found)
        ok("sin triggers de mas", found - REQUIRED_TRIGGERS == set())
        a, b, c = task(conn, "a"), task(conn, "b"), task(conn, "c")
        ok("restriccion de FK activa", conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1)
        rejected(conn, "tipo declarado incorrecto", "INSERT INTO projects (id, name) VALUES (?, 'p')", (a,))
        rejected(conn, "estado de tarea desconocido", "UPDATE tasks SET status = 'blocked' WHERE id = ?", (a,))
        rejected(conn, "completada sin fecha", "UPDATE tasks SET status = 'completed' WHERE id = ?", (a,))

        conn.execute("UPDATE tasks SET parent_task_id = ? WHERE id = ?", (a, b))
        conn.execute("UPDATE tasks SET parent_task_id = ? WHERE id = ?", (b, c))
        rejected(conn, "ciclo de subtareas", "UPDATE tasks SET parent_task_id = ? WHERE id = ?", (c, a))
        conn.execute("UPDATE tasks SET parent_task_id = NULL WHERE id = ?", (c,))

        relate(conn, "depends_on", a, b)
        relate(conn, "depends_on", b, c)
        try:
            relate(conn, "depends_on", c, a)
            ok("ciclo en depends_on", False)
        except sqlite3.Error:
            ok("ciclo en depends_on", True)
        try:
            relate(conn, "parent_of", a, b)
            ok("par no permitido por el catalogo", False)
        except sqlite3.Error:
            ok("par no permitido por el catalogo", True)
        try:
            relate(conn, "related_to", a, new_id())
            ok("destino inexistente", False)
        except sqlite3.Error:
            ok("destino inexistente", True)

        rejected(conn, "borrar con relacion viva", "DELETE FROM tasks WHERE id = ?", (a,))
        d = task(conn, "d")
        conn.execute("DELETE FROM tasks WHERE id = ?", (d,))
        ok("borrar arrastra la entidad", conn.execute("SELECT count(*) FROM entities WHERE id = ?", (d,)).fetchone()[0] == 0)
        ok("sin entidades huerfanas", conn.execute("SELECT count(*) FROM v_orphan_entities").fetchone()[0] == 0)

        aid = new_id()
        audit(conn, aid)
        rejected(conn, "auditoria sin UPDATE", "UPDATE audit_events SET action = 'y' WHERE id = ?", (aid,))
        rejected(conn, "auditoria sin DELETE", "DELETE FROM audit_events WHERE id = ?", (aid,))
        try:
            audit(conn, aid, "INSERT OR REPLACE")
            ok("auditoria sin REPLACE", False)
        except sqlite3.Error:
            ok("auditoria sin REPLACE", True)
        ok("auditoria intacta", conn.execute("SELECT count(*) FROM audit_events").fetchone()[0] == 1)

        cid = confirmation(conn)
        try:
            confirmation(conn, "INSERT OR REPLACE", cid)
            ok("confirmacion sin REPLACE", False)
        except sqlite3.Error:
            ok("confirmacion sin REPLACE", True)
        rejected(conn, "aprobar sin via de escritorio", "UPDATE pending_confirmations SET status = 'approved', decided_at = ? WHERE id = ?", (NOW, cid))
        rejected(conn, "pending no salta a executed", "UPDATE pending_confirmations SET status = 'executed', decided_at = ?, decided_via = 'desktop' WHERE id = ?", (NOW, cid))
        rejected(conn, "argumentos inmutables", "UPDATE pending_confirmations SET args_json = '{\"id\":1}' WHERE id = ?", (cid,))
        conn.execute("UPDATE pending_confirmations SET status = 'approved', decided_at = ?, decided_via = 'desktop' WHERE id = ?", (NOW, cid))
        claim = "UPDATE pending_confirmations SET status = 'executing' WHERE id = ? AND status = 'approved'"
        ok("primer reclamo gana", conn.execute(claim, (cid,)).rowcount == 1)
        ok("segundo reclamo no ejecuta", conn.execute(claim, (cid,)).rowcount == 0)
        conn.execute("UPDATE pending_confirmations SET status = 'executed' WHERE id = ?", (cid,))
        rejected(conn, "resuelta no reabre", "UPDATE pending_confirmations SET status = 'approved' WHERE id = ?", (cid,))
        rejected(conn, "confirmacion no se borra", "DELETE FROM pending_confirmations WHERE id = ?", (cid,))

        rid = entity(conn, "resource")
        rejected(conn, "traversal en ruta relativa", "INSERT INTO resources (id, title, resource_type, location_id, relative_path) VALUES (?, 'r', 'text', ?, ?)", (rid, new_id(), "a/../b"))
        conn.execute("INSERT INTO resources (id, title, resource_type, url) VALUES (?, 'r', 'link', 'https://x.test')", (rid,))
        conn.execute("INSERT INTO search_documents (entity_id, entity_type, title, body) VALUES (?, 'resource', 'Clasificación', 'texto')", (rid,))
        ok("FTS sin diacriticos", conn.execute("SELECT count(*) FROM search_fts WHERE search_fts MATCH 'clasificacion'").fetchone()[0] == 1)
        conn.execute("INSERT INTO notifications (id, kind, title, created_at, dedupe_key) VALUES (?, 'r', 't', ?, 'k')", (new_id(), NOW))
        rejected(conn, "notificacion deduplicada", "INSERT INTO notifications (id, kind, title, created_at, dedupe_key) VALUES (?, 'r', 't', ?, 'k')", (new_id(), NOW))
        counts = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("tasks", "relationships", "audit_events", "pending_confirmations")}
    finally:
        conn.close()

    backup = create_backup(db, backups, "check")
    conn = connect(db)
    try:
        conn.execute("DELETE FROM relationships")
        conn.execute("UPDATE tasks SET parent_task_id = NULL")
        conn.execute("DELETE FROM tasks")
    finally:
        conn.close()
    restore_backup(db, backups, backup)
    conn = connect(db)
    try:
        after = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in counts}
        ok("restaurar recupera conteos", after == counts)
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
        ok("triggers tras restaurar", REQUIRED_TRIGGERS <= names)
        try:
            conn.execute("INSERT INTO search_fts(search_fts, rank) VALUES('integrity-check', 1)")
            ok("FTS tras restaurar", True)
        except sqlite3.Error:
            ok("FTS tras restaurar", False)
        ok("sin entidades huerfanas tras restaurar", conn.execute("SELECT count(*) FROM v_orphan_entities").fetchone()[0] == 0)
    finally:
        conn.close()


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="drakter-mig-"))
    try:
        run(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print(f"\nFallos: {len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
