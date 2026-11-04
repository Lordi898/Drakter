"""What the agent sees: the outcome of a call and the wrapper for untrusted content."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Final
from uuid import UUID

from drakter_contracts.tools import (
    ToolConfirmationRequired,
    ToolErrorBody,
    ToolFailed,
    ToolOk,
    ToolOutcome,
    UntrustedEnvelope,
)

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


def tool_ok(data: dict[str, Any]) -> ToolOk:
    return ToolOk(data=data)


def tool_failure(
    code: str,
    message: str,
    *,
    retryable: bool = False,
    details: list[dict[str, Any]] | None = None,
) -> ToolFailed:
    return ToolFailed(
        error=ToolErrorBody(
            code=str(code), message=message, retryable=retryable, details=details or []
        )
    )


def tool_confirmation(
    action_id: UUID | str, summary: str, expires_at: datetime | str
) -> ToolConfirmationRequired:
    return ToolConfirmationRequired(action_id=action_id, summary=summary, expires_at=expires_at)


def outcome_code(outcome: ToolOutcome) -> str | None:
    return outcome.error.code if isinstance(outcome, ToolFailed) else None


def untrusted_envelope(
    source_type: str, source_id: str, content: str, *, truncated: bool = False
) -> dict[str, Any]:
    """Wrap third-party content (F11). A soft layer: the taint in the backend is the control.

    ``content_hash`` covers the original text, so it still matches the source after hidden
    characters are removed.
    """
    return UntrustedEnvelope(
        source_type=source_type,
        source_id=source_id,
        retrieved_at=datetime.now(UTC),
        content_hash=hashlib.sha256(content.encode("utf-8", "surrogatepass")).hexdigest(),
        truncated=truncated,
        content=content.translate(_HIDDEN_CHARS),
    ).model_dump(mode="json")
