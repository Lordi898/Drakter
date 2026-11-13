# Drakter

Agente personal de IA con aplicación de escritorio propia. Local-first, para un solo usuario, en Linux primero.

El diseño completo son tres sistemas conectados por APIs internas: Core (agente, personalidad, memoria, herramientas), Desktop (Electron + React) y Workspace (datos en SQLite), con un backend FastAPI en medio.

**Estado (2026-11-13): cierre en curso.** El código de todos los módulos está integrado en `drakter/integracion`; cada módulo se está verificando y en `docs/IMPLEMENTATION_STATUS.md` se marca solo lo comprobado. La app arranca (Electron + backend + Hermes) y el chat responde con el stub de desarrollo; la clave de Anthropic configurada da 401, así que nada se ha probado con el modelo real.

## Estado real

Foto del 2026-11-13. Cadena de ramas: `drakter/integracion` → `drakter/build` → `main` (local). Todas las ramas `drakter/*` están ya en `drakter/integracion`. El detalle operativo está en [`docs/RUN_STATE.md`](docs/RUN_STATE.md).

Arranque rápido: `scripts/drakter-local.sh start` (con el stub) o `start anthropic` (con clave válida); parar con `scripts/drakter-local.sh stop`.

| Bloque | Dónde | Estado verificado |
|---|---|---|
| Arquitectura y preparación (CL0) | raíz, `contracts/`, `docs/`, `scripts/` | Verificado |
| Backend FastAPI + SQLite (CL2) | `backend/app/` | Verificado, incluido el sistema de permisos: guardia de red y roles, y confirmaciones cableadas en el arranque con un único camino (`ActionService`, 300 s) |
| Base de datos y migraciones (CL6) | `backend/migrations/` (0001–0011) | Verificado: 36 tablas, integridad referencial, copia y restauración |
| Escritorio (CL1) | `desktop/` | Visto en la app: ventana, navegación, área central, panel contextual, configuración y gestión de errores; las 10 pantallas cargan contra el backend. ⚠️ Notificaciones y empaquetado en verificación; búsqueda global (Ctrl+K) sin montar |
| Hermes y chat (CL3) | `backend/app/integrations/`, `agent/` | GUI → backend → Hermes v0.22.7 → respuesta en el chat, **solo con el stub** `tools/dev-llm-stub/`; ⚠️ la clave configurada da 401. Verificados sesiones, envío, recepción, eventos y recuperación tras caída del runner. Las suites de evals (`agent/evals/`, 46 casos) están listas para correr con clave |
| Skills y herramientas (CL13) | `agent/skills/`, `backend/app/tools/` | 78 herramientas por MCP con parámetros, permisos y errores verificados. ⚠️ Las Skills están inertes en Hermes (se desactiva `skill_manage`); las confirmaciones del agente fallan cerradas sin crear la pendiente; selección sin probar con modelo |
| Personalidad y contexto (CL4) | `agent/identity/`, `agent/context/`, `agent/knowledge/` | Verificado: 14 archivos compuestos en el `SOUL.md` de Hermes, con la seguridad primero. ⚠️ La consistencia de personalidad está sin probar con modelo (sin clave) |
| Personaje (CL5) | `desktop/src/character/` | Verificado en el personaje provisional SVG: diseño, 9 estados, transiciones y eventos visuales. ⚠️ Faltan el `.riv`, el runtime de Rive y la sincronización labial con audio |
| Hábitos (CL8) | `backend/app/services/habits*.py`, `desktop/src/modules/habits/` | Verificado: CRUD, frecuencia y días, recordatorios, registros, historial, estadísticas, objetivos y persistencia. ⚠️ Herramientas sin probar con modelo |
| Tareas y proyectos (CL7) | `backend/app/services/tasks*.py`, `desktop/src/modules/tasks/`, `projects/` | Verificado el backend y las 21 herramientas: CRUD con borrado confirmado, subtareas, estados, prioridades, etiquetas, dependencias, archivo, progreso e historial. Pantallas vistas en la app. Borrar pide confirmación y se aprueba desde la app |
| Almacén (CL10) | `backend/app/services/storage*.py`, `desktop/src/modules/storage/` | Verificado: catálogo, carpetas, etiquetas, índice FTS5, lectura bajo demanda (texto, PDF, imágenes, enlaces), límites de comprimidos y rutas permitidas. ⚠️ Herramientas sin probar con modelo |
| Calendario y asignaturas | `backend/app/`, `desktop/src/modules/` | En verificación |
| Relaciones (CL11) | `backend/app/services/relations.py`, `desktop/src/modules/relationships/` | Verificado el servicio, los tipos, las validaciones, las consultas y la integridad. ⚠️ La pantalla falta verla en Electron; herramientas sin probar con modelo |
| Memoria (CL12) | `memory/`, `backend/app/integrations/memory/` | Verificado el adaptador SQLite + FTS5 y su ciclo (extraer, clasificar, deduplicar, contradicciones, caducidad). ⚠️ No se recupera al turno ni se puede olvidar aún; OpenViking desactivado (U-1, sin confirmar) |
| Voz (CL14) | `voice/` | ⚠️ En v1 solo se estabiliza; rediseño previsto sobre Pipecat |
| Automejora (CL15) | `improvement/`, `backend/app/services/improvement_*.py` | Verificado el ciclo (feedback, propuestas, evaluación aislada, rama Git, revertir) y que no puede cambiar nada sin aprobación. ⚠️ Sin flujo de aprobación en la app ni pantalla |

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
- **Python >=3.14 para Hermes**, en un venv propio, separado del backend. Hermes se instalará desde git con el tag v0.22.7 (`b200f5bc`), nunca desde PyPI. Aún no está integrado.
- **`uv`**, que crea el venv del backend. Todavía no está en el `PATH` de la máquina de desarrollo.
- **Node 24 y npm**, que son las versiones usadas aquí.
- Sesión gráfica para abrir el escritorio.

Máquina de desarrollo: i7-8665U, Intel UHD 620 sin VRAM dedicada y 14 GB de RAM. El plan maestro habla de 32 GB y 4 GB de VRAM, que no se corresponden con ella.

La instalación la ejecutas tú, y solo es posible con `backend/` y `desktop/` presentes:

```sh
(cd backend && uv sync --frozen)
(cd desktop && npm ci)
```

## Comprobar el entorno

```sh
scripts/check-env.sh
```

No admite argumentos. Imprime líneas `OK`, `AVISO` o `FALTA` y sale con 1 si hay algún `FALTA`, con 0 si no. Comprueba `python3.12`, un Python >=3.14 para el venv de Hermes (solo `AVISO` si no hay), Node, npm, `uv`, la existencia y los permisos de `~/.config/drakter/.env` (sin leerlo), el venv de `backend/`, `node_modules` de `desktop/`, el sandbox de Electron y la sesión gráfica.

## Arrancar en desarrollo

```sh
scripts/dev.sh [all|backend|desktop]
```

- `all`, el modo por defecto, arranca el backend, espera a `/health`, arranca el escritorio y para el backend al salir.
- `backend` y `desktop` arrancan solo esa parte en primer plano.

El script no instala nada. Si falta `backend/` o `desktop/` en tu checkout, sale con error y dice qué lo resuelve: hoy `drakter/build` no tiene `backend/`, así que `all` y `backend` fallan allí hasta fusionar `drakter/backend-base`. Aun con ambos, el escritorio seguirá mostrando `offline`, porque no está conectado al backend.

### Sandbox de Electron

En la máquina de desarrollo AppArmor restringe los espacios de nombres sin privilegios (`kernel.apparmor_restrict_unprivileged_userns=1`), y sin más ajustes Electron aborta con un error de `chrome-sandbox`. `dev.sh` no desactiva el sandbox por su cuenta, y `check-env.sh` da un `AVISO`. Hay dos salidas:

- Desactivarlo solo en esa sesión de desarrollo, que es lo que se ha probado: `ELECTRON_DISABLE_SANDBOX=1 scripts/dev.sh`.
- Dar a `chrome-sandbox` su propietario y modo, sin probar todavía, con `sudo chown root:root` y `sudo chmod 4755` sobre `desktop/node_modules/electron/dist/chrome-sandbox`. Hay que repetirlo tras cada `npm ci`.

## Configuración y secretos

El backend lee las variables del entorno y de `~/.config/drakter/.env` (respeta `XDG_CONFIG_HOME`). **No lee ningún `.env` en la raíz del repositorio.**

`.env.example` es la plantilla. Se copia a esa ruta, nunca lleva valores reales y `.env` está en `.gitignore`. `cp -n` no sobrescribe un `.env` que ya exista.

```sh
mkdir -p ~/.config/drakter
cp -n .env.example ~/.config/drakter/.env
chmod 600 ~/.config/drakter/.env
```

**Después de copiar, borra toda línea que dejes sin valor.** Para el backend `NOMBRE=` es un valor vacío, no una variable ausente: con `DRAKTER_PORT`, `DRAKTER_DATA_DIR`, `DRAKTER_RUNTIME_DIR` o `DRAKTER_LOG_LEVEL` vacías no arranca, y con `DRAKTER_ALLOWED_ORIGINS` vacía no admite ningún origen.

| Variable | Por defecto | Formato |
|---|---|---|
| `DRAKTER_PORT` | `8765` | Entero entre 1024 y 65535 |
| `DRAKTER_DATA_DIR` | Directorio de datos del usuario | Ruta absoluta |
| `DRAKTER_RUNTIME_DIR` | Directorio de ejecución del usuario | Ruta absoluta |
| `DRAKTER_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` o `ERROR` |
| `DRAKTER_ALLOWED_ORIGINS` | `app://drakter` | `scheme://host[:port]` separados por comas |

La dirección de escucha es fija, `127.0.0.1`, y no se configura. El resto de variables de `.env.example` están reservadas: nada las lee aún de ese archivo.

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Convenciones](docs/CONVENTIONS.md)
- [Estado de implementación](docs/IMPLEMENTATION_STATUS.md)
- [Decisiones](docs/DECISIONS.md)
- [Plan maestro](docs/MASTER_PLAN.md)
