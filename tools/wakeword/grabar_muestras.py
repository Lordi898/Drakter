"""Graba muestras reales de tu voz para entrenar las palabras de activación de Drakter.

Uso (con el venv de voz de Drakter, que ya trae soundfile y numpy). Graba con `pw-record` (PipeWire)
o, si no está, con `arecord` (ALSA); con PortAudio instalado también vale `sounddevice`:

    ~/.local/share/drakter/venvs/voice/bin/python tools/wakeword/grabar_muestras.py
    ~/.local/share/drakter/venvs/voice/bin/python tools/wakeword/grabar_muestras.py --palabras jarvis --n 30
    ~/.local/share/drakter/venvs/voice/bin/python tools/wakeword/grabar_muestras.py --negativas 120

Por cada palabra graba `--n` tomas de `--segundos` s (16 kHz, mono). Al acabar crea
`muestras_drakter.zip` con carpetas `jarvis/`, `drakter/`, `despierta/` (y `negativas/`), que el
cuaderno `entrenar_palabras_drakter.ipynb` lee desde `MyDrive/Drakter/muestras_drakter.zip`.
Las grabaciones se quedan en tu ordenador (`~/.local/share/drakter/wakeword/muestras`) y no van al repo.
"""

from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    import sounddevice as sd
except (ImportError, OSError):  # sin PortAudio en el sistema
    sd = None

SR = 16000
PALABRAS = {"jarvis": "Jarvis", "drakter": "Drakter", "despierta": "Despierta"}
CONSEJOS = [
    "normal", "más bajo", "más alto", "rápido", "despacio", "desde más lejos",
    "con «oye» delante", "como pregunta", "con prisa", "girando la cabeza",
]
DESTINO = Path.home() / ".local/share/drakter/wakeword/muestras"


def grabador() -> str:
    for nombre in ("pw-record", "arecord"):
        if shutil.which(nombre):
            return nombre
    if sd is not None:
        return "sounddevice"
    sys.exit("No encuentro con qué grabar: instala pipewire (pw-record) o alsa-utils (arecord).")


def grabar(segundos: float, dispositivo: str | None, metodo: str) -> np.ndarray:
    if metodo == "sounddevice":
        dev = int(dispositivo) if dispositivo and dispositivo.isdigit() else dispositivo
        audio = sd.rec(int(segundos * SR), samplerate=SR, channels=1, dtype="int16", device=dev)
        sd.wait()
        return audio[:, 0]
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "toma.wav"
        if metodo == "pw-record":
            cmd = ["pw-record", "--rate", str(SR), "--channels", "1", "--format", "s16"]
            cmd += ["--target", dispositivo] if dispositivo else []
        else:
            cmd = ["arecord", "-q", "-f", "S16_LE", "-r", str(SR), "-c", "1"]
            cmd += ["-D", dispositivo] if dispositivo else []
        proc = subprocess.Popen([*cmd, str(wav)], stderr=subprocess.PIPE)
        time.sleep(segundos + 0.15)
        proc.send_signal(signal.SIGINT)  # cierra el WAV limpio
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        if not wav.is_file() or wav.stat().st_size <= 44:
            err = proc.stderr.read().decode(errors="replace").strip() if proc.stderr else ""
            sys.exit(f"{metodo} no grabó nada. {err}")
        x, sr = sf.read(wav, dtype="int16", always_2d=True)
    x = x[:, 0]
    if sr != SR:
        sys.exit(f"{metodo} grabó a {sr} Hz en vez de {SR}")
    return x[: int(segundos * SR)]


def comprobar(x: np.ndarray) -> str | None:
    pico = int(np.abs(x).max()) if len(x) else 0
    if pico < 800:
        return "casi no se oye nada (¿micrófono silenciado o lejos?)"
    if pico >= 32000:
        return "satura (habla un poco más bajo o aleja el micrófono)"
    return None


def siguiente(carpeta: Path) -> int:
    nums = [int(p.stem) for p in carpeta.glob("*.wav") if p.stem.isdigit()]
    return max(nums, default=0) + 1


def sesion_palabra(clave: str, n: int, segundos: float, dispositivo: str | None, metodo: str) -> None:
    carpeta = DESTINO / clave
    carpeta.mkdir(parents=True, exist_ok=True)
    texto = PALABRAS[clave]
    print(f"\n=== «{texto}»: {n} tomas de {segundos:.1f} s. Enter = grabar, r = repetir la última, q = terminar.")
    hechas, ultima = 0, None
    while hechas < n:
        consejo = CONSEJOS[hechas % len(CONSEJOS)]
        orden = input(f"[{hechas + 1}/{n}] Di «{texto}» ({consejo}) y pulsa Enter... ").strip().lower()
        if orden == "q":
            break
        if orden == "r" and ultima is not None:
            ultima.unlink(missing_ok=True)
            hechas -= 1
            print("  borrada la última toma")
            ultima = None
            continue
        print("  ● grabando...", end="", flush=True)
        x = grabar(segundos, dispositivo, metodo)
        aviso = comprobar(x)
        if aviso:
            print(f"\r  ✗ {aviso}; repite.      ")
            continue
        ultima = carpeta / f"{siguiente(carpeta):03d}.wav"
        sf.write(ultima, x, SR, subtype="PCM_16")
        hechas += 1
        print(f"\r  ✓ guardada {ultima.name}      ")


def sesion_negativas(segundos: float, dispositivo: str | None, metodo: str) -> None:
    carpeta = DESTINO / "negativas"
    carpeta.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Voz normal (negativos): {segundos:.0f} s hablando de cualquier cosa SIN decir las palabras.")
    print("Lee un texto en voz alta, cuenta tu día o pon la tele de fondo.")
    input("Pulsa Enter para empezar... ")
    print("  ● grabando...", flush=True)
    x = grabar(segundos, dispositivo, metodo)
    destino = carpeta / f"{siguiente(carpeta):03d}.wav"
    sf.write(destino, x, SR, subtype="PCM_16")
    print(f"  ✓ guardada {destino.name}")


def empaquetar() -> Path:
    zip_path = DESTINO.parent / "muestras_drakter.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for wav in sorted(DESTINO.glob("*/*.wav")):
            z.write(wav, f"{wav.parent.name}/{wav.name}")
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--palabras", nargs="+", choices=list(PALABRAS), default=list(PALABRAS))
    ap.add_argument("--n", type=int, default=25, help="tomas por palabra (20-30 recomendado)")
    ap.add_argument("--segundos", type=float, default=2.0, help="duración de cada toma")
    ap.add_argument("--negativas", type=float, default=0, metavar="S",
                    help="graba además S segundos de voz normal como negativos (p. ej. 120)")
    ap.add_argument("--dispositivo", default=None,
                    help="micrófono: nodo de PipeWire (`wpctl status`) o dispositivo ALSA (`arecord -L`); "
                         "por defecto, el del sistema")
    args = ap.parse_args()

    metodo = grabador()
    print(f"Grabo con {metodo} ({args.dispositivo or 'micrófono por defecto'}) | carpeta: {DESTINO}")
    try:
        for clave in args.palabras:
            sesion_palabra(clave, args.n, args.segundos, args.dispositivo, metodo)
        if args.negativas > 0:
            sesion_negativas(args.negativas, args.dispositivo, metodo)
    except KeyboardInterrupt:
        print("\nInterrumpido; se empaqueta lo grabado hasta ahora.")
    zip_path = empaquetar()
    cuenta = {p.name: len(list(p.glob("*.wav"))) for p in sorted(DESTINO.iterdir()) if p.is_dir()}
    print(f"\nTomas: {cuenta}\nZIP: {zip_path}\nSúbelo a Google Drive como MyDrive/Drakter/muestras_drakter.zip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
