"""Lector de enlaces: descarga texto de una URL pública sin abrir una vía SSRF.

El nombre se resuelve una vez, se validan todas sus IP y se conecta a una de ellas, de
modo que un segundo DNS no pueda cambiar el destino. Cada redirección repite el proceso.
El contenido es dato no confiable: no se ejecuta nada y no se envían cookies. Los
mensajes de excepción son fijos: nunca incluyen la URL ni el contenido.
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
import threading
import time
from collections.abc import Callable, Sequence
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Final, NamedTuple
from urllib.parse import quote, urljoin, urlsplit

from . import Extracted, MetaValue, ReadOptions

if TYPE_CHECKING:
    from app.services.storage_ports import StorageLimits

_PORTS: Final = {"http": 80, "https": 443}
_ALLOWED_PORTS: Final = frozenset({80, 443})
_REDIRECTS: Final = frozenset({301, 302, 303, 307, 308})
_HTML_TYPES: Final = frozenset({"text/html", "application/xhtml+xml"})
_EXACT_TYPES: Final = _HTML_TYPES | {"application/json"}
_READ_CHUNK: Final = 64 * 1024
_REQUEST_HEADERS: Final = {
    "User-Agent": "Drakter/0.1",
    "Accept": "text/html, application/xhtml+xml, application/json, text/*;q=0.8",
    "Connection": "close",
}
_URL_SAFE: Final = "/%:@!$&'()*+,;=~-._?"
_NAT64_PREFIX: Final = ipaddress.ip_network("64:ff9b::/96")
_BLOCK_TAGS: Final = frozenset({
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "figcaption",
    "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li",
    "main", "nav", "ol", "p", "pre", "section", "table", "tr", "ul",
})  # fmt: skip


class UrlNotAllowed(Exception):
    """Traducir a `AppError` `url_not_allowed`."""

    def __init__(self) -> None:
        super().__init__("URL not allowed")


class LinkFetchFailed(Exception):
    """Traducir a `AppError` `link_fetch_failed`."""

    def __init__(self) -> None:
        super().__init__("Link could not be fetched")


class _Target(NamedTuple):
    url: str
    host: str
    port: int
    secure: bool
    request_target: str


class _Body(NamedTuple):
    data: bytes
    cut: bool
    content_type: str
    charset: str | None
    final_url: str
    redirects: int


Resolver = Callable[[str, int, float], Sequence[str]]


class _PinnedConnection(http.client.HTTPConnection):
    """Conecta a una IP ya validada; `host` queda para `Host`, SNI y certificado."""

    def __init__(
        self, host: str, port: int, ip: str, tls: ssl.SSLContext | None, timeout: float
    ) -> None:
        super().__init__(host, port, timeout=timeout)
        self._ip = ip
        self._tls = tls
        self._live: socket.socket | None = None

    def connect(self) -> None:
        raw = socket.create_connection((self._ip, self.port), self.timeout)
        if self._tls is None:
            self.sock = self._live = raw
            return
        try:
            wrapped = self._tls.wrap_socket(
                raw, server_hostname=self.host, do_handshake_on_connect=False
            )
        except BaseException:
            raw.close()
            raise
        # Asignado antes de negociar: `abort` debe poder cortar un handshake lento.
        self.sock = self._live = wrapped
        wrapped.do_handshake()

    def abort(self) -> None:
        """Corta el socket desde otro hilo. El timeout de socket es por lectura: un
        servidor que gotea bytes nunca lo agotaría, así que el tope total se impone aquí.
        Va por `socket.socket`: `SSLSocket.shutdown` desmontaría TLS bajo una lectura.
        """
        if self._live is not None:
            try:
                socket.socket.shutdown(self._live, socket.SHUT_RDWR)
            except OSError:
                pass


Connector = Callable[[str, int, str, ssl.SSLContext | None, float], _PinnedConnection]


def _embedded_ipv4(ip: ipaddress.IPv6Address) -> list[ipaddress.IPv4Address]:
    embedded: list[ipaddress.IPv4Address] = []
    if ip.ipv4_mapped is not None:
        embedded.append(ip.ipv4_mapped)
    if int(ip) >> 32 == 0:  # IPv4 compatible, ::a.b.c.d
        embedded.append(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
    if ip in _NAT64_PREFIX:
        embedded.append(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
    if ip.sixtofour is not None:
        embedded.append(ip.sixtofour)
    if ip.teredo is not None:
        embedded.extend(ip.teredo)
    return embedded


def _single_ip_allowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return ip.is_global and not (ip.is_multicast or ip.is_reserved)


def _ip_allowed(text: str) -> bool:
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return False
    if not _single_ip_allowed(ip):
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        return all(_single_ip_allowed(inner) for inner in _embedded_ipv4(ip))
    return True


def _parse(url: str) -> _Target:
    if not isinstance(url, str) or not url:
        raise UrlNotAllowed
    # urlsplit borra tabuladores y saltos en silencio; `\` lo interpretan distinto los
    # navegadores. Mejor rechazarlos que comprobar una URL y pedir otra.
    if "\\" in url or any(ord(ch) <= 32 or ord(ch) == 127 for ch in url):
        raise UrlNotAllowed
    try:
        parts = urlsplit(url)
        port = parts.port
        host = parts.hostname
    except ValueError:
        raise UrlNotAllowed from None
    default_port = _PORTS.get(parts.scheme)
    if default_port is None or not host or "@" in parts.netloc:
        raise UrlNotAllowed
    port = default_port if port is None else port
    if port not in _ALLOWED_PORTS or "%" in host:
        raise UrlNotAllowed
    try:
        ascii_host = host if host.isascii() else host.encode("idna").decode("ascii")
    except UnicodeError:
        raise UrlNotAllowed from None
    target = quote(parts.path or "/", safe=_URL_SAFE)
    if parts.query:
        target += "?" + quote(parts.query, safe=_URL_SAFE)
    return _Target(url, ascii_host, port, parts.scheme == "https", target)


def _system_resolve(host: str, port: int, timeout: float) -> Sequence[str]:
    """`getaddrinfo` no admite timeout: se espera en un hilo que no retiene el proceso."""
    found: list[str] = []
    done = threading.Event()

    def work() -> None:
        try:
            infos = socket.getaddrinfo(
                host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
            )
            found.extend(str(info[4][0]) for info in infos)
        except (OSError, UnicodeError):
            pass
        done.set()

    threading.Thread(target=work, daemon=True).start()
    if not done.wait(timeout):
        raise LinkFetchFailed
    return found


def _remaining(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise LinkFetchFailed
    return left


def _validated_ips(target: _Target, resolver: Resolver, deadline: float) -> list[str]:
    ips = list(dict.fromkeys(resolver(target.host, target.port, _remaining(deadline))))
    if not ips:
        raise LinkFetchFailed
    # Todas: basta una IP interna entre varias para que el destino no sea de fiar.
    if not all(_ip_allowed(ip) for ip in ips):
        raise UrlNotAllowed
    return ips


def _connect(
    target: _Target, ips: Sequence[str], connector: Connector, deadline: float
) -> tuple[_PinnedConnection, threading.Timer]:
    """Conexión viva y su vigilante, ya en marcha para cubrir también el handshake."""
    tls = ssl.create_default_context() if target.secure else None
    for ip in ips:
        conn = connector(target.host, target.port, ip, tls, _remaining(deadline))
        watchdog = threading.Timer(_remaining(deadline), conn.abort)
        watchdog.daemon = True
        watchdog.start()
        try:
            conn.connect()
        except OSError:
            watchdog.cancel()
            conn.close()
            continue
        return conn, watchdog
    raise LinkFetchFailed


def _read_body(response: http.client.HTTPResponse, limit: int, deadline: float) -> tuple[bytes, bool]:
    body = bytearray()
    while True:
        chunk = response.read(min(_READ_CHUNK, limit + 1 - len(body)))
        _remaining(deadline)  # un corte de `abort` llega aquí como fin de datos
        if not chunk:
            return bytes(body), False
        body += chunk
        if len(body) > limit:
            return bytes(body[:limit]), True


def _accepted_type(response: http.client.HTTPResponse) -> str:
    # `headers.get_content_type` inventa text/plain si falta o está mal formada.
    raw = response.getheader("Content-Type")
    if raw is None:
        raise LinkFetchFailed
    content_type = raw.split(";", 1)[0].strip().lower()
    if not (content_type.startswith("text/") or content_type in _EXACT_TYPES):
        raise LinkFetchFailed
    return content_type


def _fetch_hop(
    target: _Target,
    limits: StorageLimits,
    resolver: Resolver,
    connector: Connector,
    deadline: float,
    redirects: int,
) -> _Body | str:
    """Una petición. Devuelve el cuerpo, o la URL absoluta de la redirección."""
    ips = _validated_ips(target, resolver, deadline)
    conn: _PinnedConnection | None = None
    watchdog: threading.Timer | None = None
    try:
        conn, watchdog = _connect(target, ips, connector, deadline)
        conn.request("GET", target.request_target, headers=_REQUEST_HEADERS)
        response = conn.getresponse()
        if response.status in _REDIRECTS:
            location = response.getheader("Location")
            if not location:
                raise LinkFetchFailed
            return urljoin(target.url, location.strip())
        if response.status != 200:
            raise LinkFetchFailed
        # Sin Accept-Encoding no debería venir comprimido; nada de descomprimir bombas.
        if (response.getheader("Content-Encoding") or "identity").strip().lower() != "identity":
            raise LinkFetchFailed
        content_type = _accepted_type(response)
        data, cut = _read_body(response, limits.link_max_bytes, deadline)
        charset = response.headers.get_content_charset()
        return _Body(data, cut, content_type, charset, target.url, redirects)
    except (OSError, http.client.HTTPException, ValueError):
        raise LinkFetchFailed from None
    finally:
        if watchdog is not None:
            watchdog.cancel()
        if conn is not None:
            conn.close()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title: list[str] = []
        self._ignored = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._ignored += 1
        elif tag == "title":
            self._in_title = True
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._ignored = max(0, self._ignored - 1)
        elif tag == "title":
            self._in_title = False
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored:
            return
        (self.title if self._in_title else self.parts).append(data)


def _html_to_text(markup: str) -> tuple[str, str | None]:
    parser = _TextExtractor()
    try:
        parser.feed(markup)
        parser.close()
    except (AssertionError, ValueError):
        raise LinkFetchFailed from None
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    title = " ".join("".join(parser.title).split())
    return "\n".join(line for line in lines if line), title or None


def _decode(data: bytes, charset: str | None) -> str:
    if charset:
        try:
            return data.decode(charset, errors="replace")
        except (LookupError, UnicodeError):  # nombre inventado por el servidor
            pass
    return data.decode("utf-8", errors="replace")


def _extract(body: _Body, options: ReadOptions, limits: StorageLimits) -> Extracted:
    text = _decode(body.data, body.charset)
    title: str | None = None
    if body.content_type in _HTML_TYPES:
        text, title = _html_to_text(text)

    offset = max(options.offset, 0)
    window = max(min(options.max_chars, limits.max_read_chars), 1)
    end = offset + window
    more_here = end < len(text)
    metadata: dict[str, MetaValue] = {
        "content_type": body.content_type,
        "title": title,
        "final_url": body.final_url,
        "redirects": body.redirects,
        "total_chars": len(text),
        "body_truncated": body.cut,
    }
    return Extracted(text[offset:end], more_here or body.cut, end if more_here else None, metadata)


def _fetch(
    url: str,
    options: ReadOptions,
    limits: StorageLimits,
    *,
    resolver: Resolver = _system_resolve,
    connector: Connector = _PinnedConnection,
) -> Extracted:
    deadline = time.monotonic() + limits.link_timeout_seconds
    target = _parse(url)
    for redirects in range(limits.link_max_redirects + 1):
        outcome = _fetch_hop(target, limits, resolver, connector, deadline, redirects)
        if isinstance(outcome, _Body):
            return _extract(outcome, options, limits)
        target = _parse(outcome)
    raise LinkFetchFailed


def read_link(url: str, options: ReadOptions, limits: StorageLimits) -> Extracted:
    return _fetch(url, options, limits)
