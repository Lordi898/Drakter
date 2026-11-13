"""NET: frontera de red del backend local, contrato D-14 (Host, Origin, token y roles, WebSocket,
límite de cuerpo, handshake por stdin).

Contrato atacado (backend/CONTRACT.md §Arranque y guardia):
- Host solo `127.0.0.1:<puerto>`; `localhost` ya no vale.
- CUALQUIER cabecera Origin da 403 `forbidden_origin` (también `app://drakter`), antes de autenticar.
- Solo `Authorization: Bearer`; sin subprotocolo, query ni cookie. `/health` exige token y no hay
  excepción de preflight (no hay CORS).
- Roles: `ui` en todo salvo approve/reject de confirmaciones y escrituras de storage-locations y
  permissions; `approver` solo en eso. Rol equivocado: 403 `permission_denied`.
- WebSocket único en `/api/v1/events`. Cuerpo > 1 MiB: 413 `file_too_large`.
- Arranque: tokens por stdin, handshake inválido = código 2 sin eco, sin session.json.

Cada ataque hace primero un control positivo (`_baseline` / `_ws_baseline`): si falla, ERROR y no
BLOCKED. Los rechazos se exigen por su código concreto.

Claves opcionales del contrato (`ctx.contract.get`): `agent_tools_port`, `agent_tools_path`
(por defecto `/mcp`), `agent_tools_token_key`; el servidor MCP del agente sigue NOT_APPLICABLE
mientras el objetivo no publique su puerto.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import time
from pathlib import Path

from redlib import (
    Breach,
    Context,
    NotApplicable,
    Response,
    _isolated_root,
    attack,
    expect,
)

AUTH = "/api/v1/auth/check"
EVENTS = "/api/v1/events"
ALLOWED_ORIGIN = "app://drakter"  # el D-14 lo rechaza igualmente
MAX_BODY = 1_048_576
_MARKER = "NETMARKERzz9Q"  # valor inventado: no debe reflejarse ni registrarse


# ----------------------------------------------------------------- utilidades


def _fail(problems: list[str], header: str) -> None:
    if problems:
        raise Breach(header + ": " + "; ".join(problems))


def _blob(response: Response) -> bytes:
    return response.body + b"\r\n".join(f"{k}: {v}".encode("latin-1") for k, v in response.headers)


def _leaks(ctx: Context, response: Response) -> bool:
    blob = _blob(response)
    return any(item.encode() in blob for item in (ctx.token, ctx.approver_token, _MARKER))


def _request(
    ctx: Context,
    method: str,
    path: str,
    headers: list[str],
    *,
    host: str | None | bool = True,
    version: str = "HTTP/1.1",
    body: bytes = b"",
    timeout: float = 5.0,
) -> Response:
    """HTTP crudo con control total: `host=True` pone el Host válido, `None` lo omite."""
    lines = [f"{method} {path} {version}"]
    if host is True:
        lines.append(f"Host: {ctx.host}")
    elif isinstance(host, str):
        lines.append(f"Host: {host}")
    lines.extend(headers)
    lines.append("Connection: close")
    if body:
        lines.append(f"Content-Length: {len(body)}")
    payload = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8", "surrogateescape") + body
    return ctx.raw(payload, timeout)


def _bearer(ctx: Context, token: str | None = None) -> str:
    return f"Authorization: Bearer {token or ctx.token}"


def _approver(ctx: Context) -> str:
    return _bearer(ctx, ctx.approver_token)


def _reached(response: Response) -> bool:
    """El guardia dejó pasar la petición: no es 401, 403 del guardia ni 413."""
    return response.error_code not in (
        "unauthorized", "permission_denied", "forbidden_host", "forbidden_origin",
        "forbidden_client", "file_too_large",
    ) and response.status != 0


def _baseline(ctx: Context) -> None:
    """Control positivo: el camino legítimo funciona y cada eje del guardia se distingue."""
    ok = _request(ctx, "GET", AUTH, [_bearer(ctx)])
    if ok.status != 200:
        raise RuntimeError(f"control positivo roto: {ok.status} {ok.body[:80]!r}")
    expected = (
        ("sin token", _request(ctx, "GET", AUTH, []), "unauthorized"),
        ("Host ajeno", _request(ctx, "GET", AUTH, [_bearer(ctx)], host="evil.test"), "forbidden_host"),
        ("Origin", _request(ctx, "GET", AUTH, [_bearer(ctx), f"Origin: {ALLOWED_ORIGIN}"]),
         "forbidden_origin"),
        ("rol approver en ruta ui", _request(ctx, "GET", AUTH, [_approver(ctx)]),
         "permission_denied"),
    )
    for label, response, code in expected:
        if response.error_code != code:
            raise RuntimeError(f"control roto ({label}): esperaba {code}, dio {response.status} "
                               f"{response.error_code}")


def _ws(
    ctx: Context,
    path: str = EVENTS,
    headers: list[str] | None = None,
    *,
    host: str | list[str] | None = None,
    read_extra: float = 0.3,
) -> Response:
    """Handshake WebSocket crudo; devuelve cabeceras y lo que llegue después."""
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    lines = [f"GET {path} HTTP/1.1"]
    if isinstance(host, list):
        lines.extend(f"Host: {item}" for item in host)
    else:
        lines.append(f"Host: {host or ctx.host}")
    lines += [
        "Upgrade: websocket",
        "Connection: Upgrade",
        f"Sec-WebSocket-Key: {key}",
        "Sec-WebSocket-Version: 13",
    ]
    lines.extend(headers or [])
    payload = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8", "surrogateescape")
    with socket.create_connection(("127.0.0.1", ctx.port), timeout=5) as sock:
        sock.sendall(payload)
        data = b""
        deadline = time.monotonic() + 5
        while b"\r\n\r\n" not in data and time.monotonic() < deadline:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
        sock.settimeout(read_extra)
        try:
            while chunk := sock.recv(65536):
                data += chunk
        except OSError:
            pass
    head, _, body = data.partition(b"\r\n\r\n")
    parts = head.decode("latin-1").split("\r\n")
    status_line = parts[0].split(" ")
    status = int(status_line[1]) if len(status_line) >= 2 and status_line[1].isdigit() else 0
    found = [(n.strip(), v.strip()) for n, _, v in (line.partition(":") for line in parts[1:])]
    return Response(status, found, body)


def _ws_baseline(ctx: Context) -> None:
    ok = _ws(ctx, EVENTS, [_bearer(ctx)])
    if ok.status != 101:
        raise RuntimeError(f"control WS roto: Bearer ui en {EVENTS} dio {ok.status}")
    if _ws(ctx, EVENTS, []).status == 101:
        raise RuntimeError("control WS roto: sin token abre")


def _ws_closed(ctx: Context, response: Response, label: str, problems: list[str]) -> None:
    if response.status == 101:
        problems.append(f"{label}: handshake aceptado (101)")
    elif response.status == 0:
        problems.append(f"{label}: sin respuesta HTTP interpretable")
    if _leaks(ctx, response):
        problems.append(f"{label}: la respuesta filtra token o valor enviado")


def _deny_host(ctx: Context, response: Response, label: str, problems: list[str]) -> None:
    # Un 400 del servidor HTTP antes del guardia también es un rechazo; nunca un 200.
    if response.status == 200:
        problems.append(f"{label}: 200 con token válido")
    elif response.status != 400 and response.error_code != "forbidden_host":
        problems.append(f"{label}: status={response.status} code={response.error_code}")
    if _leaks(ctx, response):
        problems.append(f"{label}: filtra token")


# ------------------------------------------------------------------- Host


@attack("NET-01", "DNS rebinding: Host de otro dominio con token válido",
        guarantee="Solo loopback: el Host debe ser exactamente 127.0.0.1:puerto")
def host_foreign(ctx: Context) -> None:
    _baseline(ctx)
    port = ctx.port
    cases = [
        "evil.test", f"evil.test:{port}", f"rebind.evil.test:{port}", f"127.0.0.1.evil.test:{port}",
        f"localhost.evil.test:{port}", f"127.0.0.1:{port}.evil.test", f"evil.test:{port}@127.0.0.1",
        f"127.0.0.1:{port}@evil.test", f"evil.test#127.0.0.1:{port}", f"evil.test/127.0.0.1:{port}",
        f"127.0.0.1:{port},evil.test", f"evil.test, 127.0.0.1:{port}", f"127.0.0.1:{port} evil.test",
        f"xn--lcalhost-y3a.test:{port}", f"ｌocalhost:{port}",
    ]
    problems: list[str] = []
    for host in cases:
        try:
            _deny_host(ctx, _request(ctx, "GET", AUTH, [_bearer(ctx)], host=host), repr(host), problems)
        except OSError as exc:
            problems.append(f"{host!r}: conexión cortada {exc!r}")
    _fail(problems, "Host ajeno aceptado o mal rechazado")


@attack("NET-02", "Host duplicado, ausente, HTTP/1.0 y cabeceras que lo imitan",
        guarantee="Solo loopback: una sola cabecera Host, y la forwarded no cuenta")
def host_double_missing(ctx: Context) -> None:
    _baseline(ctx)
    good, evil = ctx.host, "evil.test"
    problems: list[str] = []
    for label, response in (
        ("Host doble (válido, ajeno)", _request(ctx, "GET", AUTH, [f"Host: {evil}", _bearer(ctx)], host=good)),
        ("Host doble (ajeno, válido)", _request(ctx, "GET", AUTH, [f"Host: {good}", _bearer(ctx)], host=evil)),
        ("Host doble (válido, válido)", _request(ctx, "GET", AUTH, [f"Host: {good}", _bearer(ctx)], host=good)),
        ("sin Host (HTTP/1.1)", _request(ctx, "GET", AUTH, [_bearer(ctx)], host=None)),
        ("sin Host (HTTP/1.0)", _request(ctx, "GET", AUTH, [_bearer(ctx)], host=None, version="HTTP/1.0")),
        ("Host vacío", _request(ctx, "GET", AUTH, [_bearer(ctx)], host="")),
        ("X-Forwarded-Host válido, Host ajeno", _request(
            ctx, "GET", AUTH, [f"X-Forwarded-Host: {good}", f"Forwarded: host={good}", _bearer(ctx)], host=evil)),
        ("X-Original-Host / X-Host válidos, Host ajeno", _request(
            ctx, "GET", AUTH, [f"X-Original-Host: {good}", f"X-Host: {good}", _bearer(ctx)], host=evil)),
        ("Host ajeno con URI absoluta al host bueno", _request(
            ctx, "GET", f"http://{good}{AUTH}", [_bearer(ctx)], host=evil)),
    ):
        _deny_host(ctx, response, label, problems)
    # Forma absoluta con Host válido y URI ajena: sin token no puede dar 200.
    if _request(ctx, "GET", f"http://{evil}{AUTH}", [], host=good).status == 200:
        problems.append("URI absoluta ajena + Host válido sin token: 200")
    for label, raw in (
        ("'Host :' con espacio", f"GET {AUTH} HTTP/1.1\r\nHost : {evil}\r\n{_bearer(ctx)}\r\nConnection: close\r\n\r\n"),
        ("Host con obs-fold", f"GET {AUTH} HTTP/1.1\r\nHost: {evil}\r\n {good}\r\n{_bearer(ctx)}\r\nConnection: close\r\n\r\n"),
    ):
        if ctx.raw(raw.encode("latin-1")).status == 200:
            problems.append(f"{label}: 200")
    _fail(problems, "Host duplicado/ausente/imitado aceptado")


@attack("NET-03", "Host: localhost (ya no vale), sin puerto, puerto incorrecto, IPv6 y otras formas",
        guarantee="Solo loopback: el Host debe ser exactamente 127.0.0.1:<puerto del backend>")
def host_port_forms(ctx: Context) -> None:
    _baseline(ctx)
    port = ctx.port
    other = port + 1 if port < 65535 else port - 1
    cases = [
        f"localhost:{port}", f"LOCALHOST:{port}", f"LocalHost:{port}", f"localhost.:{port}",
        "localhost", "127.0.0.1", f"127.0.0.1:{other}", f"localhost:{other}", "127.0.0.1:",
        f"127.0.0.1:0{port}", f"127.0.0.1:{port}0", "127.0.0.1:80", f"[::1]:{port}", "[::1]",
        f"::1:{port}", f"[::ffff:127.0.0.1]:{port}", f"0.0.0.0:{port}", f"127.0.0.2:{port}",
        f"127.1:{port}", f"2130706433:{port}", f"0x7f.0.0.1:{port}", f"0177.0.0.1:{port}",
        f"127.0.0.1.:{port}", f"[0:0:0:0:0:0:0:1]:{port}", f"+{port}.127.0.0.1",
        f"127.0.0.1:+{port}", f"127.0.0.1: {port}", f"127.0.0.1:{port}:{port}",
        f"http://127.0.0.1:{port}", f"127.0.0.1:{port}/", f"127.0.0.1:{port}x",
        f"Klocalhost:{port}", f"127.0.0.1:{port}\x0b", f"127.0.0.1\x00:{port}",
    ]
    problems: list[str] = []
    for host in cases:
        try:
            _deny_host(ctx, _request(ctx, "GET", AUTH, [_bearer(ctx)], host=host), repr(host), problems)
        except OSError:
            continue
    # La comparación exacta tampoco acepta nada en los otros canales.
    for host in (f"localhost:{port}", "evil.test"):
        _ws_closed(ctx, _ws(ctx, EVENTS, [_bearer(ctx)], host=host), f"WS Host {host!r}", problems)
        for token, label in ((ctx.approver_token, "approver"), (ctx.token, "ui")):
            _deny_host(ctx, _request(ctx, "GET", "/health", [_bearer(ctx, token)], host=host),
                       f"/health {label} Host {host!r}", problems)
    _fail(problems, "Host distinto de 127.0.0.1:<puerto> aceptado")


# ------------------------------------------------------------------ Origin


def _origin_case(ctx: Context, name: str, header_lines: list[str], token: str | None = None) -> list[str]:
    problems: list[str] = []
    response = _request(ctx, "GET", AUTH, [_bearer(ctx, token), *header_lines])
    if response.status == 200 or (response.status != 400 and response.error_code != "forbidden_origin"):
        problems.append(f"{name}: status={response.status} code={response.error_code}")
    for header in ("access-control-allow-origin", "access-control-allow-credentials",
                   "access-control-allow-methods", "access-control-allow-headers", "vary"):
        if response.header(header):
            problems.append(f"{name}: cabecera CORS {header}={response.header(header)}")
    if _leaks(ctx, response):
        problems.append(f"{name}: filtra token")
    return problems


@attack("NET-05", "Cualquier Origin (incluido app://drakter y null) se rechaza con token válido",
        guarantee="D-14: ninguna petición con cabecera Origin llega al backend")
def origin_any(ctx: Context) -> None:
    _baseline(ctx)
    port = ctx.port
    problems: list[str] = []
    origins = [
        ALLOWED_ORIGIN, "null", "http://evil.test", "https://evil.test", f"http://127.0.0.1:{port}",
        f"http://localhost:{port}", "http://localhost:5173", "file://", "*", "", "app://",
        "app://other", "chrome-extension://abcdefghijklmnop", "APP://DRAKTER", "app://drakter/",
        "app://drakter:80", "app://drakter.evil.test", "app://drakterx", "app://drakt",
        "app://drakter@evil.test", "app://evil.test@drakter", "xapp://drakter",
        "app://drakter​", "app://drakтer",
    ]
    for origin in origins:
        problems += _origin_case(ctx, f"Origin {origin!r}", [f"Origin: {origin}"])
    for token, label in ((ctx.approver_token, "approver"),):
        problems += _origin_case(ctx, f"Origin app://drakter con token {label}", [f"Origin: {ALLOWED_ORIGIN}"], token)
    # El Origin se evalúa antes de autenticar: sin token tampoco es 401.
    response = _request(ctx, "GET", AUTH, [f"Origin: {ALLOWED_ORIGIN}"])
    if response.error_code != "forbidden_origin":
        problems.append(f"Origin sin token: code={response.error_code} (esperaba forbidden_origin)")
    response = _request(ctx, "GET", AUTH, [_bearer(ctx, _MARKER), "Origin: http://evil.test"])
    if response.error_code != "forbidden_origin":
        problems.append(f"Origin con token malo: code={response.error_code}")
    _fail(problems, "Origin aceptado o mal rechazado")


@attack("NET-06", "Origin doble, compuesto o con nombre alterado",
        guarantee="D-14: ninguna petición con cabecera Origin llega al backend")
def origin_double(ctx: Context) -> None:
    _baseline(ctx)
    good, evil = ALLOWED_ORIGIN, "http://evil.test"
    problems: list[str] = []
    for name, lines in (
        ("dos Origin (válido, ajeno)", [f"Origin: {good}", f"Origin: {evil}"]),
        ("dos Origin (ajeno, válido)", [f"Origin: {evil}", f"Origin: {good}"]),
        ("dos Origin iguales", [f"Origin: {good}", f"Origin: {good}"]),
        ("Origin lista", [f"Origin: {good}, {evil}"]),
        ("Origin con vacío adicional", [f"Origin: {good}", "Origin: "]),
        ("ORIGIN en mayúsculas", [f"ORIGIN: {good}"]),
        ("oRiGiN mixto", [f"oRiGiN: {evil}"]),
        ("Origin con tabulador previo", [f"Origin:\t{good}"]),
    ):
        problems += _origin_case(ctx, name, lines)
    # Cabeceras que no son Origin no deben ser tratadas como tal ni rechazadas por error.
    for lines in (["Origin-Policy: x"], ["X-Origin: http://evil.test"], ["Referer: http://evil.test/"],
                  ["Sec-Fetch-Site: cross-site"]):
        response = _request(ctx, "GET", AUTH, [_bearer(ctx), *lines])
        if response.status != 200:
            problems.append(f"{lines[0]}: se trata como Origin (status {response.status}); el control no es ambiguo")
    _fail(problems, "Origin doble/compuesto aceptado")


@attack("NET-08", "Sin CORS: ninguna respuesta lleva cabeceras Access-Control-*",
        guarantee="Una página web ajena no puede leer respuestas del backend")
def no_cors(ctx: Context) -> None:
    _baseline(ctx)
    problems: list[str] = []
    probes = [
        _request(ctx, "GET", AUTH, [_bearer(ctx)]),
        _request(ctx, "GET", AUTH, []),
        _request(ctx, "GET", "/health", [_bearer(ctx)]),
        _request(ctx, "GET", "/nope", [_bearer(ctx)]),
        _request(ctx, "DELETE", AUTH, [_bearer(ctx)]),
        _request(ctx, "GET", AUTH, [_bearer(ctx), f"Origin: {ALLOWED_ORIGIN}"]),
        _request(ctx, "GET", AUTH, [f"Origin: {ALLOWED_ORIGIN}"]),
        _request(ctx, "GET", AUTH, [_bearer(ctx)], host="evil.test"),
        _request(ctx, "OPTIONS", AUTH, [f"Origin: {ALLOWED_ORIGIN}", "Access-Control-Request-Method: GET"]),
    ]
    for index, response in enumerate(probes):
        names = [k for k, _ in response.headers if k.lower().startswith("access-control-")]
        if names:
            problems.append(f"respuesta {index} ({response.status}): {names}")
        if response.header("vary") and "origin" in ",".join(response.header("vary")).lower():
            problems.append(f"respuesta {index}: Vary: Origin delata CORS")
    _fail(problems, "Cabeceras CORS presentes")


@attack("NET-09", "Preflight CORS: ningún preflight evita el token ni el Origin",
        guarantee="D-14: no hay excepción de preflight; todo exige token")
def preflight_bypass(ctx: Context) -> None:
    _baseline(ctx)
    problems: list[str] = []
    acrm = "Access-Control-Request-Method: GET"
    origin = f"Origin: {ALLOWED_ORIGIN}"
    routes = [AUTH, EVENTS, "/health", "/api/v1/nonexistent", "/",
              ctx.contract["routes"].get("confirmations", "/api/v1/confirmations")]
    for path in routes:
        # Preflight con Origin (el caso de un navegador): 403 forbidden_origin, sin CORS.
        pre = _request(ctx, "OPTIONS", path, [origin, acrm, "Access-Control-Request-Headers: authorization"])
        if pre.status != 403 or pre.error_code != "forbidden_origin":
            problems.append(f"preflight {path}: status={pre.status} code={pre.error_code}")
        if any(k.lower().startswith("access-control-") for k, _ in pre.headers):
            problems.append(f"preflight {path}: trae cabeceras Access-Control-*")
        # Preflight sin Origin: no es preflight; sin token es 401, no un atajo.
        bare = _request(ctx, "OPTIONS", path, [acrm])
        if bare.status != 401:
            problems.append(f"OPTIONS+ACRM sin Origin ni token {path}: {bare.status} (esperaba 401)")
        plain = _request(ctx, "OPTIONS", path, [])
        if plain.status != 401:
            problems.append(f"OPTIONS sin token {path}: {plain.status} (esperaba 401)")
        # Preflight de Host ajeno.
        rebind = _request(ctx, "OPTIONS", path, [origin, acrm], host="evil.test")
        if rebind.error_code != "forbidden_host":
            problems.append(f"preflight Host ajeno {path}: {rebind.status} {rebind.error_code}")
    for method in ("GET", "POST", "HEAD", "PUT", "DELETE", "PATCH", "TRACE"):
        response = _request(ctx, method, AUTH, [origin, acrm])
        if response.status not in (403,) or response.error_code not in ("forbidden_origin", None):
            problems.append(f"{method} con ACRM y Origin: {response.status} {response.error_code}")
        if b"authenticated" in response.body:
            problems.append(f"{method}: devolvió datos sin token")
    _fail(problems, "El preflight abre una vía sin token")


# ---------------------------------------------------------- Token por HTTP


@attack("NET-10", "Token por query, cookie, cabeceras alternativas o subprotocolo en HTTP",
        guarantee="Solo Authorization: Bearer autentica")
def http_alt_token(ctx: Context) -> None:
    _baseline(ctx)
    problems: list[str] = []
    for tok_label, tok in (("ui", ctx.token), ("approver", ctx.approver_token)):
        cases: list[tuple[str, str, list[str]]] = [
            ("query token", f"{AUTH}?token={tok}", []),
            ("query access_token", f"{AUTH}?access_token={tok}", []),
            ("query authorization", f"{AUTH}?authorization=Bearer%20{tok}", []),
            ("path param", f"{AUTH};token={tok}", []),
            ("cookie token", AUTH, [f"Cookie: token={tok}"]),
            ("cookie Authorization", AUTH, [f"Cookie: Authorization=Bearer {tok}"]),
            ("X-Auth-Token", AUTH, [f"X-Auth-Token: {tok}"]),
            ("X-API-Key", AUTH, [f"X-API-Key: {tok}"]),
            ("X-Authorization", AUTH, [f"X-Authorization: Bearer {tok}"]),
            ("Proxy-Authorization", AUTH, [f"Proxy-Authorization: Bearer {tok}"]),
            ("Sec-WebSocket-Protocol", AUTH, [f"Sec-WebSocket-Protocol: drakter.auth.{tok}"]),
            ("Authorization Basic", AUTH, [f"Authorization: Basic {base64.b64encode(tok.encode()).decode()}"]),
            ("Authorization Token", AUTH, [f"Authorization: Token {tok}"]),
            ("Authorization sin esquema", AUTH, [f"Authorization: {tok}"]),
        ]
        for label, path, headers in cases:
            response = _request(ctx, "GET", path, headers)
            if response.status == 200 or response.error_code != "unauthorized":
                problems.append(f"{tok_label} {label}: status={response.status} code={response.error_code}")
            if response.header("www-authenticate") != ["Bearer"]:
                problems.append(f"{tok_label} {label}: sin WWW-Authenticate: Bearer")
            if _leaks(ctx, response):
                problems.append(f"{tok_label} {label}: filtra token")
    for label, body in (("cuerpo form", f"token={ctx.token}".encode()),
                        ("cuerpo json", b'{"token":"%s"}' % ctx.token.encode())):
        response = _request(ctx, "POST", AUTH, ["Content-Type: application/json"], body=body)
        if response.error_code != "unauthorized":
            problems.append(f"{label}: status={response.status} code={response.error_code}")
    _fail(problems, "Credencial aceptada por un canal que no es Authorization: Bearer")


@attack("NET-11", "Authorization mal formada, duplicada, truncada o enorme",
        guarantee="Solo un Bearer exacto autentica; ui y approver no se mezclan")
def authorization_forms(ctx: Context) -> None:
    _baseline(ctx)
    tok, apr = ctx.token, ctx.approver_token
    problems: list[str] = []
    cases: list[tuple[str, list[str]]] = [
        ("sin valor", ["Authorization:"]),
        ("solo Bearer", ["Authorization: Bearer"]),
        ("Bearer vacío", ["Authorization: Bearer "]),
        ("token truncado", [f"Authorization: Bearer {tok[:-1]}"]),
        ("token + sufijo", [f"Authorization: Bearer {tok}x"]),
        ("prefijo + token", [f"Authorization: Bearer x{tok}"]),
        ("dos espacios", [f"Authorization: Bearer  {tok}"]),
        ("tabulador", [f"Authorization: Bearer\t{tok}"]),
        ("token en mayúsculas", [f"Authorization: Bearer {tok.upper()}"]),
        ("misma longitud, otro valor", [f"Authorization: Bearer {'A' * len(tok)}"]),
        ("dos Authorization (ui, malo)", [_bearer(ctx), f"Authorization: Bearer {_MARKER}"]),
        ("dos Authorization (malo, ui)", [f"Authorization: Bearer {_MARKER}", _bearer(ctx)]),
        ("dos Authorization iguales", [_bearer(ctx), _bearer(ctx)]),
        ("dos Authorization (ui, approver)", [_bearer(ctx), _approver(ctx)]),
        ("dos Authorization (approver, ui)", [_approver(ctx), _bearer(ctx)]),
        ("Bearer ui, approver", [f"Authorization: Bearer {tok}, Bearer {apr}"]),
        ("ui+approver concatenados", [f"Authorization: Bearer {tok}{apr}"]),
        ("coma", [f"Authorization: Bearer {tok},{_MARKER}"]),
        ("no ASCII", ["Authorization: Bearer \xe9\xe8\xe7"]),
        ("NUL en el token", [f"Authorization: Bearer {tok[:10]}\x00{tok[10:]}"]),
        ("marcador inventado", [f"Authorization: Bearer {_MARKER}"]),
    ]
    for label, headers in cases:
        try:
            response = _request(ctx, "GET", AUTH, headers)
        except OSError as exc:
            problems.append(f"{label}: conexión cortada {exc!r}")
            continue
        if response.status == 200:
            problems.append(f"{label}: 200")
        elif response.status != 400 and response.error_code != "unauthorized":
            problems.append(f"{label}: status={response.status} code={response.error_code}")
        if _leaks(ctx, response):
            problems.append(f"{label}: filtra token o el valor enviado")
    # El esquema en minúsculas es válido (RFC 9110): control de que no se rechaza de más.
    if _request(ctx, "GET", AUTH, [f"Authorization: bearer {tok}"]).status != 200:
        problems.append("esquema 'bearer' en minúsculas se rechaza")
    huge = _request(ctx, "GET", AUTH, [f"Authorization: Bearer {'A' * 65000}"])
    if huge.status == 200 or huge.status >= 500:
        problems.append(f"Authorization de 65 KB: status={huge.status}")
    if _request(ctx, "GET", AUTH, [_bearer(ctx)]).status != 200:
        problems.append("tras los ataques, el token legítimo ya no entra (¿servidor caído?)")
    _fail(problems, "Authorization defectuosa")


# --------------------------------------------------------- Rutas y /health


@attack("NET-12", "/health exige token; ninguna ruta parecida es pública",
        guarantee="D-14: no hay rutas públicas; todo pasa por el token")
def health_requires_token(ctx: Context) -> None:
    _baseline(ctx)
    health = _request(ctx, "GET", "/health", [_bearer(ctx)])
    if health.status != 200 or health.json() != {"status": "ok"}:
        raise RuntimeError(f"control roto: /health con token ui da {health.status} {health.body[:80]!r}")
    problems: list[str] = []
    if set(health.json()) != {"status"}:
        problems.append(f"/health expone claves extra: {sorted(health.json())}")
    for method in ("GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"):
        response = _request(ctx, method, "/health", [])
        if response.status != 401 or response.error_code not in ("unauthorized", None):
            problems.append(f"{method} /health sin token: {response.status} {response.error_code}")
    # approver no entra en /health (rol ui).
    response = _request(ctx, "GET", "/health", [_approver(ctx)])
    if response.error_code != "permission_denied":
        problems.append(f"/health con approver: {response.status} {response.error_code}")
    paths = [
        "/health/", "//health", "/Health", "/HEALTH", "/health.", "/health%00", "/health%20",
        f"/health/..{AUTH}", f"/health/%2e%2e{AUTH}", f"/health/..%2f{AUTH[1:]}",
        f"/health;/..{AUTH}", f"{AUTH}/../health", f"{AUTH}/health", f"{AUTH}?/health",
        f"{AUTH}?path=/health", "/health/x", "/healthz", "/health?x=1", "/%68ealth",
        f"/health#{AUTH}", "/ping", "/ready", "/live", "/status", "/version", "/metrics",
        "/favicon.ico", "/robots.txt",
    ]
    for path in paths:
        try:
            response = _request(ctx, "GET", path, [])
        except OSError as exc:
            problems.append(f"{path!r}: conexión cortada {exc!r}")
            continue
        if response.status != 401 or response.error_code != "unauthorized":
            problems.append(f"{path!r}: sin token da {response.status} {response.error_code} (esperaba 401)")
        if _leaks(ctx, response):
            problems.append(f"{path!r}: filtra token")
    for label, headers in (("X-Forwarded-Uri", ["X-Forwarded-Uri: /health"]),
                           ("X-Original-URL", ["X-Original-URL: /health"]),
                           ("X-Rewrite-URL", ["X-Rewrite-URL: /health"])):
        if _request(ctx, "GET", AUTH, headers).status == 200:
            problems.append(f"{label}: 200 sin token")
    _fail(problems, "Hay una ruta alcanzable sin token")


@attack("NET-13", "Peticiones encadenadas en una conexión: el guardia actúa por petición",
        guarantee="Cada petición se autentica; sin rutas públicas")
def pipelined_requests(ctx: Context) -> None:
    _baseline(ctx)
    host = f"Host: {ctx.host}"
    ui = f"Authorization: Bearer {ctx.token}"
    apr = f"Authorization: Bearer {ctx.approver_token}"

    def pair(first: str, second: str) -> list[int]:
        payload = (f"{first}\r\n{host}\r\nConnection: keep-alive\r\n\r\n"
                   f"{second}\r\n{host}\r\nConnection: close\r\n\r\n").encode("latin-1")
        with socket.create_connection(("127.0.0.1", ctx.port), timeout=5) as sock:
            sock.sendall(payload)
            data = b""
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    chunk = sock.recv(65536)
                except OSError:
                    break
                if not chunk:
                    break
                data += chunk
        return [int(part[:3]) for part in data.split(b"HTTP/1.1 ")[1:] if part[:3].isdigit()]

    problems: list[str] = []
    for label, first, second, expected in (
        ("ui y luego sin token", f"GET {AUTH} HTTP/1.1\r\n{ui}", f"GET {AUTH} HTTP/1.1", [200, 401]),
        ("ui y luego approver en ruta ui", f"GET {AUTH} HTTP/1.1\r\n{ui}", f"GET {AUTH} HTTP/1.1\r\n{apr}", [200, 403]),
        ("approver y luego ui en ruta ui", f"GET {AUTH} HTTP/1.1\r\n{apr}", f"GET {AUTH} HTTP/1.1\r\n{ui}", [403, 200]),
        ("ui y luego Host ajeno", f"GET {AUTH} HTTP/1.1\r\n{ui}", f"GET {AUTH} HTTP/1.1\r\n{ui}\r\nHost: evil.test", [200, 400]),
        ("ui y luego Origin", f"GET {AUTH} HTTP/1.1\r\n{ui}", f"GET {AUTH} HTTP/1.1\r\n{ui}\r\nOrigin: app://drakter", [200, 403]),
        ("sin token y luego ui", f"GET /health HTTP/1.1", f"GET /health HTTP/1.1\r\n{ui}", [401, 200]),
    ):
        statuses = pair(first, second)
        if statuses != expected:
            problems.append(f"{label}: {statuses} (esperado {expected})")
    smuggled = f"GET {AUTH} HTTP/1.1\r\nHost: {ctx.host}\r\n\r\n"
    response = ctx.raw((f"POST {AUTH} HTTP/1.1\r\n{host}\r\n{ui}\r\nContent-Length: {len(smuggled)}\r\n"
                        f"Connection: close\r\n\r\n{smuggled}").encode("latin-1"))
    if response.status == 200 and b"authenticated" in response.body:
        problems.append("POST con petición escondida en el cuerpo devolvió datos protegidos")
    cl_te = (f"POST /health HTTP/1.1\r\n{host}\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n"
             f"Connection: close\r\n\r\n0\r\n\r\nGET {AUTH} HTTP/1.1\r\n{host}\r\n\r\n").encode("latin-1")
    if b"authenticated" in ctx.raw(cl_te).body:
        problems.append("CL+TE: segunda petición sin token devolvió datos protegidos")
    _fail(problems, "El guardia no se aplica por petición")


@attack("NET-14", "Sin token no se enumera nada: toda ruta responde 401 idéntico",
        guarantee="Sin token no se ve ninguna ruta")
def no_enumeration(ctx: Context) -> None:
    _baseline(ctx)
    problems: list[str] = []
    paths = [AUTH, EVENTS, "/ws", "/health", "/docs", "/redoc", "/openapi.json",
             "/api/v1/agent/tools/call", "/api/v1/confirmations", "/api/v1/zzz-no-existe", "/",
             "/mcp", "/admin"]
    shapes = set()
    for path in paths:
        response = _request(ctx, "GET", path, [])
        shapes.add((response.status, response.error_code))
        if response.status != 401:
            problems.append(f"{path}: sin token devuelve {response.status} en vez de 401")
        if _leaks(ctx, response):
            problems.append(f"{path}: filtra token")
    if len(shapes) > 1:
        problems.append(f"respuestas distintas entre rutas sin token: {sorted(map(str, shapes))}")
    for path in ("/docs", "/redoc", "/openapi.json"):
        if _request(ctx, "GET", path, [_bearer(ctx)]).status == 200:
            problems.append(f"{path}: documentación de la API expuesta")
    _fail(problems, "Enumeración de rutas sin token")


def _descendants(root: int) -> set[int]:
    children: dict[int, list[int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            ppid = int((entry / "stat").read_text().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            continue
        children.setdefault(ppid, []).append(int(entry.name))
    found, stack = {root}, [root]
    while stack:
        for child in children.get(stack.pop(), []):
            if child not in found:
                found.add(child)
                stack.append(child)
    return found


def _local_non_loopback_addresses() -> list[str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))  # UDP: no envía nada
            address = probe.getsockname()[0]
            return [] if address.startswith("127.") else [address]
    except OSError:
        return []


@attack("NET-15", "El backend solo escucha en loopback (backend y procesos hijos)",
        guarantee="Solo loopback")
def loopback_only(ctx: Context) -> None:
    if ctx.process is None:
        raise NotApplicable("el banco no controla el proceso")
    inodes: set[str] = set()
    pids = _descendants(ctx.process.pid)
    for pid in pids:
        try:
            for fd in Path(f"/proc/{pid}/fd").iterdir():
                target = os.readlink(fd)
                if target.startswith("socket:["):
                    inodes.add(target[8:-1])
        except OSError:
            continue
    listeners: list[str] = []
    for table in ("tcp", "tcp6"):
        try:
            rows = Path(f"/proc/net/{table}").read_text().splitlines()[1:]
        except OSError:
            continue
        listeners += [f"{table} {r.split()[1]}" for r in rows if r.split()[3] == "0A" and r.split()[9] in inodes]
    expect(listeners, "no se encontró ningún socket en escucha del backend: control roto")
    bad = [item for item in listeners
           if item.split()[1].split(":")[0] not in ("0100007F", "00000000000000000000000001000000")]
    expect(not bad, f"sockets en escucha fuera de loopback (pids {sorted(pids)}): {bad}")
    expect(any(item.endswith(f":{ctx.port:04X}") for item in listeners),
           "el puerto anunciado no figura entre los sockets en escucha")
    for host in _local_non_loopback_addresses():
        try:
            with socket.create_connection((host, ctx.port), timeout=1):
                raise Breach(f"el puerto {ctx.port} acepta conexiones en {host}")
        except OSError:
            pass


# --------------------------------------------------------------- WebSocket


@attack("NET-20", "WebSocket sin token, con token malo, con subprotocolo o con rol equivocado",
        guarantee="Solo Bearer ui abre /api/v1/events")
def ws_no_token(ctx: Context) -> None:
    _ws_baseline(ctx)
    tok = ctx.token
    problems: list[str] = []
    for label, headers in (
        ("sin credenciales", []),
        ("Bearer malo", [f"Authorization: Bearer {_MARKER}"]),
        ("Bearer truncado", [f"Authorization: Bearer {tok[:-1]}"]),
        ("Bearer vacío", ["Authorization: Bearer "]),
        ("Bearer approver", [_approver(ctx)]),
        ("dos Bearer (ui, approver)", [_bearer(ctx), _approver(ctx)]),
        ("subprotocolo con token ui", [f"Sec-WebSocket-Protocol: drakter.v1, drakter.auth.{tok}"]),
        ("subprotocolo solo auth ui", [f"Sec-WebSocket-Protocol: drakter.auth.{tok}"]),
        ("subprotocolo con token approver", [f"Sec-WebSocket-Protocol: drakter.v1, drakter.auth.{ctx.approver_token}"]),
        ("subprotocolo v1 sin credencial", ["Sec-WebSocket-Protocol: drakter.v1"]),
        ("Basic", [f"Authorization: Basic {base64.b64encode(tok.encode()).decode()}"]),
    ):
        response = _ws(ctx, EVENTS, headers)
        _ws_closed(ctx, response, label, problems)
        if response.status != 403:
            problems.append(f"{label}: status={response.status} (esperaba 403 del handshake rechazado)")
    _fail(problems, "WebSocket abierto sin credencial ui válida")


@attack("NET-21", "WebSocket con token válido pero cualquier Origin o Host ajeno",
        guarantee="Una página web no puede abrir el WebSocket aunque tenga el token")
def ws_origin_host(ctx: Context) -> None:
    _ws_baseline(ctx)
    problems: list[str] = []
    for origin in (ALLOWED_ORIGIN, "http://evil.test", "null", "app://drakter.evil.test", "",
                   f"http://127.0.0.1:{ctx.port}", f"http://localhost:{ctx.port}"):
        response = _ws(ctx, EVENTS, [_bearer(ctx), f"Origin: {origin}"])
        _ws_closed(ctx, response, f"Origin {origin!r}", problems)
    _ws_closed(ctx, _ws(ctx, EVENTS, [_bearer(ctx), f"Origin: {ALLOWED_ORIGIN}", "Origin: http://evil.test"]),
               "Origin doble", problems)
    _ws_closed(ctx, _ws(ctx, EVENTS, [_bearer(ctx), "Sec-WebSocket-Origin: http://evil.test"]),
               "Sec-WebSocket-Origin (cabecera antigua) no debe cambiar nada sin Origin", [])
    for host in ("evil.test", f"evil.test:{ctx.port}", "127.0.0.1", f"127.0.0.1:{ctx.port + 1}",
                 f"[::1]:{ctx.port}", f"localhost:{ctx.port}", f"127.0.0.1:{ctx.port}.evil.test"):
        _ws_closed(ctx, _ws(ctx, EVENTS, [_bearer(ctx)], host=host), f"Host {host!r}", problems)
    _ws_closed(ctx, _ws(ctx, EVENTS, [_bearer(ctx)], host=[ctx.host, "evil.test"]), "Host doble", problems)
    _ws_closed(ctx, _ws(ctx, EVENTS, [_bearer(ctx)], host=["evil.test", ctx.host]), "Host doble inverso", problems)
    _fail(problems, "WebSocket abierto desde Origin o Host ajeno")


@attack("NET-22", "WebSocket en rutas no previstas (incluida la antigua /ws) con y sin token",
        guarantee="Solo /api/v1/events acepta WebSocket")
def ws_paths(ctx: Context) -> None:
    _ws_baseline(ctx)
    problems: list[str] = []
    reference = _ws(ctx, EVENTS, [])
    paths = [
        "/ws", "/ws/", "/ws/x", "//ws", "/WS", "/websocket", "/socket", "/events", "/api/v1/ws",
        "/api/v1/event", "/api/v1/events/", "/api/v1/events/x", "/api/v1/Events", "/API/V1/EVENTS",
        "//api/v1/events", "/api/v1/events%2f", "/api/v1/events%00", "/api/v1/events;x=1",
        "/api/v1/events/../events", "/api/v1/stream", "/api/v1/agent/ws", "/api/v1/chat/ws", AUTH,
        "/health", "/", "/mcp", "/agent", "/health/../api/v1/events", "/api/v1/%65vents/..",
    ]
    for path in paths:
        with_token = _ws(ctx, path, [_bearer(ctx)])
        no_token = _ws(ctx, path, [])
        approver = _ws(ctx, path, [_approver(ctx)])
        # Las rutas que Starlette normaliza al mismo destino no son un fallo, pero nada más abre.
        canonical = path.split("?")[0] in (EVENTS, "/api/v1/%65vents/..")
        if with_token.status == 101 and not canonical:
            problems.append(f"{path!r}: abre WebSocket con token ui")
        if no_token.status == 101:
            problems.append(f"{path!r}: abre WebSocket SIN token")
        elif no_token.status != reference.status:
            problems.append(f"{path!r}: sin token da {no_token.status}, la ruta real da {reference.status} (distinguible)")
        if approver.status == 101:
            problems.append(f"{path!r}: abre WebSocket con token approver")
        for response, label in ((with_token, "ui"), (no_token, "sin token"), (approver, "approver")):
            if _leaks(ctx, response):
                problems.append(f"{path!r} {label}: filtra token")
    _fail(problems, "WebSocket en ruta no prevista o distinguible")


@attack("NET-23", "WebSocket con token por query o cookie",
        guarantee="Solo Authorization: Bearer autentica")
def ws_query_cookie(ctx: Context) -> None:
    _ws_baseline(ctx)
    tok = ctx.token
    problems: list[str] = []
    for label, path, headers in (
        ("query token", f"{EVENTS}?token={tok}", []),
        ("query access_token", f"{EVENTS}?access_token={tok}", []),
        ("query authorization", f"{EVENTS}?authorization=Bearer%20{tok}", []),
        ("cookie token", EVENTS, [f"Cookie: token={tok}"]),
        ("cookie Authorization", EVENTS, [f"Cookie: Authorization=Bearer {tok}"]),
        ("X-Auth-Token", EVENTS, [f"X-Auth-Token: {tok}"]),
        ("query + cookie", f"{EVENTS}?token={tok}", [f"Cookie: token={tok}"]),
        ("Proxy-Authorization", EVENTS, [f"Proxy-Authorization: Bearer {tok}"]),
        ("approver por query", f"{EVENTS}?token={ctx.approver_token}", []),
    ):
        response = _ws(ctx, path, headers)
        _ws_closed(ctx, response, label, problems)
        if response.status != 403:
            problems.append(f"{label}: status={response.status} (esperaba 403)")
    _fail(problems, "WebSocket autenticado por un canal no previsto")


@attack("NET-24", "El subprotocolo nunca devuelve credenciales y no autentica",
        guarantee="El token no se devuelve ni se registra")
def ws_subprotocol_echo(ctx: Context) -> None:
    _ws_baseline(ctx)
    tok = ctx.token
    problems: list[str] = []
    for label, extra in (
        ("v1 + auth", [f"Sec-WebSocket-Protocol: drakter.v1, drakter.auth.{tok}"]),
        ("auth + v1", [f"Sec-WebSocket-Protocol: drakter.auth.{tok}, drakter.v1"]),
        ("solo auth", [f"Sec-WebSocket-Protocol: drakter.auth.{tok}"]),
        ("auth malo", [f"Sec-WebSocket-Protocol: drakter.auth.{_MARKER}"]),
        ("auth en cabeceras separadas", ["Sec-WebSocket-Protocol: drakter.v1",
                                         f"Sec-WebSocket-Protocol: drakter.auth.{tok}"]),
        ("solo v1", ["Sec-WebSocket-Protocol: drakter.v1"]),
        ("v1 y otros", ["Sec-WebSocket-Protocol: chat, drakter.v1, superchat"]),
    ):
        # Con un Bearer válido la conexión abre: lo que se comprueba es qué se devuelve.
        response = _ws(ctx, EVENTS, [_bearer(ctx), *extra])
        if response.status != 101:
            problems.append(f"{label}: el control legítimo no abrió ({response.status})")
            continue
        chosen = ",".join(response.header("sec-websocket-protocol"))
        if chosen not in ("", "drakter.v1"):
            problems.append(f"{label}: subprotocolo devuelto inesperado {chosen[:20]!r}")
        if _leaks(ctx, Response(response.status, response.headers, b"")):
            problems.append(f"{label}: una cabecera de la respuesta filtra la credencial")
    if _ws(ctx, EVENTS, [_bearer(ctx), "Sec-WebSocket-Protocol: drakter.v1"]).header("sec-websocket-protocol") != ["drakter.v1"]:
        problems.append("control: drakter.v1 ofrecido no se devuelve (cambió el contrato)")
    # Sin Bearer, el subprotocolo no autentica y el rechazo no lo repite.
    for label, extra in (
        ("solo subprotocolo con token", [f"Sec-WebSocket-Protocol: drakter.v1, drakter.auth.{tok}"]),
        ("dos credenciales", [f"Sec-WebSocket-Protocol: drakter.auth.{tok}, drakter.auth.{tok}"]),
    ):
        response = _ws(ctx, EVENTS, extra)
        _ws_closed(ctx, response, label, problems)
        if response.header("sec-websocket-protocol"):
            problems.append(f"{label}: el rechazo devuelve Sec-WebSocket-Protocol")
    _fail(problems, "El subprotocolo se refleja o autentica")


@attack("NET-25", "WebSocket: un cliente HTTP no puede forzar upgrade y la conexión no admite entrada",
        guarantee="Solo /api/v1/events abre WebSocket; el guardia se aplica también al Upgrade")
def ws_upgrade_misuse(ctx: Context) -> None:
    _ws_baseline(ctx)
    problems: list[str] = []
    upgrade = ["Upgrade: websocket", "Connection: Upgrade", "Sec-WebSocket-Version: 13",
               "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=="]
    for path in (AUTH, "/health", "/nope"):
        response = _request(ctx, "GET", path, upgrade)
        if response.status in (101, 200):
            problems.append(f"{path}: {response.status} sin token con cabeceras Upgrade")
    for path in (AUTH, "/health"):
        if _request(ctx, "GET", path, [*upgrade, _bearer(ctx)]).status == 101:
            problems.append(f"{path}: Upgrade aceptado en ruta HTTP con token")
    if _request(ctx, "POST", EVENTS, [*upgrade, _bearer(ctx)]).status == 101:
        problems.append(f"POST {EVENTS} con Upgrade: 101")
    response = _request(ctx, "GET", EVENTS, [_bearer(ctx)])
    if response.status in (101, 200):
        problems.append(f"GET {EVENTS} sin Upgrade: status={response.status}")
    lines = ["GET " + EVENTS + " HTTP/1.1", f"Host: {ctx.host}", "Upgrade: websocket",
             "Connection: Upgrade", _bearer(ctx), "Sec-WebSocket-Version: 8",
             "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=="]
    if ctx.raw(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")).status == 101:
        problems.append("WS versión 8: 101")
    # Parámetros inválidos de la ruta real no deben dar 500 ni filtrar.
    for query in ("?after_seq=-1", "?after_seq=abc", "?boot_id=not-a-uuid", f"?after_seq={'9' * 400}"):
        response = _ws(ctx, EVENTS + query, [_bearer(ctx)])
        if response.status == 101 and False:
            pass
        if response.status >= 500 or _leaks(ctx, response):
            problems.append(f"{query[:20]}: status={response.status} o filtra")
    _fail(problems, "Upgrade a WebSocket mal controlado")


# ------------------------------------------------------------ Roles (D-14)

_ID = "00000000-0000-4000-8000-000000000000"


@attack("NET-50", "Matriz de roles: approve/reject y escrituras de storage-locations/permissions son de approver",
        guarantee="Solo el rol approver aprueba y cambia permisos; el rol ui no puede")
def roles_approver_only(ctx: Context) -> None:
    _baseline(ctx)
    problems: list[str] = []
    approver_paths = [
        f"/api/v1/confirmations/{_ID}/approve", f"/api/v1/confirmations/{_ID}/reject",
        f"/api/v1/confirmations/{_ID}/approve/", f"/api/v1/confirmations/{_ID}/reject//",
        f"/api/v1/confirmations/x/approve", "/api/v1/storage-locations",
        f"/api/v1/storage-locations/{_ID}", f"/api/v1/storage-locations/{_ID}/sub/deep",
        "/api/v1/permissions", f"/api/v1/permissions/{_ID}",
    ]
    write_paths = approver_paths[5:]
    reached_any = False
    for path in approver_paths[:5]:
        for method in ("POST", "PUT", "PATCH", "DELETE", "GET"):
            ui = _request(ctx, method, path, [_bearer(ctx)])
            if ui.error_code != "permission_denied" or ui.status != 403:
                problems.append(f"ui {method} {path}: {ui.status} {ui.error_code} (esperaba 403 permission_denied)")
            apr = _request(ctx, method, path, [_approver(ctx)])
            reached_any |= _reached(apr)
            if not _reached(apr):
                problems.append(f"approver {method} {path}: el guardia lo rechaza ({apr.status} {apr.error_code})")
            if _leaks(ctx, ui):
                problems.append(f"ui {method} {path}: filtra token")
    for path in write_paths:
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "FOO", "post", "Post"):
            ui = _request(ctx, method, path, [_bearer(ctx)])
            if ui.error_code != "permission_denied" or ui.status != 403:
                problems.append(f"ui {method} {path}: {ui.status} {ui.error_code}")
            apr = _request(ctx, method, path, [_approver(ctx)])
            reached_any |= _reached(apr)
            if not _reached(apr):
                problems.append(f"approver {method} {path}: rechazado por el guardia ({apr.status} {apr.error_code})")
        # Lectura: la hace la UI, no el approver.
        for method in ("GET", "HEAD"):
            if not _reached(_request(ctx, method, path, [_bearer(ctx)])):
                problems.append(f"ui {method} {path}: la lectura se rechaza")
            apr = _request(ctx, method, path, [_approver(ctx)])
            if apr.status != 403 or apr.error_code not in ("permission_denied", None):
                problems.append(f"approver {method} {path}: {apr.status} {apr.error_code} (esperaba 403)")
    expect(reached_any, "ninguna petición del approver llegó más allá del guardia: control roto")
    # Sin token o con token malo nunca es 403 permission_denied (no distingue roles a un extraño).
    for path in approver_paths:
        for token in (None, _MARKER):
            response = _request(ctx, "POST", path, [_bearer(ctx, token)] if token else [])
            if response.status != 401:
                problems.append(f"{'token malo' if token else 'sin token'} POST {path}: {response.status}")
    # La ruta con el verbo que NO exige approver y mismo prefijo no se confunde.
    for path in ("/api/v1/storage-locationsX", "/api/v1/permissionsX", "/api/v1/storage-location",
                 "/api/v1/confirmations", f"/api/v1/confirmations/{_ID}", f"/api/v1/confirmations/{_ID}/approved"):
        ui = _request(ctx, "POST", path, [_bearer(ctx)])
        if ui.error_code == "permission_denied":
            problems.append(f"POST {path}: ruta fuera de la matriz tratada como de approver")
    _fail(problems, "Matriz de roles rota")


@attack("NET-51", "Matriz de roles: el approver no entra en nada más (HTTP, /health, WebSocket)",
        guarantee="El approver solo aprueba; no lee ni escribe el resto de la API")
def roles_approver_nothing_else(ctx: Context) -> None:
    _baseline(ctx)
    problems: list[str] = []
    for method, path in (
        ("GET", AUTH), ("GET", "/health"), ("GET", "/api/v1/tasks"), ("POST", "/api/v1/tasks"),
        ("GET", "/api/v1/confirmations"), ("GET", f"/api/v1/confirmations/{_ID}"),
        ("POST", "/api/v1/confirmations"), ("GET", f"/api/v1/confirmations/{_ID}/approve/x"),
        ("POST", f"/api/v1/confirmations/{_ID}/approved"), ("POST", f"/api/v1/confirmations/{_ID}/approve/x"),
        ("DELETE", "/api/v1/projects/x"), ("GET", "/api/v1/vault/files"), ("POST", "/api/v1/memory/search"),
        ("GET", "/api/v1/nonexistent"), ("GET", "/api/v1/storage-locationsX"), ("POST", "/nope"),
        ("GET", "/docs"), ("OPTIONS", AUTH),
    ):
        response = _request(ctx, method, path, [_approver(ctx)])
        if response.status != 403 or response.error_code != "permission_denied":
            problems.append(f"approver {method} {path}: {response.status} {response.error_code}")
        if _leaks(ctx, response):
            problems.append(f"approver {method} {path}: filtra token")
    ws = _ws(ctx, EVENTS, [_approver(ctx)])
    _ws_closed(ctx, ws, "approver en WS", problems)
    if ws.status != 403:
        problems.append(f"approver en WS: status={ws.status} (esperaba 403)")
    # Lo mismo con cuerpo grande: el rol se evalúa antes que el límite.
    response = _request(ctx, "GET", AUTH, [_approver(ctx), f"Content-Length: {MAX_BODY * 2}"])
    if response.error_code != "permission_denied":
        problems.append(f"approver + Content-Length enorme: {response.status} {response.error_code}")
    _fail(problems, "El approver alcanza rutas que no son suyas")


# --------------------------------------------------- Límite de cuerpo (D-14)


def _post_chunked(ctx: Context, path: str, headers: list[str], total: int, chunk_size: int = 65536) -> Response:
    """Cuerpo en streaming (Transfer-Encoding: chunked) de `total` bytes; lee la respuesta aunque
    el servidor corte la subida."""
    head = "\r\n".join([f"POST {path} HTTP/1.1", f"Host: {ctx.host}", *headers,
                        "Transfer-Encoding: chunked", "Connection: close"]) + "\r\n\r\n"
    data = b""
    with socket.create_connection(("127.0.0.1", ctx.port), timeout=10) as sock:
        try:
            sock.sendall(head.encode("latin-1"))
            sent = 0
            block = b"A" * chunk_size
            while sent < total:
                size = min(chunk_size, total - sent)
                sock.sendall(f"{size:x}\r\n".encode() + block[:size] + b"\r\n")
                sent += size
            sock.sendall(b"0\r\n\r\n")
        except OSError:
            pass  # el servidor cortó la subida: lo que importa es su respuesta
        sock.settimeout(5)
        try:
            while chunk := sock.recv(65536):
                data += chunk
        except OSError:
            pass
    head_raw, _, body = data.partition(b"\r\n\r\n")
    parts = head_raw.decode("latin-1").split("\r\n")
    status_line = parts[0].split(" ")
    status = int(status_line[1]) if len(status_line) >= 2 and status_line[1].isdigit() else 0
    found = [(n.strip(), v.strip()) for n, _, v in (line.partition(":") for line in parts[1:])]
    return Response(status, found, body)


@attack("NET-52", "Límite de cuerpo con Content-Length: 413 file_too_large antes de leer",
        guarantee="Un cuerpo mayor de 1 MiB no se procesa")
def body_limit_content_length(ctx: Context) -> None:
    _baseline(ctx)
    problems: list[str] = []
    ui = _bearer(ctx)
    # Control positivo: justo en el límite pasa el guardia.
    at_limit = _request(ctx, "POST", AUTH, [ui], body=b"A" * MAX_BODY, timeout=15)
    if not _reached(at_limit) or at_limit.status == 413:
        raise RuntimeError(f"control roto: cuerpo de exactamente {MAX_BODY} bytes da {at_limit.status} {at_limit.error_code}")
    # Declarado por encima del límite, sin enviar el cuerpo: el rechazo no espera los bytes.
    for declared in (MAX_BODY + 1, MAX_BODY * 2, 10**9, 10**15, 2**63, 2**64 + 1, "0001048577"):
        started = time.monotonic()
        response = _request(ctx, "POST", AUTH, [ui, f"Content-Length: {declared}"], timeout=5)
        if response.status != 413 or response.error_code != "file_too_large":
            problems.append(f"CL {declared} sin enviar cuerpo: {response.status} {response.error_code}")
        elif time.monotonic() - started > 3:
            problems.append(f"CL {declared}: el rechazo tardó {time.monotonic() - started:.1f}s (leyó el cuerpo)")
        if _leaks(ctx, response):
            problems.append(f"CL {declared}: filtra token")
    # Cuerpo real por encima del límite.
    response = _request(ctx, "POST", AUTH, [ui], body=b"A" * (MAX_BODY + 1), timeout=15)
    if response.status != 413 or response.error_code != "file_too_large":
        problems.append(f"cuerpo real de {MAX_BODY + 1} bytes: {response.status} {response.error_code}")
    # Métodos distintos de POST y rutas distintas: el límite es de toda la API.
    for method in ("PUT", "PATCH", "DELETE", "GET"):
        response = _request(ctx, method, "/api/v1/anything", [ui, f"Content-Length: {MAX_BODY + 1}"])
        if response.status != 413:
            problems.append(f"{method} con CL grande: {response.status} {response.error_code}")
    response = _request(ctx, "POST", "/api/v1/permissions", [_approver(ctx), f"Content-Length: {MAX_BODY + 1}"])
    if response.status != 413:
        problems.append(f"approver POST /api/v1/permissions con CL grande: {response.status} {response.error_code}")
    # Orden de comprobaciones: sin token es 401; rol equivocado, 403; Host/Origin antes que el límite.
    for label, response, code in (
        ("sin token", _request(ctx, "POST", AUTH, [f"Content-Length: {MAX_BODY + 1}"]), "unauthorized"),
        ("token malo", _request(ctx, "POST", AUTH, [_bearer(ctx, _MARKER), f"Content-Length: {MAX_BODY + 1}"]), "unauthorized"),
        ("rol equivocado", _request(ctx, "POST", AUTH, [_approver(ctx), f"Content-Length: {MAX_BODY + 1}"]), "permission_denied"),
        ("Host ajeno", _request(ctx, "POST", AUTH, [ui, f"Content-Length: {MAX_BODY + 1}"], host="evil.test"), "forbidden_host"),
        ("Origin", _request(ctx, "POST", AUTH, [ui, "Origin: app://drakter", f"Content-Length: {MAX_BODY + 1}"]), "forbidden_origin"),
    ):
        if response.error_code != code:
            problems.append(f"CL grande {label}: {response.status} {response.error_code} (esperaba {code})")
    # Content-Length repetido o contradictorio: nunca acaba procesándose un cuerpo grande como pequeño.
    for label, lines in (
        ("dos CL distintos", [f"Content-Length: 5", f"Content-Length: {MAX_BODY + 1}"]),
        ("CL con signo", [f"Content-Length: +{MAX_BODY + 1}"]),
        ("CL hexadecimal", ["Content-Length: 0x100001"]),
        ("CL negativo", ["Content-Length: -1"]),
    ):
        response = _request(ctx, "POST", AUTH, [ui, *lines], timeout=5)
        if response.status == 200:
            problems.append(f"{label}: 200")
    if _request(ctx, "GET", AUTH, [ui]).status != 200:
        problems.append("tras los rechazos 413 el servidor ya no atiende")
    _fail(problems, "Límite de cuerpo por Content-Length roto")


def _body_consumer(ctx: Context) -> tuple[str, str]:
    """Ruta POST que lee su cuerpo: sin ella el guardia no tiene cuerpo que limitar.

    Starlette responde 404/405 sin leer el cuerpo, así que esas rutas no sirven."""
    candidates = list(ctx.contract.get("body_routes", []))
    for name, path in ctx.contract["routes"].items():
        if name not in ("auth_check", "confirmation_approve", "confirmation_detail"):
            candidates.append(path)
    for path in candidates:
        path = path.format(id=_ID)
        probe = _request(ctx, "POST", path, [_bearer(ctx), "Content-Type: application/json"], body=b"{}")
        if probe.status not in (404, 405) and _reached(probe):
            return path, _bearer(ctx)
        probe = _request(ctx, "POST", path, [_approver(ctx), "Content-Type: application/json"], body=b"{}")
        if probe.status not in (404, 405) and _reached(probe):
            return path, _approver(ctx)
    raise NotApplicable(
        "ninguna ruta POST del objetivo lee su cuerpo (404/405 sin leerlo): el límite en streaming "
        "no es alcanzable; declara rutas con la clave `body_routes` del contrato"
    )


@attack("NET-53", "Límite de cuerpo en streaming (chunked, sin Content-Length) sobre una ruta que lo lee",
        guarantee="Un cuerpo mayor de 1 MiB no se procesa aunque no declare tamaño")
def body_limit_streaming(ctx: Context) -> None:
    _baseline(ctx)
    path, auth = _body_consumer(ctx)
    problems: list[str] = []
    ok = _post_chunked(ctx, path, [auth, "Content-Type: application/json"], 1024)
    if ok.status == 413 or not _reached(ok):
        raise RuntimeError(f"control roto: chunked pequeño en {path} da {ok.status} {ok.error_code}")
    for label, total in (("+1 byte", MAX_BODY + 1), ("1,5 MiB", MAX_BODY * 3 // 2)):
        response = _post_chunked(ctx, path, [auth, "Content-Type: application/json"], total)
        if response.status != 413 or response.error_code != "file_too_large":
            problems.append(f"{label}: {response.status} {response.error_code}")
        if _leaks(ctx, response):
            problems.append(f"{label}: filtra token")
    response = _post_chunked(ctx, path, [auth, "Content-Length: 5"], MAX_BODY + 1)
    if response.status == 200:
        problems.append("CL pequeño + chunked grande: 200")
    for label, headers, code in (("sin token", [], "unauthorized"),
                                 ("rol equivocado", [_approver(ctx) if auth == _bearer(ctx) else _bearer(ctx)],
                                  "permission_denied")):
        response = _post_chunked(ctx, path, headers, MAX_BODY + 1)
        if response.error_code != code:
            problems.append(f"chunked grande {label}: {response.status} {response.error_code} (esperaba {code})")
    if _request(ctx, "GET", AUTH, [_bearer(ctx)]).status != 200:
        problems.append("tras los rechazos 413 el servidor ya no atiende")
    _fail(problems, "Límite de cuerpo en streaming roto")


# ---------------------------------------------- Fugas y registros


@attack("NET-30", "Un rechazo no filtra el token ni el valor enviado, y los logs lo ocultan",
        guarantee="Secretos fuera de respuestas y registros")
def rejection_no_leak(ctx: Context) -> None:
    _baseline(ctx)
    problems: list[str] = []
    probes = (
        ("Host ajeno", _request(ctx, "GET", f"{AUTH}?token={_MARKER}", [_bearer(ctx)], host="evil.test")),
        ("Origin", _request(ctx, "GET", AUTH, [_bearer(ctx), f"Origin: http://{_MARKER}.test"])),
        ("sin token", _request(ctx, "GET", AUTH, [f"Cookie: token={_MARKER}"])),
        ("token malo", _request(ctx, "GET", AUTH, [f"Authorization: Bearer {_MARKER}"])),
        ("rol equivocado", _request(ctx, "GET", AUTH, [_approver(ctx)])),
        ("413", _request(ctx, "POST", AUTH, [_bearer(ctx), f"Content-Length: {MAX_BODY + 1}"])),
        ("404 con token", _request(ctx, "GET", f"/api/v1/path-{_MARKER}", [_bearer(ctx)])),
        ("405 con token", _request(ctx, "DELETE", AUTH, [_bearer(ctx)])),
        ("JSON roto con token", _request(ctx, "POST", AUTH, [_bearer(ctx), "Content-Type: application/json"],
                                         body=b'{"x":' + _MARKER.encode())),
    )
    for label, response in probes:
        blob = _blob(response)
        if ctx.token.encode() in blob or ctx.approver_token.encode() in blob:
            problems.append(f"{label}: la respuesta contiene un token de sesión")
        if label in ("Host ajeno", "Origin", "sin token", "token malo") and _MARKER.encode() in blob:
            problems.append(f"{label}: la respuesta refleja un valor del cliente")
    for label, headers in (
        ("WS Bearer malo", [f"Authorization: Bearer {_MARKER}"]),
        ("WS subprotocolo malo", [f"Sec-WebSocket-Protocol: drakter.auth.{_MARKER}"]),
        ("WS Origin + token real", [f"Origin: http://{_MARKER}.test", _bearer(ctx)]),
        ("WS approver", [_approver(ctx)]),
    ):
        response = _ws(ctx, EVENTS, headers)
        if _leaks(ctx, response) and label != "WS Origin + token real":
            problems.append(f"{label}: la respuesta del handshake filtra un valor")
        elif label == "WS Origin + token real" and (ctx.token.encode() in _blob(response)):
            problems.append(f"{label}: la respuesta del handshake filtra el token")
    # Los dos tokens reales en lugares donde no deben estar: el registro (DEBUG incluido) los enmascara.
    for tok in (ctx.token, ctx.approver_token):
        _request(ctx, "GET", f"/x/{tok}?a={tok}", [f"X-Foo: {tok}", f"Cookie: session={tok}"])
        _request(ctx, "GET", AUTH, [f"X-Anything: {tok}"], host=f"{tok}.evil.test")
        _ws(ctx, EVENTS, ["Origin: http://evil.test", f"X-Foo: {tok}",
                          f"Sec-WebSocket-Protocol: drakter.auth.{tok}"])
    _request(ctx, "GET", AUTH, [f"Authorization: Bearer {_MARKER}", f"Cookie: token={_MARKER}2",
                                f"X-Session-Token: {_MARKER}3"])
    _ws(ctx, EVENTS, [f"Sec-WebSocket-Protocol: drakter.auth.{_MARKER}4"])
    time.sleep(0.3)
    logs = ctx.logs_text()
    expect("Request rejected" in logs or "forbidden" in logs, "control roto: los rechazos no se registran")
    for label, tok in (("ui", ctx.token), ("approver", ctx.approver_token)):
        if tok in logs:
            problems.append(f"el token {label} aparece en claro en los registros")
    residue = logs.replace(f"path-{_MARKER}", "").replace(f"http://{_MARKER}.test", "")
    for variant in ("", "2", "3", "4"):
        if f"{_MARKER}{variant}" in residue:
            problems.append(f"una credencial rechazada ({_MARKER}{variant}) aparece en los registros")
    _fail(problems, "Fuga de token o de valores del cliente")


@attack("NET-31", "Inyección de líneas en los registros desde la ruta o el Host de un rechazo",
        guarantee="Los registros no pueden falsificarse desde la red")
def log_injection(ctx: Context) -> None:
    _baseline(ctx)
    fake = "FAKE-LOG-ENTRY-NET31"
    _request(ctx, "GET", f"/x%0d%0a{fake}%0a%7b%22event%22:%22session_started%22%7d", [])
    _request(ctx, "GET", AUTH, [_bearer(ctx)], host=f"evil.test\x1b[31m{fake}")
    _request(ctx, "GET", f"/x%1b%5b2J{fake}", [])
    _request(ctx, "GET", "/y" + "A" * 3000 + fake, [])
    time.sleep(0.3)
    logs = ctx.logs_text()
    expect(fake in logs, "control roto: la petición rechazada no aparece en los registros")
    for line in logs.splitlines():
        if fake in line and (line.lstrip().startswith(fake) or "\x1b" in line):
            raise Breach(f"línea de registro controlada por el cliente: {line[:120]!r}")
    # D-14: el guardia trunca la ruta registrada a 256 caracteres.
    long_lines = [line for line in logs.splitlines() if "Request rejected" in line and "/yAAAA" in line]
    for line in long_lines:
        try:
            path = json.loads(line).get("path", "")
        except ValueError:
            continue
        if len(path) > 256:
            raise Breach(f"el guardia registra una ruta de {len(path)} caracteres (límite 256)")


# ------------------------------------- Arranque: handshake por stdin (D-14)


def _spawn_with_stdin(ctx: Context, payload: bytes) -> tuple[int | None, bytes, bytes]:
    """Lanza un backend aparte, le envía `payload` por stdin y devuelve (código, stdout, stderr)."""
    root = _isolated_root()
    try:
        (root / "home").mkdir(mode=0o700)
        environment = {
            "PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "HOME": str(root / "home"),
            "XDG_CONFIG_HOME": str(root / "config"), "XDG_DATA_HOME": str(root / "xdg-data"),
            "XDG_RUNTIME_DIR": str(root / "xdg-runtime"), "TMPDIR": str(root),
            "DRAKTER_DATA_DIR": str(root / "data"), "DRAKTER_RUNTIME_DIR": str(root / "runtime"),
            "DRAKTER_LOG_LEVEL": "DEBUG", **ctx.contract.get("env", {}),
        }
        python = ctx.contract.get("python") or _python_of(ctx)
        process = subprocess.Popen(
            [python, "-m", "app"], cwd=ctx.backend_dir, env=environment, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        )
        try:
            assert process.stdin is not None
            try:
                process.stdin.write(payload)
                process.stdin.flush()
            except OSError:
                pass
            if payload.endswith(b"\n") is False or True:
                # Sin cerrar: si el backend aceptara una línea inválida se quedaría vivo.
                pass
            try:
                out, err = process.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                out, err = process.communicate()
                return None, out, err
            return process.returncode, out, err
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    finally:
        import shutil  # noqa: PLC0415

        shutil.rmtree(root, ignore_errors=True)


def _python_of(ctx: Context) -> str:
    assert ctx.process is not None
    # El intérprete del venv, tal como se lanzó (el enlace de /proc/<pid>/exe lo resuelve y pierde el venv).
    return Path(f"/proc/{ctx.process.pid}/cmdline").read_bytes().split(b"\0")[0].decode()


@attack("NET-54", "Handshake inválido por stdin: código 2, mensaje genérico, sin eco ni arranque",
        guarantee="Los tokens solo entran por un handshake válido y nunca se repiten")
def stdin_handshake_invalid(ctx: Context) -> None:
    if ctx.process is None:
        raise NotApplicable("el banco no controla el proceso")
    _baseline(ctx)  # control: el handshake válido del banco ya arrancó el objetivo
    good_a = base64.urlsafe_b64encode(bytes(range(32))).rstrip(b"=").decode()
    good_b = base64.urlsafe_b64encode(bytes(range(32, 64))).rstrip(b"=").decode()
    secret = "SECRETECHO" + "x" * 33  # 43 caracteres de aspecto válido, pero no base64 de 32 bytes
    tail43 = "ZZZZ" * 10 + "ZZZ"
    cases: list[tuple[str, bytes, str]] = [
        ("EOF sin datos", b"", ""),
        ("línea vacía", b"\n", ""),
        ("no JSON con secreto", f"{secret} not json\n".encode(), "SECRETECHO"),
        ("JSON no objeto", b'["SECRETECHO"]\n', "SECRETECHO"),
        ("sin terminador y cierre", json.dumps({"v": 1, "ui": good_a, "approver": good_b}).encode(), ""),
        ("v distinta", json.dumps({"v": 2, "ui": good_a, "approver": good_b}).encode() + b"\n", ""),
        ("v booleana", json.dumps({"v": True, "ui": good_a, "approver": good_b}).encode() + b"\n", ""),
        ("campo extra", json.dumps({"v": 1, "ui": good_a, "approver": good_b, "extra": "SECRETECHO"}).encode() + b"\n", "SECRETECHO"),
        ("falta approver", json.dumps({"v": 1, "ui": good_a}).encode() + b"\n", ""),
        ("falta ui", json.dumps({"v": 1, "approver": good_a}).encode() + b"\n", ""),
        ("tokens iguales", json.dumps({"v": 1, "ui": good_a, "approver": good_a}).encode() + b"\n", good_a),
        ("token corto", json.dumps({"v": 1, "ui": good_a[:-1], "approver": good_b}).encode() + b"\n", good_a[:-1]),
        ("token largo", json.dumps({"v": 1, "ui": good_a + "A", "approver": good_b}).encode() + b"\n", good_a + "A"),
        ("token con relleno =", json.dumps({"v": 1, "ui": good_a[:-1] + "=", "approver": good_b}).encode() + b"\n", ""),
        ("token no base64url", json.dumps({"v": 1, "ui": "+" * 43, "approver": good_b}).encode() + b"\n", "+" * 43),
        ("token que no es canónico", json.dumps({"v": 1, "ui": tail43, "approver": good_b}).encode() + b"\n", tail43),
        ("tokens numéricos", json.dumps({"v": 1, "ui": 1, "approver": 2}).encode() + b"\n", ""),
        ("token nulo", json.dumps({"v": 1, "ui": None, "approver": good_b}).encode() + b"\n", ""),
        ("dos líneas", (json.dumps({"v": 1, "ui": good_a, "approver": good_b}) + "\nSECRETECHO\n").encode(), "SECRETECHO"),
        ("línea de más de 4 KiB", b'{"v":1,"ui":"SECRETECHO' + b"A" * 6000 + b'"}\n', "SECRETECHO"),
        ("4 KiB sin salto de línea", b"SECRETECHO" + b"B" * 5000, "SECRETECHO"),
        ("bytes no UTF-8", b'{"v":1,"ui":"\xff\xfe\xfdSECRETECHO","approver":"x"}\n', "SECRETECHO"),
    ]
    problems: list[str] = []
    for label, payload, secret_text in cases:
        code, out, err = _spawn_with_stdin(ctx, payload)
        if code is None:
            problems.append(f"{label}: el backend sigue vivo tras un handshake inválido")
            continue
        if code != 2:
            problems.append(f"{label}: código {code} (esperaba 2) stderr={err[:80]!r}")
        if b'"port"' in out:
            problems.append(f"{label}: anunció puerto tras un handshake inválido")
        everything = out + err
        for needle in {secret_text, "SECRETECHO", good_a, good_b} - {""}:
            if needle.encode() in everything and needle != good_b + "x":
                # good_a/good_b solo cuentan si estaban en la entrada de este caso
                if needle.encode() in payload:
                    problems.append(f"{label}: eco de la entrada ({needle[:12]!r}...) en la salida")
                    break
        if len(err) > 400:
            problems.append(f"{label}: el mensaje de error no es genérico ({len(err)} bytes)")
    _fail(problems, "Handshake por stdin defectuoso")


@attack("NET-55", "Sin session.json ni tokens en disco; stdin/stdout del canal no los heredan hijos ni otros",
        guarantee="Secretos fuera de disco y del alcance de otros procesos")
def tokens_not_on_disk(ctx: Context) -> None:
    if ctx.process is None:
        raise NotApplicable("el banco no controla el proceso")
    _baseline(ctx)
    problems: list[str] = []
    for candidate in (ctx.runtime_dir / "session.json", ctx.data_dir / "session.json",
                      ctx.root / "session.json"):
        if candidate.exists():
            problems.append(f"existe {candidate.relative_to(ctx.root)}")
    needles = (ctx.token.encode(), ctx.approver_token.encode())
    for path in ctx.root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        for label, needle in zip(("ui", "approver"), needles, strict=True):
            if needle in data:
                problems.append(f"el token {label} está en disco: {path.relative_to(ctx.root)}")
    # fd 0 en /dev/null; fd 1 no es la tubería del canal (apunta a stderr).
    pid = ctx.process.pid
    try:
        fd0, fd1, fd2 = (os.readlink(f"/proc/{pid}/fd/{n}") for n in (0, 1, 2))
        if fd0 != "/dev/null":
            problems.append(f"fd 0 del backend apunta a {fd0!r}, no a /dev/null")
        if fd1 != fd2:
            problems.append(f"fd 1 del backend ({fd1!r}) no apunta a stderr ({fd2!r})")
    except OSError as exc:
        raise NotApplicable(f"no se pudo leer /proc/{pid}/fd: {exc}") from exc
    # Las tuberías del canal no están abiertas en ningún proceso hijo.
    pipes = set()
    for fd in Path(f"/proc/{pid}/fd").iterdir():
        try:
            target = os.readlink(fd)
        except OSError:
            continue
        if target.startswith("pipe:["):
            pipes.add(target)
    for child in _descendants(pid) - {pid}:
        try:
            for fd in Path(f"/proc/{child}/fd").iterdir():
                target = os.readlink(fd)
                if target in pipes:
                    problems.append(f"el hijo {child} hereda una tubería del backend ({target})")
        except OSError:
            continue
    # El token no está en el entorno ni en la línea de órdenes del proceso.
    for name in ("environ", "cmdline"):
        try:
            blob = Path(f"/proc/{pid}/{name}").read_bytes()
        except OSError:
            continue
        if any(needle in blob for needle in needles):
            problems.append(f"un token aparece en /proc/{pid}/{name}")
    _fail(problems, "Secretos expuestos fuera del canal de arranque")


# -------------------------------------- Servidor de herramientas del agente


def _agent_tools_target(ctx: Context) -> tuple[int, str, str]:
    port = (
        ctx.contract.get("agent_tools_port")
        or ctx.session.get("agent_tools_port")
        or ctx.contract.get("env", {}).get("DRAKTER_AGENT_TOOLS_PORT")
    )
    if not port:
        raise NotApplicable("el objetivo no publica un puerto del servidor de herramientas del agente")
    port = int(port)
    try:
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
    except OSError:
        raise NotApplicable(f"nada escucha en 127.0.0.1:{port} (servidor de herramientas no arrancado)")
    key = ctx.contract.get("principals", {}).get("agent", "agent_token")
    agent_token = ctx.session.get(ctx.contract.get("agent_tools_token_key", key))
    if not agent_token:
        raise NotApplicable(f"session.json no contiene el token del agente ({key})")
    return port, ctx.contract.get("agent_tools_path", "/mcp"), agent_token


def _agent_request(
    port: int, method: str, path: str, headers: list[str], *, host: str | None = None, body: bytes = b""
) -> Response:
    lines = [f"{method} {path} HTTP/1.1", f"Host: {host or f'127.0.0.1:{port}'}", "Connection: close", *headers]
    if body:
        lines.append(f"Content-Length: {len(body)}")
    payload = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8") + body
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.sendall(payload)
        from redlib import _read_response  # noqa: PLC0415 - utilidad del núcleo

        return _read_response(sock)


_MCP_INIT = (
    b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18",'
    b'"capabilities":{},"clientInfo":{"name":"red","version":"0"}}}'
)
_MCP_HEADERS = ["Content-Type: application/json", "Accept: application/json, text/event-stream"]


def _agent_control(ctx: Context) -> tuple[int, str, str]:
    port, path, agent_token = _agent_tools_target(ctx)
    ok = _agent_request(port, "POST", path, [*_MCP_HEADERS, f"Authorization: Bearer {agent_token}"],
                        body=_MCP_INIT)
    if ok.status in (401, 403, 404, 0):
        raise NotApplicable(
            f"el control positivo no alcanza el servidor MCP en {path} (status {ok.status}); "
            "ajusta `agent_tools_path` en el contrato"
        )
    return port, path, agent_token


@attack("NET-40", "Servidor de herramientas del agente: sin token, token de la GUI y Host ajeno",
        guarantee="Hermes solo alcanza sus herramientas, con su propio token, solo en loopback")
def agent_tools_auth(ctx: Context) -> None:
    port, path, agent_token = _agent_control(ctx)
    problems: list[str] = []
    cases: list[tuple[str, list[str], str | None]] = [
        ("sin token", [], None),
        ("token de la GUI", [f"Authorization: Bearer {ctx.token}"], None),
        ("token de aprobación", [f"Authorization: Bearer {ctx.approver_token}"], None),
        ("token malo", [f"Authorization: Bearer {_MARKER}"], None),
        ("token del agente por query", [], None),
        ("token del agente por cookie", [f"Cookie: token={agent_token}"], None),
        ("Host ajeno con token válido", [f"Authorization: Bearer {agent_token}"], "evil.test"),
        ("Host ajeno con puerto", [f"Authorization: Bearer {agent_token}"], f"evil.test:{port}"),
        ("Host sin puerto", [f"Authorization: Bearer {agent_token}"], "127.0.0.1"),
    ]
    for label, headers, host in cases:
        target = f"{path}?token={agent_token}" if label.endswith("query") else path
        response = _agent_request(port, "POST", target, [*_MCP_HEADERS, *headers], host=host, body=_MCP_INIT)
        if response.status < 400:
            problems.append(f"{label}: status={response.status}")
        if agent_token.encode() in response.body or ctx.token.encode() in response.body:
            problems.append(f"{label}: el rechazo filtra un token")
    # El token del agente no sirve en la API de la GUI ni en su WebSocket.
    for label, response in (
        ("token del agente en la API de la GUI", _request(ctx, "GET", AUTH, [f"Authorization: Bearer {agent_token}"])),
        ("token del agente en /health", _request(ctx, "GET", "/health", [f"Authorization: Bearer {agent_token}"])),
    ):
        if response.status == 200:
            problems.append(f"{label}: 200")
    ws = _ws(ctx, EVENTS, [f"Authorization: Bearer {agent_token}"])
    if ws.status == 101:
        problems.append("token del agente abre el WebSocket de la GUI")
    # Y la API de la GUI no está servida en el puerto del agente.
    for gui_path in (AUTH, EVENTS, "/api/v1/confirmations", "/health"):
        response = _agent_request(port, "GET", gui_path, [f"Authorization: Bearer {agent_token}"])
        if response.status == 200 and b"authenticated" in response.body:
            problems.append(f"{gui_path}: la API de la GUI responde en el puerto del agente")
    _fail(problems, "Frontera del servidor de herramientas del agente")


@attack("NET-41", "Servidor de herramientas del agente: Origin de navegador y rutas alternativas",
        guarantee="Hermes solo alcanza sus herramientas; una web ajena no llega al puerto del agente")
def agent_tools_origin(ctx: Context) -> None:
    port, path, agent_token = _agent_control(ctx)
    problems: list[str] = []
    headers = [*_MCP_HEADERS, f"Authorization: Bearer {agent_token}"]
    for origin in ("http://evil.test", "null", ALLOWED_ORIGIN):
        response = _agent_request(port, "POST", path, [*headers, f"Origin: {origin}"], body=_MCP_INIT)
        # Un navegador no tiene motivo para hablar con este puerto: se espera rechazo.
        if response.status < 400:
            problems.append(f"Origin {origin!r} con token del agente: status={response.status}")
    for alt in (path + "/", path.upper(), "//" + path.lstrip("/"), path + "/../" + path.lstrip("/"),
                "/health", "/", "/sse"):
        response = _agent_request(port, "POST", alt, headers, body=_MCP_INIT)
        no_token = _agent_request(port, "POST", alt, _MCP_HEADERS, body=_MCP_INIT)
        if no_token.status < 400 and alt not in ("/health",):
            problems.append(f"{alt!r}: responde {no_token.status} sin token")
        del response
    preflight = _agent_request(port, "OPTIONS", path, [
        "Origin: http://evil.test", "Access-Control-Request-Method: POST"])
    if preflight.header("access-control-allow-origin"):
        problems.append(f"preflight de Origin ajeno concede ACAO={preflight.header('access-control-allow-origin')}")
    _fail(problems, "Servidor de herramientas alcanzable desde la web o sin token")
