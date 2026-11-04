"""Silero VAD v6 over onnxruntime, using the model bundled in faster-whisper (no torch)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import numpy as np

from voice.config import VoiceConfig
from voice.contracts import FRAME_SAMPLES, AudioFrame, VoiceError

_CONTEXT = 64
_MODEL_FILE = "silero_vad_v6.onnx"


class SileroVAD:
    name = "silero"

    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._session: Any = None
        self._lock = threading.Lock()
        self._h = np.zeros((1, 1, 128), dtype=np.float32)
        self._c = np.zeros((1, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, _CONTEXT), dtype=np.float32)

    def _model_path(self) -> Path:
        override = self._config.resolved_models_dir / "silero" / _MODEL_FILE
        if override.is_file():
            return override
        try:
            from faster_whisper.utils import get_assets_path
        except ImportError as exc:
            raise VoiceError("dependency_missing", "faster-whisper is not installed (Silero model lives in it)") from exc
        bundled = Path(get_assets_path()) / _MODEL_FILE
        if not bundled.is_file():
            raise VoiceError("model_missing", f"Silero VAD model not found at {bundled}")
        return bundled

    def load(self) -> None:
        if self._session is not None:
            return
        path = self._model_path()
        try:
            import onnxruntime
        except ImportError as exc:
            raise VoiceError("dependency_missing", "onnxruntime is not installed") from exc
        opts = onnxruntime.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        opts.enable_cpu_mem_arena = False
        opts.log_severity_level = 4
        try:
            self._session = onnxruntime.InferenceSession(
                str(path), providers=["CPUExecutionProvider"], sess_options=opts
            )
        except Exception as exc:  # noqa: BLE001 - onnxruntime raises varied types
            raise VoiceError("engine_failed", f"cannot open Silero model: {type(exc).__name__}") from exc
        self.reset()

    def process(self, frame: AudioFrame) -> float:
        if self._session is None:
            raise VoiceError("invalid_request", "SileroVAD.load() was not called")
        pcm = frame.pcm
        if pcm.shape != (FRAME_SAMPLES,):
            raise VoiceError("invalid_request", f"expected {FRAME_SAMPLES} samples")
        x = np.concatenate([self._context, pcm.astype(np.float32, copy=False)[None, :]], axis=1)
        with self._lock:
            try:
                out, self._h, self._c = self._session.run(None, {"input": x, "h": self._h, "c": self._c})
            except Exception as exc:  # noqa: BLE001
                raise VoiceError("engine_failed", f"Silero inference failed: {type(exc).__name__}") from exc
            self._context = x[:, -_CONTEXT:].copy()
        return float(np.clip(out.reshape(-1)[0], 0.0, 1.0))

    def reset(self) -> None:
        with self._lock:
            self._h = np.zeros((1, 1, 128), dtype=np.float32)
            self._c = np.zeros((1, 1, 128), dtype=np.float32)
            self._context = np.zeros((1, _CONTEXT), dtype=np.float32)

    def close(self) -> None:
        self._session = None
