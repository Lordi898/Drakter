---
name: workspace-habits
description: "Hábitos: crear rutinas con su frecuencia, registrar cumplimientos, ver historial y estadísticas."
version: 2.0.0
license: MIT
metadata:
  hermes:
    tags: [drakter, habits]
---

# workspace-habits

## Herramientas
- Buscar: `list_habits`; leer: `get_habit` (frecuencia vigente y estado de hoy).
- Crear: `create_habit` (name, rrule, timezone IANA, start_date; opcional preferred_local_time y reminder_enabled para avisar).
- Cambiar: `update_habit` (solo lo indicado; cambiar rrule abre versión nueva desde schedule_effective_from).
- Archivar / restaurar: `archive_habit` (archived=false restaura). No hay borrado.
- Registrar el día: `register_habit_completion` (habit_id, occurrence_date, status done|skipped|missed). No admite días futuros.
- Consultar: `get_habit_history` (día a día) y `get_habit_statistics` (tasa y rachas), máximo 400 días.

## Orden típico
1. `list_habits` → id del hábito.
2. Para «hoy he hecho X»: `register_habit_completion` con status done; no edites el hábito.
3. Para «¿cómo voy?»: `get_habit_statistics`.

## RRULE frecuentes
Diario `FREQ=DAILY`; lunes, miércoles y viernes `FREQ=WEEKLY;BYDAY=MO,WE,FR`; cada dos días `FREQ=DAILY;INTERVAL=2`.

## Errores frecuentes
- `invalid_rrule` / `invalid_timezone`: corrige el formato (zona como Europe/Madrid).
- Registrar un día futuro: no se puede; dilo.

## Ejemplos
- «Quiero leer 20 minutos cada día a las 22:00» → `create_habit` con FREQ=DAILY y preferred_local_time.
- «Hoy he ido al gimnasio» → `list_habits` → `register_habit_completion` done.
- «¿Qué racha llevo meditando?» → `list_habits` → `get_habit_statistics`.
