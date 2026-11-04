"""Copia y restauración reales (CLAUDE.md §4): un fallo silencioso aquí sería caro."""
from __future__ import annotations

import shutil
import sqlite3
import stat
from pathlib import Path

from harness.model import check

CANARY = "e2e_canary"


def write_canary(db: Path, value: str) -> None:
    with sqlite3.connect(db) as conn:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {CANARY} (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute(f"INSERT OR REPLACE INTO {CANARY} (id, value) VALUES (1, ?)", (value,))
    conn.close()


def read_canary(db: Path) -> str:
    conn = sqlite3.connect(db)
    try:
        return conn.execute(f"SELECT value FROM {CANARY} WHERE id = 1").fetchone()[0]
    finally:
        conn.close()


def copied_path(output: str, prefix: str) -> Path:
    for line in output.splitlines():
        if line.startswith(prefix):
            return Path(line.removeprefix(prefix).strip())
    raise AssertionError(f"la CLI no informó de {prefix!r}: {output!r}")


@check("data.copia_restauracion", "Copia y restauración devuelven los datos anteriores")
def backup_restore(ctx):
    db = ctx.stack.data_dir / "drakter.db"
    write_canary(db, "antes")
    backup = ctx.stack.backend_cli("backup")
    assert backup.returncode == 0, backup.stderr
    copy = copied_path(backup.stdout, "copia: ")
    assert stat.S_IMODE(copy.stat().st_mode) == 0o600, f"copia con permisos {oct(copy.stat().st_mode)}"
    write_canary(db, "despues")
    restored = ctx.stack.backend_cli("restore", copy.name)
    assert restored.returncode == 0, restored.stderr
    previous = copied_path(restored.stdout, "copia previa: ")
    assert read_canary(db) == "antes", "la restauración no devolvió el valor copiado"
    assert read_canary(previous) == "despues", "la copia previa no conserva el estado sustituido"
    assert ctx.api.request("GET", "/health", auth=False).status == 200, "/health cae tras restaurar"
    return "valor recuperado, copia previa creada, copia 0600 y /health sigue en 200"


@check("data.restauracion_rechaza_ajenos", "No se restaura desde fuera de la carpeta de copias")
def restore_outside(ctx):
    db = ctx.stack.data_dir / "drakter.db"
    write_canary(db, "intacto")
    outside = ctx.stack.layout.work / "ajeno.db"
    shutil.copy2(db, outside)
    link = ctx.stack.data_dir / "backups" / "enlace.db"
    link.symlink_to(outside)
    for label, target in (("ruta externa", str(outside)), ("symlink", link.name)):
        reply = ctx.stack.backend_cli("restore", target)
        assert reply.returncode != 0, f"restaurada desde {label}"
    link.unlink()
    assert read_canary(db) == "intacto", "la base cambió tras un rechazo"
    return "ruta externa y symlink rechazados; base intacta"
