# RUN_STATE — Estado de la ejecución de Drakter

Foto operativa del cierre. El detalle por casilla está en `IMPLEMENTATION_STATUS.md` y los motivos, en `DECISIONS.md`.

## Estado actual (2026-11-13, cierre en curso)

- **Fase:** cierre. Solo se termina, verifica y documenta lo que ya tiene código; no entran funcionalidades nuevas ni la Checklist 18. El tema, el personaje y la voz «Jarvis» se planifican aparte y no forman parte de este cierre.
- **Coordinación:** `drakter-33` coordina, `drakter-32` integra y es el único que commitea en `drakter/integracion`. Un finalizador por módulo verifica y deja su informe; el encargado de docs marca casillas a partir de esos informes y de la pasada integrada.
- **Criterio de casilla:** se marca `[x]` solo lo comprobado y funcionando (`CLAUDE.md` §4). Lo parcial o bloqueado queda `[ ]` con ⚠️ y el motivo.
- **La app arranca** en el escritorio (Electron + backend + Hermes). Las pantallas Hoy, Drakter (chat), Hábitos, Tareas, Proyectos, Almacén, Calendario, Asignaturas, Relaciones y Configuración cargan sin errores de consola.
- **Modelo:** hay clave de Anthropic válida (`claude-haiku-5-5`). La app del usuario se arranca con el modelo real: `scripts/drakter-local.sh start anthropic`. Los finalizadores están recomprobando con el modelo real las casillas que quedaron ⚠️ «sin clave»; solo se marcan las que confirmen. El stub (`tools/dev-llm-stub`) sigue disponible para pruebas sin coste.
- **Todo es local:** sin `git push`, sin PR y sin tocar `origin`.

## Ramas

Cadena de integración: **`drakter/integracion` → `drakter/build` → `main` (local)**.

| Rama | Estado |
|---|---|
| `drakter/integracion` | Creada desde `drakter/build` (`815976f`) con las 22 ramas `drakter/*` fusionadas; ninguna tiene commits fuera de ella. Es la única que avanza durante el cierre. |
| `drakter/build` | Ancestro de `drakter/integracion` (en `815976f`). Se adelantará al terminar el cierre. |
| `main` | Ancestro de `drakter/build`; solo el commit inicial (`098e2df`). Se adelantará en local al final. |

Las ramas `ao/<sesión>/root` de los finalizadores son de trabajo; sus commits entran en `drakter/integracion` cuando `drakter-32` los fusiona. Pendientes de fusión al escribir esto: `5dd55b1` (permisos de automejora para el agente), `b8086ce` (Skills), `f364b48` (memoria en cada turno de Hermes), `dda565b`, `b31d1e8` y `6ba869a` (contratos alineados con lo montado), `b531106` (prefijo `workspace_` en los ejecutores de tareas: sin él, un `delete_task` del agente aprobado no borra). Las casillas que dependen de ellos llevan ⚠️ «pendiente de fusión».

## Cómo arrancar y parar

```sh
scripts/drakter-local.sh start anthropic  # app con Claude Haiku 5.5 real (arranque normal)
scripts/drakter-local.sh start            # stub de LLM + app, para pruebas sin modelo
scripts/drakter-local.sh status
scripts/drakter-local.sh stop
```

- **Primer plano:** `scripts/dev.sh` (= `dev.sh all`) lanza el escritorio con `electron-vite dev`; `drakter-local.sh` le añade el stub y las variables de la máquina de desarrollo. El backend **no se arranca aparte**: lo lanza el proceso principal de Electron con las credenciales por stdin y un puerto efímero (D-14). `scripts/dev.sh backend` sale con error a propósito.
- **Parar:** `scripts/drakter-local.sh stop`, o cerrar la ventana o `Ctrl+C` en la terminal de `dev.sh` (TERM a todo el grupo de procesos, KILL a los 5 s; Electron para el backend al salir). Comprobar que no quedan huérfanos: `pgrep -af 'electron|uvicorn|python -m app'`.
- **Compilado:** `(cd desktop && npm run build)` y luego `scripts/drakter`, que arranca Electron sobre `desktop/out/`.
- **Logs:** `/tmp/drakter-dev.log` (Electron y backend, prefijo `[drakter:backend]`), `/tmp/drakter-stub.log`, `~/.local/share/drakter/logs/hermes.log`. Datos: `~/.local/share/drakter/`.
- **Pasada integrada:** `scripts/verify-all.sh` (backend + stub LLM + Electron por CDP, informe por casilla). Sale con 0 sin fallos, 1 con algún FALLA y 2 si no pudo ejecutarse.
- **Evals con modelo:** `python agent/evals/run.py --provider anthropic --suite <encadenadas|personalidad|seleccion> --repeat 3` (necesita clave válida).

### Requisitos de esta máquina

- `backend/.venv` (Python 3.12): `cd backend && uv sync --frozen`. `uv` está en `~/.local/bin`.
- `desktop/node_modules`: `cd desktop && npm ci && node node_modules/electron/install.js` (npm 12 no ejecuta el script que descarga Electron).
- Hermes v0.22.7 (`b200f5b`, Python 3.14) en `/var/tmp/drakter-agente-hermes/hv/venv`, expuesto como `~/.local/bin/hermes-python` (o `DRAKTER_HERMES_PYTHON`). `/var/tmp` sobrevive a reinicios, pero no es una ubicación definitiva.
- Sandbox de Electron desactivado solo en desarrollo (`DRAKTER_DEV_NO_SANDBOX=1`, `ELECTRON_DISABLE_SANDBOX=1`): AppArmor restringe userns y `chrome-sandbox` no es `root:4755` (requiere `sudo`, ver `docs/installation/sandbox-electron.md`).

## Bloqueos

### Siguen abiertos

- **Pruebas con el modelo real:** las casillas ⚠️ «sin clave» están en recomprobación con la clave válida; hasta que cada finalizador lo confirme siguen sin marcar.
- **OpenViking (U-1):** desactivado en v1 con memoria SQLite + FTS5. Es una desviación de una decisión del usuario y falta que la confirme.
- **Personaje Rive:** el `.riv` se diseña a mano y no se ha entregado; tampoco está el runtime de Rive en `package.json`. La Checklist 5 está cerrada sobre el personaje provisional SVG.
- **Voz:** en v1 solo se estabiliza y documenta; la capa de voz y conversación se rediseñará sobre Pipecat (STT Whisper, TTS Fish Audio). Ver `DECISIONS.md`, 2026-11-13.
- **Memoria al turno pendiente de fusión:** `f364b48` conecta `memories_for_context` → `build_context` al runner de Hermes (memoria cercada en la entrada del turno, niveles 1, 2 y 4 como instrucciones efímeras); comprobado con el stub. Tras un turno con memoria la sesión queda `tainted` y las escrituras del agente fallan cerradas hasta que el runtime use `BackendToolGate`. Olvidar un recuerdo sigue fallando cerrado: `POST /api/v1/memory/{id}/forget` da 409 y `forget_memory` se deniega.
- **Automejora sin aprobación en la app:** el ciclo funciona (feedback, propuestas, evaluación en `bwrap`, rama `improvement/<id>`, revertir), pero aprobar desde la GUI da 403 porque no hay adaptador `ConfirmationGate` ni principal de GUI, y no existe pantalla de automejora. `recover_interrupted` aún no se llama al arrancar. Falla cerrado.
- **Skills inertes:** `home.py` desactiva el toolset `skills` de Hermes (arrastra `skill_manage`); el agente se guía por las descripciones de las herramientas MCP. Además la Skill de configuración cita herramientas que no existen.
- **Confirmaciones del agente:** `AgentRuntime` (`runtime.py`) crea `ToolRegistry` sin la puerta real y usa `DefaultToolGate`: las herramientas `risk=confirm` (borrados, escrituras de automejora) fallan cerradas sin crear la confirmación pendiente. Lo cierra `drakter-34`.
- **Eventos de tareas y proyectos:** `services/tasks.py` y `services/projects.py` publican `workspace.entity_*` sin `actor_type`; `HubEventSink` falla la validación y registra `event_publish_failed` en cada mutación, así que la GUI no recibe esos eventos. No se emiten tampoco `agent.expression_changed`, `storage.index_progress` ni `workspace.relationship_*`.
- **Copias por API:** `app/services/backup_api.py` no está montado (`/api/v1/backups/**` da 404) y tiene puerta propia; la única superficie de copias es `/settings/backups`.
- **Herramientas de automejora fuera del catálogo:** las 4 de `app/tools/improvement.py` no están en `contracts/tools/catalog.json` ni en `TOOL_DOMAINS` (4 avisos `tool_catalog_drift`); falta decidir si se añaden al catálogo o se retiran.
- **Contrato frente a API:** paginación por `offset` en memoria, chat y automejora (el contrato pide `cursor`); `forget` de memoria con `confirmation_id` en el cuerpo y `POST /memory/{id}/approve` sin 409; los modelos de `contracts/python`/`contracts/ts` difieren de la API en hábitos, proyectos, carpetas, etiquetas y `metadata`. No rompe la GUI (solo usa el contrato TS en chat, confirmaciones y eventos), pero conviene alinear y regenerar.
- **Búsqueda global:** `SearchPalette` sigue sin montarse en `AppShell` (Ctrl+K no hace nada).
- **Calendario:** el selector de zona horaria arranca en el primer valor de la lista (`Africa/Abidjan`) mientras `default_timezone` no esté fijado en Configuración.
- **Deriva de catálogo:** el backend avisa (`tool_catalog_drift`) de herramientas que difieren de `contracts/tools/catalog.json` (p. ej. `get_related_items` debe pasar a `returns_untrusted: true`). No bloquea.
- **Sin comprobar en pantalla:** la visualización de relaciones no se ha abierto en Electron.
- **Pasada e2e:** el arnés no espera a `agent/status = idle` antes de conversar (Hermes tarda 3-6 s), así que `conversacion.*` da 503 `agent_unavailable`; los guiones `herramienta-permitida`, `accion-destructiva` e `inyeccion-documento` piden `read_file`/`terminal`, que Drakter nunca ofrece. `desktop.arranca` falla en todas las pasadas porque `tests/e2e/harness/stack.py` no pasa `DRAKTER_DEV_NO_SANDBOX=1` (con la variable arranca; cambio pedido a `drakter-32`). Además, el catálogo (`tests/e2e/catalog.toml`) usa `GET /api/v1/audit` y la ruta real es `/api/v1/activity`.

### Cerrados en el cierre

- **Clave de Anthropic:** sustituida por una válida (`claude-haiku-5-5`); la app arranca con el modelo real.
- **Almacén (CL10):** catálogo, índice FTS5, lectores (texto, PDF, imágenes, enlaces con bloqueo SSRF), límites de comprimidos y permisos de rutas comprobados (`check_storage_paths.py` 127/127, `check_storage_archives.py` 35/35).
- **Seguridad cableada en el arranque (`4d2bcd1`):** `main.py` llama a `wire_security`/`start_security`; `check_security.py` 145/145, `check_confirmations.py` 0 fallos y borrado de tareas y proyectos 409 → aprobar → 404. Un único camino de confirmación (`ActionService`, 300 s).
- **Hermes (CL3):** runner propio sobre Hermes v0.22.7 (`b200f5bc`), sin gateway, herramientas por MCP de loopback; sesiones, mensajes, eventos y recuperación tras SIGKILL del runner (vuelve a `ready` en unos 6 s) comprobados con el stub.
- **Ramas sin fusionar:** las 22 ramas `drakter/*` están en `drakter/integracion`, con los conflictos semánticos resueltos (ver `DECISIONS.md`, «Integración de las 22 ramas»).
- **La app no arrancaba junta:** arranca con Electron como dueño del backend, Hermes y el stub; 30 peticiones concurrentes a los módulos dan 200 (conexiones SQLite por petición sin `check_same_thread`).
- **Caducidad de confirmaciones 15 min frente a 300 s:** desde `a123a90` hábitos, calendario y asignaturas usan `run_confirmable` → `ActionService` (300 s); ya no queda ningún plazo de 15 min.
- **Identidad «22 archivos»:** quedan exactamente 14 (6 en `identity/`, 4 en `context/`, 4 en `knowledge/`), y con `edbcf5e` el `SOUL.md` de Hermes los compone todos (46.227 caracteres).
- **Backend base (CL0, CL2, CL6):** migraciones 0001–0011, copia y restauración comprobadas.
- **Hábitos (CL8):** las 12 casillas funcionan con el backend real y la pantalla pinta en Electron headless.
- **Relaciones (CL11):** servicio, tipos, validaciones, consultas e integridad comprobados.
- **Memoria SQLite + FTS5 (CL12):** adaptador, extracción, clasificación, deduplicación, contradicciones, registros y skill comprobados; la memoria recuperada no sobrescribe las reglas de seguridad (`check_memory_rules.py` 40/40).
- **Automejora (CL15):** el esquema del servicio pasa a migración (`0013_improvement_cycle.sql`) y las rutas REST se montan; la automejora no puede tocar producción, permisos, confirmaciones ni auditoría sin aprobación humana.

## Copias de seguridad

Historial Git de los repos que estaban anidados en el checkout del usuario:

- `~/.drakter-backup/build-orchestrator.git` (`7a81c78`)
- `~/.drakter-backup/astraeus.git` (`1ff17b0`)

## Configuración local

- **Identidad Git:** la máquina no tiene `user.name` ni `user.email`; los commits usan `git -c user.name=... -c user.email=...`.
- **Secretos:** `~/.config/drakter/.env` pertenece al usuario y queda fuera del repositorio.

## Siguiente paso

1. Terminar la recomprobación con Haiku real: conversación, personalidad, selección y encadenado de herramientas (evals) y memoria.
2. Montar `SearchPalette`.
3. Cablear `BackendToolGate` en el runtime del agente (`drakter-34`).
