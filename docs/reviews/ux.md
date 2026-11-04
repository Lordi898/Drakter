# Revisión independiente de experiencia

Fecha: 2026-11-04. Autor: sesión `drakter-28`, con 12 revisores de solo lectura.

**Todo es revisión estática.** Nadie ha abierto la app, ni usado un lector de pantalla, ni medido nada en pantalla. Las razones de contraste sí están calculadas con la fórmula WCAG a partir de los tokens. Lo marcado PLAUSIBLE depende de algo que no se ve en el código. **Ningún hallazgo prueba que algo funcione en ejecución.**

## Hashes

Las ramas se movieron durante la revisión. Los P1 de abajo se comprobaron a mano contra estos hashes:

| Rama | Hash | Rama | Hash |
|---|---|---|---|
| `drakter/build` | `bb845ec` | `drakter/almacen-relaciones` | `e976abd` |
| `drakter/tareas-proyectos` | `b90be85` | `drakter/hoy-ajustes` | `68bebef` |
| `drakter/habitos-calendario` | `aa13f10` | `drakter/seguridad` | `05861f9` |
| `drakter/chat-personaje` | `9db91bd` | `drakter/contratos` | `8c259ca` |

Los P2 y P3 de pantallas vienen de una pasada sobre hashes algo anteriores (`8333d25`, `2cf4136`, `9eb67ec`, `6228c20`, `2bd52e3`). **Sus números de línea pueden haber cambiado y algunos pueden estar ya corregidos.** Busca por el nombre del archivo y la cita antes de aplicar.

## Severidad

- **P1:** engaña al usuario, le bloquea o pierde lo que escribió.
- **P2:** fricción real o fallo WCAG A/AA.
- **P3:** pulido.

## Veredicto

La base es honesta y los dueños ya corrigieron lo más grave que salió durante la revisión. Quedan 8 P1 abiertos. Los problemas de fondo que siguen abiertos son tres:

1. **El modo simulado no se ve donde se conversa.**
2. **Se pierde trabajo del usuario** en formularios y detalles al recargar o cerrar.
3. **Faltan patrones comunes:** diálogo de confirmación, estado de error, «sin conexión», foco tras una acción. Cada módulo lo resuelve a su manera y repite los mismos fallos.

La capa base de escritorio aún no ha recibido los arreglos de contraste y foco: siguen sin aplicarse en `bb845ec`.

## P1 abiertos

| # | Dónde | Problema y efecto | Arreglo | Dueño |
|---|---|---|---|---|
| 1 | `desktop/src/chat/*`, `pages/HomePage.tsx`, `components/status/DrakterStatus.tsx`. Aviso solo en `settings/AgentStatusSection.tsx:13` | **Sin aviso SIMULADO en el chat, en Inicio ni en la barra**, que dice «Disponible». El usuario conversa con respuestas inventadas sin saberlo si no abre Ajustes | Franja fija sobre el chat y en Inicio, y estado «Simulado» en la barra. El store debe leer `dev_mode` | `chat-personaje` |
| 2 | `desktop/electron/shared/routes.generated.ts` (build) y `contracts/api/routes.md`: no incluyen `/today`. `pages/today/requests.ts:10` lo pide. La ruta existe en `backend/app/api/today.py:28` | **Hoy aparenta estar sin conexión** con el servicio funcionando, porque el proxy rechaza la ruta | Añadir `/today` al contrato y regenerar | `contratos`, luego integración |
| 3 | `backend/app/services/projects.py:280-292` | **La confirmación de eliminar proyecto miente:** dice «y N dependientes», pero las tareas se sueltan, no se eliminan. Con proyecto vacío, `affected_count` es 0: «Afecta a 0 elementos» | `Vas a eliminar 1 proyecto: «{nombre}». Sus {n} tareas se conservan, sin proyecto. Esta acción no se puede deshacer.` con `affected_count = 1 + n` | `tareas-proyectos` |
| 4 | `modules/relationships/CreateRelationshipDialog.tsx:104,113` | **Crear una relación exige teclear dos UUID** que la interfaz no muestra. La acción principal del módulo no se puede usar | Selector con búsqueda por título | `almacen-relaciones` |
| 5 | `modules/projects/ProjectForm.tsx:147-154` | **Un conflicto de revisión cierra el formulario y pierde lo escrito** (hasta 10 000 caracteres). `TaskForm` sí se queda abierto | No cerrar: conservar valores y avisar «El proyecto cambió mientras lo editabas. Revisa los datos y vuelve a guardar.» | `tareas-proyectos` |
| 6 | `modules/storage/ResourceDetail.tsx:37-40` (`apply`) | **Añadir una etiqueta o actualizar el índice borra la descripción sin guardar** | Reponer la descripción solo si no hay cambios pendientes | `almacen-relaciones` |
| 7 | `modules/subjects/SubjectsPage.tsx:119,126,150` | **Si solo quedan asignaturas archivadas, se ocultan el interruptor y la lista:** sale «Todavía no hay asignaturas» y no se puede desarchivar | Mostrar el interruptor siempre, o avisar «Tienes N archivadas» | `habitos-calendario` |
| 8 | `modules/subjects/ExceptionDialog.tsx`, `modules/subjects/api.ts:56` (solo POST) | **Una excepción de clase no se puede ver ni deshacer** | Listar excepciones con «Quitar», o avisar antes de crearla | `habitos-calendario` |

## Corregido durante la revisión

Comprobado por lectura en los hashes de arriba. **Ninguno se ha ejecutado.**

| Antes | Estado |
|---|---|
| Cuatro clientes de backend incompatibles (`tasks/client.ts`, `workspaceClient.ts`, `storage/backend.ts`, `services/api.ts`) | Convergen en `services/api.ts` |
| Tres formas REST de confirmar; el 202 de asignaturas se leía como éxito | 409 común, según la comprobación del revisor de cruce |
| Evento `agent.confirmation_required` obsoleto: el aviso de confirmación no aparecía | `stores/confirmations.ts:106` usa `confirmation.requested` |
| Main y seguridad no coincidían en cómo aprobar | Alineados: token `approver` y `params_hash` (`approvals.ts:119-122`, `api/confirmations.py:72`) |
| Eliminar una relación desde la GUI saltaba el pipeline | `relations.py` llama siempre a `deps.gate.require` |
| Ubicaciones del almacén sin alta posible | Selector nativo en `main/storageRoots.ts`; `storage/bridge.ts` usa `window.api.addStorageLocation` |
| `fetchToday` sin usar | Lo usa `pages/today/useToday.ts` |
| Turno bloqueado en «Detener» | `stores/chat.ts:176` trata `agent.turn_finished` |
| Parpadeo de 8-25 Hz en el personaje | `rig.ts:523`: `rand(0.35, 0.8)` |
| Identidad: pedir «¿Adelante?», `viking_*`, «En la guarida no se pierde nada», «Lo compruebo cuando vuelva» | Corregidos en `build`, ver abajo |

## P2 de la capa común

Afectan a toda la app. Sin aplicar en `build` `bb845ec`. Dueño: base de escritorio.

| Dónde | Problema | Arreglo |
|---|---|---|
| `styles/globals.css:47,155` | **Foco casi invisible en tema claro:** ámbar 1,66:1 sobre fondo, 1,82 sobre tarjeta; `ring/50` 1,30. Mínimo 3:1 | `--ring: #1f4e85` en `:root` (7,22 y 7,92), `outline` con `var(--ring)`, `ring-ring` sin alfa. Ámbar solo en `.dark` (9,40) y chasis (7,73) |
| `button`, `switch`, `select`, `textarea`, `scroll-area` | `outline-none` anula el foco global y no queda nada en alto contraste. No hay ningún `@media (forced-colors)` | `outline-hidden` y bloque `forced-colors` con `Highlight` |
| `globals.css:46,80` | Borde de control: 1,65:1 en claro, 2,80:1 en oscuro. Afecta a campos, selectores e interruptores | `#6a869f` (3,25) y `#5a86b5` (4,80) |
| `globals.css:19,49` | Texto `success` 4,22:1 y `warning` 4,04:1 en claro | `#236b5a` (5,40) y `#855908` (5,23) |
| `ui/dialog.tsx:76,114` | «Close» en inglés en todos los diálogos | «Cerrar» |
| `ui/dialog.tsx:73` | Botón de cierre de 16 px | `p-1.5` |
| `ui/switch.tsx:17` | PLAUSIBLE: interruptor de 18 px | Área de pulsación de 24 px |
| `app/AppShell.tsx:65-67` | Sin foco, anuncio ni título al cambiar de sección, y sin «Saltar al contenido» | `main` con `tabIndex={-1}`, foco, enlace y `document.title` |
| `services/errors.ts:44-50` | Avisos con el mensaje crudo del fallo, normalmente en inglés | Texto fijo: «Algo ha fallado en Drakter. Si se repite, reinicia Drakter.» |
| `components/EmptyState.tsx:28-29` | Botón `disabled` sin foco y motivo sin enlazar | `aria-disabled`, `aria-describedby`, `useId` |
| `backend/app/core/errors.py:134` | Los `ValueError` de validadores llegan como «Invalid value». Se pierden textos propios. El filtro existe para no reflejar la entrada: no quitarlo | Lista blanca de `PydanticCustomError` propios |
| `core/errors.py:158,178,198`, `api/health.py:22`, `api/today.py:36`, `core/security.py:99-102` | Inglés visible en la interfaz | «Algunos datos no son válidos. Revisa los campos marcados.», «Algo ha fallado dentro de Drakter. Vuelve a intentarlo.», «Drakter todavía no está listo. Espera unos segundos y reintenta.», «La sesión no es válida; reinicia Drakter.» |

## P2 entre módulos

| Tema | Evidencia | Arreglo |
|---|---|---|
| Control de revisión | `modules/calendar/workspaceApi.ts:32`: «main aún no la reenvía, así que el control no está activo». `bridge.ts` ya declara `ApiCallOptions`, y tareas usa `?revision=`. **Verificar al integrar:** sin esto, Drakter y el usuario se pisan sin aviso | Un solo mecanismo |
| Diálogos de confirmación | Tres componentes con títulos y botones distintos: «Esto necesita tu confirmación», «Confirmar acción», «¿Eliminar «x» del almacén?» | `components/ConfirmationDialog` común |
| Verbo destructivo | «Eliminar», «Borrar» (`OccurrenceDialog.tsx`) y «Quitar» (`LocationsPanel.tsx:134,155,163`). El contrato pide «eliminar» | Unificar |
| «Sin conexión» | Cinco textos distintos. `habits/BackendState.tsx:12` dice «backend» al usuario | Un solo componente de estado |
| `Sin conexión` en almacén | `storage/errors.ts:31-34`, `relationships/api.ts:70-72` comparan códigos que `window.api` ya no emite. Con el servicio caído sale un error genérico | `error.status === 0` |
| Aviso tras aprobar | Calendario y asignaturas no avisan de nada; tareas dice «Acción confirmada» sin decir qué | Aviso que nombre lo eliminado |
| Resumen de relación | `relations.py:153-155` en inglés, fuera de la plantilla | Plantilla de `contracts/README.md` §5 |
| Serie de eventos | «Borrar toda la serie» lleva a un resumen que no dice «serie» (`OccurrenceDialog.tsx`, `calendar.py`) | `kind="serie de eventos"` |
| Ubicación con recursos | `LocationsPanel.tsx:157` promete quitar «la ubicación y sus recursos», pero el backend lo rechaza con «Tiene relaciones con otros elementos.» | Mensaje propio y diálogo honesto |
| Árboles falsos | `role="tree"` sin teclado en `tasks/SubtasksTab.tsx:29`, `storage/FolderTree.tsx:43`; `role="grid"` sin flechas en `habits/HabitHistoryGrid.tsx:46` | Listas anidadas o patrón completo |
| Cerrar sin avisar | `tasks/TaskForm.tsx:42`, `projects/ProjectForm.tsx:110`, `calendar/EventDialog.tsx:168`, `calendar/TimeBlockDialog.tsx:119` | «Hay cambios sin guardar. ¿Descartarlos?» |

## P2 por módulo

### Tareas y proyectos

- `tasks/useTasks.ts:34`, `TasksPage.tsx:70-73`: cada acción vacía la lista, y se pierden foco y scroll. Conservar la lista con `aria-busy`, como `ProjectsPage.tsx:122`.
- `tasks/useTasks.ts:64`: si falla «Cargar más», se borra lo ya cargado.
- `tasks/TasksPage.tsx:22`: «Solo principales» sigue activo mientras la búsqueda lo ignora.
- `tasks/TaskFilters.tsx:57`: sin espera entre teclas; `ProjectFilters.tsx:77-81` sí la tiene.
- `tasks/TaskForm.tsx:94-99`: el foco no va al primer error, y los minutos no se validan.
- `tasks/TaskForm.tsx:103-128`: los errores de campo del servidor acaban en un aviso.
- `tasks/TaskForm.tsx:123-126`: guardado parcial. Si fallan las etiquetas, dice que falló todo.
- `tasks/TaskDetailDialog.tsx:77-91`: `outline-none` oculta el foco en las pestañas.
- `tasks/TaskDetailDialog.tsx:85,89`: no hay forma de volver a la tarea madre.
- `tasks/format.ts:129-131`, `projects/ProjectActivity.tsx:64-66`: frases rotas como «pidió confirmación para eliminó la tarea». Usar tablas de infinitivo y pretérito.
- `tasks/useTaskRunner.ts:34-38`: «Alguien la modificó», en una app de un solo usuario. Usar «La tarea cambió desde que la abriste (quizá por Drakter).».
- `tasks/TaskRow.tsx:25`, `projects/ProjectDetail.tsx:99-113`: sin protección contra doble clic.
- `tasks/DependenciesTab.tsx:26`, `projects/ProjectTasks.tsx:121`: límite de 100 sin avisar. El aviso usa `total`, que no existe.
- `projects/ProjectsPage.tsx:94-105,126-130`: botón que parece activo y no actúa, motivo solo para lectores, y sin «Quitar filtros».
- `projects/ProjectsPage.tsx:86-88`: foco perdido al volver al listado.
- PLAUSIBLE: comprobar que tras aprobar un borrado diferido se cierra el detalle (`TasksPage.tsx:42`).
- PLAUSIBLE: `ProjectTasks.tsx:93` frente a `ProjectProgressBar.tsx:30`, recuentos distintos.

### Calendario

- `useAgenda.ts:20`, `CalendarPage.tsx:47`: la rejilla se vacía en cada recarga y el foco se pierde.
- `useAgenda.ts:21`: `fetchOverlaps(...).catch(() => [])` deja la agenda sin aviso de conflicto si falla, sin decirlo.
- `TimeGrid.tsx:78-87`, `MonthView.tsx:38-45`: sin rejilla por teclado; crear a una hora concreta solo con clic.
- `MonthView.tsx:38-45,57-64`, `OccurrenceChip.tsx:21`: los chips no dicen el día.
- `TimeGrid.tsx:42,82`, `MonthView.tsx:43,52`: hoy marcado solo con color. Añadir `aria-current="date"`.
- `TimeGrid.tsx:102-103`, `layout.ts:34-57`: solapes ilegibles sin límite de carriles.
- `CalendarPage.tsx:158-161`: agenda truncada sin salida, y filtro que deja la rejilla vacía sin explicación.
- `TimeGrid.tsx:25,64`: eventos fuera de la vista sin indicador.
- `EventDialog.tsx:130-137,296`, `TimeBlockDialog.tsx:90-93,165`: errores al final del formulario, sin campo asociado.
- **`EventDialog.tsx:86`: editar un evento cancelado lo confirma en silencio.** Es el peor de este bloque.
- `OccurrenceDialog.tsx:115-128`: cancelar una ocurrencia no tiene confirmación ni restauración.
- `OccurrenceDialog.tsx:130-136`: no existe «solo esta» ni «esta y siguientes», ni se dice cuántas ocurrencias.
- `TimeBlockDialog.tsx:159-160`: pide un UUID de tarea.
- `recurrence.ts:84`, `EventDialog.tsx:230`: RRULE cruda en pantalla.
- PLAUSIBLE: `MonthView.tsx:41`, «+N más» cortado.
- PLAUSIBLE: `OccurrenceDialog.tsx:72-73`, rótulo de zona horaria que no corresponde a la hora mostrada.

### Hábitos y asignaturas

- `HabitHistoryGrid.tsx:15-22`: el estado solo se distingue por color (WCAG 1.4.1, nivel A). Añadir iconos.
- `HabitHistoryGrid.tsx:46-69`: hasta 180 paradas de tabulación.
- `QuickMark.tsx:21-38`, `api.ts:33-34`: no se puede volver a «sin registro». Un clic erróneo queda como dato.
- `QuickMark.tsx:31`: `disabled` tira el foco. Sin anuncio del resultado.
- `HabitsPage.tsx:128-132`: el error no dice qué hábito falló.
- `HabitDetail.tsx:40-42,194-198`, `HabitStats.tsx:22-29`: cifras sin periodo. PLAUSIBLE: rachas acotadas a la ventana.
- `HabitStats.tsx:25-29`: el pie de «Sin registrar» lista otras categorías.
- `rrule.ts:62-63`, `HabitDialog.tsx:171`: RRULE cruda en hábitos creados por el agente.
- `HabitDialog.tsx:57-63`: error visible nada más abrir.
- `HabitDialog.tsx:190-198`, `SessionDialog.tsx:119-121`: zona horaria como lista IANA o texto libre.
- `useDeletion.tsx:60-66`: la confirmación no dice que se pierden clases y excepciones. Usar «Si solo quieres ocultarla, archívala.».
- `SubjectDetail.tsx:135-141`: nombres accesibles repetidos y sin el texto visible (WCAG 2.5.3).
- `ExceptionDialog.tsx:42-45,87-89`: hay que adivinar una fecha válida. Ofrecer las próximas ocurrencias.
- `SubjectsPage.tsx:35-48,58-66`: reintentar no da señal, y archivar salta a otro elemento sin avisar.

### Almacén y relaciones

- `storage/LocationsPanel.tsx:143-145`: **«Permitir que Drakter lea esta ubicación» se activa al instante**, sin decir que incluye subcarpetas ni que el texto va al modelo. Añadir ayuda fija y confirmar al activar.
- `storage/FolderTree.tsx:22,42`: un error de red se muestra como «Aún no hay carpetas».
- `storage/ResourceList.tsx:45,85-91`: la búsqueda ignora la carpeta y puede ocultar «Cargar más».
- `storage/ResourceList.tsx:74,77`: al fallar un filtro sigue la lista anterior como si fuese la nueva.
- `storage/ResourceDetail.tsx:148-150,167`: `missing` sin explicación, «Leer» sigue activo y `index_error_code` crudo.
- `storage/ResourceDetail.tsx:129`: «No se ha podido cargar» sin Reintentar ni Cerrar.
- `storage/ResourceDetail.tsx:301-326`, `LocationsPanel.tsx:152-158`: no dicen cuántos elementos afectan.
- `storage/ResourceDetail.tsx:288`: `<pre>` con scroll sin foco (WCAG 2.1.1).
- `storage/ResourceDetail.tsx:224-227`: botón de 16 px.
- `storage/StoragePage.tsx:128`: `<main>` dentro de `<main>`.
- `storage/StoragePage.tsx:129-139`: el foco no acompaña al detalle.
- `storage/CreateResourceDialog.tsx:76,117-135`: no deja claro que no se sube nada. Texto: «No se copia ni se sube: se añade al catálogo un archivo que ya está en una ubicación».
- `storage/CreateResourceDialog.tsx:139`: «Añadir» deshabilitado sin motivo.
- `relationships/RelationshipsPage.tsx:113-115,152,168`: **lista y borrado con fragmentos de UUID**, sin títulos. `RelatedPanel.tsx:117` ya lo hace bien.
- `relationships/RelationshipsPage.tsx:100-102`: error sin Reintentar.
- `relationships/RelationGraph.tsx:34-40`: etiquetas de 9 px recortadas, sin leyenda.
- PLAUSIBLE: `ResourceDetail.tsx:267-276`, archivar sin vía de restaurar.
- PLAUSIBLE: nombres de archivo sin aislamiento bidi. Son datos no confiables: un U+202E puede disfrazar una extensión. Usar `<bdi dir="auto">`.

### Hoy, Ajustes y chat

- `settings/BackupsSection.tsx:40-51`: **dice «No se pudo crear la copia» aunque se haya creado**, si falla la relectura de la lista.
- `chat/ChatComposer.tsx:24,28,39-41`: Enter no hace nada y no avisa mientras Drakter responde.
- `chat/ChatComposer.tsx:48-52`: los avisos no se anuncian (WCAG 4.1.3).
- `chat/ConfirmationDialog.tsx:49-67`: no dice que un «sí» en el chat no aprueba. Texto: «Para aprobar, pulsa Revisar. Responder en el chat no aprueba nada.». Tampoco queda rastro del resultado.
- `stores/chat.ts:37,221`: el motivo del fallo del turno siempre es genérico. Usar `CODE_MESSAGES`.
- `stores/agent.ts`: «sin conexión» igual al arrancar, reconectar y caer.
- `settings/SettingsPage.tsx`, `services/notify.ts:16-23`: la notificación de prueba calla si falla el aviso de escritorio. PLAUSIBLE.
- PLAUSIBLE: `chat/ChatTranscript.tsx:123-134`, streaming con lector de pantalla. Probar con Orca.

## Identidad

Hay honestidad de base: se presenta como IA, sin datos personales inventados en las plantillas ni afirmaciones de conciencia. El orden de prioridad coincide con el plan.

**Corregido en `build` `bb845ec`:** pedir aprobación por chat o voz, `viking_*`, «En la guarida no se pierde nada», «Lo compruebo cuando vuelva», `get_subjects`, «Si lo subes», y la lista de confirmaciones de `agent/knowledge/CAPABILITIES.md:43`.

**Abierto:**

- **P1 PLAUSIBLE, `agent/context/ENVIRONMENT.md`:** «Local-first» sin decir que la conversación y lo leído se envían al proveedor del modelo. A «¿esto sale de mi equipo?», Drakter contestaría que no. Añadir: «El razonamiento no es local: la conversación y lo que lees para responder, documentos incluidos, se envían al proveedor del modelo configurado.».
- **P2, canal expresivo:** `EMOTIONAL_STYLE.md` describe campos sin canal. El JSON acabaría en el texto, incluso en voz, y `receiver.ts` descarta `confused` y `calm`.
- **P2, sin señal de voz:** `TurnRequest` no lleva el origen del turno, así que la identidad no sabe si responde por voz.
- **P2, tamaño:** la identidad sumaba 21.130 caracteres frente al tope de 19.000 del borrador del plan. Puede haber cambiado al mover archivos. Las reglas de confirmación no deben caer en un recorte.
- **P2, barreras:** las garantías se describen en presente. Conviene bloquear el arranque con agente real hasta conectar la puerta de permisos.
- **Repetir** la comparación de nombres de herramientas cuando exista `contracts/tools/catalog.json`.

## P3 agrupados

- **Vocabulario:** «Aún no hay» frente a «Todavía no hay» (`TasksPage.tsx:86`, `SubjectsPage.tsx:121`); «Nuevo» frente a «Crear»; «carpeta» para dos cosas; cuatro nombres para reindexar; «vecinos»; `tool.name` crudo en el chat.
- **Atajos:** `useAppShortcuts.ts:19` consume AltGr+º en Windows porque el filtro de `altKey` va después (línea 25). En Linux no ocurre. Además traga el atajo con el panel no disponible.
- **Accesibilidad menor:** `<section>` sin nombre en `EmptyState.tsx:18`; ilustraciones con atributos incoherentes y tamaño fijo; `PopoverTitle` sin encabezado; `Sonner` en inglés (PLAUSIBLE); descripciones de Ajustes.
- **Personaje:** `requestAnimationFrame` sigue activo con movimiento reducido y ventana oculta; etiquetas distintas entre `CharacterSlot` y `DrakterStatus`; `error` sin caducidad.
- **Chat:** Reintentar duplica el mensaje del usuario; el scroll no baja al enviar.
- **Ajustes:** dos banners simulados seguidos; tamaño «0,0 MB»; textos técnicos.
- **Almacén:** rutas truncadas por el final; «Leer» debería ser «Ver contenido».

## Lo que está bien y no hay que tocar

- Estados de agente sin indicadores falsos.
- Mensajes del agente, documentos y fragmentos como texto, sin `dangerouslySetInnerHTML` ni enlaces activos.
- `services/api.ts` no muestra el texto del servidor: traduce por código.
- Aviso «Contenido sin verificar» en `ResourceDetail.tsx`, y `agent_read` nace apagado.
- `tasks/Field.tsx` asocia etiqueta, ayuda y error: es el patrón a copiar.
- Texto principal, botones, destructivo y chasis superan AA en ambos temas.
- El CSS respeta `prefers-reduced-motion`.
- Los 9 estados del personaje están cubiertos, y el estado no depende solo del color en `DrakterStatus`.

## Sin comprobar

- Todo el comportamiento en ejecución: conexión real, confirmación de extremo a extremo y diálogo nativo.
- Lector de pantalla (Orca), teclado real y modo de alto contraste.
- Aspecto visual y tamaños reales en pantalla.
- Quién conecta las puertas reales (`Ports`, `storage_deps`) tras la integración.
