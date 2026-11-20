"""Avisos de fallo de la voz (`voice.error`): códigos y textos cortos para la interfaz.

El proceso de voz no se corta por un fallo: avisa una vez y sigue. Los textos son fijos y nunca
llevan el mensaje de la excepción, rutas ni datos del usuario (eso va solo al log).
"""

from __future__ import annotations

from typing import Final

MESSAGES: Final[dict[str, str]] = {
    "stt_fallback": "El reconocimiento en la nube no responde: Drakter usa el local.",
    "stt_unavailable": "El reconocimiento de voz no funciona: Drakter no te oye.",
    "tts_unavailable": "La síntesis de voz no funciona: Drakter responde solo por escrito.",
    "models_missing": "Faltan los modelos de voz: revisa la instalación.",
    "pipeline_build_failed": "No se pudo arrancar la voz.",
    "pipeline_failed": "La voz se ha detenido por un error.",
    "service_failed": "Una parte de la voz ha fallado.",
}
REPEAT_S: Final = 60.0
"""Un mismo código no se repite antes de este tiempo (un servicio roto falla en cada frase)."""


def message_for(code: str) -> str:
    return MESSAGES.get(code, MESSAGES["service_failed"])
