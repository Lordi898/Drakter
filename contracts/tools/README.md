# Catálogo canónico de herramientas del agente (v1)

`catalog.json` es una lista de `ToolManifest` (`contracts/python/drakter_contracts/tools.py`). Es la única lista de lo que Hermes puede llamar; se sirve por MCP en puerto propio. Hermes no toca la BD. Formato de `ToolSpec`: `backend/app/integrations/hermes/CONTRACT.md` §1 (drakter-16).

82 herramientas en el catálogo: 37 `read`, 36 `write`, 9 `confirm`. 78 construidas, 4 sin construir. Comprobado el 2026-11-13 contra el registro real (`TOOLS` de `backend/app/tools/*.py` en `drakter/integracion`): en las 78 coinciden `domain`, `permission`, `risk` y `returns_untrusted` (corregido `get_related_items`, que el código marca `returns_untrusted`). Las 4 de automejora están en el catálogo desde la decisión de cierre (ver «Automejora»), así que `registry._warn_catalog_drift` no emite ningún aviso `tool_catalog_drift`.

## Reglas aplicadas

- `permission` = `<dominio>.<accion>`: `read`, `write`, `delete` (solo `confirm` de borrado), `forget` (memoria).
- Todo `delete_*` es `confirm`. Archivar es `write`. Aprobar o rechazar confirmaciones no existe como herramienta: solo la GUI.
- `returns_untrusted: true` en lo que devuelve texto de documentos o memoria: `search_resources`, `get_resource`, `read_resource`, `list_folders`, `search_all`, `search_memory`, `get_memory_item`, `get_related_items` (devuelve títulos).
- `args_model` y `result_model` son clases reales en las construidas (`Page[TaskOut]` es la genérica real). En las sin construir son nombres propuestos.
- `phase`: fase del ROADMAP del módulo (8 tareas, 9 proyectos, 10 hábitos, 11 calendario, 12 asignaturas, 13 almacén, 14 relaciones, 15 etiquetas/sistema/búsqueda, 16 memoria, 17 voz).

## Fusiones y diferencias de nombres

- `get_memory_status` vive en dominio `memory` (permiso `memory.read`), no en `system`.
- `search_workspace` vive en dominio `search` (`search.read`), no en `system`.
- Los frentes añadieron herramientas fuera de la lista de partida, y se incluyen: `unarchive_task`, `unarchive_project`, `set_task_tags`, `add_task_dependency`, `remove_task_dependency`, `search_all`, `search_memory`, `get_memory_item`, `propose_memory`, `forget_memory`.
- `set_task_tags` (drakter-13) convive con `add_tag`/`remove_tag` (genéricas, ya construidas en `app/tools/tags.py`). El integrador decide si se retira `set_task_tags`.
- No hay `delete_project` ni `delete_habit` ni `delete_resource`: el borrado queda en la GUI (así lo dejó drakter-13, `projects.py:1`).
- Memoria: `propose_memory` deja el registro pendiente hasta que el usuario lo aprueba en la GUI. Automejora (decisión de cierre, 2026-11-13): el agente tiene cuatro herramientas en el catálogo y en `TOOL_DOMAINS` (`improvement`, fase 18): `record_improvement_feedback` y `create_improvement_proposal` (`improvement.write`, `confirm`), y `list_improvement_proposals` y `get_improvement_proposal` (`improvement.read`, `read`, `returns_untrusted`). No hay herramienta para evaluar, aprobar, aplicar ni revertir: eso solo ocurre en la GUI.

## Sin construir (4)

`get_voice_status`, `get_workspace_summary`, `get_activity_log`, `get_pending_confirmations`. Etiquetas (`list_tags`, `add_tag`, `remove_tag`) y relaciones (`create_relationship`, `delete_relationship`, `get_related_items`, `search_relationships`) ya están construidas.

`get_activity_log` solo lee una vista filtrada (sin secretos ni argumentos), nunca la tabla de auditoría cruda. `get_pending_confirmations` solo lista.

## Desviaciones

Seguridad:

1. ~~**drakter-15, `create_resource` con `url` arbitraria**~~ Resuelto: `create_resource` solo acepta `title`, `note_body`, `folder_id`, `description`, `tags` e `index_content`; los errores de enlace se ocultan al agente (`app/tools/storage.py:35`).
2. Verificado sin hallazgos: no hay en las herramientas construidas ninguna de aprobar o rechazar confirmaciones, gestionar `storage_locations`, cambiar permisos, tocar auditoría ni ejecutar comandos.

Consistencia de permisos (el catálogo ya lleva la forma correcta):

3. ~~`delete_event` y `delete_time_block` con `calendar.write`~~ Resuelto: `calendar.delete`.
4. ~~`delete_class_session` con `subjects.write`~~ Resuelto: `subjects.delete`.
5. **Sigue abierta.** `backend/app/tools/habits_calendar_toolspec.py:26-52` define un `ToolSpec` de reserva si falla el import de `app.tools.spec`. Corrección: retirarlo, porque `app/tools/spec.py` ya está integrado y así solo existe una definición.

Comprobado el 2026-11-13: se cargaron los módulos de `app/tools` y se comparó el registro con `catalog.json`; los argumentos de `create_resource` se leyeron del modelo real.
