"""Latency benchmark of the real engines. Prints and writes JSON; invents no targets.

Example:
  python voice/tests/bench_engines.py --stt-model small --wav frase.wav --tts kokoro --out /var/tmp/drakter-voz/small.json
Every number comes from this run, with loadavg and RSS next to it. Needs models on disk
(nothing is downloaded). Run it with the machine idle; loadavg is recorded so you can tell.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

from voice.config import load_config  # noqa: E402
from voice.contracts import CancelToken, VoiceError, VoiceParams  # noqa: E402

PHRASES = {
    "corta": "Hola, ¿qué tal?",
    "media": "Tienes una reunión a las cinco y dos tareas pendientes para hoy.",
    "larga": (
        "Esta semana tienes tres entregas pendientes y un examen el jueves por la mañana. "
        "Te propongo dejar el informe de física para el martes, porque es lo que menos tiempo te llevará. "
        "Después podrías repasar el temario del examen durante el miércoles, y reservar el fin de semana "
        "para terminar el proyecto final."
    ),
}


def _registry():
    try:
        from voice import registry

        return registry
    except ImportError:
        return None


def _build(kind: str, cfg):
    reg = _registry()
    if reg is not None:
        return (reg.build_stt if kind == "stt" else reg.build_tts)(cfg), "voice.registry"
    # Registry not written yet: same classes, built directly.
    if kind == "stt":
        from voice.stt.faster_whisper_provider import FasterWhisperSTT

        return FasterWhisperSTT(cfg), "directo (registry ausente)"
    if cfg.tts_provider == "piper":
        from voice.tts.piper import PiperTTS

        return PiperTTS(cfg), "directo (registry ausente)"
    from voice.tts.kokoro import KokoroTTS

    return KokoroTTS(cfg), "directo (registry ausente)"


def bench_stt(cfg, wav: Path, reps: int) -> dict[str, Any]:
    audio = C.read_wav_16k(wav)
    audio_s = len(audio) / 16000
    eng, via = _build("stt", cfg)
    out: dict[str, Any] = {"model": cfg.stt_model, "threads": cfg.stt_threads, "beam": cfg.stt_beam_size,
                           "compute_type": cfg.stt_compute_type, "via": via, "audio_s": round(audio_s, 3),
                           "loadavg_start": C.loadavg(), "reps": []}
    t0 = time.perf_counter()
    eng.load()
    out["load_s"] = round(time.perf_counter() - t0, 3)
    out["rss_after_load_mb"] = C.hwm_mb()
    for _ in range(reps):
        t0 = time.perf_counter()
        first = None
        segs = 0
        chars = 0
        for seg in eng.transcribe(audio, language=cfg.stt_language, cancel=CancelToken()):
            if first is None:
                first = time.perf_counter() - t0
            segs += 1
            chars += len(seg.text)  # length only; text is never printed or stored
        total = time.perf_counter() - t0
        out["reps"].append({"first_segment_s": None if first is None else round(first, 3),
                            "total_s": round(total, 3), "rtf": round(total / audio_s, 3),
                            "segments": segs, "chars": chars, "loadavg": C.loadavg()})
    out["loadavg_end"] = C.loadavg()
    out["rss_peak_mb"] = C.hwm_mb()
    eng.close()
    return out


def _split(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s]


def bench_tts(cfg, reps: int) -> dict[str, Any]:
    eng, via = _build("tts", cfg)
    out: dict[str, Any] = {"engine": cfg.tts_provider, "voice": cfg.tts_voice if cfg.tts_provider == "kokoro" else cfg.piper_voice,
                           "threads": cfg.tts_threads, "via": via, "loadavg_start": C.loadavg(),
                           "phrases": {}, "streaming_by_sentence": []}
    t0 = time.perf_counter()
    eng.load()
    out["load_s"] = round(time.perf_counter() - t0, 3)
    out["rss_after_load_mb"] = C.hwm_mb()
    params = VoiceParams(voice=cfg.tts_voice if cfg.tts_provider == "kokoro" else None)

    def run(text: str) -> tuple[float | None, float, float]:
        t0 = time.perf_counter()
        first, samples, sr = None, 0, 24000
        for ch in eng.synthesize(text, params, CancelToken()):
            if first is None:
                first = time.perf_counter() - t0
            samples += len(ch.pcm)
            sr = ch.sample_rate
        return first, time.perf_counter() - t0, samples / sr

    for name, text in PHRASES.items():
        rows = []
        for _ in range(reps):
            first, total, dur = run(text)
            rows.append({"chars": len(text), "first_audio_s": None if first is None else round(first, 3),
                         "total_s": round(total, 3), "audio_s": round(dur, 3),
                         "rtf": round(total / dur, 3) if dur else None, "loadavg": C.loadavg()})
        out["phrases"][name] = rows
    # Underrun simulation: synthesise the long text sentence by sentence; sentence i must be
    # ready before sentence i-1 has finished playing (audio starts when the first is ready).
    for _ in range(reps):
        t0 = time.perf_counter()
        ready, durs = [], []
        for s in _split(PHRASES["larga"]):
            _, _, dur = run(s)
            ready.append(time.perf_counter() - t0)
            durs.append(dur)
        play_end = ready[0] + durs[0]
        underrun = 0.0
        for r, d in zip(ready[1:], durs[1:]):
            underrun += max(0.0, r - play_end)
            play_end = max(play_end, r) + d
        out["streaming_by_sentence"].append({"sentences": len(durs), "first_ready_s": round(ready[0], 3),
                                             "underrun_s": round(underrun, 3), "audio_s": round(sum(durs), 3),
                                             "loadavg": C.loadavg()})
    out["loadavg_end"] = C.loadavg()
    out["rss_peak_mb"] = C.hwm_mb()
    eng.close()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stt-model", default=None, help="small, medium... (por defecto el de la configuración)")
    ap.add_argument("--wav", type=Path, help="WAV PCM16 con voz en español; sin él se omite STT")
    ap.add_argument("--tts", choices=["kokoro", "piper"], help="motor TTS a medir; sin él se omite TTS")
    ap.add_argument("--threads", type=int, default=None, help="hilos de STT y TTS (por defecto los de la configuración)")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--min-available-mb", type=int, default=1500,
                    help="se niega a empezar si MemAvailable es menor (configurable; medium necesita más margen)")
    ap.add_argument("--out", type=Path, help="JSON de salida")
    a = ap.parse_args()

    avail = C.meminfo_mb("MemAvailable")
    if avail is not None and avail < a.min_available_mb:
        print(f"RECHAZADO: MemAvailable={avail} MB < mínimo {a.min_available_mb} MB. Cierra aplicaciones o baja --min-available-mb.")
        return 2
    if not a.wav and not a.tts:
        ap.error("indica --wav y/o --tts")

    cfg = load_config()
    over: dict[str, Any] = {}
    if a.stt_model:
        over["stt_model"] = a.stt_model
    if a.threads:
        over.update(stt_threads=a.threads, tts_threads=a.threads)
    if a.tts:
        over.update(tts_provider=a.tts, tts_fallback="")  # measure one engine alone
    cfg = dataclasses.replace(cfg, **over)

    result: dict[str, Any] = {"when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                              "mem_available_mb_start": avail, "loadavg_start": C.loadavg(),
                              "models_dir": str(cfg.resolved_models_dir), "reps": a.reps}
    try:
        if a.wav:
            result["stt"] = bench_stt(cfg, a.wav, a.reps)
        if a.tts:
            result["tts"] = bench_tts(cfg, a.reps)
    except VoiceError as exc:
        print(f"ERROR {exc.code}: {exc.message}")
        result["error"] = {"code": exc.code, "message": exc.message}
        rc = 1
    else:
        rc = 0
    result["loadavg_end"] = C.loadavg()
    result["rss_peak_mb"] = C.hwm_mb()
    result["mem_available_mb_end"] = C.meminfo_mb("MemAvailable")
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text, encoding="utf-8")
        print(f"escrito {a.out}")
    print(text)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
