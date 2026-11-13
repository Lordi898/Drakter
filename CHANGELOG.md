# Registro de cambios

Todos los cambios relevantes de Drakter se anotan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Aún no hay ninguna versión publicada.

## [Sin publicar]

### Cierre de la v1 (2026-11-13)

**Resultado:** en las Checklists 0–17, 260 de 295 casillas en `[x]` (29 con una reserva ⚠️), 25 sin marcar con ⚠️ y 10 sin código. Pasada integrada final `scripts/verify-all.sh`: 44/44 sobre `183cc25`. Banco red-team final: 169 BLOCKED / 12 BREACH / 19 N/A / 0 ERROR. Detalle en `docs/IMPLEMENTATION_STATUS.md` y `docs/RUN_STATE.md`.

#### Integración y arranque
- Las 22 ramas `drakter/*` integradas en `drakter/integracion`; cadena local `drakter/integracion` → `drakter/build` → `main` por fast-forward, sin push; respaldo de `main` en `respaldo/main-local-2026-11-13`.
- Electron es dueño del backend (handshake por stdin, puerto efímero); `scripts/drakter-local.sh start [anthropic]|stop|status` (y `stop` vuelve a parar la app); conexiones SQLite por petición sin `check_same_thread`; runner de Hermes con `-B`; Hoy se recarga cuando el servicio local conecta.
- `.env.example` lista solo las variables que lee el código y las líneas vacías se ignoran en todos los ajustes.
- Empaquetado: el backend congelado incluye todos los módulos de `app` (antes respondía 404 en todas las rutas) y el `.deb` lleva `homepage`.

#### Confirmaciones y seguridad
- Seguridad cableada en el arranque y un único camino de confirmación (`ActionService`, 300 s) para tareas, proyectos, calendario, asignaturas, relaciones, almacén, copias, automejora y memoria; las acciones del agente que lo requieren pasan por `BackendToolGate`.
- `0012_confirmation_hardening.sql`: las confirmaciones nacen pendientes y no se reescriben al cerrarse.
- Revisión adversarial: auditoría de rechazos, redactor de logs, regla única de caracteres invisibles, restauración sin `-wal` huérfano; lo que propone el agente en una sesión contaminada entra como de terceros y la conversación también marca la contaminación.
- La GUI no puede aplicar ni revertir mejoras; `ALLOWED_ROUTES` se regenera desde el contrato.

#### Agente y memoria
- Hermes con Claude Haiku 5.5 real: conversación completa, selección y encadenado de herramientas y consistencia de personalidad comprobados.
- El `SOUL.md` compone los 14 archivos de `identity/`, `knowledge/` y `context/` (antes solo llegaban los 6 de `identity/`).
- Cada turno de Hermes pasa por `build_context`: recuperación de memoria cercada como dato no confiable, nunca en el `system`.
- Memoria: los hábitos se clasifican como procedimentales; olvidar y aprobar recuerdos desde la GUI pasa por confirmación.
- Catálogo de herramientas sin deriva (automejora dentro, `get_related_items` no confiable); permiso `storage.write` para el agente; las Skills citan solo herramientas registradas (Hermes no las carga: `skill_manage` desactivado).
- Evals: el arnés lee la identidad de sus tres carpetas y los esquemas del árbol integrado.

#### Módulos
- Búsqueda global con una sola ruta `GET /api/v1/search`, que indexa tareas, proyectos, hábitos, eventos y asignaturas; Ctrl+K montado.
- Calendario: acepta `:00` final en la fecha-hora local; los recursos de una asignatura se leen de las relaciones.
- Relaciones: el filtro por tipo de la pantalla se envía como `type`.
- Almacén: arreglos de integración y pypdf en `uv.lock`.
- Automejora: esquema del servicio en `0013_improvement_cycle.sql`, rutas REST montadas, aprobación y reversión por `ActionService`, recuperación de evaluaciones cortadas al arrancar.
- Copias: API montada con borrado por `ActionService`; los modelos del contrato se alinean con la API.
- Voz: verificada como proceso aislado y congelada; se rediseñará sobre Pipecat.

#### Documentación
- `docs/IMPLEMENTATION_STATUS.md` con las casillas verificadas y un resumen de cierre; `docs/RUN_STATE.md` con el estado de cierre, los bloqueos y cómo arrancar y parar; `README.md` «Estado real»; guías de `docs/installation/` y `docs/usage/` alineadas con la integración.
- Decisiones del cierre registradas en `docs/DECISIONS.md` (2026-11-13).

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
