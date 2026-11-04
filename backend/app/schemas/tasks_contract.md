# Contrato local de tareas y proyectos (Checklist 7)

Rama `drakter/tareas-proyectos`. Manda sobre los archivos de este módulo hasta que `contracts/` lo sustituya.
Esquemas: `schemas/tasks.py`, `schemas/projects.py`. Puertos: `services/tasks_ports.py`.
Tablas comunes: `repositories/tasks_shared.py`. HTTP: `api/tasks_http.py`. Esquema: `backend/migrations/` y reglas de `contracts/README.md`, que mandan sobre este archivo.

## Capas

`api/*` y `tools/*` → `services/*` → `repositories/*` → sqlite3. Solo `repositories/` contiene SQL.
Las conexiones usan `sqlite3.Row` y `isolation_level=None`: toda escritura va dentro de
`with transaction(ctx.conn):` en el servicio. Sin `INSERT OR REPLACE`. Parámetros siempre ligados; en `LIKE`, escapar `%`, `_` y `\` con `ESCAPE '\'`.
`ORDER BY` solo desde lista blanca. `sqlite3.IntegrityError` se traduce a `conflict`; los `raise` `task_hierarchy_cycle` y `relationship_cycle`, a `hierarchy_cycle()`.
Cada escritura, dentro de su transacción: `touch_entity` (salvo al crear), `write_audit` con `changes` `{campo: {"from":..,"to":..}}`,
y tras el `COMMIT`, `ctx.ports.events.publish("workspace.entity_created|updated|archived|restored|deleted", {"entity_type","entity_id","revision"})`.
`action` de auditoría: `task.create`, `task.update`, `task.complete`, `task.reopen`, `task.archive`, `task.unarchive`, `task.delete`, `task.tags`, `task.dependency_add`, `task.dependency_remove`; igual con `project.`.
Las respuestas `*Out` se construyen con `model_validate` de dicts; `id` y fechas salen como las guarda la base.

## Reglas de dominio de tareas

- Estados: se cambian por `update_task` salvo `completed`. `update_task` sobre una tarea `completed` que incluya `status` da `conflict` ("reábrela primero").
- `complete_task`: con subtareas abiertas (no `completed` ni `cancelled`, no archivadas) da `conflict` salvo `complete_subtasks=true`, que completa el subárbol entero en la misma transacción. Con dependencias sin resolver da `conflict`; `blocked` es: alguna dependencia no está `completed` ni `cancelled`. En cascada también se comprueban las dependencias de cada tarea del subárbol, ignorando las que están dentro del propio subárbol.
- `complete_task` sobre una tarea ya completada: devuelve la tarea sin cambios (idempotente).
- `reopen_task`: solo desde `completed` o `cancelled`; queda `pending` y `completed_at` a NULL. Si su padre está completado, da `conflict`.
- Jerarquía: profundidad máxima `MAX_TASK_DEPTH` (raíz = 0), contando el subárbol que se mueve. Mover bajo sí misma o un descendiente da `hierarchy_cycle`. No se crea bajo una tarea archivada.
- Una subtarea hereda el `project_id` del padre: pasar otro distinto da `conflict`. Cambiar el proyecto de una raíz lo propaga al subárbol. Cambiar `parent_task_id` fija el proyecto del nuevo padre en todo el subárbol.
- `project_id` y `subject_id` deben existir (`entity_exists`), si no `not_found`. No se asocia a un proyecto archivado (`conflict`).
- `position`: si no llega, último del grupo de hermanos + 1.
- Dependencias: `task depends_on otro`. Autodependencia o ciclo (`dependency_would_cycle` dentro de la transacción) da `hierarchy_cycle`.
- Archivar no propaga a hijos (README §4): afecta solo a esa tarea, y desarchivar igual. Es riesgo `write`, sin confirmación.
- Borrar: siempre `confirmation`. Borra el subárbol de abajo arriba y antes llama a `remove_all_dependencies`.
- Masivo: si una cascada (complete, cambio de proyecto) afecta a más de `BULK_THRESHOLD` filas, pasa por la puerta de confirmación.

- Una tarea `completed` no admite subtareas abiertas: crear bajo ella, o pasar a un estado abierto una subtarea suya por `update_task`, da `conflict`.
- Borrar una tarea de la que dependen otras fuera del subárbol: cada una sube `revision` y audita `task.dependency_remove`; entran en `targets` y el `summary` indica `y {m} dependientes`.
- `params` de auditoría: solo ids, booleanos y nombres de campos, nunca títulos, descripciones ni metadatos (lista blanca).
- Toda escritura pública lleva `@audits_failure(action, entity_type)` de `tasks_shared`.

## Reglas de proyectos

- `status=completed` fija `completed_at`; salir de él lo pone a NULL.
- `objective` se guarda en `metadata_json` bajo `objective`; `metadata` de salida no incluye esa clave.
- Archivar un proyecto no toca sus tareas. Actualizar un proyecto archivado da `conflict`, salvo para desarchivar.
- Borrar: siempre `confirmation`. Con relaciones entrantes o salientes, o filas que lo referencien con RESTRICT, da `has_dependents` antes de pedir confirmación; un `IntegrityError` al ejecutar da lo mismo. Las tareas se quedan, con `project_id` a NULL: entran en `targets`, cada una sube `revision` y audita `task.update` con `changes`. `summary`: `Vas a eliminar 1 proyecto: «{nombre}». Esta acción no se puede deshacer.` y, si hay m>0 tareas, `Sus {m} tareas se conservan sin proyecto.`; `affected_count` = 1 + m.
- Listados: `{items, total}` con `limit` y `offset`; se excluyen archivados salvo `include_archived=true`.
- Progreso según `ProjectProgress`: hojas = tareas del proyecto sin hijos no archivados; `overdue` = hojas abiertas con `due_at` o `due_date` anterior a ahora.
- Actividad: `history_for` sobre el proyecto y todas sus tareas.

## Confirmación

- El backend decide, nunca el llamante. `summary` y `affected_count` se calculan en el servicio (C-06).
- Flujo del servicio cuando hace falta confirmar y `pre_confirmed=False`: fuera de transacción resuelve los ids y revisiones, llama a `ctx.ports.confirmations.request(...)`, audita con `result="confirmation_required"` y lanza `ConfirmationRequired(ticket)`.
- `args` son JSON (`{"task_id": str, ...}`) y permiten repetir la operación.
- `summary` sigue la plantilla del README §5: `Vas a eliminar {n} {tipo}: «{nombre}»[ y {m} dependientes]. Esta acción no se puede deshacer.`, con verbo «eliminar» para borrar.
- El 409 es el de `confirmation_response`: `{error, confirmation:{id, summary, affected_count, expires_at, params_hash}}`. La GUI nunca aprueba por REST: pide la revisión al diálogo nativo de main.
- `services/tasks.py` expone `TASK_CONFIRMABLE` y `services/projects.py` `PROJECT_CONFIRMABLE`: `dict[str, Callable[[ServiceContext, Mapping[str, Any], Sequence[ConfirmationTarget]], Any]]`, clave = `tool_name`. Es lo que debe llamar `drakter/seguridad` al aprobar. El ejecutor comprueba que cada `revision` coincide (si no, `conflict`) y llama con `pre_confirmed=True`.
- `pre_confirmed=True` solo lo pasan esos ejecutores y los handlers de herramientas con riesgo `CONFIRM`, que solo corren tras el `ToolGate`. REST nunca lo acepta del cliente.
- Sin puerta real, `FailClosedGate` responde 503 `confirmation_unavailable` y no se ejecuta nada.

## Servicios (`ctx: ServiceContext` siempre primero)

```python
# services/tasks.py
create_task(ctx, data: TaskCreate) -> TaskOut
create_subtask(ctx, parent_id: str, data: SubtaskCreate) -> TaskOut
get_task(ctx, task_id: str) -> TaskDetail
list_tasks(ctx, query: TaskListQuery) -> Page[TaskOut]
update_task(ctx, task_id, data: TaskUpdate, *, expected_revision: int | None = None, pre_confirmed: bool = False) -> TaskOut
complete_task(ctx, task_id, data: TaskCompleteRequest, *, expected_revision=None, pre_confirmed=False) -> TaskOut
reopen_task(ctx, task_id, *, expected_revision=None) -> TaskOut
archive_task(ctx, task_id, *, expected_revision=None) -> TaskOut
unarchive_task(ctx, task_id, *, expected_revision=None) -> TaskOut
delete_task(ctx, task_id, *, expected_revision=None, pre_confirmed=False) -> None
delete_leaf_task(ctx, task_id, expected_revision: int) -> None
replace_task_tags(ctx, task_id, names: list[str]) -> TaskOut
list_task_tags(ctx) -> list[TagOut]
add_task_dependency(ctx, task_id, depends_on_id) -> TaskDetail
remove_task_dependency(ctx, task_id, depends_on_id) -> TaskDetail
task_history(ctx, task_id, *, limit: int, offset: int) -> Page[HistoryEntry]

# services/projects.py
create_project(ctx, data: ProjectCreate) -> ProjectOut
get_project(ctx, project_id) -> ProjectOut
list_projects(ctx, query: ProjectListQuery) -> Page[ProjectOut]
update_project(ctx, project_id, data: ProjectUpdate, *, expected_revision=None) -> ProjectOut
archive_project(ctx, project_id, *, expected_revision=None) -> ProjectOut
unarchive_project(ctx, project_id, *, expected_revision=None) -> ProjectOut
delete_project(ctx, project_id, *, expected_revision=None, pre_confirmed=False) -> None
get_project_progress(ctx, project_id) -> ProjectProgress
project_activity(ctx, project_id, *, limit: int, offset: int) -> Page[HistoryEntry]
```

## REST (`/api/v1`, cada router exporta `router`)

Handlers síncronos con `with service_context(request) as ctx:`. Revisión opcional: `If-Match` o `?revision=N` con `expected_revision(if_match, revision)`; la GUI usa la query porque `window.api.call` no transporta cabeceras. `except ConfirmationRequired as exc: return confirmation_response(request, exc)`.

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| GET `/tasks` | query `TaskListQuery` (`status`, `priority` repetibles) | `Page[TaskOut]` |
| POST `/tasks` | `TaskCreate` | 201 `TaskOut` |
| GET `/tasks/tags` | | `list[TagOut]` |
| GET `/tasks/{id}` | | `TaskDetail` |
| PATCH `/tasks/{id}` | `TaskUpdate` | `TaskOut` |
| DELETE `/tasks/{id}` | | 204 o 409 `confirmation` |
| POST `/tasks/{id}/complete` | `TaskCompleteRequest` opcional | `TaskOut` |
| POST `/tasks/{id}/reopen`, `/archive`, `/unarchive` | | `TaskOut` |
| POST `/tasks/{id}/subtasks` | `SubtaskCreate` | 201 `TaskOut` |
| PUT `/tasks/{id}/tags` | `TaskTagsReplace` | `TaskOut` |
| POST `/tasks/{id}/dependencies` | `TaskDependencyCreate` | `TaskDetail` |
| DELETE `/tasks/{id}/dependencies/{dep_id}` | | `TaskDetail` |
| GET `/tasks/{id}/history?limit&offset` | | `Page[HistoryEntry]` |
| GET `/projects` | query `ProjectListQuery` | `Page[ProjectOut]` |
| POST `/projects` | `ProjectCreate` | 201 `ProjectOut` |
| GET, PATCH, DELETE `/projects/{id}` | `ProjectUpdate` | `ProjectOut`; DELETE 204 o 409 |
| POST `/projects/{id}/archive`, `/unarchive` | | `ProjectOut` |
| GET `/projects/{id}/progress` | | `ProjectProgress` |
| GET `/projects/{id}/activity?limit&offset` | | `Page[HistoryEntry]` |

Los `id` de ruta son `UUID`, así una ruta como `/tasks/tags` no choca. El error es el envelope común `AppError`.

## Herramientas (contrato de `drakter/agente-hermes`)

`app/tools/tasks.py` y `app/tools/projects.py`, cada uno con `TOOLS: tuple[ToolSpec, ...]`.

- `delete_task` por herramienta: `ToolSpec` no resuelve el alcance, así que llama a `delete_leaf_task(ctx, task_id, expected_revision)`: exige revisión y da `conflict` si tiene subtareas o dependientes. Lo aprobado es lo ejecutado.
- Tasks: `create_task`, `get_task`, `update_task`, `complete_task`, `reopen_task`, `archive_task`, `unarchive_task`, `create_subtask`, `list_tasks`, `search_tasks`, `set_task_tags`, `add_task_dependency`, `remove_task_dependency`, `delete_task` (CONFIRM).
- Projects: `create_project`, `get_project`, `update_project`, `archive_project`, `unarchive_project`, `list_projects`, `get_project_progress`. El borrado de proyectos queda solo en GUI (C-05).
- `get_*`, `list_*` y `search_*` son READ; el resto, WRITE, salvo `delete_task`. Permisos `tasks.read`, `tasks.write`, `tasks.delete`, `projects.read`, `projects.write`.
- Títulos y descripciones son texto del usuario o del propio agente, no documentos: `returns_untrusted=False`.
