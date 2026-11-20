---
name: workspace-tasks
description: "Tareas y subtareas: crear, buscar, editar, completar, archivar, etiquetar, dependencias y borrar."
version: 2.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, tasks]
---

# workspace-tasks

## Herramientas
- Buscar: `search_tasks` (texto) o `list_tasks` (filtros: status, priority, project_id, subject_id, tag, due_before/due_after).
- Leer: `get_task` (subtareas, dependencias y revisión).
- Crear: `create_task` (title; opcional due_date o due_at, priority low|medium|high|urgent, project_id, subject_id, tags). Subtarea: `create_subtask` (parent_task_id, subtask).
- Cambiar: `update_task` (task_id, patch con solo lo que cambia). Estado: `complete_task`, `reopen_task`, `archive_task`, `unarchive_task`.
- Etiquetas: `set_task_tags` sustituye todas; para añadir una sola usa `add_tag`.
- Dependencias: `add_task_dependency` / `remove_task_dependency` (task_id depende de depends_on_task_id).
- Borrar: `delete_task` (task_id, expected_revision). Pide confirmación en pantalla. Solo tareas sin subtareas; si basta con quitarla de la vista, archiva.

## Orden típico
1. Para algo existente: `search_tasks` → elige el id → `get_task` si hace falta la revisión.
2. Ejecuta la acción y confirma con el resultado.
3. Para «terminé X», `complete_task`, no `update_task`.

## Errores frecuentes
- Fecha relativa («el viernes»): calcúlala sobre la fecha actual y usa `due_date` AAAA-MM-DD.
- Para asociar a un proyecto, busca antes su id con `list_projects`.
- `hierarchy_cycle`: la dependencia o el padre crearía un ciclo; explícalo.

## Ejemplos
- «Apunta llamar al dentista el viernes» → `create_task` con title y due_date.
- «Ya he hecho la memoria» → `search_tasks` «memoria» → `complete_task`.
- «Borra la tarea de prueba» → `search_tasks` → `get_task` → `delete_task` → «Queda pendiente de aprobar en la interfaz».
