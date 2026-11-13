"""Comprobación rápida de WP4 con frames sintéticos sobre un `UserTurnProcessor` real (sin red ni audio).

    python -m voice.conversation.check_conversation
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import numpy as np
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    InterimTranscriptionFrame,
    InterruptionFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.tests.utils import SleepFrame, run_test
from pipecat.turns.user_stop.speech_timeout_user_turn_stop_strategy import (
    SpeechTimeoutUserTurnStopStrategy,
)
from pipecat.turns.user_turn_processor import UserTurnProcessor
from pipecat.turns.user_turn_strategies import UserTurnStrategies

from voice.conversation import duck, idle, start_strategy
from voice.ports import SessionState

CFG = SimpleNamespace(
    bargein_min_words=3, bargein_decide_ms=300, duck_gain=0.25, idle_nudge_s=0.1, followup_s=0.3
)


class FakeCtl:
    def __init__(self, **state) -> None:
        self.state = SessionState(**state)
        self.calls: list[tuple] = []
        self.ducks: list[bool] = []

    async def emit(self, type, payload):
        self.calls.append(("emit", type, payload))

    async def interrupt(self, reason):
        self.calls.append(("interrupt", reason))

    async def play_phrase(self, key, when="now"):
        self.calls.append(("phrase", key))

    def set_duck(self, on):
        self.ducks.append(on)

    async def set_mode(self, mode, trigger):
        self.state.mode = mode
        self.calls.append(("mode", mode, trigger))


def interim(t):
    return InterimTranscriptionFrame(text=t, user_id="u", timestamp="")


def final(t):
    return TranscriptionFrame(text=t, user_id="u", timestamp="", finalized=True)


S = SleepFrame(sleep=0.05)


async def scenario(name, frames, *, bot=True, **state):
    ctl = FakeCtl(**state)
    [strategy] = start_strategy.create(CFG, ctl)
    utp = UserTurnProcessor(
        user_turn_strategies=UserTurnStrategies(
            start=[strategy], stop=[SpeechTimeoutUserTurnStopStrategy()]
        )
    )
    turns = []

    @utp.event_handler("on_user_turn_started")
    async def _(_p, _s):
        turns.append(strategy.turn_overlap)

    head = [BotStartedSpeakingFrame(), S] if bot else []
    down, _ = await run_test(utp, frames_to_send=[*head, *frames, SleepFrame(sleep=0.5)])
    interruptions = sum(isinstance(f, InterruptionFrame) for f in down)
    print(f"- {name}: turnos={turns} interrupciones={interruptions} duck={ctl.ducks} "
          f"llamadas={ctl.calls} false_ducks={strategy.false_ducks}")
    return turns, interruptions, ctl, strategy


async def main() -> None:
    print("Barge-in sobre UserTurnProcessor real:")
    t, i, ctl, _ = await scenario(
        "bot callado, VAD abre turno", [VADUserStartedSpeakingFrame(), S], bot=False
    )
    assert t == ["none"] and ctl.ducks == []

    t, i, ctl, _ = await scenario(
        "«para» corta sin turno", [VADUserStartedSpeakingFrame(), S, interim("para"), S]
    )
    assert t == [] and ("interrupt", "user") in ctl.calls and ctl.ducks == [True, False]
    assert any(c[:2] == ("emit", "voice.local_command") and c[2]["command"] == "stop_speech" for c in ctl.calls)

    t, i, ctl, _ = await scenario(
        "«ajá» no corta",
        [VADUserStartedSpeakingFrame(), S, interim("ajá"), S, VADUserStoppedSpeakingFrame(), final("ajá"), S],
    )
    assert t == [] and i == 0 and not any(c[0] == "interrupt" for c in ctl.calls) and ctl.ducks == [True, False]

    t, i, ctl, _ = await scenario(
        "tres palabras nuevas abren e interrumpen",
        [VADUserStartedSpeakingFrame(), S, interim("oye"), S, interim("oye cambia eso"), S],
        spoken_tail="mañana tienes clase de matemáticas a las nueve",
    )
    assert t == ["bot_speaking"] and i == 1 and ctl.ducks == [True, False]

    t, i, ctl, _ = await scenario(
        "el eco del TTS no abre",
        [VADUserStartedSpeakingFrame(), S, interim("tienes clase de matemáticas"), S,
         VADUserStoppedSpeakingFrame(), final("tienes clase de matemáticas a las"), S],
        spoken_tail="mañana tienes clase de matemáticas a las nueve",
    )
    assert t == [] and i == 0 and ctl.ducks == [True, False]

    t, i, ctl, st = await scenario(
        "ruido sin texto restaura el volumen",
        [VADUserStartedSpeakingFrame(), SleepFrame(sleep=0.1), VADUserStoppedSpeakingFrame(), SleepFrame(sleep=0.5)],
    )
    assert t == [] and i == 0 and ctl.ducks == [True, False] and st.false_ducks == 1

    print("DuckMixer (rampa de 30 ms a 16 kHz):")
    m = duck.create(CFG, None)
    await m.start(16000)
    tone = (np.ones(160, dtype=np.int16) * 10000).tobytes()  # 10 ms
    assert await m.mix(tone) == tone
    m.set_duck(True)
    levels = [int(np.frombuffer(await m.mix(tone), dtype=np.int16)[-1]) for _ in range(5)]
    m.set_duck(False)
    up = [int(np.frombuffer(await m.mix(tone), dtype=np.int16)[-1]) for _ in range(4)]
    print(f"- bajando: {levels}  subiendo: {up}")
    assert levels[-1] == 2500 and levels[0] > levels[1] > levels[2] and up[-1] == 10000

    print("Idle:")
    ctl = FakeCtl(mode="conversation", awaiting_answer=True)
    w = idle.IdleWatcher(ctl, CFG.idle_nudge_s, CFG.followup_s)
    await w.on_idle()
    await w.on_idle()
    print(f"- con pregunta, dos avisos: {ctl.calls}")
    assert ctl.calls == [("phrase", "idle_nudge"), ("mode", "standby", "followup")]
    ctl = FakeCtl(mode="conversation")
    w = idle.IdleWatcher(ctl, CFG.idle_nudge_s, CFG.followup_s)
    await w.on_idle()
    await asyncio.sleep(0.3)
    print(f"- sin pregunta, followup_s: {ctl.calls}")
    assert ctl.calls == [("mode", "standby", "followup")]
    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
