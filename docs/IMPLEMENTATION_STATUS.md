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
  ⚠️ Con Claude Haiku 5.5 real por Hermes, leer, buscar y crear relaciones funcionan (`create_relationship`, `get_related_items`). `delete_relationship` queda denegado (`confirmation_unavailable`) hasta que el runtime use la puerta real de confirmación (drakter-34). El desvío de catálogo de `get_related_items` ya está corregido.
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
  ⚠️ La memoria de trabajo es la sesión propia de Hermes (`session_db`, `persist=True`): comprobado con el stub que el turno 2 lleva el historial del turno 1. La parte de OpenViking sigue desactivada (U-1).
- [x] Implementar y comprobar la memoria episódica en el Memory Adapter.
- [x] Implementar y comprobar la memoria semántica en el Memory Adapter.
- [x] Implementar y comprobar la memoria procedimental en el Memory Adapter.
- [x] Configurar y comprobar la recuperación selectiva.
- [x] Configurar y comprobar los límites de contexto.
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
  ⚠️ Arreglado: faltaba `storage.write` y se denegaban 4 herramientas del almacén (ya concedido en `drakter/integracion`). `improvement.read`/`improvement.write` se conceden con las dos escrituras en `RiskClass.CONFIRM` (`5dd55b1`); hoy esas escrituras quedan denegadas porque el runtime usa `DefaultToolGate` (ver «Definir confirmaciones»).
  Nota: con el modelo real (prueba de relaciones de drakter-41), el agente llamó por iniciativa propia a create/list/get_improvement_proposal y record_improvement_feedback sin que se le pidiera. Es seguro (las escrituras exigen confirmación), pero hay que revisar las descripciones de esas herramientas o las instrucciones de cuándo proponer mejoras; se deja para el rediseño de la personalidad y la conversación.
- [x] Definir confirmaciones.
- [x] Definir errores.
  ⚠️ 6 herramientas de lectura no declaran `errors` (`get_memory_status`, `search_relationships`, `list_subjects`, `get_timetable`, `get_agent_status`, `get_system_status`).
- [x] Probar selección de herramientas.
- [x] Probar operaciones encadenadas.

## Checklist 14. Voz

- [ ] Instalar openWakeWord.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
  ⚠️ `OpenWakeWordProvider` existe, pero no hay modelo para «Drakter» (los preentrenados son CC BY-NC-SA 4.0 y de otras palabras); por defecto `NullWakeWord` (pulsar para hablar). No se instala en el cierre.
- [ ] Configurar palabra de activación.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
  ⚠️ Depende de un modelo propio (`DRAKTER_WAKEWORD_MODEL`); `wakeword.set true` sin proveedor responde `invalid_request`.
- [x] Instalar Silero VAD.
- [x] Configurar detección de voz.
- [x] Instalar Faster-Whisper.
- [x] Probar modelo small.
- [x] Medir latencia.
  ⚠️ Medición lista y ejecutada (`voice/tests/bench_engines.py`, evento `voice.metrics`), pero con la máquina muy cargada (loadavg 9–14): STT small RTF 0,82–1,02; Kokoro primer audio 398–1 282 ms. Hay que repetirla con la máquina en reposo antes de dar cifras de producto.
- [x] Evaluar modelo medium.
- [x] Instalar Kokoro.
- [ ] Instalar Piper.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
  ⚠️ `PiperTTS` y `FallbackTTS` existen (proceso externo, venv propio), pero no se instaló `piper-tts` ni se probó.
- [x] Crear Voice Manager.
- [x] Crear Voice Personality Engine.
- [x] Crear reproducción de audio.
- [x] Crear interrupciones.
- [x] Crear cancelación de audio.
- [ ] Sincronizar boca.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta.
  ⚠️ La voz emite `voice.playback_level`, pero no llega a la boca: el backend no publica los eventos de voz y `SvgCharacter.setMouth` no hace nada.
- [x] Crear gestión de errores.
- [ ] Probar conversación por voz completa.
  ⚠️ Rediseño previsto sobre Pipecat (STT Whisper, TTS Fish Audio); en v1 `voice/` solo se estabiliza y documenta. El router de voz (`backend/app/integrations/voice/router.py`) no se monta en `main.py` en este cierre, aunque Electron permite `/api/v1/voice/*`.
  ⚠️ No es posible hoy: `backend/app/integrations/voice` no está registrado en `main.py` (a propósito, `DRAKTER_VOICE_ENABLED=false` por defecto) y el escritorio no tiene cliente de voz (botón de micrófono desactivado). El puente del backend (`VoiceService`, supervisor, cliente IPC, `VoiceBridge`) no se ha ejecutado contra el proceso real.

## Checklist 15. Automejora

- [x] Crear registro de feedback.
- [x] Crear clasificación de incidencias.
- [x] Crear propuestas.
- [x] Crear evaluaciones.
- [x] Crear entorno de pruebas.
- [x] Crear flujo de aprobación.
  ⚠️ En el backend funciona por `ActionService` (`approval-request`/`revert-request` → 409 → `/api/v1/confirmations/{id}/approve`, 300 s, ligado al digest, de un solo uso y auditado; el agente recibe DENY) con `2425da5` y `b1a49a3`. No hay pantalla de automejora en `desktop/src/modules/`, y `routes.generated.ts` aún lista la ruta `/approve` retirada.
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
  ⚠️ Por la GUI y por el agente funcionan (409 / confirmación pendiente → aprobar con `approver` → ejecutado; el agente por `BackendToolGate`, `3bafbe1`). Olvidar un recuerdo desde la GUI sigue con `DenyAllGate` y falla cerrado (pendiente de drakter-42).
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
  ⚠️ Sigue abierta FILE-DB-02 (TOCTOU en `connect`, riesgo bajo). INJ-05 (título y URL remotos fuera del sobre en `read_resource`) en curso (drakter-42).

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
- [ ] Realizar pruebas de aceptación.
  ⚠️ Depende de la pasada completa final de drakter-49 sobre la punta de integración.

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
