"""Per-turn latency metrics. Timings and lengths only: text never gets in here."""

from __future__ import annotations

import json
import os
import stat
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Final

MARKS: Final = (
    "wake",
    "listen_start",
    "speech_start",
    "speech_end",
    "stt_start",
    "stt_first_segment",
    "stt_end",
    "text_received",
    "tts_start",
    "tts_first_audio",
    "playback_start",
    "playback_end",
)
NOTES: Final = frozenset({"audio_s", "stt_provider", "stt_model", "tts_provider", "tts_audio_s", "tts_synth_s"})

_NS_PER_MS: Final = 1_000_000


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


def _rss_mb() -> float | None:
    try:
        with open("/proc/self/status", encoding="ascii", errors="replace") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except (OSError, ValueError, IndexError):
        pass
    return None


def _loadavg() -> list[float] | None:
    try:
        return [round(v, 2) for v in os.getloadavg()]
    except OSError:
        return None


class TurnMetrics:
    """Marks are written from several threads, so all access takes the lock."""

    def __init__(self, turn_id: str) -> None:
        self.turn_id = turn_id
        self._marks: dict[str, int] = {}
        self._notes: dict[str, float | int | str] = {}
        self._lock = threading.Lock()

    def mark(self, name: str, at_ns: int | None = None) -> None:
        """Record `name` once. `at_ns` is for callers holding the real instant (a frame, the player)."""
        if name not in MARKS:
            raise ValueError(f"unknown metric mark: {name}")
        with self._lock:
            if name not in self._marks:
                self._marks[name] = time.perf_counter_ns() if at_ns is None else at_ns

    def note(self, name: str, value: float | int | str) -> None:
        if name not in NOTES:
            raise ValueError(f"unknown metric note: {name}")
        with self._lock:
            self._notes[name] = value

    def _span_ms(self, start: str, end: str) -> float | None:
        a, b = self._marks.get(start), self._marks.get(end)
        return None if a is None or b is None else (b - a) / _NS_PER_MS

    def _ratio(self, numerator: object, denominator: object) -> float | None:
        if not isinstance(numerator, int | float) or not isinstance(denominator, int | float):
            return None
        return numerator / denominator if denominator > 0 else None

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            notes = dict(self._notes)
            stt_ms = self._span_ms("stt_start", "stt_end")
            raw: dict[str, float | None] = {
                "stt_ms": stt_ms,
                "stt_rtf": None if stt_ms is None else self._ratio(stt_ms / 1000, notes.get("audio_s")),
                "tts_first_audio_ms": self._span_ms("tts_start", "tts_first_audio"),
                "tts_rtf": self._ratio(notes.get("tts_synth_s"), notes.get("tts_audio_s")),
                "response_gap_ms": self._span_ms("speech_end", "playback_start"),
            }
        spans = {name: round(value, 3) for name, value in raw.items() if value is not None}
        return {
            "turn_id": self.turn_id,
            "spans_ms": spans,
            "notes": notes,
            "rss_mb": _rss_mb(),
            "loadavg": _loadavg(),
        }


class MetricsSink:
    """JSONL file, 0600, in a 0700 directory. Only the fields of snapshot() are ever written."""

    _FIELDS: Final = ("turn_id", "spans_ms", "notes", "rss_mb", "loadavg")

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()

    def write(self, snapshot: Mapping[str, object]) -> None:
        line = json.dumps({k: snapshot.get(k) for k in self._FIELDS}, separators=(",", ":"), allow_nan=False)
        with self._lock:
            ensure_private_dir(self._path.parent)
            flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW
            fd = os.open(self._path, flags, 0o600)
            try:
                if stat.S_IMODE(os.fstat(fd).st_mode) != 0o600:
                    os.fchmod(fd, 0o600)
                os.write(fd, (line + "\n").encode("utf-8"))
            finally:
                os.close(fd)
