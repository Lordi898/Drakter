# tools/wakeword — palabras de activación propias en castellano

Kit para entrenar «Jarvis», «Drakter» y «despierta» (es-ES) como modelos de
[openWakeWord](https://github.com/dscripka/openWakeWord) compatibles con el `openwakeword==0.4.0` de
Drakter. La guía para el usuario está en [`docs/usage/palabras-activacion.md`](../../docs/usage/palabras-activacion.md).

| Archivo | Qué es |
|---|---|
| `entrenar_palabras_drakter.ipynb` | Cuaderno de Google Colab (GPU): síntesis, aumentación, entrenamiento, métricas y exportación a ONNX |
| `grabar_muestras.py` | Graba 20-30 tomas de tu voz por palabra (y voz normal como negativo) y crea `muestras_drakter.zip` |

## Método

Sigue la receta del cuaderno oficial `notebooks/automatic_model_training.ipynb` y de `openwakeword/train.py`
(rama `main`), con tres cambios:

1. **Positivos en castellano.** El generador oficial (`piper-sample-generator`, LibriTTS) solo habla inglés.
   Aquí se sintetiza con `piper-tts==1.8.0` (voces `es_ES`) y `kokoro-onnx==0.6.1` (voces `es` y mezclas de
   estilos), con velocidad, entonación y hablante al azar.
2. **Negativos con el embedding de Drakter.** El `embedding_model.onnx` de la release v0.5.1 que descarga el
   cuaderno oficial **no es el mismo archivo** que trae la rueda `openwakeword==0.4.0` (el que instala Drakter):
   con el mismo audio, sus salidas correlan ≈0,99 pero difieren. Por eso el cuaderno usa la rueda 0.4.0 y calcula
   todas las características (positivos, negativos y validación) con ese embedding. Las 2000 h precalculadas de
   ACAV100M quedan como opción (`USAR_ACAV`), desactivada.
3. **Métricas en castellano.** Los falsos positivos por hora se miden en voz castellana de hablantes que no
   están en el entrenamiento (MLS `test`) y en una parte reservada de AudioSet, contando activaciones (con 2 s de
   refractario, como la puerta de Drakter) en vez de ventanas.

Lo demás es igual que en el oficial: clips de 2 s con la palabra al final, red DNN
(Flatten → Linear → LayerNorm → ReLU → bloque → Linear → Sigmoid) con entrada `(1, 16, 96)` y salida `(1, 1)`,
ejemplos difíciles, peso de negativos en rampa hasta 1000, *warmup* + coseno y exportación ONNX opset 13.
El cuaderno comprueba al final que cada `.onnx` carga con `openwakeword.model.Model` 0.4.0 y puntúa en streaming
de 80 ms, igual que `voice/providers/wake/openwakeword_gate.py`.

Fish Audio no se usa: haría falta la clave y red, el modelo gratuito caduca y solo podrían usarse voces oficiales.

## Datos, modelos y licencias

Nada de esto se versiona ni se redistribuye: se descarga en Colab para un uso personal.

| Recurso | Origen | Licencia |
|---|---|---|
| openWakeWord 0.4.0 (código, `melspectrogram.onnx`, `embedding_model.onnx`) | PyPI `openwakeword==0.4.0` | Apache-2.0 (el embedding deriva de `google/speech_embedding`, Apache-2.0) |
| piper-tts 1.8.0 | PyPI | GPL-3.0-or-later (solo como herramienta en Colab) |
| Voz Piper `es_ES-carlfm-x_low` | `rhasspy/piper-voices` | Dataset de dominio público |
| Voz Piper `es_ES-davefx-medium` | `rhasspy/piper-voices` | CC0 |
| Voces Piper `es_ES-mls_9972-low`, `es_ES-mls_10246-low` | `rhasspy/piper-voices` | CC BY 4.0 (MLS) |
| Voz Piper `es_ES-sharvard-medium` (2 hablantes) | `rhasspy/piper-voices` | CC BY 3.0 |
| Kokoro-82M v1.0 (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) | `thewh1teagle/kokoro-onnx` release `model-files-v1.0` | Apache-2.0 |
| Multilingual LibriSpeech, español | `facebook/multilingual_librispeech` | CC BY 4.0 |
| AudioSet (balanced train) | `agkphysics/AudioSet` | CC BY 4.0 (audio procedente de YouTube) |
| Respuestas al impulso del MIT (IR Survey) | `davidscripka/MIT_environmental_impulse_responses` | No indicada en la copia de Hugging Face |
| ACAV100M precalculado (opcional, apagado) | `davidscripka/openwakeword_features` | CC BY-NC-SA 4.0 |

Si activas `USAR_ACAV`, el modelo resultante hereda la restricción no comercial (los modelos preentrenados
de openWakeWord, como `hey_jarvis_v0.1`, ya la tienen por el mismo motivo).

## Comprobación hecha

El cuaderno es JSON válido de nbformat 4 y todas sus celdas compilan. Además se ejecutó entero en CPU, con
`DRAKTER_WW_PRUEBA=1` (30 positivos por palabra, 300 pasos, 3 min de voz real, sin AudioSet), desde las
descargas hasta la exportación y la carga con `openwakeword` 0.4.0. Con tan pocos datos las métricas no
significan nada; solo validan la tubería. En una segunda pasada con 120 positivos por palabra, 2000 pasos y LR 1e-3,
la red llegó a un recall en validación del 50-92 % según la palabra, así que la tubería aprende. Nadie lo ha
ejecutado todavía en Colab con los valores por defecto. Para repetirlo:

```bash
V=~/.local/share/drakter/venvs/wakeword-train
uv venv -p 3.12 $V
VIRTUAL_ENV=$V uv pip install --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu \
    torch openwakeword==0.4.0 piper-tts==1.8.0 kokoro-onnx==0.6.1 soundfile scipy onnx onnxscript pyarrow \
    huggingface_hub nbformat tqdm scikit-learn
DRAKTER_WW_PRUEBA=1 $V/bin/python -I -c '
import nbformat, sys
nb = nbformat.read(sys.argv[1], as_version=4); ns = {}
for c in nb.cells:
    if c.cell_type == "code": exec(c.source, ns)
' tools/wakeword/entrenar_palabras_drakter.ipynb
```

Tarda unos 5 minutos y deja los datos en `~/.local/share/drakter/wakeword/trabajo/` (`DRAKTER_WW_DIR` lo cambia).
