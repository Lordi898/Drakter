# Instalar la voz

> **Estado:** `voice/` está en `drakter/integracion` (`2e05ba6`), con su propio `pyproject.toml` (extras `stt`, `kokoro`, `wakeword`). En esta máquina solo hay modelo Kokoro en `/var/tmp/drakter-voz/models` y ningún venv de voz con sus extras. El router de voz del backend no se monta todavía. NO COMPROBADO de principio a fin.

La voz es un proceso aparte con su propio entorno Python, que arranca el backend. Escucha, transcribe (Whisper) y habla (Kokoro, con Piper de respaldo), todo en local y en CPU.

## Qué falta en la rama hoy

- `voice/CONTRACT.md` lista `manager.py`, `registry.py`, `ipc.py`, `service.py`, `__main__.py` y `metrics.py`, pero **no están en la rama** `drakter/voz`. Sin ellos `python -m voice` no puede arrancar.
- `backend/app/main.py` de esa rama no registra el servicio de voz (el contrato dice que lo hace el integrador).
- `desktop/src` no tiene ninguna pantalla ni botón de voz.

Mientras tanto solo se puede preparar el entorno, los modelos y los scripts de `voice/tests/`.

## 1. Entorno de voz

Requiere Python 3.12 y `uv`. Desde la raíz del repositorio:

```bash
cd voice
uv venv --python 3.12 .venv
uv sync --extra stt --extra kokoro
```

`--extra wakeword` solo si tienes un modelo propio de palabra de activación (ver [Uso de la voz](../usage/voz.md)).

## 2. Entorno de Piper (respaldo)

Piper es GPL y va en un venv separado, invocado solo como proceso:

```bash
uv venv --python 3.12 ~/.local/share/drakter/voice/piper-venv
uv pip install --python ~/.local/share/drakter/voice/piper-venv/bin/python piper-tts
export DRAKTER_PIPER_PYTHON=~/.local/share/drakter/voice/piper-venv/bin/python
```

Sin `DRAKTER_PIPER_PYTHON` el respaldo no funciona. Para desactivarlo, `DRAKTER_TTS_FALLBACK=` (vacío).

## 3. Modelos

La voz **nunca descarga nada**. Si falta un modelo da el error `model_missing` con la ruta esperada. Carpeta base: `DRAKTER_VOICE_MODELS_DIR`, o `~/.local/share/drakter/voice/models`. Los comandos vienen del README de la rama y **no se han ejecutado**; comprueba la sintaxis con tu versión de cada herramienta.

| Motor | Carpeta | Archivos / comando (según el README) |
|---|---|---|
| Whisper | `<models>/whisper` | `hf download Systran/faster-whisper-small --cache-dir <models>/whisper` (`...-medium` para probar `medium`) |
| Kokoro | `<models>/kokoro` | `kokoro-v1.0.int8.onnx` y `voices-v1.0.bin`, de las releases de `thewh1teagle/kokoro-onnx` (`model-files-v1.0`) con `curl -L -o <archivo> <url>` |
| Piper | `<models>/piper` | `es_ES-davefx-medium.onnx` y `.onnx.json`: `hf download rhasspy/piper-voices --include 'es/es_ES/davefx/medium/*' --local-dir <tmp>` y copiar los dos archivos |
| Silero VAD | incluido en `faster-whisper` | Opcional: `<models>/silero/silero_vad_v6.onnx` lo sustituye. Sin modelo se usa `EnergyVAD` |

Los nombres de archivo coinciden con el código (`voice/tts/kokoro.py`, `voice/tts/piper.py`, `voice/vad/silero.py`). Revisa la licencia de cada voz antes de distribuir nada.

## 4. Activar en el backend

El backend solo lanza la voz con estas dos variables (en el entorno o en `~/.config/drakter/.env`):

```bash
DRAKTER_VOICE_ENABLED=true
DRAKTER_VOICE_PYTHON=/ruta/absoluta/a/voice/.venv/bin/python
```

Por defecto `DRAKTER_VOICE_ENABLED=false`. `DRAKTER_VOICE_PYTHON` debe ser absoluta y existir; si no, el backend arranca igual y reporta `dependency_missing`. Opcional: `DRAKTER_VOICE_PROJECT_ROOT` (por defecto, la raíz del repo).

## 5. Variables DRAKTER_*

El backend pasa al proceso de voz solo estas variables (lista cerrada, tomadas del entorno o del `.env`). Valores por defecto de `voice/config.py`:

| Variable | Defecto |
|---|---|
| `DRAKTER_VOICE_MODELS_DIR` | `<data_dir>/voice/models` |
| `DRAKTER_STT_PROVIDER` / `_MODEL` / `_LANGUAGE` | `faster_whisper` / `small` / `es` |
| `DRAKTER_STT_DEVICE` / `_COMPUTE_TYPE` | `cpu` (solo admite `cpu`) / `int8` |
| `DRAKTER_STT_BEAM_SIZE` / `_THREADS` | `1` / `4` |
| `DRAKTER_TTS_PROVIDER` / `_FALLBACK` / `_VOICE` | `kokoro` / `piper` / `ef_dora` |
| `DRAKTER_TTS_THREADS` | `4` |
| `DRAKTER_PIPER_PYTHON` / `_VOICE` | sin definir / `es_ES-davefx-medium` |
| `DRAKTER_VAD_PROVIDER` / `_THRESHOLD` | `silero` / `0.5` |
| `DRAKTER_VAD_SILENCE_MS` / `_PREROLL_MS` | `800` / `320` |
| `DRAKTER_VOICE_MAX_UTTERANCE_S` | `30` |
| `DRAKTER_WAKEWORD_ENABLED` / `_PROVIDER` | `false` / `null` |
| `DRAKTER_WAKEWORD_MODEL` / `_THRESHOLD` | sin definir / `0.5` |
| `DRAKTER_VOICE_BARGE_IN` (+ `_THRESHOLD`, `_MIN_MS`) | `false` (`0.8`, `320`) |
| `DRAKTER_AUDIO_BACKEND` | `auto` (`pipewire`, `alsa`, `null`) |
| `DRAKTER_AUDIO_INPUT` / `_OUTPUT` | vacío (dispositivo por defecto) |
| `DRAKTER_VOICE_LEVEL_HZ` / `_OUTPUT_LATENCY_MS` | `15` / `0` |

## 6. Prueba guiada del micrófono (te toca a ti)

Desde la raíz del repo, con el Python del venv de voz:

```bash
PY=voice/.venv/bin/python
export TMPDIR=/var/tmp/drakter-voz
$PY voice/tests/mic_check.py             # dispositivos, nivel, VAD, turno STT -> TTS
$PY voice/tests/mic_check.py --barge-in  # eco del altavoz en el micrófono
$PY voice/tests/mic_check.py --voices    # oír Kokoro y Piper en español
```

El script pide confirmación antes de abrir el micrófono (responde `s`). Graba 5 s por defecto (`--seconds`), solo en memoria. Anota qué te sale en cada paso: dispositivo elegido, si el VAD detecta tu voz, si la transcripción es correcta y qué voz prefieres. Usa `--barge-in` con tus altavoces antes de poner `DRAKTER_VOICE_BARGE_IN=true`.

## 7. Benchmark de latencia

Necesitas un WAV tuyo con una frase en español (`frase.wav`) y los modelos en su sitio. Con la máquina en reposo:

```bash
$PY voice/tests/bench_engines.py --stt-model small  --wav frase.wav --tts kokoro --out $TMPDIR/small_kokoro.json
$PY voice/tests/bench_engines.py --stt-model medium --wav frase.wav --out $TMPDIR/medium.json
$PY voice/tests/bench_engines.py --tts piper --out $TMPDIR/piper.json
```

Opciones: `--threads N`, `--reps N`, `--min-available-mb N`. Cada cifra sale con `loadavg` y RSS. Esta guía no da tiempos esperados: compara `small` y `medium` con tus propios datos. Los números del README (carga de CPU alta, 4 hilos) son orientativos y no valen como referencia.

Para comprobar sin hardware: `$PY voice/tests/check_pipeline.py`. Declara NO COMPROBADO hasta que exista `voice/manager.py`.

## Problemas frecuentes

- `model_missing`: falta un modelo; la ruta esperada va en el mensaje. Descárgalo a mano (paso 3).
- `dependency_missing`: `DRAKTER_VOICE_PYTHON` no es una ruta absoluta a un archivo existente.
- No suena el respaldo: falta `DRAKTER_PIPER_PYTHON`.
