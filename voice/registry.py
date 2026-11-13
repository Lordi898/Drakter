"""Builds engines from configuration. Imports are lazy, so an unused engine costs nothing.

An unknown name is a configuration error. A missing dependency or model shows up later, in
load(); deciding what to degrade to is VoiceManager's job, never this module's.
"""

from __future__ import annotations

from voice.config import VoiceConfig
from voice.contracts import STTProvider, TTSProvider, VADProvider, VoiceError, WakeWordProvider


def build_vad(c: VoiceConfig) -> VADProvider:
    if c.vad_provider == "silero":
        from voice.vad.silero import SileroVAD

        return SileroVAD(c)
    if c.vad_provider == "energy":
        from voice.vad.energy import EnergyVAD

        return EnergyVAD(c)
    raise VoiceError("invalid_request", f"unknown VAD provider: {c.vad_provider}")


def build_wakeword(c: VoiceConfig) -> WakeWordProvider:
    if c.wakeword_provider == "null":
        from voice.wakeword.null import NullWakeWord

        return NullWakeWord(c)
    if c.wakeword_provider == "openwakeword":
        from voice.wakeword.openwakeword_provider import OpenWakeWordProvider

        return OpenWakeWordProvider(c)
    raise VoiceError("invalid_request", f"unknown wake word provider: {c.wakeword_provider}")


def build_stt(c: VoiceConfig) -> STTProvider:
    if c.stt_provider == "faster_whisper":
        from voice.stt.faster_whisper_provider import FasterWhisperSTT

        return FasterWhisperSTT(c)
    raise VoiceError("invalid_request", f"unknown STT provider: {c.stt_provider}")


def _tts_engine(name: str, c: VoiceConfig) -> TTSProvider:
    if name == "kokoro":
        from voice.tts.kokoro import KokoroTTS

        return KokoroTTS(c)
    if name == "piper":
        from voice.tts.piper import PiperTTS

        return PiperTTS(c)
    raise VoiceError("invalid_request", f"unknown TTS provider: {name}")


def build_tts(c: VoiceConfig) -> TTSProvider:
    primary = _tts_engine(c.tts_provider, c)
    if not c.tts_fallback or c.tts_fallback == c.tts_provider:
        return primary
    from voice.tts.fallback import FallbackTTS

    return FallbackTTS(primary, _tts_engine(c.tts_fallback, c))
