# DRAKTER --- ROADMAP DE IMPLEMENTACIÓN PARA CLAUDE CODE

> **Documento:** `ROADMAP.md`\
> **Proyecto:** Drakter\
> **Versión del roadmap:** 1.0\
> **Fecha:** 2026-11-04\
> **Objetivo:** servir como hoja de ruta ejecutable para Claude Code.\
> **Estado inicial:** proyecto por iniciar.
>
> Este documento define qué construir, en qué orden, cómo validar cada
> fase y qué condiciones deben cumplirse antes de avanzar. No presupone
> que las tecnologías estén instaladas ni que las integraciones externas
> funcionen hasta comprobarlo.
>
> **Prevalencia:** este documento es subordinado. Manda la entrada más
> reciente de `docs/DECISIONS.md` (véase "Jerarquía de documentos y
> numeración única de fases"), luego `CLAUDE.md` y `docs/MASTER_PLAN.md`.
> Los documentos viven en `docs/`. Las casillas de este roadmap son
> históricas: la lista viva es `docs/IMPLEMENTATION_STATUS.md`. Sus fases
> equivalen a los pasos de la tabla de `DECISIONS.md`: su Fase 15 son
> Skills (obligatoria, paso 14) y las ampliaciones son su Fase 21 (fuera
> de alcance). Donde haya choque con `DECISIONS.md`, ya se ha corregido
> aquí o se remite a la decisión. Esquema de datos, catálogo de
> herramientas y eventos WebSocket: véase "Contratos de datos que
> resuelve drakter/contratos".

------------------------------------------------------------------------

## 0. Instrucciones para Claude Code

Actúa como ingeniero principal de software de Drakter. Tu trabajo es
implementar el proyecto de forma incremental, mantenible, segura y
verificable.

### Reglas obligatorias de trabajo

1.  **Inspecciona antes de modificar.** Antes de crear archivos, examina
    el repositorio, su estructura, dependencias, estado de Git y
    documentación existente.
2.  **No destruyas trabajo existente.** No sobrescribas ni elimines
    archivos o cambios del usuario sin comprenderlos y obtener
    autorización cuando exista riesgo de pérdida.
3.  **Trabaja por fases.** Implementa únicamente la fase activa y sus
    dependencias. No intentes construir todo el sistema de una vez.
4.  **Planifica tareas grandes.** Divide cada fase en tareas pequeñas,
    con resultados verificables.
5.  **No inventes APIs.** Antes de integrar Hermes, OpenViking,
    Kokoro, Faster-Whisper, Rive u otros proyectos externos, comprueba sus versiones, documentación y APIs disponibles.
6.  **Comprueba compatibilidad.** Verifica versiones de Python, Node.js,
    Electron, sistema operativo, modelos y dependencias antes de
    fijarlas.
7.  **Evita dependencias innecesarias.** Elige la solución más sencilla
    que cumpla los requisitos.
8.  **Mantén tipado y validación.** Usa TypeScript estricto en frontend
    y esquemas validados en backend.
9.  **Comprueba cada cambio.** Ejecuta lint, comprobación de tipos y build
    aplicables, y una comprobación rápida de que funciona y se ve bien,
    antes de declarar una tarea terminada. Sin suites de tests ni tests
    unitarios por defecto (`CLAUDE.md` §4); solo las excepciones allí
    listadas (rutas y permisos del almacén, confirmaciones destructivas,
    migraciones y copias, memoria frente a reglas de seguridad). Las
    tareas "Crear pruebas..." de las fases se leen con ese criterio.
10. **No marques tareas sin evidencia.** Una casilla solo se marca
    cuando el código existe y las comprobaciones correspondientes han
    pasado.
11. **Actualiza documentación.** Mantén `docs/IMPLEMENTATION_STATUS.md`,
    `docs/DECISIONS.md` y el README alineados con el estado real.
12. **Registra decisiones.** Si una tecnología no es viable, documenta
    el problema, alternativas, decisión y consecuencias antes de
    sustituirla.
13. **No hagas cambios autónomos de alto impacto.** No modifiques
    permisos, seguridad, secretos, datos persistentes ni infraestructura
    crítica sin autorización.
14. **No ejecutes comandos destructivos** ni borres datos, directorios,
    bases de datos o volúmenes sin confirmación explícita.
15. **No expongas secretos.** Nunca imprimas claves API, tokens,
    contraseñas o contenidos sensibles en logs, tests, documentación o
    respuestas.
16. **No simules integraciones.** Los mocks se identificarán claramente
    como mocks y nunca se presentarán como integraciones reales.
17. **No implementes funciones vacías como si estuvieran terminadas.**
    Usa errores explícitos o estados `not implemented` cuando
    corresponda.
18. **Mantén el proyecto ejecutable.** Cada fase debe dejar el
    repositorio en un estado coherente y arrancable.

### Ciclo de trabajo para cada tarea

1.  Leer este roadmap y `IMPLEMENTATION_STATUS.md`.
2.  Inspeccionar el código afectado.
3.  Identificar dependencias y riesgos.
4.  Proponer un plan breve.
5.  Implementar el cambio mínimo completo.
6.  Añadir pruebas solo si aplica una excepción de `CLAUDE.md` §4.
7.  Ejecutar la comprobación rápida (lint, tipos, build, arranque).
8.  Revisar diff y posibles regresiones.
9.  Actualizar documentación y estado.
10. Informar de archivos modificados, comprobaciones ejecutadas,
    resultados y tareas pendientes.

### Política de avance

Según `CLAUDE.md` §3, avanza sin esperar aprobación en lo reversible y
paraleliza lo independiente. No avances a la siguiente fase si: - la
comprobación rápida falla; - el build no funciona; - hay errores de tipos o lint
relevantes; - existen decisiones arquitectónicas sin resolver que
bloquean la fase y alteran el objetivo del producto; - se ha introducido
una dependencia externa sin verificar; - la funcionalidad solo está
simulada. Las decisiones técnicas no se consultan: se eligen y se
registran en `docs/DECISIONS.md`.

Si falta información, inspecciona el repositorio y la documentación
oficial. Pregunta al usuario únicamente cuando sea una decisión de
producto, una autorización o una preferencia que no pueda deducirse con
seguridad.

------------------------------------------------------------------------

# 1. Visión del producto

Drakter será una aplicación de escritorio local-first que integra un
agente de IA con un Workspace personal.

No será solo un chat. Permitirá conversar por texto y voz, consultar
memoria persistente, ejecutar herramientas autorizadas y gestionar
información estructurada desde una única interfaz.

## 1.1. Subsistemas

### Drakter Desktop

Aplicación de escritorio propia, inspirada en patrones de interacción de
aplicaciones como Troko Desktop, ClickUp y Notion, sin copiar código,
recursos protegidos ni identidad visual ajena.

### Drakter Core

Capa de integración y coordinación del agente. Hermes será el motor de
agente principal. El backend de Drakter expondrá herramientas y
servicios internos.

### Drakter Workspace

Sistema de datos y productividad que incluirá: - Tareas y subtareas. -
Proyectos. - Hábitos y registros. - Calendario y bloques de tiempo. -
Asignaturas y horario. - Almacén de recursos. - Etiquetas. - Relaciones
entre elementos.

### Drakter Memory

Sistema de memoria persistente con recuperación selectiva, extracción de
recuerdos y organización contextual.

### Drakter Voice

Sistema local de activación, detección de voz, transcripción, síntesis y
sincronización con el personaje.

### Drakter Character

Personaje visual animado que representa estados operativos y expresiones
conversacionales.

### Drakter Improvement

Sistema de feedback y propuestas de mejora, siempre controlado y con
aprobación para cambios sensibles.

------------------------------------------------------------------------

# 2. Decisiones de arquitectura

Estas son las decisiones iniciales. Deben validarse durante la Fase 0
antes de considerarse definitivas. Las ya resueltas en `docs/DECISIONS.md`
(memoria, Python 3.12, puente Hermes-backend, datos fuera del repositorio)
prevalecen sobre esta tabla.

  -------------------------------------------------------------------------
  Área                    Selección inicial       Observaciones
  ----------------------- ----------------------- -------------------------
  Agente                  Hermes                  Comprobar instalación,
                                                  versión, API y mecanismos
                                                  reales de integración

  Modelo principal        Claude Haiku 5.5 vía    Modelo intercambiable
                          API                     mediante adaptador

  Escritorio              Electron                Aplicación
                                                  multiplataforma

  Frontend                React + TypeScript      TypeScript estricto

  UI                      Tailwind CSS +          Componentes accesibles y
                          shadcn/ui               reutilizables

  Animación               Rive                    Confirmar runtime y
                                                  licencias/condiciones de
                                                  uso

  Backend                 Python 3.12 + FastAPI   API local; Hermes y
                                                  OpenViking en entornos
                                                  propios (ver `DECISIONS`)

  Persistencia principal  SQLite                  Una fuente de verdad para
                                                  el Workspace

  Migraciones             Alembic o alternativa   Elegir tras validar el
                          compatible              ORM y esquema

  Búsqueda textual        SQLite FTS5             Índice reconstruible

  STT                     Faster-Whisper          Ejecución local; empezar
                                                  con CPU INT8

  VAD                     Silero VAD              Detectar segmentos de voz

  Wake word               openWakeWord            Activación local

  TTS principal           Kokoro                  Verificar idioma, voces y
                                                  control real de prosodia

  TTS de respaldo         Piper                   Verificar modelo de voz
                                                  español disponible

  Memoria nativa          Memoria de Hermes       MEMORY.md, USER.md y
                                                  sesiones

  Memoria contextual      OpenViking              Único proveedor externo;
                                                  capas L0/L1/L2; API
                                                  soportada

  Contexto de código      ByteRover (opcional)    Utilidad opcional de
                                                  desarrollo; fuera de la
                                                  memoria del producto

  Skills                  Hermes Skills           Verificar formato y
                                                  compatibilidad de versión

  Comunicación UI/backend REST + WebSocket        Eventos tipados

  Versionado              Git + GitHub            Ramas y commits pequeños
  -------------------------------------------------------------------------

## 2.1. Decisiones que deben cerrarse en Fase 0

-   Versión soportada de Python.
-   Versión LTS de Node.js.
-   Gestor de paquetes frontend.
-   ORM y sistema de migraciones.
-   Forma exacta de ejecutar Hermes como proceso o servicio.
-   Contrato de integración Hermes ↔ backend.
-   Estrategia de empaquetado de Python dentro de Electron.
-   Ubicación de datos de usuario por sistema operativo.
-   Estrategia de instalación y actualización.
-   Compatibilidad de Rive con Electron.
-   Despliegue de OpenViking.
-   Si las herramientas de memoria se ejecutan como servicios locales,
    librerías o procesos separados.

Resueltas en `docs/DECISIONS.md`: versión de Python (3.12 para el
backend; Hermes y OpenViking en entornos propios, sin compartir
entorno), forma de ejecutar Hermes y contrato Hermes ↔ backend (entrada
"Puente Hermes-backend y flujo de una petición": proceso aparte
supervisado por FastAPI, herramientas servidas por el backend vía MCP en
loopback, `AgentProvider` por encima) y ubicación de datos
(`DRAKTER_DATA_DIR`, fuera del repositorio).

No asumir que todas las herramientas elegidas se pueden combinar
directamente. La integración se hará mediante adaptadores propios y
contratos estables.

## 2.2. Principios

1.  Local-first: los datos del Workspace se almacenan localmente por
    defecto.
2.  Privacidad: solo se envía al proveedor de IA el contexto necesario
    para responder.
3.  Fuente única de verdad: SQLite será la fuente canónica de los datos
    del Workspace.
4.  Adaptadores: proveedores externos detrás de interfaces internas.
5.  Modularidad: frontend, backend, agente, voz y memoria separados.
6.  Recuperación selectiva: no cargar archivos o recuerdos completos por
    defecto.
7.  Seguridad: permisos mínimos, validación y auditoría.
8.  Observabilidad: logs útiles sin secretos.
9.  Reproducibilidad: versiones fijadas y pasos de instalación
    documentados.
10. Portabilidad: evitar dependencias innecesarias del sistema
    operativo.

------------------------------------------------------------------------

# 3. Arquitectura lógica

``` mermaid
flowchart TB
    U[Usuario] --> UI[Drakter Desktop<br/>Electron + React]
    UI <-->|REST + WebSocket| API[FastAPI Backend]

    API --> AUTH[Permisos y validación]
    API --> APP[Servicios de aplicación]
    APP --> DB[(SQLite<br/>Workspace)]
    APP --> IDX[(SQLite FTS5)]
    APP --> FILES[Almacén de archivos]

    API <--> CORE[Drakter Agent Adapter]
    CORE <--> H[Hermes]
    H <--> LLM[Claude Haiku 5.5<br/>API intercambiable]
    H <--> TOOLS[Drakter Tools vía MCP loopback / Skills]
    TOOLS --> APP

    H <--> NM[Memoria nativa de Hermes]
    H <--> OV[OpenViking]
    APP <--> MEM[Memory Adapter<br/>interfaz e ingesta]
    MEM <--> OV

    API <--> VOICE[Voice Manager]
    VOICE --> WW[openWakeWord]
    VOICE --> VAD[Silero VAD]
    VOICE --> STT[Faster-Whisper]
    VOICE --> TTS[Kokoro / Piper]

    API --> EVENTS[Event Bus]
    EVENTS --> UI
    UI --> RIVE[Character / Rive]
    VOICE --> RIVE

    DEV[Repositorio Git] <--> BR[ByteRover<br/>opcional, solo desarrollo]
```

El diagrama representa límites lógicos. No implica que todos los
componentes deban ejecutarse como procesos separados desde el primer
prototipo.

------------------------------------------------------------------------

# 4. Estructura objetivo del repositorio

La estructura se alcanzará gradualmente. No crear directorios vacíos
solo para que coincidan con el árbol.

``` text
Drakter/
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
│   ├── assets/
│   │   ├── icons/
│   │   └── rive/
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── integrations/
│   │   │   ├── hermes/
│   │   │   ├── memory/
│   │   │   └── voice/
│   │   ├── tools/
│   │   ├── permissions/
│   │   ├── events/
│   │   └── audit/
│   ├── migrations/
│   └── tests/
├── agent/
│   ├── identity/          # los 14 archivos de identidad (Fase 5)
│   ├── skills/
│   └── configuration/
├── memory/                # solo configuración e integración; nunca recuerdos
├── voice/
│   ├── wakeword/
│   ├── vad/
│   ├── stt/
│   ├── tts/
│   ├── personality/
│   ├── audio/
│   └── tests/
├── workspace/             # código del Workspace; sin datos (van en DRAKTER_DATA_DIR)
├── improvement/
│   ├── feedback/
│   ├── proposals/
│   ├── evaluations/
│   ├── experiments/
│   └── reports/
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── database/
│   ├── workflows/
│   ├── installation/
│   └── decisions/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
└── README.md
```

Los documentos de control viven en `docs/`: `MASTER_PLAN.md`,
`ROADMAP.md`, `IMPLEMENTATION_STATUS.md`, `DECISIONS.md` y
`RUN_STATE.md`. Los datos de ejecución (SQLite, almacén, índices,
exportaciones, copias, recuerdos) viven fuera del repositorio, en
`DRAKTER_DATA_DIR` (por defecto `user_data_dir("drakter")`). `agent/context/`
y `agent/knowledge/` no existen. La configuración no sensible puede
versionarse; la sensible, nunca (credenciales solo en
`~/.config/drakter/.env`).

------------------------------------------------------------------------

# 5. Contratos y reglas transversales

## 5.1. Identificadores

-   Usar UUID para entidades persistentes.
-   No usar títulos o nombres como identificadores.
-   Las referencias externas deben guardar proveedor, tipo e
    identificador externo.
-   Las relaciones deben referenciar entidades existentes.

## 5.2. Fechas

-   Guardar timestamps en UTC.
-   Conservar zona horaria IANA cuando sea relevante para eventos
    recurrentes.
-   Convertir a hora local solo en presentación.
-   Definir reglas para eventos sin hora, eventos recurrentes y cambios
    de horario estacional.

## 5.3. API

-   Prefijo `/api/v1`.
-   Esquemas de entrada y salida explícitos.
-   Errores con código estable, mensaje seguro y detalles de validación.
-   Paginación para listados.
-   Filtros y ordenación validados.
-   Operaciones destructivas con confirmación obligatoria; el undo es
    un mecanismo adicional cuando sea viable, nunca un sustituto.

## 5.4. Eventos WebSocket

Crear un contrato tipado y versionado. Eventos iniciales:

-   `agent.status_changed`
-   `agent.expression_changed`
-   `agent.message_delta`
-   `agent.message_completed`
-   `agent.tool_started`
-   `agent.tool_completed`
-   `agent.error`
-   `voice.listening_started`
-   `voice.transcription_partial`
-   `voice.transcription_completed`
-   `voice.playback_started`
-   `voice.playback_stopped`
-   `workspace.entity_created`
-   `workspace.entity_updated`
-   `workspace.entity_deleted`
-   `workspace.relationship_created`
-   `system.health_changed`

Los eventos deben incluir `event_id`, `timestamp`, `type`, `version` y
un `payload` validado.

Esta lista es histórica. El catálogo definitivo está en
`contracts/python/drakter_contracts/events.py` (entrada "Eventos
WebSocket resueltos en contracts/" de `docs/DECISIONS.md`).

## 5.5. Seguridad local

-   No exponer FastAPI a la red local por defecto.
-   Vincular el backend a loopback salvo configuración explícita.
-   Proteger endpoints locales con un mecanismo de sesión/token local.
-   Validar `Origin` y conexiones WebSocket.
-   No permitir que el renderer de Electron acceda directamente a
    Node.js.
-   Usar `contextIsolation`, `sandbox` y una API preload mínima.
-   No habilitar `nodeIntegration` en el renderer.
-   Validar rutas para evitar path traversal.
-   Restringir el acceso a directorios autorizados.
-   Tratar documentos, webs y contenido indexado como datos no
    confiables.
-   No ejecutar instrucciones encontradas dentro de documentos.
-   No guardar claves API en el repositorio ni en la base de datos del
    Workspace.
-   No registrar cuerpos de petición que puedan contener secretos.
-   La confirmación de acciones destructivas o masivas es obligatoria.
    Flujo (entrada "Herramientas con su módulo; confirmación y auditoría
    antes de la primera"): la herramienta crea una confirmación pendiente
    y devuelve su id sin ejecutar; solo la GUI la resuelve, mediante un
    endpoint que no es herramienta; la ejecución y la auditoría ocurren
    después. Permisos, confirmación pendiente y auditoría existen antes
    de la primera herramienta. Los detalles los congela
    `drakter/contratos`.

## 5.6. Operaciones del agente

El agente no accede directamente a SQLite ni al sistema de archivos. Usa
herramientas tipadas del backend.

Cada herramienta define: - nombre; - descripción; - esquema de
argumentos; - permisos necesarios; - nivel de riesgo; - validación; -
resultado estructurado; - errores posibles; - política de
confirmación; - registro de auditoría.

Las acciones de lectura de bajo riesgo pueden ejecutarse sin
confirmación si están autorizadas. Las operaciones destructivas, masivas
o sensibles requieren confirmación.

------------------------------------------------------------------------

# 6. Roadmap por fases

## FASE 0 --- Descubrimiento, especificación y decisiones

**Objetivo:** validar el entorno y cerrar decisiones que condicionan el
diseño.

### Tareas

-   [ ] Inspeccionar el repositorio y el estado de Git.
-   [ ] Registrar sistema operativo y arquitectura objetivo.
-   [ ] Comprobar versiones disponibles de Python y Node.js.
-   [ ] Definir versiones compatibles de Electron y React.
-   [ ] Verificar documentación y API de Hermes.
-   [ ] Definir cómo se iniciará y supervisará Hermes.
-   [ ] Verificar mecanismo de integración de Hermes Skills.
-   [ ] Verificar APIs y despliegue de OpenViking.
-   [ ] Definir la responsabilidad exacta de cada sistema de memoria.
-   [ ] Verificar compatibilidad de Rive con Electron.
-   [ ] Verificar Kokoro y voces en español.
-   [ ] Verificar Piper y voces en español.
-   [ ] Verificar requisitos de Faster-Whisper en CPU.
-   [ ] Verificar Silero VAD y openWakeWord.
-   [ ] Definir ORM y migraciones.
-   [ ] Definir ubicación de datos de usuario.
-   [ ] Definir instalación y empaquetado.
-   [ ] Crear `DECISIONS.md`.
-   [ ] Crear `IMPLEMENTATION_STATUS.md`.
-   [ ] Actualizar este roadmap con decisiones verificadas.

### Entregables

-   Arquitectura validada.
-   Matriz de compatibilidad.
-   Registro de decisiones.
-   Plan de instalación reproducible.

### Criterio de aceptación

No quedan decisiones críticas sin documentar para iniciar el esqueleto
de la aplicación.

------------------------------------------------------------------------

## FASE 1 --- Repositorio y herramientas de desarrollo

**Objetivo:** preparar una base reproducible.

### Tareas

-   [ ] Crear o verificar repositorio Git.
-   [ ] Configurar `.gitignore`.
-   [ ] Crear `.env.example` sin secretos.
-   [ ] Configurar formato y lint del frontend.
-   [ ] Configurar formato y lint del backend.
-   [ ] Configurar comprobación de tipos.
-   [ ] Configurar comprobación rápida (lint, tipos, build); sin suites por defecto.
-   [ ] Definir convenciones de commits.
-   [ ] Crear README inicial.
-   [ ] Crear documentación de arquitectura.
-   [ ] Añadir instrucciones de desarrollo.
-   [ ] Añadir comprobación básica de CI si el repositorio dispone de
    GitHub Actions.

### Criterio de aceptación

Un desarrollador puede clonar el repositorio, instalar dependencias y
ejecutar las comprobaciones iniciales siguiendo el README.

------------------------------------------------------------------------

## FASE 2 --- Esqueleto de escritorio

**Objetivo:** abrir una ventana Electron con navegación y páginas vacías
funcionales.

### Tareas

-   [ ] Crear aplicación Electron.
-   [ ] Crear frontend React + TypeScript.
-   [ ] Configurar TypeScript estricto.
-   [ ] Configurar Tailwind CSS.
-   [ ] Configurar shadcn/ui.
-   [ ] Configurar estructura de páginas.
-   [ ] Crear ventana principal.
-   [ ] Configurar preload seguro.
-   [ ] Activar `contextIsolation`.
-   [ ] Desactivar `nodeIntegration` en renderer.
-   [ ] Crear navegación lateral.
-   [ ] Crear layout principal.
-   [ ] Crear páginas placeholder para módulos.
-   [ ] Crear pantalla de configuración.
-   [ ] Crear componente de notificaciones.
-   [ ] Crear estados de carga, vacío y error.
-   [ ] Añadir pruebas básicas de renderizado.
-   [ ] Verificar build de escritorio.

### Criterio de aceptación

La aplicación se abre y navega entre todas las secciones, aunque los
módulos aún no tengan lógica de negocio.

------------------------------------------------------------------------

## FASE 3 --- Backend y comunicación

**Objetivo:** conectar de forma segura el escritorio con FastAPI.

### Tareas

-   [ ] Crear backend FastAPI.
-   [ ] Configurar settings por entorno.
-   [ ] Crear endpoint `/health`.
-   [ ] Configurar SQLite.
-   [ ] Elegir ORM y migraciones.
-   [ ] Crear sesión de base de datos.
-   [ ] Crear manejo global de errores.
-   [ ] Crear logging estructurado.
-   [ ] Crear API `/api/v1`.
-   [ ] Crear autenticación local entre Electron y backend.
-   [ ] Configurar CORS/Origin de forma restrictiva.
-   [ ] Crear WebSocket.
-   [ ] Definir esquema de eventos.
-   [ ] Crear cliente API TypeScript.
-   [ ] Crear cliente WebSocket TypeScript.
-   [ ] Añadir reconexión con backoff.
-   [ ] Mostrar estado de conexión en GUI.
-   [ ] Añadir pruebas API.
-   [ ] Añadir pruebas WebSocket.
-   [ ] Documentar contratos.

### Criterio de aceptación

La GUI consulta `/health`, recibe eventos de prueba y muestra estados
correctos de conexión y desconexión.

------------------------------------------------------------------------

## FASE 4 --- Integración de Hermes y modelo

**Objetivo:** disponer de conversación funcional desde la GUI.

### Tareas

-   [ ] Instalar Hermes siguiendo documentación oficial, en entorno propio y con versión fijada (v0.22.7), sin compartir entorno con el backend (Python 3.12).
-   [ ] Registrar versión instalada.
-   [ ] Configurar Claude Haiku 5.5 mediante configuración segura.
-   [ ] Crear interfaz interna `AgentProvider`.
-   [ ] Crear adaptador Hermes.
-   [ ] Gestionar el ciclo de vida del proceso Hermes según "Puente
    Hermes-backend": `hermes gateway run` con API server en loopback,
    supervisado por FastAPI.
-   [ ] Servir las herramientas desde el backend por MCP en loopback
    (Hermes solo cliente, perfil con lista de permitidos).
-   [ ] Definir protocolo de mensajes.
-   [ ] Implementar creación y cierre de sesiones.
-   [ ] Implementar envío de mensajes.
-   [ ] Implementar recepción de respuestas.
-   [ ] Implementar streaming si la integración soporta esa capacidad.
-   [ ] Normalizar errores del proveedor.
-   [ ] Añadir timeout y cancelación.
-   [ ] Añadir reconexión controlada.
-   [ ] Crear interfaz de chat.
-   [ ] Mostrar mensajes del usuario y agente.
-   [ ] Mostrar estado thinking.
-   [ ] Mostrar errores recuperables.
-   [ ] Construir un doble del proveedor, identificado como mock.
-   [ ] Probar con clave real (`~/.config/drakter/.env`). Sin clave, esta
    fase queda con ⚠️ y ninguna casilla de conversación, personalidad,
    selección de herramientas o memoria se marca hasta probarla con clave.

### Criterio de aceptación

El usuario puede escribir desde Drakter Desktop y recibir una respuesta
real de Hermes. Sin clave de API no se cumple: se anota con ⚠️ y no se
presenta el mock como integración.

------------------------------------------------------------------------

## FASE 5 --- Identidad, personalidad y contexto

**Objetivo:** definir la identidad persistente y el contexto base de
Drakter.

### Archivos

Los 14 archivos viven en `agent/identity/` (entrada "Los 14 archivos de
identidad viven en agent/identity/"); `agent/context/` y
`agent/knowledge/` no existen.

``` text
agent/identity/
├── SOUL.md
├── PERSONALITY.md
├── BEHAVIOR.md
├── COMMUNICATION.md
├── EMOTIONAL_STYLE.md
├── VALUES.md
├── USER.md              (plantilla sin datos reales)
├── ENVIRONMENT.md
├── PREFERENCES.md       (plantilla sin datos reales)
├── CURRENT_CONTEXT.md
├── CAPABILITIES.md
├── WORKSPACE_GUIDE.md
├── TOOL_GUIDE.md
└── SYSTEM_GUIDE.md
```

### Tareas

-   [ ] Crear `agent/identity/`.
-   [ ] Crear `SOUL.md`.
-   [ ] Crear `PERSONALITY.md`.
-   [ ] Crear `BEHAVIOR.md`.
-   [ ] Crear `COMMUNICATION.md`.
-   [ ] Crear `EMOTIONAL_STYLE.md`.
-   [ ] Crear `VALUES.md`.
-   [ ] Crear `USER.md` con plantilla vacía y editable (el `USER.md` vivo es el nativo de Hermes; la plantilla rellenada va fuera del repositorio).
-   [ ] Crear `ENVIRONMENT.md`.
-   [ ] Crear `PREFERENCES.md`.
-   [ ] Crear `CURRENT_CONTEXT.md`.
-   [ ] Crear `CAPABILITIES.md`.
-   [ ] Crear `WORKSPACE_GUIDE.md`.
-   [ ] Crear `TOOL_GUIDE.md`.
-   [ ] Crear `SYSTEM_GUIDE.md`.
-   [ ] Crear cargador de contexto: compone los 14 archivos y los publica en el `HERMES_HOME` del perfil de Drakter.
-   [ ] Definir precedencia de instrucciones.
-   [ ] Limitar tamaño de contexto (comprobar el tope de 20.000 caracteres de los archivos de contexto de Hermes, para que un recorte no elimine reglas del centro).
-   [ ] Evitar duplicar instrucciones de seguridad.
-   [ ] Comprobar carga y precedencia (comprobación rápida).

### Criterio de aceptación

Hermes recibe los archivos adecuados y demuestra un comportamiento
consistente en conversaciones de prueba (requiere clave de API; sin ella,
⚠️).

------------------------------------------------------------------------

## FASE 6 --- Personaje animado

**Objetivo:** representar visualmente los estados de Drakter.

### Tareas

-   [ ] Definir brief visual del personaje.
-   [ ] Crear diseño original.
-   [ ] Crear proyecto Rive.
-   [ ] Definir state machine.
-   [ ] Crear estado `idle`.
-   [ ] Crear estado `listening`.
-   [ ] Crear estado `thinking`.
-   [ ] Crear estado `speaking`.
-   [ ] Crear estado `executing`.
-   [ ] Crear estado `success`.
-   [ ] Crear estado `error`.
-   [ ] Crear estado `interrupted`.
-   [ ] Crear estado `offline`.
-   [ ] Crear expresiones visuales.
-   [ ] Integrar runtime Rive en React.
-   [ ] Crear `CharacterController`.
-   [ ] Conectar eventos de backend.
-   [ ] Añadir transiciones sin saltos.
-   [ ] Añadir animación de boca básica.
-   [ ] Preparar interfaz para visemas futuros.
-   [ ] Añadir pruebas de mapeo de estados.

### Criterio de aceptación

Los estados del agente se reflejan correctamente en el personaje. El
personaje no inventa estados: responde a eventos reales.

------------------------------------------------------------------------

## FASE 7 --- Modelo de datos y Workspace Core

**Objetivo:** construir la fuente de verdad del Workspace.

### Entidades iniciales

-   `Task`
-   `Project`
-   `Habit`
-   `HabitRecord`
-   `CalendarEvent`
-   `TimeBlock`
-   `Subject`
-   `ClassSession`
-   `Resource`
-   `Folder`
-   `Tag`
-   `Relationship`
-   `AuditEvent`

### Tareas

-   [ ] Diseñar esquema relacional.
-   [ ] Definir UUIDs.
-   [ ] Definir timestamps UTC.
-   [ ] Definir reglas de borrado y archivado.
-   [ ] Crear modelos ORM.
-   [ ] Crear migraciones iniciales.
-   [ ] Crear repositorios.
-   [ ] Crear servicios de dominio.
-   [ ] Crear esquemas de API.
-   [ ] Crear validaciones.
-   [ ] Crear transacciones.
-   [ ] Crear auditoría.
-   [ ] Crear pruebas de integridad.
-   [ ] Documentar el modelo de datos.

### Criterio de aceptación

Las entidades se pueden crear, consultar y actualizar mediante servicios
backend con persistencia real.

------------------------------------------------------------------------

## FASE 8 --- Tareas y subtareas

**Objetivo:** disponer del primer módulo completo del Workspace.

### Funcionalidades

-   Crear, leer, actualizar, archivar y eliminar tareas.
-   Estados y prioridades.
-   Fechas límite.
-   Etiquetas.
-   Subtareas jerárquicas.
-   Dependencias.
-   Relaciones con proyectos, asignaturas, recursos y bloques de tiempo.

### Tareas

-   [ ] Implementar CRUD de tareas.
-   [ ] Implementar estados.
-   [ ] Implementar prioridades.
-   [ ] Implementar fechas límite.
-   [ ] Implementar subtareas.
-   [ ] Validar jerarquías y evitar ciclos.
-   [ ] Implementar dependencias.
-   [ ] Implementar filtros y búsqueda.
-   [ ] Crear página de tareas.
-   [ ] Crear formulario de tarea.
-   [ ] Crear vista de detalle.
-   [ ] Crear vista de subtareas.
-   [ ] Crear estados vacío y error.
-   [ ] Crear endpoints.
-   [ ] Crear pruebas backend.
-   [ ] Crear pruebas frontend.
-   [ ] Añadir auditoría.

### Criterio de aceptación

Las tareas se gestionan desde la interfaz y los datos persisten tras
reiniciar la aplicación.

------------------------------------------------------------------------

## FASE 9 --- Proyectos

### Tareas

-   [ ] Implementar CRUD de proyectos.
-   [ ] Implementar estados.
-   [ ] Implementar prioridad.
-   [ ] Implementar fechas.
-   [ ] Asociar tareas.
-   [ ] Calcular progreso a partir de reglas explícitas.
-   [ ] Crear listado de proyectos.
-   [ ] Crear detalle de proyecto.
-   [ ] Crear filtros.
-   [ ] Crear pruebas.
-   [ ] Añadir relaciones y auditoría.

### Criterio de aceptación

Los proyectos muestran sus tareas y progreso de forma coherente, sin
duplicar información de las tareas.

------------------------------------------------------------------------

## FASE 10 --- Hábitos

### Tareas

-   [ ] Implementar CRUD de hábitos.
-   [ ] Definir frecuencia y días activos.
-   [ ] Implementar registros de cumplimiento.
-   [ ] Evitar duplicados de registro para el mismo periodo.
-   [ ] Crear historial.
-   [ ] Crear estadísticas básicas.
-   [ ] Crear interfaz de hábitos.
-   [ ] Crear recordatorios locales si se aprueban en el diseño.
-   [ ] Crear endpoints y herramientas futuras.
-   [ ] Crear pruebas de recurrencia y zona horaria.

### Criterio de aceptación

El usuario puede registrar y consultar hábitos sin perder el historial
al editar su definición.

------------------------------------------------------------------------

## FASE 11 --- Calendario y bloques de tiempo

### Tareas

-   [ ] Definir modelo de eventos.
-   [ ] Definir modelo de bloques de tiempo.
-   [ ] Implementar CRUD de eventos.
-   [ ] Implementar CRUD de bloques.
-   [ ] Implementar eventos de día completo.
-   [ ] Implementar recurrencias con reglas explícitas.
-   [ ] Implementar zona horaria.
-   [ ] Detectar solapamientos.
-   [ ] Asociar eventos con entidades del Workspace.
-   [ ] Crear vista diaria.
-   [ ] Crear vista semanal.
-   [ ] Crear vista mensual.
-   [ ] Crear filtros.
-   [ ] Crear pruebas de cambios horarios.
-   [ ] Crear pruebas de recurrencia.

### Criterio de aceptación

Los eventos y bloques se muestran en el calendario con horas correctas y
relaciones persistentes.

------------------------------------------------------------------------

## FASE 12 --- Asignaturas y horario

### Tareas

-   [ ] Implementar CRUD de asignaturas.
-   [ ] Implementar sesiones de clase recurrentes.
-   [ ] Añadir aula opcional.
-   [ ] Añadir profesor opcional.
-   [ ] Asociar recursos.
-   [ ] Asociar tareas.
-   [ ] Mostrar horario semanal.
-   [ ] Integrar sesiones con calendario.
-   [ ] Crear pruebas de recurrencia.
-   [ ] Crear documentación de uso.

### Criterio de aceptación

El horario de clases se representa correctamente y se integra con el
calendario sin duplicar sesiones.

------------------------------------------------------------------------

## FASE 13 --- Almacén e indexación

**Objetivo:** catalogar recursos sin cargar todo su contenido en el
contexto del agente.

### Tipos de recurso

-   Imágenes.
-   Documentos.
-   PDF.
-   Texto.
-   Código.
-   Enlaces.
-   Notas.
-   Apuntes.
-   Carpetas.
-   Comprimidos.
-   Otros archivos.

### Tareas

-   [ ] Definir modelo `Resource`.
-   [ ] Definir modelo `Folder`.
-   [ ] Definir metadatos.
-   [ ] Crear registro de rutas y URLs.
-   [ ] Crear descripciones opcionales.
-   [ ] Crear etiquetas.
-   [ ] Crear catálogo.
-   [ ] Configurar SQLite FTS5.
-   [ ] Indexar título, tipo, descripción y etiquetas.
-   [ ] Indexar metadatos permitidos.
-   [ ] Crear escaneo manual de ubicaciones autorizadas.
-   [ ] Detectar recursos movidos o ausentes.
-   [ ] Implementar refresco de índice.
-   [ ] Implementar búsqueda.
-   [ ] Implementar paginación.
-   [ ] Crear lectores bajo demanda para formatos aprobados.
-   [ ] Extraer texto solo cuando se solicite o se configure.
-   [ ] Definir límites de tamaño y tiempo.
-   [ ] Definir límites de extracción de comprimidos.
-   [ ] Evitar extracción automática de ejecutables.
-   [ ] Tratar el contenido como dato no confiable.
-   [ ] Crear interfaz de almacén.
-   [ ] Crear vista de carpetas.
-   [ ] Crear vista de detalle.
-   [ ] Crear pruebas con archivos ausentes y formatos inválidos.

### Criterio de aceptación

La búsqueda devuelve metadatos y referencias; el contenido completo solo
se lee bajo demanda y con permisos.

------------------------------------------------------------------------

## FASE 14 --- Relaciones entre elementos

**Objetivo:** conectar todos los módulos mediante relaciones tipadas.

### Relaciones iniciales

-   `belongs_to`
-   `related_to`
-   `scheduled_for`
-   `uses_resource`
-   `depends_on`
-   `supports`
-   `studies`
-   `parent_of`
-   `references`
-   `derived_from`

### Tareas

-   [ ] Diseñar catálogo de relaciones.
-   [ ] Validar tipos de origen y destino.
-   [ ] Crear servicio de relaciones.
-   [ ] Crear relación bidireccional solo cuando el significado lo
    requiera.
-   [ ] Implementar consulta de relaciones entrantes.
-   [ ] Implementar consulta de relaciones salientes.
-   [ ] Implementar filtros por tipo.
-   [ ] Evitar referencias huérfanas.
-   [ ] Definir borrado y archivado de elementos relacionados.
-   [ ] Crear vista de relaciones.
-   [ ] Crear pruebas de integridad.
-   [ ] Documentar cada tipo de relación.

### Criterio de aceptación

Un elemento puede mostrar sus relaciones y el backend valida que cada
relación tenga sentido para los tipos implicados.

------------------------------------------------------------------------

## FASE 15 --- Skills y herramientas de Workspace

**Objetivo:** permitir que Hermes gestione el Workspace mediante
lenguaje natural.

Cada herramienta se construye con su módulo (Fases 7 a 14) y se comprueba
por llamada directa; esta fase integra las Skills (obligatoria, paso 14)
y comprueba la selección de herramientas con el modelo. Permisos,
confirmación pendiente y auditoría existen antes de la primera
herramienta (véase §5.5): las tareas de esta fase que los nombran son
revisión y endurecimiento. El catálogo definitivo lo congela
`drakter/contratos`; si difiere, manda su entrada posterior.

### Herramientas

#### Tasks

-   `create_task`
-   `get_task`
-   `update_task`
-   `archive_task`
-   `complete_task`
-   `create_subtask`
-   `list_tasks`
-   `search_tasks`

#### Projects

-   `create_project`
-   `get_project`
-   `update_project`
-   `archive_project`
-   `list_projects`
-   `get_project_progress`

#### Habits

-   `create_habit`
-   `update_habit`
-   `register_habit_completion`
-   `list_habits`
-   `get_habit_history`
-   `get_habit_statistics`

#### Calendar

-   `create_event`
-   `update_event`
-   `delete_event`
-   `create_time_block`
-   `get_schedule`
-   `check_availability`

#### Subjects

-   `create_subject`
-   `update_subject`
-   `get_subjects`
-   `get_timetable`
-   `get_subject_resources`

#### Storage

-   `search_resources`
-   `get_resource`
-   `read_resource`
-   `create_resource_metadata`
-   `update_resource_metadata`
-   `index_resource`
-   `refresh_resource_index`

Eliminar o mover recursos no tiene herramienta de agente en la v1: se
hace solo desde la GUI, con confirmación. Si el agente recibe esa
petición, lo dice y no improvisa un sustituto (entrada "Huecos de
MASTER_PLAN §19").

#### Relationships

-   `create_relationship`
-   `delete_relationship`
-   `get_related_items`
-   `search_relationships`

#### System

-   `get_system_status`
-   `get_agent_status`
-   `get_voice_status`
-   `get_memory_status`
-   `get_workspace_summary`

### Tareas

-   [ ] Revisar el contrato común de herramientas (creado con la primera).
-   [ ] Revisar validación de argumentos.
-   [ ] Revisar permisos por herramienta.
-   [ ] Revisar clasificación de riesgo.
-   [ ] Revisar confirmación de acciones sensibles (flujo de §5.5).
-   [ ] Implementar idempotencia para operaciones que lo necesiten.
-   [ ] Implementar timeout.
-   [ ] Implementar errores estructurados.
-   [ ] Crear Skills compatibles con la versión real de Hermes.
-   [ ] Documentar cada Skill.
-   [ ] Probar operaciones desde Hermes (requiere clave de API; sin ella, ⚠️).
-   [ ] Probar operaciones ambiguas.
-   [ ] Probar intentos de acceso no autorizado.

### Criterio de aceptación

Hermes puede crear, consultar y modificar datos del Workspace
exclusivamente mediante herramientas validadas.

------------------------------------------------------------------------

## FASE 16 --- Memoria persistente

**Objetivo:** dotar a Drakter de memoria entre sesiones y recuperación
selectiva.

### Capas conceptuales

1.  Memoria de trabajo: sesión y operaciones activas.
2.  Memoria episódica: acontecimientos, decisiones y experiencias.
3.  Memoria semántica: hechos y conocimiento estable.
4.  Memoria procedimental: procedimientos y Skills.

### Responsabilidades de proveedores

-   **Memoria nativa de Hermes:** contexto breve y estable (`MEMORY.md`,
    `USER.md`, sesiones).
-   **OpenViking:** único proveedor externo; memorias extraídas y
    recursos con recuperación progresiva L0/L1/L2.

ByteRover queda fuera de la memoria del producto: es una utilidad
opcional de desarrollo.

El Memory Adapter es un servicio del backend para la interfaz y la
ingesta, no una capa multiproveedor (ver `docs/MASTER_PLAN.md` §10). No
hay pipeline propio de memoria: extraer, clasificar, deduplicar y
resolver contradicciones se configura y se comprueba en OpenViking, y lo
que falte se anota con ⚠️ (entrada "Memoria sin pipeline propio ni
recuerdos en el repositorio"). La ingesta del almacén en OpenViking es
opcional por recurso, viene apagada por defecto y pasa siempre por el
backend.

### Archivos de contexto

`agent/identity/` guarda la identidad (Fase 5). `memory/` guarda solo
configuración e integración, nunca recuerdos ni datos personales; los
recuerdos viven en la memoria nativa de Hermes y en OpenViking, fuera del
repositorio.

### Tareas

-   [ ] Crear `MemoryAdapter`.
-   [ ] Comprobar qué aportan OpenViking y Hermes en procedencia, fecha,
    confianza y caducidad de recuerdos; lo que falte, con ⚠️.
-   [ ] Configurar y comprobar la extracción de candidatos en OpenViking.
-   [ ] Configurar OpenViking como proveedor de Hermes.
-   [ ] Configurar capas L0/L1/L2.
-   [ ] Elegir embedding multilingüe.
-   [ ] Configurar y comprobar en OpenViking la clasificación, la
    deduplicación, la detección de contradicciones y la política de
    actualización; lo que falte, con ⚠️.
-   [ ] Crear la Skill `memory-management` (aquí, no en la Fase 15).
-   [ ] Ingesta del almacén en OpenViking: opcional por recurso, apagada
    por defecto y siempre vía backend.
-   [ ] Configurar recuperación por relevancia.
-   [ ] Implementar límites de tokens/contexto.
-   [ ] Implementar citas internas/procedencia de recuerdos.
-   [ ] Implementar inspección y corrección de recuerdos.
-   [ ] Implementar borrado de recuerdos con propagación a los almacenes
    implicados.
-   [ ] Comprobar persistencia entre sesiones (con clave de API; sin ella, ⚠️).
-   [ ] Comprobar recuperación y contradicciones.
-   [ ] Comprobar que la memoria recuperada no puede sobrescribir reglas
    de seguridad ni imponerse a la instrucción actual.

### Criterio de aceptación

La memoria se conserva entre sesiones, se recupera selectivamente y
puede inspeccionarse, corregirse y eliminarse sin dejar copias conocidas
en los almacenes gestionados.

------------------------------------------------------------------------

## FASE 17 --- Voz local

**Objetivo:** permitir interacción hablada sin depender inicialmente de
servicios de voz en la nube.

### Pipeline

`openWakeWord → Silero VAD → Faster-Whisper → Hermes → Kokoro/Piper → reproducción`

### Tareas

-   [ ] Crear `VoiceManager`.
-   [ ] Crear interfaz `WakeWordProvider`.
-   [ ] Integrar openWakeWord.
-   [ ] Configurar palabra de activación.
-   [ ] Crear interfaz `VADProvider`.
-   [ ] Integrar Silero VAD.
-   [ ] Crear interfaz `STTProvider`.
-   [ ] Integrar Faster-Whisper.
-   [ ] Probar modelo small en CPU INT8.
-   [ ] Medir latencia y consumo.
-   [ ] Evaluar modelo medium solo si las pruebas lo justifican.
-   [ ] Crear interfaz `TTSProvider`.
-   [ ] Integrar Kokoro.
-   [ ] Integrar Piper como alternativa.
-   [ ] Verificar voces en español.
-   [ ] Crear cola de audio.
-   [ ] Implementar cancelación.
-   [ ] Implementar interrupción por voz.
-   [ ] Implementar estados de escucha.
-   [ ] Crear `VoicePersonalityEngine`.
-   [ ] Mapear velocidad, pausas y volumen a capacidades reales del TTS.
-   [ ] Sincronizar reproducción con el personaje.
-   [ ] Añadir controles de micrófono.
-   [ ] Añadir indicador visible de escucha.
-   [ ] Añadir opción de desactivar micrófono.
-   [ ] Crear pruebas con ruido y silencios.
-   [ ] Medir rendimiento en el hardware real (i7-8665U, 8 hilos, 14 GB de
    RAM, gráfica integrada sin VRAM dedicada; voz dimensionada para CPU).
    Solo se publican cifras medidas.

### Restricción de implementación

No afirmar que el sistema ofrece emociones vocales completas si el motor
TTS solo permite controlar voz, velocidad o parámetros limitados.
Implementar primero lo que la API soporte y documentar el resto.

### Criterio de aceptación

El usuario puede activar el agente, hablar, recibir transcripción,
obtener respuesta y escucharla. La escucha puede desactivarse de forma
clara y fiable.

------------------------------------------------------------------------

## FASE 18 --- Automejora controlada

**Objetivo:** permitir propuestas de mejora sin autoalteración insegura.

Lo publicado al agente en uso (Skills, identidad) cuenta como
producción: toda modificación pasa por propuesta y autorización
(entrada "Trabajo sin clave y alcance de automejora, copias y v1").

### Tareas

-   [ ] Crear registro de feedback.
-   [ ] Crear clasificación de incidencias.
-   [ ] Crear propuestas de mejora.
-   [ ] Crear evaluaciones.
-   [ ] Crear entorno de pruebas aislado.
-   [ ] Crear flujo de aprobación.
-   [ ] Integrar Git para cambios propuestos.
-   [ ] Crear changelog.
-   [ ] Crear informes.
-   [ ] Exigir propuesta y autorización para toda modificación (código, Skills, identidad, configuración).
-   [ ] Impedir que el agente amplíe sus permisos.
-   [ ] Impedir que modifique políticas de seguridad.
-   [ ] Impedir que elimine auditoría.
-   [ ] Crear pruebas de rechazo de acciones no autorizadas.

### Criterio de aceptación

Drakter identifica oportunidades y prepara propuestas, pero no altera
producción ni sus controles de seguridad por iniciativa propia.

------------------------------------------------------------------------

## FASE 19 --- Seguridad, resiliencia y backups

Permisos, confirmación pendiente y auditoría ya existen desde antes de la
primera herramienta; las tareas siguientes son revisión y
endurecimiento.

### Tareas

-   [ ] Revisar permisos por herramienta.
-   [ ] Revisar validación de rutas.
-   [ ] Revisar protección frente a path traversal.
-   [ ] Revisar secretos y configuración.
-   [ ] Revisar CORS y WebSocket.
-   [ ] Revisar sandbox de Electron.
-   [ ] Revisar tratamiento de contenido no confiable.
-   [ ] Revisar operaciones destructivas.
-   [ ] Endurecer la auditoría (sin claves API ni datos sensibles).
-   [ ] Crear backup de SQLite.
-   [ ] Crear restauración de SQLite.
-   [ ] Crear exportación de Workspace.
-   [ ] Definir backup de configuración.
-   [ ] Las copias incluyen SQLite, configuración, identidad, Skills, datos
    de OpenViking y home de Hermes, sin secretos.
-   [ ] Definir backup de metadatos e índices.
-   [ ] Documentar qué archivos externos no se copian.
-   [ ] Probar recuperación tras cierre inesperado.
-   [ ] Probar recuperación si Hermes no está disponible.
-   [ ] Probar recuperación si memoria externa no está disponible.
-   [ ] Probar recuperación si STT/TTS falla.

### Criterio de aceptación

Los datos pueden recuperarse y los fallos de componentes externos no
corrompen la fuente de verdad del Workspace.

------------------------------------------------------------------------

## FASE 20 --- Optimización, empaquetado y versión inicial

### Tareas

-   [ ] Medir uso de RAM.
-   [ ] Medir CPU.
-   [ ] Medir uso de CPU y RAM por componente (Hermes, OpenViking, voz);
    la máquina no tiene VRAM dedicada.
-   [ ] Medir latencia del modelo.
-   [ ] Medir latencia STT.
-   [ ] Medir latencia TTS.
-   [ ] Medir consultas SQLite.
-   [ ] Medir recuperación de memoria.
-   [ ] Optimizar consultas lentas.
-   [ ] Optimizar carga de frontend.
-   [ ] Definir empaquetado de backend.
-   [ ] Definir instalación de modelos locales.
-   [ ] Definir gestión de actualizaciones.
-   [ ] Crear instalador de desarrollo.
-   [ ] Crear instalador de usuario.
-   [ ] Crear guía de instalación.
-   [ ] Crear guía de uso.
-   [ ] Crear pruebas de aceptación.
-   [ ] Crear versión `0.1.0`.
-   [ ] Etiquetar release.
-   [ ] Crear backup previo a actualización.

### Criterio de aceptación

Drakter puede instalarse, arrancar, utilizarse, actualizarse y
restaurarse siguiendo documentación reproducible.

------------------------------------------------------------------------

## FASE 21 --- Mejoras posteriores

Fuera de alcance; no bloquean la primera versión ni se tocan antes de
tiempo (las ampliaciones de `MASTER_PLAN` Fase 15 equivalen a esta Fase 21).

-   [ ] Evaluar LiveKit Agents para streaming de voz avanzado.
-   [ ] Evaluar PostgreSQL si SQLite deja de ser suficiente.
-   [ ] Añadir sincronización entre dispositivos.
-   [ ] Añadir aplicación móvil complementaria.
-   [ ] Integrar Home Assistant.
-   [ ] Añadir automatizaciones avanzadas.
-   [ ] Añadir capacidades multimodales.
-   [ ] Añadir panel de monitorización.
-   [ ] Añadir proveedores de modelos alternativos.
-   [ ] Añadir importación/exportación avanzada.
-   [ ] Añadir plugins de terceros con permisos granulares.

------------------------------------------------------------------------

# 7. Skills y archivos de personalidad previstos

## 7.1. Skills

Crear Skills solo cuando la herramienta subyacente esté implementada y
comprobada. `memory-management` se crea en la Fase 16; el resto, en la
Fase 15.

``` text
agent/skills/
├── workspace-tasks/
├── workspace-projects/
├── workspace-habits/
├── workspace-calendar/
├── workspace-subjects/
├── workspace-storage/
├── workspace-relationships/
├── memory-management/
└── system-status/
```

Cada Skill debe incluir: - propósito; - cuándo utilizarla; -
parámetros; - ejemplos no sensibles; - restricciones; - errores
esperables; - herramientas backend que invoca.

No duplicar reglas de negocio dentro de Skills. La validación real
siempre reside en backend.

## 7.2. Archivos de identidad

Los archivos de personalidad describen estilo e identidad, no permisos
técnicos. Los permisos se aplican en backend.

------------------------------------------------------------------------

# 8. Modelo de datos inicial

## 8.1. Tablas

### `tasks`

-   `id`
-   `title`
-   `description`
-   `status`
-   `priority`
-   `due_at`
-   `completed_at`
-   `parent_task_id`
-   `created_at`
-   `updated_at`
-   `archived_at`

### `projects`

-   `id`
-   `name`
-   `description`
-   `status`
-   `priority`
-   `start_at`
-   `target_at`
-   `completed_at`
-   `created_at`
-   `updated_at`

### `habits`

-   `id`
-   `name`
-   `description`
-   `schedule_rule`
-   `start_date`
-   `end_date`
-   `active`
-   `created_at`
-   `updated_at`

### `habit_records`

-   `id`
-   `habit_id`
-   `recorded_for`
-   `status`
-   `note`
-   `created_at`

### `calendar_events`

-   `id`
-   `title`
-   `description`
-   `starts_at`
-   `ends_at`
-   `timezone`
-   `all_day`
-   `recurrence_rule`
-   `created_at`
-   `updated_at`

### `time_blocks`

-   `id`
-   `title`
-   `description`
-   `starts_at`
-   `ends_at`
-   `timezone`
-   `status`
-   `created_at`
-   `updated_at`

### `subjects`

-   `id`
-   `name`
-   `description`
-   `color`
-   `created_at`
-   `updated_at`

### `class_sessions`

-   `id`
-   `subject_id`
-   `weekday`
-   `starts_local_time`
-   `ends_local_time`
-   `timezone`
-   `valid_from`
-   `valid_until`
-   `room`
-   `created_at`
-   `updated_at`

### `resources`

-   `id`
-   `title`
-   `resource_type`
-   `uri`
-   `description`
-   `mime_type`
-   `size_bytes`
-   `content_hash`
-   `availability_status`
-   `indexed_at`
-   `created_at`
-   `updated_at`

### `folders`

-   `id`
-   `name`
-   `parent_folder_id`
-   `uri`
-   `created_at`
-   `updated_at`

### `tags`

-   `id`
-   `name`
-   `color`
-   `created_at`

### `relationships`

-   `id`
-   `source_type`
-   `source_id`
-   `target_type`
-   `target_id`
-   `relationship_type`
-   `metadata_json`
-   `created_at`

### `entity_tags`

-   `id`
-   `entity_type`
-   `entity_id`
-   `tag_id`

### `audit_events`

-   `id`
-   `actor_type`
-   `action`
-   `entity_type`
-   `entity_id`
-   `result`
-   `created_at`
-   `correlation_id`

Este esquema es una base inicial, no una orden de implementar todas las
tablas en una sola migración. Revisar restricciones, índices, claves
foráneas y estrategia polimórfica antes de cerrar el diseño.

## 8.2. Decisiones de integridad

-   Las subtareas deben pertenecer a una tarea existente.
-   Las sesiones de clase deben pertenecer a una asignatura existente.
-   Los registros de hábitos deben pertenecer a un hábito existente.
-   Los enlaces de relaciones deben validarse contra entidades reales.
-   No permitir ciclos en jerarquías de tareas.
-   No borrar en cascada datos históricos accidentalmente.
-   Preferir archivado para elementos que tengan relaciones o historial.
-   Usar transacciones para operaciones compuestas.

------------------------------------------------------------------------

# 9. Estrategia de pruebas

> Sustituida por `CLAUDE.md` §3 y §4: sin suites, sin tests de cierre de
> fase y sin esperas de aprobación. Lo que sigue es un catálogo de qué
> puede comprobarse; solo se escriben tests en las excepciones de
> `CLAUDE.md` §4 (rutas y permisos del almacén, confirmaciones
> destructivas, migraciones y copias, memoria frente a reglas de
> seguridad). Se conservan: seguridad, secretos, acciones destructivas,
> no marcar sin evidencia y no presentar mocks como integraciones.

## 9.1. Backend

-   Unit tests de servicios.
-   Tests de repositorios.
-   Tests de API.
-   Tests de permisos.
-   Tests de migraciones.
-   Tests de integridad de relaciones.
-   Tests de transacciones.
-   Tests de recuperación ante errores.

## 9.2. Frontend

-   Tests de componentes.
-   Tests de formularios.
-   Tests de navegación.
-   Tests de estados de carga/error/vacío.
-   Tests de cliente API.
-   Tests de eventos WebSocket.
-   Tests de accesibilidad básicos.

## 9.3. Integración

-   GUI ↔ backend.
-   Backend ↔ Hermes.
-   Hermes ↔ tools.
-   Backend ↔ memoria.
-   Voice Manager ↔ STT/TTS.
-   Eventos backend ↔ personaje.

## 9.4. Calidad mínima antes de cerrar una fase

-   Comprobación rápida de la funcionalidad correcta.
-   Lint sin errores nuevos.
-   Typecheck sin errores.
-   Build correcto.
-   No hay secretos en diff.
-   No hay archivos temporales o modelos enormes añadidos
    accidentalmente.
-   Documentación actualizada.
-   Criterio de aceptación cumplido.

------------------------------------------------------------------------

# 10. Variables de entorno

Crear `.env.example` con nombres y descripciones, nunca valores reales.

Variables previstas, sujetas a la integración verificada:

``` dotenv
DRAKTER_ENV=development
DRAKTER_HOST=127.0.0.1
DRAKTER_PORT=8765
DRAKTER_DATA_DIR=
DRAKTER_LOG_LEVEL=INFO

ANTHROPIC_API_KEY=
DRAKTER_MODEL_PROVIDER=anthropic
DRAKTER_MODEL_NAME=claude-haiku-5-5

HERMES_COMMAND=
HERMES_CONFIG_PATH=

OPENVIKING_ENDPOINT=
OPENVIKING_API_KEY=

DRAKTER_VOICE_ENABLED=false
DRAKTER_STT_MODEL=small
DRAKTER_STT_DEVICE=cpu
DRAKTER_TTS_PROVIDER=kokoro
DRAKTER_WAKEWORD_ENABLED=false
```

No implementar variables que el sistema no utilice. Documentar cuáles
son obligatorias, opcionales y locales.

------------------------------------------------------------------------

# 11. Observabilidad y gestión de errores

## 11.1. Logs

Usar logs estructurados con: - timestamp; - nivel; - componente; -
operación; - correlation ID; - duración; - resultado.

No registrar: - claves API; - tokens; - contraseñas; - audio bruto por
defecto; - contenido completo de documentos por defecto; - datos
personales innecesarios.

## 11.2. Estados del agente

Estados funcionales: - `idle` - `listening` - `thinking` - `speaking` -
`executing` - `success` - `error` - `interrupted` - `offline`

El estado debe proceder de eventos reales del agente y del sistema.

------------------------------------------------------------------------

# 12. Checklist global de aceptación

## Producto

-   [ ] La aplicación de escritorio inicia.
-   [ ] La navegación funciona.
-   [ ] La GUI se conecta al backend.
-   [ ] Hermes responde desde el chat.
-   [ ] La personalidad se carga correctamente.
-   [ ] El personaje representa estados reales.
-   [ ] Las tareas funcionan.
-   [ ] Los proyectos funcionan.
-   [ ] Los hábitos funcionan.
-   [ ] El calendario funciona.
-   [ ] Las asignaturas funcionan.
-   [ ] El almacén cataloga recursos.
-   [ ] La indexación funciona.
-   [ ] La lectura bajo demanda funciona.
-   [ ] Las relaciones funcionan.
-   [ ] Hermes puede usar las herramientas autorizadas.
-   [ ] La memoria persiste entre sesiones.
-   [ ] La memoria se recupera selectivamente.
-   [ ] La voz local funciona.
-   [ ] Las interrupciones de voz funcionan.
-   [ ] Las operaciones sensibles requieren confirmación.
-   [ ] La auditoría registra operaciones.
-   [ ] Las copias de seguridad funcionan.
-   [ ] La restauración está probada.
-   [ ] La instalación está documentada.

## Calidad

-   [ ] Comprobación rápida del backend, del frontend y de la integración
    correcta (sin suites; solo las excepciones de `CLAUDE.md` §4).
-   [ ] Typecheck pasa.
-   [ ] Lint pasa.
-   [ ] Build pasa.
-   [ ] No hay secretos en Git.
-   [ ] No hay dependencias críticas sin versión fijada.
-   [ ] No hay funciones críticas simuladas.
-   [ ] No hay errores conocidos bloqueantes.
-   [ ] README actualizado.
-   [ ] ROADMAP actualizado.
-   [ ] IMPLEMENTATION_STATUS actualizado.
-   [ ] DECISIONS actualizado.

------------------------------------------------------------------------

# 13. Archivos de gestión del proyecto

Claude Code debe mantener estos documentos:

## `ROADMAP.md`

Este documento, subordinado a `docs/DECISIONS.md`. Contiene fases,
tareas, decisiones iniciales y criterios de aceptación; sus casillas son
históricas. Todos estos archivos viven en `docs/`.

## `IMPLEMENTATION_STATUS.md`

Debe reflejar: - fase activa; - fase completada; - tareas completadas; -
tareas pendientes; - bloqueos; - pruebas ejecutadas; - fecha de última
actualización.

## `DECISIONS.md`

Registro de decisiones con: - ID; - fecha; - contexto; - opciones
consideradas; - decisión; - motivos; - consecuencias; - estado.

## `README.md`

Debe contener: - descripción; - requisitos; - instalación; -
configuración; - ejecución; - pruebas; - estructura; - solución de
problemas.

------------------------------------------------------------------------

# 14. Primer encargo para Claude Code

Al recibir este documento:

1.  Inspecciona el repositorio sin modificar archivos.
2.  Comprueba el estado de Git y detecta cambios preexistentes.
3.  Identifica archivos y tecnologías ya existentes.
4.  Compara el estado real con este roadmap.
5.  Señala contradicciones, incompatibilidades y decisiones pendientes.
6.  Propón el plan concreto de la Fase 0.
7.  Registra las decisiones y continúa: no se espera aprobación para lo
    reversible (`CLAUDE.md` §3); se consulta al usuario solo si cambia el
    objetivo del producto.

Después, trabaja fase por fase y actualiza los documentos de seguimiento
(`docs/IMPLEMENTATION_STATUS.md` y `docs/DECISIONS.md`).

**Regla final:** la prioridad es construir un sistema funcional,
verificable y mantenible. No sacrifiques fiabilidad por aparentar
progreso ni marques como implementada una integración que solo esté
descrita o simulada.
