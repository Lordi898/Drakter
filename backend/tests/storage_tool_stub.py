"""Sustituto mínimo de `app.tools.spec` (contrato drakter/agente-hermes §1), solo si el real no existe."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import types
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


def install() -> None:
    try:
        found = importlib.util.find_spec("app.tools.spec") is not None
    except ModuleNotFoundError:
        found = False
    if found or "app.tools.spec" in sys.modules:
        return

    class RiskClass(StrEnum):
        READ = "read"
        WRITE = "write"
        CONFIRM = "confirm"

    @dataclass(frozen=True, slots=True)
    class ToolContext:
        turn_id: UUID
        session_id: UUID
        call_id: str
        principal: Literal["agent"]
        state: Any

    @dataclass(frozen=True, slots=True)
    class ToolSpec:
        name: str
        description: str
        domain: str
        args_model: type[BaseModel]
        result_model: type[BaseModel]
        permission: str
        risk: RiskClass
        handler: Callable[..., Any]
        errors: tuple[str, ...] = ()
        idempotent: bool = False
        timeout_s: float = 15.0
        returns_untrusted: bool = False
        audit: Mapping[str, str] = field(default_factory=dict)
        summarize: Callable[[BaseModel], str] | None = None

    class ToolError(Exception):
        def __init__(self, code: str, message: str, retryable: bool = False, details: Any = None) -> None:
            super().__init__(code)
            self.code, self.message, self.retryable, self.details = code, message, retryable, details

    def untrusted_envelope(source_type: str, source_id: str, content: str, *, truncated: bool = False) -> dict:
        return {
            "trust": "untrusted",
            "source_type": source_type,
            "source_id": source_id,
            "retrieved_at": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "truncated": truncated,
            "content": content,
        }

    mod = types.ModuleType("app.tools.spec")
    for obj in (RiskClass, ToolContext, ToolSpec, ToolError, untrusted_envelope):
        setattr(mod, obj.__name__, obj)
    mod.__stub__ = True  # type: ignore[attr-defined]
    sys.modules["app.tools.spec"] = mod
