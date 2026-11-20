# Contrato del frente de voz (v2, Pipecat 1.16.0)

Congelado por WP0 del plan de voz v2. En código: `voice/ports.py`, `voice/registry.py`,
`contracts/python/drakter_contracts/{voice_ipc.py,speech_markup.py,events.py}` y, en el escritorio,
`desktop/electron/shared/bridge.ts` y `desktop/src/voice/contract.ts`. Esos archivos solo los cambia
el dueño de los contratos: si falta algo, se avisa al integrador y se usa un adaptador local.
Decisiones V-01 a V-38 en `docs/DECISIONS.md`.

## Fronteras

- Voz corre en **su propio proceso y venv** (`~/.local/share/drakter/venvs/voice`, py3.12, `pipecat-ai[webrtc,fish,kokoro]==1.16.0` y `drakter_contracts`), supervisado por el backend.
- **Audio por WebRTC loopback** (transporte B): el renderer captura con `getUserMedia` (AEC3, NS, AGC) y reproduce el `<audio>` remoto; la voz usa `SmallWebRTCTransport` con `ConnectionMode.SINGLE` e `ice_servers=[]`. La señalización va renderer → `window.api.voice.offer` → main → `POST /api/v1/voice/offer` → IPC `rtc.offer` → voz. Ni audio ni SDP pasan por el WebSocket de eventos.
- Voz **no** conoce Hermes, la BD, el hub de eventos ni las confirmaciones. Entrega texto de usuario (`voice.user_turn`) y recibe texto para decir (`speak.*`). Quien habla con el agente es `VoiceOrchestrator` (`backend/app/integrations/voice/service.py`).
- **Ninguna frase hablada aprueba nada.** Ante `confirmation.requested` se dice `confirm_on_screen` y se enfoca la ventana.
- Ni audio ni transcripciones se guardan ni se registran (única excepción: el volcado de diagnóstico `DRAKTER_VOICE_DUMP_AUDIO=1`, desactivado por defecto, en `voice/dumps/` 0700/0600 y borrado a las 24 h). `metrics.jsonl` lleva tiempos y contadores, nunca texto. Los IDs de voz (`ResolvedProfile.voice`) nunca se loguean.
- **Sin descargas en ejecución**: todo modelo sale de `~/.local/share/drakter/models/`. Si falta, la fábrica falla con la ruta esperada.
- Fish solo con `s2.1-pro-free` (lista blanca) y hasta `fish_free_until` (2026-11-30); después, Kokoro salvo `allow_paid`.

## Pipeline (uno por conexión; modelos una vez por proceso)

```
input → WakeGate (oWW, prebúfer 2 s; solo audio) → VADProcessor (Silero) → [AudioDump] → STT (auto: Deepgram | Groq | Moonshine)
      → UserTurnProcessor (único; start=[DrakterStartStrategy], stop=[DrakterTurnStop: Smart Turn v3.2 + texto], user_idle_timeout)
      → BackendBridgeProcessor (turno final; prefijo «jarvis»; capa 0; speak.* → LLM frames)
      → SpeechGuard → ServiceSwitcher[Fish | Kokoro] (text_transforms por proveedor)
      → PhrasePlayer (caché PCM) → output [DuckMixer] → PlaybackTracker (→ voice.playback)
```

`SessionState` y `Ctl` viven fuera del pipeline (`voice/session.py`). El modo (`standby` | `conversation`) solo lo cambia `Ctl.set_mode`.

## Puertos (`voice/ports.py`) y registro (`voice/registry.py`)

Los puertos son fábricas `create(...)` que devuelven objetos de Pipecat. El registro es una tabla estática perezosa: `registry.create(kind, name, *args)` importa el módulo al llamarse. Un `name` con `:` (`"paquete.modulo:fabrica"`) se importa tal cual, sin tocar la tabla.

| kind | name | módulo | firma de `create` |
|---|---|---|---|
| `stt` | `moonshine` | `voice.providers.stt.moonshine_streaming` | `(cfg, shared) -> STTService` |
| `stt` | `auto`, `deepgram`, `groq` | `voice.providers.stt.cloud` | `(cfg, shared) -> FrameProcessor` (`ServiceSwitcher[nube, Moonshine]`; el núcleo pone `strategy.ctl`) |
| `vad` | `silero` | `voice.providers.vad.silero` | `(cfg) -> VADAnalyzer` |
| `turn_stop` | `smart_turn` | `voice.providers.turn.smart_turn` | `(cfg, shared) -> BaseUserTurnStopStrategy` |
| `turn_start` | `drakter` | `voice.conversation.start_strategy` | `(cfg, ctl) -> list[BaseUserTurnStartStrategy]` |
| `wake` | `openwakeword` | `voice.providers.wake.openwakeword_gate` | `(cfg, shared, ctl) -> FrameProcessor` |
| `tts` | `fish`, `kokoro` | `voice.providers.tts.{fish,kokoro}` | `(cfg, shared, profile: ResolvedProfile) -> TTSProvider` |
| `tts_chain` | `failover` | `voice.providers.tts.failover` | `(cfg, ctl, providers: list[TTSProvider]) -> FrameProcessor` |
| `mixer` | `duck` | `voice.conversation.duck` | `(cfg, ctl) -> BaseAudioMixer` |
| `channel` | `webrtc` | `voice.channels.webrtc` | `(cfg) -> Channel` |
| `*` | `null` | `voice.providers.null` | `(kind, *args)`: recibe además la clase pedida como primer argumento |

Tipos: `Shared` (`models_dir`, `get(key, loader)`), `ResolvedProfile{name, voice}`, `TTSProvider{service, name, expressive}`, `Channel` (`accept_offer`, `on_connection`, `close`), `SessionState` (cada campo con un único dueño, anotado en el código) y `Ctl` (`emit`, `interrupt`, `play_phrase`, `set_duck`, `set_mode`).

Capa 0 (`voice/conversation/layer0.py`, firma congelada; listas en `layer0.es.toml`):

```python
def classify(text: str, bot_speaking: bool, awaiting_answer: bool) -> Literal["stop_speech","rest","close","backchannel"] | None
```

## IPC voz ↔ backend (`drakter_contracts/voice_ipc.py`)

UDS JSONL (`voice/ipc.py`, socket 0600 con `SO_PEERCRED`): la voz es servidor y el backend cliente; máximo 256 KiB por línea. Sobre `IpcMessage{kind: evt|cmd|ok|err, id, type, payload}`. `Trigger = wake|hotkey|ui|followup`.

Voz → backend (`evt`, modelos en `EVTS`): `voice.ready`, `voice.state`, `voice.user_speech`, `voice.user_turn`, `voice.playback` (con `heard_tail` ≤80 y `pending_head` ≤200 solo en `interrupted`), `voice.local_command`, `voice.tts_fallback` (una vez por arranque), `voice.metrics`, `voice.error` (incluye `stt_fallback`, una vez por arranque, al pasar de la nube a Moonshine).

Backend → voz (`cmd`, modelos en `CMDS`; respuesta `ok` con `CMD_RESULTS[type]` o `{}`, o `err{code, message}`): `rtc.offer` → `RtcAnswer`, `speak.open`, `speak.delta` → `SpeakAck{ignored}`, `speak.flush`, `speak.close`, `speak.stop`, `speak.phrase`, `turn.phase`, `voice.config`, `mode.set`, `status` → `StatusResult`, `shutdown`.

- `speech_id` es monótono por proceso de backend y abre un tramo de habla; `seq` es monótono por `speech_id`. Un delta duplicado o de un speech cortado responde `ok{ignored: true}`.
- **Regla de corte:** el puente marca el `speech_id` activo como cortado ante **cualquier** `InterruptionFrame` (local o por `speak.stop`) y emite `voice.playback{interrupted}`. Tras un `steered accepted`, el backend abre un `speech_id` nuevo con el mismo `turn_id`.
- `PhraseKey` es una lista cerrada (`PHRASE_KEYS`); los textos viven en `agent/identity/voice_phrases.es.toml` y el cargador valida que no falte ninguna.
- Etiquetas de expresión: lista cerrada en `drakter_contracts/speech_markup.py` (`TAGS`). Fish recibe `keep_allowed`; Kokoro, `strip_tags`.

## Superficie hacia fuera

- REST (`contracts/api/routes.md` §Voz): `POST /voice/offer`, `POST /voice/activate`, `POST /voice/mode`, `GET /voice/status`. No hay ruta para el micrófono ni para aprobar nada.
- Eventos WS (los publica `VoiceOrchestrator`, nunca este proceso): `voice.state` (snapshot, sin `mic`), `voice.playback` (sin texto), `voice.error`, y `notification.created` para el respaldo de TTS. Los `voice.*` de la v1 se retiran en la integración (WP9).
- Ajustes de usuario (`SETTING_KEYS`): `voice_tts_enabled`, `voice_profile`, `voice_wake_enabled`, `voice_expression`. Llegan a la voz por `voice.config`. Los umbrales (`stt_model`, `stt_keyterms`, `turn_complete_threshold`, `turn_grace_s`, `turn_hanging_secs`, `wake_threshold`, `wake_energy_dbfs`, `followup_s`, `idle_nudge_s`, `turn_stop_secs`, `filler_after_ms`, `bargein_min_words`, `bargein_decide_ms`, `duck_gain`, `tool_phrase_gap_s`, `fish_free_until`, `allow_paid`) viven en `VoiceConfig`, sin calibrar hasta WP9.
- Micrófono: lo calcula el renderer (`mic = !client?.micOpen() ? "off" : mode === "conversation" ? "live" : "standby"`).
