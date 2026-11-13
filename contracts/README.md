# Contratos de Drakter (v1)

Fuente común de `backend/`, `desktop/`, herramientas y agente. Si un plan contradice esto, manda esto; si esto contradice `docs/DECISIONS.md`, manda `DECISIONS`. Un cambio aquí lo hace solo el dueño de `contracts/`: pídelo en vez de divergir.

| Qué | Dónde |
|---|---|
| Esquema SQLite | `backend/migrations/NNNN_*.sql` |
| Formatos y enumerados | `contracts/python/drakter_contracts/common.py` |
| Errores | `.../errors.py` |
| Herramientas y resultado | `.../tools.py`, `contracts/tools/catalog.json` |
| Eventos WS | `.../events.py` |
| Modelos de dominio | `.../models/` |
| Rutas REST | `contracts/api/routes.md` |
| Tipos TS | `contracts/ts/` |

Backend: dependencia local `drakter-contracts = {path = "../contracts/python", editable = true}` en `[tool.uv.sources]`.

## 1. Quién puede qué

Backend (D-14): lo lanza Electron main, su único cliente, con `python -m app`. Lee por stdin una línea `{"v":1,"ui":"<token>","approver":"<token>"}`, enlaza `127.0.0.1:0` y responde por stdout `{"v":1,"port":N}`. Ni puerto fijo ni `session.json`: las credenciales nunca pasan por argv, entorno, disco ni logs. Detalle en `backend/CONTRACT.md`.

| Credencial | Alcance |
|---|---|
| `ui`, por stdin | `/health`, `/api/v1/**` y `WS /api/v1/events`, salvo lo de `approver` |
| `approver`, por stdin, solo en Electron main | `approve` y `reject`, y métodos de escritura en `/api/v1/storage-locations/**` y `/api/v1/permissions/**`. El renderer no lo conoce |
| `agent_tool_token`, aleatorio por arranque | Solo el servidor MCP, en un listener propio de loopback con **puerto efímero** (bind a `127.0.0.1:0`), ni fijo ni configurable. El backend lo pasa al runner de Hermes por entorno filtrado (`DRAKTER_MCP_TOKEN`, con la URL en `DRAKTER_MCP_URL`). No alcanza ninguna ruta de la GUI |
| Runner de Hermes, sin credencial | Sin gateway ni `API_SERVER_KEY`: el backend lanza `integrations/hermes/runner/drakter_runner.py` como subproceso y le habla por JSONL en stdin/stdout; sin puerto. El runner termina con EOF en stdin (`DECISIONS.md`, «Hermes sin gateway») |

Toda petición lleva `Authorization: Bearer <token>`, sin excepción: no hay ruta pública, y `/health` también exige token. Nada de token por consulta, cookie o subprotocolo. Cualquier cabecera `Origin` da 403 y no hay CORS. Token válido con rol equivocado: 403 `permission_denied`; desconocido, también el del agente en este puerto: 401.

Actores: `user`, `agent`, `automation`, `system`. Orígenes: `rest`, `mcp`, `scheduler`, `internal`. La identidad de sesión y turno nunca sale de argumentos del modelo. Hay un turno activo a la vez; una llamada MCP sin turno se rechaza con `no_active_turn`.

Hermes no toca la BD ni el sistema de archivos: solo `app/tools/`, que llama a los mismos servicios que REST. Skill = guía en Markdown, sin lógica.

## 2. Formatos

- **UUID:** TEXT(36), minúsculas con guiones, lo genera solo el backend (v4). Opaco para el cliente.
- **Instante:** `YYYY-MM-DDTHH:MM:SS.sssZ`, ancho fijo, en BD y JSON. Usa `format_instant`. Nunca `isoformat()`. Se rechaza lo que no tenga zona.
- **Fecha:** `YYYY-MM-DD`. **Hora local:** `HH:MM`. **Fecha-hora local:** `YYYY-MM-DDTHH:MM`, sin segundos (lo que usan calendario, herramientas y GUI). **Zona:** nombre IANA.
- **Enumerados:** inglés `snake_case`; el texto en español es cosa de la GUI.
- **Listados:** `{items, next_cursor, total?}` con `limit` y `cursor`. El cursor es opaco y se calcula sobre (campo de orden, id), nunca sobre la versión del UUID; `limit` lo acota el servidor; `total` es opcional. `sort=campo,-campo` con lista blanca por ruta.
- **Nombres de chat:** en la API, `session_id` y `text`; `conversations.id` y `messages.content` son solo nombres de la BD.
- **PATCH:** parcial; distingue ausente de `null`. `If-Match: <revision>` opcional → 412 `revision_mismatch`. Las entradas usan `extra="forbid"`.
- **Idempotencia:** `Idempotency-Key` en POST de REST, guardada en `idempotency_records`. En herramientas, solo las declaradas `idempotent`.

## 3. Errores

Todo error HTTP: `{"error":{"code","message","request_id","details":[{"field","code","message"}]}}` (`backend/CONTRACT.md`). `details` jamás lleva `input` ni `ctx`. La GUI decide por `code`, nunca por el texto. `http_404` es ruta inexistente; `not_found` es entidad inexistente. Catálogo y estados en `errors.py`. Traducción de la BD: `task_hierarchy_cycle`, `folder_hierarchy_cycle`, `relationship_cycle` → `hierarchy_cycle`; FK de regla en `relationships` → `relationship_not_allowed`; RESTRICT → `has_dependents` con recuento en `details`.

## 4. Datos

- **Supertipo:** toda entidad tiene fila en `entities` y en su tabla de dominio, creadas en una sola función de repositorio. Nadie escribe `entities` directamente. `DELETE` de la fila de dominio borra la de `entities` por trigger y falla si quedan relaciones vivas. `v_orphan_entities` debe salir vacía al arrancar.
- **`revision`** sube en cada cambio; `updated_at` lo pone el servicio.
- **1:N estructural = columna; N:M semántica = `relationships`.** `tasks.project_id`, `subject_id`, `parent_task_id` y `parent_folder_id` son columnas; una tarea pertenece a un solo proyecto. `related_items` las devuelve como aristas virtuales. Sobre `related_to`, simétrica: se guarda con `source_id < target_id`.
- **Borrado:** activo → archivado (`archived_at`, reversible, riesgo `write`; es el undo de v1) → borrado definitivo (riesgo `confirm`). Archivar no propaga a hijos. Los listados excluyen archivados salvo `include_archived=true`. Borrar un recurso nunca borra el archivo original.
- **Calendario:** verdad = hora de pared + zona; `*_utc` son derivados y se recalculan si cambia tzdata. Día completo: `start_date` + `end_date_exclusive`. Recurrencia: subconjunto RRULE (`FREQ` DAILY/WEEKLY/MONTHLY/YEARLY, `INTERVAL`, `COUNT`, `UNTIL`, `BYDAY`, `BYMONTHDAY`), expandido en lectura dentro de una ventana acotada, nunca materializado. Hora inexistente: en creación puntual, `nonexistent_local_time`; en series, se mueve con el desfase previo (02:30 → 03:30) conservando el `local_start` nominal en `occurrence_id = <source_id>:<local_start>`. Hora ambigua: primera ocurrencia.
- **Hábitos:** `habit_records.occurrence_date` es fecha, única por hábito. Cambiar frecuencia = nueva fila en `habit_schedule_versions`.
- **Almacén:** `location_id` + `relative_path`; nunca ruta absoluta desde API o agente. La validación vive en un único servicio: `realpath`, sin symlink fuera de raíz, comprobada al abrir. `storage_locations` solo se gestiona desde la GUI, sin herramienta para el agente. La búsqueda devuelve metadatos y `snippet`; el contenido, solo bajo demanda con `UntrustedEnvelope`.
- **Búsqueda:** los recursos los escribe el servicio de almacén en la misma transacción (`storage_index.sync_document`). Desviación aceptada en v1: para los tipos estructurados, `reconcile_structured` (`app/services/search_index.py`) es el único escritor de `search_documents`; compara y escribe la diferencia antes de cada consulta. Ningún otro módulo los escribe. Si la base está ocupada, se busca con el índice anterior, porque es un dato derivado. `time_block`, `class_session` y `folder` no se indexan en v1. La consulta escapa cada término como frase con `*` final; la API expone `q`, `types`, `limit`, `cursor`, sin sintaxis FTS. Une con `entities` para excluir archivados.
- **Auditoría:** mutación y auditoría en la misma transacción; denegados y fallidos, en la suya. Toda llamada del agente se audita, también lecturas, sin contenido de documentos. Parámetros por lista blanca (`ToolSpec.audit`). `INSERT OR REPLACE` queda prohibido en repositorios.
- **Secretos:** nunca en `settings` ni en ninguna tabla. `settings.value` es texto de hasta 64 caracteres y las claves válidas las limita el servicio. `value_json` es generada, de solo lectura: lectores antiguos, nunca escritura. Zona por defecto: clave `default_timezone`, `Europe/Madrid`, nunca implícita en datos.
- **Memoria:** `memory_records` guarda el texto y `memory_fts` su copia indexada; borrar un registro borra ambos, sin FK fuera de `memory_*`. Es dato no confiable y entra en copias.
- **Recordatorios:** `notifications.dedupe_key` obligatoria para el tick; `habits.reminder_enabled`, `calendar_events.reminder_minutes_before`.

## 5. Confirmaciones

Pipeline único en backend, para GUI y agente, independiente de Hermes:

1. Una operación con riesgo efectivo `confirm` crea fila en `pending_confirmations` con argumentos, `targets_json` (ids y `revision` resueltos), `summary` y `affected_count`, calculados por el backend. Emite `confirmation.requested` y devuelve `confirmation_required`.
2. Solo Electron main aprueba: `GET /api/v1/confirmations/{id}`, con token `ui`, da el detalle con `params_hash`; `approver` no lee (403). Con token `approver`, `POST /api/v1/confirmations/{id}/approve` recibe solo `{params_hash}`. Un `params_hash` distinto de `args_hash` se rechaza. `reject` va sin cuerpo. El agente no tiene herramienta de aprobar y su token no es válido en ese listener.
3. Al aprobar se ejecutan exactamente los argumentos guardados, una vez: `pending → approved → executing → executed|failed`. Decidir es `UPDATE ... WHERE status='pending'`; reclamar la ejecución es `UPDATE ... SET status='executing' WHERE status='approved'`, y solo quien afecta una fila ejecuta. Al arrancar, lo que siga en `executing` pasa a `failed` sin reejecutar. Si `targets_json` ya no coincide: `conflict`.
4. Expirar no ejecuta nunca. Voz en v1: confirmar solo en la GUI.

**Forma REST:** pedir confirmación es siempre HTTP 409, nunca 2xx, con el sobre común y `confirmation` a su lado:

```json
{"error":{"code":"confirmation_required","message":"Esta operación necesita tu confirmación.","request_id":"...","details":[]},
 "confirmation":{"id":"<uuid>","summary":"...","affected_count":1,"expires_at":"...","params_hash":"..."}}
```

`confirmation.id` es `pending_confirmations.id` (`action_id` en herramientas y eventos) y `params_hash` es su `args_hash`. Modelo: `ConfirmationRequiredEnvelope`.

**Plantilla de `summary`,** calculada por el backend: `Vas a eliminar {n} {tipo}: «{nombre}»[ y {m} dependientes]. Esta acción {no se puede deshacer|se puede deshacer}.` Verbo único para borrar: eliminar. `{nombre}` es dato del usuario: la GUI lo muestra como texto, nunca como marcado.

**Restauración:** restaurar devuelve `pending_confirmations` y `audit_events` al estado de la copia. Tras restaurar y antes de aceptar peticiones, toda fila `pending` pasa a `expired` y toda `approved` o `executing` a `failed`, sin ejecutar nada, y se audita la restauración. Una aprobación antigua nunca revive por una copia.

Exige confirmación: borrado definitivo, restaurar copias, consolidar recuerdos candidatos, operaciones por encima de `bulk_threshold` (ajuste), cambios de configuración sensible y escrituras de un turno contaminado por contenido no confiable. Prohibido siempre, sin herramienta: ampliar permisos, alterar auditoría, gestionar ubicaciones permitidas, comandos arbitrarios.

## 6. Herramientas

`ToolSpec`, `ToolRegistry`, orden de `dispatch` y puente MCP: `backend/app/integrations/hermes/CONTRACT.md` §1. Cada módulo aporta `app/tools/<dominio>.py` con `TOOLS`; nadie edita un archivo común. `permission` = `<dominio>.<accion>`; dominios en `TOOL_DOMAINS`, y la búsqueda transversal es dominio `search`, permiso `search.read`. `risk` = `read|write|confirm`. Lo visible para el agente es `ToolOutcome`: `ok`, `error` o `confirmation_required`, con `isError:false` en rechazos previsibles para no disparar el corte de circuito de Hermes. En auditoría y GUI se usa el nombre canónico (`create_task`), no `mcp__drakter__create_task`.

## 7. Eventos

`WS /api/v1/events?after_seq=N&boot_id=<id>`, subprotocolo `drakter.v1`, solo para versionar; el token va en `Authorization: Bearer`, como en REST. Solo servidor→cliente; los comandos van por REST. Sobre: `{event_id, seq, boot_id, timestamp, type, version, correlation_id, payload}`. `seq` es monótono por `boot_id`, asignado en un único punto. Sustituye a `/ws` y a `/api/v1/chat/events`.

Si el búfer no cubre `after_seq`, o cambia `boot_id`, llega `system.resync_required` (sustituye a `agent.replay_truncated`) y la GUI relee por REST. Un hueco en `seq` también obliga a releer. `agent.confirmation_required` pasa a ser `confirmation.requested`. `agent.status_changed` usa `state`, con los 9 estados del personaje. `offline` lo deriva la GUI si cae el socket, o llega por `system.health_changed`. Catálogo y payloads en `events.py`.

## 8. Migraciones

`NNNN_nombre.sql` de 1 en 1, solo en `backend/migrations/`. Quien necesite una tabla o columna la pide al dueño de `contracts/`; dos ramas no numeran por su cuenta. Una migración aplicada no se edita.

- Todo CHECK, FK y UNIQUE con nombre; FK a nivel de tabla; sin índices por expresión.
- Reconstruir una tabla (crear, copiar, borrar, renombrar) con `foreign_keys=ON` borra hijos en cascada, y el migrador no admite `PRAGMA`. Queda prohibido en v1: usar `ADD COLUMN` o tabla nueva. Única excepción: `settings` en `0011`, sin hijos, FK ni triggers.
- Toda migración recrea los triggers de lo que toque. Objetos obligatorios al arrancar: `trg_audit_no_update`, `trg_audit_no_delete`, `trg_audit_no_replace`, `trg_pc_transition`, `trg_pc_immutable`, `trg_pc_no_delete`, `trg_pc_no_replace`, `trg_*_delete_entity` (9), `trg_*_no_cycle` (3) `trg_search_*` (3) y `trg_memory_records_*` (3).
