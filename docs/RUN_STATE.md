# RUN_STATE — Estado de la ejecución de Drakter

Foto operativa de la construcción. El detalle por tareas está en `IMPLEMENTATION_STATUS.md` y los motivos, en `DECISIONS.md`.

## Estado actual (2026-11-04)

- **Rama de trabajo:** `drakter/build` (en `488b83d` al escribir esto). `main` no se ha tocado. Cada frente trabaja en su rama `drakter/*`.
- **Fase:** construcción en paralelo e integración en curso. `drakter/build` ya contiene contratos, shell de escritorio, identidad, memoria y `dev-stub`, entre otros; `drakter/agente-hermes` y `drakter/electron-host` no estaban fusionadas. Sin pasada integrada, no se ha marcado ninguna casilla.
- **Documentos:** los `.md` de `docs/` son la fuente de verdad; los `.docx` se han eliminado.
- **Tooling versionado:** agentes, skills, `build-orchestrator` y `astraeus` llegan completos a clones y worktrees.
- **Configuración local:** `worktree.baseRef = head` y `workflowSizeGuideline = unrestricted` en `.claude/settings.local.json`. Ese archivo no se versiona, así que hay que fijarlo en cada checkout nuevo.
- **Anidación:** `drakter-lider` lanza subagentes (dos niveles comprobados en sesión nueva).
- **Identidad Git:** esta máquina no tiene `user.name` ni `user.email`. Los commits usan `git -c user.name=... -c user.email=...` con la identidad de los commits existentes.
- **Secretos:** `~/.config/drakter/.env` pertenece al usuario y queda fuera del repositorio.

## Copias de seguridad

Historial Git de los repos que estaban anidados en el checkout del usuario:

- `~/.drakter-backup/build-orchestrator.git` (`7a81c78`)
- `~/.drakter-backup/astraeus.git` (`1ff17b0`)

## Bloqueos y desajustes abiertos

- **Sin clave de API:** nada se ha probado con el modelo real.
- **Identidad:** el reparto vigente es 6 + 4 + 4 archivos. `drakter/build` sigue con 22 en `agent/` hasta fusionar `f13204a`, de `drakter/identidad-personaje`.
- **OpenViking:** el backend recupera los recuerdos y, sin plugin en Hermes, el `memory.provider` de `MASTER_PLAN` §10 ya no aplica tal cual. Falta decidir cómo entra OpenViking.
- **Confirmaciones:** caducidad de 15 minutos en `habits_calendar_support.py` frente a 300 s decididos.
- **Hermes:** la decisión es runner propio sin gateway, y el código commiteado aún lanza el gateway.
- **Electron:** falta `options` en `call`.

El detalle de cada uno está en `DECISIONS.md`.

## Siguiente paso

1. Leer `IMPLEMENTATION_STATUS.md` y las últimas entradas de `DECISIONS.md`.
2. Retomar por la primera tarea pendiente según el orden de desarrollo de `CLAUDE.md` §7.
