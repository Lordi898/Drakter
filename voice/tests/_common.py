"""Shared helpers for the voice measurement scripts. Stdlib + numpy only."""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice.contracts import SAMPLE_RATE, Pcm  # noqa: E402


def meminfo_mb(key: str) -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith(key + ":"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return None


def hwm_mb() -> int | None:
    """Peak resident set of this process (VmHWM)."""
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return None


def loadavg() -> list[float]:
    try:
        return [float(x) for x in Path("/proc/loadavg").read_text().split()[:3]]
    except OSError:
        return []


def read_wav_16k(path: Path) -> Pcm:
    """Mono float32 at 16 kHz from a PCM16 WAV (linear resampling if needed)."""
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise SystemExit(f"{path}: se espera WAV PCM de 16 bits")
        rate, ch = w.getframerate(), w.getnchannels()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if rate != SAMPLE_RATE:
        n = int(round(len(x) * SAMPLE_RATE / rate))
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return np.ascontiguousarray(x, dtype=np.float32)
