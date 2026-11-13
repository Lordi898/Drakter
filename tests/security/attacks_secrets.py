"""Fuga de secretos a logs, errores, auditoría y procesos (prefijo LEAK).

Todos los secretos son inventados y se generan en cada ejecución. Los ataques de
formateador corren en un subproceso con el intérprete del objetivo
(`ctx.process.args[0]`, cwd `ctx.backend_dir`) para ejercitar el código real de
`app.core.logging`. Los de backend usan el proceso en marcha.

Criterio: BREACH solo para lo que el contrato (backend/CONTRACT.md, sección
logging) promete. Los LEAK-4x son inventarios INFORMATIVOS de límites que ningún
redactor por patrones puede cubrir; salen como NOT_APPLICABLE con el detalle.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import stat
import subprocess
import time
from pathlib import Path

from redlib import Breach, Context, NotApplicable, attack, expect

CHILD_TIMEOUT = 90.0

# --------------------------------------------------------------------------- #
# Subproceso: ejercita el formateador real. Lee {"group","S",...} por stdin.
# Devuelve {caso: [línea, [agujas]]}. Nada de red ni de estado real.
# --------------------------------------------------------------------------- #
CHILD = r'''
import json, logging, os, sys, time
sys.path.insert(0, os.getcwd())
from app.core import logging as L

req = json.loads(sys.stdin.read())
S, group = req["S"], req["group"]
F = L.JsonFormatter()
out = {}


def rec(msg, args=(), extra=None, exc=None):
    r = logging.LogRecord("t", logging.INFO, "x.py", 1, msg, args, exc)
    for k, v in (extra or {}).items():
        r.__dict__[k] = v
    return r


def put(name, line, needles=None):
    out[name] = [line, needles or [S]]


def fmt(name, msg="m", args=(), extra=None, exc=None, needles=None):
    try:
        put(name, F.format(rec(msg, args, extra, exc)), needles)
    except BaseException as e:  # noqa: BLE001
        put(name, "<FORMAT-RAISED %s>" % type(e).__name__, [])
        out[name].append("raised")


def exc_of(factory):
    try:
        raise factory()
    except BaseException:
        return sys.exc_info()


class Obj:
    def __init__(self, v): self.v = v
    def __repr__(self): return "Req(token=%r)" % (self.v,)


if group == "keys":
    names = ["Authorization", "AUTHORIZATION", "x-api-key", "X-API-KEY", "api-key", "api_key",
             "apikey", "apiKey", "Cookie", "Set-Cookie", "Proxy-Authorization", "x-auth-token",
             "client_secret", "db_password", "access_token", "refresh_token", "credentials",
             "Credential"]
    for n in names:
        fmt("extra:" + n, extra={n: S})
        fmt("nested:" + n, extra={"headers": {"req": {n: S}}})
        fmt("listdict:" + n, extra={"items": [{n: S}]})

elif group == "structures":
    fmt("pairs-tuples-str", extra={"headers": [("authorization", S), ("accept", "a")]})
    fmt("pairs-tuples-bytes", extra={"headers": [(b"authorization", S.encode())]})
    fmt("pairs-tuples-apikey", extra={"headers": [("api-key", S)]})
    fmt("pairs-lists-str", extra={"headers": [["Authorization", "Basic " + S]]})
    fmt("pairs-asgi-bytes", extra={"headers": [(b"authorization", b"Basic " + S.encode())]})
    fmt("pairs-cookie-bytes", extra={"headers": [(b"cookie", b"sid=" + S.encode())]})
    fmt("pairs-token-tuple", extra={"headers": [("token", S)]})
    fmt("set-of-pairs", extra={"headers": {("authorization", S)}})
    fmt("dict-nonstr-key", extra={"h": {b"authorization": S}})
    fmt("dict-tuple-key", extra={"h": {("authorization",): S}})
    fmt("obj-repr-extra", extra={"req": Obj(S)})
    fmt("obj-mapping-proxy", extra={"h": __import__("types").MappingProxyType({"token": S})})
    fmt("obj-ordereddict", extra={"h": __import__("collections").OrderedDict(token=S)})
    fmt("obj-defaultdict", extra={"h": __import__("collections").defaultdict(str, token=S)})
    fmt("obj-dataclass", extra={"h": __import__("dataclasses").make_dataclass("D", ["token"])(S)})
    fmt("obj-repr-arg", "got %s", (Obj(S),))
    fmt("obj-repr-msg", Obj(S))
    fmt("bytes-extra", extra={"raw": b"token=" + S.encode()})
    fmt("bytes-repr-extra", extra={"raw": repr({"token": S.encode()})})
    fmt("bytes-arg", "got %s", (b"Authorization: Bearer " + S.encode(),))
    fmt("args-dict", "%(a)s", ({"a": "token=" + S},))
    fmt("frozenset", extra={"v": frozenset({"token=" + S})})
    fmt("deep-nesting-100", extra={"v": __import__("functools").reduce(lambda a, _: {"k": a}, range(100), {"token": S})})

elif group == "text":
    # (nombre, texto). El secreto S es hexadecimal: solo [0-9a-z].
    cases = {
        "bearer": "Authorization: Bearer %s",
        "bearer-lower": "authorization: bearer %s",
        "bearer-eq": "authorization=Bearer %s",
        "basic": "Authorization: Basic %s",
        "token-scheme": "Authorization: Token %s",
        "apikey-scheme": "Authorization: ApiKey %s",
        "digest": 'Authorization: Digest username="u", response="%s"',
        "proxy-basic": "Proxy-Authorization: Basic %s",
        "cookie-first": "Cookie: sid=%s",
        "cookie-second": "Cookie: theme=dark; sid=%s",
        "cookie-third": "Cookie: a=1; b=2; session=%s; c=3",
        "set-cookie": "Set-Cookie: sid=%s; Path=/; HttpOnly",
        "kv-eq": "token=%s",
        "kv-colon": "token: %s",
        "kv-spaced": "token = %s",
        "kv-upper": "TOKEN=%s&x=1",
        "kv-dq": 'token="%s"',
        "json-dq": '{"token": "%s"}',
        "json-compact": '{"password":"%s","a":1}',
        "py-repr-sq": "{'api_key': '%s'}",
        "py-repr-bytes": "{'token': b'%s'}",
        "py-repr-bytes-2": "{'password': b\"%s\"}",
        "esc-json-dq": '{\\"token\\": \\"%s\\"}',
        "esc-json-basic": '{\\"authorization\\": \\"Basic %s\\"}',
        "json-in-json": json.dumps(json.dumps({"password": "%s"})),
        "quoted-spaces": "password: 'a b %s c'",
        "query-token": "GET /cb?code=1&access_token=%s&state=2",
        "query-apikey": "GET /x?apikey=%s",
        "query-api-key": "GET /x?api-key=%s",
        "query-api_key": "GET /x?api_key=%s",
        "hdr-x-api-key": "X-Api-Key: %s",
        "hdr-x-api-key-lc": "x-api-key: %s",
        "header-repr-pair": "headers=[('x-api-key', '%s')]",
        "multiline-quoted": 'password: "line1\nline2 %s"',
        "ws-protocol": "Sec-WebSocket-Protocol: drakter.v1, drakter.auth.%s",
        "ws-protocol-2": "< Sec-WebSocket-Protocol: drakter.auth.%s",
        "sk": "key sk-%s",
        "sk-ant": "key sk-ant-api03-%s",
    }
    for n, t in cases.items():
        fmt(n, t.replace("%s", S) if "%s" in t else t % S if False else t.replace("%s", S))
    # valores con comilla escapada dentro: la parte tras la comilla no debe quedar
    tail = "tail" + S
    fmt("dq-escaped-inner", 'password: "ab\\"%s"' % tail, needles=[tail])
    fmt("dq-escaped-inner-json", json.dumps({"password": 'ab"%s' % tail}), needles=[tail])
    fmt("sq-escaped-inner", "password: 'ab\\'%s'" % tail, needles=[tail])

elif group == "registered":
    odd = S + '"q\\b\nzé中\U0001F600/+='
    L.register_secret(odd)
    L.register_secret(S)
    j = json.dumps(odd)[1:-1]
    needles = [odd, S, j]
    fmt("msg", "x " + odd, needles=needles)
    fmt("msg-args", "x %s", (odd,), needles=needles)
    fmt("extra-val", extra={"v": odd}, needles=needles)
    fmt("extra-nested", extra={"a": {"b": [odd]}}, needles=needles)
    fmt("extra-dict-key", extra={"a": {odd: 1}}, needles=needles)
    fmt("extra-bytes", extra={"v": odd.encode()}, needles=needles)
    fmt("repr-str", "x %r", (odd,), needles=needles)
    fmt("repr-dict", "x %s", ({"a": odd},), needles=needles)
    fmt("repr-obj", extra={"o": Obj(odd)}, needles=needles)
    fmt("repr-obj-msg", Obj(odd), needles=needles)
    fmt("exc-args", exc=exc_of(lambda: ValueError(odd)), needles=needles)
    fmt("exc-fstring", exc=exc_of(lambda: RuntimeError("fallo con %s dentro" % odd)), needles=needles)
    fmt("exc-args-dict", exc=exc_of(lambda: KeyError({"a": odd})), needles=needles)
    fmt("exc-multi-args", exc=exc_of(lambda: OSError(13, odd, odd)), needles=needles)

    def chained():
        try:
            raise ValueError(odd)
        except ValueError as e:
            raise RuntimeError("wrap") from e
    fmt("exc-chained", exc=exc_of(chained), needles=needles)

    def grouped():
        return ExceptionGroup("g", [ValueError(odd), TypeError("x")])
    fmt("exc-group", exc=exc_of(grouped), needles=needles)

    def noted():
        e = ValueError("x")
        e.add_note("nota " + odd)
        return e
    fmt("exc-note", exc=exc_of(noted), needles=needles)
    fmt("stack-info", extra={}, needles=needles)
    r = rec("m")
    r.stack_info = "Stack (most recent call last):\n  secret " + odd
    try:
        put("stack-info-real", F.format(r), needles)
    except BaseException as e:  # noqa: BLE001
        put("stack-info-real", "<RAISED %s>" % type(e).__name__, [])
    # Desempaquetados que el redactor no puede ver: se informan como límites en LEAK-4x.

elif group == "formatfail":
    # Un fallo del formateador no debe volcar el mensaje ni los argumentos crudos.
    import io
    logs = os.path.join(req["dir"], "l")
    buf = io.StringIO()
    real = sys.stderr
    sys.stderr = buf
    try:
        for _suf in ("", "b", "c", "d", "e", "f", "g"):
            L.register_secret(S + _suf)
        L.configure_logging("DEBUG", __import__("pathlib").Path(logs))
        lg = logging.getLogger("leakprobe")
        propagated = []

        def call(*a, **k):
            try:
                lg.info(*a, **k)
            except BaseException as e:  # noqa: BLE001
                propagated.append(type(e).__name__)

        circular = {}
        circular["self"] = circular
        call("login %s", S, extra={"ctx": circular})
        deep = {"k": None}
        cur = deep
        for _ in range(5000):
            cur["k"] = {"k": None}
            cur = cur["k"]
        call("login2 %s", S + "b", extra={"ctx": deep})

        class Bad:
            def __repr__(self): raise RuntimeError("repr roto")
            __str__ = __repr__
        call("login3 %s", S + "d", extra={"ctx": Bad()})
        call("login4 %s %s", S + "e", Bad())
        call("login5 %s %s", S + "f", Bad(), extra={"a": 1})

        class BadKey:
            def __str__(self): raise RuntimeError("clave rota")
            __repr__ = __str__
            def __hash__(self): return 1
        call("login6 %s", S + "g", extra={"ctx": {BadKey(): 1}})
    finally:
        sys.stderr = real
    text = buf.getvalue()
    flog = os.path.join(logs, "backend.log")
    text += open(flog, encoding="utf-8").read() if os.path.exists(flog) else ""
    out["stderr+file"] = [text, [S, S + "b", S + "d", S + "e", S + "c", S + "f", S + "g"]]
    out["propagated"] = [json.dumps(propagated), []]

elif group == "perf":
    # Tiempo de formatear texto hostil sin ningún patrón: debe ser (casi) lineal.
    def t(n, ch):
        s = ch * n
        t0 = time.perf_counter()
        F.format(rec("m " + s))
        return time.perf_counter() - t0
    out["perf"] = [json.dumps({
        "a_small": t(500, "a"), "a_big": t(2000, "a"),
        "ws_small": t(500, "a "), "ws_big": t(2000, "a "),
        "sub_small": t(500, "a-"), "sub_big": t(2000, "a-"),
    }), []]
    import signal

    def on_alarm(*_):
        raise TimeoutError("alarm")
    signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(15)
    try:
        t0 = time.perf_counter()
        put("trunc-16k", F.format(rec("m", (), {"blob": "x" * 40000 + " token=" + S})), [S])
        out["len-trunc"] = [str(len(out["trunc-16k"][0])), []]
        out["t-trunc"] = [str(time.perf_counter() - t0), []]
    except TimeoutError:
        out["trunc-16k"] = ["", []]
        out["len-trunc"] = ["0", []]
        out["t-trunc"] = ["15.0+", []]
    finally:
        signal.alarm(0)

elif group == "limits":
    import base64, urllib.parse
    L.register_secret("registered-" + S)
    r = "registered-" + S
    fmt("L-plain-unregistered-msg", "valor %s" % S)
    fmt("L-plain-unregistered-exc", exc=exc_of(lambda: ValueError(S)))
    fmt("L-plain-extra-benign-key", extra={"note": S})
    fmt("L-key-passwd", extra={"passwd": S})
    fmt("L-key-pwd", extra={"pwd": S})
    fmt("L-key-private_key", extra={"private_key": S})
    fmt("L-key-access_key", extra={"access_key": S})
    fmt("L-key-auth", extra={"auth": S})
    fmt("L-key-session", extra={"session": S})
    fmt("L-key-jwt", extra={"jwt": S})
    fmt("L-key-bearer", extra={"bearer": S})
    fmt("L-key-key", extra={"key": S})
    fmt("L-key-sig", extra={"signature": S})
    fmt("L-text-passwd", "passwd=%s" % S)
    fmt("L-text-key-eq", "GET /x?key=%s" % S)
    fmt("L-text-url-userinfo", "http://user:%s@host/x" % S)
    fmt("L-text-token-is", "the token is %s" % S)
    fmt("L-text-name-value", json.dumps({"name": "token", "value": S}))
    fmt("L-text-header-name-value", json.dumps({"headers": [{"name": "X-Api-Key", "value": S}]}))
    fmt("L-fmt-ghp", "gh ghp_" + S[:36].ljust(36, "a"), needles=[S[:30]])
    fmt("L-fmt-akia", "aws AKIA" + S[:16].upper(), needles=[S[:16].upper()])
    fmt("L-fmt-slack", "slack xoxb-1234-5678-" + S, needles=[S])
    fmt("L-fmt-google", "g AIza" + S[:35].ljust(35, "b"), needles=[S[:30]])
    jwt = "eyJhbGciOiJIUzI1NiJ9." + S + "." + S[::-1]
    fmt("L-fmt-jwt", "jwt " + jwt, needles=[S])
    fmt("L-fmt-pem", "-----BEGIN PRIVATE KEY-----\n" + S + "\n-----END PRIVATE KEY-----", needles=[S])
    fmt("L-registered-b64", "Basic " + base64.b64encode(b"u:" + r.encode()).decode(), needles=[base64.b64encode(r.encode()).decode()[:20]])
    fmt("L-registered-b64-bearerless", "creds " + base64.b64encode(r.encode()).decode(), needles=[base64.b64encode(r.encode()).decode()[:20]])
    fmt("L-registered-hex", "h " + r.encode().hex(), needles=[r.encode().hex()])
    fmt("L-registered-urlenc", "u " + urllib.parse.quote(r + " /+="), needles=[urllib.parse.quote(r + " /+=")])
    fmt("L-registered-json-in-json", "body " + json.dumps(json.dumps({"k": 'a"b\\' + r})), needles=[r])
    fmt("L-registered-split", "a " + r[:8] + " " + r[8:], needles=[r[8:]])
    fmt("L-registered-lower", "a " + r.upper(), needles=[r.upper()])
    fmt("L-registered-reversed", "a " + r[::-1], needles=[r[::-1]])
    fmt("L-registered-in-msg-truncated", "a " + r[: len(r) - 4], needles=[r[: len(r) - 4]])

print(json.dumps(out))
'''


def _python(ctx: Context) -> str:
    if ctx.process is None:
        raise NotApplicable("no hay proceso objetivo: no se conoce el intérprete")
    return str(ctx.process.args[0])  # type: ignore[index]


def _child(ctx: Context, group: str, **extra: object) -> tuple[dict[str, list], str]:
    """Ejecuta un grupo en un subproceso. Devuelve (casos, stderr)."""
    python = _python(ctx)
    if not (ctx.backend_dir / "app" / "core" / "logging.py").is_file():
        raise NotApplicable("el objetivo no tiene app/core/logging.py")
    secret = "zz" + secrets.token_hex(16)
    scratch = ctx.scratch()
    payload = json.dumps({"group": group, "S": secret, "dir": str(scratch), **extra})
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": "C.UTF-8",
        "HOME": str(ctx.root / "home"),
        "TMPDIR": str(ctx.root),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        done = subprocess.run(
            [python, "-c", CHILD],
            input=payload.encode(),
            cwd=ctx.backend_dir,
            env=environment,
            capture_output=True,
            timeout=CHILD_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise Breach(f"el grupo {group} no terminó en {CHILD_TIMEOUT:.0f}s (cuelgue del redactor)") from exc
    if done.returncode != 0:
        raise RuntimeError(f"hijo {group} falló: {done.stderr.decode('utf-8', 'replace')[-600:]}")
    cases = json.loads(done.stdout.decode("utf-8").strip().splitlines()[-1])
    return cases, done.stderr.decode("utf-8", "replace")


def _leaks(cases: dict[str, list], only: str | None = None) -> list[str]:
    found = _raised(cases)
    for name, item in cases.items():
        if only and not name.startswith(only):
            continue
        line, needles = item[0], item[1]
        if any(needle and needle in line for needle in needles):
            found.append(name)
    return found


def _raised(cases: dict[str, list]) -> list[str]:
    return [name for name, item in cases.items() if len(item) > 2 and item[2] == "raised"]


def _report(prefix: str, names: list[str]) -> str:
    return f"{prefix}: " + ", ".join(names)


# --------------------------------------------------------------------------- #
# Formateador (promesas del contrato)
# --------------------------------------------------------------------------- #
@attack(
    "LEAK-01",
    "Variantes de nombre de clave en extra (planas, anidadas, en listas) quedan redactadas",
    guarantee="CLAUDE.md §8: auditoría y logs sin claves API ni datos sensibles; contrato logging",
)
def key_name_variants(ctx: Context) -> None:
    cases, _ = _child(ctx, "keys")
    expect(len(cases) >= 50, "el control no produjo los casos esperados")
    leaks = _leaks(cases)
    expect(not leaks, _report("valor visible tras clave sensible según el contrato", leaks))


@attack(
    "LEAK-02",
    "Pares (clave, valor), cabeceras ASGI en bytes y objetos con repr no filtran",
    guarantee="CLAUDE.md §8; contrato logging: 'listas de pares', 'objetos no str'",
)
def structures(ctx: Context) -> None:
    cases, _ = _child(ctx, "structures")
    expect(len(cases) >= 20, "el control no produjo los casos esperados")
    expect(not _raised(cases), _report("el formateador lanzó excepción", _raised(cases)))
    leaks = _leaks(cases)
    expect(not leaks, _report("secreto visible", leaks))


@attack(
    "LEAK-03",
    "Cabeceras HTTP en texto libre, esquemas, comillas escapadas y valores multilínea",
    guarantee="CLAUDE.md §8; contrato logging: '<clave>=<valor> en texto libre', 'cualquier esquema'",
)
def free_text(ctx: Context) -> None:
    cases, _ = _child(ctx, "text")
    expect(len(cases) >= 35, "el control no produjo los casos esperados")
    # Control positivo: el caso más simple sí se redacta, el camino se alcanzó.
    expect("kv-eq" not in _leaks(cases), "control roto: 'token=<valor>' no se redacta")
    leaks = _leaks(cases)
    expect(not leaks, _report("secreto visible", leaks))


@attack(
    "LEAK-04",
    "register_secret enmascara el valor en mensaje, extra, claves, repr, bytes y excepciones",
    guarantee="CLAUDE.md §8; contrato logging: valores registrados, trazas de excepción",
)
def registered_values(ctx: Context) -> None:
    cases, _ = _child(ctx, "registered")
    expect(len(cases) >= 15, "el control no produjo los casos esperados")
    expect(not _raised(cases), _report("el formateador lanzó excepción", _raised(cases)))
    leaks = _leaks(cases)
    expect(not leaks, _report("secreto registrado visible", leaks))


@attack(
    "LEAK-05",
    "Con secretos registrados, si el mensaje no se puede formatear (repr roto) logging no vuelca los argumentos crudos",
    guarantee="CLAUDE.md §8: logs sin secretos; el fallo no debe abrir la redacción",
)
def formatter_failure_open(ctx: Context) -> None:
    cases, child_stderr = _child(ctx, "formatfail")
    text = cases["stderr+file"][0] + child_stderr
    # Control: el fallo se produjo de verdad (Logging error / Traceback), si no el ataque no llegó.
    expect(
        "Logging error" in text or "Traceback" in text or "RecursionError" in text,
        "control: el formateador no llegó a fallar; ataque no alcanzó el camino",
    )
    needles = cases["stderr+file"][1]
    leaked = [i for i, needle in enumerate(needles) if needle in text]
    expect(
        not leaked,
        "al fallar el formateador, logging.Handler.handleError escribe record.msg/args sin redactar "
        f"en stderr ({len(leaked)} de {len(needles)} secretos visibles)",
    )


@attack(
    "LEAK-07",
    "Un extra cíclico o muy anidado no hace que logger.info lance una excepción al código llamante",
    guarantee="Contrato logging: 'nunca dejar que el logging lance' (el formateador cae a un texto seguro)",
)
def formatter_exception_propagates(ctx: Context) -> None:
    cases, _ = _child(ctx, "formatfail")
    propagated = json.loads(cases["propagated"][0])
    expect(not propagated, f"logger.info propagó {propagated} al llamante (RecursionError no se captura en logging)")


@attack(
    "LEAK-06",
    "Redacción en tiempo lineal y con truncado a 16 KiB por campo (sin ReDoS)",
    guarantee="Contrato logging: 'en tiempo lineal ... se trunca cada campo a 16 KiB'",
)
def redaction_cost(ctx: Context) -> None:
    cases, _ = _child(ctx, "perf")
    times = json.loads(cases["perf"][0])
    # 4x más entrada: lineal ~4x; cuadrático ~16x. Umbral holgado frente al ruido.
    ratios = {
        name: times[name + "_big"] / max(times[name + "_small"], 1e-4) for name in ("a", "ws", "sub")
    }
    worst_name = max(ratios, key=ratios.get)
    quadratic = ratios[worst_name] > 9 and times[worst_name + "_big"] > 0.05
    trunc_len = int(cases["len-trunc"][0])
    untruncated = trunc_len > 20000
    secret_after_cut = bool(_leaks({"x": cases["trunc-16k"]}))
    problems = []
    if quadratic:
        problems.append(
            f"coste superlineal: {worst_name} x4 de entrada = x{ratios[worst_name]:.0f} "
            f"({times[worst_name + '_big']:.2f}s con 2000 caracteres)"
        )
    if cases["t-trunc"][0].endswith("+"):
        problems.append("un campo de 40000 caracteres sin patrones no terminó en 15 s (cuadrático, sin truncado a 16 KiB)")
    elif untruncated:
        problems.append(f"el campo de 40000 caracteres no se trunca (línea de {trunc_len}; t={float(cases['t-trunc'][0]):.1f}s)")
    if secret_after_cut:
        problems.append("secreto visible pasado el límite de 16 KiB")
    expect(not problems, "; ".join(problems))


# --------------------------------------------------------------------------- #
# Backend real
# --------------------------------------------------------------------------- #
def _marker() -> str:
    return "leakprobe" + secrets.token_hex(6)


@attack(
    "LEAK-08",
    "Una cabecera larga hostil no bloquea el bucle del backend al registrarla (ReDoS en el redactor)",
    guarantee="Contrato logging: redacción en tiempo lineal; disponibilidad del backend local",
)
def long_header_blocks_event_loop(ctx: Context) -> None:
    marker = _marker()
    size = 3000  # acotado: con un redactor cuadrático cuesta segundos, no minutos
    baseline = time.perf_counter()
    expect(ctx.http("GET", "/health").status == 200, "control: /health con token no responde")
    baseline = time.perf_counter() - baseline
    try:
        ctx.ws_handshake(headers=[("X-Probe", marker + "a-" * (size // 2))], timeout=0.5)
    except OSError:
        pass  # el cliente se rinde; lo que importa es cuánto tarda el servidor en atender lo siguiente
    start = time.perf_counter()
    status = ctx.http("GET", "/health", timeout=30.0).status
    blocked = time.perf_counter() - start
    expect(status == 200, f"/health devolvió {status} tras la cabecera larga")
    time.sleep(0.3)
    if marker not in ctx.logs_text():
        raise NotApplicable("la cabecera no llegó al log (nivel de log sin DEBUG): camino no alcanzado")
    expect(
        blocked < 1.5,
        f"el bucle estuvo bloqueado {blocked:.1f}s (base {baseline * 1000:.0f} ms) por {size} caracteres de cabecera",
    )


@attack(
    "LEAK-10",
    "Token bueno, malo, por query, cabecera y subprotocolo no aparecen en los logs",
    guarantee="CLAUDE.md §8; contrato backend: 'el guardia nunca registra cabeceras, consulta ni token'",
)
def token_not_in_logs(ctx: Context) -> None:
    bad = "zz" + secrets.token_hex(16)
    marker = _marker()
    probes = [
        ("bearer-malo", {"token": bad}, f"/{marker}-a"),
        ("query-aprobador", {"token": False}, f"/api/v1/auth/check?approver={ctx.approver_token}&{marker}=i"),
        ("path-aprobador", {"token": False}, f"/{marker}-j/{ctx.approver_token}"),
        ("query-bueno", {"token": False}, f"/api/v1/auth/check?token={ctx.token}&{marker}=b"),
        ("query-malo", {"token": False}, f"/api/v1/auth/check?token={bad}&access_token={bad}"),
        ("path-bueno", {"token": False}, f"/{marker}-c/{ctx.token}"),
        ("cookie", {"token": False, "headers": [("Cookie", f"a=1; sid={bad}; t={ctx.token}")]}, f"/{marker}-e"),
        ("x-api-key", {"token": False, "headers": [("X-Api-Key", bad), ("X-Auth-Token", ctx.token)]}, f"/{marker}-f"),
        ("basic", {"token": False, "headers": [("Authorization", f"Basic {bad}")]}, f"/{marker}-g"),
        ("bearer-bueno-ruta-404", {}, f"/{marker}-h"),
    ]
    statuses = {}
    for name, kwargs, path in probes:
        statuses[name] = ctx.http("GET", path, **kwargs).status
    expect(statuses["bearer-malo"] == 401, "control: token malo no devuelve 401, no se alcanzó el guardia")
    # WS con credencial mala y buena por cabecera y subprotocolo.
    handshakes = {
        "ws-sub-malo": ctx.ws_handshake(headers=[("Sec-WebSocket-Protocol", f"drakter.v1, drakter.auth.{bad}")]),
        "ws-sub-aprobador": ctx.ws_handshake(headers=[("Sec-WebSocket-Protocol", f"drakter.v1, drakter.auth.{ctx.approver_token}")]),
        "ws-sub-bueno": ctx.ws_handshake(headers=[("Sec-WebSocket-Protocol", f"drakter.v1, drakter.auth.{ctx.token}")]),
        "ws-bearer-malo": ctx.ws_handshake(headers=[("Authorization", f"Bearer {bad}")]),
        "ws-bearer-bueno": ctx.ws_handshake(headers=[("Authorization", f"Bearer {ctx.token}")]),
        "ws-bearer-aprobador": ctx.ws_handshake(headers=[("Authorization", f"Bearer {ctx.approver_token}")]),
        "ws-xapikey-malo": ctx.ws_handshake(headers=[("X-Api-Key", bad), ("Cookie", f"a=1; sid={bad}")]),
        "ws-basic-malo": ctx.ws_handshake(headers=[("Authorization", f"Basic {bad}")]),
    }
    expect(handshakes["ws-bearer-bueno"].status == 101, "control: el Bearer bueno no abre el websocket")
    time.sleep(0.5)
    text = ctx.logs_text()
    expect(marker in text, "control: el guardia no registró las peticiones rechazadas")
    leaked = []
    if bad in text:
        leaked.append("token malo inventado")
    if ctx.token in text:
        leaked.append("token de sesión (ui)")
    if ctx.approver_token in text:
        leaked.append("token del aprobador")
    expect(not leaked, "visible en los logs: " + ", ".join(leaked))


@attack(
    "LEAK-11",
    "Los cuerpos y cabeceras de error no devuelven el secreto enviado ni lo reflejan",
    guarantee="CLAUDE.md §8: nada sensible fuera; contrato errores: mensaje fijo",
)
def error_bodies(ctx: Context) -> None:
    bad = "zz" + secrets.token_hex(16)
    attempts = [
        ctx.http("GET", f"/api/v1/auth/check?token={bad}", token=bad),
        ctx.http("GET", f"/{bad}/nope"),
        ctx.http("POST", "/api/v1/auth/check", json_body={"token": bad, "password": bad}),
        ctx.http("POST", "/api/v1/auth/check", body=b'{"password": "' + bad.encode() + b'"', headers=[("Content-Type", "application/json")]),
        ctx.http("GET", "/health", host=f"{bad}.example"),
        ctx.http("GET", "/health", headers=[("Origin", f"http://{bad}.example")]),
        ctx.http("GET", "/api/v1/auth/check", token=False, headers=[("Origin", "app://drakter"), ("X-Api-Key", bad)]),
        ctx.http("GET", f"/api/v1/auth/check?x={'%ff' * 8}{bad}", token=bad),
        ctx.http("GET", "/%00%ff" + bad),
    ]
    expect({a.status for a in attempts} >= {401, 403, 404}, "control: no se alcanzaron los caminos 401/403/404")
    reflected = [
        i for i, a in enumerate(attempts) if bad.encode() in a.body or bad in str(a.headers)
    ]
    expect(not reflected, f"el secreto se refleja en {len(reflected)} respuestas de error: índices {reflected}")
    # El token bueno tampoco debe volver nunca en un error.
    good = ctx.http("POST", "/api/v1/auth/check", json_body={"token": ctx.token})
    expect(ctx.token.encode() not in good.body, "el token de sesión se refleja en un cuerpo de error")


ERROR_APP = r'''
import asyncio, json, os, sys, logging
sys.path.insert(0, os.getcwd())
req = json.loads(sys.stdin.read())
S, scratch = req["S"], req["dir"]
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel, field_validator
from app.core import logging as L
from app.core.errors import install_error_handlers
L.configure_logging("DEBUG", Path(scratch) / "logs")
L.register_secret(S)
app = FastAPI()
install_error_handlers(app)

class Body(BaseModel):
    password: str
    @field_validator("password")
    @classmethod
    def v(cls, value):
        raise ValueError("invalido " + value)

@app.get("/boom")
async def boom():
    raise RuntimeError("fallo interno con " + S)

@app.post("/val")
async def val(body: Body):
    return {}

async def call(method, path, body=b"", ctype=None):
    sent = []
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    async def send(message):
        sent.append(message)
    headers = [(b"host", b"x"), (b"content-length", str(len(body)).encode())]
    if ctype:
        headers.append((b"content-type", ctype))
    scope = {"type": "http", "method": method, "path": path, "raw_path": path.encode(), "query_string": b"",
             "headers": headers, "server": ("x", 1), "client": ("127.0.0.1", 1), "scheme": "http",
             "http_version": "1.1", "root_path": "", "state": {}, "app": app}
    try:
        await app(scope, receive, send)
    except Exception as exc:
        sent.append({"type": "raised", "exc": type(exc).__name__})
    status = next((m["status"] for m in sent if m["type"] == "http.response.start"), None)
    text = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, text.decode("utf-8", "replace")

async def main():
    out = {}
    out["boom"] = await call("GET", "/boom")
    out["val"] = await call("POST", "/val", json.dumps({"password": S}).encode(), b"application/json")
    out["val-bad-type"] = await call("POST", "/val", json.dumps({"password": [S]}).encode(), b"application/json")
    out["val-extra-key"] = await call("POST", "/val", json.dumps({S: 1}).encode(), b"application/json")
    for h in logging.getLogger().handlers:
        h.flush()
    log = (Path(scratch) / "logs" / "backend.log").read_text("utf-8")
    print(json.dumps({"responses": out, "log": log}))

asyncio.run(main())
'''


@attack(
    "LEAK-12",
    "Un 500 y un 422 reales (app aislada con los manejadores del objetivo) no filtran el secreto ni en cuerpo ni en log",
    guarantee="CLAUDE.md §8; contrato errores: 500 con mensaje fijo, traza solo en el log y redactada",
)
def unhandled_and_validation(ctx: Context) -> None:
    python = _python(ctx)
    if not (ctx.backend_dir / "app" / "core" / "errors.py").is_file():
        raise NotApplicable("el objetivo no tiene app/core/errors.py")
    secret = "zz" + secrets.token_hex(16)
    scratch = ctx.scratch()
    done = subprocess.run(
        [python, "-c", ERROR_APP],
        input=json.dumps({"S": secret, "dir": str(scratch)}).encode(),
        cwd=ctx.backend_dir,
        env={"PATH": os.environ.get("PATH", ""), "HOME": str(ctx.root / "home"), "TMPDIR": str(ctx.root), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )
    if done.returncode != 0:
        raise RuntimeError("app de error aislada falló: " + done.stderr.decode("utf-8", "replace")[-600:])
    result = json.loads(done.stdout.decode().strip().splitlines()[-1])
    responses = result["responses"]
    expect(responses["boom"][0] == 500, f"control: /boom no dio 500 sino {responses['boom'][0]}")
    expect(responses["val"][0] == 422, f"control: /val no dio 422 sino {responses['val'][0]}")
    leaked = [name for name, (_, body) in responses.items() if secret in body]
    expect(not leaked, _report("el secreto vuelve en el cuerpo", leaked))
    expect("internal_error" in responses["boom"][1], "control: el 500 no usa el sobre de error")
    expect(secret not in result["log"], "el secreto registrado aparece en la traza del 500 en el log")
    expect("Unhandled exception" in result["log"], "control: el log no recoge el 500")


def _descendants(pid: int) -> list[int]:
    children: dict[int, list[int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat_text = (entry / "stat").read_text()
            ppid = int(stat_text.rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            continue
        children.setdefault(ppid, []).append(int(entry.name))
    found, queue = [], [pid]
    while queue:
        current = queue.pop()
        for child in children.get(current, []):
            found.append(child)
            queue.append(child)
    return found


@attack(
    "LEAK-20",
    "Los tokens (ui y aprobador) no están en argv, entorno, descriptores ni en el proceso; fd 0 es /dev/null",
    guarantee="D-14: el canal de control no se hereda; tokens fuera de argv, entorno, disco y logs",
)
def token_not_in_proc(ctx: Context) -> None:
    if ctx.process is None:
        raise NotApplicable("sin proceso objetivo")
    pid = ctx.process.pid
    cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
    expect(b"app" in cmdline, "control: no se leyó la línea de órdenes del backend")
    try:
        environment = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError as exc:
        raise NotApplicable(f"environ ilegible: {exc}") from exc
    expect(b"DRAKTER_DATA_DIR" in environment, "control: no se leyó el entorno del backend")
    needles = {"ui": ctx.token.encode(), "aprobador": ctx.approver_token.encode()}
    for pidx in [pid, *_descendants(pid)]:
        for name in ("cmdline", "environ"):
            try:
                data = Path(f"/proc/{pidx}/{name}").read_bytes()
            except OSError:
                continue
            for who, needle in needles.items():
                expect(needle not in data, f"token {who} en /proc/{pidx}/{name}")
    try:
        fd0 = os.readlink(f"/proc/{pid}/fd/0")
    except OSError as exc:
        raise NotApplicable(f"fd ilegibles: {exc}") from exc
    expect(fd0 == os.devnull, f"fd 0 del backend apunta a {fd0}, no a /dev/null")
    expect(not (ctx.runtime_dir / "session.json").exists(), "existe session.json: el token está en disco")


@attack(
    "LEAK-21",
    "Hijos del backend (Hermes): API_SERVER_KEY y claves del modelo no van en argv ni en cmdline",
    guarantee="Contrato Hermes: clave solo en el entorno del hijo, entorno limpio por lista blanca",
)
def child_process_secrets(ctx: Context) -> None:
    if ctx.process is None:
        raise NotApplicable("sin proceso objetivo")
    children = _descendants(ctx.process.pid)
    if not children:
        raise NotApplicable("el backend no lanza subprocesos todavía (integración Hermes ausente)")
    problems = []
    for child in children:
        try:
            environment = Path(f"/proc/{child}/environ").read_bytes().split(b"\0")
            cmdline = Path(f"/proc/{child}/cmdline").read_bytes()
        except OSError:
            continue
        values = [
            item.split(b"=", 1)[1]
            for item in environment
            if b"=" in item and any(w in item.split(b"=", 1)[0].upper() for w in (b"KEY", b"TOKEN", b"SECRET", b"PASSWORD"))
        ]
        for value in values:
            if len(value) >= 8 and value in cmdline:
                problems.append(f"pid {child}: un valor de clave de entorno está en argv")
        blob = b"\0".join(environment) + cmdline
        for who, tok in (("ui", ctx.token), ("aprobador", ctx.approver_token)):
            if tok.encode() in blob:
                problems.append(f"pid {child}: token {who} del backend heredado")
        try:
            if os.readlink(f"/proc/{child}/fd/0") != os.devnull:
                problems.append(f"pid {child}: fd 0 no es /dev/null (canal de control heredado)")
            parent_pipes = {os.readlink(f"/proc/{ctx.process.pid}/fd/{n}") for n in os.listdir(f"/proc/{ctx.process.pid}/fd") if os.readlink(f"/proc/{ctx.process.pid}/fd/{n}").startswith("pipe:")}
            shared = [n for n in os.listdir(f"/proc/{child}/fd") if os.readlink(f"/proc/{child}/fd/{n}") in parent_pipes]
            if shared:
                problems.append(f"pid {child}: hereda tuberías del backend en fd {shared}")
        except OSError:
            pass
        parent_env = Path(f"/proc/{ctx.process.pid}/environ").read_bytes()
        leaked_vars = [
            item.split(b"=", 1)[0].decode()
            for item in environment
            if item.split(b"=", 1)[0] in {b"DRAKTER_DATA_DIR", b"DRAKTER_RUNTIME_DIR"} and item in parent_env
        ]
        if leaked_vars:
            problems.append(f"pid {child}: hereda {', '.join(leaked_vars)} (entorno no limpio)")
    expect(not problems, "; ".join(problems))


@attack(
    "LEAK-22",
    "Sin session.json; tokens ausentes de todo el disco; logs 0600 y directorios 0700",
    guarantee="D-14: tokens fuera de disco; contrato logging: logs 0600",
)
def file_permissions(ctx: Context) -> None:
    problems = []

    def mode(path: Path) -> int:
        return stat.S_IMODE(path.lstat().st_mode)

    if (ctx.runtime_dir / "session.json").exists():
        problems.append("session.json existe (el token está en disco)")
    logs_dir = ctx.data_dir / "logs"
    expect(logs_dir.is_dir() and any(logs_dir.iterdir()), "control: no hay logs en data/logs")
    if mode(logs_dir) & 0o077:
        problems.append(f"logs_dir {oct(mode(logs_dir))}")
    for path in logs_dir.iterdir():
        if mode(path) & 0o177:
            problems.append(f"{path.name} {oct(mode(path))}")
    if ctx.runtime_dir.exists() and mode(ctx.runtime_dir) & 0o077:
        problems.append(f"runtime_dir {oct(mode(ctx.runtime_dir))}")
    # Ningún token en ningún archivo de la raíz aislada (base de datos, logs, temporales).
    needles = [ctx.token.encode(), ctx.approver_token.encode()]
    scanned = 0
    for path in ctx.root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        scanned += 1
        if any(n in data for n in needles):
            problems.append(f"token en disco: {path.relative_to(ctx.root)}")
    expect(scanned >= 2, "control: el barrido de disco no encontró archivos")
    expect(not problems, "; ".join(problems))


ROTATE = r'''
import json, os, sys, logging, stat
sys.path.insert(0, os.getcwd())
from pathlib import Path
req = json.loads(sys.stdin.read())
S, d = req["S"], Path(req["dir"])
os.umask(0o000)  # el handler no debe depender del umask del proceso
from app.core import logging as L
h = L._PrivateRotatingFileHandler(d / "backend.log", maxBytes=400, backupCount=3, encoding="utf-8")
h.setFormatter(L.JsonFormatter())
lg = logging.getLogger("rot"); lg.setLevel(logging.INFO); lg.addHandler(h); lg.propagate = False
for i in range(40):
    lg.info("linea %d token=%s", i, S)
h.close()
files = {p.name: oct(stat.S_IMODE(p.stat().st_mode)) for p in d.iterdir()}
print(json.dumps({"files": files, "content": "".join(p.read_text() for p in d.iterdir())}))
'''


@attack(
    "LEAK-23",
    "Los logs rotados quedan 0600 aunque el umask sea 000, y la rotación no filtra el secreto",
    guarantee="Contrato backend: rotación 5 MiB, 3 copias, permisos 600, también las rotadas",
)
def rotated_log_permissions(ctx: Context) -> None:
    python = _python(ctx)
    if not (ctx.backend_dir / "app" / "core" / "logging.py").is_file():
        raise NotApplicable("sin app/core/logging.py")
    secret = "zz" + secrets.token_hex(16)
    scratch = ctx.scratch()
    done = subprocess.run(
        [python, "-c", ROTATE],
        input=json.dumps({"S": secret, "dir": str(scratch)}).encode(),
        cwd=ctx.backend_dir,
        env={"PATH": os.environ.get("PATH", ""), "HOME": str(ctx.root / "home"), "TMPDIR": str(ctx.root), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )
    if done.returncode != 0:
        raise RuntimeError("rotación aislada falló: " + done.stderr.decode("utf-8", "replace")[-600:])
    result = json.loads(done.stdout.decode().strip().splitlines()[-1])
    files = result["files"]
    expect(len(files) >= 3, f"control: la rotación no produjo copias ({sorted(files)})")
    loose = {name: mode for name, mode in files.items() if int(mode, 8) & 0o177}
    expect(not loose, f"permisos laxos: {loose}")
    expect(secret not in result["content"], "el secreto aparece en el contenido rotado")


# --------------------------------------------------------------------------- #
# Auditoría
# --------------------------------------------------------------------------- #
AUDIT = r'''
import hashlib, json, os, sys
sys.path.insert(0, os.getcwd())
req = json.loads(sys.stdin.read())
S = req["S"]
import importlib
for _m in ("app.audit.writer", "app.audit.log"):
    try:
        filter_params = importlib.import_module(_m).filter_params
        break
    except ModuleNotFoundError as _e:
        if _e.name != _m:
            print(json.dumps({"import_error": repr(_e)})); sys.exit(0)
    except ImportError as _e:
        print(json.dumps({"import_error": repr(_e)})); sys.exit(0)
policies = {"note": "log", "blob": "log", "bag": "log", "who": "hash", "pwd_note": "log", "dropme": "omit"}
params = {
    "note": "Authorization: Basic " + S,
    "blob": "x" * 2000 + " token=" + S,
    "bag": {"headers": [("x-api-key", S)], "token": S, "nested": {"authorization": "Basic " + S}},
    "who": S,
    "password": S,
    "api_key": S,
    "not_listed": S,
    "dropme": S,
    "pwd_note": "{\\\"password\\\": \\\"" + S + "\\\"}",
}
kept = filter_params(params, policies)
print(json.dumps({"kept": kept, "text": json.dumps(kept, ensure_ascii=False)}))
'''


@attack(
    "LEAK-30",
    "Auditoría: los parámetros sensibles no se guardan en claro (lista blanca, hash, redacción)",
    guarantee="CLAUDE.md §8: auditoría sin claves API ni datos sensibles; contrato Hermes log|hash|omit",
)
def audit_params(ctx: Context) -> None:
    python = _python(ctx)
    audit_dir = ctx.backend_dir / "app" / "audit"
    if not ((audit_dir / "writer.py").is_file() or (audit_dir / "log.py").is_file()):
        raise NotApplicable("el objetivo no tiene app/audit/{writer,log}.py (auditoría aún no integrada)")
    secret = "zz" + secrets.token_hex(16)
    done = subprocess.run(
        [python, "-c", AUDIT],
        input=json.dumps({"S": secret}).encode(),
        cwd=ctx.backend_dir,
        env={"PATH": os.environ.get("PATH", ""), "HOME": str(ctx.root / "home"), "TMPDIR": str(ctx.root), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )
    if done.returncode != 0:
        raise RuntimeError("filter_params falló: " + done.stderr.decode("utf-8", "replace")[-600:])
    result = json.loads(done.stdout.decode().strip().splitlines()[-1])
    if "import_error" in result:
        raise NotApplicable("el módulo de auditoría del objetivo no se puede importar: " + result["import_error"][:200])
    kept = result["kept"]
    expect(set(kept) == {"note", "blob", "bag", "who", "pwd_note"}, f"control: claves conservadas inesperadas {sorted(kept)}")
    expect("password" not in kept and "api_key" not in kept and "not_listed" not in kept and "dropme" not in kept,
           "un parámetro no listado se conservó en la auditoría")
    expect(kept["who"].startswith("sha256:") and secret not in kept["who"], "la política hash guardó el valor en claro")
    expect(secret not in result["text"], "el secreto aparece en claro en los parámetros auditados con política log")


@attack(
    "LEAK-31",
    "Auditoría real: audit_events y pending_actions no contienen el token ni secretos enviados",
    guarantee="CLAUDE.md §8: auditoría sin datos sensibles",
)
def audit_table_contents(ctx: Context) -> None:
    tables = ctx.contract.get("tables", {})
    audit, pending = tables.get("audit_events", "audit_events"), tables.get("pending_actions", "pending_actions")
    if not ctx.db_path.is_file():
        raise NotApplicable("no hay base de datos")
    uri = f"file:{ctx.db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if audit not in existing:
            raise NotApplicable(f"el objetivo no tiene la tabla {audit} (F13 no integrada)")
        bad = "zz" + secrets.token_hex(16)
        # Ataque activo si la ruta de herramientas existe: parámetros sensibles reales.
        try:
            route = ctx.route("tool_call")
        except NotApplicable:
            route = None
        if route:
            ctx.http("POST", route, json_body={"tool": ctx.contract["tools"]["destructive"], "arguments": {"password": bad, "api_key": bad, "token": bad, "note": f"Authorization: Basic {bad}"}})
            ctx.http("POST", route, json_body={"tool": ctx.contract["tools"]["not_allowed"], "arguments": {"password": bad}})
        dump = ""
        for name in (audit, pending):
            if name in existing:
                dump += json.dumps([list(map(str, r)) for r in conn.execute(f"SELECT * FROM {name}")])
    finally:
        conn.close()
    expect(ctx.token not in dump and ctx.approver_token not in dump, "un token de sesión está en la auditoría")
    if route is None:
        raise NotApplicable("tabla de auditoría presente, pero sin ruta de herramientas para sembrar parámetros sensibles")
    expect(bad not in dump, "un parámetro sensible enviado a una herramienta quedó en claro en la base")


# --------------------------------------------------------------------------- #
# Inventarios informativos de límites (no son defectos del contrato)
# --------------------------------------------------------------------------- #
@attack(
    "LEAK-40",
    "INFORMATIVO: límites de un redactor por patrones (secretos sin clave, formatos de proveedor, derivados)",
    guarantee="Ninguna: el contrato no promete esto; se documenta para no darlo por cubierto",
)
def pattern_limits(ctx: Context) -> None:
    cases, _ = _child(ctx, "limits")
    leaks = _leaks(cases)
    clean = sorted(set(cases) - set(leaks))
    raise NotApplicable(
        "INFORMATIVO (no es un veredicto de defecto). Visibles hoy: "
        + ", ".join(leaks)
        + " | Cubiertos: "
        + ", ".join(clean)
    )
