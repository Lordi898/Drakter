# CHECKLISTS GENERALES DE IMPLEMENTACIÓN

Las siguientes listas son el control de trabajo del proyecto y la única lista viva de casillas. Se marcarán cuando la tarea esté implementada y funcione como se espera (`CLAUDE.md` §4). Lo bloqueado se anota con ⚠️. La equivalencia entre checklists, pasos del orden real y fases de cada plan está en `DECISIONS.md`.

> **Pasada integrada 2026-11-13** (`drakter/integracion`): solo se marca lo visto funcionar en la app arrancada (Electron + backend + Hermes con el stub). Detalle en `RUN_STATE.md`.

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
- [ ] Crear notificaciones.
- [x] Crear configuración.
- [x] Crear gestión de errores.
- [ ] Configurar empaquetado.

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
- [ ] Configurar Claude Haiku 5.5.
  ⚠️ 2026-11-13: la `ANTHROPIC_API_KEY` de `~/.config/drakter/.env` da 401 `invalid x-api-key` (también en llamada directa a la API). Sin clave válida no hay prueba con el modelo real.
  ⚠️ `render_config` genera `model: {default: claude-haiku-5-5, provider: anthropic}`; sin ejecutar contra el modelo real.
- [x] Configurar credenciales.
  ⚠️ El backend lee la clave y Hermes la recibe redactada en logs; falta una clave válida (ver arriba).
- [x] Conectar Hermes con backend.
- [x] Crear adaptador.
- [x] Crear sesiones.
- [x] Crear envío de mensajes.
- [x] Crear recepción de respuestas.
- [x] Crear eventos de agente.
- [x] Crear gestión de desconexiones.
- [ ] Crear primera Skill.
  ⚠️ Las Skills existen y son coherentes con las herramientas reales, pero están inertes: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage`, que permitiría al agente escribir sus propias instrucciones (H-06/F14). Ver `DECISIONS.md` «Skills de agent/ inertes en Hermes».
- [ ] Probar conversación completa.
  ⚠️ Conversación completa GUI → backend → Hermes (b200f5b) → respuesta en el chat comprobada SOLO con `tools/dev-llm-stub` (2 s). Falta con Haiku real.
  ⚠️ Sin clave de API no se cierra: el adaptador usa un doble identificado como mock, y ninguna casilla de conversación, personalidad, selección de herramientas o memoria se marca hasta probarla con clave.
  ⚠️ Evals (cierre 2026-11-13): la tubería está verificada con el stub (`agent/evals/run.py`: encadenadas 11/11, personalidad 16/16, selección 19/19, 101/101 controles negativos). El arnés va directo a la Messages API, no pasa por Hermes ni MCP; el paso por Hermes se verifica en `tests/e2e` con el stub. Con `--provider anthropic` y sin clave sale BLOQUEADO.

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
- [ ] Probar consistencia de personalidad.
  ⚠️ Sin clave: la tubería está verificada con el stub (`agent/evals/run.py --suite personalidad`: 16/16 casos y 33/33 controles negativos), pero el stub no evalúa el modelo. Repetir con Claude Haiku 5.5: `--provider anthropic --suite personalidad --repeat 3`.
  ⚠️ Además de la clave, falta la lectura humana de las rúbricas de la suite `personalidad` (16 casos).

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
- [ ] Integrar Rive con React.
  ⚠️ El enchufe está listo (`plug.ts` de una línea, `CharacterRendererProps`, `EmptyFrame` de respaldo, `rive.md`), pero faltan el runtime de Rive (no está en `package.json`) y el `.riv`.
- [x] Crear sistema de eventos visuales.
  ⚠️ Provisional SVG. Cadena `agent.status_changed` → `protocol.ts` → `stores/agent.ts` → `CharacterSlot` comprobada por typecheck, lectura y render por estado. Falta el e2e `desktop.personaje` en Electron (hoy NO COMPROBADO: Electron no arranca por CDP en la pasada y la conversación da 503). `agent.expression_changed` se valida pero el SVG la ignora y el backend no la emite.
- [ ] Implementar sincronización labial.
  ⚠️ En `speaking` solo hay articulación procedural (`talk`/`stepTalk`); `CharacterSink.setMouth(level)` no hace nada en `SvgCharacter`. Depende del audio real del módulo de voz y del `.riv`.
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
- [ ] Probar operaciones desde GUI.
- [ ] Probar operaciones desde Drakter.
  ⚠️ Sin clave: las 21 herramientas se han invocado directamente con un `ToolContext` de agente (14/14 OK), pero no en una conversación con Haiku 5.5.

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
- [ ] Crear vista diaria.
- [ ] Crear vista semanal.
- [ ] Crear vista mensual.
- [ ] Crear eventos.
- [ ] Editar eventos.
- [ ] Eliminar eventos.
- [ ] Crear bloques de tiempo.
- [ ] Asociar bloques a tareas.
- [ ] Detectar solapamientos.
- [ ] Gestionar zonas horarias.
- [ ] Crear asignaturas.
- [ ] Crear horarios recurrentes.
- [ ] Crear sesiones de clase.
- [ ] Asociar recursos.
- [ ] Asociar tareas.
- [ ] Crear herramientas Hermes.
- [ ] Probar recurrencias y fechas.

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
  ⚠️ Las 8 herramientas se registran sin deriva del catálogo y funcionan por `ToolRegistry.dispatch`; ya cargan en la app (`abd56b4`, `ce830cb`) y el agente tiene `storage.write`. Sin clave: no se han probado en una conversación real.
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
- [ ] Crear visualización de relaciones.
  ⚠️ El código existe (`RelationshipsPage`, `RelationGraph`, `RelatedPanel`, diálogos), está enrutado, tipa sin errores y su contrato coincide con el backend; arreglado el filtro por tipo (`78acfca`). Falta abrirla una vez en Electron (`scripts/dev.sh`) para confirmar que se ve bien.
- [ ] Crear herramientas Hermes.
  ⚠️ Las 4 de relaciones y las 3 de etiquetas se registran en el `ToolRegistry` real y sus handlers funcionan. Sin clave: no se han probado con el modelo real. Aviso `tool_catalog_drift` en `get_related_items` hasta alinear `contracts/tools/catalog.json` a `returns_untrusted: true` (pedido a drakter-32).
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
- [ ] Configurar y comprobar la memoria de trabajo en Hermes y OpenViking.
  ⚠️ OpenViking desactivado (U-1). Solo hay plantillas en `memory/working/`; ningún código escribe `DRAKTER_DATA_DIR/memory/working/`. La memoria de trabajo real es la sesión del runner de Hermes.
- [x] Implementar y comprobar la memoria episódica en el Memory Adapter.
- [x] Implementar y comprobar la memoria semántica en el Memory Adapter.
- [x] Implementar y comprobar la memoria procedimental en el Memory Adapter.
- [ ] Configurar y comprobar la recuperación selectiva.
  ⚠️ La búsqueda selectiva por herramienta funciona (filtros, límite, solo aprobados y vigentes), pero la recuperación del backend al turno (`MemoryService.memories_for_context` → `context.builder.build_context`) no está conectada al runner de Hermes.
- [ ] Configurar y comprobar los límites de contexto.
  ⚠️ `ContextBudget` y su orden de recorte están comprobados en `check_memory_rules.py` (40/40), pero no se aplican aún a un turno real (misma causa que la recuperación selectiva).
- [x] Configurar y comprobar los registros de memoria.
- [x] Crear Skill de memoria.
- [x] Probar persistencia.
- [x] Probar recuperación.
  ⚠️ Sin modelo real (sin clave): comprobado por REST y por la herramienta `search_memory`.
- [x] Probar recuerdos contradictorios.
- [x] Probar información obsoleta.

## Checklist 13. Skills y herramientas

- [x] Crear estructura de Skills.
  ⚠️ Las 78 herramientas cargan en el registro y Hermes arranca con ellas (tras arreglar imports y auditorías en la integración), pero el stub no las usa: selección y encadenado sin probar con modelo real.
- [ ] Crear Skill de tareas.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`46bdc88`, pendiente de fusión).
- [ ] Crear Skill de proyectos.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`46bdc88`, pendiente de fusión).
- [ ] Crear Skill de hábitos.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`46bdc88`, pendiente de fusión).
- [ ] Crear Skill de calendario.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`46bdc88`, pendiente de fusión).
- [ ] Crear Skill de asignaturas.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`46bdc88`, pendiente de fusión).
- [ ] Crear Skill de almacén.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`46bdc88`, pendiente de fusión).
- [ ] Crear Skill de relaciones.
  ⚠️ Creada y coherente con las herramientas reales, pero **inerte**: `home.py` desactiva el toolset `skills` de Hermes porque arrastra `skill_manage` (H-06/F14). Hermes no la carga; el modelo se guía por la descripción y el esquema de cada herramienta MCP. Corregidas las herramientas citadas en `workspace-subjects` y `workspace-storage` (`46bdc88`, pendiente de fusión).
- [ ] Crear Skill de configuración.
  ⚠️ El archivo existe, pero sus herramientas (`get_configuration`, `propose_configuration_change`) son PROPUESTA y no existen ni en el catálogo ni en el backend. Además está inerte.
- [x] Definir parámetros.
- [x] Definir permisos.
  ⚠️ Arreglado: faltaba `storage.write` y se denegaban 4 herramientas del almacén (ya concedido en `drakter/integracion`). `improvement.read`/`improvement.write` se conceden con las dos escrituras en `RiskClass.CONFIRM` (`fa511e7`, pendiente de fusión); hoy esas escrituras quedan denegadas porque el runtime usa `DefaultToolGate` (ver «Definir confirmaciones»).
- [ ] Definir confirmaciones.
  ⚠️ 7 herramientas con `risk=confirm` y `summarize`; la puerta falla cerrada (`delete_task` del agente no se ejecuta y se audita `rejected`), pero nunca se crea la confirmación pendiente: `main.py` no llama a `install_security` y `AgentRuntime` crea `ToolRegistry` sin `gate=BackendToolGate`. `GET /api/v1/confirmations` da 503.
- [x] Definir errores.
  ⚠️ 6 herramientas de lectura no declaran `errors` (`get_memory_status`, `search_relationships`, `list_subjects`, `get_timetable`, `get_agent_status`, `get_system_status`).
- [ ] Probar selección de herramientas.
  ⚠️ Sin clave. Suite `seleccion` (19 casos) lista y verificada con el stub: `agent/evals/run.py --provider anthropic --suite seleccion`.
- [ ] Probar operaciones encadenadas.
  ⚠️ Sin clave. Suite `encadenadas` (11 casos) lista y verificada con el stub: `agent/evals/run.py --provider anthropic --suite encadenadas`.
  ⚠️ Cableado comprobado con el stub por Hermes y MCP: `create_task` → `search_tasks` en un mismo turno, y la segunda encuentra lo creado por la primera.

## Checklist 14. Voz

- [ ] Instalar openWakeWord.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Configurar palabra de activación.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Instalar Silero VAD.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Configurar detección de voz.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Instalar Faster-Whisper.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Probar modelo small.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Medir latencia.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Evaluar modelo medium.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Instalar Kokoro.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Instalar Piper.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Crear Voice Manager.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Crear Voice Personality Engine.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Crear reproducción de audio.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Crear interrupciones.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Crear cancelación de audio.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Sincronizar boca.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Crear gestión de errores.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
- [ ] Probar conversación por voz completa.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.

## Checklist 15. Automejora

- [x] Crear registro de feedback.
- [x] Crear clasificación de incidencias.
- [x] Crear propuestas.
- [x] Crear evaluaciones.
- [x] Crear entorno de pruebas.
- [ ] Crear flujo de aprobación.
  ⚠️ La lógica funciona con una puerta de prueba (`request_approval` → `approve` ligado al digest → `apply`), pero falta integrarla en la app: no hay adaptador `ConfirmationGate` sobre `ActionService` (sin cablear en `main.py`), nadie fija `app.state.gui_principal` (por HTTP la GUI cuenta como agente y aprobar/evaluar/aplicar dan 403 `user_required`) y no hay pantalla de automejora en `desktop/src/modules/`. Falla cerrado.
- [x] Integrar Git.
- [x] Crear historial de cambios.
- [x] Crear informes.
- [x] Impedir cambios no autorizados.
- [x] Probar recuperación de cambios.
  ⚠️ `revert` funciona. Falta llamar a `recover_interrupted(settings)` al arrancar (una línea en `main.py`, pedida a drakter-32) y registrar `invalidate_after_restore` como hook de restauración de copias (módulo de copias).

## Checklist 16. Seguridad y fiabilidad

- [ ] Crear permisos por módulo.
- [ ] Crear permisos por operación.
- [x] Crear confirmaciones.
  ⚠️ Permisos, confirmación pendiente y auditoría se construyen antes de la primera herramienta. Las casillas de esta checklist son revisión y endurecimiento finales.
- [x] Proteger credenciales.
- [ ] Validar rutas.
- [ ] Limitar acceso a archivos.
- [ ] Proteger operaciones destructivas.
- [x] Crear auditoría.
- [ ] Crear copias de seguridad.
- [ ] Probar restauración.
- [ ] Probar desconexiones.
- [ ] Probar recuperación del backend.
- [ ] Probar recuperación de Hermes.
- [ ] Probar errores de memoria.
- [ ] Revisar datos sensibles.

## Checklist 17. Optimización y lanzamiento

- [ ] Medir consumo de RAM.
- [ ] Medir CPU.
- [ ] Medir uso de CPU y RAM (no hay VRAM dedicada).
- [ ] Medir latencia de STT.
- [ ] Medir latencia de TTS.
- [ ] Medir latencia de Hermes.
- [ ] Optimizar consultas SQLite.
- [ ] Optimizar FTS5.
- [ ] Optimizar recuperación de memoria.
- [ ] Optimizar carga de interfaz.
- [ ] Crear instalador.
- [ ] Crear actualización de aplicación.
- [ ] Crear documentación de instalación.
- [ ] Crear documentación de uso.
- [ ] Crear versión estable.
- [ ] Crear copia de seguridad inicial.
- [ ] Realizar pruebas de aceptación.

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
