"""Hardware-free check of the whole voice turn. Prints PASS/FAIL per step.

No microphone, no models, no network: fake STT/TTS/VAD/capture are injected into the
VoiceManager together with NullSink. Covers: full turn, interrupt, cancel, late deltas
after an interrupt, and `mic.set false` really closing the capture.

The VoiceManager API is not part of the frozen contract in code, only its commands and events
(CONTRACT.md). All the coupling is in `ManagerAdapter`: adapt it there if the signatures differ.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402,F401  (sets sys.path)

import numpy as np  # noqa: E402

from voice.audio.null import NullSink  # noqa: E402
from voice.config import VoiceConfig  # noqa: E402
from voice.contracts import (  # noqa: E402
    FRAME_SAMPLES,
    AudioFrame,
    CancelToken,
    PcmChunk,
    TranscriptSegment,
    TTSCapabilities,
    VoiceError,
    VoiceInfo,
    VoiceParams,
)

# ---- doubles ---------------------------------------------------------------------------------


class FakeSTT:
    name = "fake_stt"

    def load(self) -> None: ...
    def close(self) -> None: ...

    def transcribe(self, audio, *, language, cancel: CancelToken) -> Iterator[TranscriptSegment]:
        yield TranscriptSegment("hola drakter", 0.0, 1.0)


class FakeTTS:
    name = "fake_tts"
    capabilities = TTSCapabilities(speed=True, voices=False, streaming=False)

    def __init__(self) -> None:
        self.spoken: list[str] = []

    def load(self) -> None: ...
    def close(self) -> None: ...
    def voices(self) -> list[VoiceInfo]:
        return [VoiceInfo("fake", "es-ES")]

    def synthesize(self, text: str, params: VoiceParams, cancel: CancelToken) -> Iterator[PcmChunk]:
        self.spoken.append(text)
        for _ in range(4):  # 4 x 250 ms
            if cancel.cancelled:
                return
            yield PcmChunk(np.zeros(6000, dtype=np.float32), 24000)


class FakeVAD:
    name = "fake_vad"

    def load(self) -> None: ...
    def reset(self) -> None: ...
    def close(self) -> None: ...
    def process(self, frame: AudioFrame) -> float:
        return 1.0 if float(np.abs(frame.pcm).max()) > 0.01 else 0.0


class FakeCapture:
    """Emits a loud frame every 32 ms while active, like a mic with someone talking."""

    name = "fake_capture"

    def __init__(self) -> None:
        self.starts = 0
        self.stops = 0
        self._active = False
        self._thread: threading.Thread | None = None

    @property
    def active(self) -> bool:
        return self._active

    def start(self, on_frame: Callable[[AudioFrame], None], on_error: Callable[[VoiceError], None]) -> None:
        if self._active:
            return
        self._active = True
        self.starts += 1

        def loop() -> None:
            pcm = np.full(FRAME_SAMPLES, 0.2, dtype=np.float32)
            while self._active:
                on_frame(AudioFrame(pcm, time.perf_counter_ns()))
                time.sleep(0.032)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._active = False
        self.stops += 1
        if self._thread:
            self._thread.join(1.0)


# ---- adapter to VoiceManager -----------------------------------------------------------------


class ManagerAdapter:
    """Builds the manager by constructor-parameter name and exposes cmd(name, **args) + events."""

    def __init__(self) -> None:
        from voice.manager import VoiceManager  # raises ImportError if not written yet

        self.events: list[tuple[str, dict[str, Any]]] = []
        self.capture, self.stt, self.tts = FakeCapture(), FakeSTT(), FakeTTS()
        cfg = VoiceConfig(audio_backend="null", vad_silence_ms=300)
        pool: dict[str, Any] = {
            "config": cfg, "stt": self.stt, "tts": self.tts, "vad": FakeVAD(), "wakeword": None,
            "capture": self.capture, "sink": NullSink(), "emit": self._emit, "on_event": self._emit,
            "events": self._emit, "publish": self._emit,
        }
        params = inspect.signature(VoiceManager).parameters
        kwargs = {k: v for k, v in pool.items() if k in params}
        missing = [p for p in params.values() if p.default is p.empty and p.name not in kwargs
                   and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]
        if missing:
            raise RuntimeError(f"adaptar ManagerAdapter: parámetros sin cubrir {[p.name for p in missing]}")
        self.mgr = VoiceManager(**kwargs)

    def _emit(self, *a: Any, **kw: Any) -> None:
        # Accept (name, payload) or a single dict/object; stay permissive.
        if len(a) == 2 and isinstance(a[0], str):
            self.events.append((a[0], dict(a[1])))
        elif a and isinstance(a[0], dict) and "name" in a[0]:
            self.events.append((a[0]["name"], dict(a[0].get("payload", {}))))

    async def start(self) -> None:
        r = getattr(self.mgr, "start", None)
        if r:
            res = r()
            if inspect.isawaitable(res):
                await res

    async def stop(self) -> None:
        for n in ("shutdown", "close", "stop"):
            r = getattr(self.mgr, n, None)
            if r:
                res = r()
                if inspect.isawaitable(res):
                    await res
                return

    async def cmd(self, name: str, **args: Any) -> Any:
        for n in ("handle_command", "handle", "execute", "command"):
            f = getattr(self.mgr, n, None)
            if f:
                res = f(name, args)
                return await res if inspect.isawaitable(res) else res
        raise RuntimeError("adaptar ManagerAdapter.cmd: el gestor no expone handle_command/handle/execute/command")

    def names(self) -> list[str]:
        return [n for n, _ in self.events]

    async def wait_event(self, name: str, timeout: float = 5.0) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if name in self.names():
                return True
            await asyncio.sleep(0.02)
        return False


# ---- checks ----------------------------------------------------------------------------------

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))


async def run() -> None:
    a = ManagerAdapter()
    await a.start()
    st = await a.cmd("status")
    check("arranca con el micrófono apagado y la captura cerrada",
          not a.capture.active and not _get(st, "mic_enabled", False), str(_get(st, "state", "?")))

    await a.cmd("mic.set", enabled=True)
    await a.cmd("listen.start")
    await asyncio.sleep(0.4)
    check("listen.start abre la captura", a.capture.active)
    await a.cmd("listen.stop")
    check("turno: transcripción completada", await a.wait_event("voice.transcription_completed"))
    turn = next((p.get("turn_id") for n, p in a.events if n == "voice.transcription_completed"), "t1")
    await a.cmd("speak", turn_id=turn, text="Hola. Esto es una prueba. ", final=False)
    await a.cmd("speak", turn_id=turn, text="Tercera frase.", final=True)
    check("turno: empieza la reproducción", await a.wait_event("voice.playback_started"))
    check("turno: termina la reproducción", await a.wait_event("voice.playback_stopped", 10.0))
    check("turno: voice.metrics emitido", await a.wait_event("voice.metrics", 3.0))

    # interrupt + late delta must stay silent
    before = len(a.tts.spoken)
    await a.cmd("listen.start")
    await asyncio.sleep(0.1)
    await a.cmd("listen.cancel")
    check("listen.cancel descarta sin transcribir", "voice.listening_stopped" in a.names())
    a.events.clear()
    await a.cmd("speak", turn_id="t2", text="Una frase larga que se va a cortar. Otra más. ", final=False)
    await a.wait_event("voice.playback_started")
    await a.cmd("interrupt", reason="user")
    check("interrupt emite playback_interrupted", await a.wait_event("voice.playback_interrupted", 3.0))
    spoken_after_interrupt = len(a.tts.spoken)
    r = await a.cmd("speak", turn_id="t2", text="Delta tardío. ", final=True)
    await asyncio.sleep(0.5)
    check("delta tardío del turno interrumpido no suena",
          len(a.tts.spoken) == spoken_after_interrupt and bool(_get(r, "ignored", False)),
          f"sintetizadas {len(a.tts.spoken) - before} antes de cortar")
    try:
        await a.cmd("interrupt")
        idem = True
    except Exception:  # noqa: BLE001
        idem = False
    check("interrupt repetido no falla (idempotente)", idem)

    # mic.set false closes capture for real
    await a.cmd("listen.start")
    await asyncio.sleep(0.2)
    await a.cmd("mic.set", enabled=False)
    await asyncio.sleep(0.2)
    check("mic.set false deja la captura cerrada", not a.capture.active)
    starts = a.capture.starts
    await asyncio.sleep(0.5)
    check("nada reabre la captura tras mic.set false", a.capture.starts == starts and not a.capture.active)
    await a.stop()


def _get(obj: Any, key: str, default: Any) -> Any:
    if isinstance(obj, dict):
        res = obj.get("result", obj)
        return res.get(key, default) if isinstance(res, dict) else default
    return getattr(obj, key, default)


def main() -> int:
    try:
        import voice.manager  # noqa: F401
    except ImportError as exc:
        print(f"NO COMPROBADO: voice.manager no existe todavía ({exc}). El script está escrito contra el contrato.")
        return 3
    try:
        asyncio.run(asyncio.wait_for(run(), 60))
    except Exception as exc:  # noqa: BLE001
        check("ejecución sin excepción", False, f"{type(exc).__name__}: {exc}")
    bad = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(bad)} PASS, {len(bad)} FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
