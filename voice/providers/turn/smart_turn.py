"""Fin de turno con Smart Turn v3.2 (V-07).

`TurnAnalyzerUserTurnStopStrategy(LocalSmartTurnAnalyzerV3(cpu_count=2), wait_for_transcript=True)`.
Modelo: `models/smart-turn/smart-turn-v3.2-cpu.onnx` si existe; si no, el del wheel de Pipecat
(no se instala el extra `local-smart-turn`). El analizador se carga una vez por proceso: sigue
usable tras `cleanup()` (Pipecat relanza su hilo) y se limpia al montar cada conexión.
La inferencia corre en el hilo propio del analizador, fuera del bucle asyncio.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.turns.user_stop.turn_analyzer_user_turn_stop_strategy import (
    TurnAnalyzerUserTurnStopStrategy,
)

if TYPE_CHECKING:
    from voice.config import VoiceConfig
    from voice.ports import Shared

MODEL_FILE = "smart-turn/smart-turn-v3.2-cpu.onnx"


def model_path(models_dir: Path) -> str | None:
    """Ruta local del modelo, o None para usar el del wheel."""
    path = Path(models_dir) / MODEL_FILE
    return str(path) if path.is_file() else None


def load_analyzer(models_dir: Path, stop_secs: float, cpu_count: int = 2) -> LocalSmartTurnAnalyzerV3:
    return LocalSmartTurnAnalyzerV3(
        smart_turn_model_path=model_path(models_dir),
        cpu_count=cpu_count,
        params=SmartTurnParams(stop_secs=stop_secs),
    )


def create(cfg: VoiceConfig, shared: Shared) -> TurnAnalyzerUserTurnStopStrategy:
    """Fábrica `turn_stop(cfg, shared)` (plan §4.7)."""
    stop_secs = float(getattr(cfg, "turn_stop_secs", 3.0))
    models_dir = Path(shared.models_dir)
    analyzer = shared.get("smart_turn", lambda: load_analyzer(models_dir, stop_secs))
    analyzer.clear()  # estado de la conexión anterior
    return TurnAnalyzerUserTurnStopStrategy(turn_analyzer=analyzer, wait_for_transcript=True)
