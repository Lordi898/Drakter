"""Volcado opcional del audio que entra al STT, para diagnosticar la calidad de la transcripción.

Desactivado por defecto: solo con `DRAKTER_VOICE_DUMP_AUDIO=1` (campo `dump_audio`). Es la única
excepción a «ni audio ni transcripciones se guardan», y la activa el usuario a mano:

- Un wav por turno de usuario (16 kHz, s16, mono, tal como lo recibe el STT, con 0,5 s previos al
  VAD) y un `.json` al lado con niveles: RMS, pico, % de muestras recortadas, frecuencia y
  duración. Nunca texto.
- En `<data_dir>/voice/dumps/` (directorio 0700, archivos 0600). Cada volcado borra los de más
  de 24 h; al arrancar también se purga.
- Va entre el VAD y el STT, y solo copia: los frames siguen igual.
"""

from __future__ import annotations

import json
import math
import os
import time
import wave
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Final

import numpy as np
from loguru import logger
from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    UserStoppedSpeakingFrame,
    VADUserStartedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from voice.metrics import ensure_private_dir

if TYPE_CHECKING:
    from voice.config import VoiceConfig

MAX_AGE_S: Final = 24 * 3600
PREROLL_S: Final = 0.5
MAX_TURN_S: Final = 60.0
CLIP: Final = 32700


def purge(directory: Path, max_age_s: float = MAX_AGE_S) -> int:
    """Borra los volcados de más de `max_age_s`. Devuelve cuántos archivos quitó."""
    removed, limit = 0, time.time() - max_age_s
    try:
        entries = list(directory.iterdir())
    except OSError:
        return 0
    for path in entries:
        if path.suffix in (".wav", ".json") and path.is_file() and path.stat().st_mtime < limit:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def levels(pcm: bytes, sample_rate: int) -> dict[str, float | int]:
    x = np.frombuffer(pcm, dtype=np.int16)
    if x.size == 0:
        return {"sample_rate": sample_rate, "duration_s": 0.0}
    f = x.astype(np.float32) / 32768.0
    rms, peak = float(np.sqrt(np.mean(f**2))), float(np.max(np.abs(f)))
    return {
        "sample_rate": sample_rate,
        "duration_s": round(x.size / sample_rate, 2),
        "rms_dbfs": round(20 * math.log10(rms + 1e-9), 1),
        "peak_dbfs": round(20 * math.log10(peak + 1e-9), 1),
        "clip_pct": round(100 * float(np.mean(np.abs(x) >= CLIP)), 3),
        "dc_offset": round(float(np.mean(f)), 4),
    }


def _write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)


class AudioDump(FrameProcessor):
    def __init__(self, directory: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._dir = Path(directory)
        self._preroll: deque[bytes] = deque()
        self._preroll_bytes = 0
        self._chunks: list[bytes] | None = None
        self._rate = 16000
        self._started = 0.0
        ensure_private_dir(self._dir)
        purge(self._dir)

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            self._on_audio(frame)
        elif isinstance(frame, VADUserStartedSpeakingFrame) and self._chunks is None:
            self._chunks = list(self._preroll)
            self._started = time.time()
        elif isinstance(frame, (UserStoppedSpeakingFrame, EndFrame, CancelFrame)):
            self._flush()
        await self.push_frame(frame, direction)

    def _on_audio(self, frame: InputAudioRawFrame) -> None:
        self._rate = frame.sample_rate
        if self._chunks is not None:
            self._chunks.append(frame.audio)
            if time.time() - self._started > MAX_TURN_S:
                self._flush()
            return
        self._preroll.append(frame.audio)
        self._preroll_bytes += len(frame.audio)
        limit = int(self._rate * 2 * PREROLL_S)
        while self._preroll_bytes > limit and len(self._preroll) > 1:
            self._preroll_bytes -= len(self._preroll.popleft())

    def _flush(self) -> None:
        chunks, self._chunks = self._chunks, None
        self._preroll.clear()
        self._preroll_bytes = 0
        if not chunks:
            return
        pcm = b"".join(chunks)
        stem = time.strftime("%Y%m%d-%H%M%S", time.localtime(self._started)) + f"-{int(self._started * 1000) % 1000:03d}"
        try:
            ensure_private_dir(self._dir)
            purge(self._dir)
            wav_path = self._dir / f"{stem}.wav"
            fd = os.open(wav_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as fh, wave.open(fh, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(self._rate)
                w.writeframes(pcm)
            _write_private(self._dir / f"{stem}.json", json.dumps(levels(pcm, self._rate)).encode())
        except (OSError, ValueError) as exc:  # el diagnóstico nunca rompe la voz
            logger.warning(f"AudioDump: no se pudo escribir el volcado ({type(exc).__name__})")


def create(cfg: VoiceConfig) -> AudioDump | None:
    """El procesador si `dump_audio` está activo; si no, `None` (no entra en el pipeline)."""
    if not getattr(cfg, "dump_audio", False):
        return None
    logger.warning(f"Volcado de audio ACTIVO en {cfg.voice_dir / 'dumps'} (se borra a las 24 h)")
    return AudioDump(cfg.voice_dir / "dumps")
