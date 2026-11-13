"""Ataques FILE: rutas, enlaces, comprimidos y capa de datos (SQLite).

Dos familias:

- FILE-DB-*: contra lo que YA existe (`app.database.*`, `ensure_private_dir`). Se
  ejecutan de verdad en un subproceso con el intérprete del objetivo
  (`ctx.process.args[0]`) y el código de `ctx.backend_dir`, siempre dentro de un
  `ctx.scratch()`; nunca tocan la base del backend en marcha.
- FILE-PATH-* y FILE-ARC-*: contra el contrato del almacén (rutas `/storage-locations`
  y `/resources` de `storage_relations_contract.md`). Si el objetivo no sirve esas
  rutas, son NOT_APPLICABLE con motivo. Los comprimidos se generan en memoria con
  límites propios y jamás se expanden aquí.

Claves nuevas del contrato (todas opcionales, con valor por defecto):
  contract["storage"] = {"locations": "/api/v1/storage-locations",
                         "resources": "/api/v1/resources"}
"""

from __future__ import annotations

import bz2
import gzip
import io
import json
import lzma
import os
import socket
import struct
import subprocess
import tarfile
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any

from redlib import Breach, Context, NotApplicable, attack, expect

DB = "Garantía §8: rutas limitadas, datos con un único origen"
ARC = "Garantía §8: límites de tamaño, número y profundidad en comprimidos"
PATHS = "Garantía §8: rutas de archivos limitadas a ubicaciones permitidas"
HARNESS_TIMEOUT = 90

HARNESS = r'''
import json, os, sys, stat, sqlite3, shutil, time
backend, scenario = sys.argv[1], sys.argv[2]
sys.path.insert(0, backend)
payload = json.load(sys.stdin)
work = payload["work"]
args = payload.get("args", {})
os.umask(0o077)
from pathlib import Path
from app.database.connection import connect
from app.database import backup as bk
from app.database.migrator import migrate
from app.core.config import ensure_private_dir


def err(e):
    return type(e).__name__ + ": " + str(e)


def attempt(fn, *a, **k):
    try:
        fn(*a, **k)
        return {"ok": True}
    except BaseException as e:  # noqa
        return {"ok": False, "error": err(e), "type": type(e).__name__}


def mk(path, rows=("a",)):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE IF NOT EXISTS t(v)")
    c.executemany("INSERT INTO t VALUES (?)", [(r,) for r in rows])
    c.commit()
    c.close()


def rows(path):
    try:
        c = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
        try:
            return [r[0] for r in c.execute("SELECT v FROM t ORDER BY v")]
        finally:
            c.close()
    except BaseException as e:  # noqa
        return "ERR " + err(e)


def hdr(path):
    with open(path, "rb") as f:
        h = f.read(20)
    return [h[18], h[19]] if len(h) == 20 else None


def mode(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


def tree(root):
    out = set()
    for d, ds, fs in os.walk(root):
        for n in ds + fs:
            out.add(os.path.join(d, n))
    return out


def sc_connect():
    o = {}
    p = work + "/ctl.db"
    mk(p)
    os.chmod(p, 0o644)
    try:
        c = connect(Path(p))
        jm = c.execute("PRAGMA journal_mode").fetchone()[0]
        fk = c.execute("PRAGMA foreign_keys").fetchone()[0]
        c.close()
        o["control"] = {"ok": True, "journal": jm, "fk": fk, "mode": mode(p)}
    except BaseException as e:  # noqa
        o["control"] = {"ok": False, "error": err(e)}
    victim = work + "/victim.db"
    mk(victim, ["VICTIM"])
    vh = hdr(victim)
    link = work + "/link.db"
    os.symlink(victim, link)
    o["symlink"] = attempt(connect, Path(link))
    o["victim"] = {"hdr": hdr(victim), "hdr_before": vh, "wal": os.path.exists(victim + "-wal"),
                   "rows": rows(victim)}
    tgt = work + "/dangling-target.db"
    dang = work + "/dangling.db"
    os.symlink(tgt, dang)
    o["dangling"] = attempt(connect, Path(dang))
    o["dangling_created"] = os.path.exists(tgt)
    dd = work + "/dir.db"
    os.mkdir(dd)
    o["dir"] = attempt(connect, Path(dd))
    ff = work + "/fifo.db"
    os.mkfifo(ff)
    o["fifo"] = attempt(connect, Path(ff))
    s = work + "/side.db"
    mk(s)
    v2 = work + "/sidevictim"
    open(v2, "w").write("x")
    os.chmod(v2, 0o644)
    os.symlink(v2, s + "-wal")
    o["sidecar"] = attempt(connect, Path(s))
    o["sidecar_victim_mode"] = mode(v2)
    n = work + "/new.db"
    o["nonexistent"] = attempt(connect, Path(n))
    o["nonexistent_created"] = os.path.exists(n)
    os.symlink(work, work + "/parentlink")
    o["parent_symlink"] = attempt(connect, Path(work + "/parentlink/ctl.db"))
    return o


def sc_race():
    o = {}
    victim = work + "/victim.db"
    mk(victim, ["VICTIM"])
    vh = hdr(victim)
    orig = work + "/orig.db"
    mk(orig)
    db = work + "/db.db"
    os.link(orig, db)
    pid = os.fork()
    if pid == 0:
        try:
            i = 0
            tmp = work + "/swap.tmp"
            while True:
                try:
                    os.unlink(tmp)
                except FileNotFoundError:
                    pass
                if i % 2:
                    os.symlink(victim, tmp)
                else:
                    os.link(orig, tmp)
                os.replace(tmp, db)
                i += 1
        finally:
            os._exit(0)
    counts = {"ok": 0, "symlink": 0, "changed": 0, "other": 0}
    others = []
    end = time.monotonic() + args.get("seconds", 4)
    n = 0
    while time.monotonic() < end:
        n += 1
        try:
            connect(Path(db)).close()
            counts["ok"] += 1
        except BaseException as e:  # noqa
            m = str(e)
            if "enlace" in m:
                counts["symlink"] += 1
            elif "cambi" in m:
                counts["changed"] += 1
            else:
                counts["other"] += 1
                if len(others) < 3:
                    others.append(err(e))
    os.kill(pid, 9)
    os.waitpid(pid, 0)
    o["iterations"] = n
    o["counts"] = counts
    o["others"] = others
    o["victim"] = {"hdr": hdr(victim), "hdr_before": vh,
                   "wal": os.path.exists(victim + "-wal"), "shm": os.path.exists(victim + "-shm"),
                   "rows": rows(victim)}
    return o


def sc_ensure():
    o = {}
    d = work + "/new/a/b"
    o["create"] = attempt(ensure_private_dir, Path(d))
    o["create_mode"] = mode(d) if os.path.isdir(d) else None
    loose = work + "/loose"
    os.mkdir(loose)
    os.chmod(loose, 0o777)
    o["loose"] = attempt(ensure_private_dir, Path(loose))
    o["loose_mode"] = mode(loose)
    tgt = work + "/tgt"
    os.mkdir(tgt)
    os.chmod(tgt, 0o755)
    ln = work + "/lnk"
    os.symlink(tgt, ln)
    o["symlink"] = attempt(ensure_private_dir, Path(ln))
    o["symlink_target_mode"] = mode(tgt)
    f = work + "/afile"
    open(f, "w").close()
    o["file"] = attempt(ensure_private_dir, Path(f))
    dang = work + "/dang"
    os.symlink(work + "/nowhere", dang)
    o["dangling"] = attempt(ensure_private_dir, Path(dang))
    o["dangling_target_created"] = os.path.exists(work + "/nowhere")
    anc = work + "/anc"
    os.symlink(tgt, anc)
    o["ancestor"] = attempt(ensure_private_dir, Path(anc + "/child"))
    o["ancestor_child_in_target"] = os.path.isdir(tgt + "/child")
    ff = work + "/ffifo"
    os.mkfifo(ff)
    o["fifo"] = attempt(ensure_private_dir, Path(ff))
    return o


def sha_of(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def sidecar(path):
    path = str(path)
    with open(path + ".sha256", "w") as f:
        f.write(sha_of(path) + "  " + os.path.basename(path) + "\n")


def setup_backup():
    data = work + "/data"
    os.makedirs(data)
    db = Path(data + "/drakter.db")
    bdir = Path(data + "/backups")
    migrate(db, bdir)
    c = connect(db)
    c.execute("CREATE TABLE t(v)")
    c.execute("INSERT INTO t VALUES ('ORIGINAL')")
    c.close()
    return db, bdir


def setv(db, v):
    c = connect(db)
    c.execute("UPDATE t SET v=?", (v,))
    c.close()


def clone(good, dest, v=None, sql=None, wal=False):
    """Copia compatible de `good` (con su sidecar) y, opcionalmente, modificada."""
    dest = str(dest)
    shutil.copy(str(good), dest)
    if v is not None or sql:
        c = sqlite3.connect(dest)
        if v is not None:
            c.execute("UPDATE t SET v=?", (v,))
        if sql:
            c.execute(sql)
        c.commit()
        c.close()
    sidecar(dest)
    return dest


def sc_lock():
    o = {}
    db, bdir = setup_backup()
    good = bk.create_backup(db, bdir, "ctl")
    setv(db, "LIVE")
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:
        try:
            from app.database.lock import exclusive_instance
            with exclusive_instance(db):
                os.write(w, b"1")
                time.sleep(6)
        finally:
            os._exit(0)
    os.read(r, 1)
    o["while_locked"] = attempt(bk.restore_backup, db, bdir, good)
    o["rows_locked"] = rows(db)
    os.waitpid(pid, 0)
    o["after_unlock"] = attempt(bk.restore_backup, db, bdir, good)
    o["rows_after"] = rows(db)
    return o


def sc_restore():
    o = {}
    db, bdir = setup_backup()
    try:
        good = bk.create_backup(db, bdir, "ctl")
        o["ctl_create"] = {"ok": True, "mode": mode(good), "dir_mode": mode(bdir),
                           "sidecar": os.path.exists(str(good) + ".sha256")}
    except BaseException as e:  # noqa
        o["ctl_create"] = {"ok": False, "error": err(e)}
        return o
    setv(db, "CHANGED")
    o["ctl_restore"] = attempt(bk.restore_backup, db, bdir, good)
    o["ctl_rows"] = rows(db)
    setv(db, "LIVE")
    outside = work + "/outside"
    os.makedirs(outside)
    clone(good, outside + "/poison.db", v="POISON")
    bd = str(bdir)

    def case(name, path):
        before = tree(work)
        r = attempt(bk.restore_backup, db, bdir, Path(path))
        r["rows"] = rows(db)
        r["new_outside_bdir"] = sorted(
            p for p in tree(work) - before
            if not p.startswith(bd) and "drakter.db" not in p)[:5]
        o[name] = r
        if isinstance(r["rows"], list) and r["rows"] != ["LIVE"]:
            setv(db, "LIVE")

    # control de alcance: una copia compatible y con sidecar dentro de backups SÍ se restaura
    clone(good, bd + "/legit.db", v="LEGIT")
    case("legit_clone", bd + "/legit.db")
    o["legit_clone_rows"] = o["legit_clone"]["rows"]
    setv(db, "LIVE")
    case("outside", outside + "/poison.db")
    case("dotdot", bd + "/../../outside/poison.db")
    os.symlink(outside + "/poison.db", bd + "/lnk-out.db")
    case("symlink_out", bd + "/lnk-out.db")
    os.symlink(str(good), bd + "/lnk-in.db")
    case("symlink_in", bd + "/lnk-in.db")
    os.symlink(outside, bd + "/sub")
    case("dirlink", bd + "/sub/poison.db")
    case("bdir_itself", bd)
    case("missing", bd + "/nope.db")
    for name, data in (("text", b"hello world"), ("empty", b""),
                       ("magic", b"SQLite format 3\x00" + b"\x00" * 200)):
        with open(bd + "/" + name + ".db", "wb") as f:
            f.write(data)
        sidecar(bd + "/" + name + ".db")
        case(name if name != "magic" else "magic_garbage", bd + "/" + name + ".db")
    with open(str(good), "rb") as s_, open(bd + "/trunc.db", "wb") as d_:
        d_.write(s_.read(8192))
    sidecar(bd + "/trunc.db")
    case("truncated", bd + "/trunc.db")
    clone(good, bd + "/walhdr.db", v="WALHDR")
    with open(bd + "/walhdr.db", "r+b") as f:
        f.seek(18)
        f.write(b"\x02\x02")
    sidecar(bd + "/walhdr.db")
    case("wal_header", bd + "/walhdr.db")
    # copia legitima y verificada + un -wal ajeno junto a ella (el hash solo cubre el principal)
    stray = clone(good, bd + "/stray.db")
    tmpw = work + "/walsrc.db"
    shutil.copy(str(good), tmpw)
    w = sqlite3.connect(tmpw, isolation_level=None)
    w.execute("PRAGMA journal_mode=WAL")
    w.execute("PRAGMA wal_autocheckpoint=0")
    w.execute("UPDATE t SET v='POISON-WAL'")
    shutil.copy(tmpw + "-wal", stray + "-wal")
    o["stray_wal_size"] = os.path.getsize(stray + "-wal")
    case("stray_wal", stray)
    w.close()
    # integridad y compatibilidad
    clone(good, bd + "/badsum.db", v="BADSUM")
    sidecar(bd + "/badsum.db")
    with open(bd + "/badsum.db", "r+b") as f:
        f.seek(-1, 2)
        f.write(b"\x07")
    case("bad_hash", bd + "/badsum.db")
    clone(good, bd + "/nosidecar.db", v="NOSIDE")
    os.unlink(bd + "/nosidecar.db.sha256")
    case("no_sidecar", bd + "/nosidecar.db")
    clone(good, bd + "/wrongname.db", v="WRONGNAME")
    shutil.copy(bd + "/wrongname.db.sha256", bd + "/other.db.sha256")
    shutil.copy(bd + "/wrongname.db", bd + "/other.db")
    case("sidecar_other_name", bd + "/other.db")
    fx = bd + "/foreign.db"
    c = sqlite3.connect(fx)
    c.execute("CREATE TABLE other(x)")
    c.commit()
    c.close()
    sidecar(fx)
    case("foreign", fx)
    clone(good, bd + "/csum.db", v="CSUM",
          sql="UPDATE schema_version SET checksum='%s'" % ("0" * 64))
    case("wrong_checksum", bd + "/csum.db")
    clone(good, bd + "/future.db", v="FUTURE",
          sql="INSERT INTO schema_version VALUES (999,'x','%s','2026-01-01')" % ("0" * 64))
    case("future_version", bd + "/future.db")
    return o


def sc_tamper():
    o = {}
    db, bdir = setup_backup()
    good = bk.create_backup(db, bdir, "ctl")
    o["sidecar"] = os.path.exists(str(good) + ".sha256")
    c = sqlite3.connect(str(good))
    c.execute("UPDATE t SET v='TAMPERED'")
    c.commit()
    c.close()
    o["verify_tampered"] = attempt(bk.verify_backup, good)
    setv(db, "LIVE")
    o["restore_tampered"] = attempt(bk.restore_backup, db, bdir, good)
    o["rows"] = rows(db)
    return o


def sc_create():
    o = {}
    db, bdir = setup_backup()
    bd = str(bdir)
    # existing loose backups dir gets tightened
    os.makedirs(bd)
    os.chmod(bd, 0o755)
    o["ctl"] = attempt(bk.create_backup, db, bdir, "ok-1")
    o["dir_mode"] = mode(bd)
    labels = ["../x", "a/b", "a\n", "a\x00b", "ä", "", "A", "x" * 5, "..", "a b", "/etc/x", "a․b"]
    res = {}
    for lab in labels:
        before = tree(work)
        r = attempt(bk.create_backup, db, bdir, lab)
        new = sorted(p for p in tree(work) - before)
        r["new"] = [p.replace(work, "") for p in new][:3]
        r["escaped"] = [p.replace(work, "") for p in new if not p.startswith(bd + "/")][:3]
        res[repr(lab)] = r
    o["labels"] = res
    real = work + "/realbackups"
    os.makedirs(real)
    bl = work + "/bdlink"
    os.symlink(real, bl)
    o["bdir_symlink"] = attempt(bk.create_backup, db, Path(bl), "x")
    o["bdir_symlink_files"] = os.listdir(real)
    good = sorted(os.listdir(bd))[0]
    for n in os.listdir(bd):
        if n.endswith("-ok-1.db"):
            good = n
    shutil.copy(bd + "/" + good, real + "/x.db")
    o["restore_bdir_symlink"] = attempt(bk.restore_backup, db, Path(bl), Path(bl + "/x.db"))
    victim = work + "/victim.db"
    mk(victim, ["VICTIM"])
    vh = hdr(victim)
    dl = work + "/dblink.db"
    os.symlink(victim, dl)
    o["backup_db_symlink"] = attempt(bk.create_backup, Path(dl), bdir, "y")
    o["restore_db_symlink"] = attempt(bk.restore_backup, Path(dl), bdir, Path(bd + "/" + good))
    o["victim"] = {"rows": rows(victim), "hdr": hdr(victim), "hdr_before": vh,
                   "wal": os.path.exists(victim + "-wal")}
    return o


def sc_migrations():
    results = []
    for idx, case in enumerate(args["cases"]):
        base = work + "/case%d" % idx
        mig = base + "/migrations"
        os.makedirs(mig)
        ext = base + "/ext.db"
        db = Path(base + "/drakter.db")
        bdir = Path(base + "/backups")
        steps = []
        for step in case["steps"]:
            for fn, content in step.get("files", {}).items():
                data = content if isinstance(content, bytes) else content.replace("@EXT@", ext).encode(
                    "utf-8", "surrogateescape")
                with open(mig + "/" + fn, "wb") as f:
                    f.write(data)
            for fn, content in step.get("outside", {}).items():
                with open(base + "/" + fn, "w") as f:
                    f.write(content.replace("@EXT@", ext))
            for fn, target in step.get("symlinks", {}).items():
                os.symlink(target.replace("@BASE@", base), mig + "/" + fn)
            r = attempt(migrate, db, bdir, Path(mig))
            try:
                c = sqlite3.connect("file:" + str(db) + "?mode=ro", uri=True)
                tables = sorted(x[0] for x in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
                try:
                    ver = c.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
                except sqlite3.Error:
                    ver = None
                c.close()
            except BaseException as e:  # noqa
                tables, ver = "ERR " + err(e), None
            r["tables"] = tables
            r["versions"] = ver
            r["ext_exists"] = os.path.exists(ext)
            steps.append(r)
        results.append({"name": case["name"], "steps": steps})
    return results


out = globals()["sc_" + scenario]()
print("@@RESULT@@" + json.dumps(out))
'''


# --------------------------------------------------------------------------- #
# Subproceso con el código del objetivo
# --------------------------------------------------------------------------- #
def _harness(ctx: Context, scenario: str, **args: Any) -> Any:
    if ctx.process is None:
        raise NotApplicable("sin proceso objetivo: no se conoce el intérprete")
    python = str(ctx.process.args[0])  # type: ignore[index]
    if not (ctx.backend_dir / "app" / "database").is_dir():
        raise NotApplicable("el objetivo no tiene app/database")
    work = ctx.scratch()
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "HOME": str(work),
        "TMPDIR": str(work),
    }
    try:
        done = subprocess.run(
            [python, "-I", "-c", HARNESS, str(ctx.backend_dir), scenario],
            input=json.dumps({"work": str(work), "args": args}).encode(),
            capture_output=True,
            timeout=HARNESS_TIMEOUT,
            cwd=work,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise Breach(f"el escenario {scenario} no terminó en {HARNESS_TIMEOUT}s (bloqueo)") from exc
    text = done.stdout.decode("utf-8", "replace")
    marker = text.rfind("@@RESULT@@")
    if marker < 0:
        raise NotApplicable(
            "el arnés no produjo resultado (¿API distinta?): "
            + (done.stderr.decode("utf-8", "replace")[-300:] or text[-300:])
        )
    return json.loads(text[marker + 10 :])


def _is_error(step: dict[str, Any], *names: str) -> bool:
    return step.get("ok") is False and (not names or step.get("type") in names)


# --------------------------------------------------------------------------- #
# FILE-DB: connect
# --------------------------------------------------------------------------- #
@attack("FILE-DB-01", "connect rechaza enlaces, directorios, FIFO y auxiliares simbólicos",
        guarantee=DB)
def db_connect_special_files(ctx: Context) -> None:
    r = _harness(ctx, "connect")
    control = r["control"]
    expect(control.get("ok") and control["journal"] == "wal" and control["fk"] == 1
           and control["mode"] == 0o600,
           f"control: connect legítimo no deja WAL/FK/0600: {control}")
    for key in ("symlink", "dangling", "dir", "fifo", "sidecar"):
        expect(_is_error(r[key], "ValueError"), f"connect aceptó o falló raro con {key}: {r[key]}")
    victim = r["victim"]
    expect(victim["hdr"] == victim["hdr_before"] and not victim["wal"]
           and victim["rows"] == ["VICTIM"], f"la base víctima fue tocada: {victim}")
    expect(not r["dangling_created"], "connect creó el destino de un enlace colgante")
    expect(r["sidecar_victim_mode"] == 0o644, "chmod siguió el -wal simbólico hasta su destino")


@attack("FILE-DB-15", "connect no crea una base inexistente (promesa del CONTRACT)",
        guarantee=DB, finding="FILE-A1")
def db_connect_no_create(ctx: Context) -> None:
    r = _harness(ctx, "connect")
    expect(r["control"].get("ok"), "control: connect legítimo falla")
    expect(not r["nonexistent_created"] and _is_error(r["nonexistent"], "FileNotFoundError"),
           "CONTRACT: connect sobre una base inexistente debe lanzar FileNotFoundError sin crearla; "
           f"resultado {r['nonexistent']} creada={r['nonexistent_created']}")


@attack("FILE-DB-02", "Carrera: base alternando archivo regular y enlace durante connect",
        guarantee=DB)
def db_connect_race(ctx: Context) -> None:
    r = _harness(ctx, "race", seconds=4)
    counts = r["counts"]
    seen = counts["symlink"] + counts["changed"]
    if counts["ok"] == 0 or seen == 0:
        raise NotApplicable(
            f"la carrera no llegó a ejercitarse (control sin cumplir): {counts} en {r['iterations']}"
        )
    victim = r["victim"]
    expect(victim["hdr"] == victim["hdr_before"] and not victim["wal"] and not victim["shm"]
           and victim["rows"] == ["VICTIM"],
           f"connect acabó operando sobre la base enlazada: {victim} con {counts}")


@attack("FILE-DB-04", "ensure_private_dir: enlaces, ficheros, FIFO y permisos", guarantee=DB)
def db_ensure_private_dir(ctx: Context) -> None:
    r = _harness(ctx, "ensure")
    expect(r["create"]["ok"] and r["create_mode"] == 0o700, f"control: creación 0700 falla: {r}")
    expect(r["loose"]["ok"] and r["loose_mode"] == 0o700, "no endureció un directorio 0777")
    for key in ("symlink", "file", "dangling", "fifo"):
        expect(_is_error(r[key], "ValueError"), f"ensure_private_dir aceptó {key}: {r[key]}")
    expect(r["symlink_target_mode"] == 0o755, "chmod siguió el enlace y cambió el destino")
    expect(not r["dangling_target_created"], "creó el destino de un enlace colgante")


# --------------------------------------------------------------------------- #
# FILE-DB: backups
# --------------------------------------------------------------------------- #
def _restore(ctx: Context) -> dict[str, Any]:
    r = _harness(ctx, "restore")
    expect(r["ctl_create"].get("ok") and r["ctl_restore"].get("ok") and r["ctl_rows"] == ["ORIGINAL"],
           f"control: crear y restaurar una copia legítima falla: {r['ctl_create']} {r['ctl_restore']}")
    expect(r["legit_clone"].get("ok") and r["legit_clone_rows"] == ["LEGIT"],
           f"control: una copia compatible con sidecar dentro de backups no se restaura: {r['legit_clone']}")
    return r


def _rejected(r: dict[str, Any], *names: str) -> None:
    for name in names:
        step = r[name]
        expect(_is_error(step, "BackupError"), f"restore_backup aceptó '{name}': {step}")
        expect(step["rows"] == ["LIVE"], f"'{name}' fue rechazada pero la base cambió: {step['rows']}")
        expect(not step["new_outside_bdir"], f"'{name}' dejó archivos fuera de backups: {step}")


@attack("FILE-DB-05", "restore_backup: copia fuera de backups_dir, .., enlaces, directorio",
        guarantee=DB)
def db_restore_outside(ctx: Context) -> None:
    r = _restore(ctx)
    _rejected(r, "outside", "dotdot", "symlink_out", "symlink_in", "dirlink", "bdir_itself", "missing")


@attack("FILE-DB-06", "restore_backup: no SQLite, vacío, truncado, cabecera con basura",
        guarantee=DB)
def db_restore_not_sqlite(ctx: Context) -> None:
    r = _restore(ctx)
    _rejected(r, "text", "empty", "magic_garbage", "truncated")


@attack("FILE-DB-07", "restore_backup: cabecera WAL y -wal huérfano junto a la copia", guarantee=DB,
        finding="FILE-A2")
def db_restore_wal(ctx: Context) -> None:
    r = _restore(ctx)
    _rejected(r, "wal_header")
    if r["stray_wal_size"] <= 0:
        raise NotApplicable("el -wal de prueba salió vacío")
    stray = r["stray_wal"]
    expect(not (stray["ok"] and stray["rows"] == ["POISON-WAL"]),
           "restore_backup/verify_backup validaron un archivo y restauraron otro contenido: "
           "un -wal junto a la copia (sin cabecera WAL) se aplicó y sustituyó la base viva "
           f"por filas que solo estaban en el -wal: {stray['rows']}")


@attack("FILE-DB-08", "restore_backup exige schema_version y migraciones coherentes (CONTRACT)",
        guarantee=DB, finding="FILE-A3")
def db_restore_foreign(ctx: Context) -> None:
    r = _restore(ctx)
    _rejected(r, "foreign", "wrong_checksum", "future_version")


@attack("FILE-DB-09", "verify_backup/restore exigen sidecar sha256 y detectan copias alteradas",
        guarantee=DB, finding="FILE-A4")
def db_verify_tamper(ctx: Context) -> None:
    r = _harness(ctx, "tamper")
    expect(_is_error(r["verify_tampered"], "BackupError") and r["rows"] != ["TAMPERED"]
           and not r["restore_tampered"]["ok"],
           f"una copia modificada en sitio se verificó o restauró (filas: {r['rows']})")
    rr = _restore(ctx)
    _rejected(rr, "bad_hash", "no_sidecar", "sidecar_other_name")


@attack("FILE-DB-10", "create_backup: etiquetas, backups_dir simbólico, base simbólica", guarantee=DB)
def db_create_backup(ctx: Context) -> None:
    r = _harness(ctx, "create")
    expect(r["ctl"].get("ok") and r["dir_mode"] == 0o700, f"control: copia legítima o 0700: {r}")
    for label, step in r["labels"].items():
        expect(not step["escaped"], f"la etiqueta {label} creó archivos fuera de backups: {step}")
        if label != "'xxxxx'":
            expect(_is_error(step, "BackupError"), f"etiqueta {label} aceptada: {step}")
    expect(r["labels"]["'xxxxx'"].get("ok"), "control: etiqueta válida rechazada")
    for key in ("bdir_symlink", "restore_bdir_symlink", "backup_db_symlink", "restore_db_symlink"):
        expect(_is_error(r[key], "BackupError"), f"{key} aceptado: {r[key]}")
    expect(r["bdir_symlink_files"] == [], "se escribió a través de un backups_dir simbólico")
    victim = r["victim"]
    expect(victim["rows"] == ["VICTIM"] and victim["hdr"] == victim["hdr_before"]
           and not victim["wal"], f"la base víctima del enlace fue tocada: {victim}")


@attack("FILE-DB-11", "restore_backup toma un bloqueo exclusivo (lock.py)", guarantee=DB,
        finding="FILE-A6")
def db_restore_lock(ctx: Context) -> None:
    if not (ctx.backend_dir / "app" / "database" / "lock.py").exists():
        raise NotApplicable("app/database/lock.py no existe en este objetivo")
    r = _harness(ctx, "lock")
    expect(r["after_unlock"].get("ok"),
           f"control: sin bloqueo ajeno, restore debería funcionar: {r['after_unlock']}")
    expect(_is_error(r["while_locked"], "BackupError") and r["rows_locked"] == ["LIVE"],
           f"restore actuó con otra instancia sujetando el bloqueo: {r['while_locked']} {r['rows_locked']}")


# --------------------------------------------------------------------------- #
# FILE-DB: migraciones
# --------------------------------------------------------------------------- #
BENIGN = "CREATE TABLE ctl(a INTEGER);\n"


def _case(name: str, files: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"name": name, "steps": [{"files": files, **extra}]}


def _run_migrations(ctx: Context, cases: list[dict[str, Any]]) -> dict[str, Any]:
    cases = [_case("control", {"0001_ctl.sql": BENIGN})] + cases
    results = _harness(ctx, "migrations", cases=cases)
    control = results[0]["steps"][0]
    expect(control.get("ok") and control["tables"] == ["ctl", "schema_version"]
           and control["versions"] == 1, f"control: una migración legítima no se aplicó: {control}")
    return {item["name"]: item["steps"] for item in results[1:]}


def _must_reject(steps: dict[str, Any], names: list[str], *, text: str | None = None) -> None:
    for name in names:
        step = steps[name][-1]
        expect(_is_error(step, "MigrationError"), f"'{name}' no fue rechazada: {step}")
        expect(not step["ext_exists"], f"'{name}': ATTACH/VACUUM INTO creó un archivo externo")
        expect(step["tables"] in ([], ["schema_version"]) or str(step["tables"]).startswith("ERR"),
               f"'{name}': la base quedó modificada: {step['tables']}")
        if text is not None:
            expect(text in step["error"], f"'{name}': rechazada por otra causa, no se alcanzó "
                   f"el control atacado ({text!r}): {step['error']}")


ALLOWLIST = {
    "attach": "ATTACH DATABASE '@EXT@' AS x;\n",
    "attach_lower": "attach '@EXT@' as x;\n",
    "attach_comments": "/* c */ -- d\n ATTACH '@EXT@' AS x;\n",
    "attach_semicolons": ";;ATTACH '@EXT@' AS x;\n",
    "attach_second": "CREATE TABLE a(x);\nATTACH '@EXT@' AS x;\n",
    "detach": "DETACH x;\n",
    "pragma_fk": "PRAGMA foreign_keys=OFF;\n",
    "pragma_ws": "PRAGMA writable_schema=ON;\n",
    "pragma_lower": "pragma journal_mode=DELETE;\n",
    "begin": "BEGIN;\n",
    "begin_imm": "BEGIN IMMEDIATE;\n",
    "commit": "COMMIT;\n",
    "commit_tx": "COMMIT TRANSACTION;\n",
    "end": "END;\n",
    "end_tx": "END TRANSACTION;\n",
    "rollback": "ROLLBACK;\n",
    "savepoint": "SAVEPOINT s;\n",
    "release": "RELEASE s;\n",
    "vacuum": "VACUUM;\n",
    "vacuum_into": "VACUUM INTO '@EXT@';\n",
    "select": "SELECT 1;\n",
}



@attack("FILE-DB-12", "Migraciones: ATTACH, PRAGMA, control de transacción y VACUUM rechazados",
        guarantee=DB)
def db_migration_allowlist(ctx: Context) -> None:
    cases = [_case(name, {"0001_bad.sql": sql}) for name, sql in ALLOWLIST.items()]
    cases.append({"name": "bad_after_good", "steps": [{"files": {
        "0001_ok.sql": BENIGN, "0002_bad.sql": "ATTACH '@EXT@' AS x;\n"}}]})
    steps = _run_migrations(ctx, cases)
    _must_reject(steps, [*ALLOWLIST, "bad_after_good"], text="no permitida")


TRICKS = {
    "trigger_then_attach": (
        "CREATE TABLE a(x);\nCREATE TRIGGER t AFTER INSERT ON a BEGIN SELECT 1; END; "
        "ATTACH DATABASE '@EXT@' AS x;\n"),
    "nbsp_prefix": " ATTACH '@EXT@' AS x;\n",
    "fullwidth": "ＡＴＴＡＣＨ '@EXT@' AS x;\n",
    "bom_prefix": "﻿ATTACH '@EXT@' AS x;\n",
    "null_byte": "CREATE TABLE a(x);\x00ATTACH '@EXT@' AS x;\n",
    "no_final_semicolon": "CREATE TABLE a(x);\nATTACH '@EXT@' AS x",
    "unterminated_comment": "/* ATTACH '@EXT@' AS x;\n",
}


@attack("FILE-DB-13", "Migraciones: trucos de troceado, Unicode, load_extension y sqlite_master",
        guarantee=DB)
def db_migration_tricks(ctx: Context) -> None:
    cases = [_case(name, {"0001_bad.sql": sql}) for name, sql in TRICKS.items()]
    cases.append(_case("invalid_utf8", {"0001_bad.sql": "CREATE TABLE a(x);\udcff\udcfe\n"}))
    cases.append(_case("load_extension", {"0001_bad.sql": (
        "CREATE TABLE a(x);\nINSERT INTO a VALUES (load_extension('/nonexistent/x.so'));\n")}))
    cases.append(_case("with_load_extension", {"0001_bad.sql": (
        "WITH c AS (SELECT 1) SELECT load_extension('/nonexistent/x.so');\n")}))
    cases.append(_case("write_master", {"0001_bad.sql": (
        "INSERT INTO sqlite_master VALUES('table','a','a',2,'CREATE TABLE a(x)');\n")}))
    # Falsos positivos del troceado: esto es legítimo y NO debe ejecutar el ATTACH.
    cases.append(_case("semicolon_in_string", {"0001_ok.sql": (
        "CREATE TABLE a(x);\nINSERT INTO a VALUES ('; ATTACH ''@EXT@'' AS x; --');\n")}))
    cases.append(_case("semicolon_in_comment", {"0001_ok.sql": (
        "CREATE TABLE a(x); /* ; ATTACH '@EXT@' AS x; */\n")}))
    steps = _run_migrations(ctx, cases)
    _must_reject(steps, [*TRICKS, "invalid_utf8", "write_master"])
    _must_reject(steps, ["load_extension", "with_load_extension"], text="not authorized")
    for name in ("semicolon_in_string", "semicolon_in_comment"):
        step = steps[name][-1]
        expect(step.get("ok") and not step["ext_exists"],
               f"'{name}': el troceador ejecutó el ATTACH o rechazó SQL legítimo: {step}")


@attack("FILE-DB-14", "Migraciones: enlaces, huecos, duplicados, nombres, checksum", guarantee=DB)
def db_migration_files(ctx: Context) -> None:
    cases = [
        {"name": "symlink_benign", "steps": [{"outside": {"o.sql": BENIGN},
                                              "symlinks": {"0001_l.sql": "@BASE@/o.sql"}}]},
        {"name": "symlink_attach", "steps": [{"outside": {"o.sql": "ATTACH '@EXT@' AS x;\n"},
                                              "symlinks": {"0001_l.sql": "@BASE@/o.sql"}}]},
        _case("gap", {"0001_a.sql": BENIGN, "0003_b.sql": "CREATE TABLE b(x);\n"}),
        _case("duplicate", {"0001_a.sql": BENIGN, "0001_b.sql": "CREATE TABLE b(x);\n"}),
        _case("bad_name", {"1_a.sql": BENIGN}),
        _case("space_name", {"0001_a b.sql": BENIGN}),
        _case("null_file", {"0001_a.sql": "CREATE TABLE a(x);\x00\n"}),
        {"name": "checksum", "steps": [
            {"files": {"0001_ok.sql": BENIGN}},
            {"files": {"0001_ok.sql": BENIGN + "-- alterada tras aplicarse\n"}}]},
    ]
    steps = _run_migrations(ctx, cases)
    _must_reject(steps, ["symlink_benign", "symlink_attach"], text="archivo regular")
    _must_reject(steps, ["gap", "duplicate", "bad_name", "space_name", "null_file"])
    first, second = steps["checksum"]
    expect(first.get("ok"), "control: la primera aplicación de 'checksum' falla")
    expect(_is_error(second, "MigrationError") and "checksum" in second["error"],
           f"una migración ya aplicada y modificada no se detectó: {second}")


# --------------------------------------------------------------------------- #
# Almacén: rutas, enlaces, comprimidos (contra el contrato, por HTTP)
# --------------------------------------------------------------------------- #
SECRET = "RED-SECRET-" + uuid.uuid4().hex
OK_TEXT = "OKCONTENT-" + uuid.uuid4().hex[:8]


class Vault:
    """Ubicación de prueba con un archivo legítimo y un secreto fuera de ella."""

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.ids: dict[str, str] = {}
        storage = ctx.contract.get("storage", {})
        self.locations = storage.get("locations", "/api/v1/storage-locations")
        self.resources = storage.get("resources", "/api/v1/resources")
        probe = ctx.http("GET", self.resources)
        if probe.status == 404 and probe.error_code in (None, "http_404"):
            raise NotApplicable(
                f"el objetivo no sirve {self.resources}: el almacén no está integrado; "
                "ataque escrito contra storage_relations_contract.md"
            )
        self.base = ctx.scratch()
        self.loc = self.base / "loc"
        self.outside = self.base / "outside"
        self.loc.mkdir()
        self.outside.mkdir()
        (self.outside / "secret.txt").write_text(SECRET)
        (self.loc / "ok.txt").write_text(OK_TEXT)
        self.loc_id = self.create_location(self.loc, "red")
        control = self.probe("ok.txt")
        if control["read"] != 200 or OK_TEXT not in control["text"]:
            raise NotApplicable(f"control sin cumplir: lectura legítima no devuelve 200 con su texto: {control}")

    def approver(self) -> str:
        """Regla del guardia (core/security.py): escribir en /storage-locations exige el aprobador."""
        key = self.ctx.contract.get("principals", {}).get("gui_approver", "approver_token")
        token = self.ctx.session.get(key)
        if not isinstance(token, str):
            raise NotApplicable(f"session.json no trae la credencial {key!r}")
        return token

    def create_location(self, path: Path | str, label: str) -> str:
        response = self.ctx.http("POST", self.locations, token=self.approver(), json_body={
            "path": str(path), "label": label, "read_only": True, "agent_read": False})
        payload = response.json()
        if response.status not in (200, 201) or not isinstance(payload, dict) or "id" not in payload:
            raise NotApplicable(
                f"control: no se pudo crear la ubicación ({response.status} {response.error_code})")
        return str(payload["id"])

    def probe(self, rel: str, *, timeout: float = 10.0) -> dict[str, Any]:
        created = self.ctx.http("POST", self.resources, timeout=timeout, json_body={
            "title": "red", "location_id": self.loc_id, "relative_path": rel})
        out: dict[str, Any] = {"create": created.status, "code": created.error_code, "read": None,
                               "read_code": None, "text": created.body.decode("utf-8", "replace")}
        payload = created.json()
        if 200 <= created.status < 300 and isinstance(payload, dict) and "id" in payload:
            self.ids[rel] = payload["id"]
        elif created.status == 409 and rel in self.ids:  # ya creado antes: se relee el mismo
            payload = {"id": self.ids[rel]}
            created.status = 201
            out["create"] = 201
        if 200 <= created.status < 300 and isinstance(payload, dict) and "id" in payload:
            read = self.ctx.http("POST", f"{self.resources}/{payload['id']}/read", timeout=timeout,
                                 json_body={})
            out.update(read=read.status, read_code=read.error_code)
            out["text"] += read.body.decode("utf-8", "replace")
        return out


def _judge(name: str, out: dict[str, Any]) -> bool:
    """Falla si hay fuga o 5xx. Devuelve True si el sistema rechazó con un código propio."""
    expect(SECRET not in out["text"], f"'{name}': FUGA del contenido fuera de la ubicación: {out}")
    for status in (out["create"], out["read"]):
        expect(status is None or status < 500, f"'{name}': error interno {status}: {out['code']}")
    codes = [c for c in (out["code"], out["read_code"]) if c]
    return any(c != "http_404" for c in codes)


def _sweep(ctx: Context, names: list[str], make: Any) -> None:
    vault = Vault(ctx)
    rejected = 0
    for name in names:
        out = vault.probe(make(vault, name))
        rejected += _judge(name, out)
    if not rejected:
        raise NotApplicable("ningún payload recibió un rechazo con código propio: camino no alcanzado")


def _fmt(vault: Vault, template: str) -> str:
    return template.replace("{abs}", str(vault.outside / "secret.txt"))


TRAVERSAL = [
    "../outside/secret.txt",
    "../../outside/secret.txt",
    "a/../../outside/secret.txt",
    "./../outside/secret.txt",
    "ok.txt/../../outside/secret.txt",
    "....//outside/secret.txt",
    "..././outside/secret.txt",
    "{abs}",
    "/{abs}",
    "//{abs}",
    "../outside/secret.txt\x00.txt",
    "ok.txt\x00../../outside/secret.txt",
    "..\\outside\\secret.txt",
    "..\\..\\outside\\secret.txt",
    "ok.txt\r\n../outside/secret.txt",
    "../outside/secret.txt ",
    "../outside/secret.txt.",
    "..",
    ".",
    "",
]
ENCODED = [
    "..%2foutside%2fsecret.txt",
    "%2e%2e/outside/secret.txt",
    "%2e%2e%2foutside%2fsecret.txt",
    "%252e%252e%252foutside%252fsecret.txt",
    "..%252foutside%252fsecret.txt",
    "%c0%ae%c0%ae/outside/secret.txt",
    "..%c0%afoutside%c0%afsecret.txt",
    "..%5coutside%5csecret.txt",
    "%00../outside/secret.txt",
    "．．/outside/secret.txt",
    "..／outside／secret.txt",
    "‥/outside/secret.txt",
    "﹒﹒/outside/secret.txt",
    "..∕outside∕secret.txt",
    "..⧸outside⧸secret.txt",
    "‮../outside/secret.txt",
    ".​./outside/secret.txt",
]


@attack("FILE-PATH-01", "Almacén: traversal clásico, absolutas, byte nulo y barras invertidas",
        guarantee=PATHS)
def path_traversal(ctx: Context) -> None:
    _sweep(ctx, TRAVERSAL, lambda v, t: _fmt(v, t))


@attack("FILE-PATH-02", "Almacén: URL-encoded, doble codificación y Unicode que normaliza a '..'",
        guarantee=PATHS)
def path_encoded(ctx: Context) -> None:
    _sweep(ctx, ENCODED, lambda v, t: _fmt(v, t))


@attack("FILE-PATH-03", "Almacén: symlinks y hardlinks dentro de la ubicación", guarantee=PATHS)
def path_symlinks(ctx: Context) -> None:
    vault = Vault(ctx)
    loc, outside = vault.loc, vault.outside
    os.symlink("../outside/secret.txt", loc / "link_file")
    os.symlink(str(outside / "secret.txt"), loc / "link_abs")
    os.symlink("../outside", loc / "link_dir")
    (loc / "mid").mkdir()
    os.symlink("../../outside", loc / "mid" / "up")
    os.symlink("/proc/self/root" + str(outside / "secret.txt"), loc / "link_magic")
    os.symlink("link_chain2", loc / "link_chain1")
    os.symlink("../outside/secret.txt", loc / "link_chain2")
    try:
        os.link(outside / "secret.txt", loc / "hard.txt")
    except OSError as exc:
        raise NotApplicable(f"no se pudo crear el hardlink de prueba: {exc}") from exc
    rejected = 0
    for rel in ("link_file", "link_abs", "link_dir/secret.txt", "mid/up/secret.txt", "link_magic",
                "link_chain1", "hard.txt"):
        rejected += _judge(rel, vault.probe(rel))
    expect(rejected >= 1, "ningún enlace recibió un rechazo con código propio")
    # Lo que sí es legítimo debe seguir funcionando: el rechazo no es "todo falla".
    after = vault.probe("ok.txt")
    expect(after["read"] == 200 and OK_TEXT in after["text"], "tras los enlaces, ok.txt dejó de leerse")


@attack("FILE-PATH-04", "Almacén: archivos protegidos (.env, .ssh, .gnupg) dentro de la ubicación",
        guarantee=PATHS)
def path_denied_names(ctx: Context) -> None:
    vault = Vault(ctx)
    for rel in (".env", ".env.local", ".ssh/id_rsa", "sub/.ssh/key", ".gnupg/secring", "sub/.env"):
        target = vault.loc / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(SECRET)
    rejected = 0
    for rel in (".env", ".env.local", ".ssh/id_rsa", "sub/.ssh/key", ".gnupg/secring", "sub/.env"):
        out = vault.probe(rel)
        rejected += _judge(rel, out)
        expect(out["read"] != 200, f"'{rel}' se leyó con 200: {out}")
    expect(rejected >= 1, "ningún archivo protegido recibió un rechazo con código propio")


@attack("FILE-PATH-05", "Almacén: ubicaciones peligrosas (/, home, enlace, relativa)", guarantee=PATHS)
def path_bad_locations(ctx: Context) -> None:
    vault = Vault(ctx)
    link = vault.base / "loc-link"
    os.symlink(vault.outside, link)
    candidates = {
        "root": "/",
        "home": str(ctx.root / "home"),
        "symlink": str(link),
        "relative": "../outside",
        "dotdot": f"{vault.loc}/../outside",
        "nul": f"{vault.loc}\x00/x",
    }
    rejected = 0
    for name, path in candidates.items():
        response = ctx.http("POST", vault.locations, token=vault.approver(), json_body={
            "path": path, "label": name, "read_only": True, "agent_read": False})
        expect(response.status < 500, f"'{name}': error interno {response.status}")
        expect(not 200 <= response.status < 300, f"'{name}': ubicación peligrosa aceptada ({path!r})")
        rejected += response.error_code not in (None, "http_404")
    expect(rejected == len(candidates), "alguna ubicación peligrosa no recibió un error con código")


@attack("FILE-PATH-08", "Almacén: el token de la UI no puede crear ni cambiar ubicaciones (guardia)",
        guarantee=PATHS)
def path_location_needs_approver(ctx: Context) -> None:
    vault = Vault(ctx)
    other = vault.base / "other"
    other.mkdir()
    body = {"path": str(other), "label": "ui", "read_only": True, "agent_read": True}
    for method, path in (("POST", vault.locations), ("PATCH", f"{vault.locations}/{vault.loc_id}"),
                         ("DELETE", f"{vault.locations}/{vault.loc_id}")):
        response = ctx.http(method, path, token=True, json_body=body if method != "DELETE" else None)
        expect(response.status == 403 and response.error_code == "permission_denied",
               f"{method} {path} con el token de la UI no dio 403 permission_denied: "
               f"{response.status} {response.error_code}")
    still = vault.probe("ok.txt")
    expect(still["read"] == 200, "la ubicación desapareció tras un DELETE rechazado")


@attack("FILE-PATH-06", "Almacén: la raíz de la ubicación se cambia por un enlace tras crearla",
        guarantee=PATHS)
def path_root_swap(ctx: Context) -> None:
    vault = Vault(ctx)
    other = vault.base / "other"
    other.mkdir()
    (other / "ok.txt").write_text(SECRET)
    os.rename(vault.loc, vault.base / "loc.bak")
    os.symlink(other, vault.loc)
    out = vault.probe("ok.txt")
    _judge("root_swap", out)
    expect(out["read"] != 200, f"se leyó a través de la raíz sustituida por un enlace: {out}")


@attack("FILE-PATH-07", "Almacén: carrera archivo regular / enlace durante la lectura", guarantee=PATHS)
def path_race(ctx: Context) -> None:
    vault = Vault(ctx)
    target = vault.loc / "race.txt"
    target.write_text(OK_TEXT)
    stop = threading.Event()

    def flip() -> None:
        index = 0
        while not stop.is_set():
            tmp = vault.loc / ".race.tmp"
            if tmp.exists() or tmp.is_symlink():
                tmp.unlink()
            if index % 2:
                os.symlink(vault.outside / "secret.txt", tmp)
            else:
                tmp.write_text(OK_TEXT)
            os.replace(tmp, target)
            index += 1

    created = ctx.http("POST", vault.resources, json_body={
        "title": "race", "location_id": vault.loc_id, "relative_path": "race.txt"})
    payload = created.json()
    if not (200 <= created.status < 300 and isinstance(payload, dict) and "id" in payload):
        raise NotApplicable(f"control: no se pudo crear el recurso de la carrera: {created.status}")
    thread = threading.Thread(target=flip, daemon=True)
    thread.start()
    good = refused = 0
    deadline = time.monotonic() + 4
    try:
        while time.monotonic() < deadline:
            read = ctx.http("POST", f"{vault.resources}/{payload['id']}/read", json_body={})
            text = read.body.decode("utf-8", "replace")
            expect(SECRET not in text, "FUGA: la carrera comprobación/uso leyó el secreto externo")
            expect(read.status < 500, f"error interno bajo carrera: {read.status}")
            if read.status == 200 and OK_TEXT in text:
                good += 1
            elif read.error_code not in (None, "http_404"):
                refused += 1
    finally:
        stop.set()
        thread.join(5)
    if not good or not refused:
        raise NotApplicable(f"la carrera no se ejercitó: lecturas buenas={good}, rechazadas={refused}")


# --------------------------------------------------------------------------- #
# Comprimidos: generados en memoria y acotados; el atacante nunca los expande
# --------------------------------------------------------------------------- #
MAX_ARCHIVE_BYTES = 8 << 20  # el archivo malicioso en sí nunca pasa de 8 MiB


class _Zeros:
    def __init__(self, total: int) -> None:
        self.left = total

    def read(self, size: int = -1) -> bytes:
        size = self.left if size is None or size < 0 else min(size, self.left)
        size = min(size, 1 << 20)
        self.left -= size
        return b"\0" * size


def _zip_bytes(entries: list[tuple[str, bytes]], method: int = zipfile.ZIP_STORED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", method) as archive:
        for name, data in entries:
            archive.writestr(zipfile.ZipInfo(name), data, compress_type=method)
    return buf.getvalue()


def _zip_bomb(total: int, *, zip64: bool = True) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        with archive.open("big.bin", "w", force_zip64=zip64) as stream:
            left = total
            while left:
                step = min(left, 1 << 20)
                stream.write(b"\0" * step)
                left -= step
    return buf.getvalue()


def _tar_stream(mode: str, members: Any) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode=mode) as archive:
        for info, stream in members:
            archive.addfile(info, stream)
    return buf.getvalue()


def _tar_bomb(compression: str, total: int) -> bytes:
    info = tarfile.TarInfo("big.bin")
    info.size = total
    return _tar_stream("w|" + compression, [(info, _Zeros(total))])


def _tar_many(count: int) -> bytes:
    def members() -> Any:
        for index in range(count):
            info = tarfile.TarInfo(f"d{index}")
            info.type = tarfile.DIRTYPE
            yield info, None

    return _tar_stream("w|gz", members())


def _patch(data: bytes, signature: bytes, offset: int, value: bytes, *, last: bool = False) -> bytes:
    start = data.rfind(signature) if last else data.find(signature)
    if start < 0:
        raise NotApplicable(f"el generador no encontró la firma {signature!r}")
    out = bytearray(data)
    out[start + offset : start + offset + len(value)] = value
    return bytes(out)


def _tar_lies() -> bytes:
    info = tarfile.TarInfo("big.bin")
    info.size = 10 << 30
    return info.tobuf(tarfile.GNU_FORMAT) + b"A" * 1024


def _tar_longname_lie() -> bytes:
    info = tarfile.TarInfo("././@LongLink")
    info.type = tarfile.GNUTYPE_LONGNAME
    info.size = (2 << 30) - 1
    return info.tobuf(tarfile.GNU_FORMAT) + b"x" * 512


def _tar_pax_lie() -> bytes:
    info = tarfile.TarInfo("pax")
    info.type = tarfile.XHDTYPE
    info.size = (4 << 30)
    return info.tobuf(tarfile.GNU_FORMAT) + b"30 path=" + b"y" * 100


def _tar_zoo(root: Path) -> bytes:
    members: list[tuple[tarfile.TarInfo, Any]] = []

    def add(name: str, kind: bytes, link: str = "", data: bytes = b"", mode: int = 0o644,
            major: int = 0, minor: int = 0) -> None:
        info = tarfile.TarInfo(name)
        info.type = kind
        info.linkname = link
        info.mode = mode
        info.devmajor, info.devminor = major, minor
        info.size = len(data) if kind == tarfile.REGTYPE else 0
        members.append((info, io.BytesIO(data) if kind == tarfile.REGTYPE else None))

    add("link-abs", tarfile.SYMTYPE, "/etc/passwd")
    add("link-up", tarfile.SYMTYPE, "../../../../../../etc/passwd")
    add("hard", tarfile.LNKTYPE, "/etc/passwd")
    add("dev-null", tarfile.CHRTYPE, major=1, minor=3)
    add("fifo", tarfile.FIFOTYPE)
    add("suid.sh", tarfile.REGTYPE, data=b"#!/bin/sh\n", mode=0o4755)
    add("../PWNED-t1.txt", tarfile.REGTYPE, data=b"x")
    add(f"{root}/abs-target/PWNED-tabs.txt", tarfile.REGTYPE, data=b"x")
    add("dirlink", tarfile.SYMTYPE, "../..")
    add("dirlink/PWNED-t2.txt", tarfile.REGTYPE, data=b"x")
    return _tar_stream("w:", members)


def _zip_in_zip(levels: int) -> bytes:
    data = _zip_bytes([("INNER_MARKER.txt", b"x"), ("../PWNED-inner.txt", b"x")])
    for level in range(levels):
        data = _zip_bytes([(f"inner{level}.zip", data)])
    return data


def _zip_traversal(root: Path) -> bytes:
    names = ["../PWNED-z1.txt", "../../PWNED-z2.txt", f"{root}/abs-target/PWNED-zabs.txt",
             "a/../../PWNED-z3.txt", "..\\PWNED-z4.txt", "C:\\PWNED-z5.txt", "ZZZZZZZZZZ"]
    data = _zip_bytes([(name, b"x") for name in names])
    return data.replace(b"ZZZZZZZZZZ", b"z\x00PWNED-z6")


def _loc_tree(loc: Path) -> set[str]:
    return {str(p.relative_to(loc)) for p in loc.rglob("*")}


def _pwned(ctx: Context) -> list[str]:
    return [str(p) for p in ctx.root.rglob("PWNED*")]


def _rss_peak_kb(ctx: Context) -> int:
    if ctx.process is None:
        return 0
    try:
        for line in Path(f"/proc/{ctx.process.pid}/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    except OSError:
        pass
    return 0


def _archive_probe(vault: Vault, name: str, data: bytes, *, forbid: tuple[str, ...] = ()) -> dict[str, Any]:
    ctx = vault.ctx
    expect(len(data) <= MAX_ARCHIVE_BYTES, f"generador fuera de límite: {name} {len(data)} bytes")
    (vault.loc / name).write_bytes(data)
    before, rss = _loc_tree(vault.loc), _rss_peak_kb(ctx)
    started = time.monotonic()
    try:
        out = vault.probe(name, timeout=30)
    except (TimeoutError, socket.timeout) as exc:
        raise Breach(f"'{name}': el backend no responde en 30 s (posible expansión sin límite)") from exc
    elapsed = time.monotonic() - started
    expect(ctx.process is None or ctx.process.poll() is None, f"'{name}': el backend murió")
    for status in (out["create"], out["read"]):
        expect(status is None or status < 500, f"'{name}': error interno {status}: {out['code']} {out['text'][:200]}")
    expect(not _pwned(ctx), f"'{name}': se escribió fuera del destino: {_pwned(ctx)[:3]}")
    expect(_loc_tree(vault.loc) == before, f"'{name}': la lectura creó archivos junto al comprimido")
    for marker in forbid:
        expect(marker not in out["text"], f"'{name}': la respuesta contiene {marker!r} (se siguió un enlace o se recursó)")
    expect(elapsed < 25, f"'{name}': tardó {elapsed:.1f} s")
    grown = _rss_peak_kb(ctx) - rss
    expect(grown < 300_000, f"'{name}': el pico de RSS del backend creció {grown // 1024} MiB")
    return out


def _archive_vault(ctx: Context) -> Vault:
    vault = Vault(ctx)
    control = _archive_probe(vault, "control.zip", _zip_bytes([("hello.txt", b"hola")]))
    if control["read"] != 200 or "hello.txt" not in control["text"]:
        raise NotApplicable(f"control sin cumplir: un zip legítimo no se lista: {control}")
    return vault


def _run_archives(ctx: Context, items: list[tuple[str, bytes]], **kw: Any) -> None:
    vault = _archive_vault(ctx)
    for name, data in items:
        _archive_probe(vault, name, data, **kw)


@attack("FILE-ARC-01", "Comprimidos: bomba por tamaño (zip, tar.gz, tar.bz2, tar.xz)", guarantee=ARC)
def arc_size_bomb(ctx: Context) -> None:
    zip_data = _zip_bomb(64 << 20)
    declared = sum(i.file_size for i in zipfile.ZipFile(io.BytesIO(zip_data)).infolist())
    expect(declared >= 64 << 20 and len(zip_data) < 1 << 20, "generador vacío: el zip no es una bomba")
    items = [("bomb.zip", zip_data)]
    for suffix, comp in (("tar.gz", "gz"), ("tar.bz2", "bz2"), ("tar.xz", "xz")):
        data = _tar_bomb(comp, 48 << 20)
        items.append((f"bomb.{suffix}", data))
    _run_archives(ctx, items)


@attack("FILE-ARC-02", "Comprimidos: número de entradas (60 000 en zip y tar.gz)", guarantee=ARC)
def arc_entry_count(ctx: Context) -> None:
    zip_data = _zip_bytes([(f"{i}", b"") for i in range(60_000)])
    expect(len(zipfile.ZipFile(io.BytesIO(zip_data)).namelist()) == 60_000, "generador defectuoso")
    _run_archives(ctx, [("many.zip", zip_data), ("many.tar.gz", _tar_many(60_000))])


@attack("FILE-ARC-03", "Comprimidos: profundidad y longitud de nombre", guarantee=ARC)
def arc_depth(ctx: Context) -> None:
    deep = "/".join(["d"] * 1500) + "/x.txt"
    long_name = "n" * 60_000
    expect(deep.count("/") >= 1500, "generador defectuoso")
    tar_info = tarfile.TarInfo(deep)
    tar_info.size = 1
    tar_deep = _tar_stream("w:", [(tar_info, io.BytesIO(b"x"))])
    _run_archives(ctx, [("deep.zip", _zip_bytes([(deep, b"x")])), ("long.zip", _zip_bytes([(long_name, b"x")])),
                        ("deep.tar", tar_deep)])


@attack("FILE-ARC-04", "Comprimidos: zip dentro de zip (recursión)", guarantee=ARC)
def arc_nested(ctx: Context) -> None:
    data = _zip_in_zip(8)
    outer = zipfile.ZipFile(io.BytesIO(data)).namelist()
    expect(outer == ["inner7.zip"], f"generador defectuoso: {outer}")
    _run_archives(ctx, [("nested.zip", data)], forbid=("INNER_MARKER",))


@attack("FILE-ARC-05", "Comprimidos: nombres ../, absolutos, con barras invertidas y NUL en zip",
        guarantee=ARC)
def arc_zip_traversal(ctx: Context) -> None:
    data = _zip_traversal(ctx.root)
    expect(b"../PWNED-z1.txt" in data and b"PWNED-z6" in data, "generador defectuoso")
    _run_archives(ctx, [("traversal.zip", data)])


@attack("FILE-ARC-06", "Comprimidos: tar con symlinks, hardlinks, dispositivos, setuid y nombres ../",
        guarantee=ARC)
def arc_tar_links(ctx: Context) -> None:
    data = _tar_zoo(ctx.root)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        kinds = {m.type for m in archive.getmembers()}
    expect({tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE} <= kinds, "generador defectuoso")
    _run_archives(ctx, [("zoo.tar", data), ("zoo.tar.gz", gzip.compress(data))], forbid=("root:x:",))


@attack("FILE-ARC-07", "Comprimidos: cabeceras que mienten (tamaños, contador, offsets, longname)",
        guarantee=ARC)
def arc_lying_headers(ctx: Context) -> None:
    base = _zip_bomb(32 << 20, zip64=False)
    liar = _patch(_patch(base, b"PK\x01\x02", 24, struct.pack("<I", 1)), b"PK\x03\x04", 22, struct.pack("<I", 1))
    count = _patch(_patch(base, b"PK\x05\x06", 8, b"\xff\xff", last=True), b"PK\x05\x06", 10, b"\xff\xff", last=True)
    offset = _patch(base, b"PK\x05\x06", 16, struct.pack("<I", 0xFFFFFFF0), last=True)
    items = [("lie-size.zip", liar), ("lie-count.zip", count), ("lie-offset.zip", offset),
             ("lie-size.tar", _tar_lies()), ("lie-longname.tar", _tar_longname_lie()),
             ("lie-pax.tar", _tar_pax_lie()), ("lie-gz.tar.gz", gzip.compress(_tar_lies())[:-8]),
             ("lie-bz2.tar.bz2", bz2.compress(_tar_lies())[:-6]), ("lie-xz.tar.xz", lzma.compress(_tar_lies())[:-12])]
    _run_archives(ctx, items)
