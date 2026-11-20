# CHECKLISTS GENERALES DE IMPLEMENTACIÓN

Las siguientes listas son el control de trabajo del proyecto y la única lista viva de casillas. Se marcarán cuando la tarea esté implementada y funcione como se espera (`CLAUDE.md` §4). Lo bloqueado se anota con ⚠️. La equivalencia entre checklists, pasos del orden real y fases de cada plan está en `DECISIONS.md`.

> **Cierre 2026-11-13** (`drakter/integracion`): cada casilla se marcó a partir del informe de su finalizador o de la pasada integrada final (`scripts/verify-all.sh`, 44/44 sobre `183cc25`), con Claude Haiku 5.5 real donde dependía del modelo. `[x]` con ⚠️ = funciona, con una reserva anotada; `[ ]` con ⚠️ = bloqueado o a medias, con el motivo; `[ ]` sin nota = sin código (no se tocó). La Checklist 18 no entra en el cierre. Detalle operativo en `RUN_STATE.md`.

> **Voz v2 (2026-11-14, WP9):** las filas 3, 13 y 14 incluyen ya las casillas de «Jobs y streaming de voz», «Voz v2: trabajos y herramientas» y «Voz v2: Pipecat», marcadas con las cifras y comprobaciones de la integración (`DECISIONS.md` 2026-11-14).

| Checklist | Casillas | `[x]` | de ellas con ⚠️ | `[ ]` con ⚠️ | `[ ]` sin código |
|---|---|---|---|---|---|
| 0. Arquitectura y preparación | 14 | 14 | 0 | 0 | 0 |
| 1. Aplicación de escritorio | 13 | 13 | 0 | 0 | 0 |
| 2. Backend | 12 | 12 | 0 | 0 | 0 |
| 3. Hermes | 21 | 16 | 0 | 5 | 0 |
| 4. Personalidad y contexto | 17 | 17 | 0 | 0 | 0 |
| 5. Personaje | 19 | 16 | 16 | 3 | 0 |
| 6. Base de datos y relaciones | 18 | 18 | 0 | 0 | 0 |
| 7. Tareas y proyectos | 23 | 23 | 0 | 0 | 0 |
| 8. Hábitos | 12 | 12 | 1 | 0 | 0 |
| 9. Calendario y asignaturas | 18 | 18 | 0 | 0 | 0 |
| 10. Almacén e indexación | 25 | 25 | 1 | 0 | 0 |
| 11. Relaciones avanzadas | 14 | 13 | 0 | 1 | 0 |
| 12. Memoria | 22 | 20 | 4 | 0 | 2 |
| 13. Skills y herramientas | 19 | 9 | 2 | 10 | 0 |
| 14. Voz | 51 | 42 | 8 | 9 | 0 |
| 15. Automejora | 11 | 11 | 2 | 0 | 0 |
| 16. Seguridad y fiabilidad | 15 | 14 | 2 | 1 | 0 |
| 17. Optimización y lanzamiento | 17 | 3 | 1 | 6 | 8 |
| 18. Ampliaciones futuras | 10 | 0 | 0 | 0 | 10 |
| **Total 0–17** | **341** | **296** | **37** | **35** | **10** |

## Checklist 0. Arquitectura y preparación

- [x] Crear repositorio Drakter.
- [x] Configurar Git.
- [x] Crear estructura de carpetas (cada carpeta se crea cuando entra código).
- [x] Crear README.
- [x] Crear CHANGELOG.
- [x] Documentar arquitectura.
- [x] Documentar decisiones técnicas.
- [x] Definir convenciones.
- [x] Definir modelos de datos.
- [x] Definir API.
- [x] Definir eventos.
- [x] Definir permisos.
- [x] Definir configuración.
- [x] Preparar entorno de desarrollo.

## Checklist 1. Aplicación de escritorio

- [x] Configurar Electron.
- [x] Configurar React.
- [x] Configurar TypeScript.
- [x] Configurar Tailwind.
- [x] Configurar shadcn/ui.
- [x] Crear ventana principal.
- [x] Crear navegación lateral.
- [x] Crear área central.
- [x] Crear panel contextual.
- [x] Crear notificaciones.
- [x] Crear configuración.
- [x] Crear gestión de errores.
- [x] Configurar empaquetado.
  Nota: con esta configuración drakter-50 generó el AppImage; lo pendiente del `.deb` está en la Checklist 17 «Crear instalador».

## Checklist 2. Backend

- [x] Crear FastAPI.
- [x] Configurar SQLite.
- [x] Configurar migraciones.
- [x] Crear API REST.
- [x] Crear WebSocket.
- [x] Crear servicios.
- [x] Crear repositorios.
- [x] Crear esquemas.
- [x] Crear validaciones.
- [x] Crear logs.
- [x] Crear gestión de errores.
- [x] Crear sistema de permisos.

## Checklist 3. Hermes

- [x] Instalar Hermes.
- [x] Configurar Claude Haiku 5.5.
  Nota: comprobado con Claude Haiku 5.5 real a través de Hermes (`informes/hermes.md`, «Recomprobación con modelo real»; de apoyo, `informes/relaciones.md`, 3 turnos reales por Hermes).
- [x] Configurar credenciales.
- [x] Conectar Hermes con backend.
- [x] Crear adaptador.
- [x] Crear sesiones.
- [x] Crear envío de mensajes.
- [x] Crear recepción de respuestas.
- [x] Crear eventos de agente.
- [x] Crear gestión de desconexiones.
- [ ] Crear primera Skill.
  ⚠️ (d) Las Skills existen y son coherentes con las herramientas reales, pero Hermes no las carga: `home.py` desactiva el toolset `skills` porque arrastra `skill_manage` (H-06/F14). Ver `DECISIONS.md` «Skills de agent/ inertes en Hermes».
- [x] Probar conversación completa.
  Nota: comprobado con Claude Haiku 5.5 real a través de Hermes (`informes/hermes.md`, «Recomprobación con modelo real»; de apoyo, `informes/relaciones.md`, 3 turnos reales por Hermes).

### Jobs y streaming de voz

- [x] `TurnTap` no bloqueante (con `on_steered`) y prefijos de turno no persistidos en `AgentRuntime`
- [x] Op `steer` en el runner (`redirect`, `pending_steer`) y filtro previo en la política de voz
- [ ] `reasoning_effort` por carril (low en primer plano, medium en trabajadores) y hash de instructions estable
  ⚠️ No consta verificado en la integración (WP9); falta comprobarlo.
- [x] `Lane` y home `hermes-w1` con token y guard proof propios
- [x] `JobManager`, tabla `jobs` y migración 0014 probada sobre una copia
- [ ] Eventos `job.*`, REST `/jobs` y JobsList en el panel
  ⚠️ Solo se comprobó la notificación de fin; JobsList en el panel requiere la UI y no se observó.
- [x] Aviso de fin de trabajo (notificación, frase en silencio y resumen no confiable en el prefijo)
- [ ] Confirmación de trabajo en pantalla; el trabajo termina con `pending_actions`
  ⚠️ No probado: trabajo con confirmación pendiente → `pending_actions>0`.
- [ ] RSS del runner trabajador medido; decisión sobre N=2
  ⚠️ RSS de Hermes w1 medido (~188 MB); falta la decisión sobre N=2.

## Checklist 4. Personalidad y contexto

- [x] Crear SOUL.md.
- [x] Crear PERSONALITY.md.
- [x] Crear BEHAVIOR.md.
- [x] Crear COMMUNICATION.md.
- [x] Crear EMOTIONAL_STYLE.md.
- [x] Crear VALUES.md.
- [x] Crear USER.md.
- [x] Crear ENVIRONMENT.md.
- [x] Crear PREFERENCES.md.
- [x] Crear CURRENT_CONTEXT.md.
- [x] Crear CAPABILITIES.md.
- [x] Crear WORKSPACE_GUIDE.md.
- [x] Crear TOOL_GUIDE.md.
- [x] Crear SYSTEM_GUIDE.md.
- [x] Configurar carga de contexto.
- [x] Configurar prioridades.
- [x] Probar consistencia de personalidad.
  Nota: matices de estilo con Haiku 5.5 (a veces supera max_sentences; muletilla de apertura) y rúbricas de evals pendientes de lectura humana: se tratarán en el rediseño de personalidad, fuera de este cierre.

## Checklist 5. Personaje

- [x] Diseñar identidad visual.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Diseñar ojos.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Diseñar boca.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Diseñar expresiones.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [ ] Crear proyecto Rive.
  ⚠️ Se ve el personaje sustituto (SVG) en la pantalla Drakter; el `.riv` real sigue pendiente.
  ⚠️ El `.riv` se diseña a mano en el editor de Rive. Por código solo se cubre el personaje provisional; las casillas de estados, transiciones e integración dependen de ese archivo hasta que el usuario lo entregue.
- [x] Crear estado idle.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Crear estado listening.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Crear estado thinking.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Crear estado speaking.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Crear estado executing.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Crear estado success.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Crear estado error.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Crear estado interrupted.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Crear estado offline.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Crear transiciones.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).
- [x] Integrar Rive con React.
  ⚠️ `RiveCharacter` (`@rive-app/canvas` 2.53.0) y `AdaptiveCharacter` están listos: cargan el `.riv` del usuario, mapean `state` y `mouthOpen` a la state machine `Drakter` y, si no hay archivo o falla, usan el SVG (probado el respaldo con un archivo inválido). NO probado con un `.riv` real: no existe hasta que el usuario lo diseñe (ver `docs/usage/personaje.md`).
- [x] Crear sistema de eventos visuales.
  ⚠️ Provisional SVG. Cadena `agent.status_changed` → `protocol.ts` → `stores/agent.ts` → `CharacterSlot` comprobada por typecheck, lectura y render por estado. Falta el e2e `desktop.personaje` en Electron (hoy NO COMPROBADO: Electron no arranca por CDP en la pasada y la conversación da 503). `agent.expression_changed` se valida pero el SVG la ignora y el backend no la emite.
- [x] Implementar sincronización labial.
  ⚠️ Hecho en el personaje provisional SVG (nivel real del audio vía `AnalyserNode`); en el `.riv` llega por el input `mouthOpen`, sin probar con un `.riv` real.
- [x] Probar animaciones.
  ⚠️ Hecho en el personaje provisional SVG; la versión `.riv` sigue pendiente (ver «Crear proyecto Rive»).

## Checklist 6. Base de datos y relaciones

- [x] Crear esquema SQLite.
- [x] Crear tabla de tareas.
- [x] Crear tabla de proyectos.
- [x] Crear tabla de hábitos.
- [x] Crear tabla de registros de hábitos.
- [x] Crear tabla de eventos.
- [x] Crear tabla de bloques de tiempo.
- [x] Crear tabla de asignaturas.
- [x] Crear tabla de sesiones de clase.
- [x] Crear tabla de recursos.
- [x] Crear tabla de carpetas.
- [x] Crear tabla de etiquetas.
- [x] Crear tabla de relaciones.
- [x] Crear tabla de auditoría.
- [x] Crear identificadores UUID.
- [x] Crear integridad referencial.
- [x] Crear migraciones.
- [x] Probar persistencia.

## Checklist 7. Tareas y proyectos

- [x] Crear interfaz de tareas.
- [x] Crear tareas.
- [x] Editar tareas.
- [x] Eliminar tareas.
- [x] Completar tareas.
- [x] Reabrir tareas.
- [x] Crear subtareas.
- [x] Crear subtareas anidadas.
- [x] Crear estados.
- [x] Crear prioridades.
- [x] Crear fechas límite.
- [x] Crear etiquetas.
- [x] Crear dependencias.
- [x] Crear interfaz de proyectos.
- [x] Crear proyectos.
- [x] Editar proyectos.
- [x] Archivar proyectos.
- [x] Asociar tareas a proyectos.
- [x] Mostrar progreso.
- [x] Crear historial.
- [x] Crear herramientas Hermes.
- [x] Probar operaciones desde GUI.
- [x] Probar operaciones desde Drakter.

## Checklist 8. Hábitos

- [x] Crear interfaz.
- [x] Crear hábitos.
- [x] Editar hábitos.
- [x] Definir frecuencia.
- [x] Definir días.
- [x] Definir recordatorios.
- [x] Registrar cumplimiento.
- [x] Consultar historial.
- [x] Calcular estadísticas.
- [x] Asociar hábitos con objetivos.
- [x] Crear herramientas Hermes.
  ⚠️ Las 8 herramientas se registran sin deriva del catálogo y sus handlers responden con el actor `agent`; sin clave, no se han probado desde una conversación real.
- [x] Probar persistencia.

## Checklist 9. Calendario y asignaturas

- [x] Crear interfaz de calendario.
- [x] Crear vista diaria.
- [x] Crear vista semanal.
- [x] Crear vista mensual.
- [x] Crear eventos.
- [x] Editar eventos.
- [x] Eliminar eventos.
- [x] Crear bloques de tiempo.
- [x] Asociar bloques a tareas.
- [x] Detectar solapamientos.
- [x] Gestionar zonas horarias.
- [x] Crear asignaturas.
- [x] Crear horarios recurrentes.
- [x] Crear sesiones de clase.
- [x] Asociar recursos.
- [x] Asociar tareas.
- [x] Crear herramientas Hermes.
- [x] Probar recurrencias y fechas.

## Checklist 10. Almacén e indexación

- [x] Crear interfaz del almacén.
- [x] Crear catálogo de recursos.
- [x] Crear carpetas.
- [x] Crear metadatos.
- [x] Crear descripciones opcionales.
- [x] Crear etiquetas.
- [x] Crear registro de rutas.
- [x] Crear índice FTS5.
- [x] Indexar nombres.
- [x] Indexar tipos.
- [x] Indexar descripciones.
- [x] Indexar rutas y metadatos.
- [x] Indexar texto extraído, de forma opcional.
- [x] Implementar búsqueda.
- [x] Implementar actualización del índice.
- [x] Detectar archivos ausentes.
- [x] Implementar lectura bajo demanda.
- [x] Implementar lectores PDF.
- [x] Implementar lectores de texto.
- [x] Implementar lectores de imágenes mediante metadatos.
- [x] Implementar lectura de enlaces.
- [x] Implementar límites de comprimidos.
- [x] Implementar permisos.
- [x] Crear herramientas Hermes.
  ⚠️ Las 8 herramientas se registran sin deriva del catálogo y funcionan por `ToolRegistry.dispatch`; no se ha probado una conversación real con ellas.
- [x] Probar formatos y errores.

## Checklist 11. Relaciones avanzadas

- [x] Crear servicio de relaciones.
- [x] Crear tipos de relación.
- [x] Crear validaciones.
- [x] Crear relaciones entre tareas y proyectos.
- [x] Crear relaciones entre tareas y asignaturas.
- [x] Crear relaciones entre tareas y recursos.
- [x] Crear relaciones entre tareas y calendario.
- [x] Crear relaciones entre proyectos y recursos.
- [x] Crear relaciones entre asignaturas y recursos.
- [x] Crear consulta inversa.
- [x] Crear consulta de elementos relacionados.
- [x] Crear visualización de relaciones.
  Nota: vista en Electron real con backend (drakter-48): lista con filtros, panel con grafo SVG y relaciones salientes, sin errores de consola. Detalles menores: la lista muestra tipo + ID corto en vez del título, y el panel contextual del shell sigue en «Nada seleccionado».
- [ ] Crear herramientas Hermes.
  ⚠️ Con Claude Haiku 5.5 real por Hermes, leer, buscar y crear relaciones funcionan (`create_relationship`, `get_related_items`). `delete_relationship` se denegaba porque el runtime no usaba la puerta real; desde `b722aca` debería crear la confirmación pendiente, pero no se ha recomprobado con el modelo.
- [x] Probar integridad y eliminación.

## Checklist 12. Memoria

- [x] Definir cuatro capas de memoria.
- [x] Crear configuración e integración de `memory/` (sin recuerdos ni datos personales).
- [x] Crear Memory Adapter.
- [x] Implementar la memoria SQLite + FTS5 tras el Memory Adapter.
  ⚠️ OpenViking queda desactivado en v1 (entrada "Memoria v1 en SQLite + FTS5; OpenViking desactivado" de `DECISIONS.md`); desviación pendiente de confirmar por el usuario (U-1).
- [ ] Configurar capas L0/L1/L2 (futuro, con OpenViking).
- [ ] Elegir embedding multilingüe (futuro, con OpenViking).
- [x] Implementar y comprobar la extracción de recuerdos en el Memory Adapter.
  ⚠️ Funciona (`RuleExtractor` vía `MemoryService.extract_from_turn`), pero aún nadie la invoca tras un turno de chat (ver recuperación selectiva).
- [x] Implementar y comprobar la clasificación en el Memory Adapter.
- [x] Implementar y comprobar la deduplicación en el Memory Adapter.
- [x] Implementar y comprobar la detección de contradicciones en el Memory Adapter.
- [x] Configurar y comprobar la memoria de trabajo en Hermes y OpenViking.
  ⚠️ En Hermes funciona: con Claude Haiku 5.5 real el turno 2 recuerda el turno 1 (sesión de Hermes, `persist=True`). La parte de OpenViking sigue desactivada (U-1); ningún código escribe `DRAKTER_DATA_DIR/memory/working/`.
- [x] Implementar y comprobar la memoria episódica en el Memory Adapter.
- [x] Implementar y comprobar la memoria semántica en el Memory Adapter.
- [x] Implementar y comprobar la memoria procedimental en el Memory Adapter.
- [x] Configurar y comprobar la recuperación selectiva.
- [x] Configurar y comprobar los límites de contexto.
- [x] Configurar y comprobar los registros de memoria.
- [x] Crear Skill de memoria.
  ⚠️ El archivo existe y cita las herramientas reales, pero Hermes no carga las Skills (toolset `skills` apagado por `skill_manage`), como las de la Checklist 13.
- [x] Probar persistencia.
- [x] Probar recuperación.
- [x] Probar recuerdos contradictorios.
- [x] Probar información obsoleta.

## Checklist 13. Skills y herramientas

- [x] Crear estructura de Skills.
- [ ] Crear Skill de tareas.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`b8086ce`).
- [ ] Crear Skill de proyectos.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`b8086ce`).
- [ ] Crear Skill de hábitos.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`b8086ce`).
- [ ] Crear Skill de calendario.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`b8086ce`).
- [ ] Crear Skill de asignaturas.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`b8086ce`).
- [ ] Crear Skill de almacén.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`b8086ce`).
- [ ] Crear Skill de relaciones.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`b8086ce`).
- [ ] Crear Skill de configuración.
  ⚠️ El archivo existe, pero sus herramientas (`get_configuration`, `propose_configuration_change`) son PROPUESTA y no existen ni en el catálogo ni en el backend. Además está inerte.
- [x] Definir parámetros.
- [x] Definir permisos.
  Nota: con el modelo real (prueba de relaciones de drakter-41), el agente llamó por iniciativa propia a create/list/get_improvement_proposal y record_improvement_feedback sin que se le pidiera. Es seguro (las escrituras exigen confirmación), pero hay que revisar las descripciones de esas herramientas o las instrucciones de cuándo proponer mejoras; se deja para el rediseño de la personalidad y la conversación.
- [x] Definir confirmaciones.
- [x] Definir errores.
  ⚠️ 6 herramientas de lectura no declaran `errors` (`get_memory_status`, `search_relationships`, `list_subjects`, `get_timetable`, `get_agent_status`, `get_system_status`).
- [x] Probar selección de herramientas.
- [x] Probar operaciones encadenadas.

### Voz v2: trabajos y herramientas

- [x] `jobs_start`, `jobs_status`, `jobs_amend`, `jobs_cancel` con esquema, permisos (`jobs.read`, `jobs.write`), catálogo, auditoría y errores
  ⚠️ `jobs_amend` no probado con un trabajo en marcha (el de prueba acabó en ~7 s).
- [ ] `ToolContext.job_id` y `confirmation.requested.job_id`
  ⚠️ No probado: trabajo con confirmación pendiente.
- [x] Eval `agent/evals/jobs_routing.jsonl` (20-30 frases) superada
- [ ] `voice_list_profiles` y `voice_set_profile` siguen funcionando con el pipeline nuevo
  ⚠️ Cambio de voz en caliente entre turnos: no probado.

## Checklist 14. Voz

- [x] Instalar openWakeWord.
- [x] Configurar palabra de activación.
  ⚠️ «Hey Jarvis» (openWakeWord 0,92-1,00 con voz inglesa sintética; con voz castellana sintética no detecta). Pendiente con la voz real del usuario.
- [x] Instalar Silero VAD.
- [x] Configurar detección de voz.
- [x] Instalar Faster-Whisper.
- [x] Probar modelo small.
- [x] Medir latencia.
  ⚠️ Medición lista y ejecutada (`voice/tests/bench_engines.py`, evento `voice.metrics`), pero con la máquina muy cargada (loadavg 9–14): STT small RTF 0,82–1,02; Kokoro primer audio 398–1 282 ms. Hay que repetirla con la máquina en reposo antes de dar cifras de producto.
- [x] Evaluar modelo medium.
- [x] Instalar Kokoro.
- [ ] Instalar Piper.
  ↪ Reemplazado por «Voz v2: Pipecat» (DECISIONS 2026-11-13, V-01 a V-38).
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
  ⚠️ `PiperTTS` y `FallbackTTS` existen (proceso externo, venv propio), pero no se instaló `piper-tts` ni se probó.
- [x] Crear Voice Manager.
- [x] Crear Voice Personality Engine.
- [x] Crear reproducción de audio.
- [x] Crear interrupciones.
- [x] Crear cancelación de audio.
- [x] Sincronizar boca.
  ↪ Reemplazado por «Voz v2: Pipecat» (DECISIONS 2026-11-13, V-01 a V-38).
  Nivel medido en el renderer sobre la pista remota de WebRTC (`voice/outputLevel.ts`), sin depender de eventos del backend. Comprobado en Electron sin pantalla con un bucle WebRTC real: boca en movimiento con audio y quieta en silencio.
  ⚠️ No observado con la voz real de Fish Audio en la app completa.
  ⚠️ Personaje: secuencia listening→thinking→speaking→idle no observada visualmente en WP9.
- [x] Crear gestión de errores.
- [x] Probar conversación por voz completa.
  ⚠️ Conversación por voz verificada en la app integrada (WP9) con frases sintéticas; calidad y volumen a oído, pendientes del usuario.

### Voz v2: Pipecat

- [x] Venv de voz py3.12 con `pipecat-ai[webrtc,fish,kokoro]==1.16.0`, `drakter_contracts`, lock fijado e `install-voice.sh`
- [x] Modelos locales en `~/.local/share/drakter/models/`, sin descargas en ejecución (Kokoro incluido)
- [x] Transporte WebRTC renderer ↔ `SmallWebRTCTransport`, sin STUN, con señalización por main y data channel con ping
- [ ] ICE por loopback (127.0.0.1) probado sin red y con cambio de red
  ⚠️ Sin red y cambio wifi→ethernet no probados en WP9 (cortaría la sesión del integrador); WP8a midió 347 ms sin red.
- [x] Un pipeline por conexión, con modelos cargados una vez por proceso
- [x] STT Moonshine streaming en castellano (small, con tiny de respaldo) con `finalized`
- [x] VAD Silero y fin de turno Smart Turn v3.2, con un único `UserTurnProcessor`
- [x] Puente `BackendBridgeProcessor` e IPC v2 con `speech_id`
- [x] Hablar mientras genera (deltas → frases → Fish)
- [x] Fish `s2.1-pro-free` con guard de modelo y corte por fecha (30-11-2026)
- [ ] Perfiles de voz en caliente entre turnos (`TTSUpdateSettingsFrame(service=…)`)
  ⚠️ Cambio de voz en caliente entre turnos: no probado.
- [x] Respaldo Kokoro con conmutación propia y aviso único
  ⚠️ Tras conmutar a Kokoro no vuelve a Fish hasta reiniciar el proceso de voz.
- [x] Caché de frases (`voice_phrases.es.toml`, `TTSAudioRawFrame`) y CLI `voice phrases`
  ⚠️ El usuario debe ejecutar `python -m voice phrases` con su perfil antes del 30-11-2026.
- [x] Etiquetas de lista cerrada: se hablan y nunca llegan al chat, la BD ni la auditoría (deltas y texto terminal)
- [ ] Texto por proveedor (`text_transforms`) y guard de bloques de código, tablas y URL
  ⚠️ No consta verificado en WP9.
- [x] Barge-in con ducking y decisión por transcripción; cero falsas interrupciones en 60 s de TTS
  ⚠️ Con el bucle acústico débil de este portátil; falta con la voz del usuario y altavoces a volumen alto.
- [x] Asentimientos y eco ignorados; falso ducking restaurado y contado
- [x] Capa 0 en datos: para, calla, descansa y cierre, también con el bot callado
- [x] Modo conversación con ventana de seguimiento y gestión del silencio, con dueño único (`Ctl.set_mode`)
- [x] Palabra «Jarvis» (openWakeWord 0.4.0 más confirmación textual en el puente) con la orden en la misma frase
  ⚠️ Con voz castellana sintética openWakeWord no detecta; falta la voz real del usuario y un falso positivo real.
- [x] Super+J por atajo de GNOME y `drakter activate`, con la latencia medida
- [x] Lo oído (`heard_tail`, `pending_head`) y reanudación («siga»)
- [x] Acuses y frases de herramienta condicionales
- [x] `StatusArbiter` como productor único; `/agent/status` lo lee
- [x] Voz y chat comparten sesión (`current_session`, `chat.user_message`, `input_source`)
- [ ] Icono de altavoz (`voice_tts_enabled`, punto único de silencio) e indicador de micrófono calculado en el renderer
  ⚠️ Requiere la UI; no verificado en WP9.
- [ ] Tope de lectura en turnos escritos (`rest_on_screen`)
  ⚠️ Requiere la UI; no verificado en WP9.
- [ ] Propagación de ajustes (`add_setting_listener`)
  ⚠️ No consta verificado en WP9.
- [ ] Bandeja y escucha con la ventana oculta
  ⚠️ No verificado en WP9 (escucha con la ventana oculta).
- [x] Confirmaciones nunca por voz (comprobación puntual)
- [x] Métricas por turno en `metrics.jsonl`; umbrales calibrados con cifras medidas
  ⚠️ Umbrales sin cambios (los datos no justifican moverlos); calibración fina pendiente con la voz real del usuario.
- [x] `VOICE.md` (brevedad, usted, identidad «con qué funciona»)
- [x] Calidad de la voz tras la prueba del usuario (2026-11-20): STT en la nube (Deepgram/Groq) con respaldo Moonshine, volcado de audio opcional, fin de turno con umbral y regla de texto, activación difusa, sin respuestas solapadas y acuse cortable (la identidad en voz va en el PR #17)
  ⚠️ Groq solo probado con clave falsa (conmuta a Moonshine); no hay clave real. Todo con voz sintética: falta repetirlo con la voz del usuario (`DRAKTER_VOICE_DUMP_AUDIO=1` para diagnosticar).
- [x] Eventos `voice.*` antiguos eliminados del contrato; `/tmp/dr-at` borrado
- Aplazado (sin casilla activa): «Drakter» y «despierta», dictado, subtítulos, emoción, avisos de calendario, transporte A

## Checklist 15. Automejora

- [x] Crear registro de feedback.
- [x] Crear clasificación de incidencias.
- [x] Crear propuestas.
- [x] Crear evaluaciones.
- [x] Crear entorno de pruebas.
- [x] Crear flujo de aprobación.
  ⚠️ En el backend funciona por `ActionService` (`approval-request`/`revert-request` → 409 → `/api/v1/confirmations/{id}/approve`, 300 s, ligado al digest, de un solo uso y auditado; el agente recibe DENY). No hay pantalla de automejora en `desktop/src/modules/`.
- [x] Integrar Git.
- [x] Crear historial de cambios.
- [x] Crear informes.
- [x] Impedir cambios no autorizados.
- [x] Probar recuperación de cambios.
  ⚠️ `revert` funciona y `recover_interrupted` se llama al arrancar (`a1f2b88`). Falta registrar `invalidate_after_restore` como hook de restauración de copias (módulo de copias).

## Checklist 16. Seguridad y fiabilidad

- [x] Crear permisos por módulo.
- [x] Crear permisos por operación.
- [x] Crear confirmaciones.
- [x] Proteger credenciales.
- [x] Validar rutas.
- [x] Limitar acceso a archivos.
- [x] Proteger operaciones destructivas.
  ⚠️ Brechas de diseño del red-team que siguen abiertas: CONF-46/INJ-26 (la contaminación no persiste al reiniciar), INJ-11/25 (`TurnRequest` sin canal de datos; mitigado por la propagación de tainted, `df258b1`, `1588c04`). Ver `DECISIONS.md` «Brechas del red-team conocidas al cierre».
- [x] Crear auditoría.
- [x] Crear copias de seguridad.
- [x] Probar restauración.
- [ ] Probar desconexiones.
  ⚠️ Backend↔Hermes comprobado (el runner muere y se reconecta solo). La reconexión del WebSocket del escritorio (`eventsBridge.ts`) no se ha observado aislada.
- [x] Probar recuperación del backend.
- [x] Probar recuperación de Hermes.
- [x] Probar errores de memoria.
- [x] Revisar datos sensibles.
  ⚠️ Brechas de diseño abiertas: FILE-DB-02 (TOCTOU en `connect`, riesgo bajo) e INJ-05 (título y URL de `read_resource` fuera del sobre).

## Checklist 17. Optimización y lanzamiento

- [ ] Medir consumo de RAM.
- [ ] Medir CPU.
- [ ] Medir uso de CPU y RAM (no hay VRAM dedicada).
- [ ] Medir latencia de STT.
  ⚠️ Método listo (`voice/metrics.py`, `voice/tests/bench_engines.py --wav`). La única medición (informe de voz: Whisper small, RTF 0,82–1,02) se tomó con la máquina muy cargada; hay que repetirla en reposo. Voz congelada a la espera de Pipecat.
- [ ] Medir latencia de TTS.
  ⚠️ Método listo (`voice/tests/bench_engines.py --tts kokoro`). La única medición (informe de voz: Kokoro, primer audio 398–1 282 ms) se tomó con la máquina muy cargada; hay que repetirla en reposo. Voz congelada a la espera de Pipecat.
- [ ] Medir latencia de Hermes.
  ⚠️ No hay instrumentación de latencia de Hermes (las marcas de `voice/metrics.py` solo cubren la voz); no se crea en este cierre.
- [ ] Optimizar consultas SQLite.
- [x] Optimizar FTS5.
  ⚠️ Comprobado en la búsqueda global: índice de prefijos `prefix='2 3'`, pesos bm25 por columna y `reconcile_structured` con atajo sin cambios. Con 5.000 tareas sintéticas: reconcile inicial 0,95 s, sin cambios 18 ms, consultas de caso peor 190–460 ms. El FTS del almacén se cubre en la Checklist 10.
- [ ] Optimizar recuperación de memoria.
- [ ] Optimizar carga de interfaz.
- [ ] Crear instalador.
  ⚠️ Configuración y build funcionan: PyInstaller (backend congelado de 45 MB, arreglado en `39503a7` porque respondía 404 en todas las rutas), AppImage (~150 MB, con el backend corregido) y `.deb` revisado (sandbox SUID, perfil AppArmor, fuses, sin secretos). Pero el `.deb` no se ha regenerado tras el arreglo (`fpm` falló con `/tmp` lleno), no se ha instalado (requiere sudo) ni se ha abierto la ventana empaquetada sin `--no-sandbox`. Faltan icono propio, `desktopName` y `electron-builder` en `desktop/package.json` (hoy por `npx`). Windows sin probar.
- [ ] Crear actualización de aplicación.
- [x] Crear documentación de instalación.
- [ ] Crear documentación de uso.
  ⚠️ Las 14 guías de `docs/usage/` tienen la cabecera de estado comprobada contra el código (`276cc11`), pero las notas «Pendiente» del cuerpo no se han revisado una a una y nadie las ha seguido paso a paso en la app.
- [ ] Crear versión estable.
- [ ] Crear copia de seguridad inicial.
  ⚠️ El mecanismo funciona (`python -m app.database.cli migrate|backup|status|restore`, copias 600 con `.sha256`), pero una instalación nueva no hace copia inicial automática y no se ha copiado la base real del usuario (el protocolo prohíbe tocar `~/.local/share/drakter`). En la app instalada se hace desde Configuración → Copias de seguridad.
- [x] Realizar pruebas de aceptación.
  Nota: pasada integrada final `scripts/verify-all.sh` sobre `drakter/integracion@183cc25`: 44/44 comprobaciones PASA, 0 FALLA (backend, módulos, confirmaciones, copia y restauración, conversación, escritorio con Electron real y parada limpia). La conversación de esa pasada usa el stub; el modelo real se probó en los informes de Hermes, evals, tareas y relaciones. No cubre el sandbox real de Electron ni el paquete instalado (ver «Crear instalador»).

## Checklist 18. Ampliaciones futuras

- [ ] Evaluar LiveKit Agents.
- [ ] Implementar streaming de voz avanzado.
- [ ] Evaluar PostgreSQL.
- [ ] Evaluar sincronización entre dispositivos.
- [ ] Evaluar aplicación móvil.
- [ ] Integrar Home Assistant.
- [ ] Incorporar control de dispositivos.
- [ ] Crear monitorización avanzada.
- [ ] Ampliar capacidades multimodales.
- [ ] Ampliar automatizaciones.
