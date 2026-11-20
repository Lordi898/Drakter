---
name: workspace-subjects
description: "Asignaturas: crear y editar, horario semanal de clases, cancelar o mover una clase y ver su material."
version: 2.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, subjects]
---

# workspace-subjects

## Herramientas
- Buscar: `list_subjects`; leer: `get_subject`.
- Crear / editar: `create_subject` (name; opcional teacher, color #RRGGBB, description), `update_subject`.
- Horario: `get_timetable` (on: fecha) para ver las clases vigentes ese día de la semana.
- Clase semanal: `create_class_session` (subject_id, weekday 1=lunes..7=domingo, starts_local_time, ends_local_time, timezone, valid_from; opcional room, valid_until).
- Cambiar una clase: `update_class_session`; una sola fecha: `create_schedule_exception` (session_id, occurrence_date, kind cancelled|modified, override).
- Borrar una clase semanal: `delete_class_session`. Pide confirmación en pantalla.
- Material: `get_subject_resources`; para título o contenido, `get_resource` / `read_resource`.
- Tareas de la asignatura: `list_tasks` con subject_id.

## Orden típico
1. `list_subjects` → subject_id.
2. Para clases: `get_timetable` o `get_subject` → session_id.
3. Acción y aviso de los `conflicts` que devuelva.

## Errores frecuentes
- «No hay clase el martes que viene»: es una excepción, no borres la sesión semanal.
- No hay borrado de asignaturas; dilo.

## Ejemplos
- «Añade Física los lunes y miércoles de 10 a 12 en el aula 3» → `create_subject` si no existe → dos `create_class_session`.
- «¿Qué clases tengo el jueves?» → `get_timetable` con la fecha del jueves.
- «El viernes 12 se cancela Química» → `list_subjects` → `get_subject`/`get_timetable` → `create_schedule_exception` cancelled.
