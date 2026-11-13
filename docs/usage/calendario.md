# Calendario

> **Estado:** integrado en `drakter/integracion` (`2e05ba6`): pantalla **Calendario** en la navegación y API `calendar` montada. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

## Para qué sirve

Agenda con eventos, recordatorios, sesiones de trabajo, bloques de tiempo y las clases de [asignaturas](asignaturas.md), en vista diaria, semanal y mensual. Abre **Calendario** en la barra lateral (Ctrl+6). Empieza en la vista **Semana**.

## Moverte por la agenda

- **Día**, **Semana**, **Mes**: botones de vista.
- Flechas de anterior/siguiente, **Hoy** y el campo **Ir a la fecha**.
- Filtros **Filtrar por tipo**: Evento, Recordatorio, Sesión de trabajo, Bloque de tiempo, Clase. Un tipo tachado está oculto.
- En vista mes o semana, abrir un día lleva a su vista **Día**.

## Zona horaria

El selector **Zona horaria** de la barra (por defecto la del sistema) decide en qué zona ves la agenda. Cada evento guarda además su propia zona: se escribe la hora local en ella y el backend deriva el instante UTC.

- Una hora que no existe por cambio de horario se rechaza con "Esa hora local no existe en <zona> (cambio de horario). Elige otra hora."
- Una hora ambigua (se repite al retrasar el reloj) usa la primera.
- La ventana de consulta máxima es de 370 días (`window_too_large`).

## Crear un evento

1. Pulsa **Nuevo evento**.
2. **Título** (obligatorio), **Tipo** (Evento, Recordatorio, Sesión de trabajo), **Estado** (Confirmado, Provisional).
3. **Todo el día** o **Inicio** y **Final** (el final debe ser posterior).
4. **Zona horaria**.
5. **Repetición**: **Frecuencia** (Sin repetición, Diaria, Semanal, Mensual), **Cada** N días/semanas/meses, **Días de la semana** si es semanal, y **Termina**: Nunca, En una fecha (**Hasta**) o Tras un número de veces (**Veces**).
6. Opcional: **Lugar (opcional)**, **Aviso previo (opcional)** en minutos, **Descripción**.
7. **Crear evento**.

Al editar una serie, el diálogo avisa: "Los cambios afectan a toda la serie." Si la serie ya tiene excepciones, el backend rechaza cambiar su rango temporal (`conflict`).

## Recurrencia

Las series se calculan al leer, sobre la hora local, y no se guardan ocurrencia a ocurrencia. La fecha de inicio cuenta como primera ocurrencia. Reglas admitidas: DAILY, WEEKLY, MONTHLY y YEARLY con INTERVAL, COUNT, UNTIL, BYDAY y BYMONTHDAY; el editor ofrece solo Diaria, Semanal y Mensual.

## Bloques de tiempo

**Nuevo bloque** reserva un tramo: **Título**, **Inicio**, **Final**, **Zona horaria**, **Estado** (Planificado, En curso, Hecho, Omitido, Cancelado), **Tarea vinculada (opcional)** (por ahora se pega el ID de la tarea) y **Descripción**. Botón **Crear bloque**.

## Solapes

Guardar nunca se bloquea por solapes: aparece el aviso "Guardado, pero se solapa con ...", con la lista de elementos. Solo cuentan elementos con hora; no cuentan los de día completo, los recordatorios ni los cancelados, omitidos o hechos.

## Abrir, cancelar una ocurrencia y borrar

Pulsa un elemento para ver **Cuándo**, **Zona horaria**, **Lugar**, **Repetición**, etc.

- **Editar** (o **Editar serie**).
- **Cancelar solo esta ocurrencia**: solo en series. Es reversible y no pide confirmación.
- **Borrar** (o **Borrar toda la serie**): pide confirmación.
- Las clases son de solo lectura aquí: se gestionan desde Asignaturas.

## Qué pide confirmación

Borrar un evento o un bloque. El borrado abre "Confirmar acción" con el resumen y los elementos afectados; pulsa **Revisar** (o **Cerrar** para cancelar). Se abre entonces el diálogo nativo del proceso principal de Electron (`desktop/electron/main/approvals.ts`): título **Confirmar acción**, el resumen, «Elementos afectados: N» y los botones **Cancelar** (predeterminado) y **Aprobar**. Hasta que apruebes, no se borra nada. Si caduca: "La confirmación ha caducado. Inténtalo de nuevo." Si el elemento cambió: "El elemento ha cambiado; no se ha borrado. Recarga y vuelve a intentarlo."

## Problemas frecuentes

- **"El calendario no está conectado"**: el backend no responde; no se muestran datos de ejemplo. Usa **Reintentar**.
- **"La agenda tiene más elementos de los que se muestran en este periodo."**: acorta el periodo o filtra por tipo.
- **"Las confirmaciones aún no están disponibles; no se ha borrado nada."**: falta el puente de confirmaciones en Electron.

## Pendiente

- **Pendiente:** el aviso previo se guarda y el código de entrega existe (`services/reminders.py`, `services/calendar_reminders.py`, `repositories/notifications_due.py`, `modules/notifications/feed.ts`; avisos «Empieza a las HH:MM» o «El DD/MM, todo el día»), pero en 2da8bef el backend no arranca el programador ni la interfaz inicia el feed, así que no llegará ningún aviso. Solo funcionará con Drakter abierto. Ver [recordatorios](recordatorios.md).
- **Pendiente:** selector de tareas para el bloque. Sigue pidiendo pegar el ID (el formulario dice que el selector llegará con el módulo de tareas, que en 2da8bef solo tiene la pantalla vacía; ver [tareas y proyectos](tareas-y-proyectos.md)).
- Por chat existen `create_event`, `update_event`, `delete_event`, `create_event_exception`, `create_time_block`, `move_time_block` y otras (`backend/app/tools/calendar.py`). NO COMPROBADO.
