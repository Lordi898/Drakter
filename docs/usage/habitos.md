# Hábitos

> **Estado:** integrado en `drakter/integracion` (`7fd30e1`): pantalla **Hábitos** en la navegación y API `habits` montada. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

## Para qué sirve

Registras rutinas con su frecuencia y marcas cada día si las cumpliste. La pantalla calcula rachas, porcentaje de cumplimiento e historial. Abre la sección **Hábitos** de la barra lateral (atajo Ctrl+2).

## Crear un hábito

1. En **Hábitos**, pulsa **Crear hábito**.
2. Rellena **Nombre** (obligatorio) y, si quieres, **Descripción (opcional)**.
3. En **Frecuencia**, elige en **Se repite**:
   - **Todos los días**.
   - **Días concretos de la semana**: marca los botones L, M, X, J, V, S, D (**Días activos**).
   - **Cada N semanas**: indica **Cada cuántas semanas** (de 2 a 52) y los días.
   - **Una vez al mes**: indica **Día del mes** (de 1 a 31).
4. Ajusta **Fecha de inicio**, **Fecha final (opcional)** y **Zona horaria** (por defecto, la del sistema).
5. Opcional: **Hora preferida (opcional)**, el interruptor **Recordatorio** y **Objetivo (opcional)**.
6. Pulsa **Crear hábito**.

Si falta algo, el diálogo lista el problema (por ejemplo "Escribe un nombre." o "Elige al menos un día de la semana.") y el botón queda desactivado.

## Registrar cada día

En la lista, cada hábito que toca hoy muestra tres botones: **Hecho**, **Saltado** y **No hecho**. Si hoy no toca, ves "Hoy no toca".

- "Hoy" se calcula en la zona horaria del hábito, no en la del sistema.
- Volver a pulsar otro botón corrige el registro del mismo día (no se duplica).
- Para corregir otro día: pulsa el nombre del hábito, elige un día en la cuadrícula **Historial** y marca su estado. Los días futuros no se pueden registrar. Un día no programado sí se puede registrar.

Leyenda del historial: Hecho, Saltado, No hecho, Programado sin registro, No programado. Puedes ver 30 días, 90 días o 6 meses.

## Rachas y estadísticas

En el detalle, el bloque **Estadísticas** muestra:

- **Cumplimiento**: hechos entre programados (los saltados no cuentan).
- **Racha actual** y **Mejor racha**: días programados consecutivos con **Hecho**. Un día **Saltado** ni suma ni rompe la racha.
- **Sin registrar**: días programados ya pasados sin marca (hoy no cuenta).
- **Por día de la semana**.

## Editar, cambiar frecuencia y archivar

- **Editar** abre el mismo formulario. Los registros ya guardados se conservan.
- Si cambias la frecuencia, aparece **La nueva frecuencia rige desde** (por defecto, hoy). Los días anteriores siguen con la frecuencia vieja; el detalle lo muestra en **Versiones de la frecuencia**.
- La **Fecha de inicio** no se puede cambiar al editar.
- **Archivar** / **Desarchivar** está en el detalle. No hay borrado definitivo y los registros nunca se borran. Los archivados se ven con el interruptor **Ver archivados** y no se pueden marcar.

## Qué pide confirmación

Nada en esta pantalla: archivar y registrar son reversibles y no abren ningún diálogo de confirmación (no hay llamada de confirmación en `services/habits.py`).

## Con el chat

El agente tiene las herramientas `create_habit`, `get_habit`, `update_habit`, `archive_habit`, `list_habits`, `register_habit_completion`, `get_habit_history` y `get_habit_statistics` (`backend/app/tools/habits.py`). NO COMPROBADO.

## Problemas frecuentes

- **"No se pudo cargar" / pantalla de estado del servidor** (`BackendState`): el backend no está conectado; usa el botón de reintento. Sin backend no se muestra nada de ejemplo.
- **Error al registrar un día futuro**: el backend lo rechaza (`conflict`).
- **La frecuencia actual (...) no se puede editar aquí**: la regla guardada usa algo que el editor no sabe representar; si eliges otra, sustituye a la actual.

## Pendiente

- **Pendiente:** el aviso del recordatorio. La pantalla sigue diciendo que se activará "cuando exista el programador de recordatorios". En 2da8bef el código del aviso ya existe: `services/calendar_reminders.py` genera el aviso `reminder.habit` («Hoy a las HH:MM», solo si el hábito programado no tiene registro ese día), `services/reminders.py` es el programador (ciclo de 60 s) y `modules/notifications/feed.ts` lo muestra. Pero `main.py` no arranca el programador ni la interfaz llama a `startNotificationFeed`, así que no sonará. Los avisos solo funcionan con Drakter abierto. Ver [recordatorios](recordatorios.md).
- Relacionado: [calendario](calendario.md), [tareas y proyectos](tareas-y-proyectos.md).
