# Registro de cambios

Todos los cambios relevantes de Drakter se anotan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Aún no hay ninguna versión publicada.

## [Sin publicar]

### Cierre de la v1 (2026-11-13)

- Integradas todas las ramas `drakter/*` en `drakter/integracion`; cadena de publicación local `drakter/integracion` → `drakter/build` → `main`.
- Verificación módulo a módulo y marcado en `docs/IMPLEMENTATION_STATUS.md` solo de lo comprobado: Checklists 0, 2, 3 (Hermes, con la conversación completa comprobada con Claude Haiku 5.5 real), 4 (personalidad, con la consistencia comprobada con el modelo real), 5 (personaje provisional SVG, con ⚠️ en Rive y sincronización labial), 6, 7 (tareas y proyectos), 8 (hábitos), 9 (calendario y asignaturas, con ⚠️ en las vistas diaria y mensual), 10 (almacén), 11 (relaciones, con ⚠️ en la visualización y las herramientas Hermes) y 12 (memoria, con ⚠️ en recuperación al turno, límites de contexto y memoria de trabajo), 13 (parámetros, permisos y errores de herramientas; Skills inertes ⚠️) 14 (voz como proceso aislado, ⚠️ sin conectar a la app) 15 (automejora, con ⚠️ en el flujo de aprobación) 16 (seguridad, con revisión adversarial) y 17 (documentación de instalación; instalador y mediciones con ⚠️).
- Pasada integrada: la app arranca con Electron como dueño del backend; `scripts/drakter-local.sh start|stop|status`; conexiones SQLite por petición sin `check_same_thread`; runner de Hermes con `-B`; rutas permitidas de Electron regeneradas desde el contrato.
- `scripts/drakter-local.sh stop` vuelve a parar la app (el pid se tomaba antes del fork de `setsid`).
- `.env.example` solo lista las variables que lee el código y las líneas vacías se ignoran en todos los ajustes; la API de copias se monta con borrado por `ActionService`; los modelos del contrato se alinean con la API; las 4 herramientas de automejora entran en el catálogo de herramientas.
- `docs/RUN_STATE.md` reescrito con el estado real, los bloqueos y cómo arrancar y parar la app; `README.md` «Estado real» actualizado.
- Memoria: los hábitos se clasifican como memoria procedimental antes que como perfil.
- Relaciones: el filtro por tipo de la pantalla se envía como `type`, el nombre que lee el backend.
- Identidad: el `SOUL.md` de Hermes compone los 14 archivos de `identity/`, `knowledge/` y `context/`; antes solo llegaban los 6 de `identity/`.
- Automejora: migración `0013_improvement_cycle.sql` con el esquema del servicio y rutas REST montadas.
- Evals: el arnés lee la identidad de sus tres carpetas y los esquemas de herramientas del árbol integrado.
- Voz: cierre mínimo en v1; la capa de voz se rediseñará sobre Pipecat.
- Calendario: acepta `:00` final en la fecha-hora local; los recursos de una asignatura se leen de las relaciones.
- Hoy se recarga cuando el servicio local conecta (antes podía quedarse en «no conectado» al abrir la app).
- Búsqueda global: una sola ruta `GET /api/v1/search` que indexa tareas, proyectos, hábitos, eventos y asignaturas.
- Almacén: arreglos de integración (`runtime_dir`, `untrusted_envelope`, mapas de auditoría) y pypdf en `uv.lock`.
- Agente: permiso `storage.write` concedido; las Skills citan solo herramientas registradas.
- Empaquetado: el backend congelado incluye todos los módulos de `app` (antes respondía 404) y el `.deb` lleva `homepage`; guías de instalación y uso alineadas con la integración.
- Seguridad: revisión adversarial con banco red-team; auditoría de rechazos, redactor de logs, regla única de caracteres invisibles y restauración sin `-wal` huérfano.
- Seguridad cableada en el arranque: confirmaciones con un único camino (`ActionService`, 300 s) para tareas, proyectos y calendario; migración `0012_confirmation_hardening.sql`.
- Registradas en `docs/DECISIONS.md` las decisiones del cierre (2026-11-13).

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
