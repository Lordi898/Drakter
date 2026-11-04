# RUN_STATE — Estado de la ejecución de Drakter

Foto operativa de la construcción. El detalle por tareas está en `IMPLEMENTATION_STATUS.md` y los motivos, en `DECISIONS.md`.

## Estado actual (2026-11-04)

- **Rama de trabajo:** `drakter/build`. `main` no se ha tocado.
- **Fase:** preparación terminada. No se ha empezado a construir producto.
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

## Siguiente paso

1. Leer `IMPLEMENTATION_STATUS.md` y las últimas entradas de `DECISIONS.md`.
2. Retomar por la primera tarea pendiente según el orden de desarrollo de `CLAUDE.md` §7.
