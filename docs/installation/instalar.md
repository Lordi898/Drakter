# Instalar Drakter en esta máquina

> **Estado:** integrado en `drakter/build` (2da8bef): `backend/`, `desktop/` y `scripts/`. La integración sigue en marcha, así que la rama puede ir por delante de esta guía. NO COMPROBADO: nadie ha ejecutado estos pasos de principio a fin.

Esta guía deja Drakter listo para ejecutarse en modo desarrollo desde el repositorio. El instalador `.deb` está en [paquete-deb.md](paquete-deb.md).

## Qué esperar hoy

En `2da8bef`, `backend/app/main.py` solo registra `health`, `auth` y `ws`. Los routers de módulos (`calendar`, `habits`, `settings`, `today`...) están en `backend/app/api/`, pero sin registrar. Puedes instalar y arrancar la base, pero las pantallas de módulos aún no reciben datos de ese backend. Tareas, almacén, chat, voz, Hermes y seguridad siguen en sus ramas: cada guía de [usage](../usage/README.md) indica de cuál sale.

El `README.md` de la raíz aún dice que `backend/` no está en `drakter/build`. Ya no es cierto en `2da8bef`.

## Requisitos

- Ubuntu 26.04 (la máquina de referencia) con sesión gráfica.
- Node 24 con `npm`. Aquí: v24.21.0, en `~/.local/bin`.
- `python3.12` para el backend (`requires-python = ">=3.12,<3.13"`).
- Python >=3.14 solo para Hermes, en su propio venv: [hermes-y-openviking.md](hermes-y-openviking.md).
- `uv`. **No está en el PATH de esta máquina** y hace falta para crear el venv del backend. **Pendiente:** ninguna rama da el comando de instalación; el empaquetado remite a <https://docs.astral.sh/uv/>. Comprueba con `uv --version`.

## Pasos

1. Clona el repositorio y entra en la rama de integración. En `origin` solo están `main` y `drakter/build`:

   ```sh
   git clone https://github.com/Lordi898/Drakter.git drakter
   cd drakter
   git checkout drakter/build
   ```

2. Instala las dependencias:

   ```sh
   (cd backend && uv sync --frozen)
   (cd desktop && npm ci)
   ```

3. Comprueba el entorno. Imprime líneas `OK`, `AVISO` o `FALTA` y sale con 1 si hay algún `FALTA`:

   ```sh
   scripts/check-env.sh
   ```

4. Añade la clave: [clave-api.md](clave-api.md).
5. Si `check-env.sh` avisa de que Electron abortará por su sandbox, sigue [sandbox-electron.md](sandbox-electron.md).

## Arrancar en desarrollo

```sh
scripts/dev.sh [all|backend|desktop]
```

- `all`, el modo por defecto, arranca el backend, espera a `/health`, abre el escritorio y para el backend al salir.
- `backend` y `desktop` arrancan solo esa parte, en primer plano.
- El script no instala nada. Si falta algo, dice cómo resolverlo.

Electron tiene además su propio supervisor del backend (`desktop/electron/main/backendProcess.ts`): usa `backend/.venv/bin/python -m app` o, si no existe, `uv run --frozen python -m app`. NO COMPROBADO cómo convive con `dev.sh`.

## Lanzador de escritorio (opcional)

1. Compila: `cd desktop && npm run build`. El lanzador falla sin `out/main/index.js`.
2. Arranca con `scripts/drakter`, que apunta a `desktop/electron/launcher/drakter`.
3. Para tenerlo en el menú de aplicaciones: `desktop/electron/launcher/install-launcher.sh`. Crea `~/.local/share/applications/drakter.desktop`.

El lanzador se niega a arrancar si el sandbox no está configurado: [sandbox-electron.md](sandbox-electron.md).

## Cómo saber que funciona

Con el backend en marcha:

```sh
curl http://127.0.0.1:8765/health
```

Debe responder `{"status":"ok"}`. Un 503 `service_unavailable` indica que la base de datos no se pudo abrir.

Pasada integrada, que no instala nada: `scripts/verify-all.sh`. Usa un LLM de pruebas, así que no demuestra que el modelo real funcione. Sale con 0 sin fallos, 1 con algún fallo y 2 si no pudo ejecutarse.

## Dónde van los datos

| Qué | Ruta en Linux |
|---|---|
| `drakter.db`, `backups/`, `logs/` | `~/.local/share/drakter` (o `DRAKTER_DATA_DIR`) |
| Configuración | `~/.config/drakter/.env` (respeta `XDG_CONFIG_HOME`) |
| `session.json` con el token de sesión | `$XDG_RUNTIME_DIR/drakter` (o `DRAKTER_RUNTIME_DIR`) |

El backend escucha siempre en `127.0.0.1`, puerto 8765 salvo que definas `DRAKTER_PORT` (1024 a 65535). No lee ningún `.env` en la raíz del repositorio.

## Parar

- `scripts/dev.sh`: `Ctrl+C`. Para el backend y el escritorio.
- Backend suelto: `Ctrl+C` en su terminal.

## Problemas frecuentes

- `invalid configuration: <campos>`: algún `DRAKTER_*` es inválido o está vacío. Una línea `DRAKTER_PORT=` sin valor impide arrancar: bórrala. Comprobado con `pydantic-settings` en la versión del backend.
- `cannot bind 127.0.0.1:8765`: el puerto está ocupado. Cierra el otro proceso o usa `DRAKTER_PORT`.
- `falta backend/.venv`: ejecuta `cd backend && uv sync --frozen`.
- `backend/.venv no es Python 3.12`: ejecuta `rm -rf backend/.venv && cd backend && uv sync --frozen`.

## Pendiente

- Comando para instalar `uv`.
- Registrar los routers de módulos en `backend/app/main.py`.
- Integrar en `drakter/build` las ramas que faltan.
