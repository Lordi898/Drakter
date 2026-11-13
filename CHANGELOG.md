# Registro de cambios

Todos los cambios relevantes de Drakter se anotan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Aún no hay ninguna versión publicada.

## [Sin publicar]

### Cierre de la v1 (2026-11-13)

- Integradas todas las ramas `drakter/*` en `drakter/integracion`; cadena de publicación local `drakter/integracion` → `drakter/build` → `main`.
- Verificación módulo a módulo y marcado en `docs/IMPLEMENTATION_STATUS.md` solo de lo comprobado: Checklists 0, 2 (salvo permisos, ⚠️), 3 (Hermes con el stub, ⚠️ sin clave), 4 (personalidad, con ⚠️ en la consistencia sin clave), 5 (personaje provisional SVG, con ⚠️ en Rive y sincronización labial), 6, 7 (tareas y proyectos, con ⚠️ en el borrado), 8 (hábitos), 11 (relaciones, con ⚠️ en la visualización y las herramientas Hermes) y 12 (memoria, con ⚠️ en recuperación al turno, límites de contexto y memoria de trabajo) 13 (parámetros, permisos y errores de herramientas; Skills inertes ⚠️) y 15 (automejora, con ⚠️ en el flujo de aprobación).
- Pasada integrada: la app arranca con Electron como dueño del backend; `scripts/drakter-local.sh start|stop|status`; conexiones SQLite por petición sin `check_same_thread`; runner de Hermes con `-B`; rutas permitidas de Electron regeneradas desde el contrato.
- `docs/RUN_STATE.md` reescrito con el estado real, los bloqueos y cómo arrancar y parar la app; `README.md` «Estado real» actualizado.
- Memoria: los hábitos se clasifican como memoria procedimental antes que como perfil.
- Relaciones: el filtro por tipo de la pantalla se envía como `type`, el nombre que lee el backend.
- Identidad: el `SOUL.md` de Hermes compone los 14 archivos de `identity/`, `knowledge/` y `context/`; antes solo llegaban los 6 de `identity/`.
- Automejora: migración `0012_improvement_cycle.sql` con el esquema del servicio y rutas REST montadas.
- Evals: el arnés lee la identidad de sus tres carpetas y los esquemas de herramientas del árbol integrado.
- Voz: cierre mínimo en v1; la capa de voz se rediseñará sobre Pipecat.
- Agente: permiso `storage.write` concedido; las Skills citan solo herramientas registradas.
- Registrada en `docs/DECISIONS.md` la decisión de no cablear las confirmaciones desde backend base hasta reconciliarlas con hábitos y calendario.

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
