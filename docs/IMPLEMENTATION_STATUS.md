# CHECKLISTS GENERALES DE IMPLEMENTACIÓN

Las siguientes listas son el control de trabajo del proyecto y la única lista viva de casillas. Se marcarán cuando la tarea esté implementada y funcione como se espera (`CLAUDE.md` §4). Lo bloqueado se anota con ⚠️. La equivalencia entre checklists, pasos del orden real y fases de cada plan está en `DECISIONS.md`.

> **Pasada integrada 2026-11-13** (`drakter/integracion`): solo se marca lo visto funcionar en la app arrancada (Electron + backend + Hermes con el stub). Detalle en `RUN_STATE.md`.

## Checklist 0. Arquitectura y preparación

- [x] Crear repositorio Drakter.
- [x] Configurar Git.
- [x] Crear estructura de carpetas (cada carpeta se crea cuando entra código).
- [x] Crear README.
- [x] Crear CHANGELOG.
- [ ] Documentar arquitectura.
- [x] Documentar decisiones técnicas.
- [ ] Definir convenciones.
- [ ] Definir modelos de datos.
- [x] Definir API.
- [ ] Definir eventos.
- [ ] Definir permisos.
- [ ] Definir configuración.
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
- [ ] Crear sistema de permisos.
  ⚠️ Matriz de roles y confirmaciones comprobadas (`check_confirmations.py`: 0 fallos), pero tareas y proyectos no están cableados a `ActionService`: borrar desde la GUI da 503 `confirmation_unavailable` (falla cerrado).

## Checklist 3. Hermes

- [x] Instalar Hermes.
- [ ] Configurar Claude Haiku 5.5.
  ⚠️ 2026-11-13: la `ANTHROPIC_API_KEY` de `~/.config/drakter/.env` da 401 `invalid x-api-key` (también en llamada directa a la API). Sin clave válida no hay prueba con el modelo real.
- [ ] Configurar credenciales.
  ⚠️ El backend lee la clave y Hermes la recibe redactada en logs; falta una clave válida (ver arriba).
- [x] Conectar Hermes con backend.
- [x] Crear adaptador.
- [x] Crear sesiones.
- [x] Crear envío de mensajes.
- [x] Crear recepción de respuestas.
- [x] Crear eventos de agente.
- [ ] Crear gestión de desconexiones.
- [ ] Crear primera Skill.
- [ ] Probar conversación completa.
  ⚠️ Conversación completa GUI → backend → Hermes (b200f5b) → respuesta en el chat comprobada SOLO con `tools/dev-llm-stub` (2 s). Falta con Haiku real.
  ⚠️ Sin clave de API no se cierra: el adaptador usa un doble identificado como mock, y ninguna casilla de conversación, personalidad, selección de herramientas o memoria se marca hasta probarla con clave.

## Checklist 4. Personalidad y contexto

- [x] Crear SOUL.md.
- [x] Crear PERSONALITY.md.
- [x] Crear BEHAVIOR.md.
- [x] Crear COMMUNICATION.md.
- [x] Crear EMOTIONAL_STYLE.md.
- [x] Crear VALUES.md.
- [ ] Crear USER.md.
- [ ] Crear ENVIRONMENT.md.
- [ ] Crear PREFERENCES.md.
- [ ] Crear CURRENT_CONTEXT.md.
- [ ] Crear CAPABILITIES.md.
- [ ] Crear WORKSPACE_GUIDE.md.
- [ ] Crear TOOL_GUIDE.md.
- [ ] Crear SYSTEM_GUIDE.md.
- [ ] Configurar carga de contexto.
- [ ] Configurar prioridades.
- [ ] Probar consistencia de personalidad.

## Checklist 5. Personaje

- [ ] Diseñar identidad visual.
- [ ] Diseñar ojos.
- [ ] Diseñar boca.
- [ ] Diseñar expresiones.
- [ ] Crear proyecto Rive.
  ⚠️ Se ve el personaje sustituto (SVG) en la pantalla Drakter; el `.riv` real sigue pendiente.
  ⚠️ El `.riv` se diseña a mano en el editor de Rive. Por código solo se cubre el personaje provisional; las casillas de estados, transiciones e integración dependen de ese archivo hasta que el usuario lo entregue.
- [ ] Crear estado idle.
- [ ] Crear estado listening.
- [ ] Crear estado thinking.
- [ ] Crear estado speaking.
- [ ] Crear estado executing.
- [ ] Crear estado success.
- [ ] Crear estado error.
- [ ] Crear estado interrupted.
- [ ] Crear estado offline.
- [ ] Crear transiciones.
- [ ] Integrar Rive con React.
- [ ] Crear sistema de eventos visuales.
- [ ] Implementar sincronización labial.
- [ ] Probar animaciones.

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
- [ ] Crear integridad referencial.
- [x] Crear migraciones.
- [ ] Probar persistencia.

## Checklist 7. Tareas y proyectos

- [x] Crear interfaz de tareas.
- [x] Crear tareas.
- [ ] Editar tareas.
- [ ] Eliminar tareas.
  ⚠️ 503 `confirmation_unavailable`: `tasks_ports.Ports` usa `FailClosedGate` porque nadie fija `app.state.workspace_ports` ni hay ejecutores de tareas/proyectos en `load_confirmed_executors`.
- [ ] Completar tareas.
- [ ] Reabrir tareas.
- [ ] Crear subtareas.
- [ ] Crear subtareas anidadas.
- [ ] Crear estados.
- [ ] Crear prioridades.
- [ ] Crear fechas límite.
- [ ] Crear etiquetas.
- [ ] Crear dependencias.
- [x] Crear interfaz de proyectos.
- [ ] Crear proyectos.
- [ ] Editar proyectos.
- [ ] Archivar proyectos.
- [ ] Asociar tareas a proyectos.
- [ ] Mostrar progreso.
- [ ] Crear historial.
- [ ] Crear herramientas Hermes.
- [ ] Probar operaciones desde GUI.
- [ ] Probar operaciones desde Drakter.

## Checklist 8. Hábitos

- [x] Crear interfaz.
- [ ] Crear hábitos.
- [ ] Editar hábitos.
- [ ] Definir frecuencia.
- [ ] Definir días.
- [ ] Definir recordatorios.
- [ ] Registrar cumplimiento.
- [ ] Consultar historial.
- [ ] Calcular estadísticas.
- [ ] Asociar hábitos con objetivos.
- [ ] Crear herramientas Hermes.
- [ ] Probar persistencia.

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
- [ ] Crear catálogo de recursos.
- [ ] Crear carpetas.
- [ ] Crear metadatos.
- [ ] Crear descripciones opcionales.
- [ ] Crear etiquetas.
- [ ] Crear registro de rutas.
- [x] Crear índice FTS5.
- [ ] Indexar nombres.
- [ ] Indexar tipos.
- [ ] Indexar descripciones.
- [ ] Indexar rutas y metadatos.
- [ ] Indexar texto extraído, de forma opcional.
- [ ] Implementar búsqueda.
- [ ] Implementar actualización del índice.
- [ ] Detectar archivos ausentes.
- [ ] Implementar lectura bajo demanda.
- [ ] Implementar lectores PDF.
- [ ] Implementar lectores de texto.
- [ ] Implementar lectores de imágenes mediante metadatos.
- [ ] Implementar lectura de enlaces.
- [ ] Implementar límites de comprimidos.
- [ ] Implementar permisos.
- [ ] Crear herramientas Hermes.
- [ ] Probar formatos y errores.

## Checklist 11. Relaciones avanzadas

- [x] Crear servicio de relaciones.
- [x] Crear tipos de relación.
- [ ] Crear validaciones.
- [ ] Crear relaciones entre tareas y proyectos.
- [ ] Crear relaciones entre tareas y asignaturas.
- [ ] Crear relaciones entre tareas y recursos.
- [ ] Crear relaciones entre tareas y calendario.
- [ ] Crear relaciones entre proyectos y recursos.
- [ ] Crear relaciones entre asignaturas y recursos.
- [ ] Crear consulta inversa.
- [ ] Crear consulta de elementos relacionados.
- [ ] Crear visualización de relaciones.
- [ ] Crear herramientas Hermes.
- [ ] Probar integridad y eliminación.

## Checklist 12. Memoria

- [ ] Definir cuatro capas de memoria.
- [ ] Crear configuración e integración de `memory/` (sin recuerdos ni datos personales).
- [ ] Crear Memory Adapter.
- [ ] Implementar la memoria SQLite + FTS5 tras el Memory Adapter.
  ⚠️ OpenViking queda desactivado en v1 (entrada "Memoria v1 en SQLite + FTS5; OpenViking desactivado" de `DECISIONS.md`); desviación pendiente de confirmar por el usuario (U-1).
- [ ] Configurar capas L0/L1/L2 (futuro, con OpenViking).
- [ ] Elegir embedding multilingüe (futuro, con OpenViking).
- [ ] Implementar y comprobar la extracción de recuerdos en el Memory Adapter.
- [ ] Implementar y comprobar la clasificación en el Memory Adapter.
- [ ] Implementar y comprobar la deduplicación en el Memory Adapter.
- [ ] Implementar y comprobar la detección de contradicciones en el Memory Adapter.
- [ ] Configurar y comprobar la memoria de trabajo en Hermes y OpenViking.
- [ ] Implementar y comprobar la memoria episódica en el Memory Adapter.
- [ ] Implementar y comprobar la memoria semántica en el Memory Adapter.
- [ ] Implementar y comprobar la memoria procedimental en el Memory Adapter.
- [ ] Configurar y comprobar la recuperación selectiva.
- [ ] Configurar y comprobar los límites de contexto.
- [ ] Configurar y comprobar los registros de memoria.
- [ ] Crear Skill de memoria.
- [ ] Probar persistencia.
- [ ] Probar recuperación.
- [ ] Probar recuerdos contradictorios.
- [ ] Probar información obsoleta.

## Checklist 13. Skills y herramientas

- [ ] Crear estructura de Skills.
  ⚠️ Las 78 herramientas cargan en el registro y Hermes arranca con ellas (tras arreglar imports y auditorías en la integración), pero el stub no las usa: selección y encadenado sin probar con modelo real.
- [ ] Crear Skill de tareas.
- [ ] Crear Skill de proyectos.
- [ ] Crear Skill de hábitos.
- [ ] Crear Skill de calendario.
- [ ] Crear Skill de asignaturas.
- [ ] Crear Skill de almacén.
- [ ] Crear Skill de relaciones.
- [ ] Crear Skill de configuración.
- [ ] Definir parámetros.
- [ ] Definir permisos.
- [ ] Definir confirmaciones.
- [ ] Definir errores.
- [ ] Probar selección de herramientas.
- [ ] Probar operaciones encadenadas.

## Checklist 14. Voz

- [ ] Instalar openWakeWord.
- [ ] Configurar palabra de activación.
- [ ] Instalar Silero VAD.
- [ ] Configurar detección de voz.
- [ ] Instalar Faster-Whisper.
- [ ] Probar modelo small.
- [ ] Medir latencia.
- [ ] Evaluar modelo medium.
- [ ] Instalar Kokoro.
- [ ] Instalar Piper.
- [ ] Crear Voice Manager.
- [ ] Crear Voice Personality Engine.
- [ ] Crear reproducción de audio.
- [ ] Crear interrupciones.
- [ ] Crear cancelación de audio.
- [ ] Sincronizar boca.
- [ ] Crear gestión de errores.
- [ ] Probar conversación por voz completa.

## Checklist 15. Automejora

- [ ] Crear registro de feedback.
- [ ] Crear clasificación de incidencias.
- [ ] Crear propuestas.
- [ ] Crear evaluaciones.
- [ ] Crear entorno de pruebas.
- [ ] Crear flujo de aprobación.
- [ ] Integrar Git.
- [ ] Crear historial de cambios.
- [ ] Crear informes.
- [ ] Impedir cambios no autorizados.
- [ ] Probar recuperación de cambios.

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
