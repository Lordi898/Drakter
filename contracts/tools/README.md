# Catálogo canónico de herramientas del agente (v1)

`catalog.json` es una lista de `ToolManifest` (`contracts/python/drakter_contracts/tools.py`). Es la única lista de lo que Hermes puede llamar; se sirve por MCP en puerto propio. Hermes no toca la BD. Formato de `ToolSpec`: `backend/app/integrations/hermes/CONTRACT.md` §1 (drakter-16).

78 herramientas: 35 `read`, 36 `write`, 7 `confirm`. 67 construidas, 11 sin construir. Los datos de las construidas se extrajeron de `backend/app/tools/*.py` de los frentes drakter-13, 14, 15, 16, 18 y 27, solo leyendo.

## Reglas aplicadas

- `permission` = `<dominio>.<accion>`: `read`, `write`, `delete` (solo `confirm` de borrado), `forget` (memoria).
- Todo `delete_*` es `confirm`. Archivar es `write`. Aprobar o rechazar confirmaciones no existe como herramienta: solo la GUI.
- `returns_untrusted: true` en lo que devuelve texto de documentos o memoria: `search_resources`, `get_resource`, `read_resource`, `list_folders`, `search_all`, `search_memory`, `get_memory_item`.
- `args_model` y `result_model` son clases reales en las construidas (`Page[TaskOut]` es la genérica real). En las sin construir son nombres propuestos.
- `phase`: fase del ROADMAP del módulo (8 tareas, 9 proyectos, 10 hábitos, 11 calendario, 12 asignaturas, 13 almacén, 14 relaciones, 15 etiquetas/sistema/búsqueda, 16 memoria, 17 voz).

## Fusiones y diferencias de nombres

- `get_memory_status` vive en dominio `memory` (permiso `memory.read`), no en `system`.
- `search_workspace` vive en dominio `search` (`search.read`), no en `system`.
- Los frentes añadieron herramientas fuera de la lista de partida, y se incluyen: `unarchive_task`, `unarchive_project`, `set_task_tags`, `add_task_dependency`, `remove_task_dependency`, `search_all`, `search_memory`, `get_memory_item`, `propose_memory`, `forget_memory`.
- `set_task_tags` (drakter-13) convive con `add_tag`/`remove_tag` (genéricas, sin construir). Cuando existan, el integrador decide si se retira `set_task_tags`.
- No hay `delete_project` ni `delete_habit` ni `delete_resource`: el borrado queda en la GUI (así lo dejó drakter-13, `projects.py:1`).
- Memoria: `propose_memory` deja el registro pendiente hasta que el usuario lo aprueba en la GUI. Automejora: ninguna herramienta (Fase 18 no expone nada al agente).

## Sin construir (11)

`list_tags`, `add_tag`, `remove_tag`; `create_relationship`, `delete_relationship`, `get_related_items`, `search_relationships`; `get_voice_status`, `get_workspace_summary`, `get_activity_log`, `get_pending_confirmations`.

`get_activity_log` solo lee una vista filtrada (sin secretos ni argumentos), nunca la tabla de auditoría cruda. `get_pending_confirmations` solo lista.

## Desviaciones

Seguridad:

1. **drakter-15, `backend/app/tools/storage.py:120-130` y `:257-266` (`create_resource`)**: acepta `url` arbitraria (hasta 2048 caracteres). Con `index_resource` (`:279-290`) y `read_resource` (`:235-247`), el backend baja el contenido de esa URL (`services/readers/link.py`). Es ingerir URLs arbitrarias por iniciativa del agente. Corrección: `create_resource` solo con `note_body`; los enlaces los registra la GUI, y `read_resource`/`index_resource` solo descargan enlaces ya registrados por el usuario, nunca lo que el agente haya pasado. Quitar `url_not_allowed` y `link_fetch_failed` de los errores del agente. El catálogo mantiene el modelo real hasta que se corrija.
2. Verificado sin hallazgos: no hay en las herramientas construidas ninguna de aprobar o rechazar confirmaciones, gestionar `storage_locations`, cambiar permisos, tocar auditoría ni ejecutar comandos.

Consistencia de permisos (el catálogo ya lleva la forma correcta):

3. **drakter-14, `backend/app/tools/calendar.py:197` (`delete_event`) y `:267` (`delete_time_block`)**: `permission="calendar.write"` con riesgo `confirm`. Corrección: `calendar.delete`.
4. **drakter-14, `backend/app/tools/subjects.py:232` (`delete_class_session`)**: `subjects.write` con `confirm`. Corrección: `subjects.delete`. Así quien conceda `*.write` no concede borrar.
5. **drakter-16 / drakter-14**: `habits_calendar_toolspec.py` define un `ToolSpec` propio de reserva si falla el import de `app.tools.spec`. Corrección: retirarlo cuando drakter-16 esté integrado, para que solo exista una definición.

NO COMPROBADO: nada de lo anterior se ha ejecutado en los frentes; todo viene de lectura estática. Los worktrees drakter-12, 19, 20 y 26 no tienen `app/tools`.
