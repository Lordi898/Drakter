# Palabras de activación propias («Jarvis», «Drakter», «despierta»)

Hoy Drakter se despierta con `hey_jarvis_v0.1`, el modelo en inglés que trae openWakeWord. Con voz castellana falla
a menudo. Esta guía explica cómo entrenar en Google Colab tus propios modelos en castellano de España para
«Jarvis» a secas, «Drakter» y «despierta», cómo instalarlos y cómo volver al modelo inglés.

**Estado:** el cuaderno se ha ejecutado entero en CPU con muy pocas muestras para comprobar que todo funciona de
principio a fin. Nadie lo ha ejecutado todavía en Colab con los valores reales, ni se han probado los modelos con
la app.

Cuando salta la palabra, Drakter comprueba además que el texto transcrito empiece por ella (lista `[wake]` de
`voice/conversation/layer0.es.toml`, que ya incluye «drakter», «despierta» y las variantes con que las escribe el
reconocimiento de voz). Si a veces se activa pero tu frase no llega al chat, es que el reconocimiento escribió la
palabra de otra forma: hay que añadir esa variante a la lista.

## Qué necesitas

- Una cuenta de Google con Colab (con Colab Pro va más rápido y no se corta).
- Google Drive si quieres guardar allí los resultados (ocupan menos de 5 MB). Las descargas grandes se quedan en Colab.
- Opcional: 10 minutos para grabar tu voz con el micrófono, que mejora mucho la detección.

## 1. (Opcional) Graba tu voz

Con 20-30 tomas por palabra el modelo aprende tu voz, tu micrófono y tu habitación. En tu ordenador, desde la
carpeta del repositorio:

```bash
~/.local/share/drakter/venvs/voice/bin/python tools/wakeword/grabar_muestras.py --negativas 120
```

Para cada palabra te pide pulsar Enter y decirla (cada toma dura 2 s). Te va sugiriendo variaciones: más bajo, más
alto, más rápido, desde lejos… Escribe `r` para repetir la última toma o `q` para pasar a la siguiente palabra.
`--negativas 120` graba además 2 minutos de ti hablando de cualquier cosa **sin** decir las palabras, para que no
se active con tu voz normal.

Las grabaciones se guardan en `~/.local/share/drakter/wakeword/muestras/` y el script crea
`~/.local/share/drakter/wakeword/muestras_drakter.zip`. Sube ese ZIP a Google Drive dentro de una carpeta
`Drakter`, de modo que quede en `Mi unidad/Drakter/muestras_drakter.zip`.

Otras opciones: `--palabras jarvis` (solo una palabra), `--n 30` (más tomas) y `--dispositivo <nodo>` para otro
micrófono (`wpctl status` muestra los nodos de PipeWire). El script graba con `pw-record` o, si no lo hay, con
`arecord`.

## 2. Abre el cuaderno en Colab

El cuaderno es `tools/wakeword/entrenar_palabras_drakter.ipynb`. El repositorio es privado, así que elige una de
estas dos formas:

- **Subirlo:** en [colab.research.google.com](https://colab.research.google.com), *Archivo → Subir cuaderno* y
  elige el `.ipynb` de tu copia local del repo.
- **Desde GitHub:** *Archivo → Abrir cuaderno → GitHub*, marca «Incluir repositorios privados», autoriza a Colab y
  busca `Lordi898/Drakter`.

Luego, en *Entorno de ejecución → Cambiar tipo de entorno de ejecución*, elige **GPU** (T4 basta; L4 o A100 van
más rápido).

## 3. Revisa la configuración y ejecuta

La primera celda de código, **1. Configuración**, tiene todo lo que puedes ajustar:

- `PALABRAS`: las tres palabras, con los textos que se sintetizan (`textos`), las palabras parecidas que **no**
  deben activarlo (`parecidas`: «jardín», «Travis», «despiertas», «Drácula»…) y el nombre de la carpeta de tus
  grabaciones. Si no quieres una palabra, borra su bloque.
- `N_POSITIVOS` (2500), `N_PARECIDAS` (1500), `N_FRASES` (1000): cuántos clips sintéticos se generan.
- `HORAS_VOZ_ES` (12) y `AUDIOSET_PARTES` (4, unas 1,4 h de ruidos y música cada una): cuánto audio real se usa como «esto no es la palabra».
- `OBJETIVO_FP_HORA` (0,5): cuántas activaciones falsas por hora aceptas.

Después, *Entorno de ejecución → Ejecutar todas*. Te pedirá permiso para montar Google Drive: acéptalo (o pon
`USAR_DRIVE = False` y no se guardará nada en Drive). Con los valores por defecto tarda alrededor de 1-1,5 horas.
Casi todo se va en sintetizar voces (va en CPU, la GPU no la acelera) y en descargar audio; entrenar cada palabra
lleva unos minutos. Para ir más rápido, baja `N_POSITIVOS` y `N_PARECIDAS` o sube `PROP_PIPER` (Piper es unas cinco
veces más rápido que Kokoro).

En la sección 5 puedes escuchar un ejemplo de cada palabra sintetizada, para comprobar que la pronuncia bien.

## 4. Lee las métricas

La sección 9 imprime, para cada palabra y para los umbrales 0,3, 0,5 y 0,7, una tabla con estas columnas:

- **recall sint. / recall tu voz:** el porcentaje de veces que la palabra lo activa, con voces sintéticas que no ha
  visto y con tu propia voz (si grabaste). Cuanto más alto, mejor; a partir del 80 % va bien.
- **FP/h:** activaciones falsas por hora de audio normal, con voz castellana de personas que no están en el
  entrenamiento y con ruidos y música. Por debajo de 0,5 va bien.
- **parecidas / frases:** el porcentaje de palabras parecidas y de frases normales que lo activan por error.

Al final recomienda un umbral: el más bajo que cumple `OBJETIVO_FP_HORA` en todas las palabras.

## 5. Descarga e instala

La sección 10 exporta `jarvis_es.onnx`, `drakter_es.onnx` y `despierta_es.onnx`, comprueba que cargan con el mismo
`openwakeword` 0.4.0 que usa Drakter y descarga `palabras_drakter.zip` (también los copia a
`Mi unidad/Drakter/wakeword/`). En tu ordenador:

```bash
mkdir -p ~/.local/share/drakter/models/openwakeword
unzip -o ~/Descargas/palabras_drakter.zip -d ~/.local/share/drakter/models/openwakeword/
```

Quedan junto a `hey_jarvis_v0.1.onnx`, `melspectrogram.onnx` y `embedding_model.onnx`, que no se tocan.

## 6. Actívalos

Añade estas dos líneas a `~/.config/drakter/.env` (créalo si no existe), con el umbral que recomendó el cuaderno:

```bash
DRAKTER_VOICE_WAKE_MODELS=jarvis_es,drakter_es,despierta_es
DRAKTER_VOICE_WAKE_THRESHOLD=0.5
```

Cierra Drakter del todo (icono de la bandeja → Salir) y vuelve a abrirlo. Los nombres van sin `.onnx` y
separados por comas. Puedes poner solo los que quieras (`jarvis_es`) o mezclarlos con el inglés
(`hey_jarvis_v0.1,jarvis_es`): basta con que salte uno.

Si prefieres no usar el `.env`, lo mismo se puede poner en `~/.config/drakter/voice.toml`:

```toml
wake_models = ["jarvis_es", "drakter_es", "despierta_es"]
wake_threshold = 0.5
```

Si están las dos, manda la variable del `.env`.

## 7. Ajusta el umbral

El umbral va de 0 a 1 y es el mismo para todos los modelos:

- **Se activa sola** (con la tele, hablando con alguien): súbelo de 0,1 en 0,1 (0,6, 0,7…).
- **Tienes que repetir la palabra:** bájalo (0,4, 0,3). Si aun así falla, graba tus muestras (paso 1) y vuelve a
  entrenar.

Tras cada cambio, reinicia Drakter.

## Volver al modelo inglés

Borra las dos líneas de `~/.config/drakter/.env` (o las de `voice.toml`) y reinicia Drakter. También puedes ser
explícito:

```bash
DRAKTER_VOICE_WAKE_MODELS=hey_jarvis_v0.1
DRAKTER_VOICE_WAKE_THRESHOLD=0.3
```

Los `.onnx` propios pueden quedarse en la carpeta; solo se cargan los que nombras.

## Si algo falla

- **Drakter no arranca la voz tras el cambio:** revisa que el nombre en `DRAKTER_VOICE_WAKE_MODELS` coincide con
  el archivo de `~/.local/share/drakter/models/openwakeword/` (sin `.onnx`). Si falta, el proceso de voz avisa con
  «Falta el modelo de openWakeWord».
- **Colab se queda sin memoria:** baja `HORAS_VOZ_ES` o `AUDIOSET_PARTES`, o usa un entorno con más RAM.
- **Colab se desconecta a mitad:** vuelve a ejecutar todo; lo descargado se reutiliza mientras dure la sesión.

## Licencias

Las voces y el audio que descarga el cuaderno tienen licencias libres (dominio público, CC0, CC BY, Apache-2.0),
salvo dos excepciones: las reverberaciones del MIT, cuya copia en Hugging Face no indica licencia, y ACAV100M
(CC BY-NC-SA 4.0, no comercial), que viene desactivado (`USAR_ACAV = False`). Todo es para tu uso personal y no se
redistribuye. Detalle en
[`tools/wakeword/README.md`](../../tools/wakeword/README.md).
