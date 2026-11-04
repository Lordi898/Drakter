"""Kokoro TTS (kokoro-onnx, int8). Primary engine; Apache-2.0 code, models read from disk only."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import Any

import numpy as np

from voice.config import VoiceConfig
from voice.contracts import (
    CancelToken,
    PcmChunk,
    TTSCapabilities,
    VoiceError,
    VoiceInfo,
    VoiceParams,
)

MODEL_FILE = "kokoro-v1.0.int8.onnx"
VOICES_FILE = "voices-v1.0.bin"
_LANG = "es"
# Kokoro voice ids start with <lang letter><gender letter>_. Only Spanish ("e") fits lang="es".
_SPANISH_PREFIX = "e"


class KokoroTTS:
    name = "kokoro"
    # Each sentence is synthesised whole; the manager already splits text by sentences.
    capabilities = TTSCapabilities(speed=True, voices=True, streaming=False, intonation=False, emotion=False)

    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._dir = config.resolved_models_dir / "kokoro"
        self._kokoro: Any = None
        self._lock = threading.Lock()  # one inference at a time

    def load(self) -> None:
        if self._kokoro is not None:
            return
        model, voices = self._dir / MODEL_FILE, self._dir / VOICES_FILE
        for path in (model, voices):
            if not path.is_file():
                raise VoiceError("model_missing", f"Kokoro file not found: {path}")
        try:
            import onnxruntime as ort
            from kokoro_onnx import Kokoro
        except ImportError as exc:
            raise VoiceError("dependency_missing", f"kokoro-onnx / onnxruntime not installed: {exc.name}") from exc
        try:
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = self._config.tts_threads
            opts.inter_op_num_threads = 1  # measured best; memory arena stays enabled (lower peak)
            session = ort.InferenceSession(str(model), sess_options=opts, providers=["CPUExecutionProvider"])
            self._kokoro = Kokoro.from_session(session, str(voices))
        except Exception as exc:  # noqa: BLE001 - library errors are heterogeneous
            raise VoiceError("engine_failed", f"Kokoro failed to load: {type(exc).__name__}") from exc

    def _spanish_voice_ids(self) -> list[str]:
        if self._kokoro is None:
            return []
        return [v for v in self._kokoro.get_voices() if v.startswith(_SPANISH_PREFIX)]

    def voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(id=v, language="es-ES", gender={"f": "female", "m": "male"}.get(v[1:2]))
            for v in self._spanish_voice_ids()
        ]

    def synthesize(self, text: str, params: VoiceParams, cancel: CancelToken) -> Iterator[PcmChunk]:
        if cancel.cancelled:
            return
        if self._kokoro is None:
            self.load()
        voice = params.voice or self._config.tts_voice
        if voice not in self._spanish_voice_ids():
            raise VoiceError("invalid_request", f"Unknown Kokoro voice: {voice}")
        if not text.strip():
            return
        try:
            with self._lock:
                audio, rate = self._kokoro.create(text, voice=voice, speed=params.speed, lang=_LANG)
        except Exception as exc:  # noqa: BLE001
            raise VoiceError("engine_failed", f"Kokoro synthesis failed: {type(exc).__name__}") from exc
        if cancel.cancelled:
            return
        pcm = np.ascontiguousarray(audio, dtype=np.float32).reshape(-1)
        if pcm.size:
            yield PcmChunk(pcm=pcm, sample_rate=int(rate))

    def close(self) -> None:
        self._kokoro = None
