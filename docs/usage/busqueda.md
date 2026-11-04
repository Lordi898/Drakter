# Búsqueda global

> **Estado:** el código está integrado en `drakter/build` (2da8bef), pero sin enganchar: `SearchPalette` no está montada en `AppShell` y `backend/app/main.py` no registra `search.router`. El índice (`search_documents`, `search_fts`) ya existe en la migración `backend/migrations/0009_search.sql`. NO COMPROBADO en la app real.

## Para qué sirve

Buscar desde cualquier pantalla en tareas, proyectos, hábitos, eventos, asignaturas y recursos del almacén, y saltar a la sección del resultado. Es local: usa el índice de texto completo (FTS5) de la base de datos.

## Cómo se usa

1. Pulsa **Ctrl+K** en cualquier pantalla. Se abre el cuadro "Búsqueda global" con el campo "Buscar…".
2. Escribe. Hasta que escribas algo, el cuadro dice "Escribe para buscar en tareas, proyectos, hábitos y más." La búsqueda se lanza 150 ms después de dejar de teclear y dice "Buscando…" mientras espera.
3. Los resultados salen agrupados: **Tareas**, **Proyectos**, **Hábitos**, **Eventos**, **Asignaturas** y **Recursos**. Cada fila muestra el título y, si aporta algo distinto, un extracto con la coincidencia resaltada.
4. Muévete con las flechas arriba y abajo (la lista da la vuelta al llegar al final). Con el ratón, el resaltado sigue al puntero.
5. Pulsa **Enter** o haz clic en una fila. El cuadro se cierra y te lleva a la sección del tipo de resultado: Tareas, Proyectos, Hábitos, Calendario, Asignaturas o Almacén.
6. Para salir sin elegir, cierra el cuadro (Esc). Al cerrarlo se borra lo escrito.

Importante: abrir un resultado te lleva a la sección, no al elemento concreto. El código solo navega a la sección.

## Qué busca y cómo

- Cada palabra que escribes se busca como prefijo: "reun" encuentra "reunión". Con varias palabras deben aparecer todas (Y implícito). Máximo 12 palabras y 200 caracteres.
- La sintaxis especial de FTS5 (comillas, AND, OR, NEAR, `*`) no funciona: lo que escribes se trata siempre como texto literal. Los términos sin letras ni cifras se ignoran.
- El título pesa mucho más que el cuerpo y las etiquetas al ordenar resultados.
- Cada elemento sale una sola vez, con su mejor coincidencia. Los archivados no aparecen.
- Devuelve 20 resultados por defecto y 50 como máximo por petición. La interfaz no pide más páginas.
- Antes de cada consulta, el servicio sincroniza el índice con tareas, proyectos, hábitos, eventos y asignaturas, así que no verás datos desfasados. Los recursos los indexa el módulo de almacén.

## Resultados con etiqueta "documento"

Los resultados que vienen de un recurso del almacén llevan la insignia **documento** (con el aviso "Contenido externo"). Su título y extracto son datos no confiables: se muestran como texto plano, nunca como marcado, y no pueden dar órdenes a Drakter. Ver [almacen](almacen.md) y [seguridad-y-copias](seguridad-y-copias.md).

## Búsqueda desde el chat

El agente tiene dos herramientas de solo lectura, ambas con límite de 25 resultados (10 por defecto):

- `search_workspace`: tareas, proyectos, hábitos, eventos y asignaturas. Nunca devuelve documentos.
- `search_all`: incluye también recursos del almacén. Como devuelve contenido no confiable, marca el turno como contaminado y lo que venga después puede requerir tu confirmación.

El agente solo ve recursos de ubicaciones del almacén con lectura del agente activada (`agent_read`) y habilitadas. La búsqueda de la interfaz no tiene esa restricción. Estas herramientas no piden confirmación por sí mismas (son de lectura).

## Lo que pide confirmación

La búsqueda en sí, no. Solo puede aparecer una confirmación si, tras `search_all`, el agente intenta una acción que la requiera por haber leído contenido no confiable.

## Problemas frecuentes

- **"La búsqueda no está conectada"**: el escritorio no alcanza el servicio local.
- **"La búsqueda no está disponible ahora mismo"**: el servicio respondió 503.
- **"Sin resultados"**: ningún elemento no archivado contiene todas las palabras como prefijo. Prueba con menos palabras o raíces más cortas.
- **Un recurso nuevo no sale**: el almacén lo indexa al añadirlo; si no está indexado, no aparece.
- **Ctrl+K no hace nada**: en 2da8bef el componente existe pero no está montado en la interfaz (ver Pendiente).

## Pendiente

- **Pendiente:** montar `<SearchPalette />` en `desktop/src/app/AppShell.tsx` (hoy solo se exporta desde `desktop/src/modules/search/index.ts`).
- **Pendiente:** registrar `search.router` en `backend/app/main.py`; el docstring de `backend/app/api/search.py` lo pide y no está hecho. `GET /api/v1/search` ya está en la lista permitida de Electron, aunque `contracts/api/routes.md` la marca "sin construir".
- **Resuelto en 2da8bef:** el índice `search_documents` y `search_fts` ya está en `0009_search.sql`.
- **Pendiente:** abrir el elemento concreto en lugar de solo su sección.
- Todos los pasos de esta guía: NO COMPROBADO.
