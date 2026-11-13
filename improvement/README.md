# Automejora controlada

Drakter puede preparar cambios sobre su propio código, pero no aplicarlos por su
cuenta. Un parche se trata siempre como no confiable, aunque lo proponga el
propio agente o lo haya inducido un documento.

## Ciclo

1. **Feedback y clasificación.** Una incidencia o preferencia se registra y se
   clasifica.
2. **Propuesta.** Se documenta la mejora, con su parche si cambia código.
3. **Evaluación.** `evaluate_patch` juzga el parche en un clon desechable.
4. **Aprobación.** `approval-request` responde 409 `confirmation_required` y la
   persona aprueba en `/api/v1/confirmations/{id}/approve` con la credencial
   `approver`: es el mismo `ActionService` y la misma caducidad (300 s) que el resto.
   La acción `approve_improvement_proposal` lleva el digest del parche y la
   evaluación; si la propuesta cambia antes de aprobar, termina en `conflict`.
   Revertir sigue el mismo camino (`revert-request`, `revert_improvement_proposal`).
   El agente no tiene estos permisos.
5. **Publicación.** `apply_patch` repite la validación con un clon nuevo y publica
   solo la rama `improvement/<proposal_id>`.
6. **Integración.** Una persona revisa y fusiona la rama. Drakter no fusiona nunca.

Implementación: `backend/app/services/improvement_lab.py` (laboratorio y Git) y
`backend/app/services/improvement_policy.py` (rutas).

## Garantías

- **El checkout real no se toca.** Todo ocurre en un clon nuevo bajo
  `experiments/<proposal_id>/<uuid>`, que se borra al terminar, también con error.
  Sobre el repositorio real solo se resuelve `HEAD` y se escribe una ref.
- **Git aislado.** Argv sin shell, entorno construido desde cero, sin hooks, sin
  configuración global ni de sistema, sin `fsmonitor`, sin `attributesFile` y sin
  filtros.
- **La verdad sale de Git.** Las rutas y los modos se leen del índice después de
  aplicar, no del texto del parche. Se rechazan enlaces simbólicos, submódulos,
  binarios y parches que no aplican.
- **Política en código.** Denegación por defecto: el agente solo llega a
  `desktop/src/`, `agent/skills/` y `docs/`, menos las rutas protegidas. Ningún
  Python del backend le queda abierto, porque correría en el proceso del backend y
  podría anular la política en memoria: todo `.py` bajo `backend/` y todo
  `__init__.py` están protegidos. Si incumple, el resultado es `failed` y
  definitivo. Una persona sí puede pasar, con aprobación elevada, y las rutas se
  informan en `protected_paths`. `system` sigue las reglas del agente.
- **Las comprobaciones no dependen del parche.** Se leen de
  `evaluations/default.json` en el commit base, nunca del árbol parcheado.
- **Sandbox obligatorio.** Se ejecutan dentro de `bwrap`, sobre una exportación de
  solo lectura y sin `.git`: sin red, sin el HOME real, sin `data_dir`, con
  entorno mínimo, tiempo límite, salida truncada a 8 KiB y límites de `prlimit` si
  está disponible. Si `bwrap` falta o no arranca, el resultado es `blocked`: no
  existe modo degradado.
- **Publicación mínima.** Solo `refs/heads/improvement/<id>`, con autor fijo y sin
  firma. Sin checkout, sin tocar `HEAD`, el índice ni otras ramas. Nunca merge ni
  push.
- **Reversión acotada.** `revert_change` solo borra esa ref, y solo si sigue en el
  commit esperado y hay prueba de que el cambio no ha entrado. Devuelve
  `change_already_merged` si el commit está en `HEAD` o en otra rama, o si `HEAD`,
  `main` o `master` tienen el mismo contenido con otro SHA (squash, rebase o
  cherry-pick, detectados con `git cherry` y aplicando el parche al revés en un
  índice temporal). Hay que revertirlo a mano. Si no se puede decidir, por ejemplo
  porque esos archivos cambiaron después, devuelve `revert_inconclusive` y la ref
  se queda.
- **Sin restos.** Al arrancar, `sweep_experiments` borra los experimentos huérfanos
  de una caída, sin seguir enlaces. Debe ejecutarse antes de la primera evaluación.

`apply_patch` no recibe el autor, así que quien lo llame debe pasar por `check_paths`
con el autor de la propuesta y tener un resultado `passed` y la aprobación para ese
mismo SHA-256.

## Qué vive dónde

| Dato | Lugar |
|---|---|
| Definición de evaluaciones, este README, `CHECKS.md` | `improvement/` en el repositorio |
| Política de rutas, laboratorio | `backend/app/services/` (protegidos) |
| Feedback y propuestas | SQLite del usuario, **nunca** en el repositorio |
| Experimentos temporales | `data_dir/improvement/experiments/` |
| Cambios publicados | Ramas `improvement/<proposal_id>` |

El feedback y las propuestas son datos del usuario. Por eso las carpetas
`feedback/`, `proposals/`, `experiments/`, `changelog/` y `reports/` de
`MASTER_PLAN.md` §23.1 no existen aquí.

## Configuración

`DRAKTER_IMPROVEMENT_REPO` es la ruta absoluta del repositorio. Sin ella, como en
una instalación empaquetada, `evaluate_patch` devuelve `blocked` y `apply_patch` y
`revert_change` devuelven el error 409 `improvement_repo_unconfigured`.

## Formato de las evaluaciones

```json
{"checks": [{"name": "compileall", "argv": ["{python}", "-I", "..."], "timeout_s": 120}]}
```

Cada argumento se pasa tal cual, sin shell. Dos argumentos exactos se sustituyen:
`{python}` por el intérprete base y `{diff}` por la ruta del diff real, que permite
la comprobación equivalente a `git diff --check` aunque el sandbox no tenga `.git`.
El árbol es de solo lectura, así que lo que se escriba va a `/tmp`.
