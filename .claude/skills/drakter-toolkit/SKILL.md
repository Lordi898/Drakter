---
name: drakter-toolkit
description: Mapa de todo el tooling del proyecto Drakter: skills, agentes, subagentes, sublíderes, comandos, plugins y sus trampas. Úsala antes de elegir herramientas, delegar, repartir una fase, planificar trabajo paralelo, lanzar drakter-lider, usar build-orchestrator o /batch, construir Electron/React/FastAPI, integrar Hermes u OpenViking, crear una skill o un agente, o instalar o clonar recursos de la comunidad. Actívala con frases como "qué agente uso", "qué skills hay", "lanza agentes", "reparte el trabajo", "instala esta skill". No la uses para el contenido del producto: eso está en docs/MASTER_PLAN.md.
---

# Drakter Toolkit

Inventario de lo instalado y cómo combinarlo. `CLAUDE.md` manda en caso de conflicto. Para crear agentes o redactar briefs, usa `agent-forge`.

## Flota

Claude Code admite hasta 3 niveles de subagentes bajo el hilo principal; en el último desaparece `Agent`.

| Nivel | Agente | Función |
|---|---|---|
| 0 | `drakter-orquestator` | Agente principal: planifica, crea, despliega, integra e informa |
| 1 | `drakter-lider` | Dirige un frente y despliega sus especialistas |
| 2 | Especialistas | Construyen una pieza |
| 3 | Ayudantes | Tareas hoja |

Agentes propios en `.claude/agents/`:

| Agente | Cuándo |
|---|---|
| `contract-architect` | Antes de paralelizar: BD, Pydantic, API, eventos, herramientas |
| `integrator` | Al cerrar un lote: fusionar y comprobar que arranca |
| `docs-keeper` | Mantener `IMPLEMENTATION_STATUS.md` y `DECISIONS.md` |
| `researcher` | Investigar en segundo plano con fuentes primarias |
| `agent-organizer` | Heredado; `drakter-orquestator` lo sustituye como coordinador |

### Catálogo de especialistas

`.claude/agents/categories/` tiene 202 archivos de comunidad en 17 categorías. Núcleo útil para Drakter:

| Área | Agentes |
|---|---|
| Escritorio y UI | `electron-pro`, `frontend-developer`, `react-specialist`, `typescript-pro`, `ui-designer`, `ux-designer`, `accessibility-tester` |
| Backend y datos | `python-pro`, `fastapi-developer`, `backend-developer`, `api-designer`, `websocket-engineer`, `database-optimizer`, `sql-pro` |
| Agente e IA | `ai-engineer`, `llm-architect`, `prompt-engineer`, `mcp-developer`, `nlp-engineer` |
| Calidad y seguridad | `surgeon-reviewer`, `code-reviewer`, `security-auditor`, `penetration-tester`, `architect-reviewer`, `debugger`, `performance-engineer`, `ui-ux-tester` |
| Operación | `git-workflow-manager`, `dependency-manager`, `build-engineer`, `documentation-engineer`, `research-analyst` |

Hay 29 nombres duplicados entre categorías (`debugger`, `python-pro`, `ai-engineer`, `electron-pro`, `typescript-pro`, `frontend-developer`…): solo se carga una copia, sin precedencia documentada. Si importa cuál, lee el archivo o crea un agente propio.

Algunos agentes declaran herramientas que aquí no existen (`mcp__context7*`, `sequential-thinking`). Si uno falla por eso, usa `general-purpose` con el rol en el brief.

## Skills por tarea

**Orquestación**
- `build-orchestrator`: skill principal para construir en lotes con contratos, worktrees, revisión y fusión. Admite `--roadmap <ruta>`.
- `agent-forge`: crear agentes y redactar briefs.
- `writing-plans`, `executing-plans`, `subagent-driven-development`: planificar y ejecutar.
- `dispatching-parallel-agents`, `using-git-worktrees`, `finishing-a-development-branch`: paralelo y cierre.
- `brainstorming`: explorar antes de diseñar.

**Calidad**
- `systematic-debugging`, `verification-before-completion`.
- `requesting-code-review`, `receiving-code-review`.

**Escritorio**: `electron`, `electron-vite`, `electron-builder`, `vite`, `react-19`, `typescript-best-practices`.

**Interfaz**: `frontend-design` (identidad visual, una vez y para toda la app), `shadcn`, `radix-ui`, `tailwind-css`, `lucide-react`, `motion`, `react-arborist`.

**Avatar animado**: concepto y continuidad con `character-design-continuity`; rig 2D/2.5D, poses, expresiones y visemas con `2d-character-rig-animation`; timing y easing con `animation-principles`; máquina de estados del `.riv` con `rive-interactive`; SVG con `svg-animation`; 3D con `three-best-practices`, `r3f-best-practices`, `threejs-shaders` y `threejs-animation` (morph targets y huesos); GSAP con `gsap-core`, `gsap-timeline`, `gsap-plugins` (MorphSVG, DrawSVG), `gsap-react` y `gsap-performance`; dirección de arte con `frontend-design`, `canvas-design` y `algorithmic-art`.

**Backend**: `fastapi`, `pydantic-dev`, `python-best-practices`, `fastmcp-sdk`.

**Agente y memoria**: `hermes-agent`. La memoria es la nativa de Hermes + OpenViking con capas L0/L1/L2 (`MASTER_PLAN.md` §10); Hindsight y Mem0 están descartados.

**Comprobación**: `playwright-cli` (ver la interfaz), `vitest` (solo lo imprescindible).

**Documentos**: `pdf-to-markdown` (requiere `pymupdf4llm`).

**Skills y recursos**: `skill-creator`, `writing-skills`, `find-skills`.

**Superpowers internas**: `using-superpowers`, `diagnosing-superpowers`.

## Comandos y plugins

| Recurso | Uso |
|---|---|
| `/effort high`, `/effort ultracode on` | Fijar esfuerzo y orquestación por sesión |
| `/workflows` | Ver y controlar flujos en curso |
| `/batch <instrucción>` | Descomponer en 5-30 unidades. Entra en plan mode y pide aprobación; sus workers hacen push y abren PR salvo que se indique otra cosa |
| `/astraeus` | Comando de terceros. Pide `curl \| sh` y `claude mcp add`: léelo antes de usarlo |
| `plugin-builder@claude-market` | Crear plugins (`/plugin-builder:init`, `add`, `edit`, `validate`) |

`specforge` y `specforge-backend-rust-axum` están en el marketplace `claude-market`, sin activar.

## Reparto por tipo de trabajo

| Trabajo | Combinación |
|---|---|
| Fase completa | `build-orchestrator` + `writing-plans` → `contract-architect` → un `drakter-lider` por frente → `integrator` → revisión |
| Módulo del Workspace | `drakter-lider` con backend, UI y herramientas en paralelo |
| Pantalla | `ui-designer` o `frontend-developer` + `frontend-design`, `shadcn`, `playwright-cli` |
| Herramienta de Hermes | `mcp-developer` o `ai-engineer` + `hermes-agent` + `fastmcp-sdk` |
| Fallo difícil | `debugger` + `systematic-debugging` |
| Seguridad | `security-auditor` + `penetration-tester` |
| Revisar un lote | `surgeon-reviewer`, `security-auditor` y `architect-reviewer`, distintos de los autores |

Reutiliza un rol del catálogo si existe. Un rol puntual va con `general-purpose`; uno que se repite 3 o más veces merece archivo propio en `.claude/agents/`.

## Adaptaciones al proyecto

- **TDD desactivado.** `CLAUDE.md` §4 anula los pasos de test previo que aún aparecen en `writing-plans` y `executing-plans`. El paso se sustituye por una comprobación real.
- **Revisión en `build-orchestrator`.** Pide Codex o Pi, que no están instalados. Usa revisores independientes y deja rastro de los hallazgos, porque esa skill detiene la orquestación si faltan dos revisiones.
- **Concurrencia en `build-orchestrator`.** Sus topes de 2-3 agentes son un valor por defecto: paraleliza más solo con conjuntos de escritura disjuntos.

## Trampas conocidas

- **Base de los worktrees:** salen de `origin/main` salvo con `"worktree": {"baseRef": "head"}`. Solo ven lo commiteado: haz commit antes de cada lote.
- **Agentes de `Workflow`:** los que no llevan `agentType` no pueden lanzar subagentes. Para anidar, lanza `drakter-lider` desde el hilo principal con `Agent`.
- **Agentes nuevos:** la lista se carga al arrancar la sesión. Un agente añadido después da `Agent type not found` hasta abrir una sesión nueva.
- **Dentro de un worktree** solo carga su propia `.claude/skills`. Lo sin commitear no existe allí.
- **Skills de LLMTooling no versionadas:** `electron`, `electron-vite`, `electron-builder`, `vite`, `vitest`, `playwright-cli`, `typescript-best-practices`, `react-19`, `shadcn`, `radix-ui`, `tailwind-css`, `lucide-react`, `motion`, `react-arborist`, `fastapi`, `pydantic-dev`, `python-best-practices`, `fastmcp-sdk` y `pdf-to-markdown` no tienen licencia redistribuible y están en `.gitignore`. En el checkout principal y en cada worktree nuevo, ejecuta `scripts/install-agent-skills.sh` antes de usarlas.
- **Máquina:** 8 CPU y 14 GB de RAM; limita instalaciones y compilaciones simultáneas.
- **Coste de contexto:** el catálogo completo se anuncia en cada sesión. Recortarlo reduce ese coste.

## Instalar o añadir recursos

Instalar de la comunidad está permitido. Antes de ejecutar scripts ajenos, lee en un minuto qué hacen y a qué red acceden, fija versión o commit y registra origen en `docs/DECISIONS.md`. Una actualización de superpowers debe repetir las adaptaciones anotadas allí.

Candidatas a skill propia si el patrón se repite: `drakter-conventions`, `drakter-tool-contract`, `drakter-migrations`.
