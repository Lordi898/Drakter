#!/usr/bin/env python3
"""Comprobacion breve de lectores (texto, imagen, PDF) y listado seguro de comprimidos.

Uso (desde backend/):
    TMPDIR=/var/tmp/drakter-almacen-relaciones <python> tests/check_storage_archives.py
Sale con codigo != 0 si algun caso falla.
"""
from __future__ import annotations

import io
import os
import struct
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.readers import (  # noqa: E402
    ArchiveLimit, ReadFailed, ReadOptions, UnsupportedFormat, detect_type, extract_for_index, read_file,
)
from app.services.readers.sandbox import run_in_sandbox  # noqa: E402
from app.services.storage_ports import StorageLimits  # noqa: E402

RESULTS: list[tuple[bool, str]] = []
LIM = StorageLimits()


def check(name: str, cond: bool, detail: str = "") -> bool:
    RESULTS.append((bool(cond), name))
    print(f"{'OK  ' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not cond else ""))
    return bool(cond)


def raises(exc: type[BaseException], fn) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception as e:  # noqa: BLE001
        print("   inesperada:", type(e).__name__, e)
        return False
    return False


def rd(path: Path, rtype: str, limits=LIM, **kw):
    fd = os.open(path, os.O_RDONLY)
    try:
        return read_file(fd, rtype, None, ReadOptions(**kw), limits)
    finally:
        os.close(fd)


def tar_bytes(members, mode="w:gz") -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode=mode) as tf:
        for name, data, kind in members:
            ti = tarfile.TarInfo(name)
            if kind == "symlink":
                ti.type, ti.linkname = tarfile.SYMTYPE, "/etc/passwd"
                tf.addfile(ti)
            else:
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def zip_bytes(members) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members:
            zf.writestr(name, data)
    return buf.getvalue()


def png(w: int, h: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I4sIIBBBBB", 13, b"IHDR", w, h, 8, 2, 0, 0, 0) + b"\0\0\0\0"


def jpeg(w: int, h: int) -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\0\x01\x01\0\0\x01\0\x01\0\0"
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, h, w, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="check_readers_", dir=os.environ.get("TMPDIR")))

    def w(name: str, data: bytes) -> Path:
        p = tmp / name
        p.write_bytes(data)
        return p

    # --- deteccion
    check("detect pdf/png/zip", detect_type("x.bin2", b"%PDF-1.4")[0] == "pdf"
          and detect_type("a.jpg", png(1, 1))[0] == "image" and detect_type("a.zip", b"PK\x03\x04")[0] == "archive")
    check("detect docx=document, exe=other, py=code",
          detect_type("a.docx", b"PK\x03\x04")[0] == "document" and detect_type("run.AppImage", b"\x7fELF")[0] == "other"
          and detect_type("a.exe", b"MZ")[0] == "other" and detect_type("a.py", b"print(1)")[0] == "code")
    check("docx no se lee", raises(UnsupportedFormat, lambda: rd(w("a.docx", b"PK\x03\x04"), "document")))

    # --- comprimidos normales
    r = rd(w("ok.zip", zip_bytes([("a.txt", b"hola"), ("d/b.txt", b"x" * 100)])), "archive")
    check("zip normal", r.metadata["entries"] == 2 and r.metadata["total_uncompressed_bytes"] == 104 and "a.txt" in r.text, str(r))
    for ext, mode in (("gz", "w:gz"), ("bz2", "w:bz2"), ("xz", "w:xz")):
        r = rd(w(f"ok.tar.{ext}", tar_bytes([("a.txt", b"hola", "f"), ("b/c.txt", b"adios", "f")], mode)), "archive")
        check(f"tar.{ext} normal", r.metadata["entries"] == 2 and r.metadata["total_uncompressed_bytes"] == 9, str(r))

    # --- nombres peligrosos
    r = rd(w("bad.zip", zip_bytes([("../evil.txt", b"x"), ("/abs.txt", b"y"), ("ok.txt", b"z")])), "archive")
    check("zip con .. y absoluto: listados y marcados", r.metadata["entries"] == 3 and "invalid_name" in str(r.metadata["flags"])
          and "traversal" in r.text and "absolute" in r.text, r.text)
    r = rd(w("sym.tar.gz", tar_bytes([("l", b"", "symlink"), ("f", b"1", "f")])), "archive")
    check("tar con symlink marcado sin error", "symlink" in r.text and r.metadata["entries"] == 2, r.text)

    # --- limites
    small = replace(LIM, archive_max_ratio=100)
    bomb = w("bomb.tar.gz", tar_bytes([("zeros", b"\0" * (30 << 20), "f")]))
    check("bomba de proporcion (tar.gz)", raises(ArchiveLimit, lambda: rd(bomb, "archive", small)))
    check("bomba de proporcion (zip, cabeceras)", raises(ArchiveLimit, lambda: rd(
        w("bomb.zip", zip_bytes([("z", b"\0" * (30 << 20))])), "archive", small)))
    # total real excede con cabeceras pequenas: tar con 2 miembros de 3 MiB; ratio relajada, total 4 MiB
    import random
    rnd = random.Random(1)
    noise = bytes(rnd.getrandbits(8) for _ in range(1 << 20))
    real = w("real.tar.gz", tar_bytes([("a", noise, "f"), ("b", noise, "f"), ("c", noise, "f")]))
    lim_total = replace(LIM, archive_max_total_bytes=2 << 20, archive_max_ratio=10_000)
    check("tar.gz excede total real", raises(ArchiveLimit, lambda: rd(real, "archive", lim_total)))
    # cabeceras pequenas (declarado 2000 B) pero 2000 miembros ocupan ~1 MiB reales: solo el contador real lo ve
    tiny = w("tiny.tar.gz", tar_bytes([(f"m{i}", b"x", "f") for i in range(2000)]))
    msg = ""
    try:
        rd(tiny, "archive", replace(LIM, archive_max_total_bytes=512 << 10, archive_max_ratio=10_000))
    except ArchiveLimit as e:
        msg = str(e)
    check("contador real por trozos (cabeceras pequenas)", msg != "" and "declarado" not in msg, msg)
    many = w("many.zip", zip_bytes([(f"f{i}.txt", b"x") for i in range(30)]))
    check("mas de archive_max_entries (zip)", raises(ArchiveLimit, lambda: rd(many, "archive", replace(LIM, archive_max_entries=10))))
    manyt = w("many.tar.gz", tar_bytes([(f"f{i}", b"x", "f") for i in range(30)]))
    check("mas de archive_max_entries (tar)", raises(ArchiveLimit, lambda: rd(manyt, "archive", replace(LIM, archive_max_entries=10))))
    inner = zip_bytes([("in.txt", b"secreto")])
    r = rd(w("nest.zip", zip_bytes([("inner.zip", inner)])), "archive")
    check("zip dentro de zip no se abre", r.metadata["entries"] == 1 and "nested_archive" in r.text and "in.txt" not in r.text, r.text)
    check("archivo no comprimido en tipo archive", raises(ReadFailed, lambda: rd(w("x.zip", b"hola mundo"), "archive")))
    check("extract_for_index no indexa comprimidos", extract_for_index(os.open(tmp / "ok.zip", os.O_RDONLY), "archive", None, LIM) == "")

    # --- PDF
    from pypdf import PdfWriter
    wr = PdfWriter()
    for _ in range(3):
        wr.add_blank_page(200, 200)
    buf = io.BytesIO()
    wr.write(buf)
    good = w("ok.pdf", buf.getvalue())
    r = rd(good, "pdf")
    check("PDF valido (3 paginas)", r.metadata["pages"] == 3, str(r))
    check("PDF selector page:2 / pages:2-3", rd(good, "pdf", selector="page:2").metadata["pages"] == 3
          and rd(good, "pdf", selector="pages:2-3").truncated is False)
    check("PDF selector fuera de rango", raises(ReadFailed, lambda: rd(good, "pdf", selector="page:9")))
    check("PDF corrupto", raises(ReadFailed, lambda: rd(w("bad.pdf", b"%PDF-1.4\nbasura sin estructura"), "pdf")))
    wr2 = PdfWriter()
    wr2.add_blank_page(100, 100)
    wr2.encrypt("secreto")
    b2 = io.BytesIO()
    wr2.write(b2)
    check("PDF cifrado", raises(ReadFailed, lambda: rd(w("enc.pdf", b2.getvalue()), "pdf")))
    check("extract_for_index pdf no falla", isinstance(extract_for_index(os.open(good, os.O_RDONLY), "pdf", None, LIM), str))

    # --- texto
    r = rd(w("l1.txt", "canción año\n".encode("latin-1")), "text")
    check("texto latin-1", r.text.startswith("canción año") and r.metadata["encoding"] == "latin-1", str(r))
    r = rd(w("u8.txt", b"\xef\xbb\xbfhola\nsegunda\ntercera\n"), "text", selector="lines:2-3")
    check("texto UTF-8 BOM y lines:2-3", r.text == "segunda\ntercera\n", repr(r.text))
    check("binario rechazado", raises(UnsupportedFormat, lambda: rd(w("b.txt", b"ab\x00cd" * 10), "text")))
    r = rd(w("big.txt", b"a" * 100), "text", max_chars=10)
    check("paginacion texto", r.truncated and r.next_offset == 10 and len(r.text) == 10)

    # --- imagen
    r = rd(w("a.png", png(800, 600)), "image")
    check("PNG 800x600", r.text == "Imagen PNG de 800×600" and r.metadata["width"] == 800, r.text)
    r = rd(w("a.jpg", jpeg(640, 480)), "image")
    check("JPEG 640x480", r.metadata["height"] == 480 and r.metadata["format"] == "JPEG", str(r))
    check("imagen truncada", raises(ReadFailed, lambda: rd(w("t.png", png(5, 5)[:20]), "image")))
    check("imagen invalida (extension miente)", raises(ReadFailed, lambda: rd(w("f.png", b"no soy imagen"), "image")))

    # --- aislamiento
    fd = os.open(good, os.O_RDONLY)
    check("timeout de worker", raises(ReadFailed, lambda: run_in_sandbox(
        "_selftest_sleep", fd, {"seconds": 30}, replace(LIM, worker_timeout_seconds=0.7))))
    check("limite de memoria del worker", raises(ReadFailed, lambda: run_in_sandbox(
        "_selftest_alloc", fd, {"bytes": 600 << 20}, replace(LIM, worker_address_space_bytes=256 << 20))))
    check("salida acotada", raises(ReadFailed, lambda: run_in_sandbox(
        "pdf", fd, {"pages": None, "offset": 0, "max_chars": 10}, replace(LIM, worker_max_output_bytes=10))))
    os.close(fd)

    bad = [n for ok, n in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} correctos")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
