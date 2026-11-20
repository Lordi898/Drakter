"""Fin de turno con Smart Turn v3.2 (V-07) y dos salvaguardas para las pausas de pensar.

Cadena (umbrales en `VoiceConfig`):

1. VAD Silero: el usuario calla 0,2 s (`VADUserStoppedSpeakingFrame`).
2. Smart Turn v3.2 predice «completo» si su probabilidad supera `turn_complete_threshold`
   (Pipecat usa 0,5 fijo). Si no, el turno se cierra al llegar a `turn_stop_secs` de silencio.
3. Con «completo», `wait_for_transcript=True` exige el texto final del STT.
4. `DrakterTurnStop` no cierra todavía: espera hasta `turn_grace_s` más de silencio y, si el
   texto acaba colgando («… de la», «… y», una coma), hasta `turn_hanging_secs` de silencio.
   Si el usuario vuelve a hablar entre medias, el turno sigue abierto.

Medido sobre 80 frases cortadas a mitad (voz sintética, DECISIONS «Fin de turno»): Smart Turn solo
da «completo» al 81 % de los cortes con 0,5; con umbral 0,7 y la regla de texto, al 29 %, sin
retener ninguna frase completa.

Modelo: `models/smart-turn/smart-turn-v3.2-cpu.onnx` si existe; si no, el del wheel de Pipecat.
El analizador se carga una vez por proceso y se limpia al montar cada conexión.
"""

from __future__ import annotations

import asyncio
import re
import time
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import numpy as np
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.frames.frames import VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame
from pipecat.turns.user_stop.turn_analyzer_user_turn_stop_strategy import (
    TurnAnalyzerUserTurnStopStrategy,
)

if TYPE_CHECKING:
    from voice.config import VoiceConfig
    from voice.ports import Shared

MODEL_FILE = "smart-turn/smart-turn-v3.2-cpu.onnx"

# Palabras con las que una frase en castellano no suele acabar: preposiciones, artículos,
# determinantes, conjunciones e intensificadores. Si el texto acaba así, el usuario está pensando.
_HANGING: Final = frozenset(
    """a al ante bajo con contra de del desde durante en entre hacia hasta mediante para por segun
    sin sobre tras el la los las lo un una unos unas mi mis tu tus su sus nuestro nuestra nuestros
    nuestras este esta estos estas ese esa esos esas aquel aquella y e ni o u pero sino que porque
    pues como cuando donde si aunque mientras cual cuyo cuya muy mas menos tan tanto""".split()
)
_WORD: Final = re.compile(r"[a-zñ]+")


def hanging(text: str) -> bool:
    """`True` si el texto parece cortado a mitad de frase."""
    t = text.strip()
    if not t:
        return False
    if t.endswith((",", "…", "...", ":", ";", "-")):
        return True
    plain = "".join(c for c in unicodedata.normalize("NFKD", t.lower()) if not unicodedata.combining(c))
    words = _WORD.findall(plain)
    return bool(words) and words[-1] in _HANGING


def model_path(models_dir: Path) -> str | None:
    """Ruta local del modelo, o None para usar el del wheel."""
    path = Path(models_dir) / MODEL_FILE
    return str(path) if path.is_file() else None


class ThresholdSmartTurn(LocalSmartTurnAnalyzerV3):
    """Smart Turn v3 con umbral de «completo» configurable (Pipecat fija 0,5)."""

    threshold: float = 0.5

    def _predict_endpoint(self, audio_array: np.ndarray) -> dict[str, Any]:
        result = super()._predict_endpoint(audio_array)
        result["prediction"] = 1 if result["probability"] > self.threshold else 0
        return result


def load_analyzer(models_dir: Path, stop_secs: float, cpu_count: int = 2) -> ThresholdSmartTurn:
    return ThresholdSmartTurn(
        smart_turn_model_path=model_path(models_dir),
        cpu_count=cpu_count,
        params=SmartTurnParams(stop_secs=stop_secs),
    )


class DrakterTurnStop(TurnAnalyzerUserTurnStopStrategy):
    """Retrasa el fin de turno ya decidido hasta que el silencio llega a su objetivo."""

    def __init__(self, *, grace_s: float, hanging_s: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._grace_s = grace_s
        self._hanging_s = hanging_s
        self._silence_since: float | None = None
        self._hold: asyncio.Task | None = None

    def target_silence(self, text: str) -> float:
        """Silencio que debe acumular el usuario antes de cerrar el turno."""
        return self._hanging_s if hanging(text) else self._stop_secs + self._grace_s

    async def process_frame(self, frame: Any) -> None:
        if isinstance(frame, VADUserStartedSpeakingFrame):
            self._silence_since = None
            await self._cancel_hold()
        elif isinstance(frame, VADUserStoppedSpeakingFrame):
            self._silence_since = time.monotonic() - frame.stop_secs
        await super().process_frame(frame)

    async def report_user_turn_stopped(self) -> None:
        if self._hold is not None:
            return  # ya hay un cierre en espera
        since = self._silence_since
        wait = 0.0 if since is None else self.target_silence(self._text) - (time.monotonic() - since)
        if wait <= 0:
            await super().report_user_turn_stopped()
            return
        self._hold = self.task_manager.create_task(self._hold_then_report(wait), f"{self}::turn_hold")

    async def _hold_then_report(self, wait: float) -> None:
        try:
            await asyncio.sleep(wait)
        except asyncio.CancelledError:
            return
        self._hold = None
        await TurnAnalyzerUserTurnStopStrategy.report_user_turn_stopped(self)

    async def _cancel_hold(self) -> None:
        hold, self._hold = self._hold, None
        if hold is not None and hold is not asyncio.current_task():
            await self.task_manager.cancel_task(hold)

    async def _reset(self) -> None:
        await self._cancel_hold()
        await super()._reset()

    async def cleanup(self) -> None:
        await self._cancel_hold()
        await super().cleanup()


def create(cfg: VoiceConfig, shared: Shared) -> DrakterTurnStop:
    """Fábrica `turn_stop(cfg, shared)` (plan §4.7)."""
    stop_secs = float(getattr(cfg, "turn_stop_secs", 3.0))
    models_dir = Path(shared.models_dir)
    analyzer = shared.get("smart_turn", lambda: load_analyzer(models_dir, stop_secs))
    analyzer.threshold = float(getattr(cfg, "turn_complete_threshold", 0.7))
    analyzer.clear()  # estado de la conexión anterior
    return DrakterTurnStop(
        turn_analyzer=analyzer,
        wait_for_transcript=True,
        grace_s=float(getattr(cfg, "turn_grace_s", 0.3)),
        hanging_s=float(getattr(cfg, "turn_hanging_secs", 2.0)),
    )
