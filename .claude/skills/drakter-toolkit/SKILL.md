---
name: drakter-toolkit
description: Registro e instrucciones de las skills y agentes del proyecto Drakter. Úsala SIEMPRE al empezar el proyecto (Fase 0) para instalar las skills necesarias, y cada vez que vayas a construir Electron/React/Vite, interfaz con frontend-design, integrar Hermes, crear skills o subagentes nuevos, planificar trabajo en paralelo o instalar/clonar skills y agentes de la comunidad. Úsala aunque el usuario no mencione "skills" explícitamente: en cualquier tarea de Drakter que implique elegir herramientas, delegar en subagentes o instalar recursos externos.
---

# Drakter Toolkit

Skills y agentes del proyecto Drakter, cómo instalarlos y cuándo usar cada uno.
Complementa a `CLAUDE.md` (que manda en caso de conflicto): velocidad primero, pruebas mínimas, agentes sin límite.

## 1. Skills del proyecto

| # | Skill | Origen | Para qué se usa en Drakter |
|---|---|---|---|
| 1 | Selección de `LLMTooling/agent-skills` (lista en `CLAUDE.md`, sección 6) | https://github.com/LLMTooling/agent-skills | Electron, Vite, TypeScript, React, shadcn/ui, Tailwind, FastAPI, Pydantic, MCP, Vitest, Playwright CLI, etc. (Fases 1, 6–9, 14) |
| 2 | `skill-creator` | `anthropics/skills` | Crear skills propias del proyecto y mejorarlas |
| 3 | `frontend-design` | `anthropics/skills` | Diseño de la GUI: sidebar, pestañas, chat, paneles (Fases 1, 4, 6–9) |
| 4 | `superpowers` | `obra/superpowers` | Brainstorming, planes, ejecución paralela, depuración. **Sin TDD** |
| 5 | `hermes-agent` | https://skillselion.com/skills/nousresearch/hermes-agent (repo `nousresearch/hermes-agent`) | Configurar y operar Hermes, memoria, skills de Hermes (Fases 2, 10, 11) |

## 2. Instalación (hazla en la Fase 0, en paralelo)

Lanza un subagente por skill. Si un comando falla, **no te detengas**: usa el método alternativo (clonar y copiar) y anota en `DECISIONS.md` lo que hiciste. Verifica siempre que cada skill queda en `.claude/skills/` (proyecto) o `~/.claude/skills/` (global) y que aparece disponible.

**1. LLMTooling/agent-skills (todas):**
```bash
git clone --depth=1 https://github.com/LLMTooling/agent-skills /tmp/llmtooling-skills
# Las skills son paquetes zip en skills/<categoría>/<nombre>.skill.
# Extrae solo las de la lista de CLAUDE.md (sección 6), cada una en .claude/skills/<name del frontmatter>/.
# Normaliza a LF su SKILL.md: varios vienen con CRLF.
unzip -q /tmp/llmtooling-skills/skills/electron/electron.skill -d .claude/skills/electron
```

**2 y 3. skill-creator y frontend-design (anthropics/skills):**
```bash
npx skills add anthropics/skills --skill skill-creator
npx skills add anthropics/skills --skill frontend-design
# Alternativa: clonar https://github.com/anthropics/skills y copiar skills/skill-creator y skills/frontend-design a .claude/skills/
```

**4. superpowers:**
```bash
# Dentro de Claude Code:
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@claude-plugins-official
# Alternativa: npx skills add obra/superpowers
```

**5. hermes-agent:**
```bash
npx skills add https://github.com/nousresearch/hermes-agent --skill hermes-agent
# Alternativa: clonar https://github.com/NousResearch/hermes-agent y copiar su carpeta de skill a .claude/skills/
```

Cuando termine la instalación, deja constancia en `DECISIONS.md` (qué se instaló, de dónde, versión o commit) y marca la casilla correspondiente en `IMPLEMENTATION_STATUS.md`.

## 3. Cómo usar cada skill en este proyecto

- **LLMTooling (electron, electron-vite, electron-builder, vite, vitest, typescript-best-practices, playwright-cli):** consúltalas al crear el proyecto Electron + React + TypeScript, la comunicación main/preload/renderer y el empaquetado. De `vitest` y `playwright-cli` usa solo lo imprescindible: la política de pruebas es mínima (ver `CLAUDE.md`, sección 4). `playwright-cli` sirve también para comprobar visualmente que la UI se ve bien.
- **frontend-design:** úsala para cada pantalla principal (Cara de Drakter, Tareas, Proyectos, Calendario, Almacén, Asignaturas, Relaciones, Configuración). Define una vez la identidad visual (paleta, tipografía, componentes shadcn/ui) y reutilízala; no rediseñes pantalla por pantalla.
- **superpowers:** aprovecha brainstorming y planificación para cada fase, y la ejecución con subagentes en paralelo. **Desactiva el TDD obligatorio**: en este proyecto no se escribe test antes del código. Si la skill lo exige, indica que `CLAUDE.md` lo anula.
- **hermes-agent:** úsala para instalar Hermes, configurar Claude Haiku 5.5 por variables de entorno, ver sus opciones de proveedor de memoria y definir las Skills propias de Drakter en el formato de Hermes. Recuerda el riesgo conocido: Hermes admite un solo proveedor de memoria externo activo; el Memory Adapter debe llamar a OpenViking, Hindsight y Mem0 directamente.
- **skill-creator:** cuando un patrón se repita en 3 o más sitios, conviértelo en skill propia. Candidatas: `drakter-conventions` (capas, nombres, "todo pasa por servicios"), `drakter-tool-contract` (esquema, validación, permisos, resultado estructurado y auditoría de cada herramienta de Hermes), `drakter-migrations` (reglas SQLite, UUID, migraciones). Hazlas rápido, sin ciclos de evaluación ni benchmarks salvo que el usuario los pida.

## 4. Agentes y subagentes

**No hay límite.** Usa todos los que quieras, en paralelo, para terminar lo antes posible con el nivel y la corrección intactos.

### Fuentes permitidas
- **Internos:** los subagentes de Claude Code (herramienta Task / agentes en `.claude/agents/`).
- **Comunidad / externos:** cualquier agente o subagente de GitHub o de registros de la comunidad. Puedes **instalarlos, copiarlos o clonarlos** y usarlos tal cual o adaptarlos. Búscalos tú mismo en internet cuando te falte uno.
- **Propios:** créalos en `.claude/agents/<nombre>.md` (frontmatter con `name`, `description`, `tools` y el prompt de sistema). Hazlos específicos y con una sola responsabilidad.

### Agentes propios sugeridos (créalos si te ayudan)
| Agente | Responsabilidad |
|---|---|
| `contract-architect` | Fija esquema de BD, modelos Pydantic, rutas API, eventos WS y firmas de herramientas Hermes antes de paralelizar |
| `backend-module-builder` | Repositorio + servicio + API de un módulo (tareas, hábitos, calendario…) |
| `ui-module-builder` | Pantalla React de un módulo siguiendo `frontend-design` |
| `hermes-tool-writer` | Herramientas y skills de Hermes de un módulo, con permisos y auditoría |
| `voice-integrator` | openWakeWord, Silero VAD, Faster-Whisper, Kokoro, Piper |
| `researcher` | Busca documentación, repos y skills/agentes de la comunidad mientras otros construyen |
| `docs-keeper` | Mantiene `IMPLEMENTATION_STATUS.md` y `DECISIONS.md` sin frenar al resto |
| `integrator` | Une ramas, resuelve conflictos y comprueba que todo arranca junto |

### Patrón de paralelización recomendado
1. `contract-architect` congela los contratos del módulo o fase.
2. Se lanzan **en paralelo** tantos `backend-module-builder`, `ui-module-builder` y `hermes-tool-writer` como módulos independientes haya (p. ej., en la Fase 7: hábitos, calendario y asignaturas a la vez).
3. Cada agente trabaja en su propia rama o `git worktree` y sobre archivos que solo él toca.
4. `researcher` y `docs-keeper` trabajan de fondo durante todo el proceso.
5. `integrator` fusiona y hace la comprobación rápida de que funciona y se ve bien.

### Higiene al instalar recursos de terceros
Permitido y fomentado. Antes de ejecutar scripts de un skill o agente externo, revisa en un minuto qué comandos corre y a qué red accede; fija versión o commit si puedes; registra origen y versión en `DECISIONS.md`. No es una auditoría, solo una lectura rápida.

## 5. Plantilla para crear un subagente propio

```markdown
---
name: backend-module-builder
description: Construye repositorio, servicio y endpoints FastAPI de un módulo del Workspace de Drakter. Úsalo para tareas, proyectos, hábitos, calendario, asignaturas, almacén o relaciones.
tools: Read, Write, Edit, Bash, Grep, Glob
---

Eres un ingeniero backend de Drakter. Sigues MASTER_PLAN.md y CLAUDE.md.
Entradas: módulo a construir, contrato (modelos y rutas) ya fijado.
Reglas: solo editas archivos de tu módulo; todo pasa por servicios; UUID; validación Pydantic;
registro en auditoría; sin tests exhaustivos (comprobación rápida de que funciona).
Salida: módulo funcionando + resumen de 5 líneas + decisiones para DECISIONS.md.
```

## 6. Resumen de prioridades

1. `CLAUDE.md` manda sobre cualquier skill en caso de conflicto.
2. Rápido y correcto: se avanza en cuanto funciona y se ve bien.
3. Pruebas mínimas; TDD desactivado.
4. Agentes y skills ilimitados, propios o de la comunidad.
5. Todo cambio relevante queda en `DECISIONS.md`; todo avance, en `IMPLEMENTATION_STATUS.md`.
