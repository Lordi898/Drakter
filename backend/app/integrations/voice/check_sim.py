"""Quick check of the voice orchestrator against a simulated voice process (not a test suite).

    cd backend && python -m app.integrations.voice.check_sim

A fake voice server speaks the IPC of `drakter_contracts.voice_ipc` over a real UDS, and a
runtime stub implements plan §4.6. Prints one line per check and exits 1 on the first failure.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI

from app.events.hub import EventHub
from app.integrations.voice.router import router
from app.integrations.voice.service import VoiceOrchestrator
from app.integrations.voice.settings import VoiceSettings
from app.services import settings as settings_service


class FakeVoice:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.cmds: list[tuple[str, dict[str, Any]]] = []
        self.writer: asyncio.StreamWriter | None = None
        self.connected = asyncio.Event()

    async def start(self) -> None:
        self.server = await asyncio.start_unix_server(self._serve, path=str(self.path))

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.writer = writer
        self.connected.set()
        while line := await reader.readline():
            msg = json.loads(line)
            self.cmds.append((msg["type"], msg["payload"]))
            payload: dict[str, Any] = {}
            if msg["type"] == "rtc.offer":
                payload = {"sdp": "v=0 answer", "type": "answer", "pc_id": "pc-1"}
            elif msg["type"] == "speak.delta":
                payload = {"ignored": False}
            elif msg["type"] == "status":
                payload = {"state": {}, "metrics_last": {"tts_ttfa_ms": 700}}
            reply = {"kind": "ok", "id": msg["id"], "type": msg["type"], "payload": payload}
            writer.write(json.dumps(reply).encode() + b"\n")
            await writer.drain()

    async def evt(self, type: str, payload: dict[str, Any]) -> None:
        assert self.writer is not None
        line = {"kind": "evt", "id": str(uuid4()), "type": type, "payload": payload}
        self.writer.write(json.dumps(line).encode() + b"\n")
        await self.writer.drain()

    def take(self) -> list[tuple[str, dict[str, Any]]]:
        out, self.cmds = self.cmds, []
        return out


class Arbiter:
    def __init__(self) -> None:
        self.signals: list[tuple[str, str | None]] = []

    def signal(self, source: str, state: str | None, *, turn_id: UUID | None = None,
               reason: str | None = None) -> None:
        self.signals.append((source, state))


class RuntimeStub:
    """Plan §4.6, just enough: one turn at a time, deltas paced by `gate`."""

    def __init__(self) -> None:
        self.hub = EventHub()
        self.status_arbiter = Arbiter()
        self.tap: Any = None
        self.session = uuid4()
        self.active: SimpleNamespace | None = None
        self.submitted: list[tuple[str, str]] = []
        self.steered: list[str] = []
        self.gate = asyncio.Event()

    def set_turn_tap(self, tap: Any) -> None:
        self.tap = tap

    async def current_session(self) -> UUID:
        return self.session

    def active_turn(self) -> SimpleNamespace | None:
        return self.active

    async def submit_message(self, session_id: UUID, text: str, client_message_id: UUID | None,
                             *, source: str = "text") -> tuple[UUID, UUID]:
        turn_id = uuid4()
        self.submitted.append((source, text))
        self.active = SimpleNamespace(turn_id=turn_id, session_id=session_id, phase="generating")
        self.tap.on_turn_started(turn_id, session_id, source)
        asyncio.create_task(self._run(turn_id, source))
        return turn_id, uuid4()

    async def _run(self, turn_id: UUID, source: str) -> None:
        self.tap.on_raw_delta(turn_id, "[calm] Hola. ")
        await self.gate.wait()
        self.tap.on_tool_started(turn_id, "tasks_list")
        long = "Frase larga de relleno. " * 30 if source == "text" else "¿Qué tal?"
        self.tap.on_raw_delta(turn_id, long)
        self.tap.on_terminal(turn_id, "completed")
        self.active = None

    async def steer(self, turn_id: UUID, text: str) -> bool:
        self.steered.append(text)
        self.tap.on_steered(turn_id, True)
        return True


def check(ok: bool, what: str) -> None:
    print(("OK   " if ok else "FAIL ") + what)
    if not ok:
        sys.exit(1)


async def settle(t: float = 0.2) -> None:
    await asyncio.sleep(t)


def turn(text: str, overlap: str = "none") -> dict[str, Any]:
    return {"utt_id": str(uuid4()), "text": text, "trigger": "wake", "overlap": overlap,
            "audio_ms": 900, "stt_ms": 120, "eot_ms": 200}


async def main() -> None:
    base = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir())
    rundir = Path(tempfile.mkdtemp(prefix="drakter-wp5-", dir=base))
    voice = FakeVoice(rundir / "voice.sock")
    await voice.start()
    runtime = RuntimeStub()
    events: list[Any] = []
    sub = runtime.hub.subscribe(None, None)

    async def collect() -> None:
        while True:
            events.append(await sub.queue.get())

    asyncio.create_task(collect())
    orch = VoiceOrchestrator(
        VoiceSettings(voice_enabled=False), runtime=runtime,
        data_dir=rundir, runtime_dir=rundir, db_path=rundir / "missing.db",
    )
    await orch.start()
    orch.attach_client_only()
    await asyncio.wait_for(voice.connected.wait(), 5)
    await settle()
    first = voice.take()
    check(first[:1] == [("voice.config", {"tts_enabled": True, "profile": "natural",
                                          "wake_enabled": True, "expression": "llm"})],
          "handshake sends voice.config with the user's settings")

    # 1) voice.user_turn → agent turn; deltas → speak.delta{speech_id}
    await voice.evt("voice.user_turn", turn("hey jarvis qué tengo hoy"))
    await settle()
    check(runtime.submitted == [("voice", "hey jarvis qué tengo hoy")], "user_turn → submit_message(source=voice)")
    # 2) while the agent is busy, a real sentence steers it
    await voice.evt("voice.user_turn", turn("mejor dime solo las de mañana", "agent_busy"))
    await voice.evt("voice.user_turn", turn("vale", "agent_busy"))  # backchannel: dropped
    await settle()
    check(runtime.steered == ["mejor dime solo las de mañana"], "busy: sentence steers, backchannel dropped")
    runtime.gate.set()
    await settle()
    cmds = voice.take()
    kinds = [c[0] for c in cmds]
    opens = [c[1]["speech_id"] for c in cmds if c[0] == "speak.open"]
    deltas = [(c[1]["speech_id"], c[1]["seq"], c[1]["text"]) for c in cmds if c[0] == "speak.delta"]
    check(len(opens) == 2 and opens[1] > opens[0], f"on_steered(True) opens a new speech_id {opens}")
    check(("speak.stop", {"speech_id": opens[0], "reason": "steered"}) in cmds, "speak.stop{steered} on the old speech")
    check(deltas[0] == (opens[0], 0, "[calm] Hola. ") and deltas[1][0] == opens[1],
          "deltas go raw (tags kept) with their speech_id and seq")
    check("speak.flush" in kinds and ("turn.phase" in kinds), "tool_started → speak.flush + turn.phase")
    check(("speak.close", {"speech_id": opens[1], "outcome": "completed"}) in cmds, "terminal → speak.close")
    agent_ttft = orch._metrics_last.get("agent_ttft_ms")
    check(isinstance(agent_ttft, int), f"agent_ttft_ms measured ({agent_ttft} ms)")

    # 3) written turn: read aloud up to speak_max_chars_text, then rest_on_screen
    runtime.gate.clear()
    await runtime.submit_message(runtime.session, "hola", None, source="text")
    runtime.gate.set()
    await settle()
    cmds = voice.take()
    said = sum(len(c[1]["text"]) for c in cmds if c[0] == "speak.delta")
    check(said <= 400 and ("speak.phrase", {"key": "rest_on_screen", "when": "now"}) in cmds,
          f"written turn capped at a sentence end ({said} chars) + rest_on_screen")

    # 4) playback events → hub (no text) + arbiter + heard prefix
    tid = str(uuid4())
    runtime.gate.clear()
    t_id, _ = await runtime.submit_message(runtime.session, "x", None, source="voice")
    await settle()
    sid = [c[1]["speech_id"] for c in voice.take() if c[0] == "speak.open"][0]
    await voice.evt("voice.playback", {"turn_id": str(t_id), "speech_id": sid, "state": "started", "sentence_index": 0})
    await voice.evt("voice.playback", {"turn_id": str(t_id), "speech_id": sid, "state": "interrupted",
                                       "sentence_index": 0, "heard_tail": "Hola", "pending_head": "tienes tres tareas"})
    await settle()
    pb = [e.payload for e in events if e.type == "voice.playback"]
    check(len(pb) == 2 and "heard_tail" not in pb[1], "voice.playback published without heard text")
    check(("voice", "speaking") in runtime.status_arbiter.signals and ("voice", "interrupted") in runtime.status_arbiter.signals,
          "arbiter gets speaking / interrupted")
    prefix = orch.heard.prefix(runtime.session, "voice")
    check(prefix == "[canal: voz]\n[interrumpido tras: «Hola»; pendiente sin decir: «tienes tres tareas»]",
          "heard note in the next prefix")
    check(orch.heard.prefix(runtime.session, "text") is None, "heard note used once")
    runtime.gate.set()
    await settle()
    voice.take()
    del tid

    # 5) speaker off: voice.config + speak.stop{mute}; then no speak.* at all
    await asyncio.to_thread(settings_service.notify_setting_changed, "voice_tts_enabled", "false")
    await settle()
    cmds = voice.take()
    check(("speak.stop", {"reason": "mute"}) in cmds and any(c[0] == "voice.config" and c[1]["tts_enabled"] is False for c in cmds),
          "voice_tts_enabled=false → voice.config + speak.stop{mute}")
    runtime.gate.clear()
    await voice.evt("voice.user_turn", turn("otra pregunta"))
    await settle()
    runtime.gate.set()
    await settle()
    cmds = voice.take()
    check(cmds and not any(c[0].startswith("speak.") for c in cmds), f"muted turn sends no speak.* ({[c[0] for c in cmds]})")

    # 6) TTS fallback → notification.created once
    await voice.evt("voice.tts_fallback", {"from": "fish", "to": "local", "reason": "quota"})
    await voice.evt("voice.tts_fallback", {"from": "fish", "to": "local", "reason": "quota"})
    await settle()
    check(sum(e.type == "notification.created" for e in events) == 1, "tts_fallback → one notification")
    check(all(not e.type.startswith("voice.") or e.type in ("voice.state", "voice.playback", "voice.error") for e in events),
          "no v1 voice.* events published")

    # 7) REST
    app = FastAPI()
    app.include_router(router)
    app.state.voice = orch
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as http:
        r = await http.post("/api/v1/voice/offer", json={"sdp": "v=0 offer", "type": "offer"})
        check(r.status_code == 200 and r.json() == {"sdp": "v=0 answer", "type": "answer", "pc_id": "pc-1"},
              "POST /voice/offer returns the answer")
        r = await http.post("/api/v1/voice/activate", json={"trigger": "hotkey"})
        check(r.status_code == 200 and r.json()["mode"] == "conversation", "POST /voice/activate → conversation")
        check(("mode.set", {"mode": "conversation", "trigger": "hotkey"}) in voice.take(), "activate sends mode.set")
        r = await http.get("/api/v1/voice/status")
        check(r.status_code == 200 and r.json()["metrics_last"]["tts_ttfa_ms"] == 700, "GET /voice/status")

    await orch.stop()
    voice.server.close()
    (rundir / "voice.sock").unlink(missing_ok=True)
    rundir.rmdir()
    print("ALL OK")


if __name__ == "__main__":
    asyncio.run(main())
