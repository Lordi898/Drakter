"""Comprobación de punta a punta del núcleo de voz, sin micrófono, modelos ni red exterior.

Arranca `python -m voice run --null` con un STT simulado, se conecta como haría el backend
(socket IPC) y como haría el renderer (un par WebRTC de aiortc por loopback) y comprueba:

  1. el proceso arranca con proveedores vacíos y anuncia `voice.ready`;
  2. `rtc.offer` con un SDP de aiortc devuelve un answer y la conexión se establece;
  3. un wav enviado por la pista de audio acaba en `voice.user_turn`;
  4. `speak.open/delta/close` produce audio (TTS simulado) y `speak.stop` lo corta;
  5. una segunda oferta (reconexión) monta un pipeline nuevo sin recargar `Shared`.

Uso, desde la raíz del repo:  ~/.local/share/drakter/venvs/voice/bin/python voice/tests/check_pipeline.py [--wav habla.wav]
Imprime PASS/FAIL por paso y sale con 1 si algo falla.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import fractions
import itertools
import json
import os
import shutil
import sys
import tempfile
import time
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FAKE_TEXT = "qué hora es"
RTC_RATE = 48000


# ── STT simulado: lo carga el proceso de voz por `DRAKTER_VOICE_STT=voice.tests.check_pipeline:fake_stt`
def fake_stt(cfg: Any, shared: Any) -> Any:
    from pipecat.frames.frames import TranscriptionFrame, VADUserStoppedSpeakingFrame
    from pipecat.transcriptions.language import Language

    from voice.providers.null import NullSTT

    # Pasa por `shared` como un modelo real: una sola carga por proceso.
    text = shared.get("fake-stt", lambda: FAKE_TEXT)

    class FakeSTT(NullSTT):
        async def process_frame(self, frame: Any, direction: Any) -> None:
            await super().process_frame(frame, direction)
            if isinstance(frame, VADUserStoppedSpeakingFrame):
                stamp = datetime.now(UTC).isoformat()
                await self.push_frame(TranscriptionFrame(text, "", stamp, Language.ES, finalized=True))

    return FakeSTT()


# ── cliente IPC (el papel del backend) ──────────────────────────────────────
class Backend:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader, self._writer = reader, writer
        self._ids = itertools.count(1)
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self.events: list[dict[str, Any]] = []
        self._new_event = asyncio.Event()
        self._task = asyncio.create_task(self._read())

    async def _read(self) -> None:
        while line := await self._reader.readline():
            message = json.loads(line)
            if message["kind"] == "evt":
                self.events.append(message)
                self._new_event.set()
            elif (future := self._pending.pop(message["id"], None)) is not None:
                future.set_result(message)

    async def cmd(self, type_: str, **payload: Any) -> dict[str, Any]:
        request_id = f"c{next(self._ids)}"
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        body = {"kind": "cmd", "id": request_id, "type": type_, "payload": payload}
        self._writer.write(json.dumps(body).encode() + b"\n")
        await self._writer.drain()
        reply = await asyncio.wait_for(future, 20)
        if reply["kind"] != "ok":
            raise RuntimeError(f"{type_} → {reply['payload']}")
        return reply["payload"]

    async def wait_event(self, type_: str, timeout: float = 10.0, since: int = 0, **match: Any) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            for event in self.events[since:]:
                if event["type"] == type_ and all(event["payload"].get(k) == v for k, v in match.items()):
                    return event["payload"]
            self._new_event.clear()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"no llegó {type_} {match or ''}")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._new_event.wait(), remaining)

    def close(self) -> None:
        self._task.cancel()
        self._writer.close()


# ── par WebRTC (el papel del renderer) ──────────────────────────────────────
def load_speech(path: Path | None) -> Any:
    """Audio a 48 kHz mono int16: 1 s de silencio, la voz y 2 s de silencio."""
    import numpy as np

    if path is None:  # sin wav: un tono de 1,2 s que el VAD por energía toma por voz
        t = np.arange(int(1.2 * RTC_RATE)) / RTC_RATE
        speech = (0.3 * 32767 * np.sin(2 * np.pi * 220 * t)).astype(np.int16)
    else:
        with wave.open(str(path), "rb") as wav:
            raw = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
            raw = raw.reshape(-1, wav.getnchannels()).mean(axis=1)
            positions = np.linspace(0, len(raw) - 1, int(len(raw) * RTC_RATE / wav.getframerate()))
            speech = np.interp(positions, np.arange(len(raw)), raw).astype(np.int16)
    silence = np.zeros(RTC_RATE, dtype=np.int16)
    return np.concatenate([silence, speech, silence, silence])


class Renderer:
    """Un `RTCPeerConnection` con micrófono simulado, data channel con ping y medidor de salida."""

    def __init__(self) -> None:
        from aiortc import RTCPeerConnection

        self.pc = RTCPeerConnection()
        self.pc_id: str | None = None
        self.peak = 0.0  # mayor RMS oído del bot desde el último reset
        self._mic = _Microphone()
        self._tasks: list[asyncio.Task[None]] = []

    async def connect(self, backend: Backend) -> dict[str, Any]:
        from aiortc import RTCSessionDescription

        self.pc.addTrack(self._mic)
        channel = self.pc.createDataChannel("drakter")

        @channel.on("open")
        def on_open() -> None:
            self._tasks.append(asyncio.create_task(self._ping(channel)))

        @self.pc.on("track")
        def on_track(track: Any) -> None:
            self._tasks.append(asyncio.create_task(self._listen(track)))

        await self.pc.setLocalDescription(await self.pc.createOffer())  # reúne los candidatos ICE
        offer = self.pc.localDescription
        answer = await backend.cmd("rtc.offer", sdp=offer.sdp, type=offer.type)
        await self.pc.setRemoteDescription(RTCSessionDescription(answer["sdp"], answer["type"]))
        self.pc_id = answer["pc_id"]
        return answer

    async def _ping(self, channel: Any) -> None:
        while channel.readyState == "open":
            channel.send("ping")
            await asyncio.sleep(1.0)

    async def _listen(self, track: Any) -> None:
        import numpy as np

        with contextlib.suppress(Exception):  # la pista termina con MediaStreamError al cerrar
            while True:
                samples = (await track.recv()).to_ndarray().astype(np.float32) / 32768.0
                self.peak = max(self.peak, float(np.sqrt(np.mean(samples * samples))))

    def say(self, samples: Any) -> None:
        self._mic.play(samples)

    async def close(self) -> None:
        for task in self._tasks:
            task.cancel()
        await self.pc.close()


def _microphone_base() -> type:
    from aiortc.mediastreams import MediaStreamTrack

    return MediaStreamTrack


class _Microphone(_microphone_base()):  # type: ignore[misc]
    """Pista de audio a tiempo real: silencio, salvo lo que se le pida reproducir."""

    kind = "audio"

    def __init__(self) -> None:
        super().__init__()
        self._queue: Any = None
        self._pos = 0
        self._pts = 0
        self._start: float | None = None

    def play(self, samples: Any) -> None:
        self._queue, self._pos = samples, 0

    async def recv(self) -> Any:
        import av
        import numpy as np

        size = RTC_RATE // 50  # 20 ms
        if self._start is None:
            self._start = time.monotonic()
        await asyncio.sleep(max(0.0, self._start + self._pts / RTC_RATE - time.monotonic()))
        chunk = np.zeros(size, dtype=np.int16)
        if self._queue is not None:
            part = self._queue[self._pos : self._pos + size]
            chunk[: len(part)] = part
            self._pos += size
            if self._pos >= len(self._queue):
                self._queue = None
        frame = av.AudioFrame.from_ndarray(chunk.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate, frame.pts, frame.time_base = RTC_RATE, self._pts, fractions.Fraction(1, RTC_RATE)
        self._pts += size
        return frame


# ── la comprobación ─────────────────────────────────────────────────────────
class Report:
    def __init__(self) -> None:
        self.failed = 0

    def step(self, ok: bool, label: str, detail: str = "") -> None:
        self.failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""), flush=True)


def _log_events(log_path: Path, event: str) -> list[dict[str, Any]]:
    found = []
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        with contextlib.suppress(ValueError):
            record = json.loads(line)
            if isinstance(record, dict) and record.get("event") == event:
                found.append(record.get("data", {}))
    return found


async def run_checks(wav: Path | None, workdir: Path, report: Report) -> None:
    from voice.channels.webrtc import enable_loopback_candidates

    enable_loopback_candidates()  # el renderer real lo consigue con el switch de Chromium
    env = {
        **os.environ,
        "DRAKTER_RUNTIME_DIR": str(workdir / "run"),
        "DRAKTER_DATA_DIR": str(workdir / "data"),
        "DRAKTER_VOICE_STT": "voice.tests.check_pipeline:fake_stt",
        "PYTHONPATH": str(ROOT),
    }
    log_path = workdir / "voice.log"
    with log_path.open("wb") as log_file:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "voice", "run", "--null", cwd=ROOT, env=env, stderr=log_file
        )
    socket_path = workdir / "run" / "voice.sock"
    backend: Backend | None = None
    peers: list[Renderer] = []
    try:
        for _ in range(100):
            if socket_path.exists() or process.returncode is not None:
                break
            await asyncio.sleep(0.1)
        report.step(socket_path.exists(), "1. `python -m voice run` arranca con proveedores null")
        if not socket_path.exists():
            return
        backend = Backend(*await asyncio.open_unix_connection(str(socket_path)))
        ready = await backend.wait_event("voice.ready")
        state = await backend.wait_event("voice.state")
        report.step(ready["pipecat"] == "1.16.0" and state == {
            "connected": False, "mode": "standby", "tts": "fish", "profile": "natural"
        }, "1. voice.ready y voice.state inicial", f"stt={ready['stt']} tts={ready['tts']}")

        # 2. Oferta de aiortc → answer → conexión.
        first = Renderer()
        peers.append(first)
        answer = await first.connect(backend)
        report.step(answer["type"] == "answer" and "m=audio" in answer["sdp"] and bool(answer["pc_id"]),
                    "2. rtc.offer devuelve un answer", f"loopback={'127.0.0.1' in answer['sdp']}")
        await backend.wait_event("voice.state", connected=True)
        report.step(True, "2. conexión WebRTC establecida (voice.state connected)")

        # 3. Un wav por el micrófono → voice.user_turn. En reposo no debe salir texto.
        speech = load_speech(wav)
        mark = len(backend.events)
        first.say(speech)
        await asyncio.sleep(len(speech) / RTC_RATE + 1.5)
        leaked = [e for e in backend.events[mark:] if e["type"] == "voice.user_turn"]
        report.step(not leaked, "3. en reposo (standby) el audio no produce voice.user_turn")

        await backend.cmd("mode.set", mode="conversation", trigger="ui")
        await backend.wait_event("voice.state", mode="conversation")
        mark = len(backend.events)
        first.say(speech)
        turn = await backend.wait_event("voice.user_turn", timeout=len(speech) / RTC_RATE + 8, since=mark)
        report.step(turn["text"] == FAKE_TEXT and turn["trigger"] == "ui" and turn["overlap"] == "none",
                    "3. el wav produce voice.user_turn",
                    f"audio_ms={turn['audio_ms']} eot_ms={turn['eot_ms']} stt_ms={turn['stt_ms']}")
        phases = [e["payload"]["phase"] for e in backend.events[mark:] if e["type"] == "voice.user_speech"]
        report.step(phases[:2] == ["started", "stopped"], "3. voice.user_speech started/stopped", str(phases))

        # 4. speak.* → audio del TTS simulado; seq idempotente; speak.stop corta.
        await backend.cmd("turn.phase", turn_id="t1", phase="thinking")
        first.peak, mark = 0.0, len(backend.events)
        await backend.cmd("speak.open", turn_id="t1", speech_id=1)
        ack = await backend.cmd("speak.delta", speech_id=1, seq=0, text="[calm] Son las diez ")
        repeated = await backend.cmd("speak.delta", speech_id=1, seq=0, text="repetido")
        await backend.cmd("speak.delta", speech_id=1, seq=1, text="de la mañana.")
        await backend.cmd("speak.close", speech_id=1, outcome="completed")
        await backend.wait_event("voice.playback", since=mark, state="started", speech_id=1)
        await backend.wait_event("voice.playback", since=mark, state="finished", speech_id=1, timeout=15)
        report.step(first.peak > 0.02, "4. speak.open/delta/close produce audio", f"rms máx={first.peak:.3f}")
        report.step(ack == {"ignored": False} and repeated == {"ignored": True},
                    "4. un seq repetido se ignora (ok{ignored:true})")
        await backend.cmd("turn.phase", turn_id="t1", phase="done")

        mark = len(backend.events)
        await backend.cmd("speak.open", turn_id="t2", speech_id=2)
        # El TTS suelta una frase cuando ve empezar la siguiente (o el cierre del speech).
        await backend.cmd("speak.delta", speech_id=2, seq=0, text="Esta frase es larga y se va a cortar a la mitad. ")
        await backend.cmd("speak.delta", speech_id=2, seq=1, text="Y esta otra no llega")
        await backend.wait_event("voice.playback", since=mark, state="started", speech_id=2)
        await backend.cmd("speak.stop", speech_id=2, reason="user")
        cut = await backend.wait_event("voice.playback", since=mark, state="interrupted", speech_id=2)
        late = await backend.cmd("speak.delta", speech_id=2, seq=2, text="esto ya no suena")
        report.step(late == {"ignored": True} and "pending_head" in cut,
                    "4. speak.stop corta y los deltas posteriores se ignoran")

        # 5. Reconexión: oferta nueva sin pc_id → pipeline nuevo; Shared y el modo sobreviven.
        second = Renderer()
        peers.append(second)
        mark = len(backend.events)
        answer2 = await second.connect(backend)
        await backend.wait_event("voice.state", since=mark, connected=True, timeout=15)
        started = _log_events(log_path, "pipeline_started")
        report.step(answer2["pc_id"] != answer["pc_id"] and len(started) == 2,
                    "5. la segunda oferta monta un pipeline nuevo", f"pipelines={len(started)}")
        report.step([s.get("models_loaded") for s in started] == [1, 1],
                    "5. Shared no se recarga en la reconexión", f"cargas={[s.get('models_loaded') for s in started]}")
        status = await backend.cmd("status")
        report.step(status["state"]["connected"] and status["state"]["mode"] == "conversation",
                    "5. SessionState sobrevive a la reconexión", f"mode={status['state']['mode']}")
        second.peak = 0.0
        await backend.cmd("speak.open", turn_id="t3", speech_id=3)
        await backend.cmd("speak.delta", speech_id=3, seq=0, text="Sigo aquí.")
        await backend.cmd("speak.close", speech_id=3, outcome="completed")
        await backend.wait_event("voice.playback", since=mark, state="finished", speech_id=3, timeout=15)
        report.step(second.peak > 0.02, "5. el pipeline nuevo también habla", f"rms máx={second.peak:.3f}")

        await backend.cmd("shutdown")
        await asyncio.wait_for(process.wait(), 15)
        report.step(process.returncode == 0 and not socket_path.exists(), "shutdown ordenado",
                    f"exit={process.returncode}")
    finally:
        for peer in peers:
            with contextlib.suppress(Exception):
                await peer.close()
        if backend is not None:
            backend.close()
        if process.returncode is None:
            process.terminate()
            await process.wait()
        errors = [l for l in log_path.read_text(errors="replace").splitlines() if '"level": "ERROR"' in l]
        report.step(not errors, "sin errores en el log del proceso", f"{len(errors)} errores")
        if report.failed:
            print(f"--- log del proceso de voz ({log_path}) ---")
            print("\n".join(log_path.read_text(errors="replace").splitlines()[-40:]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wav", type=Path, help="wav mono o estéreo de 16 bits con la voz a enviar")
    args = parser.parse_args()
    # Directorio efímero de la comprobación (socket y métricas), fuera de los datos reales.
    base = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir())
    workdir = Path(tempfile.mkdtemp(prefix="drakter-voice-check-", dir=base))
    report = Report()
    try:
        asyncio.run(run_checks(args.wav, workdir, report))
    except Exception as exc:  # noqa: BLE001 - se informa como fallo de la comprobación
        report.step(False, "la comprobación terminó", f"{type(exc).__name__}: {exc}")
    finally:
        if not report.failed:
            shutil.rmtree(workdir, ignore_errors=True)
    print("RESULTADO:", "PASS" if not report.failed else f"FAIL ({report.failed})")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
