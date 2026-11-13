"""Microphone and speaker through external processes (PipeWire or ALSA tools). No PortAudio.

Capture: one subprocess writes raw s16le mono 16 kHz to stdout; a reader thread regroups it
into AudioFrame of exactly FRAME_SAMPLES. Sink: one subprocess reads raw s16le mono from stdin.
Arguments are always a list (never a shell). Audio is never logged.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from collections.abc import Callable

import numpy as np

from voice.audio.null import NullCapture, NullSink
from voice.contracts import FRAME_SAMPLES, SAMPLE_RATE, AudioCapture, AudioFrame, AudioSink, Pcm, VoiceError
from voice.config import VoiceConfig

log = logging.getLogger(__name__)

_FRAME_BYTES = FRAME_SAMPLES * 2
_TERM_WAIT_S = 1.0
_KILL_WAIT_S = 2.0


def _resolve(config: VoiceConfig, pipewire_bin: str, alsa_bin: str) -> str:
    """Return "pipewire", "alsa" or "null". Raises VoiceError if the needed binary is missing."""
    backend = config.audio_backend
    if backend == "null":
        return "null"
    if backend == "auto":
        if shutil.which(pipewire_bin):
            return "pipewire"
        if shutil.which(alsa_bin):
            return "alsa"
        raise VoiceError("dependency_missing", f"neither {pipewire_bin} nor {alsa_bin} found in PATH")
    if backend == "pipewire":
        binary = pipewire_bin
    elif backend == "alsa":
        binary = alsa_bin
    else:
        raise VoiceError("invalid_request", f"unknown audio_backend {backend!r}")
    if not shutil.which(binary):
        raise VoiceError("dependency_missing", f"{binary} not found in PATH")
    return backend


def _stop_process(proc: subprocess.Popen[bytes]) -> None:
    """terminate, wait up to _TERM_WAIT_S, then kill and wait. Safe to call twice."""
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(_TERM_WAIT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(_KILL_WAIT_S)
            except subprocess.TimeoutExpired:
                log.error("audio process %s did not exit after kill", proc.pid)
        except OSError:
            pass
    for stream in (proc.stdin, proc.stdout):
        try:
            if stream is not None:
                stream.close()
        except OSError:
            pass


def open_capture(config: VoiceConfig) -> AudioCapture:
    kind = _resolve(config, "pw-record", "arecord")
    if kind == "null":
        return NullCapture()
    if kind == "pipewire":
        argv = ["pw-record", "--raw", "--rate", str(SAMPLE_RATE), "--channels", "1", "--format", "s16"]
        if config.input_device:
            argv += ["--target", config.input_device]
        argv.append("-")
    else:
        argv = ["arecord", "-q", "-t", "raw", "-f", "S16_LE", "-r", str(SAMPLE_RATE), "-c", "1"]
        if config.input_device:
            argv += ["-D", config.input_device]
    return ProcessCapture(kind, argv)


def open_sink(config: VoiceConfig) -> AudioSink:
    kind = _resolve(config, "pw-play", "aplay")
    if kind == "null":
        return NullSink()
    return ProcessSink(kind, config.output_device)


class ProcessCapture:
    """Microphone through pw-record/arecord. start() on an active capture is a documented no-op."""

    def __init__(self, name: str, argv: list[str]) -> None:
        self.name = name
        self._argv = argv
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._active = False
        self._stopping = False

    @property
    def active(self) -> bool:
        return self._active

    def start(self, on_frame: Callable[[AudioFrame], None], on_error: Callable[[VoiceError], None]) -> None:
        with self._lock:
            if self._active:
                return
            leftovers = self._detach_locked()  # a capture that died by itself
        self._cleanup(*leftovers)
        try:
            proc = subprocess.Popen(
                self._argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
        except OSError as exc:
            raise VoiceError("audio_device", f"cannot start {self._argv[0]}: {exc.strerror or exc}") from exc
        thread = threading.Thread(
            target=self._read_loop, args=(proc, on_frame, on_error), name="voice-capture", daemon=True
        )
        with self._lock:
            self._proc, self._thread = proc, thread
            self._stopping = False
            self._active = True
        thread.start()

    def stop(self) -> None:
        """Kills the process and waits for it: the microphone is free when this returns."""
        with self._lock:
            self._stopping = True
            self._active = False
            detached = self._detach_locked()
        self._cleanup(*detached)

    def _detach_locked(self) -> tuple[subprocess.Popen[bytes] | None, threading.Thread | None]:
        proc, thread = self._proc, self._thread
        self._proc = self._thread = None
        return proc, thread

    @staticmethod
    def _cleanup(proc: subprocess.Popen[bytes] | None, thread: threading.Thread | None) -> None:
        if proc is not None:
            _stop_process(proc)
        if thread is not None and thread is not threading.current_thread():
            thread.join(_KILL_WAIT_S)

    def _read_loop(
        self,
        proc: subprocess.Popen[bytes],
        on_frame: Callable[[AudioFrame], None],
        on_error: Callable[[VoiceError], None],
    ) -> None:
        assert proc.stdout is not None
        buf = bytearray()
        reason = "audio process ended"
        try:
            while True:
                data = proc.stdout.read(_FRAME_BYTES - len(buf) if buf else _FRAME_BYTES)
                if not data:
                    break
                buf += data
                if len(buf) < _FRAME_BYTES:
                    continue
                pcm: Pcm = np.frombuffer(bytes(buf), dtype="<i2").astype(np.float32) / 32768.0
                buf.clear()
                frame = AudioFrame(pcm=pcm, captured_ns=time.perf_counter_ns())
                try:
                    on_frame(frame)
                except Exception:  # a bad consumer must not stop the microphone loop
                    log.exception("on_frame callback failed")
        except (OSError, ValueError) as exc:  # closed by stop(), or read error
            reason = f"read failed: {exc}"
        with self._lock:
            if self._stopping or self._proc is not proc:
                return  # normal stop()
            self._active = False
            self._stopping = True  # report once
            code = proc.poll()
        try:
            on_error(VoiceError("audio_device", f"{reason} (exit code {code})"))
        except Exception:
            log.exception("on_error callback failed")


class ProcessSink:
    """Speaker through pw-play/aplay. One process per open(); drain() ends it, write() after drain needs open()."""

    def __init__(self, kind: str, device: str) -> None:
        self.name = kind
        self._device = device
        self._proc: subprocess.Popen[bytes] | None = None
        self._aborted = False

    def _argv(self, rate: int) -> list[str]:
        if self.name == "pipewire":
            argv = ["pw-play", "--raw", "--rate", str(rate), "--channels", "1", "--format", "s16"]
            if self._device:
                argv += ["--target", self._device]
            return [*argv, "-"]
        argv = ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-r", str(rate), "-c", "1"]
        if self._device:
            argv += ["-D", self._device]
        return argv

    def open(self, sample_rate: int) -> None:
        self.close()
        try:
            self._proc = subprocess.Popen(
                self._argv(sample_rate),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
        except OSError as exc:
            raise VoiceError("audio_device", f"cannot start audio output: {exc.strerror or exc}") from exc
        self._aborted = False

    def write(self, pcm: Pcm) -> None:
        proc = self._proc
        if self._aborted or proc is None or proc.stdin is None:
            if self._aborted:
                return  # cut by abort(): nothing to say
            raise VoiceError("audio_device", "sink not open")
        data = (np.clip(pcm, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        try:
            proc.stdin.write(data)
        except (BrokenPipeError, ValueError, OSError) as exc:
            if self._aborted:
                return
            raise VoiceError("audio_device", f"audio output closed: {exc}") from exc

    def drain(self) -> None:
        """Closes stdin and waits until the process has finished playing."""
        proc = self._proc
        if proc is None or self._aborted:
            return
        try:
            if proc.stdin is not None:
                proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        try:
            proc.wait()
        except Exception:
            pass
        if proc.returncode not in (0, None) and not self._aborted:
            raise VoiceError("audio_device", f"audio output exited with code {proc.returncode}")

    def abort(self) -> None:
        """Callable from any thread: kills the process now. A write() in flight returns silently."""
        self._aborted = True
        proc = self._proc
        if proc is None:
            return
        try:
            proc.kill()
            proc.wait(_KILL_WAIT_S)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def close(self) -> None:
        proc, self._proc = self._proc, None
        if proc is not None:
            _stop_process(proc)
