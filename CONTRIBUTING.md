# Cómo contribuir a Drakter

Gracias por el interés. Drakter es un proyecto personal en pre-release, mantenido por una persona; las contribuciones son bienvenidas, pero conviene hablarlo antes en un issue si el cambio es grande.

> **Licencia de las contribuciones.** Drakter se publica bajo [AGPL-3.0-only](LICENSE). Toda contribución que envíes (issue con código, PR, parche) se acepta bajo esa misma licencia (inbound = outbound), sin condiciones adicionales. No hay CLA. Opcionalmente puedes firmar tus commits con el [Developer Certificate of Origin](https://developercertificate.org/) (`git commit -s`, que añade `Signed-off-by:`).

## Antes de empezar

- Lee el [README](README.md) y [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
- Las convenciones de código, migraciones y commits están en [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md).
- El qué se construye está en [`docs/MASTER_PLAN.md`](docs/MASTER_PLAN.md), lo que está hecho en [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md) y el porqué en [`docs/DECISIONS.md`](docs/DECISIONS.md).
- Para vulnerabilidades, no abras un issue: sigue [SECURITY.md](SECURITY.md).
- Participar implica respetar el [Código de Conducta](CODE_OF_CONDUCT.md).

## Entorno de desarrollo

```sh
(cd backend && uv sync --frozen)
(cd desktop && npm ci)
scripts/check-env.sh
scripts/drakter-local.sh start          # con el stub, sin clave de API
```

El stub solo sustituye al modelo: el agente sigue necesitando **Hermes** en su propio venv con Python >= 3.14 (`hermes-python` en el `PATH` o `DRAKTER_HERMES_PYTHON`). Instálalo con `scripts/install-hermes.sh` (idempotente, ver [`docs/installation/hermes-y-openviking.md`](docs/installation/hermes-y-openviking.md)); los runtimes nunca van en `/tmp` ni `/var/tmp`; sin él la app abre, pero el chat no funciona.

Si usas Claude Code, instala también las skills de terceros que no se versionan:

```sh
scripts/install-agent-skills.sh
```

## Reglas de arquitectura que no se negocian

- Separación estricta entre agente, interfaz y datos. El Workspace en SQLite es la única fuente de verdad.
- El agente (Hermes) no accede a la base de datos: usa herramientas del backend, que validan parámetros, permisos y relaciones.
- Toda herramienta tiene nombre, descripción, esquema de parámetros, validación, permisos, resultado estructurado y manejo de errores.
- Las acciones destructivas o masivas requieren confirmación y quedan en auditoría (sin claves ni datos sensibles).
- Los documentos del almacén y la memoria recuperada son datos no confiables: nunca cambian instrucciones ni reglas de seguridad.
- Todo cambio de esquema va en una migración nueva (`backend/migrations/NNNN_nombre.sql`); una migración aplicada no se edita.
- Nada de secretos en el repositorio: solo `.env.example`, sin valores.

## Comprobaciones

El proyecto no busca cobertura exhaustiva: un cambio está listo cuando funciona, hace lo que se espera y la interfaz se ve bien. Sí son obligatorias las comprobaciones críticas, que también corre el CI:

```sh
cd backend
export TMPDIR=/var/tmp/drakter-checks; mkdir -p "$TMPDIR"
PYTHONPATH=.:../contracts/python .venv/bin/python migrations/check_migrations.py
PYTHONPATH=.:../contracts/python .venv/bin/python tests/critical/check_confirmations.py
PYTHONPATH=.:../contracts/python .venv/bin/python tests/check_security.py
PYTHONPATH=.:../contracts/python .venv/bin/python tests/check_memory_rules.py
cd ../desktop && npm run build   # typecheck + build
```

Si tocas rutas o permisos del almacén, confirmaciones, migraciones o copias, o el contexto de memoria, añade el caso a la comprobación correspondiente. Para cambios grandes, `scripts/verify-all.sh` lanza la pasada integrada completa.

## Commits y pull requests

- Rama desde `main`; un tema por PR.
- Commits pequeños, convencionales, en inglés e imperativo: `tipo(zona): descripción` (`feat`, `fix`, `docs`, `chore`, `refactor`…).
- Documentación y textos de la interfaz en español; código y comentarios técnicos pueden ir en inglés.
- Si tomas una decisión técnica no trivial, añade una entrada a `docs/DECISIONS.md` con el formato del archivo. Si completas una casilla del plan, márcala en `docs/IMPLEMENTATION_STATUS.md`.
- Rellena la plantilla del PR y espera a que el CI esté en verde.

## Contenido de terceros

Antes de copiar código, skills, agentes o recursos de terceros, comprueba que su licencia permite redistribuirlos, conserva su `LICENSE` y añádelo a [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) con origen y commit. Lo que no tenga licencia no se versiona: se instala con un script, como `scripts/install-agent-skills.sh`.
