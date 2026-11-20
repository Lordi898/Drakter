---
name: workspace-calendar
description: "Calendario: eventos, recordatorios, series y excepciones, bloques de tiempo, agenda y disponibilidad."
version: 2.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, calendar]
---

# workspace-calendar

## Herramientas
- Ver agenda: `get_schedule` (from_date incluido, to_date excluido, timezone). Incluye eventos, bloques y clases.
- Hueco libre: `check_availability` (local_start, local_end, timezone) antes de proponer o crear.
- Evento: `create_event` (title, timezone; con hora local_start/local_end sin desfase; de día entero all_day con start_date/end_date_exclusive; kind event|reminder|work_session; rrule para series; reminder_minutes_before para avisar).
- Leer / editar: `get_event`, `update_event` (solo lo indicado).
- Una sola ocurrencia de una serie: `create_event_exception` (occurrence_local_start original, kind cancelled|modified).
- Bloque de tiempo para trabajar: `create_time_block` (opcional task_id), `update_time_block`, `move_time_block`.
- Borrar: `delete_event`, `delete_time_block`. Piden confirmación en pantalla.

## Orden típico
1. Si no sabes el id, `get_schedule` en el rango probable.
2. Antes de crear o mover, `check_availability`; los solapes llegan como aviso: cuéntalos.
3. Crea o cambia y resume día, hora y zona.

## Errores frecuentes
- Hora sin zona: usa siempre la del usuario (Europe/Madrid si no dice otra).
- `nonexistent_local_time`: cae en el cambio de hora; propone otra.
- Para quitar un día de una serie no borres la serie: usa `create_event_exception` cancelled.

## Ejemplos
- «¿Qué tengo mañana?» → `get_schedule` de mañana a pasado mañana.
- «Dentista el jueves a las 17:00, avísame una hora antes» → `check_availability` → `create_event` con reminder_minutes_before 60.
- «Borra la reunión del lunes» → `get_schedule` → `delete_event` → pendiente de aprobar en la interfaz.
