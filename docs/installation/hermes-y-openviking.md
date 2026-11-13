# Hermes y OpenViking

> **Estado:** integrado en `drakter/build` (2da8bef): `tools/dev-llm-stub/`, el adaptador de OpenViking (hueco cerrado) y `docs/DECISIONS.md`. Sin integrar (solo `drakter/agente-hermes`): `backend/app/integrations/hermes/` entero (contrato, `settings.py`, `home.py`); en 2da8bef esa carpeta no existe. NO COMPROBADO en la app real: nadie ha ejecutado estos pasos y aquí no se ha instalado nada.

Hermes es el agente que razona y llama a las herramientas. Corre como proceso aparte, con su propio entorno de Python. OpenViking es el proveedor de memoria externo. Esta guía cubre solo la parte de Hermes que existe en las ramas. Lee antes [instalar.md](instalar.md) (backend y app) y [clave-api.md](clave-api.md) (clave del modelo).

## Requisitos

- Python 3.14 para Hermes. Su `pyproject.toml` admite `>=3.11,<3.15`, pero el lock es de 3.14 y el proyecto lo exige (`DECISIONS.md`, entrada "Python 3.12 para el backend...").
- Python 3.12 para el backend: es otro entorno distinto. No se comparte venv con Hermes.
- `git` y `uv`. El contrato de Hermes pide `uv sync --frozen`.
- Hermes se instala desde git. No uses `pip install hermes-agent`: la versión de PyPI (0.19.0) está retirada a propósito.

## Instalar Hermes (v0.22.7, commit fijado)

Versión y commit salen de `backend/app/integrations/hermes/CONTRACT.md` (línea 5): v0.22.7, commit `b200f5bc60e31588ba2cb60e288029c4a54ba5fa`.

1. Clona el repositorio. La URL (`homepage` de `.claude/skills/hermes-agent/SKILL.md` en `drakter/agente-hermes`) es `https://github.com/NousResearch/hermes-agent`.
2. Cámbiate al commit fijado: `git checkout b200f5bc60e31588ba2cb60e288029c4a54ba5fa`.
3. Crea el venv con Python 3.14 y las dependencias: `uv sync --frozen --extra anthropic --extra mcp`. Los extras salen del contrato, que cita `--extra anthropic --extra mcp` al explicar que `aiohttp` no entra con ellos y que el preflight lo comprueba.
4. El binario queda en `<venv>/bin/hermes` (así lo usa `tools/dev-llm-stub/check_hermes.sh`, que lo busca en `$VENV/bin/hermes`).

**Pendiente:** el comando exacto de `uv` con Python 3.14 (`--python`) no consta en ninguna rama; el contrato solo dice "Python >=3.14, `uv sync --frozen`".

## Dónde lo espera el backend

Todo son variables con prefijo `DRAKTER_` (`backend/app/integrations/hermes/settings.py`), leídas del entorno y de `~/.config/drakter/.env` (el mismo archivo de [clave-api.md](clave-api.md)).

| Variable | Valor por defecto | Para qué |
|---|---|---|
| `DRAKTER_HERMES_COMMAND` | `hermes` | Un solo ejecutable, sin argumentos ni shell. Con `hermes` a secas se busca en el `PATH`; si está en un venv aparte, pon aquí su ruta completa. |
| `DRAKTER_HERMES_PORT` | `8767` | API de Hermes, solo loopback (1024-65535). |
| `DRAKTER_AGENT_TOOLS_PORT` | `8766` | Puerto de las herramientas del backend. Debe ser distinto del anterior. |
| `DRAKTER_MODEL_PROVIDER` | `anthropic` | `anthropic` o `dev_stub`. |
| `DRAKTER_MODEL_NAME` | `claude-haiku-5-5` | Modelo. |
| `DRAKTER_AGENT_PROVIDER` | `hermes` | `hermes` o `fake`. |
| `DRAKTER_ENV` | `development` | `development` o `production`. |

HERMES_HOME propio: el backend lo genera en `<data_dir>/hermes` (`HomePaths.under` en `home.py`), donde `data_dir` es `DRAKTER_DATA_DIR` (documentada en `backend/.env.example` y `core/config.py`; por defecto el directorio de datos de usuario de `platformdirs` para `drakter`, p. ej. `~/.local/share/drakter`: NO COMPROBADO). Ahí escribe `config.yaml`, `SOUL.md` (reglas de seguridad más los archivos de `agent/identity/`) y el plugin `drakter_guard`. Es un directorio privado (0700): cualquier archivo ajeno en `plugins/` o `hooks/`, o un `.env` dentro, hace que el backend se niegue a arrancar Hermes. No lo edites a mano: se regenera.

## Quién arranca Hermes

Según el contrato, el backend FastAPI supervisa Hermes como subproceso (`hermes gateway run`, API en `127.0.0.1`, `HERMES_HOME` propio, entorno limpio). Por tanto no se arranca a mano.

**Pendiente:** el supervisor (`supervisor.py`) y el preflight (`python -m app.integrations.hermes.preflight`) siguen sin existir: ni en 2da8bef ni en `drakter/agente-hermes` (ahí solo hay `__init__.py`, `home.py` y `settings.py`). No se puede confirmar en código que el backend lo lance.

## Comprobar la versión por commit

Se compara el commit, no el texto de versión (el `pyproject.toml` del tag dice `0.0.0`).

1. En el clon de Hermes: `git rev-parse HEAD`. Debe dar `b200f5bc60e31588ba2cb60e288029c4a54ba5fa`.
2. `<venv>/bin/hermes --version`. El contrato afirma que lo confirma, pero `DECISIONS.md` dice que no se ha ejecutado desde esas ramas: NO COMPROBADO.

## Sin clave real: `dev_stub`

Para probar el cableado sin clave ni red, existe un servidor falso que imita la API de Anthropic (`tools/dev-llm-stub/`, ya en 2da8bef). No es un modelo: no demuestra nada sobre Claude Haiku 5.5.

1. Arranca el stub: `python3 tools/dev-llm-stub/server.py --var sandbox=/ruta/de/pruebas` (ruta absoluta de dos o más niveles). Escucha solo en `127.0.0.1`.
2. Pon `DRAKTER_MODEL_PROVIDER=dev_stub`. La URL por defecto es `http://127.0.0.1:28517`; solo vale `http` en loopback, sin ruta (`DRAKTER_DEV_STUB_URL`).
3. Para una comprobación de Hermes de punta a punta con el stub: `tools/dev-llm-stub/check_hermes.sh <venv-de-hermes> <directorio-de-trabajo>`. Usa un `HERMES_HOME` temporal, no el tuyo.

Se prohíbe en producción: con `DRAKTER_ENV=production`, `dev_stub` hace fallar el arranque del backend (`settings.py`) y el stub sale con código 3. Para uso real, vuelve a `anthropic` y sigue [clave-api.md](clave-api.md).

## OpenViking

Estado real en 2da8bef (`backend/app/integrations/memory/openviking.py`): **no está integrado**. `OpenVikingAdapter` (`openviking.py`) es un hueco cerrado: `status()` dice "OpenViking no esta configurado" y el resto de operaciones lanzan `MemoryBackendUnavailable`. No hay rutas ni cargas útiles de su API.

Lo único decidido (`DECISIONS.md`): entorno propio, Python 3.12 o 3.13, separado del backend y de Hermes.

**Pendiente:** pasos de instalación, comando de arranque, puerto, variables y modelo de embeddings de OpenViking. No constan en ninguna rama; no los inventes. Hasta entonces el agente funciona sin memoria externa (en la configuración de Hermes `memory_enabled` está a `false`).

## Problemas frecuentes (deducibles del código)

- El backend no arranca con `DRAKTER_MODEL_PROVIDER=dev_stub` y `DRAKTER_ENV=production`: es intencionado.
- Error por puertos: `DRAKTER_HERMES_PORT` y `DRAKTER_AGENT_TOOLS_PORT` no pueden coincidir.
- "cannot prepare the Hermes home" o "unexpected content": hay archivos ajenos en `<data_dir>/hermes/plugins`, `hooks` o un `.env`, o permisos más abiertos que 0700/0600. Quita lo ajeno.
- `DRAKTER_HERMES_COMMAND` con espacios o argumentos se rechaza.
