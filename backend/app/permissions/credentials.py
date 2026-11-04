"""Credentials of the confirmation path: approver token and one-use approval tokens.

The approver token belongs to Electron main only. The renderer has no way to send it:
`X-Drakter-Approver` is not in the CORS allow-list and any `Origin` is refused here.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Final

from app.core.security import SessionToken

APPROVER_FILE_NAME: Final = "approver.json"
_O_NOFOLLOW: Final = getattr(os, "O_NOFOLLOW", 0)


class ApprovalSigner:
    """Token bound to the row. Single use comes from the atomic `pending` transition.

    The key lives in memory and changes on each boot, which is why every pending
    confirmation expires at startup.
    """

    def __init__(self) -> None:
        self._key = secrets.token_bytes(32)

    def issue(self, action_id: str, tool_name: str, params_hash: str, expires_at: str) -> str:
        material = "\x00".join((action_id, tool_name, params_hash, expires_at))
        mac = hmac.new(self._key, material.encode("utf-8"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(mac).decode("ascii")

    def verify(
        self, token: str, action_id: str, tool_name: str, params_hash: str, expires_at: str
    ) -> bool:
        expected = self.issue(action_id, tool_name, params_hash, expires_at)
        return hmac.compare_digest(expected.encode("ascii"), token.encode("utf-8"))

    def __repr__(self) -> str:
        return "ApprovalSigner(<redacted>)"


def write_approver_file(path: Path, token: SessionToken) -> None:
    """Hand the token to Electron main, which reads the file once and deletes it."""
    payload = json.dumps({"approver_token": token.reveal()}).encode("utf-8")
    path.unlink(missing_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
