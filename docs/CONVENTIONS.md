# Convenciones de Drakter

Recoge lo que `CLAUDE.md` §9 exige y lo que ya se practica en las ramas. Cuando algo es norma sin uso real todavía, se indica. Foto del 2026-11-04: `desktop/` ya está en `drakter/build`; `backend/` sigue en `drakter/backend-base`, sin fusionar.

## Ramas y commits

- Rama de integración: `drakter/build`. `main` no se toca.
- Una rama por zona o agente, con la forma `drakter/<zona>`: `drakter/backend-base`, `drakter/desktop-shell`, `drakter/identidad-personaje`.
- Trabajo paralelo en un `git worktree` por rama. Dos agentes no editan el mismo archivo.
- Commits pequeños y convencionales, en inglés y en imperativo: `tipo(zona): descripción`. La zona es opcional.
- Tipos usados: `feat`, `chore`, `docs`. Zonas usadas: `backend`, `desktop`, `identity`.
- Ejemplo real: `feat(backend): add secure local FastAPI base with SQLite migrations`.

## Idioma

- Respuestas al usuario: español. Documentos del proyecto e interfaz: también en español.
- Código, nombres de archivo y comentarios técnicos pueden ir en inglés. Hoy conviven comentarios en inglés y en español.

## Documentos de control

Están en `docs/`, no en la raíz: `MASTER_PLAN.md`, `IMPLEMENTATION_STATUS.md`, `DECISIONS.md` y `RUN_STATE.md`. Decisión no trivial: entrada en `DECISIONS.md` con el formato de `CLAUDE.md` §2.

## Estructura de carpetas

La define `MASTER_PLAN.md`, Parte XII. Hoy solo existe una parte de ella; ver la tabla de componentes de `ARCHITECTURE.md`.

## Datos

- **Identificadores:** UUID. Sin entidades de dominio todavía; el único uso real es `request_id` (`uuid4`).
- **Fechas:** UTC en ISO 8601 en lo que ya existe (`schema_version.applied_at`, campo `ts` de los logs). El calendario llevará zonas horarias explícitas; aún no existe.
- **Migraciones:** todo cambio de esquema pasa por una migración.

## Migraciones SQLite

- Archivos `NNNN_nombre.sql` en `backend/migrations/`, numerados de 1 en 1 sin huecos. El nombre admite `[A-Za-z0-9_-]`.
- Una migración aplicada no se edita: su checksum SHA-256 queda en `schema_version` y un cambio bloquea el arranque.
- Solo se admiten `ALTER`, `ANALYZE`, `CREATE`, `DELETE`, `DROP`, `INSERT`, `REINDEX`, `REPLACE`, `UPDATE` y `WITH`. Quedan fuera `PRAGMA`, `ATTACH` y el control de transacciones.
- `python -m app` migra al arrancar. Si hay datos y migraciones pendientes, crea y verifica antes una copia; todo se aplica en una transacción.
- Uso manual, desde `backend/`: `python -m app.database.cli status|migrate|backup|restore <archivo>`.

## TypeScript

- Modo estricto en `desktop/tsconfig.web.json` y `desktop/tsconfig.node.json`: `strict`, `noUncheckedIndexedAccess`, `noImplicitOverride`, `noFallthroughCasesInSwitch`.
- Comprobación: `npm run typecheck`. No hay linter configurado.
- Versiones exactas en `desktop/package.json`, con `package-lock.json` versionado.
- Importaciones del renderer con el alias `@/`.
- El renderer solo habla con el sistema por `window.drakter`. El contrato está en `desktop/electron/shared/bridge.ts` y cada mensaje se valida en el proceso principal.

## Python

- Backend: Python `>=3.12,<3.13` por elección, con `uv` y `uv.lock` versionado.
- Hermes: venv propio con Python `>=3.14`, desde git con el tag v0.22.7 (`b200f5bc`), nunca desde PyPI.
- Código tipado, con `Final` para las constantes. Modelos y configuración con Pydantic y `pydantic-settings`.
- Variables de entorno con prefijo `DRAKTER_`.
- Punto de entrada único: `python -m app`, desde `backend/`.
- `mypy` y `ruff` no están configurados.

## Errores de la API

Todo error HTTP usa el mismo sobre, definido en `backend/app/core/errors.py`:

```json
{"error": {"code": "...", "message": "...", "request_id": "...", "details": []}}
```

- `details` lleva `field`, `code` y `message`; nunca la entrada del usuario.
- Códigos actuales: `validation_error`, `internal_error`, `http_<estado>`, `unauthorized`, `forbidden_client`, `forbidden_host`, `forbidden_origin`, `service_unavailable`.
- Los errores de la aplicación se lanzan con `AppError(code, message, status_code, details)`.
- `request_id` lo genera siempre el servidor. La traza de un 500 solo va al log.

## Secretos

- Nada de secretos en el repositorio. `.env` está ignorado, y `.env.example` y `backend/.env.example` solo llevan nombres.
- Configuración real: `~/.config/drakter/.env`, fuera del repositorio.
- Las claves y el token de sesión nunca van a logs. El backend redacta los campos sensibles y lo que parece una credencial.

## Comprobación

Política mínima de `CLAUDE.md` §4: hecho significa que se ejecuta, hace lo esperado y la interfaz se ve bien. Basta una comprobación rápida. Sin suites exhaustivas, sin cobertura, sin TDD y sin repetir pruebas superadas.

Se admite una comprobación puntual solo en cuatro casos: rutas y permisos del almacén, confirmaciones destructivas, migraciones y copias, y que la memoria no pueda sobrescribir la seguridad.

Forma actual: scripts sueltos contra el sistema real (`backend/tests/check_database.py`, `backend/tests/check_security.py`). No hay `pytest` ni `vitest` configurados.
