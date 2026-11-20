---
name: workspace-projects
description: "Proyectos: crear, consultar, editar, ver el progreso, archivar y restaurar."
version: 2.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, projects]
---

# workspace-projects

## Herramientas
- Buscar: `list_projects` (q, status planned|active|paused|completed|cancelled, priority, include_archived).
- Leer: `get_project`; avance: `get_project_progress` (no lo estimes tú).
- Crear: `create_project` (name; opcional description, objective, status, priority, start_date, target_date).
- Cambiar: `update_project` (project_id, patch con solo lo que cambia, expected_revision si la tienes).
- Archivar / restaurar: `archive_project`, `unarchive_project`. No hay borrado de proyectos: archívalo o dilo.
- Tareas del proyecto: `list_tasks` con project_id; crear una dentro: `create_task` con project_id.

## Orden típico
1. `list_projects` con q para encontrar el id.
2. `get_project` o `get_project_progress` según la pregunta.
3. Acción y respuesta con el dato devuelto.

## Errores frecuentes
- Confundir proyecto con tarea: un proyecto agrupa tareas; «haz X» suele ser una tarea.
- `revision_mismatch`: vuelve a leer con `get_project` y reintenta una vez.
- Pedir borrar un proyecto: no existe la herramienta; ofrece archivarlo.

## Ejemplos
- «¿Cómo va el TFG?» → `list_projects` q «TFG» → `get_project_progress`.
- «Crea un proyecto Mudanza para junio» → `create_project` con name y target_date.
- «Archiva el proyecto viejo de la web» → `list_projects` → `archive_project`.
