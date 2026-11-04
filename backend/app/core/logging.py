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
    "apikey",
    "cookie",
    "credential",
)
_KW = "|".join(_SENSITIVE)

_BEARER_RE = re.compile(r"(?i)\bBearer\s+[^\s\"',;]+")
_WS_AUTH_RE = re.compile(r"drakter\.auth\.[A-Za-z0-9_\-.~+/=]+")
_SK_RE = re.compile(r"\bsk-[A-Za-z0-9_\-]+")
_KV_RE = re.compile(
    r"(?P<pre>(?P<kq>[\"']?)[\w\-]*(?:" + _KW + r")[\w\-]*(?P=kq)\s*[:=]\s*)"
    r"(?P<val>\"[^\"]*\"|'[^']*'|[^\s,;&}\]\"']+)",
    re.IGNORECASE,
)

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


def _kv_sub(match: re.Match[str]) -> str:
    val = match.group("val")
    quote = val[0] if val[0] in "\"'" else ""
    return f"{match.group('pre')}{quote}{REDACTED}{quote}"


def _redact_text(text: str) -> str:
    text = _mask_registered(text)
    text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
    text = _WS_AUTH_RE.sub(f"drakter.auth.{REDACTED}", text)
    text = _SK_RE.sub(REDACTED, text)
    return _KV_RE.sub(_kv_sub, text)


def _is_sensitive_key(key: object) -> bool:
    lowered = str(key).lower()
    return any(word in lowered for word in _SENSITIVE)


def redact(value: object) -> object:
    """Return a copy of ``value`` with secrets replaced by ``[REDACTED]``."""
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {
            str(k): (REDACTED if _is_sensitive_key(k) else redact(v)) for k, v in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact(v) for v in value]
    if isinstance(value, bytes):
        return _redact_text(value.decode("utf-8", "replace"))
    return value


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
        line = json.dumps(ordered, ensure_ascii=False, default=str)
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

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        for old in list(lg.handlers):
            lg.removeHandler(old)
        lg.propagate = True
        lg.setLevel(numeric)
