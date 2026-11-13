# Drakter Voice (v2)

Proceso de voz de Drakter: Pipecat 1.16.0 con WebRTC por loopback. Escucha (activación, VAD, STT), decide los turnos y el barge-in, y habla (Fish Audio con Kokoro local de respaldo). No conoce Hermes, la BD ni las confirmaciones: recibe texto para decir y entrega texto transcrito. Contrato completo del proceso en `CONTRACT.md`; el diseño, en las decisiones V-01 a V-38 de `docs/DECISIONS.md`. Guía de uso: [`docs/usage/voz.md`](../docs/usage/voz.md); instalación: [`docs/installation/voz.md`](../docs/installation/voz.md).

## Procesos

```
Renderer (Chromium)  getUserMedia con AEC3/NS/AGC ──WebRTC 127.0.0.1 (ice_servers=[]) + data channel con ping──► voice/
        │ señalización: window.api → main → backend (POST /api/v1/voice/offer) → IPC rtc.offer
Backend FastAPI      VoiceOrchestrator ⇄ socket UDS ⇄ voice/   (supervisa el proceso; Hermes queda fuera)
voice/               python -m voice run (py3.12, venv propio)
```

- El audio nunca pasa por el backend: va del renderer a `voice/` por WebRTC. Por el socket solo viajan JSON.
- Hay un `PipelineWorker` por conexión WebRTC (`SmallWebRTCRequestHandler` en modo `SINGLE`). Los modelos pesados se cargan una vez por proceso (`SharedModels`) y el estado de sesión (`Session`, modo, perfil) vive fuera del pipeline, así que recargar el renderer no recarga modelos.
- `channels/webrtc.py` añade 127.0.0.1 a los candidatos ICE (aioice lo excluye) y vigila el ping del data channel (`rtc_ping_timeout_s`). Electron debe arrancar con `--allow-loopback-in-peer-connection`; `scripts/drakter` ya lo pone.

## Pipeline

Lo monta `pipeline.py` (`build`), en este orden:

```
transport.input() → WakeGate → VADProcessor(Silero) → STT (Moonshine streaming)
  → UserTurnProcessor (único; inicio: DrakterStartStrategy, fin: Smart Turn v3.2)
  → BackendBridgeProcessor → SpeechGuard → cadena TTS (Fish | Kokoro)
  → PhrasePlayer → transport.output() [DuckMixer] → PlaybackTracker
```

- `WakeGate` (openWakeWord, `hey_jarvis`) es solo una puerta de audio; en `standby` el STT no recibe audio. La confirmación textual de «jarvis» la hace el puente sobre el turno final.
- `DrakterStartStrategy` implementa «bajar primero, decidir después»: con el bot hablando baja el volumen (`DuckMixer`) y solo abre turno si la transcripción parcial confirma al menos `bargein_min_words` palabras que no sean eco.
- `BackendBridgeProcessor` (`bridge.py`) aplica la capa 0 (`conversation/layer0.py` y `layer0.es.toml`: «para», «descansa», cierres, asentimientos) y, si el turno procede, emite `voice.user_turn` al backend. Las respuestas del agente llegan como `speak.*` y se convierten en frames de texto para el TTS.
- La cadena TTS (`providers/tts/failover.py`) conmuta de Fish a Kokoro por errores de autenticación, cuota, petición inválida o 3 fallos seguidos, con un único aviso hablado. Fish se corta por fecha (`fish_free_until`) salvo `allow_paid`.
- `PlaybackTracker` va después de la salida: cuenta lo que se oyó, no lo sintetizado. Al interrumpir, el backend recibe `heard_tail` y `pending_head`.
- `PhrasePlayer` emite frases fijas desde la caché PCM (`agent/identity/voice_phrases.es.toml`).
- `metrics.py` escribe un `metrics.jsonl` por turno solo con tiempos y contadores, nunca texto.

## IPC con el backend (UDS JSONL)

`<runtime_dir>/voice.sock` (permisos 0600, `SO_PEERCRED`). Una línea JSON por mensaje, con `kind` en `evt | cmd | ok | err` (`ipc.py`). Los modelos Pydantic están en `contracts/python/drakter_contracts/voice_ipc.py` y son la fuente de verdad. Un `err` lleva `payload = {code, message}`; códigos: `invalid_request`, `rtc_failed`, `internal_error`. El backend (`backend/app/integrations/voice/`) es el único que habla con el hub de eventos, la BD y las confirmaciones; `voice/` solo emite eventos IPC.

## Proveedores y cómo añadir uno

`registry.py` tiene una tabla estática y perezosa `TABLE[(tipo, nombre)] = "modulo:fabrica"`; nada se importa hasta `create`. Los nombres son campos de `VoiceConfig`.

| Tipo | Por defecto | Fábrica |
|---|---|---|
| `stt` | `moonshine` | `voice.providers.stt.moonshine_streaming:create` |
| `vad` | `silero` | `voice.providers.vad.silero:create` |
| `turn_start` | `drakter` | `voice.conversation.start_strategy:create` |
| `turn_stop` | `smart_turn` | `voice.providers.turn.smart_turn:create` |
| `wake` | `openwakeword` | `voice.providers.wake.openwakeword_gate:create` |
| `tts` (lista) | `fish`, `kokoro` | `voice.providers.tts.fish:create`, `voice.providers.tts.kokoro:create` |
| `tts_chain` | `failover` | `voice.providers.tts.failover:create` |
| `mixer` | `duck` | `voice.conversation.duck:create` |
| `channel` | `webrtc` | `voice.channels.webrtc:create` |
| cualquiera | `null` | `voice.providers.null:create` (proveedor vacío) |

Para añadir un proveedor hay dos caminos, sin tocar el núcleo:

1. Escribe una fábrica `create(cfg, ...)` que devuelva la clase del puerto correspondiente (firmas en `ports.py`) y añade una línea a `TABLE`.
2. O pon directamente `"paquete.modulo:fabrica"` como valor del campo (por ejemplo `stt = "mi_paquete.stt:create"` en `voice.toml`): `resolve` usa tal cual cualquier nombre que contenga `:`.

`python -m voice check` comprueba que cada fábrica se importa y que existen sus modelos.

## Configuración

`config.py` define `VoiceConfig` (dataclass inmutable) con todos los campos y sus valores por defecto. Precedencia, de menor a mayor:

1. Valores por defecto.
2. `~/.config/drakter/voice.toml` (respeta `XDG_CONFIG_HOME`), con claves planas que se llaman como el campo. Una clave desconocida da error.
3. Variables `DRAKTER_VOICE_<CAMPO>` en mayúsculas (`DRAKTER_VOICE_STT_MODEL=tiny`, `DRAKTER_VOICE_TTS=kokoro`, `DRAKTER_VOICE_FISH_FREE_UNTIL=2026-11-30`). Las listas van separadas por comas.

Además: `DRAKTER_RUNTIME_DIR` (directorio del socket), `DRAKTER_DATA_DIR` (raíz de datos), `DRAKTER_VOICE_NULL=1` (todos los proveedores vacíos) y `DRAKTER_VOICE_PIPECAT_LOG` (nivel de log de Pipecat, `WARNING` por defecto). La clave `FISH_API_KEY` la lee el proveedor Fish del entorno; el backend se la pasa al hijo. Los ajustes de usuario (`voice_tts_enabled`, `voice_wake_enabled`, `voice_profile`, `voice_expression`) no se configuran aquí: llegan por el comando IPC `voice.config`.

Los umbrales (`bargein_min_words`, `bargein_decide_ms`, `duck_gain`, `idle_nudge_s`, `followup_s`, `wake_threshold`…) son provisionales y sin calibrar. Las variantes de «jarvis» que acepta el puente viven en `conversation/layer0.es.toml`, sección `[wake]`. Añadir una variante es editar ese archivo.

## Comandos

Desde la raíz del repo y con el Python del venv de voz (`~/.local/share/drakter/venvs/voice/bin/python`):

```bash
python -m voice run                  # el proceso de voz (lo lanza el backend; --null = proveedores vacíos)
python -m voice check                # proveedores importables y modelos en disco; sin audio ni red
python -m voice phrases [--profile P] [--only fish|kokoro] [--no-voice] [--force] [--check]
```

`phrases` genera la caché de frases fijas con el perfil activo (o `--profile`). Con `--check` solo valida el TOML de frases.

## Comprobaciones

Sin suite de tests: tres comprobaciones rápidas, del mismo venv.

```bash
python voice/tests/check_pipeline.py [--wav habla.wav]            # arranque, oferta WebRTC (aiortc), turno de usuario, speak.*, reconexión, métricas
python -m voice.providers.stt.check_wp2 <wav> [--model small|tiny] # STT, Smart Turn y openWakeWord sobre un wav
python -m voice.conversation.check_conversation                   # capa 0, barge-in, eco y ruido sobre un UserTurnProcessor real
```

Cada una imprime PASS/FAIL por paso y sale con 1 si algo falla. Latencias y consumo medidos: cierre del turno 375-388 ms con frase única (1,2-2,3 s en otras), STT final 98-302 ms (Moonshine small), TTFA de Fish 0,71-0,96 s y de Kokoro 0,72 s, primer audio tras callar el usuario 2,36-2,88 s (normalmente el acuse), RSS del proceso de voz ~990 MB (i7-8665U, sin GPU, voz sintética).

## Instalación y modelos

`scripts/install-voice.sh` (desde el checkout principal) crea el venv `~/.local/share/drakter/venvs/voice` con Python 3.12, instala `voice/requirements.lock` y `contracts/python` en editable, y comprueba que los modelos existen. Pasos y requisitos en [`docs/installation/voz.md`](../docs/installation/voz.md).

Los modelos están en `~/.local/share/drakter/models/` (`moonshine/`, `smart-turn/`, `openwakeword/`, `kokoro/`, `silero/`). El código no descarga nada en ejecución: si falta un modelo, `check` y el arranque dicen la ruta esperada. Los runtimes y modelos nunca van en `/tmp`.

## Privacidad

Ni el audio ni las transcripciones se guardan. Los logs de Pipecat se limitan a `WARNING` (en `DEBUG` imprimirían el texto) y el formateador de logs omite trazas. Solo persisten `metrics.jsonl` (sin texto) y la caché de frases fijas, en `~/.local/share/drakter/voice/`.
