"""Sequenced event bus. `publish` is the only place that assigns `seq`."""

from __future__ import annotations

import asyncio
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, Literal
from uuid import UUID, uuid4

from drakter_contracts.events import EVENTS, EventEnvelope, SystemResyncRequired
from pydantic import BaseModel

BUFFER_SIZE: Final = 500
CLIENT_QUEUE_SIZE: Final = 256
CLOSE: Final = object()

ResyncReason = Literal["buffer_overflow", "boot_changed", "client_lagging"]


@dataclass(eq=False, slots=True)
class Subscription:
    """One client: `replay` is sent first, then the bounded live queue."""

    hub: EventHub
    replay: list[EventEnvelope]
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[Any] = field(default_factory=lambda: asyncio.Queue(CLIENT_QUEUE_SIZE + 2))

    def deliver(self, envelope: EventEnvelope) -> None:
        """Called from any thread, in `seq` order."""
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self.loop:
            self._enqueue(envelope)
        elif not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self._enqueue, envelope)

    def _enqueue(self, envelope: EventEnvelope) -> None:
        if self.queue.qsize() >= CLIENT_QUEUE_SIZE:
            # A slow client loses its queue, told why; the ring buffer or REST catch it up.
            self.hub.unsubscribe(self)
            while not self.queue.empty():
                self.queue.get_nowait()
            self.queue.put_nowait(self.hub.resync_notice("client_lagging"))
            self.queue.put_nowait(CLOSE)
            return
        self.queue.put_nowait(envelope)

    def close(self) -> None:
        self.hub.unsubscribe(self)


class EventHub:
    def __init__(self, buffer_size: int = BUFFER_SIZE) -> None:
        self.boot_id: UUID = uuid4()
        # Reentrant: a lagging client unsubscribes itself from inside `publish`.
        self._lock = threading.RLock()
        self._buffer: deque[EventEnvelope] = deque(maxlen=buffer_size)
        self._subscribers: set[Subscription] = set()
        self._seq = 0

    def publish(
        self, type: str, payload: BaseModel, *, correlation_id: str | None = None
    ) -> EventEnvelope:
        """Validate against the event catalog and fan out. Publish only after COMMIT."""
        model = EVENTS[type]
        checked = payload if isinstance(payload, model) else model.model_validate(payload.model_dump())
        body = checked.model_dump(mode="json")
        with self._lock:
            self._seq += 1
            envelope = self._envelope(self._seq, type, body, correlation_id)
            self._buffer.append(envelope)
            for subscriber in tuple(self._subscribers):
                subscriber.deliver(envelope)
        return envelope

    def subscribe(self, after_seq: int | None, boot_id: UUID | None) -> Subscription:
        """Replay and registration are atomic: no event falls between them."""
        loop = asyncio.get_running_loop()
        with self._lock:
            subscription = Subscription(hub=self, replay=self._replay(after_seq, boot_id), loop=loop)
            self._subscribers.add(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        with self._lock:
            self._subscribers.discard(subscription)

    def _replay(self, after_seq: int | None, boot_id: UUID | None) -> list[EventEnvelope]:
        if boot_id is not None and boot_id != self.boot_id:
            return [self.resync_notice("boot_changed")]
        if after_seq is None:
            return []
        if after_seq > self._seq:
            # Only a previous backend run can have handed out that number.
            return [self.resync_notice("boot_changed")]
        oldest = self._buffer[0].seq if self._buffer else self._seq + 1
        if after_seq + 1 < oldest:
            return [self.resync_notice("buffer_overflow")]
        return [event for event in self._buffer if event.seq > after_seq]

    def resync_notice(self, reason: ResyncReason) -> EventEnvelope:
        """Private to one client, so it repeats the last `seq` instead of taking a new one."""
        body = SystemResyncRequired(reason=reason).model_dump(mode="json")
        return self._envelope(self._seq, "system.resync_required", body, None)

    def _envelope(
        self, seq: int, type: str, payload: dict[str, Any], correlation_id: str | None
    ) -> EventEnvelope:
        return EventEnvelope(
            event_id=uuid4(),
            seq=seq,
            boot_id=self.boot_id,
            timestamp=datetime.now(UTC),
            type=type,
            correlation_id=correlation_id,
            payload=payload,
        )
