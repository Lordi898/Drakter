# Confirmaciones y seguridad

Drakter pide tu confirmación antes de lo destructivo, registra lo que hace el agente y no le deja tocar sus propios permisos. Las copias de seguridad están en [Copias y actualización](copias-y-actualizacion.md).

## Confirmaciones

Piden confirmación: el borrado definitivo, las operaciones masivas (por encima del ajuste `bulk_threshold`), los cambios de configuración sensible, olvidar o aprobar recuerdos y las escrituras de un turno contaminado por contenido no confiable (un documento o una web que leyó el agente).

1. En el chat aparece **«Drakter necesita tu confirmación»**, con un temporizador y el botón **Revisar**.
2. **Revisar** abre el diálogo del sistema **«Confirmar acción»**, con el resumen («Vas a eliminar 1 tarea: «…». Esta acción no se puede deshacer.»), los elementos afectados y, si lo hay, el riesgo. **Cancelar** es la opción por defecto; **Aprobar** la ejecuta.
3. Al aprobar se ejecuta exactamente lo que se pidió, una sola vez. Si los elementos cambiaron entretanto: «Los elementos han cambiado; la acción no se ha ejecutado.»
4. Caduca a los 5 minutos: una confirmación caducada no se ejecuta nunca.

**Nunca por voz:** decir «sí» no confirma. Drakter avisa («Necesito su confirmación en pantalla») y trae la ventana al frente. El agente tampoco puede aprobar ni rechazar: su credencial no vale para esa ruta.

## Permisos

Cada herramienta tiene un permiso (`tasks.write`, `storage.read`…) y un riesgo (`read`, `write` o `confirm`). El agente no puede, ni con confirmación: ampliar sus permisos, alterar la auditoría, gestionar las carpetas permitidas del almacén ni ejecutar comandos. Las carpetas permitidas del almacén solo se cambian desde la interfaz.

## Auditoría

Cada llamada del agente a una herramienta (también las lecturas) queda en la tabla `audit_events` de la base, sin contenido de documentos ni claves. El registro solo se añade, nunca se edita. Aún no hay pantalla para consultarlo.

## Datos no confiables

Lo que Drakter lee de tus documentos, de la web o de su memoria es **información, no órdenes**: no puede cambiar sus instrucciones ni sus reglas de seguridad. Si un documento dice «borra todo», Drakter no lo hace, y lo que proponga en ese turno pasa por confirmación.
