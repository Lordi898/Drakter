"""TTS de respaldo local: Kokoro int8 con la voz `ef_dora` (plan de voz v2 V-12, V-35).

`KokoroTTSService` descarga los modelos si faltan, así que la fábrica comprueba ANTES que existen
`models/kokoro/kokoro-v1.0.int8.onnx` y `voices-v1.0.bin`. El modelo se carga una vez por proceso
(`shared.get("kokoro")`) con los hilos limitados, y se inyecta en cada servicio nuevo.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Final

from pipecat.services.kokoro import tts as kokoro_tts
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.transcriptions.language import Language
from pipecat.utils.text.transforms.strip_markdown import StripMarkdown

from voice.ports import ResolvedProfile, TTSProvider
from voice.providers.tts._common import cfg_get, models_dir, t_strip_tags
from voice.speech.lexicon import lexicon
from voice.speech.normalize import normalize_es

MODEL_FILE: Final = "kokoro-v1.0.int8.onnx"
VOICES_FILE: Final = "voices-v1.0.bin"
VOICE: Final = "ef_dora"
DEFAULT_THREADS: Final = 2

_build_lock = threading.Lock()


class KokoroModelMissing(FileNotFoundError):
    pass


def model_paths(cfg: Any, shared: Any = None) -> tuple[Path, Path]:
    base = models_dir(cfg, shared) / "kokoro"
    model, voices = base / MODEL_FILE, base / VOICES_FILE
    missing = [str(p) for p in (model, voices) if not p.is_file()]
    if missing:
        raise KokoroModelMissing(
            "faltan los modelos de Kokoro (no se descargan en ejecución): " + ", ".join(missing)
        )
    return model, voices


def load_kokoro(model: Path, voices: Path, threads: int):
    """Carga `kokoro_onnx.Kokoro` con `intra_op_num_threads` limitado."""
    import onnxruntime as ort
    from kokoro_onnx import Kokoro

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = threads
    opts.inter_op_num_threads = 1
    session = ort.InferenceSession(str(model), sess_options=opts, providers=["CPUExecutionProvider"])
    return Kokoro.from_session(session, str(voices))


def create(cfg: Any, shared: Any, profile: ResolvedProfile) -> TTSProvider:
    model, voices = model_paths(cfg, shared)
    threads = int(cfg_get(cfg, "tts_threads", DEFAULT_THREADS))
    loader = lambda: load_kokoro(model, voices, threads)  # noqa: E731
    engine = shared.get("kokoro", loader) if shared is not None else loader()
    # KokoroTTSService.__init__ construye `Kokoro(model, voices)` por su cuenta: se sustituye el
    # nombre del módulo durante la construcción para reutilizar el modelo ya cargado.
    with _build_lock:
        original = kokoro_tts.Kokoro
        kokoro_tts.Kokoro = lambda *_a, **_k: engine
        try:
            service = KokoroTTSService(
                model_path=str(model),
                voices_path=str(voices),
                settings=KokoroTTSService.Settings(voice=VOICE, language=Language.ES),
                text_transforms=[
                    ("*", t_strip_tags),
                    ("*", StripMarkdown(strip_urls=True)),
                    ("*", lexicon),
                    ("*", normalize_es),
                ],
            )
        finally:
            kokoro_tts.Kokoro = original
    return TTSProvider(service=service, name="kokoro", expressive=False)
