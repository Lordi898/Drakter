"""Structured JSON logging with secret redaction (see backend/CONTRACT.md)."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Final

from app.core.config import ensure_private_dir

REDACTED: Final = "[REDACTED]"
_SENSITIVE: Final = (
    "authorization",
    "token",
    "secret",
    "password",
    "api_key",
    "api-key",
    "apikey",
    "cookie",
    "credential",
)

_MAX_FIELD: Final = 16 * 1024
_MAX_DEPTH: Final = 8

# Every pattern below is linear: no unbounded quantifier is nested or follows another
# unbounded one, so there is no backtracking blow-up on adversarial input.
_BEARER_RE = re.compile(r"(?i)\bBearer[ \t]{1,16}[^\s\"',;]+")
_WS_AUTH_RE = re.compile(r"drakter\.auth\.[A-Za-z0-9_\-.~+/=]+")
_SK_RE = re.compile(r"\bsk-[A-Za-z0-9_\-]+")
_KEY_RE = re.compile(
    r"(?P<kw>authorization|token|secret|password|api[_\-]key|apikey|cookie|credential)"
    r"[\w\-]{0,64}+(?:\\?[\"'])?[ \t]{0,16}+[:=][ \t]{0,16}+",
    re.IGNORECASE,
)
_HEADER_VALUE_RE = re.compile(r"[^\r\n]*")
_PLAIN_VALUE_RE = re.compile(r"[^\s,;&})\]\"']*")
_HEADER_KEYS: Final = frozenset({"authorization", "cookie"})

_secrets: set[str] = set()
_secrets_lock = threading.Lock()

_STD_ATTRS: Final = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "taskName"}

_HANDLER_TAG: Final = "_drakter_handler"


def register_secret(value: str) -> None:
    """Make every future log line mask this exact value."""
    if value:
        with _secrets_lock:
            _secrets.add(value)


def _mask_registered(text: str) -> str:
    with _secrets_lock:
        secrets = sorted(_secrets, key=len, reverse=True)
    for secret in secrets:
        text = text.replace(secret, REDACTED)
        escaped = json.dumps(secret)[1:-1]
        if escaped != secret:
            text = text.replace(escaped, REDACTED)
    return text


def _value_span(text: str, start: int, kw: str) -> tuple[int, int]:
    """Span of the value that begins at ``start`` (quotes excluded)."""
    if start >= len(text):
        return start, start
    if text[start] == "\\" and text[start + 1 : start + 2] in ('"', "'"):
        closer = text[start : start + 2]
        value_start = start + 2
        end = text.find(closer, value_start)
        return value_start, len(text) if end == -1 else end
    if text[start] in "\"'":
        quote = text[start]
        value_start = start + 1
        end = text.find(quote, value_start)
        while end != -1 and text[end - 1] == "\\":
            end = text.find(quote, end + 1)
        return value_start, len(text) if end == -1 else end
    pattern = _HEADER_VALUE_RE if kw in _HEADER_KEYS else _PLAIN_VALUE_RE
    match = pattern.match(text, start)
    return start, match.end() if match else start


def _redact_key_values(text: str) -> str:
    parts: list[str] = []
    pos = last = 0
    while (match := _KEY_RE.search(text, pos)) is not None:
        value_start, value_end = _value_span(text, match.end(), match.group("kw").lower())
        if value_end <= value_start:
            pos = max(match.end(), value_end)
            continue
        parts.append(text[last:value_start])
        parts.append(REDACTED)
        last = pos = value_end
    parts.append(text[last:])
    return "".join(parts)


def _truncate(text: str) -> str:
    if len(text) > _MAX_FIELD:
        return text[:_MAX_FIELD] + "...[truncated]"
    return text


def _redact_text(text: str) -> str:
    text = _truncate(_mask_registered(text))
    text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
    text = _WS_AUTH_RE.sub(f"drakter.auth.{REDACTED}", text)
    text = _SK_RE.sub(REDACTED, text)
    return _redact_key_values(text)


def _is_sensitive_key(key: object) -> bool:
    lowered = str(key).lower()
    return any(word in lowered for word in _SENSITIVE)


def _redact(value: object, depth: int) -> object:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, bytes):
        return _redact_text(value[:_MAX_FIELD].decode("utf-8", "replace"))
    if depth >= _MAX_DEPTH and isinstance(value, (dict, list, tuple, set, frozenset)):
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return {
            str(k): (REDACTED if _is_sensitive_key(k) else _redact(v, depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        if len(items) == 2:
            name = items[0].decode("latin-1") if isinstance(items[0], bytes) else items[0]
            if isinstance(name, str) and _is_sensitive_key(name):
                return [_redact(items[0], depth + 1), REDACTED]
        return [_redact(v, depth + 1) for v in items]
    return value


def redact(value: object) -> object:
    """Return a copy of ``value`` with secrets replaced by ``[REDACTED]``."""
    return _redact(value, 0)


def _json_default(value: object) -> str:
    """Fallback for non-JSON objects: their text is redacted too."""
    try:
        return _redact_text(str(value))
    except Exception:  # noqa: BLE001 - never let logging raise
        return "<unprintable>"


class JsonFormatter(logging.Formatter):
    """One JSON object per line; redaction runs on the final text."""

    def format(self, record: logging.LogRecord) -> str:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - never let logging raise
            message = f"{record.msg!r} {record.args!r}"
        payload: dict[str, Any] = {}
        for key, val in record.__dict__.items():
            if key in _STD_ATTRS or key.startswith("_"):
                continue
            payload[key] = REDACTED if _is_sensitive_key(key) else redact(val)
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc_info"] = _redact_text(self.formatException(record.exc_info))
        if record.stack_info:
            payload["stack_info"] = _redact_text(self.formatStack(record.stack_info))
        payload.update(
            ts=datetime.fromtimestamp(record.created, UTC).isoformat(),
            level=record.levelname,
            logger=record.name,
            message=_redact_text(message),
        )
        ordered = {k: payload.pop(k) for k in ("ts", "level", "logger", "message")}
        ordered.update(payload)
        line = json.dumps(ordered, ensure_ascii=False, default=_json_default)
        return _mask_registered(line)


class _PrivateRotatingFileHandler(RotatingFileHandler):
    """Rotating file handler whose files (current and rotated) are always 0600."""

    def _open(self):  # type: ignore[no-untyped-def]
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.baseFilename, flags, 0o600)
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(fd, 0o600)
            return os.fdopen(fd, self.mode, encoding=self.encoding, errors=self.errors)
        except BaseException:
            os.close(fd)
            raise

    def rotate(self, source: str, dest: str) -> None:
        super().rotate(source, dest)
        try:
            os.chmod(dest, 0o600)
        except OSError:
            pass


def configure_logging(level: str, logs_dir: Path) -> None:
    """Route root and uvicorn loggers to stderr and ``logs_dir/backend.log``. Idempotent."""
    numeric = logging.getLevelNamesMapping().get(str(level).upper())
    if numeric is None:
        raise ValueError(f"invalid log level: {level!r}")
    ensure_private_dir(logs_dir)

    formatter = JsonFormatter()
    stream = logging.StreamHandler(sys.stderr)
    file_handler = _PrivateRotatingFileHandler(
        Path(logs_dir) / "backend.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    new_handlers = [stream, file_handler]
    for handler in new_handlers:
        handler.setFormatter(formatter)
        handler.setLevel(numeric)
        setattr(handler, _HANDLER_TAG, True)

    root = logging.getLogger()
    for old in [h for h in root.handlers if getattr(h, _HANDLER_TAG, False)]:
        root.removeHandler(old)
        old.close()
    for handler in new_handlers:
        root.addHandler(handler)
    root.setLevel(numeric)

    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        for old in list(lg.handlers):
            lg.removeHandler(old)
        # The access line carries the query string: it must go nowhere.
        lg.propagate = name != "uvicorn.access"
        lg.setLevel(numeric)

    # Uvicorn activa el log de acceso si este logger alcanza algún handler, y ese log
    # incluye la consulta de cada petición.
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False
