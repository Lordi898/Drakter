"""Prueba guiada con micrófono real, paso a paso, en español. Nada de audio se guarda en disco.

  python voice/tests/mic_check.py                 # dispositivos, grabación, nivel, VAD, STT->TTS si hay modelos
  python voice/tests/mic_check.py --barge-in      # prueba de eco: ¿se oye Drakter a sí mismo por el micrófono?
  python voice/tests/mic_check.py --voices        # escuchar Kokoro y Piper en español
Usa los auriculares o altavoces que quieras probar. Antes de abrir el micrófono pide confirmación.
"""

from __future__ import annotations

import argparse
import dataclasses
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

import numpy as np  # noqa: E402

from voice.config import load_config  # noqa: E402
from voice.contracts import FRAME_SAMPLES, SAMPLE_RATE, AudioFrame, CancelToken, VoiceError, VoiceParams  # noqa: E402

PHRASE = "Hola, soy Drakter. Esta es una prueba de voz en español."


def ask(msg: str) -> bool:
    try:
        return input(f"{msg} [s/N] ").strip().lower() in {"s", "si", "sí", "y", "yes"}
    except EOFError:
        return False


def step(n: int, title: str) -> None:
    print(f"\n=== Paso {n}: {title} ===")


def list_devices() -> None:
    shown = False
    if shutil.which("pw-cli"):
        r = subprocess.run(["pw-cli", "ls", "Node"], capture_output=True, text=True, timeout=10)
        names = [ln.strip() for ln in r.stdout.splitlines() if "node.description" in ln or "media.class" in ln]
        if names:
            print("PipeWire (nodos):")
            print("\n".join("  " + n for n in names))
            shown = True
    if shutil.which("arecord"):
        print("ALSA (entradas):")
        print(subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=10).stdout or "  (ninguna)")
        shown = True
    if not shown:
        print("No hay pw-cli ni arecord: instala pipewire-utils o alsa-utils.")
    print("Para elegir uno: DRAKTER_AUDIO_INPUT=<nombre> DRAKTER_AUDIO_OUTPUT=<nombre>")


def record(cfg, seconds: float) -> np.ndarray:
    from voice.audio.backends import open_capture

    frames: list[np.ndarray] = []
    errors: list[VoiceError] = []
    cap = open_capture(cfg)
    cap.start(lambda f: frames.append(f.pcm), errors.append)
    try:
        time.sleep(seconds)
    finally:
        cap.stop()  # el micrófono se cierra siempre
    print("Micrófono cerrado." if not cap.active else "AVISO: la captura sigue activa.")
    if errors:
        raise errors[0]
    return np.concatenate(frames) if frames else np.zeros(0, dtype=np.float32)


def play(cfg, pcm: np.ndarray, rate: int) -> None:
    from voice.audio.backends import open_sink

    sink = open_sink(cfg)
    sink.open(rate)
    try:
        step_n = rate // 10
        for i in range(0, len(pcm), step_n):
            sink.write(np.ascontiguousarray(pcm[i : i + step_n], dtype=np.float32))
        sink.drain()
    finally:
        sink.close()


def level(pcm: np.ndarray) -> None:
    if not len(pcm):
        print("No llegó ningún audio del micrófono.")
        return
    rms = float(np.sqrt(np.mean(pcm**2)))
    peak = float(np.abs(pcm).max())
    db = 20 * np.log10(max(rms, 1e-9))
    print(f"Duración {len(pcm) / SAMPLE_RATE:.1f} s | RMS {db:.1f} dBFS | pico {peak:.2f}"
          + ("  <- CLIPPING: baja la ganancia" if peak >= 0.99 else ""))
    if rms < 0.002:
        print("Nivel muy bajo: ¿micrófono silenciado o dispositivo equivocado?")


def vad_run(cfg, pcm: np.ndarray) -> list[float]:
    from voice import registry

    vad = registry.build_vad(cfg)
    try:
        vad.load()
    except VoiceError as exc:
        print(f"Silero no disponible ({exc.code}); uso EnergyVAD.")
        vad = registry.build_vad(dataclasses.replace(cfg, vad_provider="energy"))
        vad.load()
    probs = []
    for i in range(0, len(pcm) - FRAME_SAMPLES + 1, FRAME_SAMPLES):
        probs.append(vad.process(AudioFrame(pcm[i : i + FRAME_SAMPLES], time.perf_counter_ns())))
    vad.close()
    return probs


def vad_report(cfg, probs: list[float]) -> None:
    if not probs:
        return
    speech = sum(p >= cfg.vad_threshold for p in probs)
    print(f"VAD ({cfg.vad_provider}, umbral {cfg.vad_threshold}): {speech}/{len(probs)} tramas con voz "
          f"({speech * 32 / 1000:.1f} s), probabilidad máxima {max(probs):.2f}")


def synth(tts, text: str, voice: str | None) -> tuple[np.ndarray, int, float | None]:
    t0 = time.perf_counter()
    first, chunks, rate = None, [], 24000
    for ch in tts.synthesize(text, VoiceParams(voice=voice), CancelToken()):
        if first is None:
            first = time.perf_counter() - t0
        chunks.append(ch.pcm)
        rate = ch.sample_rate
    return (np.concatenate(chunks) if chunks else np.zeros(0, np.float32)), rate, first


def turn(cfg, pcm: np.ndarray) -> None:
    from voice import registry
    from voice.metrics import TurnMetrics

    m = TurnMetrics("mic_check")
    stt = registry.build_stt(cfg)
    stt.load()
    m.mark("speech_end")
    m.mark("stt_start")
    texts = []
    for seg in stt.transcribe(pcm, language=cfg.stt_language, cancel=CancelToken()):
        if not texts:
            m.mark("stt_first_segment")
        texts.append(seg.text)
    m.mark("stt_end")
    m.note("audio_s", round(len(pcm) / SAMPLE_RATE, 2))
    m.note("stt_provider", stt.name)
    m.note("stt_model", cfg.stt_model)
    text = " ".join(texts).strip()
    print(f"Transcripción: «{text or '(vacía)'}»")  # solo en pantalla; no se guarda
    stt.close()
    if not text:
        return
    m.mark("text_received")
    tts = registry.build_tts(cfg)
    tts.load()
    m.mark("tts_start")
    t0 = time.perf_counter()
    audio, rate, first = synth(tts, f"Has dicho: {text}", cfg.tts_voice if cfg.tts_provider == "kokoro" else None)
    if first is not None:
        m.mark("tts_first_audio")  # ver nota: la síntesis no es incremental en Kokoro
    m.note("tts_provider", tts.name)
    m.note("tts_audio_s", round(len(audio) / rate, 2))
    m.note("tts_synth_s", round(time.perf_counter() - t0, 2))
    m.mark("playback_start")
    play(cfg, audio, rate)
    m.mark("playback_end")
    tts.close()
    print("Marcas de voice.metrics (sin texto):")
    snap = m.snapshot()
    for k, v in snap.items():
        print(f"  {k}: {v}")


def barge_in(cfg, seconds: float) -> None:
    from voice import registry

    print("Esta prueba reproduce una frase por el altavoz mientras el micrófono escucha EN SILENCIO.")
    print("No hables. Sirve para saber si el eco del altavoz activa el VAD (riesgo de falso barge-in).")
    tts = registry.build_tts(cfg)
    tts.load()
    audio, rate, _ = synth(tts, PHRASE + " " + PHRASE, cfg.tts_voice if cfg.tts_provider == "kokoro" else None)
    tts.close()
    cap_frames: list[np.ndarray] = []
    from voice.audio.backends import open_capture

    cap = open_capture(cfg)
    cap.start(lambda f: cap_frames.append(f.pcm), lambda e: None)
    th = threading.Thread(target=play, args=(cfg, audio, rate))
    th.start()
    th.join()
    time.sleep(0.3)
    cap.stop()
    pcm = np.concatenate(cap_frames) if cap_frames else np.zeros(0, np.float32)
    level(pcm)
    probs = vad_run(cfg, pcm)
    vad_report(cfg, probs)
    thr, need = cfg.barge_in_threshold, max(1, cfg.barge_in_min_ms // 32)
    run = best = 0
    for p in probs:
        run = run + 1 if p >= thr else 0
        best = max(best, run)
    print(f"Racha máxima por encima del umbral de barge-in ({thr}): {best} tramas; se necesitan {need} "
          f"({cfg.barge_in_min_ms} ms).")
    print("Resultado:", "ECO DETECTADO: deja DRAKTER_VOICE_BARGE_IN=false o usa auriculares." if best >= need
          else "Sin eco suficiente para disparar barge-in con esta configuración. Repite con distinto volumen.")


def voices(cfg) -> None:
    from voice import registry

    for engine in ("kokoro", "piper"):
        c = dataclasses.replace(cfg, tts_provider=engine, tts_fallback="")
        print(f"\n--- {engine} ---")
        try:
            tts = registry.build_tts(c)
            tts.load()
            audio, rate, first = synth(tts, PHRASE, c.tts_voice if engine == "kokoro" else None)
            tts.close()
        except VoiceError as exc:
            print(f"No disponible ({exc.code}): {exc.message}")
            continue
        print(f"Síntesis de {len(audio) / rate:.1f} s de audio; primer audio a los {first:.2f} s. Reproduciendo...")
        play(c, audio, rate)
    print("\nAnota cuál suena mejor en español y revisa la licencia de cada voz en su ficha.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=float, default=5.0, help="duración de la grabación (solo memoria)")
    ap.add_argument("--barge-in", action="store_true", help="prueba de eco para la interrupción por voz")
    ap.add_argument("--voices", action="store_true", help="comparar las voces Kokoro y Piper")
    a = ap.parse_args()
    cfg = load_config()
    print(f"Memoria disponible: {C.meminfo_mb('MemAvailable')} MB | carga: {C.loadavg()}")

    try:
        if a.voices:
            voices(cfg)
            return 0
        step(1, "Dispositivos de audio")
        list_devices()
        if a.barge_in:
            if not ask("\nVa a sonar audio y se abrirá el micrófono. ¿Continuar?"):
                return 0
            barge_in(cfg, a.seconds)
            return 0
        step(2, f"Grabación de {a.seconds:.0f} s (solo en memoria)")
        print("Se va a ABRIR EL MICRÓFONO. Cuando empiece, di una frase en español, por ejemplo: «Recuérdame comprar pan».")
        if not ask("¿Abrir el micrófono ahora?"):
            print("Cancelado: no se abrió el micrófono.")
            return 0
        print("Grabando...")
        pcm = record(cfg, a.seconds)
        step(3, "Nivel")
        level(pcm)
        if not len(pcm):
            return 1
        step(4, "Detección de voz (VAD)")
        vad_report(cfg, vad_run(cfg, pcm))
        step(5, "Reproducción de lo grabado")
        if ask("¿Reproducirlo? (si no usas auriculares puede dar eco)"):
            play(cfg, pcm, SAMPLE_RATE)
        step(6, "Turno completo STT -> TTS")
        if ask("¿Probar la transcripción y la respuesta hablada? (necesita los modelos)"):
            turn(cfg, pcm)
    except VoiceError as exc:
        print(f"\nFALLO {exc.code}: {exc.message}")
        return 1
    except ImportError as exc:
        print(f"\nFalta un módulo del frente de voz o una dependencia: {exc}")
        return 1
    print("\nHecho. Nada de audio se guardó en disco.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
