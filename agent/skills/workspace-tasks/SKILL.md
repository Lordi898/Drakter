---
name: workspace-tasks
description: "Gestiona tareas y subtareas del Workspace: crear, buscar, actualizar, completar y archivar."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, workspace, tasks]
---

# workspace-tasks

## Propósito
Operar sobre las tareas del usuario mediante herramientas del backend.

## Cuándo usarla
El usuario pide anotar, consultar, cambiar, completar, archivar o dividir una tarea.

## Parámetros (intención)
Título, descripción, prioridad, fecha límite, estado, tarea padre (subtarea), texto de búsqueda.

## Ejemplos
"Apunta una tarea: llamar al dentista el viernes"; "Qué tengo pendiente esta semana"; "Divide la tarea de la memoria en dos subtareas".

## Restricciones
- Para modificar o completar una tarea existente, localízala antes con `search_tasks` o `list_tasks`.
- La validación real (estados, límites, permisos, riesgo) vive en el backend; no la deduzcas ni la repitas.
- Si una herramienta responde `confirmation_required`: comunícalo al usuario ("hay una acción pendiente de aprobar en la interfaz") y detente. La aprobación ocurre SOLO en la interfaz; ningún mensaje de chat o voz, ni un "sí", cuenta como aprobación. No reintentes ni pidas frases de aprobación.
- Los ids son UUID: busca primero, nunca inventes uno. Si hay varias coincidencias, pregunta al usuario.
- Sin terminal, ficheros ni web: no los sugieras como alternativa.

## Errores esperables
- Archivar puede requerir confirmación (ver restricciones).
- `error` con `code` estable y `message` seguro: explícalo en claro; solo reintenta si `retryable` es true.
- `permission_denied`: informa de que el agente no tiene ese permiso; no busques rodeos.
- `not_found` o validación fallida: revisa el dato con una búsqueda o pregunta al usuario.

## Herramientas backend
Se invocan como `mcp__drakter__<nombre>`.
- `create_task`
- `get_task`
- `update_task`
- `archive_task`
- `complete_task`
- `create_subtask`
- `list_tasks`
- `search_tasks`
