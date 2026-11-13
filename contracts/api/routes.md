# Rutas REST v1 de Drakter

Tabla única de rutas. Manda `contracts/README.md`; después, lo ya construido en los frentes. Prefijo `/api/v1` en todo salvo `GET /health`. Credencial: `Authorization: Bearer` en toda ruta, `ui` salvo lo marcado `approver` (README §1). El puerto es efímero. **Ninguna de estas rutas existe para el agente**: el agente solo entra por el listener MCP, con su propio puerto efímero y llama a los mismos servicios (`README` §1).

## Convenciones

- **Listados:** salvo las excepciones aceptadas en v1 (memoria, chat y automejora paginan por `offset`: ver desviaciones), `GET` devuelve `{items, next_cursor, total?}` y acepta `limit`, `cursor`, `sort=campo,-campo` (lista blanca por ruta); `limit` por defecto 50, máximo 200 (100 en recursos y búsqueda). El cursor es opaco; `total` es opcional. Salvo marca expresa, los listados excluyen archivados y aceptan `include_archived=true`.
- **PATCH:** parcial, `extra="forbid"`; `If-Match: <revision>` opcional, 412 `revision_mismatch`. Las mutaciones sobre una entidad aceptan `If-Match`. `POST` acepta `Idempotency-Key`.
- **Errores:** `{"error":{"code","message","request_id","details":[{"field","code","message"}]}}`. Sin otra forma de error.
- **Confirmación:** una ruta con riesgo `confirm` responde **409** `confirmation_required` con el sobre más `confirmation:{id,summary,affected_count,expires_at,params_hash}`; nunca 2xx. El cliente no manda `confirmation_id` ni `pre_confirmed`: la GUI aprueba con `POST /confirmations/{id}/approve` y el backend ejecuta los argumentos guardados. Los `DELETE` definitivos tienen riesgo `confirm`; archivar es `write`.
- **Borrado definitivo:** el `DELETE` directo de la GUI siempre responde 409 y crea la confirmación; la ejecución real (que termina en 204 de la operación guardada) ocurre en `approve`. Borrar un recurso nunca borra el archivo original.
- **Tiempo real:** un único `WS /api/v1/events?after_seq=N&boot_id=<id>` (subprotocolo `drakter.v1`, token en `Authorization: Bearer`). Sustituye a `/ws` y a `/api/v1/chat/events`.
- **Estado** (comprobado contra `drakter/integracion` el 2026-11-13): `construida` = montada en la app (`main.py` autodescubre cada `app/api/<nombre>.py` con `router`; memoria entra por `_install_services`); `escrita, sin montar` = el router existe fuera de `app/api/` y no se monta, así que hoy responde 404 `http_404`; `(sin construir)` = sin código.
- **Riesgo:** `read`, `write`, `confirm` (efectivo; puede subir a `confirm` por `bulk_threshold` o turno contaminado).

## Sistema, auth y tiempo real

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/health` (sin prefijo, con token `ui`) | - | `{status:"ok"}` | construida | read | seguridad (12) |
| GET | `/api/v1/auth/check` | - | `{authenticated:true}` | construida | read | seguridad (12) |
| WS | `/api/v1/events` | `after_seq`, `boot_id` | eventos `{event_id,seq,boot_id,timestamp,type,version,correlation_id,payload}` | construida | read | contratos / chat (17) |
| GET | `/api/v1/system/status` | - | versión, `boot_id`, BD y migración, salud de módulos, hora y zona | (sin construir) | read | seguridad (12) |
| GET | `/api/v1/backups` | - | `BundleInfo[]`, lista completa sin paginar | construida | read | backend-base (copias) |
| POST | `/api/v1/backups` | `CreateBundleRequest` `{label?, include_storage?}` | `BundleInfo` | construida | write | backend-base (copias) |
| POST | `/api/v1/backups/export` | - | `ExportResponse` | construida | write | backend-base (copias) |
| POST | `/api/v1/backups/{name}/verify` | - | `VerifyResponse` | construida | read | backend-base (copias) |
| POST | `/api/v1/backups/{name}/restore` | sin cuerpo | 409 `confirmation_required`; se ejecutaría en `/confirmations/{id}/approve` | (sin construir), ver desviaciones | confirm | backend-base (copias) |
| DELETE | `/api/v1/backups/{name}` | sin cuerpo | 409 `confirmation_required` (acción `delete_backup`, permiso `backups.delete`); se borra en `/confirmations/{id}/approve` | construida | confirm | backend-base (copias) |
| GET | `/api/v1/today` | `timezone` (obligatoria, IANA) | `TodayResponse`; 422 `invalid_timezone` | construida | read | hoy-ajustes |
| GET | `/api/v1/settings` | - | `{persisted, items:[SettingOut]}` | construida | read | hoy-ajustes |
| GET | `/api/v1/settings/status` | - | estado de agente y clave, solo presencia | construida | read | hoy-ajustes |
| GET | `/api/v1/settings/backups` | - | copias | construida | read | hoy-ajustes |
| POST | `/api/v1/settings/backups` | - | 201 copia | construida | write | hoy-ajustes |
| POST | `/api/v1/settings/{key}` | `SettingUpdate` `{value}` | `SettingOut`; 404 `unknown_setting` si la clave no está permitida | construida | write | hoy-ajustes |
| GET | `/api/v1/activity` | `actor`, `entity_id`, `result`, `from`, `to`, `limit`, `cursor` | `{items,next_cursor}` de auditoría (sin contenido de documentos) | construida | read | seguridad (12) |

## Confirmaciones

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/confirmations` | `status`, `limit`, `cursor` | `{items,next_cursor}` | construida | read | seguridad (12) |
| GET | `/api/v1/confirmations/{id}` | - (`ui`; `approver` no lee: 403) | acción, `summary`, `affected_count`, `targets`, `status`, `expires_at`, `params_hash` | construida | read | seguridad (12) |
| POST | `/api/v1/confirmations/{id}/approve` | `ConfirmationApprove`: `{params_hash}` (`approver`) | resultado de la operación ejecutada; 409 `conflict` si `targets_json` cambió o `confirmation_already_resolved`; 410 `confirmation_expired`; 404; 422 | construida | write (ejecuta lo guardado) | seguridad (12) |
| POST | `/api/v1/confirmations/{id}/reject` | sin cuerpo (`approver`) | confirmación en `rejected` | construida | write | seguridad (12) |

## Agente y chat

`backend/app/api/chat.py`, especificado en `backend/app/integrations/hermes/CONTRACT.md` §4; el hilo de eventos es `WS /api/v1/events`.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| POST | `/api/v1/chat/sessions` | - | 201 `ChatSession` | construida | write | agente/chat (16) |
| GET | `/api/v1/chat/sessions` | `limit`, `cursor` | `{items,next_cursor}` | construida | read | agente/chat (16) |
| POST | `/api/v1/chat/sessions/{id}/close` | - | `ChatSession` | construida | write | agente/chat (16) |
| GET | `/api/v1/chat/sessions/{id}/messages` | `limit`, `cursor` | `{items,next_cursor}` `MessageOut` (`session_id`, `text`) | construida | read | agente/chat (16) |
| POST | `/api/v1/chat/sessions/{id}/messages` | `MessageCreate`: `{text, client_message_id, input_source?}` | 202 `MessageAccepted` `{turn_id,message_id}`; 409 `agent_busy` | construida | write | agente/chat (16) |
| POST | `/api/v1/chat/turns/{turn_id}/cancel` | - | 202 | construida | write | agente/chat (16) |
| GET | `/api/v1/agent/status` | - | `AgentStatusOut` `{state,provider,model,detail}`; `state` entre los 9 del personaje | construida | read | agente/chat (16) |

## Tareas

`backend/app/api/tasks.py` (ayudantes HTTP en `api/tasks_http.py`), según `backend/app/schemas/tasks_contract.md`. La GUI (`desktop/src/modules/tasks/api.ts`) las consume.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/tasks` | `status`, `priority` (repetibles), `project_id`, `subject_id`, `parent_task_id`, `due_from`, `due_to`, `q`, `include_archived`, `sort`, `limit`, `cursor` | `{items,next_cursor}` `TaskOut` | construida | read | tareas (13) |
| POST | `/api/v1/tasks` | `TaskCreate` | 201 `TaskOut` | construida | write | tareas (13) |
| GET | `/api/v1/tasks/{id}` | - | `TaskDetail` | construida | read | tareas (13) |
| PATCH | `/api/v1/tasks/{id}` | `TaskUpdate` | `TaskOut` | construida | write | tareas (13) |
| DELETE | `/api/v1/tasks/{id}` | `If-Match` | 409 `confirmation_required` (204 al ejecutarse tras aprobar) | construida | confirm | tareas (13) |
| POST | `/api/v1/tasks/{id}/complete` | `{complete_subtasks?}` | `TaskOut` | construida | write; `confirm` si cierra por encima de `bulk_threshold` | tareas (13) |
| POST | `/api/v1/tasks/{id}/reopen` | - | `TaskOut` | construida | write | tareas (13) |
| POST | `/api/v1/tasks/{id}/archive` | - | `TaskOut` | construida | write | tareas (13) |
| POST | `/api/v1/tasks/{id}/unarchive` | - | `TaskOut` | construida | write | tareas (13) |
| GET | `/api/v1/tasks/{id}/subtasks` | `limit`, `cursor` | `{items,next_cursor}` `TaskOut` | (sin construir) | read | tareas (13) |
| POST | `/api/v1/tasks/{id}/subtasks` | `SubtaskCreate` | 201 `TaskOut` | construida | write | tareas (13) |
| POST | `/api/v1/tasks/{id}/dependencies` | `{depends_on_task_id}` | `TaskDetail` | construida | write | tareas (13) |
| DELETE | `/api/v1/tasks/{id}/dependencies/{dep_id}` | - | `TaskDetail` | construida | write | tareas (13) |
| GET | `/api/v1/tasks/{id}/history` | `limit`, `cursor` | `{items,next_cursor}` `HistoryEntry` | construida | read | tareas (13) |

## Proyectos

`backend/app/api/projects.py`.

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

`backend/app/api/habits.py`. No hay `DELETE /habits/{id}`: un hábito se archiva.

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
| DELETE | `/api/v1/habits/{id}/records/{date}` | - | 204 | construida | write | hábitos/calendario (14) |
| GET | `/api/v1/habits/{id}/history` | - | `HabitHistory` (versiones de frecuencia) | construida | read | hábitos/calendario (14) |
| GET | `/api/v1/habits/{id}/statistics` | `from`, `to` | `HabitStatistics` | construida | read | hábitos/calendario (14) |

## Calendario

`backend/app/api/calendar.py`. `timezone` IANA obligatoria en consultas por ventana.

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

`backend/app/api/subjects.py`.

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

`backend/app/api/storage.py`. Nunca ruta absoluta salvo al crear una ubicación; `storage-locations` solo desde la GUI, sin herramienta para el agente.

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

`backend/app/api/relations.py` y `relations_tags.py`; búsqueda global en `backend/app/api/search.py`.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/tasks/tags` | - | `TagOut[]`, lista completa sin paginar (excepción a `{items,next_cursor}`) | construida | read | tareas (13) |
| PUT | `/api/v1/tasks/{id}/tags` | `TaskTagsReplace` `{names:[...]}` (sustituye) | `TaskOut` | construida | write | tareas (13) |
| GET | `/api/v1/tags` | `q`, `limit`, `cursor` | `{items,next_cursor}` `TagOut` | construida | read | relaciones (15) |
| GET | `/api/v1/entities/{id}/tags` | - | `{items,next_cursor}` `TagOut` | construida | read | relaciones (15) |
| PUT | `/api/v1/entities/{id}/tags` | `{names:[...]}` (sustituye) | `{items,next_cursor}` `TagOut` | construida | write | relaciones (15) |
| GET | `/api/v1/relationships/types` | - | lista de reglas `RelationshipTypeOut` | construida | read | relaciones (15) |
| GET | `/api/v1/relationships` | `source_id`, `target_id`, `entity_type`, `type`, `limit`, `cursor` | `{items,next_cursor}` `RelationshipOut` | construida | read | relaciones (15) |
| POST | `/api/v1/relationships` | `RelationshipCreate` | 201 `RelationshipOut` | construida | write | relaciones (15) |
| PATCH | `/api/v1/relationships/{id}` | `RelationshipUpdate` | `RelationshipOut` | construida | write | relaciones (15) |
| DELETE | `/api/v1/relationships/{id}` | - | 409 `confirmation_required` | construida | confirm | relaciones (15) |
| GET | `/api/v1/entities/{id}/related` | `direction=in\|out\|both`, `type` | `RelatedItems` (incluye aristas virtuales de columnas) | construida | read | relaciones (15) |
| GET | `/api/v1/search` | `q`, `types`, `limit`, `cursor` (sin sintaxis FTS) | `SearchPage` `{items,next_cursor}` con `snippet`, sin archivados | construida | read | búsqueda (27) |

## Notificaciones y recordatorios

`backend/app/api/notifications.py`.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/notifications` | `unread`, `limit`, `cursor` | `{items,next_cursor}` `NotificationOut` | construida | read | recordatorios (26) |
| POST | `/api/v1/notifications/read` | `{ids:[uuid]}` (1..200) | `{updated}` | construida | write | recordatorios (26) |
| GET | `/api/v1/notifications/status` | - | `ReminderStatus` (`requires_app_open: true`) | construida | read | recordatorios (26) |

## Memoria

`backend/app/integrations/memory/router.py`, montado desde `_install_services`. Contenido recuperado = dato no confiable.

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

Router escrito en `backend/app/integrations/voice/router.py` (`voice/CONTRACT.md`), sin montar: no está en `app/api/` y `main.py` no lo incluye. En v1 se queda así (DECISIONS «Voz: cierre mínimo, rediseño posterior sobre Pipecat»). Sin ruta para hacer hablar a Drakter; voz no confirma en v1.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/voice/status` | - | estado de voz, dispositivos, latencias medidas | escrita, sin montar | read | voz (19) |
| POST | `/api/v1/voice/mic` | `{enabled}` | estado | escrita, sin montar | write | voz (19) |
| POST | `/api/v1/voice/wakeword` | `{enabled}` | estado | escrita, sin montar | write | voz (19) |
| POST | `/api/v1/voice/listen/start` | - | 202 | escrita, sin montar | write | voz (19) |
| POST | `/api/v1/voice/listen/stop` | - | 202 | escrita, sin montar | write | voz (19) |
| POST | `/api/v1/voice/listen/cancel` | - | 202 | escrita, sin montar | write | voz (19) |
| POST | `/api/v1/voice/interrupt` | - | 202 | escrita, sin montar | write | voz (19) |

## Automejora

`backend/app/services/improvement_api.py`, montado por `backend/app/api/improvement.py` (DECISIONS «Esquema de automejora: manda el del servicio», migración 0012). Drakter propone; aplicar exige una propuesta aprobada. Aprobar y revertir pasan por `ActionService` (`services/improvement_actions.py`): `approval-request` y `revert-request` responden 409 y el approver decide en `/confirmations/{id}/approve`. Nada cambia producción, permisos, confirmaciones ni auditoría sin aprobación.

| Método | Ruta | Entrada | Respuesta | Estado | Riesgo | Dueño |
|---|---|---|---|---|---|---|
| GET | `/api/v1/improvement/feedback` | `limit`, `offset`, `category`, `severity`, `origin` | listado de comentarios | construida, ver desviaciones | read | automejora (20) |
| POST | `/api/v1/improvement/feedback` | `FeedbackCreate` | 201 comentario | construida | write | automejora (20) |
| GET | `/api/v1/improvement/feedback/{id}` | - | comentario | construida | read | automejora (20) |
| PATCH | `/api/v1/improvement/feedback/{id}/classification` | `FeedbackReclassify` | comentario | construida | write | automejora (20) |
| GET | `/api/v1/improvement/proposals` | `status`, `limit`, `offset` | listado de propuestas | construida, ver desviaciones | read | automejora (20) |
| POST | `/api/v1/improvement/proposals` | `ProposalCreate` | 201 propuesta | construida | write | automejora (20) |
| GET | `/api/v1/improvement/proposals/{id}` | - | propuesta y evaluaciones | construida | read | automejora (20) |
| POST | `/api/v1/improvement/proposals/{id}/evaluate` | - | evaluación | construida | write | automejora (20) |
| POST | `/api/v1/improvement/proposals/{id}/approval-request` | - | 409 `confirmation_required`; se aprueba en `/confirmations/{id}/approve` | construida | confirm | automejora (20) |
| POST | `/api/v1/improvement/proposals/{id}/apply` | - | propuesta aplicada (solo si está aprobada) | construida | write | automejora (20) |
| POST | `/api/v1/improvement/proposals/{id}/revert-request` | - | 409 `confirmation_required`; se revierte en `/confirmations/{id}/approve` | construida | confirm | automejora (20) |
| POST | `/api/v1/improvement/proposals/{id}/reject` | `{reason}` | propuesta | construida | write | automejora (20) |
| GET | `/api/v1/improvement/reports/summary` | `from`, `to` | resumen | construida | read | automejora (20) |
| POST | `/api/v1/improvement/reports/export` | `ReportExportBody` | 201 ruta del informe | construida | write | automejora (20) |
| GET | `/api/v1/improvement/changelog` | `limit`, `offset`, `proposal_id` | historial de cambios aplicados | construida, ver desviaciones | read | automejora (20) |

## Desviaciones que deben corregirse

Revisadas contra `drakter/integracion` el 2026-11-13. Rutas relativas a la raíz del repositorio. Lo que figuraba antes y ya está corregido (clave `default_timezone`; `WS /ws` y `/api/v1/chat/events`, sustituidos por `/api/v1/events`; `limit` sin tope en hábitos, calendario y asignaturas; `relations.py` sin prefijo; `api/tasks.py`, `api/chat.py`, `confirmations`, `activity` y `settings` sin código; `DELETE` 202 en hábitos y calendario; `?confirmation_id=` en almacén; `ConfirmationTicket` de tareas) no se repite aquí.

### Arranque: piezas escritas que no se conectan (integración, `backend/app/main.py`)

Ya resuelto (fusión de drakter-34, `app/permissions/wiring.py`): pipeline de confirmaciones instalado (`wire_security`, `start_security`, `stop_security`), acciones de hábitos y calendario registradas con `calendar_actions.register_actions`, y `workspace_ports` con `ConfirmationGate` sobre `ActionService` y `HubEventSink`. Comprobado: `DELETE /api/v1/tasks/{id}` → 409 con `confirmation`; `GET /api/v1/confirmations` → 200.

| Qué | Dónde | Efecto hoy | Qué debe hacer |
|---|---|---|---|
| Restaurar copias por la API | `app/services/backup_service.py:restore_bundle` llama a `database/backup.restore_backup`, que toma el bloqueo de instancia con un `flock` propio; con el backend en marcha ese bloqueo ya lo tiene el proceso, y nadie instala `post_restore_hooks` ni `restore_quiesce` | ⚠️ Sin ruta: restaurar solo con el backend parado (`python -m app.database.cli restore`, copias SQLite) | Diseño propio: dejar de servir, soltar el bloqueo, restaurar, invalidar confirmaciones (README §5) y rearrancar. Fuera del cierre v1 |
| Voz sin montar ni arrancar | `app/integrations/voice/router.py` y su supervisor no se usan fuera de su paquete | `/api/v1/voice/**` da 404 y no se emite ningún `voice.*` | Nada en v1: DECISIONS «Voz: cierre mínimo, rediseño posterior sobre Pipecat». Se rehace con el rediseño |

### Paginación por `offset`: desviación aceptada en v1

El contrato pide `{items,next_cursor,total?}` con `limit`/`cursor`. Estos listados usan `limit`/`offset` y **no se refactorizan en v1** (decisión de cierre del 2026-11-13): el cliente debe usar `offset` en ellos. El resto de listados siguen el cursor.

| Frente | Dónde | Qué hace | Forma del contrato (posterior a v1) |
|---|---|---|---|
| memoria (18) | `backend/app/integrations/memory/router.py:84,115-125` | `limit`, `offset`, `{items,total,limit,offset}` | `cursor` y `next_cursor`; puede conservar `total` |
| agente/chat (16) | `backend/app/api/chat.py:83,95` | `limit`, `offset` en sesiones y mensajes | `cursor` y `next_cursor` |
| automejora (20) | `backend/app/services/improvement_api.py` (`feedback`, `proposals`, `changelog`) | `limit`, `offset` | `cursor` y `next_cursor` |

### Confirmación con flujo propio (debe ser 409 y aprobar en `/confirmations/{id}/approve`)

| Frente | archivo:línea | Qué hace | Qué debe hacer |
|---|---|---|---|
| memoria (18) | `backend/app/integrations/memory/router.py:105,188-189` | `forget` recibe `confirmation_id` en el cuerpo | Sin cuerpo; 409 con `confirmation` en el sobre |
| memoria (18) | `backend/app/integrations/memory/router.py:178-179` | `POST /memory/{id}/approve` aprueba directamente | 409 y camino único: consolidar un recuerdo candidato exige confirmación |
| hoy-ajustes | `backend/app/api/settings.py:35,40`, consumidas por `desktop/src/pages/today/requests.ts:29,33` | `/settings/backups`, copias SQLite sueltas (`database/backup.create_backup`), segunda superficie junto a los bundles de `/api/v1/backups` | Que la GUI pase a `/api/v1/backups` y retirar estas rutas |

### Eventos del catálogo que nadie emite o nadie escucha

Solo documentados: en v1 no se implementan emisores ni oyentes nuevos (decisión de cierre del 2026-11-13). El catálogo de `events.py` se mantiene.

| Evento | Estado |
|---|---|
| `workspace.entity_*` | Tareas y proyectos ya los emiten con `actor_type` (`services/tasks.py:186`, `services/projects.py:113`); el resto de módulos no los emite, y el desktop no escucha `workspace.*` |
| `workspace.relationship_*` | Ningún emisor en el backend |
| `agent.expression_changed`, `storage.index_progress` | Ningún emisor en el backend |
| `voice.*` | Los emite la integración de voz, que no se arranca |
| `system.health_changed` | Lo emite `integrations/hermes/runtime.py`; el desktop no lo escucha y deriva `offline` solo de la caída del socket (admitido en README §7) |

### Sobre de error

Sin divergencia: todos usan `core/errors.py` (`AppError` y `_handle_http_exception`); tareas añade `confirmation` al sobre común (correcto). Sin `HTTPException` directas en `api/`.
