# Drakter Voice

Pipeline de voz local de Drakter: escucha (VAD, pulsar para hablar), transcribe (STT), habla (TTS) y avisa de los niveles para la boca del personaje. Corre en su propio proceso y venv, arrancado por el backend. No conoce Hermes, la BD ni las confirmaciones: recibe texto para decir y entrega texto transcrito. Contrato completo en `CONTRACT.md`.

## Arquitectura

1. `voice/vad/`: `SileroVAD` (ONNX, sin torch) y `EnergyVAD` como reserva sin modelo.
2. `voice/wakeword/`: `NullWakeWord` por defecto; `OpenWakeWordProvider` solo con modelo propio.
3. `voice/stt/`: `FasterWhisperSTT`, solo CPU, `int8`.
4. `voice/tts/`: `KokoroTTS` principal, `PiperTTS` de respaldo como proceso externo, unidos por `FallbackTTS`.
5. `voice/audio/`: captura y altavoz mediante procesos externos de PipeWire o ALSA; `NullCapture`/`NullSink` sin hardware.
6. `voice/personality/`: normaliza el texto, lo trocea en frases y decide los parámetros de voz que el motor soporta de verdad.
7. `voice/manager.py`: máquina de estados `idle > listening > transcribing > waiting > speaking`; VAD, STT y TTS en hilos distintos.
8. `voice/ipc.py`: socket Unix `<runtime_dir>/voice.sock` (JSON por líneas, 0600). No viaja audio por él.
9. `voice/metrics.py`: marcas de tiempo por turno (`voice.metrics`), sin texto.
10. Nada se graba ni se descarga solo: si falta un modelo, error `model_missing` con la ruta esperada.

## Instalación

Python 3.12, con `uv`, desde `voice/`:

```bash
cd voice
uv venv --python 3.12 .venv
uv sync --extra stt --extra kokoro          # alternativa: uv pip install "faster-whisper==1.2.1" "kokoro-onnx==0.6.1" numpy onnxruntime
# openWakeWord solo si tienes un modelo propio:  uv sync --extra stt --extra kokoro --extra wakeword
```

Piper (GPL-3.0-or-later) va en un entorno aparte y solo se invoca como proceso:

```bash
uv venv --python 3.12 ~/.local/share/drakter/voice/piper-venv
uv pip install --python ~/.local/share/drakter/voice/piper-venv/bin/python piper-tts
export DRAKTER_PIPER_PYTHON=~/.local/share/drakter/voice/piper-venv/bin/python
```

## Modelos

`<models>` es `DRAKTER_VOICE_MODELS_DIR`, o por defecto `~/.local/share/drakter/voice/models`. Los comandos de descarga son manuales (la voz nunca descarga nada) y **no se han ejecutado desde este README**: compruébalos con tu versión de las herramientas.

| Motor | Ruta | Cómo obtenerlo |
|---|---|---|
| Whisper | `<models>/whisper` | `hf download Systran/faster-whisper-small --cache-dir <models>/whisper` (y `...-medium` para probar `medium`). El nombre `small`/`medium` se resuelve en esa caché. También vale una carpeta con el modelo y `DRAKTER_STT_MODEL=<ruta absoluta>`. |
| Kokoro | `<models>/kokoro` | `kokoro-v1.0.int8.onnx` y `voices-v1.0.bin` de las releases de `thewh1teagle/kokoro-onnx` (`model-files-v1.0`), por ejemplo con `curl -L -o <archivo> <url de la release>`. |
| Piper | `<models>/piper` | `es_ES-davefx-medium.onnx` y `es_ES-davefx-medium.onnx.json` del repositorio `rhasspy/piper-voices` (`es/es_ES/davefx/medium/`), por ejemplo con `hf download rhasspy/piper-voices --include 'es/es_ES/davefx/medium/*' --local-dir <tmp>` y copiando los dos archivos. |
| Silero VAD | incluido en `faster-whisper` | Opcional: `<models>/silero/silero_vad_v6.onnx` lo sustituye. Sin modelo, `EnergyVAD`. |
| Wake word | `DRAKTER_WAKEWORD_MODEL` | Modelo propio ONNX. |

Licencias de las voces: revisa la ficha de cada voz (la de `es_ES-davefx` en `rhasspy/piper-voices` y la de las voces de Kokoro) antes de distribuir nada; este README no las da por buenas.

**Wake word.** No hay modelo para «Drakter»: los preentrenados de openWakeWord son para otras palabras y su licencia es CC BY-NC-SA 4.0 (no comercial), así que el proveedor solo carga un modelo propio y nunca descarga ninguno. Hasta entonces `wakeword_provider=null` y el modo es pulsar para hablar. Entrenar uno propio queda pendiente; ver la documentación del proyecto openWakeWord si se quiere hacer.

## Variables de entorno

Valores por defecto copiados de `voice/config.py` (`load_config()`).

| Variable | Defecto |
|---|---|
| `DRAKTER_RUNTIME_DIR` | `$XDG_RUNTIME_DIR/drakter` (o `/run/user/<uid>/drakter`) |
| `DRAKTER_DATA_DIR` | `~/.local/share/drakter` |
| `DRAKTER_VOICE_MODELS_DIR` | `<data_dir>/voice/models` |
| `DRAKTER_STT_PROVIDER` | `faster_whisper` |
| `DRAKTER_STT_MODEL` | `small` |
| `DRAKTER_STT_DEVICE` | `cpu` (solo se admite `cpu`) |
| `DRAKTER_STT_COMPUTE_TYPE` | `int8` |
| `DRAKTER_STT_LANGUAGE` | `es` |
| `DRAKTER_STT_BEAM_SIZE` | `1` |
| `DRAKTER_STT_THREADS` | `4` |
| `DRAKTER_TTS_PROVIDER` | `kokoro` |
| `DRAKTER_TTS_FALLBACK` | `piper` (vacío lo desactiva) |
| `DRAKTER_TTS_VOICE` | `ef_dora` |
| `DRAKTER_TTS_THREADS` | `4` |
| `DRAKTER_PIPER_PYTHON` | sin definir |
| `DRAKTER_PIPER_VOICE` | `es_ES-davefx-medium` |
| `DRAKTER_VAD_PROVIDER` | `silero` |
| `DRAKTER_VAD_THRESHOLD` | `0.5` |
| `DRAKTER_VAD_SILENCE_MS` | `800` |
| `DRAKTER_VAD_PREROLL_MS` | `320` |
| `DRAKTER_VOICE_MAX_UTTERANCE_S` | `30` |
| `DRAKTER_WAKEWORD_ENABLED` | `false` |
| `DRAKTER_WAKEWORD_PROVIDER` | `null` |
| `DRAKTER_WAKEWORD_MODEL` | sin definir |
| `DRAKTER_WAKEWORD_THRESHOLD` | `0.5` |
| `DRAKTER_VOICE_BARGE_IN` | `false` |
| `DRAKTER_VOICE_BARGE_IN_THRESHOLD` | `0.8` |
| `DRAKTER_VOICE_BARGE_IN_MIN_MS` | `320` |
| `DRAKTER_AUDIO_BACKEND` | `auto` (`auto`, `pipewire`, `alsa`, `null`) |
| `DRAKTER_AUDIO_INPUT` | vacío (dispositivo por defecto) |
| `DRAKTER_AUDIO_OUTPUT` | vacío (dispositivo por defecto) |
| `DRAKTER_VOICE_LEVEL_HZ` | `15` |
| `DRAKTER_VOICE_OUTPUT_LATENCY_MS` | `0` |

## Licencias

- Piper: GPL-3.0-or-later. Por eso va en un entorno aparte y solo como proceso externo (`voice/tts/piper.py`); nada de Piper se importa en este proceso.
- openWakeWord: código Apache-2.0; los modelos preentrenados, CC BY-NC-SA 4.0. Aquí solo se usa con modelo propio.
- Kokoro-82M (pesos): Apache-2.0. `kokoro-onnx`: MIT.
- Faster-Whisper: MIT. Silero VAD: MIT.
- Cada voz o modelo concreto puede tener su propia licencia: mira su ficha.

## Comprobación pendiente

Los tres scripts viven en `voice/tests/`. Se ejecutan desde la raíz del repositorio con el Python del venv de voz. Ninguno guarda audio ni imprime transcripciones en los archivos que escribe.

```bash
PY=voice/.venv/bin/python        # o el intérprete del venv de voz que uses
export TMPDIR=/var/tmp/drakter-voz   # no escribir en /tmp

# 1. Sin hardware ni modelos: turno completo, interrupción, cancelación y mic.set false
$PY voice/tests/check_pipeline.py

# 2. Latencia real (con la máquina en reposo; guarda loadavg y RSS junto a cada cifra).
#    Necesita un WAV propio con voz en español y los modelos en su sitio.
$PY voice/tests/bench_engines.py --stt-model small  --wav frase.wav --tts kokoro --out $TMPDIR/small_kokoro.json
$PY voice/tests/bench_engines.py --stt-model medium --wav frase.wav --out $TMPDIR/medium.json
$PY voice/tests/bench_engines.py --tts piper --out $TMPDIR/piper.json
#    Opciones: --threads N, --reps N, --min-available-mb N (se niega a empezar por debajo)

# 3. Con micrófono: guiada, pide confirmación antes de abrirlo
$PY voice/tests/mic_check.py                # dispositivos, nivel, VAD, turno STT -> TTS
$PY voice/tests/mic_check.py --barge-in     # eco del altavoz en el micrófono
$PY voice/tests/mic_check.py --voices       # oír Kokoro y Piper en español
```

Estado: los scripts compilan y `--help` funciona. Al escribirlos no existían aún `voice/manager.py`, `voice/registry.py`, `voice/metrics.py` ni `voice/audio/player.py`; por eso `check_pipeline.py` declara NO COMPROBADO hasta que exista el gestor, y `mic_check.py` y el benchmark (que usa el registro, o las clases directas si falta) no se han ejecutado contra motores reales.

Queda ⚠️ a cargo del usuario:

- ⚠️ Micrófono real: elegir dispositivo y comprobar nivel y VAD (`mic_check.py`).
- ⚠️ Eco y barge-in: `--barge-in` con tus altavoces; `DRAKTER_VOICE_BARGE_IN` sigue en `false` hasta entonces.
- ⚠️ Calidad de las voces en español: `--voices` (Kokoro `ef_dora` frente a Piper `es_ES-davefx-medium`) y licencia de cada voz.
- ⚠️ `medium` frente a `small`: ejecutar el benchmark con ambos sobre el mismo WAV y decidir con los datos.
- ⚠️ Latencia en esta máquina y, si existe otra, en la máquina objetivo: repetir el benchmark allí.
- ⚠️ Wake word: sin modelo propio, no se puede probar.

## Datos previos (drakter-5)

Medidos por drakter-5 con la máquina cargada (no en reposo), con Kokoro `ef_dora` en CPU; son orientativos, no un objetivo. Copiados de `results/kokoro_a_t4.json` (4 hilos, carga `load_start` 6.72, `avail_mb_start` 1435 MB, `rss_after_load.VmHWM` 195 MB, `load_s` 1.01), primera repetición:

| Frase | Caracteres | `wall` (s) | `dur` (s) | `rtf` | `load` |
|---|---|---|---|---|---|
| corta | 20 | 0.951 | 1.365 | 0.697 | 6.72 |
| media | 100 | 4.507 | 5.547 | 0.813 | 7.94 |
| larga | 306 | 11.913 | 16.811 | 0.709 | 7.79 |

Rehacer estas medidas en reposo con `bench_engines.py`; las de esta tabla no son una referencia de la máquina sin carga.
