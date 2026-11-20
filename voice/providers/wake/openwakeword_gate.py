"""Palabra de activación (V-16): `WakeGate`, una puerta de AUDIO con `openwakeword==0.4.0`.

- En `standby` (con `wake_enabled`) no deja pasar audio: lo guarda en un prebúfer circular de 2 s y
  puntúa cada 80 ms. Al superar `cfg.wake_threshold` llama a `ctl.set_mode("conversation", "wake")`
  y suelta el prebúfer, de modo que el STT oye «jarvis …» y el puente confirma el texto.
- NO mira texto: la confirmación («jarvis» / «hey jarvis» al inicio) la hace el puente.
- En `conversation`, o con `wake_enabled=false`, deja pasar todo.
- Ignora las detecciones mientras `state.bot_speaking` (el TTS no debe autoactivarse).
- La inferencia corre en un único hilo propio; el modelo se carga una vez por proceso.

CPU en reposo (DECISIONS «CPU-1»): puntuar cada 80 ms costaba ~17 % de un núcleo con el micro
callado. Ahora:
- Con el micro por debajo de `cfg.wake_energy_dbfs` (y 1 s después del último sonido) no se
  puntúa; el audio sigue entrando en el prebúfer.
- Al volver el sonido se puntúan de una vez los 2 s del prebúfer (renuevan entera la ventana del
  modelo, ~2 s), así que el arranque de «hey jarvis» no se pierde, y se sigue en bloques de 160 ms.
  Con varios bloques, `Model.predict` (0.4.0) puntúa cada ventana de 80 ms y devuelve el máximo.

Modelos en `models/openwakeword/`: `melspectrogram.onnx`, `embedding_model.onnx` y uno o varios
`<nombre>.onnx` de `cfg.wake_models` (por defecto `hey_jarvis_v0.1`).
"""

from __future__ import annotations

import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from loguru import logger
from pipecat.frames.frames import Frame, InputAudioRawFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

if TYPE_CHECKING:
    from openwakeword.model import Model

    from voice.config import VoiceConfig
    from voice.ports import Ctl, Shared

SAMPLE_RATE = 16000
CHUNK = 1280  # 80 ms, lo que espera openWakeWord
BLOCK = CHUNK * 2  # 160 ms por inferencia mientras hay sonido
PREBUFFER_S = 2.0
HANG_S = 1.0  # se sigue puntuando este tiempo tras el último bloque con sonido
DEFAULT_MODELS = ("hey_jarvis_v0.1",)
# Un hilo para todas las conexiones: el modelo es compartido y no admite llamadas a la vez.
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wake")


def model_paths(models_dir: Path, names: list[str] | tuple[str, ...]) -> dict[str, Any]:
    base = Path(models_dir) / "openwakeword"
    paths = {
        "wakeword_model_paths": [str(base / (n if n.endswith(".onnx") else f"{n}.onnx")) for n in names],
        "melspec_onnx_model_path": str(base / "melspectrogram.onnx"),
        "embedding_onnx_model_path": str(base / "embedding_model.onnx"),
    }
    for p in [*paths["wakeword_model_paths"], paths["melspec_onnx_model_path"], paths["embedding_onnx_model_path"]]:
        if not Path(p).is_file():
            raise FileNotFoundError(f"Falta el modelo de openWakeWord: {p}")
    return paths


def load_model(models_dir: Path, names: list[str] | tuple[str, ...]) -> Model:
    from openwakeword.model import Model

    return Model(**model_paths(models_dir, names))


def flush_model(model: Model) -> None:
    """Vacía el contexto de audio (≈2 s de silencio) y el búfer de predicciones.

    Sin esto, al volver a `standby` la primera predicción vería aún el «hey jarvis» anterior.
    """
    model.predict(np.zeros(CHUNK * 25, dtype=np.int16))
    model.reset()


class WakeGate(FrameProcessor):
    """Puerta de audio por palabra de activación. Solo actúa sobre `InputAudioRawFrame` aguas abajo."""

    def __init__(
        self, *, model: Model, ctl: Ctl, threshold: float, energy_dbfs: float = -50.0, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._ctl = ctl
        self._threshold = threshold
        self._energy = 32768.0 * 10 ** (energy_dbfs / 20)  # RMS mínimo en muestras int16
        self._hot = 0  # muestras que quedan por puntuar tras el último sonido
        self._cold = True  # sin puntuar: al volver el sonido se recupera el prebúfer
        self._prebuf: deque[InputAudioRawFrame] = deque()
        self._prebuf_bytes = 0
        self._prebuf_max = int(SAMPLE_RATE * 2 * PREBUFFER_S)
        self._pending = b""  # audio aún sin puntuar (< 80 ms)
        self._was_gating = False
        self.last_scores: dict[str, float] = {}

    def _gating(self) -> bool:
        st = self._ctl.state
        return st.wake_enabled and st.mode == "standby"

    def _predict_sync(self, audio: bytes) -> dict[str, float]:
        scores = self._model.predict(np.frombuffer(audio, dtype=np.int16))
        return {k: float(v) for k, v in scores.items()}

    async def _run(self, fn: Any, arg: Any) -> Any:
        return await asyncio.get_running_loop().run_in_executor(_EXECUTOR, fn, arg)

    async def _reset(self) -> None:
        self._prebuf.clear()
        self._prebuf_bytes = 0
        self._pending = b""
        self._hot, self._cold = 0, True
        await self._run(flush_model, self._model)

    def _loud(self, audio: bytes) -> bool:
        samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32)
        return bool(samples.size) and float(np.sqrt(np.mean(samples * samples))) >= self._energy

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if not isinstance(frame, InputAudioRawFrame) or direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        gating = self._gating()
        if gating and not self._was_gating:
            await self._reset()  # se vuelve a reposo: contexto limpio
        self._was_gating = gating
        if not gating:
            await self.push_frame(frame, direction)
            return

        self._prebuf.append(frame)
        self._prebuf_bytes += len(frame.audio)
        while self._prebuf_bytes > self._prebuf_max and len(self._prebuf) > 1:
            self._prebuf_bytes -= len(self._prebuf.popleft().audio)

        if self._loud(frame.audio):
            self._hot = int(HANG_S * SAMPLE_RATE)
        elif self._hot > 0:
            self._hot -= len(frame.audio) // 2
        if self._hot <= 0:  # callado: no se puntúa
            self._cold, self._pending = True, b""
            return
        if self._cold:  # vuelve el sonido: se puntúa todo el prebúfer (incluye este frame)
            self._cold = False
            self._pending = b"".join(f.audio for f in self._prebuf)
            step = CHUNK * 2
        else:
            self._pending += frame.audio
            step = BLOCK * 2
        n = (len(self._pending) // step) * step
        if not n:
            return
        chunk, self._pending = self._pending[:n], self._pending[n:]
        self.last_scores = await self._run(self._predict_sync, chunk)
        best = max(self.last_scores.items(), key=lambda kv: kv[1], default=(None, 0.0))
        if best[1] < self._threshold or self._ctl.state.bot_speaking:
            return

        logger.info(f"WakeGate: {best[0]} ({best[1]:.2f})")
        await self._ctl.set_mode("conversation", "wake")
        frames = list(self._prebuf)
        self._prebuf.clear()
        self._prebuf_bytes = 0
        self._pending = b""
        self._hot, self._cold = 0, True
        self._was_gating = False
        for f in frames:  # el STT oye la palabra y lo que siga
            await self.push_frame(f, direction)


def create(cfg: VoiceConfig, shared: Shared, ctl: Ctl) -> WakeGate:
    """Fábrica `wake(cfg, shared, ctl)` (plan §4.7)."""
    names = tuple(getattr(cfg, "wake_models", None) or DEFAULT_MODELS)
    models_dir = Path(shared.models_dir)
    model = shared.get("openwakeword:" + ",".join(names), lambda: load_model(models_dir, names))
    return WakeGate(
        model=model,
        ctl=ctl,
        threshold=float(getattr(cfg, "wake_threshold", 0.3)),
        energy_dbfs=float(getattr(cfg, "wake_energy_dbfs", -50.0)),
    )
