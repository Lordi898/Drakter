# Registro de cambios

Todos los cambios relevantes de Drakter se anotan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Aún no hay ninguna versión publicada.

## [Sin publicar]

### Añadido

- Documentos de planificación y control en `docs/`: `MASTER_PLAN.md`, `ROADMAP.md`, `IMPLEMENTATION_STATUS.md`, `DECISIONS.md`, `PLAN_DISEÑO_COMPLETO_DRAKTER.md` y `RUN_STATE.md`.
- Instrucciones del proyecto (`.claude/CLAUDE.md`) y configuración de agentes, skills y comandos en `.claude/`, incluidos `drakter-orquestator`, `drakter-lider`, `contract-architect`, `integrator`, `docs-keeper` y `researcher`.
- `build-orchestrator` y `astraeus` copiados como archivos normales en `.claude/`.
- `.gitignore` en la raíz.
- Carcasa de escritorio en `desktop/`, sin conexión al backend, y boceto del personaje en `desktop/design/character/`.
- Archivos de identidad en `agent/identity/`.
- `README.md`, `CHANGELOG.md` y `.env.example`.
- `docs/ARCHITECTURE.md` y `docs/CONVENTIONS.md`.
- `scripts/check-env.sh` y `scripts/dev.sh`.

### Cambiado

- Sincronizados los documentos de planificación con la copia de trabajo del usuario.

### Eliminado

- Agente `.claude/agents/orchestrator.md`, sustituido por `drakter-orquestator`.
- Copias `.docx` de los documentos de `docs/`.
