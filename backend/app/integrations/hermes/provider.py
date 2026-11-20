"""Provider-neutral agent interface: the rest of the backend only sees this."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

from app.integrations.hermes.events import AgentEvent

ProviderState = Literal["starting", "ready", "offline", "failed"]


@dataclass(frozen=True, slots=True)
class TurnRequest:
    session_id: UUID
    turn_id: UUID
    text: str
    # Ephemeral turn prefixes (channel, heard note, jobs): only for the model's turn prompt,
    # never stored by Drakter nor used for memory retrieval.
    prefix: str = ""
    # Where the user spoke: a voice turn runs without thinking (first delta sooner, LAT-1).
    source: Literal["text", "voice"] = "text"


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    state: ProviderState
    detail: str | None = None  # safe for the GUI
    model: str | None = None


@runtime_checkable
class AgentProvider(Protocol):
    name: str

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def status(self) -> ProviderStatus: ...

    async def create_session(self) -> UUID: ...

    async def close_session(self, session_id: UUID) -> None: ...

    def stream_turn(self, request: TurnRequest) -> AsyncIterator[AgentEvent]:
        """Yield the turn's events. The last one is always terminal."""
        ...

    async def cancel(self, turn_id: UUID) -> None: ...

    async def steer_turn(self, turn_id: UUID, text: str) -> None:
        """Ask the running turn to take `text` as a correction. The answer arrives in the
        turn's stream as `Steered`; nothing arrives if the turn is not running."""
        ...
