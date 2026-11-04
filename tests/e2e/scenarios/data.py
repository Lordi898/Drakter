"""Copia y restauración reales (CLAUDE.md §4): un fallo silencioso aquí sería caro."""
from __future__ import annotations

import shutil
import sqlite3
import stat
from contextlib import contextmanager
from pathlib import Path

from harness.model import check

CANARY = "e2e_canary"
IN_USE = "en uso"  # texto del rechazo de `exclusive_instance`


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


@contextmanager
def backend_stopped(ctx):
    """El backend es el único escritor: restaurar exige pararlo y rearrancarlo después."""
    ctx.stack.stop("backend")
    try:
        yield
    finally:
        assert ctx.stack.start_backend(), f"no rearrancó: {ctx.stack.why_unavailable('backend')}"


def refused(reply, label: str) -> None:
    """Rechazada, y por su causa: un rechazo por «en uso» no probaría nada aquí."""
    assert reply.returncode != 0, f"restaurada desde {label}"
    assert IN_USE not in reply.stderr, f"{label}: rechazo por otra causa: {reply.stderr.strip()}"


@check("data.copia_restauracion", "Copia y restauración devuelven los datos anteriores")
def backup_restore(ctx):
    db = ctx.stack.data_dir / "drakter.db"
    write_canary(db, "antes")
    backup = ctx.stack.backend_cli("backup")
    assert backup.returncode == 0, backup.stderr
    copy = copied_path(backup.stdout, "copia: ")
    assert stat.S_IMODE(copy.stat().st_mode) == 0o600, f"copia con permisos {oct(copy.stat().st_mode)}"
    write_canary(db, "despues")

    live = ctx.stack.backend_cli("restore", copy.name)
    assert live.returncode != 0 and IN_USE in live.stderr, f"restaurada en caliente: {live.stderr}"
    assert read_canary(db) == "despues", "un rechazo en caliente cambió la base"

    with backend_stopped(ctx):
        restored = ctx.stack.backend_cli("restore", copy.name)
        assert restored.returncode == 0, restored.stderr
        previous = copied_path(restored.stdout, "copia previa: ")
        assert read_canary(db) == "antes", "la restauración no devolvió el valor copiado"
        assert read_canary(previous) == "despues", "la copia previa no conserva el estado sustituido"
    assert ctx.api.request("GET", "/health", auth=False).status == 200, "/health cae tras restaurar"
    return "rechazada en caliente; con el backend parado recupera el valor, crea copia previa y rearranca"


@check("data.restauracion_rechaza_ajenos", "No se restaura desde fuera de las copias ni una copia manipulada")
def restore_outside(ctx):
    db = ctx.stack.data_dir / "drakter.db"
    write_canary(db, "intacto")
    backup = ctx.stack.backend_cli("backup")
    assert backup.returncode == 0, backup.stderr
    good = copied_path(backup.stdout, "copia: ")
    tampered = good.with_name(good.name.replace("-manual", "-e2etamper"))
    shutil.copy2(good, tampered)
    outside = ctx.stack.layout.work / "ajeno.db"
    shutil.copy2(good, outside)
    with tampered.open("r+b") as handle:
        handle.seek(-1, 2)
        last = handle.read(1)
        handle.seek(-1, 2)
        handle.write(bytes([last[0] ^ 0xFF]))
    link = ctx.stack.data_dir / "backups" / "enlace.db"
    link.symlink_to(outside)
    with backend_stopped(ctx):
        for label, target in (("ruta externa", str(outside)), ("symlink", link.name),
                              ("copia manipulada", tampered.name)):
            refused(ctx.stack.backend_cli("restore", target), label)
        assert read_canary(db) == "intacto", "la base cambió tras un rechazo"
    link.unlink()
    return "ruta externa, symlink y copia manipulada rechazados por su causa; base intacta"
