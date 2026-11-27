# Configuración: el archivo `.env`

Toda la configuración de Drakter, incluidas las claves, va en **un único archivo**: `~/.config/drakter/.env`. Si tienes definido `XDG_CONFIG_HOME`, va en `$XDG_CONFIG_HOME/drakter/.env`. La plantilla es [`.env.example`](../../.env.example), en la raíz del repositorio, y solo tiene nombres, nunca valores.

> **Importante.** Drakter **no lee ningún `.env` dentro del repositorio**, ni en la raíz ni en `backend/`. Si pones tus claves en `Drakter/.env`, no se usarán y además corres el riesgo de subirlas a git. El `.gitignore` ignora `.env`, pero no te fíes de eso.

## Crear el archivo

```sh
mkdir -p ~/.config/drakter
cp -n .env.example ~/.config/drakter/.env     # -n: no pisa uno que ya exista
chmod 600 ~/.config/drakter/.env              # solo tu usuario puede leerlo
```

Ábrelo con tu editor (`nano ~/.config/drakter/.env`) y rellena lo que necesites. Lo mínimo para usar el modelo real es una línea:

```sh
ANTHROPIC_API_KEY=sk-ant-...
```

Reinicia Drakter después de cambiar el archivo: se lee al arrancar.

## Formato

- Una variable por línea: `NOMBRE=valor`, **sin espacios** alrededor del `=` y **sin comillas**.
- Las líneas que empiezan por `#` son comentarios.
- Una línea sin valor (`NOMBRE=`) se ignora y se usa el valor por defecto. Por eso puedes dejar la plantilla entera y rellenar solo lo que quieras.
- Los booleanos aceptan `true`/`false`, y en la voz también `1`, `yes` y `on`.
- Las listas van separadas por comas, sin espacios: `DRAKTER_VOICE_TTS=fish,kokoro`.
- Las rutas deben ser **absolutas** (`/home/tu-usuario/...`). Una ruta relativa hace que el backend no arranque y muestre `invalid configuration`.

Comprueba que el archivo existe y tiene permisos seguros, sin leer su contenido:

```sh
scripts/check-env.sh
```

## Cómo llega cada variable

Electron lanza el backend con un **entorno filtrado**. De las variables exportadas en tu terminal solo le llegan `DRAKTER_DATA_DIR`, las `XDG_*` y, en desarrollo, `DRAKTER_MODEL_PROVIDER` y `DRAKTER_DEV_STUB_URL`. **Todo lo demás, incluida `ANTHROPIC_API_KEY`, tiene que estar en `~/.config/drakter/.env`.** Exportarlo en la shell no basta.

El backend, a su vez, solo pasa al proceso de voz las variables `DRAKTER_VOICE_*` de su lista blanca y las claves `FISH_API_KEY`, `DEEPGRAM_API_KEY` y `GROQ_API_KEY`.

## Referencia de variables

### Claves (secretos)

| Variable | Obligatoria | Para qué |
|---|---|---|
| `ANTHROPIC_API_KEY` | Sí, para el modelo real | Clave de Anthropic para Claude Haiku 5.5. Se obtiene en la consola de Anthropic. Sin ella, el agente solo funciona con el stub de desarrollo (`DRAKTER_MODEL_PROVIDER=dev_stub`). Detalle: [clave-api.md](clave-api.md) |
| `FISH_API_KEY` | No | Voz en la nube de Fish Audio. Sin ella, Drakter habla con Kokoro, la voz local |
| `DEEPGRAM_API_KEY` | No | Reconocimiento de voz en la nube (Deepgram Nova-3, región UE). Es el preferido si está |
| `GROQ_API_KEY` | No | Reconocimiento en la nube con Groq Whisper si no hay Deepgram. Sin ninguna de las dos, se usa Moonshine local |

### Backend

| Variable | Por defecto | Para qué |
|---|---|---|
| `DRAKTER_DATA_DIR` | `~/.local/share/drakter` | Ruta absoluta de la base de datos (`drakter.db`), las copias (`backups/`) y los logs (`logs/`) |
| `DRAKTER_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` o `ERROR` |

### Agente (Hermes)

| Variable | Por defecto | Para qué |
|---|---|---|
| `DRAKTER_ENV` | `development` | `development` o `production`. En `production` no se admite el stub |
| `DRAKTER_AGENT_PROVIDER` | `hermes` | `hermes` (el agente real) o `fake` (respuestas fijas, para pruebas) |
| `DRAKTER_MODEL_PROVIDER` | `anthropic` | `anthropic` (Claude real) o `dev_stub` (modelo simulado de `tools/dev-llm-stub`) |
| `DRAKTER_MODEL_NAME` | `claude-haiku-5-5` | Modelo del agente |
| `DRAKTER_HERMES_PYTHON` | `hermes-python` (en el `PATH`) | Python del venv de Hermes. Lo crea `scripts/install-hermes.sh` en `~/.local/bin/hermes-python` |
| `DRAKTER_DEV_STUB_URL` | `http://127.0.0.1:28517` | Dirección del stub. Solo se admite `http` en loopback |
| `DRAKTER_AGENT_MAX_TURNS` | `12` | Llamadas al modelo como mucho por turno |
| `DRAKTER_TURN_TIMEOUT_S` | `300` | Tope de un turno, en segundos |
| `DRAKTER_IDLE_TIMEOUT_S` | `120` | Tope sin actividad dentro de un turno, en segundos |

### Voz: arranque

| Variable | Por defecto | Para qué |
|---|---|---|
| `DRAKTER_VOICE_ENABLED` | `true` | Con `false` no se lanza el proceso de voz (la app funciona sin voz) |
| `DRAKTER_VOICE_PYTHON` | `~/.local/share/drakter/venvs/voice/bin/python` | Python del venv de voz (ruta absoluta). Lo crea `scripts/install-voice.sh` |

### Voz: ajustes finos

El proceso de voz acepta **cualquier campo de `VoiceConfig`** (en [`voice/config.py`](../../voice/config.py)) como `DRAKTER_VOICE_<CAMPO_EN_MAYÚSCULAS>`. También se pueden poner en `~/.config/drakter/voice.toml`, con el nombre del campo en minúsculas. Los más útiles:

| Variable | Por defecto | Para qué |
|---|---|---|
| `DRAKTER_VOICE_STT` | `auto` | Reconocimiento: `auto` (según las claves), `deepgram`, `groq` o `moonshine` (local) |
| `DRAKTER_VOICE_TTS` | `fish,kokoro` | Voces en orden de preferencia. Si la primera falla, pasa a la siguiente |
| `DRAKTER_VOICE_KOKORO_VOICE` | `ef_dora` | Voz de Kokoro |
| `DRAKTER_VOICE_WAKE_THRESHOLD` | `0.3` | Sensibilidad de «Hey Jarvis», de 0 a 1. Súbela si se activa sola |
| `DRAKTER_VOICE_FOLLOWUP_S` | `20` | Segundos sin voz tras responder antes de volver a reposo |
| `DRAKTER_VOICE_THREADS` | `2` | Hilos por modelo local |
| `DRAKTER_VOICE_ALLOW_PAID` | `false` | Permitir modelos de pago de Fish. Por defecto solo el gratuito |
| `DRAKTER_VOICE_DUMP_AUDIO` | `false` | Guarda un `.wav` por turno para depurar (se borran a las 24 h) |

El resto (umbrales del detector de voz, del fin de turno, del barge-in…) está comentado en `voice/config.py`. Diseño de la voz: [`voice/README.md`](../../voice/README.md).

### Automejora

| Variable | Por defecto | Para qué |
|---|---|---|
| `DRAKTER_IMPROVEMENT_REPO` | — | Ruta absoluta de un clon de pruebas donde se evalúan las propuestas de mejora. Sin ella, evaluar queda bloqueado (nunca se toca el repositorio de producción) |

### Reservadas

`OPENVIKING_ENDPOINT` y `OPENVIKING_API_KEY` no las lee nada todavía: OpenViking está desactivado en la v1 ([hermes-y-openviking.md](hermes-y-openviking.md)).

## Variables de shell (no van en el `.env`)

Estas se usan al lanzar scripts o la app desde una terminal. **No** se leen del `.env`:

| Variable | Dónde | Para qué |
|---|---|---|
| `DRAKTER_DEV_NO_SANDBOX=1` | `scripts/dev.sh`, lanzador | Solo en desarrollo: arrancar Electron sin sandbox ([sandbox-electron.md](sandbox-electron.md)) |
| `DRAKTER_CHARACTER_RIV` | Electron | Ruta de tu personaje `.riv` ([personaje.md](../usage/personaje.md)) |
| `DRAKTER_VOICE_VENV`, `DRAKTER_KOKORO_SRC` | `scripts/install-voice.sh` | Dónde crear el venv de voz y de dónde copiar los modelos de Kokoro |
| `DRAKTER_BIN_DIR`, `DRAKTER_RUNTIME_DIR` | `scripts/install-hermes.sh`, `scripts/install-appimage.sh` | Dónde enlazar `hermes-python` y dónde van los runtimes |
| `DRAKTER_INSTALL_DIR` | `scripts/install-appimage.sh` | Dónde instalar el AppImage (por defecto `~/.local/opt/drakter`) |

## Problemas frecuentes

- **El agente no responde y el log dice `agent_unavailable` o falta la clave:** `ANTHROPIC_API_KEY` no está en `~/.config/drakter/.env`, o tiene espacios o comillas.
- **`invalid configuration: <campos>` al arrancar:** algún valor no es válido. Suele ser una ruta relativa o un valor fuera de la lista (por ejemplo, `DRAKTER_LOG_LEVEL=info` en minúsculas).
- **He cambiado el `.env` y no pasa nada:** reinicia Drakter (`scripts/drakter-local.sh stop` y `start`, o cierra la ventana y vuelve a abrir).
- **Más:** [problemas.md](../usage/problemas.md).
