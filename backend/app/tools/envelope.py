"""What the agent sees: the outcome of a call and the wrapper for untrusted content."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer

# Bidi controls, zero-width characters and Unicode tags hide text from a human reader.
# ZWJ and ZWNJ stay: they are required by emoji and several scripts.
_HIDDEN_CHARS: Final = dict.fromkeys(
    [
        *range(0x202A, 0x202F),
        *range(0x2066, 0x206A),
        0x200B,
        0x2060,
        0xFEFF,
        *range(0xE0000, 0xE0080),
    ]
)


class ToolFailure(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: list[dict[str, Any]] = Field(default_factory=list)


class ToolOutcome(BaseModel):
    """Result of ``ToolRegistry.dispatch``. ``model_dump()`` is the only thing the agent sees."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok", "error", "confirmation_required"]
    data: dict[str, Any] | None = None
    error: ToolFailure | None = None
    action_id: str | None = None
    summary: str | None = None
    expires_at: str | None = None

    @classmethod
    def ok(cls, data: dict[str, Any]) -> ToolOutcome:
        return cls(status="ok", data=data)

    @classmethod
    def failure(
        cls,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: list[dict[str, Any]] | None = None,
    ) -> ToolOutcome:
        return cls(
            status="error",
            error=ToolFailure(
                code=code, message=message, retryable=retryable, details=details or []
            ),
        )

    @classmethod
    def confirmation(cls, action_id: str, summary: str, expires_at: str) -> ToolOutcome:
        return cls(
            status="confirmation_required",
            action_id=action_id,
            summary=summary,
            expires_at=expires_at,
        )

    @model_serializer
    def _shape(self) -> dict[str, Any]:
        if self.status == "ok":
            return {"status": "ok", "data": self.data if self.data is not None else {}}
        if self.status == "error":
            failure = self.error or ToolFailure(code="tool_internal_error", message="Tool failed.")
            return {"status": "error", "error": failure.model_dump()}
        return {
            "status": "confirmation_required",
            "action_id": self.action_id,
            "summary": self.summary,
            "expires_at": self.expires_at,
        }


def untrusted_envelope(
    source_type: str, source_id: str, content: str, *, truncated: bool = False
) -> dict[str, Any]:
    """Wrap third-party content (F11). A soft layer: the taint in the backend is the control.

    ``content_hash`` covers the original text, so it still matches the source after hidden
    characters are removed.
    """
    return {
        "trust": "untrusted",
        "source_type": source_type,
        "source_id": source_id,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "content_hash": hashlib.sha256(content.encode("utf-8", "surrogatepass")).hexdigest(),
        "truncated": truncated,
        "content": content.translate(_HIDDEN_CHARS),
    }
