"""Hermes plugin: blocks every tool outside Drakter's allowlist.

Defense in depth, not a boundary: it runs inside the untrusted Hermes process.
The list comes from allowed_tools.json, generated next to this file. If it
cannot be read, nothing is allowed and no load proof is written.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_NONCE_ENV = "DRAKTER_GUARD_NONCE"
_PROOF_NAME = "drakter_guard.proof"
_MESSAGE = "Herramienta bloqueada por la política de Drakter."


def _load_allowed() -> frozenset[str]:
    data = json.loads((Path(__file__).parent / "allowed_tools.json").read_text(encoding="utf-8"))
    names = data["allowed"]
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ValueError("allowed must be a list of strings")
    return frozenset(names)


def _write_proof(nonce: str) -> None:
    home = os.environ.get("HERMES_HOME")
    if not home:
        raise RuntimeError("HERMES_HOME is not set")
    path = Path(home) / "run" / _PROOF_NAME
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(nonce)


def register(ctx) -> None:
    allowed = _load_allowed()

    def pre_tool_call(tool_name: str = "", **_: object) -> dict[str, str] | None:
        if tool_name in allowed:
            return None
        return {"action": "block", "message": _MESSAGE}

    ctx.register_hook("pre_tool_call", pre_tool_call)
    nonce = os.environ.pop(_NONCE_ENV, "")
    if nonce:
        _write_proof(nonce)
