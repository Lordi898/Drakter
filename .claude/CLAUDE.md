# CLAUDE.md — Proyecto DRAKTER

Agente personal de IA con aplicación de escritorio propia. Este archivo se carga automáticamente en cada sesión de Claude Code. Léelo entero al empezar y respétalo durante todo el proyecto.

---

## 1. Qué es el proyecto (resumen)

Drakter se compone de tres sistemas conectados por APIs internas:

- **Drakter Core**: agente (Hermes + Claude Haiku 5.5), personalidad, memoria, herramientas.
- **Drakter Desktop**: Electron + React + TypeScript + Tailwind + shadcn/ui + Rive (personaje animado), voz y paneles.
- **Drakter Workspace**: SQLite (+ FTS5) con tareas, proyectos, hábitos, calendario, asignaturas, almacén y relaciones.

Backend: Python 3.12 + FastAPI (REST + WebSocket), versión elegida por el proyecto. Hermes (tag v0.22.7, `b200f5bc`, instalado desde git, no desde PyPI) corre como subproceso en su propio venv con Python 3.14; OpenViking, en otro entorno (ver `docs/DECISIONS.md`). Local-first, un solo usuario, Linux primero (arquitectura preparada para Windows).
El detalle completo (arquitectura, módulos, fases, estructura de carpetas) está en `docs/MASTER_PLAN.md`. **No lo copies aquí; consúltalo.**

---

## 2. Los documentos del proyecto

Los documentos de control están en `docs/`. Tres son la memoria del proyecto entre sesiones; `RUN_STATE.md` es la foto operativa de la ejecución; `ROADMAP.md` y `PLAN_DISEÑO_COMPLETO_DRAKTER.md` son planes subordinados.

**Prevalencia:** entrada más reciente de `DECISIONS.md` → este archivo → `MASTER_PLAN.md` → `ROADMAP.md` → `PLAN_DISEÑO_COMPLETO_DRAKTER.md`. Lo verificado en la realidad corrige a todos, y una inversión de este orden exige entrada en `DECISIONS.md`.

| Archivo | Contenido | Quién lo modifica |
|---|---|---|
| `MASTER_PLAN.md` | El plan maestro (arquitectura, módulos, fases, flujos). Es la fuente de verdad del **qué** construir. | Solo se cambia si el usuario lo pide o si una decisión en `DECISIONS.md` lo exige; en ese caso anota el cambio allí también. |
| `IMPLEMENTATION_STATUS.md` | Las checklists 0–18 del plan, con su estado actual. Es la fuente de verdad del **qué está hecho** y la única lista viva de casillas. | Tú, constantemente. |
| `DECISIONS.md` | Decisiones técnicas, cambios de tecnología y sus motivos. Es la fuente de verdad del **por qué**. | Tú, cada vez que decidas algo no trivial. |

### Reglas de uso

1. **Al empezar una sesión:** lee `IMPLEMENTATION_STATUS.md` y las últimas entradas de `DECISIONS.md`. Retoma por la primera tarea pendiente según el orden real de desarrollo del plan.
2. **Al terminar cualquier tarea:** marca la casilla en `IMPLEMENTATION_STATUS.md` en el mismo momento (`- [x]`). Una tarea se marca cuando **está implementada y funciona como se espera** (ver sección 4). No hace falta una suite de tests para marcarla.
3. **Si algo queda a medias o bloqueado:** anótalo bajo la casilla con `⚠️` y el motivo. No marques como hecho lo que no funciona.
4. **Al cambiar de tecnología, desviarte del plan o tomar una decisión de arquitectura:** añade una entrada a `DECISIONS.md` con este formato:

```
## [AAAA-MM-DD] Título corto de la decisión
- **Contexto:** qué problema o situación la provoca.
- **Decisión:** qué se hace.
- **Alternativas descartadas:** y por qué.
- **Motivo:** razón principal.
- **Impacto:** qué archivos, fases o checklists afecta.
```

5. Si el plan y la realidad chocan (una librería no existe, una API es distinta, un componente es incompatible), **no te bloquees ni preguntes**: elige la mejor alternativa, regístrala en `DECISIONS.md` y sigue. Solo consulta al usuario si el cambio altera el objetivo del producto.

### Riesgos ya identificados (regístralos en DECISIONS.md al llegar a ellos)

- **Memoria:** se usa la memoria nativa de Hermes + OpenViking como único proveedor externo, con sus capas L0/L1/L2 (`MASTER_PLAN.md` §10). El backend recupera los recuerdos y los entrega cercados como dato no confiable, nunca en el prompt de sistema; con el runner propio no hay plugin de memoria en Hermes (ver `docs/DECISIONS.md`). Hindsight y Mem0 quedan fuera. Antes de guardar datos reales hay que elegir un embedding multilingüe y validar el modelo que genera L0/L1.
- **Rive:** el archivo `.riv` se diseña en el editor visual de Rive y no puede generarse por código. Construye el componente React, el receptor de eventos y un personaje placeholder (SVG/CSS) con la misma API de estados (`idle`, `listening`, `thinking`, `speaking`, `executing`, `success`, `error`, `interrupted`, `offline`). El `.riv` real se enchufa después sin tocar el resto.
- **Hermes embebido:** Hermes es un framework de agente completo (bucle propio, CLI, gateway). No se usa su gateway: un runner propio crea `AIAgent` en un proceso aparte, con el venv de Hermes, supervisado por FastAPI, y las herramientas las sirve el backend mediante MCP. La decisión está en `docs/DECISIONS.md` y aún no se ha probado en ejecución.
- **Voz:** la latencia real depende del hardware. La máquina de desarrollo es un i7-8665U con 14 GB de RAM y gráfica integrada, sin VRAM dedicada: se dimensiona para CPU. Deja medición y configuración listas, pero no inventes cifras.

---

## 3. Prioridad absoluta: velocidad con calidad

El objetivo es terminar **lo antes posible**, manteniendo el nivel y que todo esté correcto.

- Trabaja en el orden real de desarrollo del plan, pero **paraleliza todo lo que no tenga dependencias entre sí** (ver sección 5).
- No pidas confirmación para cosas reversibles. Decide, avanza, registra.
- No sobre-diseñes: implementa lo que pide el plan, bien hecho, sin extras ni abstracciones especulativas. Las ampliaciones futuras (MASTER Fase 15, ROADMAP Fase 21, Checklist 18) **no** se tocan.
- Evita ciclos largos de revisión, refactor o pulido innecesario. Si funciona y se ve bien, se pasa a lo siguiente.
- Cuando una tarea sea mecánica o repetitiva (CRUD de un módulo, esquemas, herramientas Hermes), genera por patrón y delega en subagentes.

---

## 4. Política de pruebas (mínima y pragmática)

**Regla general: no hacer pruebas ni tests innecesarios.**

- **Criterio de "hecho":** la funcionalidad se ejecuta, hace lo que se espera, y la interfaz se ve bien. Una comprobación rápida (arrancar, llamar al endpoint, abrir la pantalla, una conversación de prueba) es suficiente.
- **No** escribas suites de tests exhaustivas, ni tests unitarios por defecto, ni pruebas de cobertura, ni test-driven development. **No** repitas pruebas ya superadas. **No** te quedes depurando casos improbables.
- **Excepción (solo estas, y de forma breve):** un test o comprobación puntual está permitido cuando un fallo silencioso sería caro o peligroso:
  1. Validación de rutas y permisos de archivos del almacén.
  2. Confirmaciones de acciones destructivas.
  3. Migraciones de SQLite y copia/restauración de datos.
  4. Que la memoria recuperada no pueda sobrescribir reglas de seguridad.
- Si algo falla al comprobarlo, arréglalo y avanza. No añadas tests de regresión salvo que el mismo fallo reaparezca.
- **Esto prevalece sobre cualquier skill que exija TDD** (en particular, el flujo de TDD de `superpowers`): para este proyecto está desactivado. Usa de `superpowers` el brainstorming, la planificación, la ejecución paralela y la depuración sistemática, no el ciclo rojo-verde-refactor obligatorio.
- Lo que el plan llama "pruebas satisfactorias" al final de cada fase se interpreta como "funciona y se ve bien", no como "cobertura completa".

---

## 5. Agentes y subagentes: sin límites

Tienes **libertad total y sin límite** para usar agentes y subagentes, cuantos quieras y cuando quieras. Cuantos más en paralelo, mejor, siempre que eso reduzca el tiempo total y mantenga el resultado correcto. Frenos de esta máquina: como mucho 2 instalaciones o compilaciones pesadas a la vez en toda la flota, y ningún lanzamiento nuevo con `MemAvailable` por debajo de 300 MB.

### Reglas fijas

- **Para crear, instalar o adaptar cualquier agente o subagente, usa siempre la skill `agent-forge`** (`.claude/skills/agent-forge/SKILL.md`). También para redactar el prompt de cada delegación.
- **El agente principal es `drakter-orquestator`** (`.claude/agents/drakter-orquestator.md`), activo por `"agent"` en `.claude/settings.local.json` o con `claude --agent drakter-orquestator`. Los subagentes pueden lanzar subagentes hasta 3 niveles bajo el hilo principal; `drakter-lider` dirige los frentes grandes. Si esta sesión no corre como `drakter-orquestator`, adopta igualmente su ciclo de trabajo.

### Qué puedes hacer

- Lanzar todos los subagentes que consideres, en paralelo, para cualquier parte del trabajo (frontend, backend, base de datos, herramientas Hermes, personalidad, documentación, investigación, revisión).
- **Instalar, copiar o clonar agentes y subagentes de la comunidad**, de forma interna o externa, desde GitHub, registros de skills o cualquier otra fuente, y usarlos directamente.
- **Crear tus propios agentes y subagentes** especializados (en `.claude/agents/`) cuando ninguno existente encaje: por ejemplo `backend-module-builder`, `ui-module-builder`, `hermes-tool-writer`, `docs-keeper`, `reviewer`.
- Usar agentes para investigar en internet, leer documentación y comparar librerías mientras otros agentes siguen construyendo.
- Usar un agente dedicado al mantenimiento de `IMPLEMENTATION_STATUS.md` y `DECISIONS.md` para que no frene al resto.

### Cómo mantener la corrección mientras paralelizas

Esto no limita el número de agentes; evita que se pisen y haya que rehacer trabajo.

1. **Reparte por zonas disjuntas** del repositorio (`desktop/`, `backend/`, `agent/`, `memory/`, `voice/`) o por módulos. Dos agentes no editan el mismo archivo a la vez. `memory/` y `workspace/` no guardan datos reales.
2. **Congela primero los contratos** (esquema de BD, modelos Pydantic, rutas de API, eventos WebSocket, formato de herramientas Hermes). Con los contratos fijos, frontend, backend y herramientas se construyen en paralelo.
3. Para trabajo en paralelo sobre el mismo repo, usa **ramas o `git worktree`** por agente y fusiona al terminar.
4. Un agente (o tú) actúa de **integrador**: une las piezas, resuelve conflictos y comprueba que todo arranca junto.
5. Cada subagente recibe en su instrucción: el objetivo concreto, los archivos que le pertenecen, el contrato que debe cumplir y el criterio de "hecho" de la sección 4.

### Higiene al instalar cosas de terceros

Instalar de la comunidad está permitido y fomentado. Aun así: antes de ejecutar scripts de un skill o agente externo, échales un vistazo rápido (qué comandos corren, a qué red acceden); fija la versión o el commit cuando sea posible; y anota en `DECISIONS.md` qué has instalado y de dónde. Nada de esto debe frenar el avance: es una lectura de un minuto, no una auditoría.

---

## 6. Skills del proyecto

Las skills de este proyecto son estas y ya están instaladas en `.claude/skills/` (orígenes y adaptaciones en `docs/DECISIONS.md`). Cuándo usar cada una está en **`.claude/skills/drakter-toolkit/SKILL.md`**.

1. **Las skills útiles para Drakter de** `https://github.com/LLMTooling/agent-skills` (no las 105): `electron`, `electron-builder`, `electron-vite`, `vite`, `vitest`, `playwright-cli`, `typescript-best-practices`, `react-19`, `shadcn`, `radix-ui`, `tailwind-css`, `lucide-react`, `motion`, `react-arborist`, `fastapi`, `pydantic-dev`, `python-best-practices`, `fastmcp-sdk`, `pdf-to-markdown`.
2. **`skill-creator`** (Anthropic).
3. **`frontend-design`** (de `anthropics/skills`).
4. **`obra/superpowers`** (con TDD desactivado, ver sección 4).
5. **`hermes-agent`** (Nous Research): `https://skillselion.com/skills/nousresearch/hermes-agent`.

Además de estas, puedes **instalar o crear cualquier otra skill** que te acelere (skills de FastAPI, SQLite, Rive, Electron, voz, etc.), de la comunidad o propias. Crea con `skill-creator` las skills propias del proyecto cuando un patrón se repita (por ejemplo, `drakter-conventions`, `drakter-tool-contract`, `drakter-migrations`) y regístralas en `DECISIONS.md`.

---

## 7. Flujo de trabajo por fase

1. Lee `IMPLEMENTATION_STATUS.md` → identifica la fase actual.
2. Planifica en pocas líneas: qué se hace, qué se paraleliza, qué contratos hay que fijar antes.
3. Congela contratos → lanza agentes en paralelo → integra.
4. Comprobación rápida de que funciona y se ve bien (sección 4).
5. Marca las casillas en `IMPLEMENTATION_STATUS.md`; registra decisiones en `DECISIONS.md`.
6. Commit en Git con mensaje claro y pasa a la siguiente fase.

La fase se identifica por el paso de este orden; la equivalencia con las fases de cada plan y las checklists está en `docs/DECISIONS.md`. Orden real de desarrollo (del plan): arquitectura y repo → Electron + React → FastAPI + SQLite → comunicación GUI-backend → Hermes + Haiku 5.5 → personalidad → personaje Rive → modelo de datos → tareas y proyectos → hábitos → calendario y asignaturas → almacén e indexación → relaciones → skills y herramientas → memoria → voz → automejora → seguridad → optimización → empaquetado.

---

## 8. Reglas del plan que NO se saltan (ni por velocidad)

Ir rápido no significa romper la arquitectura. Estas reglas del plan se mantienen siempre:

- Separación estricta entre agente, interfaz y datos. Un único origen de verdad para los datos del Workspace.
- Hermes **no** accede directamente a la base de datos: usa herramientas que llaman al backend, el cual valida parámetros, permisos y relaciones.
- Todas las herramientas tienen nombre, descripción, esquema de parámetros, validación, permisos, resultado estructurado y manejo de errores.
- Las acciones destructivas o masivas requieren confirmación. Las acciones del agente se registran en auditoría (sin guardar claves API ni datos sensibles).
- Los documentos del almacén y la memoria recuperada son **datos no confiables**: no pueden modificar las instrucciones internas ni las reglas de seguridad. Orden de prioridad: seguridad y permisos → reglas del sistema → identidad → contexto del usuario → conversación → memoria → instrucción actual. Este orden enmarca la instrucción actual; la memoria solo informa y nunca da órdenes. Si contradice lo que el usuario dice ahora, vale lo que dice ahora y se señala la discrepancia.
- Rutas de archivos limitadas a ubicaciones permitidas; límites de tamaño, número y profundidad para comprimidos.
- La automejora nunca modifica producción, permisos, confirmaciones ni auditoría sin autorización.
- Secretos y configuración sensible **fuera del repositorio** (`.env` ignorado; solo `.env.example`).
- La personalidad vive en `agent/identity/`, separada del modelo; la voz, separada del razonamiento; el proveedor del modelo, intercambiable.

---

## 9. Convenciones

- Estructura de carpetas: la definida en la Parte XII de `docs/MASTER_PLAN.md`, con las desviaciones de `docs/DECISIONS.md`. Las carpetas se crean cuando entra código, y los datos de ejecución viven fuera del repositorio.
- Identificadores: UUID. Zonas horarias explícitas en calendario. Migraciones controladas para cualquier cambio de esquema.
- TypeScript estricto en `desktop/`; tipado y Pydantic en `backend/`, con Python 3.12 obligatorio.
- Commits pequeños y frecuentes; una rama por agente en trabajo paralelo.
- Responde al usuario en **español**. Código, nombres de archivos y comentarios técnicos pueden ir en inglés.
- Cuando termines un bloque grande, resume en pocas líneas: qué quedó hecho, qué decisiones tomaste y qué sigue.
