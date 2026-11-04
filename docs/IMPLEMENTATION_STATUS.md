# CHECKLISTS GENERALES DE IMPLEMENTACIÓN

Las siguientes listas son el control de trabajo del proyecto y la única lista viva de casillas. Se marcarán cuando la tarea esté implementada y funcione como se espera (`CLAUDE.md` §4). Lo bloqueado se anota con ⚠️. La equivalencia entre checklists, pasos del orden real y fases de cada plan está en `DECISIONS.md`.

## Checklist 0. Arquitectura y preparación

- [ ] Crear repositorio Drakter.
- [ ] Configurar Git.
- [ ] Crear estructura de carpetas (cada carpeta se crea cuando entra código).
- [ ] Crear README.
- [ ] Crear CHANGELOG.
- [ ] Documentar arquitectura.
- [ ] Documentar decisiones técnicas.
- [ ] Definir convenciones.
- [ ] Definir modelos de datos.
- [ ] Definir API.
- [ ] Definir eventos.
- [ ] Definir permisos.
- [ ] Definir configuración.
- [ ] Preparar entorno de desarrollo.

## Checklist 1. Aplicación de escritorio

- [ ] Configurar Electron.
- [ ] Configurar React.
- [ ] Configurar TypeScript.
- [ ] Configurar Tailwind.
- [ ] Configurar shadcn/ui.
- [ ] Crear ventana principal.
- [ ] Crear navegación lateral.
- [ ] Crear área central.
- [ ] Crear panel contextual.
- [ ] Crear notificaciones.
- [ ] Crear configuración.
- [ ] Crear gestión de errores.
- [ ] Configurar empaquetado.

## Checklist 2. Backend

- [ ] Crear FastAPI.
- [ ] Configurar SQLite.
- [ ] Configurar migraciones.
- [ ] Crear API REST.
- [ ] Crear WebSocket.
- [ ] Crear servicios.
- [ ] Crear repositorios.
- [ ] Crear esquemas.
- [ ] Crear validaciones.
- [ ] Crear logs.
- [ ] Crear gestión de errores.
- [ ] Crear sistema de permisos.

## Checklist 3. Hermes

- [ ] Instalar Hermes.
- [ ] Configurar Claude Haiku 5.5.
- [ ] Configurar credenciales.
- [ ] Conectar Hermes con backend.
- [ ] Crear adaptador.
- [ ] Crear sesiones.
- [ ] Crear envío de mensajes.
- [ ] Crear recepción de respuestas.
- [ ] Crear eventos de agente.
- [ ] Crear gestión de desconexiones.
- [ ] Crear primera Skill.
- [ ] Probar conversación completa.
  ⚠️ Sin clave de API no se cierra: el adaptador usa un doble identificado como mock, y ninguna casilla de conversación, personalidad, selección de herramientas o memoria se marca hasta probarla con clave.

## Checklist 4. Personalidad y contexto

- [ ] Crear SOUL.md.
- [ ] Crear PERSONALITY.md.
- [ ] Crear BEHAVIOR.md.
- [ ] Crear COMMUNICATION.md.
- [ ] Crear EMOTIONAL_STYLE.md.
- [ ] Crear VALUES.md.
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

- [ ] Crear esquema SQLite.
- [ ] Crear tabla de tareas.
- [ ] Crear tabla de proyectos.
- [ ] Crear tabla de hábitos.
- [ ] Crear tabla de registros de hábitos.
- [ ] Crear tabla de eventos.
- [ ] Crear tabla de bloques de tiempo.
- [ ] Crear tabla de asignaturas.
- [ ] Crear tabla de sesiones de clase.
- [ ] Crear tabla de recursos.
- [ ] Crear tabla de carpetas.
- [ ] Crear tabla de etiquetas.
- [ ] Crear tabla de relaciones.
- [ ] Crear tabla de auditoría.
- [ ] Crear identificadores UUID.
- [ ] Crear integridad referencial.
- [ ] Crear migraciones.
- [ ] Probar persistencia.

## Checklist 7. Tareas y proyectos

- [ ] Crear interfaz de tareas.
- [ ] Crear tareas.
- [ ] Editar tareas.
- [ ] Eliminar tareas.
- [ ] Completar tareas.
- [ ] Reabrir tareas.
- [ ] Crear subtareas.
- [ ] Crear subtareas anidadas.
- [ ] Crear estados.
- [ ] Crear prioridades.
- [ ] Crear fechas límite.
- [ ] Crear etiquetas.
- [ ] Crear dependencias.
- [ ] Crear interfaz de proyectos.
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

- [ ] Crear interfaz.
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

- [ ] Crear interfaz de calendario.
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

- [ ] Crear interfaz del almacén.
- [ ] Crear catálogo de recursos.
- [ ] Crear carpetas.
- [ ] Crear metadatos.
- [ ] Crear descripciones opcionales.
- [ ] Crear etiquetas.
- [ ] Crear registro de rutas.
- [ ] Crear índice FTS5.
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

- [ ] Crear servicio de relaciones.
- [ ] Crear tipos de relación.
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
- [ ] Configurar OpenViking como proveedor de Hermes.
- [ ] Configurar capas L0/L1/L2.
- [ ] Elegir embedding multilingüe.
- [ ] Configurar y comprobar la extracción de recuerdos de OpenViking.
- [ ] Configurar y comprobar la clasificación de OpenViking.
- [ ] Configurar y comprobar la deduplicación de OpenViking.
- [ ] Configurar y comprobar la detección de contradicciones de OpenViking.
- [ ] Crear memoria de trabajo.
- [ ] Crear memoria episódica.
- [ ] Crear memoria semántica.
- [ ] Crear memoria procedimental.
- [ ] Crear recuperación selectiva.
- [ ] Crear límites de contexto.
- [ ] Crear registros de memoria.
- [ ] Crear Skill de memoria.
- [ ] Probar persistencia.
- [ ] Probar recuperación.
- [ ] Probar recuerdos contradictorios.
- [ ] Probar información obsoleta.

## Checklist 13. Skills y herramientas

- [ ] Crear estructura de Skills.
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
- [ ] Crear confirmaciones.
  ⚠️ Permisos, confirmación pendiente y auditoría se construyen antes de la primera herramienta. Las casillas de esta checklist son revisión y endurecimiento finales.
- [ ] Proteger credenciales.
- [ ] Validar rutas.
- [ ] Limitar acceso a archivos.
- [ ] Proteger operaciones destructivas.
- [ ] Crear auditoría.
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
