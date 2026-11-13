# Rutas REST v1 de Drakter

Tabla única de rutas. Manda `contracts/README.md`; después, lo ya construido en los frentes. Prefijo `/api/v1` en todo salvo `GET /health`. Credencial: `Authorization: Bearer` en toda ruta, `ui` salvo lo marcado `approver` (README §1). El puerto es efímero. **Ninguna de estas rutas existe para el agente**: el agente solo entra por el listener MCP, con su propio puerto efímero y llama a los mismos servicios (`README` §1).

## Convenciones

- **Listados:** `GET` devuelve `{items, next_cursor, total?}` y acepta `limit`, `cursor`, `sort=campo,-campo` (lista blanca por ruta); `limit` por defecto 50, máximo 200 (100 en recursos y búsqueda). El cursor es opaco; `total` es opcional. Salvo marca expresa, los listados excluyen archivados y aceptan `include_archived=true`.
- **PATCH:** parcial, `extra="forbid"`; `If-Match: <revision>` opcional, 412 `revision_mismatch`. Las mutaciones sobre una entidad aceptan `If-Match`. `POST` acepta `Idempotency-Key`.
- **Errores:** `{"error":{"code","message","request_id","details":[{"field","code","message"}]}}`. Sin otra forma de error.
- **Confirmación:** una ruta con riesgo `confirm` responde **409** `confirmation_required` con el sobre más `confirmation:{id,summary,affected_count,expires_at,params_hash}`; nunca 2xx. El cliente no manda `confirmation_id` ni `pre_confirmed`: la GUI aprueba con `POST /confirmations/{id}/approve` y el backend ejecuta los argumentos guardados. Los `DELETE` definitivos tienen riesgo `confirm`; archivar es `write`.
- **Borrado definitivo:** el `DELETE` directo de la GUI siempre responde 409 y crea la confirmación; la ejecución real (que termina en 204 de la operación guardada) ocurre en `approve`. Borrar un recurso nunca borra el archivo original.
- **Tiempo real:** un único `WS /api/v1/events?after_seq=N&boot_id=<id>` (subprotocolo `drakter.v1`, token en `Authorization: Bearer`). Sustituye a `/ws` y a `/api/v1/chat/events`.
- **Estado:** `construida` = hay router escrito en el frente (no está montado en `main.py` de ninguna rama: todos montan solo `health`, `auth`, `ws`); `especificada` = documentada por el frente, sin código; `(sin construir)` = ruta inventada aquí para cubrir un hueco.
- **Riesgo:** `read`, `write`, `confirm` (efectivo; puede subir a `confirm` por `bulk_threshold` o turno contaminado).

## Sistema, auth y tiempo real

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/health` (sin prefijo, con token `ui`) | - | `{status:"ok"}` | construida | read | seguridad (12) |
| GET | `/api/v1/auth/check` | - | `{authenticated:true}` | construida | read | seguridad (12) |
| WS | `/api/v1/events` | `after_seq`, `boot_id` | eventos `{event_id,seq,boot_id,timestamp,type,version,correlation_id,payload}` | especificada (`events.py`); servidor sin construir | read | contratos / chat (17) |
| GET | `/api/v1/system/status` | - | versión, `boot_id`, BD y migración, salud de módulos, hora y zona | (sin construir) | read | seguridad (12) |
| GET | `/api/v1/backups` | - | `BundleInfo[]`, lista completa sin paginar | construida | read | automejora (20) |
| POST | `/api/v1/backups` | opciones de copia | `BundleInfo` | construida | write | automejora (20) |
| POST | `/api/v1/backups/export` | - | `ExportResponse` | construida | write | automejora (20) |
| POST | `/api/v1/backups/{name}/verify` | - | `VerifyResponse` | construida | read | automejora (20) |
| POST | `/api/v1/backups/{name}/restore` | sin cuerpo | 409 `confirmation_required`; se ejecuta en `/confirmations/{id}/approve` | construida, ver desviaciones | confirm | automejora (20) |
| DELETE | `/api/v1/backups/{name}` | sin cuerpo | 409 `confirmation_required`; se ejecuta en `/confirmations/{id}/approve` | construida, ver desviaciones | confirm | automejora (20) |
| GET | `/api/v1/today` | `timezone` (obligatoria, IANA) | `TodayResponse`; 422 `invalid_timezone` | construida | read | hoy-ajustes |
| GET | `/api/v1/settings` | - | `{persisted, items:[SettingOut]}` | construida | read | hoy-ajustes |
| GET | `/api/v1/settings/status` | - | estado de agente y clave, solo presencia | construida | read | hoy-ajustes |
| GET | `/api/v1/settings/backups` | - | copias | construida | read | hoy-ajustes |
| POST | `/api/v1/settings/backups` | - | 201 copia | construida | write | hoy-ajustes |
| POST | `/api/v1/settings/{key}` | `SettingUpdate` `{value}` | `SettingOut`; 404 `unknown_setting` si la clave no está permitida | construida | write | hoy-ajustes |
| GET | `/api/v1/activity` | `actor`, `entity_id`, `result`, `from`, `to`, `limit`, `cursor` | `{items,next_cursor}` de auditoría (sin contenido de documentos) | (sin construir) | read | seguridad (12) |

## Confirmaciones

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/confirmations` | `status`, `limit`, `cursor` | `{items,next_cursor}` | construida | read | seguridad (12) |
| GET | `/api/v1/confirmations/{id}` | - (`ui`; `approver` no lee: 403) | acción, `summary`, `affected_count`, `targets`, `status`, `expires_at`, `params_hash` | construida | read | seguridad (12) |
| POST | `/api/v1/confirmations/{id}/approve` | `ConfirmationApprove`: `{params_hash}` (`approver`) | resultado de la operación ejecutada; 409 `conflict` si `targets_json` cambió o `confirmation_already_resolved`; 410 `confirmation_expired`; 404; 422 | construida | write (ejecuta lo guardado) | seguridad (12) |
| POST | `/api/v1/confirmations/{id}/reject` | sin cuerpo (`approver`) | confirmación en `rejected` | construida | write | seguridad (12) |

## Agente y chat

Especificadas en `backend/app/integrations/hermes/CONTRACT.md` §4 (drakter-16, `api/chat.py`, aún sin código); el hilo de eventos pasa a `WS /api/v1/events`.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| POST | `/api/v1/chat/sessions` | - | 201 `ChatSession` | especificada | write | agente/chat (16) |
| GET | `/api/v1/chat/sessions` | `limit`, `cursor` | `{items,next_cursor}` | especificada | read | agente/chat (16) |
| POST | `/api/v1/chat/sessions/{id}/close` | - | `ChatSession` | especificada | write | agente/chat (16) |
| GET | `/api/v1/chat/sessions/{id}/messages` | `limit`, `cursor` | `{items,next_cursor}` `MessageOut` (`session_id`, `text`) | especificada | read | agente/chat (16) |
| POST | `/api/v1/chat/sessions/{id}/messages` | `MessageCreate`: `{text, client_message_id, input_source?}` | 202 `MessageAccepted` `{turn_id,message_id}`; 409 `agent_busy` | especificada | write | agente/chat (16) |
| POST | `/api/v1/chat/turns/{turn_id}/cancel` | - | 202 | especificada | write | agente/chat (16) |
| GET | `/api/v1/agent/status` | - | `AgentStatusOut` `{state,provider,model,detail}`; `state` entre los 9 del personaje | especificada | read | agente/chat (16) |

## Tareas

Especificadas en `drakter-13/backend/app/schemas/tasks_contract.md`; `api/tasks_http.py` solo tiene ayudantes, no rutas. La GUI (`desktop/src/modules/tasks/api.ts`) las consume.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/tasks` | `status`, `priority` (repetibles), `project_id`, `subject_id`, `parent_task_id`, `due_from`, `due_to`, `q`, `include_archived`, `sort`, `limit`, `cursor` | `{items,next_cursor}` `TaskOut` | especificada | read | tareas (13) |
| POST | `/api/v1/tasks` | `TaskCreate` | 201 `TaskOut` | especificada | write | tareas (13) |
| GET | `/api/v1/tasks/{id}` | - | `TaskDetail` | especificada | read | tareas (13) |
| PATCH | `/api/v1/tasks/{id}` | `TaskUpdate` | `TaskOut` | especificada | write | tareas (13) |
| DELETE | `/api/v1/tasks/{id}` | `If-Match` | 409 `confirmation_required` (204 al ejecutarse tras aprobar) | especificada | confirm | tareas (13) |
| POST | `/api/v1/tasks/{id}/complete` | `{complete_subtasks?}` | `TaskOut` | especificada | write; `confirm` si cierra por encima de `bulk_threshold` | tareas (13) |
| POST | `/api/v1/tasks/{id}/reopen` | - | `TaskOut` | especificada | write | tareas (13) |
| POST | `/api/v1/tasks/{id}/archive` | - | `TaskOut` | especificada | write | tareas (13) |
| POST | `/api/v1/tasks/{id}/unarchive` | - | `TaskOut` | especificada | write | tareas (13) |
| GET | `/api/v1/tasks/{id}/subtasks` | `limit`, `cursor` | `{items,next_cursor}` `TaskOut` | (sin construir) | read | tareas (13) |
| POST | `/api/v1/tasks/{id}/subtasks` | `SubtaskCreate` | 201 `TaskOut` | especificada | write | tareas (13) |
| POST | `/api/v1/tasks/{id}/dependencies` | `{depends_on_task_id}` | `TaskDetail` | especificada | write | tareas (13) |
| DELETE | `/api/v1/tasks/{id}/dependencies/{dep_id}` | - | `TaskDetail` | especificada | write | tareas (13) |
| GET | `/api/v1/tasks/{id}/history` | `limit`, `cursor` | `{items,next_cursor}` `HistoryEntry` | especificada | read | tareas (13) |

## Proyectos

Router escrito en `drakter-13/backend/app/api/projects.py`.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/projects` | `ProjectListQuery`, `limit`, `cursor` | `{items,next_cursor}` `ProjectOut` | construida | read | tareas (13) |
| POST | `/api/v1/projects` | `ProjectCreate` | 201 `ProjectOut` | construida | write | tareas (13) |
| GET | `/api/v1/projects/{id}` | - | `ProjectOut` | construida | read | tareas (13) |
| PATCH | `/api/v1/projects/{id}` | `ProjectUpdate` | `ProjectOut` | construida | write | tareas (13) |
| DELETE | `/api/v1/projects/{id}` | `If-Match` | 409 `confirmation_required`; 204 al ejecutarse | construida | confirm | tareas (13) |
| POST | `/api/v1/projects/{id}/archive` | - | `ProjectOut` | construida | write | tareas (13) |
| POST | `/api/v1/projects/{id}/unarchive` | - | `ProjectOut` | construida | write | tareas (13) |
| GET | `/api/v1/projects/{id}/progress` | - | `ProjectProgress` | construida | read | tareas (13) |
| GET | `/api/v1/projects/{id}/activity` | `limit`, `cursor` | `{items,next_cursor}` `HistoryEntry` | construida | read | tareas (13) |

## Hábitos

`drakter-14/backend/app/api/habits.py`. No hay `DELETE /habits/{id}`: un hábito se archiva.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/habits` | `status`, `include_archived`, `limit`, `cursor` | `{items,next_cursor}` `HabitOut` | construida | read | hábitos/calendario (14) |
| POST | `/api/v1/habits` | `HabitCreate` | 201 `HabitOut` | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/habits/{id}` | - | `HabitOut` | construida | read | hábitos/calendario (14) |
| PATCH | `/api/v1/habits/{id}` | `HabitUpdate` (frecuencia nueva = `habit_schedule_versions`) | `HabitOut` | construida | write | hábitos/calendario (14) |
| POST | `/api/v1/habits/{id}/archive` | - | `HabitOut` | construida | write | hábitos/calendario (14) |
| POST | `/api/v1/habits/{id}/unarchive` | - | `HabitOut` | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/habits/{id}/records` | `from`, `to`, `limit`, `cursor` | `{items,next_cursor}` `HabitRecordOut` | construida | read | hábitos/calendario (14) |
| PUT | `/api/v1/habits/{id}/records/{date}` | `HabitRecordWrite` (`date` = `occurrence_date`) | `HabitRecordOut` | construida | write | hábitos/calendario (14) |
| DELETE | `/api/v1/habits/{id}/records/{date}` | - | 204 | (sin construir) | write | hábitos/calendario (14) |
| GET | `/api/v1/habits/{id}/history` | - | `HabitHistory` (versiones de frecuencia) | construida | read | hábitos/calendario (14) |
| GET | `/api/v1/habits/{id}/statistics` | `from`, `to` | `HabitStatistics` | construida | read | hábitos/calendario (14) |

## Calendario

`drakter-14/backend/app/api/calendar.py`. `timezone` IANA obligatoria en consultas por ventana.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/calendar/agenda` | `from`, `to`, `timezone`, `types`, `status` | `AgendaResponse` (ocurrencias expandidas) | construida | read | hábitos/calendario (14) |
| GET | `/api/v1/calendar/availability` | `local_start`, `local_end`, `timezone` | `AvailabilityResponse` | construida | read | hábitos/calendario (14) |
| GET | `/api/v1/calendar/free-slots` | `from`, `to`, `timezone`, `min_minutes` | `FreeSlotsResponse` | construida | read | hábitos/calendario (14) |
| GET | `/api/v1/calendar/overlaps` | `from`, `to`, `timezone` | `OverlapsResponse` | construida | read | hábitos/calendario (14) |
| GET | `/api/v1/calendar/events` | `status`, `include_archived`, `limit`, `cursor` | `{items,next_cursor}` `EventOut` | construida | read | hábitos/calendario (14) |
| POST | `/api/v1/calendar/events` | `EventCreate` | 201 `EventWriteResult` | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/calendar/events/{id}` | - | `EventOut` | construida | read | hábitos/calendario (14) |
| PATCH | `/api/v1/calendar/events/{id}` | `EventUpdate` | `EventWriteResult` | construida | write | hábitos/calendario (14) |
| DELETE | `/api/v1/calendar/events/{id}` | - | 409 `confirmation_required` | construida | confirm | hábitos/calendario (14) |
| GET | `/api/v1/calendar/events/{id}/exceptions` | - | `{items,next_cursor}` `RecurrenceExceptionOut` | construida | read | hábitos/calendario (14) |
| POST | `/api/v1/calendar/events/{id}/exceptions` | `RecurrenceExceptionCreate` | 201 `RecurrenceExceptionOut` | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/calendar/time-blocks` | `include_archived`, `limit`, `cursor` | `{items,next_cursor}` `TimeBlockOut` | construida | read | hábitos/calendario (14) |
| POST | `/api/v1/calendar/time-blocks` | `TimeBlockCreate` | 201 `TimeBlockWriteResult` | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/calendar/time-blocks/{id}` | - | `TimeBlockOut` | construida | read | hábitos/calendario (14) |
| PATCH | `/api/v1/calendar/time-blocks/{id}` | `TimeBlockUpdate` | `TimeBlockWriteResult` | construida | write | hábitos/calendario (14) |
| DELETE | `/api/v1/calendar/time-blocks/{id}` | - | 409 `confirmation_required` | construida | confirm | hábitos/calendario (14) |

## Asignaturas y horario

`drakter-14/backend/app/api/subjects.py`.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/subjects` | `include_archived`, `limit`, `cursor` | `{items,next_cursor}` `SubjectOut` | construida | read | hábitos/calendario (14) |
| POST | `/api/v1/subjects` | `SubjectCreate` | 201 `SubjectOut` | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/subjects/{id}` | - | `SubjectOut` | construida | read | hábitos/calendario (14) |
| PATCH | `/api/v1/subjects/{id}` | `SubjectUpdate` | `SubjectOut` | construida | write | hábitos/calendario (14) |
| DELETE | `/api/v1/subjects/{id}` | - | 409 `confirmation_required` | construida | confirm | hábitos/calendario (14) |
| POST | `/api/v1/subjects/{id}/archive` | - | `SubjectOut` | construida | write | hábitos/calendario (14) |
| POST | `/api/v1/subjects/{id}/unarchive` | - | `SubjectOut` | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/subjects/{id}/sessions` | `include_archived` | `{items,next_cursor}` `ClassSessionOut` | construida | read | hábitos/calendario (14) |
| POST | `/api/v1/subjects/{id}/sessions` | `ClassSessionCreate` | 201 `ClassSessionWriteResult` | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/subjects/{id}/resources` | - | `SubjectResources` | construida | read | hábitos/calendario (14) |
| GET | `/api/v1/class-sessions/{id}` | - | `ClassSessionOut` | construida | read | hábitos/calendario (14) |
| PATCH | `/api/v1/class-sessions/{id}` | `ClassSessionUpdate` | `ClassSessionWriteResult` | construida | write | hábitos/calendario (14) |
| DELETE | `/api/v1/class-sessions/{id}` | - | 409 `confirmation_required` | construida | confirm | hábitos/calendario (14) |
| POST | `/api/v1/class-sessions/{id}/exceptions` | `ScheduleExceptionCreate` | 201 `RecurrenceExceptionOut` | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/timetable` | `on` (fecha) | `Timetable` | construida | read | hábitos/calendario (14) |

## Almacén (ubicaciones, carpetas, recursos)

`drakter-15/backend/app/api/storage.py`. Nunca ruta absoluta salvo al crear una ubicación; `storage-locations` solo desde la GUI, sin herramienta para el agente.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/storage-locations` | - | `{items,next_cursor}` `StorageLocationOut` | construida | read | almacén (15) |
| POST | `/api/v1/storage-locations` | `StorageLocationCreate` (`approver`) | 201 `StorageLocationOut` | construida | write | almacén (15) |
| PATCH | `/api/v1/storage-locations/{id}` | `StorageLocationUpdate` (`approver`) | `StorageLocationOut` | construida | write | almacén (15) |
| DELETE | `/api/v1/storage-locations/{id}` | - (`approver`) | 409 `confirmation_required` | construida | confirm | almacén (15) |
| GET | `/api/v1/folders` | `parent_id`, `include_archived` | `{items,next_cursor}` `FolderOut` | construida | read | almacén (15) |
| POST | `/api/v1/folders` | `FolderCreate` | 201 `FolderOut` | construida | write | almacén (15) |
| PATCH | `/api/v1/folders/{id}` | `FolderUpdate` | `FolderOut` | construida | write | almacén (15) |
| DELETE | `/api/v1/folders/{id}` | - | 409 `confirmation_required` | construida | confirm | almacén (15) |
| GET | `/api/v1/resources` | `folder_id`, `type`, `availability`, `tag`, `include_archived`, `limit`, `cursor` | `{items,next_cursor}` `ResourceSummary` | construida | read | almacén (15) |
| POST | `/api/v1/resources` | `ResourceCreate` (`location_id`+`relative_path`) | 201 `ResourceOut` | construida | write | almacén (15) |
| GET | `/api/v1/resources/search` | `q`, `type`, `limit`, `cursor` | `{items,next_cursor}` `SearchHit` (metadatos + `snippet`) | construida | read | almacén (15) |
| POST | `/api/v1/resources/refresh-index` | - | `RefreshResult` | construida | confirm (masiva) | almacén (15) |
| POST | `/api/v1/resources/scan` | `{location_id}` | resultado del escaneo | construida | confirm (masiva) | almacén (15) |
| GET | `/api/v1/resources/{id}` | - | `ResourceOut` | construida | read | almacén (15) |
| PATCH | `/api/v1/resources/{id}` | `ResourceUpdate` | `ResourceOut` | construida | write | almacén (15) |
| DELETE | `/api/v1/resources/{id}` | `detach?` | 409 `confirmation_required`; nunca borra el archivo original | construida | confirm | almacén (15) |
| POST | `/api/v1/resources/{id}/archive` | - | `ResourceOut` | construida | write | almacén (15) |
| POST | `/api/v1/resources/{id}/unarchive` | - | `ResourceOut` | construida | write | almacén (15) |
| POST | `/api/v1/resources/{id}/read` | `ReadRequest` (opcional) | contenido en `UntrustedEnvelope` | construida | read | almacén (15) |
| POST | `/api/v1/resources/{id}/index` | `include_content?` | `ResourceOut` | construida | write | almacén (15) |

## Etiquetas, relaciones y búsqueda

`relations.py` es de drakter-15. La búsqueda global es de drakter-27 (`backend/app/api/search.py`).

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/tasks/tags` | - | `TagOut[]`, lista completa sin paginar (excepción a `{items,next_cursor}`) | construida | read | tareas (13) |
| PUT | `/api/v1/tasks/{id}/tags` | `TaskTagsReplace` `{names:[...]}` (sustituye) | `TaskOut` | construida | write | tareas (13) |
| GET | `/api/v1/tags` | `q`, `limit`, `cursor` | `{items,next_cursor}` `TagOut` | (sin construir) | read | relaciones (15) |
| GET | `/api/v1/entities/{id}/tags` | - | `{items,next_cursor}` `TagOut` | (sin construir) | read | relaciones (15) |
| PUT | `/api/v1/entities/{id}/tags` | `{names:[...]}` (sustituye) | `{items,next_cursor}` `TagOut` | (sin construir) | write | relaciones (15) |
| GET | `/api/v1/relationships/types` | - | lista de reglas `RelationshipTypeOut` | construida | read | relaciones (15) |
| GET | `/api/v1/relationships` | `source_id`, `target_id`, `entity_type`, `type`, `limit`, `cursor` | `{items,next_cursor}` `RelationshipOut` | construida | read | relaciones (15) |
| POST | `/api/v1/relationships` | `RelationshipCreate` | 201 `RelationshipOut` | construida | write | relaciones (15) |
| PATCH | `/api/v1/relationships/{id}` | `RelationshipUpdate` | `RelationshipOut` | construida | write | relaciones (15) |
| DELETE | `/api/v1/relationships/{id}` | - | 409 `confirmation_required` | construida | confirm | relaciones (15) |
| GET | `/api/v1/entities/{id}/related` | `direction=in\|out\|both`, `type` | `RelatedItems` (incluye aristas virtuales de columnas) | construida | read | relaciones (15) |
| GET | `/api/v1/search` | `q`, `types`, `limit`, `cursor` (sin sintaxis FTS) | `SearchPage` `{items,next_cursor}` con `snippet`, sin archivados | construida | read | búsqueda (27) |

## Notificaciones y recordatorios

`drakter-26/backend/app/api/notifications.py`.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/notifications` | `unread`, `limit`, `cursor` | `{items,next_cursor}` `NotificationOut` | construida | read | recordatorios (26) |
| POST | `/api/v1/notifications/read` | `{ids:[uuid]}` (1..200) | `{updated}` | construida | write | recordatorios (26) |
| GET | `/api/v1/notifications/status` | - | `ReminderStatus` (`requires_app_open: true`) | construida | read | recordatorios (26) |

## Memoria

`drakter-18/backend/app/integrations/memory/router.py`. Contenido recuperado = dato no confiable.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/memory` | `statuses`, `kinds`, `categories`, `limit`, `cursor` | `{items,next_cursor}` `MemoryRecord` | construida | read | memoria (18) |
| POST | `/api/v1/memory` | `MemoryCreate` | 201 `MemoryCreated` | construida | write | memoria (18) |
| GET | `/api/v1/memory/status` | - | `BackendStatus` | construida | read | memoria (18) |
| GET | `/api/v1/memory/conflicts` | `open_only` | `{items,next_cursor}` `MemoryConflict` | construida | read | memoria (18) |
| POST | `/api/v1/memory/conflicts/{id}/resolve` | `{kept}` | `MemoryConflict` | construida | write | memoria (18) |
| POST | `/api/v1/memory/search` | `SearchBody` | `{items,next_cursor}` `MemoryHit` | construida | read | memoria (18) |
| GET | `/api/v1/memory/{id}` | - | `MemoryRecord` | construida | read | memoria (18) |
| PATCH | `/api/v1/memory/{id}` | `MemoryPatch` | `MemoryRecord` | construida | write | memoria (18) |
| POST | `/api/v1/memory/{id}/approve` | - | 409 `confirmation_required`; se ejecuta en `/confirmations/{id}/approve` y devuelve `MemoryRecord` | construida, ver desviaciones | confirm | memoria (18) |
| POST | `/api/v1/memory/{id}/reject` | - | `MemoryRecord` | construida | write | memoria (18) |
| POST | `/api/v1/memory/{id}/forget` | - (sin `confirmation_id`) | 409 `confirmation_required`; al aprobar, `ForgetReport` | construida | confirm | memoria (18) |

## Voz

Especificadas en `drakter-19/voice/CONTRACT.md:144` (`router.py` aún no existe). Sin ruta para hacer hablar a Drakter; voz no confirma en v1.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/voice/status` | - | estado de voz, dispositivos, latencias medidas | especificada | read | voz (19) |
| POST | `/api/v1/voice/mic` | `{enabled}` | estado | especificada | write | voz (19) |
| POST | `/api/v1/voice/wakeword` | `{enabled}` | estado | especificada | write | voz (19) |
| POST | `/api/v1/voice/listen/start` | - | 202 | especificada | write | voz (19) |
| POST | `/api/v1/voice/listen/stop` | - | 202 | especificada | write | voz (19) |
| POST | `/api/v1/voice/listen/cancel` | - | 202 | especificada | write | voz (19) |
| POST | `/api/v1/voice/interrupt` | - | 202 | especificada | write | voz (19) |

## Automejora

El frente 20 solo tiene puertos (`services/improvement_ports.py`, `get_principal`, `require_user`); no hay rutas. Las siguientes salen de las tablas `improvement_*` (migración 0010). Aprobar una propuesta no modifica producción, permisos, confirmaciones ni auditoría sin pasar por `confirmations`.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/improvement/proposals` | `status`, `limit`, `cursor` | `{items,next_cursor}` | (sin construir) | read | automejora (20) |
| GET | `/api/v1/improvement/proposals/{id}` | - | propuesta y evaluaciones | (sin construir) | read | automejora (20) |
| POST | `/api/v1/improvement/proposals/{id}/approve` | - | 409 `confirmation_required` | (sin construir) | confirm | automejora (20) |
| POST | `/api/v1/improvement/proposals/{id}/reject` | - | propuesta | (sin construir) | write | automejora (20) |
| POST | `/api/v1/improvement/feedback` | `{target, rating, note?}` | 201 | (sin construir) | write | automejora (20) |

## Desviaciones que deben corregirse

### Ajustes

| Frente | archivo:línea | Qué hace | Qué debe hacer |
|---|---|---|---|
| hoy-ajustes | `services/settings_models.py:18`, `services/settings.py:73`, `desktop/src/settings/TimezoneSection.tsx:37,96` | Clave `timezone`, que nadie más lee | Clave `default_timezone`: los recordatorios leen esa y hoy ignorarían la zona elegida |

Rutas de `drakter-NN` = `/home/imagana/.ao/data/worktrees/drakter/drakter-NN/`.

**Transversal (todos los frentes).** `backend/app/main.py:56-58`: solo montan `health`, `auth` y `ws`; ningún router de módulo está incluido. Cada dueño debe añadir `include_router` en la integración, no en un archivo común editado a la vez.

### Paginación (debe ser `{items,next_cursor,total?}` + `limit`/`cursor`)

Decisión: se adopta el cursor, que ya usan tareas, hábitos/calendario, almacén, relaciones y recordatorios.

| Frente | Dónde | Qué hace | Qué debe hacer |
|---|---|---|---|
| memoria (18) | `backend/app/memory/router.py` | `limit`, `offset`, `{items,total}` | `cursor` y `next_cursor`; puede conservar `total` |
| agente/chat (16) | `backend/app/integrations/hermes/CONTRACT.md` §4 | especifica `limit`, `offset` | Construir `api/chat.py` con cursor |
| tareas (13) | `tasks_contract.md:83+` | el documento mezcla `cursor` y `offset` | Dejar solo `cursor` |
| hábitos/calendario (14) | `api/habits.py:43-50`, `api/calendar.py:50-56`, `api/subjects.py:55-62` | `limit` sin tope en la ruta | Acotar `limit` en `Query` |

### Confirmación 2xx o con flujo propio (debe ser 409 y aprobar en `/confirmations/{id}/approve`)

| Frente | archivo:línea | Qué hace | Qué debe hacer |
|---|---|---|---|
| hábitos/calendario (14) | `backend/app/api/subjects.py:85,133`; `api/calendar.py:77,127`; forma en `services/habits_calendar_support.py:46-53` | `DELETE` responde **202** `ConfirmationRef{status,confirmation_id,summary,expires_at}` | 409 con sobre de error + `confirmation{id,summary,affected_count,expires_at,params_hash}` |
| almacén (15) | `backend/app/api/storage.py:42,92,123,145,151,199`; `api/relations.py:58-63` | El cliente reenvía la operación con `?confirmation_id=`; `DELETE` responde 204 si el id vale; `DenyAllConfirmations` da 503 (`services/storage_ports.py:133-149`) | La ruta no recibe `confirmation_id`: devuelve 409 y ejecuta `approve` con los argumentos guardados |
| memoria (18) | `backend/app/integrations/memory/router.py:103-105,189`; `service.py:193-195` | `forget` recibe `confirmation_id` en el cuerpo; 409 sin objeto `confirmation` | Sin cuerpo; 409 con `confirmation` en el sobre |
| memoria (18) | `backend/app/integrations/memory/router.py` | `POST /memory/{id}/approve` aprueba directamente con riesgo `write` | 409 y camino único: consolidar un recuerdo candidato exige confirmación |
| automejora (20) | `backend/app/services/backup_api.py:117-152,214-221,224-227,260-263` | Puerta propia `get_gate`, rutas `restore-request` y `delete-request`, `confirmation_id` en el cuerpo | Quitar esas dos rutas y la puerta; `restore` y `DELETE` sin cuerpo, 409 y ejecución en `/confirmations/{id}/approve` |
| hoy-ajustes | `backend/app/api/settings.py:35,40` | `/settings/backups`, segunda superficie de copias | Usar `/api/v1/backups` y retirar estas rutas |
| tareas (13) | `backend/app/api/tasks_http.py:62-70` | 409 correcto pero `confirmation` = `required.ticket` sin garantía de `id`/`params_hash` | Validar contra `ConfirmationRequiredEnvelope` |

### WebSocket distinto de `/api/v1/events`

| Frente | archivo:línea | Qué hace | Qué debe hacer |
|---|---|---|---|
| seguridad (12) y copias en 13-20 | `backend/app/api/ws.py:12`, `main.py:58` | `WS /ws` solo con ping/pong de texto | Sustituir por `WS /api/v1/events` |
| agente/chat (16) | `backend/app/integrations/hermes/CONTRACT.md:151,153` | `WS /api/v1/chat/events?after_seq`; sobre sin `boot_id` ni `correlation_id`; `state` de 6 valores | `/api/v1/events`, sobre completo, 9 estados |
| chat y personaje (17) | `desktop/src/services/ws.ts:5,192` | Conecta a `chatEventsPath(lastSeq)` (importado de `services/protocol.ts`, donde no está definido) | Conectar a `/api/v1/events?after_seq&boot_id` |

### Sobre de error

Sin divergencia en el JSON: todos usan `core/errors.py` (`AppError` y `_handle_http_exception`). Lo único propio es `drakter-13/backend/app/api/tasks_http.py:62-70`, que usa el sobre común más `confirmation` (correcto). Sin `HTTPException` directas en `api/`.

### Rutas distintas a la tabla

| Frente | archivo:línea | Qué hace | Qué debe hacer |
|---|---|---|---|
| relaciones (15) | `backend/app/api/relations.py:19` | `APIRouter(tags=...)` sin prefijo: `/relationships`, `/entities/{id}/related` quedan fuera de `/api/v1` | `prefix="/api/v1"` |
| tareas (13) | `backend/app/api/tasks_http.py` (sin rutas) | La GUI consume `/tasks...` pero no hay router de tareas | Escribir `api/tasks.py` según `tasks_contract.md` |
| voz (19) | `voice/CONTRACT.md:144` | Describe `router.py` que no existe | Escribirlo con las rutas de la sección Voz |
| agente/chat (16) | `CONTRACT.md:138-151` | `api/chat.py` documentado, sin código | Escribirlo; listados `{items,total}` ya cumplen |
| automejora (20) | `backend/app/services/improvement_ports.py` | Sin rutas | Router `/api/v1/improvement` de la sección Automejora |
| seguridad (12) | `backend/app/main.py:56-58` | Sin `confirmations`, `activity`, `settings`, `system/*` | Implementar las rutas marcadas `(sin construir)` |
