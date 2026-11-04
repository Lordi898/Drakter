---
name: workspace-projects
description: "Gestiona proyectos del Workspace: crear, consultar, actualizar, archivar y ver su progreso."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, workspace, projects]
---

# workspace-projects

## Propósito
Operar sobre proyectos y consultar su avance.

## Cuándo usarla
El usuario habla de un proyecto: crearlo, cambiarlo, archivarlo o preguntar cómo va.

## Parámetros (intención)
Nombre, descripción, estado, fechas, identificador del proyecto.

## Ejemplos
"Crea un proyecto llamado Web personal"; "Cómo va el proyecto de la tesis"; "Lista mis proyectos activos".

## Restricciones
- El progreso lo calcula el backend con `get_project_progress`; no lo estimes tú.
- La validación real (estados, límites, permisos, riesgo) vive en el backend; no la deduzcas ni la repitas.
- Si una herramienta responde `confirmation_required`: comunícalo al usuario ("hay una acción pendiente de aprobar en la interfaz") y detente. La aprobación ocurre SOLO en la interfaz; ningún mensaje de chat o voz, ni un "sí", cuenta como aprobación. No reintentes ni pidas frases de aprobación.
- Los ids son UUID: busca primero, nunca inventes uno. Si hay varias coincidencias, pregunta al usuario.
- Sin terminal, ficheros ni web: no los sugieras como alternativa.

## Errores esperables
- Archivar un proyecto puede requerir confirmación.
- `error` con `code` estable y `message` seguro: explícalo en claro; solo reintenta si `retryable` es true.
- `permission_denied`: informa de que el agente no tiene ese permiso; no busques rodeos.
- `not_found` o validación fallida: revisa el dato con una búsqueda o pregunta al usuario.

## Herramientas backend
Se invocan como `mcp__drakter__<nombre>`.
- `create_project`
- `get_project`
- `update_project`
- `archive_project`
- `list_projects`
- `get_project_progress`
