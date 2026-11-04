# DECISIONS

Decisiones técnicas, cambios de tecnología y motivos.

## [2026-11-04] Instalación de las skills del proyecto en `.claude/skills/`
- **Contexto:** `CLAUDE.md` y `drakter-toolkit` piden instalar las skills de terceros antes de escribir código, cada una en su carpeta.
- **Decisión:** copia local en `.claude/skills/<nombre>/`, con estos orígenes:
  - `LLMTooling/agent-skills@f096e2bc`: `electron`, `electron-vite`, `electron-builder`, `vite`, `vitest`, `typescript-best-practices`, `playwright-cli`. Son paquetes `.skill` (zip); se extraen y se normalizan a LF los `SKILL.md` que venían con CRLF.
  - `obra/superpowers@22f0b463` (MIT): 14 skills sueltas, sin `test-driven-development`. Se reescribe `superpowers:<x>` a `<x>` porque ya no van como plugin, se añade una nota de TDD desactivado a las 6 skills que lo mencionan y se quitan las exigencias explícitas de cargar TDD. No se instala el hook `SessionStart` del plugin.
  - `NousResearch/hermes-agent@785c2e51` (MIT): `skills/autonomous-ai-agents/hermes-agent`.
  - `frontend-design`: idéntica a `anthropics/skills@ca45fc49`.
  - `skill-creator`: se conserva la versión que ya estaba en el proyecto; no es la de `anthropics/skills`, que incluye evals y benchmarks.
  - `drakter-toolkit.md` pasa a `drakter-toolkit/SKILL.md`, la ruta que cita `CLAUDE.md`.
- **Alternativas descartadas:** instalar superpowers como plugin (quedaría fuera de `.claude/skills/` y activaría TDD); una única carpeta `superpowers/` (Claude Code no descubre skills anidadas); las 105 skills de LLMTooling (ver la entrada siguiente).
- **Motivo:** cada skill en su carpeta, versionada con el proyecto y sin TDD obligatorio.
- **Impacto:** `.claude/skills/`. Una actualización futura de superpowers debe repetir las adaptaciones. Los scrapers de `vite` y `electron-builder` y el `screenshot.js` de `playwright-cli` se revisaron por encima y no se han ejecutado.

## [2026-11-04] Marketplace de plugins `claude-market` añadido a mano (solo este proyecto)
- **Contexto:** `/plugin` no está disponible en este entorno, así que no se puede usar `/plugin marketplace add`.
- **Decisión:** registrar el marketplace en `.claude/settings.local.json` con `extraKnownMarketplaces` (fuente git `https://github.com/claude-market/marketplace.git`). Es un fichero local y no se versiona. No se ha instalado ningún plugin.
- **Revisión previa:** clonado en un directorio temporal de la sesión, commit `8cda5e18`. Contiene 3 plugins (`plugin-builder` 1.3.2, `specforge` 0.1.2, `specforge-backend-rust-axum` 1.0.0) hechos de Markdown: comandos, agentes y skills. No hay hooks, ni servidores MCP, ni llamadas de red en los manifiestos.
- **Alternativas descartadas:** `~/.claude/settings.json` (afectaría a todos los proyectos); `.claude/settings.json` (se versionaría y lo verían los demás).
- **Impacto:** `.claude/settings.local.json`. Para activar un plugin concreto hará falta añadir `enabledPlugins`, o instalarlo desde una sesión interactiva con `/plugin`.
- **Actualización:** se activa `plugin-builder@claude-market` en `enabledPlugins` de `.claude/settings.local.json`. `specforge` y `specforge-backend-rust-axum` quedan sin activar (el backend es Python + FastAPI).

## [2026-11-04] Selección de skills de LLMTooling en lugar de todas
- **Contexto:** `CLAUDE.md` pedía las 105 skills de `LLMTooling/agent-skills`, muchas ajenas a Drakter (Android, Wear OS, Minecraft, Angular…), y cada una añade su descripción al contexto de cada sesión.
- **Decisión:** instalar 19 skills de `LLMTooling/agent-skills@f096e2bc`: las 7 iniciales más `shadcn`, `tailwind-css`, `react-19`, `radix-ui`, `lucide-react`, `fastapi`, `pydantic-dev`, `python-best-practices`, `fastmcp-sdk`, `motion`, `react-arborist`, `pdf-to-markdown`. Se actualizan `CLAUDE.md` (sección 6) y `drakter-toolkit` a petición del usuario.
- **Alternativas descartadas:** `electron-store` (segundo origen de datos frente al Workspace), `pytest`/`jest`/`mypy` (política de pruebas mínima), `modern-frontend-design` (duplica `frontend-design`).
- **Motivo:** cubrir el stack real, sobre todo el backend, sin cargar skills que no se van a usar.
- **Impacto:** `.claude/skills/`, `.claude/CLAUDE.md`, `drakter-toolkit`. Los scripts incluidos (scrapers de documentación y `convert_pdf.py`) se revisaron por encima y no se han ejecutado; `pdf-to-markdown` necesita `pymupdf4llm` cuando se use.
