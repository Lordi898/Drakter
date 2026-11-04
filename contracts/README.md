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

| Credencial | Alcance |
|---|---|
| Token de sesión (GUI), archivo de sesión | `/api/v1/*` y `WS /api/v1/events` en el puerto del backend (8765) |
| `agent_tool_token`, aleatorio por arranque | Solo el servidor MCP, en **otro** puerto de loopback (8766). No alcanza ninguna ruta de la GUI |
| `API_SERVER_KEY` de Hermes | Solo backend → Hermes (8767) |

Actores: `user`, `agent`, `automation`, `system`. Orígenes: `rest`, `mcp`, `scheduler`, `internal`. La identidad de sesión y turno nunca sale de argumentos del modelo. Hay un turno activo a la vez; una llamada MCP sin turno se rechaza con `no_active_turn`.

Hermes no toca la BD ni el sistema de archivos: solo `app/tools/`, que llama a los mismos servicios que REST. Skill = guía en Markdown, sin lógica.

## 2. Formatos

- **UUID:** TEXT(36), minúsculas con guiones, lo genera solo el backend (v4). Opaco para el cliente.
- **Instante:** `YYYY-MM-DDTHH:MM:SS.sssZ`, ancho fijo, en BD y JSON. Usa `format_instant`. Nunca `isoformat()`. Se rechaza lo que no tenga zona.
- **Fecha:** `YYYY-MM-DD`. **Hora local:** `HH:MM`. **Fecha-hora local:** `YYYY-MM-DDTHH:MM`. **Zona:** nombre IANA.
- **Enumerados:** inglés `snake_case`; el texto en español es cosa de la GUI.
- **Listados:** `{items, total}` con `limit` y `offset`, acotados por el servidor. `sort=campo,-campo` con lista blanca por ruta.
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
- **Búsqueda:** el servicio escribe `search_documents` en la misma transacción. Escapa cada término como frase con `*` final; la API expone `q`, `types`, `limit`, `offset`, sin sintaxis FTS. Une con `entities` para excluir archivados.
- **Auditoría:** mutación y auditoría en la misma transacción; denegados y fallidos, en la suya. Toda llamada del agente se audita, también lecturas, sin contenido de documentos. Parámetros por lista blanca (`ToolSpec.audit`). `INSERT OR REPLACE` queda prohibido en repositorios.
- **Secretos:** nunca en `settings` ni en ninguna tabla. Zona por defecto: ajuste `default_timezone`, `Europe/Madrid`, nunca implícita en datos.
- **Memoria:** `memory_items` guarda metadatos y procedencia, no el recuerdo. `review_text` solo vive mientras el candidato espera.

## 5. Confirmaciones

Pipeline único en backend, para GUI y agente, independiente de Hermes:

1. Una operación con riesgo efectivo `confirm` crea fila en `pending_confirmations` con argumentos, `targets_json` (ids y `revision` resueltos), `summary` y `affected_count`, calculados por el backend. Emite `confirmation.requested` y devuelve `confirmation_required`.
2. Solo la GUI aprueba: `POST /api/v1/confirmations/{id}/approve|reject`. El agente no tiene herramienta de aprobar y su token no llega a ese puerto.
3. Al aprobar se ejecutan exactamente los argumentos guardados, una vez (`pending → approved → executed|failed`, transición atómica con `WHERE status='pending'`). Si `targets_json` ya no coincide: `conflict`.
4. Expirar no ejecuta nunca. Voz en v1: confirmar solo en la GUI.

Exige confirmación: borrado definitivo, operaciones por encima de `bulk_threshold` (ajuste), cambios de configuración sensible y escrituras de un turno contaminado por contenido no confiable. Prohibido siempre, sin herramienta: ampliar permisos, alterar auditoría, gestionar ubicaciones permitidas, comandos arbitrarios.

## 6. Herramientas

`ToolSpec`, `ToolRegistry`, orden de `dispatch` y puente MCP: `backend/app/integrations/hermes/CONTRACT.md` §1 (rama `drakter/agente-hermes`). Cada módulo aporta `app/tools/<dominio>.py` con `TOOLS`; nadie edita un archivo común. `permission` = `<dominio>.<accion>`. `risk` = `read|write|confirm`. Lo visible para el agente es `ToolOutcome`: `ok`, `error` o `confirmation_required`, con `isError:false` en rechazos previsibles para no disparar el corte de circuito de Hermes. En auditoría y GUI se usa el nombre canónico (`create_task`), no `mcp__drakter__create_task`.

## 7. Eventos

`WS /api/v1/events?after_seq=N&boot_id=<id>`, subprotocolos `drakter.v1` y `drakter.auth.<token>`. Solo servidor→cliente; los comandos van por REST. Sobre: `{event_id, seq, boot_id, timestamp, type, version, correlation_id, payload}`. `seq` es monótono por `boot_id`, asignado en un único punto. Sustituye a `/ws` y a `/api/v1/chat/events`.

Si el búfer no cubre `after_seq`, o cambia `boot_id`, llega `system.resync_required` (sustituye a `agent.replay_truncated`) y la GUI relee por REST. Un hueco en `seq` también obliga a releer. `agent.confirmation_required` pasa a ser `confirmation.requested`. `agent.status_changed` usa `state`, con los 9 estados del personaje. `offline` lo deriva la GUI si cae el socket, o llega por `system.health_changed`. Catálogo y payloads en `events.py`.

## 8. Migraciones

`NNNN_nombre.sql` de 1 en 1, solo en `backend/migrations/`. Quien necesite una tabla o columna la pide al dueño de `contracts/`; dos ramas no numeran por su cuenta. Una migración aplicada no se edita.

- Todo CHECK, FK y UNIQUE con nombre; FK a nivel de tabla; sin índices por expresión.
- Reconstruir una tabla (crear, copiar, borrar, renombrar) con `foreign_keys=ON` borra hijos en cascada, y el migrador no admite `PRAGMA`. Queda prohibido en v1: usar `ADD COLUMN` o tabla nueva.
- Toda migración recrea los triggers de lo que toque. Objetos obligatorios al arrancar: `trg_audit_no_update`, `trg_audit_no_delete`, `trg_audit_no_replace`, `trg_pc_transition`, `trg_pc_immutable`, `trg_pc_no_delete`, `trg_*_delete_entity` (9), `trg_*_no_cycle` (3) y `trg_search_*` (3).
