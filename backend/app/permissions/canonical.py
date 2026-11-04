"""Canonical JSON, the action hash and the only instant format used here."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any


def canonical_json(value: Any) -> str:
    """Serialize deterministically; NaN and Infinity raise `ValueError`."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def action_hash(action: str, canonical_params: str, target_digest: str) -> str:
    """Bind the action, its exact parameters and the state of its targets."""
    material = "\x00".join((action, canonical_params, target_digest))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def format_instant(moment: datetime) -> str:
    """Fixed width, so that text order equals time order. Rejects naive datetimes."""
    if moment.tzinfo is None:
        raise ValueError("naive datetime")
    moment = moment.astimezone(UTC)
    return f"{moment:%Y-%m-%dT%H:%M:%S}.{moment.microsecond // 1000:03d}Z"


def utc_now() -> datetime:
    return datetime.now(UTC)


def after(moment: datetime, seconds: float) -> datetime:
    return moment + timedelta(seconds=seconds)
