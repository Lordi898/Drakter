"""Devices that need no hardware: for tests, CI and `audio_backend="null"`."""

from __future__ import annotations

import threading
from collections.abc import Callable

from voice.contracts import AudioFrame, Pcm, VoiceError


class NullCapture:
    """Never emits a frame. `active` is True only between start() and stop(). start() twice is a no-op."""

    name = "null"

    def __init__(self) -> None:
        self._active = False

    def start(self, on_frame: Callable[[AudioFrame], None], on_error: Callable[[VoiceError], None]) -> None:
        self._active = True

    def stop(self) -> None:
        self._active = False

    @property
    def active(self) -> bool:
        return self._active


class NullSink:
    """Discards audio but takes real time to do it (sleeps the duration of each write).

    abort() wakes a sleeping write() at once, so interruption behaves like a real device.
    """

    name = "null"

    def __init__(self) -> None:
        self._rate = 0
        self._wake = threading.Event()  # set by abort(), cleared by open()

    def open(self, sample_rate: int) -> None:
        self._rate = sample_rate
        self._wake.clear()

    def write(self, pcm: Pcm) -> None:
        if self._rate <= 0:
            raise VoiceError("audio_device", "sink not open")
        self._wake.wait(len(pcm) / self._rate)

    def drain(self) -> None:
        return None  # write() already took real time

    def abort(self) -> None:
        self._wake.set()

    def close(self) -> None:
        self._rate = 0
        self._wake.set()
