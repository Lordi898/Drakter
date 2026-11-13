# RUN_STATE — Estado de la ejecución de Drakter

Foto operativa del cierre. El detalle por casilla está en `IMPLEMENTATION_STATUS.md` y los motivos, en `DECISIONS.md`.

## Estado actual (2026-11-13, cierre en curso)

- **Fase:** cierre. Solo se termina, verifica y documenta lo que ya tiene código; no entran funcionalidades nuevas ni la Checklist 18. El tema, el personaje y la voz «Jarvis» se planifican aparte y no forman parte de este cierre.
- **Coordinación:** `drakter-33` coordina, `drakter-32` integra y es el único que commitea en `drakter/integracion`. Un finalizador por módulo verifica y deja su informe; el encargado de docs marca casillas a partir de esos informes y de la pasada integrada.
- **Criterio de casilla:** se marca `[x]` solo lo comprobado y funcionando (`CLAUDE.md` §4). Lo parcial o bloqueado queda `[ ]` con ⚠️ y el motivo.
- **La app arranca** en el escritorio (Electron + backend + Hermes). Las pantallas Hoy, Drakter (chat), Hábitos, Tareas, Proyectos, Almacén, Calendario, Asignaturas, Relaciones y Configuración cargan sin errores de consola.
- **Modelo:** el chat funciona de extremo a extremo con `tools/dev-llm-stub` (respuestas `[DEV-STUB]`, unos 2 s). La `ANTHROPIC_API_KEY` de `~/.config/drakter/.env` es rechazada por Anthropic (401 `invalid x-api-key`), así que **no hay prueba con Claude Haiku 5.5 real**.
- **Todo es local:** sin `git push`, sin PR y sin tocar `origin`.

## Ramas

Cadena de integración: **`drakter/integracion` → `drakter/build` → `main` (local)**.

| Rama | Estado |
|---|---|
| `drakter/integracion` | Creada desde `drakter/build` (`815976f`) con las 22 ramas `drakter/*` fusionadas; ninguna tiene commits fuera de ella. Es la única que avanza durante el cierre. |
| `drakter/build` | Ancestro de `drakter/integracion` (en `815976f`). Se adelantará al terminar el cierre. |
| `main` | Ancestro de `drakter/build`; solo el commit inicial (`098e2df`). Se adelantará en local al final. |

Las ramas `ao/<sesión>/root` de los finalizadores son de trabajo; sus commits entran en `drakter/integracion` cuando `drakter-32` los fusiona. Pendientes de fusión al escribir esto: `a27c22a` (memoria), `78acfca` y `997ce07` (relaciones), `edbcf5e` (identidad), `b5a0d25` y `9a9a34e` (automejora, migración 0012), `95f53e5` (evals), `db85f3e` (confirmaciones de tareas y proyectos). Las casillas que dependen de ellos llevan ⚠️ «pendiente de fusión».

## Cómo arrancar y parar

```sh
scripts/drakter-local.sh start            # stub de LLM + app, desacoplados de la terminal
scripts/drakter-local.sh start anthropic  # con Haiku real (necesita clave válida)
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

- **Clave de Anthropic inválida:** sustituirla en `~/.config/drakter/.env` y arrancar con `start anthropic`. Hasta entonces, todo lo que depende del modelo queda ⚠️ «sin clave».
- **OpenViking (U-1):** desactivado en v1 con memoria SQLite + FTS5. Es una desviación de una decisión del usuario y falta que la confirme.
- **Personaje Rive:** el `.riv` se diseña a mano y no se ha entregado; tampoco está el runtime de Rive en `package.json`. La Checklist 5 está cerrada sobre el personaje provisional SVG.
- **Voz:** en v1 solo se estabiliza y documenta; la capa de voz y conversación se rediseñará sobre Pipecat (STT Whisper, TTS Fish Audio). Ver `DECISIONS.md`, 2026-11-13.
- **Confirmaciones sin cablear:** `app/permissions/setup.py` no se invoca desde `app/main.py`. `/api/v1/confirmations/**`, los borrados de tareas y proyectos y los borrados confirmables de calendario y asignaturas dan 503 `confirmation_unavailable` (falla cerrado). Cablearlo tal cual rompe el arranque (`habits_calendar_support.CONFIRMED_ACTIONS` ya no existe). El arreglo está propuesto (quitar ese bucle de `setup.py`, registrar `calendar_actions.register_actions` y los ejecutores de `tasks_confirmations.py`, y llamar a `install_security`/`start_security` en `main.py`); lo cierra `drakter-34`. El plazo ya está decidido: un único camino, `ActionService` con 300 s.
- **Memoria sin conectar al turno:** la recuperación del backend (`memories_for_context` → `build_context`) no la llama el runner de Hermes; el agente solo accede a la memoria por herramientas. Olvidar un recuerdo falla cerrado: `POST /api/v1/memory/{id}/forget` da 409 y `forget_memory` se deniega.
- **Automejora sin aprobación en la app:** el ciclo funciona (feedback, propuestas, evaluación en `bwrap`, rama `improvement/<id>`, revertir), pero aprobar desde la GUI da 403 porque no hay adaptador `ConfirmationGate` ni principal de GUI, y no existe pantalla de automejora. `recover_interrupted` aún no se llama al arrancar. Falla cerrado.
- **Búsqueda global:** `SearchPalette` sigue sin montarse en `AppShell` (Ctrl+K no hace nada).
- **Calendario:** el selector de zona horaria arranca en el primer valor de la lista (`Africa/Abidjan`) mientras `default_timezone` no esté fijado en Configuración.
- **Deriva de catálogo:** el backend avisa (`tool_catalog_drift`) de herramientas que difieren de `contracts/tools/catalog.json` (p. ej. `get_related_items` debe pasar a `returns_untrusted: true`). No bloquea.
- **Sin comprobar en pantalla:** la visualización de relaciones no se ha abierto en Electron.
- **Pasada e2e:** `desktop.arranca` falla en todas las pasadas porque `tests/e2e/harness/stack.py` no pasa `DRAKTER_DEV_NO_SANDBOX=1` (con la variable arranca; cambio pedido a `drakter-32`). Además, `tests/e2e/coverage.toml` cita dos textos antiguos de casillas y `verify-all.sh` sale con 2; el catálogo usa `GET /api/v1/audit` (la ruta real es `/api/v1/activity`), y `POST /api/v1/calendar/events` da 422 con el payload del catálogo.

### Cerrados en el cierre

- **Ramas sin fusionar:** las 22 ramas `drakter/*` están en `drakter/integracion`, con los conflictos semánticos resueltos (ver `DECISIONS.md`, «Integración de las 22 ramas»).
- **La app no arrancaba junta:** arranca con Electron como dueño del backend, Hermes y el stub; 30 peticiones concurrentes a los módulos dan 200 (conexiones SQLite por petición sin `check_same_thread`).
- **Caducidad de confirmaciones 15 min frente a 300 s:** desde `a123a90` hábitos, calendario y asignaturas usan `run_confirmable` → `ActionService` (300 s); ya no queda ningún plazo de 15 min.
- **Identidad «22 archivos»:** quedan exactamente 14 (6 en `identity/`, 4 en `context/`, 4 en `knowledge/`), y con `edbcf5e` el `SOUL.md` de Hermes los compone todos (46.227 caracteres).
- **Backend base (CL0, CL2, CL6):** migraciones 0001–0011, copia y restauración comprobadas.
- **Hábitos (CL8):** las 12 casillas funcionan con el backend real y la pantalla pinta en Electron headless.
- **Relaciones (CL11):** servicio, tipos, validaciones, consultas e integridad comprobados.
- **Memoria SQLite + FTS5 (CL12):** adaptador, extracción, clasificación, deduplicación, contradicciones, registros y skill comprobados; la memoria recuperada no sobrescribe las reglas de seguridad (`check_memory_rules.py` 40/40).
- **Automejora (CL15):** el esquema del servicio pasa a migración (`0012`) y las rutas REST se montan; la automejora no puede tocar producción, permisos, confirmaciones ni auditoría sin aprobación humana.

## Copias de seguridad

Historial Git de los repos que estaban anidados en el checkout del usuario:

- `~/.drakter-backup/build-orchestrator.git` (`7a81c78`)
- `~/.drakter-backup/astraeus.git` (`1ff17b0`)

## Configuración local

- **Identidad Git:** la máquina no tiene `user.name` ni `user.email`; los commits usan `git -c user.name=... -c user.email=...`.
- **Secretos:** `~/.config/drakter/.env` pertenece al usuario y queda fuera del repositorio.

## Siguiente paso

1. Clave de Anthropic válida y prueba de conversación, personalidad y herramientas con Haiku real (evals).
2. Cablear las confirmaciones en el arranque (`drakter-34`).
3. Montar `SearchPalette`.
