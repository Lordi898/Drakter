#!/usr/bin/env python3
"""Comprobacion breve de SafeFS y del lector de enlaces (CLAUDE.md seccion 4, excepcion 1).

Uso (desde backend/):
    TMPDIR=/var/tmp/drakter-almacen-relaciones \
        /var/tmp/drakter-almacen-relaciones/venv/bin/python tests/check_storage_paths.py
Sale con codigo != 0 si algun caso falla. No toca la red: todo va a 127.0.0.1.
"""
from __future__ import annotations

import ctypes
import errno
import http.server
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import storage_safefs as fs  # noqa: E402
from app.services.readers import Extracted, ReadOptions  # noqa: E402
from app.services.readers import link  # noqa: E402
from app.services.storage_ports import StorageLimits  # noqa: E402

RESULTS: list[tuple[bool, str]] = []
LIMITS = StorageLimits(link_timeout_seconds=5.0)


def check(name: str, cond: bool, detail: str = "") -> bool:
    RESULTS.append((bool(cond), name))
    print(f"{'OK  ' if cond else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not cond else ""))
    return bool(cond)


def _try(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def main() -> int:
    base = os.environ.get("TMPDIR") or "/var/tmp/drakter-almacen-relaciones"
    Path(base).mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="drakter-paths-", dir=base))
    try:
        check_paths(tmp)
        check_link_rejections()
        check_link_server()
        check_link_tls(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = [n for ok, n in RESULTS if not ok]
    print(f"\nResumen: {len(RESULTS) - len(bad)}/{len(RESULTS)} OK, {len(bad)} FAIL")
    for n in bad:
        print(f"  FAIL: {n}")
    return 1 if bad else 0


# --- SafeFS -----------------------------------------------------------------


def check_paths(tmp: Path) -> None:
    root = tmp / "root"
    outside = tmp / "outside"
    (root / "sub" / "deep").mkdir(parents=True)
    outside.mkdir()
    (root / "a.txt").write_text("hola")
    (root / "sub" / "b.txt").write_text("b")
    (root / "sub" / "deep" / "c.txt").write_text("c")
    (outside / "secret.txt").write_text("secreto")
    (root / ".env").write_text("TOKEN=1")
    (root / ".env.local").write_text("TOKEN=2")
    (root / ".ssh").mkdir()
    (root / ".ssh" / "id").write_text("k")
    (root / "sub" / ".gnupg").mkdir()
    (root / "sub" / ".gnupg" / "k").write_text("k")
    (root / "forbidden").mkdir()
    (root / "forbidden" / "x.txt").write_text("x")
    (root / "forbidden2").mkdir()
    (root / "forbidden2" / "y.txt").write_text("y")
    (root / "final_link").symlink_to(root / "a.txt")
    (root / "dir_link").symlink_to(root / "sub")
    (root / "escape").symlink_to(outside)
    (root / "abs_file").symlink_to(outside / "secret.txt")
    os.link(root / "a.txt", tmp / "peer.txt")  # a.txt queda con dos nombres
    (root / "solo.txt").write_text("solo")
    os.mkfifo(root / "pipe")

    denied = [root / "forbidden"]
    canonical, identity = fs.validate_location_path(str(root), denied=[outside])
    check("raiz valida aceptada", canonical == root)

    def rejected(relative: str) -> bool:
        return isinstance(_try(fs.open_file, root, identity, relative, denied=denied),
                          fs.PathNotAllowed)

    with fs.open_file(root, identity, "solo.txt", denied=denied) as opened:
        check("lectura normal", os.read(opened.fd, 10) == b"solo" and opened.size == 4)
        fd = opened.fd
    check("__exit__ cierra el fd", isinstance(_try(os.fstat, fd), OSError))
    opened.close()
    check("close repetido no falla", True)
    with fs.open_file(root, identity, "./sub//b.txt", denied=denied) as opened:
        check("ruta normalizada", os.read(opened.fd, 1) == b"b")

    for name, relative in (
        ("..", "../outside/secret.txt"), (".. interno", "sub/../../outside/secret.txt"),
        ("absoluto", str(outside / "secret.txt")), ("NUL", "a\0.txt"), ("control", "a\n.txt"),
        ("vacio", ""), ("solo punto", "."), ("surrogate", "a\udc80.txt"),
        ("symlink final", "final_link"), ("symlink intermedio", "dir_link/b.txt"),
        ("symlink que escapa", "escape/secret.txt"), ("symlink absoluto", "abs_file"),
        ("hardlink", "a.txt"), ("FIFO", "pipe"), ("directorio", "sub"),
        (".env", ".env"), (".env.local", ".env.local"), (".ENV", ".ENV"),
        (".ssh", ".ssh/id"), (".gnupg intermedio", "sub/.gnupg/k"),
        ("ruta denegada", "forbidden/x.txt"),
    ):
        check(f"open_file rechaza {name}", rejected(relative))
    with fs.open_file(root, identity, "forbidden2/y.txt", denied=denied) as opened:
        check("denegacion por componentes, no por prefijo", opened.size == 1)
    check("archivo ausente es MissingFile",
          isinstance(_try(fs.open_file, root, identity, "nada.txt", denied=denied), fs.MissingFile))
    check("padre que es archivo es MissingFile",
          isinstance(_try(fs.open_file, root, identity, "solo.txt/x", denied=denied),
                     fs.MissingFile))
    check("max_bytes da FileTooLarge",
          isinstance(_try(fs.open_file, root, identity, "solo.txt", denied=denied, max_bytes=3),
                     fs.FileTooLarge))
    check("mensaje sin ruta", "solo" not in str(
        _try(fs.open_file, root, identity, "a.txt", denied=denied)))

    entry = fs.stat_file(root, identity, "solo.txt", denied=denied)
    check("stat_file", entry.size == 4 and entry.nlink == 1 and entry.relative_path == "solo.txt")
    for name, relative in (("symlink", "final_link"), ("FIFO", "pipe"), ("hardlink", "a.txt"),
                           (".env", ".env"), ("denegada", "forbidden/x.txt")):
        check(f"stat_file rechaza {name}", isinstance(
            _try(fs.stat_file, root, identity, relative, denied=denied), fs.PathNotAllowed))

    found = {e.relative_path for e in fs.scan(root, identity, denied=denied,
                                              max_entries=100, max_depth=8)}
    check("scan solo ve lo servible",
          found == {"solo.txt", "sub/b.txt", "sub/deep/c.txt", "forbidden2/y.txt"}, str(found))
    check("scan respeta max_depth", "sub/deep/c.txt" not in {
        e.relative_path for e in fs.scan(root, identity, denied=denied, max_entries=100,
                                         max_depth=1)})
    check("scan respeta max_entries", len(list(
        fs.scan(root, identity, denied=denied, max_entries=2, max_depth=8))) == 2)
    if os.geteuid() != 0:
        (root / "closed").mkdir()
        (root / "closed").chmod(0)
        survivors = {e.relative_path for e in fs.scan(root, identity, denied=denied,
                                                      max_entries=100, max_depth=8)}
        check("scan salta un subdirectorio EACCES", "solo.txt" in survivors)
        (root / "closed").chmod(0o700)

    # openat2 ausente o bloqueado: nunca se cae a un open normal.
    real = fs._syscall
    for code in (errno.ENOSYS, errno.EPERM):
        def blocked(*_a, code=code):
            ctypes.set_errno(code)
            return -1
        fs._syscall = lambda: blocked
        result = _try(fs.open_file, root, identity, "solo.txt", denied=denied)
        fs._syscall = real
        check(f"{errno.errorcode[code]} falla cerrado", isinstance(result, fs.PathNotAllowed))

    moved = tmp / "moved"
    root_link = tmp / "root_link"
    root_link.symlink_to(root)
    check("raiz symlink rechazada al abrir", isinstance(
        _try(fs.open_file, root_link, identity, "solo.txt", denied=[]), fs.PathNotAllowed))
    root.rename(moved)
    root.mkdir()
    (root / "solo.txt").write_text("otra")
    check("raiz sustituida rechazada", isinstance(
        _try(fs.open_file, root, identity, "solo.txt", denied=[]), fs.PathNotAllowed))
    check("raiz sustituida rechazada en scan", isinstance(
        _try(lambda: list(fs.scan(root, identity, denied=[], max_entries=9, max_depth=1))),
        fs.PathNotAllowed))

    home = Path.home()
    for name, path, deny in (
        ("/", "/", []), ("home", str(home), []), ("padre del home", str(home.parent), []),
        ("relativa", "algo/rel", []), ("con ..", f"{moved}/../moved", []), ("NUL", "/va\0r", []),
        ("symlink", str(root_link), []), ("inexistente", str(tmp / "nada"), []),
        ("archivo", str(moved / "solo.txt"), []), (".ssh dentro", str(moved / ".ssh"), []),
        ("contiene denegada", str(moved), [moved / "sub"]),
        ("dentro de denegada", str(moved / "sub"), [moved]),
        ("denegada exacta", str(moved / "sub"), [moved / "sub"]),
        ("denegada via symlink", str(moved / "sub"), [tmp / "root_link2"]),
    ):
        if name == "denegada via symlink":
            (tmp / "root_link2").symlink_to(moved / "sub")
        check(f"validate_location_path rechaza {name}",
              isinstance(_try(fs.validate_location_path, path, deny), fs.PathNotAllowed))


# --- Enlaces: rechazos sin conexion -----------------------------------------


class Recorder:
    def __init__(self, port: int = 0, tls: ssl.SSLContext | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.port = port
        self.tls = tls

    def __call__(self, host, port, ip, tls, timeout):
        self.calls.append((host, ip))
        return link._PinnedConnection(host, self.port or port, "127.0.0.1",
                                      self.tls or tls, timeout)


FAKE_DNS = {
    "public.test": ["93.184.216.34"],
    "rebind.test": ["127.0.0.1"],
    "mixed.test": ["93.184.216.34", "10.0.0.1"],
    "metadata.test": ["169.254.169.254"],
    "mapped.test": ["::ffff:127.0.0.1"],
    "compat.test": ["::7f00:1"],
    "nat64.test": ["64:ff9b::7f00:1"],
    "sixtofour.test": ["2002:7f00:1::1"],
    "cgnat.test": ["100.64.0.1"],
    "multicast.test": ["224.0.0.1"],
    "reserved.test": ["240.0.0.1"],
    "nodata.test": [],
}


def fake_resolve(host, _port, _timeout):
    return FAKE_DNS.get(host, [host])  # un literal de IP se resuelve a si mismo


def check_link_rejections() -> None:
    def blocked(url: str, **kw) -> bool:
        rec = Recorder()
        result = _try(link._fetch, url, ReadOptions(), LIMITS, connector=rec, **kw)
        return isinstance(result, link.UrlNotAllowed) and not rec.calls

    for url in (
        "http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/",
        "http://[::ffff:127.0.0.1]/", "http://[::1]/", "http://[::7f00:1]/",
        "http://10.0.0.1/", "http://192.168.1.1/", "http://0.0.0.0/",
        "http://2130706433/", "http://0x7f.1/", "http://localhost/",
        "file:///etc/passwd", "ftp://93.184.216.34/", "gopher://93.184.216.34/",
        "http://93.184.216.34:22/", "http://93.184.216.34:8080/",
        "http://user:pw@93.184.216.34/", "http://user@93.184.216.34/",
        "http://93.184.216.34@127.0.0.1/", "http://93.184.216.34:99999/",
        "http://93.184.216.34\\@127.0.0.1/", "http://93.184.216.34/\r\nX: y", "http://", "",
        "http://exam\tple.test/",
    ):
        check(f"URL rechazada: {url!r}", blocked(url))
    for host in ("rebind", "mixed", "metadata", "mapped", "compat", "nat64", "sixtofour",
                 "cgnat", "multicast", "reserved"):
        check(f"DNS rechazado: {host}", blocked(f"http://{host}.test/", resolver=fake_resolve))
    result = _try(link._fetch, "http://nodata.test/", ReadOptions(), LIMITS,
                  resolver=fake_resolve, connector=Recorder())
    check("nombre sin IP es LinkFetchFailed", isinstance(result, link.LinkFetchFailed))
    check("mensaje sin URL", "169.254" not in str(
        _try(link.read_link, "http://169.254.169.254/", ReadOptions(), LIMITS)))
    check("read_link publica sin inyectar nada rechaza 127.0.0.1", isinstance(
        _try(link.read_link, "http://127.0.0.1/", ReadOptions(), LIMITS), link.UrlNotAllowed))


# --- Enlaces: servidor local ------------------------------------------------

HTML = (
    "<html><head><title>Hola &amp; adios</title><style>.x{color:red}</style></head><body>"
    "<script>alert('no')</script><p>Uno &lt;dos&gt;</p><div>tres</div></body></html>"
)


class Handler(http.server.BaseHTTPRequestHandler):
    seen: list[dict[str, str]] = []
    protocol_version = "HTTP/1.1"

    def log_message(self, *_a) -> None:
        pass

    def _send(self, status: int, body: bytes = b"", **headers: str) -> None:
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key.replace("_", "-"), value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        Handler.seen.append({k.lower(): v for k, v in self.headers.items()})
        routes = {
            "/page": lambda: self._send(200, HTML.encode(), Content_Type="text/html; charset=utf-8"),
            "/rel": lambda: self._send(302, Location="/page"),
            "/abs": lambda: self._send(301, Location="http://public.test/page"),
            "/to-ip": lambda: self._send(302, Location="http://127.0.0.1/"),
            "/to-meta": lambda: self._send(302, Location="http://169.254.169.254/"),
            "/to-rebind": lambda: self._send(302, Location="http://rebind.test/"),
            "/to-mapped": lambda: self._send(302, Location="http://[::ffff:127.0.0.1]/"),
            "/to-port": lambda: self._send(302, Location="http://public.test:22/"),
            "/to-file": lambda: self._send(302, Location="file:///etc/passwd"),
            "/loop": lambda: self._send(302, Location="/loop"),
            "/noloc": lambda: self._send(302),
            "/404": lambda: self._send(404, b"no", Content_Type="text/plain"),
            "/bin": lambda: self._send(200, b"\x7fELF", Content_Type="application/octet-stream"),
            "/notype": lambda: self._send(200, b"x"),
            "/badcharset": lambda: self._send(200, b"ok", Content_Type="text/plain; charset=nope"),
            "/gzip": lambda: self._send(200, b"x", Content_Type="text/plain",
                                        Content_Encoding="gzip"),
            "/json": lambda: self._send(200, b'{"a": 1}', Content_Type="application/json"),
            "/big": lambda: self._send(200, b"z" * 5000, Content_Type="text/plain"),
        }
        if self.path == "/drip":
            self.wfile.write(b"HTTP/1.1 200 OK\r\n")
            try:
                while True:
                    self.wfile.write(b"X-Slow: 1\r\n")
                    self.wfile.flush()
                    time.sleep(0.1)
            except OSError:
                self.close_connection = True
            return
        routes.get(self.path, lambda: self._send(404))()


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        pass


def _serve() -> Server:
    server = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def check_link_server() -> None:
    server = _serve()
    port = server.server_address[1]
    try:
        def fetch(path: str, options=ReadOptions(), limits=LIMITS):
            rec = Recorder(port)
            return (_try(link._fetch, f"http://public.test{path}", options, limits,
                         resolver=fake_resolve, connector=rec), rec)

        result, rec = fetch("/page")
        ok = isinstance(result, Extracted)
        check("descarga HTML", ok, repr(result))
        if ok:
            check("HTML a texto sin script ni style", result.text == "Uno <dos>\ntres", result.text)
            check("title en metadatos", result.metadata["title"] == "Hola & adios")
        check("conecta a la IP validada", rec.calls == [("public.test", "93.184.216.34")])
        sent = Handler.seen[-1]
        check("Host del nombre", sent.get("host", "").startswith("public.test"), str(sent))
        check("User-Agent generico", sent.get("user-agent") == "Drakter/0.1")
        check("sin cookies ni referer", not {"cookie", "referer", "authorization"} & set(sent))

        result, _ = fetch("/page", ReadOptions(offset=4, max_chars=3))
        check("offset y max_chars", isinstance(result, Extracted) and result.text == "<do"
              and result.truncated and result.next_offset == 7, repr(result))
        result, _ = fetch("/big", limits=StorageLimits(link_max_bytes=1000, max_read_chars=5000))
        check("link_max_bytes corta el cuerpo", isinstance(result, Extracted)
              and len(result.text) == 1000 and result.truncated
              and result.next_offset is None, repr(result))

        result, rec = fetch("/rel")
        check("redireccion relativa permitida", isinstance(result, Extracted)
              and len(rec.calls) == 2 and result.metadata["redirects"] == 1, repr(result))

        for path in ("/to-ip", "/to-meta", "/to-rebind", "/to-mapped", "/to-port", "/to-file"):
            result, rec = fetch(path)
            check(f"redireccion cortada {path}", isinstance(result, link.UrlNotAllowed)
                  and len(rec.calls) == 1, repr(result))
        result, rec = fetch("/loop")
        check("limite de redirecciones", isinstance(result, link.LinkFetchFailed)
              and len(rec.calls) == LIMITS.link_max_redirects + 1, repr(result))
        for path in ("/noloc", "/404", "/bin", "/notype", "/gzip"):
            result, _ = fetch(path)
            check(f"{path} es LinkFetchFailed", isinstance(result, link.LinkFetchFailed),
                  repr(result))
        result, _ = fetch("/json")
        check("JSON aceptado", isinstance(result, Extracted) and result.text == '{"a": 1}')
        result, _ = fetch("/badcharset")
        check("charset invalido no rompe", isinstance(result, Extracted) and result.text == "ok")

        started = time.monotonic()
        result, _ = fetch("/drip", limits=StorageLimits(link_timeout_seconds=0.6))
        elapsed = time.monotonic() - started
        check("tope de tiempo total con goteo", isinstance(result, link.LinkFetchFailed)
              and elapsed < 2.0, f"{result!r} {elapsed:.2f}s")
    finally:
        server.shutdown()
        server.server_close()


def _make_cert(tmp: Path, name: str) -> tuple[Path, Path] | None:
    cert, key = tmp / f"{name}.crt", tmp / f"{name}.key"
    done = subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
         "-nodes", "-days", "1", "-subj", f"/CN={name}", "-addext", f"subjectAltName=DNS:{name}",
         "-keyout", str(key), "-out", str(cert)],
        capture_output=True, check=False,
    )
    return (cert, key) if done.returncode == 0 else None


def check_link_tls(tmp: Path) -> None:
    """TLS contra un servidor local: conexion fijada, SNI y verificacion del nombre."""
    pair = _make_cert(tmp, "drakter.test") if shutil.which("openssl") else None
    if pair is None:
        print("NO COMPROBADO: TLS local (sin openssl)")
        return
    cert, key = pair
    FAKE_DNS["drakter.test"] = ["93.184.216.34"]
    FAKE_DNS["other.test"] = ["93.184.216.34"]

    snis: list[str | None] = []
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(cert, key)
    server_ctx.sni_callback = lambda _s, name, _c: snis.append(name)
    server = Server(("127.0.0.1", 0), Handler)
    server.socket = server_ctx.wrap_socket(server.socket, server_side=True,
                                           do_handshake_on_connect=False)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    def trusting() -> ssl.SSLContext:
        return ssl.create_default_context(cafile=str(cert))

    try:
        result = _try(link._fetch, "https://drakter.test/page", ReadOptions(), LIMITS,
                      resolver=fake_resolve, connector=Recorder(port))
        check("TLS rechaza certificado no confiable", isinstance(result, link.LinkFetchFailed),
              repr(result))
        result = _try(link._fetch, "https://other.test/page", ReadOptions(), LIMITS,
                      resolver=fake_resolve, connector=Recorder(port, trusting()))
        check("TLS rechaza nombre distinto", isinstance(result, link.LinkFetchFailed), repr(result))
        snis.clear()
        result = _try(link._fetch, "https://drakter.test/page", ReadOptions(), LIMITS,
                      resolver=fake_resolve, connector=Recorder(port, trusting()))
        check("TLS valido con IP fijada", isinstance(result, Extracted), repr(result))
        check("SNI con el nombre real", snis == ["drakter.test"], str(snis))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
