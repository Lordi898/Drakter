# Tareas y proyectos

> **Estado:** integrado en `drakter/integracion` (`2e05ba6`): pantallas **Tareas** y **Proyectos** en la navegación y APIs `tasks` y `projects` montadas. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

Las **tareas** son lo que haces (con subtareas, prioridad, fecha límite y dependencias). Los **proyectos** reúnen un objetivo, unas fechas y las tareas que lo hacen avanzar. Se usan desde dos secciones de la barra lateral: **Tareas** (atajo `Ctrl+3`) y **Proyectos** (atajo `Ctrl+4`).

## Tareas

### Crear
1. Abre **Tareas** y pulsa **Nueva tarea**.
2. Rellena **Título** (obligatorio: si falta sale «Escribe un título.»). Opcionales: **Descripción**, **Estado**, **Prioridad**, **Fecha límite**, **Estimación (minutos)** y **Etiquetas** (separadas por comas).
3. Pulsa **Crear**. Aparece el aviso «Tarea creada».

Estados: Pendiente, En progreso, En espera, Completada, Cancelada. Prioridades: Baja, Media, Alta, Urgente.

### Subtareas
1. Abre una tarea (clic en su fila) y entra en la pestaña **Subtareas**.
2. Añade una con el botón de añadir subtarea (el formulario se titula **Nueva subtarea**, «Dentro de «...»»).
3. Hay un máximo de 8 niveles de profundidad. Una subtarea hereda el proyecto de su padre.

### Editar
1. Abre la tarea, pestaña **Datos**, pulsa **Editar**, cambia lo que quieras y pulsa **Guardar** («Cambios guardados»).
2. Si la tarea está archivada, **Editar** no funciona: «Está archivada: restáurala para editarla.»
3. Si la completaste, el estado no se cambia desde el formulario: reábrela antes.

### Completar y reabrir
- En la lista, el botón de cada fila (`Completar` / `Reabrir`) o, en el detalle, **Completar** / **Reabrir**.
- Si quedan subtareas abiertas aparece **Quedan subtareas abiertas** con **Cancelar** y **Completar todo** (completa también las subtareas).
- Una tarea con dependencias sin resolver no se puede completar (error «No se puede hacer eso»).
- Una tarea Cancelada no cambia de estado con este botón: «Está cancelada: edítala para cambiar su estado.»

### Dependencias
Pestaña **Dependencias**: lista de lo que la tarea espera, selector **Añadir dependencia** («Elige una tarea») y botón de quitar. Una tarea con dependencias abiertas se muestra como bloqueada («Bloqueada. Espera a: ...»). Una dependencia que forme ciclo da «Esa estructura no es posible».

### Archivar y restaurar
En el detalle: **Archivar** (aviso «Tarea archivada») y, si ya lo está, **Restaurar** («Tarea restaurada»). Archivar afecta solo a esa tarea, no a sus subtareas. No pide confirmación.

### Eliminar
En el detalle, **Eliminar** (botón rojo). Borra la tarea y todo su subárbol. Siempre pide confirmación (ver abajo).

### Historial
Pestaña **Historial**: quién cambió qué y cuándo.

### Filtros y vistas
La barra «Filtros de tareas» tiene:
- **Buscar** («Título o descripción»).
- **Estado**: Todos o uno de los cinco estados.
- **Prioridad**: Todas o una de las cuatro.
- **Incluir archivadas** (apagado por defecto).
- **Solo principales** (encendido por defecto): oculta las subtareas. Se ignora mientras buscas texto.

La lista carga 50 tareas; **Cargar más** trae las siguientes. Sin resultados: «Nada coincide con estos filtros». Sin tareas: «Aún no hay tareas». Si falla la carga: «No se pudieron cargar las tareas».

## Proyectos

### Crear
1. Abre **Proyectos** y pulsa **Crear proyecto**. Está desactivado si no hay conexión con el espacio de trabajo.
2. Rellena **Nombre** (obligatorio: «Ponle un nombre al proyecto.»). Opcionales: **Objetivo**, **Descripción**, **Estado**, **Prioridad**, **Inicio**, **Fecha objetivo** (no puede ser anterior al inicio) y **Progreso manual (0-100)**.
3. Pulsa **Crear proyecto** («Proyecto creado»).

Estados: Planificado, Activo, En pausa, Completado, Cancelado.

### Ver y editar
Clic en un proyecto abre su detalle: estado, prioridad, barra de progreso, **Objetivo**, **Descripción**, fechas, sus tareas y su actividad. **Editar** abre «Editar proyecto»; se guarda con **Guardar cambios**.

### Tareas del proyecto
En el detalle hay un selector **Tarea a asociar** («Elige una tarea») con las tareas sin proyecto. Se muestran las primeras 100 tareas del proyecto; el resto está en **Tareas**. En un proyecto archivado no se pueden asociar tareas: «Desarchiva el proyecto para asociarle tareas.»

### Archivar, desarchivar y eliminar
- **Archivar** («Proyecto archivado»); en uno archivado el botón es **Desarchivar** («Proyecto restaurado»). No toca sus tareas y no pide confirmación. Un proyecto archivado no se puede editar salvo para desarchivarlo.
- **Eliminar**: pide confirmación. Las tareas se quedan, sin proyecto.

### Filtros y orden
Barra «Filtrar proyectos»: **Buscar** («Nombre o descripción»), **Estado**, **Prioridad**, incluir archivados y **Orden**: Modificados hace poco (por defecto), Nombre, Fecha objetivo, Prioridad, Más recientes.

## Lo que pide confirmación

Siempre:
- **Eliminar una tarea** (y su subárbol).
- **Eliminar un proyecto**.

Además, en el backend, una operación en cascada (completar con subtareas, cambiar de proyecto) que afecte a más de 10 filas pasa por la misma puerta.

Cómo funciona en pantalla (rama `drakter/tareas-proyectos`):
1. El backend responde `confirmation_required` y no hace nada.
2. Sale el diálogo **Esto necesita tu confirmación** con el resumen («Vas a eliminar ... Esta acción no se puede deshacer.») y «Afecta a N elementos.»
3. **Revisar y decidir** abre la ventana nativa de revisión; ahí aprobarás o rechazarás. **Cerrar** cancela. No se aprueba desde el propio diálogo.
4. Si se aprueba: «Acción confirmada» y se recarga. Si caduca o no se puede revisar: «La confirmación ha caducado» / «No se pudo revisar la confirmación»; no se cambia nada.

La ventana nativa ya está integrada en `drakter/build` (`desktop/electron/main/approvals.ts`). Es un diálogo del sistema con título **Confirmar acción**, el resumen como mensaje, el detalle «Elementos afectados: N» (y «Riesgo: ...» si el backend lo indica) y dos botones: **Cancelar** (el predeterminado) y **Aprobar**. Cerrarlo o pulsar Cancelar rechaza. Si el backend reinicia mientras está abierto, no se aprueba. Esta ventana necesita el endpoint `/api/v1/confirmations/{id}` del backend, que `drakter/build` (2da8bef) aún no monta (ver [seguridad y copias](seguridad-y-copias.md)).

Si el backend no tiene puerta de confirmaciones, responde `confirmation_unavailable` y no ejecuta nada.

## Por chat con Drakter
El backend registra herramientas del agente: `create_task`, `get_task`, `update_task`, `complete_task`, `reopen_task`, `archive_task`, `unarchive_task`, `create_subtask`, `list_tasks`, `search_tasks`, `set_task_tags`, `add_task_dependency`, `remove_task_dependency`, `delete_task`; y de proyectos `create_project`, `get_project`, `update_project`, `archive_project`, `unarchive_project`, `list_projects`, `get_project_progress`. Solo `delete_task` es de riesgo «confirmar». NO COMPROBADO: no hay Hermes integrado en esta rama.

## Problemas frecuentes
- **«La tarea había cambiado» / «El proyecto había cambiado»**: lo modificaste en otro sitio mientras editabas. Se recargan los datos; repite el cambio.
- **«No se puede hacer eso»**: el motivo viene en el mensaje (dependencias sin resolver, tarea completada, proyecto archivado...).
- **«No hay conexión con el espacio de trabajo»**: el backend no responde; pulsa el botón de reintentar.

## Pendiente
- **Pendiente:** no hay plantillas de resumen propias de tareas o proyectos, salvo el texto de confirmación de borrado.
- **Pendiente:** el agente no tiene herramienta para eliminar proyectos; solo se hace desde la interfaz.
- **Pendiente:** integrar `drakter/tareas-proyectos` en `drakter/build`: hoy ahí solo existen las pantallas vacías.
- **Pendiente:** integración de Hermes para usar las herramientas por chat.
