# Instalar Drakter (guía completa)

> **Estado:** contrastada con `main` el 2026-11-27. Comprobado en la máquina de referencia (Ubuntu 26.04, i7-8665U, 14 GB, gráfica integrada): el venv del backend con `python3.12 -m venv` + `pip install -r requirements.txt` instala, el backend importa y sus comprobaciones críticas pasan.

Esta guía deja Drakter funcionando **desde el repositorio** (modo desarrollo), paso a paso y con todos los comandos. Para instalar la app empaquetada (AppImage, sin sudo) ve a [primeros pasos](../usage/primeros-pasos.md). Para el `.deb`, a [paquete-deb.md](paquete-deb.md).

Drakter usa **tres entornos de Python separados**, cada uno en su venv. No se mezclan:

| Entorno | Python | Dónde vive | Cómo se instala |
|---|---|---|---|
| Backend (FastAPI + SQLite) | **3.12** | `backend/.venv` | `requirements.txt` con `pip`, o `uv sync` (paso 4) |
| Hermes (el agente) | **3.14** | `~/.local/share/drakter/venvs/hermes` | `scripts/install-hermes.sh` (paso 6) |
| Voz (Pipecat), opcional | **3.12** | `~/.local/share/drakter/venvs/voice` | `scripts/install-voice.sh` (paso 7) |

Además, el escritorio (Electron + React) necesita **Node 24**.

## 1. Requisitos del sistema

- **Linux** con sesión gráfica. Se desarrolla en Ubuntu 26.04 con GNOME; la arquitectura está preparada para Windows, pero solo se ha probado en Linux.
- **git** y **curl**: `sudo apt install git curl`.
- Unos **3 GB de disco** para dependencias y modelos, y **8 GB de RAM** o más (con voz, mejor 14 GB).

Comprueba lo que ya tienes:

```sh
git --version
python3.12 --version      # puede no existir: el paso 2 lo resuelve
node --version            # debe ser v24.x
uv --version
```

## 2. Herramientas: uv, Python 3.12 y Node 24

**uv** (gestor de Python y de entornos; lo usan los scripts de instalación):

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
# abre otra terminal, o:  source ~/.local/bin/env
uv --version
```

**Python 3.12.** Si `python3.12 --version` falla, instálalo con uv, sin sudo:

```sh
uv python install 3.12
mkdir -p ~/.local/bin
ln -sfn "$(uv python find --managed-python 3.12)" ~/.local/bin/python3.12   # deja python3.12 en el PATH
python3.12 --version       # Python 3.12.x
```

`~/.local/bin` debe estar en tu `PATH`. En Ubuntu lo está si la carpeta existe al iniciar sesión; si no, añade `export PATH="$HOME/.local/bin:$PATH"` a `~/.bashrc`. `scripts/check-env.sh` exige `python3.12` en el `PATH`.

Si prefieres el de tu distribución, en Ubuntu: `sudo apt install python3.12 python3.12-venv`. Si tu versión de Ubuntu no lo trae, usa la vía de uv.

**Node 24 y npm.** Por ejemplo, con [nvm](https://github.com/nvm-sh/nvm):

```sh
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# abre otra terminal
nvm install 24
node --version             # v24.x
```

## 3. Descargar el código

```sh
git clone https://github.com/Lordi898/Drakter.git
cd Drakter
```

A partir de aquí, todos los comandos se ejecutan **desde la raíz del repositorio** (`Drakter/`), salvo que se indique otra carpeta.

## 4. Entorno del backend (Python 3.12)

Elige **una** de las dos opciones. Las dos dejan el mismo entorno en `backend/.venv`, con las mismas versiones fijadas.

### Opción A: venv + `pip` + `requirements.txt`

```sh
cd backend
python3.12 -m venv .venv                 # crea el entorno virtual
                                         # (sin python3.12 en el PATH: "$(uv python find 3.12)" -m venv .venv)
source .venv/bin/activate                # lo activa: el prompt muestra (.venv)
python --version                         # Python 3.12.x
pip install --upgrade pip
pip install -r requirements.txt          # dependencias fijadas + contratos (../contracts/python)
deactivate                               # sale del entorno (opcional)
cd ..
```

- `requirements.txt` instala también los contratos del proyecto en modo editable (`-e ../contracts/python`). Por eso hay que ejecutarlo **desde `backend/`**.
- Para volver a entrar en el entorno: `source backend/.venv/bin/activate`. No hace falta activarlo para usar la app: Electron lanza `backend/.venv/bin/python` directamente.
- Para lanzar a mano las comprobaciones del backend con el entorno activado, desde `backend/`: `PYTHONPATH=. python tests/check_security.py`.

### Opción B: uv (la que usan el CI y los scripts)

```sh
(cd backend && uv sync --frozen)
```

Crea `backend/.venv` con Python 3.12 (lo descarga si falta) y las versiones exactas de `backend/uv.lock`. Para activarlo es igual: `source backend/.venv/bin/activate`.

### Mantener `requirements.txt`

La fuente de verdad es `backend/pyproject.toml` + `backend/uv.lock`. `backend/requirements.txt` se **genera** a partir de ellos; no se edita a mano. Tras cambiar dependencias:

```sh
(cd backend && uv add <paquete>)        # o editar pyproject.toml y: uv lock
scripts/export-requirements.sh          # regenera backend/requirements.txt
scripts/export-requirements.sh --check  # lo mismo que comprueba el CI
```

## 5. Escritorio (Node 24)

```sh
(cd desktop && npm ci)
```

Instala las dependencias exactas de `desktop/package-lock.json` y descarga el binario de Electron (~100 MB) con su `postinstall`. Si falta el binario: `node desktop/scripts/ensure-electron.cjs` (es idempotente; `scripts/dev.sh` y `scripts/drakter-local.sh` lo ejecutan solos).

## 6. Hermes, el agente (Python 3.14)

```sh
scripts/install-hermes.sh
```

- **Qué hace:** instala Python 3.14 con uv, clona Hermes **v0.22.7** (commit fijado `b200f5bc`) en `~/.local/share/drakter/src/hermes-agent` y crea su venv en `~/.local/share/drakter/venvs/hermes`. Por último deja el lanzador `~/.local/bin/hermes-python`, que es el que usa el backend.
- **Repetirlo:** es idempotente, así que se puede volver a ejecutar sin problema.
- **No uses `pip install hermes-agent`:** la versión de PyPI está retirada a propósito.

Detalle: [hermes-y-openviking.md](hermes-y-openviking.md). Sin Hermes la app abre, pero el chat y el agente no funcionan.

## 7. Voz (opcional)

La voz necesita su venv, unos modelos en `~/.local/share/drakter/models/` y, para el atajo Super+J, GNOME. Ejecútalo **desde el checkout principal, no desde un worktree**:

```sh
scripts/install-voice.sh                                  # venv de voz (Python 3.12) + voice/requirements.lock
~/.local/share/drakter/venvs/voice/bin/python -m voice check
scripts/install-shortcut.sh install                       # atajo Super+J (opcional)
```

Equivale a hacerlo a mano así:

```sh
uv venv --python 3.12 ~/.local/share/drakter/venvs/voice
uv pip install --python ~/.local/share/drakter/venvs/voice/bin/python -r voice/requirements.lock
uv pip install --python ~/.local/share/drakter/venvs/voice/bin/python -e contracts/python
```

El script, además, comprueba los modelos y copia los de Kokoro si faltan. Qué modelos hacen falta y dónde: [voz.md](voz.md). Si no vas a usar voz, pon `DRAKTER_VOICE_ENABLED=false` en el `.env` (paso 8).

## 8. Configuración y claves (`.env`)

```sh
mkdir -p ~/.config/drakter
cp -n .env.example ~/.config/drakter/.env
chmod 600 ~/.config/drakter/.env
nano ~/.config/drakter/.env        # rellena al menos ANTHROPIC_API_KEY
```

- **Dónde va:** el `.env` va en `~/.config/drakter/.env`, **nunca en el repositorio**.
- **Qué contiene:** todas las variables, con sus valores por defecto, están en la [guía del `.env`](configuracion-env.md).
- **La clave del modelo:** cómo conseguirla y comprobarla, en [clave-api.md](clave-api.md).

## 9. Comprobar el entorno

```sh
scripts/check-env.sh
```

Imprime `OK`, `AVISO` o `FALTA` por cada requisito y sale con 1 si falta algo:

- **Versiones:** Python 3.12 y 3.14, Node, npm y uv.
- **Entornos:** `backend/.venv`, `hermes-python` y los venvs de voz. También comprueba que ninguno resuelva a `/tmp` o sea un enlace roto.
- **Sistema:** el `.env` (sin leerlo), el sandbox de Electron y la sesión gráfica.

**Sandbox de Electron.** En Ubuntu reciente, si `check-env.sh` avisa del sandbox, tienes dos opciones:

- Sigue [sandbox-electron.md](sandbox-electron.md). Es un paso con sudo, una sola vez.
- En desarrollo, arranca sin sandbox: `ELECTRON_DISABLE_SANDBOX=1 DRAKTER_DEV_NO_SANDBOX=1 scripts/dev.sh`.

## 10. Arrancar

```sh
scripts/drakter-local.sh start anthropic   # app con Claude Haiku 5.5 real (desacoplada de la terminal)
scripts/drakter-local.sh status
scripts/drakter-local.sh stop
```

Otras formas:

- `scripts/dev.sh all`: escritorio en primer plano, con recarga en caliente; se para con `Ctrl+C`.
- `scripts/drakter-local.sh start`: arranca con el stub, sin clave.
- `scripts/drakter`: lanzador; antes hay que compilar con `cd desktop && npm run build`.

El backend **no se arranca aparte**: lo lanza Electron en `127.0.0.1` con un puerto efímero y le pasa las credenciales por stdin. No hay puerto que abrir ni que consultar con `curl`.

## 11. Cómo saber que funciona

- `scripts/check-env.sh` sin ningún `FALTA`.
- Se abre la ventana en **Hoy** y el indicador de estado no dice «Desconectado».
- Escribes en el chat y Drakter responde. Con el stub, responde un texto fijo de prueba.
- Con voz: Super+J o «Hey Jarvis» y hablas.
- Pasada integrada completa, que no instala nada (backend + stub + Electron): `scripts/verify-all.sh`. Con `--headless` no abre ventana.

## Dónde van los datos

| Qué | Ruta |
|---|---|
| Base de datos `drakter.db`, copias `backups/`, logs `logs/` | `~/.local/share/drakter` (o `DRAKTER_DATA_DIR`) |
| Configuración y claves | `~/.config/drakter/.env` |
| Hermes, voz, modelos, runtimes | `~/.local/share/drakter/{src,venvs,models}` |

Los runtimes nunca van en `/tmp` ni en `/var/tmp`: una limpieza los borraría.

## Actualizar

```sh
scripts/update.sh             # git pull, dependencias que cambien, copia de la base, migraciones y reinicio
```

Si instalaste el backend con la opción A (pip), tras actualizar repite `source backend/.venv/bin/activate && cd backend && pip install -r requirements.txt`. `update.sh` usa uv. Copias y restauración: [copias-y-actualizacion.md](../usage/copias-y-actualizacion.md).

## Desinstalar

```sh
scripts/drakter-local.sh stop
scripts/install-shortcut.sh remove                      # si instalaste el atajo
rm -rf backend/.venv desktop/node_modules               # entornos del repositorio
rm -rf ~/.local/share/drakter/venvs ~/.local/share/drakter/src ~/.local/bin/hermes-python ~/.local/bin/python3.14
```

Tus **datos** (`~/.local/share/drakter/drakter.db`, `backups/`) y tu **configuración** (`~/.config/drakter/`) no se borran con esto. Bórralos solo si de verdad quieres perderlos, y haz antes una copia.

## Problemas frecuentes

- **`falta backend/.venv`:** haz el paso 4.
- **`backend/.venv no es Python 3.12`:** `rm -rf backend/.venv` y repite el paso 4.
- **`pip install -r requirements.txt` falla con `../contracts/python`:** lo estás ejecutando fuera de `backend/`. Haz `cd backend` primero.
- **`invalid configuration: <campos>`:** algún valor del `.env` no es válido (por ejemplo, una ruta relativa). Ver [configuracion-env.md](configuracion-env.md).
- **Electron se cierra con un error de `chrome-sandbox`:** [sandbox-electron.md](sandbox-electron.md).
- **El chat no responde:** falta Hermes (paso 6) o la clave (paso 8). `scripts/check-env.sh` lo dice.
- Más: [problemas.md](../usage/problemas.md).
