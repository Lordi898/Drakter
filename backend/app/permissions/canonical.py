"""Canonical JSON and the hash that binds a confirmation to its action."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any


def canonical_json(value: Any) -> str:
    """Serialize deterministically; NaN and Infinity raise `ValueError`."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def compute_params_hash(tool_name: str, canonical_args: str) -> str:
    """Bind the tool to its exact arguments."""
    material = "\x00".join((tool_name, canonical_args))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.now(UTC)


def after(moment: datetime, seconds: float) -> datetime:
    return moment + timedelta(seconds=seconds)


def encode_cursor(*values: str | int) -> str:
    """Opaque position on (sort field, id)."""
    return base64.urlsafe_b64encode(canonical_json(values).encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> list[Any]:
    try:
        values = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid cursor") from exc
    if not isinstance(values, list):
        raise ValueError("invalid cursor")
    return values
