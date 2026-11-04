"""FallbackTTS: primary engine with automatic switch to a backup engine."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace

from voice.contracts import (
    CancelToken,
    PcmChunk,
    TTSCapabilities,
    TTSProvider,
    VoiceError,
    VoiceInfo,
    VoiceParams,
)


class FallbackTTS:
    def __init__(self, primary: TTSProvider, fallback: TTSProvider | None) -> None:
        self._primary = primary
        self._fallback = fallback
        self._active: TTSProvider = primary
        self._primary_ok = False
        self._fallback_ok = False

    @property
    def active_name(self) -> str:
        return self._active.name

    @property
    def name(self) -> str:
        return self._active.name

    @property
    def capabilities(self) -> TTSCapabilities:
        return self._active.capabilities

    def load(self) -> None:
        try:
            self._primary.load()
        except VoiceError:
            if self._fallback is None:
                raise
            self._fallback.load()  # if this fails too, its error propagates
            self._fallback_ok = True
            self._active = self._fallback
            return
        self._primary_ok = True
        self._active = self._primary

    def voices(self) -> list[VoiceInfo]:
        return self._active.voices()

    def _use_fallback(self) -> TTSProvider | None:
        fb = self._fallback
        if fb is None or self._active is fb:
            return None
        if not self._fallback_ok:
            fb.load()  # may raise VoiceError; caller re-raises the original instead
            self._fallback_ok = True
        return fb

    def synthesize(self, text: str, params: VoiceParams, cancel: CancelToken) -> Iterator[PcmChunk]:
        engine = self._active
        emitted = False
        try:
            for chunk in engine.synthesize(text, params, cancel):
                emitted = True
                yield chunk
            return
        except VoiceError as err:
            if emitted or cancel.cancelled or err.code == "cancelled":
                raise
            try:
                fb = self._use_fallback()
            except VoiceError:
                fb = None
            if fb is None:
                raise err from None
        # Failed before any audio: retry once on the backup with its own default voice.
        if err.code != "invalid_request":  # a bad voice must not demote the primary for good
            self._active = fb
        yield from fb.synthesize(text, replace(params, voice=None, extra={}), cancel)

    def close(self) -> None:
        for engine in (self._primary, self._fallback):
            if engine is not None:
                engine.close()
