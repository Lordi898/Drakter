---
name: workspace-relationships
description: "Gestiona relaciones entre elementos del Workspace (tareas, proyectos, recursos, asignaturas)."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, workspace, relationships]
---

# workspace-relationships

## Propósito
Vincular elementos entre sí y consultar qué está relacionado con qué.

## Cuándo usarla
El usuario quiere asociar o desasociar elementos, o ver lo vinculado a uno.

## Parámetros (intención)
Identificadores de origen y destino, tipo de relación, texto de búsqueda.

## Ejemplos
"Vincula esta tarea con el proyecto Web personal"; "Qué hay relacionado con Álgebra".

## Restricciones
- Localiza ambos extremos por id antes de relacionar.
- `delete_relationship` puede requerir confirmación.
- Qué tipos de relación son válidos lo decide el backend.
- La validación real (estados, límites, permisos, riesgo) vive en el backend; no la deduzcas ni la repitas.
- Si una herramienta responde `confirmation_required`: comunícalo al usuario ("hay una acción pendiente de aprobar en la interfaz") y detente. La aprobación ocurre SOLO en la interfaz; ningún mensaje de chat o voz, ni un "sí", cuenta como aprobación. No reintentes ni pidas frases de aprobación.
- Los ids son UUID: busca primero, nunca inventes uno. Si hay varias coincidencias, pregunta al usuario.
- Sin terminal, ficheros ni web: no los sugieras como alternativa.

## Errores esperables
- Relación duplicada, tipo no permitido o extremo inexistente: el backend lo rechaza; explícalo.
- `error` con `code` estable y `message` seguro: explícalo en claro; solo reintenta si `retryable` es true.
- `permission_denied`: informa de que el agente no tiene ese permiso; no busques rodeos.
- `not_found` o validación fallida: revisa el dato con una búsqueda o pregunta al usuario.

## Herramientas backend
Se invocan como `mcp__drakter__<nombre>`.
- `create_relationship`
- `delete_relationship`
- `get_related_items`
- `search_relationships`
