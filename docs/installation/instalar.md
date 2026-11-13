# Instalar Drakter en esta máquina

> **Estado:** contrastada con `drakter/integracion` (`7fd30e1`), que reúne todas las ramas `drakter/*`. `scripts/check-env.sh` se ejecutó en esta máquina (9 OK, 1 AVISO de sandbox). El arranque completo con la app real depende de la clave de API: sin ella solo se ha probado con el LLM de pruebas (`scripts/verify-all.sh`).

Esta guía deja Drakter listo para ejecutarse en modo desarrollo desde el repositorio. El instalador `.deb` está en [paquete-deb.md](paquete-deb.md).

## Qué esperar hoy

El backend monta solo cada `backend/app/api/<módulo>.py` que tenga `router` (`_discover_routers()` en `backend/app/main.py`), además de la memoria. Las pantallas Hoy, Inicio, Hábitos, Tareas, Proyectos, Almacén, Calendario, Asignaturas, Relaciones y Configuración están en la navegación. Cada guía de [usage](../usage/README.md) indica lo que aún falta en su módulo.

## Requisitos

- Ubuntu 26.04 (la máquina de referencia) con sesión gráfica.
- Node 24 con `npm`. Aquí: v24.21.0, en `~/.local/bin`.
- `python3.12` para el backend (`requires-python = ">=3.12,<3.13"`).
- Python >=3.14 solo para Hermes, en su propio venv: [hermes-y-openviking.md](hermes-y-openviking.md).
- `uv` en el PATH (aquí: 0.13.8, en `~/.local/bin`). Instalación: <https://docs.astral.sh/uv/>. Comprueba con `uv --version`.

## Pasos

1. Clona el repositorio y entra en la rama que contenga el código integrado (hoy, `drakter/integracion` en local):

   ```sh
   git clone https://github.com/Lordi898/Drakter.git drakter
   cd drakter
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
scripts/dev.sh [all|desktop]
```

- `all`, el modo por defecto, comprueba backend y escritorio y abre Electron con `npm run dev`. Avisa si no encuentra `hermes-python` (sin él el chat no funciona).
- `desktop` abre solo el escritorio.
- `backend` no existe como modo: el backend no se arranca suelto. Lo lanza Electron (`desktop/electron/main/backendProcess.ts`) con `backend/.venv/bin/python -m app`, le pasa las credenciales por stdin y lee por stdout el puerto efímero que anuncia (D-14).
- El script no instala nada. Si falta algo, dice cómo resolverlo.

## Lanzador de escritorio (opcional)

1. Compila: `cd desktop && npm run build`. El lanzador falla sin `out/main/index.js`.
2. Arranca con `scripts/drakter`, que apunta a `desktop/electron/launcher/drakter`.
3. Para tenerlo en el menú de aplicaciones: `desktop/electron/launcher/install-launcher.sh`. Crea `~/.local/share/applications/drakter.desktop`.

El lanzador se niega a arrancar si el sandbox no está configurado: [sandbox-electron.md](sandbox-electron.md).

## Cómo saber que funciona

- `scripts/check-env.sh` sin ningún `FALTA`.
- Al abrir la app, la pantalla inicial (Hoy) carga y el personaje no está en `offline`.
- Pasada integrada, que no instala nada: `scripts/verify-all.sh` (`--help` para las opciones; `--headless` sin ventana). Usa un LLM de pruebas, así que no demuestra que el modelo real funcione. Sale con 0 sin fallos, 1 con algún fallo y 2 si no pudo ejecutarse.

No hay puerto fijo que consultar con `curl`: el backend escucha en `127.0.0.1` en un puerto efímero y exige el token de sesión que solo conoce Electron.

## Dónde van los datos

| Qué | Ruta en Linux |
|---|---|
| `drakter.db`, `backups/`, `logs/` | `~/.local/share/drakter` (o `DRAKTER_DATA_DIR`, ruta absoluta) |
| Configuración | `~/.config/drakter/.env` (respeta `XDG_CONFIG_HOME`) |

El backend solo lee `DRAKTER_DATA_DIR` y `DRAKTER_LOG_LEVEL` (`backend/app/core/config.py`); el agente, sus propias variables ([clave-api.md](clave-api.md)). No lee ningún `.env` en la raíz del repositorio.

## Parar

- `scripts/dev.sh`: `Ctrl+C`. Para el escritorio, y Electron para el backend.
- Cerrar la ventana de Drakter también para el backend.

## Problemas frecuentes

- `invalid configuration: <campos>`: algún `DRAKTER_*` es inválido (por ejemplo, `DRAKTER_DATA_DIR` relativa). Las líneas sin valor se ignoran (`env_ignore_empty`).
- `falta backend/.venv`: ejecuta `cd backend && uv sync --frozen`.
- `backend/.venv no es Python 3.12`: ejecuta `rm -rf backend/.venv && cd backend && uv sync --frozen`.

## Pendiente

- `.env.example` de la raíz aún lista variables que el backend ya no lee (`DRAKTER_PORT`, `DRAKTER_RUNTIME_DIR`, `DRAKTER_ALLOWED_ORIGINS`...). Guíate por [clave-api.md](clave-api.md).
