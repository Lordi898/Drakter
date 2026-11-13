# Contrato del frente de voz

`voice/contracts.py` y `voice/config.py` son la parte congelada en código. Este archivo fija lo demás.
Todos los eventos `voice.*` son `experimental` hasta medir la latencia real.

## Fronteras

- Voz corre en **su propio proceso y venv** (`voice/pyproject.toml`), arrancado por el backend. Motivo: torch fuera, memoria aislada, Piper GPL fuera del proceso.
- **La captura y la reproducción viven en el proceso de voz.** No viaja audio por el socket ni por WebSocket. La boca recibe niveles (`voice.playback_level`).
- Voz **no** conoce Hermes, la BD ni las confirmaciones. Recibe texto para decir y entrega texto transcrito. Quien habla con el agente es `backend/app/integrations/voice/bridge.py`.
- Ninguna frase hablada aprueba nada: las confirmaciones solo se aprueban desde la GUI. El puente no tiene ninguna vía hacia ellas.
- Ni audio ni transcripciones se guardan ni se registran. Logs y métricas llevan longitudes y tiempos, nunca texto.
- Nunca se descarga un modelo solo: si falta, error `model_missing` con la ruta esperada.
- Micrófono apagado al arrancar. `mic.set false` cierra la captura de verdad y nada lo reabre salvo otro `mic.set true`.
- Pulsar para hablar es el modo por defecto. Con él la captura solo está abierta durante la intervención.

## Módulos y dueños

| Ruta | Contenido |
|---|---|
| `voice/vad/` | `silero.py` (`SileroVAD`, ONNX, sin torch), `energy.py` (`EnergyVAD`, reserva sin modelo) |
| `voice/wakeword/` | `null.py` (`NullWakeWord`), `openwakeword_provider.py` (`OpenWakeWordProvider`, ONNX) |
| `voice/stt/` | `faster_whisper_provider.py` (`FasterWhisperSTT`) |
| `voice/tts/` | `kokoro.py` (`KokoroTTS`), `piper.py` (`PiperTTS`, proceso externo), `fallback.py` (`FallbackTTS`) |
| `voice/audio/` | `backends.py` (`open_capture`, `open_sink`), `player.py` (`Player`), `null.py` (`NullCapture`, `NullSink`) |
| `voice/personality/` | `engine.py` (`VoicePersonalityEngine`), `segmenter.py` (`SentenceSegmenter`), `normalize.py` (`normalize_for_speech`) |
| `voice/` raíz | `manager.py` (`VoiceManager`), `metrics.py` (`TurnMetrics`, `MetricsSink`), `registry.py`, `ipc.py`, `service.py`, `__main__.py` |
| `backend/app/integrations/voice/` | `settings.py`, `client.py`, `supervisor.py`, `bridge.py`, `schemas.py`, `router.py`, `service.py` |

Constructores: cada motor recibe solo `VoiceConfig` (`SileroVAD(config)`), excepto `FallbackTTS(primary, fallback)`, `NullSink()`, `NullCapture()` y `EnergyVAD(config)`. `Player(sink, listener, *, level_hz, output_latency_ms)`.

```python
# voice/audio/backends.py
def open_capture(config: VoiceConfig) -> AudioCapture: ...
def open_sink(config: VoiceConfig) -> AudioSink: ...

# voice/audio/player.py
class Player:
    def start(self) -> None: ...
    def enqueue(self, utterance_id: str, chunk: PcmChunk, gain: float = 1.0) -> None: ...
    def add_silence(self, utterance_id: str, ms: int) -> None: ...
    def finish(self, utterance_id: str) -> None: ...     # no llegará más audio de esa locución
    def interrupt(self) -> tuple[str, ...]: ...          # corta ya y descarta todo; devuelve ids afectados
    def close(self) -> None: ...

# voice/personality/
def normalize_for_speech(text: str) -> str: ...          # quita Markdown, código, URL y emojis
class SentenceSegmenter:
    def __init__(self, *, max_chars: int = 200) -> None: ...
    def feed(self, delta: str) -> list[str]: ...         # frases ya completas
    def flush(self) -> list[str]: ...
class VoicePersonalityEngine:
    def __init__(self, config: VoiceConfig, profile_path: Path | None = None) -> None: ...
    def plan(self, sentence: str, context: VoiceContext, caps: TTSCapabilities) -> SpeechSegment: ...

# voice/metrics.py
class TurnMetrics:
    def __init__(self, turn_id: str) -> None: ...
    def mark(self, name: str) -> None: ...               # time.perf_counter_ns, solo la primera vez
    def note(self, name: str, value: float | int | str) -> None: ...
    def snapshot(self) -> dict[str, object]: ...         # spans_ms, notes, rss_mb, loadavg
class MetricsSink:
    def __init__(self, path: Path) -> None: ...
    def write(self, snapshot: Mapping[str, object]) -> None: ...  # JSONL 0600, sin texto

# voice/registry.py: imports perezosos; desconocido -> VoiceError("invalid_request", ...)
def build_vad(c: VoiceConfig) -> VADProvider: ...        # silero|energy
def build_wakeword(c: VoiceConfig) -> WakeWordProvider: ...  # null|openwakeword
def build_stt(c: VoiceConfig) -> STTProvider: ...        # faster_whisper
def build_tts(c: VoiceConfig) -> TTSProvider: ...        # kokoro|piper, envuelto en FallbackTTS si hay respaldo
```

Marcas de `TurnMetrics`, en orden: `wake`, `listen_start`, `speech_start`, `speech_end`, `stt_start`, `stt_first_segment`, `stt_end`, `text_received`, `tts_start`, `tts_first_audio`, `playback_start`, `playback_end`. Notas: `audio_s`, `stt_provider`, `stt_model`, `tts_provider`, `tts_audio_s`, `tts_synth_s`. Spans derivados: `stt_ms`, `stt_rtf`, `tts_first_audio_ms`, `tts_rtf`, `response_gap_ms` (`speech_end`→`playback_start`). Sin marca, no hay span: nunca se rellena con una estimación.

## IPC: socket Unix `<runtime_dir>/voice.sock`

Socket 0600 dentro de un directorio 0700; se comprueba `SO_PEERCRED` y solo se admite el mismo uid y un cliente a la vez. JSON por líneas, UTF-8, máximo 256 KiB por línea (se cierra la conexión si se supera).

```jsonc
{"kind":"cmd","id":"<uuid>","name":"status","args":{}}
{"kind":"res","id":"<uuid>","ok":true,"result":{}}
{"kind":"res","id":"<uuid>","ok":false,"error":{"code":"invalid_request","message":"..."}}
{"kind":"evt","name":"voice.state_changed","ts":"<UTC ISO 8601>","payload":{}}
```

| Comando | `args` | Efecto |
|---|---|---|
| `status` | | `{state, mic_enabled, listen_mode, wakeword_available, barge_in, providers:{stt,tts,tts_active,vad,wakeword,audio}, ready:{stt,tts,vad}, turn_id, utterance_id}` |
| `mic.set` | `enabled` | Abre o prohíbe el micrófono. `false` cancela la escucha en curso |
| `wakeword.set` | `enabled` | Solo si hay proveedor real; si no, `invalid_request` |
| `listen.start` | | Pulsar para hablar. Si Drakter habla, primero interrumpe. Devuelve `{turn_id}`. Con el micrófono apagado, `invalid_request` |
| `listen.stop` | | Soltar: cierra la intervención y transcribe |
| `listen.cancel` | | Descarta el audio sin transcribir |
| `speak` | `turn_id, text, final, context?` | `text` es un delta; las frases se trocean y encolan. `final:true` cierra el turno. `context` es `VoiceContext` |
| `interrupt` | `reason?` | Corta reproducción, cola y síntesis. Idempotente |
| `shutdown` | | Cierra motores y sale |

Un `speak` de un `turn_id` ya interrumpido se ignora con `ok:true, result:{ignored:true}`: así los deltas tardíos del agente no vuelven a sonar.

## Eventos (`payload`)

| Evento | Payload |
|---|---|
| `voice.state_changed` | `state, previous, reason?` |
| `voice.mic_changed` | `enabled, capture_open` |
| `voice.wakeword_detected` | `keyword, score, turn_id` |
| `voice.listening_started` | `turn_id, mode` |
| `voice.speech_started` | `turn_id` |
| `voice.speech_ended` | `turn_id` |
| `voice.listening_stopped` | `turn_id, reason`: `released`, `silence`, `max_duration`, `cancelled`, `no_speech`, `mic_disabled`, `error` |
| `voice.transcription_partial` | `turn_id, text` (acumulado por segmentos) |
| `voice.transcription_completed` | `turn_id, text, language, audio_ms` |
| `voice.playback_started` | `turn_id, utterance_id, provider` |
| `voice.playback_level` | `utterance_id, level` (0..1), `position_ms`. No se audita ni se registra |
| `voice.playback_stopped` | `turn_id, utterance_id, reason, played_ms` |
| `voice.playback_interrupted` | `turn_id, reason` (`user`, `barge_in`, `new_turn`) |
| `voice.metrics` | `TurnMetrics.snapshot()` |
| `voice.error` | `code, stage` (`wakeword`, `vad`, `stt`, `tts`, `capture`, `playback`), `message, recoverable, turn_id?` |

Cada sentencia encolada es una locución con su `utterance_id`. Estado del personaje: `listening`→`listening`, `transcribing`/`waiting`→`thinking`, `speaking`→`speaking`, `voice.playback_interrupted`→`interrupted`, `voice.error` no recuperable→`error`.

## Ciclo del turno

`idle → listening → transcribing → waiting → speaking → idle`. El gestor nunca bloquea su bucle: `VAD` y `wakeword` corren en un hilo de escucha, STT en un hilo propio y TTS en otro. Con `barge_in_enabled=false` todo audio captado mientras Drakter habla se descarta, para no transcribir su propio eco. Con `true`, hacen falta `barge_in_min_ms` seguidos por encima de `barge_in_threshold`. El fallo de STT o de TTS emite `voice.error` y vuelve a `idle`: el texto sigue visible en el chat.

## Backend

```python
# backend/app/integrations/voice/service.py
class VoiceService:
    def __init__(self, settings: VoiceSettings, *, events: EventSink, agent: AgentTurnPort, audit: AuditPort, data_dir: Path, runtime_dir: Path) -> None: ...
    async def start(self) -> None: ...     # no hace nada si DRAKTER_VOICE_ENABLED=false
    async def stop(self) -> None: ...
    async def status(self) -> VoiceStatus: ...   # base de la herramienta get_voice_status

class EventSink(Protocol):
    async def publish(self, type: str, payload: Mapping[str, object], *, version: int = 1, experimental: bool = True) -> None: ...
class AgentTurnPort(Protocol):
    async def submit_user_turn(self, text: str, *, turn_id: str, source: Literal["voice"]) -> AsyncIterator[str]: ...   # deltas de texto
class AuditPort(Protocol):
    async def record(self, action: str, meta: Mapping[str, object]) -> None: ...   # sin texto ni audio
```

Rutas (`router.py`, prefijo `/api/v1/voice`, solo token de escritorio): `GET /status`, `POST /mic`, `POST /wakeword`, `POST /listen/start`, `POST /listen/stop`, `POST /listen/cancel`, `POST /interrupt`. No existe ruta para hacer hablar a Drakter: solo el puente llama a `speak`. El registro en `main.py`, la conexión con el hub de eventos, el servicio del agente y la auditoría los hace el integrador con los puertos anteriores.
