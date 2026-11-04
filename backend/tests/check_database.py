#!/usr/bin/env python3
"""Comprobacion breve de migrate / create_backup / verify_backup / restore_backup.

Escrita a partir de backend/CONTRACT.md. Uso (desde backend/):
    TMPDIR=/var/tmp/drakter-8 .venv/bin/python tests/check_database.py
Sale con codigo != 0 si algun caso falla.
"""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.backup import BackupError, create_backup, restore_backup, verify_backup  # noqa: E402
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

    pre = restore_backup(db, backups, bk)
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
    e = _try(restore_backup, db, backups, outside)
    check("restore fuera de backups_dir rechazado", isinstance(e, BackupError), repr(e))
    link = backups / "drakter-20000101T000000000001Z-link.db"
    link.symlink_to(outside)
    e = _try(restore_backup, db, backups, link)
    check("restore de symlink rechazado", isinstance(e, BackupError), repr(e))
    e = _try(restore_backup, db, backups, bad)
    check("restore de copia corrupta rechazado", isinstance(e, BackupError), repr(e))
    check("la base no cambio tras los rechazos",
          rows(db, "SELECT id, v FROM items ORDER BY id") == snapshot)


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
