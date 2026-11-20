---
name: workspace-relationships
description: "Relaciones: conectar elementos del Workspace entre sí y consultar qué está relacionado con qué."
version: 2.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, relationships]
---

# workspace-relationships

## Herramientas
- Ver lo conectado a un elemento: `get_related_items` (entity_id; direction y relationship_type opcionales).
- Buscar relaciones: `search_relationships` (source_id, target_id, entity_type, relationship_type).
- Relacionar: `create_relationship` (source_id, target_id, relationship_type).
- Cambiar la nota de una relación: `update_relationship` (relationship_id, metadata). Solo sustituye `metadata`; para cambiar extremos o tipo, borra y crea.
- Quitar: `delete_relationship` (relationship_id). Pide confirmación en pantalla.
- Localizar los dos extremos: `search_workspace` o `search_all` (incluye almacén), o la búsqueda del dominio.

## Tipos
belongs_to, related_to, scheduled_for, uses_resource, depends_on, supports, studies, parent_of, references, derived_from. El backend decide cuáles valen para cada par de tipos.

## Orden típico
1. Busca los dos elementos y toma sus ids.
2. `create_relationship` con el tipo que mejor exprese la frase (apuntes de una asignatura → uses_resource; tarea de un proyecto → belongs_to; si dudas, related_to).
3. Para «qué hay sobre X»: busca X → `get_related_items`.

## Errores frecuentes
- `relationship_not_allowed`: ese tipo no vale para esos elementos; prueba related_to o explícalo.
- `conflict`: la relación ya existe.
- `hierarchy_cycle`: crearía un ciclo.
- Una tarea dentro de un proyecto se hace mejor con project_id de la tarea; una dependencia entre tareas, con `add_task_dependency`.

## Ejemplos
- «Relaciona el PDF de derivadas con Cálculo» → `search_resources` + `list_subjects` → `create_relationship` uses_resource.
- «¿Qué tengo relacionado con el TFG?» → `list_projects` → `get_related_items`.
- «Quita esa relación» → `get_related_items` → `delete_relationship` → pendiente de aprobar en la interfaz.
