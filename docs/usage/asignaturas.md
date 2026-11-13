# Asignaturas

> **Estado:** integrado en `drakter/integracion` (`2e05ba6`): pantalla **Asignaturas** en la navegación y API `subjects` montada. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

## Para qué sirve

Guarda tus asignaturas con profesor, color, aula y clases semanales. Las clases aparecen en el [calendario](calendario.md) como "Clase" (solo lectura). Abre **Asignaturas** en la barra lateral (Ctrl+7).

## Crear una asignatura

1. Pulsa **Nueva asignatura**.
2. **Nombre** (obligatorio: "Escribe el nombre de la asignatura."), **Profesor o profesora**, **Descripción**.
3. **Color**: elige uno; pulsa de nuevo el elegido para quitarlo.
4. **Crear asignatura**.

La lista tiene dos vistas: **Asignaturas** y **Horario semanal** (con **Horario vigente el** para ver el horario de una fecha). El interruptor **Mostrar archivadas** incluye las archivadas.

## Añadir clases semanales

1. Abre la asignatura y pulsa **Añadir clase** (desactivado si está archivada).
2. Rellena **Día de la semana**, **Empieza**, **Termina**, **Aula**.
3. **Zona horaria**: nombre IANA, por ejemplo Europe/Madrid.
4. **Vigente desde** y **Hasta (opcional)**.
5. **Frecuencia**: Cada semana, Cada 2 semanas o Cada N semanas (**Número de semanas**, de 1 a 52).
6. **Añadir clase**.

Si la nueva clase se pisa con otra, la respuesta de creación incluye un aviso de conflictos (`conflicts`); no bloquea.

## Cancelar o cambiar una sola clase

En la fila de la clase, el botón **Cancelar o cambiar una clase del <día>** abre **Excepción de una clase**:

1. **Fecha de la clase** (debe caer dentro de la vigencia).
2. **Qué ocurre ese día**: "Se cancela la clase" o "Cambia la hora o el aula" (con **Nueva hora de inicio**, **Nueva hora de fin**, **Aula ese día**).
3. **Guardar excepción**. El resto de semanas no cambia.

## Editar y archivar

- **Editar** y **Archivar** / **Desarchivar** en el detalle de la asignatura.
- Las clases tienen sus propios **Editar** y **Eliminar**.

## Qué pide confirmación

- **Eliminar** una asignatura o **Eliminar** una clase abre "Confirmar acción"; pulsa **Revisar** y aprueba en el diálogo nativo de Electron (título **Confirmar acción**, resumen, «Elementos afectados: N», botones **Cancelar** y **Aprobar**; ver [calendario](calendario.md)).
- Si la asignatura tiene clases o tareas vinculadas, el borrado falla con conflicto y el diálogo ("No se puede eliminar la asignatura" / "No se puede eliminar la clase") ofrece **Archivar en su lugar**.
- Archivar y crear excepciones no piden confirmación.

## Problemas frecuentes

- **"Espacio de trabajo sin conexión"**: el backend no está conectado; no se muestra nada.
- **"Esa fecha queda fuera de la vigencia de la clase."**: elige una fecha entre **Vigente desde** y **Hasta**.
- **"La hora de fin debe ser posterior a la de inicio."**

## Pendiente

- **Pendiente:** recursos de la asignatura. En 2da8bef `GET /subjects/{id}/resources` sigue devolviendo siempre una lista vacía ("Vacío hasta que exista el módulo de relaciones"), y las pantallas de [relaciones](relaciones.md) y [almacén](almacen.md) son aún vacías.
- Las tareas vinculadas se gestionan en [tareas y proyectos](tareas-y-proyectos.md).
- Por chat: `create_subject`, `update_subject`, `list_subjects`, `create_class_session`, `create_schedule_exception` y otras (`backend/app/tools/subjects.py`). NO COMPROBADO.
