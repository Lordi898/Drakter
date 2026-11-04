"""Piper TTS as an EXTERNAL process only. Piper is GPL-3.0-or-later: never import it here.

Mode: one persistent worker process (voice/tts/_piper_worker.py run with config.piper_python),
talking over stdin/stdout pipes: no network port, no Flask (piper's http_server needs Flask, which is
not part of piper-tts' own dependencies). The model loads once; speed goes per request as length_scale.
Cancelling kills the worker; it is respawned lazily on the next sentence.
"""

from __future__ import annotations

import json
import os
import select
import struct
import subprocess
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from voice.config import VoiceConfig
from voice.contracts import (
    CancelToken,
    PcmChunk,
    TTSCapabilities,
    VoiceError,
    VoiceInfo,
    VoiceParams,
)

_WORKER = Path(__file__).with_name("_piper_worker.py")
_ENV_ALLOW = ("PATH", "LANG", "LC_ALL", "TMPDIR")  # nothing else is inherited (no secrets)
_STARTUP_TIMEOUT_S = 60.0
_REQUEST_TIMEOUT_S = 60.0  # max silence between two frames
_MAX_FRAME = 16 * 1024 * 1024


class PiperTTS:
    name = "piper"
    capabilities = TTSCapabilities(speed=True, voices=False, streaming=True, intonation=False, emotion=False)

    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._model = config.resolved_models_dir / "piper" / f"{config.piper_voice}.onnx"
        self._json = self._model.with_name(self._model.name + ".json")
        self._proc: subprocess.Popen[bytes] | None = None
        self._rate = 0
        self._lock = threading.Lock()

    # -- lifecycle ---------------------------------------------------------------------------

    def _check_files(self) -> None:
        if self._config.piper_python is None:
            raise VoiceError("dependency_missing", "piper_python (DRAKTER_PIPER_PYTHON) is not configured")
        if not self._config.piper_python.is_file():
            raise VoiceError("dependency_missing", f"Piper interpreter not found: {self._config.piper_python}")
        for path in (self._model, self._json):
            if not path.is_file():
                raise VoiceError("model_missing", f"Piper file not found: {path}")
        try:
            self._rate = int(json.loads(self._json.read_text(encoding="utf-8"))["audio"]["sample_rate"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise VoiceError("engine_failed", f"Invalid Piper voice config: {self._json}") from exc

    def load(self) -> None:
        self._check_files()
        with self._lock:
            self._ensure_proc()

    def _ensure_proc(self) -> subprocess.Popen[bytes]:
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        env = {k: os.environ[k] for k in _ENV_ALLOW if k in os.environ}
        assert self._config.piper_python is not None
        try:
            proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell, text never in argv
                [str(self._config.piper_python), "-I", str(_WORKER), str(self._model), str(self._json)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                shell=False,
            )
        except OSError as exc:
            raise VoiceError("dependency_missing", f"Cannot start Piper worker: {exc.strerror}") from exc
        self._proc = proc
        try:
            ready = self._read_exact(proc, 4, CancelToken(), _STARTUP_TIMEOUT_S)
        except VoiceError:
            self._kill()
            raise
        if ready != b"\x00\x00\x00\x00":
            self._kill()
            raise VoiceError("engine_failed", "Piper worker sent an invalid ready marker")
        return proc

    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        if proc.poll() is None:
            proc.kill()
        for stream in (proc.stdin, proc.stdout):
            try:
                if stream:
                    stream.close()
            except OSError:
                pass
        proc.wait()

    def close(self) -> None:
        self._kill()

    # -- IO ----------------------------------------------------------------------------------

    @staticmethod
    def _read_exact(proc: subprocess.Popen[bytes], n: int, cancel: CancelToken, timeout_s: float) -> bytes | None:
        """Read n bytes polling `cancel` every 50 ms. None if cancelled."""
        assert proc.stdout is not None
        fd = proc.stdout.fileno()
        buf = bytearray()
        deadline = time.monotonic() + timeout_s
        while len(buf) < n:
            if cancel.cancelled:
                return None
            if time.monotonic() > deadline:
                raise VoiceError("engine_failed", "Piper worker timed out")
            ready, _, _ = select.select([fd], [], [], 0.05)
            if not ready:
                if proc.poll() is not None:
                    raise VoiceError("engine_failed", "Piper worker exited")
                continue
            part = os.read(fd, n - len(buf))
            if not part:
                raise VoiceError("engine_failed", "Piper worker closed its output")
            buf += part
        return bytes(buf)

    # -- TTS ---------------------------------------------------------------------------------

    def voices(self) -> list[VoiceInfo]:
        # One voice per model: the configured one.
        lang = self._config.piper_voice.split("-", 1)[0].replace("_", "-")
        return [VoiceInfo(id=self._config.piper_voice, language=lang)]

    def synthesize(self, text: str, params: VoiceParams, cancel: CancelToken) -> Iterator[PcmChunk]:
        if cancel.cancelled:
            return
        if params.voice not in (None, self._config.piper_voice):
            raise VoiceError("invalid_request", f"Unknown Piper voice: {params.voice}")
        if params.speed <= 0:
            raise VoiceError("invalid_request", "speed must be > 0")
        if not text.strip():
            return
        request = json.dumps({"text": text, "length_scale": 1.0 / params.speed}).encode("utf-8") + b"\n"
        with self._lock:
            if not self._rate:
                self._check_files()
            proc = self._ensure_proc()
            assert proc.stdin is not None
            try:
                proc.stdin.write(request)
                proc.stdin.flush()
            except OSError as exc:
                self._kill()
                raise VoiceError("engine_failed", "Piper worker is not accepting input") from exc
            try:
                while True:
                    head = self._read_exact(proc, 4, cancel, _REQUEST_TIMEOUT_S)
                    if head is None:
                        self._kill()  # abort the request; respawned on next use
                        return
                    (size,) = struct.unpack("<I", head)
                    if size == 0:
                        return
                    if size > _MAX_FRAME or size % 2:
                        raise VoiceError("engine_failed", "Piper worker sent an invalid frame")
                    data = self._read_exact(proc, size, cancel, _REQUEST_TIMEOUT_S)
                    if data is None:
                        self._kill()
                        return
                    pcm = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
                    yield PcmChunk(pcm=pcm, sample_rate=self._rate)
            except VoiceError:
                self._kill()
                raise
            except GeneratorExit:
                self._kill()  # consumer stopped mid-request: the pipe would be out of sync
                raise
