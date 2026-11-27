# Drakter

> **English summary.** Drakter is a local-first personal AI agent with its own desktop app, built for a single user on Linux. An Electron + React desktop talks to a local FastAPI + SQLite backend, which drives a [Hermes Agent](https://github.com/NousResearch/hermes-agent) runtime backed by Claude Haiku 5.5. The agent manages tasks, projects, habits, calendar, subjects, a file storage with full-text search, relations between items and its own memory, always through validated backend tools with explicit confirmation for destructive actions. Status: v0.1.0 pre-release — the v1 scope is integrated and verified module by module; voice v2 (Pipecat + WebRTC loopback) is integrated; the character is one of eight selectable 3D avatars (Three.js); and an optional holographic "Jarvis mode" UI (three layouts) can be switched on from the UI, by voice or by the agent. The self-improvement screen is still in progress. Documentation is in Spanish. License: [AGPL-3.0-only](LICENSE) (it incorporates code from Roamies); the license does not grant rights to the Drakter name.

Agente personal de IA con aplicación de escritorio propia. Local-first, para un solo usuario, en Linux primero.

## Qué es

Tres sistemas conectados por APIs internas:

- **Drakter Core:** el agente (Hermes + Claude Haiku 5.5), su personalidad, su memoria y sus herramientas.
- **Drakter Desktop:** Electron + React + TypeScript + Tailwind + shadcn/ui, con un personaje animado y paneles por módulo.
- **Drakter Workspace:** SQLite (+ FTS5) con tareas, proyectos, hábitos, calendario, asignaturas, almacén y relaciones.

En medio, un backend FastAPI (REST + WebSocket) que es el único dueño de los datos. El agente nunca toca la base de datos: llama a herramientas del backend, que validan parámetros, permisos y relaciones, piden confirmación para lo destructivo y lo registran en auditoría.

## Estado

**v0.1.0, pre-release (2026-11-13).** El alcance de la v1 está integrado y verificado módulo a módulo; la app arranca (Electron + backend + Hermes) con Claude Haiku 5.5 real. En las Checklists 0–17 hay 260 de 295 casillas en `[x]` (29 con una reserva ⚠️), 25 sin marcar con ⚠️ y 10 sin código. Pasada integrada final: `scripts/verify-all.sh` 44/44.

Voz v2 (Pipecat 1.16.0 + WebRTC por loopback) integrada en la app: activación con Super+J o «Hey Jarvis», conversación, barge-in, trabajos en segundo plano; primer audio 2,36-2,88 s tras callar el usuario y RSS del proceso de voz ~990 MB (máquina de desarrollo, sin GPU). Guía: [`docs/usage/voz.md`](docs/usage/voz.md).

**Avatares 3D y modo Jarvis (2026-11-26).** El personaje es un avatar 3D elegible entre 8 (por defecto Holo-Contorno; el personaje clásico SVG o tu `.riv` siguen disponibles). El **modo Jarvis** es una segunda interfaz holográfica, con tres diseños (Núcleo, Holomesa y Visor), sobre los mismos datos. Se activa con un botón, `Ctrl+Shift+J`, `Ctrl+K`, la bandeja, la voz («modo Jarvis») o el agente. Drakter sigue siendo la interfaz de inicio. En la UHD 620, en reposo, el proceso que dibuja la ventana usa entre el 7 % y el 9 % de un núcleo. Guías: [`docs/usage/modo-jarvis.md`](docs/usage/modo-jarvis.md) y [`docs/usage/personaje.md`](docs/usage/personaje.md).

**Autoconsciencia y contexto (2026-11-27).** Drakter sabe qué es (versión, modelo, herramientas y límites) y en qué ordenador corre: lo mide solo y, si lo pasas a otro equipo o cambias el hardware, lo nota y lo avisa. En cada mensaje sabe en qué punto de la conversación vais y puede buscar y leer conversaciones anteriores, que trata como datos no confiables. Guía: [`docs/usage/consciencia.md`](docs/usage/consciencia.md).

Pendiente sobre todo: OpenViking, pantalla de automejora, `.deb` instalado, probar la voz del modo Jarvis con micrófono real y parte de las mediciones de rendimiento.

<details>
<summary>Estado por bloque</summary>

| Bloque | Dónde | `[x]` | Estado verificado |
|---|---|---|---|
| Arquitectura y preparación (CL0) | raíz, `contracts/`, `docs/`, `scripts/` | 14/14 | Verificado |
| Escritorio (CL1) | `desktop/` | 13/13 | Verificado en la app: Electron con backend real, ventana, navegación de 10 secciones, área central, panel contextual, notificaciones, configuración y gestión de errores; búsqueda global (Ctrl+K), Hoy y Ajustes contra el backend. Empaquetado configurado (AppImage generado; el `.deb`, ver CL17) |
| Backend FastAPI + SQLite (CL2) | `backend/app/` | 12/12 | Verificado, incluido el sistema de permisos: guardia de red y roles, y confirmaciones cableadas en el arranque con un único camino (`ActionService`, 300 s) |
| Hermes y chat (CL3) | `backend/app/integrations/`, `agent/` | 11/12 | GUI → backend → Hermes v0.22.7 → respuesta en el chat con Claude Haiku 5.5 real: sesiones, envío, recepción, eventos y recuperación tras caída del runner verificados. ⚠️ La primera Skill no la carga Hermes |
| Personalidad y contexto (CL4) | `agent/identity/`, `agent/context/`, `agent/knowledge/` | 17/17 | Verificado: 14 archivos compuestos en el `SOUL.md` de Hermes, con la seguridad primero, y consistencia de personalidad comprobada con Claude Haiku 5.5 real |
| Personaje (CL5) | `desktop/src/character/` | 16/19 | 8 avatares 3D elegibles (Three.js), con los 9 estados, boca sincronizada con el audio real y respaldo al SVG; el `.riv` del usuario sigue siendo opcional. Ver `IMPLEMENTATION_STATUS.md` |
| Base de datos y migraciones (CL6) | `backend/migrations/` (0001–0013) | 18/18 | Verificado: 36 tablas, integridad referencial, copia y restauración |
| Tareas y proyectos (CL7) | `backend/app/services/tasks*.py`, `desktop/src/modules/tasks/`, `projects/` | 23/23 | Verificado el backend y las 21 herramientas, desde la GUI y desde el chat con Haiku real, incluido el borrado pedido por el agente, que pide confirmación y se aprueba en la app |
| Hábitos (CL8) | `backend/app/services/habits*.py`, `desktop/src/modules/habits/` | 12/12 | Verificado: CRUD, frecuencia y días, recordatorios, registros, historial, estadísticas, objetivos y persistencia. ⚠️ Herramientas sin probar con modelo |
| Calendario y asignaturas (CL9) | `backend/app/services/calendar*.py`, `subjects.py`, `desktop/src/modules/calendar/`, `subjects/` | 18/18 | Verificado: vistas diaria, semanal y mensual, eventos, bloques, solapamientos, zonas horarias, asignaturas, horarios y sesiones, recursos y tareas asociadas, borrado con confirmación |
| Almacén (CL10) | `backend/app/services/storage*.py`, `desktop/src/modules/storage/` | 25/25 | Verificado: catálogo, carpetas, etiquetas, índice FTS5, lectura bajo demanda (texto, PDF, imágenes, enlaces), límites de comprimidos y rutas permitidas. ⚠️ Herramientas sin probar con modelo |
| Relaciones (CL11) | `backend/app/services/relations.py`, `desktop/src/modules/relationships/` | 13/14 | Verificado el servicio, los tipos, las validaciones, las consultas y la integridad; leer, buscar y crear desde el agente con Haiku real. ⚠️ Borrar desde el agente sin recomprobar con el modelo |
| Memoria (CL12) | `memory/`, `backend/app/integrations/memory/` | 20/22 | Verificado el adaptador SQLite + FTS5 y su ciclo (extraer, clasificar, deduplicar, contradicciones, caducidad); olvidar o aprobar recuerdos pasa por confirmación. ⚠️ OpenViking desactivado |
| Skills y herramientas (CL13) | `agent/skills/`, `backend/app/tools/` | 7/15 | 95 herramientas por MCP, todas las del catálogo con parámetros, permisos y errores verificados. ⚠️ Las Skills están inertes en Hermes (`skill_manage` desactivado) |
| Voz (CL14) | `voice/`, `backend/app/integrations/voice/`, `desktop/src/voice/` | ver `IMPLEMENTATION_STATUS.md` | Voz v2: Pipecat 1.16.0, WebRTC por loopback, Moonshine, openWakeWord («Hey Jarvis»), Smart Turn, Fish con Kokoro de respaldo. Detalle en [`voice/README.md`](voice/README.md) |
| Automejora (CL15) | `improvement/`, `backend/app/services/improvement_*.py` | 11/11 | Verificado el ciclo (feedback, propuestas, evaluación aislada, rama Git, revertir) y que no puede cambiar nada sin aprobación. ⚠️ Sin pantalla de automejora |
| Seguridad (CL16) | `backend/app/permissions/`, `tests/security/` | 14/15 | Revisión adversarial hecha (banco final 169 BLOCKED / 12 BREACH / 0 ERROR). ⚠️ Brechas de diseño conocidas: ver [SECURITY.md](SECURITY.md) |
| Optimización y lanzamiento (CL17) | `desktop/electron-builder.*`, `scripts/`, `docs/usage/` | ver `IMPLEMENTATION_STATUS.md` | AppImage y `.deb` regenerados con backend, identidad y voz empaquetados; instalador sin sudo (`install-appimage.sh`), actualización por git (`update.sh`), copia inicial y guías de uso. ⚠️ `.deb` sin instalar (sudo) y sandbox desde el menú sin probar |

| Modo Jarvis (ampliación) | `desktop/src/jarvis/`, `desktop/src/stores/{uiMode,appearance}.ts`, `backend/app/tools/ui.py` | 15/16 | Probado en Electron real con la UHD 620: tres interfaces, cambio de modo, interfaz y avatar por todas las vías, y confirmaciones visibles. ⚠️ Voz sin micrófono real |

Detalle por casilla en [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) y estado operativo en [`docs/RUN_STATE.md`](docs/RUN_STATE.md).

</details>

## Requisitos

- **Linux** con sesión gráfica. La arquitectura está preparada para Windows, pero solo se ha probado en Linux.
- **Python 3.12** para el backend (`requires-python` admite solo 3.12; se usa el comando `python3.12`).
- **Python >= 3.14** para Hermes, en un venv propio separado del backend. Hermes se instala desde git con el tag v0.22.7 (`b200f5bc`), nunca desde PyPI (ver [`docs/installation/hermes-y-openviking.md`](docs/installation/hermes-y-openviking.md)).
- **[`uv`](https://docs.astral.sh/uv/)** para crear los venvs (lo usan los scripts de instalación). El backend también se puede instalar con `python3.12 -m venv` + `pip install -r backend/requirements.txt`.
- **Node 24 y npm.**
- **Hermes Agent** instalado en ese venv (`hermes-python` en el `PATH` o `DRAKTER_HERMES_PYTHON`). Sin Hermes la app abre, pero el chat y el agente no funcionan.
- Una **clave de API de Anthropic** para usar el modelo real. Sin ella, el agente puede usar el stub de desarrollo (`tools/dev-llm-stub`) en lugar del modelo; Hermes sigue siendo necesario.

Se ha desarrollado en un portátil con 14 GB de RAM y gráfica integrada; la voz local es la parte más exigente. Para la voz, `uv` y los modelos en `~/.local/share/drakter/models/` (ver [`docs/installation/voz.md`](docs/installation/voz.md)).

## Instalación

- **Guía completa desde el repositorio**, paso a paso con todos los comandos (Python 3.12 y venv, `requirements.txt`, Node, Hermes, voz, `.env`, comprobación, arranque, actualización y desinstalación): [`docs/installation/instalar.md`](docs/installation/instalar.md).
- **App empaquetada** (AppImage, sin sudo): [`docs/usage/primeros-pasos.md`](docs/usage/primeros-pasos.md).

**App instalada (AppImage, sin sudo).** Tras preparar el repositorio (abajo):

```sh
scripts/package.sh appimage        # backend congelado + escritorio -> desktop/release/Drakter-<versión>.AppImage
scripts/install-appimage.sh        # ~/.local/opt/drakter, lanzador drakter-app, menú y comprobación de runtimes
```

La voz (venv y modelos) y Hermes no van en el paquete: el instalador comprueba que existan y, con `--runtimes`, los instala con `scripts/install-hermes.sh` y `scripts/install-voice.sh`. En Ubuntu 24+ imprime además un comando con sudo, de una sola vez, para el perfil AppArmor del sandbox. `scripts/package.sh deb` genera el `.deb`.

**Desde el repositorio (desarrollo):**

```sh
git clone https://github.com/Lordi898/Drakter.git
cd Drakter

# Backend (Python 3.12), opción A: venv + pip + requirements.txt
cd backend
python3.12 -m venv .venv
source .venv/bin/activate          # activar (el prompt muestra «(.venv)»); salir: deactivate
pip install --upgrade pip
pip install -r requirements.txt    # desde backend/: incluye los contratos (-e ../contracts/python)
deactivate
cd ..
# Backend, opción B (equivalente, la que usan los scripts y el CI):  (cd backend && uv sync --frozen)

(cd desktop && npm ci)             # escritorio (Node 24)
scripts/install-hermes.sh          # agente Hermes v0.22.7 en su venv (Python 3.14)
scripts/install-voice.sh           # opcional: voz (Python 3.12, venv propio)

mkdir -p ~/.config/drakter && cp -n .env.example ~/.config/drakter/.env && chmod 600 ~/.config/drakter/.env
nano ~/.config/drakter/.env        # al menos ANTHROPIC_API_KEY

scripts/check-env.sh               # OK / AVISO / FALTA
scripts/drakter-local.sh start anthropic
```

`backend/requirements.txt` se genera desde `backend/uv.lock` con `scripts/export-requirements.sh` (mismas versiones; el CI comprueba que coinciden). No lo edites a mano.

Hermes va aparte, en su propio venv con Python >= 3.14: `scripts/install-hermes.sh` lo instala (v0.22.7, commit fijado, desde git) en `~/.local/share/drakter/venvs/hermes` y crea `hermes-python`. Detalle en [`docs/installation/hermes-y-openviking.md`](docs/installation/hermes-y-openviking.md). Los runtimes nunca van en `/tmp` ni `/var/tmp`.

- Electron 45 ya no trae `postinstall` y descarga su binario al primer arranque; por eso `desktop/package.json` tiene un `postinstall` propio (`desktop/scripts/ensure-electron.cjs`, idempotente) que lo baja durante `npm ci`. Si lo instalaste sin él: `node desktop/scripts/ensure-electron.cjs`.
- `scripts/check-env.sh` imprime líneas `OK`, `AVISO` o `FALTA` y sale con 1 si falta algo. Comprueba Python 3.12, que haya un Python >= 3.14 para Hermes (no comprueba que Hermes esté instalado), que `python3.12`, `python3.14`, `hermes-python`, `backend/.venv` y los venvs de `~/.local/share/drakter/venvs/` no resuelvan a `/tmp` o `/var/tmp` ni sean enlaces rotos (y da el comando para arreglarlo), Node, npm, `uv`, `~/.config/drakter/.env` (sin leerlo), el sandbox de Electron y la sesión gráfica.

## Actualizar y copias de seguridad

```sh
scripts/update.sh             # git pull --ff-only, dependencias que cambien, copia, migraciones y reinicio
scripts/update.sh --package   # además reconstruye y reinstala el AppImage
cd backend && .venv/bin/python -m app.database.cli backup    # copia (también: restore <archivo>, status)
```

La app empaquetada trae la misma CLI: `~/.local/opt/drakter/app/resources/backend/drakter-backend -m app.database.cli backup`. Guía: [`docs/usage/copias-y-actualizacion.md`](docs/usage/copias-y-actualizacion.md). Problemas frecuentes: [`docs/usage/problemas.md`](docs/usage/problemas.md).

## Configuración

La configuración va en `~/.config/drakter/.env` (respeta `XDG_CONFIG_HOME`). **No se lee ningún `.env` en la raíz del repositorio.** El backend lo lanza Electron con un entorno filtrado por lista blanca: de las variables exportadas en la shell solo le llegan `DRAKTER_DATA_DIR`, las `XDG_*` y, en desarrollo, `DRAKTER_MODEL_PROVIDER` y `DRAKTER_DEV_STUB_URL`. Todo lo demás (incluida `ANTHROPIC_API_KEY`) tiene que estar en ese `.env`. [`.env.example`](.env.example) es la plantilla completa, solo con nombres. Guía con todas las variables: [`docs/installation/configuracion-env.md`](docs/installation/configuracion-env.md).

```sh
mkdir -p ~/.config/drakter
cp -n .env.example ~/.config/drakter/.env
chmod 600 ~/.config/drakter/.env
```

Las líneas sin valor (`NOMBRE=`) se ignoran y se usa el valor por defecto; basta con rellenar las que necesites (al menos `ANTHROPIC_API_KEY` para el modelo real). No hay puerto que configurar: Electron lanza el backend en `127.0.0.1` con un puerto efímero.

Variables que se leen de `~/.config/drakter/.env`:

| Variable | Por defecto | Para qué |
|---|---|---|
| `DRAKTER_DATA_DIR` | Directorio de datos del usuario | Ruta absoluta de datos, base de datos y logs |
| `DRAKTER_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` o `ERROR` |
| `DRAKTER_ENV` | `development` | `development` o `production` (en producción no se admite el stub) |
| `ANTHROPIC_API_KEY` | — | Clave de Anthropic; obligatoria con `DRAKTER_MODEL_PROVIDER=anthropic` |
| `DRAKTER_AGENT_MAX_TURNS`, `DRAKTER_TURN_TIMEOUT_S`, `DRAKTER_IDLE_TIMEOUT_S` | `12`, `300`, `120` | Límites del turno del agente |
| `DRAKTER_AGENT_PROVIDER` | `hermes` | `hermes` o `fake` |
| `DRAKTER_MODEL_PROVIDER` | `anthropic` | `anthropic` o `dev_stub` |
| `DRAKTER_MODEL_NAME` | `claude-haiku-5-5` | Modelo del agente |
| `DRAKTER_HERMES_PYTHON` | `hermes-python` (en el `PATH`) | Python del venv de Hermes |
| `DRAKTER_DEV_STUB_URL` | `http://127.0.0.1:28517` | Stub de desarrollo; solo `http` en loopback |
| `DRAKTER_VOICE_ENABLED` | `true` | Activa el proceso de voz; con `false` no se lanza |
| `DRAKTER_VOICE_PYTHON` | `~/.local/share/drakter/venvs/voice/bin/python` | Python del venv de voz (ruta absoluta) |
| `DRAKTER_VOICE_<CAMPO>` | ver `voice/config.py` | Cualquier campo de `VoiceConfig` (`DRAKTER_VOICE_STT`, `DRAKTER_VOICE_TTS`, `DRAKTER_VOICE_WAKE_THRESHOLD`…); también en `~/.config/drakter/voice.toml` (ver [`voice/README.md`](voice/README.md)) |
| `FISH_API_KEY` | — | Clave de Fish Audio para la voz; sin ella habla Kokoro (local) |
| `DEEPGRAM_API_KEY`, `GROQ_API_KEY` | — | Reconocimiento de voz en la nube (Deepgram, si no Groq); sin ellas, Moonshine local |
| `DRAKTER_IMPROVEMENT_REPO` | — | Repositorio de pruebas de la automejora; sin él, evaluar queda bloqueado |

`OPENVIKING_ENDPOINT` y `OPENVIKING_API_KEY` están reservadas: nada las lee todavía. Más: [clave de API](docs/installation/clave-api.md).

## Arranque

```sh
scripts/drakter-local.sh start anthropic  # app con Claude Haiku 5.5 real
scripts/drakter-local.sh start            # app con el stub de desarrollo
scripts/drakter-local.sh status
scripts/drakter-local.sh stop
scripts/dev.sh [all|desktop]              # escritorio en primer plano
```

- El backend no se arranca aparte: lo lanza el proceso principal de Electron, con las credenciales por stdin y un puerto efímero.
- `drakter-local.sh` deja la app y el stub desacoplados de la terminal. Logs y cómo parar sin dejar procesos: [`docs/RUN_STATE.md`](docs/RUN_STATE.md).
- Pasada integrada completa (backend + stub + Electron): `scripts/verify-all.sh`.

**Arrancar con voz.** Instala el entorno una vez con `scripts/install-voice.sh` (desde el checkout principal) y el atajo con `scripts/install-shortcut.sh install` (Super+J); comprueba con `~/.local/share/drakter/venvs/voice/bin/python -m voice check`. Después arranca con `scripts/drakter-local.sh start anthropic` o con `scripts/drakter`: ambos pasan a Electron `--allow-loopback-in-peer-connection`, necesario para el WebRTC por loopback (la voz funciona también sin red). `scripts/drakter activate` equivale a Super+J. Uso: [`docs/usage/voz.md`](docs/usage/voz.md); instalación: [`docs/installation/voz.md`](docs/installation/voz.md); diseño: [`voice/README.md`](voice/README.md).

**Sandbox de Electron.** Si AppArmor restringe los espacios de nombres sin privilegios (`kernel.apparmor_restrict_unprivileged_userns=1`, el caso de Ubuntu reciente), Electron aborta con un error de `chrome-sandbox`. En desarrollo: `ELECTRON_DISABLE_SANDBOX=1 DRAKTER_DEV_NO_SANDBOX=1 scripts/dev.sh`. En producción el sandbox es obligatorio. Detalle en [`docs/installation/sandbox-electron.md`](docs/installation/sandbox-electron.md).

## Arquitectura en breve

```
Electron (main) ──lanza──▶ backend FastAPI (127.0.0.1, puerto efímero)
   │  proxy con lista blanca de rutas            │
React (renderer) ◀── REST + WebSocket ──▶  servicios ── SQLite + FTS5 (Workspace)
                                                  │
                                       runner de Hermes (proceso aparte)
                                       ── herramientas MCP ──▶ backend
```

- **Una sola fuente de verdad:** el Workspace en SQLite, con migraciones controladas (`backend/migrations/`).
- **Herramientas, no acceso directo:** las 95 herramientas del agente tienen esquema, permisos, validación, resultado estructurado y errores; las destructivas pasan por confirmación (`ActionService`).
- **Datos no confiables:** los documentos del almacén y la memoria recuperada se tratan como datos; no pueden cambiar las instrucciones ni las reglas de seguridad.
- **Personalidad en archivos** (`agent/identity/`), separada del modelo; proveedor del modelo intercambiable; voz separada del razonamiento.

Más en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Estructura de carpetas

```
.
├── .claude/        instrucciones, agentes, skills y comandos para Claude Code
├── .github/        CI, plantillas de issues y PR, Dependabot
├── agent/          identidad, contexto, conocimiento, skills y evaluaciones del agente
├── backend/        FastAPI + SQLite (API REST, WebSocket, migraciones)
├── contracts/      contratos de API, eventos y modelos compartidos
├── desktop/        Electron, React, TypeScript
├── docs/           plan, estado, decisiones, arquitectura, instalación y uso
├── improvement/    automejora y evaluaciones
├── memory/         memoria del agente
├── scripts/        arranque, empaquetado e instalación, actualización, comprobación del entorno y pasada integrada
├── tests/          pasada e2e y banco de seguridad
├── tools/          dev-llm-stub
└── voice/          proceso de voz (Pipecat)
```

## Documentación

- [Primeros pasos](docs/usage/primeros-pasos.md) · [Instalación completa](docs/installation/instalar.md) · [Configuración (`.env`)](docs/installation/configuracion-env.md) · [Uso por módulo](docs/usage/README.md) · [Modo Jarvis](docs/usage/modo-jarvis.md) · [Autoconsciencia y contexto](docs/usage/consciencia.md) · [Solución de problemas](docs/usage/problemas.md)
- [Arquitectura](docs/ARCHITECTURE.md) · [Convenciones](docs/CONVENTIONS.md)
- [Estado de implementación](docs/IMPLEMENTATION_STATUS.md) · [Decisiones](docs/DECISIONS.md) · [Plan maestro](docs/MASTER_PLAN.md)
- [Registro de cambios](CHANGELOG.md)

## Contribuir y seguridad

- Cómo contribuir: [CONTRIBUTING.md](CONTRIBUTING.md). Normas de convivencia: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Vulnerabilidades: **no abras un issue público**; sigue [SECURITY.md](SECURITY.md).
- Contenido y dependencias de terceros: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Licencia

Drakter se distribuye bajo la [GNU Affero General Public License v3.0](LICENSE) (SPDX: `AGPL-3.0-only`), porque incorpora código de [Roamies](https://github.com/KenKaiii/Roamies) (© Ken Kai, AGPL-3.0). Ver también [NOTICE](NOTICE). El código anterior a este cambio sigue disponible bajo Apache-2.0 en el historial de Git.

La licencia no concede permiso para usar el nombre «Drakter», sus logotipos ni el personaje como marca (aviso aparte de la licencia, ver [NOTICE](NOTICE)), salvo lo razonable para describir el origen del software. Si publicas una versión modificada, usa otro nombre.

El contenido de terceros conserva su propia licencia: ver [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
