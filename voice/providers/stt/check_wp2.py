"""Comprobación rápida de WP2, sin red: `python -m voice.providers.stt.check_wp2 <wav> [--model small|tiny]`.

1. Pasa el wav (castellano) en tiempo real por `VADProcessor(Silero) → MoonshineStreamingSTT` en un
   pipeline real y muestra los parciales y el final (`finalized=True`) con tiempos.
2. Smart Turn v3.2 devuelve una predicción sobre el mismo audio.
3. openWakeWord puntúa los frames (y el `WakeGate` no deja pasar audio en standby).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

SR = 16000
FRAME = 320  # 20 ms, como WebRTC


def load_wav(path: str) -> bytes:
    with wave.open(path) as w:
        assert w.getsampwidth() == 2, "wav de 16 bits"
        rate, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if rate != SR:
        t = np.arange(0, len(x) * SR / rate) * rate / SR
        x = np.interp(t, np.arange(len(x)), x)
    return x.astype(np.int16).tobytes()


@dataclass
class StubShared:
    models_dir: Path
    cache: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, loader):
        if key not in self.cache:
            self.cache[key] = loader()
        return self.cache[key]


@dataclass
class StubCfg:
    stt_model: str = "small"
    turn_stop_secs: float = 3.0
    wake_threshold: float = 0.3


async def run_stt(audio: bytes, shared: StubShared, cfg: StubCfg) -> None:
    from pipecat.frames.frames import (
        EndFrame,
        Frame,
        InputAudioRawFrame,
        InterimTranscriptionFrame,
        TranscriptionFrame,
        VADUserStartedSpeakingFrame,
        VADUserStoppedSpeakingFrame,
    )
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.processors.audio.vad_processor import VADProcessor
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    from voice.providers.stt.moonshine_streaming import create as stt_create
    from voice.providers.vad.silero import create as vad_create

    t0 = time.monotonic()
    t_stop = [0.0]

    def ms() -> int:
        return int((time.monotonic() - t0) * 1000)

    class Sink(FrameProcessor):
        async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
            await super().process_frame(frame, direction)
            if isinstance(frame, VADUserStartedSpeakingFrame):
                print(f"[{ms():6d} ms] VAD inicio")
            elif isinstance(frame, VADUserStoppedSpeakingFrame):
                t_stop[0] = time.monotonic()
                print(f"[{ms():6d} ms] VAD fin")
            elif isinstance(frame, InterimTranscriptionFrame):
                print(f"[{ms():6d} ms] parcial: {frame.text}")
            elif isinstance(frame, TranscriptionFrame):
                lag = int((time.monotonic() - t_stop[0]) * 1000) if t_stop[0] else -1
                print(f"[{ms():6d} ms] FINAL finalized={frame.finalized} lang={frame.language} "
                      f"(+{lag} ms tras VAD fin): {frame.text}")
            await self.push_frame(frame, direction)

    t_load = time.monotonic()
    stt = stt_create(cfg, shared)
    print(f"STT {cfg.stt_model} cargado en {int((time.monotonic() - t_load) * 1000)} ms")
    pipeline = Pipeline([VADProcessor(vad_analyzer=vad_create(cfg)), stt, Sink()])
    task = PipelineTask(pipeline, params=PipelineParams(audio_in_sample_rate=SR), enable_rtvi=False,
                        cancel_on_idle_timeout=False)

    async def feed() -> None:
        await asyncio.sleep(0.3)
        silence = b"\0\0" * SR  # 1 s de silencio delante y detrás
        data = silence + audio + silence
        start = time.monotonic()
        for i in range(0, len(data), FRAME * 2):
            await task.queue_frame(InputAudioRawFrame(audio=data[i:i + FRAME * 2], sample_rate=SR, num_channels=1))
            await asyncio.sleep(max(0.0, start + (i // 2 + FRAME) / SR - time.monotonic()))
        await asyncio.sleep(1.5)
        await task.queue_frame(EndFrame())

    await asyncio.gather(PipelineRunner(handle_sigint=False).run(task), feed())


async def run_smart_turn(audio: bytes, shared: StubShared, cfg: StubCfg) -> None:
    from voice.providers.turn.smart_turn import create

    strategy = create(cfg, shared)
    analyzer = strategy._turn_analyzer  # solo para la comprobación
    analyzer.set_sample_rate(SR)
    for i in range(0, len(audio), FRAME * 2):
        analyzer.append_audio(audio[i:i + FRAME * 2], is_speech=True)
    t = time.monotonic()
    state, metrics = await analyzer.analyze_end_of_turn()
    print(f"Smart Turn: {state.name} en {int((time.monotonic() - t) * 1000)} ms; "
          f"{getattr(metrics, 'probability', metrics)}")


async def run_wake(audio: bytes, shared: StubShared, cfg: StubCfg) -> None:
    from voice.ports import SessionState
    from voice.providers.wake.openwakeword_gate import CHUNK, create

    class Ctl:
        state = SessionState()

        async def set_mode(self, mode: str, trigger: str) -> None:
            print(f"ctl.set_mode({mode!r}, {trigger!r})")
            self.state.mode = mode  # type: ignore[assignment]

    gate = create(cfg, shared, Ctl())
    model = gate._model
    from voice.providers.wake.openwakeword_gate import flush_model

    flush_model(model)
    t = time.monotonic()
    scores = [model.predict(np.frombuffer(audio[i:i + CHUNK * 2], dtype=np.int16))
              for i in range(0, len(audio) - CHUNK * 2, CHUNK * 2)]
    dt = (time.monotonic() - t) / max(1, len(scores)) * 1000
    best = max((max(s.values()) for s in scores), default=0.0)
    print(f"openWakeWord: {len(scores)} frames de 80 ms puntuados ({dt:.1f} ms/frame), máx={best:.3f}, "
          f"modelos={list(scores[0]) if scores else []}")

    # WakeGate en un pipeline real: en standby no pasa audio; al detectar suelta el prebúfer.
    from pipecat.frames.frames import EndFrame, Frame, InputAudioRawFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    ctl = gate._ctl
    ctl.state.mode = "standby"
    passed = [0]

    class Count(FrameProcessor):
        async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
            await super().process_frame(frame, direction)
            if isinstance(frame, InputAudioRawFrame):
                passed[0] += 1
            await self.push_frame(frame, direction)

    task = PipelineTask(Pipeline([gate, Count()]), params=PipelineParams(audio_in_sample_rate=SR),
                        enable_rtvi=False, cancel_on_idle_timeout=False)
    frames = [audio[i:i + FRAME * 2] for i in range(0, len(audio), FRAME * 2)]

    async def feed() -> None:
        await asyncio.sleep(0.3)
        for f in frames:
            await task.queue_frame(InputAudioRawFrame(audio=f, sample_rate=SR, num_channels=1))
            await asyncio.sleep(0.005)
        await asyncio.sleep(0.5)
        await task.queue_frame(EndFrame())

    await asyncio.gather(PipelineRunner(handle_sigint=False).run(task), feed())
    print(f"WakeGate: {len(frames)} frames de entrada, {passed[0]} pasaron; modo final={ctl.state.mode}")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--model", default="small", choices=["small", "tiny"])
    ap.add_argument("--models-dir", default=str(Path.home() / ".local/share/drakter/models"))
    args = ap.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    audio = load_wav(args.wav)
    print(f"wav: {len(audio) / 2 / SR:.2f} s a 16 kHz")
    shared = StubShared(Path(args.models_dir))
    cfg = StubCfg(stt_model=args.model)
    await run_stt(audio, shared, cfg)
    await run_smart_turn(audio, shared, cfg)
    await run_wake(audio, shared, cfg)


if __name__ == "__main__":
    asyncio.run(main())
