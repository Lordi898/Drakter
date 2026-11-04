# DRAKTER

## Plan maestro de implementación, arquitectura y desarrollo

**Versión del documento:** 1.0  
**Fecha:** 4 de noviembre de 2026  
**Tipo de proyecto:** Agente personal de IA con aplicación de escritorio propia  
**Motor principal:** Hermes  
**Modelo de razonamiento inicial:** Claude Haiku 5.5  
**Sistema operativo inicial:** Linux, con arquitectura preparada para Windows  
**Estrategia:** Desarrollo modular, local-first y ampliable.

> **Prevalencia.** Donde este plan contradiga una decisión registrada, manda la entrada más reciente de `DECISIONS.md` (orden completo en su entrada "Jerarquía de documentos y numeración única de fases"). La fase se identifica por el **paso** de la tabla de esa entrada; la numeración de Fases de este documento es solo la suya. Las listas de casillas de la Parte XVI son históricas: la lista viva es `docs/IMPLEMENTATION_STATUS.md`. Los conflictos de esquema y de catálogo (entidades, campos, estados, herramientas) los resuelve la entrada "Contratos de datos que resuelve drakter/contratos".

# PARTE I. DEFINICIÓN GENERAL DEL PROYECTO

## 1. Objetivo

Drakter será un agente personal de inteligencia artificial integrado en una aplicación de escritorio desarrollada desde cero.

No será únicamente un chatbot. Tendrá capacidad para:

- Conversar mediante texto y voz.
- Mantener una personalidad consistente.
- Recordar información entre conversaciones.
- Consultar y gestionar memoria persistente.
- Ejecutar herramientas y habilidades.
- Gestionar tareas, subtareas, proyectos y hábitos.
- Administrar un calendario y bloques de tiempo.
- Conocer las asignaturas y el horario de clases.
- Consultar un almacén de archivos y documentos indexados.
- Crear relaciones entre todos los elementos del Workspace.
- Consultar, modificar y organizar los datos mediante instrucciones en lenguaje natural.
- Mostrar un personaje animado que represente sus estados operativos y expresivos.
- Controlar de forma integrada los módulos de su propia aplicación.
- Registrar sus operaciones y permitir revisar sus decisiones.
- Aprender preferencias y mejorar su comportamiento mediante un sistema controlado.

El proyecto se dividirá en tres grandes sistemas:

1. **Drakter Core:** agente, razonamiento, personalidad, memoria, herramientas y lógica.
2. **Drakter Desktop:** aplicación de escritorio, interfaz, personaje, voz y paneles.
3. **Drakter Workspace:** datos, tareas, proyectos, calendario, hábitos, asignaturas, archivos y relaciones.

Los tres estarán conectados mediante APIs internas.

## 2. Decisiones tecnológicas fijadas

| **Área** | **Tecnología elegida** |
| --- | --- |
| Agente principal | Hermes |
| Modelo principal | Claude Haiku 5.5 |
| Interfaz | React |
| Lenguaje de interfaz | TypeScript |
| Aplicación de escritorio | Electron |
| Estilos | Tailwind CSS |
| Componentes UI | shadcn/ui |
| Animaciones del personaje | Rive |
| Backend propio | Python + FastAPI |
| Comunicación interna | REST + WebSocket |
| Base de datos principal | SQLite |
| Búsqueda textual | SQLite FTS5 |
| Voz STT | Faster-Whisper |
| Detección de voz | Silero VAD |
| Palabra de activación | openWakeWord |
| Voz TTS principal | Kokoro |
| Voz TTS alternativa | Piper |
| Memoria nativa del agente | Memoria nativa de Hermes |
| Memoria jerárquica (L0/L1/L2) | OpenViking |
| Contexto del repositorio de desarrollo (utilidad opcional, fuera del producto) | ByteRover |
| Habilidades del agente | Hermes Skills |
| Orquestación futura de voz | LiveKit Agents |
| Control de versiones | Git + GitHub |
| Entorno de desarrollo | Visual Studio Code |

La aplicación empezará siendo local y de un único usuario.

La arquitectura permitirá incorporar PostgreSQL, otros modelos, más motores de voz y servicios externos sin tener que reconstruir el proyecto.

## 3. Principios de diseño

1. Separación entre agente, interfaz y datos.
2. Un único origen de verdad para los datos del Workspace.
3. Ningún módulo debe duplicar innecesariamente la información de otro.
4. Todas las operaciones deben pasar por servicios internos.
5. Drakter utilizará las mismas reglas de negocio que la interfaz.
6. La memoria no se cargará completa en cada conversación.
7. Los documentos se leerán bajo demanda.
8. Las operaciones importantes tendrán permisos y confirmaciones.
9. Las acciones del agente quedarán registradas.
10. La personalidad estará separada del modelo de IA.
11. La voz estará separada del razonamiento.
12. Las actualizaciones del sistema no podrán modificar automáticamente el código de producción.
13. Los módulos tendrán interfaces estables para facilitar futuras ampliaciones.

# PARTE II. ARQUITECTURA GENERAL

## 4. Estructura por capas

Drakter tendrá las siguientes capas.

### Capa 1. Interfaz y presentación

Responsable de mostrar y permitir utilizar Drakter.

Incluye:

- Aplicación Electron.
- React y TypeScript.
- Navegación.
- Paneles.
- Chat.
- Personaje animado.
- Configuración.
- Indicadores de actividad.
- Notificaciones.
- Visualización de tareas, proyectos y calendario.

### Capa 2. Comunicación y API

Responsable de conectar la GUI con los servicios internos.

Incluye:

- API REST.
- WebSocket.
- Autenticación local entre componentes.
- Gestión de sesiones.
- Eventos.
- Validación de mensajes.
- Gestión de errores.
- Control de conexiones.

### Capa 3. Backend y lógica de aplicación

Responsable de gestionar el funcionamiento real de Drakter.

Incluye:

- FastAPI.
- Servicios de tareas.
- Servicios de proyectos.
- Servicios de hábitos.
- Servicios de calendario.
- Servicios de asignaturas.
- Servicios del almacén.
- Servicios de relaciones.
- Servicios de configuración.
- Servicios de permisos.
- Registro de operaciones.

### Capa 4. Agente e inteligencia

Responsable del razonamiento y de la ejecución de instrucciones.

Incluye:

- Hermes.
- Claude Haiku 5.5.
- Contexto de conversación.
- Constructor de contexto.
- Planificación de operaciones.
- Selección de herramientas.
- Ejecución de Skills.
- Interpretación de resultados.
- Gestión de errores.

### Capa 5. Memoria y conocimiento

Responsable de conservar y recuperar información.

Incluye:

- Memoria de trabajo.
- Memoria episódica.
- Memoria semántica.
- Memoria procedimental.
- Memoria nativa de Hermes.
- OpenViking.
- Archivos de contexto.
- Índices.
- Recuperación selectiva.

### Capa 6. Voz y percepción

Responsable de escuchar y hablar.

Incluye:

- openWakeWord.
- Silero VAD.
- Faster-Whisper.
- Kokoro.
- Piper.
- Sincronización labial.
- Gestor de audio.
- Interrupciones.
- Estados de voz.

### Capa 7. Persistencia y almacenamiento

Responsable de guardar los datos.

Incluye:

- SQLite.
- SQLite FTS5.
- Base de datos del Workspace.
- Archivos de configuración.
- Índices.
- Documentos originales.
- Memoria externa.
- Registros.
- Copias de seguridad.

# PARTE III. DRAKTER DESKTOP

## 5. Aplicación de escritorio

### 5.1. Tecnologías

- Electron: contenedor de escritorio.
- React: interfaz.
- TypeScript: lógica tipada.
- Tailwind CSS: estilos.
- shadcn/ui: componentes.
- Rive: animaciones del personaje.
- WebSocket: comunicación en tiempo real con el backend.

La GUI se desarrollará desde cero.

Troko Desktop será una referencia de experiencia visual y de interacción, no una dependencia obligatoria ni una copia de su código.

### 5.2. Diseño general

La aplicación tendrá:

- Barra lateral de navegación.
- Área central de contenido.
- Panel de información contextual.
- Acceso rápido al chat.
- Indicador del estado de Drakter.
- Notificaciones.
- Configuración global.

Las secciones serán predefinidas. No se permitirá crear módulos arbitrarios ni reorganizar la arquitectura de la aplicación.

Sí se permitirá crear libremente los elementos de trabajo que correspondan a cada módulo.

### 5.3. Pestañas

1. Cara de Drakter.
2. Hábitos.
3. Tareas.
4. Proyectos.
5. Almacén.
6. Calendario.
7. Asignaturas.
8. Relaciones.
9. Configuración.

Se podrán añadir posteriormente vistas de actividad, estadísticas y monitorización.

## 6. Cara animada de Drakter

### 6.1. Tecnología

Rive será el motor principal de animación.

La cara tendrá un diseño gráfico propio, compuesto por:

- Ojos.
- Párpados.
- Pupilas.
- Cejas o elementos expresivos equivalentes.
- Boca.
- Elementos decorativos.
- Animaciones de transición.

### 6.2. Estados funcionales

Los estados funcionales serán independientes de las expresiones:

| **Estado** | **Significado** |
| --- | --- |
| idle | Disponible |
| listening | Escuchando |
| thinking | Procesando |
| speaking | Hablando |
| executing | Ejecutando una herramienta |
| success | Operación completada |
| error | Error |
| interrupted | Interrumpido |
| offline | Desconectado |

### 6.3. Expresiones

Se implementarán expresiones como:

- `neutral`
- `curious`
- `focused`
- `happy`
- `concerned`
- `confused`
- `calm`

Son un catálogo cerrado de 7 (decisión "Las expresiones no tienen campo propio"). La expresión viaja en el campo `animation` del objeto expresivo; no existe un campo `expression` propio. La app valida cada valor contra este catálogo.

Las expresiones se seleccionarán mediante información contextual generada por Drakter.

No se interpretarán como emociones humanas reales, sino como representación de su estado conversacional.

### 6.4. Sincronización labial

Se utilizará un sistema de sincronización entre el audio generado y la boca.

Orden de implementación:

1. Apertura de boca mediante intensidad de audio.
2. Ajuste de amplitud y velocidad.
3. Incorporación de fonemas o visemas si el motor de voz proporciona información compatible.
4. Sincronización de animaciones y audio.
5. Gestión de pausas y silencios.

### 6.5. Comunicación de estados

Drakter enviará eventos al frontend. La lista siguiente es orientativa: el catálogo definitivo está en `contracts/python/drakter_contracts/events.py` (entrada "Eventos WebSocket resueltos en contracts/" de `DECISIONS.md`).


- agent.listening
- agent.thinking
- agent.speaking
- agent.executing
- agent.success
- agent.error
- agent.interrupted
- agent.expression_changed

El frontend transformará estos eventos en animaciones.

# PARTE IV. HERMES Y EL CEREBRO DE DRAKTER

## 7. Hermes

Hermes será el motor de agente principal.

Se encargará de:

- Recibir mensajes.
- Mantener conversaciones.
- Razonar.
- Elegir herramientas.
- Ejecutar Skills.
- Consultar memoria.
- Construir respuestas.
- Coordinar las operaciones solicitadas por el usuario.

No será responsable de guardar directamente los datos del Workspace ni de gestionar visualmente la aplicación.

### 7.1. Modelo principal

Claude Haiku 5.5 será el modelo inicial mediante API.

Se utilizará para:

- Razonamiento.
- Comprensión del lenguaje natural.
- Planificación.
- Selección de herramientas.
- Interpretación de resultados.
- Generación de respuestas.
- Clasificación contextual.

La arquitectura mantendrá separado el proveedor del modelo para poder probar GPT-6 Luna u otros modelos posteriormente.

No se implementará un sistema complejo de enrutamiento entre modelos en la primera versión.

### 7.2. Herramientas de Hermes

Hermes utilizará:

- Skills.
- Herramientas de memoria.
- Herramientas del Workspace.
- Herramientas de voz cuando corresponda.
- Herramientas de consulta.
- Herramientas de administración autorizadas.

Cada herramienta tendrá:

- Nombre.
- Descripción.
- Parámetros.
- Validación.
- Permisos.
- Resultado estructurado.
- Tratamiento de errores.

### 7.3. Integración con el Workspace

Hermes no tendrá acceso directo e ilimitado a la base de datos.

Llamará a herramientas que utilizarán el backend de Drakter.

Ejemplo:

create_task(title, project_id, due_date, priority)

El backend comprobará los parámetros, permisos y relaciones antes de guardar la tarea.

# PARTE V. PERSONALIDAD Y CONTEXTO

## 8. Sistema de personalidad

La personalidad de Drakter será independiente del modelo de IA.

Se definirá mediante archivos de configuración y contexto.

### 8.1. Archivos

drakter/

└── agent/

└── identity/

├── SOUL.md

├── PERSONALITY.md

├── BEHAVIOR.md

├── COMMUNICATION.md

├── EMOTIONAL_STYLE.md

├── VALUES.md

├── USER.md

├── ENVIRONMENT.md

├── PREFERENCES.md

├── CURRENT_CONTEXT.md

├── CAPABILITIES.md

├── WORKSPACE_GUIDE.md

├── TOOL_GUIDE.md

└── SYSTEM_GUIDE.md

Los 14 archivos viven en `agent/identity/`; `agent/context/` y `agent/knowledge/` no forman parte de la estructura vigente (decisión "Los 14 archivos de identidad viven en agent/identity/"). La fuente es el repositorio: un cargador los compone y los publica en el `HERMES_HOME` del perfil de Drakter. `USER.md` y `PREFERENCES.md` son plantillas sin datos reales; el `USER.md` vivo es el nativo de Hermes (véase §10).

### 8.2. Responsabilidad de cada archivo

**SOUL.md**

Define quién es Drakter, su identidad y principios generales.

**PERSONALITY.md**

Define sus rasgos, humor, actitud, carácter y forma habitual de responder.

**BEHAVIOR.md**

Define cómo debe comportarse ante diferentes situaciones.

**COMMUNICATION.md**

Define estilo, vocabulario, longitud, formalidad y adaptación al contexto.

**EMOTIONAL_STYLE.md**

Define las expresiones y estados representativos que puede utilizar.

**VALUES.md**

Define principios, prioridades y límites.

**USER.md**

Plantilla, sin datos reales, de la información estable y relevante sobre el usuario. El `USER.md` vivo es el nativo de Hermes (véase §10).

**ENVIRONMENT.md**

Describe el entorno técnico, sistema operativo, dispositivos y servicios autorizados.

**PREFERENCES.md**

Plantilla de preferencias persistentes, sin datos reales; sigue el mismo criterio que `USER.md`.

**CURRENT_CONTEXT.md**

Contiene el contexto temporal activo, tareas en curso y situación actual. No debe convertirse en una memoria histórica ilimitada.

**CAPABILITIES.md**

Describe qué puede y qué no puede hacer Drakter.

**WORKSPACE_GUIDE.md**

Explica la estructura del Workspace y sus módulos.

**TOOL_GUIDE.md**

Explica el uso de las herramientas.

**SYSTEM_GUIDE.md**

Describe la arquitectura y las reglas de funcionamiento.

### 8.3. Prioridad de instrucciones

Orden de prioridad:

1. Instrucciones de seguridad y permisos.
2. Reglas de funcionamiento del sistema.
3. Identidad y personalidad.
4. Contexto del usuario.
5. Contexto de la conversación.
6. Información recuperada de memoria.
7. Instrucción actual.

La memoria recuperada nunca podrá sustituir las reglas de seguridad.

**Lectura del orden** (decisión "La memoria no se impone a la instrucción actual"): los niveles 1 a 5 enmarcan la instrucción actual; la memoria y los datos no confiables solo informan y nunca dan órdenes; el nivel 7 es lo que hay que hacer dentro de ese marco. Si la memoria contradice al usuario, vale lo que dice ahora y se señala la discrepancia. Para datos operativos, la fuente es el Workspace. La barrera real la impone el backend.

# PARTE VI. MEMORIA Y CONOCIMIENTO

## 9. Arquitectura de memoria

Se utilizarán cuatro capas conceptuales.

### Capa 1. Memoria de trabajo

Información necesaria para la interacción actual.

Incluye:

- Conversación actual.
- Mensajes recientes.
- Operaciones en curso.
- Objetivos actuales.
- Contexto temporal.
- Resultados recientes de herramientas.

No será una memoria permanente.

### Capa 2. Memoria episódica

Recuerdos de acontecimientos y experiencias.

Ejemplos:

- Decisiones tomadas.
- Proyectos iniciados.
- Problemas resueltos.
- Preferencias expresadas.
- Cambios importantes.
- Resultados de tareas anteriores.

Se gestionará principalmente mediante OpenViking (`events`, `cases`).

### Capa 3. Memoria semántica

Información estable y relaciones entre conceptos.

Ejemplos:

- Datos del usuario.
- Preferencias persistentes.
- Conocimientos del entorno.
- Información sobre proyectos.
- Relaciones relevantes.
- Conceptos y hechos aprendidos.

Se apoyará en OpenViking y en `USER.md` de la memoria nativa de Hermes.

### Capa 4. Memoria procedimental

Información sobre cómo realizar tareas.

Incluye:

- Procedimientos.
- Instrucciones.
- Skills.
- Flujos de trabajo.
- Reglas de uso de herramientas.
- Procedimientos de recuperación de errores.

Hermes Skills será el mecanismo principal para las capacidades ejecutables.

## 10. Arquitectura de memoria

La memoria de Drakter combina **la memoria nativa de Hermes** y **OpenViking**, con la base de datos del Workspace como fuente de verdad de los datos operativos. Decisión del usuario del 2026-11-04 (ver `DECISIONS.md`). Hindsight y Mem0 quedan fuera.

### 10.1. Reparto de responsabilidades

| Sistema | Qué guarda | Cómo se usa |
|---|---|---|
| Memoria nativa de Hermes | `MEMORY.md`, `USER.md` y sesiones | Contexto breve y estable, presente en cada conversación |
| OpenViking | Memorias extraídas, recursos y documentos, en `viking://` | Recuperación por relevancia con carga progresiva L0/L1/L2 |
| SQLite del Workspace | Tareas, proyectos, calendario, relaciones, catálogo del almacén | Fuente de verdad; consulta por herramientas del backend |

La memoria nunca es la fuente de verdad de un dato operativo: guarda la referencia a la entidad, no una copia de su estado.

Hermes solo admite un proveedor de memoria externo activo. Ese lugar lo ocupa OpenViking (`memory.provider: openviking`), y la memoria nativa sigue activa a su lado.

**`USER.md`:** en el repositorio (`agent/identity/USER.md`) solo hay una plantilla sin datos reales. El `USER.md` nativo, en el `HERMES_HOME` del perfil de Drakter, guarda lo esencial y OpenViking guarda lo demás. La plantilla rellenada por el usuario vive fuera del repositorio, en el directorio de datos de Drakter, y solo inicializa el `USER.md` nativo; a partir de ahí manda el nativo (decisión "agent/identity/USER.md es plantilla; el USER.md vivo es el de Hermes").

### 10.2. Las tres capas de OpenViking

| Capa | Lectura | Límite por defecto | Uso en Drakter |
|---|---|---|---|
| L0, resumen | `abstract` | 256 caracteres | Búsqueda vectorial y decidir si algo es relevante |
| L1, visión general | `overview` | 4.000 caracteres | Planificar y responder en la mayoría de los casos |
| L2, detalle | `read` | Sin límite uniforme | Contenido original, solo cuando L1 no basta |

Los límites son los de la configuración de OpenViking (`semantic.abstract_max_chars`, `semantic.overview_max_chars`). La documentación de Hermes habla de unos 100 tokens y 2.000 tokens: se medirá el consumo real. L0 y L1 se generan con un modelo (VLM), así que sin VLM disponible no hay resúmenes ni indexación semántica completa.

Estas capas L0/L1/L2 describen **nivel de detalle**. Son distintas de las cuatro capas de la sección 9 (trabajo, episódica, semántica y procedimental), que describen **tipo de memoria**.

### 10.3. Bases e indexación

- **Vectorial:** índice vectorial local de OpenViking, con vectores densos y dispersos, URI y texto de recuperación. L0 se usa para la recuperación y L1 para el reordenamiento.
- **Contenido:** AGFS, el sistema de archivos de OpenViking, guarda L0, L1 y L2.
- **Indexación semántica:** OpenViking procesa de abajo arriba: archivo, directorio y directorio padre.
- **Relacional:** SQLite del Workspace. OpenViking **no ofrece una base relacional de memorias**: su SQLite o MySQL interno sirve para colas, bloqueos y tareas. Las relaciones entre entidades viven en el Workspace; en OpenViking solo existen la jerarquía de URI y las referencias entre memorias y recursos (`resource_refs`).
- **Texto exacto:** FTS5 del Workspace, para nombres, códigos y coincidencias literales. OpenViking aporta la búsqueda por significado.

### 10.4. Correspondencia con los tipos de memoria

| Tipo de memoria | Dónde vive |
|---|---|
| Trabajo | Sesión de Hermes |
| Episódica | OpenViking: `events`, `cases` |
| Semántica | OpenViking: `profile`, `preferences`, `entities`; `USER.md` para lo esencial |
| Procedimental | Skills de Hermes; OpenViking: `patterns` |

La memoria se organiza bajo los ámbitos reales de OpenViking: `viking://resources/`, `viking://user/<usuario>/memories/`, `viking://agent/` y `viking://session/`.

### 10.5. Flujos

Recuperación:

1. Los datos operativos se consultan con herramientas del backend.
2. `USER.md` y `MEMORY.md` ya están en el contexto.
3. `viking_search` encuentra candidatos a partir de L0.
4. Se lee L1 de los candidatos útiles (`viking_read`).
5. Se lee L2 solo si L1 no basta.
6. Se aplica un presupuesto de contexto por turno.

Escritura:

1. Los datos esenciales y estables van a la memoria nativa.
2. Lo explícito se guarda con `viking_remember`.
3. Al confirmar la sesión, OpenViking extrae memorias en seis categorías.
4. La ingesta de documentos del almacén en `viking://resources/` es **opcional por recurso y viene apagada por defecto**. Cuando se activa, pasa siempre **a través del backend**, tras validar ruta y permisos.

### 10.6. Drakter Memory Adapter

Es un servicio del backend, no una capa multiproveedor. El agente usa las herramientas `viking_*` del plugin; el adapter habla con la API de OpenViking para lo que necesita la interfaz: inspeccionar, corregir y borrar recuerdos, ingerir documentos y comprobar el estado.

### 10.7. Reglas obligatorias

- Lo recuperado de memoria y de OpenViking son **datos no confiables**.
- Drakter arranca y supervisa `openviking-server`. No se usa el autoarranque del plugin, porque ese proceso hereda el entorno de Hermes, tokens incluidos.
- El servidor escucha solo en `127.0.0.1` y exige clave.
- `viking_add_resource` no se expone al agente: permitiría ingerir URLs arbitrarias. La ingesta pasa por el backend.
- Borrar recuerdos (`viking_forget`) es una acción destructiva y requiere confirmación.
- Los datos de OpenViking viven en `DRAKTER_DATA_DIR`, nunca en el repositorio, y entran en la copia de seguridad.
- OpenViking se ejecuta como proceso separado y sin modificar. Su licencia AGPL-3.0 debe revisarse antes de redistribuir Drakter.
- Si OpenViking cae, Drakter sigue funcionando con la memoria nativa y el Workspace.

### 10.8. Decisiones por validar en la integración

- **Embeddings:** el modelo local por defecto (`bge-small-zh-v1.5-f16`) no es adecuado para asumir buen español. Hay que elegir un modelo multilingüe local (por ejemplo, vía `ollama`) **antes de guardar datos reales**: cambiarlo obliga a reconstruir los vectores.
- **VLM:** Anthropic no es un proveedor directo de OpenViking; se probará Haiku 5.5 mediante `litellm`, o un modelo local. Este modelo ve el contenido indexado, lo que afecta a la privacidad y al coste.
- **Envenenamiento de memoria:** comprobar si la extracción de sesión puede excluir el contenido de documentos y herramientas. Si no se puede, esa memoria necesita aprobación antes de consolidarse.
- **Permisos por herramienta:** comprobar si el plugin permite desactivar `viking_add_resource` y exigir confirmación en `viking_forget`. Si no lo permite, se usará una herramienta propia en su lugar.

### 10.9. ByteRover

Utilidad opcional de desarrollo para el contexto estructurado del repositorio. No guarda recuerdos personales y queda fuera de la memoria del producto y de la Capa 5 (decisión "Memoria sin pipeline propio ni recuerdos en el repositorio").

## 11. Archivos de memoria

`memory/` guarda **configuración e integración** de la memoria (configuración de OpenViking y del proveedor de Hermes, adaptador, scripts de comprobación). **Nunca guarda recuerdos ni datos personales**: los recuerdos viven en la memoria nativa de Hermes y en OpenViking, y sus datos en `DRAKTER_DATA_DIR`, fuera del repositorio.

No hay pipeline propio de memoria. Extraer, clasificar, deduplicar y resolver contradicciones se configura y se comprueba en OpenViking; lo que falte se anota con ⚠️ en `IMPLEMENTATION_STATUS.md`. La taxonomía de la sección 9 y las capas L0/L1/L2 de la sección 10 se conservan.

Las bases de datos internas de OpenViking no se manipularán directamente desde la GUI. Se utilizarán sus interfaces y adaptadores.

# PARTE VII. WORKSPACE

## 12. Modelo de datos común

El Workspace tendrá una base de datos SQLite principal.

Cada elemento tendrá:

- Identificador único.
- Tipo.
- Nombre o título.
- Descripción.
- Fecha de creación.
- Fecha de modificación.
- Estado.
- Metadatos.
- Relaciones.

Se utilizarán identificadores UUID.

### 12.1. Entidades principales

- Task.
- Subtask.
- Project.
- Habit.
- HabitRecord.
- CalendarEvent.
- TimeBlock.
- Subject.
- ClassSession.
- Resource.
- Note.
- Folder.
- Tag.
- Relationship.

### 12.2. Sistema de relaciones

Las relaciones se almacenarán en una tabla común.

Campos:

- id
- source_type
- source_id
- target_type
- target_id
- relationship_type
- metadata
- created_at

Tipos iniciales:

- belongs_to
- related_to
- scheduled_for
- uses_resource
- depends_on
- supports
- studies
- parent_of
- references
- derived_from

Se podrán ampliar mediante migraciones controladas.

Las relaciones jerárquicas de tareas y carpetas tendrán además sus propias reglas de integridad.

## 13. Módulo de tareas

Funciones:

- Crear tareas.
- Editar tareas.
- Eliminar tareas.
- Completar tareas.
- Reabrir tareas.
- Crear subtareas.
- Anidar subtareas.
- Asignar prioridades.
- Asignar fechas.
- Añadir descripciones.
- Añadir etiquetas.
- Asociar proyectos.
- Asociar asignaturas.
- Asociar recursos.
- Asociar bloques de tiempo.
- Crear dependencias.
- Consultar historial.

Campos principales:

- ID.
- Título.
- Descripción.
- Estado.
- Prioridad.
- Fecha de creación.
- Fecha límite.
- Fecha de finalización.
- Proyecto asociado.
- Asignatura asociada.
- Tarea padre.
- Orden.
- Metadatos.

Estados iniciales:

- Pendiente.
- En progreso.
- En espera.
- Completada.
- Cancelada.

## 14. Módulo de proyectos

Funciones:

- Crear proyectos.
- Editar proyectos.
- Archivar proyectos.
- Establecer objetivos.
- Establecer fechas.
- Asociar tareas.
- Asociar recursos.
- Asociar asignaturas.
- Consultar progreso.
- Consultar dependencias.
- Mostrar actividad.

Campos:

- ID.
- Nombre.
- Descripción.
- Estado.
- Prioridad.
- Fecha de inicio.
- Fecha objetivo.
- Fecha de finalización.
- Metadatos.

## 15. Módulo de hábitos

Funciones:

- Crear hábitos.
- Editar hábitos.
- Registrar cumplimiento.
- Consultar historial.
- Consultar estadísticas.
- Definir frecuencia.
- Establecer recordatorios.
- Relacionar hábitos con proyectos y objetivos.

Campos:

- ID.
- Nombre.
- Descripción.
- Frecuencia.
- Días activos.
- Hora recomendada.
- Estado.
- Fecha de inicio.
- Fecha de finalización.

Los registros de cumplimiento se guardarán por separado.

No se eliminará el historial al modificar un hábito.

## 16. Módulo de calendario

Funciones:

- Vista diaria.
- Vista semanal.
- Vista mensual.
- Crear eventos.
- Crear bloques de tiempo.
- Editar eventos.
- Eliminar eventos.
- Asociar tareas.
- Asociar proyectos.
- Asociar asignaturas.
- Consultar disponibilidad.
- Detectar solapamientos.

Los bloques de tiempo serán elementos propios, no simples fechas de vencimiento.

Campos:

- ID.
- Título.
- Descripción.
- Inicio.
- Final.
- Tipo.
- Estado.
- Relaciones.
- Recordatorio.

Se gestionarán las zonas horarias de manera explícita.

## 17. Módulo de asignaturas

Funciones:

- Crear asignaturas.
- Editar asignaturas.
- Definir horario.
- Definir aula.
- Definir profesor opcional.
- Asociar apuntes.
- Asociar tareas.
- Asociar proyectos.
- Consultar calendario de clases.
- Consultar recursos relacionados.

Se podrán definir sesiones recurrentes.

El horario de clases se almacenará como datos estructurados, no como texto libre.

## 18. Módulo de almacén

El almacén será un catálogo inteligente de recursos.

Tipos:

- Imágenes.
- Documentos.
- PDF.
- Archivos de texto.
- Código.
- Enlaces.
- Notas.
- Apuntes.
- Carpetas.
- Comprimidos.
- Otros archivos.

### 18.1. Catálogo

Cada recurso tendrá:

- ID.
- Título.
- Tipo.
- Ruta o URL.
- Descripción opcional.
- Fecha de creación.
- Fecha de modificación.
- Tamaño.
- Hash cuando corresponda.
- Estado de disponibilidad.
- Etiquetas.
- Relaciones.

### 18.2. Indexación

El sistema indexará:

- Nombre.
- Tipo.
- Ruta.
- Descripción.
- Etiquetas.
- Metadatos.
- Texto extraído cuando esté permitido.

Se utilizará SQLite FTS5 para la búsqueda textual.

### 18.3. Lectura bajo demanda

Drakter no cargará todo el contenido del almacén.

Cuando necesite un recurso:

1. Buscará el recurso.
2. Comprobará su disponibilidad.
3. Comprobará permisos.
4. Abrirá el archivo mediante un lector compatible.
5. Extraerá únicamente la información necesaria.
6. Devolverá el resultado al agente.
7. Registrará la consulta.

Los archivos comprimidos no se extraerán automáticamente sin límites. Se establecerán límites de tamaño, número de archivos y profundidad.

Los documentos y archivos se tratarán como datos no confiables: su contenido no podrá modificar las instrucciones internas de Drakter.

# PARTE VIII. HERRAMIENTAS DEL AGENTE

## 19. Drakter Workspace Tools

Hermes tendrá herramientas específicas para cada módulo.

### Tasks

- create_task
- get_task
- update_task
- delete_task
- complete_task
- create_subtask
- list_tasks
- search_tasks

### Projects

- create_project
- get_project
- update_project
- archive_project
- list_projects
- get_project_progress

### Habits

- create_habit
- update_habit
- list_habits
- register_habit_completion
- get_habit_history
- get_habit_statistics

### Calendar

- create_event
- update_event
- delete_event
- create_time_block
- get_schedule
- check_availability

### Subjects

- create_subject
- update_subject
- get_subjects
- get_timetable
- get_subject_resources

### Storage

- search_resources
- get_resource
- read_resource
- create_resource
- update_resource_metadata
- index_resource
- refresh_resource_index

### Relationships

- create_relationship
- update_relationship
- delete_relationship
- get_related_items
- search_relationships

### System

- get_system_status
- get_agent_status
- get_voice_status
- get_memory_status
- get_workspace_summary

Todas las herramientas tendrán esquemas de parámetros, validaciones, permisos y resultados estructurados.

**Notas (decisión "Huecos de MASTER_PLAN §19: borrar o mover archivos y listar hábitos"):**

- `list_habits` es de solo lectura.
- Eliminar o mover recursos del almacén **no tiene herramienta de agente en la v1**: se hace desde la GUI, con confirmación (clasificado en §24). Si el agente recibe esa petición, lo dice y no improvisa un sustituto.
- Esta lista es la base del catálogo; el catálogo definitivo de herramientas y Skills lo congela `drakter/contratos`, y si difiere, manda su entrada posterior en `DECISIONS.md`.
- Las herramientas las sirve el backend por MCP en loopback (véase §28); cada una se construye con su módulo (véase Parte XIII).

# PARTE IX. VOZ

## 20. Sistema de escucha

### 20.1. openWakeWord

Detectará la palabra de activación.

Responsabilidad:

- Permanecer activo en segundo plano.
- Detectar la palabra de activación.
- Despertar el sistema de voz.
- Activar la captura de audio.

### 20.2. Silero VAD

Detectará cuándo existe voz humana.

Responsabilidad:

- Identificar inicio de voz.
- Identificar final de voz.
- Reducir silencios.
- Gestionar fragmentos de audio.
- Evitar enviar audio innecesario al STT.

### 20.3. Faster-Whisper

Será el motor de reconocimiento de voz.

Configuración inicial:

- Modelo small.
- Ejecución CPU INT8.
- Idioma español configurado inicialmente.
- Modelo medium como alternativa si las pruebas de rendimiento lo justifican.

La máquina de desarrollo y de comprobación es un i7-8665U de 8 hilos con 14 GB de RAM y gráfica integrada Intel UHD 620, sin VRAM dedicada (decisión "Hardware real y paralelismo acotado"). La voz se dimensiona para CPU y las cifras de rendimiento solo se publican medidas.

Se medirá latencia real, uso de CPU y de RAM antes de decidir el modelo; no hay GPU dedicada con la que contar.

## 21. Sistema TTS

### 21.1. Kokoro

Motor TTS principal.

Responsabilidades:

- Convertir texto en voz.
- Generar fragmentos de audio.
- Permitir selección de voz.
- Integrarse con el gestor de voz.

### 21.2. Piper

Motor alternativo.

Se utilizará como respaldo por su eficiencia y funcionamiento local.

### 21.3. Adaptación de voz

Se creará un módulo denominado Voice Personality Engine.

Recibirá:

- Texto.
- Contexto.
- Intención.
- Estado del agente.
- Expresión.
- Prioridad comunicativa.

Producirá parámetros de voz:

- Velocidad.
- Volumen.
- Pausas.
- Entonación disponible.
- Voz seleccionada.
- Intensidad expresiva.

Se aplicarán únicamente parámetros que el motor de voz admita realmente.

No se supondrá que Kokoro o Piper permiten controlar emociones arbitrarias si sus interfaces no ofrecen esa capacidad.

## 22. Flujo de voz

1. openWakeWord detecta la palabra de activación.
2. Silero VAD detecta el comienzo de voz.
3. Se captura el audio.
4. VAD detecta el final de la intervención.
5. Faster-Whisper transcribe.
6. El texto se envía a Hermes.
7. Hermes razona y consulta herramientas.
8. Se genera una respuesta.
9. Voice Personality Engine adapta la salida.
10. Kokoro genera audio.
11. La aplicación reproduce la voz.
12. La cara sincroniza su boca.
13. Se registra el resultado.

### 22.1. Interrupciones

Se implementará:

- Detección de nueva voz mientras Drakter habla.
- Parada de reproducción.
- Cancelación del audio pendiente.
- Cambio a estado listening.
- Envío de la nueva intervención.

### 22.2. LiveKit Agents

No será una dependencia de la primera versión.

Se incorporará en una fase posterior si necesitamos:

- Streaming de audio avanzado.
- Comunicación de baja latencia.
- Gestión de sesiones de voz complejas.
- Transporte de audio más sofisticado.
- Arquitectura multimodal en tiempo real.

# PARTE X. AUTOMEJORA Y AUTOEVOLUCIÓN

## 23. Sistema de mejora controlada

Drakter tendrá capacidad para identificar oportunidades de mejora, pero no modificará libremente su propio código ni sus reglas de seguridad.

Se implementará un ciclo controlado:

1. Detectar un problema o una necesidad.
2. Registrar el evento.
3. Clasificarlo.
4. Identificar su causa probable.
5. Proponer una mejora.
6. Crear una propuesta documentada.
7. Ejecutar pruebas en entorno aislado.
8. Mostrar resultados.
9. Solicitar autorización del usuario (siempre).
10. Aplicar cambios autorizados.
11. Registrar la versión y el resultado.

Todo cambio pasa por propuesta y autorización, también en Skills. Lo publicado al agente en uso (identidad, Skills, configuración del perfil) cuenta como producción (decisión "Trabajo sin clave y alcance de automejora, copias y v1").

### 23.1. Archivos

drakter/

└── improvement/

├── feedback/

├── proposals/

├── evaluations/

├── experiments/

├── changelog/

└── reports/

### 23.2. Tipos de mejora

- Preferencias de comunicación.
- Ajustes de contexto.
- Corrección de Skills.
- Mejora de procedimientos.
- Ajustes de recuperación de memoria.
- Mejoras de rendimiento.
- Mejoras de interfaz.
- Corrección de errores.

### 23.3. Protección

No podrá:

- Modificar sus permisos para ampliarlos.
- Desactivar confirmaciones.
- Cambiar sus reglas de seguridad.
- Modificar producción (código, identidad, Skills o configuración publicada al agente) sin autorización.
- Eliminar registros de auditoría.
- Ejecutar cambios no probados.

El repositorio Git será el mecanismo de control de versiones.

# PARTE XI. SEGURIDAD Y FIABILIDAD

## 24. Permisos

Se definirán permisos por categoría:

- Lectura.
- Creación.
- Edición.
- Eliminación.
- Ejecución.
- Administración.

Las acciones se clasificarán por riesgo.

### Acciones ordinarias

Podrán ejecutarse directamente si están autorizadas:

- Consultar tareas.
- Consultar proyectos.
- Buscar documentos.
- Consultar calendario.
- Consultar hábitos.

### Acciones que requieren confirmación

La confirmación es obligatoria (el undo, si existe, es adicional). Flujo: la herramienta destructiva crea una confirmación pendiente y devuelve su id sin ejecutar; solo la GUI la resuelve, por un endpoint que no es herramienta; la ejecución y la auditoría ocurren después. Los detalles los congela `drakter/contratos` (decisión "Herramientas con su módulo; confirmación y auditoría antes de la primera").

- Eliminar elementos.
- Eliminar archivos.
- Mover grandes cantidades de recursos.
- Modificar muchas relaciones.
- Realizar operaciones masivas.
- Cambiar configuraciones sensibles.

### Acciones prohibidas por defecto

- Ejecutar comandos arbitrarios sin autorización.
- Acceder a archivos fuera de las ubicaciones permitidas.
- Modificar permisos de seguridad.
- Alterar el sistema de auditoría.

## 25. Registro y auditoría

Se registrará:

- Acción.
- Usuario o agente que la solicitó.
- Herramienta utilizada.
- Parámetros relevantes.
- Resultado.
- Fecha.
- Errores.
- Confirmación recibida.

Los registros no almacenarán innecesariamente claves API ni información sensible.

## 26. Copias de seguridad

Se implementará:

- Copia de SQLite.
- Copia de configuración.
- Copia de la identidad.
- Copia de las Skills.
- Copia de los datos de OpenViking.
- Copia del home de Hermes.
- Copia de índices reconstruibles.
- Copia de metadatos del almacén.
- Exportación de datos.
- Restauración verificada.

Las copias no incluyen secretos y no deben incluir automáticamente todos los documentos originales si estos permanecen en ubicaciones externas.

# PARTE XII. ESTRUCTURA DEL REPOSITORIO

## 27. Organización de carpetas

Drakter/

│

├── desktop/

│   ├── electron/

│   ├── src/

│   │   ├── app/

│   │   ├── components/

│   │   ├── pages/

│   │   ├── navigation/

│   │   ├── character/

│   │   ├── chat/

│   │   ├── modules/

│   │   │   ├── habits/

│   │   │   ├── tasks/

│   │   │   ├── projects/

│   │   │   ├── storage/

│   │   │   ├── calendar/

│   │   │   ├── subjects/

│   │   │   └── relationships/

│   │   ├── settings/

│   │   ├── hooks/

│   │   ├── services/

│   │   ├── stores/

│   │   └── types/

│   └── assets/

│       ├── icons/

│       ├── images/

│       └── rive/

│

├── backend/

│   ├── app/

│   │   ├── api/

│   │   ├── core/

│   │   ├── database/

│   │   ├── models/

│   │   ├── schemas/

│   │   ├── services/

│   │   ├── repositories/

│   │   ├── integrations/

│   │   │   ├── hermes/

│   │   │   ├── memory/

│   │   │   ├── voice/

│   │   │   └── storage/

│   │   ├── tools/

│   │   ├── permissions/

│   │   ├── events/

│   │   └── audit/

│   ├── migrations/

│   └── tests/

│

├── agent/

│   ├── identity/      (los 14 archivos .md)

│   ├── skills/

│   ├── mcp_server/    (servidor MCP delgado de herramientas, sin lógica de negocio)

│   └── configuration/

│

├── memory/            (solo configuración e integración; sin recuerdos)

│

├── voice/

│   ├── wakeword/

│   ├── vad/

│   ├── stt/

│   ├── tts/

│   ├── personality/

│   ├── audio/

│   └── tests/

│

├── workspace/         (código del módulo; no guarda datos)

│

├── improvement/

│   ├── feedback/

│   ├── proposals/

│   ├── evaluations/

│   ├── experiments/

│   ├── changelog/

│   └── reports/

│

├── docs/

│   ├── architecture/

│   ├── api/

│   ├── database/

│   ├── workflows/

│   ├── installation/

│   └── decisions/

│

├── scripts/

├── tests/

├── .env.example

├── .gitignore

├── README.md

└── CHANGELOG.md

Los archivos de configuración y secretos se mantendrán fuera del repositorio.

**Reglas de esta estructura** (decisión "Datos fuera del repositorio y estructura de carpetas"):

- Los datos de ejecución (SQLite, almacén, índices, exportaciones, copias, datos de OpenViking, home de Hermes) viven en `DRAKTER_DATA_DIR`, que por defecto es el `user_data_dir("drakter")` fijado en `backend/CONTRACT.md`. `workspace/` no guarda datos.
- Las carpetas se crean **cuando entra código**, no todas al inicio. Este árbol es el destino, no una lista de carpetas a crear de golpe.
- No se usan `apps/` ni `docker-compose`.
- La configuración no sensible puede versionarse; la sensible, nunca (credenciales en `~/.config/drakter/.env`).
- Las Skills y la identidad tienen su fuente en `agent/` y se publican al perfil de Hermes.

# PARTE XIII. IMPLEMENTACIÓN POR FASES

**Cómo leer esta parte** (decisiones "Jerarquía de documentos y numeración única de fases" y "Herramientas con su módulo; confirmación y auditoría antes de la primera"):

- El orden real de desarrollo es el de los 20 pasos de la tabla de `DECISIONS.md`; las Fases de abajo se ejecutan en ese orden. En particular, **Skills y herramientas (Fase 11, paso 14) va antes que Memoria (Fase 10, paso 15)**, y la Skill de memoria pasa al paso 15.
- Cada herramienta se construye **con su módulo** (tareas, proyectos, hábitos, etc.) y se comprueba por llamada directa; la Fase 11 integra las Skills y comprueba la selección de herramientas con el modelo.
- Permisos, confirmación pendiente y auditoría van en el backend base o en el modelo de datos, **antes de la primera herramienta**. Las tareas de seguridad de la Fase 14 pasan a ser revisión y endurecimiento.
- Las "pruebas" y "pruebas completas" de las tareas y los criterios de finalización se leen según `CLAUDE.md` §4: una comprobación rápida de que funciona y se ve bien, sin suites. Solo se escribe un test puntual en los casos que §4 enumera.

## Fase 0. Especificación y preparación

Objetivo: dejar preparada la arquitectura antes de desarrollar funcionalidades.

Tareas:

1. Crear repositorio Git.
2. Crear estructura inicial.
3. Documentar arquitectura.
4. Definir convenciones de nombres.
5. Definir modelos de datos.
6. Definir API.
7. Definir eventos.
8. Definir permisos.
9. Definir sistema de configuración.
10. Preparar entorno de desarrollo.
11. Definir estrategia de pruebas.
12. Documentar decisiones técnicas.

Criterio de finalización:

La estructura, los contratos y los modelos principales están documentados y aprobados.

## Fase 1. Infraestructura base

Objetivo: conseguir que la aplicación y el backend funcionen.

Tareas:

1. Crear proyecto Electron.
2. Configurar React.
3. Configurar TypeScript.
4. Configurar Tailwind.
5. Instalar y configurar shadcn/ui.
6. Crear backend FastAPI.
7. Configurar SQLite.
8. Crear sistema de migraciones.
9. Crear API REST.
10. Crear WebSocket.
11. Configurar comunicación GUI-backend.
12. Crear gestión de errores.
13. Crear sistema de logs.
14. Crear configuración local.
15. Preparar empaquetado inicial.

Criterio de finalización:

La aplicación se abre, se conecta al backend, realiza peticiones y recibe eventos en tiempo real.

## Fase 2. Integración de Hermes

Objetivo: conectar el agente con la aplicación.

Tareas:

1. Instalar y configurar Hermes.
2. Configurar Claude Haiku 5.5.
3. Configurar credenciales mediante variables seguras.
4. Conectar Hermes con el backend.
5. Crear adaptador de comunicación.
6. Implementar envío de mensajes.
7. Implementar recepción de respuestas.
8. Implementar gestión de sesiones.
9. Implementar eventos de actividad.
10. Implementar errores y reconexión.
11. Crear primera Skill de Drakter.
12. Crear pruebas de conversación.

Criterio de finalización:

Se puede conversar desde la GUI y recibir respuestas generadas por Hermes.

## Fase 3. Identidad y personalidad

Objetivo: establecer el comportamiento de Drakter.

Tareas:

1. Crear SOUL.md.
2. Crear PERSONALITY.md.
3. Crear BEHAVIOR.md.
4. Crear COMMUNICATION.md.
5. Crear EMOTIONAL_STYLE.md.
6. Crear VALUES.md.
7. Crear USER.md.
8. Crear ENVIRONMENT.md.
9. Crear PREFERENCES.md.
10. Crear CURRENT_CONTEXT.md.
11. Crear CAPABILITIES.md.
12. Crear WORKSPACE_GUIDE.md.
13. Crear TOOL_GUIDE.md.
14. Crear SYSTEM_GUIDE.md.
15. Configurar carga de archivos.
16. Definir prioridad de instrucciones.
17. Crear pruebas de consistencia.

Criterio de finalización:

Drakter mantiene su identidad y comportamiento entre sesiones.

## Fase 4. Personaje animado

Objetivo: implementar la presencia visual.

Tareas:

1. Diseñar personaje.
2. Crear recursos gráficos.
3. Crear proyecto Rive.
4. Diseñar ojos.
5. Diseñar boca.
6. Crear estados funcionales.
7. Crear expresiones.
8. Crear transiciones.
9. Crear integración Rive-React.
10. Crear receptor de eventos.
11. Sincronizar estados con Hermes.
12. Implementar animación de boca.
13. Crear sistema de expresiones contextuales.
14. Crear pruebas de animación.

Criterio de finalización:

El personaje cambia de estado de forma coherente con las acciones del agente.

## Fase 5. Base de datos y Workspace

Objetivo: crear la estructura de información.

Tareas:

1. Diseñar esquema SQLite.
2. Crear migraciones.
3. Crear entidades.
4. Crear repositorios.
5. Crear servicios.
6. Crear validaciones.
7. Crear relaciones.
8. Crear integridad referencial.
9. Crear sistema de etiquetas.
10. Crear registro de cambios.
11. Crear pruebas de datos.
12. Crear API de Workspace.

Criterio de finalización:

Todos los módulos comparten una estructura de datos coherente.

## Fase 6. Tareas y proyectos

Objetivo: implementar el núcleo de productividad.

Tareas:

1. Crear interfaz de tareas.
2. Crear listado.
3. Crear filtros.
4. Crear prioridades.
5. Crear estados.
6. Crear subtareas.
7. Crear jerarquía de subtareas.
8. Crear dependencias.
9. Crear interfaz de proyectos.
10. Asociar tareas a proyectos.
11. Crear indicadores de progreso.
12. Crear historial.
13. Crear herramientas Hermes.
14. Crear pruebas completas.

Criterio de finalización:

Se pueden gestionar tareas y proyectos tanto desde la GUI como mediante Drakter.

## Fase 7. Hábitos, calendario y asignaturas

Objetivo: implementar planificación personal.

Tareas:

1. Crear módulo de hábitos.
2. Crear frecuencias.
3. Crear registros de cumplimiento.
4. Crear historial.
5. Crear estadísticas.
6. Crear módulo de calendario.
7. Crear vistas diaria, semanal y mensual.
8. Crear eventos.
9. Crear bloques de tiempo.
10. Detectar solapamientos.
11. Crear asignaturas.
12. Crear horarios recurrentes.
13. Asociar recursos y tareas.
14. Crear herramientas Hermes.
15. Crear pruebas de recurrencia y fechas.

Criterio de finalización:

Drakter puede consultar y gestionar la planificación personal completa.

## Fase 8. Almacén e indexación

Objetivo: permitir que Drakter localice y consulte recursos.

Tareas:

1. Crear catálogo.
2. Crear entidades Resource.
3. Crear explorador de carpetas.
4. Crear registro de rutas.
5. Crear metadatos.
6. Crear descripciones opcionales.
7. Crear etiquetas.
8. Configurar SQLite FTS5.
9. Implementar indexación.
10. Implementar actualización de índices.
11. Implementar detección de archivos ausentes.
12. Implementar lectores de documentos.
13. Implementar lectura bajo demanda.
14. Implementar búsqueda de enlaces.
15. Implementar límites para comprimidos.
16. Implementar permisos.
17. Crear herramientas Hermes.
18. Crear pruebas con distintos formatos.

Criterio de finalización:

Drakter puede localizar recursos, identificar su tipo y leerlos bajo demanda.

## Fase 9. Relaciones avanzadas

Objetivo: conseguir que todo el Workspace funcione como un sistema conectado.

Tareas:

1. Implementar tabla de relaciones.
2. Definir tipos de relación.
3. Crear validación de relaciones.
4. Crear relaciones bidireccionales cuando proceda.
5. Crear relaciones jerárquicas.
6. Crear relaciones entre tareas y proyectos.
7. Crear relaciones con asignaturas.
8. Crear relaciones con recursos.
9. Crear relaciones con eventos.
10. Crear relaciones con bloques de tiempo.
11. Crear consulta de elementos relacionados.
12. Crear visualización de relaciones.
13. Crear herramientas Hermes.
14. Crear pruebas de integridad.

Criterio de finalización:

Cualquier elemento puede consultar sus relaciones permitidas y Drakter puede crearlas y gestionarlas.

## Fase 10. Memoria persistente

Objetivo: incorporar memoria avanzada sin cargarla completa en el contexto.

Sin pipeline propio y sin recuerdos en el repositorio (véase §11). Lo que OpenViking no cubra se anota con ⚠️.

Tareas:

1. Definir interfaces de memoria.
2. Crear Memory Adapter.
3. Configurar OpenViking como proveedor de Hermes.
4. Configurar capas L0/L1/L2.
5. Elegir embedding multilingüe.
6. Configurar y comprobar la extracción en OpenViking.
7. Configurar y comprobar la clasificación de recuerdos en OpenViking.
8. Configurar y comprobar la deduplicación en OpenViking.
9. Configurar y comprobar la resolución de contradicciones en OpenViking.
10. Implementar recuperación selectiva.
11. Implementar límites de contexto.
12. Memoria de trabajo: sesión de Hermes.
13. Memoria episódica: OpenViking (`events`, `cases`).
14. Memoria semántica: OpenViking y `USER.md` nativo.
15. Memoria procedimental: Skills de Hermes y OpenViking (`patterns`).
16. Crear registros de recuperación.
17. Crear pruebas de persistencia.
18. Documentar copias de seguridad.

Criterio de finalización:

Drakter recuerda información relevante entre sesiones y recupera únicamente lo necesario.

## Fase 11. Skills y herramientas

Objetivo: conectar todas las capacidades con Hermes. Se ejecuta antes que la Fase 10 (memoria); las herramientas ya existen, construidas con su módulo, y aquí se integran las Skills.

Tareas:

1. Crear estructura de Skills.
2. Crear Skill de tareas.
3. Crear Skill de proyectos.
4. Crear Skill de hábitos.
5. Crear Skill de calendario.
6. Crear Skill de asignaturas.
7. Crear Skill de almacén.
8. Crear Skill de relaciones.
9. Crear Skill de memoria (se hace en el paso 15, junto con la memoria).
10. Crear Skill de configuración.
11. Definir parámetros.
12. Revisar permisos (ya definidos en el backend base).
13. Revisar confirmaciones (ya implementadas antes de la primera herramienta destructiva).
14. Definir errores.
15. Comprobar la selección de herramientas con el modelo.

Criterio de finalización:

Drakter puede operar todos los módulos mediante lenguaje natural.

## Fase 12. Voz

Objetivo: permitir conversación oral local.

Tareas:

1. Configurar openWakeWord.
2. Configurar palabra de activación.
3. Configurar Silero VAD.
4. Integrar Faster-Whisper.
5. Probar modelo small.
6. Medir latencia.
7. Probar medium si procede.
8. Integrar Kokoro.
9. Integrar Piper.
10. Crear Voice Manager.
11. Crear Voice Personality Engine.
12. Implementar reproducción.
13. Implementar interrupciones.
14. Sincronizar boca y audio.
15. Implementar estados de escucha.
16. Implementar errores de audio.
17. Crear pruebas en hardware real.

Criterio de finalización:

Se puede activar Drakter, hablar, recibir transcripción, obtener una respuesta y escucharla.

## Fase 13. Automejora controlada

Objetivo: permitir que Drakter proponga mejoras.

Tareas:

1. Crear registro de feedback.
2. Crear clasificación de problemas.
3. Crear propuestas.
4. Crear evaluaciones.
5. Crear entorno de pruebas.
6. Crear flujo de aprobación.
7. Integrar Git.
8. Crear historial de cambios.
9. Crear informes.
10. Impedir cambios no autorizados.
11. Crear pruebas de seguridad.

Criterio de finalización:

Drakter puede identificar y proponer mejoras, pero no modificar producción sin autorización.

## Fase 14. Seguridad y optimización

Objetivo: preparar una versión estable.

Tareas:

1. Revisar permisos.
2. Revisar rutas de archivos.
3. Revisar secretos.
4. Revisar validaciones.
5. Revisar operaciones destructivas.
6. Revisar registros.
7. Implementar copias de seguridad.
8. Implementar restauración.
9. Medir consumo de RAM.
10. Medir CPU.
11. Medir uso de CPU y RAM bajo carga de voz (sin VRAM dedicada).
12. Medir latencia de voz.
13. Optimizar consultas.
14. Optimizar recuperación de memoria.
15. Probar desconexiones.
16. Probar recuperación.
17. Probar actualización.
18. Crear instalador.
19. Crear documentación de instalación.
20. Crear versión estable.

Criterio de finalización:

La aplicación puede utilizarse de forma continuada, recuperarse de fallos y conservar sus datos.

## Fase 15. Ampliaciones futuras

No son requisitos para la primera versión:

- LiveKit Agents.
- Streaming de voz avanzado.
- Soporte multimodal ampliado.
- Sincronización entre dispositivos.
- Integración con Home Assistant.
- Control de dispositivos externos.
- Panel NOC.
- Integración con servicios externos.
- PostgreSQL.
- Aplicación móvil complementaria.
- Automatizaciones avanzadas.

# PARTE XIV. FLUJO COMPLETO DEL SISTEMA

## 28. Flujo de una conversación de texto

1. El usuario escribe en la GUI.
2. React envía el mensaje al backend.
3. FastAPI identifica la sesión.
4. El backend entrega a Hermes el mensaje y el contexto de sesión.
5. Hermes corre como proceso aparte, supervisado por FastAPI: un runner propio sobre `AIAgent`, sin gateway.
6. La recuperación de memoria ocurre **dentro de Hermes** (memoria nativa y herramientas `viking_*` de OpenViking), no antes de él.
7. Claude Haiku 5.5 procesa la solicitud.
8. Hermes decide si necesita herramientas.
9. Si no necesita herramientas, genera respuesta.
10. Si necesita herramientas, llama a la herramienta correspondiente, que el backend sirve por MCP en loopback (servidor delgado, sin lógica de negocio, que usa los mismos servicios que la API). Hermes es solo cliente, con lista de permitidos.
11. FastAPI valida permisos y parámetros.
12. El servicio correspondiente ejecuta la operación. Si es destructiva, crea una confirmación pendiente que solo la GUI resuelve.
13. SQLite guarda los cambios.
14. Se genera un evento.
15. WebSocket informa a la GUI.
16. Hermes recibe el resultado.
17. El agente prepara la respuesta.
18. La GUI muestra la respuesta.
19. Se registra la interacción (auditoría).
20. El sistema de memoria evalúa si existe información que conservar.

El modelo y Hermes se tratan como no confiables: la frontera real es el backend (decisión "Puente Hermes-backend y flujo de una petición").

## 29. Flujo de una operación sobre el Workspace

Ejemplo: crear una tarea relacionada con un proyecto, una asignatura y un documento.

1. El usuario formula la petición.
2. Hermes interpreta los elementos.
3. Consulta si existen los elementos mencionados.
4. Solicita aclaración si existe ambigüedad.
5. Construye la operación.
6. La herramienta valida los parámetros.
7. El backend crea la tarea.
8. Se crean las relaciones.
9. Se comprueba la integridad.
10. Se guarda la operación.
11. Se emite un evento.
12. La interfaz se actualiza.
13. Hermes comunica el resultado.

## 30. Flujo de una conversación por voz

1. openWakeWord detecta la activación.
2. Silero VAD detecta la voz.
3. Se captura audio.
4. Faster-Whisper transcribe.
5. El texto se entrega al backend.
6. Se entrega el contexto de sesión a Hermes.
7. Hermes procesa la petición y recupera la memoria pertinente.
8. Se ejecutan herramientas si son necesarias.
9. Se genera una respuesta.
10. Voice Personality Engine selecciona parámetros.
11. Kokoro sintetiza el audio.
12. La GUI reproduce la voz.
13. Rive anima la boca.
14. La GUI muestra el texto.
15. Se registra la interacción.

## 31. Flujo de memoria

1. Se produce una conversación o evento.
2. El sistema detecta información potencialmente persistente.
3. OpenViking extrae candidatos al confirmar la sesión.
4. Se clasifican.
5. Se comprueba si ya existen.
6. Se detectan contradicciones.
7. Se valida su utilidad.
8. Se almacena en el sistema correspondiente.
9. Se actualiza la organización contextual.
10. Se registra el cambio.

En la siguiente conversación, Hermes recuperará, con las herramientas de OpenViking, únicamente los recuerdos pertinentes.

# PARTE XV. PRUEBAS Y CRITERIOS DE CALIDAD

## 32. Pruebas obligatorias

Esta parte se lee según `CLAUDE.md` §4: criterio de "hecho" es que funciona como se espera y se ve bien, con una comprobación rápida y sin suites exhaustivas. Las listas siguientes son áreas a comprobar, no tests a escribir. Test puntual solo para: rutas y permisos del almacén, confirmaciones de acciones destructivas, migraciones y copia/restauración, y que la memoria recuperada no sobrescriba reglas de seguridad.

### Interfaz

- Apertura y cierre.
- Navegación.
- Persistencia de configuración.
- Actualización en tiempo real.
- Gestión de errores.
- Adaptación de ventanas.

### Backend

- Validación.
- API.
- WebSocket.
- Base de datos.
- Migraciones.
- Errores.
- Permisos.

### Agente

- Conversación.
- Selección de herramientas.
- Parámetros.
- Uso de memoria.
- Respuestas erróneas.
- Recuperación de errores.

### Workspace

- Creación.
- Edición.
- Eliminación.
- Relaciones.
- Integridad.
- Búsqueda.
- Historial.

### Memoria

- Persistencia.
- Recuperación.
- Duplicados.
- Contradicciones.
- Contexto excesivo.
- Información obsoleta.

### Voz

- Activación.
- Reconocimiento.
- Silencios.
- Ruido.
- Síntesis.
- Interrupción.
- Sincronización labial.

### Seguridad

- Permisos.
- Acceso a archivos.
- Secretos.
- Confirmaciones.
- Auditoría.
- Restauración.

# PARTE XVI. CHECKLISTS GENERALES DE IMPLEMENTACIÓN

Las siguientes listas son el control de trabajo del proyecto. Son históricas: la lista viva es `docs/IMPLEMENTATION_STATUS.md`. Una tarea se marca cuando está implementada y funciona como se espera (`CLAUDE.md` §4: "funciona y se ve bien"), sin exigir suites de tests.

## Checklist 0. Arquitectura y preparación

- [ ] Crear repositorio Drakter.
- [ ] Configurar Git.
- [ ] Crear estructura de carpetas.
- [ ] Crear README.
- [ ] Crear CHANGELOG.
- [ ] Documentar arquitectura.
- [ ] Documentar decisiones técnicas.
- [ ] Definir convenciones.
- [ ] Definir modelos de datos.
- [ ] Definir API.
- [ ] Definir eventos.
- [ ] Definir permisos.
- [ ] Definir configuración.
- [ ] Preparar entorno de desarrollo.

## Checklist 1. Aplicación de escritorio

- [ ] Configurar Electron.
- [ ] Configurar React.
- [ ] Configurar TypeScript.
- [ ] Configurar Tailwind.
- [ ] Configurar shadcn/ui.
- [ ] Crear ventana principal.
- [ ] Crear navegación lateral.
- [ ] Crear área central.
- [ ] Crear panel contextual.
- [ ] Crear notificaciones.
- [ ] Crear configuración.
- [ ] Crear gestión de errores.
- [ ] Configurar empaquetado.

## Checklist 2. Backend

- [ ] Crear FastAPI.
- [ ] Configurar SQLite.
- [ ] Configurar migraciones.
- [ ] Crear API REST.
- [ ] Crear WebSocket.
- [ ] Crear servicios.
- [ ] Crear repositorios.
- [ ] Crear esquemas.
- [ ] Crear validaciones.
- [ ] Crear logs.
- [ ] Crear gestión de errores.
- [ ] Crear sistema de permisos.

## Checklist 3. Hermes

- [ ] Instalar Hermes.
- [ ] Configurar Claude Haiku 5.5.
- [ ] Configurar credenciales.
- [ ] Conectar Hermes con backend.
- [ ] Crear adaptador.
- [ ] Crear sesiones.
- [ ] Crear envío de mensajes.
- [ ] Crear recepción de respuestas.
- [ ] Crear eventos de agente.
- [ ] Crear gestión de desconexiones.
- [ ] Crear primera Skill.
- [ ] Probar conversación completa.

## Checklist 4. Personalidad y contexto

- [ ] Crear SOUL.md.
- [ ] Crear PERSONALITY.md.
- [ ] Crear BEHAVIOR.md.
- [ ] Crear COMMUNICATION.md.
- [ ] Crear EMOTIONAL_STYLE.md.
- [ ] Crear VALUES.md.
- [ ] Crear USER.md.
- [ ] Crear ENVIRONMENT.md.
- [ ] Crear PREFERENCES.md.
- [ ] Crear CURRENT_CONTEXT.md.
- [ ] Crear CAPABILITIES.md.
- [ ] Crear WORKSPACE_GUIDE.md.
- [ ] Crear TOOL_GUIDE.md.
- [ ] Crear SYSTEM_GUIDE.md.
- [ ] Configurar carga de contexto.
- [ ] Configurar prioridades.
- [ ] Probar consistencia de personalidad.

## Checklist 5. Personaje

- [ ] Diseñar identidad visual.
- [ ] Diseñar ojos.
- [ ] Diseñar boca.
- [ ] Diseñar expresiones.
- [ ] Crear proyecto Rive.
- [ ] Crear estado idle.
- [ ] Crear estado listening.
- [ ] Crear estado thinking.
- [ ] Crear estado speaking.
- [ ] Crear estado executing.
- [ ] Crear estado success.
- [ ] Crear estado error.
- [ ] Crear estado interrupted.
- [ ] Crear estado offline.
- [ ] Crear transiciones.
- [ ] Integrar Rive con React.
- [ ] Crear sistema de eventos visuales.
- [ ] Implementar sincronización labial.
- [ ] Probar animaciones.

## Checklist 6. Base de datos y relaciones

- [ ] Crear esquema SQLite.
- [ ] Crear tabla de tareas.
- [ ] Crear tabla de proyectos.
- [ ] Crear tabla de hábitos.
- [ ] Crear tabla de registros de hábitos.
- [ ] Crear tabla de eventos.
- [ ] Crear tabla de bloques de tiempo.
- [ ] Crear tabla de asignaturas.
- [ ] Crear tabla de sesiones de clase.
- [ ] Crear tabla de recursos.
- [ ] Crear tabla de carpetas.
- [ ] Crear tabla de etiquetas.
- [ ] Crear tabla de relaciones.
- [ ] Crear tabla de auditoría.
- [ ] Crear identificadores UUID.
- [ ] Crear integridad referencial.
- [ ] Crear migraciones.
- [ ] Probar persistencia.

## Checklist 7. Tareas y proyectos

- [ ] Crear interfaz de tareas.
- [ ] Crear tareas.
- [ ] Editar tareas.
- [ ] Eliminar tareas.
- [ ] Completar tareas.
- [ ] Reabrir tareas.
- [ ] Crear subtareas.
- [ ] Crear subtareas anidadas.
- [ ] Crear estados.
- [ ] Crear prioridades.
- [ ] Crear fechas límite.
- [ ] Crear etiquetas.
- [ ] Crear dependencias.
- [ ] Crear interfaz de proyectos.
- [ ] Crear proyectos.
- [ ] Editar proyectos.
- [ ] Archivar proyectos.
- [ ] Asociar tareas a proyectos.
- [ ] Mostrar progreso.
- [ ] Crear historial.
- [ ] Crear herramientas Hermes.
- [ ] Probar operaciones desde GUI.
- [ ] Probar operaciones desde Drakter.

## Checklist 8. Hábitos

- [ ] Crear interfaz.
- [ ] Crear hábitos.
- [ ] Editar hábitos.
- [ ] Definir frecuencia.
- [ ] Definir días.
- [ ] Definir recordatorios.
- [ ] Registrar cumplimiento.
- [ ] Consultar historial.
- [ ] Calcular estadísticas.
- [ ] Asociar hábitos con objetivos.
- [ ] Crear herramientas Hermes.
- [ ] Probar persistencia.

## Checklist 9. Calendario y asignaturas

- [ ] Crear interfaz de calendario.
- [ ] Crear vista diaria.
- [ ] Crear vista semanal.
- [ ] Crear vista mensual.
- [ ] Crear eventos.
- [ ] Editar eventos.
- [ ] Eliminar eventos.
- [ ] Crear bloques de tiempo.
- [ ] Asociar bloques a tareas.
- [ ] Detectar solapamientos.
- [ ] Gestionar zonas horarias.
- [ ] Crear asignaturas.
- [ ] Crear horarios recurrentes.
- [ ] Crear sesiones de clase.
- [ ] Asociar recursos.
- [ ] Asociar tareas.
- [ ] Crear herramientas Hermes.
- [ ] Probar recurrencias y fechas.

## Checklist 10. Almacén e indexación

- [ ] Crear interfaz del almacén.
- [ ] Crear catálogo de recursos.
- [ ] Crear carpetas.
- [ ] Crear metadatos.
- [ ] Crear descripciones opcionales.
- [ ] Crear etiquetas.
- [ ] Crear registro de rutas.
- [ ] Crear índice FTS5.
- [ ] Indexar nombres.
- [ ] Indexar tipos.
- [ ] Indexar descripciones.
- [ ] Implementar búsqueda.
- [ ] Implementar actualización del índice.
- [ ] Detectar archivos ausentes.
- [ ] Implementar lectura bajo demanda.
- [ ] Implementar lectores PDF.
- [ ] Implementar lectores de texto.
- [ ] Implementar lectores de imágenes mediante metadatos.
- [ ] Implementar lectura de enlaces.
- [ ] Implementar límites de comprimidos.
- [ ] Implementar permisos.
- [ ] Crear herramientas Hermes.
- [ ] Probar formatos y errores.

## Checklist 11. Relaciones avanzadas

- [ ] Crear servicio de relaciones.
- [ ] Crear tipos de relación.
- [ ] Crear validaciones.
- [ ] Crear relaciones entre tareas y proyectos.
- [ ] Crear relaciones entre tareas y asignaturas.
- [ ] Crear relaciones entre tareas y recursos.
- [ ] Crear relaciones entre tareas y calendario.
- [ ] Crear relaciones entre proyectos y recursos.
- [ ] Crear relaciones entre asignaturas y recursos.
- [ ] Crear consulta inversa.
- [ ] Crear consulta de elementos relacionados.
- [ ] Crear visualización de relaciones.
- [ ] Crear herramientas Hermes.
- [ ] Probar integridad y eliminación.

## Checklist 12. Memoria

- [ ] Definir cuatro capas de memoria.
- [ ] Crear estructura de archivos (solo configuración e integración en `memory/`; sin recuerdos).
- [ ] Crear Memory Adapter.
- [ ] Configurar OpenViking como proveedor de Hermes.
- [ ] Configurar capas L0/L1/L2.
- [ ] Elegir embedding multilingüe.
- [ ] Integrar ByteRover para el repositorio (utilidad opcional de desarrollo, fuera de la memoria del producto).
- [ ] Crear extracción de recuerdos.
- [ ] Crear clasificación.
- [ ] Crear deduplicación.
- [ ] Crear detección de contradicciones.
- [ ] Crear memoria de trabajo.
- [ ] Crear memoria episódica.
- [ ] Crear memoria semántica.
- [ ] Crear memoria procedimental.
- [ ] Crear recuperación selectiva.
- [ ] Crear límites de contexto.
- [ ] Crear registros de memoria.
- [ ] Probar persistencia.
- [ ] Probar recuperación.
- [ ] Probar recuerdos contradictorios.
- [ ] Probar información obsoleta.

## Checklist 13. Skills y herramientas

- [ ] Crear estructura de Skills.
- [ ] Crear Skill de tareas.
- [ ] Crear Skill de proyectos.
- [ ] Crear Skill de hábitos.
- [ ] Crear Skill de calendario.
- [ ] Crear Skill de asignaturas.
- [ ] Crear Skill de almacén.
- [ ] Crear Skill de relaciones.
- [ ] Crear Skill de memoria.
- [ ] Crear Skill de configuración.
- [ ] Definir parámetros.
- [ ] Definir permisos.
- [ ] Definir confirmaciones.
- [ ] Definir errores.
- [ ] Probar selección de herramientas.
- [ ] Probar operaciones encadenadas.

## Checklist 14. Voz

- [ ] Instalar openWakeWord.
- [ ] Configurar palabra de activación.
- [ ] Instalar Silero VAD.
- [ ] Configurar detección de voz.
- [ ] Instalar Faster-Whisper.
- [ ] Probar modelo small.
- [ ] Medir latencia.
- [ ] Evaluar modelo medium.
- [ ] Instalar Kokoro.
- [ ] Instalar Piper.
- [ ] Crear Voice Manager.
- [ ] Crear Voice Personality Engine.
- [ ] Crear reproducción de audio.
- [ ] Crear interrupciones.
- [ ] Crear cancelación de audio.
- [ ] Sincronizar boca.
- [ ] Crear gestión de errores.
- [ ] Probar conversación por voz completa.

## Checklist 15. Automejora

- [ ] Crear registro de feedback.
- [ ] Crear clasificación de incidencias.
- [ ] Crear propuestas.
- [ ] Crear evaluaciones.
- [ ] Crear entorno de pruebas.
- [ ] Crear flujo de aprobación.
- [ ] Integrar Git.
- [ ] Crear historial de cambios.
- [ ] Crear informes.
- [ ] Impedir cambios no autorizados.
- [ ] Probar recuperación de cambios.

## Checklist 16. Seguridad y fiabilidad

- [ ] Crear permisos por módulo.
- [ ] Crear permisos por operación.
- [ ] Crear confirmaciones.
- [ ] Proteger credenciales.
- [ ] Validar rutas.
- [ ] Limitar acceso a archivos.
- [ ] Proteger operaciones destructivas.
- [ ] Crear auditoría.
- [ ] Crear copias de seguridad.
- [ ] Probar restauración.
- [ ] Probar desconexiones.
- [ ] Probar recuperación del backend.
- [ ] Probar recuperación de Hermes.
- [ ] Probar errores de memoria.
- [ ] Revisar datos sensibles.

## Checklist 17. Optimización y lanzamiento

- [ ] Medir consumo de RAM.
- [ ] Medir CPU.
- [ ] Medir uso de CPU y RAM (sin VRAM dedicada).
- [ ] Medir latencia de STT.
- [ ] Medir latencia de TTS.
- [ ] Medir latencia de Hermes.
- [ ] Optimizar consultas SQLite.
- [ ] Optimizar FTS5.
- [ ] Optimizar recuperación de memoria.
- [ ] Optimizar carga de interfaz.
- [ ] Crear instalador.
- [ ] Crear actualización de aplicación.
- [ ] Crear documentación de instalación.
- [ ] Crear documentación de uso.
- [ ] Crear versión estable.
- [ ] Crear copia de seguridad inicial.
- [ ] Realizar pruebas de aceptación.

## Checklist 18. Ampliaciones futuras

- [ ] Evaluar LiveKit Agents.
- [ ] Implementar streaming de voz avanzado.
- [ ] Evaluar PostgreSQL.
- [ ] Evaluar sincronización entre dispositivos.
- [ ] Evaluar aplicación móvil.
- [ ] Integrar Home Assistant.
- [ ] Incorporar control de dispositivos.
- [ ] Crear monitorización avanzada.
- [ ] Ampliar capacidades multimodales.
- [ ] Ampliar automatizaciones.

# PARTE XVII. CRITERIO DE FINALIZACIÓN DEL PROYECTO

Drakter se considerará funcionalmente completo en su primera versión cuando cumpla todos estos requisitos:

1. La aplicación de escritorio se inicia correctamente.
2. Hermes está conectado y puede conversar.
3. La personalidad se mantiene entre sesiones.
4. El personaje representa los estados del agente.
5. La voz permite escuchar y hablar localmente.
6. Las tareas y proyectos se gestionan desde GUI y agente.
7. Los hábitos se registran y consultan.
8. El calendario gestiona eventos y bloques de tiempo.
9. Las asignaturas y horarios están integrados.
10. El almacén indexa recursos sin cargar todos sus contenidos.
11. Los documentos se leen bajo demanda.
12. Los elementos pueden relacionarse entre sí.
13. Hermes puede consultar y modificar el Workspace.
14. La memoria persiste y se recupera selectivamente.
15. Las acciones importantes tienen permisos y confirmaciones.
16. Las operaciones quedan registradas.
17. Los datos pueden respaldarse y restaurarse.
18. El sistema puede recuperarse de errores habituales.
19. La aplicación tiene documentación de instalación y uso.
20. Existe una versión estable y reproducible.

# ORDEN REAL DE DESARROLLO

El orden de implementación será:

1. Arquitectura y repositorio.
2. Electron + React.
3. FastAPI + SQLite.
4. Comunicación GUI-backend.
5. Hermes + Claude Haiku 5.5.
6. Personalidad y contexto.
7. Personaje Rive.
8. Modelo de datos.
9. Tareas y proyectos.
10. Hábitos.
11. Calendario y asignaturas.
12. Almacén e indexación.
13. Relaciones avanzadas.
14. Integración de herramientas y Skills.
15. Memoria avanzada.
16. Voz local.
17. Automejora controlada.
18. Seguridad.
19. Optimización.
20. Empaquetado y lanzamiento.

La regla durante todo el desarrollo será que cada fase debe terminar funcionando y viéndose bien (`CLAUDE.md` §4: comprobación rápida, sin suites) antes de empezar a depender de ella en la siguiente.

Este orden de 20 pasos es el de la tabla de `DECISIONS.md`: Skills y herramientas (paso 14) va antes que memoria (paso 15); cada herramienta se construye con su módulo; y permisos, confirmación pendiente y auditoría existen antes de la primera herramienta.

**Resultado esperado:** Drakter será una aplicación de escritorio propia, con un agente Hermes como motor, una identidad y personalidad persistentes, un personaje animado, conversación por voz, memoria externa organizada y un Workspace personal cuyos módulos estarán conectados mediante un sistema común de datos y relaciones.
