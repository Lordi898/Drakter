# Drakter

Agente personal de IA con aplicación de escritorio propia. Local-first, para un solo usuario, en Linux primero.

El diseño completo son tres sistemas conectados por APIs internas: Core (agente, personalidad, memoria, herramientas), Desktop (Electron + React) y Workspace (datos en SQLite), con un backend FastAPI en medio.

**Estado (2026-11-13): cierre de la v1 terminado.** Todo el código está integrado y verificado módulo a módulo; la app arranca (Electron + backend + Hermes) con Claude Haiku 5.5 real. En las Checklists 0–17 hay 260 de 295 casillas en `[x]` (29 con una reserva ⚠️), 25 sin marcar con ⚠️ y 10 sin código. Pendiente sobre todo: voz conectada (se rediseña sobre Pipecat), personaje Rive, OpenViking (U-1), pantalla de automejora, `.deb` instalado y mediciones de rendimiento.

## Estado real

Foto del cierre, 2026-11-13. Cadena de ramas: `drakter/integracion` → `drakter/build` → `main` (local, por fast-forward, sin push). Pasada integrada final: `scripts/verify-all.sh` 44/44. Detalle operativo en [`docs/RUN_STATE.md`](docs/RUN_STATE.md) y por casilla en [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md).

Arranque desde el checkout: `scripts/drakter-local.sh start anthropic` (con el modelo real) o `start` (con el stub); `status` y `stop` para consultarla y pararla.

| Bloque | Dónde | `[x]` | Estado verificado |
|---|---|---|---|
| Arquitectura y preparación (CL0) | raíz, `contracts/`, `docs/`, `scripts/` | 14/14 | Verificado |
| Escritorio (CL1) | `desktop/` | 13/13 | Verificado en la app: Electron con backend real, ventana, navegación de 10 secciones, área central, panel contextual, notificaciones, configuración y gestión de errores; búsqueda global (Ctrl+K), Hoy y Ajustes contra el backend. Empaquetado configurado (AppImage generado; el `.deb`, ver CL17) |
| Backend FastAPI + SQLite (CL2) | `backend/app/` | 12/12 | Verificado, incluido el sistema de permisos: guardia de red y roles, y confirmaciones cableadas en el arranque con un único camino (`ActionService`, 300 s) |
| Hermes y chat (CL3) | `backend/app/integrations/`, `agent/` | 11/12 | GUI → backend → Hermes v0.22.7 → respuesta en el chat con Claude Haiku 5.5 real: sesiones, envío, recepción, eventos y recuperación tras caída del runner verificados. ⚠️ La primera Skill no la carga Hermes |
| Personalidad y contexto (CL4) | `agent/identity/`, `agent/context/`, `agent/knowledge/` | 17/17 | Verificado: 14 archivos compuestos en el `SOUL.md` de Hermes, con la seguridad primero, y consistencia de personalidad comprobada con Claude Haiku 5.5 real. Los matices de estilo pasan al rediseño de personalidad |
| Personaje (CL5) | `desktop/src/character/` | 16/19 | Verificado en el personaje provisional SVG: diseño, 9 estados, transiciones y eventos visuales. ⚠️ Faltan el `.riv`, el runtime de Rive y la sincronización labial con audio |
| Base de datos y migraciones (CL6) | `backend/migrations/` (0001–0013) | 18/18 | Verificado: 36 tablas, integridad referencial, copia y restauración |
| Tareas y proyectos (CL7) | `backend/app/services/tasks*.py`, `desktop/src/modules/tasks/`, `projects/` | 23/23 | Verificado el backend y las 21 herramientas: CRUD con borrado confirmado, subtareas, estados, prioridades, etiquetas, dependencias, archivo, progreso e historial. Operaciones probadas desde la GUI en Electron y desde el chat con Haiku real, incluido el borrado pedido por el agente, que pide confirmación y se aprueba en la app |
| Hábitos (CL8) | `backend/app/services/habits*.py`, `desktop/src/modules/habits/` | 12/12 | Verificado: CRUD, frecuencia y días, recordatorios, registros, historial, estadísticas, objetivos y persistencia. ⚠️ Herramientas sin probar con modelo |
| Calendario y asignaturas (CL9) | `backend/app/services/calendar*.py`, `subjects.py`, `desktop/src/modules/calendar/`, `subjects/` | 18/18 | Verificado: vistas diaria, semanal y mensual, eventos, bloques, solapamientos, zonas horarias, asignaturas, horarios y sesiones, recursos y tareas asociadas, borrado con confirmación. Las 21 herramientas se registran |
| Almacén (CL10) | `backend/app/services/storage*.py`, `desktop/src/modules/storage/` | 25/25 | Verificado: catálogo, carpetas, etiquetas, índice FTS5, lectura bajo demanda (texto, PDF, imágenes, enlaces), límites de comprimidos y rutas permitidas. ⚠️ Herramientas sin probar con modelo |
| Relaciones (CL11) | `backend/app/services/relations.py`, `desktop/src/modules/relationships/` | 13/14 | Verificado el servicio, los tipos, las validaciones, las consultas y la integridad. Leer, buscar y crear relaciones funcionan desde el agente con Haiku real. Pantalla vista en Electron (lista, grafo, panel). ⚠️ Borrar desde el agente sin recomprobar con el modelo |
| Memoria (CL12) | `memory/`, `backend/app/integrations/memory/` | 20/22 | Verificado el adaptador SQLite + FTS5 y su ciclo (extraer, clasificar, deduplicar, contradicciones, caducidad). Recupera recuerdos en cada turno de Hermes (comprobado con Haiku real) y olvidar o aprobar recuerdos pasa por confirmación. ⚠️ OpenViking desactivado (U-1, sin confirmar) |
| Skills y herramientas (CL13) | `agent/skills/`, `backend/app/tools/` | 7/15 | 78 herramientas por MCP con parámetros, permisos y errores verificados. ⚠️ Las Skills están inertes en Hermes (se desactiva `skill_manage`); selección y encadenado comprobados con Haiku real por Hermes y evals; las acciones del agente que lo requieren piden confirmación (`BackendToolGate`) |
| Voz (CL14) | `voice/` | 13/18 | Verificado como proceso aislado: VAD, Whisper small, Kokoro, Voice Manager, reproducción e interrupciones. ⚠️ Sin conectar a la app (no hay conversación por voz), sin wake word ni Piper; rediseño previsto sobre Pipecat |
| Automejora (CL15) | `improvement/`, `backend/app/services/improvement_*.py` | 11/11 | Verificado el ciclo (feedback, propuestas, evaluación aislada, rama Git, revertir) y que no puede cambiar nada sin aprobación. Aprobación y reversión por `ActionService`. ⚠️ Sin pantalla de automejora |
| Seguridad (CL16) | `backend/app/permissions/`, `tests/security/` | 14/15 | Revisión adversarial hecha: permisos, confirmaciones por la GUI, rutas, comprimidos, auditoría, copias y restauración verificados (banco final 169 BLOCKED / 12 BREACH / 0 ERROR) y recuperación del backend tras caída. Las confirmaciones pedidas por el agente pasan por `BackendToolGate`. ⚠️ Brechas de diseño conocidas (contaminación no persistente, canal de datos de `TurnRequest`, INJ-05, TOCTOU de bajo riesgo); reconexión del WebSocket del escritorio sin observar |
| Optimización y lanzamiento (CL17) | `desktop/electron-builder.*`, `docs/installation/` | 3/17 | Guías de instalación al día; AppImage generado con el backend congelado. Pruebas de aceptación: `verify-all.sh` 44/44. ⚠️ `.deb` sin regenerar ni instalar, sin mediciones de rendimiento ni optimización, sin versión estable |

## Estructura de carpetas

```
.
├── .claude/        instrucciones, agentes, skills y comandos para Claude Code
├── agent/          identidad, contexto, conocimiento, skills y evaluaciones del agente
├── backend/        FastAPI + SQLite (API REST, WebSocket, migraciones)
├── contracts/      contratos de API, eventos y modelos compartidos
├── desktop/        Electron, React, TypeScript
├── docs/           plan, estado, decisiones, arquitectura, instalación y uso
├── improvement/    automejora y evaluaciones
├── memory/         memoria del agente
├── scripts/        check-env.sh, dev.sh, drakter, drakter-local.sh y verify-all.sh
├── tests/          pasada e2e
├── tools/          dev-llm-stub
├── voice/          servicio de voz
├── .env.example    plantilla de configuración (solo nombres)
├── CHANGELOG.md
└── README.md
```

## Requisitos

- **Python 3.12 para el backend**, por elección del proyecto: `requires-python` admite solo 3.12 y se usa el comando `python3.12`.
- **Python >=3.14 para Hermes**, en un venv propio, separado del backend. Hermes se instala desde git con el tag v0.22.7 (`b200f5bc`), nunca desde PyPI, y el backend lo encuentra como `hermes-python` en el `PATH` o con `DRAKTER_HERMES_PYTHON` (ver `docs/installation/hermes-y-openviking.md`).
- **`uv`**, que crea el venv del backend (en la máquina de desarrollo, en `~/.local/bin`).
- **Node 24 y npm**, que son las versiones usadas aquí.
- Sesión gráfica para abrir el escritorio.

Máquina de desarrollo: i7-8665U, Intel UHD 620 sin VRAM dedicada y 14 GB de RAM. El plan maestro habla de 32 GB y 4 GB de VRAM, que no se corresponden con ella.

La instalación la ejecutas tú (detalle en [`docs/installation/instalar.md`](docs/installation/instalar.md)):

```sh
(cd backend && uv sync --frozen)
(cd desktop && npm ci && node node_modules/electron/install.js)
```

`npm` 12 no ejecuta el script que descarga Electron; de ahí la última orden.

## Comprobar el entorno

```sh
scripts/check-env.sh
```

No admite argumentos. Imprime líneas `OK`, `AVISO` o `FALTA` y sale con 1 si hay algún `FALTA`, con 0 si no. Comprueba `python3.12`, un Python >=3.14 para el venv de Hermes (solo `AVISO` si no hay), Node, npm, `uv`, la existencia y los permisos de `~/.config/drakter/.env` (sin leerlo), el venv de `backend/`, `node_modules` de `desktop/`, el sandbox de Electron y la sesión gráfica.

## Arrancar en desarrollo

```sh
scripts/drakter-local.sh start anthropic  # app con Claude Haiku 5.5 real
scripts/drakter-local.sh start            # app con el stub de desarrollo
scripts/drakter-local.sh status
scripts/drakter-local.sh stop
scripts/dev.sh [all|desktop]              # escritorio en primer plano
```

- El backend no se arranca aparte: lo lanza el proceso principal de Electron con las credenciales por stdin y un puerto efímero (D-14). `scripts/dev.sh backend` sale con error a propósito.
- `drakter-local.sh` deja la app y el stub desacoplados de la terminal; `dev.sh` no instala nada y avisa si falta `hermes-python`.
- Logs y cómo parar sin dejar procesos: [`docs/RUN_STATE.md`](docs/RUN_STATE.md).

### Sandbox de Electron

En la máquina de desarrollo AppArmor restringe los espacios de nombres sin privilegios (`kernel.apparmor_restrict_unprivileged_userns=1`), y sin más ajustes Electron aborta con un error de `chrome-sandbox`. `dev.sh` no desactiva el sandbox por su cuenta, y `check-env.sh` da un `AVISO`. Hay dos salidas (detalle en [`docs/installation/sandbox-electron.md`](docs/installation/sandbox-electron.md)):

- Desactivarlo solo en esa sesión de desarrollo, que es lo que se ha probado: `ELECTRON_DISABLE_SANDBOX=1 DRAKTER_DEV_NO_SANDBOX=1 scripts/dev.sh`.
- Dar a `chrome-sandbox` su propietario y modo, sin probar todavía, con `sudo chown root:root` y `sudo chmod 4755` sobre `desktop/node_modules/electron/dist/chrome-sandbox`. Hay que repetirlo tras cada `npm ci`.

## Configuración y secretos

El backend lee las variables del entorno y de `~/.config/drakter/.env` (respeta `XDG_CONFIG_HOME`). **No lee ningún `.env` en la raíz del repositorio.**

`.env.example` es la plantilla. Se copia a esa ruta, nunca lleva valores reales y `.env` está en `.gitignore`. `cp -n` no sobrescribe un `.env` que ya exista.

```sh
mkdir -p ~/.config/drakter
cp -n .env.example ~/.config/drakter/.env
chmod 600 ~/.config/drakter/.env
```

Las líneas sin valor (`NOMBRE=`) se ignoran y se usa el valor por defecto, así que basta con rellenar las que necesites (al menos `ANTHROPIC_API_KEY`).

No hay puerto, dirección ni orígenes que configurar: Electron lanza el backend, que escucha en `127.0.0.1` con un puerto efímero (D-14).

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
| `DRAKTER_VOICE_ENABLED`, `DRAKTER_VOICE_PYTHON`, `DRAKTER_PIPER_PYTHON` | voz desactivada | Proceso de voz (ver `docs/installation/voz.md`) |
| `DRAKTER_IMPROVEMENT_REPO` | — | Repositorio de pruebas de la automejora; sin él, evaluar queda bloqueado |

`OPENVIKING_ENDPOINT` y `OPENVIKING_API_KEY` están reservadas: nada las lee todavía. Guías: [instalación](docs/installation/README.md), [clave de API](docs/installation/clave-api.md) y [uso por módulo](docs/usage/README.md).

## Documentación

- [Instalación](docs/installation/README.md)
- [Uso por módulo](docs/usage/README.md)
- [Arquitectura](docs/ARCHITECTURE.md)
- [Convenciones](docs/CONVENTIONS.md)
- [Estado de implementación](docs/IMPLEMENTATION_STATUS.md)
- [Decisiones](docs/DECISIONS.md)
- [Plan maestro](docs/MASTER_PLAN.md)
