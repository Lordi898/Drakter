# Relaciones

> **Estado:** sale de la rama `drakter/almacen-relaciones`, sin integrar en `drakter/build` (2da8bef). En `drakter/build` (2da8bef) solo hay la migración `0006_relationships.sql` y una pantalla **Relaciones** vacía (`RelationshipsPage.tsx`: «Aún no hay relaciones»); no hay servicio ni API de relaciones. NO COMPROBADO en la app real: se ha leído el código de la rama (`desktop/src/modules/relationships/`, `backend/app/services/relations.py`).

Una relación es un vínculo entre dos elementos del espacio de trabajo: tareas, proyectos, hábitos, eventos, bloques de tiempo, asignaturas, clases, recursos y carpetas. Sirve para saber qué usa, qué depende de qué y qué apoya a qué.

## Dónde se ven
En la pantalla **Relaciones** (título: «Los vínculos entre tareas, proyectos, asignaturas, recursos y otros elementos del espacio de trabajo»). No hay panel de relaciones dentro de las pantallas de cada módulo en esta rama.
- **Lista de relaciones** (centro): cada fila con su tipo y sus dos extremos. **Cargar más** pagina.
- Filtros: **Tipo de relación** y **Tipo de elemento** (Todos por defecto).
- Panel **Relaciones del elemento** (derecha): al elegir un elemento muestra su título, su tipo y un mapa con hasta 12 vecinos; el resto, en la lista. Se agrupa en **Salientes** y **Entrantes**. Pulsar un vecino lo selecciona.
- Insignias: **Archivado** y **Estructural**. Una relación estructural viene de la propia estructura (tarea en un proyecto, carpeta dentro de otra) y no se puede borrar aquí.

## Cómo enlazar
1. Pulsa **Nueva relación** (arriba a la derecha).
2. En **Tipo de relación** elige uno. Nombres: pertenece a, relacionado con, programado para, usa el recurso, depende de, apoya a, estudia, es padre de, hace referencia a, deriva de.
3. Escribe **Origen (identificador)** y **Destino (identificador)**. Deben ser UUID válidos; si no, sale «Escribe un identificador válido (UUID).»
4. Pulsa **Crear relación**. Aviso: «Relación creada».

Reglas del servidor: cada tipo solo vale para ciertas parejas de tipos (por ejemplo `uses_resource` va de tarea, proyecto, asignatura, evento, clase u hábito hacia un recurso; `depends_on` solo entre tareas o entre proyectos). Si la pareja no está permitida, no se crea. «Relacionado con» es simétrica y no tiene dirección. `depends_on`, `parent_of` entre proyectos y `derived_from` entre recursos no admiten ciclos. No se enlaza con elementos archivados («Uno de los dos elementos está archivado...»).

## Eliminar una relación
1. Pulsa el icono de papelera de la fila en la lista o en el panel del elemento.
2. En **Eliminar relación** se muestra el vínculo; los dos elementos se conservan.
3. Pulsa **Eliminar**. Aviso: «Relación eliminada».

## Qué pide confirmación
- Desde la interfaz, eliminar una relación no pide aprobación (según el servidor, el usuario no pasa por la confirmación). El diálogo sí tiene el estado «Espera tu aprobación...» con **Reintentar** por si el servidor la exige.
- Si es el agente quien la elimina, sí necesita tu aprobación. Crear y editar relaciones desde el agente no la necesita.
- Eliminar un recurso con relaciones pide **Desvincular y eliminar** (ver [Almacén](almacen.md)).

## Con el agente
El agente tiene herramientas para consultar relaciones de un elemento, buscarlas, crearlas, editarlas y eliminarlas (esta con confirmación). Los títulos que devuelve son datos no confiables.

## Problemas frecuentes
- «Las relaciones aparecerán al conectar el espacio de trabajo»: no hay servicio local.
- «No se han podido cargar las relaciones.»: error de lectura; cambia de filtro o reintenta.
- «Esa relación ya existe.»: duplicada.
- «Esos dos elementos no se pueden vincular con ese tipo de relación.»: la pareja no está permitida.
- «Esa relación crearía un ciclo...»: el tipo no admite ciclos.

## Pendiente
- **Pendiente:** no hay selector de elementos; origen y destino se escriben como UUID y la interfaz no muestra un buscador por título.
- **Pendiente:** ver las relaciones desde la pantalla de cada módulo (tareas, proyectos...) no existe en esta rama.
- Enlaza con [Almacén](almacen.md) y [Tareas y proyectos](tareas-y-proyectos.md).
