# Drakter

Agente personal de IA con aplicación de escritorio propia. Local-first, para un solo usuario, en Linux primero.

El diseño completo son tres sistemas conectados por APIs internas: Core (agente, personalidad, memoria, herramientas), Desktop (Electron + React) y Workspace (datos en SQLite), con un backend FastAPI en medio.

**Hoy no es usable como agente: no hay chat, ni modelo conectado, ni ningún módulo funcional.** Lo que existe es la base técnica, y parte sigue en ramas sin fusionar.

## Estado real

Foto del 2026-11-04. `drakter/build` es la rama de integración y `main` no se ha tocado.

| Existe | Dónde | Qué hace |
|---|---|---|
| Planificación y control | `docs/` | Plan, hoja de ruta, estado y decisiones |
| Scripts de desarrollo | `scripts/` | Comprobar el entorno y arrancar |
| Carcasa de escritorio | `desktop/`, en `drakter/build` | Electron, navegación y páginas de módulos sin datos. Sin conexión al backend: `useDrakterState()` devuelve siempre `offline`, el envío de mensajes está deshabilitado y el personaje es un marco vacío |
| Identidad | `agent/identity/`, en `drakter/build` | 14 archivos Markdown que aún no carga nada |
| Boceto del personaje | `desktop/design/character/`, en `drakter/build` | SVG sustituto que la aplicación no carga: `characterRenderer` sigue en `null` |
| Backend base | Rama `drakter/backend-base`, sin fusionar | FastAPI en `127.0.0.1:8765` con `GET /health`, `GET /api/v1/auth/check` y `WS /ws`. El sistema de migraciones existe, pero no hay ninguna migración ni tablas de dominio. Contrato en `backend/CONTRACT.md` |
| Stub de LLM para desarrollo | Rama `drakter/dev-stub`, sin fusionar | `tools/dev-llm-stub/`: respuestas guionizadas para probar el cableado de Hermes. No es un modelo |

| No existe | Nota |
|---|---|
| Hermes integrado y Claude Haiku conectado | Ningún código de la aplicación llama a un modelo |
| Chat con el agente | Solo el campo de texto deshabilitado |
| Memoria y OpenViking | |
| Voz | |
| Tareas, proyectos, hábitos, calendario, asignaturas, almacén, relaciones | Solo páginas vacías en la carcasa |
| Personaje Rive real | |

## Estructura de carpetas

```
.
├── .claude/        instrucciones, agentes, skills y comandos para Claude Code
├── agent/identity/ personalidad en archivos
├── desktop/        Electron, React, TypeScript
├── docs/           plan, hoja de ruta, estado, decisiones, arquitectura y convenciones
├── scripts/        check-env.sh y dev.sh
├── .env.example    plantilla de configuración (solo nombres)
├── .gitignore
├── CHANGELOG.md
└── README.md
```

`agent/` y `desktop/` ya están en `drakter/build`, pero no en `drakter/repo-base`, que partió de antes de esas fusiones. Aparecerán al fusionar sus ramas:

```
├── backend/        FastAPI, SQLite (drakter/backend-base)
└── tools/          dev-llm-stub    (drakter/dev-stub)
```

## Requisitos

- **Python 3.12 para el backend**, por elección del proyecto: `requires-python` admite solo 3.12 y se usa el comando `python3.12`.
- **Python >=3.14 para Hermes**, en un venv propio, separado del backend. Hermes se instalará desde git con el tag v0.22.7 (`b200f5bc`), nunca desde PyPI. Aún no está integrado.
- **`uv`**, que crea el venv del backend. Todavía no está en el `PATH` de la máquina de desarrollo.
- **Node 24 y npm**, que son las versiones usadas aquí.
- Sesión gráfica para abrir el escritorio.

Máquina de desarrollo: i7-8665U, Intel UHD 620 sin VRAM dedicada y 14 GB de RAM. El plan maestro habla de 32 GB y 4 GB de VRAM, que no se corresponden con ella.

La instalación la ejecutas tú, y solo es posible con `backend/` y `desktop/` presentes:

```sh
(cd backend && uv sync --frozen)
(cd desktop && npm ci)
```

## Comprobar el entorno

```sh
scripts/check-env.sh
```

No admite argumentos. Imprime líneas `OK`, `AVISO` o `FALTA` y sale con 1 si hay algún `FALTA`, con 0 si no. Comprueba `python3.12`, un Python >=3.14 para el venv de Hermes (solo `AVISO` si no hay), Node, npm, `uv`, la existencia y los permisos de `~/.config/drakter/.env` (sin leerlo), el venv de `backend/`, `node_modules` de `desktop/`, el sandbox de Electron y la sesión gráfica.

## Arrancar en desarrollo

```sh
scripts/dev.sh [all|backend|desktop]
```

- `all`, el modo por defecto, arranca el backend, espera a `/health`, arranca el escritorio y para el backend al salir.
- `backend` y `desktop` arrancan solo esa parte en primer plano.

El script no instala nada. Si falta `backend/` o `desktop/` en tu checkout, sale con error y dice qué lo resuelve: hoy `drakter/build` no tiene `backend/`, así que `all` y `backend` fallan allí hasta fusionar `drakter/backend-base`. Aun con ambos, el escritorio seguirá mostrando `offline`, porque no está conectado al backend.

### Sandbox de Electron

En la máquina de desarrollo AppArmor restringe los espacios de nombres sin privilegios (`kernel.apparmor_restrict_unprivileged_userns=1`), y sin más ajustes Electron aborta con un error de `chrome-sandbox`. `dev.sh` no desactiva el sandbox por su cuenta, y `check-env.sh` da un `AVISO`. Hay dos salidas:

- Desactivarlo solo en esa sesión de desarrollo, que es lo que se ha probado: `ELECTRON_DISABLE_SANDBOX=1 scripts/dev.sh`.
- Dar a `chrome-sandbox` su propietario y modo, sin probar todavía, con `sudo chown root:root` y `sudo chmod 4755` sobre `desktop/node_modules/electron/dist/chrome-sandbox`. Hay que repetirlo tras cada `npm ci`.

## Configuración y secretos

El backend lee las variables del entorno y de `~/.config/drakter/.env` (respeta `XDG_CONFIG_HOME`). **No lee ningún `.env` en la raíz del repositorio.**

`.env.example` es la plantilla. Se copia a esa ruta, nunca lleva valores reales y `.env` está en `.gitignore`. `cp -n` no sobrescribe un `.env` que ya exista.

```sh
mkdir -p ~/.config/drakter
cp -n .env.example ~/.config/drakter/.env
chmod 600 ~/.config/drakter/.env
```

**Después de copiar, borra toda línea que dejes sin valor.** Para el backend `NOMBRE=` es un valor vacío, no una variable ausente: con `DRAKTER_PORT`, `DRAKTER_DATA_DIR`, `DRAKTER_RUNTIME_DIR` o `DRAKTER_LOG_LEVEL` vacías no arranca, y con `DRAKTER_ALLOWED_ORIGINS` vacía no admite ningún origen.

| Variable | Por defecto | Formato |
|---|---|---|
| `DRAKTER_PORT` | `8765` | Entero entre 1024 y 65535 |
| `DRAKTER_DATA_DIR` | Directorio de datos del usuario | Ruta absoluta |
| `DRAKTER_RUNTIME_DIR` | Directorio de ejecución del usuario | Ruta absoluta |
| `DRAKTER_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` o `ERROR` |
| `DRAKTER_ALLOWED_ORIGINS` | `app://drakter` | `scheme://host[:port]` separados por comas |

La dirección de escucha es fija, `127.0.0.1`, y no se configura. El resto de variables de `.env.example` están reservadas: nada las lee aún de ese archivo.

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Convenciones](docs/CONVENTIONS.md)
- [Estado de implementación](docs/IMPLEMENTATION_STATUS.md)
- [Decisiones](docs/DECISIONS.md)
- [Plan maestro](docs/MASTER_PLAN.md)
