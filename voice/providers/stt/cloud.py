"""STT en la nube con respaldo local: Deepgram (streaming) o Groq (Whisper por segmentos) → Moonshine.

Nombres del registro (`VoiceConfig.stt`):

- `auto` (por defecto): Deepgram si hay `DEEPGRAM_API_KEY`; si no, Groq si hay `GROQ_API_KEY`;
  si no, Moonshine. Con nube, Moonshine queda detrás como respaldo.
- `deepgram` / `groq`: ese proveedor (si falta la clave, Moonshine con un aviso).
- `moonshine`: solo local (`moonshine_streaming.py`).

Respaldo: un `ServiceSwitcher` [nube, Moonshine]. Cualquier error del servicio en la nube (red,
401, cuota) conmuta a Moonshine para el resto del proceso, con un único aviso:
`voice.error{code: "stt_fallback", stage: "stt", recoverable: true}` y un log. Nunca se registra la
clave ni el texto.

Verificado en Pipecat 1.16.0:
- `DeepgramSTTService(api_key, base_url, mip_opt_out, settings=DeepgramSTTService.Settings(...))`,
  con `keyterm` como lista (Nova-3). Manda `Finalize` al `VADUserStoppedSpeakingFrame`, así que el
  texto final llega con `finalized=True`. `mip_opt_out=True`: fuera del programa de mejora del
  modelo (Deepgram no conserva el audio para entrenar). `base_url="api.eu.deepgram.com"`: región UE.
- `GroqSTTService` hereda de `BaseWhisperSTTService` (cliente `openai`, sin el SDK `groq`) y
  de `SegmentedSTTService`: transcribe cada tramo de VAD. Su `TranscriptionFrame` no lleva
  `finalized`; aquí se marca, porque un tramo segmentado ya es definitivo.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any, Final

from loguru import logger
from pipecat.frames.frames import ErrorFrame, Frame, StartFrame, TranscriptionFrame
from pipecat.pipeline.service_switcher import ServiceSwitcher, ServiceSwitcherStrategyFailover
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transcriptions.language import Language

if TYPE_CHECKING:
    from pipecat.services.stt_service import STTService

    from voice.config import VoiceConfig
    from voice.ports import Shared

DEEPGRAM_KEY: Final = "DEEPGRAM_API_KEY"
GROQ_KEY: Final = "GROQ_API_KEY"
CLOUD: Final = ("deepgram", "groq")

_announced = False  # voice.error{stt_fallback}: una vez por proceso
_fell_back = False  # tras conmutar, las conexiones nuevas arrancan en Moonshine


def _key(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def select(cfg: VoiceConfig) -> str:
    """Proveedor efectivo: `deepgram`, `groq` o `moonshine`."""
    wanted = str(getattr(cfg, "stt", "auto"))
    if wanted == "auto":
        if _key(DEEPGRAM_KEY):
            return "deepgram"
        return "groq" if _key(GROQ_KEY) else "moonshine"
    if wanted == "deepgram" and not _key(DEEPGRAM_KEY):
        logger.warning("STT deepgram sin DEEPGRAM_API_KEY: se usa Moonshine")
        return "moonshine"
    if wanted == "groq" and not _key(GROQ_KEY):
        logger.warning("STT groq sin GROQ_API_KEY: se usa Moonshine")
        return "moonshine"
    return wanted


def keyterms(cfg: VoiceConfig) -> list[str]:
    return [t for t in getattr(cfg, "stt_keyterms", ()) if t]


# ── servicios ────────────────────────────────────────────────────────────────
def deepgram_service(cfg: VoiceConfig) -> STTService:
    from pipecat.services.deepgram.stt import DeepgramSTTService

    return DeepgramSTTService(
        api_key=_key(DEEPGRAM_KEY) or "",
        base_url=str(getattr(cfg, "stt_deepgram_base_url", "") or ""),
        sample_rate=16000,
        mip_opt_out=True,
        settings=DeepgramSTTService.Settings(
            model=str(getattr(cfg, "stt_deepgram_model", "nova-3")),
            language=Language.ES,
            keyterm=keyterms(cfg),
            interim_results=True,
            punctuate=True,
            smart_format=True,
        ),
    )


def groq_service(cfg: VoiceConfig) -> STTService:
    from pipecat.services.groq.stt import GroqSTTService

    class DrakterGroqSTT(GroqSTTService):
        """Marca el texto como final y comprueba la clave al arrancar (un 401 conmuta antes de hablar)."""

        async def start(self, frame: StartFrame) -> None:
            await super().start(frame)
            self.create_task(self._check_key(), "groq_key_check")

        async def _check_key(self) -> None:
            try:
                await self._client.models.list()
            except Exception as exc:  # noqa: BLE001 - 401, red o cuota: a Moonshine
                await self.push_error(error_msg=f"Groq no disponible ({type(exc).__name__})", exception=exc)

        async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:
            async for frame in super().run_stt(audio):
                if isinstance(frame, TranscriptionFrame):
                    frame.finalized = True
                yield frame

    terms = keyterms(cfg)
    return DrakterGroqSTT(
        api_key=_key(GROQ_KEY) or "",
        settings=GroqSTTService.Settings(
            model=str(getattr(cfg, "stt_groq_model", "whisper-large-v3-turbo")),
            language=Language.ES,
            # Whisper sigue el estilo y la ortografía del prompt: los nombres propios salen bien.
            prompt=(f"Conversación en castellano con {', '.join(terms)}." if terms else None),
            temperature=0.0,
        ),
    )


# ── respaldo ─────────────────────────────────────────────────────────────────
class SttFailover(ServiceSwitcherStrategyFailover):
    """Cualquier error del servicio en la nube activo conmuta a Moonshine (el último de la lista)."""

    ctl: Any = None

    async def handle_error(self, error: ErrorFrame) -> FrameProcessor | None:
        global _fell_back
        failed = error.processor or self._active_service
        local = self._services[-1]
        if failed is not self._active_service or failed is local:
            return None
        switched = await self._set_active_if_available(local)
        if switched is not None:
            _fell_back = True
            await announce_fallback(self.ctl, failed.name, error.error)
        return switched


async def announce_fallback(ctl: Any, name: str, detail: str) -> None:
    global _announced
    if _announced:
        return
    _announced = True
    logger.warning(f"STT {name} no disponible: se pasa a Moonshine local ({str(detail)[:120]})")
    if ctl is not None:
        try:
            await ctl.emit("voice.error", {"code": "stt_fallback", "stage": "stt", "recoverable": True})
        except Exception as exc:  # noqa: BLE001 - el aviso nunca rompe la voz
            logger.warning(f"stt_fallback: no se pudo avisar: {type(exc).__name__}")


def _with_fallback(cloud: STTService, cfg: VoiceConfig, shared: Shared, ctl: Any) -> ServiceSwitcher:
    from voice.providers.stt import moonshine_streaming

    local = moonshine_streaming.create(cfg, shared)
    switcher = ServiceSwitcher(services=[cloud, local], strategy_type=SttFailover)
    switcher.strategy.ctl = ctl
    return switcher


def create(cfg: VoiceConfig, shared: Shared, ctl: Any = None) -> FrameProcessor:
    """Fábrica `stt(cfg, shared)` para `auto`, `deepgram` y `groq`. `ctl` (opcional) recibe el aviso."""
    from voice.providers.stt import moonshine_streaming

    name = select(cfg)
    if name == "moonshine" or _fell_back:
        return moonshine_streaming.create(cfg, shared)
    if name not in CLOUD:
        raise KeyError(f"proveedor STT desconocido: {name}")
    cloud = deepgram_service(cfg) if name == "deepgram" else groq_service(cfg)
    logger.info(f"STT: {name} con respaldo Moonshine")
    return _with_fallback(cloud, cfg, shared, ctl)
