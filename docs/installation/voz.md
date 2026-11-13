# Instalar la voz

La voz es un proceso aparte (Pipecat 1.16.0, Python 3.12, venv propio) que arranca y supervisa el backend. Todo se instala una vez; en ejecución no se descarga nada. Cómo se usa: [Usar la voz](../usage/voz.md). Diseño para desarrolladores: [`voice/README.md`](../../voice/README.md).

## Requisitos

- Lo de [Instalar Drakter](instalar.md) ya hecho (backend, `npm ci`, Hermes).
- `uv` en el `PATH` (el script instala Python 3.12 con él si falta).
- Los modelos ya en `~/.local/share/drakter/models/` (ver más abajo). El script no los descarga.
- Sesión GNOME si quieres el atajo Super+J.
- Una clave `FISH_API_KEY` en `~/.config/drakter/.env` para la voz de Fish; sin ella habla Kokoro ([clave de API](clave-api.md)).

## 1. Entorno de voz

Ejecútalo **desde el checkout principal, no desde un worktree**: `drakter-contracts` queda instalado en editable apuntando al checkout donde lo ejecutes, y si ese es un worktree que luego se borra, el venv se rompe (el script avisa en ese caso).

```bash
scripts/install-voice.sh
```

Crea `~/.local/share/drakter/venvs/voice` (Python 3.12), instala `voice/requirements.lock` y `contracts/python`, copia Kokoro si falta y comprueba que están todos los modelos. Es idempotente: repítelo tras fusionar o mover el repositorio. `--relock` regenera el lock desde `voice/pyproject.toml`. El script se niega a instalar en `/tmp` o `/var/tmp`.

## 2. Modelos

Carpeta: `~/.local/share/drakter/models/`. El script se detiene con la ruta exacta si falta alguno.

| Carpeta | Contenido |
|---|---|
| `moonshine/` | modelos `small-streaming-es` y `tiny-streaming-es` (STT) |
| `smart-turn/` | `smart-turn-v3.2-cpu.onnx` (fin de turno) |
| `openwakeword/` | `hey_jarvis_v0.1.onnx`, `melspectrogram.onnx`, `embedding_model.onnx` |
| `kokoro/` | `kokoro-v1.0.int8.onnx` y `voices-v1.0.bin` (voz local) |

Si Kokoro no está, el script lo copia desde la ruta de `DRAKTER_KOKORO_SRC` (por defecto, una copia local de seguridad). Licencias de los modelos: `THIRD_PARTY_NOTICES.md`.

## 3. Atajo Super+J

```bash
scripts/install-shortcut.sh install   # crea el atajo de GNOME Super+J → scripts/drakter activate
scripts/install-shortcut.sh remove    # lo retira
```

Es idempotente y solo toca su propia entrada. Si instalas con `DRAKTER_DEV_NO_SANDBOX=1` en el entorno (desarrollo), el atajo arranca también así.

## 4. Comprobar

Desde la raíz del repositorio:

```bash
~/.local/share/drakter/venvs/voice/bin/python -m voice check
```

Imprime `OK` o `FALL` por cada proveedor y modelo, y acaba con `Todo en orden.`. No abre audio ni red. Comprobaciones de punta a punta, opcionales: `voice/README.md`, sección «Comprobaciones».

## 5. Arrancar con voz

La voz está activada por defecto (`DRAKTER_VOICE_ENABLED=true`). Arranca la app con el lanzador, que añade `--allow-loopback-in-peer-connection` (sin él no hay WebRTC sin red):

```bash
scripts/drakter-local.sh start anthropic   # o: scripts/drakter
```

El backend arranca el proceso de voz con el Python de `~/.local/share/drakter/venvs/voice`. Para usar otro: `DRAKTER_VOICE_PYTHON` (ruta absoluta) en `~/.config/drakter/.env`. Si falta el venv, la app arranca igual y publica un error de voz `dependency_missing`.

## 6. Frases fijas con tu perfil

Antes del 30-11-2026, con tu `voces.toml` ya rellenado ([Perfiles de voz](../usage/voces.md)):

```bash
~/.local/share/drakter/venvs/voice/bin/python -m voice phrases
```

## Configuración opcional

`~/.config/drakter/voice.toml` (claves planas con el nombre del campo de `VoiceConfig`) o variables `DRAKTER_VOICE_<CAMPO>`. La lista completa de campos y su precedencia está en [`voice/README.md`](../../voice/README.md#configuración). Ejemplos: `stt_model = "tiny"` (STT más ligero), `tts = ["kokoro"]` (solo voz local), `allow_paid = true` (permite Fish de pago tras el 30-11-2026).

## Problemas frecuentes

- **`ERROR: falta el modelo <ruta>`:** copia el modelo a esa ruta y repite el script.
- **`AVISO: drakter-contracts queda enlazado a un worktree`:** repite el script desde el checkout principal.
- **`FALL tts/fish` o un `FALL` de módulo:** el paquete no se importa; repite el script con el venv correcto.
- **Error `dependency_missing` en la app:** falta `~/.local/share/drakter/venvs/voice` o `DRAKTER_VOICE_PYTHON` apunta a algo que no existe.
- **No hay voz de Fish:** falta `FISH_API_KEY` o no hay red; habla Kokoro, con un único aviso.
