# Avisos de terceros

Este documento recoge el código y el contenido de terceros que **se distribuye dentro de este repositorio** y las licencias de las dependencias que se instalan aparte. Auditoría del 2026-11-13 sobre `main` (`eff16d1`).

La licencia del propio Drakter está pendiente de elegir (ver [README](README.md#licencia)). Nada de lo que hay aquí cambia la licencia de cada componente de terceros: cada uno conserva la suya.

**Cómo se ha verificado el origen:** comparando el hash de cada blob versionado con el árbol del repositorio de origen en el commit indicado (API de GitHub). «Idéntico» significa que todos los archivos coinciden byte a byte, salvo los que se indican como adaptados.

## 1. Contenido de terceros versionado en `.claude/`

Son instrucciones, agentes y skills para Claude Code que se usan en el desarrollo. No forman parte de la aplicación ni del paquete instalable.

| Ruta | Origen | Commit | Licencia | Texto de la licencia | Notas |
|---|---|---|---|---|---|
| `.claude/skills/{brainstorming, diagnosing-superpowers, dispatching-parallel-agents, executing-plans, finishing-a-development-branch, receiving-code-review, requesting-code-review, subagent-driven-development, systematic-debugging, using-git-worktrees, using-superpowers, verification-before-completion, writing-plans, writing-skills}/` | [obra/superpowers](https://github.com/obra/superpowers) | `22f0b463` | MIT, © 2025 Jesse Vincent | `LICENSE` en cada carpeta | **Adaptadas:** `superpowers:<x>` → `<x>` y TDD desactivado ([DECISIONS 2026-11-04](docs/DECISIONS.md#2026-11-04-instalación-de-las-skills-del-proyecto-en-claudeskills)) |
| `.claude/skills/hermes-agent/` | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) `skills/autonomous-ai-agents/hermes-agent` | `785c2e51` | MIT, © 2025 Nous Research | `.claude/skills/hermes-agent/LICENSE` | Idéntica |
| `.claude/skills/frontend-design/` | [anthropics/skills](https://github.com/anthropics/skills) `skills/frontend-design` | `ca45fc49` | Apache-2.0 | `.claude/skills/frontend-design/LICENSE.txt` | Idéntica |
| `.claude/skills/skill-creator/` | [sentient-agi/meta-skill-creator](https://github.com/sentient-agi/meta-skill-creator) `skill-creator/` | `02cb1db9` | Apache-2.0 | `.claude/skills/skill-creator/LICENSE` | Idéntica. El `LICENSE` se añade en esta auditoría (faltaba) |
| `.claude/skills/find-skills/` | [vercel-labs/skills](https://github.com/vercel-labs/skills) `skills/find-skills` | `b716f9dc` | MIT, © 2026 Vercel, Inc. | `.claude/skills/find-skills/LICENSE` | Idéntica. El `LICENSE` se añade en esta auditoría |
| `.claude/skills/build-orchestrator/` | [indiekitai/claude-orchestrator](https://github.com/indiekitai/claude-orchestrator) | `7a81c78` | MIT, © 2025 IndieKit.ai | `.claude/skills/build-orchestrator/LICENSE` | Idéntica |
| `.claude/commands/astraeus/` | [RchGrav/astraeus](https://github.com/RchGrav/astraeus) | `1ff17b0` | MIT, © 2025 Richard Graver | `.claude/commands/astraeus/LICENSE` | Idéntica |
| `.claude/agents/categories/01-…` a `10-research-analysis/` (186 archivos) | [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) `categories/` | `ed74d115` | MIT, © 2025 VoltAgent | [docs/third-party-licenses/VoltAgent-awesome-claude-code-subagents.txt](docs/third-party-licenses/VoltAgent-awesome-claude-code-subagents.txt) | Idénticos |
| `.claude/agents/categories/11-business/` a `17-specialization/` (36 archivos) y `.claude/agents/agent-organizer.md` | [lst97/claude-code-sub-agents](https://github.com/lst97/claude-code-sub-agents) `agents/` | `96f5a506` | MIT, © 2025 SIO TOU LAI | [docs/third-party-licenses/lst97-claude-code-sub-agents.txt](docs/third-party-licenses/lst97-claude-code-sub-agents.txt) | Idénticos |

Propio del proyecto (no es de terceros): `.claude/CLAUDE.md`, `.claude/agents/{contract-architect, docs-keeper, drakter-lider, drakter-orquestator, integrator, researcher}.md` y `.claude/skills/{agent-forge, drakter-toolkit}/`.

### Retirado del árbol: sin licencia redistribuible

| Contenido | Origen | Commit | Motivo | Cómo obtenerlo |
|---|---|---|---|---|
| 19 skills: `electron`, `electron-builder`, `electron-vite`, `vite`, `vitest`, `playwright-cli`, `typescript-best-practices`, `react-19`, `shadcn`, `radix-ui`, `lucide-react`, `react-arborist`, `tailwind-css`, `motion`, `fastapi`, `pydantic-dev`, `python-best-practices`, `fastmcp-sdk`, `pdf-to-markdown` | [LLMTooling/agent-skills](https://github.com/LLMTooling/agent-skills) | `f096e2bc` | El repositorio no declara licencia (ni en la raíz ni en las skills), así que no hay permiso para redistribuirlo | `scripts/install-agent-skills.sh` las descarga del commit fijado y las deja en `.claude/skills/`, ignoradas por Git |

⚠️ Estas 19 skills siguen en el **historial** de Git (commits anteriores a esta auditoría). Retirarlas también de ahí exige reescribir el historial; es decisión del propietario antes de hacer público el repositorio.

## 2. Código de terceros dentro de la aplicación

| Ruta | Origen | Licencia | Texto |
|---|---|---|---|
| `desktop/src/components/ui/*.tsx` | Componentes generados con [shadcn/ui](https://github.com/shadcn-ui/ui) y adaptados | MIT, © 2023 shadcn | [docs/third-party-licenses/shadcn-ui.txt](docs/third-party-licenses/shadcn-ui.txt) |

## 3. Dependencias (se instalan aparte, no se versionan)

### Escritorio (`desktop/package-lock.json`)

Paquetes que acaban en la aplicación (dependencias de producción, 86 en total):

| Licencia | Paquetes |
|---|---|
| MIT | 82 (entre ellos `react`, `react-dom`, `radix-ui`, `sonner`, `clsx`, `tailwind-merge`) |
| ISC | `lucide-react` |
| Apache-2.0 | `class-variance-authority` |
| 0BSD | `tslib` |
| OFL-1.1 | `@fontsource-variable/recursive` (fuente Recursive) |

Herramientas de build y desarrollo (no se empaquetan en el renderer): MIT, ISC, Apache-2.0, BSD-3-Clause y 0BSD, más **MPL-2.0** (`lightningcss`, por Tailwind) y **CC-BY-4.0** (`caniuse-lite`, datos de navegadores). Electron (MIT) incluye Chromium y sus licencias; `electron-builder` las copia al paquete.

### Backend (`backend/uv.lock`)

Todas permisivas: MIT, BSD-3-Clause, Apache-2.0, PSF-2.0 y MIT-0 (`fastapi`, `starlette`, `uvicorn`, `pydantic`, `httpx`, `mcp`, `pypdf`, `python-dotenv`, `platformdirs`, `websockets`, `cryptography`…), más **MPL-2.0** en `certifi` (se usa sin modificar).

### Agente y servicios opcionales

| Componente | Licencia | Cómo se usa |
|---|---|---|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.22.7 | MIT | Venv propio, instalado desde git; el backend lo lanza como proceso |
| Voz: `numpy`, `onnxruntime` | BSD-3-Clause, MIT | Dependencias de `voice/` |
| Voz (extras): `faster-whisper`, `kokoro-onnx` | MIT | Opcionales |
| Voz (extra): `openwakeword` | Apache-2.0 (código) | Opcional. ⚠️ Sus modelos preentrenados se publican con licencia no comercial (CC BY-NC-SA 4.0); revisar antes de distribuirlos |
| Piper TTS | GPL-3.0-or-later | Entorno aparte y solo como proceso externo, a propósito (`voice/tts/piper.py`) |
| OpenViking | AGPL-3.0 | Desactivado en v1; no se instala |

Los modelos (Whisper, Kokoro, Silero VAD, voces de Piper) no se versionan: se descargan aparte y cada uno tiene su licencia.

## Cómo mantener este documento

- Al copiar algo de terceros al repositorio: comprueba que su licencia permite redistribuirlo, conserva su `LICENSE` y añade una fila aquí con origen y commit. Si no tiene licencia, no lo versiones: añádelo a `scripts/install-agent-skills.sh` (o a un script similar) y a `.gitignore`.
- Al añadir una dependencia con licencia distinta de MIT, BSD, Apache-2.0 o ISC, anótala aquí.
