"""Agent permissions: ``agent/configuration/permissions.json``, list ``granted``."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Final

DEFAULT_PERMISSIONS_PATH: Final = (
    Path(__file__).resolve().parents[3] / "agent" / "configuration" / "permissions.json"
)
_GRANT_RE: Final = re.compile(r"^[a-z][a-z0-9_]*\.([a-z][a-z0-9_]*|\*)$")

logger = logging.getLogger("drakter.tools")


class PermissionPolicy:
    """Exact grants plus ``"<domain>.*"``. Whatever is not granted is denied."""

    def __init__(self, granted: Iterable[str] = ()) -> None:
        self._exact: set[str] = set()
        self._domains: set[str] = set()
        for grant in granted:
            if not isinstance(grant, str) or _GRANT_RE.fullmatch(grant) is None:
                raise ValueError(f"invalid permission grant: {grant!r}")
            domain, action = grant.split(".", 1)
            if action == "*":
                self._domains.add(domain)
            else:
                self._exact.add(grant)

    def allows(self, permission: str) -> bool:
        return permission in self._exact or permission.split(".", 1)[0] in self._domains

    @classmethod
    def load(cls, path: Path = DEFAULT_PERMISSIONS_PATH) -> PermissionPolicy:
        """Read the file. If it is missing or invalid, fails closed: nothing is granted."""
        try:
            granted = json.loads(path.read_text(encoding="utf-8"))["granted"]
            if not isinstance(granted, list):
                raise ValueError("'granted' must be a list")
            return cls(granted)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.error(
                "agent permissions unavailable, denying every tool",
                extra={"event": "permissions_load_failed", "reason": type(exc).__name__},
            )
            return cls()
