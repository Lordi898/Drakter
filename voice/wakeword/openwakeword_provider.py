"""openWakeWord over ONNX with a user-supplied model only. Never uses pretrained models or downloads."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import numpy as np

from voice.config import VoiceConfig
from voice.contracts import FRAME_SAMPLES, AudioFrame, VoiceError, WakeDetection

_CHUNK = 1280  # 80 ms at 16 kHz, what openWakeWord expects


class OpenWakeWordProvider:
    name = "openwakeword"

    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._model: Any = None
        self._key = ""
        self._buf = np.zeros(0, dtype=np.float32)
        self._lock = threading.Lock()

    def _feature_models(self) -> dict[str, str]:
        """melspectrogram/embedding ONNX: models_dir/openwakeword first, then the package dir."""
        import openwakeword

        names = ("melspectrogram.onnx", "embedding_model.onnx")
        local = self._config.resolved_models_dir / "openwakeword"
        pkg = Path(openwakeword.__file__).parent / "resources" / "models"
        for base in (local, pkg):
            if all((base / n).is_file() for n in names):
                return {
                    "melspec_model_path": str(base / names[0]),
                    "embedding_model_path": str(base / names[1]),
                }
        raise VoiceError(
            "model_missing", f"openWakeWord feature models {names} not found in {local}"
        )

    def load(self) -> None:
        if self._model is not None:
            return
        path = self._config.wakeword_model
        if path is None:
            raise VoiceError("model_missing", "wakeword_model is required: no pretrained model is ever used")
        if not path.is_file() or path.suffix != ".onnx":
            raise VoiceError("model_missing", f"wake word model (.onnx) not found at {path}")
        try:
            from openwakeword.model import Model
        except ImportError as exc:
            raise VoiceError("dependency_missing", "openwakeword is not installed") from exc
        features = self._feature_models()
        try:
            self._model = Model(
                wakeword_models=[str(path)], inference_framework="onnx", **features
            )
        except Exception as exc:  # noqa: BLE001
            raise VoiceError("engine_failed", f"cannot load wake word model: {type(exc).__name__}") from exc
        self._key = path.stem
        self.reset()

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        if self._model is None:
            raise VoiceError("invalid_request", "OpenWakeWordProvider.load() was not called")
        if frame.pcm.shape != (FRAME_SAMPLES,):
            raise VoiceError("invalid_request", f"expected {FRAME_SAMPLES} samples")
        with self._lock:
            self._buf = np.concatenate([self._buf, frame.pcm])
            best = 0.0
            while self._buf.size >= _CHUNK:
                chunk, self._buf = self._buf[:_CHUNK], self._buf[_CHUNK:]
                pcm16 = (np.clip(chunk, -1.0, 1.0) * 32767.0).astype(np.int16)
                try:
                    scores = self._model.predict(pcm16)
                except Exception as exc:  # noqa: BLE001
                    raise VoiceError("engine_failed", f"wake word inference failed: {type(exc).__name__}") from exc
                best = max(best, float(scores.get(self._key, 0.0)))
            if best >= self._config.wakeword_threshold:
                self._reset_locked()
                return WakeDetection(keyword=self._key, score=best)
        return None

    def _reset_locked(self) -> None:
        self._buf = np.zeros(0, dtype=np.float32)
        if self._model is not None:
            self._model.reset()

    def reset(self) -> None:
        with self._lock:
            self._reset_locked()

    def close(self) -> None:
        self._model = None
        self._buf = np.zeros(0, dtype=np.float32)
