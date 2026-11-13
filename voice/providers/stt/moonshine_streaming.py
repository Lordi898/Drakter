"""STT streaming con Moonshine (`moonshine-voice==0.1.6`), no segmentado (V-06).

- El `Transcriber` se carga una vez por proceso (`shared.get("moonshine", …)`) desde
  `models/moonshine/download.moonshine.ai/model/<small|tiny>-streaming-es/quantized_26_08_24/`.
  Nunca se llama a `get_model_for_language` (descargaría).
- Solo se alimenta durante el habla: el audio previo al `VADUserStartedSpeakingFrame` se guarda en
  un pre-roll circular y se vuelca al abrir el stream. Un stream nuevo por tramo de VAD.
- La inferencia corre en `asyncio.to_thread`. Los listeners de Moonshine se disparan en ese hilo:
  solo anotan texto, y los frames se empujan desde el bucle (nunca `push_frame` desde el hilo).
- Con `VADUserStoppedSpeakingFrame`: `stream.stop()` y `TranscriptionFrame(finalized=True)`.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from loguru import logger
from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.services.settings import STTSettings
from pipecat.services.stt_service import STTService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601

if TYPE_CHECKING:
    from moonshine_voice import Transcriber

    from voice.config import VoiceConfig
    from voice.ports import Shared

SAMPLE_RATE = 16000
MODEL_SUBDIR = "moonshine/download.moonshine.ai/model/{name}-streaming-es/quantized_26_08_24"
REQUIRED_FILES = ("encoder.ort", "decoder_kv.ort", "tokenizer.bin", "streaming_config.json")


def model_dir(models_dir: Path, name: str) -> Path:
    if name not in ("small", "tiny"):
        raise ValueError(f"stt_model debe ser 'small' o 'tiny', no {name!r}")
    path = Path(models_dir) / MODEL_SUBDIR.format(name=name)
    missing = [f for f in REQUIRED_FILES if not (path / f).is_file()]
    if missing:
        raise FileNotFoundError(f"Falta el modelo Moonshine {name}-streaming-es en {path} ({', '.join(missing)})")
    return path


def load_transcriber(models_dir: Path, name: str, update_interval: float) -> Transcriber:
    from moonshine_voice import ModelArch, Transcriber

    arch = ModelArch.SMALL_STREAMING if name == "small" else ModelArch.TINY_STREAMING
    path = model_dir(models_dir, name)
    logger.info(f"Moonshine: cargando {name}-streaming-es")
    return Transcriber(str(path), arch, update_interval=update_interval)


class MoonshineStreamingSTTService(STTService):
    """STT streaming propio sobre un `Transcriber` compartido; un stream por tramo de habla."""

    def __init__(
        self,
        *,
        transcriber: Transcriber,
        model_name: str,
        update_interval: float = 0.25,
        preroll_ms: int = 500,
        ttfs_p99_latency: float = 0.35,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            sample_rate=SAMPLE_RATE,
            ttfs_p99_latency=ttfs_p99_latency,
            settings=STTSettings(model=f"moonshine-{model_name}-streaming-es", language=Language.ES),
            **kwargs,
        )
        self._transcriber = transcriber
        self._update_interval = update_interval
        self._preroll: deque[bytes] = deque()
        self._preroll_bytes = 0
        self._preroll_max = int(SAMPLE_RATE * 2 * preroll_ms / 1000)
        self._stream: Any = None
        self._lines: dict[int, str] = {}  # line_id -> texto; lo escribe el hilo, lo lee el bucle tras await
        self._last_interim = ""
        self._t_open = 0.0

    def can_generate_metrics(self) -> bool:
        return True

    def language_to_service_language(self, language: Language) -> str | None:
        return "es"

    # --- trabajo en hilo (sin frames) -------------------------------------------------------------

    def _on_event(self, event: Any) -> None:
        line = getattr(event, "line", None)
        if line is not None:
            self._lines[line.line_id] = line.text or ""

    def _text(self) -> str:
        return " ".join(t.strip() for _, t in sorted(self._lines.items()) if t.strip()).strip()

    @staticmethod
    def _floats(audio: bytes) -> list[float]:
        return (np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0).tolist()

    def _open_sync(self, preroll: bytes) -> None:
        stream = self._transcriber.create_stream(update_interval=self._update_interval)
        stream.add_listener(self._on_event)
        stream.start()
        self._stream = stream
        if preroll:
            stream.add_audio(self._floats(preroll), SAMPLE_RATE)

    def _feed_sync(self, audio: bytes) -> str:
        self._stream.add_audio(self._floats(audio), SAMPLE_RATE)
        return self._text()

    def _close_sync(self) -> str:
        stream, self._stream = self._stream, None
        if stream is None:
            return self._text()
        try:
            transcript = stream.stop()
            if transcript is not None:
                for line in transcript.lines:
                    self._lines[line.line_id] = line.text or ""
            return self._text()
        finally:
            stream.close()

    # --- bucle ------------------------------------------------------------------------------------

    def _frame(self, cls: type, text: str, **kw: Any) -> Frame:
        return cls(text, self._user_id, time_now_iso8601(), Language.ES, **kw)

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:
        if self._stream is None:
            self._preroll.append(audio)
            self._preroll_bytes += len(audio)
            while self._preroll_bytes > self._preroll_max and len(self._preroll) > 1:
                self._preroll_bytes -= len(self._preroll.popleft())
            yield None
            return
        text = await asyncio.to_thread(self._feed_sync, audio)
        if text and text != self._last_interim:
            self._last_interim = text
            yield self._frame(InterimTranscriptionFrame, text)

    async def _open(self) -> None:
        if self._stream is not None:  # VAD reabre sin cerrar: se cierra el anterior sin emitir
            await asyncio.to_thread(self._close_sync)
        preroll = b"".join(self._preroll)
        self._preroll.clear()
        self._preroll_bytes = 0
        self._lines = {}
        self._last_interim = ""
        self._t_open = time.monotonic()
        await asyncio.to_thread(self._open_sync, preroll)

    async def _close(self) -> None:
        if self._stream is None:
            return
        t0 = time.monotonic()
        text = await asyncio.to_thread(self._close_sync)
        logger.debug(f"Moonshine: final en {int((time.monotonic() - t0) * 1000)} ms ({len(text)} car.)")
        if text:
            await self.push_frame(self._frame(TranscriptionFrame, text, finalized=True))

    async def _handle_vad_user_started_speaking(self, frame: VADUserStartedSpeakingFrame) -> None:
        await super()._handle_vad_user_started_speaking(frame)
        await self._open()

    async def _handle_vad_user_stopped_speaking(self, frame: VADUserStoppedSpeakingFrame) -> None:
        await super()._handle_vad_user_stopped_speaking(frame)
        await self._close()

    async def cleanup(self) -> None:
        if self._stream is not None:
            stream, self._stream = self._stream, None
            await asyncio.to_thread(stream.close)
        await super().cleanup()


def create(cfg: VoiceConfig, shared: Shared) -> MoonshineStreamingSTTService:
    """Fábrica `stt(cfg, shared)` (plan §4.7)."""
    name = str(getattr(cfg, "stt_model", "small"))
    interval = float(getattr(cfg, "stt_update_interval", 0.25))
    models_dir = Path(shared.models_dir)
    transcriber = shared.get(f"moonshine:{name}", lambda: load_transcriber(models_dir, name, interval))
    return MoonshineStreamingSTTService(
        transcriber=transcriber,
        model_name=name,
        update_interval=interval,
        preroll_ms=int(getattr(cfg, "stt_preroll_ms", 500)),
    )
