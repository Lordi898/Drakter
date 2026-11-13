# Drakter

> **English summary.** Drakter is a local-first personal AI agent with its own desktop app, built for a single user on Linux. An Electron + React desktop talks to a local FastAPI + SQLite backend, which drives a [Hermes Agent](https://github.com/NousResearch/hermes-agent) runtime backed by Claude Haiku 5.5. The agent manages tasks, projects, habits, calendar, subjects, a file storage with full-text search, relations between items and its own memory, always through validated backend tools with explicit confirmation for destructive actions. Status: v0.1.0 pre-release — the v1 scope is integrated and verified module by module; voice, the animated Rive character and the self-improvement screen are still in progress. Documentation is in Spanish. License: [Apache-2.0](LICENSE); the license does not grant rights to the Drakter name.

Agente personal de IA con aplicación de escritorio propia. Local-first, para un solo usuario, en Linux primero.

## Qué es

Tres sistemas conectados por APIs internas:

- **Drakter Core:** el agente (Hermes + Claude Haiku 5.5), su personalidad, su memoria y sus herramientas.
- **Drakter Desktop:** Electron + React + TypeScript + Tailwind + shadcn/ui, con un personaje animado y paneles por módulo.
- **Drakter Workspace:** SQLite (+ FTS5) con tareas, proyectos, hábitos, calendario, asignaturas, almacén y relaciones.

En medio, un backend FastAPI (REST + WebSocket) que es el único dueño de los datos. El agente nunca toca la base de datos: llama a herramientas del backend, que validan parámetros, permisos y relaciones, piden confirmación para lo destructivo y lo registran en auditoría.

## Estado

**v0.1.0, pre-release (2026-11-13).** El alcance de la v1 está integrado y verificado módulo a módulo; la app arranca (Electron + backend + Hermes) con Claude Haiku 5.5 real. En las Checklists 0–17 hay 260 de 295 casillas en `[x]` (29 con una reserva ⚠️), 25 sin marcar con ⚠️ y 10 sin código. Pasada integrada final: `scripts/verify-all.sh` 44/44.

Pendiente sobre todo: voz conectada a la app, personaje Rive (hoy hay un provisional en SVG con los mismos estados), OpenViking, pantalla de automejora, `.deb` instalado y mediciones de rendimiento.

<details>
<summary>Estado por bloque</summary>

| Bloque | Dónde | `[x]` | Estado verificado |
|---|---|---|---|
| Arquitectura y preparación (CL0) | raíz, `contracts/`, `docs/`, `scripts/` | 14/14 | Verificado |
| Escritorio (CL1) | `desktop/` | 13/13 | Verificado en la app: Electron con backend real, ventana, navegación de 10 secciones, área central, panel contextual, notificaciones, configuración y gestión de errores; búsqueda global (Ctrl+K), Hoy y Ajustes contra el backend. Empaquetado configurado (AppImage generado; el `.deb`, ver CL17) |
| Backend FastAPI + SQLite (CL2) | `backend/app/` | 12/12 | Verificado, incluido el sistema de permisos: guardia de red y roles, y confirmaciones cableadas en el arranque con un único camino (`ActionService`, 300 s) |
| Hermes y chat (CL3) | `backend/app/integrations/`, `agent/` | 11/12 | GUI → backend → Hermes v0.22.7 → respuesta en el chat con Claude Haiku 5.5 real: sesiones, envío, recepción, eventos y recuperación tras caída del runner verificados. ⚠️ La primera Skill no la carga Hermes |
| Personalidad y contexto (CL4) | `agent/identity/`, `agent/context/`, `agent/knowledge/` | 17/17 | Verificado: 14 archivos compuestos en el `SOUL.md` de Hermes, con la seguridad primero, y consistencia de personalidad comprobada con Claude Haiku 5.5 real |
| Personaje (CL5) | `desktop/src/character/` | 16/19 | Verificado en el personaje provisional SVG: diseño, 9 estados, transiciones y eventos visuales. ⚠️ Faltan el `.riv`, el runtime de Rive y la sincronización labial con audio |
| Base de datos y migraciones (CL6) | `backend/migrations/` (0001–0013) | 18/18 | Verificado: 36 tablas, integridad referencial, copia y restauración |
| Tareas y proyectos (CL7) | `backend/app/services/tasks*.py`, `desktop/src/modules/tasks/`, `projects/` | 23/23 | Verificado el backend y las 21 herramientas, desde la GUI y desde el chat con Haiku real, incluido el borrado pedido por el agente, que pide confirmación y se aprueba en la app |
| Hábitos (CL8) | `backend/app/services/habits*.py`, `desktop/src/modules/habits/` | 12/12 | Verificado: CRUD, frecuencia y días, recordatorios, registros, historial, estadísticas, objetivos y persistencia. ⚠️ Herramientas sin probar con modelo |
| Calendario y asignaturas (CL9) | `backend/app/services/calendar*.py`, `subjects.py`, `desktop/src/modules/calendar/`, `subjects/` | 18/18 | Verificado: vistas diaria, semanal y mensual, eventos, bloques, solapamientos, zonas horarias, asignaturas, horarios y sesiones, recursos y tareas asociadas, borrado con confirmación |
| Almacén (CL10) | `backend/app/services/storage*.py`, `desktop/src/modules/storage/` | 25/25 | Verificado: catálogo, carpetas, etiquetas, índice FTS5, lectura bajo demanda (texto, PDF, imágenes, enlaces), límites de comprimidos y rutas permitidas. ⚠️ Herramientas sin probar con modelo |
| Relaciones (CL11) | `backend/app/services/relations.py`, `desktop/src/modules/relationships/` | 13/14 | Verificado el servicio, los tipos, las validaciones, las consultas y la integridad; leer, buscar y crear desde el agente con Haiku real. ⚠️ Borrar desde el agente sin recomprobar con el modelo |
| Memoria (CL12) | `memory/`, `backend/app/integrations/memory/` | 20/22 | Verificado el adaptador SQLite + FTS5 y su ciclo (extraer, clasificar, deduplicar, contradicciones, caducidad); olvidar o aprobar recuerdos pasa por confirmación. ⚠️ OpenViking desactivado |
| Skills y herramientas (CL13) | `agent/skills/`, `backend/app/tools/` | 7/15 | 78 herramientas por MCP con parámetros, permisos y errores verificados. ⚠️ Las Skills están inertes en Hermes (`skill_manage` desactivado) |
| Voz (CL14) | `voice/` | 13/18 | Verificado como proceso aislado: VAD, Whisper small, Kokoro, Voice Manager, reproducción e interrupciones. ⚠️ Sin conectar a la app, sin wake word ni Piper |
| Automejora (CL15) | `improvement/`, `backend/app/services/improvement_*.py` | 11/11 | Verificado el ciclo (feedback, propuestas, evaluación aislada, rama Git, revertir) y que no puede cambiar nada sin aprobación. ⚠️ Sin pantalla de automejora |
| Seguridad (CL16) | `backend/app/permissions/`, `tests/security/` | 14/15 | Revisión adversarial hecha (banco final 169 BLOCKED / 12 BREACH / 0 ERROR). ⚠️ Brechas de diseño conocidas: ver [SECURITY.md](SECURITY.md) |
| Optimización y lanzamiento (CL17) | `desktop/electron-builder.*`, `docs/installation/` | 3/17 | Guías de instalación al día; AppImage generado con el backend congelado. ⚠️ `.deb` sin regenerar ni instalar, sin mediciones de rendimiento |

Detalle por casilla en [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) y estado operativo en [`docs/RUN_STATE.md`](docs/RUN_STATE.md).

</details>

## Requisitos

- **Linux** con sesión gráfica. La arquitectura está preparada para Windows, pero solo se ha probado en Linux.
- **Python 3.12** para el backend (`requires-python` admite solo 3.12; se usa el comando `python3.12`).
- **Python >= 3.14** para Hermes, en un venv propio separado del backend. Hermes se instala desde git con el tag v0.22.7 (`b200f5bc`), nunca desde PyPI (ver [`docs/installation/hermes-y-openviking.md`](docs/installation/hermes-y-openviking.md)).
- **[`uv`](https://docs.astral.sh/uv/)** para el venv del backend.
- **Node 24 y npm.**
- **Hermes Agent** instalado en ese venv (`hermes-python` en el `PATH` o `DRAKTER_HERMES_PYTHON`). Sin Hermes la app abre, pero el chat y el agente no funcionan.
- Una **clave de API de Anthropic** para usar el modelo real. Sin ella, el agente puede usar el stub de desarrollo (`tools/dev-llm-stub`) en lugar del modelo; Hermes sigue siendo necesario.

Se ha desarrollado en un portátil con 14 GB de RAM y gráfica integrada; la voz local es la parte más exigente.

## Instalación

Detalle paso a paso en [`docs/installation/instalar.md`](docs/installation/instalar.md).

```sh
git clone https://github.com/Lordi898/Drakter.git
cd Drakter
(cd backend && uv sync --frozen)
(cd desktop && npm ci)
scripts/check-env.sh
```

Hermes va aparte, en su propio venv con Python >= 3.14: `scripts/install-hermes.sh` lo instala (v0.22.7, commit fijado, desde git) en `~/.local/share/drakter/venvs/hermes` y crea `hermes-python`. Detalle en [`docs/installation/hermes-y-openviking.md`](docs/installation/hermes-y-openviking.md). Los runtimes nunca van en `/tmp` ni `/var/tmp`.

- Electron 45 ya no trae `postinstall` y descarga su binario al primer arranque; por eso `desktop/package.json` tiene un `postinstall` propio (`desktop/scripts/ensure-electron.cjs`, idempotente) que lo baja durante `npm ci`. Si lo instalaste sin él: `node desktop/scripts/ensure-electron.cjs`.
- `scripts/check-env.sh` imprime líneas `OK`, `AVISO` o `FALTA` y sale con 1 si falta algo. Comprueba Python 3.12, que haya un Python >= 3.14 para Hermes (no comprueba que Hermes esté instalado), que `python3.12`, `python3.14`, `hermes-python`, `backend/.venv` y los venvs de `~/.local/share/drakter/venvs/` no resuelvan a `/tmp` o `/var/tmp` ni sean enlaces rotos (y da el comando para arreglarlo), Node, npm, `uv`, `~/.config/drakter/.env` (sin leerlo), el sandbox de Electron y la sesión gráfica.

## Configuración

La configuración va en `~/.config/drakter/.env` (respeta `XDG_CONFIG_HOME`). **No se lee ningún `.env` en la raíz del repositorio.** El backend lo lanza Electron con un entorno filtrado por lista blanca: de las variables exportadas en la shell solo le llegan `DRAKTER_DATA_DIR`, las `XDG_*` y, en desarrollo, `DRAKTER_MODEL_PROVIDER` y `DRAKTER_DEV_STUB_URL`. Todo lo demás (incluida `ANTHROPIC_API_KEY`) tiene que estar en ese `.env`. [`.env.example`](.env.example) es la plantilla completa, solo con nombres:

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
| `DRAKTER_AGENT_PROVIDER` | `hermes` | `hermes` o `fake` |
| `DRAKTER_MODEL_PROVIDER` | `anthropic` | `anthropic` o `dev_stub` |
| `DRAKTER_MODEL_NAME` | `claude-haiku-5-5` | Modelo del agente |
| `DRAKTER_HERMES_PYTHON` | `hermes-python` (en el `PATH`) | Python del venv de Hermes |
| `DRAKTER_DEV_STUB_URL` | `http://127.0.0.1:28517` | Stub de desarrollo; solo `http` en loopback |
| `DRAKTER_VOICE_*`, `DRAKTER_STT_*`, `DRAKTER_TTS_*`, `DRAKTER_VAD_*`, `DRAKTER_WAKEWORD_*`, `DRAKTER_AUDIO_*`, `DRAKTER_PIPER_*` | voz desactivada | Proceso de voz (ver [`docs/installation/voz.md`](docs/installation/voz.md)) |
| `DRAKTER_IMPROVEMENT_REPO` | — | Repositorio de pruebas de la automejora; sin él, evaluar queda bloqueado |

`OPENVIKING_ENDPOINT`, `OPENVIKING_API_KEY` y `FISH_API_KEY` están reservadas: nada las lee todavía. Más: [clave de API](docs/installation/clave-api.md).

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
- **Herramientas, no acceso directo:** las 78 herramientas del agente tienen esquema, permisos, validación, resultado estructurado y errores; las destructivas pasan por confirmación (`ActionService`).
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
├── scripts/        arranque, comprobación del entorno, pasada integrada e instalación de skills
├── tests/          pasada e2e y banco de seguridad
├── tools/          dev-llm-stub
└── voice/          servicio de voz
```

## Documentación

- [Instalación](docs/installation/README.md) · [Uso por módulo](docs/usage/README.md)
- [Arquitectura](docs/ARCHITECTURE.md) · [Convenciones](docs/CONVENTIONS.md)
- [Estado de implementación](docs/IMPLEMENTATION_STATUS.md) · [Decisiones](docs/DECISIONS.md) · [Plan maestro](docs/MASTER_PLAN.md)
- [Registro de cambios](CHANGELOG.md)

## Contribuir y seguridad

- Cómo contribuir: [CONTRIBUTING.md](CONTRIBUTING.md). Normas de convivencia: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Vulnerabilidades: **no abras un issue público**; sigue [SECURITY.md](SECURITY.md).
- Contenido y dependencias de terceros: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Licencia

Drakter se distribuye bajo la [Licencia Apache 2.0](LICENSE) (SPDX: `Apache-2.0`). Ver también [NOTICE](NOTICE).

La licencia no concede permiso para usar el nombre «Drakter», sus logotipos ni el personaje como marca (Apache-2.0, §6), salvo lo razonable para describir el origen del software. Si publicas una versión modificada, usa otro nombre.

El contenido de terceros conserva su propia licencia: ver [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
