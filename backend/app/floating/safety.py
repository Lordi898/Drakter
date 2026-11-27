"""Port literal de una parte de `showcase/tauri/sidecar/safety.mjs` de Roamies (CONTRACT.md §9.1, §9.3, §11.3).

Origen: KenKaiii/Roamies@8f0adaa, `safety.mjs` (AGPL-3.0, ver THIRD_PARTY_NOTICES.md): `PRIVATE_HOST`,
`isPrivateAddress`, `checkUrl`, `checkLink` (sin la rama `file:`: en Drakter `home` es siempre null) y
`checkDrawAction`. Cada bloque cita su línea original. Los motivos en inglés son los de Roamies.

`new URL()` (WHATWG) se emula con `urllib.parse.urlsplit` más lo que cambia el resultado de estas reglas: el
recorte de espacios y controles, la normalización del host (minúsculas, porcentajes, IDNA) y las formas cortas de
IPv4 de los esquemas especiales (`http://127.1`, `http://2130706433`, `http://0x7f.1`), que el navegador convierte en
`127.0.0.1`. Lo que no se emula del todo se rechaza como enlace no válido (cierra, no abre).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Final, NamedTuple
from urllib.parse import unquote, urlsplit

from app.floating.drawjs import js_str, js_trim, u16len

SAFE: Final = "safe"  # safety.mjs:12
ASK: Final = "ask"
BLOCK: Final = "block"


class Verdict(NamedTuple):  # safety.mjs:13
    level: str
    reason: str = ""


def verdict(level: str, reason: str = "") -> Verdict:  # safety.mjs:13
    return Verdict(level, reason)


# safety.mjs:440
PRIVATE_HOST: Final = re.compile(
    r"(localhost|.*\.local|.*\.internal|0\.0\.0\.0|127\.[0-9]+\.[0-9]+\.[0-9]+|10\.[0-9]+\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+"
    r"|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+|169\.254\.[0-9]+\.[0-9]+|\[?::1\]?|\[?f[cd][0-9a-f:]*\]?|\[?fe80:[0-9a-f:]*\]?)",
    re.I,
)
_MAPPED: Final = re.compile(r"(?:0*:)*:?ffff:(?:0+:)?([0-9a-f]{1,4}):([0-9a-f]{1,4})")
_V4: Final = re.compile(r"(?:.*:)?([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})")


def is_private_address(ip: Any) -> bool:  # safety.mjs:442-454
    """An IP address that isn't on the public internet: this computer, the local network, link-local (cloud metadata),
    carrier-grade NAT, multicast and reserved ranges, also written as IPv4 inside IPv6 (::ffff:127.0.0.1)."""
    a = js_str(ip if ip is not None else "").lower()
    a = re.sub(r"^\[|\]\Z", "", a)
    a = re.sub(r"%.*\Z", "", a, count=1)
    mapped = _MAPPED.fullmatch(a)
    if mapped:
        hi, lo = int(mapped[1], 16), int(mapped[2], 16)
        a = f"{hi >> 8}.{hi & 255}.{lo >> 8}.{lo & 255}"
    v4 = _V4.fullmatch(a)
    if v4:
        b0, b1 = int(v4[1]), int(v4[2])
        return (b0 == 0 or b0 == 10 or b0 == 127 or (b0 == 100 and 64 <= b1 <= 127) or (b0 == 169 and b1 == 254) or (b0 == 172 and 16 <= b1 <= 31)
                or (b0 == 192 and (b1 == 168 or (b1 == 0 and int(v4[3]) == 0))) or (b0 == 198 and b1 in (18, 19)) or b0 >= 224)
    if ":" not in a:
        return False
    return (a == "::" or a == "::1" or bool(re.match("f[cd]", a)) or bool(re.match("fe[89ab]", a)) or a.startswith("ff")
            or a.startswith("64:ff9b:") or (bool(re.match("0*:", a)) and bool(re.fullmatch(r"[0:]*(:1)?", a))))


# ---------------------------------------------------------------- new URL() (emulación de lo que usan estas reglas)
class _Url(NamedTuple):
    protocol: str  # "https:"
    username: str
    password: str
    hostname: str  # como `URL.hostname`: IPv6 entre corchetes


_SCHEME: Final = re.compile(r"[a-zA-Z][a-zA-Z0-9+.\-]*:")
_SPECIAL: Final = frozenset({"http", "https", "ws", "wss", "ftp", "file"})
_FORBIDDEN_HOST: Final = re.compile(r"[\x00-\x20#%/:<>?@\[\\\]^|\x7f]")


def _ipv4_part(p: str) -> int | None:
    if re.fullmatch(r"0[xX][0-9a-fA-F]*", p):
        return int(p[2:] or "0", 16)
    if re.fullmatch(r"0[0-7]+", p):
        return int(p, 8)
    if re.fullmatch(r"[0-9]+", p):
        return int(p, 10)
    return None


def _whatwg_ipv4(host: str) -> str | None:
    """'' si no es IPv4, la forma canónica si lo es; None si "acaba en número" pero no se lee (URL inválida)."""
    parts = host.split(".")
    if parts[-1] == "" and len(parts) > 1:
        parts = parts[:-1]
    last = parts[-1]
    if not (re.fullmatch(r"[0-9]+", last) or re.fullmatch(r"0[xX][0-9a-fA-F]*", last)):
        return ""
    if len(parts) > 4:
        return None
    nums = [_ipv4_part(p) for p in parts]
    if any(n is None for n in nums):
        return None
    values = [n for n in nums if n is not None]
    if any(n > 255 for n in values[:-1]) or values[-1] >= 256 ** (5 - len(values)):
        return None
    ipv4 = values[-1]
    for k, n in enumerate(values[:-1]):
        ipv4 += n * 256 ** (3 - k)
    return ".".join(str((ipv4 >> s) & 255) for s in (24, 16, 8, 0))


def _parse_url(url: Any) -> _Url | None:
    raw = re.sub(r"^[\x00-\x20]+|[\x00-\x20]+$", "", js_str(url))
    raw = re.sub(r"[\t\n\r]", "", raw)
    if not _SCHEME.match(raw):
        return None
    scheme = raw.split(":", 1)[0].lower()
    if scheme in _SPECIAL:
        raw = raw.replace("\\", "/")
    try:
        u = urlsplit(raw)
        username, password = u.username or "", u.password or ""
        host = u.hostname or ""
        u.port  # noqa: B018 - un puerto no numérico invalida la URL, como en JS
    except ValueError:
        return None
    if scheme in _SPECIAL and scheme != "file":
        if not host:
            return None
        if ":" in host:  # IPv6 literal
            return _Url(f"{scheme}:", username, password, f"[{host}]")
        host = unquote(host, errors="strict") if "%" in host else host
        if not host.isascii():
            try:
                host = host.encode("idna").decode("ascii").lower()
            except UnicodeError:
                return None
        host = host.lower()
        if _FORBIDDEN_HOST.search(host):
            return None
        v4 = _whatwg_ipv4(host)
        if v4 is None:
            return None
        host = v4 or host
    return _Url(f"{scheme}:", username, password, host)


def check_url(url: Any) -> Verdict:  # safety.mjs:456-464
    """web_fetch: public web pages only, so a web page can't steer Sidekick into the user's router or local apps."""
    u = _parse_url(url)
    if u is None:
        return verdict(BLOCK, "That isn't a valid link.")
    if u.protocol not in ("http:", "https:"):
        return verdict(BLOCK, "I only fetch http and https pages.")
    if u.username or u.password:
        return verdict(BLOCK, "Links with passwords in them are blocked.")
    host = re.sub(r"^\[|\]\Z", "", u.hostname)
    if PRIVATE_HOST.fullmatch(u.hostname) or ((re.fullmatch(r"[0-9.]+", host) or ":" in host) and is_private_address(host)):
        return verdict(BLOCK, f"{u.hostname} is on your own computer or network, so I won't fetch it.")
    return verdict(SAFE)


def check_link(url: Any) -> Verdict:  # safety.mjs:477-494 (home=null: la rama file: no aplica)
    """A link the user clicked in a reply: opened in their browser, so web and mail links only (no file:, apps or scripts)."""
    u = _parse_url(url)
    if u is None:
        return verdict(BLOCK, "That isn't a valid link.")
    if u.protocol == "mailto:":
        return verdict(SAFE)
    if u.protocol not in ("http:", "https:"):
        return verdict(BLOCK, "Only web and email links open from a reply.")
    if u.username or u.password:
        return verdict(BLOCK, "Links with passwords in them are blocked.")
    return verdict(SAFE)


def check_draw_action(spec: Mapping[str, Any] | None = None, *, allow_actions: bool = False) -> Verdict:  # safety.mjs:504-523
    """What a draw call may do beyond drawing. kind: 'open', 'photo' and 'favicon', 'type' (only with actions allowed),
    'copy', 'button' (ask sends its words as a new request, open and copy follow the rules above)."""
    spec = spec or {}
    kind, url, text, action = spec.get("kind"), spec.get("url"), spec.get("text"), spec.get("action")
    if kind == "open":
        return check_link(url)
    if kind in ("photo", "favicon"):
        return check_url(url)
    if kind == "type":
        if not allow_actions:
            return verdict(BLOCK, "Typing into apps is switched off (Allow File Edits & Commands).")
        if not u16len(js_str(text if text is not None else "")) or u16len(js_str(text)) > 2000:
            return verdict(BLOCK, "Nothing (or far too much) to type.")
        return verdict(SAFE)
    if kind == "copy":
        ok = u16len(js_str(text if text is not None else "")) and u16len(js_str(text)) <= 10_000
        return verdict(SAFE) if ok else verdict(BLOCK, "Nothing (or far too much) to copy.")
    if kind == "button":
        a = action if isinstance(action, Mapping) else {}
        if a.get("do") == "ask":
            value = a.get("value")
            return verdict(SAFE) if js_trim(js_str(value if value is not None else "")) else verdict(BLOCK, "A button needs words to ask.")
        if a.get("do") == "open":
            return check_link(a.get("value"))
        if a.get("do") == "copy":
            return check_draw_action({"kind": "copy", "text": a.get("value")})
        return verdict(BLOCK, "A button can only ask, open a link or copy.")
    if kind == "handoff":
        return verdict(SAFE)
    return verdict(BLOCK, f"{js_str(kind)} isn't something a drawing can do.")
