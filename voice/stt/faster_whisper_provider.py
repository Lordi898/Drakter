"""Local STT with Faster-Whisper (CPU only). Never downloads a model.

Neither audio nor transcribed text is ever logged or put in error messages.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from voice.config import VoiceConfig
from voice.contracts import CancelToken, Pcm, TranscriptSegment, VoiceError


class FasterWhisperSTT:
    name = "faster_whisper"

    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._model: Any = None

    def _model_source(self) -> tuple[str, Path | None]:
        """Return (model argument, expected local path). Local-only, so a name maps to a dir."""
        raw = self._config.stt_model
        download_root = self._config.resolved_models_dir / "whisper"
        as_path = Path(raw).expanduser()
        if as_path.is_absolute() or raw.startswith(("./", "../", "~")):
            return str(as_path), as_path
        return raw, download_root

    def load(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel  # lazy: heavy import
        except ImportError as exc:
            raise VoiceError("dependency_missing", "faster-whisper is not installed") from exc

        source, expected = self._model_source()
        download_root = self._config.resolved_models_dir / "whisper"
        if expected is not None and expected != download_root and not expected.is_dir():
            raise VoiceError("model_missing", f"Whisper model directory not found: {expected}")
        try:
            self._model = WhisperModel(
                source,
                device="cpu",
                compute_type=self._config.stt_compute_type,
                cpu_threads=self._config.stt_threads,
                download_root=str(download_root),
                local_files_only=True,
            )
        except Exception as exc:
            if _is_missing(exc, source, expected):
                raise VoiceError(
                    "model_missing",
                    f"Whisper model '{self._config.stt_model}' not found; expected under {expected}. "
                    "It is never downloaded automatically.",
                ) from None
            raise VoiceError("engine_failed", f"could not load Whisper model: {type(exc).__name__}") from None

    def transcribe(
        self, audio: Pcm, *, language: str | None, cancel: CancelToken
    ) -> Iterator[TranscriptSegment]:
        if self._model is None:
            raise VoiceError("engine_failed", "STT model is not loaded")
        if cancel.cancelled:
            return
        try:
            segments, _info = self._model.transcribe(
                audio,
                language=language,
                beam_size=self._config.stt_beam_size,
                vad_filter=False,
                condition_on_previous_text=False,
            )
            for seg in segments:
                if cancel.cancelled:
                    return
                text = seg.text.strip()
                if not text:
                    continue
                yield TranscriptSegment(
                    text=text,
                    start_s=float(seg.start),
                    end_s=float(seg.end),
                    no_speech_prob=getattr(seg, "no_speech_prob", None),
                )
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceError("engine_failed", f"transcription failed: {type(exc).__name__}") from None

    def close(self) -> None:
        self._model = None


def _is_missing(exc: Exception, source: str, expected: Path | None) -> bool:
    name = type(exc).__name__
    if name in {"LocalEntryNotFoundError", "FileNotFoundError", "RepositoryNotFoundError"}:
        return True
    if isinstance(exc, (FileNotFoundError, OSError)) and "local" in str(exc).lower():
        return True
    return isinstance(exc, ValueError) and "Invalid model size" in str(exc)
