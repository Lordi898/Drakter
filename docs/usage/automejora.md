# Automejora

> **Estado:** el código de backend está en `drakter/integracion` (`2e05ba6`) (`backend/app/services/improvement_*.py`), y su router `/api/v1/improvement` se monta (`backend/app/api/improvement.py`) y está en las rutas permitidas de Electron, pero no hay pantalla en `desktop/src`: hoy solo se usa por API o desde el agente. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

Drakter puede preparar cambios sobre su propio código a partir de tus quejas o preferencias, pero no los aplica por su cuenta. Tú decides. Nada se fusiona solo.

## Qué propone

Una propuesta nace de un feedback (una incidencia o preferencia) que se clasifica en una de estas categorías: preferencia de comunicación, ajuste de contexto, arreglo de skill, mejora de procedimiento, recuperación de memoria, rendimiento, interfaz o corrección de error. Si cambia código, lleva un parche.

El agente dispone de estas herramientas: `record_improvement_feedback`, `create_improvement_proposal`, `list_improvement_proposals` y `get_improvement_proposal`. Ninguna aprueba ni aplica nada.

## Dónde se ven las propuestas

1. Por chat: pídele a Drakter que liste sus propuestas de mejora.
2. Por la API del backend: `GET /api/v1/improvement/proposals` (y `/proposals/{id}`), `GET /api/v1/improvement/changelog` y `GET /api/v1/improvement/reports/summary`.

No hay pantalla de propuestas en `desktop/` de esa rama. Las propuestas y el feedback viven en tu base SQLite, nunca en el repositorio.

## Ciclo de una propuesta

Estados: `draft`, `evaluating`, `evaluated_passed`, `evaluated_failed`, `evaluation_blocked`, `approved`, `applied`, `reverted`, `rejected`.

1. **Evaluación** (`POST .../proposals/{id}/evaluate`): el parche se prueba en un clon desechable, dentro de `bwrap`, sin red ni tu HOME. Si `bwrap` falta, el resultado es `blocked`; no hay modo degradado.
2. **Aprobación**: se pide con `POST .../approval-request`, que crea una confirmación ligada al SHA-256 exacto del parche. Se aprueba con `POST .../approve`. Si el parche toca rutas protegidas, la aprobación es elevada.
3. **Publicación** (`POST .../apply`): repite la validación y crea solo la rama Git `improvement/<id_propuesta>`. No hace merge ni push.
4. **Integración**: la revisas y la fusionas tú.

Para rechazar: `POST .../proposals/{id}/reject` con un motivo.
Para deshacer: `POST .../revert-request` y `.../revert`; solo borra la rama `improvement/<id>` si sigue en el commit esperado. Si ya está fusionada, responde `change_already_merged` y hay que revertirla a mano.

## Lo que nunca hace sin tu autorización

- No toca el checkout real: todo ocurre en un clon que se borra al terminar.
- No modifica producción, permisos, confirmaciones ni auditoría. La política de rutas deniega por defecto y protege, entre otras, `backend/app/core/`, `backend/app/database/`, `backend/migrations/`, `backend/app/tools/`, `contracts/`, `agent/identity/`, `agent/policies/`, `desktop/electron/`, `improvement/` y los archivos de dependencias. Si el agente incumple, el resultado es `failed` y definitivo.
- Solo puede proponer cambios en `desktop/src/`, `backend/app/services/`, `backend/app/api/`, `agent/skills/` y `docs/`.
- Un parche se trata siempre como no confiable, aunque lo haya propuesto el propio agente.

## Lo que pide confirmación

Aprobar y revertir exigen una confirmación emitida por el backend y decidida por ti en un diálogo nativo (`desktop/electron/main/approvals.ts`, ya en 2da8bef). Ver [seguridad-y-copias.md](seguridad-y-copias.md).

## Problemas frecuentes

- `blocked` al evaluar: falta `bwrap` o no arranca.
- Error 409 `improvement_repo_unconfigured` al aplicar o revertir: falta la variable `DRAKTER_IMPROVEMENT_REPO` (ruta absoluta del repositorio). En una instalación empaquetada no estará.
- Tras restaurar una copia de seguridad, las propuestas pendientes pueden quedar invalidadas (evento `invalidated_by_restore`).

## Pendiente

- **Pendiente:** pantalla para ver y aprobar propuestas; no existe ni en la rama ni en 2da8bef. NO COMPROBADO cómo se muestra la confirmación de aprobación de una propuesta.
- **Pendiente:** confirmar que el repositorio real queda configurado con `DRAKTER_IMPROVEMENT_REPO` en el uso diario.
