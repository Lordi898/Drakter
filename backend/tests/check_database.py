#!/usr/bin/env python3
"""Comprobacion breve de migrate / create_backup / verify_backup / restore_backup.

Escrita a partir de backend/CONTRACT.md. Uso (desde backend/):
    TMPDIR=/var/tmp/drakter-8 .venv/bin/python tests/check_database.py
Sale con codigo != 0 si algun caso falla.
"""
from __future__ import annotations

import http.client
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
HEALTH_PORT = 18766
sys.path.insert(0, str(BACKEND))

from app.database.backup import BackupError, create_backup, restore_backup, verify_backup  # noqa: E402
from app.database import lock as lock_module  # noqa: E402
from app.database import migrator as migrator_module  # noqa: E402
from app.database.connection import connect  # noqa: E402
from app.database.lock import DatabaseInUse, exclusive_instance  # noqa: E402
from app.database.migrator import MigrationError, migrate  # noqa: E402

RESULTS: list[tuple[bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> bool:
    RESULTS.append((bool(cond), name))
    print(f"{'OK  ' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not cond else ""))
    return bool(cond)


def rows(db: Path, sql: str) -> list:
    c = sqlite3.connect(db)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def tables(db: Path) -> set[str]:
    return {r[0] for r in rows(db, "SELECT name FROM sqlite_master WHERE type='table'")}


def mode(p: Path) -> int:
    return stat.S_IMODE(p.stat().st_mode)


def main() -> int:
    base = os.environ.get("TMPDIR") or "/var/tmp/drakter-8"
    Path(base).mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="drakter-db-", dir=base))
    try:
        run(root)
        run_audit_cases(root / "audit")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    bad = [n for ok, n in RESULTS if not ok]
    print(f"\nResumen: {len(RESULTS) - len(bad)}/{len(RESULTS)} OK, {len(bad)} FAIL")
    for n in bad:
        print(f"  FAIL: {n}")
    return 1 if bad else 0


def run(root: Path) -> None:
    os.umask(0o077)
    data = root / "data"
    data.mkdir(mode=0o700)
    db = data / "drakter.db"
    backups = data / "backups"
    mig = root / "migrations"
    mig.mkdir()
    (mig / "0001_items.sql").write_text(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, v TEXT NOT NULL);\n"
    )
    (mig / "0002_more.sql").write_text(
        "CREATE TABLE other (id INTEGER PRIMARY KEY, n INTEGER);\n"
        "INSERT INTO other (n) VALUES (1);\n"
        "INSERT INTO items (v) VALUES ('semilla; con punto y coma');\n"
    )

    # 1. aplicar sobre base nueva
    try:
        r = migrate(db, backups, mig)
        check("migrate aplica 0001-0002 en base nueva",
              (r.from_version, r.to_version, len(r.applied)) == (0, 2, 2), repr(r))
    except Exception as e:
        check("migrate aplica 0001-0002 en base nueva", False, repr(e))
        return
    check("tablas creadas y datos de la migracion presentes",
          {"items", "other", "schema_version"} <= tables(db)
          and rows(db, "SELECT v FROM items") == [("semilla; con punto y coma",)])
    sv = rows(db, "SELECT version, name, checksum, applied_at FROM schema_version ORDER BY version")
    check("schema_version: 2 filas, checksum SHA-256 hex y hora UTC",
          len(sv) == 2 and all(re.fullmatch(r"[0-9a-f]{64}", s[2]) for s in sv)
          and all(("Z" in s[3] or "+00:00" in s[3]) for s in sv), repr(sv))
    check("base de datos con permisos 600", mode(db) == 0o600, oct(mode(db)))

    # 2. idempotencia
    before = sorted(p.name for p in backups.glob("*")) if backups.exists() else []
    r2 = migrate(db, backups, mig)
    after = sorted(p.name for p in backups.glob("*")) if backups.exists() else []
    check("migrate es idempotente: sin aplicadas, sin copia",
          r2.applied == () and r2.backup is None and r2.from_version == r2.to_version == 2
          and before == after, repr((r2, before, after)))

    # 3. fallo a mitad: revertido y con copia
    (mig / "0003_bad.sql").write_text(
        "CREATE TABLE t3 (x INTEGER);\n"
        "INSERT INTO items (v) VALUES ('no debe quedar');\n"
        "INSERT INTO tabla_inexistente VALUES (1);\n"
    )
    before = set(backups.glob("*.db")) if backups.exists() else set()
    try:
        migrate(db, backups, mig)
        check("migracion defectuosa lanza MigrationError", False, "no lanzo")
    except MigrationError as e:
        new = (set(backups.glob("*.db")) if backups.exists() else set()) - before
        check("migracion defectuosa lanza MigrationError", True)
        check("fallo revertido por completo (sin t3, sin fila, version 2)",
              "t3" not in tables(db)
              and rows(db, "SELECT count(*) FROM items") == [(1,)]
              and rows(db, "SELECT max(version) FROM schema_version") == [(2,)])
        check("se creo una copia antes de aplicar y es valida", len(new) == 1
              and not _fails(verify_backup, next(iter(new))), repr(new))
        check("el error cita la copia", bool(new) and next(iter(new)).name in str(e), str(e))
    except Exception as e:
        check("migracion defectuosa lanza MigrationError", False, repr(e))

    # 4. archivos que no se aceptan / checksum cambiado / hueco
    for name, body in (("PRAGMA", "PRAGMA foreign_keys=OFF;\n"),
                       ("COMMIT", "CREATE TABLE z (x INTEGER);\nCOMMIT;\n"),
                       ("ATTACH", "ATTACH DATABASE 'x.db' AS x;\n")):
        (mig / "0003_bad.sql").write_text(body)
        e = _try(migrate, db, backups, mig)
        check(f"migracion con {name} rechazada y sin efectos",
              isinstance(e, MigrationError) and "z" not in tables(db)
              and rows(db, "SELECT max(version) FROM schema_version") == [(2,)], repr(e))
    (mig / "0003_bad.sql").unlink()
    (mig / "0005_gap.sql").write_text("CREATE TABLE g (x INTEGER);\n")
    e = _try(migrate, db, backups, mig)
    check("hueco de numeracion rechazado", isinstance(e, MigrationError) and "g" not in tables(db), repr(e))
    (mig / "0005_gap.sql").unlink()
    orig = (mig / "0001_items.sql").read_text()
    (mig / "0001_items.sql").write_text(orig + "-- cambiado\n")
    e = _try(migrate, db, backups, mig)
    check("checksum aplicado cambiado rechazado", isinstance(e, MigrationError), repr(e))
    (mig / "0001_items.sql").write_text(orig)
    check("tras restaurar el archivo, migrate vuelve a ser no-op",
          _try(migrate, db, backups, mig).__class__.__name__ == "MigrationResult")

    # 5. copia -> cambio -> restauracion con datos exactos
    c = sqlite3.connect(db)
    c.executemany("INSERT INTO items (v) VALUES (?)", [(f"dato-{i}-ñ",) for i in range(25)])
    c.commit()
    c.close()
    snapshot = rows(db, "SELECT id, v FROM items ORDER BY id")
    other_snap = rows(db, "SELECT id, n FROM other ORDER BY id")
    bk = create_backup(db, backups, "manual-1")
    check("create_backup: dentro de backups_dir, nombre del contrato, 600",
          bk.parent.resolve() == backups.resolve()
          and re.fullmatch(r"drakter-\d{8}T\d{12}Z-manual-1\.db", bk.name) is not None
          and mode(bk) == 0o600 and mode(backups) == 0o700,
          f"{bk.name} {oct(mode(bk))} {oct(mode(backups))}")
    check("verify_backup acepta una copia buena", not _fails(verify_backup, bk))
    check("label invalido rechazado", _fails(create_backup, db, backups, "Mal Label/.."))

    bad = backups / "drakter-20000101T000000000000Z-corrupta.db"
    bad.write_bytes(b"esto no es sqlite" * 100)
    check("verify_backup rechaza archivo corrupto", _fails(verify_backup, bad))

    c = sqlite3.connect(db)
    c.execute("DELETE FROM items WHERE id % 2 = 0")
    c.execute("INSERT INTO items (v) VALUES ('posterior a la copia')")
    c.execute("DROP TABLE other")
    c.commit()
    c.close()
    mutated = rows(db, "SELECT id, v FROM items ORDER BY id")
    check("la mutacion de prueba cambio los datos", mutated != snapshot and "other" not in tables(db))

    pre = restore_backup(db, backups, bk, mig)
    check("restore_backup devuelve la copia previa (pre-restore) existente",
          isinstance(pre, Path) and pre.is_file() and "pre-restore" in pre.name
          and pre.parent.resolve() == backups.resolve(), repr(pre))
    check("restauracion: datos exactos (items y other)",
          rows(db, "SELECT id, v FROM items ORDER BY id") == snapshot
          and rows(db, "SELECT id, n FROM other ORDER BY id") == other_snap)
    check("la copia pre-restore conserva el estado mutado",
          rows(pre, "SELECT id, v FROM items ORDER BY id") == mutated)
    check("tras restaurar: integrity_check ok y permisos 600",
          rows(db, "PRAGMA integrity_check") == [("ok",)] and mode(db) == 0o600, oct(mode(db)))
    check("tras restaurar, migrate sigue siendo no-op (schema_version restaurado)",
          _try(migrate, db, backups, mig).__class__.__name__ == "MigrationResult")

    # restauracion fuera de backups_dir o symlink: rechazada y sin tocar la base
    outside = root / "fuera.db"
    shutil.copy(bk, outside)
    e = _try(restore_backup, db, backups, outside, mig)
    check("restore fuera de backups_dir rechazado", isinstance(e, BackupError), repr(e))
    link = backups / "drakter-20000101T000000000001Z-link.db"
    link.symlink_to(outside)
    e = _try(restore_backup, db, backups, link, mig)
    check("restore de symlink rechazado", isinstance(e, BackupError), repr(e))
    e = _try(restore_backup, db, backups, bad, mig)
    check("restore de copia corrupta rechazado", isinstance(e, BackupError), repr(e))
    check("la base no cambio tras los rechazos",
          rows(db, "SELECT id, v FROM items ORDER BY id") == snapshot)


def box(root: Path, name: str, *migrations: str) -> tuple[Path, Path, Path]:
    """Create an isolated database directory with its own migrations."""
    home = root / name
    (home / "m").mkdir(parents=True)
    home.chmod(0o700)
    for number, sql in enumerate(migrations, start=1):
        (home / "m" / f"{number:04d}_m.sql").write_text(sql)
    return home / "x.db", home / "b", home / "m"


def run_audit_cases(root: Path) -> None:
    root.mkdir(mode=0o700)
    case_cascade(root)
    case_lock(root)
    case_incompatible_copy(root)
    case_damaged_live_database(root)
    case_row_damage(root)
    case_no_create(root)


PARENT_CHILD = (
    "CREATE TABLE project(id TEXT PRIMARY KEY, name TEXT);\n"
    "CREATE TABLE task(id TEXT PRIMARY KEY, project_id TEXT NOT NULL\n"
    "  REFERENCES project(id) ON DELETE CASCADE);\n"
    "INSERT INTO project VALUES('p1','n');\n"
    "INSERT INTO task VALUES('t1','p1'),('t2','p1');\n"
)
REBUILD = (
    "CREATE TABLE project_new(id TEXT PRIMARY KEY, name TEXT NOT NULL);\n"
    "INSERT INTO project_new SELECT id,name FROM project;\n"
    "DROP TABLE project;\n"
    "ALTER TABLE project_new RENAME TO project;\n"
)


def case_cascade(root: Path) -> None:
    db, backups, mig = box(root, "cascade", PARENT_CHILD)
    migrate(db, backups, mig)
    # Control: this same SQL does destroy the rows with foreign keys on.
    control = sqlite3.connect(db.parent / "control.db", isolation_level=None)
    control.execute("PRAGMA foreign_keys=ON")
    for statement in (PARENT_CHILD + REBUILD).split(";\n"):
        if statement.strip():
            control.execute(statement)
    check("control 1: con FK activas la reconstruccion borra task",
          control.execute("SELECT count(*) FROM task").fetchone() == (0,))
    control.close()

    (mig / "0002_m.sql").write_text(REBUILD)
    r = migrate(db, backups, mig)
    check("1: reconstruir con DROP TABLE conserva las filas hijas",
          r.to_version == 2 and rows(db, "SELECT count(*) FROM task") == [(2,)]
          and rows(db, "SELECT count(*) FROM project") == [(1,)])

    (mig / "0003_m.sql").write_text("DELETE FROM project;\n")
    e = _try(migrate, db, backups, mig)
    check("1: una migracion que deja huerfanos aborta y revierte",
          isinstance(e, MigrationError) and "foreign_key_check" in str(e)
          and rows(db, "SELECT count(*) FROM project") == [(1,)]
          and rows(db, "SELECT max(version) FROM schema_version") == [(2,)], repr(e))

    # The pragma must come back on both exits of the protected block.
    conn = connect(db)
    loaded = migrator_module.load_migrations(mig)
    e = _try(migrator_module._attempt, conn, db, backups, loaded)
    failed_on = conn.execute("PRAGMA foreign_keys").fetchone()
    (mig / "0003_m.sql").write_text("CREATE TABLE ok3(a);\n")
    done = _try(migrator_module._attempt, conn, db, backups, migrator_module.load_migrations(mig))
    done_on = conn.execute("PRAGMA foreign_keys").fetchone()
    conn.close()
    check("1: foreign_keys vuelve a ON tras fallo y tras exito",
          isinstance(e, MigrationError) and failed_on == (1,)
          and done.applied == ("0003_m.sql",) and done_on == (1,), repr((e, failed_on, done_on)))


def case_lock(root: Path) -> None:
    db, backups, mig = box(root, "lock", "CREATE TABLE t(a);\nINSERT INTO t VALUES(1);\n")
    migrate(db, backups, mig)
    bk = create_backup(db, backups, "manual")
    c = sqlite3.connect(db)
    c.execute("INSERT INTO t VALUES(2)")
    c.commit()
    c.close()
    holder = subprocess.Popen(
        [sys.executable, "-c",
         "import sys, time\nfrom pathlib import Path\n"
         "from app.database.lock import exclusive_instance\n"
         "with exclusive_instance(Path(sys.argv[1])):\n"
         "    print('held', flush=True); time.sleep(30)\n", str(db)],
        stdout=subprocess.PIPE, text=True, cwd=BACKEND)
    try:
        holder.stdout.readline()
        names = sorted(p.name for p in backups.iterdir())
        e = _try(restore_backup, db, backups, bk, mig)
        check("2: con otro proceso vivo restore falla sin tocar nada",
              isinstance(e, BackupError) and rows(db, "SELECT count(*) FROM t") == [(2,)]
              and sorted(p.name for p in backups.iterdir()) == names, repr(e))
        e = _try(lambda: exclusive_instance(db).__enter__())
        check("2: un segundo exclusive_instance lanza DatabaseInUse",
              isinstance(e, DatabaseInUse), repr(e))
    finally:
        holder.kill()
        holder.wait()
    check("2: <db>.lock con permisos 600", mode(Path(f"{db}.lock")) == 0o600)
    prev = _try(restore_backup, db, backups, bk, mig)
    check("control 2: al morir el proceso el bloqueo se libera y restore funciona",
          isinstance(prev, Path) and rows(db, "SELECT count(*) FROM t") == [(1,)], repr(prev))
    original, lock_module.fcntl = lock_module.fcntl, None
    try:
        e = _try(lambda: exclusive_instance(db).__enter__())
    finally:
        lock_module.fcntl = original
    check("2: sin fcntl hay error explicito", isinstance(e, DatabaseInUse) and "flock" in str(e), repr(e))


def case_incompatible_copy(root: Path) -> None:
    first, second = "CREATE TABLE a(x);\n", "CREATE TABLE b(x);\n"
    db, backups, mig = box(root, "compat", first, second)
    migrate(db, backups, mig)
    newer = create_backup(db, backups, "newer")
    (mig / "0002_m.sql").unlink()
    older_db = db.parent / "older.db"
    migrate(older_db, backups, mig)
    baseline = rows(older_db, "SELECT count(*) FROM schema_version")
    e = _try(restore_backup, older_db, backups, newer, mig)
    check("3: copia mas nueva que el codigo rechazada antes de tocar la base",
          isinstance(e, BackupError) and "más nueva" in str(e)
          and rows(older_db, "SELECT count(*) FROM schema_version") == baseline, repr(e))
    (mig / "0002_m.sql").write_text(second)

    (mig / "0001_m.sql").write_text(first + "-- otra\n")
    e = _try(restore_backup, older_db, backups, newer, mig)
    check("3: copia con checksum distinto al codigo rechazada",
          isinstance(e, BackupError) and "checksum" in str(e), repr(e))
    (mig / "0001_m.sql").write_text(first)

    foreign = db.parent / "foreign.db"
    c = sqlite3.connect(foreign)
    c.execute("CREATE TABLE z(a)")
    c.commit()
    c.close()
    copy = create_backup(foreign, backups, "foreign")
    check("3: SQLite ajeno con hash valido rechazado por verify_backup",
          _fails(verify_backup, copy) and "schema_version" in str(_try(verify_backup, copy)))
    e = _try(restore_backup, older_db, backups, copy, mig)
    check("3: restore de SQLite ajeno no toca la base",
          isinstance(e, BackupError) and "z" not in tables(older_db), repr(e))

    # Control: the same newer copy is fine once the code reaches its version.
    prev = _try(restore_backup, older_db, backups, newer, mig)
    check("control 3: una copia compatible se restaura",
          isinstance(prev, Path) and "b" in tables(older_db), repr(prev))


def case_damaged_live_database(root: Path) -> None:
    db, backups, mig = box(root, "damaged", "CREATE TABLE t(a);\n")
    migrate(db, backups, mig)
    c = sqlite3.connect(db)
    c.executemany("INSERT INTO t VALUES(?)", [("x" * 500,) for _ in range(2000)])
    c.commit()
    c.close()
    bk = create_backup(db, backups, "manual")
    expected = rows(db, "SELECT count(*) FROM t")

    prev = restore_backup(db, backups, bk, mig)
    check("control 4: con la base sana hay pre-restore y ninguna cuarentena",
          prev.is_file() and not list(backups.glob("quarantine-*")), repr(prev))

    # The empty -wal stands for the one a crashed process leaves behind.
    with open(db, "r+b") as stream:
        stream.seek(4096 * 5)
        stream.write(os.urandom(4096 * 10))
    Path(f"{db}-wal").write_bytes(b"")
    damaged = db.read_bytes()
    check("control 4: la base esta realmente dañada",
          _fails(create_backup, db, backups, "probe"))
    result = _try(restore_backup, db, backups, bk, mig)
    moved = result / db.name if isinstance(result, Path) else None
    check("4: la base dañada queda en cuarentena 0700, intacta y no se borra",
          isinstance(result, Path) and result.is_dir() and result.name.startswith("quarantine-")
          and result.parent == backups and mode(result) == 0o700
          and moved.read_bytes() == damaged, repr(result))
    check("4: y se restaura sobre una base nueva sana en WAL",
          rows(db, "SELECT count(*) FROM t") == expected and mode(db) == 0o600
          and db.read_bytes()[18:20] == b"\x02\x02"
          and rows(db, "PRAGMA integrity_check") == [("ok",)])

    db.write_bytes(b"\x00" * 8192)
    result = _try(restore_backup, db, backups, bk, mig)
    check("4: una cabecera destruida tambien va a cuarentena",
          isinstance(result, Path) and result.is_dir()
          and rows(db, "SELECT count(*) FROM t") == expected, repr(result))

    # A refusal that is not damage must not move the user's file.
    for suffix in ("", "-wal", "-shm"):
        Path(f"{db}{suffix}").unlink(missing_ok=True)
    target = db.parent / "real.db"
    target.write_bytes(b"datos")
    db.symlink_to(target)
    before = len(list(backups.glob("quarantine-*")))
    e = _try(restore_backup, db, backups, bk, mig)
    check("4: un rechazo que no es daño no pone nada en cuarentena",
          isinstance(e, BackupError) and db.is_symlink() and target.read_bytes() == b"datos"
          and len(list(backups.glob("quarantine-*"))) == before, repr(e))
    db.unlink()

    Path(f"{db}-wal").write_bytes(b"resto")
    result = _try(restore_backup, db, backups, bk, mig)
    kept = sorted(backups.glob(f"quarantine-*/{db.name}-wal"))
    check("4: base perdida con -wal huerfano: lo aparta y restaura",
          isinstance(result, Path) and len(kept) == 1 and kept[0].read_bytes() == b"resto"
          and rows(db, "SELECT count(*) FROM t") == expected, repr(result))


def case_row_damage(root: Path) -> None:
    db, backups, mig = box(root, "rows", "CREATE TABLE t(a);\n")
    migrate(db, backups, mig)
    c = sqlite3.connect(db)
    c.execute("INSERT INTO t VALUES('importe=1000')")
    c.commit()
    c.close()
    bk = create_backup(db, backups, "manual")
    sidecar = Path(f"{bk}.sha256")
    check("5: sidecar .sha256 con 600", sidecar.is_file() and mode(sidecar) == 0o600)
    check("control 5: la copia intacta verifica", not _fails(verify_backup, bk))
    good = bk.read_bytes()
    index = good.index(b"importe=1000")
    bk.write_bytes(good[: index + 8] + b"9" + good[index + 9:])
    check("control 5: integrity_check no ve el daño en la fila",
          rows(bk, "PRAGMA integrity_check") == [("ok",)])
    e = _try(restore_backup, db, backups, bk, mig)
    check("5: el hash rechaza la fila alterada y la base sigue igual",
          isinstance(e, BackupError) and "hash" in str(e)
          and rows(db, "SELECT a FROM t") == [("importe=1000",)], repr(e))
    bk.write_bytes(good)
    saved = sidecar.read_bytes()
    sidecar.unlink()
    check("5: sin sidecar verify_backup falla", _fails(verify_backup, bk))
    sidecar.symlink_to(root / "nada")
    check("5: sidecar symlink rechazado", _fails(verify_backup, bk))
    sidecar.unlink()
    sidecar.write_bytes(saved)
    sidecar.chmod(0o600)
    check("control 5: con el sidecar devuelto vuelve a verificar", not _fails(verify_backup, bk))


def get_health() -> int:
    conn = http.client.HTTPConnection("127.0.0.1", HEALTH_PORT, timeout=5)
    try:
        conn.request("GET", "/health")
        return conn.getresponse().status
    finally:
        conn.close()


def wait_for_health() -> int:
    for _ in range(100):
        try:
            return get_health()
        except OSError:
            time.sleep(0.1)
    return 0


def case_no_create(root: Path) -> None:
    missing = root / "none.db"
    e = _try(connect, missing)
    check("6: connect sin create no crea la base",
          isinstance(e, FileNotFoundError) and not missing.exists(), repr(e))
    connect(missing, create=True).close()
    check("control 6: connect con create la crea", missing.is_file() and mode(missing) == 0o600)

    home = root / "health"
    env = {**os.environ, "XDG_CONFIG_HOME": str(home / "c"), "XDG_DATA_HOME": str(home / "d"),
           "XDG_RUNTIME_DIR": str(home / "r"), "DRAKTER_PORT": str(HEALTH_PORT),
           "PYTHONDONTWRITEBYTECODE": "1"}
    (home / "r").mkdir(mode=0o700, parents=True)
    db = home / "d" / "drakter" / "drakter.db"
    server = subprocess.Popen([sys.executable, "-m", "app"], env=env, cwd=BACKEND,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        alive = wait_for_health()
        for suffix in ("", "-wal", "-shm"):
            Path(f"{db}{suffix}").unlink(missing_ok=True)
        gone = get_health()
    finally:
        server.terminate()
        server.wait(timeout=10)
    check("control 6: /health da 200 con la base presente", alive == 200, str(alive))
    check("6: /health da 503 con la base desaparecida y no la recrea",
          gone == 503 and not db.exists(), str(gone))

    xdg = root / "xdg"
    env = {**os.environ, "XDG_CONFIG_HOME": str(xdg / "c"), "XDG_DATA_HOME": str(xdg / "d"),
           "XDG_RUNTIME_DIR": str(xdg / "r"), "PYTHONDONTWRITEBYTECODE": "1"}
    cli = [sys.executable, "-m", "app.database.cli"]
    status = subprocess.run([*cli, "status"], env=env, cwd=BACKEND, capture_output=True, text=True)
    check("6: la CLI status no crea nada",
          status.returncode == 0 and not list(xdg.rglob("*.db")) and not (xdg / "d").exists(),
          status.stderr)
    done = subprocess.run([*cli, "migrate"], env=env, cwd=BACKEND, capture_output=True, text=True)
    check("control 6: la CLI migrate si crea la base",
          done.returncode == 0 and len(list(xdg.rglob("drakter.db"))) == 1, done.stderr)


def _try(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def _fails(fn, *a, **kw) -> bool:
    try:
        fn(*a, **kw)
    except Exception:  # noqa: BLE001
        return True
    return False


if __name__ == "__main__":
    sys.exit(main())
