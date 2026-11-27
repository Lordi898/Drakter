"""Comprobación breve del modo flotante en la voz (docs/floating/CONTRACT.md §10), sin micrófono ni red.

Arranca `python -m voice run` con proveedores vacíos (TTS de tonos) y un STT simulado que siempre
oye «modo flotante», y se conecta como el backend (IPC) y como el renderer (aiortc por loopback):

  1. dos `speak.beat` seguidos y luego `speak.open` de la respuesta del mismo turno suenan en orden,
     uno detrás de otro y sin `interrupted`;
  2. la voz del usuario encima de un beat (barge-in) lo corta, emite `interrupted` y descarta el
     beat que esperaba en cola;
  3. «modo flotante» dicho en voz alta emite `voice.local_command{ui_floating_on}` sin turno.

Uso, desde la raíz del repo, con el Python del venv de voz:
    python voice/tests/check_beats.py
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice.tests.check_pipeline import RTC_RATE, Backend, Renderer, Report, load_speech  # noqa: E402

SAID = "modo flotante"


def fake_stt(cfg: Any, shared: Any) -> Any:
    """STT simulado: al acabar cada tramo de voz, «modo flotante»."""
    from pipecat.frames.frames import TranscriptionFrame, VADUserStoppedSpeakingFrame
    from pipecat.transcriptions.language import Language

    from voice.providers.null import NullSTT

    class FakeSTT(NullSTT):
        async def process_frame(self, frame: Any, direction: Any) -> None:
            await super().process_frame(frame, direction)
            if isinstance(frame, VADUserStoppedSpeakingFrame):
                stamp = datetime.now(UTC).isoformat()
                await self.push_frame(TranscriptionFrame(SAID, "", stamp, Language.ES, finalized=True))

    return FakeSTT()


def playback(backend: Backend, since: int) -> list[tuple[int, str]]:
    return [
        (e["payload"]["speech_id"], e["payload"]["state"])
        for e in backend.events[since:]
        if e["type"] == "voice.playback" and e["payload"]["state"] != "sentence_done"
    ]


async def run(workdir: Path, report: Report) -> None:
    from voice.channels.webrtc import enable_loopback_candidates

    enable_loopback_candidates()
    env = {
        **os.environ,
        "DRAKTER_RUNTIME_DIR": str(workdir / "run"),
        "DRAKTER_DATA_DIR": str(workdir / "data"),
        "DRAKTER_VOICE_NULL": "1",
        "DRAKTER_VOICE_STT": "voice.tests.check_beats:fake_stt",
        # Los contratos de este checkout (el venv puede apuntar a otro).
        "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "contracts" / "python"))),
    }
    log_path = workdir / "voice.log"
    with log_path.open("wb") as log_file:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "voice", "run", cwd=ROOT, env=env, stderr=log_file
        )
    socket_path = workdir / "run" / "voice.sock"
    backend: Backend | None = None
    peer: Renderer | None = None
    try:
        for _ in range(100):
            if socket_path.exists() or process.returncode is not None:
                break
            await asyncio.sleep(0.1)
        if not socket_path.exists():
            report.step(False, "el proceso de voz arranca")
            return
        backend = Backend(*await asyncio.open_unix_connection(str(socket_path)))
        await backend.wait_event("voice.ready")
        peer = Renderer()  # salida medida en memoria: nada suena por los altavoces
        await peer.connect(backend)
        await backend.wait_event("voice.state", connected=True)
        await backend.cmd("mode.set", mode="conversation", trigger="ui")

        # 1. beat, beat, respuesta: FIFO del turno, sin cortes.
        await backend.cmd("turn.phase", turn_id="t1", phase="executing", tool="draw")
        mark = len(backend.events)
        peer.peak = 0.0
        a = await backend.cmd("speak.beat", turn_id="t1", speech_id=10, guide_id="g1", beat=1,
                              text="Primero, pulsa aquí en Archivo.")
        b = await backend.cmd("speak.beat", turn_id="t1", speech_id=11, guide_id="g1", beat=2,
                              text="[calm] Luego, en Exportar.")
        await backend.cmd("speak.open", turn_id="t1", speech_id=12)
        await backend.cmd("speak.delta", speech_id=12, seq=0, text="Listo, ")
        await backend.cmd("speak.delta", speech_id=12, seq=1, text="ya lo tiene.")
        await backend.cmd("speak.close", speech_id=12, outcome="completed")
        await backend.wait_event("voice.playback", since=mark, speech_id=12, state="finished", timeout=30)
        order = playback(backend, mark)
        expected = [(10, "started"), (10, "finished"), (11, "started"), (11, "finished"),
                    (12, "started"), (12, "finished")]
        report.step(a == b == {"ignored": False}, "1. speak.beat devuelve ok{ignored:false}")
        report.step(order == expected and peer.peak > 0.02,
                    "1. dos beats y la respuesta suenan en orden y sin cortarse", str(order))
        await backend.cmd("turn.phase", turn_id="t1", phase="done")

        # 2. Barge-in encima de un beat: lo corta, `interrupted`, y el beat en cola no suena.
        speech = load_speech(None)
        await asyncio.sleep(1.0)
        mark = len(backend.events)
        await backend.cmd("speak.beat", turn_id="t2", speech_id=20, guide_id="g2", beat=1,
                          text="Este beat es bastante largo para que dé tiempo a interrumpirlo.")
        await backend.cmd("speak.beat", turn_id="t2", speech_id=21, guide_id="g2", beat=2,
                          text="Y este no debería sonar.")
        await backend.wait_event("voice.playback", since=mark, speech_id=20, state="started", timeout=10)
        peer.say(speech)
        await backend.wait_event("voice.playback", since=mark, speech_id=20, state="interrupted", timeout=10)
        await asyncio.sleep(len(speech) / RTC_RATE + 2.0)
        order = playback(backend, mark)
        report.step((20, "interrupted") in order and not any(sid == 21 for sid, _ in order),
                    "2. el barge-in corta el beat (interrupted) y vacía la cola", str(order))

        # 3. «modo flotante» → voice.local_command{ui_floating_on}, sin voice.user_turn.
        cmd = next((e["payload"] for e in backend.events[mark:] if e["type"] == "voice.local_command"), None)
        if cmd is None:
            mark = len(backend.events)
            peer.say(speech)
            cmd = await backend.wait_event("voice.local_command", since=mark, timeout=10)
        turns = [e for e in backend.events[mark:] if e["type"] == "voice.user_turn"]
        report.step(cmd["command"] == "ui_floating_on" and not turns,
                    "3. «modo flotante» emite voice.local_command{ui_floating_on} sin turno", str(cmd))

        await backend.cmd("shutdown")
        await asyncio.wait_for(process.wait(), 15)
    finally:
        if peer is not None:
            with contextlib.suppress(Exception):
                await peer.close()
        if backend is not None:
            backend.close()
        if process.returncode is None:
            process.terminate()
            await process.wait()
        errors = [line for line in log_path.read_text(errors="replace").splitlines() if '"level": "ERROR"' in line]
        report.step(not errors, "sin errores en el log del proceso", f"{len(errors)} errores")
        if report.failed:
            print("\n".join(log_path.read_text(errors="replace").splitlines()[-40:]))


def main() -> int:
    base = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir())
    workdir = Path(tempfile.mkdtemp(prefix="drakter-voice-beats-", dir=base))
    report = Report()
    try:
        asyncio.run(run(workdir, report))
    except Exception as exc:  # noqa: BLE001
        report.step(False, "la comprobación terminó", f"{type(exc).__name__}: {exc}")
    finally:
        if not report.failed:
            shutil.rmtree(workdir, ignore_errors=True)
    print("RESULTADO:", "PASS" if not report.failed else f"FAIL ({report.failed})")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
