# RUN_STATE — Estado de la ejecución de Drakter

Foto operativa de la construcción. El detalle por tareas está en `IMPLEMENTATION_STATUS.md` y los motivos, en `DECISIONS.md`.

## Estado actual (2026-11-04)

- **Rama de trabajo:** `drakter/build` (en `4a84a5d` al escribir esto). `main` no se ha tocado. Cada frente trabaja en su rama `drakter/*`.
- **Fase:** construcción en paralelo e integración en curso. `drakter/build` ya contiene contratos, shell de escritorio, identidad, memoria y `dev-stub`, entre otros; `drakter/agente-hermes` no estaba fusionada del todo. Sin pasada integrada, no se ha marcado ninguna casilla.
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
- **OpenViking (U-1):** desactivado en v1, con memoria SQLite + FTS5. Es una desviación de una decisión del usuario y **falta que la confirme**.
- **Confirmaciones:** caducidad de 15 minutos en `habits_calendar_support.py` frente a 300 s decididos.
- **Hermes:** el runner está en `drakter/agente-hermes` (`866ad9d`), aún sin fusionar en `drakter/build`. `contracts/README.md` §1 sigue citando `API_SERVER_KEY`.

El detalle de cada uno está en `DECISIONS.md`.

## Siguiente paso

1. Leer `IMPLEMENTATION_STATUS.md` y las últimas entradas de `DECISIONS.md`.
2. Retomar por la primera tarea pendiente según el orden de desarrollo de `CLAUDE.md` §7.
