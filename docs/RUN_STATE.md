# RUN_STATE — Estado de la ejecución de Drakter

Foto operativa al cierre de la v1. El detalle por casilla está en `IMPLEMENTATION_STATUS.md` y los motivos, en `DECISIONS.md`.

## Estado de cierre (2026-11-13)

- **Cierre terminado.** Solo se terminó, verificó y documentó lo que ya tenía código; no entraron funcionalidades nuevas ni la Checklist 18.
- **Casillas (Checklists 0–17):** 260 de 295 en `[x]` (29 de ellas con una reserva ⚠️), 25 sin marcar con ⚠️ y su motivo, y 10 sin código. Tabla por checklist al principio de `IMPLEMENTATION_STATUS.md`.
- **Cómo se marcó:** cada casilla, a partir del informe de su finalizador (`/var/tmp/drakter-cierre/informes/`) o de la pasada integrada final; con Claude Haiku 5.5 real donde dependía del modelo.
- **Pasada integrada final:** `scripts/verify-all.sh --headless` sobre `drakter/integracion@183cc25` sale con 0: 44/44 comprobaciones PASA (backend, módulos, confirmaciones, copia y restauración, conversación, escritorio con Electron real y parada limpia). La conversación de esa pasada usa el stub; el modelo real se probó aparte (Hermes, evals, tareas, relaciones, memoria).
- **La app arranca** con Electron, el backend y Hermes, con Claude Haiku 5.5 real. Las 10 pantallas (Hoy, Drakter, Hábitos, Tareas, Proyectos, Almacén, Calendario, Asignaturas, Relaciones y Configuración) cargan sin errores de consola.
- **Seguridad:** revisión adversarial hecha; banco red-team final 169 BLOCKED / 12 BREACH / 19 N/A / 0 ERROR, con las 12 BREACH clasificadas (ver «Siguen abiertos»).

## Ramas

Cadena de cierre: **`drakter/integracion` → `drakter/build` → `main` (local)**, por fast-forward y **sin push** (nada se publica en `origin`).

| Rama | Papel |
|---|---|
| `drakter/integracion` | Reúne `drakter/build` (`815976f`), las 22 ramas `drakter/*` y todos los arreglos del cierre, fusionados por `drakter-32`. Ninguna rama de finalizador tiene commits fuera de ella. |
| `drakter/build` | Avanza por fast-forward hasta `drakter/integracion`. |
| `main` | Avanza en local por fast-forward desde `drakter/build`. |
| `respaldo/main-local-2026-11-13` | Respaldo con los cambios locales del usuario que había en `main` antes del cierre. |

## Cómo arrancar y parar

Desde el checkout del repositorio:

```sh
scripts/drakter-local.sh start anthropic  # app con Claude Haiku 5.5 real (arranque normal)
scripts/drakter-local.sh status
scripts/drakter-local.sh stop
scripts/drakter-local.sh start            # app con el stub de desarrollo, sin modelo
```

- `drakter-local.sh` deja la app (y el stub, si se usa) desacoplada de la terminal. `stop` para todo (arreglado en `f0f084b`). Comprobar que no quedan procesos: `pgrep -af 'electron|python -m app'`.
- **Primer plano:** `scripts/dev.sh` lanza el escritorio con `electron-vite dev`. El backend **no se arranca aparte**: lo lanza Electron con las credenciales por stdin y un puerto efímero (D-14); `scripts/dev.sh backend` sale con error a propósito.
- **Compilado:** `(cd desktop && npm run build)` y luego `scripts/drakter`.
- **Empaquetado:** backend con PyInstaller y `npx --yes electron-builder@26.18.0 --linux deb AppImage -c.npmRebuild=false`; pasos en `docs/installation/paquete-deb.md`.
- **Logs:** `/tmp/drakter-dev.log` (Electron y backend, prefijo `[drakter:backend]`), `/tmp/drakter-stub.log`, `~/.local/share/drakter/logs/hermes.log`. Datos: `~/.local/share/drakter/`.
- **Comprobar:** `scripts/check-env.sh` (entorno), `scripts/verify-all.sh` (pasada integrada), `python agent/evals/run.py --provider anthropic --suite <encadenadas|personalidad|seleccion>` (evals con el modelo).
- **Instalación y uso:** guías de `docs/installation/` (`instalar.md`, `clave-api.md`, `hermes-y-openviking.md`, `sandbox-electron.md`, `voz.md`, `paquete-deb.md`) y `docs/usage/`.

### Requisitos de esta máquina

- `backend/.venv` (Python 3.12): `cd backend && uv sync --frozen`. `uv` está en `~/.local/bin`.
- `desktop/node_modules`: `cd desktop && npm ci && node node_modules/electron/install.js` (npm 12 no ejecuta el script que descarga Electron).
- Hermes v0.22.7 (`b200f5b`, Python 3.14) en `/var/tmp/drakter-agente-hermes/hv/venv`, expuesto como `~/.local/bin/hermes-python`, o con `DRAKTER_HERMES_PYTHON` en `~/.config/drakter/.env` (no en el entorno de `dev.sh`: Electron no la pasa al backend). `/var/tmp` sobrevive a reinicios, pero no es una ubicación definitiva.
- Clave: `ANTHROPIC_API_KEY` en `~/.config/drakter/.env` (las líneas vacías se ignoran).
- Sandbox de Electron desactivado solo en desarrollo (`DRAKTER_DEV_NO_SANDBOX=1`, `ELECTRON_DISABLE_SANDBOX=1`): AppArmor restringe userns y `chrome-sandbox` no es `root:4755` (requiere `sudo`, ver `docs/installation/sandbox-electron.md`).

## Bloqueos

### Siguen abiertos

- **OpenViking (U-1):** desactivado en v1 con memoria SQLite + FTS5. Es una desviación de una decisión del usuario y falta que la confirme.
- **Personaje Rive:** el `.riv` se diseña a mano y no se ha entregado; tampoco está el runtime de Rive en `package.json`. La Checklist 5 está cerrada sobre el personaje provisional SVG.
- **Voz:** el pipeline propio (`voice/`) está verificado como proceso aislado (VAD, Whisper small, Kokoro, Voice Manager, interrupciones), pero no está registrado en `main.py`, su router `/api/v1/voice/*` no se monta y el escritorio no tiene cliente de voz: no hay conversación por voz. Se congela así; la capa de voz y conversación se rediseñará sobre Pipecat (STT Whisper, TTS Fish Audio).
- **Skills inertes:** `home.py` desactiva el toolset `skills` de Hermes (arrastra `skill_manage`); el agente se guía por las descripciones de las herramientas MCP. La Skill de configuración cita herramientas que no existen.
- **Automejora sin pantalla:** aprobar y revertir pasan por `ActionService` (409 → `/confirmations/{id}/approve`), pero no hay pantalla de automejora en el escritorio. Falta registrar `invalidate_after_restore` como hook de restauración de copias.
- **Restaurar copias con la app en marcha:** `/api/v1/backups/**` está montado y borrar va por `ActionService`, pero restaurar no tiene ruta: `restore_backup` necesita el bloqueo de instancia que ya tiene el backend. Hoy se restaura con el backend parado (`python -m app.database.cli restore`). Necesita un diseño propio.
- **Seguridad, brechas de diseño del red-team:** CONF-46/INJ-26 (la contaminación de la sesión no persiste al reiniciar), INJ-11/25 (`TurnRequest` sin canal de datos aparte; mitigado porque tainted se propaga y fuerza confirmación, `df258b1`, `1588c04`), INJ-05 (título y URL de `read_resource` fuera del sobre) y FILE-DB-02 (TOCTOU en `connect`, riesgo bajo). No son brechas abiertas: DESK-04 y DESK-16 (falsos positivos), DESK-20 (resuelto en `89a87b5`), INJ-24 (contradicción del propio banco) e INJ-32 (arreglado en código; falta ajustar la sonda).
- **Instalador:** el AppImage se genera con el backend congelado corregido (`39503a7`), pero el `.deb` no se ha regenerado tras ese arreglo (`fpm` falló con `/tmp` lleno; regenerar con más de 3 GB libres, `flock` y `TMPDIR` en disco), no se ha instalado ni se ha abierto la ventana empaquetada sin `--no-sandbox`. Sin icono propio ni proceso de versión (0.1.0).
- **Sin medir ni optimizar:** RAM y CPU generales, latencia de Hermes, y STT/TTS en reposo (la única medición de voz se hizo con la máquina muy cargada). Sin pasada de optimización de SQLite, FTS5, memoria ni carga de interfaz (el renderer es un único JS de 1,63 MB).
- **Pendientes menores:**
  - La reconexión del WebSocket del escritorio no se ha observado aislada.
  - `delete_relationship` desde el agente no se ha recomprobado con el modelo tras `b722aca`.
  - Las herramientas de hábitos y almacén no se han probado en una conversación real.
  - El calendario arranca en `Africa/Abidjan` si `default_timezone` no está fijado.
  - El aviso de un evento da la hora en la zona del evento, y Hoy, en la del usuario.
  - Paginación por `offset` en memoria, chat y automejora (desviación aceptada en v1).
  - Eventos sin emisor: `agent.expression_changed`, `storage.index_progress` y `workspace.relationship_*`.
  - Con otra instancia abierta, Electron cierra la nueva sin ventana; las pruebas usan `--user-data-dir` propio.
- **Observación para el rediseño de personalidad y conversación:**
  - Con el modelo real, el agente llamó por su cuenta a herramientas de automejora (create/list/get_improvement_proposal, record_improvement_feedback). Es seguro: las escrituras exigen confirmación.
  - Matices de estilo: a veces supera `max_sentences` y usa una muletilla de apertura.

### Cerrados en el cierre

**Integración y arranque**
- Las 22 ramas `drakter/*` están en `drakter/integracion`, con los conflictos semánticos resueltos.
- La app arranca con Electron como dueño del backend, Hermes y el stub o el modelo real. 30 peticiones concurrentes a los módulos dan 200 (conexiones SQLite por petición sin `check_same_thread`).
- La clave de Anthropic se sustituyó por una válida (`claude-haiku-5-5`).
- `drakter-local.sh stop` vuelve a parar la app (`f0f084b`).
- Hoy se recarga cuando el servicio local conecta (`76270ca`).
- Recuperación del backend: con Electron, un SIGKILL al backend se relanza en unos 2 s; al arrancar se reconcilian las confirmaciones y se recuperan las evaluaciones de automejora cortadas (`a1f2b88`).
- La pasada integrada pasa de 23 PASA / 9 FALLA a 44/44.

**Confirmaciones y seguridad**
- Seguridad cableada en el arranque (`4d2bcd1`), con un único camino de confirmación: `ActionService`, 300 s. Desde `a123a90` ya no queda ningún plazo de 15 min.
- Por ese camino pasan:
  - el borrado de tareas, proyectos, eventos, bloques, sesiones, asignaturas, relaciones, copias y elementos del almacén;
  - la aprobación y reversión de automejora;
  - el olvido y la aprobación de recuerdos (`effda18`, `6270011`).
- Las acciones CONFIRM del agente crean la confirmación pendiente por `BackendToolGate` (`b722aca`, `42a0a17`). Comprobado con el modelo real en tareas: «Elimina la tarea» → confirmación → aprobar → borrada.
- Revisión adversarial hecha (drakter-34): el banco pasa de 125/27/47/1 a 169/12/19/0. Arreglados:
  - auditoría que registraba los rechazos como éxito;
  - fugas en logs;
  - caracteres invisibles;
  - restauración con un `-wal` huérfano;
  - endurecimiento de `pending_confirmations` (`0012`).
- La GUI no puede aplicar ni revertir mejoras (`89a87b5`).

**Agente y memoria**
- Hermes con runner propio sin gateway y herramientas por MCP de loopback. Con Claude Haiku 5.5 real:
  - la conversación completa recuerda el turno anterior;
  - elige y encadena herramientas;
  - recupera el recuerdo correcto e ignora uno envenenado, sin llamar a ninguna herramienta.
- `SOUL.md` compone los 14 archivos de identidad, contexto y conocimiento (`edbcf5e`). La consistencia de personalidad está comprobada con el modelo real.
- Memoria en cada turno por `build_context` (`df258b1`); un turno con memoria marca la sesión como contaminada y sus escrituras piden confirmación (`1588c04`).
- Catálogo de herramientas sin deriva: automejora dentro (`aff7605`) y `get_related_items` como no confiable.

**Módulos**
- Escritorio, backend, base de datos, tareas y proyectos, hábitos, calendario y asignaturas, almacén, relaciones, memoria y automejora verificados por sus finalizadores.
- Búsqueda global con una sola ruta, que indexa los cinco tipos (`7787e9b`).
- Eventos `workspace.entity_*` con `actor_type` (`88aa3c3`).
- Contrato alineado con la API.
- Automejora con esquema en migración (`0013`) y rutas montadas.

## Copias de seguridad

Historial Git de los repos que estaban anidados en el checkout del usuario:

- `~/.drakter-backup/build-orchestrator.git` (`7a81c78`)
- `~/.drakter-backup/astraeus.git` (`1ff17b0`)

Rama `respaldo/main-local-2026-11-13` con los cambios locales del usuario en `main` antes del cierre.

## Configuración local

- **Identidad Git:** la máquina no tiene `user.name` ni `user.email`; los commits usan `git -c user.name=... -c user.email=...`.
- **Secretos:** `~/.config/drakter/.env` pertenece al usuario y queda fuera del repositorio.

## Siguiente paso

1. Regenerar e instalar el `.deb` y abrir la ventana empaquetada sin `--no-sandbox`.
2. Que el usuario confirme o rechace U-1 (OpenViking).
3. Fuera de este cierre: rediseño de voz sobre Pipecat, rediseño de personalidad (estilo y cuándo proponer mejoras), `.riv` del personaje, pantalla de automejora y restauración de copias con la app en marcha.
