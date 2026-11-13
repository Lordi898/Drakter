"""Latencias por turno: tiempos y contadores, nunca texto.

`UserBotLatencyObserver` de Pipecat mide el ciclo usuario → bot; aquí se resume en los campos
de `voice.metrics` (`drakter_contracts.voice_ipc.EvtMetrics`), se escribe una línea en
`metrics.jsonl` y se emite el evento. `agent_ttft_ms` lo mide el backend.
"""

from __future__ import annotations

import json
import logging
import os
import stat
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from pipecat.observers.user_bot_latency_observer import LatencyBreakdown, UserBotLatencyObserver

    from voice.session import Session

log = logging.getLogger("voice.metrics")

# Claves de `LatencyBreakdown.contributions` (Pipecat 1.16.0) → campo de voice.metrics.
_CONTRIBUTIONS: Final[Mapping[str, str]] = {
    "endpointing_wait": "endpointing_ms",
    "turn_detection": "endpointing_ms",
    "transcription": "stt_ms",
    "speech_synthesis": "tts_ttfa_ms",
}


def ensure_private_dir(path: Path) -> None:
    """Create `path` (and missing parents) as 0700, or validate and tighten an existing one.

    Same checks as backend/app/core/config.py, which this process must not import.
    """
    path = Path(path)
    missing: list[Path] = []
    probe = path
    while not probe.exists() and not probe.is_symlink():
        missing.append(probe)
        if probe.parent == probe:
            break
        probe = probe.parent
    for directory in reversed(missing):
        try:
            os.mkdir(directory, 0o700)
        except FileExistsError:
            pass  # lost a race; the leaf is validated below

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"not a safe directory (symlink or not a directory): {path}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISDIR(st.st_mode):
            raise ValueError(f"not a directory: {path}")
        if st.st_uid != os.getuid():
            raise ValueError(f"directory not owned by the current user: {path}")
        if stat.S_IMODE(st.st_mode) != 0o700:
            os.fchmod(fd, 0o700)
    finally:
        os.close(fd)


class MetricsSink:
    """Fichero JSONL 0600 en un directorio 0700. Solo números: los campos son una lista cerrada."""

    _FIELDS: Final = ("ts", "turn_id", "endpointing_ms", "stt_ms", "tts_ttfa_ms", "total_ms", "false_ducks")

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()

    def write(self, record: Mapping[str, Any]) -> None:
        line = json.dumps({k: record[k] for k in self._FIELDS if k in record}, separators=(",", ":"))
        with self._lock:
            ensure_private_dir(self._path.parent)
            fd = os.open(self._path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                if stat.S_IMODE(os.fstat(fd).st_mode) != 0o600:
                    os.fchmod(fd, 0o600)
                os.write(fd, (line + "\n").encode("utf-8"))
            finally:
                os.close(fd)


def summarize(breakdown: LatencyBreakdown) -> dict[str, int]:
    """Reduce el desglose de Pipecat a milisegundos enteros por campo del contrato."""
    out: dict[str, int] = {"total_ms": round(breakdown.total_secs * 1000)}
    for part in breakdown.contributions:
        name = _CONTRIBUTIONS.get(part.key)
        if name:
            out[name] = out.get(name, 0) + round(part.duration_secs * 1000)
    return out


def create_observer(session: Session, sink: MetricsSink) -> UserBotLatencyObserver:
    """Observador de un pipeline: escribe `metrics.jsonl` y emite `voice.metrics`."""
    from pipecat.observers.user_bot_latency_observer import UserBotLatencyObserver

    observer = UserBotLatencyObserver()

    @observer.event_handler("on_latency_breakdown")
    async def on_latency_breakdown(_observer: Any, breakdown: LatencyBreakdown) -> None:
        metrics: dict[str, Any] = summarize(breakdown)
        if session.state.turn_id:
            metrics["turn_id"] = session.state.turn_id
        false_ducks = session.take_false_ducks()
        if false_ducks:
            metrics["false_ducks"] = false_ducks
        session.metrics_last = metrics
        try:
            sink.write({"ts": round(time.time(), 3), **metrics})
        except (OSError, ValueError) as exc:
            log.warning("metrics_write_failed", extra={"data": {"error": type(exc).__name__}})
        await session.emit("voice.metrics", metrics)

    return observer
