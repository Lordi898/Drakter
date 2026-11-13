# Usar la voz

> **Estado:** `voice/` y `backend/app/integrations/voice/` están en `drakter/integracion` (`2e05ba6`), y Electron permite las rutas `/api/v1/voice/*`, pero el router de voz no se monta en `backend/app/main.py` y no hay botón de voz en `desktop/src`: hoy no se puede usar desde la app. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

Hablas a Drakter y te contesta en voz alta. Todo es local: ni el audio ni las transcripciones se guardan ni se registran. Instalación previa: [Instalar la voz](../installation/voz.md).

## Activar y desactivar

1. La voz viene apagada: `DRAKTER_VOICE_ENABLED=false` por defecto.
2. Para activarla pon `DRAKTER_VOICE_ENABLED=true` (entorno o `~/.config/drakter/.env`) y reinicia el backend.
3. Para desactivarla, vuelve a `false` y reinicia. Con `false` el servicio no hace nada y el estado de voz es `disabled`.
4. Si `DRAKTER_VOICE_PYTHON` está mal, el backend arranca pero la voz queda `misconfigured`.

## Micrófono

- Arranca **apagado**. Hay que encenderlo expresamente (`POST /api/v1/voice/mic` con `{"enabled": true}`).
- Encenderlo se anota en auditoría (solo que se pidió, sin audio). Si la auditoría falla, el micrófono se queda apagado.
- Apagarlo cierra la captura de verdad y cancela la escucha en curso.

## Hablar

El modo por defecto es **pulsar para hablar**: la captura solo está abierta durante tu intervención.

1. Enciende el micrófono.
2. Inicia la escucha (`POST /api/v1/voice/listen/start`). Si Drakter está hablando, primero se interrumpe.
3. Habla. Se cierra sola tras `DRAKTER_VAD_SILENCE_MS` (800 ms) de silencio, o a los `DRAKTER_VOICE_MAX_UTTERANCE_S` (30 s).
4. Para cerrar a mano: `POST /api/v1/voice/listen/stop`. Para descartar sin transcribir: `POST /api/v1/voice/listen/cancel`.
5. El texto transcrito va al agente y la respuesta se habla por frases según llega.

**Pendiente:** no hay pantalla ni botón de voz en `desktop/src` (ni en la rama de origen ni en 2da8bef); hoy solo existen estas rutas HTTP (solo con el token de escritorio), y en 2da8bef el backend no las sirve.

## Palabra de activación

No existe. No hay modelo para "Drakter": los de openWakeWord son para otras palabras y con licencia no comercial, así que solo se carga un modelo propio ONNX (`DRAKTER_WAKEWORD_MODEL`) y nunca se descarga. Sin él, `DRAKTER_WAKEWORD_PROVIDER=null` y solo hay pulsar para hablar. Con `wakeword.set` sin proveedor real el resultado es un error `invalid_request`. **Pendiente:** entrenar un modelo propio.

## Interrumpir

- `POST /api/v1/voice/interrupt` corta reproducción, cola y síntesis. Es idempotente.
- Iniciar una escucha nueva también interrumpe.
- Interrumpir por voz mientras Drakter habla (barge-in) está desactivado (`DRAKTER_VOICE_BARGE_IN=false`): lo que se capta mientras habla se descarta, para no transcribir su propio eco. Actívalo solo tras probar `mic_check.py --barge-in`.

## Estados

Ciclo: `idle`, `listening`, `transcribing`, `waiting`, `speaking`, `idle`. En el personaje: escuchando = `listening`; transcribiendo o esperando = `thinking`; hablando = `speaking`; interrumpido = `interrupted`; error no recuperable = `error`. La boca recibe niveles de volumen, no audio.

## Lo que pide confirmación

Nada se aprueba por voz. Las confirmaciones de acciones solo se aprueban desde la interfaz; decir "sí" no vale. No existe ruta para hacer hablar a Drakter fuera de las respuestas del agente.

## Qué tienes que probar tú

1. Instala y haz la prueba guiada de [voz (instalación)](../installation/voz.md): `mic_check.py`, `--voices`, `--barge-in`.
2. Cuando se integre, enciende micrófono, pulsa para hablar, di una frase en español y comprueba que el texto es correcto y que la respuesta suena.
3. Interrumpe a mitad de respuesta y comprueba que corta.
4. Apaga el micrófono y comprueba que no hay captura.
5. Mide la latencia con `bench_engines.py` y decide `small` o `medium`.

## Problemas frecuentes

- Estado `not_responding`: el proceso de voz no contesta (en la rama faltan `voice/manager.py` y `voice/__main__.py`).
- `invalid_request` (409) al iniciar escucha: micrófono apagado.
- `voice_unavailable` (503): voz desactivada, mal configurada o caída. Tras 8 fallos seguidos el supervisor deja de reiniciarla.
- Error `voice.error` en etapa `stt` o `tts`: vuelve a `idle`; el texto sigue visible en el chat.

## Pendiente

- Pantalla de voz en el escritorio, palabra de activación propia, integración en `main.py`, y todo lo anterior sin comprobar en hardware real.
