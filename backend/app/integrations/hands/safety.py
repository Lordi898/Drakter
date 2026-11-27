"""Backend barrier of the hands: RISKY classification, secret redaction and what `open_target` may open.

Ports of Roamies `safety.mjs` (`checkUrl`, `isPrivateAddress`, `checkOpen`'s RUNNABLE, `redactArgs`).
"""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any, Final
from urllib.parse import urlsplit

from drakter_contracts.floating import (
    StepChoose,
    StepClick,
    StepClickAt,
    StepClickText,
    StepFill,
    StepFocus,
    StepHover,
    StepKey,
    StepScroll,
    StepSet,
    StepType,
    StepWait,
)
from drakter_contracts.hands_ipc import AtspiControl

from app.integrations.hands.lists import is_risky_combo, is_risky_text, risky_kind

# ── RISKY ────────────────────────────────────────────────────────────────────


def step_risk(step: Any, controls: dict[int, AtspiControl] | None = None) -> str | None:
    """The risky word (or key) of a step, or None. `controls`: the turn's read, to name `id` targets."""
    controls = controls or {}
    texts: list[str | None] = []
    if isinstance(step, StepClickText):
        texts = [step.text, step.near]
    elif isinstance(step, (StepClick, StepFocus)):
        c = controls.get(step.id)
        texts = [c.name if c else None]
    elif isinstance(step, StepChoose):
        c = controls.get(step.id) if step.id is not None else None
        texts = [step.option, c.name if c else None]
    elif isinstance(step, StepSet):
        c = controls.get(step.id)
        texts = [c.name if c else None]
    elif isinstance(step, StepKey):
        return step.combo if is_risky_combo(step.combo) else None
    for t in texts:
        if is_risky_text(t):
            return risky_kind(t)
    return None


def args_risk(args: Any) -> str | None:
    """For `confirm_if`: risky by the text or the combo the model wrote (ids are checked in the handler)."""
    for i, step in enumerate(getattr(args, "steps", []) or []):
        if (kind := step_risk(step)) is not None:
            return f"Paso {i + 1} arriesgado: {kind}."
    return None


def step_phrase(step: Any, controls: dict[int, AtspiControl] | None = None) -> str:
    """Spanish description of a step for the confirmation and the trail. Typed text: only its length."""
    controls = controls or {}

    def name(cid: int | None) -> str:
        c = controls.get(cid) if cid is not None else None
        return f"«{c.name[:30]}»" if c and c.name else f"el control #{cid}"

    if isinstance(step, StepClickText):
        return f"{'doble ' if step.double else ''}clic en «{step.text[:30]}»"
    if isinstance(step, StepClick):
        return f"{'doble ' if step.double else ''}clic en {name(step.id)}"
    if isinstance(step, StepClickAt):
        return f"clic en ({round(step.x)}, {round(step.y)}) de la captura"
    if isinstance(step, StepFill):
        where = f"«{step.field[:30]}»" if step.field else name(step.id)
        return f"escribir {len(step.text)} caracteres en {where}"
    if isinstance(step, StepChoose):
        return f"elegir «{step.option[:30]}»"
    if isinstance(step, StepType):
        return f"escribir {len(step.text)} caracteres"
    if isinstance(step, StepKey):
        return f"pulsar {step.combo}" + (f" ×{step.repeat}" if step.repeat > 1 else "")
    if isinstance(step, StepScroll):
        return "desplazar " + {"up": "arriba", "down": "abajo", "left": "a la izquierda", "right": "a la derecha"}[step.direction]
    if isinstance(step, StepHover):
        return f"pasar el ratón por «{step.text[:30]}»" if step.text else f"pasar el ratón por {name(step.id)}"
    if isinstance(step, StepFocus):
        return f"enfocar {name(step.id)}"
    if isinstance(step, StepSet):
        return f"cambiar {name(step.id)}"
    if isinstance(step, StepWait):
        return "esperar"
    return "paso"


# ── redaction (read_window) ──────────────────────────────────────────────────


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


_SECRET_PATTERNS: Final = [
    re.compile(r"-----BEGIN [A-Z ]*-----[\s\S]*?(-----END [A-Z ]*-----|$)"),
    re.compile(r"\b(sk|pk|rk)-(ant-|proj-|live-|test-)?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"),  # JWT
    re.compile(r"(?i)\b(password|passwd|pwd|contraseña|token|secret|api[_-]?key|access[_-]?key)\s*[=:]\s*\S+"),
    re.compile(r"\b[0-9a-fA-F]{32,}\b"),
    re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{32,}={0,2}(?![A-Za-z0-9+/=])"),
]
_CARD: Final = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
MASK: Final = "[oculto]"


def redact(text: str | None) -> tuple[str, int]:
    """Text with keys, tokens, JWTs, long hex/base64 and Luhn-valid card numbers replaced. (text, count)."""
    if not text:
        return text or "", 0
    count = 0

    def sub(_m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return MASK

    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub(sub, out)

    def card(m: re.Match[str]) -> str:
        nonlocal count
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn(digits):
            count += 1
            return MASK
        return m.group(0)

    out = _CARD.sub(card, out)
    return out, count


# ── open_target ──────────────────────────────────────────────────────────────

_PRIVATE_HOST: Final = re.compile(
    r"^(localhost|.*\.local|.*\.internal|.*\.localdomain|.*\.home\.arpa|0\.0\.0\.0|127\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+|"
    r"192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|169\.254\.\d+\.\d+|\[?::1\]?|\[?f[cd][0-9a-f:]*\]?|"
    r"\[?fe80:[0-9a-f:]*\]?)$",
    re.IGNORECASE,
)


def is_private_address(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.strip("[]").split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return not addr.is_global or addr.is_multicast


def check_url(url: str) -> str | None:
    """None if it may open, else the reason. http, https or mailto; no credentials; no local network."""
    try:
        u = urlsplit(url.strip())
    except ValueError:
        return "enlace no válido"
    scheme = (u.scheme or "").lower()
    if scheme == "mailto":
        return None if u.path and "@" in u.path else "enlace de correo no válido"
    if scheme not in ("http", "https"):
        return "solo se abren enlaces http, https o mailto"
    if u.username or u.password:
        return "los enlaces con contraseña están bloqueados"
    host = (u.hostname or "").strip()
    if not host:
        return "enlace sin servidor"
    if _PRIVATE_HOST.match(host) or is_private_address(host):
        return "apunta a este equipo o a la red local"
    return None


def check_url_dns(url: str) -> str | None:
    """`check_url` plus the addresses the host resolves to (a public name can point at 127.0.0.1)."""
    if (reason := check_url(url)) is not None:
        return reason
    u = urlsplit(url.strip())
    if (u.scheme or "").lower() == "mailto":
        return None
    try:
        infos = socket.getaddrinfo(u.hostname or "", None)
    except (OSError, UnicodeError):
        return None  # does not resolve: the browser will fail on its own
    if any(is_private_address(str(info[4][0])) for info in infos):
        return "apunta a este equipo o a la red local"
    return None


# `checkOpen`'s RUNNABLE: scripts, installers and apps that would run when opened.
RUNNABLE: Final = re.compile(
    r"\.(app|command|sh|bash|zsh|fish|tool|terminal|scpt|scptd|applescript|workflow|action|pkg|mpkg|dmg|jar|py|pyw|rb|"
    r"pl|php|js|mjs|cjs|exe|bat|cmd|ps1|shortcut|mobileconfig|kext|plugin|prefPane|saver|desktop|appimage|deb|rpm|"
    r"run|bin|flatpakref|flatpak|snap|msi|msix|appx|appxbundle|vbs|vbe|wsf|wsh|hta|scr|cpl|lnk|reg|msc|pif|jse|"
    r"psm1|fileloc|webloc|inetloc|service|timer|so)/?$",
    re.IGNORECASE,
)


def runnable(path: str, mode: int) -> bool:
    return RUNNABLE.search(path) is not None or bool(mode & 0o111)
