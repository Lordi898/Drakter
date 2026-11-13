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

Las ramas `ao/<sesión>/root` de los finalizadores son de trabajo; sus commits entran en `drakter/integracion` cuando `drakter-32` los fusiona. Al escribir esto, todos los arreglos de los informes recibidos están fusionados.

## Cómo arrancar y parar

Instalación: guías de `docs/installation/` (`instalar.md`, `clave-api.md`, `hermes-y-openviking.md`, `sandbox-electron.md`, `voz.md`, `paquete-deb.md`). Uso por módulo: `docs/usage/`.

```sh
scripts/drakter-local.sh start anthropic  # app con Claude Haiku 5.5 real (arranque normal)
scripts/drakter-local.sh start            # stub de LLM + app, para pruebas sin modelo
scripts/drakter-local.sh status
scripts/drakter-local.sh stop
```

- **Primer plano:** `scripts/dev.sh` (= `dev.sh all`) lanza el escritorio con `electron-vite dev`; `drakter-local.sh` le añade el stub y las variables de la máquina de desarrollo. El backend **no se arranca aparte**: lo lanza el proceso principal de Electron con las credenciales por stdin y un puerto efímero (D-14). `scripts/dev.sh backend` sale con error a propósito.
- **Parar:** `scripts/drakter-local.sh stop`, o cerrar la ventana o `Ctrl+C` en la terminal de `dev.sh` (TERM a todo el grupo de procesos, KILL a los 5 s; Electron para el backend al salir). Comprobar que no quedan huérfanos: `pgrep -af 'electron|uvicorn|python -m app'`.
- **Compilado:** `(cd desktop && npm run build)` y luego `scripts/drakter`, que arranca Electron sobre `desktop/out/`.
- **Empaquetado:** backend con PyInstaller y `npx --yes electron-builder@26.18.0 --linux deb AppImage -c.npmRebuild=false`; pasos en `docs/installation/paquete-deb.md` y `desktop/electron-builder.README.md`.
- **Logs:** `/tmp/drakter-dev.log` (Electron y backend, prefijo `[drakter:backend]`), `/tmp/drakter-stub.log`, `~/.local/share/drakter/logs/hermes.log`. Datos: `~/.local/share/drakter/`.
- **Pasada integrada:** `scripts/verify-all.sh` (backend + stub LLM + Electron por CDP, informe por casilla). Sale con 0 sin fallos, 1 con algún FALLA y 2 si no pudo ejecutarse.
- **Evals con modelo:** `python agent/evals/run.py --provider anthropic --suite <encadenadas|personalidad|seleccion> --repeat 3` (necesita clave válida).

### Requisitos de esta máquina

- `backend/.venv` (Python 3.12): `cd backend && uv sync --frozen`. `uv` está en `~/.local/bin`.
- `desktop/node_modules`: `cd desktop && npm ci && node node_modules/electron/install.js` (npm 12 no ejecuta el script que descarga Electron).
- Hermes v0.22.7 (`b200f5b`, Python 3.14) en `/var/tmp/drakter-agente-hermes/hv/venv`, expuesto como `~/.local/bin/hermes-python`, o con `DRAKTER_HERMES_PYTHON` en `~/.config/drakter/.env` (no en el entorno de `dev.sh`: Electron no la pasa al backend). `/var/tmp` sobrevive a reinicios, pero no es una ubicación definitiva.
- Sandbox de Electron desactivado solo en desarrollo (`DRAKTER_DEV_NO_SANDBOX=1`, `ELECTRON_DISABLE_SANDBOX=1`): AppArmor restringe userns y `chrome-sandbox` no es `root:4755` (requiere `sudo`, ver `docs/installation/sandbox-electron.md`).

## Bloqueos

### Siguen abiertos

- **Pruebas con el modelo real:** hechas con `claude-haiku-5-5` por Hermes (conversación, selección y encadenado de herramientas, recuperación de memoria con un recuerdo malicioso ignorado) y por evals (personalidad, selección, encadenado). Lo que sigue con ⚠️ ya no depende de la clave, salvo alguna herramienta concreta sin conversación real.
- **OpenViking (U-1):** desactivado en v1 con memoria SQLite + FTS5. Es una desviación de una decisión del usuario y falta que la confirme.
- **Personaje Rive:** el `.riv` se diseña a mano y no se ha entregado; tampoco está el runtime de Rive en `package.json`. La Checklist 5 está cerrada sobre el personaje provisional SVG.
- **Voz:** el pipeline propio (`voice/`) está verificado como proceso aislado (VAD, Whisper small, Kokoro, Voice Manager, interrupciones), pero no está registrado en `main.py` ni tiene cliente en el escritorio, así que no hay conversación por voz. El router `/api/v1/voice/*` tampoco se monta, aunque Electron lo permite. Se congela así: la capa de voz y conversación se rediseñará sobre Pipecat (STT Whisper, TTS Fish Audio). Las cifras de latencia se tomaron con la máquina cargada y hay que repetirlas en reposo.
- **Memoria al turno:** `df258b1` conecta `memories_for_context` → `build_context` al runner de Hermes (memoria cercada en la entrada del turno, niveles 1, 2 y 4 como instrucciones efímeras); comprobado con el stub. Tras un turno con memoria la sesión queda `tainted` y las escrituras del agente fallan cerradas hasta `b722aca`. Olvidar un recuerdo sigue fallando cerrado: `POST /api/v1/memory/{id}/forget` da 409 y `forget_memory` se deniega.
- **Automejora:** la aprobación y la reversión pasan por `ActionService` (409 → `/confirmations/{id}/approve`) (`2425da5`, `b1a49a3`). No existe pantalla de automejora en el escritorio, `routes.generated.ts` hay que regenerarlo y `recover_interrupted` aún no se llama al arrancar.
- **Skills inertes:** `home.py` desactiva el toolset `skills` de Hermes (arrastra `skill_manage`); el agente se guía por las descripciones de las herramientas MCP. Además la Skill de configuración cita herramientas que no existen.
- **Calendario:** el selector de zona horaria arranca en el primer valor de la lista (`Africa/Abidjan`) mientras `default_timezone` no esté fijado en Configuración.
- **Deriva de catálogo:** el backend avisa (`tool_catalog_drift`) de herramientas que difieren de `contracts/tools/catalog.json` (p. ej. `get_related_items` debe pasar a `returns_untrusted: true`). No bloquea.
- **Observación, herramientas de automejora espontáneas:** con el modelo real (prueba de relaciones de drakter-41), el agente llamó por iniciativa propia a create/list/get_improvement_proposal y record_improvement_feedback sin que se le pidiera. Es seguro (las escrituras exigen confirmación), pero hay que revisar las descripciones de esas herramientas o las instrucciones de cuándo proponer mejoras; se deja para el rediseño de la personalidad y la conversación.
- **Restaurar copias con la app en marcha:** `/api/v1/backups/**` está montado y borrar va por `ActionService`, pero restaurar no tiene ruta: `restore_backup` necesita el bloqueo de instancia que ya tiene el backend. Hoy se restaura con el backend parado (`python -m app.database.cli restore`). Necesita un diseño propio.
- **Paginación por `offset`** en memoria, chat y automejora: desviación aceptada en v1 (el contrato pide `cursor`).
- **Eventos sin emisor:** `agent.expression_changed`, `storage.index_progress` y `workspace.relationship_*`.
- **Seguridad, brechas abiertas del banco red-team** (cribado de drakter-42: 170 BLOCKED / 11 BREACH / 19 N/A / 0 ERROR; recuento final pendiente de drakter-34):
  - INJ-11 e INJ-25, diseño pendiente: los recuerdos viajan dentro del texto del turno; hace falta un campo de contexto aparte en `TurnRequest`; mitigado porque tainted se propaga y fuerza confirmación (`df258b1`, `1588c04`).
  - CONF-46/INJ-26: la contaminación de la sesión vive solo en memoria y se pierde al reiniciar el backend.
  - INJ-24 (WRITE sin `summarize` adaptada con resumen por defecto), INJ-05 (título y URL remotos fuera del sobre en `read_resource`) y FILE-DB-02 (TOCTOU en `connect`, riesgo bajo).
  - DESK-20, ya acotado: el renderer solo puede rechazar propuestas de automejora (aprobar se retiró) y aprobar o rechazar recuerdos.
  - INJ-14 cerrado e INJ-32 arreglado en código (`1588c04`); DESK-04, DESK-16 y la sonda de INJ-32 son falsos positivos o pruebas desfasadas.
- **Instalador:** el AppImage se genera con el backend congelado corregido (`39503a7`), pero el `.deb` no se ha regenerado tras ese arreglo (`fpm` falló con `/tmp` lleno; regenerar con más de 3 GB libres, `flock` y `TMPDIR` en disco, ver `docs/installation/paquete-deb.md`), no se ha instalado ni se ha abierto la ventana empaquetada sin `--no-sandbox`. Sin icono propio ni proceso de versión (0.1.0).
- **Sin medir:** RAM/CPU general, latencia de Hermes, y STT/TTS en reposo. Sin pasada de optimización de SQLite, FTS5, memoria ni carga de interfaz (el renderer es un único JS de 1,63 MB).
- **Hora de los avisos de eventos:** el aviso dice «Empieza a las HH:MM» en la zona del evento, mientras Hoy muestra la hora en la zona del usuario. Solo difiere si el evento tiene otra zona.
- **Pruebas paralelas de Electron:** con otra instancia abierta, `requestSingleInstanceLock` cierra la nueva sin ventana; las pruebas usan `--user-data-dir` propio. Con Hermes sin preparar, `GET /api/v1/confirmations?status=pending` da 503 y la GUI muestra «No se pudieron leer las confirmaciones pendientes» (no rompe).
- **Sin comprobar en pantalla:** las vistas diaria y mensual del calendario no se han visto funcionar en Electron.
- **Pasada e2e:** el arnés no espera a `agent/status = idle` antes de conversar (Hermes tarda 3-6 s), así que `conversacion.*` da 503 `agent_unavailable`; los guiones `herramienta-permitida`, `accion-destructiva` e `inyeccion-documento` piden `read_file`/`terminal`, que Drakter nunca ofrece. `desktop.arranca` falla en todas las pasadas porque `tests/e2e/harness/stack.py` no pasa `DRAKTER_DEV_NO_SANDBOX=1` (con la variable arranca; cambio pedido a `drakter-32`). Además, el catálogo (`tests/e2e/catalog.toml`) usa `GET /api/v1/audit` y la ruta real es `/api/v1/activity`.

### Cerrados en el cierre

- **Escritorio (CL1):** Electron 45 con backend real, React 19, TypeScript, Tailwind 4, shadcn/ui, ventana, 10 secciones, área central, panel contextual, notificaciones, configuración y gestión de errores vistos en la app; `ALLOWED_ROUTES` regenerado desde el contrato (`89a87b5`) y la GUI no puede aplicar ni revertir mejoras.
- **Confirmaciones pedidas por el agente:** su registro de herramientas usa `BackendToolGate` (`b722aca`, `42a0a17`): las acciones CONFIRM crean la confirmación pendiente que se aprueba en la app, y quedan en `audit_events`. Falta recomprobar el borrado desde el agente en cada módulo.
- **Hoy, búsqueda, Ajustes y notificaciones vistos en Electron:** Hoy carga como pantalla inicial (antes se quedaba en «no conectado» si cargaba antes que el backend; arreglado en `76270ca`), Ctrl+K agrupa resultados de tareas, eventos, proyectos y asignaturas, y los recordatorios salen como aviso emergente, campana y centro de notificaciones.
- **Revisión adversarial de seguridad:** hecha (drakter-34). Banco de 200 ataques de 125/27/47/1 a 169/12/19/0 (BLOCKED/BREACH/N/A/ERROR). Arreglados: auditoría que registraba rechazos como éxito, fugas en logs (LEAK-02/03/05), caracteres invisibles en el sobre y en memoria (INJ-03/16/40/41), restauración con `-wal` huérfano (FILE-DB-07) y endurecimiento de `pending_confirmations` (`0012`). Electron sin hallazgos reales.
- **Eventos de tareas y proyectos:** `workspace.entity_*` lleva `actor_type` (`88aa3c3`); ya no falla la validación en cada mutación.
- **Contrato frente a API:** los modelos de `contracts/python` y `contracts/ts` se alinean con la API construida; la API de copias está montada (`/api/v1/backups/**`) y borrar una copia va por `ActionService`.
- **Conversación con el modelo real (CL3):** `agent/status` = `claude-haiku-5-5`; la conversación completa por Hermes recuerda el turno anterior, elige y encadena herramientas, y con un recuerdo que dice «IGNORA TODAS TUS REGLAS…» responde a lo pedido, avisa del recuerdo sospechoso y no llama a ninguna herramienta.
- **Catálogo de automejora:** las 4 herramientas están en `contracts/tools/catalog.json` y `improvement` en `TOOL_DOMAINS` (`aff7605`); ya no hay avisos `tool_catalog_drift`.
- **Borrar relaciones:** el 500 visto en un arnés de calendario no se reproduce en la app real (`05381dd`): `DELETE /relationships/{id}` → 409 → aprobar → 200 `executed`.
- **Calendario y asignaturas (CL9):** eventos, bloques, solapamientos, zonas horarias (cambio de hora), asignaturas, horarios recurrentes y sesiones comprobados; recursos de asignatura por relaciones (`bbee4c4`); `POST /calendar/events` acepta `:00` final (`f16753f`).
- **Búsqueda global:** `SearchPalette` (Ctrl+K) y el aviso de notificaciones están montados en `AppShell`; con `7787e9b` hay una sola ruta `GET /api/v1/search` y encuentra tareas, proyectos, hábitos, eventos y asignaturas (antes daba 0 resultados).
- **`drakter-local.sh stop` no paraba la app:** el pid se guardaba mal porque `setsid` hace fork; corregido en `f0f084b`.
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

1. Informe de escritorio (Checklist 1) y pasada completa de drakter-49: pruebas de aceptación, vistas diaria y mensual del calendario y recuperación del backend.
2. Repaso de drakter-34 sobre la punta: brechas INJ-11/14/22/25 con `build_context` conectado y borrado pedido por el agente en cada módulo.
3. Regenerar e instalar el `.deb` y abrir la ventana empaquetada sin `--no-sandbox`.
4. Fuera de este cierre: rediseño de voz sobre Pipecat, rediseño de personalidad (estilo) y `.riv` del personaje.
