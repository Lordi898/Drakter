# DRAKTER

## Documento maestro de arquitectura, diseño y funcionamiento

> **Prevalencia.** Pese a su título, este documento es **subordinado**: es el último en el orden de prevalencia de `DECISIONS.md` (entrada "Jerarquía de documentos y numeración única de fases": `DECISIONS.md` más reciente, `CLAUDE.md`, `MASTER_PLAN.md`, `ROADMAP.md` y este documento). No es maestro ni definitorio. Donde choque con una decisión registrada, manda la decisión. Sus "Fases 0 a 10" (§20) equivalen a los pasos de la tabla de esa entrada (p. ej. Fase 8 = paso 6, Personalidad y contexto). Los esquemas de datos (entidades, campos, estados, enums, tipos de relación), el catálogo de herramientas y los eventos WebSocket los resuelve `drakter/contratos` (entrada "Contratos de datos que resuelve drakter/contratos"); las listas de este documento son orientativas hasta que publique.

**Versión del diseño:** 1.0  
 **Fecha:** 4 de noviembre de 2026  
 **Tipo:** Aplicación personal de escritorio con agente de IA integrado  
 **Plataforma inicial:** Linux de escritorio  
 **Arquitectura:** Local-first, modular y extensible  
 **Usuario:** Un único usuario, con datos y configuración locales

# PARTE 1. DISEÑO Y PLANIFICACIÓN COMPLETA

## 1. Definición del proyecto

Drakter será un agente personal de inteligencia artificial integrado nativamente en una aplicación de escritorio propia.

No será solamente un chatbot. Será un entorno de trabajo personal capaz de:

- Conversar mediante texto y voz.
- Mostrar un personaje animado que represente su estado operativo y expresivo.
- Gestionar tareas, subtareas, proyectos y hábitos.
- Administrar un calendario y bloques de tiempo.
- Conocer las asignaturas y el horario de clases.
- Catalogar, indexar, localizar y leer archivos bajo demanda.
- Relacionar información de todos los módulos.
- Consultar, crear, actualizar y organizar elementos mediante instrucciones naturales.
- Recordar información relevante entre sesiones.
- Aprender procedimientos y mejorar sus propias skills mediante un proceso controlado.
- Mostrar actividad, herramientas utilizadas, operaciones realizadas, errores y estadísticas.

La aplicación tendrá una estructura fija y diseñada de antemano. No será un constructor de páginas como Notion ni un sistema completamente configurable como ClickUp. Sus módulos y navegación estarán definidos por el proyecto, pero el usuario podrá crear libremente los elementos de contenido admitidos en cada módulo.

### Principios fundamentales

1. La aplicación y el agente comparten los mismos datos.
2. El agente utiliza las mismas operaciones internas que la interfaz.
3. La base de datos de Drakter es la fuente de verdad de las tareas, proyectos, hábitos, eventos y recursos.
4. La memoria de IA no sustituye a la base de datos operativa.
5. Los archivos originales permanecen en sus ubicaciones; Drakter conserva un catálogo e índices.
6. El contexto se recupera bajo demanda, no se introduce entero en cada petición al modelo.
7. La personalidad es persistente, pero su expresión se adapta a la situación.
8. El agente puede ejecutar operaciones, pero debe respetar permisos y confirmaciones.
9. La automejora se realiza mediante propuestas, pruebas y aprobación, nunca mediante modificaciones ocultas e ilimitadas.
10. Los componentes deben poder sustituirse sin reconstruir toda la aplicación.

## 2. Arquitectura general

Drakter estará compuesto por ocho grandes capas.

### Capa 1. Interfaz de escritorio

Tecnologías:

- Electron.
- React.
- TypeScript.
- Tailwind CSS.
- Rive para la cara animada.
- Gráficos y estadísticas: fuera de la v1; sin Recharts hasta que hagan falta (decisión "Trabajo sin clave y alcance de automejora, copias y v1").

Responsabilidad:

- Mostrar toda la aplicación.
- Gestionar navegación y ventanas.
- Recoger las interacciones del usuario.
- Mostrar el personaje y sus expresiones.
- Reproducir audio.
- Mostrar conversaciones, resultados y actividad.
- Presentar formularios, listas, calendarios y relaciones.

La interfaz no ejecutará directamente operaciones de base de datos ni tendrá acceso general al sistema de archivos.

### Capa 2. Backend de aplicación

Tecnologías:

- Python.
- FastAPI.
- Pydantic.
- SQL propio con `sqlite3` y migraciones `.sql`, sin SQLAlchemy ni Alembic.

Responsabilidad:

- Exponer la API de Drakter.
- Validar datos.
- Aplicar reglas de negocio.
- Gestionar permisos.
- Ejecutar operaciones de los módulos.
- Controlar las relaciones.
- Comunicarse con la base de datos.
- Proporcionar servicios a la interfaz y al agente.

Será el punto central de acceso a los datos de Drakter.

### Capa 3. Agente

Tecnología principal:

- Hermes Agent.

Modelo inicial:

- Claude Haiku 5.5 mediante API.

Responsabilidad:

- Interpretar instrucciones.
- Razonar sobre el contexto.
- Seleccionar herramientas.
- Consultar memoria.
- Consultar recursos.
- Ejecutar operaciones mediante herramientas.
- Responder y explicar lo realizado.

Hermes será el runtime del agente. Drakter será la identidad, el entorno y la integración que construimos alrededor de él.

### Capa 4. Memoria y contexto

Componentes:

- Memoria nativa de Hermes.
- OpenViking como proveedor externo principal. Y usar su memoria por capas (L0, L1, L2).
- Skills nativas de Hermes.
- Catálogo de recursos de Drakter.
- Índice de búsqueda.
- Sistema de recuperación contextual.
- Historial de sesiones.

Responsabilidad:

- Conservar información útil entre conversaciones.
- Recuperar información relevante.
- Evitar cargar todo el historial.
- Organizar conocimiento, recursos, skills y reglas.
- Proporcionar contexto progresivo.

### Capa 5. Voz

Componentes:

- openWakeWord. Para palabra de activación.
- Silero VAD. Para detección de voz.
- Faster-Whisper (small o medium).
- Kokoro TTS.
- Piper como alternativa TTS.
- Servicio de audio local.
- Motor de sincronización labial.

Responsabilidad:

- Detectar la palabra de activación.
- Detectar cuándo comienza y termina el habla.
- Transcribir audio.
- Sintetizar voz.
- Reproducir respuestas.
- Gestionar interrupciones.
- Sincronizar el audio con la boca del personaje.

### Capa 6. Workspace

Módulos:

- Tareas.
- Subtareas.
- Proyectos.
- Hábitos.
- Calendario.
- Bloques de tiempo.
- Asignaturas.
- Horarios.
- Almacén de recursos.
- Relaciones.

Responsabilidad:

- Organizar toda la información personal.
- Permitir conexiones entre elementos.
- Proporcionar datos estructurados al agente.

### Capa 7. Herramientas y automatizaciones

Componentes:

- Servidor MCP propio de Drakter.
- Skills de Hermes.
- Servicio de tareas programadas.
- Sistema de notificaciones.
- Servicio de indexación.
- Servicio de monitorización.

Responsabilidad:

- Exponer capacidades al agente.
- Automatizar procedimientos.
- Ejecutar acciones de forma controlada.
- Mantener sincronizados los módulos.

### Capa 8. Seguridad y observabilidad

Componentes:

- Gestor de permisos.
- Credenciales fuera del repositorio (`~/.config/drakter/.env`).
- Registro de actividad.
- Registro de cambios.
- Copias de seguridad.
- Monitorización.
- Sistema de errores. Error Handling.

Responsabilidad:

- Proteger datos.
- Controlar operaciones.
- Registrar cambios.
- Facilitar recuperación.
- Evitar acciones no autorizadas.

## 3. Aplicación de escritorio

### 3.1. Tecnología

Electron + React + TypeScript.

Electron permitirá crear una aplicación de escritorio real utilizando tecnologías web. React gestionará los componentes visuales y TypeScript aportará tipado al código.

Tailwind CSS se utilizará para estilos y diseño.

Rive se utilizará para el personaje animado, sus expresiones y sus máquinas de estados.

### 3.2. Estructura visual

La aplicación tendrá una barra lateral fija con las siguientes secciones:

1. Inicio / Cara de Drakter.
2. Hábitos.
3. Tareas.
4. Proyectos.
5. Almacén.
6. Calendario.
7. Asignaturas.
8. Relaciones.
9. Configuración.

La cara de Drakter será la pantalla principal.

También existirá una zona de conversación accesible desde las distintas secciones. El usuario podrá pedir operaciones relacionadas con el módulo que está visualizando.

### 3.3. Pantalla principal

Incluirá:

- Personaje animado.
- Estado actual.
- Conversación.
- Entrada de texto.
- Botón de micrófono.
- Indicador de escucha.
- Indicador de procesamiento.
- Actividad reciente.
- Notificaciones.
- Accesos rápidos.
- Resumen del día.

El personaje tendrá un modo compacto y otro ampliado.

### 3.4. Ventanas y paneles

La aplicación incluirá:

- Ventana principal.
- Panel de conversación.
- Panel de actividad.
- Panel de detalles de elementos.
- Panel de confirmación de operaciones.
- Panel de configuración.
- Notificaciones de escritorio.

Se podrá estudiar más adelante una ventana flotante del personaje, pero no será necesaria para la primera versión.

### 3.5. Comunicación segura

Electron tendrá:

- contextIsolation: true.
- nodeIntegration: false.
- sandbox: true.
- Preload limitado.
- API explícita mediante contextBridge.
- Validación de todos los mensajes IPC.
- Política CSP restrictiva.

React no tendrá acceso libre a Node.js ni al sistema operativo.

El acceso a archivos y operaciones privilegiadas se realizará mediante el backend.

## 4. Hermes: motor del agente

### 4.1. Función

Hermes será el runtime encargado de ejecutar el ciclo de razonamiento y herramientas.

No se modificará su núcleo salvo que una necesidad técnica concreta lo exija.

Drakter se conectará a Hermes mediante sus interfaces documentadas y un adaptador propio.

### 4.2. Modelo principal

Configuración inicial:

- Proveedor: Anthropic.
- Modelo: Claude Haiku 5.5.
- Identificador de API: claude-haiku-5-5.

Modelo alternativo:

- GPT-6 Luna.
- Configurable desde la administración del agente.

La aplicación tendrá una abstracción de proveedor y modelo para que cambiar el modelo no implique cambiar el resto de la arquitectura.

El modelo principal se utilizará para:

- Conversación.
- Planificación.
- Interpretación de instrucciones.
- Selección de herramientas.
- Consultas al Workspace.
- Gestión contextual.
- Resúmenes.
- Clasificación.

La memoria, la base de datos y las reglas no dependerán de un único modelo.

### 4.3. Ciclo del agente

Hermes recibirá el mensaje y el contexto preparado.

Después:

1. Interpreta la petición.
2. Identifica la información necesaria.
3. Decide si debe consultar memoria.
4. Decide si debe consultar recursos.
5. Selecciona herramientas.
6. Ejecuta las herramientas necesarias.
7. Analiza los resultados.
8. Decide si necesita más operaciones.
9. Prepara la respuesta.
10. Devuelve texto, eventos y resultados.

### 4.4. Herramientas

Drakter tendrá un servidor MCP propio.

El servidor MCP expondrá operaciones del Workspace. Las operaciones reales se ejecutarán en el backend de Drakter, no directamente en la base de datos.

El agente podrá consultar:

- Tareas.
- Subtareas.
- Proyectos.
- Hábitos.
- Calendario.
- Asignaturas.
- Recursos.
- Relaciones.
- Configuración autorizada.

También podrá crear, actualizar y relacionar elementos.

Las herramientas tendrán esquemas estrictos, validación y permisos.

## 5. Identidad, personalidad y comportamiento

La personalidad tendrá una estructura separada del razonamiento y de la memoria.

### 5.1. Archivos de personalidad

La personalidad vive en archivos, separada del modelo. Fuente única: el repositorio, con 14 archivos `.md`: 6 en `agent/identity/` (`SOUL`, `PERSONALITY`, `BEHAVIOR`, `COMMUNICATION`, `EMOTIONAL_STYLE`, `VALUES`), 4 en `agent/context/` (`USER`, `ENVIRONMENT`, `PREFERENCES`, `CURRENT_CONTEXT`) y 4 en `agent/knowledge/` (`CAPABILITIES`, `WORKSPACE_GUIDE`, `TOOL_GUIDE`, `SYSTEM_GUIDE`). Un cargador los compone y los publica en el `HERMES_HOME` de un perfil propio de Drakter, y comprueba el tope de 20.000 caracteres de los archivos de contexto de Hermes. `~/.hermes/SOUL.md` no es la fuente, y la personalidad no se configura con archivos YAML en `config/` (decisión "Los 14 archivos de identidad viven en agent/identity/").

`USER.md` y `PREFERENCES.md` del repositorio son plantillas sin datos reales; la plantilla rellenada vive fuera del repositorio y solo inicializa el `USER.md` nativo de Hermes, que a partir de ahí es el vivo (decisión "agent/context/USER.md es plantilla; el USER.md vivo es el de Hermes").

Los parámetros de estilo (humor, formalidad, concisión, expresividad, proactividad, intensidad y velocidad de voz) se expresan en esos archivos de identidad.

Catálogo cerrado de expresiones (7): `neutral`, `curious`, `focused`, `happy`, `concerned`, `confused`, `calm` (decisión "Las expresiones no tienen campo propio"). La expresión viaja en `animation`; no hay campo `expression`. El evento `agent.expression_changed` la transporta en `expression` (entrada "Eventos WebSocket resueltos en contracts/" de `DECISIONS.md`).

Estos estados son etiquetas de representación conversacional y visual, no emociones experimentadas por el modelo.

### 5.2. Capas de personalidad

La personalidad se organizará en cinco capas:

1. Identidad estable: quién es Drakter.
2. Estilo comunicativo: cómo se expresa.
3. Contexto: cómo adapta el tono a la situación.
4. Estado expresivo: qué expresión y tono utiliza en ese momento.
5. Canal: cómo transmite el mensaje por texto, voz y animación.

La identidad estable no cambiará automáticamente porque el modelo haya generado una respuesta diferente.

### 5.3. Contexto

El comportamiento se adaptará a:

- Conversación informal.
- Trabajo y productividad.
- Estudio.
- Explicaciones técnicas.
- Errores.
- Tareas completadas.
- Situaciones que requieren atención.
- Conversaciones por voz.
- Operaciones en curso.

### 5.4. Estado expresivo

El agente podrá producir un objeto estructurado de salida:

- state: estado visual.
- tone: tono vocal.
- intensity: intensidad.
- speech_rate: velocidad.
- voice_profile: perfil de voz.
- animation: animación recomendada; transporta la expresión del catálogo de 7 (no hay campo `expression`).

La aplicación validará esos valores contra un catálogo cerrado.

La IA no enviará código de animación ni instrucciones arbitrarias a Rive.

## 6. Cara animada

### 6.1. Tecnología

Rive + React.

Se creará un personaje original desde cero, con:

- Ojos.
- Párpados.
- Cejas.
- Boca.
- Expresiones.
- Animaciones.
- Estados.
- Transiciones.
- Movimientos secundarios.

### 6.2. Máquina de estados

Estados funcionales:

- idle
- listening
- thinking
- speaking
- executing
- success
- error
- interrupted
- offline

Estados expresivos:

- neutral
- curious
- focused
- happy
- concerned
- confused
- calm

La máquina de estados combinará estado funcional y expresión.

Por ejemplo:

- thinking + curious
- executing + focused
- speaking + happy
- error + concerned

### 6.3. Movimiento de la boca

Primera implementación:

- Apertura de boca según intensidad del audio.
- Cierre durante silencios.
- Variación de apertura para evitar movimiento mecánico.
- Sincronización con el inicio y final de los fragmentos de voz.

Evolución:

- Incorporación de visemas.
- Sincronización con fonemas cuando el proveedor de voz permita obtener marcas temporales.
- Transiciones naturales entre formas de boca.

### 6.4. Eventos

Lista orientativa. El catálogo definitivo está en `contracts/python/drakter_contracts/events.py` (entrada "Eventos WebSocket resueltos en contracts/" de `DECISIONS.md`).

La interfaz recibirá eventos del agente:

- agent.listening
- agent.thinking
- agent.speaking
- agent.tool_started
- agent.tool_completed
- agent.success
- agent.error
- agent.interrupted

La GUI transformará esos eventos en animaciones.

## 7. Voz y audio

### 7.1. Arquitectura

La voz funcionará como un servicio independiente.

Flujo de entrada:

Micrófono → openWakeWord → Silero VAD → Faster-Whisper → texto → Hermes.

Flujo de salida:

Hermes → texto y perfil vocal → Kokoro TTS → audio → altavoz.

El audio se comunicará con la interfaz para sincronizar la boca.

### 7.2. Wake word

Tecnología: openWakeWord.

Función:

- Detectar la palabra de activación.
- Activar la escucha.
- Evitar que el sistema procese continuamente todo el audio como una conversación.

Se entrenará o configurará un modelo para la palabra de activación elegida: “Drakter”.

### 7.3. VAD

Tecnología: Silero VAD.

Función:

- Detectar actividad de voz.
- Identificar silencios.
- Separar segmentos.
- Evitar enviar audio innecesario al STT.
- Facilitar la detección del final de una intervención.

### 7.4. STT

Tecnología: Faster-Whisper.

Configuración inicial:

- Modelo: small.
- Ejecución: CPU.
- Cuantización: INT8.
- Idioma preferente: español.
- Detección automática disponible para otros idiomas.

La configuración se validará con pruebas de latencia y precisión.

El modelo base será alternativa si small resulta demasiado lento.

### 7.5. TTS

Motor principal: Kokoro.

Alternativa: Piper.

Kokoro será el primer motor que evaluaremos para calidad de voz y español.

Piper se conservará como alternativa ligera y local.

Hermes dispone de su propio sistema TTS, pero Kokoro se integrará mediante un servicio local y un adaptador. No se asumirá que Hermes lo soporta de forma nativa sin comprobar la versión y el proveedor disponible.

### 7.6. Personalidad vocal

El sistema tendrá perfiles vocales:

- Normal.
- Conversacional.
- Serio.
- Concentrado.
- Enérgico.
- Tranquilo.
- Explicativo.

Cada perfil podrá definir:

- Voz.
- Velocidad.
- Volumen.
- Pausas.
- Entonación disponible.
- Intensidad.

No se prometerá una actuación emocional avanzada si el motor TTS no proporciona controles suficientes.

### 7.7. Interrupciones

El usuario podrá interrumpir a Drakter.

Al detectar una interrupción:

1. Se detiene la reproducción.
2. Se cancela el fragmento pendiente.
3. Se registra el estado de interrupción.
4. Se vuelve a escucha.
5. Se procesa la nueva instrucción.

## 8. Memoria y contexto

### 8.1. Arquitectura seleccionada

Memoria integrada de Hermes + OpenViking como proveedor externo principal.

Solo hay un proveedor externo activo: OpenViking.

La documentación de Hermes contempla un proveedor externo activo cada vez, junto a la memoria integrada.

OpenViking ocupa el único lugar de proveedor externo (`memory.provider: openviking`), junto a `MEMORY.md` y `USER.md`; Hindsight, Mem0, Supermemory y Honcho quedan fuera del plan (decisión "Memoria: nativa de Hermes + OpenViking con capas L0/L1/L2"). OpenViking es la elección porque permite organizar recursos, memorias, skills y reglas en una estructura jerárquica con recuperación progresiva.

### 8.2. Archivos de Hermes

Directorio:

`HERMES_HOME` del perfil propio de Drakter (no el `~/.hermes/` por defecto como fuente de identidad).

Archivos y carpetas:

- SOUL.md: identidad estable de Drakter, publicada desde `agent/identity/` (el repositorio es la fuente).
- memories/USER.md: perfil y preferencias del usuario (el vivo es este; el del repositorio es solo plantilla).
- memories/MEMORY.md: notas persistentes del agente.
- config.yaml: configuración de Hermes.
- .env y auth.json: los secretos no se versionan; el origen único de credenciales de Drakter es `~/.config/drakter/.env`.
- skills/: skills instaladas y creadas.
- sessions/: sesiones.
- cron/: trabajos programados.
- logs/: registros.

Instrucciones del proyecto:

- .hermes.md o AGENTS.md: instrucciones de desarrollo y del proyecto.
- Los archivos de instrucciones estarán versionados junto al código cuando sean específicos del repositorio.

### 8.3. OpenViking

Se utilizará para contexto externo y recuperación progresiva.

Organización conceptual:

viking://resources/

Documentación, archivos, proyectos y fuentes.

viking://user/<usuario>/memories/

Preferencias, decisiones, experiencias y conocimiento persistente.

viking://agent/

Skills y contexto reutilizable del agente.

viking://session/

Contexto de la sesión en curso.

OpenViking utilizará resúmenes y niveles de detalle para evitar cargar todo el contenido. La ingesta del almacén en OpenViking es opcional por recurso, viene apagada por defecto y pasa siempre por el backend.

### 8.4. Capas de memoria

Nivel 0: instrucciones y reglas del sistema.

Nivel 1: identidad estable de Drakter.

Nivel 2: perfil del usuario y preferencias.

Nivel 3: memoria persistente del agente.

Nivel 4: instrucciones del proyecto activo.

Nivel 5: memorias externas recuperadas de OpenViking.

Nivel 6: recursos recuperados mediante búsqueda.

Nivel 7: historial de la sesión actual.

Nivel 8: datos operativos consultados en el Workspace.

Nota: estos "Niveles 0-8" son el orden de construcción del contexto; son distintos de las capas L0/L1/L2 de OpenViking, que describen el nivel de detalle de cada recuerdo (ver `MASTER_PLAN.md` §10.2).

No todos estos niveles se inyectarán siempre. El contexto se seleccionará según la tarea.

### 8.5. Ciclo de memoria

Durante una conversación:

1. El agente recibe el mensaje.
2. Identifica qué contexto necesita.
3. Recibe del backend los recuerdos relevantes, cercados como dato no confiable y fuera del prompt de sistema; puede pedir más con una herramienta del backend.
4. Consulta recursos si hace falta.
5. Recibe resultados resumidos y referencias.
6. Responde o ejecuta acciones.
7. Al terminar la sesión, OpenViking evalúa qué información merece conservarse.
8. Extracción, clasificación, deduplicación y resolución de contradicciones las hace OpenViking, configurado y comprobado (lo que falte se anota con ⚠️). Drakter no tiene pipeline propio ni guarda recuerdos en el repositorio (decisión "Memoria sin pipeline propio ni recuerdos en el repositorio").
9. Se guardan los recuerdos aprobados según las reglas configuradas.

### 8.6. Tipos de memoria

- Perfil: información estable del usuario.
- Preferencias: formas de trabajar y comunicarse.
- Episódica: hechos importantes de sesiones anteriores.
- Semántica: conocimientos generales y relaciones.
- Procedimental: cómo realizar tareas.
- Proyecto: decisiones, objetivos y convenciones.
- Operativa: datos actuales del Workspace.

La memoria operativa no se duplicará como verdad en OpenViking. La base de datos del Workspace seguirá siendo la fuente de verdad para tareas, eventos, proyectos y demás elementos.

### 8.7. Recuperación

La recuperación tendrá tres pasos:

1. Búsqueda inicial por significado y metadatos.
2. Selección de resultados relevantes.
3. Lectura de detalle solo cuando sea necesario.

El agente recibirá referencias a las fuentes y no copias indiscriminadas de todo el contenido.

### 8.8. Control de memoria

El usuario podrá:

- Consultar recuerdos.
- Corregirlos.
- Eliminar recuerdos.
- Marcar información como temporal.
- Impedir que determinados datos se guarden.
- Revisar el origen de un recuerdo.

Los recuerdos importantes deberán conservar una referencia de procedencia cuando sea posible.

## 9. Skills y conocimiento procedimental

Las skills serán procedimientos reutilizables.

Ejemplos:

- manage-tasks
- plan-week
- organize-project
- search-resources
- prepare-study-session
- summarize-document
- review-calendar
- create-project-report

Cada skill tendrá:

- Nombre.
- Descripción.
- Objetivo.
- Instrucciones.
- Herramientas requeridas.
- Parámetros.
- Restricciones.
- Ejemplos de entrada y salida.
- Pruebas.

La fuente de las skills está en `agent/` y se publican al perfil de Hermes; podrán tener documentación complementaria en OpenViking.

No se duplicarán instrucciones innecesariamente.

## 10. Automejora y evolución controlada

Drakter tendrá un sistema de mejora continua, pero no modificará su propio código ni sus reglas de forma autónoma y silenciosa. Lo publicado al agente en uso (Skills incluidas) cuenta como producción: todo cambio pasa por propuesta y autorización (decisión "Trabajo sin clave y alcance de automejora, copias y v1").

### 10.1. Qué podrá mejorar

- Skills.
- Plantillas.
- Procedimientos.
- Recuperación contextual.
- Clasificación de recuerdos.
- Archivos de identidad (siempre con propuesta y autorización).
- Prompts de trabajo.
- Flujos de automatización.

### 10.2. Qué no podrá cambiar sin autorización

- Su código principal.
- Los permisos.
- Las políticas de seguridad.
- Las credenciales.
- La estructura de datos crítica.
- Las reglas de confirmación.
- Las instrucciones de máxima prioridad.

### 10.3. Ciclo de mejora

1. Detecta un error o una oportunidad.
2. Registra el problema.
3. Propone una mejora.
4. Genera una nueva versión de la skill o configuración.
5. Ejecuta pruebas.
6. Compara resultados.
7. Presenta los cambios.
8. Solicita siempre aprobación antes de publicar, también en Skills.
9. Guarda la versión aprobada.
10. Mantiene la posibilidad de revertir.

El sistema conservará historial de versiones.

## 11. Workspace: base de datos y módulos

### 11.1. Base de datos

Tecnología: SQLite.

Acceso con SQL propio.

Migraciones `.sql` en `backend/migrations/` (entrada "SQL propio sin Alembic" de `DECISIONS.md`).

Búsqueda textual mediante SQLite FTS5.

Identificadores UUID.

Fechas almacenadas en UTC y presentadas en la zona horaria local Europe/Madrid.

La base de datos será la fuente de verdad del Workspace.

### 11.2. Tareas

Cada tarea tendrá:

- ID.
- Título.
- Descripción.
- Estado.
- Prioridad.
- Fecha de creación.
- Fecha de inicio.
- Fecha límite.
- Fecha de finalización.
- Estimación de duración.
- Tiempo real dedicado, si se registra.
- Tarea padre opcional.
- Proyecto asociado opcional.
- Asignatura asociada opcional.
- Etiquetas.
- Relaciones.
- Notas.

Estados iniciales:

- Pendiente.
- En progreso.
- En revisión.
- Bloqueada.
- Completada.
- Cancelada.

Las subtareas serán tareas con relación jerárquica padre-hijo.

Podrán anidarse varios niveles, con un límite configurable para evitar estructuras absurdas.

### 11.3. Proyectos

Cada proyecto tendrá:

- ID.
- Nombre.
- Descripción.
- Estado.
- Prioridad.
- Fecha de inicio.
- Fecha objetivo.
- Fecha de finalización.
- Objetivos.
- Tareas asociadas.
- Recursos relacionados.
- Eventos relacionados.
- Asignaturas relacionadas.
- Progreso calculado.

Estados:

- Planificado.
- Activo.
- Pausado.
- Completado.
- Cancelado.

El progreso se calculará a partir de las tareas, pero podrá mostrarse también como progreso manual cuando se necesite.

### 11.4. Hábitos

Cada hábito tendrá:

- ID.
- Nombre.
- Descripción.
- Frecuencia.
- Días de repetición.
- Objetivo.
- Fecha de inicio.
- Fecha de finalización opcional.
- Historial de cumplimiento.
- Racha actual.
- Mejor racha.
- Recordatorios.
- Relaciones.

El historial de cumplimiento será independiente del estado de una tarea.

### 11.5. Calendario

Tipos de elementos:

- Evento.
- Bloque de tiempo.
- Clase.
- Recordatorio.
- Sesión de trabajo.

Cada elemento tendrá:

- Título.
- Descripción.
- Inicio.
- Fin.
- Zona horaria.
- Recurrencia opcional.
- Tipo.
- Relaciones.
- Estado.

Los bloques de tiempo podrán relacionarse con tareas, proyectos, asignaturas, hábitos y recursos.

### 11.6. Asignaturas

Cada asignatura tendrá:

- ID.
- Nombre.
- Profesor opcional.
- Descripción.
- Color.
- Aula opcional.
- Horarios.
- Recursos.
- Tareas relacionadas.
- Proyectos relacionados.
- Eventos relacionados.

El horario de clases se almacenará mediante reglas semanales y excepciones para días especiales.

### 11.7. Almacén de recursos

Tipos:

- Imagen.
- Documento.
- PDF.
- Archivo de texto.
- Código.
- Carpeta.
- Comprimido.
- Enlace.
- Nota.
- Apunte.
- Otro.

Cada recurso tendrá:

- ID.
- Título.
- Tipo.
- Ruta o URL.
- Descripción escrita por el usuario, opcional.
- Fecha de incorporación.
- Fecha de modificación conocida.
- Tamaño, cuando corresponda.
- Hash de contenido, cuando sea posible.
- Estado de disponibilidad.
- Metadatos.
- Relaciones.

La descripción será opcional y solo se rellenará si el usuario la introduce o solicita expresamente que se redacte.

### 11.8. Indexación

El almacén mantendrá tres niveles:

1. Catálogo: título, tipo, ubicación, metadatos y descripción del usuario.
2. Índice de búsqueda: texto extraído y datos necesarios para localizar contenido.
3. Archivo original: permanece en su ubicación.

Drakter no cargará todos los archivos en el prompt.

Cuando se solicite leer un recurso:

1. Localiza su registro.
2. Comprueba que sigue disponible.
3. Comprueba los permisos.
4. Accede al archivo.
5. Extrae el contenido necesario.
6. Devuelve el resultado al agente.
7. Evita conservar copias innecesarias.

Para comprimidos se podrá indexar el listado de contenidos sin extraer automáticamente todos los archivos.

### 11.9. Relaciones

Las relaciones serán un sistema transversal.

Cada relación tendrá:

- ID.
- Tipo de origen.
- ID de origen.
- Tipo de destino.
- ID de destino.
- Tipo de relación.
- Fecha de creación.
- Metadatos opcionales.

Relaciones iniciales:

- belongs_to
- related_to
- scheduled_for
- uses_resource
- depends_on
- studies
- supports
- parent_of
- references
- created_from
- tracks
- blocks
- precedes

Las relaciones se validarán según los tipos de elementos.

La interfaz mostrará las relaciones desde ambos extremos, aunque la relación se almacene con una dirección definida.

Las relaciones jerárquicas de subtareas y carpetas tendrán reglas propias y no se tratarán como relaciones genéricas sin restricciones.

## 12. API de Drakter

El backend expondrá una API REST y WebSocket.

REST:

- Consultas.
- Creación.
- Actualización.
- Eliminación.
- Búsqueda.
- Relaciones.
- Configuración.

WebSocket:

- Estado del agente.
- Actividad.
- Eventos de herramientas.
- Respuestas en streaming.
- Audio y estados de voz.
- Notificaciones en tiempo real.

La API tendrá versiones.

Ruta base conceptual:

/api/v1/

Áreas:

- /tasks
- /projects
- /habits
- /calendar
- /subjects
- /resources
- /relationships
- /search
- /agent
- /settings
- /activity

Las operaciones MCP llamarán a los mismos servicios internos que la API.

No habrá una implementación de negocio para la GUI y otra distinta para Hermes.

## 13. Herramientas de Drakter

Lista orientativa. El catálogo base es `MASTER_PLAN.md` §19, y lo congela `drakter/contratos`; si difiere, manda su entrada (decisión "Huecos de MASTER_PLAN §19: borrar o mover archivos y listar hábitos"). `list_habits` se mantiene (solo lectura). Eliminar o mover recursos no tiene herramienta de agente en la v1: se hace solo desde la GUI, con confirmación; si el agente recibe esa petición, lo dice y no improvisa un sustituto. Las herramientas las sirve el backend por MCP en loopback (servidor delgado, sin lógica de negocio) y Hermes es solo cliente (decisión "Puente Hermes-backend y flujo de una petición").

Las familias siguientes son las de este plan; las operaciones destructivas de la lista (`delete_task`, `delete_event`, `remove_relationship`) crean una confirmación pendiente y no se ejecutan hasta que la GUI la resuelve.

### Tasks

- list_tasks
- get_task
- create_task
- update_task
- complete_task
- delete_task
- create_subtask
- list_subtasks

### Projects

- list_projects
- get_project
- create_project
- update_project
- archive_project

### Habits

- list_habits
- create_habit
- update_habit
- register_habit_completion
- get_habit_history

### Calendar

- get_calendar
- get_schedule
- create_event
- update_event
- create_time_block
- move_time_block
- delete_event

### Subjects

- list_subjects
- get_subject
- get_timetable
- create_schedule_exception

### Resources

- search_resources
- get_resource_metadata
- read_resource
- index_resource
- refresh_resource_index
- create_note
- create_link

### Relationships

- create_relationship
- remove_relationship
- list_relationships
- get_related_items

### System

- get_agent_status
- get_workspace_summary
- get_activity_log
- get_pending_confirmations

Cada herramienta tendrá:

- Esquema de entrada.
- Validación.
- Permisos.
- Resultado estructurado.
- Gestión de errores.
- Registro de actividad.

## 14. Seguridad y permisos

Se utilizarán tres niveles de operación.

### Nivel 1. Lectura

Puede consultar información autorizada sin modificarla.

Ejemplos:

- Ver tareas.
- Consultar calendario.
- Buscar archivos.
- Leer documentos autorizados.

### Nivel 2. Escritura ordinaria

Puede crear o modificar elementos de bajo riesgo cuando el usuario lo haya solicitado claramente.

Ejemplos:

- Crear una tarea.
- Añadir una nota.
- Relacionar un documento.
- Crear un bloque de tiempo solicitado.

### Nivel 3. Operaciones sensibles

Requieren confirmación.

Ejemplos:

- Eliminar cualquier elemento (toda eliminación confirma, no solo las masivas).
- Mover grandes cantidades de recursos (mover o renombrar archivos concretos solo es posible desde la GUI; ver §13 y `MASTER_PLAN.md` §24).
- Modificar una gran cantidad de datos.
- Ejecutar acciones externas.
- Modificar configuración crítica.

Cambiar permisos está prohibido para el agente: no es una acción confirmable, solo la GUI puede hacerlo (decisión "Contratos de datos que resuelve drakter/contratos").

Flujo de confirmación (decisión "Herramientas con su módulo; confirmación y auditoría antes de la primera"): la herramienta destructiva crea una confirmación pendiente y devuelve su id sin ejecutar; solo la GUI la resuelve, por un endpoint que no es herramienta; la ejecución y la auditoría ocurren después. La confirmación es obligatoria y el undo es adicional. Permisos, confirmaciones pendientes y auditoría existen antes de la primera herramienta.

El usuario podrá consultar qué herramienta se ha ejecutado y qué datos ha cambiado.

Se conservará un registro de operaciones con:

- Fecha.
- Herramienta.
- Parámetros relevantes.
- Resultado.
- Elementos afectados.
- Usuario o agente que inició la operación.

Las claves API no se guardarán en la base de datos del Workspace ni en el frontend. El origen único de credenciales es `~/.config/drakter/.env`, fuera del repositorio.

## 15. Automatizaciones y notificaciones

Alcance v1: las automatizaciones avanzadas quedan fuera; solo se incluye un mínimo local que dispara recordatorios (decisión "Trabajo sin clave y alcance de automejora, copias y v1"). El resto de esta sección describe el diseño completo, no la v1.

Se incorporará un servicio de tareas programadas.

Funciones:

- Recordatorios.
- Revisiones de hábitos.
- Resúmenes diarios.
- Revisión de tareas pendientes.
- Preparación del día.
- Avisos de eventos próximos.
- Comprobación de recursos que han cambiado.

Las automatizaciones tendrán:

- Nombre.
- Frecuencia.
- Condiciones.
- Acción.
- Estado.
- Última ejecución.
- Próxima ejecución.
- Historial.

Las automatizaciones no podrán saltarse el sistema de permisos.

## 16. Monitorización

Alcance v1: los paneles avanzados quedan fuera; el panel de estado y los indicadores siguientes describen el diseño completo, no la v1.

La aplicación tendrá un panel de estado.

Indicadores:

- Estado de Hermes.
- Estado del backend.
- Estado de OpenViking.
- Estado de la base de datos.
- Estado del micrófono.
- Estado de STT.
- Estado de TTS.
- Modelo activo.
- Tokens de entrada.
- Tokens de salida.
- Coste estimado.
- Tiempo de respuesta.
- Herramientas ejecutadas.
- Errores recientes.
- CPU.
- RAM.
- GPU, cuando sea detectable (la máquina de desarrollo no tiene VRAM dedicada: 14 GB de RAM y gráfica integrada Intel UHD 620; ver decisión "Hardware real y paralelismo acotado").

El coste se calculará utilizando los precios configurados del proveedor y el uso real registrado.

## 17. Estructura del proyecto

La estructura vigente es la de `MASTER_PLAN.md` Parte XII con las desviaciones registradas en `DECISIONS.md` (entrada "Datos fuera del repositorio y estructura de carpetas"). Se descartan `apps/` y `docker-compose`; el árbol de este plan queda eliminado para no duplicar la estructura. Las carpetas se crean cuando entra código. La configuración no sensible puede versionarse; la sensible, nunca. Los datos de ejecución viven en `DRAKTER_DATA_DIR` (por defecto `user_data_dir("drakter")`, según `backend/CONTRACT.md`); `workspace/` no guarda datos.

Los archivos de datos (`DRAKTER_DATA_DIR`) y las credenciales (`~/.config/drakter/.env`) se guardan fuera del repositorio.

## 18. Despliegue local

Servicios:

- Drakter Desktop.
- Drakter Backend.
- Runner de Hermes.
- Drakter MCP Server.
- Voice Service.
- OpenViking.
- SQLite.

Los servicios se podrán iniciar y detener desde la aplicación.

La aplicación comprobará su estado y mostrará errores claros si alguno no está disponible.

La comunicación local utilizará interfaces restringidas a localhost. No se expondrán servicios a la red local o Internet por defecto.

Sin Docker hasta que haga falta (decisión "Trabajo sin clave y alcance de automejora, copias y v1"); la aplicación de escritorio no depende de contenedores.

## 19. Copias de seguridad y recuperación

Se realizarán copias de seguridad de:

- Base de datos.
- Configuración.
- Archivos de identidad y contexto (`agent/identity/`, `agent/context/`, `agent/knowledge/`).
- Skills.
- Índices y metadatos.
- Configuración de memoria.
- Datos de OpenViking.
- Home de Hermes.

Sin secretos en las copias.

Los archivos originales del almacén no se duplicarán automáticamente en las copias de seguridad de Drakter, salvo que se configure expresamente.

Se conservarán versiones recientes y un procedimiento de restauración probado.

## 20. Plan de desarrollo

### Fase 0. Especificación

- Cerrar modelos de datos.
- Definir API.
- Definir permisos.
- Diseñar estructura de repositorio.
- Crear decisiones arquitectónicas.

### Fase 1. Núcleo

- Electron.
- React.
- FastAPI.
- SQLite.
- Conexión con Hermes.
- Navegación básica.

### Fase 2. Cara

(Las Fases de este plan equivalen a los pasos de la tabla de `DECISIONS.md`; ver Prevalencia.)

- Diseño del personaje.
- Archivo Rive (el `.riv` lo diseña el usuario; hasta entonces, personaje provisional con la misma API de estados y ⚠️ en sus casillas).
- Estados.
- Expresiones.
- Eventos.
- Boca y sincronización.

### Fase 3. Workspace

- Tareas.
- Subtareas.
- Proyectos.
- Relaciones.
- API.
- MCP.

### Fase 4. Organización personal

- Hábitos.
- Calendario.
- Bloques de tiempo.
- Asignaturas.
- Horario.

### Fase 5. Almacén

- Catálogo.
- Indexación.
- Búsqueda.
- Lectura bajo demanda.
- Relaciones.

### Fase 6. Memoria

- Archivos de Hermes.
- OpenViking.
- Extracción y clasificación configuradas en OpenViking (sin pipeline propio).
- Recuperación.
- Evaluación.
- Skills.

### Fase 7. Voz

- Wake word.
- VAD.
- STT.
- TTS.
- Interrupciones.
- Lip-sync.

### Fase 8. Personalidad

- Archivos de `agent/identity/`, `agent/context/` y `agent/knowledge/`, y su cargador.
- Perfiles vocales.
- Estados expresivos.
- Contexto.
- Adaptación.

### Fase 9. Automejora

- Registro de errores.
- Propuestas.
- Versionado de skills.
- Pruebas.
- Aprobación.
- Reversión.

### Fase 10. Acabado

- Seguridad.
- Rendimiento.
- Monitorización.
- Copias de seguridad.
- Pruebas de integración.
- Empaquetado.

# PARTE 2. FLUJO COMPLETO DE FUNCIONAMIENTO

## 1. Arranque de Drakter

1. El usuario abre Drakter Desktop.
2. Electron inicia el proceso principal.
3. Se carga la interfaz React.
4. Se comprueba la configuración local.
5. Se inicia o verifica el backend FastAPI.
6. El backend comprueba SQLite.
7. Se inicia o verifica el runner de Hermes (proceso aparte sobre `AIAgent`, sin gateway, supervisado por FastAPI).
8. Se inicia o verifica OpenViking.
9. Se inicia o verifica el servidor MCP.
10. Se comprueba el servicio de voz.
11. Se recupera el estado del Workspace.
12. Se cargan las preferencias de interfaz.
13. Se comprueba el estado de los módulos.
14. La interfaz muestra el panel principal.
15. El personaje pasa a estado idle.

Si algún servicio falla, Drakter seguirá funcionando en modo degradado cuando sea posible y mostrará qué funciones no están disponibles.

## 2. Inicio de conversación por texto

1. El usuario escribe un mensaje.
2. React recoge el texto.
3. La interfaz envía la petición al backend.
4. El backend crea un identificador de interacción.
5. Se envía el mensaje a Hermes.
6. Hermes recibe el contexto base.
7. Hermes evalúa si necesita memoria.
8. El backend recupera los recuerdos relevantes y los entrega cercados como dato no confiable.
9. Se buscan recursos si la petición lo requiere.
10. El backend entrega a Hermes el mensaje, el contexto de sesión y los recuerdos cercados.
11. El modelo analiza la instrucción.
12. Decide si necesita herramientas.
13. Ejecuta las herramientas necesarias.
14. El backend valida cada operación.
15. Se consultan o modifican los datos.
16. Los resultados regresan a Hermes.
17. Hermes prepara la respuesta.
18. El backend transmite la respuesta.
19. React actualiza el chat.
20. La cara cambia a su estado correspondiente.
21. Se registra la actividad.

## 3. Inicio de conversación por voz

1. El servicio de audio mantiene disponible el detector de activación.
2. openWakeWord detecta “Drakter”.
3. Se activa el modo de escucha.
4. La cara cambia a listening.
5. Silero VAD detecta el inicio de voz.
6. Se captura el segmento de audio.
7. VAD detecta el final de la intervención.
8. Faster-Whisper transcribe el audio.
9. Se obtiene el texto.
10. El texto se envía a Hermes.
11. Hermes procesa la petición.
12. Se prepara una respuesta textual.
13. Se determina el perfil vocal.
14. Kokoro genera el audio.
15. El audio comienza a reproducirse.
16. La cara cambia a speaking.
17. El sistema sincroniza la boca.
18. Si el usuario interrumpe, se detiene la reproducción.
19. Se procesa la nueva intervención.
20. Se registra la interacción.

## 4. Ejecución de una herramienta

1. Hermes identifica una operación necesaria.
2. Selecciona una herramienta MCP (servida por el backend en loopback).
3. Envía los parámetros.
4. El servidor MCP valida el esquema.
5. El backend comprueba permisos.
6. Se verifica si requiere confirmación.
7. Si requiere confirmación, se presenta al usuario.
8. Si está autorizada, se ejecuta.
9. Se actualiza la base de datos.
10. Se registra el cambio.
11. Se devuelve el resultado a Hermes.
12. Hermes continúa el razonamiento.
13. La interfaz muestra la operación realizada.

## 5. Gestión de una tarea relacionada con un proyecto

Ejemplo: el usuario pide crear una tarea para un proyecto, relacionarla con una asignatura y programar una sesión.

1. Hermes identifica la intención.
2. Consulta proyectos.
3. Consulta asignaturas.
4. Consulta tareas existentes para evitar duplicados.
5. Propone o crea la tarea según la instrucción.
6. Relaciona la tarea con el proyecto.
7. Relaciona la tarea con la asignatura.
8. Consulta el calendario.
9. Comprueba disponibilidad.
10. Crea el bloque de tiempo si está autorizado.
11. Relaciona el bloque con la tarea.
12. Registra la operación.
13. Devuelve un resumen.
14. La interfaz actualiza tareas, proyecto y calendario.

## 6. Búsqueda y lectura de archivos

1. El usuario solicita localizar información.
2. Hermes consulta el catálogo.
3. El buscador filtra por título, tipo, descripción y contenido indexado.
4. Se muestran resultados.
5. Si se solicita leer un archivo, se comprueba disponibilidad.
6. Se comprueban permisos.
7. Se accede al archivo original.
8. Se extrae el contenido necesario.
9. Se devuelve el contenido al agente.
10. Hermes analiza la información.
11. Responde con referencia al recurso.
12. No se carga permanentemente el documento completo en memoria.

## 7. Memoria persistente

1. Se registra la interacción.
2. OpenViking identifica datos potencialmente reutilizables, los clasifica, detecta duplicados y contradicciones (sin pipeline propio).
3. Se comprueba si existe una regla que impida guardar el dato.
4. Se guarda en el sistema correspondiente.
5. OpenViking organiza el contenido.
6. En futuras sesiones se recupera únicamente cuando resulta relevante.

## 8. Automejora

1. Se registra un fallo o procedimiento mejorable.
2. Drakter identifica una posible causa.
3. Propone una modificación.
4. Crea una versión de prueba.
5. Ejecuta pruebas.
6. Compara el resultado.
7. Presenta el cambio.
8. El usuario aprueba o rechaza (siempre, también en Skills).
9. Si se aprueba, se publica la nueva versión.
10. Se conserva la versión anterior para poder revertir.

## 9. Cierre

1. Se detiene o finaliza la conversación.
2. Se completan las operaciones pendientes.
3. Se registra la actividad.
4. Se consolidan los recuerdos permitidos.
5. Se actualizan índices cuando corresponda.
6. Se guarda el estado de la interfaz.
7. Los servicios permanecen activos o se cierran según la configuración.

# PARTE 3. CRITERIOS DE ACEPTACIÓN

Drakter no se considerará funcionalmente completo hasta que cumpla estas condiciones:

1. La GUI puede iniciar y detener los servicios.
2. Hermes puede conversar desde la aplicación.
3. El personaje refleja los estados reales del agente.
4. La voz funciona sin depender de servicios de pago para STT y TTS en la configuración local.
5. La boca se sincroniza con el audio de forma aceptable.
6. Las tareas y subtareas se pueden crear y gestionar.
7. Los proyectos pueden contener tareas relacionadas.
8. Los hábitos mantienen un historial.
9. El calendario gestiona eventos y bloques.
10. Las asignaturas admiten horarios recurrentes.
11. Los recursos pueden catalogarse sin cargarlos completos.
12. La búsqueda localiza recursos por metadatos y contenido indexado.
13. Las relaciones funcionan entre módulos.
14. Hermes puede utilizar todas las operaciones autorizadas.
15. La memoria persiste entre sesiones.
16. El contexto se recupera de forma selectiva.
17. Las skills pueden actualizarse con control de versiones.
18. Las acciones sensibles requieren confirmación.
19. Existe registro de actividad.
20. Se pueden realizar y restaurar copias de seguridad.

**Resultado esperado:** Drakter será una aplicación de escritorio local con un agente inteligente integrado, una identidad propia, voz, personaje animado, memoria persistente y un Workspace unificado que podrá gestionar tanto el usuario como el agente mediante una única arquitectura de datos y operaciones.
